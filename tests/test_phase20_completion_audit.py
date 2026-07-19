from __future__ import annotations

import hashlib
import importlib.util
import json
from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    CallIR,
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
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.mysql_expressions import render_mysql_expression

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-20-sum-avg-aggregate-mvp.md"
POSTGRES_INPUT = Path("tests/fixtures/phase20/postgres_sum_avg_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase20/mysql_sum_avg_aggregate.pietto")
POSTGRES_GOLDEN = "tests/fixtures/golden/emit_sql_sum_avg_aggregate.sql"
MYSQL_GOLDEN = "tests/fixtures/golden/emit_mysql_sum_avg_aggregate.sql"

GRAMMAR_HASH = "1c394db1f72561022941e0e937899e2d340880de220ebfa85cf387b86573384e"
GENERATED_HASH = "bc5be46411f947c4d591e81ce8dd8345140fd5e10276f2ff0055eccfc12babe4"

SPAN = SourceSpan(
    path="phase20-completion-audit.pietto",
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


def test_phase20_artifacts_and_completion_plan_exist() -> None:
    for path in (
        REPO_ROOT / "tests/test_phase20_sum_avg_semantics.py",
        REPO_ROOT / "tests/test_phase20_sum_avg_ir.py",
        REPO_ROOT / "tests/test_phase20_sum_avg_sql.py",
        REPO_ROOT / POSTGRES_INPUT,
        REPO_ROOT / MYSQL_INPUT,
        REPO_ROOT / POSTGRES_GOLDEN,
        REPO_ROOT / MYSQL_GOLDEN,
        PLAN_PATH,
    ):
        assert path.is_file()

    plan = _normalized(PLAN_PATH)
    for required in (
        "Phase 20 Slice 1: Sum/Avg Semantic And IR Entry is complete.",
        "Phase 20 Slice 2: Sum/Avg SQL Lowering And Goldens is complete.",
        "Phase 20 Slice 3: Sum/Avg Aggregate MVP Completion Audit is complete.",
        "direct aliased no-GROUP projections only",
        "bare fields and already-supported single-input qualified fields",
        "`Int` and `Float` field arguments only",
        "Phase 20 is complete after Slice 3.",
    ):
        assert required in plan


def test_aggregate_diagnostics_and_golden_inventory_are_complete() -> None:
    diagnostics = _read(REPO_ROOT / "docs/spec/diagnostics.md")
    for code in (
        "PIE-S2308",
        "PIE-S2309",
        "PIE-S2310",
        "PIE-S2311",
        "PIE-S2312",
        "PIE-S2313",
        "PIE-S2314",
        "PIE-S2315",
    ):
        assert f"| `{code}` |" in diagnostics

    check_goldens = _check_goldens()
    sql_fixtures = cast(frozenset[str], getattr(check_goldens, "SQL_FIXTURES"))
    fixture_inputs = cast(
        dict[str, tuple[str, ...]],
        getattr(check_goldens, "FIXTURE_INPUTS"),
    )
    reference_tests = cast(tuple[Path, ...], getattr(check_goldens, "REFERENCE_TESTS"))
    audit = cast(Callable[[Path], tuple[str, ...]], getattr(check_goldens, "audit"))

    assert "emit_sql_sum_avg_aggregate.sql" in sql_fixtures
    assert "emit_mysql_sum_avg_aggregate.sql" in sql_fixtures
    assert fixture_inputs["emit_sql_sum_avg_aggregate.sql"] == (
        "tests/fixtures/phase20/postgres_sum_avg_aggregate.pietto",
    )
    assert fixture_inputs["emit_mysql_sum_avg_aggregate.sql"] == (
        "tests/fixtures/phase20/mysql_sum_avg_aggregate.pietto",
    )
    assert Path("tests/test_phase20_sum_avg_sql.py") in reference_tests
    assert audit(REPO_ROOT) == ()


def test_valid_sum_avg_ir_types_and_sql_bytes_are_locked() -> None:
    postgres_ir = _compile(POSTGRES_INPUT)
    relation = _relation_ir(postgres_ir)
    projections = {
        projection.name: projection.expression for projection in relation.projections
    }

    _assert_aggregate(projections["total"], "count", "Int", NullabilityIR.NON_NULL, ())
    _assert_aggregate(
        projections["revenue"],
        "sum",
        "Int",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_aggregate(
        projections["score_total"],
        "sum",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )
    _assert_aggregate(
        projections["average_amount"],
        "avg",
        "Float",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_aggregate(
        projections["average_score"],
        "avg",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )

    postgres_result = emit_postgres_sql(postgres_ir)
    mysql_result = emit_mysql_sql(_compile(MYSQL_INPUT))

    assert postgres_result.diagnostics == ()
    assert mysql_result.diagnostics == ()
    assert (
        _render_artifacts(postgres_result) == (REPO_ROOT / POSTGRES_GOLDEN).read_bytes()
    )
    assert _render_artifacts(mysql_result) == (REPO_ROOT / MYSQL_GOLDEN).read_bytes()
    assert render_expression_sql(_aggregate("count", INT_NON_NULL)) == "COUNT(*)"
    assert render_mysql_expression(_aggregate("count", INT_NON_NULL)) == "COUNT(*)"


@pytest.mark.parametrize(
    ("select_body", "expected_code"),
    [
        ("        revenue = sum(1)\n", "PIE-S2315"),
        ("        average = avg(1)\n", "PIE-S2315"),
        ("        revenue = sum(status)\n", "PIE-S2314"),
        ("        average = avg(status)\n", "PIE-S2314"),
        ("        revenue = sum(avg(amount))\n", "PIE-S2311"),
        ("        revenue = sum(amount) + 1\n", "PIE-S2310"),
        ("        status\n        revenue = sum(amount)\n", "PIE-S2312"),
    ],
)
def test_invalid_deferred_sum_avg_shapes_stop_before_sql(
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
        "malformed_sum_result_type",
        "malformed_avg_result_type",
    ],
)
def test_malformed_hand_built_sum_avg_ir_still_fails_closed(
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


def test_grammar_generated_and_forbidden_scope_remain_locked() -> None:
    plan = _normalized(PLAN_PATH)

    assert _sha256(REPO_ROOT / "grammar/Pietto.g4") == GRAMMAR_HASH
    assert _aggregate_files(_generated_files("src/pietto/generated")) == GENERATED_HASH

    for required in (
        "no GROUP BY",
        "no HAVING user syntax",
        "no `satisfying`",
        "no `filter`",
        "no JOIN",
        "no Decimal aggregate semantics",
        "no arbitrary aggregate expression arguments",
        "no SQL casts",
        "no runtime/database execution",
    ):
        assert required in plan


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


def _assert_aggregate(
    expression: ExpressionIR,
    function: str,
    expected_type: str,
    expected_nullability: NullabilityIR,
    expected_arguments: tuple[str, ...],
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == function
    assert expression.value_type.canonical_name == expected_type
    assert expression.value_type.nullability is expected_nullability
    assert tuple(_field_name(argument) for argument in expression.arguments) == (
        expected_arguments
    )


def _field_name(expression: ExpressionIR) -> str:
    assert isinstance(expression, FieldRefIR)
    return ".".join((*expression.qualifier, expression.name))


def _malformed_aggregate(case: str) -> AggregateCallIR:
    if case == "unsupported_function":
        return _aggregate("median", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
    if case == "wrong_arity":
        return _aggregate("sum", INT_NULLABLE)
    if case == "non_field_argument":
        return _aggregate("sum", INT_NULLABLE, _literal(1, INT_NON_NULL))
    if case == "decimal_argument":
        return _aggregate("sum", INT_NULLABLE, _field("price", DECIMAL_NON_NULL))
    if case == "malformed_sum_result_type":
        return _aggregate("sum", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
    if case == "malformed_avg_result_type":
        return _aggregate("avg", INT_NULLABLE, _field("amount", INT_NON_NULL))
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


def _render_artifacts(result: SqlResult) -> bytes:
    return ("\n\n".join(artifact.sql for artifact in result.artifacts) + "\n").encode(
        "utf-8"
    )


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return cast(dict[str, object], json.loads(captured.out))


def _check_goldens() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_phase20_check_goldens",
        REPO_ROOT / "scripts/check_goldens.py",
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return cast(ModuleType, module)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _generated_files(path: str) -> tuple[Path, ...]:
    return tuple(
        file_path
        for file_path in (REPO_ROOT / path).rglob("*")
        if file_path.is_file() and "__pycache__" not in file_path.parts
    )


def _aggregate_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
