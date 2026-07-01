from __future__ import annotations

import subprocess
import tomllib
from fnmatch import fnmatchcase
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    ALLOWED_SLICE3_CHANGED_PATHS,
    _non_slice3_repair_diff_paths,
    _non_slice3_repair_status_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md"
)
PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
COUNT_EXPRESSION_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-expression-mvp-decision-v1.md"
)
COUNT_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md"
)
MIN_MAX_SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"
ANY_BYTES_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/any-bytes-json-support-posture-v1.md"
ENUM_SPEC_PATH = REPO_ROOT / "docs/spec/enum-support-resolution-v1.md"
UUID_SPEC_PATH = REPO_ROOT / "docs/spec/uuid-support-completion-v1.md"
SCALAR_MATRIX_SPEC_PATH = REPO_ROOT / "docs/spec/expanded-scalar-operator-matrix-v1.md"
DECIMAL_CARRIER_SPEC_PATH = (
    REPO_ROOT / "docs/spec/decimal-precision-scale-carrier-mvp-decision-v1.md"
)

PHASE23_COUNT_TEST_PATH = REPO_ROOT / "tests/test_phase23_count_field_semantics.py"
PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE36_ANY_BYTES_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_any_bytes_json_support_posture.py"
)
PHASE36_ENUM_TEST_PATH = REPO_ROOT / "tests/test_phase36_enum_support_resolution.py"
PHASE36_UUID_TEST_PATH = REPO_ROOT / "tests/test_phase36_uuid_support_completion.py"
PHASE36_DATETIME_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_datetime_time_interval_boundary.py"
)
PHASE36_DECIMAL_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py"
)
PHASE36_SCALAR_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_expanded_scalar_operator_matrix.py"
)
PHASE37_CURRENT_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_current_aggregate_matrix.py"
)
PHASE37_GROUPED_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_grouped_aggregate_interaction_hardening.py"
)
SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
SEMANTIC_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "src",
    "grammar",
    "src/pietto/generated",
    "fixtures",
    "tests/fixtures",
    "scripts",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
)

ALLOWED_SLICE1_CHANGED_PATHS = {
    "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md",
    "tests/test_phase38_candidate_decision.py",
}

IN_PROGRESS_PHASE38_STATIC_AUDIT_PATTERNS = (
    "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md",
    "tests/test_phase38_candidate_decision.py",
)


def _plan() -> str:
    return _normalized(PLAN_PATH)


def _combined_aggregate_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PLAN_PATH,
            PHASE37_PLAN_PATH,
            FREEZE_SPEC_PATH,
            COUNT_EXPRESSION_SPEC_PATH,
            COUNT_DISTINCT_SPEC_PATH,
            MIN_MAX_SPEC_PATH,
            PHASE23_COUNT_TEST_PATH,
            PHASE31_MATRIX_TEST_PATH,
            PHASE37_CURRENT_MATRIX_TEST_PATH,
            PHASE37_GROUPED_TEST_PATH,
            SEMANTIC_AGGREGATES_PATH,
        )
    )


def _combined_type_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PLAN_PATH,
            ANY_BYTES_JSON_SPEC_PATH,
            ENUM_SPEC_PATH,
            UUID_SPEC_PATH,
            SCALAR_MATRIX_SPEC_PATH,
            DECIMAL_CARRIER_SPEC_PATH,
            PHASE36_ANY_BYTES_JSON_TEST_PATH,
            PHASE36_ENUM_TEST_PATH,
            PHASE36_UUID_TEST_PATH,
            PHASE36_DATETIME_TEST_PATH,
            PHASE36_DECIMAL_TEST_PATH,
            PHASE36_SCALAR_MATRIX_TEST_PATH,
            SEMANTIC_AGGREGATES_PATH,
            SEMANTIC_EXPRESSIONS_PATH,
        )
    )


def _git_status() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return [line for line in result.stdout.splitlines() if line]


def _git_status_for(paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def _is_in_progress_phase38_static_audit_path(path: str) -> bool:
    return any(
        fnmatchcase(path, pattern)
        for pattern in IN_PROGRESS_PHASE38_STATIC_AUDIT_PATTERNS
    )


def test_phase38_slice1_plan_exists_and_records_trusted_handoff() -> None:
    assert PLAN_PATH.is_file()
    plan = _plan()

    for required in (
        "Phase 38 Slice 1 is Aggregate Semantics And Type Capability Consolidation Candidate Decision",
        "docs/plan/static-audit/tests-only",
        "implements no behavior change",
        "baseline HEAD: `d2957b773066ea009828fde079ebca5c8e6e2cbb`",
        "baseline branch: `main`",
        "baseline commit: `Complete Phase 37 aggregate surface audit`",
        "latest completed phase: Phase 37 Post-v0.2 Aggregate Surface Expansion MVP",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation is authorized by Slice 1",
    ):
        assert required in plan, required


def test_slice1_candidate_decision_sections_are_present() -> None:
    plan = _plan()

    for required in (
        "## Candidate Decision",
        "## Repo-Derived Aggregate Inventory",
        "## Exact `count(field)` Current Posture",
        "## Type Capability Matrix",
        "## Count Family Future Semantics",
        "## Any / Json / Bytes / Enum / UUID Boundary",
        "## Distinct, Collation, Ordering, And Decimal Readiness",
        "## Binding / Filtered Aggregate / Post-Aggregate Layer Roadmap",
        "## Phase 38 Slice Sequence",
        "## Slice 1 Public Surface Constraints",
        "## Validation Plan And Gate 2 Allowlist",
        "Aggregate semantics and type capability consolidation",
    ):
        assert required in plan, required


def test_current_aggregate_inventory_is_evidence_backed() -> None:
    evidence = _combined_aggregate_evidence()

    for required in (
        "`count()`",
        "Accepted as SQL `COUNT(*)`; result is `Int not null`",
        "`count(field)` / `count(source.field)`",
        "direct or supported qualified fields",
        "`count_distinct(field)` / `count_distinct(source.field)`",
        "`Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`",
        "`count_distinct(lower/trim Text chain)`",
        "exactly one `Text` field leaf",
        "`sum(field)` / `sum(source.field)`",
        "`avg(field)` / `avg(source.field)`",
        "`sum(...)` / `avg(...)` bounded numeric expressions",
        "`min(field)` / `max(field)`",
        "direct `Int`, `Float`, `Decimal`, `Date`, and `Timestamp`",
        "grouped aggregate projections",
        "`satisfying:`",
        "grouped result `order by:`",
        "Current Phase 25 `satisfying:` behavior is frozen",
        "Current Phase 27 grouped selected-output `order by` behavior is frozen",
    ):
        assert required in evidence, required

    for source_evidence in (
        "def is_supported_count_argument",
        "def is_supported_count_distinct_argument",
        "def is_supported_numeric_argument",
        "def is_supported_extrema_argument",
        "def _is_supported_sum_avg_numeric_expression_shape",
    ):
        assert source_evidence in _read(SEMANTIC_AGGREGATES_PATH), source_evidence


def test_count_field_type_posture_is_exact() -> None:
    evidence = _combined_type_evidence()

    for required in (
        "`count(Any field)` | Rejected with `PIE-S2314`",
        "`count(Json field)` | Accepted and SQL-emitting",
        "`count(Bytes field)` | Accepted and SQL-emitting",
        "`count(Enum field)` | Rejected with `PIE-S2314`",
        "no longer reaches backend `PIE-B1000`",
        "`count(UUID field)` | Accepted",
        "the resolved type kind must not be `ENUM` or `UNKNOWN`",
        "must not be builtin `Any`",
        "value_type.resolved_type.kind not in",
        "TypeKind.ENUM",
        'not _is_builtin(value_type, "Any")',
        "test_bytes_json_direct_count_remains_accepted_and_sql_emitting",
        "test_count_enum_field_fails_semantic_validation_with_pie_s2314",
        "test_count_field_boundary_types_are_locked_with_enum_fail_closed",
    ):
        assert required in evidence, required


def test_capability_matrix_covers_boundary_types() -> None:
    plan = _plan()

    for required in (
        "| `Any` | current generic field/projection | generic `is null` expression exists, not Any-specific | no, `PIE-S2314` | no | no | no | no |",
        "| `Json` | current generic field/projection | generic `is null` expression exists, not Json-specific | yes, direct `count(Json field)` | no | no | no | no |",
        "| `Bytes` | current generic field/projection | generic `is null` expression exists, not Bytes-specific | yes, direct `count(Bytes field)` | no | no | no | no |",
        "| Enum | metadata/projection readiness, not stable SQL scalar | generic expression machinery exists, no Enum-specific contract | no, `PIE-S2314` | no | no | no | no |",
        "| `UUID` | current `limited_frozen` field/projection | generic `is null` expression exists, not UUID-specific | yes, direct `count(UUID field)` | no | no current `min/max`; ordering remains risky/deferred | yes, direct `count_distinct(UUID field)` | no |",
        "returns `Bool NON_NULL` for `IsNullExpr`",
        "test_is_null_expression_maps_to_non_null_bool",
        "countable, null-checkable, lowerable, numeric, arithmetic-capable, orderable",
        "distinct-compatible, text-transform-capable",
    ):
        assert required in plan, required


def test_type_system_inventory_details_are_preserved() -> None:
    evidence = _combined_type_evidence()

    for required in (
        "`DateTime` / `Time` / `Interval` remain unsupported/deferred",
        "fail semantic type resolution with `PIE-S2002`",
        "Decimal precision-scale carrier work remains deferred",
        "`Decimal(12, 2)` generic `TypeExpr.arguments` do not create accepted precision/scale semantics",
        "`Float` has current direct `count_distinct(Float)` and direct `min/max(Float)` support",
        "No Float-specific caveat is currently documented",
        "`Text` has current direct `count_distinct(Text)` and lower/trim Text-chain support",
        "Text collation, Unicode normalization, locale-sensitive folding",
        "backend-specific equality rules remain outside current behavior",
        "`UUID` remains `limited_frozen`",
        "Enum remains `metadata_only`",
        "Json path operators, structural typing, object/array schema validation",
        "Bytes binary literals, encoding, functions, operators, native storage, or native metadata",
    ):
        assert required in evidence, required


def test_count_family_and_future_readiness_are_planning_only() -> None:
    plan = _plan()

    for required in (
        "`count()` remains all-row count and SQL `COUNT(*)`",
        "`count(field)` remains SQL non-null field-value count",
        "`count(expression)` remains a future candidate",
        "`count(constant)` / `count(1)` remains a future compatibility candidate",
        "`count_if(predicate)` remains a future candidate",
        "FALSE/NULL/UNKNOWN exclusion",
        "Slice 1 does not implement any of these future count-family behaviors",
        "Projection aliases remain output naming",
        "likely through a later `let:` or `with:` style contract",
        "Filtered aggregates remain deferred",
        "Aggregate projection composition such as `sum(amount) + 1`",
        "relationship/JOIN and grain/fanout semantics",
    ):
        assert required in plan, required


def test_phase38_slice_sequence_is_locked() -> None:
    plan = _plan()

    for required in (
        "| 1 | Candidate Decision And Scope Inventory | docs/plan/static-audit/tests-only; no behavior change |",
        "| 2 | Count Family Semantics Contract | docs/spec/static-audit first; no initial behavior change |",
        "| 3 | Type Capability Matrix Contract | docs/spec/static-audit first; no behavior change |",
        "| 4 | Any / Json / Bytes / Enum / UUID Capability Boundary | docs/spec/static-audit first; no initial behavior change |",
        "| 5 | Distinct / Collation / Ordering Readiness | docs/spec/tests first; no behavior change |",
        "| 6 | Binding / Aggregate Filter / Post-Aggregate Roadmap | docs/spec/static-audit first; no behavior change |",
        "| 7 | Completion Audit And Public Surface Lock | audit/status; no behavior change unless a prior slice separately approved implementation |",
        "every implementation slice requires a separate Gate 1 and Gate 2 authorization",
    ):
        assert required in plan, required


def test_slice1_authorizes_no_behavior_or_public_surface_expansion() -> None:
    plan = _plan()

    for required in (
        "Slice 1 authorizes no source/compiler behavior change",
        "source implementation",
        "grammar change",
        "generated ANTLR change",
        "parser or AST behavior change",
        "semantic behavior change",
        "IR behavior change",
        "SQL behavior change",
        "CLI behavior change",
        "JSON v1 change",
        "Project JSON v2 change",
        "Semantic Metadata Artifact v1 schema or output change",
        "diagnostic envelope change",
        "SQL golden byte change",
        "fixture or golden change",
        "script change",
        "workflow change",
        "package metadata change",
        "lockfile change",
        "package version change",
    ):
        assert required in plan, required

    for forbidden in (
        "Slice 1 implements `count(expression)`",
        "Slice 1 implements `count_if(predicate)`",
        "Slice 1 changes SQL behavior",
        "Slice 1 changes CLI JSON v1",
        "Slice 1 changes Project JSON v2",
        "Slice 1 changes Semantic Metadata Artifact v1",
        "Slice 1 starts CI",
        "Slice 1 publishes",
    ):
        assert forbidden not in plan, forbidden


def test_public_outputs_package_and_release_surfaces_remain_unchanged() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    plan = _plan()

    for required in (
        "CLI text output unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "generated parser inventory unchanged",
        "package version remains `0.1.0`",
        "no package/workflow/release metadata change",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in plan, required

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)


def test_gate2_allowlist_and_forbidden_surfaces_are_documented() -> None:
    plan = _plan()

    for required in (
        "Approved Slice 1 Gate 2 file allowlist:",
        "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md",
        "tests/test_phase38_candidate_decision.py",
        "`README.md`",
        "`AGENTS.md`",
        "`docs/spec/pietto-v0.9.md`",
        "`src/`",
        "`grammar/`",
        "`src/pietto/generated/`",
        "`fixtures/`",
        "`tests/fixtures/`",
        "`scripts/`",
        "`.github/workflows/`",
        "`pyproject.toml`",
        "`uv.lock`",
        "`/tmp/phase38-slice1-gate2-evidence.txt`",
        "no-index diff for untracked new files",
        "untracked whitespace check",
        "Gate 2 must not stage, commit, push, start or poll CI",
    ):
        assert required in plan, required


def test_forbidden_surfaces_are_not_modified_or_untracked() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)
    status_output = _git_status_for(FORBIDDEN_DIFF_PATHS)

    assert _non_slice3_repair_diff_paths(diff_output) == set()
    assert _non_slice3_repair_status_paths(status_output) == set()


def test_only_phase38_slice1_static_audit_files_are_changed_or_untracked() -> None:
    status_lines = _git_status()
    changed_paths = {line[3:] for line in status_lines}
    forbidden_paths = sorted(
        path
        for path in changed_paths
        if not _is_in_progress_phase38_static_audit_path(path)
    )

    assert set(forbidden_paths) <= ALLOWED_SLICE3_CHANGED_PATHS
    assert changed_paths <= ALLOWED_SLICE3_CHANGED_PATHS
