from __future__ import annotations

import json
import re
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.sql as sql_api
from pietto.ast_nodes import NameExpr, OrderByClause, QueryDef, TableDef
from pietto.errors import Severity
from pietto.ir import FieldRefIR, RelationIR, ScriptIR, build_ir
from pietto.ir.model import OrderDirectionIR, OrderItemIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
POSTGRES_PREFIX = (
    "shape User:\n"
    "    id: Int not null\n"
    "    created_at: Int not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
)
MYSQL_PREFIX = POSTGRES_PREFIX.replace("postgres.table", "mysql.table")


@pytest.mark.parametrize("direction", [None, "asc", "desc"])
@pytest.mark.parametrize("relation_kind", ["query", "table"])
def test_parser_accepts_one_order_item_and_preserves_direction(
    direction: str | None,
    relation_kind: str,
) -> None:
    suffix = "" if direction is None else f" {direction}"
    result = parse_source(
        _relation_source(
            relation_kind=relation_kind,
            order_items=(f"created_at{suffix}",),
        ),
        path="order.pietto",
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef | TableDef, result.ast.definitions[0])
    assert isinstance(relation.order_by_clause, OrderByClause)
    assert len(relation.order_by_clause.items) == 1
    item = relation.order_by_clause.items[0]
    assert isinstance(item.expression, NameExpr)
    assert item.expression.name == "created_at"
    assert item.direction == direction


def test_parser_preserves_multiple_order_items_in_source_order() -> None:
    relation = cast(
        QueryDef,
        _parse(
            _relation_source(order_items=("created_at desc", "id", "lower(email) asc"))
        ).definitions[0],
    )

    assert relation.order_by_clause is not None
    assert [
        (
            item.expression.name
            if isinstance(item.expression, NameExpr)
            else type(item.expression).__name__,
            item.direction,
        )
        for item in relation.order_by_clause.items
    ] == [
        ("created_at", "desc"),
        ("id", None),
        ("CallExpr", "asc"),
    ]


@pytest.mark.parametrize(
    "body",
    [
        ("    from users\n    select:\n        id\n    order by:\n"),
        (
            "    from users\n"
            "    select:\n"
            "        id\n"
            "    order by:\n"
            "        id\n"
            "    order by:\n"
            "        created_at\n"
        ),
        ("    from users\n    order by:\n        id\n    select:\n        id\n"),
        (
            "    from users\n"
            "    select:\n"
            "        id\n"
            "    limit 10\n"
            "    order by:\n"
            "        id\n"
        ),
        (
            "    from users\n"
            "    select:\n"
            "        id\n"
            "    order by:\n"
            "        id sideways\n"
        ),
        ("    from users\n    select:\n        id\n    order by:\n        1\n"),
    ],
)
def test_invalid_order_by_shapes_are_parser_errors(body: str) -> None:
    result = parse_source(f"query selected:\n{body}", path="order.pietto")

    assert result.ast is None
    assert result.diagnostics
    assert all(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


def test_grammar_contains_only_the_approved_order_keywords() -> None:
    grammar = (REPO_ROOT / "grammar/Pietto.g4").read_text(encoding="utf-8")

    for token in (
        "ORDER: 'order';",
        "BY: 'by';",
        "ASC: 'asc';",
        "DESC: 'desc';",
    ):
        assert grammar.count(token) == 1
    for token in ("NULLS:", "COLLATE:", "OFFSET:", "FETCH:"):
        assert token not in grammar


def test_new_order_keywords_remain_valid_in_identifier_positions() -> None:
    result = parse_source(
        "shape Keywords:\n"
        "    order: Int not null\n"
        "    by: Int not null\n"
        "    asc: Int not null\n"
        "    desc: Int not null\n"
        'source order: Keywords is postgres.table("keywords")\n'
        "query by:\n"
        "    from order\n"
        "    select:\n"
        "        asc = asc\n"
        "        desc = desc\n"
        "    order by:\n"
        "        order\n",
        path="soft-keywords.pietto",
    )

    assert result.diagnostics == ()
    assert result.ast is not None


def test_semantic_accepts_input_fields_and_existing_expression_typing() -> None:
    script = _parse(
        POSTGRES_PREFIX
        + _relation_source(
            where="active == true",
            order_items=("created_at + id desc", "lower(email)"),
        )
    )
    relation = cast(QueryDef, script.definitions[-1])
    assert relation.order_by_clause is not None

    result = analyze(script)

    assert not [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
    assert all(
        item.expression in result.model.expression_value_types
        for item in relation.order_by_clause.items
    )


def test_projection_alias_is_not_an_order_by_name_scope() -> None:
    script = _parse(
        POSTGRES_PREFIX
        + _relation_source(
            projections=("sort_key = lower(email)",),
            order_items=("sort_key",),
        )
    )

    result = analyze(script)
    errors = [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]

    assert [(diagnostic.code, diagnostic.message) for diagnostic in errors] == [
        ("PIE-S2102", "Unknown field: sort_key")
    ]


def test_alias_matching_an_input_field_still_resolves_the_input_field() -> None:
    script_ir = _compile_ir(
        POSTGRES_PREFIX
        + _relation_source(
            projections=("created_at = lower(email)",),
            order_items=("created_at",),
        )
    )
    relation = _relation_ir(script_ir)
    expression = relation.order_by[0].expression

    assert isinstance(expression, FieldRefIR)
    assert expression.name == "created_at"
    assert expression.field is not None
    assert expression.field.owner == relation.source.target


def test_ir_defaults_and_normalized_order_items_are_stable() -> None:
    no_order = _relation_ir(_compile_ir(POSTGRES_PREFIX + _relation_source()))
    ordered = _relation_ir(
        _compile_ir(
            POSTGRES_PREFIX + _relation_source(order_items=("created_at desc", "id"))
        )
    )
    order_field = next(
        field for field in fields(RelationIR) if field.name == "order_by"
    )

    assert order_field.default == ()
    assert no_order.order_by == ()
    assert [item.direction for item in ordered.order_by] == [
        OrderDirectionIR.DESC,
        OrderDirectionIR.ASC,
    ]
    assert [cast(FieldRefIR, item.expression).name for item in ordered.order_by] == [
        "created_at",
        "id",
    ]
    assert [item.span.line for item in ordered.order_by] == [12, 13]
    assert all(item.span.end_column > item.span.column for item in ordered.order_by)


def test_postgres_and_mysql_render_exact_multiline_order_by() -> None:
    postgres = sql_api.emit_postgres_sql(
        _compile_ir(
            POSTGRES_PREFIX + _relation_source(order_items=("created_at desc", "id"))
        )
    )
    mysql = emit_mysql_sql(
        _compile_ir(
            MYSQL_PREFIX + _relation_source(order_items=("created_at desc", "id"))
        )
    )

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == (
        "SELECT\n"
        '    "id" AS "id"\n'
        'FROM "users"\n'
        "ORDER BY\n"
        '    "created_at" DESC,\n'
        '    "id" ASC'
    )
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == (
        "SELECT\n"
        "    `id` AS `id`\n"
        "FROM `users`\n"
        "ORDER BY\n"
        "    `created_at` DESC,\n"
        "    `id` ASC"
    )
    assert not postgres.artifacts[0].sql.endswith("\n")
    assert not mysql.artifacts[0].sql.endswith("\n")


def test_both_backends_render_order_by_before_existing_limit() -> None:
    for prefix, emitter, quote in (
        (POSTGRES_PREFIX, sql_api.emit_postgres_sql, '"'),
        (MYSQL_PREFIX, emit_mysql_sql, "`"),
    ):
        result = emitter(
            _compile_ir(
                prefix
                + _relation_source(
                    order_items=("created_at desc", "id"),
                    limit="100",
                )
            )
        )

        assert result.diagnostics == ()
        assert result.artifacts[0].sql.endswith(
            "ORDER BY\n"
            f"    {quote}created_at{quote} DESC,\n"
            f"    {quote}id{quote} ASC\n"
            "LIMIT 100"
        )


def test_both_backends_fail_closed_for_malformed_order_direction() -> None:
    for prefix, emitter in (
        (POSTGRES_PREFIX, sql_api.emit_postgres_sql),
        (MYSQL_PREFIX, emit_mysql_sql),
    ):
        script_ir = _compile_ir(prefix + _relation_source(order_items=("created_at",)))
        relation = _relation_ir(script_ir)
        item = relation.order_by[0]
        malformed = replace(
            relation,
            order_by=(
                replace(
                    item,
                    direction=cast(OrderDirectionIR, "SIDEWAYS"),
                ),
            ),
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


def test_cli_text_and_json_v1_carry_order_sql_without_new_options(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    postgres_path = tmp_path / "postgres-order.pietto"
    postgres_path.write_text(
        POSTGRES_PREFIX + _relation_source(order_items=("created_at desc", "id")),
        encoding="utf-8",
    )
    mysql_path = tmp_path / "mysql-order.pietto"
    mysql_path.write_text(
        MYSQL_PREFIX + _relation_source(order_items=("created_at desc", "id")),
        encoding="utf-8",
    )

    assert cli.main(["emit-sql", str(postgres_path), "--dialect", "postgres"]) == 0
    text = capsys.readouterr()
    assert text.err == ""
    assert text.out.endswith('ORDER BY\n    "created_at" DESC,\n    "id" ASC\n')

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
    assert document["artifacts"][0]["sql"].endswith(
        "ORDER BY\n    `created_at` DESC,\n    `id` ASC"
    )


def test_internal_order_ir_types_are_not_public_exports() -> None:
    assert not hasattr(sql_api, "OrderItemIR")
    assert not hasattr(sql_api, "OrderDirectionIR")
    assert OrderItemIR.__module__ == "pietto.ir.model"
    assert OrderDirectionIR.__module__ == "pietto.ir.model"


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


def _relation_source(
    *,
    relation_kind: str = "query",
    where: str | None = None,
    projections: tuple[str, ...] = ("id",),
    order_items: tuple[str, ...] = (),
    limit: str | None = None,
) -> str:
    where_clause = "" if where is None else f"    where {where}\n"
    order_clause = ""
    if order_items:
        order_clause = "    order by:\n" + "".join(
            f"        {item}\n" for item in order_items
        )
    limit_clause = "" if limit is None else f"    limit {limit}\n"
    return (
        f"{relation_kind} selected:\n"
        "    from users\n"
        f"{where_clause}"
        "    select:\n"
        + "".join(f"        {projection}\n" for projection in projections)
        + order_clause
        + limit_clause
    )


def _parse(source: str, *, path: str = "order.pietto"):
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
