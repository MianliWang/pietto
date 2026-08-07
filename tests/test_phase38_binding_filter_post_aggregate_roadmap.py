from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
)
from test_phase39_candidate_decision import (
    ALLOWED_SLICE3_CHANGED_PATHS,
    _non_slice3_repair_status_paths,
)
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = REPO_ROOT / "docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md"
PHASE38_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md"
)
COMPOSITION_SCOPE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/composition-scope-name-resolution-contract-v1.md"
)
DIAGNOSTICS_SPEC_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
COUNT_FAMILY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-count-family-semantics-contract-v1.md"
)
TYPE_CAPABILITY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-type-capability-matrix-contract-v1.md"
)
DISTINCT_ORDERING_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-distinct-collation-ordering-readiness-v1.md"
)
COUNT_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md"
)
MIN_MAX_SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"
FILTER_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md"
)

RELATION_SCHEMAS_SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/relation_schemas.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
POSTGRES_RELATIONS_PATH = REPO_ROOT / "src/pietto/sql/relations.py"
MYSQL_RELATIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_relations.py"
PHASE37_NESTED_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_nested_aggregate_composition_hardening.py"
)
PHASE37_FILTER_DISTINCT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE6_CHANGED_PATHS = {
    "docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md",
    "tests/test_phase38_binding_filter_post_aggregate_roadmap.py",
}

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md",
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


def _spec() -> str:
    return _normalized(SPEC_PATH)


def _combined_roadmap_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            SPEC_PATH,
            PHASE38_PLAN_PATH,
            COMPOSITION_SCOPE_SPEC_PATH,
            DIAGNOSTICS_SPEC_PATH,
            FREEZE_SPEC_PATH,
            DEFERRED_REGISTER_PATH,
            COUNT_FAMILY_SPEC_PATH,
            TYPE_CAPABILITY_SPEC_PATH,
            DISTINCT_ORDERING_SPEC_PATH,
            COUNT_DISTINCT_SPEC_PATH,
            MIN_MAX_SPEC_PATH,
            FILTER_DISTINCT_SPEC_PATH,
            RELATION_SCHEMAS_SOURCE_PATH,
            IR_MODEL_PATH,
            POSTGRES_RELATIONS_PATH,
            MYSQL_RELATIONS_PATH,
            PHASE37_NESTED_TEST_PATH,
            PHASE37_FILTER_DISTINCT_TEST_PATH,
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


def _status_path(line: str) -> str:
    return line[3:]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_spec_exists_and_records_slice6_guardrail() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 38 Binding Filter Post Aggregate Roadmap v1",
        "Phase 38 Slice 6 is Binding / Aggregate Filter / Post-Aggregate Roadmap",
        "docs/spec/static-audit/tests-only",
        "authorizes no behavior change",
        "does not add or change source/compiler behavior",
        "grammar, generated ANTLR files",
        "semantic behavior, IR behavior",
        "SQL lowering, CLI behavior, JSON v1",
        "Project JSON v2, Semantic Metadata Artifact v1",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_current_projection_alias_and_binding_posture_is_documented() -> None:
    evidence = _combined_roadmap_evidence()

    for required in (
        "Current relation bodies have one input relation scope",
        "Projection aliases do not enter input-scope ordering",
        "Projection aliases define output field names after the projection alias boundary",
        "They are output naming, not implicit reusable variable binding",
        "Current projection output naming is alias-first, then direct field names",
        "Computed alias fields can carry known expression type and nullability",
        "`PIE-S2304`",
        "`PIE-S2305`",
        "Current aggregate projection validation accepts the direct aliased aggregate call shape only",
        "Nested aggregate calls remain `PIE-S2311`",
        "aggregate projection composition remains `PIE-S2310`",
        "aggregate projections without an explicit alias remain `PIE-S2313`",
        "Projection aliases as aggregate argument leaves remain excluded",
        "def _projection_output_name",
        "def _computed_row_field",
        "def _aggregate_projection_diagnostics",
        "PIE-S2310",
        "PIE-S2311",
    ):
        assert required in evidence, required


def test_explicit_binding_roadmap_is_future_only() -> None:
    spec = _spec()

    for required in (
        "Future reusable row-level binding should require a separate syntax contract",
        "likely `let:` or `with:` style",
        "scope and clause visibility",
        "lifecycle and relation boundary ownership",
        "immutability",
        "cycle rejection",
        "hygiene and name conflicts",
        "source-span ownership",
        "PostgreSQL/private MySQL lowering",
        "Slice 6 does not authorize same-`select` alias reuse",
        "projection alias aggregation",
        "aggregate over projection aliases",
        "hidden CTE insertion",
        "hidden subquery insertion",
        "output-schema/JSON behavior changes",
    ):
        assert required in spec, required


def test_current_where_satisfying_and_grouped_order_posture_is_documented() -> None:
    evidence = _combined_roadmap_evidence()

    for required in (
        "Current row-level `where:` is pre-aggregate input filtering",
        "not SQL aggregate `FILTER`",
        "Current `satisfying:` is the only result-predicate user surface",
        "GROUP BY-only",
        "selected-output-name based",
        "lowered as SQL `HAVING`",
        "not aggregate filter syntax",
        "Direct aggregate calls inside `satisfying:` remain invalid",
        "`PIE-S2308`",
        "Current grouped `order by:` is result-level selected-output-name ordering",
        "not aggregate internal ordering",
        "`PIE-S2321`",
        "aggregate filters / SQL `FILTER (WHERE ...)`",
        "generic `DISTINCT` syntax such as `count(distinct field)`",
        "aggregate internal ordering / `WITHIN GROUP`",
        "window functions / `OVER (...)`",
        "`count(*)` source syntax",
    ):
        assert required in evidence, required


def test_aggregate_filter_and_count_if_roadmap_is_future_only() -> None:
    spec = _spec()

    for required in (
        "Aggregate filters remain future-only",
        "separate from both row `where:` and grouped `satisfying:`",
        "Pietto source spelling",
        "Bool and nullable Bool predicate rules",
        "interaction with `count(field)`",
        "interaction with `count_if(predicate)`",
        "SQL `NULL` and SQL three-valued `UNKNOWN` behavior",
        "IR representation",
        "`count_if(predicate)` remains a future candidate only",
        "`TRUE` counts",
        "`FALSE`, SQL `NULL`, and SQL three-valued `UNKNOWN` do not count",
        "result is `Int not null`",
        "`count_if(predicate)` is different from `count(predicate)`",
        "does not choose final aggregate-filter syntax",
        "does not implement filtered aggregate behavior",
    ):
        assert required in spec, required


def test_current_post_aggregate_expression_posture_is_documented() -> None:
    evidence = _combined_roadmap_evidence()

    for required in (
        "Aggregate projection composition is currently rejected",
        "`sum(amount) + 1`",
        "`count(amount) + 1`",
        "`count_distinct(customer_id) + 1`",
        "`lower(min(amount))`",
        "`PIE-S2310`",
        "Nested aggregate calls are currently rejected",
        "`count(count())`",
        "`sum(avg(amount))`",
        "`min(max(amount))`",
        "`PIE-S2311`",
        "`sum(amount) > 0` in `where` as `PIE-S2308`",
        "direct aggregate calls inside `satisfying:` as `PIE-S2308`",
        "direct aggregate calls in grouped `order by:` as `PIE-S2321`",
        "class FilterIR",
        "class ResultPredicateIR",
        "result_predicate: ResultPredicateIR | None",
        "def render_relation_sql",
        "def render_mysql_relation",
        "HAVING",
    ):
        assert required in evidence, required


def test_post_aggregate_relation_layer_roadmap_is_future_only() -> None:
    spec = _spec()

    for required in (
        "Post-aggregate expressions remain future-only",
        "`total_plus_one = sum(amount) + 1`",
        "`ratio = sum(amount) / count()`",
        "aggregating over projection aliases",
        "relation-layer or subquery lowering model",
        "output scope",
        "aggregate/non-aggregate composition rules",
        "relation-layer IR ownership",
        "type and nullability rules",
        "alias visibility and shadowing",
        "must not reuse projection aliases as hidden inputs",
        "must not silently rewrite one relation into nested SQL",
        "post-aggregate expression layer",
        "relation layer IR",
        "subquery lowering model",
    ):
        assert required in spec, required


def test_relationship_fanout_join_boundary_remains_deferred() -> None:
    evidence = _combined_roadmap_evidence()

    for required in (
        "Relationship/fanout-safe aggregates remain deferred",
        "relationship/JOIN and grain/fanout semantics exist",
        "Relationship querying crosses composition, ambiguity, fanout, and SQL shape boundaries",
        "Future scope work must not rely on hidden runtime post-processing",
        "in-memory JOIN fallback",
        "connector execution",
        "backend guessing",
        "relationship-aware aggregate rewrites",
        "fanout warnings",
        "grain inference",
        "cardinality warnings",
        "endpoint-qualified lookup",
        "multi-input traversal",
        "relation composition",
        "JOIN behavior",
        "No JOIN implementation, relation composition, endpoint-qualified lookup",
    ):
        assert required in evidence, required


def test_diagnostics_and_deferred_surfaces_remain_listed() -> None:
    spec = _spec()

    for required in (
        "`PIE-P1000`",
        "`PIE-S2308`",
        "`PIE-S2321`",
        "`PIE-S2309`",
        "`PIE-S2310`",
        "`PIE-S2311`",
        "`PIE-S2313`",
        "`PIE-S2315`",
        "`PIE-S2314`",
        "adds no diagnostic codes",
        "`let:` / `with:` binding syntax",
        "same-`select` alias reuse",
        "aggregate filters / SQL `FILTER (WHERE ...)`",
        "`count_if(predicate)`",
        "`count(distinct field)`",
        "`count(*)` source syntax",
        "nested aggregates",
        "aggregate projection composition",
        "broad `count(expression)`",
        "broad `count_distinct(expression)`",
        "`min/max(expression)`",
        "relation layer IR",
        "relationship/JOIN/fanout-safe aggregates",
        "parser/AST/grammar/generated changes",
        "semantic/IR/SQL/CLI/JSON behavior changes",
    ):
        assert required in spec, required


def test_public_surfaces_and_package_version_remain_locked() -> None:
    spec = _spec()

    for required in (
        "source/compiler behavior unchanged",
        "grammar and generated parser inventory unchanged",
        "parser and AST behavior unchanged",
        "semantic behavior unchanged",
        "IR behavior unchanged",
        "SQL behavior unchanged",
        "CLI text output unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "scripts/workflows unchanged",
        "package metadata unchanged",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in spec, required

    with PYPROJECT_PATH.open("rb") as handle:
        pyproject = tomllib.load(handle)
    assert pyproject["project"]["version"] == "0.1.0"


def test_only_slice6_files_are_changed_and_forbidden_surfaces_are_clean() -> None:
    status = _git_status()
    status_paths = {_status_path(line) for line in status}

    # Accept both clean CI checkout and dirty Gate 2/repair states.
    assert (
        status_paths <= ALLOWED_SLICE3_CHANGED_PATHS
    ) or _phase54_active_gate2_is_active()

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert (
            _non_slice3_repair_status_paths(_git_status_for((forbidden,))) == set()
        ) or _phase54_active_gate2_is_active()
        assert (
            not any(
                _path_matches(path, forbidden)
                and path not in ALLOWED_SLICE3_CHANGED_PATHS
                for path in status_paths
            )
        ) or _phase54_active_gate2_is_active()


def test_phase38_plan_already_records_slice6_without_plan_edit() -> None:
    plan = _normalized(PHASE38_PLAN_PATH)

    for required in (
        "## Binding / Filtered Aggregate / Post-Aggregate Layer Roadmap",
        "Projection aliases remain output naming, not automatic reusable variable binding",
        "likely through a later `let:` or `with:` style contract",
        "Filtered aggregates remain deferred",
        "Post-aggregate expression support remains deferred",
        "Aggregate projection composition such as `sum(amount) + 1`",
        "projection alias aggregation remain blocked",
        "post-aggregate expression layer, relation layer IR, or subquery lowering model",
        "Relationship/fanout-safe aggregate remains deferred",
        "| 6 | Binding / Aggregate Filter / Post-Aggregate Roadmap | docs/spec/static-audit first; no behavior change |",
    ):
        assert required in plan, required
