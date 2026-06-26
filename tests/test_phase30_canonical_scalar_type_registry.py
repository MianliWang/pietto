from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-30-core-type-system-stabilization-i.md"
SPEC_PATH = REPO_ROOT / "docs/spec/canonical-scalar-type-registry-v1.md"
CORE_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/core-type-system-stabilization-contract-v1.md"
)
CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
AGGREGATE_FREEZE_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
TYPE_GAP_PATH = REPO_ROOT / "docs/spec/v02-core-type-system-gap-matrix-v1.md"

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

CONCRETE_SCALAR_CORE = (
    "Bool",
    "Int",
    "Float",
    "Decimal",
    "Text",
    "Date",
    "Timestamp",
)

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
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice2_artifacts_baseline_and_status_are_locked() -> None:
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    core_contract = _normalized(CORE_CONTRACT_PATH)

    for required in (
        "Phase 30 Slice 2 is complete as canonical scalar type registry "
        "contract, static audit, and status work only",
        "HEAD: `374698aec9b9774f1df1c1c3aa7132159f7f65a0`",
        "commit: `Plan Phase 30 core type system stabilization`",
        "CI run: `27885002942 success`",
        "v0.2 is not complete yet",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in plan
        assert required in spec

    assert "canonical-scalar-type-registry-v1.md" in plan
    assert "canonical-scalar-type-registry-v1.md" in core_contract


def test_slice2_candidate_decision_is_docs_static_audit_only() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "| Candidate | Fit | Risk | Decision |",
        "Slice 2 docs/spec/static-audit/status only",
        "Chosen",
        "Minimal scalar registry implementation artifact",
        "Rejected for Slice 2",
        "Broad type-system behavior implementation",
        "Rejected",
        "The selected Slice 2 direction is contract-first",
        "documentation and static-audit contract only",
    ):
        assert required in spec

    for forbidden in (
        "Slice 2 implements a scalar registry object",
        "Slice 2 changes semantic behavior",
        "Slice 2 changes SQL lowering",
        "Slice 2 changes JSON behavior",
    ):
        assert forbidden not in spec


def test_current_builtin_names_and_concrete_core_are_grounded() -> None:
    spec = _normalized(SPEC_PATH)
    catalog = _read(CATALOG_PATH)

    assert "BUILTIN_TYPE_NAMES = frozenset(" in catalog
    for builtin_name in CURRENT_BUILTIN_NAMES:
        assert f'"{builtin_name}"' in catalog
        assert f"`{builtin_name}`" in spec

    assert "The v0.2 concrete scalar core is:" in spec
    for scalar_name in CONCRETE_SCALAR_CORE:
        assert f"`{scalar_name}`" in spec

    for required in (
        "`Any` is the boundary/top scalar classification",
        "`Bytes` and `Json` are deferred/unsupported behavior built-ins",
        "no scalar registry object, trait enum, registry API, or Decimal "
        "precision/scale carrier exists",
    ):
        assert required in spec


def test_uuid_is_limited_frozen_identifier_scalar_not_fully_deferred() -> None:
    spec = _normalized(SPEC_PATH)
    aggregates = _read(AGGREGATES_PATH)
    aggregate_freeze = _normalized(AGGREGATE_FREEZE_PATH)
    type_gap = _normalized(TYPE_GAP_PATH)

    count_distinct_function = aggregates[
        aggregates.index("def is_supported_count_distinct_argument") : aggregates.index(
            "def _is_field_only_numeric_shape"
        )
    ]

    for required in (
        "`UUID` is a limited/frozen identifier scalar",
        "`UUID` is a current built-in name",
        "direct-field `count_distinct(UUID)`",
        "`count_distinct(source.uuid_field)`",
        "broader UUID behavior remains deferred",
        "literals, casts, functions, storage semantics, DDL, general comparison "
        "guarantees, wider SQL behavior, dialect compatibility, and public API "
        "exposure",
        "Phase 31 must make the UUID readiness or narrow-MVP decision",
    ):
        assert required in spec

    for forbidden in (
        "`UUID` is a deferred/unsupported behavior built-in",
        "`UUID` has no accepted v0.2 behavior",
        "UUID literals are supported",
        "UUID casts are supported",
        "UUID functions are supported",
        "UUID DDL is supported",
    ):
        assert forbidden not in spec

    assert '"UUID"' in count_distinct_function
    assert "current direct-field" in aggregate_freeze
    assert (
        "`UUID` is a built-in name and is accepted by current "
        "`count_distinct(field)` direct-field support"
    ) in type_gap


def test_identifier_trait_label_does_not_imply_other_semantics() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "The `identifier` label is only a registry classification label",
        "It does not imply primary-key semantics",
        "foreign-key semantics",
        "relationship semantics",
        "cardinality",
        "grain",
        "row identity",
        "business ID validation",
        "general comparison behavior",
        "cast behavior",
        "SQL storage behavior",
        "public API behavior",
    ):
        assert required in spec


def test_enum_remains_non_builtin_semantic_type_kind() -> None:
    spec = _normalized(SPEC_PATH)
    catalog = _read(CATALOG_PATH)
    model = _read(MODEL_PATH)

    for required in (
        "`Enum` is a non-builtin semantic type kind",
        "`Enum` is not in `BUILTIN_TYPE_NAMES`",
        "enum/type-definition support and `TypeKind.ENUM`",
        "broader Enum SQL behavior remains deferred",
        "Slice 2 does not implement an Enum primitive",
        "Enum scalar registry entry",
        "Enum SQL lowering",
        "Enum DDL",
        "Enum runtime mapping",
        "Enum value validation changes",
    ):
        assert required in spec

    assert '"Enum"' not in catalog
    assert 'ENUM = "enum"' in model


def test_trait_vocabulary_is_contract_only_without_behavior_expansion() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "| Trait | Scalars |",
        "| numeric | `Int`, `Float`, `Decimal` |",
        "| exact numeric | `Int`, `Decimal` |",
        "| approximate numeric | `Float` |",
        "| text | `Text` |",
        "| boolean | `Bool` |",
        "| temporal | `Date`, `Timestamp` |",
        "| binary | `Bytes` |",
        "| json | `Json` |",
        "| identifier | `UUID` |",
        "| boundary/top | `Any` |",
        "These traits are contract vocabulary only in Slice 2",
        "They do not authorize new operators, comparisons, aggregate forms, "
        "SQL lowering behavior, diagnostics, JSON behavior, CLI behavior, "
        "public API behavior, type-system behavior, or runtime behavior",
    ):
        assert required in spec


def test_registry_facts_and_expression_value_facts_are_separated() -> None:
    spec = _normalized(SPEC_PATH)
    model = _read(MODEL_PATH)

    for required in (
        "Future scalar registry facts may include",
        "canonical scalar identity",
        "category or trait labels",
        "concrete-core, boundary, limited/frozen, or deferred status",
        "Expression value facts remain outside the registry",
        "`ResolvedType.name`",
        "`ResolvedType.kind`",
        "`ResolvedType.definition`",
        "`ValueType.resolved_type`",
        "`ValueType.nullability`",
        "`ValueType.kind`",
        "Slice 2 does not add carriers for Decimal precision/scale",
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
    ):
        assert required in model


def test_later_slice_handoff_and_non_goals_are_locked() -> None:
    plan_and_spec = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for required in (
        "Slice 3 Nullability Propagation Contract",
        "Slice 4 Bool And Predicate Semantics",
        "Slice 5 Date / Timestamp Formalization",
        "Slice 6 Decimal Precision / Scale Contract",
        "Slice 7 Operator And Comparison Matrix",
        "Slice 3 is complete as nullability propagation contract, static audit, "
        "and status work only",
        "Slice 4 is complete as Bool and predicate semantics contract, static "
        "audit, and status work only",
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
        assert required in plan_and_spec

    for required in PHASE30_HARD_NON_GOALS:
        assert required in plan_and_spec


def test_status_docs_record_slice2_without_v02_completion_or_behavior_change() -> None:
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
            "`UUID` is a limited/frozen identifier scalar only for existing "
            "frozen behavior such as direct-field `count_distinct(UUID)`",
            "broader UUID behavior remains deferred",
            "Enum remains a non-builtin semantic type kind",
            "`EffectiveNullability.UNKNOWN`, `ValueTypeKind.UNKNOWN`, and SQL "
            "three-valued logic `UNKNOWN` remain distinct",
            "Slice 8 is complete as completion audit and status lock work only",
            "Phase 30 is complete",
            "Phase 31 v0.2 Hardening And Stable Completion is complete",
            "Pietto v0.2 single-file stable complete",
            "Phase 31 Slice 8 complete",
            "Phase 32 remains post-v0.2 and has not started",
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
