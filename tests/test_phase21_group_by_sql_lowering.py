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
from pietto.ir.model import OrderDirectionIR, OrderItemIR, StaticValue
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
POSTGRES_INPUT = Path("tests/fixtures/phase21/postgres_group_by_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase21/mysql_group_by_aggregate.pietto")
POSTGRES_GOLDEN = "emit_sql_group_by_aggregate.sql"
MYSQL_GOLDEN = "emit_mysql_group_by_aggregate.sql"

SPAN = SourceSpan(
    path="phase21-group-by-sql.pietto",
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
TEXT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Text",
    canonical_name="Text",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)


@pytest.mark.parametrize(
    ("input_path", "golden_name", "emitter"),
    [
        (POSTGRES_INPUT, POSTGRES_GOLDEN, emit_postgres_sql),
        (MYSQL_INPUT, MYSQL_GOLDEN, emit_mysql_sql),
    ],
)
def test_direct_group_by_sql_matches_reviewed_golden(
    input_path: Path,
    golden_name: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    result = emitter(_compile(input_path))

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].name == "revenue_by_status"
    assert _render_artifacts(result) == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_text_group_by_sql_matches_reviewed_golden(
    input_path: Path,
    dialect: str,
    golden_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", str(input_path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_json_group_by_sql_success_preserves_v1_shape(
    input_path: Path,
    dialect: str,
    golden_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

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
    assert result["dialect"] == dialect
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": "revenue_by_status",
            "sql": _golden_text(golden_name).removesuffix("\n"),
        }
    ]


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_json_group_by_sql_output_writes_exact_sql(
    input_path: Path,
    dialect: str,
    golden_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / f"{dialect}-group-by.sql"
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = _read_json(capsys)

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts[0]["sql"] == _golden_text(golden_name).removesuffix("\n")
    assert output_path.read_bytes() == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect"),
    [
        (POSTGRES_INPUT, "postgres"),
        (MYSQL_INPUT, "mysql"),
    ],
)
def test_cli_check_succeeds_for_valid_grouped_relation(
    input_path: Path,
    dialect: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del dialect
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["check", str(input_path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {input_path}\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("body", "expected_codes"),
    [
        (
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        customer_id\n"
            "        total = count()\n",
            ["PIE-S2318"],
        ),
        (
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        label = lower(status)\n"
            "        total = count()\n",
            ["PIE-S2319"],
        ),
        (
            "    group by:\n        status\n    select:\n        status\n",
            ["PIE-S2320"],
        ),
        (
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    order by:\n"
            "        sum(amount) desc\n",
            ["PIE-S2321"],
        ),
        (
            "    group by:\n"
            "        status\n"
            "        orders.status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            ["PIE-S2317"],
        ),
        (
            "    group by:\n"
            "        missing\n"
            "    select:\n"
            "        missing\n"
            "        total = count()\n",
            ["PIE-S2102"],
        ),
        (
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        revenue = sum(amount + 1)\n",
            ["PIE-S2315"],
        ),
    ],
)
def test_invalid_grouped_relations_fail_semantically_before_sql(
    body: str,
    expected_codes: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "invalid-grouped.pietto"
    path.write_text(_invalid_grouped_source(body), encoding="utf-8")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    assert codes == expected_codes
    assert "PIE-S2316" not in codes
    assert "PIE-B1000" not in codes
    assert result["artifacts"] == []


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
        "unsupported_aggregate",
        "non_grouped_projection",
    ],
)
def test_malformed_grouped_ir_fails_closed_with_pie_b1000(
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


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_from"),
    [
        ("postgres.table", emit_postgres_sql, 'FROM "grouped_orders"'),
        ("mysql.table", emit_mysql_sql, "FROM `grouped_orders`"),
    ],
)
def test_downstream_from_grouped_relation_uses_relation_name_without_expansion(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_from: str,
) -> None:
    result = emitter(_compile_source(_grouped_chain_source(connector)))

    assert result.diagnostics == ()
    assert [artifact.name for artifact in result.artifacts] == [
        "grouped_orders",
        "downstream",
    ]
    downstream_sql = result.artifacts[1].sql
    assert expected_from in downstream_sql
    assert downstream_sql.count("SELECT") == 1
    assert "WITH" not in downstream_sql
    assert "GROUP BY" not in downstream_sql


def test_postgres_group_keys_render_in_ir_source_order_with_qualified_alias() -> None:
    result = emit_postgres_sql(
        _compile_source(
            "shape Order:\n"
            "    status: Text not null\n"
            "    region: Text nullable\n"
            'source orders: Order is postgres.table("orders")\n'
            "table grouped_orders:\n"
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "        orders.region\n"
            "    select:\n"
            "        status\n"
            "        bucket = orders.region\n"
            "        total = count()\n"
            "    limit 10\n"
        )
    )

    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        "SELECT\n"
        '    "status" AS "status",\n'
        '    "orders"."region" AS "bucket",\n'
        '    COUNT(*) AS "total"\n'
        'FROM "orders" AS "orders"\n'
        "GROUP BY\n"
        '    "status",\n'
        '    "orders"."region"\n'
        "LIMIT 10"
    )


def _compile(path: Path) -> ScriptIR:
    return _compile_path(REPO_ROOT / path)


def _compile_path(path: Path) -> ScriptIR:
    parse_result = parse_file(path)
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
    parse_result = parse_source(source, path="phase21-group-by-sql.pietto")
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
            relation,
            group_keys=(replace(relation.group_keys[0], field=None),),
        )
    if case == "non_field_group_key":
        return replace(
            relation,
            group_keys=cast(tuple[FieldRefIR, ...], (_literal(1),)),
        )
    if case == "duplicate_group_key":
        return replace(
            relation,
            group_keys=(relation.group_keys[0], relation.group_keys[0]),
        )
    if case == "grouped_order_by":
        return replace(
            relation,
            order_by=(
                OrderItemIR(
                    expression=_field("customer_id", TEXT_NON_NULL),
                    direction=OrderDirectionIR.ASC,
                    span=SPAN,
                ),
            ),
        )
    if case == "unsupported_aggregate":
        projection = relation.projections[2]
        assert isinstance(projection.expression, AggregateCallIR)
        return replace(
            relation,
            projections=(
                *relation.projections[:2],
                replace(
                    projection,
                    expression=replace(projection.expression, function="median"),
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
    raise AssertionError(f"Unknown malformed grouped IR case: {case}")


def _literal(value: StaticValue) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=INT_NON_NULL, value=value)


def _field(name: str, value_type: TypeRefIR) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=(),
        field=FieldId(owner=OWNER, name=name),
    )


def _invalid_grouped_source(body: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text not null\n"
        "    customer_id: Text not null\n"
        "    amount: Int not null\n"
        'source orders: Order is postgres.table("orders")\n'
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


def _golden_text(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def _golden_bytes(name: str) -> bytes:
    return (GOLDEN_ROOT / name).read_bytes()


def _render_artifacts(result: SqlResult) -> bytes:
    return ("\n\n".join(artifact.sql for artifact in result.artifacts) + "\n").encode(
        "utf-8"
    )


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return cast(dict[str, object], json.loads(captured.out))
