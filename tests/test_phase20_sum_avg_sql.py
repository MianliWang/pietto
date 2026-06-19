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
    ExpressionIR,
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
from pietto.ir.model import StaticValue
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
POSTGRES_INPUT = Path("tests/fixtures/phase20/postgres_sum_avg_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase20/mysql_sum_avg_aggregate.pietto")
POSTGRES_GOLDEN = "emit_sql_sum_avg_aggregate.sql"
MYSQL_GOLDEN = "emit_mysql_sum_avg_aggregate.sql"

SPAN = SourceSpan(
    path="phase20-sum-avg-sql.pietto",
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
INT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
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
DECIMAL_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Decimal",
    canonical_name="Decimal",
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
def test_direct_backend_sum_avg_sql_matches_reviewed_golden(
    input_path: Path,
    golden_name: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    result = emitter(_compile(input_path))

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].name == "paid_order_stats"
    assert _render_artifacts(result) == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_text_sum_avg_sql_matches_reviewed_golden(
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
def test_cli_json_sum_avg_sql_success_preserves_v1_shape(
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
            "name": "paid_order_stats",
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
def test_cli_json_sum_avg_sql_output_writes_exact_sql(
    input_path: Path,
    dialect: str,
    golden_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / f"{dialect}-sum-avg.sql"
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
    ("select_body", "expected_code"),
    [
        ("        revenue = sum(amount + 1)\n", "PIE-S2315"),
        ("        average = avg(1)\n", "PIE-S2315"),
        ("        revenue = sum(status)\n", "PIE-S2314"),
        ("        average = avg(status)\n", "PIE-S2314"),
        ("        revenue = sum(avg(amount))\n", "PIE-S2311"),
        ("        revenue = sum(amount) + 1\n", "PIE-S2310"),
        ("        status\n        revenue = sum(amount)\n", "PIE-S2312"),
    ],
)
def test_invalid_sum_avg_shapes_stop_before_sql_without_artifacts(
    select_body: str,
    expected_code: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "invalid-sum-avg.pietto"
    path.write_text(
        "shape Order:\n"
        "    status: Text not null\n"
        "    amount: Int not null\n"
        "    price: Decimal not null\n"
        'source orders: Order is postgres.table("orders")\n'
        "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"{select_body}",
        encoding="utf-8",
    )

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
    assert codes == [expected_code]
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
        "unsupported_function",
        "wrong_arity",
        "non_field_argument",
        "decimal_argument",
        "malformed_result_type",
    ],
)
def test_malformed_hand_built_sum_avg_ir_fails_closed_with_pie_b1000(
    input_path: Path,
    emitter: Callable[[ScriptIR], SqlResult],
    case: str,
) -> None:
    script_ir = _compile(input_path)
    relation = _relation_ir(script_ir)
    projection = relation.projections[1]
    bad_relation = replace(
        relation,
        projections=(replace(projection, expression=_malformed_aggregate(case)),),
    )
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


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _malformed_aggregate(case: str) -> AggregateCallIR:
    if case == "unsupported_function":
        return _aggregate("median", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
    if case == "wrong_arity":
        return _aggregate("sum", INT_NULLABLE)
    if case == "non_field_argument":
        return _aggregate("sum", INT_NULLABLE, _literal(1, INT_NON_NULL))
    if case == "decimal_argument":
        return _aggregate("sum", INT_NULLABLE, _field("price", DECIMAL_NON_NULL))
    if case == "malformed_result_type":
        return _aggregate("sum", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
    raise AssertionError(f"Unknown malformed aggregate case: {case}")


def _aggregate(
    function: str,
    value_type: TypeRefIR,
    *arguments: ExpressionIR,
) -> AggregateCallIR:
    return AggregateCallIR(
        span=SPAN,
        value_type=value_type,
        function=function,
        arguments=arguments,
    )


def _field(name: str, value_type: TypeRefIR) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=(),
        field=FieldId(owner=OWNER, name=name),
    )


def _literal(value: StaticValue, value_type: TypeRefIR) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=value_type, value=value)


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
