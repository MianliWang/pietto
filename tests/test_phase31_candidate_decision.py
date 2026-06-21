from __future__ import annotations

from pathlib import Path

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-31-v02-hardening-and-stable-completion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/v02-hardening-and-stable-completion-v1.md"

OLD_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-31-core-type-system-stabilization-ii-dialect-matrix-hardening.md"
)
OLD_SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/core-type-system-stabilization-ii-dialect-matrix-hardening-v1.md"
)

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
PHASE30_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/core-type-system-stabilization-contract-v1.md"
)
PHASE30_REGISTRY_PATH = REPO_ROOT / "docs/spec/canonical-scalar-type-registry-v1.md"
PHASE30_NULLABILITY_PATH = (
    REPO_ROOT / "docs/spec/nullability-propagation-contract-v1.md"
)
PHASE30_BOOL_PATH = REPO_ROOT / "docs/spec/bool-predicate-semantics-contract-v1.md"
PHASE30_DATE_PATH = REPO_ROOT / "docs/spec/date-timestamp-formalization-contract-v1.md"
PHASE30_DECIMAL_PATH = REPO_ROOT / "docs/spec/decimal-precision-scale-contract-v1.md"
PHASE30_OPERATOR_PATH = (
    REPO_ROOT / "docs/spec/operator-comparison-matrix-contract-v1.md"
)
CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
SQL_API_PATH = REPO_ROOT / "src/pietto/sql/__init__.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"

PHASE31_ARTIFACTS = (
    "docs/plan/phase-31-v02-hardening-and-stable-completion.md",
    "docs/spec/v02-hardening-and-stable-completion-v1.md",
    "tests/test_phase31_candidate_decision.py",
)

PHASE31_SLICES = (
    "Candidate Decision And Phase 30 Carry-forward Audit",
    "Aggregate Result Matrix Hardening",
    "Numeric Promotion And Decimal Boundary Tests",
    "Date / Timestamp SQL Compatibility Audit",
    "UUID / Enum Readiness Decision",
    "Diagnostic / CLI / JSON Stability Hardening",
    "Docs / Examples / Package / CI v0.2 Readiness Audit",
    "v0.2 Stable Completion Audit And Status Lock",
)

POST_V02_ROADMAP = (
    "Phase 32: Semantic Explain And Metadata Output MVP",
    "Phase 33: Project And Multi-file MVP",
    "Phase 34: Semantic Graph / ERD / AI Metadata Export MVP",
    "Phase 35: Relationship Grain And Narrow JOIN MVP",
)

FORBIDDEN_BOUNDARY_PHRASES = (
    "v0.2 is complete",
    "v0.2 stable completion is locked",
    "Phase 31 is complete",
    "Phase 31 implementation is complete",
    "Phase 31 implementation has started",
    "Phase 32 is complete",
    "JSON v2 is implemented",
    "public `emit_mysql_sql`",
    "Decimal precision/scale carrier is implemented",
    "UUID behavior is implemented",
    "Enum behavior is implemented",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_phase31_slice1_artifacts_and_preferred_paths_are_locked() -> None:
    for relative_path in PHASE31_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    assert not OLD_PLAN_PATH.exists()
    assert not OLD_SPEC_PATH.exists()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 31 Slice 1 is complete as candidate decision, Phase 30 "
        "carry-forward audit, static audit, and status work only",
        "HEAD: `182ed41e7dc7dd7e616cfb1be5cfbb4a7fcdae58`",
        "final Phase 30 commit: `Complete Phase 30 core type system "
        "stabilization audit`",
        "CI run: `27891119809 success`",
        "v0.2 is not complete yet at Phase 31 Slice 1",
        "Phase 31 Slice 8 is the future v0.2 Stable Completion Audit And Status Lock",
        "Phase 31 completion may lock v0.2 stable if all criteria pass",
        "Phase 32 is post-v0.2 work",
    ):
        assert required in plan
        assert required in spec


def test_phase31_candidate_decision_selects_merged_direction() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 31 selects **v0.2 Hardening And Stable Completion**",
        "| Candidate | Fit | Risk | Decision |",
        "v0.2 Hardening And Stable Completion",
        "Chosen for Slice 1",
        "Keep Phase 31 as Core Type System Stabilization II and require "
        "Phase 32 for completion",
        "Rejected; the v0.2 hardening and stable completion audit are now "
        "merged into Phase 31",
        "Continue docs-only contracts for the whole phase",
        "Rejected; Phase 30 already locked the contracts",
        "Aggregate/Numeric Expansion III",
        "Rejected; it violates the v0.2 aggregate freeze except separately "
        "approved bug fixes",
        "Project/JOIN/runtime/schema introspection/JSON v2/public MySQL API",
        "Rejected by the v0.2 single-file compiler boundary",
        "UUID/Enum behavior MVP now",
        "Rejected for Slice 1",
        "docs/spec/static-audit/status only",
    ):
        assert required in plan

    for required in (
        "This contract selects Phase 31 v0.2 Hardening And Stable Completion",
        "This merged direction turns the remaining pre-v0.2 hardening and the "
        "v0.2 stable completion audit into one phase",
        "replaces the earlier split where Phase 31 was Core Type System "
        "Stabilization II And Dialect Matrix Hardening",
    ):
        assert required in spec


def test_phase31_master_plan_and_slice_boundaries_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for slice_title in PHASE31_SLICES:
        assert slice_title in plan
        assert slice_title in spec

    for required in (
        "Slice 1 does not implement Slice 2",
        "It does not authorize behavior fixes or production changes",
        "compiler behavior may change only after separate explicit approval",
        "Slices 2 through 8 are planned only",
        "Do not add UUID or Enum behavior without separate explicit approval",
        "This slice must not imply JSON v1 schema expansion",
        "no package version bump, release tag, publishing",
        "Slice 8 is the only Phase 31 slice that may declare v0.2 stable completion",
        "Slice 1 does not declare v0.2 complete",
    ):
        assert required in plan

    for required in (
        "Slice 1 is docs/spec/static-audit/status only",
        "Later Phase 31 hardening may mean tests, specs, and static audit only",
        "No new JSON fields, JSON v2, public MySQL API expansion, CLI behavior "
        "change, or diagnostic behavior change may happen without later "
        "explicit approval",
        "v0.2 Stable Completion Audit And Status Lock is the future Phase 31 Slice 8",
        "Slice 1 does not declare v0.2 complete",
    ):
        assert required in spec


def test_phase31_post_v02_roadmap_is_locked_without_phase32_start() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in POST_V02_ROADMAP:
        assert required in plan
        assert required in spec

    for required in (
        "Phase 31 Slice 1 does not start Phase 32 or implement any post-v0.2 work",
        "Do not stage real content, commit, or push without a separate Gate 3 approval",
        "Do not start Slice 2 or Phase 32 without separate approval",
    ):
        assert required in plan

    assert "Phase 32 is post-v0.2 work" in spec
    assert "Phase 31 Slice 1 does not start Phase 32" in spec


def test_phase29_and_phase30_carry_forward_contracts_remain_active() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    register = _normalized(PHASE29_REGISTER_SPEC_PATH)
    aggregate_freeze = _normalized(PHASE29_AGGREGATE_FREEZE_SPEC_PATH)
    type_gap = _normalized(PHASE29_TYPE_GAP_SPEC_PATH)
    exit_criteria = _normalized(PHASE29_EXIT_CRITERIA_SPEC_PATH)
    phase30_contracts = " ".join(
        _normalized(path)
        for path in (
            PHASE30_CONTRACT_PATH,
            PHASE30_REGISTRY_PATH,
            PHASE30_NULLABILITY_PATH,
            PHASE30_BOOL_PATH,
            PHASE30_DATE_PATH,
            PHASE30_DECIMAL_PATH,
            PHASE30_OPERATOR_PATH,
        )
    )

    for required in (
        "Phase 29 deferred register remains active",
        "Phase 29 aggregate freeze remains active",
        "Phase 30 type-system contracts are carried forward",
        "`docs/spec/v02-deferred-feature-register-v1.md`",
        "`docs/spec/v02-aggregate-surface-freeze-v1.md`",
        "`docs/spec/core-type-system-stabilization-contract-v1.md`",
        "`docs/spec/operator-comparison-matrix-contract-v1.md`",
    ):
        assert required in plan
        assert required in spec

    assert "It does not authorize implementation" in register
    assert "For v0.2, the Phase 19 through Phase 28 aggregate surface is frozen" in (
        aggregate_freeze
    )
    assert "Phase 31 should carry forward aggregate result matrix hardening" in (
        type_gap
    )
    assert "Phase 31 prerequisites" in exit_criteria
    assert "Phase 30 is complete as docs/spec/static-audit/status work only" in (
        phase30_contracts
    )


def test_phase31_slice1_is_grounded_in_current_repo_facts() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    catalog = _read(CATALOG_PATH)
    model = _read(MODEL_PATH)
    aggregates = _read(AGGREGATES_PATH)
    sql_api_source = _read(SQL_API_PATH)
    cli_json_source = _read(CLI_JSON_PATH)

    for required in (
        "built-in scalar names remain string entries in `BUILTIN_TYPE_NAMES`",
        "no canonical scalar registry object exists",
        "no Decimal precision/scale carrier exists",
        "`ResolvedType` stores",
        "`ValueType` stores",
        "aggregate result behavior remains owned by existing semantic helpers",
        "PostgreSQL remains the only public Python SQL API",
        "MySQL remains private to explicit CLI dispatch",
        "JSON v1 remains the current single-file machine-readable output "
        "contract and has no type-output fields",
    ):
        assert required in plan
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

    assert "class ResolvedType:" in model
    assert "class ValueType:" in model
    assert "def semantic_aggregate_result_value_type(" in aggregates
    assert "def aggregate_result_value_type(" in aggregates
    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert "emit_mysql_sql" not in sql_api_source
    assert '"types"' not in cli_json_source
    assert '"type_output"' not in cli_json_source


def test_phase31_slice1_hard_non_goals_are_locked() -> None:
    combined = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for required in (
        "source implementation changes",
        "grammar changes",
        "generated file changes",
        "fixtures or goldens changes",
        "public API changes",
        "CLI behavior",
        "JSON v1 schema changes",
        "new JSON fields",
        "JSON v2 implementation",
        "IR implementation or IR model changes",
        "SQL backend or SQL lowering changes",
        "semantic implementation or semantic behavior changes",
        "aggregate expansion or aggregate behavior changes",
        "diagnostic behavior changes",
        "predicate behavior changes",
        "type-system behavior changes",
        "public MySQL API expansion",
        "project or multi-file implementation",
        "schema introspection",
        "runtime/database behavior",
        "relationship or JOIN implementation",
        "DateTime, Time, Interval, or timezone semantics",
        "Money or Currency primitives",
        "semantic annotation syntax",
        "Decimal precision/scale carrier",
        "UUID or Enum behavior implementation",
        "Phase 32 implementation",
        "v0.2 completion declaration in Slice 1",
    ):
        assert required in combined

    for forbidden in FORBIDDEN_BOUNDARY_PHRASES:
        assert forbidden not in combined


def test_phase31_status_docs_record_slice1_without_v02_completion() -> None:
    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 31 v0.2 Hardening And Stable Completion",
            "Phase 31 Slice 1 is complete as candidate decision, Phase 30 "
            "carry-forward audit, static audit, and status work only",
            "Phase 29 deferred register remains active",
            "Phase 29 aggregate freeze remains active",
            "Phase 30 type-system contracts are carried forward",
            "v0.2 is not complete yet at Phase 31 Slice 1",
            "Phase 31 Slice 8 is the future v0.2 Stable Completion Audit And "
            "Status Lock",
            "Phase 31 completion may lock v0.2 stable if all criteria pass",
            "Phase 32 is post-v0.2 Semantic Explain And Metadata Output MVP",
            "no Phase 31 behavior implementation in Slice 1",
            "no Phase 32 implementation in Slice 1",
            "JSON v1 schema expansion",
            "public MySQL API",
            "UUID or Enum behavior implementation",
        ):
            assert required in status_doc

        assert "Phase 32 remains required before v0.2 stable completion" not in (
            status_doc
        )
        for forbidden in FORBIDDEN_BOUNDARY_PHRASES:
            assert forbidden not in status_doc


def test_phase31_slice1_does_not_touch_forbidden_repo_surfaces() -> None:
    for relative_path in (
        "src",
        "grammar",
        "tests/fixtures",
        "scripts",
        ".github",
    ):
        root = REPO_ROOT / relative_path
        assert root.exists(), relative_path
        for path in root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                assert "Phase 31" not in path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

    assert (
        not (REPO_ROOT / "docs/spec/project-cli-json-v2.md")
        .read_text(encoding="utf-8")
        .startswith("# v0.2 Hardening And Stable Completion")
    )
