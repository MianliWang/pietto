from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    ComparisonIR,
    FieldRefIR,
    RelationIR,
    ScriptIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze
from pietto.sql import SqlArtifactKind, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    discount: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float nullable\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    'source orders: Order is postgres.table("orders")\n'
)
MYSQL_SOURCE_PREFIX = SOURCE_PREFIX.replace("postgres.table", "mysql.table")


@pytest.mark.parametrize(
    "satisfying",
    [
        "sum(gross) > 10",
        "avg(weighted) > 1.5",
        "count(gross) > 0",
        "count_distinct(normalized) > 1",
    ],
)
def test_satisfying_aggregate_wrapped_row_let_is_semantically_accepted(
    satisfying: str,
) -> None:
    semantic = _semantic_for(_grouped_source(satisfying=satisfying))

    assert _errors(semantic) == []


def test_satisfying_selected_alias_for_aggregate_row_let_still_lowers_inline() -> None:
    relation = _relation_ir(_grouped_source(satisfying="total > 10"))

    predicate = relation.result_predicate
    assert predicate is not None
    assert isinstance(predicate.expression, ComparisonIR)
    aggregate = predicate.expression.left
    assert isinstance(aggregate, AggregateCallIR)
    assert aggregate.function == "sum"
    assert aggregate.arguments
    assert _field_refs_named(aggregate, {"amount", "tax"})
    assert not _field_refs_named(aggregate, {"gross", "total"})


def test_ir_lowers_satisfying_aggregate_row_let_to_selected_aggregate_expression() -> (
    None
):
    relation = _relation_ir(_grouped_source(satisfying="sum(gross) > 10"))

    predicate = relation.result_predicate
    assert predicate is not None
    assert isinstance(predicate.expression, ComparisonIR)
    aggregate = predicate.expression.left
    assert isinstance(aggregate, AggregateCallIR)
    assert aggregate.function == "sum"
    assert len(aggregate.arguments) == 1
    argument = aggregate.arguments[0]
    assert isinstance(argument, BinaryIR)
    assert _field_refs_named(argument, {"amount", "tax"})
    assert not _field_refs_named(relation, {"gross", "total"})


@pytest.mark.parametrize(
    ("prefix", "dialect", "expected_having", "forbidden"),
    [
        (
            SOURCE_PREFIX,
            "postgres",
            '    SUM(("amount" + "tax")) > 10',
            ('"gross"', '"total"', "WITH ", "FROM (SELECT"),
        ),
        (
            MYSQL_SOURCE_PREFIX,
            "mysql",
            "    SUM((`amount` + `tax`)) > 10",
            ("`gross`", "`total`", "WITH ", "FROM (SELECT"),
        ),
    ],
)
def test_sql_inlines_satisfying_aggregate_row_let_without_hidden_layers(
    prefix: str,
    dialect: str,
    expected_having: str,
    forbidden: tuple[str, ...],
) -> None:
    sql = _sql_for(
        _grouped_source(satisfying="sum(gross) > 10"),
        prefix=prefix,
        dialect=dialect,
    )

    having = _having_clause(sql)
    assert having == expected_having
    for fragment in forbidden:
        if fragment.endswith(" "):
            assert fragment not in sql.upper()
        else:
            assert fragment not in having


def test_cli_json_and_explain_shapes_remain_compatible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(
        tmp_path,
        "satisfying_aggregate_let.pietto",
        _grouped_source(satisfying="sum(gross) > 10"),
    )

    assert cli.main(["check", str(source_path)]) == 0
    check_output = capsys.readouterr()
    assert check_output.err == ""
    assert f"OK: {source_path}" in check_output.out

    assert (
        cli.main(
            [
                "emit-sql",
                str(source_path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )
    emit_document = _read_json(capsys)
    assert emit_document["ok"] is True
    assert emit_document["diagnostics"] == []
    assert len(cast(list[object], emit_document["artifacts"])) == 1
    assert "let_scopes" not in json.dumps(emit_document)

    assert cli.main(["explain", str(source_path), "--format", "json"]) == 0
    explain_document = _read_json(capsys)
    assert explain_document["ok"] is True
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert "metadata" in explain_document
    assert "let_scopes" not in json.dumps(explain_document)


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(gross)\n"
            "    satisfying:\n"
            "        gross > 10\n",
            "PIE-S2324",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(gross)\n"
            "    satisfying:\n"
            "        sum(amount + tax) > 10\n",
            "PIE-S2308",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    satisfying:\n"
            "        sum(gross) > 10\n",
            "PIE-S2308",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(gross)\n"
            "    satisfying:\n"
            "        min(gross) > 10\n",
            "PIE-S2308",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        one = 1\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(one)\n"
            "    satisfying:\n"
            "        sum(one) > 10\n",
            "PIE-S2315",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        amount\n"
            "    limit gross\n",
            "PIE-S2307",
        ),
    ],
)
def test_non_slice6_satisfying_let_consumers_remain_rejected(
    body: str,
    expected_code: str,
) -> None:
    semantic = _semantic_for("query grouped_orders:\n" + body)

    assert expected_code in _error_codes(semantic)


def _grouped_source(*, satisfying: str) -> str:
    return (
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        weighted = score * weight\n"
        "        normalized = lower(trim(status))\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = sum(gross)\n"
        "        average_weighted = avg(weighted)\n"
        "        known_gross = count(gross)\n"
        "        unique_normalized = count_distinct(normalized)\n"
        "    satisfying:\n"
        f"        {satisfying}\n"
    )


def _semantic_for(source: str) -> SemanticResult:
    result = parse_source(SOURCE_PREFIX + source, path="phase43-slice6.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return analyze(result.ast)


def _relation_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> RelationIR:
    script_ir = _script_ir(source, prefix=prefix)
    relation = script_ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    return relation


def _script_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> ScriptIR:
    result = parse_source(prefix + source, path="phase43-slice6.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic = analyze(result.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(result.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _sql_for(source: str, *, prefix: str, dialect: str) -> str:
    script_ir = _script_ir(source, prefix=prefix)
    result = (
        emit_mysql_sql(script_ir)
        if dialect == "mysql"
        else emit_postgres_sql(script_ir)
    )
    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].kind is SqlArtifactKind.RELATION
    return result.artifacts[0].sql


def _write_source(tmp_path: Path, filename: str, relation_source: str) -> Path:
    path = tmp_path / filename
    path.write_text(SOURCE_PREFIX + relation_source, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    return cast(dict[str, object], json.loads(captured.out))


def _having_clause(sql: str) -> str:
    return sql.split("HAVING\n", maxsplit=1)[1].split("\nORDER BY", maxsplit=1)[0]


def _field_refs_named(value: object, names: set[str]) -> bool:
    return any(ref.name in names for ref in _field_refs(value))


def _field_refs(value: object) -> tuple[FieldRefIR, ...]:
    refs: list[FieldRefIR] = []
    if isinstance(value, FieldRefIR):
        refs.append(value)
    if isinstance(value, tuple):
        for item in value:
            refs.extend(_field_refs(item))
    elif is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            refs.extend(_field_refs(getattr(value, field.name)))
    return tuple(refs)


def _error_codes(semantic: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _errors(semantic: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
