from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-30-core-type-system-stabilization-i.md"
SPEC_PATH = REPO_ROOT / "docs/spec/operator-comparison-matrix-contract-v1.md"
CORE_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/core-type-system-stabilization-contract-v1.md"
)
REGISTRY_CONTRACT_PATH = REPO_ROOT / "docs/spec/canonical-scalar-type-registry-v1.md"
NULLABILITY_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/nullability-propagation-contract-v1.md"
)
BOOL_CONTRACT_PATH = REPO_ROOT / "docs/spec/bool-predicate-semantics-contract-v1.md"
DATE_CONTRACT_PATH = REPO_ROOT / "docs/spec/date-timestamp-formalization-contract-v1.md"
DECIMAL_CONTRACT_PATH = REPO_ROOT / "docs/spec/decimal-precision-scale-contract-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
PREDICATE_CHECKS_PATH = REPO_ROOT / "src/pietto/semantic/predicate_checks.py"
SATISFYING_PATH = REPO_ROOT / "src/pietto/semantic/satisfying.py"

PHASE17_EXPRESSION_TEST_PATH = (
    REPO_ROOT / "tests/test_phase17_core_scalar_expression_semantics.py"
)
PHASE26_NUMERIC_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_numeric_scalar_expression_semantics.py"
)
PHASE26_DECIMAL_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_decimal_scalar_expression_semantics.py"
)
SEMANTIC_EXPRESSION_TEST_PATH = REPO_ROOT / "tests/test_semantic_expressions.py"
SEMANTIC_WHERE_TEST_PATH = REPO_ROOT / "tests/test_semantic_where.py"
SHAPE_PREDICATE_TEST_PATH = REPO_ROOT / "tests/test_semantic_shape_predicates.py"
SATISFYING_TEST_PATH = REPO_ROOT / "tests/test_phase25_satisfying_semantics.py"

PHASE30_HARD_NON_GOALS = (
    "source implementation changes",
    "grammar, generated ANTLR, AST, or parser changes",
    "semantic implementation or semantic behavior changes",
    "type-system behavior changes",
    "diagnostic behavior changes",
    "predicate behavior changes",
    "IR implementation or IR model changes",
    "SQL backend or SQL lowering changes",
    "SQL three-valued logic lowering changes",
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
    "Text concatenation",
    "new scalar functions, function overloads, casts, or collation behavior",
    "new comparison validation or pair-specific compatibility guarantees",
    "DateTime primitive or alias",
    "TimestampTZ, Instant, Time, or Interval primitives",
    "timezone semantics",
    "temporal arithmetic, date/time functions, extraction, or truncation",
    "Date/Timestamp literal syntax, Date/Timestamp casts, timestamp precision",
    "Decimal precision/scale syntax semantics, carrier, propagation, validation,",
    "SQL precision guarantees, JSON/API exposure, native database metadata, or",
    "public contract",
    "Decimal literal syntax, Decimal multiplication or division expansion, mixed",
    "Decimal promotion expansion, or casts",
    "Money or Currency primitives",
    "exchange-rate, accounting, rounding, or minor-unit semantics",
    "semantic annotation syntax",
    "UUID implementation or broader UUID behavior",
    "UUID comparison, cast, literal, storage, DDL, wider SQL, or public API",
    "Enum implementation or broader Enum behavior",
    "Enum SQL or comparison behavior",
    "Bytes or Json behavior expansion",
    "native database type metadata",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice7_artifacts_baseline_and_status_are_locked() -> None:
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    core_contract = _normalized(CORE_CONTRACT_PATH)
    registry_contract = _normalized(REGISTRY_CONTRACT_PATH)
    nullability_contract = _normalized(NULLABILITY_CONTRACT_PATH)
    bool_contract = _normalized(BOOL_CONTRACT_PATH)
    date_contract = _normalized(DATE_CONTRACT_PATH)
    decimal_contract = _normalized(DECIMAL_CONTRACT_PATH)

    for required in (
        "Phase 30 Slice 7 is complete as operator and comparison matrix "
        "contract, static audit, and status work only",
        "HEAD: `da9394c1e9e0383e574a5c773d1414e7969ca7c0`",
        "commit: `Document Decimal precision and scale contract`",
        "CI run: `27889088949 success`",
        "v0.2 is not complete yet",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in plan
        assert required in spec

    assert "operator-comparison-matrix-contract-v1.md" in plan
    assert "operator-comparison-matrix-contract-v1.md" in core_contract
    assert "Slice 7 Operator And Comparison Matrix" in registry_contract
    assert "Slice 7 Operator And Comparison Matrix" in nullability_contract
    assert "Slice 7 Operator And Comparison Matrix" in bool_contract
    assert "Slice 7 Operator And Comparison Matrix" in date_contract
    assert "Slice 7 Operator And Comparison Matrix" in decimal_contract
    assert "Slice 8 Completion Audit And Status Lock is complete" in spec
    assert "Phase 30 is complete as docs/spec/static-audit/status work only" in spec
    assert "v0.2 is not complete" in spec


def test_slice7_candidate_decision_is_docs_static_audit_status_only() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "| Candidate | Fit | Risk | Decision |",
        "Slice 7 docs/spec/static-audit/status only",
        "Chosen",
        "Tests-only hardening",
        "Rejected for Slice 7",
        "current behavior tests already cover the relevant operator, "
        "comparison, Decimal, Bool, and unknown-propagation surfaces",
        "Minimal implementation artifact",
        "Rejected; no consumer requires a registry object, compatibility "
        "helper, matrix API, or diagnostic helper before the contract is accepted",
        "Broad behavior implementation",
        "The selected Slice 7 direction is contract-first",
        "does not add operator compatibility validation",
        "diagnostic behavior",
        "SQL lowering changes",
    ):
        assert required in spec

    for forbidden in (
        "Slice 7 implements operator validation",
        "Slice 7 changes comparison validation",
        "Slice 7 changes diagnostics",
        "Slice 7 changes SQL lowering",
        "Slice 7 adds casts",
    ):
        assert forbidden not in spec


def test_operator_status_vocabulary_and_nullability_boundary_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    model = _read(MODEL_PATH)

    for required in (
        "currently accepted behavior",
        "currently rejected behavior with existing diagnostics",
        "currently deferred/unknown behavior",
        "current generic behavior without pair-specific compatibility guarantee",
        "explicitly out of v0.2 scope",
        "Operator result `UNKNOWN` below means Pietto `EffectiveNullability.UNKNOWN`",
        "It is not SQL three-valued logic `UNKNOWN`",
        "`ValueTypeKind.UNKNOWN` means the value type itself is unknown",
        "SQL three-valued logic `UNKNOWN` is a runtime SQL predicate truth value",
    ):
        assert required in spec

    for required in (
        "class EffectiveNullability(StrEnum):",
        'UNKNOWN = "unknown"',
        "class ValueTypeKind(StrEnum):",
        'KNOWN = "known"',
        'UNKNOWN = "unknown"',
    ):
        assert required in model


def test_unary_numeric_matrix_is_grounded_in_current_expressions() -> None:
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    numeric_tests = _read(PHASE26_NUMERIC_TEST_PATH)

    for required in (
        "Unary `+` / `-` | `Int`",
        "Unary `+` / `-` | `Float`",
        "preserves `Int` and operand nullability",
        "preserves `Float` and operand nullability",
        "Unary `+` / `-` | `Decimal`",
        "currently rejected with existing `PIE-S2105`",
        "Decimal unary is not accepted",
    ):
        assert required in spec

    is_numeric_body = _function_body(expressions, "def _is_numeric(")
    assert (
        'return _is_builtin(value_type, "Int") or _is_builtin(value_type, "Float")'
        in (is_numeric_body)
    )
    assert '"Decimal"' not in is_numeric_body

    unary_body = _function_body(expressions, "def _unary_value_type(")
    for required in (
        "operand_type.kind is ValueTypeKind.UNKNOWN",
        "return _UNKNOWN_VALUE_TYPE",
        "if not _is_numeric(operand_type):",
        'expected="numeric operand"',
        "resolved_type=operand_type.resolved_type",
        "nullability=operand_type.nullability",
    ):
        assert required in unary_body

    for required in (
        "test_unary_numeric_semantics_remain_unchanged",
        '("+amount", "Int", EffectiveNullability.NON_NULL)',
        '("-amount", "Int", EffectiveNullability.NON_NULL)',
        '("+weight", "Float", EffectiveNullability.NULLABLE)',
        '("-weight", "Float", EffectiveNullability.NULLABLE)',
    ):
        assert required in numeric_tests


def test_binary_numeric_decimal_modulo_and_division_matrix_is_grounded() -> None:
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    phase17_tests = _read(PHASE17_EXPRESSION_TEST_PATH)
    numeric_tests = _read(PHASE26_NUMERIC_TEST_PATH)
    decimal_tests = _read(PHASE26_DECIMAL_TEST_PATH)

    for required in (
        "Binary `+` / `-` / `*` | `Int` / `Int`",
        "currently accepted as `Int UNKNOWN`",
        "`Int` / `Float`, `Float` / `Int`, `Float` / `Float`",
        "currently accepted as `Float UNKNOWN`",
        "Binary `+` / `-` | `Decimal` / `Decimal`",
        "currently accepted as `Decimal UNKNOWN`",
        "Binary `*` | `Decimal` / `Decimal`",
        "no Decimal multiplication",
        "no mixed Decimal promotion",
        "Modulo `%` | `Int` / `Int`",
        "currently accepted as `Int UNKNOWN`",
        "Division `/` | all operand pairs",
        "currently deferred/unknown",
        "does not emit `PIE-S2105`",
    ):
        assert required in spec

    binary_body = _function_body(expressions, "def _binary_value_type(")
    for required in (
        'if expression.operator == "/":',
        "return _UNKNOWN_VALUE_TYPE",
        "left_type.kind is ValueTypeKind.UNKNOWN",
        "or right_type.kind is ValueTypeKind.UNKNOWN",
        'if expression.operator == "%":',
        '_is_builtin(left_type, "Int")',
        '_is_builtin(right_type, "Int")',
        'expected="Int operands"',
        'if expression.operator in {"+", "-", "*"}:',
        "return_type = _binary_arithmetic_result_type(",
        'expected="numeric operands"',
    ):
        assert required in binary_body

    arithmetic_body = _function_body(expressions, "def _binary_arithmetic_result_type(")
    for required in (
        "if _is_numeric(left_type) and _is_numeric(right_type):",
        '"Float"',
        '"Int"',
        'operator in {"+", "-"}',
        '_is_builtin(left_type, "Decimal")',
        '_is_builtin(right_type, "Decimal")',
        'return "Decimal"',
        "return None",
    ):
        assert required in arithmetic_body

    for required in (
        "test_modulo_projection_requires_int_and_returns_int",
        "value = count % 2",
        "test_division_remains_semantically_deferred_without_s2105",
    ):
        assert required in phase17_tests

    for required in (
        '("amount + tax", "Int")',
        '("amount * tax", "Int")',
        '("amount + score", "Float")',
        '("score * amount", "Float")',
        "test_division_remains_deferred_without_diagnostic",
    ):
        assert required in numeric_tests

    for required in (
        "price + price",
        "price - price",
        "test_invalid_decimal_arithmetic_forms_reuse_s2105",
        "price * price",
        "price * amount",
        "score + price",
        "price + score",
        "test_decimal_division_remains_deferred_without_diagnostic",
    ):
        assert required in decimal_tests


def test_text_concatenation_and_scalar_function_boundaries_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    catalog = _read(CATALOG_PATH)
    phase17_tests = _read(PHASE17_EXPRESSION_TEST_PATH)

    for required in (
        "Text concatenation is not supported by Slice 7",
        "`Text + Text` is not a string concatenation operator",
        "Current scalar function calls remain exact built-ins",
        "`lower` | `lower(Text) -> Text`",
        "`trim` | `trim(Text) -> Text`",
        "`len` | `len(Text) -> Int`",
        "`matches` | `matches(Text, Text) -> Bool`",
        "does not add scalar functions",
        "function overloads",
        "collation behavior",
        "Text comparison guarantees",
        "Text concatenation",
    ):
        assert required in spec

    for required in (
        "BUILTIN_FUNCTIONS: Mapping[str, BuiltinFunction]",
        'BuiltinFunction("lower", ("Text",), "Text")',
        'BuiltinFunction("trim", ("Text",), "Text")',
        'BuiltinFunction("len", ("Text",), "Int")',
        'BuiltinFunction("matches", ("Text", "Text"), "Bool")',
    ):
        assert required in catalog

    for required in (
        "test_invalid_arithmetic_reports_s2105",
        "value = text + 1",
        "Invalid operands for operator +: expected numeric operands",
    ):
        assert required in phase17_tests


def test_bool_operator_matrix_and_predicate_boundary_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    bool_contract = _normalized(BOOL_CONTRACT_PATH)
    predicate_checks = _read(PREDICATE_CHECKS_PATH)
    satisfying = _read(SATISFYING_PATH)
    where_tests = _read(SEMANTIC_WHERE_TEST_PATH)
    shape_tests = _read(SHAPE_PREDICATE_TEST_PATH)
    satisfying_tests = _read(SATISFYING_TEST_PATH)

    for required in (
        "Bool `and` / `or` | `Bool` / `Bool`",
        "currently accepted as `Bool UNKNOWN`",
        "Bool operators require Bool operands",
        "unknown operands",
        "without an extra invalid-operand cascade",
        "predicate diagnostics remain owned by the existing predicate paths",
        "Slice 4 Bool/predicate contract",
    ):
        assert required in spec

    binary_body = _function_body(expressions, "def _binary_value_type(")
    for required in (
        'if expression.operator in {"and", "or"}:',
        '_is_builtin(left_type, "Bool")',
        '_is_builtin(right_type, "Bool")',
        'return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)',
        'expected="Bool operands"',
    ):
        assert required in binary_body

    for required in (
        "known `Bool` predicates pass the current Bool consumer check",
        "known non-Bool predicates report the existing `PIE-S2202` diagnostic",
        "unknown value type predicates do not receive an extra Bool-cascade",
    ):
        assert required in bool_contract

    for required in (
        "value_type is None or value_type.kind is ValueTypeKind.UNKNOWN",
        "return None",
        'value_type.resolved_type.name == "Bool"',
        'code="PIE-S2202"',
    ):
        assert required in predicate_checks

    for required in (
        'code="PIE-S2323"',
        'code="PIE-S2324"',
        'code="PIE-S2325"',
        'code="PIE-S2326"',
        'code="PIE-S2327"',
        'code="PIE-S2202"',
    ):
        assert required in satisfying

    for required in (
        "Expected Bool expression in where clause",
        "PIE-S2202",
    ):
        assert required in where_tests

    for required in (
        "Expected Bool expression in shape check",
        "Expected Bool expression in index predicate",
        "PIE-S2202",
    ):
        assert required in shape_tests

    for required in (
        "`satisfying` requires GROUP BY",
        "PIE-S2327",
        "Expected Bool expression in satisfying clause",
    ):
        assert required in satisfying_tests


def test_comparison_between_and_is_null_boundaries_are_generic_only() -> None:
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    semantic_expression_tests = _read(SEMANTIC_EXPRESSION_TEST_PATH)
    phase17_tests = _read(PHASE17_EXPRESSION_TEST_PATH)

    for required in (
        "Current comparison behavior is generic known-child typing",
        "known child value types currently produce `Bool UNKNOWN`",
        "current compiler behavior fact, not a final pair-specific semantic "
        "compatibility guarantee",
        "does not add new comparison validation",
        "casts",
        "collation",
        "temporal comparison rules",
        "UUID comparison guarantees",
        "Enum comparison behavior",
        "Bytes/Json comparison behavior",
        "SQL lowering changes",
        "`BetweenExpr` has the same generic posture",
        "if all child value types are known",
        "`is null` and `is not null` type the operand expression and currently "
        "return `Bool NON_NULL`",
    ):
        assert required in spec

    infer_body = _function_body(expressions, "def _infer(")
    for required in (
        "elif isinstance(expression, ComparisonExpr):",
        "expression.left",
        "expression.right",
        '"Bool"',
        "EffectiveNullability.UNKNOWN",
        "elif isinstance(expression, BetweenExpr):",
        "elif isinstance(expression, IsNullExpr):",
        "EffectiveNullability.NON_NULL",
    ):
        assert required in infer_body

    between_body = _function_body(expressions, "def _between_value_type(")
    for required in (
        "child_types = tuple(",
        "expression.value, expression.lower, expression.upper",
        "if any(child_type.kind is ValueTypeKind.UNKNOWN for child_type in child_types):",
        "return _UNKNOWN_VALUE_TYPE",
        'return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)',
    ):
        assert required in between_body

    for required in (
        "test_simple_comparison_maps_to_bool_and_types_operands",
        "where id >= 1",
        'value_type.resolved_type.name == "Bool"',
        "test_is_null_expression_maps_to_non_null_bool",
        "EffectiveNullability.NON_NULL",
        "test_unknown_call_argument_suppresses_dependent_call_diagnostic",
    ):
        assert required in semantic_expression_tests

    for required in (
        "test_between_where_resolves_to_known_bool",
        "where count between 1 and 5",
        "test_unknown_children_suppress_s2105_cascades",
    ):
        assert required in phase17_tests


def test_registry_temporal_decimal_uuid_enum_bytes_json_boundaries_are_preserved() -> (
    None
):
    spec = _normalized(SPEC_PATH)
    registry_contract = _normalized(REGISTRY_CONTRACT_PATH)
    date_contract = _normalized(DATE_CONTRACT_PATH)
    decimal_contract = _normalized(DECIMAL_CONTRACT_PATH)
    catalog = _read(CATALOG_PATH)
    model = _read(MODEL_PATH)

    for required in (
        "`UUID` remains a limited/frozen identifier scalar only for existing "
        "accepted behavior such as direct-field `count_distinct(UUID)`",
        "adds no UUID comparison, cast, literal, storage, DDL, wider SQL, or "
        "public API behavior",
        "`Enum` remains a non-builtin semantic type kind",
        "has no SQL/comparison behavior in Slice 7",
        "`Bytes` and `Json` remain deferred/unsupported behavior built-ins",
        "`Any` must not hide unsupported behavior",
        "no Date/Timestamp-specific comparison matrix",
        "no DateTime primitive or alias",
        "no Time or Interval primitive",
        "no timezone semantics",
        "no temporal arithmetic",
        "no date/time functions",
        "no temporal casts",
        "no Date/Timestamp literals",
        "no timestamp precision modeling",
        "no Decimal multiplication",
        "no Decimal division",
        "no mixed Decimal/Int promotion",
        "no mixed Decimal/Float promotion",
        "no Decimal literals",
        "no casts",
        "no Decimal precision/scale semantics",
    ):
        assert required in spec

    for builtin_name in (
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
    ):
        assert f'"{builtin_name}"' in catalog

    assert '"Enum"' not in catalog
    assert 'ENUM = "enum"' in model

    for required in (
        "`UUID` is a limited/frozen identifier scalar",
        "`Bytes` and `Json` are deferred/unsupported behavior built-ins",
        "`Any` is the boundary/top scalar classification",
        "`Enum` is a non-builtin semantic type kind",
        "| temporal | `Date`, `Timestamp` |",
        "| identifier | `UUID` |",
    ):
        assert required in registry_contract

    for required in (
        "Current comparison handling is generic and not Date/Timestamp-specific",
        "Slice 5 does not define a Date/Timestamp-specific comparison "
        "compatibility matrix",
    ):
        assert required in date_contract

    for required in (
        "`Decimal + Decimal` returns logical `Decimal UNKNOWN`",
        "`Decimal - Decimal` returns logical `Decimal UNKNOWN`",
        "Decimal multiplication",
        "Decimal division",
        "mixed Decimal/Int promotion",
        "mixed Decimal/Float promotion",
        "Decimal literal syntax",
        "casts",
        "There are no stable v0.2 Decimal precision/scale semantics",
    ):
        assert required in decimal_contract


def test_diagnostics_and_unknown_propagation_are_current_behavior_only() -> None:
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    phase17_tests = _read(PHASE17_EXPRESSION_TEST_PATH)
    numeric_tests = _read(PHASE26_NUMERIC_TEST_PATH)
    decimal_tests = _read(PHASE26_DECIMAL_TEST_PATH)

    for required in (
        "Current diagnostic behavior is preserved exactly",
        "invalid known operator operands use existing `PIE-S2105` only where "
        "current repo behavior already emits it",
        "division `/` remains deferred/unknown and does not become a new "
        "diagnostic behavior",
        "unknown child value types suppress invalid-operator cascades",
        "Slice 7 introduces no new diagnostic code",
        "no renamed diagnostic",
        "no reordered diagnostic",
        "no reworded diagnostic",
        "no span or severity change",
    ):
        assert required in spec

    for required in (
        'code="PIE-S2105"',
        "message=(",
        "Invalid operands for operator {expression.operator}: expected {expected}",
    ):
        assert required in expressions

    for test_source in (phase17_tests, numeric_tests, decimal_tests):
        for required in (
            "ValueTypeKind.UNKNOWN",
            "PIE-S2105",
            "not in [diagnostic.code for diagnostic in",
        ):
            assert required in test_source


def test_handoff_non_goals_and_status_docs_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    core_contract = _normalized(CORE_CONTRACT_PATH)
    plan_and_specs = f"{plan} {spec} {core_contract}"

    for required in (
        "Slice 8 Completion Audit And Status Lock is complete as completion "
        "audit and status lock work only",
        "verifies the complete Phase 30 contract set",
        "Phase 31 Core Type System Stabilization II And Dialect Matrix "
        "Hardening is the next mainline",
        "may separately harden numeric/Decimal boundaries",
        "UUID/Enum readiness",
        "Date/Timestamp SQL compatibility",
        "diagnostic boundaries",
        "CLI/JSON hardening",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in plan_and_specs

    for required in PHASE30_HARD_NON_GOALS:
        assert required in plan_and_specs

    for relative_path in ("AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 30 Core Type System Stabilization I",
            "Slice 7 is complete as operator and comparison matrix contract, "
            "static audit, and status work only",
            "current comparison behavior is generic known-child typing",
            "not a final pair-specific semantic compatibility guarantee",
            "no Text concatenation",
            "no Decimal multiplication/division expansion",
            "no mixed Decimal promotion expansion",
            "no Date/Timestamp-specific comparison matrix",
            "no UUID comparison, cast, literal, storage, DDL, wider SQL, or "
            "public API behavior",
            "Enum remains a non-builtin semantic type kind",
            "Bytes and Json remain deferred/unsupported behavior built-ins",
            "Slice 8 is complete as completion audit and status lock work only",
            "Phase 30 is complete",
            "Phase 31 v0.2 Hardening And Stable Completion is complete",
            "Pietto v0.2 single-file stable complete",
            "Phase 31 Slice 8 complete",
            "Phase 32 has started",
            "Phase 32 Slice 1 Candidate Decision, Roadmap Alignment, And v0.2 "
            "Handoff Audit is complete as docs/spec/static-audit/status-only work",
            "Phase 32 as a whole is not complete",
            "Phase 32: Semantic Explain And Metadata Output MVP",
        ):
            assert required in status_doc
        assert "Phase 32 remains post-v0.2 and has not started" not in status_doc

        for forbidden in (
            "v0.2 is complete",
            "Phase 30 implementation",
            "Phase 31 implementation is complete",
            "Text concatenation is implemented",
            "comparison compatibility matrix is implemented",
            "DateTime primitive is allowed",
            "Currency primitive is allowed",
            "Money primitive is allowed",
            "UUID implementation is allowed",
            "Enum implementation is allowed",
            "public `emit_mysql_sql`",
            "Phase 30 implements relationship/JOIN",
            "Phase 30 implements project mode",
            "Phase 30 changes JSON v1",
            "Phase 30 implements JSON v2",
            "Phase 30 expands aggregate",
            "Phase 30 changes predicate behavior",
            "Phase 30 changes diagnostics",
            "Phase 30 changes SQL lowering",
        ):
            assert forbidden not in status_doc


def _function_body(source: str, marker: str) -> str:
    start = source.index(marker)
    rest = source[start:]
    next_def = rest.find("\n\ndef ", len(marker))
    return rest if next_def == -1 else rest[:next_def]
