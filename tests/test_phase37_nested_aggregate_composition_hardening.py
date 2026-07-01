from __future__ import annotations

import subprocess
from fnmatch import fnmatchcase
from pathlib import Path

import pytest

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
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze

REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE36_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
)
COUNT_EXPRESSION_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-expression-mvp-decision-v1.md"
)
COUNT_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md"
)
MIN_MAX_SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"
AGGREGATES_SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
RELATION_SCHEMAS_SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/relation_schemas.py"
GROUP_BY_SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/group_by.py"
PHASE25_SATISFYING_TEST_PATH = REPO_ROOT / "tests/test_phase25_satisfying_semantics.py"
PHASE27_GROUPED_ORDER_TEST_PATH = (
    REPO_ROOT / "tests/test_phase27_grouped_order_semantics.py"
)
PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE31_DIAGNOSTIC_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_diagnostic_cli_json_stability.py"
)

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md",
    "src",
    "grammar",
    "src/pietto/generated",
    "fixtures",
    "tests/fixtures",
    "tests/_static_audit_helpers.py",
    "scripts",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
)

IN_PROGRESS_PHASE37_STATIC_AUDIT_PATTERNS = (
    "docs/spec/phase37-*.md",
    "tests/test_phase37_*.py",
)

SOURCE_PREFIX = (
    "shape Order:\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    customer_id: Text\n"
    "    status: Text not null\n"
    "    region: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def _phase37_plan() -> str:
    return _normalized(PHASE37_PLAN_PATH)


def _combined_boundary_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PHASE37_PLAN_PATH,
            FREEZE_SPEC_PATH,
            DEFERRED_REGISTER_PATH,
            PHASE36_PLAN_PATH,
            COUNT_EXPRESSION_SPEC_PATH,
            COUNT_DISTINCT_SPEC_PATH,
            MIN_MAX_SPEC_PATH,
            PHASE31_MATRIX_TEST_PATH,
        )
    )


def _errors(source: str) -> list[str]:
    parsed = parse_source(source, path="phase37-slice6-hardening.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    result = analyze(parsed.ast)
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _aggregate_projection(projection: str) -> str:
    return (
        SOURCE_PREFIX + "table aggregate_hardening:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
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


def _is_in_progress_phase37_static_audit_path(path: str) -> bool:
    return any(
        fnmatchcase(path, pattern)
        for pattern in IN_PROGRESS_PHASE37_STATIC_AUDIT_PATTERNS
    )


@pytest.mark.parametrize(
    "projection",
    [
        "value = count(count())",
        "value = sum(avg(amount))",
        "value = avg(sum(amount))",
        "value = min(max(amount))",
        "value = max(min(amount))",
        "value = count_distinct(lower(avg(status)))",
    ],
)
def test_nested_aggregates_remain_rejected_with_existing_diagnostic(
    projection: str,
) -> None:
    assert _errors(_aggregate_projection(projection)) == ["PIE-S2311"]


@pytest.mark.parametrize(
    "projection",
    [
        "value = sum(amount) + 1",
        "value = count(amount) + 1",
        "value = count_distinct(customer_id) + 1",
        "value = min(amount) + 1",
        "value = lower(min(amount))",
    ],
)
def test_aggregate_projection_composition_remains_rejected(
    projection: str,
) -> None:
    assert _errors(_aggregate_projection(projection)) == ["PIE-S2310"]


def test_invalid_aggregate_contexts_keep_existing_diagnostics() -> None:
    where_source = (
        SOURCE_PREFIX + "table invalid_where:\n"
        "    from orders\n"
        "    where sum(amount) > 0\n"
        "    select:\n"
        "        amount\n"
    )
    satisfying_source = (
        SOURCE_PREFIX + "table invalid_satisfying:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount)\n"
        "    satisfying:\n"
        "        sum(amount) > 0\n"
    )
    grouped_order_source = (
        SOURCE_PREFIX + "table invalid_grouped_order:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount)\n"
        "    order by:\n"
        "        sum(amount)\n"
    )

    assert _errors(where_source) == ["PIE-S2308"]
    assert _errors(satisfying_source) == ["PIE-S2308"]
    assert _errors(grouped_order_source) == ["PIE-S2321"]


@pytest.mark.parametrize(
    "projection",
    [
        "count()",
        "sum(amount)",
        "avg(amount)",
        "count_distinct(customer_id)",
        "min(amount)",
        "max(amount)",
    ],
)
def test_direct_aggregate_projections_remain_alias_required(
    projection: str,
) -> None:
    assert _errors(_aggregate_projection(projection)) == ["PIE-S2313"]


@pytest.mark.parametrize(
    "projection",
    [
        "value = count(1)",
        "value = count_distinct(amount + tax)",
        "value = min(amount + tax)",
        "value = max(amount + tax)",
    ],
)
def test_phase37_expression_widening_candidates_remain_deferred(
    projection: str,
) -> None:
    assert _errors(_aggregate_projection(projection)) == ["PIE-S2315"]


def test_slice6_hardening_authorizes_no_behavior_or_surface_expansion() -> None:
    plan = _phase37_plan()
    boundary_evidence = _combined_boundary_evidence()
    implementation_evidence = " ".join(
        _read(path)
        for path in (
            AGGREGATES_SOURCE_PATH,
            RELATION_SCHEMAS_SOURCE_PATH,
            GROUP_BY_SOURCE_PATH,
            PHASE25_SATISFYING_TEST_PATH,
            PHASE27_GROUPED_ORDER_TEST_PATH,
        )
    )
    combined = f"{plan} {boundary_evidence} {implementation_evidence}"

    for required in (
        "| 6 | Nested Aggregate And Composition Hardening |",
        "nested aggregates",
        "aggregate projection composition",
        "Current Phase 25 `satisfying:` behavior is frozen",
        "Current Phase 27 grouped selected-output `order by` behavior is frozen",
        "nested_aggregate_diagnostic",
        "deferred_composition_diagnostic",
        "PIE-S2311",
        "PIE-S2310",
        "PIE-S2313",
        "PIE-S2308",
        "PIE-S2321",
        "does not implement `count(expression)`",
        "does not implement broad `count_distinct(expression)`",
        "does not implement `min(expression)` or `max(expression)`",
    ):
        assert required in combined, required

    for prohibited in (
        "Slice 6 implements nested aggregates",
        "Slice 6 implements aggregate projection composition",
        "Slice 6 widens aggregate expression surfaces",
        "Slice 6 adds new accepted syntax",
        "Slice 6 changes diagnostic behavior",
    ):
        assert prohibited not in combined, prohibited


def test_deferred_and_prohibited_phase37_surfaces_remain_locked() -> None:
    boundary_evidence = _combined_boundary_evidence()

    for required in (
        "`count(expression)`",
        "broad `count_distinct(expression)`",
        "`min(expression)` / `max(expression)`",
        "aggregate filters",
        "window functions",
        "generic `DISTINCT` syntax",
        "generic aggregate modifiers",
        "aggregate over projection aliases",
        "relationship/fanout-safe aggregates",
        "No new aggregate functions, modifiers, filters, window functions",
        "`count(distinct field)`",
        "runtime/database execution",
        "public MySQL API expansion",
    ):
        assert required in boundary_evidence, required


def test_public_output_schema_and_release_surfaces_remain_unchanged() -> None:
    boundary_evidence = _combined_boundary_evidence()
    diagnostic_evidence = _read(PHASE31_DIAGNOSTIC_TEST_PATH)
    combined = f"{boundary_evidence} {diagnostic_evidence}"

    for required in (
        "no source/compiler behavior change",
        "grammar",
        "generated ANTLR files",
        "IR behavior",
        "SQL lowering",
        "CLI behavior",
        "JSON v1",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "no package/workflow/release metadata change",
        "no tag/release/publish/upload/signing/attestation",
        "package version remains `0.1.0`",
    ):
        assert required in combined, required

    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_phase36_type_boundaries_still_constrain_aggregate_hardening() -> None:
    boundary_evidence = _combined_boundary_evidence()

    for required in (
        "Decimal precision-scale carrier deferred with exact prerequisites",
        "UUID remains `limited_frozen` with no behavior expansion",
        "Enum remains metadata/readiness except `count(Enum field)` fails closed with `PIE-S2314`",
        "DateTime / Time / Interval remain deferred",
        "Any / Bytes / Json behavior surfaces remain unchanged and deferred",
        "type alias behavior is preserved",
        "domain refinement remains deferred",
        "Currency/Money remain deferred",
        "native DB metadata remains deferred",
    ):
        assert required in boundary_evidence, required


def test_forbidden_surfaces_are_not_modified_or_untracked() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)
    status_output = _git_status_for(FORBIDDEN_DIFF_PATHS)

    assert _non_slice3_repair_diff_paths(diff_output) == set()
    assert _non_slice3_repair_status_paths(status_output) == set()


def test_only_phase37_static_audit_files_are_changed_or_untracked() -> None:
    status_lines = _git_status()
    changed_paths = {line[3:] for line in status_lines}
    forbidden_paths = sorted(
        path
        for path in changed_paths
        if not _is_in_progress_phase37_static_audit_path(path)
    )

    assert set(forbidden_paths) <= ALLOWED_SLICE3_CHANGED_PATHS
