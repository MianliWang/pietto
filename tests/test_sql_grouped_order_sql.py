from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import cast

import pytest

import pietto.sql as sql_api
from pietto.errors import Severity
from pietto.ir import (
    FieldId,
    FieldRefIR,
    RelationIR,
    ScriptIR,
    build_ir,
)
from pietto.ir.model import OrderDirectionIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SOURCE_SHAPE = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
)


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_order", "forbidden_order_sql"),
    [
        ("postgres.table", emit_postgres_sql, '    "region" ASC', '"total"'),
        ("mysql.table", emit_mysql_sql, "    `region` ASC", "`total`"),
    ],
)
def test_grouped_order_by_bare_group_key_output_renders_field_expression(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_order: str,
    forbidden_order_sql: str,
) -> None:
    result = emitter(
        _compile(
            _grouped_source(
                connector,
                projections=("region", "total = count()"),
                order_items=("region asc",),
            )
        )
    )

    assert result.diagnostics == ()
    order_by = _order_by_clause(result.artifacts[0].sql)
    assert order_by == expected_order
    assert forbidden_order_sql not in order_by


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_order", "forbidden_order_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            '    "orders"."region" DESC',
            '"r"',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "    `orders`.`region` DESC",
            "`r`",
        ),
    ],
)
def test_grouped_order_by_aliased_group_key_renders_underlying_field(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_order: str,
    forbidden_order_sql: str,
) -> None:
    result = emitter(
        _compile(
            _grouped_source(
                connector,
                group_keys=("orders.region",),
                projections=("r = orders.region", "total = count()"),
                order_items=("r desc",),
            )
        )
    )

    assert result.diagnostics == ()
    order_by = _order_by_clause(result.artifacts[0].sql)
    assert order_by == expected_order
    assert forbidden_order_sql not in order_by


@pytest.mark.parametrize(
    (
        "projection",
        "order_item",
        "expected_postgres",
        "expected_mysql",
        "forbidden_alias",
    ),
    [
        ("total = count()", "total desc", "COUNT(*) DESC", "COUNT(*) DESC", "total"),
        (
            "total = sum(amount)",
            "total desc",
            'SUM("amount") DESC',
            "SUM(`amount`) DESC",
            "total",
        ),
        (
            "average_score = avg(score)",
            "average_score asc",
            'AVG("score") ASC',
            "AVG(`score`) ASC",
            "average_score",
        ),
        (
            "total = sum(amount + tax)",
            "total desc",
            'SUM(("amount" + "tax")) DESC',
            "SUM((`amount` + `tax`)) DESC",
            "total",
        ),
        (
            "normalized = count_distinct(lower(trim(status)))",
            "normalized desc",
            'COUNT(DISTINCT lower(trim("status"))) DESC',
            "COUNT(DISTINCT LOWER(TRIM(`status`))) DESC",
            "normalized",
        ),
    ],
)
def test_grouped_order_by_aggregate_outputs_render_underlying_expressions(
    projection: str,
    order_item: str,
    expected_postgres: str,
    expected_mysql: str,
    forbidden_alias: str,
) -> None:
    for connector, emitter, expected_order, quote in (
        ("postgres.table", emit_postgres_sql, expected_postgres, '"'),
        ("mysql.table", emit_mysql_sql, expected_mysql, "`"),
    ):
        result = emitter(
            _compile(
                _grouped_source(
                    connector,
                    projections=("region", projection),
                    order_items=(order_item,),
                )
            )
        )

        assert result.diagnostics == ()
        order_by = _order_by_clause(result.artifacts[0].sql)
        assert order_by == f"    {expected_order}"
        assert f"{quote}{forbidden_alias}{quote}" not in order_by


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    "region" AS "region",\n'
            '    SUM(("amount" + "tax")) AS "total"\n'
            'FROM "orders"\n'
            "GROUP BY\n"
            '    "region"\n'
            "HAVING\n"
            '    SUM(("amount" + "tax")) > 1000\n'
            "ORDER BY\n"
            '    SUM(("amount" + "tax")) DESC,\n'
            '    "region" ASC\n'
            "LIMIT 10",
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    `region` AS `region`,\n"
            "    SUM((`amount` + `tax`)) AS `total`\n"
            "FROM `orders`\n"
            "GROUP BY\n"
            "    `region`\n"
            "HAVING\n"
            "    SUM((`amount` + `tax`)) > 1000\n"
            "ORDER BY\n"
            "    SUM((`amount` + `tax`)) DESC,\n"
            "    `region` ASC\n"
            "LIMIT 10",
        ),
    ],
)
def test_grouped_satisfying_order_by_and_limit_render_in_clause_order(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
) -> None:
    result = emitter(
        _compile(
            _grouped_source(
                connector,
                projections=("region", "total = sum(amount + tax)"),
                satisfying="total > 1000",
                order_items=("total desc", "region asc"),
                limit="10",
            )
        )
    )

    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    assert sql == expected_sql
    assert sql.index("GROUP BY") < sql.index("HAVING") < sql.index("ORDER BY")
    assert sql.index("ORDER BY") < sql.index("LIMIT")


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_order"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            '    COUNT(*) DESC,\n    "region" ASC,\n    COUNT(*) ASC',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "    COUNT(*) DESC,\n    `region` ASC,\n    COUNT(*) ASC",
        ),
    ],
)
def test_grouped_order_preserves_duplicate_items_and_source_order(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_order: str,
) -> None:
    result = emitter(
        _compile(
            _grouped_source(
                connector,
                projections=("region", "total = count()"),
                order_items=("total desc", "region", "total asc"),
            )
        )
    )

    assert result.diagnostics == ()
    assert _order_by_clause(result.artifacts[0].sql) == expected_order


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_order"),
    [
        ("postgres.table", emit_postgres_sql, '    "amount" DESC'),
        ("mysql.table", emit_mysql_sql, "    `amount` DESC"),
    ],
)
def test_no_group_sql_order_by_still_uses_input_scope(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_order: str,
) -> None:
    result = emitter(
        _compile(
            _source_prefix(connector) + "table sorted_orders:\n"
            "    from orders\n"
            "    select:\n"
            "        amount_alias = amount\n"
            "    order by:\n"
            "        amount desc\n"
        )
    )

    assert result.diagnostics == ()
    assert _order_by_clause(result.artifacts[0].sql) == expected_order


def test_no_group_projection_alias_still_fails_before_sql() -> None:
    parse_result = parse_source(
        _source_prefix("postgres.table") + "table sorted_orders:\n"
        "    from orders\n"
        "    select:\n"
        "        sort_key = lower(status)\n"
        "    order by:\n"
        "        sort_key\n",
        path="phase27-grouped-order-sql.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    result = analyze(parse_result.ast)

    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == [("PIE-S2102", "Unknown field: sort_key")]


def test_unsupported_grouped_order_source_fails_semantically_before_sql() -> None:
    parse_result = parse_source(
        _grouped_source(
            "postgres.table",
            projections=("region", "total = count()"),
            order_items=("sum(amount)",),
        ),
        path="phase27-grouped-order-sql.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    result = analyze(parse_result.ast)

    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == [
        (
            "PIE-S2321",
            "Unsupported grouped ORDER BY item; expected a supported select output name",
        )
    ]


@pytest.mark.parametrize(
    ("connector", "emitter"),
    [
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ],
)
def test_malformed_grouped_order_expression_fails_closed_with_pie_b1000(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    script_ir = _compile(
        _grouped_source(
            connector,
            projections=("region", "total = sum(amount)"),
            order_items=("total",),
        )
    )
    relation = _relation(script_ir)
    valid_order = relation.order_by[0]
    region = relation.projections[0].expression
    assert isinstance(region, FieldRefIR)
    bad_order_expression = FieldRefIR(
        name="status",
        qualifier=(),
        field=FieldId(owner=relation.source.target, name="status"),
        span=relation.span,
        value_type=region.value_type,
    )
    bad_relation = replace(
        relation,
        order_by=(replace(valid_order, expression=bad_order_expression),),
    )

    result = emitter(_replace_relation(script_ir, relation, bad_relation))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert "must match a selected" in result.diagnostics[0].message


@pytest.mark.parametrize(
    ("connector", "emitter"),
    [
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ],
)
def test_malformed_grouped_order_direction_still_fails_closed_with_pie_b1000(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    script_ir = _compile(
        _grouped_source(
            connector,
            projections=("region", "total = count()"),
            order_items=("total",),
        )
    )
    relation = _relation(script_ir)
    bad_relation = replace(
        relation,
        order_by=(
            replace(
                relation.order_by[0],
                direction=cast(OrderDirectionIR, "SIDEWAYS"),
            ),
        ),
    )

    result = emitter(_replace_relation(script_ir, relation, bad_relation))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"


def test_private_mysql_api_remains_unexported() -> None:
    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert not hasattr(sql_api, "emit_mysql_sql")


def _grouped_source(
    connector: str,
    *,
    projections: tuple[str, ...],
    order_items: tuple[str, ...],
    group_keys: tuple[str, ...] = ("region",),
    satisfying: str | None = None,
    limit: str | None = None,
) -> str:
    group_block = "".join(f"        {key}\n" for key in group_keys)
    projection_block = "".join(f"        {projection}\n" for projection in projections)
    satisfying_block = (
        "" if satisfying is None else f"    satisfying:\n        {satisfying}\n"
    )
    order_block = "".join(f"        {item}\n" for item in order_items)
    limit_block = "" if limit is None else f"    limit {limit}\n"
    return (
        _source_prefix(connector) + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        f"{group_block}"
        "    select:\n"
        f"{projection_block}"
        f"{satisfying_block}"
        "    order by:\n"
        f"{order_block}"
        f"{limit_block}"
    )


def _source_prefix(connector: str) -> str:
    return SOURCE_SHAPE + f'source orders: Order is {connector}("orders")\n'


def _compile(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="phase27-grouped-order-sql.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == []

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _replace_relation(
    script_ir: ScriptIR,
    old_relation: RelationIR,
    new_relation: RelationIR,
) -> ScriptIR:
    return ScriptIR(
        definitions=tuple(
            new_relation if definition is old_relation else definition
            for definition in script_ir.definitions
        )
    )


def _order_by_clause(sql: str) -> str:
    _before, order_by = sql.split("ORDER BY\n", maxsplit=1)
    return order_by.split("\nLIMIT", maxsplit=1)[0]
