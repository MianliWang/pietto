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
    build_ir,
)
from pietto.ir.model import LimitIR, OrderDirectionIR, OrderItemIR
from pietto.ast_nodes import QueryDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze
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
    "    region: Text\n"
    "    amount: Int\n"
    'source orders: Order = postgres.table("orders")\n'
)


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    "region" AS "r",\n'
            '    CAST(SUM(CAST("amount" AS pg_catalog.int8)) AS pg_catalog.int8) AS "total_amount"\n'
            'FROM "orders"\n'
            "GROUP BY\n"
            '    "region"\n'
            "HAVING\n"
            '    CAST(SUM(CAST("amount" AS pg_catalog.int8)) AS pg_catalog.int8) > 1000',
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
def test_malformed_grouped_order_by_remains_fail_closed_with_result_predicate(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    script = _script(connector, _result_predicate(_sum_amount_gt_1000()))
    relation = _relation(script)
    bad_relation = replace(
        relation,
        order_by=(
            OrderItemIR(
                expression=_amount(),
                direction=OrderDirectionIR.ASC,
                span=SPAN,
            ),
        ),
    )

    result = emitter(_replace_relation(script, bad_relation))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert "must match a selected" in result.diagnostics[0].message


def test_source_satisfying_text_emit_sql_succeeds_with_having(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == f"-- revenue\n{_expected_postgres_satisfying_sql()};\n"


def test_source_satisfying_having_uses_underlying_expressions_not_aliases(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _alias_satisfying_source())

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    having = _having_clause(captured.out)
    assert (
        'CAST(SUM(CAST("amount" AS pg_catalog.int8)) AS pg_catalog.int8) > 1000'
        in having
    )
    assert "\"region\" <> 'test'" in having
    assert '"total_amount"' not in having
    assert '"r"' not in having


def test_source_satisfying_json_emit_sql_preserves_v1_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())

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
        == 0
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    result = cast(dict[str, object], json.loads(captured.out))
    assert set(result) == {
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    }
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["dialect"] == "postgres"
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": "revenue",
            "sql": _expected_postgres_satisfying_sql(),
        }
    ]


def test_source_satisfying_text_output_writes_having_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())
    output = tmp_path / "out.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert output.read_text(encoding="utf-8") == (
        f"-- revenue\n{_expected_postgres_satisfying_sql()};\n"
    )


def test_source_satisfying_json_output_writes_having_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())
    output = tmp_path / "out.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    result = cast(dict[str, object], json.loads(captured.out))
    assert result["ok"] is True
    assert result["output"] == {"path": str(output), "written": True}
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts[0]["sql"] == _expected_postgres_satisfying_sql()
    assert output.read_text(encoding="utf-8") == (
        f"-- revenue\n{_expected_postgres_satisfying_sql()};\n"
    )


def test_invalid_source_satisfying_still_fails_before_text_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _invalid_satisfying_source())
    _forbid_ir_and_sql(monkeypatch)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2324 error: Unknown select output in having: missing" in captured.err


def test_invalid_source_satisfying_json_output_does_not_replace_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _invalid_satisfying_source())
    output = _write(tmp_path, "out.sql", "old SQL\n")
    _forbid_ir_and_sql(monkeypatch)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output),
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    result = cast(dict[str, object], json.loads(captured.out))
    assert result["ok"] is False
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output), "written": False}
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2324"]
    assert output.read_text(encoding="utf-8") == "old SQL\n"


def test_private_mysql_source_pipeline_renders_satisfying_having() -> None:
    parse_result = parse_source(_valid_satisfying_source(connector="mysql.table"))
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    semantic_result = analyze(parse_result.ast)
    assert semantic_result.diagnostics == ()
    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None

    result = emit_mysql_sql(ir_result.ir)

    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        "SELECT\n"
        "    `region` AS `region`,\n"
        "    SUM(`amount`) AS `total_amount`\n"
        "FROM `orders`\n"
        "GROUP BY\n"
        "    `region`\n"
        "HAVING\n"
        "    SUM(`amount`) > 1000"
    )


@pytest.mark.parametrize("connector", ("postgres.table", "mysql.table"))
@pytest.mark.parametrize(
    ("shape", "body"),
    (
        # A group key whose type is unknown (a Decimal division upstream).
        (
            "shape Order:\n    id: Int\n    amount: Decimal\n",
            "table rates:\n    from orders\n    select:\n        id\n"
            "        per = amount / id\n"
            "query q:\n    from rates\n    group by:\n        per\n"
            "    select:\n        per\n        n = count()\n"
            "    having:\n        per >= 0\n",
        ),
        # An unknown input row: a source without a shape.
        (
            "",
            "query q:\n    from orders\n    group by:\n        uid\n"
            "    select:\n        uid\n        n = count()\n"
            "    having:\n        n > 1\n",
        ),
    ),
)
def test_satisfying_of_unknown_type_fails_closed_at_emission_not_in_ir(
    connector: str, shape: str, body: str
) -> None:
    source = (
        shape
        + "source orders"
        + (": Order" if shape else "")
        + f' = {connector}("orders")\n'
        + body
    )
    parse_result = parse_source(source)
    assert parse_result.diagnostics == () and parse_result.ast is not None
    semantic_result = analyze(parse_result.ast)
    # Gradual typing: an unknown predicate type is not refused at check.
    assert all(d.severity is not Severity.ERROR for d in semantic_result.diagnostics)
    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == () and ir_result.ir is not None

    emitter = emit_postgres_sql if connector == "postgres.table" else emit_mysql_sql
    result = emitter(ir_result.ir)

    prefix = "PostgreSQL" if connector == "postgres.table" else "MySQL"
    assert [d.code for d in result.diagnostics] == ["PIE-B1000"]
    assert result.diagnostics[0].message.endswith(
        f"{prefix} result predicate requires a known Bool type"
    )
    assert not any(artifact.name == "q" for artifact in result.artifacts)


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


def _valid_satisfying_source(*, connector: str = "postgres.table") -> str:
    return (
        _source_prefix(connector) + "table revenue:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total_amount = sum(amount)\n"
        "    having:\n"
        "        total_amount > 1000\n"
    )


def _alias_satisfying_source() -> str:
    return (
        SOURCE_PREFIX + "table revenue:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        r = region\n"
        "        total_amount = sum(amount)\n"
        "    having:\n"
        '        total_amount > 1000 and r != "test"\n'
    )


def _invalid_satisfying_source() -> str:
    return (
        SOURCE_PREFIX + "table revenue:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total_amount = sum(amount)\n"
        "    having:\n"
        "        missing > 1000\n"
    )


def _source_prefix(connector: str) -> str:
    return (
        "shape Order:\n"
        "    region: Text\n"
        "    amount: Int\n"
        f'source orders: Order = {connector}("orders")\n'
    )


def _expected_postgres_satisfying_sql() -> str:
    return (
        "SELECT\n"
        '    "region" AS "region",\n'
        '    CAST(SUM(CAST("amount" AS pg_catalog.int8)) AS pg_catalog.int8) AS "total_amount"\n'
        'FROM "orders"\n'
        "GROUP BY\n"
        '    "region"\n'
        "HAVING\n"
        '    CAST(SUM(CAST("amount" AS pg_catalog.int8)) AS pg_catalog.int8) > 1000'
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _forbid_ir_and_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("invalid satisfying source must fail before IR and SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)


@pytest.mark.parametrize(
    "connector,emitter,summed,counted",
    [
        (
            "postgres.table",
            emit_postgres_sql,
            'CAST(SUM(CAST("amount" AS pg_catalog.int8)) AS pg_catalog.int8)',
            "COUNT(*)",
        ),
        ("mysql.table", emit_mysql_sql, "SUM(`amount`)", "COUNT(*)"),
    ],
)
@pytest.mark.parametrize(
    "composition", ["sum(amount)", "coalesce(sum(amount), 0)", "sum(amount) + count()"]
)
def test_selected_aggregate_result_alias_keeps_having_and_order_scope(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    summed: str,
    counted: str,
    composition: str,
) -> None:
    source = (
        _source_prefix(connector)
        + f"query summary:\n    from orders\n    group by region\n    select region, total = {composition}\n    having total > 0\n    order by total desc\n"
    )
    parsed = parse_source(source)
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    script = semantic.script or parsed.ast
    lowered = build_ir(script, semantic.model)
    assert lowered.ir is not None and lowered.diagnostics == ()
    result = emitter(lowered.ir)
    assert result.diagnostics == () and len(result.artifacts) == 1
    value = (
        summed
        if composition == "sum(amount)"
        else f"COALESCE({summed}, 0)"
        if composition.startswith("coalesce")
        else f"{summed} + {counted}"
    )
    predicate_value = f"({value})" if composition == "sum(amount) + count()" else value
    sql = result.artifacts[0].sql
    assert f"HAVING\n    {predicate_value} > 0\nORDER BY\n    {value} DESC" in sql


@pytest.mark.parametrize("predicate", ["total + 1 > 0", "coalesce(total, 0) > 0"])
def test_composed_output_alias_does_not_expand_having_expression_forms(
    predicate: str,
) -> None:
    source = (
        _source_prefix("postgres.table")
        + f"query summary:\n    from orders\n    group by region\n    select region, total = coalesce(sum(amount), 0)\n    having {predicate}\n"
    )
    parsed = parse_source(source)
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert any(d.code == "PIE-S2327" for d in semantic.diagnostics)


@pytest.mark.parametrize(
    "connector,emitter",
    [("postgres.table", emit_postgres_sql), ("mysql.table", emit_mysql_sql)],
)
@pytest.mark.parametrize(
    "projection", ["count()", "count() + 1", "coalesce(count(), 0)"]
)
def test_unknown_row_aggregate_alias_keeps_its_typed_having_scope(
    connector: str, emitter: Callable[[ScriptIR], SqlResult], projection: str
) -> None:
    source = f'source rows = {connector}("rows")\nquery q:\n    from rows\n    group by key\n    select total = {projection}\n    having total > 0\n'
    parsed = parse_source(source)
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert not [d for d in semantic.diagnostics if d.severity is Severity.ERROR]
    lowered = build_ir(semantic.script or parsed.ast, semantic.model)
    assert lowered.ir is not None and lowered.diagnostics == ()
    result = emitter(lowered.ir)
    assert result.artifacts == ()
    assert [d.code for d in result.diagnostics] == ["PIE-B1000"]


@pytest.mark.parametrize(
    "projection",
    ["count() + raw", "coalesce(count(), sign(raw))", "count() + len(raw)"],
)
def test_unknown_row_having_does_not_admit_a_raw_composition_sibling(
    projection: str,
) -> None:
    source = f'source rows = postgres.table("rows")\nquery q:\n    from rows\n    group by key\n    select total = {projection}\n    having total > 0\n'
    parsed = parse_source(source)
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert any(d.code == "PIE-S2310" for d in semantic.diagnostics)


@pytest.mark.parametrize(
    "connector,emitter",
    [("postgres.table", emit_postgres_sql), ("mysql.table", emit_mysql_sql)],
)
@pytest.mark.parametrize("computed_key", [False, True])
@pytest.mark.parametrize("projection", ["key + 1", "7"])
def test_grouped_scalar_output_beside_a_real_aggregate_keeps_having_and_order(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    computed_key: bool,
    projection: str,
) -> None:
    key = "bucket" if computed_key else "amount"
    binding = "    let bucket = amount + 1\n" if computed_key else ""
    value = projection.replace("key", key)
    order = "n" if projection == "7" else "label"
    one = (
        _source_prefix(connector)
        + f"query result:\n    from orders\n{binding}    group by {key}\n    select label = {value}, n = count()\n    having label > 0\n    order by {order} desc\n"
    )
    two = (
        _source_prefix(connector)
        + f"query grouped:\n    from orders\n{binding}    group by {key}\n    select {key}, n = count()\nquery result:\n    from grouped\n    where {value} > 0\n    select label = {value}, n\n    order by {order} desc\n"
    )
    schemas = []
    for source in (one, two):
        parsed = parse_source(source)
        assert parsed.ast is not None and parsed.diagnostics == ()
        semantic = analyze(parsed.ast)
        assert not [d for d in semantic.diagnostics if d.severity is Severity.ERROR]
        script = semantic.script or parsed.ast
        selected = script.definitions[-1]
        assert isinstance(selected, QueryDef)
        fields = semantic.model.relation_row_schemas[selected].fields
        schemas.append(
            tuple(
                (name, field.resolved_type, field.nullability)
                for name, field in fields.items()
            )
        )
        lowered = build_ir(script, semantic.model)
        assert lowered.ir is not None and lowered.diagnostics == ()
        result = emitter(lowered.ir)
        assert result.diagnostics == ()
        assert "ORDER BY" in result.artifacts[-1].sql
        assert ("HAVING" if source == one else "WHERE") in result.artifacts[-1].sql
    assert schemas[0] == schemas[1]


@pytest.mark.parametrize(
    "connector,emitter",
    [("postgres.table", emit_postgres_sql), ("mysql.table", emit_mysql_sql)],
)
def test_unknown_row_literal_output_beside_count_keeps_check_but_refuses_emission(
    connector: str, emitter: Callable[[ScriptIR], SqlResult]
) -> None:
    parsed = parse_source(
        f'source rows = {connector}("rows")\nquery q:\n    from rows\n    group by key\n    select fixed = 7, n = count()\n    having fixed > 0\n'
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert not [d for d in semantic.diagnostics if d.severity is Severity.ERROR]
    lowered = build_ir(semantic.script or parsed.ast, semantic.model)
    assert lowered.ir is not None and lowered.diagnostics == ()
    result = emitter(lowered.ir)
    assert result.artifacts == () and [d.code for d in result.diagnostics] == [
        "PIE-B1000"
    ]


@pytest.mark.parametrize(
    "projection,code",
    [
        ("label = amount + 1, n = count()", "PIE-S2319"),
        ("label = label + 1, n = count()", "PIE-S2102"),
        ("label = later + 1, later = count()", "PIE-S2102"),
        ("label = 7", "PIE-S2319"),
        ("region", "PIE-S2320"),
    ],
)
def test_grouped_zero_leaf_outputs_keep_raw_self_forward_and_no_aggregate_refusals(
    projection: str, code: str
) -> None:
    parsed = parse_source(
        _source_prefix("postgres.table")
        + f"query q:\n    from orders\n    group by region\n    select {projection}\n"
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert any(d.code == code for d in semantic.diagnostics)


def test_global_standalone_literal_beside_aggregate_keeps_mixed_projection_refusal() -> (
    None
):
    parsed = parse_source(
        _source_prefix("postgres.table")
        + "query q:\n    from orders\n    select fixed = 7, n = count()\n"
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert any(d.code == "PIE-S2312" for d in semantic.diagnostics)


@pytest.mark.parametrize("value", ["7", "-7", "True", '"text"'])
def test_grouped_standalone_constant_order_alias_keeps_positional_key_refusal(
    value: str,
) -> None:
    parsed = parse_source(
        _source_prefix("postgres.table")
        + f"query q:\n    from orders\n    group by amount\n    select fixed = {value}, n = count()\n    order by fixed\n"
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert [d.code for d in semantic.diagnostics if d.severity is Severity.ERROR] == [
        "PIE-S2380"
    ]
