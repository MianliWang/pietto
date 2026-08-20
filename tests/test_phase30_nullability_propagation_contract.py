from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "docs/spec/nullability-propagation-contract-v1.md"
REGISTRY_CONTRACT_PATH = REPO_ROOT / "docs/spec/canonical-scalar-type-registry-v1.md"
MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
ANALYZER_PATH = REPO_ROOT / "src/pietto/semantic/analyzer.py"
SOURCES_PATH = REPO_ROOT / "src/pietto/semantic/sources.py"
EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
RELATION_SCHEMAS_PATH = REPO_ROOT / "src/pietto/semantic/relation_schemas.py"
GROUP_BY_PATH = REPO_ROOT / "src/pietto/semantic/group_by.py"
SATISFYING_PATH = REPO_ROOT / "src/pietto/semantic/satisfying.py"
PREDICATE_CHECKS_PATH = REPO_ROOT / "src/pietto/semantic/predicate_checks.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"

PHASE30_HARD_NON_GOALS = (
    "source implementation changes",
    "grammar, generated ANTLR, AST, or parser changes",
    "semantic implementation or semantic behavior changes",
    "type-system behavior changes",
    "diagnostic behavior changes",
    "IR implementation or IR model changes",
    "SQL backend or SQL lowering changes",
    "CLI behavior, command, option, help, exit-code, or output changes",
    "JSON v1 changes or JSON v2 implementation",
    "public API changes or public MySQL API expansion",
    "aggregate expansion or aggregate behavior changes",
    "fixture, golden, script, dependency, lockfile, package metadata, CI, or",
    "package version changes",
    "project or multi-file implementation",
    "schema introspection, database pull, SQL execution, connector execution, or",
    "runtime/database behavior",
    "relationship or JOIN implementation",
    "DateTime, Time, timezone, or Interval primitives",
    "Decimal precision/scale syntax semantics, carrier, propagation, validation,",
    "SQL precision guarantees, JSON/API exposure, native database metadata, or",
    "public contract",
    "Decimal literal syntax, Decimal multiplication or division expansion, mixed",
    "Decimal promotion expansion, or casts",
    "Currency or Money primitives",
    "exchange-rate, accounting, rounding, or minor-unit semantics",
    "semantic annotation syntax",
    "UUID implementation or broader UUID behavior",
    "Enum implementation or broader Enum behavior",
    "Bytes or Json behavior expansion",
    "native database type metadata",
    "broader nullability inference",
    "predicate rewrite behavior",
    "SQL three-valued logic lowering changes",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_three_unknown_concepts_are_distinct() -> None:
    spec = _normalized(SPEC_PATH)
    model = _read(MODEL_PATH)

    for required in (
        "`EffectiveNullability.UNKNOWN` is a nullability fact on a known value type",
        "the expression or value has a known type, but Pietto does not have a "
        "stable proof that the value is non-null or nullable",
        "`ValueTypeKind.UNKNOWN` / unknown value type is not merely unknown "
        "nullability",
        "Pietto cannot determine the value type itself, or the expression is "
        "unsupported or unknown under current semantics",
        "SQL three-valued logic `UNKNOWN` is a runtime predicate truth value",
        "Pietto `EffectiveNullability.UNKNOWN` is not SQL three-valued logic `UNKNOWN`",
        "an unknown value type is not a known type with unknown nullability",
    ):
        assert required in spec

    for required in (
        "class EffectiveNullability(StrEnum):",
        'NON_NULL = "non_null"',
        'NULLABLE = "nullable"',
        'UNKNOWN = "unknown"',
        "class ValueTypeKind(StrEnum):",
        'KNOWN = "known"',
        "class ValueType:",
        "nullability: EffectiveNullability",
        "kind: ValueTypeKind = ValueTypeKind.KNOWN",
    ):
        assert required in model


def test_typeexpr_source_projection_and_unknown_nullability_rules_are_grounded() -> (
    None
):
    spec = _normalized(SPEC_PATH)
    analyzer = _read(ANALYZER_PATH)
    sources = _read(SOURCES_PATH)
    relation_schemas = _read(RELATION_SCHEMAS_PATH)
    group_by = _read(GROUP_BY_PATH)
    satisfying = _read(SATISFYING_PATH)

    for required in (
        "`TypeExpr` nullability maps `nullable` to `EffectiveNullability.NULLABLE`",
        "`not null` to `EffectiveNullability.NON_NULL`",
        "implicit nullability to `EffectiveNullability.UNKNOWN`",
        "Source, shape, and callable field",
        "Inherits the field or parameter `TypeExpr` effective nullability",
        "Bare field reference",
        "Preserves the resolved `RowField.nullability`",
        "Unknown schema, unknown field, unsupported expression, or unsupported output",
        "Publishes unknown type facts and `EffectiveNullability.UNKNOWN`",
    ):
        assert required in spec

    for required in (
        "def _effective_nullability(type_expr: TypeExpr) -> EffectiveNullability:",
        "if type_expr.nullability is Nullability.NULLABLE:",
        "return EffectiveNullability.NULLABLE",
        "if type_expr.nullability is Nullability.NOT_NULL:",
        "return EffectiveNullability.NON_NULL",
        "return EffectiveNullability.UNKNOWN",
    ):
        assert required in analyzer

    assert "nullability=type_nullability[field.type_expr]" in sources
    assert "nullability=input_field.nullability" in relation_schemas
    assert "nullability=value_type.nullability" in relation_schemas
    assert "nullability=EffectiveNullability.UNKNOWN" in relation_schemas
    assert "nullability=input_field.nullability" in group_by
    assert "nullability=value_type.nullability" in group_by
    assert "nullability=EffectiveNullability.UNKNOWN" in group_by
    assert "nullability=field.nullability" in satisfying


def test_expression_nullability_rules_are_current_behavior_only() -> None:
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)

    for required in (
        "Bool literal",
        "`Bool NON_NULL`",
        "Text literal",
        "`Text NON_NULL`",
        "Int literal",
        "`Int NON_NULL`",
        "Float literal",
        "`Float NON_NULL`",
        "Unary numeric `+` / `-`",
        "Preserves operand type and operand nullability",
        "Binary arithmetic `+`, `-`, `*`, `%`",
        "returns conservative `EffectiveNullability.UNKNOWN`",
        "Bool `and` / `or` expression",
        "returns `Bool UNKNOWN`",
        "Comparison expression",
        "returns `Bool UNKNOWN`",
        "`between` expression",
        "`is null` / `is not null` expression",
        "Returns `Bool NON_NULL`",
        "Scalar function call",
        "returns conservative `EffectiveNullability.UNKNOWN`",
    ):
        assert required in spec

    for required in (
        "def _literal_value_type(expression: LiteralExpr) -> ValueType:",
        "if isinstance(value, bool):",
        'name = "Bool"',
        "elif isinstance(value, str):",
        'name = "Text"',
        "elif isinstance(value, int):",
        'name = "Int"',
        "elif isinstance(value, float):",
        'name = "Float"',
        "return _builtin_value_type(name, EffectiveNullability.NON_NULL)",
        "resolved_type=operand_type.resolved_type",
        "nullability=operand_type.nullability",
        'if expression.operator in {"and", "or"}:',
        'return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)',
        'if expression.operator == "%":',
        'return _builtin_value_type("Int", EffectiveNullability.UNKNOWN)',
        'if expression.operator in {"+", "-", "*"}:',
        "return _builtin_value_type(return_type, EffectiveNullability.UNKNOWN)",
        "elif isinstance(expression, ComparisonExpr):",
        "elif isinstance(expression, BetweenExpr):",
        'return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)',
        "elif isinstance(expression, IsNullExpr):",
        '"Bool",',
        "EffectiveNullability.NON_NULL",
        "signature.return_type",
        "EffectiveNullability.UNKNOWN",
    ):
        assert required in expressions


def test_aggregate_result_nullability_matrix_is_locked() -> None:
    spec = _normalized(SPEC_PATH)
    aggregates = _read(AGGREGATES_PATH)

    for required in (
        "| `count()` | `Int NON_NULL` |",
        "| `count(field)` | `Int NON_NULL` |",
        "| `count(source.field)` | `Int NON_NULL` |",
        "| `count_distinct(field)` | `Int NON_NULL` |",
        "| `count_distinct(source.field)` | `Int NON_NULL` |",
        "| `sum(Int)` | `Int NULLABLE` |",
        "| `sum(Float)` | `Float NULLABLE` |",
        "| `sum(Decimal)` | `Decimal NULLABLE` |",
        "| `avg(Int)` | `Float NULLABLE` |",
        "| `avg(Float)` | `Float NULLABLE` |",
        "| `avg(Decimal)` | `Decimal NULLABLE` |",
        "| `min(Int)` / `max(Int)` | `Int NULLABLE` |",
        "| `min(Float)` / `max(Float)` | `Float NULLABLE` |",
        "| `min(Decimal)` / `max(Decimal)` | `Decimal NULLABLE` |",
        "| `min(Date)` / `max(Date)` | `Date NULLABLE` |",
        "| `min(Timestamp)` / `max(Timestamp)` | `Timestamp NULLABLE` |",
        "Aggregate argument acceptance remains unchanged",
        "Slice 3 does not expand aggregate names, aggregate argument shapes, "
        "aggregate argument types, aggregate result types, or aggregate SQL "
        "lowering",
    ):
        assert required in spec

    for required in (
        "COUNT_VALUE_TYPE = ValueType(",
        'ResolvedType(name="Int", kind=TypeKind.BUILTIN)',
        "nullability=EffectiveNullability.NON_NULL",
        "INT_NULLABLE_VALUE_TYPE = ValueType(",
        'ResolvedType(name="Int", kind=TypeKind.BUILTIN)',
        "FLOAT_NULLABLE_VALUE_TYPE = ValueType(",
        'ResolvedType(name="Float", kind=TypeKind.BUILTIN)',
        "DECIMAL_NULLABLE_VALUE_TYPE = ValueType(",
        'ResolvedType(name="Decimal", kind=TypeKind.BUILTIN)',
        "nullability=EffectiveNullability.NULLABLE",
        "if function_name == COUNT_AGGREGATE_NAME:",
        "if function_name == COUNT_DISTINCT_AGGREGATE_NAME:",
        "return COUNT_VALUE_TYPE",
        "if function_name == SUM_AGGREGATE_NAME:",
        "if function_name == AVG_AGGREGATE_NAME:",
        "return ValueType(",
        "resolved_type=argument_type.resolved_type",
        "nullability=EffectiveNullability.NULLABLE",
    ):
        assert required in aggregates


def test_predicate_boundaries_and_sql_three_valued_logic_handoff_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    predicate_checks = _read(PREDICATE_CHECKS_PATH)
    satisfying = _read(SATISFYING_PATH)

    for required in (
        "Row-level `where` consumes known Bool predicates under current behavior",
        "If a predicate expression has a known non-Bool value type, Pietto "
        "reports the existing predicate diagnostic",
        "If the predicate value type is unknown, existing unknown-type, "
        "unknown-field, unsupported-expression, and deferred diagnostic paths "
        "remain responsible for fail-closed behavior",
        "Result-level `satisfying:` consumes known Bool predicates over "
        "supported output names under current behavior",
        "records predicate facts only when the result predicate is supported "
        "and typed as Bool",
        "This predicate boundary is a compile-time Pietto contract",
        "It is not a SQL runtime truth-table contract",
        "Slice 4 Bool And Predicate Semantics owns the fuller Bool/predicate "
        "contract and the SQL three-valued logic boundary",
    ):
        assert required in spec

    for required in (
        "Require known where, shape check, and index predicates to be Bool",
        "Return a diagnostic when a predicate has a known non-Bool type",
        "if value_type is None or value_type.kind is ValueTypeKind.UNKNOWN:",
        "return None",
        'if value_type.resolved_type.name == "Bool":',
        "Expected Bool expression in {context}",
    ):
        assert required in predicate_checks

    for required in (
        "_BOOL_VALUE_TYPE = ValueType(",
        'ResolvedType(name="Bool", kind=TypeKind.BUILTIN)',
        "nullability=EffectiveNullability.UNKNOWN",
        "if value_type.kind is ValueTypeKind.UNKNOWN:",
        "continue",
        "SatisfyingResultPredicateInfo(",
        "def _bool_predicate_diagnostic(",
        "if value_type.kind is ValueTypeKind.UNKNOWN or _is_bool(value_type):",
        "Expected Bool expression in satisfying clause",
    ):
        assert required in satisfying
