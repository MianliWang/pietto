from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-30-core-type-system-stabilization-i.md"
SPEC_PATH = REPO_ROOT / "docs/spec/date-timestamp-formalization-contract-v1.md"
CORE_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/core-type-system-stabilization-contract-v1.md"
)
REGISTRY_CONTRACT_PATH = REPO_ROOT / "docs/spec/canonical-scalar-type-registry-v1.md"
NULLABILITY_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/nullability-propagation-contract-v1.md"
)
BOOL_CONTRACT_PATH = REPO_ROOT / "docs/spec/bool-predicate-semantics-contract-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
PREDICATE_CHECKS_PATH = REPO_ROOT / "src/pietto/semantic/predicate_checks.py"
SATISFYING_PATH = REPO_ROOT / "src/pietto/semantic/satisfying.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"

PHASE22_MIN_MAX_TEST_PATH = REPO_ROOT / "tests/test_phase22_min_max_semantics.py"
PHASE22_SQL_TEST_PATH = REPO_ROOT / "tests/test_phase22_min_max_sql.py"
PHASE17_EXPRESSION_TEST_PATH = (
    REPO_ROOT / "tests/test_phase17_core_scalar_expression_semantics.py"
)
PHASE25_SATISFYING_TEST_PATH = REPO_ROOT / "tests/test_phase25_satisfying_semantics.py"

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
    "DateTime primitive or alias",
    "TimestampTZ or Instant primitive",
    "Time or Interval primitive",
    "timezone semantics",
    "temporal arithmetic",
    "date/time functions, extraction, or truncation",
    "Date/Timestamp literal syntax",
    "casts between Date and Timestamp",
    "timestamp precision modeling",
    "native database type metadata or physical storage guarantees",
    "Decimal precision/scale syntax semantics, carrier, propagation, validation,",
    "SQL precision guarantees, JSON/API exposure, native database metadata, or",
    "public contract",
    "Decimal literal syntax, Decimal multiplication or division expansion, mixed",
    "Decimal promotion expansion, or casts",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice5_artifacts_baseline_and_status_are_locked() -> None:
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    core_contract = _normalized(CORE_CONTRACT_PATH)
    registry_contract = _normalized(REGISTRY_CONTRACT_PATH)
    nullability_contract = _normalized(NULLABILITY_CONTRACT_PATH)
    bool_contract = _normalized(BOOL_CONTRACT_PATH)

    for required in (
        "Phase 30 Slice 5 is complete as Date / Timestamp formalization "
        "contract, static audit, and status work only",
        "HEAD: `2a47dfef6c5c0dd8302cdef5a1f253e52ecb1275`",
        "commit: `Document Bool and predicate semantics contract`",
        "CI run: `27887558604 success`",
        "v0.2 is not complete yet",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in plan
        assert required in spec

    assert "date-timestamp-formalization-contract-v1.md" in plan
    assert "date-timestamp-formalization-contract-v1.md" in core_contract
    assert "Slice 5 Date / Timestamp Formalization" in registry_contract
    assert "Slice 5 Date / Timestamp Formalization" in nullability_contract
    assert "Slice 5 Date / Timestamp Formalization" in bool_contract


def test_slice5_candidate_decision_is_docs_static_audit_status_only() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "| Candidate | Fit | Risk | Decision |",
        "Slice 5 docs/spec/static-audit/status only",
        "Chosen",
        "Tests-only hardening",
        "Rejected for Slice 5",
        "Minimal implementation artifact",
        "Rejected; no consumer needs a new temporal helper, registry object, "
        "type carrier, or dialect metadata object",
        "Broad behavior implementation",
        "Rejected; it could change semantic, diagnostic, predicate, IR, SQL, "
        "CLI, JSON, fixture, golden, aggregate, and public API behavior",
        "The selected Slice 5 direction is contract-first",
        "does not add temporal comparison rules",
        "temporal literal syntax",
        "casts",
        "dialect-specific temporal guarantees",
    ):
        assert required in spec

    for forbidden in (
        "Slice 5 implements Date/Timestamp behavior",
        "Slice 5 changes temporal comparison behavior",
        "Slice 5 changes SQL lowering",
        "Slice 5 adds DateTime",
        "Slice 5 adds temporal literals",
        "Slice 5 adds casts",
    ):
        assert forbidden not in spec


def test_date_timestamp_scalar_and_temporal_trait_facts_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    registry_contract = _normalized(REGISTRY_CONTRACT_PATH)
    catalog = _read(CATALOG_PATH)

    for required in (
        "`Date` is a current built-in scalar name",
        "`Timestamp` is a current built-in scalar name",
        "`Timestamp` is the current canonical v0.2 spelling for date+time values",
        "does not model timezone semantics",
        "timestamp precision",
        "runtime timezone interpretation",
        "native database metadata",
        "physical storage guarantees",
        "does not introduce `DateTime` as a primitive or alias",
        "does not introduce `TimestampTZ`, `Instant`, `Time`, or `Interval`",
        "does not define Date or Timestamp literal syntax",
    ):
        assert required in spec

    for required in (
        "BUILTIN_TYPE_NAMES = frozenset(",
        '"Date"',
        '"Timestamp"',
    ):
        assert required in catalog

    for required in (
        "| temporal | `Date`, `Timestamp` |",
        "These traits are contract vocabulary only in Slice 2",
        "do not authorize new operators, comparisons, aggregate forms, SQL "
        "lowering behavior",
    ):
        assert required in registry_contract


def test_date_timestamp_extrema_aggregate_surface_remains_frozen() -> None:
    spec = _normalized(SPEC_PATH)
    aggregates = _read(AGGREGATES_PATH)
    min_max_tests = _read(PHASE22_MIN_MAX_TEST_PATH)

    for required in (
        "| `min(Date)` / `max(Date)` | `Date NULLABLE` |",
        "| `min(Timestamp)` / `max(Timestamp)` | `Timestamp NULLABLE` |",
        "The accepted source shape remains direct-field `min(field)` / `max(field)`",
        "supported single-input qualified direct-field `min(source.field)` / "
        "`max(source.field)`",
        "does not widen `min(expression)` / `max(expression)`",
        "does not add temporal aggregate functions",
        "does not change aggregate validation",
        "aggregate diagnostics",
        "aggregate IR",
        "aggregate SQL lowering",
        "fixtures",
        "goldens",
    ):
        assert required in spec

    for required in (
        "def is_supported_extrema_argument(value_type: ValueType) -> bool:",
        'for name in ("Int", "Float", "Decimal", "Date", "Timestamp")',
        "def semantic_aggregate_result_value_type(",
        "if function_name not in {MIN_AGGREGATE_NAME, MAX_AGGREGATE_NAME}:",
        "if argument_type is None or not is_supported_extrema_argument(argument_type):",
        "resolved_type=argument_type.resolved_type",
        "nullability=EffectiveNullability.NULLABLE",
    ):
        assert required in aggregates

    for required in (
        "test_no_group_min_max_accept_date_and_timestamp_arguments",
        "test_qualified_min_max_field_arguments_are_accepted",
        "test_grouped_min_max_projections_are_accepted",
        "first_order_date = min(order_date)",
        "latest_created_at = max(created_at)",
        "Date",
        "Timestamp",
        "EffectiveNullability.NULLABLE",
        "test_min_max_invalid_projection_shapes_use_existing_aggregate_diagnostics",
        "Aggregate function min requires a direct field argument; ",
        "expression arguments are deferred",
    ):
        assert required in min_max_tests


def test_postgres_and_mysql_extrema_sql_validation_remains_current_only() -> None:
    spec = _normalized(SPEC_PATH)
    postgres = _read(POSTGRES_EXPRESSIONS_PATH)
    mysql = _read(MYSQL_EXPRESSIONS_PATH)
    sql_tests = _read(PHASE22_SQL_TEST_PATH)

    for required in (
        "PostgreSQL/MySQL portability in Slice 5 means only current SQL "
        "generation compatibility",
        "already accepted Date/Timestamp direct-field extrema aggregate surface",
        "runtime timezone interpretation",
        "database introspection",
        "native temporal metadata",
        "physical storage guarantees",
        "casts between `Date` and `Timestamp`",
        "date extraction or truncation functions",
        "temporal arithmetic",
        "timestamp precision modeling",
        "dialect-specific temporal comparison guarantees",
    ):
        assert required in spec

    for source in (postgres, mysql):
        for required in (
            "_SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES = frozenset(",
            '{"Int", "Float", "Decimal", "Date", "Timestamp"}',
            "def _render_extrema_aggregate(",
            "supports only Int, ",
            "Decimal, Date, or Timestamp field arguments",
            "approved logical shape",
        ):
            assert required in source

    for required in (
        'MIN("orders"."order_date") AS "first_order_date"',
        'MAX("orders"."created_at") AS "latest_created_at"',
        "MIN(`orders`.`order_date`) AS `first_order_date`",
        "MAX(`orders`.`created_at`) AS `latest_created_at`",
        "latest_created_at",
    ):
        assert required in sql_tests


def test_current_comparison_posture_is_generic_not_temporal_specific() -> None:
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    phase17_tests = _read(PHASE17_EXPRESSION_TEST_PATH)

    for required in (
        "Current comparison handling is generic and not Date/Timestamp-specific",
        "Date/Timestamp comparisons are accepted only where current generic "
        "expression typing already accepts known typed operands and returns "
        "`Bool UNKNOWN`",
        "Current `between` handling likewise returns `Bool UNKNOWN` when all "
        "child value types are known",
        "`Bool UNKNOWN` is Pietto `EffectiveNullability.UNKNOWN`",
        "It is not SQL three-valued logic `UNKNOWN`",
        "does not define a Date/Timestamp-specific comparison compatibility matrix",
        "does not add temporal comparison rules",
        "does not add casts",
        "does not add temporal literal syntax",
        "does not add dialect-specific comparison guarantees",
        "Slice 7 owns the final operator and comparison matrix",
    ):
        assert required in spec

    for required in (
        "elif isinstance(expression, ComparisonExpr):",
        "expression.left",
        "expression.right",
        "_builtin_value_type(",
        '"Bool"',
        "EffectiveNullability.UNKNOWN",
        "def _between_value_type(",
        "if any(child_type.kind is ValueTypeKind.UNKNOWN for child_type in child_types):",
        "return _UNKNOWN_VALUE_TYPE",
        'return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)',
    ):
        assert required in expressions

    for required in (
        "test_boolean_binary_where_resolves_to_known_bool",
        "test_between_where_resolves_to_known_bool",
        "test_invalid_bool_binary_reports_s2105_at_full_span",
    ):
        assert required in phase17_tests


def test_predicate_boundary_is_only_existing_known_bool_typing() -> None:
    spec = _normalized(SPEC_PATH)
    bool_contract = _normalized(BOOL_CONTRACT_PATH)
    predicate_checks = _read(PREDICATE_CHECKS_PATH)
    satisfying = _read(SATISFYING_PATH)
    satisfying_tests = _read(PHASE25_SATISFYING_TEST_PATH)

    for required in (
        "Date/Timestamp values interact with row-level `where`, shape `check`, "
        "index `when`, and result-level `satisfying:` only through existing "
        "expression typing",
        "Known Bool predicate acceptance remains a compile-time type-level fact",
        "does not prove non-nullness",
        "does not evaluate runtime truth",
        "does not collapse SQL three-valued logic",
        "does not change predicate validation",
        "predicate diagnostics",
        "`satisfying:` result-predicate support",
        "SQL predicate rendering",
        "SQL three-valued logic lowering",
    ):
        assert required in spec

    for required in (
        "A known Bool predicate is accepted only as a compile-time type-level fact",
        "does not mean Pietto proves the predicate non-null",
        "does not mean the runtime predicate is true or false",
        "does not collapse SQL three-valued logic",
    ):
        assert required in bool_contract

    for required in (
        "Require known where, shape check, and index predicates to be Bool",
        'context="where clause"',
        'context = "shape check"',
        'context = "index predicate"',
        "if value_type is None or value_type.kind is ValueTypeKind.UNKNOWN:",
        "return None",
        'if value_type.resolved_type.name == "Bool":',
        'code="PIE-S2202"',
    ):
        assert required in predicate_checks

    for required in (
        "def _bool_predicate_diagnostic(",
        'code="PIE-S2202"',
        "Expected Bool expression in satisfying clause",
        "if value_type.kind is ValueTypeKind.UNKNOWN:",
        "continue",
    ):
        assert required in satisfying

    for required in (
        "test_grouped_satisfying_over_aggregate_alias_is_accepted",
        "test_non_bool_satisfying_predicate_reuses_predicate_diagnostic",
        "test_and_or_bool_composition_is_accepted",
        "test_invalid_and_or_operands_reuse_operator_diagnostic",
    ):
        assert required in satisfying_tests


def test_later_slice_handoff_and_hard_non_goals_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    core_contract = _normalized(CORE_CONTRACT_PATH)
    plan_and_specs = f"{plan} {spec} {core_contract}"

    for required in (
        "Slice 6 Decimal Precision / Scale Contract",
        "records current logical Decimal behavior and precision/scale deferral",
        "Slice 7 Operator And Comparison Matrix",
        "Slice 7 Operator And Comparison Matrix owns the full supported, "
        "rejected, and deferred matrix for temporal and non-temporal operators "
        "and comparisons",
        "Phase 31 may carry Date/Timestamp SQL compatibility hardening",
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


def test_status_docs_record_slice5_without_behavior_change() -> None:
    for relative_path in ("AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 30 Core Type System Stabilization I",
            "Slice 5 is complete as Date / Timestamp formalization contract, "
            "static audit, and status work only",
            "`Timestamp` is the current canonical v0.2 spelling for date+time values",
            "current generic comparison behavior only",
            "no `DateTime` primitive or alias",
            "no Date/Timestamp literal syntax",
            "no timezone semantics",
            "no temporal arithmetic, date/time functions, casts, timestamp "
            "precision modeling, native database type metadata, or runtime "
            "timezone interpretation",
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
            "not a final pair-specific semantic compatibility guarantee",
            "no Text concatenation",
            "no Date/Timestamp-specific comparison matrix",
            "no UUID comparison, cast, literal, storage, DDL, wider SQL, or "
            "public API behavior",
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
            "DateTime primitive is allowed",
            "DateTime alias is allowed",
            "TimestampTZ primitive is allowed",
            "Instant primitive is allowed",
            "Time primitive is allowed",
            "Interval primitive is allowed",
            "timezone semantics are implemented",
            "temporal arithmetic is implemented",
            "Date/Timestamp literals are implemented",
            "Date/Timestamp casts are implemented",
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
