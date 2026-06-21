from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-30-core-type-system-stabilization-i.md"
SPEC_PATH = REPO_ROOT / "docs/spec/core-type-system-stabilization-contract-v1.md"

PHASE29_BOUNDARY_SPEC_PATH = REPO_ROOT / "docs/spec/v02-stabilization-boundary-v1.md"
PHASE29_REGISTER_SPEC_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE29_AGGREGATE_FREEZE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
)
PHASE29_TYPE_GAP_SPEC_PATH = (
    REPO_ROOT / "docs/spec/v02-core-type-system-gap-matrix-v1.md"
)
PHASE29_EXIT_CRITERIA_SPEC_PATH = (
    REPO_ROOT / "docs/spec/v02-exit-criteria-validation-strategy-v1.md"
)

MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"

PHASE30_ARTIFACTS = (
    "docs/plan/phase-30-core-type-system-stabilization-i.md",
    "docs/spec/core-type-system-stabilization-contract-v1.md",
    "docs/spec/canonical-scalar-type-registry-v1.md",
    "docs/spec/nullability-propagation-contract-v1.md",
    "docs/spec/bool-predicate-semantics-contract-v1.md",
    "docs/spec/date-timestamp-formalization-contract-v1.md",
    "docs/spec/decimal-precision-scale-contract-v1.md",
    "docs/spec/operator-comparison-matrix-contract-v1.md",
    "tests/test_phase30_candidate_decision.py",
    "tests/test_phase30_canonical_scalar_type_registry.py",
    "tests/test_phase30_nullability_propagation_contract.py",
    "tests/test_phase30_bool_predicate_semantics_contract.py",
    "tests/test_phase30_date_timestamp_formalization_contract.py",
    "tests/test_phase30_decimal_precision_scale_contract.py",
    "tests/test_phase30_operator_comparison_matrix_contract.py",
    "tests/test_phase30_completion_audit.py",
)

PHASE30_SLICES = (
    "Candidate Decision And Type-System Contract",
    "Canonical Scalar Type Registry",
    "Nullability Propagation Contract",
    "Bool And Predicate Semantics",
    "Date / Timestamp Formalization",
    "Decimal Precision / Scale Contract",
    "Operator And Comparison Matrix",
    "Completion Audit And Status Lock",
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

PHASE30_NON_GOALS = (
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
    "release tags, release artifacts, publishing, upload, signing, or attestation",
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


def test_phase30_slice1_artifacts_and_trusted_baseline_are_locked() -> None:
    for relative_path in PHASE30_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 30 Slice 1 is complete as candidate decision, type-system "
        "contract, static audit, and status work only",
        "HEAD: `92cdf6010c6f55524023f214a0e1173ea9492240`",
        "final Phase 29 commit: `Complete Phase 29 v0.2 stabilization audit`",
        "CI run: `27884233974 success`",
        "v0.2 is not complete yet",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in plan
        assert required in spec


def test_phase30_candidate_decision_selects_core_type_system_stabilization() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 30 selects **Core Type System Stabilization I**",
        "| Candidate | Fit | Risk | Decision |",
        "Phase 30 docs/spec/static-audit first",
        "Chosen for Slice 1",
        "Narrow scalar registry implementation now",
        "Rejected for Slice 1",
        "Broad type-system behavior implementation",
        "Aggregate or numeric expansion continuation",
        "Rejected; Phase 29 freezes aggregate expansion for v0.2 except bug fixes",
        "Project, JOIN, runtime, introspection, JSON v2, or public MySQL API",
        "Rejected by the v0.2 single-file compiler boundary",
        "The chosen Slice 1 direction is contract-first",
    ):
        assert required in plan

    assert "Phase 30 selects **Core Type System Stabilization I**" in spec
    assert "The selected Slice 1 approach is contract-first" in spec


def test_phase30_master_plan_and_later_slice_approval_boundary_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for step in PHASE30_SLICES:
        assert step in plan
        assert step in spec

    for required in (
        "Phase 30 Slice 2 is complete as canonical scalar type registry "
        "contract, static audit, and status work only",
        "Phase 30 Slice 3 is complete as nullability propagation contract, "
        "static audit, and status work only",
        "Phase 30 Slice 4 is complete as Bool and predicate semantics "
        "contract, static audit, and status work only",
        "Phase 30 Slice 5 is complete as Date / Timestamp formalization "
        "contract, static audit, and status work only",
        "Phase 30 Slice 6 is complete as Decimal precision / scale contract, "
        "static audit, and status work only",
        "Phase 30 Slice 7 is complete as operator and comparison matrix "
        "contract, static audit, and status work only",
        "Phase 30 Slice 8 is complete as completion audit and status lock work only",
        "Phase 30 Core Type System Stabilization I is complete as "
        "docs/spec/static-audit/status work only",
        "v0.2 is not complete yet",
        "Phase 31 Core Type System Stabilization II And Dialect Matrix "
        "Hardening is the next mainline",
    ):
        assert required in plan

    assert (
        "Phase 30 Slice 2 is complete as canonical scalar type registry "
        "contract, static audit, and status work only"
    ) in spec
    assert (
        "Phase 30 Slice 3 is complete as nullability propagation contract, "
        "static audit, and status work only"
    ) in spec
    assert (
        "Phase 30 Slice 4 is complete as Bool and predicate semantics "
        "contract, static audit, and status work only"
    ) in spec
    assert (
        "Phase 30 Slice 5 is complete as Date / Timestamp formalization "
        "contract, static audit, and status work only"
    ) in spec
    assert (
        "Phase 30 Slice 6 is complete as Decimal precision / scale contract, "
        "static audit, and status work only"
    ) in spec
    assert (
        "Phase 30 Slice 7 is complete as operator and comparison matrix "
        "contract, static audit, and status work only"
    ) in spec
    assert "Slice 8 is complete as completion audit" in spec
    assert "Phase 30 is complete as docs/spec/static-audit/status work only" in spec
    assert "v0.2 is not complete" in spec
    assert "Phase 31 and Phase 32 remain required before v0.2 stable completion" in (
        spec
    )


def test_phase30_contract_is_grounded_in_phase29_handoff_and_repo_facts() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    boundary = _normalized(PHASE29_BOUNDARY_SPEC_PATH)
    register = _normalized(PHASE29_REGISTER_SPEC_PATH)
    aggregate_freeze = _normalized(PHASE29_AGGREGATE_FREEZE_SPEC_PATH)
    type_gap = _normalized(PHASE29_TYPE_GAP_SPEC_PATH)
    exit_criteria = _normalized(PHASE29_EXIT_CRITERIA_SPEC_PATH)
    model = _read(MODEL_PATH)
    catalog = _read(CATALOG_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    aggregates = _read(AGGREGATES_PATH)

    for required in (
        "`docs/spec/v02-stabilization-boundary-v1.md`",
        "`docs/spec/v02-deferred-feature-register-v1.md`",
        "`docs/spec/v02-aggregate-surface-freeze-v1.md`",
        "`docs/spec/v02-core-type-system-gap-matrix-v1.md`",
        "`docs/spec/v02-exit-criteria-validation-strategy-v1.md`",
        "current built-in scalar names are stored as strings in `BUILTIN_TYPE_NAMES`",
        "`ResolvedType` stores only `name`, `kind`, and optional `definition`",
        "`ValueType` stores resolved type, effective nullability, and "
        "known/unknown status",
        "no canonical scalar registry object exists",
        "no Decimal precision/scale carrier exists",
        "`ValueTypeKind.UNKNOWN` records an unknown value type and remains "
        "distinct from `EffectiveNullability.UNKNOWN`",
        "SQL three-valued logic `UNKNOWN` is a runtime predicate truth value",
        "`UUID` is a current built-in name with limited/frozen identifier-scalar "
        "status for existing accepted behavior such as direct-field "
        "`count_distinct(UUID)`",
        "broader UUID behavior remains deferred",
        "enums remain syntax/metadata-level or readiness concerns",
    ):
        assert required in plan

    for builtin_name in CURRENT_BUILTIN_NAMES:
        assert f'"{builtin_name}"' in catalog
        assert f"`{builtin_name}`" in spec

    for required in (
        "v0.2 is defined as a stable single-file typed SQL authoring compiler boundary",
        "Phase 30 Core Type System Stabilization I",
    ):
        assert required in boundary

    assert "Phase 30/31 stabilization only if explicitly approved" in register
    assert (
        "For v0.2, the Phase 19 through Phase 28 aggregate surface is frozen "
        "except for bug fixes and audit-only clarifications"
    ) in aggregate_freeze
    assert "Phase 30 Handoff" in type_gap
    assert "Phase 30 prerequisites" in exit_criteria

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
    assert '"Enum"' not in catalog

    for required in (
        'if expression.operator == "/":',
        "return _UNKNOWN_VALUE_TYPE",
        'if expression.operator in {"and", "or"}:',
        'if expression.operator == "%":',
        'if expression.operator in {"+", "-", "*"}:',
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
    ):
        assert required in aggregates


def test_phase30_non_goals_and_status_docs_preserve_v02_boundary() -> None:
    plan_and_spec = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for required in PHASE30_NON_GOALS:
        assert required in plan_and_spec

    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 30 Core Type System Stabilization I",
            "Slice 2 is complete as canonical scalar type registry contract, "
            "static audit, and status work only",
            "Slice 3 is complete as nullability propagation contract, static "
            "audit, and status work only",
            "Slice 4 is complete as Bool and predicate semantics contract, "
            "static audit, and status work only",
            "Known Bool predicate acceptance remains a compile-time type-level fact",
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
            "v0.2 is not complete",
            "Phase 31 v0.2 Hardening And Stable Completion is the current mainline",
            "Phase 31 Slice 8 is the future v0.2 Stable Completion Audit And "
            "Status Lock",
            "Phase 31 completion may lock v0.2 stable if all criteria pass",
            "Phase 32 is post-v0.2 Semantic Explain And Metadata Output MVP",
        ):
            assert required in status_doc

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
        ):
            assert forbidden not in status_doc


def test_slice1_validation_commands_and_forbidden_surfaces_are_documented() -> None:
    plan = _normalized(PLAN_PATH)

    for command in (
        "uv run pytest tests/test_phase30_candidate_decision.py",
        "uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py "
        "tests/test_phase29_v02_exit_criteria_validation_strategy.py "
        "tests/test_phase29_completion_audit.py",
        "uv run pytest tests/test_phase17_core_scalar_expression_semantics.py "
        "tests/test_phase26_numeric_scalar_expression_semantics.py "
        "tests/test_phase26_decimal_scalar_expression_semantics.py "
        "tests/test_semantic_expressions.py tests/test_semantic_where.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
        "uv run python scripts/validate.py",
        "git diff --check",
        "git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock "
        ".github Makefile",
    ):
        assert command in plan

    for forbidden in (
        "Slice 1 implements a scalar registry",
        "Slice 1 changes semantic behavior",
        "Slice 1 changes SQL lowering",
        "Slice 1 changes CLI output",
        "Slice 1 changes JSON v1",
        "Slice 1 changes aggregate behavior",
        "Slice 1 starts Slice 2",
    ):
        assert forbidden not in plan
