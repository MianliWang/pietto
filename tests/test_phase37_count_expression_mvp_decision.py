from __future__ import annotations

import subprocess
from fnmatch import fnmatchcase
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = REPO_ROOT / "docs/spec/phase37-count-expression-mvp-decision-v1.md"
PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE36_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
)
PHASE23_SEMANTICS_TEST_PATH = REPO_ROOT / "tests/test_phase23_count_field_semantics.py"
PHASE23_IR_TEST_PATH = REPO_ROOT / "tests/test_phase23_count_field_ir.py"
PHASE26_SEMANTICS_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_semantics.py"
)
PHASE26_IR_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_ir.py"
)
PHASE26_SQL_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_sql.py"
)
PHASE26_CLI_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_cli_json_output.py"
)
PHASE28_SEMANTICS_TEST_PATH = (
    REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_semantics.py"
)
PHASE28_SQL_TEST_PATH = (
    REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_sql.py"
)
PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE36_ENUM_TEST_PATH = REPO_ROOT / "tests/test_phase36_enum_support_resolution.py"
PHASE36_ANY_BYTES_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_any_bytes_json_support_posture.py"
)
PHASE36_SCALAR_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_expanded_scalar_operator_matrix.py"
)
AGGREGATES_SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"

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


def _spec() -> str:
    return _normalized(SPEC_PATH)


def _phase37_plan() -> str:
    return _normalized(PHASE37_PLAN_PATH)


def _combined_current_deferred_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            FREEZE_SPEC_PATH,
            DEFERRED_REGISTER_PATH,
            PHASE37_PLAN_PATH,
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


def _is_in_progress_phase37_static_audit_path(path: str) -> bool:
    return any(
        fnmatchcase(path, pattern)
        for pattern in IN_PROGRESS_PHASE37_STATIC_AUDIT_PATTERNS
    )


def test_phase37_slice3_spec_exists_and_has_required_sections() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 37 Count Expression MVP Decision v1",
        "## Status",
        "## Current Count Surface",
        "## Current Deferred State",
        "## Decision",
        "## Future MVP Constraints",
        "## Explicit Exclusions",
        "## SQL Portability And Diagnostics",
        "## Phase 36 Type Boundary Preservation",
        "## Public Surface Stability",
        "Phase 37 Slice 3 is `count(expression)` MVP Decision",
        "docs/spec/static-audit only",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_slice3_authorizes_no_behavior_source_or_output_changes() -> None:
    spec = _spec()
    plan = _phase37_plan()

    for required in (
        "Slice 3 does not implement `count(expression)`",
        "authorizes no behavior change",
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
    ):
        assert required in spec, required

    assert (
        "| 3 | `count(expression)` MVP Decision | docs/spec first; "
        "possible later implementation only if separately approved |"
    ) in plan
    assert "Later slices may recommend implementation" in plan
    assert "Gate 1 and Gate 2 authorization" in plan


def test_current_count_surface_and_deferred_state_are_locked() -> None:
    spec = _spec()
    current_evidence = _combined_current_deferred_evidence()
    phase23_semantics = _read(PHASE23_SEMANTICS_TEST_PATH)
    phase23_ir = _read(PHASE23_IR_TEST_PATH)
    aggregate_source = _read(AGGREGATES_SOURCE_PATH)
    combined = f"{spec} {current_evidence} {phase23_semantics} {phase23_ir}"

    for required in (
        "`count()`",
        "`count(field)`",
        "`count(source.field)`",
        "Accepted as SQL `COUNT(*)`; result is `Int not null`",
        "concrete non-`Any` and not Enum",
        "Current `count(field)` counts non-null field values",
        "`count(expression)` remains deferred and fail-closed today",
        "`count(expression)` as a rejected aggregate expansion",
        "new aggregate functions, modifiers, filters, window functions, `count(expression)`",
        "known_values = count(amount + amount)",
        "known_values = count(lower(status))",
        "known_values = count(count())",
        "known_values = count(amount) + 1",
        "PIE-S2315",
        "PIE-S2311",
        "PIE-S2310",
        "PIE-S2313",
    ):
        assert required in combined, required

    for source_evidence in (
        'COUNT_AGGREGATE_NAME = "count"',
        "expected_semantic_aggregate_arities",
        "return (0, 1)",
        "is_supported_count_argument",
        "deferred_argument_expression_diagnostic",
    ):
        assert source_evidence in aggregate_source, source_evidence


def test_existing_tests_prove_count_expression_remains_deferred_today() -> None:
    combined = " ".join(
        _read(path)
        for path in (
            PHASE26_SEMANTICS_TEST_PATH,
            PHASE26_IR_TEST_PATH,
            PHASE26_SQL_TEST_PATH,
            PHASE26_CLI_JSON_TEST_PATH,
            PHASE28_SEMANTICS_TEST_PATH,
            PHASE28_SQL_TEST_PATH,
            PHASE31_MATRIX_TEST_PATH,
        )
    )

    for required in (
        "value = count(amount + tax)",
        "value = count(amount + 1)",
        "value = count_distinct(len(status))",
        "value = min(amount + tax)",
        "value = max(score * weight)",
        "value = sum(1)",
        "value = avg(1)",
        "value = sum(amount / tax)",
        "value = sum(amount % tax)",
        "value = sum(price * discount)",
        "value = sum(avg(amount))",
        "PIE-S2315",
        "PIE-S2311",
    ):
        assert required in combined, required


def test_future_mvp_candidate_constraints_are_locked() -> None:
    spec = _spec()

    for required in (
        "`count(expression)` is a future implementation candidate only",
        "direct aliased aggregate projections only",
        "no-GROUP and grouped contexts only",
        "expression must include at least one direct input field leaf",
        "expression result type must be a known concrete non-`Any` scalar",
        "result would be `Int not null`",
        "aggregate name remains an aggregate, not a scalar builtin",
        "current `count()` and `count(field)` behavior must remain byte-compatible",
        "unsupported forms must fail closed before SQL lowering",
        "Slice 3 does not decide an implementation algorithm",
        "Any behavior implementation requires a later Gate 1 and Gate 2 authorization",
    ):
        assert required in spec, required


def test_future_mvp_exclusions_are_locked() -> None:
    spec = _spec()

    for required in (
        "`count(1)`",
        "literal-only expressions",
        "projection aliases as aggregate argument leaves",
        "nested aggregates",
        "aggregate composition",
        "generic `DISTINCT`",
        "generic `count(distinct field)` syntax",
        "aggregate filters",
        "window functions",
        "aggregate internal ordering",
        "generic aggregate modifiers",
        "relationship/JOIN/fanout-sensitive contexts",
        "multi-input relationship traversal",
        "Enum arguments",
        "`Any` arguments",
        "Unknown or unresolved arguments",
        "Decimal precision-scale widening",
        "Decimal literal support",
        "Decimal multiplication support",
        "Decimal division support",
        "mixed Decimal promotion widening",
        "UUID expansion beyond current Phase 36 boundaries",
        "Bytes expansion beyond current Phase 36 boundaries",
        "Json expansion beyond current Phase 36 boundaries",
        "public MySQL API expansion",
        "runtime/database execution",
        "`sum(1)` and `avg(1)` remain outside current behavior",
        "Division and modulo aggregate expression arguments remain outside",
    ):
        assert required in spec, required


def test_sql_portability_and_fail_closed_diagnostics_are_required() -> None:
    spec = _spec()

    for required in (
        "portable across the existing PostgreSQL and private MySQL emitters",
        "must not rely on backend execution",
        "schema introspection",
        "native database type metadata",
        "runtime database checks",
        "Unsupported `count(expression)` shapes must fail closed",
        "`PIE-S2315`",
        "`PIE-S2311`",
        "`PIE-S2310`",
        "`PIE-S2314`",
        "existing unresolved-field diagnostics",
        "no diagnostic envelope change",
        "no diagnostic inventory expansion",
    ):
        assert required in spec, required


def test_phase36_type_boundaries_are_preserved_for_count_expression_decision() -> None:
    spec = _spec()
    phase36 = _normalized(PHASE36_PLAN_PATH)
    phase36_enum = _normalized(PHASE36_ENUM_TEST_PATH)
    any_bytes_json = _normalized(PHASE36_ANY_BYTES_JSON_TEST_PATH)
    scalar_matrix = _normalized(PHASE36_SCALAR_MATRIX_TEST_PATH)
    combined = f"{spec} {phase36} {phase36_enum} {any_bytes_json} {scalar_matrix}"

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
        "`count(Enum field)` now fails in semantic aggregate validation with existing diagnostic `PIE-S2314`",
        "Direct `count(Bytes field)` and `count(Json field)` remain current accepted concrete non-Any `count(field)` behavior",
        "`count(Any field)` remains semantic `PIE-S2314`",
        "`count_distinct` over `Any`, `Bytes`, `Json`, and Enum remains `PIE-S2314`",
    ):
        assert required in combined, required


def test_public_output_schema_and_release_surfaces_remain_unchanged() -> None:
    spec = _spec()

    for required in (
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "public status docs unchanged",
        "package version remains `0.1.0`",
        "no package/workflow/release metadata change",
        "no tag/release/publish/upload/signing/attestation",
        "no public schema/output change",
    ):
        assert required in spec, required

    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_forbidden_surfaces_are_not_modified_or_untracked() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)
    status_output = _git_status_for(FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""
    assert status_output == ""


def test_only_phase37_static_audit_files_are_changed_or_untracked() -> None:
    status_lines = _git_status()
    changed_paths = {line[3:] for line in status_lines}
    forbidden_paths = sorted(
        path
        for path in changed_paths
        if not _is_in_progress_phase37_static_audit_path(path)
    )

    assert forbidden_paths == []
