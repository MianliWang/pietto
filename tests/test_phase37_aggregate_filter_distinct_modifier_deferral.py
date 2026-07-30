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
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md"
)
PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
COUNT_EXPRESSION_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-expression-mvp-decision-v1.md"
)
COUNT_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md"
)
MIN_MAX_SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"
NESTED_COMPOSITION_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_nested_aggregate_composition_hardening.py"
)
CURRENT_MATRIX_TEST_PATH = REPO_ROOT / "tests/test_phase37_current_aggregate_matrix.py"
PHASE29_FREEZE_TEST_PATH = (
    REPO_ROOT / "tests/test_phase29_v02_aggregate_surface_freeze.py"
)
PHASE25_SATISFYING_TEST_PATH = REPO_ROOT / "tests/test_phase25_satisfying_semantics.py"
PHASE25_SATISFYING_PARSER_TEST_PATH = (
    REPO_ROOT / "tests/test_phase25_satisfying_parser_ast.py"
)
PHASE27_GROUPED_ORDER_TEST_PATH = (
    REPO_ROOT / "tests/test_phase27_grouped_order_semantics.py"
)
PARSER_RELATIONS_TEST_PATH = REPO_ROOT / "tests/test_parser_relations.py"
DIAGNOSTIC_STABILITY_TEST_PATH = (
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


def _spec() -> str:
    return _normalized(SPEC_PATH)


def _boundary_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            SPEC_PATH,
            PHASE37_PLAN_PATH,
            FREEZE_SPEC_PATH,
            DEFERRED_REGISTER_PATH,
            COUNT_EXPRESSION_SPEC_PATH,
            COUNT_DISTINCT_SPEC_PATH,
            MIN_MAX_SPEC_PATH,
            NESTED_COMPOSITION_TEST_PATH,
            CURRENT_MATRIX_TEST_PATH,
            PHASE29_FREEZE_TEST_PATH,
        )
    )


def _parser_codes(source: str) -> list[str]:
    result = parse_source(source, path="phase37-slice7-deferral.pietto")
    return [diagnostic.code for diagnostic in result.diagnostics]


def _semantic_error_codes(source: str) -> list[str]:
    parsed = parse_source(source, path="phase37-slice7-deferral.pietto")
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
        SOURCE_PREFIX + "table aggregate_modifier_deferral:\n"
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


def test_phase37_slice7_spec_exists_and_has_required_sections() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 37 Aggregate Filter Distinct Modifier Deferral v1",
        "## Status",
        "## Current Accepted Distinct Aggregate Spelling",
        "## Current Row And Result Predicate Surfaces",
        "## Deferred And Prohibited Syntax",
        "## Existing Failure Posture",
        "## Public Surface Stability",
        "Phase 37 Slice 7 is `Aggregate Filter / DISTINCT / Modifier Syntax Deferral`",
        "docs/spec/static-audit plus parser/semantic behavior-audit tests only",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_slice7_authorizes_no_behavior_source_or_output_changes() -> None:
    spec = _spec()
    plan = _normalized(PHASE37_PLAN_PATH)

    for required in (
        "Slice 7 authorizes no behavior change",
        "does not change source/compiler behavior",
        "grammar",
        "generated ANTLR files",
        "parser behavior",
        "AST behavior",
        "semantic behavior",
        "IR behavior",
        "SQL lowering",
        "CLI behavior",
        "JSON v1",
        "Project JSON v2",
        "Semantic Metadata Artifact v1",
        "diagnostic envelope shape",
        "SQL golden bytes",
        "fixtures/goldens",
        "public status docs",
        "scripts",
        "workflows",
        "package metadata",
        "lockfiles",
        "package version",
        "release operations",
        "tags",
        "publish/upload",
        "signing",
        "attestation",
    ):
        assert required in spec, required

    assert (
        "| 7 | Aggregate Filter / DISTINCT / Modifier Syntax Deferral | "
        "docs/spec/static-audit; no behavior change |"
    ) in plan


def test_current_count_distinct_satisfying_and_order_boundaries_are_locked() -> None:
    evidence = " ".join(
        _normalized(path)
        for path in (
            SPEC_PATH,
            COUNT_DISTINCT_SPEC_PATH,
            FREEZE_SPEC_PATH,
            PHASE25_SATISFYING_TEST_PATH,
            PHASE25_SATISFYING_PARSER_TEST_PATH,
            PHASE27_GROUPED_ORDER_TEST_PATH,
            PARSER_RELATIONS_TEST_PATH,
        )
    )

    for required in (
        "The current accepted distinct aggregate spelling is `count_distinct(...)`",
        "Generic SQL-style `count(distinct field)` is not Pietto source syntax",
        "Current row-level `where:` is not aggregate `FILTER`",
        "`satisfying:` is GROUP BY-only result-level filtering lowered as `HAVING`",
        "Current `satisfying:` is the only result-predicate user surface",
        "having:",
        "Direct aggregate calls inside `satisfying:` remain invalid",
        "grouped `order by:` accepts bare selected output names",
        "Unsupported grouped ORDER BY item; expected a supported select output name",
        "window recent",
    ):
        assert required in evidence, required


@pytest.mark.parametrize(
    "projection",
    [
        "value = count(distinct customer_id)",
        "value = sum(amount) filter where amount > 0",
        "value = sum(amount) FILTER (WHERE amount > 0)",
        "value = sum(amount) over (region)",
        "value = sum(amount) within group (order by amount)",
        "value = count(*)",
    ],
)
def test_sql_like_aggregate_modifier_syntax_remains_parser_rejected(
    projection: str,
) -> None:
    codes = _parser_codes(_aggregate_projection(projection))

    assert "PIE-P1000" in codes


def test_semantic_context_and_modifier_like_argument_boundaries_are_locked() -> None:
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

    assert _semantic_error_codes(satisfying_source) == ["PIE-S2308"]
    assert _semantic_error_codes(grouped_order_source) == ["PIE-S2321"]
    assert _semantic_error_codes(_aggregate_projection("value = sum(amount, tax)")) == [
        "PIE-S2309"
    ]
    assert _semantic_error_codes(
        _aggregate_projection("value = count_distinct(customer_id, status)")
    ) == ["PIE-S2309"]


def test_deferred_aggregate_modifier_surfaces_remain_prohibited() -> None:
    evidence = _boundary_evidence()

    for required in (
        "aggregate filters / SQL `FILTER (WHERE ...)`",
        "generic `DISTINCT` syntax such as `count(distinct field)`",
        "aggregate internal ordering / `WITHIN GROUP`",
        "window functions / `OVER (...)`",
        "generic aggregate modifiers",
        "`count(*)` source syntax",
        "modifier-like aggregate arguments",
        "`count_distinct(...)` remains the current aggregate spelling",
        "Generic `count(distinct field)` syntax remains deferred and prohibited",
        "No new aggregate functions, modifiers, filters, window functions",
        "aggregate filters",
        "window functions",
        "aggregate internal ordering",
        "generic aggregate modifiers",
    ):
        assert required in evidence, required


def test_existing_diagnostic_posture_and_public_surfaces_are_preserved() -> None:
    evidence = f"{_boundary_evidence()} {_read(DIAGNOSTIC_STABILITY_TEST_PATH)}"

    for required in (
        "`PIE-P1000`",
        "`PIE-S2308`",
        "`PIE-S2309`",
        "`PIE-S2321`",
        "Slice 7 adds no diagnostic codes",
        "diagnostic envelope unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in evidence, required

    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_forbidden_surfaces_are_not_modified_or_untracked() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)
    status_output = _git_status_for(FORBIDDEN_DIFF_PATHS)

    assert (_non_slice3_repair_diff_paths(diff_output) == set()) or _slice5_gate2()
    assert (_non_slice3_repair_status_paths(status_output) == set()) or _slice5_gate2()


def test_only_phase37_static_audit_files_are_changed_or_untracked() -> None:
    status_lines = _git_status()
    changed_paths = {line[3:] for line in status_lines}
    forbidden_paths = sorted(
        path
        for path in changed_paths
        if not _is_in_progress_phase37_static_audit_path(path)
    )

    assert (set(forbidden_paths) <= ALLOWED_SLICE3_CHANGED_PATHS) or _slice5_gate2()
