from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    FieldId,
    FieldRefIR,
    LiteralIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    build_ir,
)
from pietto.ir.model import OrderDirectionIR, OrderItemIR
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
POSTGRES_INPUT = Path("tests/fixtures/phase21/postgres_group_by_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase21/mysql_group_by_aggregate.pietto")

SPAN = SourceSpan(
    path="phase21-group-by-hardening.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
OWNER = SymbolId(SymbolNamespace.RELATION, "orders")
INT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
FLOAT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Float",
    canonical_name="Float",
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

DIALECT_CASES = (
    (POSTGRES_INPUT, "postgres", "postgres.table", 'FROM "grouped_orders"'),
    (MYSQL_INPUT, "mysql", "mysql.table", "FROM `grouped_orders`"),
)

INVALID_GROUPED_CASES = (
    (
        "duplicate_group_key",
        "    group by:\n"
        "        status\n"
        "        orders.status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        "PIE-S2317",
    ),
    (
        "unknown_group_key",
        "    group by:\n"
        "        missing\n"
        "    select:\n"
        "        missing\n"
        "        total = count()\n",
        "PIE-S2102",
    ),
    (
        "non_grouped_projection",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        customer_id\n"
        "        total = count()\n",
        "PIE-S2318",
    ),
    (
        "scalar_grouped_projection",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        label = lower(status)\n"
        "        total = count()\n",
        "PIE-S2319",
    ),
    (
        "pure_grouping",
        "    group by:\n        status\n    select:\n        status\n",
        "PIE-S2320",
    ),
    (
        "grouped_order_by",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "    order by:\n"
        "        total desc\n",
        "PIE-S2321",
    ),
    (
        "unaliased_aggregate",
        "    group by:\n        status\n    select:\n        status\n        count()\n",
        "PIE-S2313",
    ),
    (
        "nested_aggregate",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum(avg(amount))\n",
        "PIE-S2311",
    ),
    (
        "aggregate_composition",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum(amount) + 1\n",
        "PIE-S2310",
    ),
    (
        "wrong_arity",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum()\n",
        "PIE-S2309",
    ),
    (
        "wrong_type",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum(status)\n",
        "PIE-S2314",
    ),
    (
        "aggregate_expression_argument",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum(amount + amount)\n",
        "PIE-S2315",
    ),
)


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
def test_valid_grouped_check_succeeds_for_both_dialects(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del dialect, connector, expected_from
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["check", str(input_path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {input_path}\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
def test_valid_grouped_emit_sql_text_and_json_smoke(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del connector, expected_from
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", str(input_path), "--dialect", dialect]) == 0
    text = capsys.readouterr()
    assert text.err == ""
    assert "GROUP BY" in text.out
    assert "COUNT(*)" in text.out

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                dialect,
                "--format",
                "json",
            ]
        )
        == 0
    )
    result = _read_json(capsys)
    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert len(artifacts) == 1
    assert "GROUP BY" in cast(str, artifacts[0]["sql"])


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
def test_valid_grouped_emit_sql_output_writes_sql_and_suppresses_stdout(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del connector, expected_from
    output_path = tmp_path / f"{dialect}-grouped.sql"
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                dialect,
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert "GROUP BY" in output_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
@pytest.mark.parametrize(("case_name", "body", "expected_code"), INVALID_GROUPED_CASES)
def test_invalid_grouped_emit_sql_json_output_fails_before_sql_without_writing(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    case_name: str,
    body: str,
    expected_code: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del input_path, expected_from
    source_path = tmp_path / f"{dialect}-{case_name}.pietto"
    output_path = tmp_path / f"{dialect}-{case_name}.sql"
    output_path.write_text("existing SQL\n", encoding="utf-8")
    source_path.write_text(_invalid_grouped_source(connector, body), encoding="utf-8")
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(source_path),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    assert result["artifacts"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "existing SQL\n"
    assert codes == [expected_code]
    assert expected_code.startswith("PIE-S")
    assert "PIE-S2316" not in codes
    assert "PIE-B1000" not in codes


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
def test_downstream_from_grouped_cli_json_uses_relation_name_without_expansion(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del input_path
    path = tmp_path / f"{dialect}-downstream-grouped.pietto"
    path.write_text(_grouped_chain_source(connector), encoding="utf-8")
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format",
                "json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    downstream_sql = cast(str, artifacts[1]["sql"])

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert [artifact["name"] for artifact in artifacts] == [
        "grouped_orders",
        "downstream",
    ]
    assert expected_from in downstream_sql
    assert downstream_sql.count("SELECT") == 1
    assert "WITH" not in downstream_sql
    assert "GROUP BY" not in downstream_sql
    assert "(SELECT" not in downstream_sql
    assert "FROM (" not in downstream_sql


@pytest.mark.parametrize(
    ("input_path", "emitter"),
    [
        (POSTGRES_INPUT, emit_postgres_sql),
        (MYSQL_INPUT, emit_mysql_sql),
    ],
)
@pytest.mark.parametrize(
    "case",
    [
        "unresolved_group_key",
        "non_field_group_key",
        "duplicate_group_key",
        "grouped_order_by",
        "non_grouped_projection",
        "pure_grouped_output",
        "unsupported_aggregate",
    ],
)
def test_malformed_grouped_ir_direct_emitters_fail_closed_with_pie_b1000(
    input_path: Path,
    emitter: Callable[[ScriptIR], SqlResult],
    case: str,
) -> None:
    script_ir = _compile(input_path)
    relation = _relation_ir(script_ir, "revenue_by_status")
    bad_relation = _malformed_grouped_relation(relation, case)
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emitter(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"


def _compile(path: Path) -> ScriptIR:
    parse_result = parse_file(REPO_ROOT / path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _compile_source(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="phase21-group-by-hardening.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation_ir(script_ir: ScriptIR, name: str) -> RelationIR:
    matches = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _malformed_grouped_relation(relation: RelationIR, case: str) -> RelationIR:
    if case == "unresolved_group_key":
        return replace(
            relation, group_keys=(replace(relation.group_keys[0], field=None),)
        )
    if case == "non_field_group_key":
        return replace(
            relation, group_keys=cast(tuple[FieldRefIR, ...], (_literal(1),))
        )
    if case == "duplicate_group_key":
        return replace(
            relation, group_keys=(relation.group_keys[0], relation.group_keys[0])
        )
    if case == "grouped_order_by":
        return replace(
            relation,
            order_by=(
                OrderItemIR(
                    expression=relation.projections[0].expression,
                    direction=OrderDirectionIR.ASC,
                    span=SPAN,
                ),
            ),
        )
    if case == "non_grouped_projection":
        projection = relation.projections[0]
        return replace(
            relation,
            projections=(
                replace(
                    projection,
                    name="customer_id",
                    expression=_field("customer_id", TEXT_NON_NULL),
                ),
                *relation.projections[1:],
            ),
        )
    if case == "pure_grouped_output":
        return replace(relation, projections=(relation.projections[0],))
    if case == "unsupported_aggregate":
        projection = relation.projections[2]
        assert isinstance(projection.expression, AggregateCallIR)
        return replace(
            relation,
            projections=(
                *relation.projections[:2],
                replace(
                    projection,
                    expression=replace(
                        projection.expression,
                        function="median",
                        value_type=FLOAT_NULLABLE,
                    ),
                ),
            ),
        )
    raise AssertionError(f"Unknown malformed grouped IR case: {case}")


def _literal(value: int) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=INT_NON_NULL, value=value)


def _field(name: str, value_type: TypeRefIR) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=(),
        field=FieldId(owner=OWNER, name=name),
    )


def _invalid_grouped_source(connector: str, body: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text not null\n"
        "    customer_id: Text not null\n"
        "    amount: Int not null\n"
        f'source orders: Order is {connector}("orders")\n'
        "table grouped_orders:\n"
        "    from orders\n"
        f"{body}"
    )


def _grouped_chain_source(connector: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text not null\n"
        "    amount: Int not null\n"
        f'source orders: Order is {connector}("orders")\n'
        "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "query downstream:\n"
        "    from grouped_orders\n"
        "    select:\n"
        "        status\n"
        "        total\n"
    )


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return cast(dict[str, object], json.loads(captured.out))
