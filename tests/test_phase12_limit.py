from __future__ import annotations

import json
import re
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.sql as sql_api
from pietto.ast_nodes import LimitClause, LiteralExpr, QueryDef
from pietto.errors import Severity
from pietto.ir import RelationIR, ScriptIR, build_ir
from pietto.ir.model import LimitIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_LIMIT = 9_223_372_036_854_775_807
LIMIT_MESSAGE = "Limit must be a static integer from 0 to 9223372036854775807"
POSTGRES_PREFIX = (
    'shape User:\n    id: Int not null\nsource users: User is postgres.table("users")\n'
)
MYSQL_PREFIX = (
    'shape User:\n    id: Int not null\nsource users: User is mysql.table("users")\n'
)


@pytest.mark.parametrize(
    ("source_value", "expected_value"),
    [
        ("100", 100),
        ("0", 0),
        ("9223372036854775807", MAX_LIMIT),
        ("0007", 7),
    ],
)
def test_parser_accepts_static_limit_after_select(
    source_value: str,
    expected_value: int,
) -> None:
    result = parse_source(_relation_source("", source_value), path="limit.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[0])
    assert isinstance(relation.limit_clause, LimitClause)
    assert isinstance(relation.limit_clause.expression, LiteralExpr)
    assert relation.limit_clause.expression.value == expected_value


@pytest.mark.parametrize(
    "body",
    [
        "    from users\n    select:\n        id\n    limit\n",
        ("    from users\n    select:\n        id\n    limit 1\n    limit 2\n"),
        "    from users\n    limit 1\n    select:\n        id\n",
        "    from users\n    select:\n        id\n    limit 1 2\n",
    ],
)
def test_malformed_or_misplaced_limit_remains_parser_error(body: str) -> None:
    result = parse_source(f"query selected:\n{body}", path="limit.pietto")

    assert result.ast is None
    assert result.diagnostics
    assert all(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


def test_order_by_tokens_are_present_without_changing_limit_contract() -> None:
    grammar = (REPO_ROOT / "grammar/Pietto.g4").read_text(encoding="utf-8")
    result = parse_source(
        "query selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "    order by:\n"
        "        id\n",
        path="order.pietto",
    )

    assert "LIMIT: 'limit';" in grammar
    for token in (
        "ORDER: 'order';",
        "BY: 'by';",
        "ASC: 'asc';",
        "DESC: 'desc';",
    ):
        assert token in grammar
    assert result.diagnostics == ()
    assert result.ast is not None


@pytest.mark.parametrize("source_value", ["0", "0007", str(MAX_LIMIT)])
def test_semantic_accepts_valid_static_limits(source_value: str) -> None:
    script = _parse(POSTGRES_PREFIX + _relation_source("", source_value))

    result = analyze(script)

    assert not [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


@pytest.mark.parametrize(
    "operand",
    [
        "9223372036854775808",
        "-1",
        "1.5",
        '"1"',
        "missing",
        "missing()",
        "row.id",
        "1 + 2",
        "true",
        "null",
    ],
)
@pytest.mark.parametrize("mode", ["loose", "checked", "strict"])
def test_invalid_captured_limit_has_one_dedicated_diagnostic(
    operand: str,
    mode: str,
) -> None:
    script = _parse(f"mode {mode}\n" + POSTGRES_PREFIX + _relation_source("", operand))

    result = analyze(script)
    errors = [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]

    assert len(errors) == 1
    diagnostic = errors[0]
    assert diagnostic.code == "PIE-S2307"
    assert diagnostic.message == LIMIT_MESSAGE
    assert diagnostic.suggestion is None


def test_limit_diagnostic_span_covers_only_complete_operand() -> None:
    source = POSTGRES_PREFIX + _relation_source("", "missing(unknown)")
    script = _parse(source, path="span.pietto")
    relation = cast(QueryDef, script.definitions[-1])
    assert relation.limit_clause is not None

    result = analyze(script)
    diagnostic = next(item for item in result.diagnostics if item.code == "PIE-S2307")
    expression_span = relation.limit_clause.expression.span

    assert diagnostic.location.path == "span.pietto"
    assert diagnostic.location.line == expression_span.line
    assert diagnostic.location.column == expression_span.column
    assert diagnostic.location.end_line == expression_span.end_line
    assert diagnostic.location.end_column == expression_span.end_column
    line = source.splitlines()[expression_span.line - 1]
    assert (
        line[expression_span.column - 1 : expression_span.end_column - 1]
        == "missing(unknown)"
    )


def test_ir_limit_defaults_to_none_and_stores_canonical_integer() -> None:
    no_limit = _relation_ir(_compile_ir(POSTGRES_PREFIX + _relation_source("", None)))
    leading_zero = _relation_ir(
        _compile_ir(POSTGRES_PREFIX + _relation_source("", "0007"))
    )
    limit_field = next(field for field in fields(RelationIR) if field.name == "limit")

    assert limit_field.default is None
    assert no_limit.limit is None
    assert leading_zero.limit is not None
    assert leading_zero.limit.value == 7
    assert leading_zero.limit.span.line == 8
    assert leading_zero.limit.span.column == 11


def test_postgres_and_mysql_render_exact_canonical_limit_sql() -> None:
    postgres = sql_api.emit_postgres_sql(
        _compile_ir(POSTGRES_PREFIX + _relation_source("", "0007"))
    )
    mysql = emit_mysql_sql(_compile_ir(MYSQL_PREFIX + _relation_source("", "0007")))

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == (
        'SELECT\n    "id" AS "id"\nFROM "users"\nLIMIT 7'
    )
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == ("SELECT\n    `id` AS `id`\nFROM `users`\nLIMIT 7")


def test_both_backends_fail_closed_for_malformed_limit_ir() -> None:
    postgres_ir = _compile_ir(POSTGRES_PREFIX + _relation_source("", "1"))
    mysql_ir = _compile_ir(MYSQL_PREFIX + _relation_source("", "1"))

    for script_ir, emitter in (
        (postgres_ir, sql_api.emit_postgres_sql),
        (mysql_ir, emit_mysql_sql),
    ):
        relation = _relation_ir(script_ir)
        assert relation.limit is not None
        malformed = replace(
            relation,
            limit=LimitIR(value=cast(int, True), span=relation.limit.span),
        )
        replaced = ScriptIR(
            definitions=tuple(
                malformed if definition is relation else definition
                for definition in script_ir.definitions
            )
        )
        result = emitter(replaced)

        assert result.artifacts == ()
        assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-B1000"]


def test_cli_text_and_json_v1_carry_limit_without_new_options(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    postgres_path = tmp_path / "postgres-limit.pietto"
    postgres_path.write_text(
        POSTGRES_PREFIX + _relation_source("", "10"),
        encoding="utf-8",
    )
    mysql_path = tmp_path / "mysql-limit.pietto"
    mysql_path.write_text(
        MYSQL_PREFIX + _relation_source("", "10"),
        encoding="utf-8",
    )

    assert cli.main(["emit-sql", str(postgres_path), "--dialect", "postgres"]) == 0
    text = capsys.readouterr()
    assert text.out.endswith('FROM "users"\nLIMIT 10\n')
    assert text.err == ""

    assert (
        cli.main(
            [
                "emit-sql",
                str(mysql_path),
                "--dialect",
                "mysql",
                "--format",
                "json",
            ]
        )
        == 0
    )
    json_output = capsys.readouterr()
    document = json.loads(json_output.out)
    assert json_output.err == ""
    assert document["schema_version"] == 1
    assert document["artifacts"][0]["sql"].endswith("FROM `users`\nLIMIT 10")


def test_suffix_and_diagnostic_code_contracts_remain_canonical() -> None:
    repository_text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in ("src", "tests", "docs", "examples", "grammar")
        for path in sorted((REPO_ROOT / root).rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix in {".py", ".md", ".pietto", ".g4"}
    )

    assert re.search(r"\." + "pie" + r"\b", repository_text) is None
    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", repository_text) is None


def _relation_source(prefix: str, limit: str | None) -> str:
    limit_clause = "" if limit is None else f"    limit {limit}\n"
    return (
        prefix + "query selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n" + limit_clause
    )


def _parse(source: str, *, path: str = "limit.pietto"):
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _compile_ir(source: str) -> ScriptIR:
    script = _parse(source)
    semantic_result = analyze(script)
    assert not [
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
    result = build_ir(script, semantic_result.model)
    assert result.diagnostics == ()
    assert result.ir is not None
    return result.ir


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    )
