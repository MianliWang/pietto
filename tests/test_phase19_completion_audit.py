from __future__ import annotations

import hashlib
import importlib.util
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

import pietto.ir as ir_api
from pietto.ast_nodes import QueryDef, Script, TableDef
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
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze
from pietto.semantic.catalog import BUILTIN_FUNCTIONS
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.mysql_render import MySqlRenderError

REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE19_AUDIT_INPUTS = (
    REPO_ROOT / "tests/test_phase19_count_semantics.py",
    REPO_ROOT / "tests/test_phase19_count_ir.py",
    REPO_ROOT / "tests/test_phase19_count_sql.py",
    REPO_ROOT / "tests/test_phase19_count_emit_sql_success.py",
    REPO_ROOT / "tests/fixtures/phase19/postgres_count_aggregate.pietto",
    REPO_ROOT / "tests/fixtures/phase19/mysql_count_aggregate.pietto",
    REPO_ROOT / "tests/fixtures/golden/emit_sql_count_aggregate.sql",
    REPO_ROOT / "tests/fixtures/golden/emit_mysql_count_aggregate.sql",
)

PHASE18_DOCS = (
    REPO_ROOT / "docs/plan/phase-18-aggregate-readiness-audit.md",
    REPO_ROOT / "docs/spec/aggregate-semantic-contract-v1.md",
    REPO_ROOT / "docs/spec/aggregate-ir-sql-readiness-contract-v1.md",
)

GRAMMAR_HASH = "6a5f6bc45d4f66011a7898fe783b6600beaf73f3b984d6539f975cf0cd7f3110"
GENERATED_HASH = "44dad9dc2fced336b8e102a558be94786fb7618fd860a3ef6f6d56e49fdebf1f"

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    'source orders: Order is postgres.table("orders")\n'
)

COUNT_SOURCE = (
    SOURCE_PREFIX + "table paid_order_stats:\n"
    "    from orders\n"
    '    where status == "paid"\n'
    "    select:\n"
    "        total = count()\n"
)

SPAN = SourceSpan(
    path="phase19-completion-audit.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
UNKNOWN_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="<unknown>",
    canonical_name="<unknown>",
    kind=TypeKindIR.UNKNOWN,
    canonical_kind=TypeKindIR.UNKNOWN,
    nullability=NullabilityIR.UNKNOWN,
)
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
OWNER = SymbolId(SymbolNamespace.RELATION, "orders")


def test_phase19_count_mvp_artifacts_exist() -> None:
    for path in PHASE19_AUDIT_INPUTS:
        assert path.is_file()


def test_aggregate_diagnostics_are_registered() -> None:
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
    assert "Aggregate used in an invalid context" in diagnostics
    assert "Aggregate called with the wrong arity" in diagnostics
    assert "Aggregate composition is deferred" in diagnostics
    assert "Nested aggregate is unsupported" in diagnostics
    assert (
        "Aggregate projection mixed with non-aggregate projection without `GROUP BY`"
        in diagnostics
    )
    assert "Aggregate projection without an explicit alias" in diagnostics
    assert "Aggregate field argument has an unsupported type" in diagnostics
    assert "Aggregate expression argument is deferred" in diagnostics


def test_semantic_count_sum_avg_mvp_is_locked() -> None:
    script = _parse(COUNT_SOURCE)
    relation = _relation_ast(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]
    field = schema.fields["total"]
    expression = relation.select_items[0].expression
    value_type = result.model.expression_value_types[expression]

    assert _errors(result) == []
    assert list(schema.fields) == ["total"]
    assert field.resolved_type.kind is TypeKind.BUILTIN
    assert field.resolved_type.name == "Int"
    assert field.nullability is EffectiveNullability.NON_NULL
    assert value_type.resolved_type.name == "Int"
    assert value_type.nullability is EffectiveNullability.NON_NULL
    assert "count" not in BUILTIN_FUNCTIONS
    assert "sum" not in BUILTIN_FUNCTIONS
    assert "avg" not in BUILTIN_FUNCTIONS

    sum_avg = _parse(
        SOURCE_PREFIX + "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        revenue = sum(amount)\n"
        "        average = avg(amount)\n"
    )
    sum_avg_relation = _relation_ast(sum_avg)
    sum_avg_result = analyze(sum_avg)
    sum_avg_schema = sum_avg_result.model.relation_row_schemas[sum_avg_relation]

    assert _errors(sum_avg_result) == []
    assert sum_avg_schema.fields["revenue"].resolved_type.name == "Int"
    assert sum_avg_schema.fields["revenue"].nullability is (
        EffectiveNullability.NULLABLE
    )
    assert sum_avg_schema.fields["average"].resolved_type.name == "Float"
    assert sum_avg_schema.fields["average"].nullability is (
        EffectiveNullability.NULLABLE
    )


def test_invalid_count_shapes_fail_semantically_before_sql() -> None:
    source = (
        SOURCE_PREFIX + "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count() + 1\n"
    )

    parse_result = parse_source(source)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    semantic_result = analyze(parse_result.ast)
    phase19_sql_tests = _read(REPO_ROOT / "tests/test_phase19_count_sql.py")

    assert _errors(semantic_result) == [
        (
            "PIE-S2310",
            "Aggregate projection must be a direct aggregate call; "
            "composition around count() is deferred",
        )
    ]
    assert "test_invalid_count_shape_stops_before_sql_without_artifacts" in (
        phase19_sql_tests
    )


def test_count_ir_is_explicit_aggregate_and_not_generic_call() -> None:
    script = _parse(COUNT_SOURCE)
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert "AggregateCallIR" in ir_api.__all__
    assert _errors(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation_ir = _relation_ir(ir_result.ir)
    expression = relation_ir.projections[0].expression

    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == "count"
    assert expression.arguments == ()
    assert expression.value_type.canonical_name == "Int"
    assert expression.value_type.nullability is NullabilityIR.NON_NULL


def test_count_sql_goldens_cli_json_coverage_and_inventory_are_locked() -> None:
    postgres_result = emit_postgres_sql(
        _compile_fixture("tests/fixtures/phase19/postgres_count_aggregate.pietto")
    )
    mysql_result = emit_mysql_sql(
        _compile_fixture("tests/fixtures/phase19/mysql_count_aggregate.pietto")
    )

    assert postgres_result.diagnostics == ()
    assert mysql_result.diagnostics == ()
    assert (
        _render_artifacts(postgres_result)
        == (
            REPO_ROOT / "tests/fixtures/golden/emit_sql_count_aggregate.sql"
        ).read_bytes()
    )
    assert (
        _render_artifacts(mysql_result)
        == (
            REPO_ROOT / "tests/fixtures/golden/emit_mysql_count_aggregate.sql"
        ).read_bytes()
    )

    phase19_sql_tests = _read(REPO_ROOT / "tests/test_phase19_count_sql.py")
    check_goldens = _read(REPO_ROOT / "scripts/check_goldens.py")

    assert "test_cli_json_count_sql_success_preserves_v1_shape" in phase19_sql_tests
    assert "test_cli_json_count_sql_output_writes_exact_sql" in phase19_sql_tests
    assert (
        "test_invalid_count_shape_stops_before_sql_without_artifacts"
        in phase19_sql_tests
    )
    assert "emit_sql_count_aggregate.sql" in check_goldens
    assert "emit_mysql_count_aggregate.sql" in check_goldens
    assert "tests/test_phase19_count_sql.py" in check_goldens
    assert _check_goldens().audit(REPO_ROOT) == ()


def test_sql_renderers_preserve_count_and_support_direct_sum_avg_aggregates() -> None:
    assert render_expression_sql(_aggregate("count", INT_NON_NULL)) == "COUNT(*)"
    assert render_mysql_expression(_aggregate("count", INT_NON_NULL)) == "COUNT(*)"
    assert (
        render_expression_sql(
            _aggregate("sum", INT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == 'SUM("amount")'
    )
    assert (
        render_mysql_expression(
            _aggregate("sum", INT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == "SUM(`amount`)"
    )
    assert (
        render_expression_sql(
            _aggregate("avg", FLOAT_NULLABLE, _field("score", FLOAT_NULLABLE))
        )
        == 'AVG("score")'
    )
    assert (
        render_mysql_expression(
            _aggregate("avg", FLOAT_NULLABLE, _field("score", FLOAT_NULLABLE))
        )
        == "AVG(`score`)"
    )


def test_sql_renderers_keep_malformed_aggregate_ir_fail_closed() -> None:
    count_with_argument = _aggregate("count", INT_NON_NULL, _literal(1))
    unsupported_function = _aggregate(
        "median",
        FLOAT_NULLABLE,
        _field("amount", INT_NON_NULL),
    )
    sum_wrong_arity = _aggregate("sum", INT_NULLABLE)
    sum_non_field = _aggregate("sum", INT_NULLABLE, _literal(1))
    sum_decimal_argument = _aggregate(
        "sum",
        INT_NULLABLE,
        _field("price", DECIMAL_NON_NULL),
    )

    with pytest.raises(
        ValueError,
        match="Unsupported PostgreSQL aggregate call: median",
    ):
        render_expression_sql(unsupported_function)
    with pytest.raises(ValueError, match="PostgreSQL aggregate count expects 0"):
        render_expression_sql(count_with_argument)
    with pytest.raises(ValueError, match="PostgreSQL aggregate sum expects 1"):
        render_expression_sql(sum_wrong_arity)
    with pytest.raises(ValueError, match="direct field argument"):
        render_expression_sql(sum_non_field)
    with pytest.raises(ValueError, match="supports only Int or Float"):
        render_expression_sql(sum_decimal_argument)

    with pytest.raises(MySqlRenderError, match="Unsupported MySQL aggregate call"):
        render_mysql_expression(unsupported_function)
    with pytest.raises(MySqlRenderError, match="MySQL aggregate count expects 0"):
        render_mysql_expression(count_with_argument)
    with pytest.raises(MySqlRenderError, match="MySQL aggregate sum expects 1"):
        render_mysql_expression(sum_wrong_arity)
    with pytest.raises(MySqlRenderError, match="direct field argument"):
        render_mysql_expression(sum_non_field)
    with pytest.raises(MySqlRenderError, match="supports only Int or Float"):
        render_mysql_expression(sum_decimal_argument)


def test_sum_avg_decimal_and_result_predicate_deferrals_remain_documented() -> None:
    docs = _normalized_docs(PHASE18_DOCS)

    for required in (
        "`sum` and `avg` may follow in later slices",
        "after the aggregate framework is stable",
        "Decimal exists in Pietto's built-in type catalog",
        "Decimal aggregate semantics are out of scope for this future MVP",
        "Decimal aggregate semantics are out of the future no-GROUP MVP",
        "PostgreSQL and MySQL physical return types for `SUM` and `AVG` may differ",
        "No GROUP BY",
        "SQL HAVING user syntax",
        "`satisfying` remains provisional, unparsed, unimplemented",
        "`where` remains input row-level filtering",
        "`filter` should not be introduced casually because it is too dataframe-like",
        "relationship-driven behavior",
        "Relationship metadata remains read-only metadata",
        "database execution",
    ):
        assert required in docs


def test_grammar_and_generated_surfaces_are_unchanged() -> None:
    assert _sha256(REPO_ROOT / "grammar/Pietto.g4") == GRAMMAR_HASH
    assert _aggregate_files(_generated_files("src/pietto/generated")) == GENERATED_HASH


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation_ast(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _compile_fixture(path: str) -> ScriptIR:
    parse_result = parse_file(REPO_ROOT / path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert _errors(semantic_result) == []

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


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


def _literal(value: StaticValue) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=INT_NON_NULL, value=value)


def _render_artifacts(result: SqlResult) -> bytes:
    return ("\n\n".join(artifact.sql for artifact in result.artifacts) + "\n").encode(
        "utf-8"
    )


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _check_goldens() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_phase19_check_goldens",
        REPO_ROOT / "scripts/check_goldens.py",
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return cast(ModuleType, module)


def _normalized_docs(paths: Iterable[Path]) -> str:
    return " ".join(" ".join(_read(path).split()) for path in paths)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
