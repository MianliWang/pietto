from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-29-v02-stabilization-boundary.md"
SPEC_PATH = REPO_ROOT / "docs/spec/v02-stabilization-boundary-v1.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_phase29_slice1_artifacts_exist_and_record_status() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 29 Slice 1 is complete as candidate decision, v0.2 boundary "
        "contract, and static audit work only",
        "Trusted Phase 28 baseline",
        "HEAD: `6f8f30421250ce8ffffb89e64ce5c5d9dc885f35`",
        "Phase 28 Numeric / Aggregate Refinement II is complete",
        "Slice 1: Candidate Decision And v0.2 Boundary Contract",
        "Status: complete as candidate decision, v0.2 boundary contract, and "
        "static audit work only",
    ):
        assert required in plan

    for required in (
        "Phase 29 Slice 1 is complete as a candidate decision, boundary "
        "contract, and static audit slice only",
        "This contract defines the planned v0.2 stabilization boundary",
        "v0.2 is defined as a stable single-file typed SQL authoring compiler boundary",
    ):
        assert required in spec


def test_phase29_candidate_decision_selects_stabilization_and_rejects_prior_direction() -> (
    None
):
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 29 selects **v0.2 Stabilization Boundary And Deferred Register**",
        "Explainable Compiler Audit Readiness",
        "Rejected for Phase 29 because v0.2 needs stabilization first",
        "Numeric / Aggregate Refinement III",
        "Rejected; v0.2 freezes aggregate expansion except bug fixes",
        "Project / Multi-file Readiness II",
        "Relationship / JOIN Readiness",
        "CLI / JSON / API hardening implementation",
        "v0.2 needs stabilization first",
    ):
        assert required in plan


def test_v02_single_file_compiler_boundary_is_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    cli_json_contract = _normalized(REPO_ROOT / "docs/spec/cli-json-v1.md")
    sql_api = _read(REPO_ROOT / "src/pietto/sql/__init__.py")

    for required in (
        "one input Pietto file",
        "parser and semantic diagnostics",
        "immutable Semantic IR",
        "explicit PostgreSQL and private MySQL SQL generation",
        "current CLI `check` and `emit-sql` forms",
        "JSON v1 single-file machine-readable output",
        "SQL generation only",
    ):
        assert required in plan

    for required in (
        "single-file Pietto source compiler",
        "diagnostic-first and fail-closed",
        "SQL generation only",
        "JSON v1 remains the single-file machine-readable contract",
        "The public Python SQL API remains PostgreSQL-only",
        "The MySQL emitter remains private to explicit CLI dispatch",
    ):
        assert required in spec

    assert "JSON schema version 1 remains exclusively single-file" in cli_json_contract
    assert '"emit_postgres_sql",' in sql_api
    assert "emit_mysql_sql" not in sql_api


def test_aggregate_surface_freeze_is_directionally_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 19 through Phase 28 aggregate surface for v0.2 except bug fixes",
        "`count()`",
        "direct-field `sum(field)` and `avg(field)`",
        "`min(field)` and `max(field)`",
        "`count(field)`",
        "`count_distinct(field)`",
        "direct-field Decimal aggregate support",
        "grouped `satisfying:` result predicates",
        "selected aggregate expression arguments from Phase 26",
        "grouped result ordering over selected outputs from Phase 27",
        "Int/Float literal leaves in selected `sum(...)` and `avg(...)`",
    ):
        assert required in plan

    for required in (
        "freezes aggregate expansion after Phase 28 except for bug fixes",
        "new aggregate functions",
        "generic distinct syntax or aggregate modifiers",
        "aggregate filters",
        "window functions",
        "`count(expression)`",
        "`min(expression)` and `max(expression)`",
        "broad `count_distinct(...)` expression widening",
        "Decimal literal aggregate arguments",
        "Decimal multiplication, division, mixed promotion, and precision/scale",
    ):
        assert required in spec


def test_type_system_gap_matrix_and_repo_facts_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    model = _read(REPO_ROOT / "src/pietto/semantic/model.py")
    catalog = _read(REPO_ROOT / "src/pietto/semantic/catalog.py")
    expressions = _read(REPO_ROOT / "src/pietto/semantic/expressions.py")

    for required in (
        "built-in scalar names are cataloged as strings",
        "`ResolvedType` carries only `name`, `kind`, and optional `definition`",
        "`ValueType` carries a resolved type, effective nullability, and "
        "known/unknown status",
        "no canonical scalar type registry object exists",
        "no Decimal precision/scale carrier exists",
        "`Date` and `Timestamp` exist as built-in names",
        "`UUID` and enums exist at syntax/metadata levels",
    ):
        assert required in plan
        assert required in spec

    assert "class ResolvedType:" in model
    assert "name: str" in model
    assert "kind: TypeKind" in model
    assert "definition: Node | None = None" in model
    assert "class ValueType:" in model
    assert "resolved_type: ResolvedType" in model
    assert "nullability: EffectiveNullability" in model
    assert '"Date"' in catalog
    assert '"Timestamp"' in catalog
    assert '"UUID"' in catalog
    assert '"Decimal"' in catalog
    assert "def _binary_arithmetic_result_type(" in expressions


def test_deferred_register_shape_and_hard_non_goals_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Slice 2 will add the full deferred feature register",
        "aggregate expansion",
        "numeric expression expansion",
        "DateTime, timezone, Time, and Interval",
        "UUID",
        "Enum",
        "Decimal precision and scale",
        "native database type metadata",
        "database pull and schema introspection",
        "Prisma bridge",
        "project and multi-file behavior",
        "relationship and JOIN",
        "relationship cardinality, grain, and fanout diagnostics",
        "semantic and domain annotations",
        "explain and audit output",
        "LSP and playground",
        "runtime and database execution",
        "Arrow and dataframe integration",
    ):
        assert required in plan

    for required in (
        "source implementation changes",
        "grammar, generated ANTLR, AST, or parser changes",
        "semantic implementation changes",
        "IR implementation or IR model changes",
        "SQL backend or SQL lowering changes",
        "CLI behavior, command, option, help, or exit-code changes",
        "JSON v1 changes or JSON v2 implementation",
        "public MySQL API expansion",
        "aggregate feature expansion",
        "project or multi-file implementation",
        "relationship or JOIN implementation",
        "semantic annotation syntax",
        "DateTime, Time, timezone, Interval, Currency, or Money primitives",
        "database pull, schema introspection, SQL execution, connector execution",
        "Prisma bridge",
        "explain or audit output",
        "LSP, playground, web UI, Arrow, or dataframe integration",
    ):
        assert required in spec


def test_six_slice_plan_and_validation_commands_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Slice 1: Candidate Decision And v0.2 Boundary Contract",
        "Slice 2: Deferred Feature Register",
        "Slice 3: Aggregate Surface Freeze",
        "Slice 4: Core Type System Gap Matrix",
        "Slice 5: v0.2 Exit Criteria And Validation Strategy",
        "Slice 6: Completion Audit And Status Lock",
        "uv run pytest tests/test_phase29_v02_stabilization_candidate_decision.py",
        "uv run python scripts/validate.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/package_smoke.py",
        "Plan Phase 29 v0.2 stabilization boundary",
        "Document v0.2 deferred feature register",
        "Freeze v0.2 aggregate surface",
        "Audit v0.2 core type system gaps",
        "Define v0.2 validation strategy",
        "Complete Phase 29 v0.2 stabilization audit",
    ):
        assert required in plan


def test_phase30_through_phase32_mainline_is_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 30 Core Type System Stabilization I",
        "Candidate Decision And Type-System Contract",
        "Canonical Scalar Type Registry",
        "Nullability Propagation Contract",
        "Bool And Predicate Semantics",
        "Date / Timestamp Formalization",
        "Decimal Precision / Scale Contract",
        "Operator And Comparison Matrix",
        "Phase 31 Core Type System Stabilization II And Dialect Matrix Hardening",
        "Aggregate Result Matrix Hardening",
        "Numeric Promotion And Decimal Boundary Tests",
        "Date / Timestamp SQL Lowering Compatibility Audit",
        "UUID / Enum Readiness Or Narrow MVP Decision",
        "Diagnostic And CLI/JSON Type Output Hardening",
        "Phase 32 v0.2 Single-file Stable Completion Audit",
        "v0.2 Candidate Release Contract",
        "Language Surface Freeze Audit",
        "CLI / JSON / Public API Stability Audit",
        "Examples / Golden / Documentation Completion",
        "Full Validation And Package Smoke Audit",
        "v0.2 Status Lock",
    ):
        assert required in plan
    assert "Phase 30 Core Type System Stabilization I" in spec
    assert "Phase 31 Core Type System Stabilization II" in spec
    assert "Phase 32 v0.2 Single-file Stable Completion Audit" in spec


def test_status_docs_record_phase29_slice1_without_broadening_scope() -> None:
    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 29 v0.2 Stabilization Boundary",
            "Slice 1 is complete",
            "stable single-file typed SQL authoring compiler",
            "Phase 19 through Phase 28 aggregate surface",
            "except bug fixes",
            "Phase 30 Core Type System Stabilization I",
            "no source implementation, grammar, generated, CLI/JSON/API, IR, "
            "SQL, aggregate semantic, runtime/database, schema introspection, "
            "project/multi-file, public MySQL API, or relationship/JOIN "
            "behavior changes",
        ):
            assert required in status_doc
        for forbidden in (
            "Phase 29 implements JSON v2",
            "Phase 29 implements relationship/JOIN",
            "Phase 29 implements project mode",
            "Phase 29 implements schema introspection",
            "Phase 29 expands aggregate syntax",
            "Phase 29 changes public `emit_mysql_sql`",
        ):
            assert forbidden not in status_doc
