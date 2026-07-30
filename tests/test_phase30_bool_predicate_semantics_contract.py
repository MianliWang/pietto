from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-30-core-type-system-stabilization-i.md"
SPEC_PATH = REPO_ROOT / "docs/spec/bool-predicate-semantics-contract-v1.md"
CORE_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/core-type-system-stabilization-contract-v1.md"
)
REGISTRY_CONTRACT_PATH = REPO_ROOT / "docs/spec/canonical-scalar-type-registry-v1.md"
NULLABILITY_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/nullability-propagation-contract-v1.md"
)

MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
PREDICATE_CHECKS_PATH = REPO_ROOT / "src/pietto/semantic/predicate_checks.py"
SATISFYING_PATH = REPO_ROOT / "src/pietto/semantic/satisfying.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"

SEMANTIC_WHERE_TEST_PATH = REPO_ROOT / "tests/test_semantic_where.py"
SHAPE_PREDICATE_TEST_PATH = REPO_ROOT / "tests/test_semantic_shape_predicates.py"
SATISFYING_TEST_PATH = REPO_ROOT / "tests/test_phase25_satisfying_semantics.py"
EXPRESSION_TEST_PATH = REPO_ROOT / "tests/test_semantic_expressions.py"
PHASE17_EXPRESSION_TEST_PATH = (
    REPO_ROOT / "tests/test_phase17_core_scalar_expression_semantics.py"
)

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
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice4_artifacts_baseline_and_status_are_locked() -> None:
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    core_contract = _normalized(CORE_CONTRACT_PATH)
    registry_contract = _normalized(REGISTRY_CONTRACT_PATH)
    nullability_contract = _normalized(NULLABILITY_CONTRACT_PATH)

    for required in (
        "Phase 30 Slice 4 is complete as Bool and predicate semantics "
        "contract, static audit, and status work only",
        "HEAD: `b0d9f99b20c691af921cbd06dc45b22d3c509a17`",
        "commit: `Document nullability propagation contract`",
        "CI run: `27886514387 success`",
        "v0.2 is not complete yet",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in plan
        assert required in spec

    assert "bool-predicate-semantics-contract-v1.md" in plan
    assert "bool-predicate-semantics-contract-v1.md" in core_contract
    assert "Slice 4 Bool And Predicate Semantics" in registry_contract
    assert "Slice 4 Bool And Predicate Semantics" in nullability_contract


def test_slice4_candidate_decision_is_docs_static_audit_status_only() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "| Candidate | Fit | Risk | Decision |",
        "Slice 4 docs/spec/static-audit/status only",
        "Chosen",
        "Tests-only hardening",
        "Rejected for Slice 4",
        "Minimal implementation artifact",
        "Rejected; no helper, enum, registry, or predicate API is needed",
        "Broad behavior implementation",
        "Rejected; it could change semantic, diagnostic, IR, SQL, CLI, JSON, "
        "fixture, golden, aggregate, and public API behavior",
        "The selected Slice 4 direction is contract-first",
        "does not widen predicate acceptance",
    ):
        assert required in spec

    for forbidden in (
        "Slice 4 implements predicate behavior",
        "Slice 4 changes predicate validation",
        "Slice 4 changes diagnostics",
        "Slice 4 changes SQL lowering",
        "Slice 4 implements SQL three-valued logic",
    ):
        assert forbidden not in spec


def test_bool_registry_trait_is_contract_vocabulary_only() -> None:
    spec = _normalized(SPEC_PATH)
    registry_contract = _normalized(REGISTRY_CONTRACT_PATH)
    catalog = _read(CATALOG_PATH)

    for required in (
        "`Bool` is a current built-in scalar name",
        "the Slice 2 canonical scalar registry contract records `Bool` under "
        "the `boolean` trait",
        "The `boolean` trait is contract vocabulary only in Phase 30 Slice 4",
        "does not add a scalar registry object",
        "operator behavior",
        "comparison behavior",
        "predicate behavior",
        "diagnostic behavior",
        "SQL lowering behavior",
    ):
        assert required in spec

    assert "BUILTIN_TYPE_NAMES = frozenset(" in catalog
    assert '"Bool"' in catalog
    assert "| boolean | `Bool` |" in registry_contract
    assert "These traits are contract vocabulary only in Slice 2" in registry_contract


def test_expression_bool_facts_are_current_behavior_only() -> None:
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    expression_tests = _read(EXPRESSION_TEST_PATH)
    phase17_expression_tests = _read(PHASE17_EXPRESSION_TEST_PATH)

    for required in (
        "| Bool literal | `Bool NON_NULL` |",
        "| Bool `and` / `or` | Requires known Bool operands; returns `Bool UNKNOWN` |",
        "| Bool `and` / `or` with known non-Bool operands | Reports existing "
        "`PIE-S2105` invalid-operator diagnostic and produces unknown value type |",
        "| Comparison expression | Types children and returns `Bool UNKNOWN` "
        "when children are known |",
        "| `between` expression | Types children and returns `Bool UNKNOWN` "
        "when children are known |",
        "| `is null` / `is not null` expression | Returns `Bool NON_NULL` |",
        "`UNKNOWN` in `Bool UNKNOWN` is Pietto `EffectiveNullability.UNKNOWN`",
        "It is not a SQL runtime truth value",
    ):
        assert required in spec

    for required in (
        "def _literal_value_type(expression: LiteralExpr) -> ValueType:",
        "if isinstance(value, bool):",
        'name = "Bool"',
        "return _builtin_value_type(name, EffectiveNullability.NON_NULL)",
        'if expression.operator in {"and", "or"}:',
        'if _is_builtin(left_type, "Bool") and _is_builtin(right_type, "Bool"):',
        'return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)',
        'expected="Bool operands"',
        "left_type.kind is ValueTypeKind.UNKNOWN",
        "or right_type.kind is ValueTypeKind.UNKNOWN",
        "elif isinstance(expression, ComparisonExpr):",
        "elif isinstance(expression, BetweenExpr):",
        'return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)',
        "elif isinstance(expression, IsNullExpr):",
        '"Bool",',
        "EffectiveNullability.NON_NULL",
        'code="PIE-S2105"',
    ):
        assert required in expressions

    for required in (
        "test_is_null_expression_maps_to_non_null_bool",
        "test_simple_comparison_maps_to_bool_and_types_operands",
    ):
        assert required in expression_tests

    for required in (
        "test_boolean_binary_where_resolves_to_known_bool",
        "test_between_where_resolves_to_known_bool",
        "test_invalid_bool_binary_reports_s2105_at_full_span",
    ):
        assert required in phase17_expression_tests


def test_row_shape_and_index_predicate_consumers_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    predicate_checks = _read(PREDICATE_CHECKS_PATH)
    where_tests = _read(SEMANTIC_WHERE_TEST_PATH)
    shape_tests = _read(SHAPE_PREDICATE_TEST_PATH)

    for required in (
        "| Row-level `where` | Consumes a Pietto expression typed as known "
        "`Bool` under current row-scope expression rules |",
        "| Shape `check` | Consumes a Pietto expression typed as known `Bool` "
        "under current shape-scope expression rules |",
        "| Index `when` predicate | Consumes a Pietto expression typed as known "
        "`Bool` under current shape/index expression rules |",
        "known `Bool` predicates pass the current Bool consumer check",
        "known non-Bool predicates report the existing `PIE-S2202` diagnostic",
        "unknown value type predicates do not receive an extra Bool-cascade "
        "diagnostic from the Bool consumer",
    ):
        assert required in spec

    for required in (
        "Require known where, shape check, and index predicates to be Bool",
        'context="where clause"',
        'context = "shape check"',
        'context = "index predicate"',
        "Return a diagnostic when a predicate has a known non-Bool type",
        "if value_type is None or value_type.kind is ValueTypeKind.UNKNOWN:",
        "return None",
        'if value_type.resolved_type.name == "Bool":',
        'code="PIE-S2202"',
        "Expected Bool expression in {context}",
    ):
        assert required in predicate_checks

    for required in (
        "test_known_non_bool_table_where_reports_pie_s2202",
        "test_unknown_field_suppresses_bool_cascade",
        "test_unknown_function_suppresses_bool_diagnostic",
    ):
        assert required in where_tests

    for required in (
        "test_known_bool_shape_check_passes",
        "test_known_non_bool_shape_check_reports_pie_s2202",
        "test_known_bool_index_predicate_passes",
        "test_known_non_bool_index_predicate_reports_pie_s2202",
        "test_unknown_shape_field_suppresses_bool_cascade",
    ):
        assert required in shape_tests


def test_satisfying_result_predicate_boundary_uses_existing_diagnostics() -> None:
    spec = _normalized(SPEC_PATH)
    satisfying = _read(SATISFYING_PATH)
    aggregates = _read(AGGREGATES_PATH)
    satisfying_tests = _read(SATISFYING_TEST_PATH)

    for required in (
        "| Result-level `satisfying:` | Consumes a supported grouped result "
        "predicate typed as known `Bool` over supported selected output names |",
        "`satisfying:` requires GROUP BY and otherwise reports existing `PIE-S2323`",
        "unknown selected output names report existing `PIE-S2324`",
        "input field references where a selected output name is required report "
        "existing `PIE-S2325`",
        "unsupported selected outputs report existing `PIE-S2326`",
        "unsupported result-predicate expression forms report existing `PIE-S2327`",
        "direct aggregate calls inside `satisfying:` report the existing "
        "aggregate invalid-context diagnostic `PIE-S2308`",
        "known non-Bool `satisfying:` predicates report existing `PIE-S2202`",
        "invalid Bool `and` / `or` operands report existing `PIE-S2105`",
        "Slice 4 introduces no new diagnostic code",
    ):
        assert required in spec

    for required in (
        "if contains_semantic_aggregate(expression):",
        "invalid_context_diagnostic(",
        'context="satisfying clause"',
        "if definition.group_by_clause is None:",
        "def _no_group_diagnostic(",
        'code="PIE-S2323"',
        "`satisfying` requires GROUP BY in the Phase 25 MVP",
        "def _unknown_output_diagnostic(",
        'code="PIE-S2324"',
        "Unknown select output in satisfying",
        "def _input_field_reference_diagnostic(",
        'code="PIE-S2325"',
        "Satisfying reference must use select output name",
        "def _unsupported_output_diagnostic(",
        'code="PIE-S2326"',
        "Satisfying output is not a group-key or direct aggregate ",
        "projection: {expression.name}",
        "def _unsupported_expression_diagnostic(",
        'code="PIE-S2327"',
        "Unsupported satisfying expression form",
        "def _bool_predicate_diagnostic(",
        'code="PIE-S2202"',
        "Expected Bool expression in satisfying clause",
        "def _invalid_bool_operands_diagnostic(",
        'code="PIE-S2105"',
        "expected Bool operands",
        "if value_type.kind is ValueTypeKind.UNKNOWN:",
        "continue",
        "SatisfyingResultPredicateInfo(",
    ):
        assert required in satisfying

    for required in (
        "def invalid_context_diagnostic(",
        'code="PIE-S2308"',
        "is not allowed in",
        "use it only as a direct aliased select projection",
    ):
        assert required in aggregates

    for required in (
        "test_no_group_satisfying_is_rejected",
        "test_unknown_select_output_name_in_satisfying_is_rejected",
        "test_input_field_reference_in_satisfying_must_use_select_output",
        "test_computed_projection_output_in_satisfying_is_deferred",
        "test_unsupported_satisfying_expression_forms_are_deferred",
        "test_non_bool_satisfying_predicate_reuses_predicate_diagnostic",
        "test_and_or_bool_composition_is_accepted",
        "test_invalid_and_or_operands_reuse_operator_diagnostic",
    ):
        assert required in satisfying_tests


def test_three_unknown_concepts_remain_separate() -> None:
    spec = _normalized(SPEC_PATH)
    nullability_contract = _normalized(NULLABILITY_CONTRACT_PATH)
    model = _read(MODEL_PATH)

    for required in (
        "`EffectiveNullability.UNKNOWN` is a nullability fact on a known value type",
        "`Bool UNKNOWN` predicate has a known Pietto value type of `Bool`",
        "`ValueTypeKind.UNKNOWN` / unknown value type means Pietto cannot "
        "determine the value type itself",
        "SQL three-valued logic `UNKNOWN` is a runtime SQL predicate truth value",
        "not a Pietto compile-time type fact",
        "Pietto compile-time predicate acceptance means only that the expression "
        "is typed as `Bool` under the current compiler rules",
        "does not evaluate runtime truth",
        "infer SQL TRUE/FALSE/UNKNOWN",
        "or rewrite predicates",
    ):
        assert required in spec

    for required in (
        "class EffectiveNullability(StrEnum):",
        'UNKNOWN = "unknown"',
        "class ValueTypeKind(StrEnum):",
        'UNKNOWN = "unknown"',
        "class ValueType:",
        "nullability: EffectiveNullability",
        "kind: ValueTypeKind = ValueTypeKind.KNOWN",
    ):
        assert required in model

    for required in (
        "`EffectiveNullability.UNKNOWN` is a nullability fact on a known value type",
        "`ValueTypeKind.UNKNOWN` / unknown value type is not merely unknown nullability",
        "SQL three-valued logic `UNKNOWN` is a runtime predicate truth value",
    ):
        assert required in nullability_contract


def test_later_slice_handoff_and_hard_non_goals_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    core_contract = _normalized(CORE_CONTRACT_PATH)
    plan_and_specs = f"{plan} {spec} {core_contract}"

    for required in (
        "Slice 5 Date / Timestamp Formalization",
        "Slice 6 Decimal Precision / Scale Contract",
        "Slice 7 Operator And Comparison Matrix",
        "Slice 7 Operator And Comparison Matrix owns the full supported, "
        "rejected, and deferred matrix for operators and comparisons",
        "Slice 4 does not widen comparison acceptance",
        "SQL three-valued logic lowering changes",
        "Slice 5 is complete as Date / Timestamp formalization contract, "
        "static audit, and status work only",
        "Slice 6 is complete as Decimal precision / scale contract, static "
        "audit, and status work only",
        "Slice 7 is complete as operator and comparison matrix contract, "
        "static audit, and status work only",
        "Slice 8 is complete as completion audit and status lock work only",
        "Phase 30 is complete as docs/spec/static-audit/status work only",
        "v0.2 is not complete",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in plan_and_specs

    for required in PHASE30_HARD_NON_GOALS:
        assert required in plan_and_specs


def test_status_docs_record_slice4_without_v02_completion_or_behavior_change() -> None:
    for relative_path in ("AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 30 Core Type System Stabilization I",
            "Slice 4 is complete as Bool and predicate semantics contract, "
            "static audit, and status work only",
            "Known Bool predicate acceptance remains a compile-time type-level fact",
            "Slice 5 is complete as Date / Timestamp formalization contract, "
            "static audit, and status work only",
            "`Timestamp` is the current canonical v0.2 spelling for date+time values",
            "current generic comparison behavior only",
            "no `DateTime` primitive or alias",
            "Slice 6 is complete as Decimal precision / scale contract, static "
            "audit, and status work only",
            "`Decimal` remains logical v0.2 exact numeric",
            "generic `TypeExpr.arguments`, including currently parsed "
            "`Decimal(12, 2)`, do not create accepted precision/scale semantics",
            "no Decimal precision/scale carrier, propagation, validation, SQL "
            "precision guarantee, native DB metadata, JSON/API exposure, or "
            "public contract",
            "no Decimal literal syntax, Decimal multiplication/division "
            "expansion, mixed Decimal promotion expansion, casts, "
            "Money/Currency primitive, or semantic annotation syntax",
            "Slice 7 is complete as operator and comparison matrix contract, "
            "static audit, and status work only",
            "current comparison behavior is generic known-child typing",
            "not a final pair-specific semantic compatibility guarantee",
            "no Text concatenation",
            "no Date/Timestamp-specific comparison matrix",
            "no UUID comparison, cast, literal, storage, DDL, wider SQL, or "
            "public API behavior",
            "Bytes and Json remain deferred/unsupported behavior built-ins",
            "`EffectiveNullability.UNKNOWN`, `ValueTypeKind.UNKNOWN`, and SQL "
            "three-valued logic `UNKNOWN` remain distinct",
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
