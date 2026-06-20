from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-29-v02-stabilization-boundary.md"
SPEC_PATH = REPO_ROOT / "docs/spec/v02-core-type-system-gap-matrix-v1.md"

MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"

PHASE17_SCALAR_TEST_PATH = (
    REPO_ROOT / "tests/test_phase17_core_scalar_expression_semantics.py"
)
PHASE26_NUMERIC_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_numeric_scalar_expression_semantics.py"
)
PHASE26_DECIMAL_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_decimal_scalar_expression_semantics.py"
)
PHASE24_DECIMAL_AGGREGATE_TEST_PATH = (
    REPO_ROOT / "tests/test_phase24_decimal_aggregate_contract.py"
)

REQUIRED_MATRIX_ROWS = (
    "Canonical scalar type registry",
    "Type fact model",
    "Any",
    "Bool",
    "Int",
    "Float",
    "Decimal",
    "Text",
    "Bytes",
    "Json",
    "Date",
    "Timestamp",
    "UUID",
    "Enum",
    "Nullability propagation",
    "Predicate semantics / SQL three-valued logic boundary",
    "Operator compatibility matrix",
    "Comparison compatibility matrix",
    "Aggregate result matrix",
    "Decimal precision/scale",
    "DateTime/Time/Interval/timezone deferral",
    "Native DB type metadata deferral",
    "Semantic/domain annotation deferral",
    "Relationship cardinality/grain/fanout deferral",
)

CURRENT_BUILTIN_NAMES = (
    "Any",
    "Bool",
    "Bytes",
    "Date",
    "Decimal",
    "Float",
    "Int",
    "Json",
    "Text",
    "Timestamp",
    "UUID",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice4_plan_status_links_and_validation_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 29 Slice 4 is complete as core type-system gap matrix contract "
        "and static audit work only",
        "docs/spec/v02-core-type-system-gap-matrix-v1.md",
        "tests/test_phase29_v02_core_type_system_gap_matrix.py",
        "Status: complete as core type-system gap matrix contract and static "
        "audit work only",
        "uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py",
        "uv run pytest tests/test_phase29_v02_aggregate_surface_freeze.py",
        "uv run pytest tests/test_phase29_v02_deferred_feature_register.py",
        "uv run pytest tests/test_phase29_v02_stabilization_candidate_decision.py",
        "uv run pytest tests/test_phase17_core_scalar_expression_semantics.py "
        "tests/test_phase26_numeric_scalar_expression_semantics.py "
        "tests/test_phase26_decimal_scalar_expression_semantics.py",
        "uv run python scripts/validate.py",
        "Audit v0.2 core type system gaps",
    ):
        assert required in plan

    for later_slice in (
        "### Slice 5: v0.2 Exit Criteria And Validation Strategy Status: planned only",
        "### Slice 6: Completion Audit And Status Lock Status: planned only",
    ):
        assert later_slice in plan


def test_gap_matrix_spec_contract_boundary_is_static_audit_only() -> None:
    spec = _normalized(SPEC_PATH)

    assert SPEC_PATH.is_file()
    for required in (
        "Phase 29 Slice 4 is complete as a core type-system gap matrix "
        "contract and static audit slice only",
        "current repo facts, desired v0.2 contract targets, gaps, and "
        "Phase 30/31 disposition",
        "It does not authorize source implementation changes",
        "grammar changes",
        "generated ANTLR changes",
        "public API changes",
        "CLI behavior changes",
        "JSON behavior or schema changes",
        "IR behavior changes",
        "SQL lowering changes",
        "semantic behavior changes",
        "aggregate behavior changes",
        "diagnostic behavior changes",
        "type-system behavior changes",
        "Decimal precision/scale implementation",
        "UUID/Enum behavior",
        "Bytes/Json behavior expansion",
        "DateTime primitives",
        "Currency/Money primitives",
        "semantic annotation syntax",
    ):
        assert required in spec


def test_matrix_columns_and_required_rows_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    assert (
        "| Area | Current repo fact | Desired v0.2 contract target | Gap / risk | "
        "Phase 30/31 disposition | Explicit non-goals |"
    ) in spec
    for row in REQUIRED_MATRIX_ROWS:
        assert f"| {row} |" in spec


def test_current_type_model_and_builtin_catalog_facts_are_grounded() -> None:
    spec = _normalized(SPEC_PATH)
    model = _read(MODEL_PATH)
    catalog = _read(CATALOG_PATH)

    for required in (
        "built-in type names are cataloged as strings in `BUILTIN_TYPE_NAMES`",
        "`ResolvedType` carries `name`, `kind`, and optional `definition`",
        "`ValueType` carries `resolved_type`, `nullability`, and `kind`",
        "`Enum` is represented through enum/type-definition support and "
        "semantic type kinds, not as a normal built-in scalar name",
    ):
        assert required in spec

    for required in (
        "class ResolvedType:",
        "name: str",
        "kind: TypeKind",
        "definition: Node | None = None",
        "class ValueType:",
        "resolved_type: ResolvedType",
        "nullability: EffectiveNullability",
        "kind: ValueTypeKind = ValueTypeKind.KNOWN",
        'ENUM = "enum"',
    ):
        assert required in model

    assert "BUILTIN_TYPE_NAMES = frozenset(" in catalog
    for builtin_name in CURRENT_BUILTIN_NAMES:
        assert f'"{builtin_name}"' in catalog
        assert f"`{builtin_name}`" in spec
    assert '"Enum"' not in catalog


def test_current_operator_comparison_nullability_and_aggregate_facts_are_grounded() -> (
    None
):
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    aggregates = _read(AGGREGATES_PATH)
    phase17_tests = _read(PHASE17_SCALAR_TEST_PATH)
    phase26_numeric_tests = _read(PHASE26_NUMERIC_TEST_PATH)
    phase26_decimal_tests = _read(PHASE26_DECIMAL_TEST_PATH)
    phase24_decimal_aggregate_tests = _read(PHASE24_DECIMAL_AGGREGATE_TEST_PATH)

    for required in (
        "expression comparisons currently return Pietto `Bool` with unknown "
        "nullability when children are known",
        "that nullability uncertainty is separate from SQL predicate "
        "three-valued logic",
        "Current operators cover Int/Float `+`, `-`, `*`, Int `%`, Decimal "
        "`+`, `-`, Bool `and`/`or`, unary numeric `+`/`-`; `/` is deferred "
        "and unknown",
        "Aggregate result typing is implemented in aggregate helpers and "
        "frozen by `docs/spec/v02-aggregate-surface-freeze-v1.md`",
    ):
        assert required in spec

    for required in (
        'if expression.operator == "/":',
        "return _UNKNOWN_VALUE_TYPE",
        'if expression.operator in {"and", "or"}:',
        'if expression.operator == "%":',
        'if expression.operator in {"+", "-", "*"}:',
        'operator in {"+", "-"}',
        '_is_builtin(left_type, "Decimal")',
        '_builtin_value_type("Bool", EffectiveNullability.UNKNOWN)',
        "elif isinstance(expression, IsNullExpr):",
        "EffectiveNullability.NON_NULL",
    ):
        assert required in expressions

    for required in (
        "def semantic_aggregate_result_value_type(",
        "def aggregate_result_value_type(",
        "COUNT_VALUE_TYPE",
        "INT_NULLABLE_VALUE_TYPE",
        "FLOAT_NULLABLE_VALUE_TYPE",
        "DECIMAL_NULLABLE_VALUE_TYPE",
        "for name in (",
        '"UUID"',
    ):
        assert required in aggregates

    for required in (
        "test_division_remains_semantically_deferred_without_s2105",
        "test_boolean_binary_where_resolves_to_known_bool",
        "test_between_where_resolves_to_known_bool",
        "test_unary_numeric_projection_preserves_type_and_nullability",
    ):
        assert required in phase17_tests

    for required in (
        "test_division_remains_deferred_without_diagnostic",
        "test_numeric_arithmetic_inside_where_comparison_is_locked",
        "test_int_float_binary_arithmetic_computed_projection_schema_is_locked",
    ):
        assert required in phase26_numeric_tests

    for required in (
        "test_decimal_add_subtract_computed_projection_schema_is_locked",
        "test_decimal_division_remains_deferred_without_diagnostic",
        "test_invalid_decimal_arithmetic_forms_reuse_s2105",
    ):
        assert required in phase26_decimal_tests

    for required in (
        "`sum(Decimal) -> Decimal nullable`",
        "`avg(Decimal) -> Decimal nullable`",
        "`min(Decimal) -> Decimal nullable`",
        "`max(Decimal) -> Decimal nullable`",
        "there is no Decimal precision/scale promise in Phase 24",
    ):
        assert required in phase24_decimal_aggregate_tests


def test_phase30_and_phase31_handoff_is_locked_without_implementation() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 30 Slice 2 should define the canonical scalar registry contract",
        "Phase 30 Slice 3 should define the propagation contract",
        "Phase 30 Slice 4 should define Bool/predicate semantics and the SQL "
        "3VL boundary",
        "Phase 30 Slice 5 should formalize Date/Timestamp",
        "Phase 30 Slice 6 should define the contract",
        "Phase 30 Slice 7 should define operator matrix",
        "Phase 30 Slice 7 should define comparison matrix",
        "Phase 31 Slice 2 should harden aggregate result matrix after Phase 30",
        "Phase 31 UUID readiness or narrow-MVP decision",
        "Phase 31 Enum readiness or narrow-MVP decision",
        "Diagnostic And CLI/JSON Type Output Hardening",
    ):
        assert required in spec

    for step in (
        "Candidate Decision And Type-System Contract",
        "Canonical Scalar Type Registry",
        "Nullability Propagation Contract",
        "Bool And Predicate Semantics",
        "Date / Timestamp Formalization",
        "Decimal Precision / Scale Contract",
        "Operator And Comparison Matrix",
        "Completion Audit",
    ):
        assert step in spec


def test_deferred_boundaries_include_bytes_json_enum_and_domain_semantics() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "No Bytes behavior expansion in Slice 4 or before v0.2",
        "No Json behavior expansion in Slice 4 or before v0.2",
        "No UUID implementation or behavior expansion in Slice 4",
        "No enum SQL behavior, DDL, runtime mapping, or primitive scalar behavior",
        "No DateTime, Time, Interval, or timezone primitive",
        "No native DB type annotations, introspection, or physical schema binding",
        "No semantic annotation syntax; no Currency or Money primitive",
        "No relationship/JOIN implementation, grain inference, fanout analysis, "
        "or diagnostics",
        "No Decimal precision/scale implementation, syntax, casts, or behavior "
        "changes in Slice 4",
    ):
        assert required in spec


def test_forbidden_scope_is_not_authorized() -> None:
    plan_and_spec = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for forbidden in (
        "Slice 4 implements",
        "Slice 4 changes semantic behavior",
        "Slice 4 changes type-system behavior",
        "Slice 4 changes diagnostic behavior",
        "Slice 4 changes SQL lowering",
        "DateTime primitive is allowed",
        "Currency primitive is allowed",
        "Money primitive is allowed",
        "UUID implementation is allowed",
        "Enum implementation is allowed",
        "Bytes behavior expansion is allowed",
        "Json behavior expansion is allowed",
        "JSON v2 is allowed",
        "public `emit_mysql_sql`",
    ):
        assert forbidden not in plan_and_spec
