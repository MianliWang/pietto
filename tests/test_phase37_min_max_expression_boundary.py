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

SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"
PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE36_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
)
PHASE22_CANDIDATE_TEST_PATH = (
    REPO_ROOT / "tests/test_phase22_min_max_candidate_decision.py"
)
PHASE22_SEMANTICS_TEST_PATH = REPO_ROOT / "tests/test_phase22_min_max_semantics.py"
PHASE22_IR_TEST_PATH = REPO_ROOT / "tests/test_phase22_min_max_ir.py"
PHASE22_SQL_TEST_PATH = REPO_ROOT / "tests/test_phase22_min_max_sql.py"
PHASE22_COMPLETION_TEST_PATH = REPO_ROOT / "tests/test_phase22_completion_audit.py"
PHASE26_CANDIDATE_TEST_PATH = (
    REPO_ROOT
    / "tests/test_phase26_aggregate_expression_arguments_candidate_decision.py"
)
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
PHASE31_NUMERIC_BOUNDARY_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_numeric_promotion_decimal_boundary.py"
)
PHASE31_DATE_TIMESTAMP_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_date_timestamp_sql_compatibility.py"
)
PHASE36_ENUM_TEST_PATH = REPO_ROOT / "tests/test_phase36_enum_support_resolution.py"
PHASE36_ANY_BYTES_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_any_bytes_json_support_posture.py"
)
PHASE36_UUID_TEST_PATH = REPO_ROOT / "tests/test_phase36_uuid_support_completion.py"
PHASE36_SCALAR_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_expanded_scalar_operator_matrix.py"
)
PHASE36_DATETIME_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_datetime_time_interval_boundary.py"
)
PHASE36_COMPLETION_TEST_PATH = REPO_ROOT / "tests/test_phase36_completion_audit.py"
AGGREGATES_SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
POSTGRES_SQL_SOURCE_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_SQL_SOURCE_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"

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


def test_phase37_slice5_spec_exists_and_has_required_sections() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 37 Min Max Expression Boundary v1",
        "## Status",
        "## Current Accepted Extrema Surface",
        "## Current Deferred State",
        "## Decision",
        "## Future Candidate Constraints",
        "## Explicit Exclusions",
        "## SQL Portability, Ordering, And Null Semantics",
        "## Fail-closed Diagnostics",
        "## Phase 36 Type Boundary Preservation",
        "## Public Surface Stability",
        "Phase 37 Slice 5 is `min/max(expression)` Boundary",
        "docs/spec/static-audit only",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_slice5_authorizes_no_behavior_source_or_output_changes() -> None:
    spec = _spec()
    plan = _phase37_plan()

    for required in (
        "Slice 5 does not change semantic acceptance",
        "Slice 5 authorizes no behavior change",
        "does not implement `min(expression)` or `max(expression)`",
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
        "| 5 | `min/max(expression)` Boundary | "
        "readiness/spec/tests first; no initial behavior change |"
    ) in plan
    assert "Later slices may recommend implementation" in plan
    assert "Gate 1 and Gate 2 authorization" in plan


def test_current_direct_field_extrema_surface_is_locked() -> None:
    spec = _spec()
    current_evidence = _combined_current_deferred_evidence()
    phase22_semantics = _read(PHASE22_SEMANTICS_TEST_PATH)
    phase22_ir = _read(PHASE22_IR_TEST_PATH)
    phase22_sql = _read(PHASE22_SQL_TEST_PATH)
    phase31_matrix = _read(PHASE31_MATRIX_TEST_PATH)
    aggregate_source = _read(AGGREGATES_SOURCE_PATH)
    postgres_sql = _read(POSTGRES_SQL_SOURCE_PATH)
    mysql_sql = _read(MYSQL_SQL_SOURCE_PATH)
    combined = (
        f"{spec} {current_evidence} {phase22_semantics} {phase22_ir} "
        f"{phase22_sql} {phase31_matrix} {aggregate_source} "
        f"{postgres_sql} {mysql_sql}"
    )

    for required in (
        "`min(field)` / `max(field)`",
        "`min(source.field)` / `max(source.field)`",
        "accepted direct-field types `Int`, `Float`, `Decimal`, `Date`, and `Timestamp`",
        "result is nullable same type",
        "smallest_amount = min(amount)",
        "largest_amount = max(amount)",
        "first_order_date = min(order_date)",
        "latest_created_at = max(created_at)",
        "first_order_date = min(orders.order_date)",
        "highest_score = max(orders.score)",
        "smallest_price = min(price)",
        "latest_created_at = max(created_at)",
        'MIN_AGGREGATE_NAME = "min"',
        'MAX_AGGREGATE_NAME = "max"',
        "is_supported_extrema_argument",
        "semantic_aggregate_result_value_type",
        "_SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES",
        '"Int", "Float", "Decimal", "Date", "Timestamp"',
    ):
        assert required in combined, required


def test_broad_min_max_expression_remains_deferred_today() -> None:
    spec = _spec()
    current_evidence = _combined_current_deferred_evidence()
    existing_tests = " ".join(
        _read(path)
        for path in (
            PHASE22_CANDIDATE_TEST_PATH,
            PHASE22_SEMANTICS_TEST_PATH,
            PHASE22_IR_TEST_PATH,
            PHASE22_SQL_TEST_PATH,
            PHASE22_COMPLETION_TEST_PATH,
            PHASE26_CANDIDATE_TEST_PATH,
            PHASE26_SEMANTICS_TEST_PATH,
            PHASE26_IR_TEST_PATH,
            PHASE26_SQL_TEST_PATH,
            PHASE26_CLI_JSON_TEST_PATH,
            PHASE28_SEMANTICS_TEST_PATH,
            PHASE28_SQL_TEST_PATH,
            PHASE31_MATRIX_TEST_PATH,
            PHASE31_NUMERIC_BOUNDARY_TEST_PATH,
        )
    )
    combined = f"{spec} {current_evidence} {existing_tests}"

    for required in (
        "Broad `min(expression)` / `max(expression)` remains deferred and fail-closed today",
        "`min(expression)` beyond direct fields",
        "`max(expression)` beyond direct fields",
        "No new aggregate functions, modifiers, filters, window functions",
        "expression arguments remain deferred",
        "value = min(amount + amount)",
        "value = min(amount + tax)",
        "value = max(score * weight)",
        "value = min(amount + 1)",
        "value = max(score * 2)",
        "value = min(max(amount))",
        "value = min(amount) + 1",
        "where min(amount) > 0",
        "PIE-S2315",
        "PIE-S2309",
        "PIE-S2311",
        "PIE-S2310",
        "PIE-S2313",
        "PIE-S2308",
        "PIE-S2314",
    ):
        assert required in combined, required


def test_future_min_max_candidate_constraints_are_locked() -> None:
    spec = _spec()

    for required in (
        "`min(expression)` and `max(expression)` are future implementation candidates only",
        "direct aliased aggregate projections only",
        "no-GROUP and grouped contexts only",
        "expression must contain at least one direct input field leaf",
        "known concrete supported orderable scalar result type",
        "result would be nullable same type",
        "aggregate names remain aggregates, not scalar builtins",
        "current `min(field)` / `max(field)` behavior must remain byte-compatible",
        "unsupported forms must fail closed before SQL lowering",
        "Slice 5 does not decide an implementation algorithm",
        "Any behavior implementation requires a later Gate 1 and Gate 2 authorization",
    ):
        assert required in spec, required


def test_future_min_max_exclusions_are_locked() -> None:
    spec = _spec()

    for required in (
        "literal-only forms such as `min(1)` / `max(1)`",
        "multi-field expressions",
        "projection aliases as aggregate argument leaves",
        "nested aggregates",
        "aggregate composition",
        "aggregate filters",
        "window functions",
        "generic aggregate modifiers",
        "relationship/JOIN/fanout-sensitive contexts",
        "multi-input traversal",
        "Text arguments or expressions",
        "Bool arguments or expressions",
        "UUID arguments or expressions",
        "Enum arguments or expressions",
        "`Any` arguments or expressions",
        "Bytes arguments or expressions",
        "Json arguments or expressions",
        "DateTime / Time / Interval arguments or expressions",
        "Unknown or unresolved arguments",
        "Decimal precision-scale widening",
        "Decimal literals",
        "Decimal multiplication/division",
        "mixed Decimal promotion widening",
        "temporal arithmetic/function portability",
        "collation/order semantics expansion",
        "public MySQL API expansion",
        "runtime/database execution",
    ):
        assert required in spec, required


def test_sql_portability_ordering_null_semantics_and_diagnostics_are_locked() -> None:
    spec = _spec()
    postgres_sql = _read(POSTGRES_SQL_SOURCE_PATH)
    mysql_sql = _read(MYSQL_SQL_SOURCE_PATH)
    combined_sql = f"{postgres_sql} {mysql_sql}"

    for required in (
        "portable across the existing PostgreSQL and private MySQL emitters",
        "must not rely on backend execution",
        "schema introspection",
        "native database type metadata",
        "runtime database checks",
        "Ordering semantics must remain deterministic for the accepted subset",
        "Collation/order semantics expansion is not authorized",
        "Text collation",
        "UUID ordering",
        "Bytes ordering",
        "Json ordering",
        "Enum SQL scalar ordering",
        "accepted `min/max` results are nullable same type",
        "Unsupported `min/max(expression)` shapes must fail closed",
        "`PIE-S2315`",
        "`PIE-S2309`",
        "`PIE-S2311`",
        "`PIE-S2310`",
        "`PIE-S2314`",
        "`PIE-S2308`",
        "`PIE-S2313`",
        "existing unresolved-field diagnostics",
        "no diagnostic envelope change",
        "no diagnostic inventory expansion",
    ):
        assert required in spec, required

    for source_evidence in (
        "_SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES",
        "PostgreSQL aggregate",
        "MySQL aggregate",
        "expects a direct field argument",
        "Float, Decimal, Date, or Timestamp field arguments",
        "match approved logical shape",
    ):
        assert source_evidence in combined_sql, source_evidence


def test_phase36_type_boundaries_are_preserved_for_min_max_boundary() -> None:
    spec = _spec()
    phase36 = _normalized(PHASE36_PLAN_PATH)
    phase36_enum = _normalized(PHASE36_ENUM_TEST_PATH)
    any_bytes_json = _normalized(PHASE36_ANY_BYTES_JSON_TEST_PATH)
    uuid = _normalized(PHASE36_UUID_TEST_PATH)
    scalar_matrix = _normalized(PHASE36_SCALAR_MATRIX_TEST_PATH)
    datetime_boundary = _normalized(PHASE36_DATETIME_TEST_PATH)
    phase36_completion = _normalized(PHASE36_COMPLETION_TEST_PATH)
    numeric_boundary = _read(PHASE31_NUMERIC_BOUNDARY_TEST_PATH)
    date_timestamp = _read(PHASE31_DATE_TIMESTAMP_TEST_PATH)
    combined = (
        f"{spec} {phase36} {phase36_enum} {any_bytes_json} {uuid} "
        f"{scalar_matrix} {datetime_boundary} {phase36_completion} "
        f"{numeric_boundary} {date_timestamp}"
    )

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
        "UUID `min` or `max` support unless separately approved",
        "`min` / `max` supported direct-field rows remain current for `Int`, `Float`, `Decimal`, `Date`, and `Timestamp`",
        "value = min(raw)",
        "value = max(payload)",
        "Decimal multiplication remains rejected with `PIE-S2105`",
        "DateTime, Time, Interval, or timezone semantics",
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
