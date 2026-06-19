from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ir import (
    AggregateCallIR,
    CallIR,
    ComparisonIR,
    ConnectorIR,
    FieldId,
    FieldRefIR,
    LiteralIR,
    NullabilityIR,
    ProjectionIR,
    RelationIR,
    RelationKindIR,
    RelationSourceIR,
    ResultPredicateIR,
    RowSchemaIR,
    ScriptIR,
    SourceIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
)
from pietto.ir.model import LimitIR, OrderDirectionIR, OrderItemIR
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SPAN = SourceSpan(
    path="phase25-satisfying-sql.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
ORDERS = SymbolId(SymbolNamespace.RELATION, "orders")
INT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
INT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)
TEXT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Text",
    canonical_name="Text",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
BOOL_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Bool",
    canonical_name="Bool",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
SOURCE_PREFIX = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    amount: Int not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    "region" AS "r",\n'
            '    SUM("amount") AS "total_amount"\n'
            'FROM "orders"\n'
            "GROUP BY\n"
            '    "region"\n'
            "HAVING\n"
            '    SUM("amount") > 1000',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    `region` AS `r`,\n"
            "    SUM(`amount`) AS `total_amount`\n"
            "FROM `orders`\n"
            "GROUP BY\n"
            "    `region`\n"
            "HAVING\n"
            "    SUM(`amount`) > 1000",
        ),
    ],
)
def test_constructed_aggregate_result_predicate_renders_having(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
) -> None:
    result = emitter(_script(connector, _result_predicate(_sum_amount_gt_1000())))

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].sql == expected_sql


@pytest.mark.parametrize(
    ("connector", "emitter", "field_sql", "alias_sql"),
    [
        ("postgres.table", emit_postgres_sql, '"region"', '"r"'),
        ("mysql.table", emit_mysql_sql, "`region`", "`r`"),
    ],
)
def test_constructed_group_key_result_predicate_renders_underlying_field_not_alias(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    field_sql: str,
    alias_sql: str,
) -> None:
    result = emitter(_script(connector, _result_predicate(_region_ne_test())))

    assert result.diagnostics == ()
    having = _having_clause(result.artifacts[0].sql)
    assert field_sql in having
    assert alias_sql not in having


@pytest.mark.parametrize(
    ("connector", "emitter"),
    [
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ],
)
def test_constructed_result_predicate_having_is_after_group_by_and_before_limit(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    result = emitter(
        _script(
            connector,
            _result_predicate(_sum_amount_gt_1000()),
            limit=LimitIR(value=10, span=SPAN),
        )
    )

    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    assert sql.index("GROUP BY") < sql.index("HAVING") < sql.index("LIMIT")


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_from"),
    [
        ("postgres.table", emit_postgres_sql, 'FROM "physical_orders" AS "orders"'),
        ("mysql.table", emit_mysql_sql, "FROM `physical_orders` AS `orders`"),
    ],
)
def test_result_predicate_participates_in_qualified_field_source_aliasing(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_from: str,
) -> None:
    result = emitter(
        _script(
            connector,
            _result_predicate(_qualified_region_ne_test()),
            table_name="physical_orders",
        )
    )

    assert result.diagnostics == ()
    assert expected_from in result.artifacts[0].sql


@pytest.mark.parametrize(
    ("connector", "emitter"),
    [
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ],
)
def test_relation_without_result_predicate_still_omits_having(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    result = emitter(_script(connector, result_predicate=None))

    assert result.diagnostics == ()
    assert "HAVING" not in result.artifacts[0].sql


@pytest.mark.parametrize(
    ("connector", "emitter"),
    [
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ],
)
def test_result_predicate_without_group_keys_fails_closed_without_artifact(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    script = _script(connector, _result_predicate(_sum_amount_gt_1000()))
    relation = _relation(script)
    bad_relation = replace(relation, group_keys=())

    result = emitter(_replace_relation(script, bad_relation))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert "result predicate requires GROUP BY" in result.diagnostics[0].message


@pytest.mark.parametrize(
    ("connector", "emitter"),
    [
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ],
)
def test_unsupported_result_predicate_expression_fails_closed_without_artifact(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    predicate = ResultPredicateIR(
        expression=CallIR(
            callee="unknown",
            callee_symbol=None,
            arguments=(),
            span=SPAN,
            value_type=BOOL_NON_NULL,
        ),
        span=SPAN,
    )

    result = emitter(_script(connector, predicate))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert "Unsupported" in result.diagnostics[0].message


@pytest.mark.parametrize(
    ("connector", "emitter"),
    [
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ],
)
def test_grouped_order_by_remains_fail_closed_with_result_predicate(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    script = _script(connector, _result_predicate(_sum_amount_gt_1000()))
    relation = _relation(script)
    bad_relation = replace(
        relation,
        order_by=(
            OrderItemIR(
                expression=_region(),
                direction=OrderDirectionIR.ASC,
                span=SPAN,
            ),
        ),
    )

    result = emitter(_replace_relation(script, bad_relation))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert "grouped ORDER BY is not supported" in result.diagnostics[0].message


def test_source_satisfying_still_fails_closed_before_text_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())
    _forbid_ir_and_sql(monkeypatch)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2322 error: `satisfying` IR/SQL lowering is deferred" in captured.err


def test_source_satisfying_still_fails_closed_before_json_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())
    _forbid_ir_and_sql(monkeypatch)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    result = cast(dict[str, object], json.loads(captured.out))
    assert result["ok"] is False
    assert result["artifacts"] == []
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2322"]


def _script(
    connector: str,
    result_predicate: ResultPredicateIR | None,
    *,
    limit: LimitIR | None = None,
    table_name: str = "orders",
) -> ScriptIR:
    source = SourceIR(
        symbol=ORDERS,
        name="orders",
        shape_symbol=None,
        row_schema=RowSchemaIR(fields=()),
        connector=ConnectorIR(
            name=connector,
            arguments=(table_name,),
            span=SPAN,
        ),
        span=SPAN,
    )
    relation = RelationIR(
        symbol=SymbolId(SymbolNamespace.RELATION, "high_value_regions"),
        name="high_value_regions",
        kind=RelationKindIR.TABLE,
        source=RelationSourceIR(target=ORDERS, name="orders", span=SPAN),
        filter=None,
        projections=(
            ProjectionIR(
                name="r",
                expression=_region(),
                type_ref=TEXT_NON_NULL,
                span=SPAN,
            ),
            ProjectionIR(
                name="total_amount",
                expression=_sum_amount(),
                type_ref=INT_NULLABLE,
                span=SPAN,
            ),
        ),
        row_schema=RowSchemaIR(fields=()),
        span=SPAN,
        limit=limit,
        group_keys=(_region(),),
        result_predicate=result_predicate,
    )
    return ScriptIR(definitions=(source, relation))


def _relation(script: ScriptIR) -> RelationIR:
    relation = script.definitions[1]
    assert isinstance(relation, RelationIR)
    return relation


def _replace_relation(script: ScriptIR, relation: RelationIR) -> ScriptIR:
    return ScriptIR(definitions=(script.definitions[0], relation))


def _result_predicate(expression: ComparisonIR) -> ResultPredicateIR:
    return ResultPredicateIR(expression=expression, span=SPAN)


def _sum_amount_gt_1000() -> ComparisonIR:
    return ComparisonIR(
        left=_sum_amount(),
        operator=">",
        right=LiteralIR(value=1000, span=SPAN, value_type=INT_NON_NULL),
        span=SPAN,
        value_type=BOOL_NON_NULL,
    )


def _region_ne_test() -> ComparisonIR:
    return ComparisonIR(
        left=_region(),
        operator="!=",
        right=LiteralIR(value="test", span=SPAN, value_type=TEXT_NON_NULL),
        span=SPAN,
        value_type=BOOL_NON_NULL,
    )


def _qualified_region_ne_test() -> ComparisonIR:
    return ComparisonIR(
        left=FieldRefIR(
            name="region",
            qualifier=("orders",),
            field=FieldId(owner=ORDERS, name="region"),
            span=SPAN,
            value_type=TEXT_NON_NULL,
        ),
        operator="!=",
        right=LiteralIR(value="test", span=SPAN, value_type=TEXT_NON_NULL),
        span=SPAN,
        value_type=BOOL_NON_NULL,
    )


def _sum_amount() -> AggregateCallIR:
    return AggregateCallIR(
        function="sum",
        arguments=(_amount(),),
        span=SPAN,
        value_type=INT_NULLABLE,
    )


def _amount() -> FieldRefIR:
    return FieldRefIR(
        name="amount",
        qualifier=(),
        field=FieldId(owner=ORDERS, name="amount"),
        span=SPAN,
        value_type=INT_NON_NULL,
    )


def _region() -> FieldRefIR:
    return FieldRefIR(
        name="region",
        qualifier=(),
        field=FieldId(owner=ORDERS, name="region"),
        span=SPAN,
        value_type=TEXT_NON_NULL,
    )


def _having_clause(sql: str) -> str:
    _prefix, having = sql.split("HAVING\n", maxsplit=1)
    return having.split("\nLIMIT", maxsplit=1)[0]


def _valid_satisfying_source() -> str:
    return (
        SOURCE_PREFIX + "table revenue:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total_amount = sum(amount)\n"
        "    satisfying:\n"
        "        total_amount > 1000\n"
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _forbid_ir_and_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("satisfying source must still fail before IR and SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
