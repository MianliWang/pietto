from __future__ import annotations

import subprocess
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
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md"
)
PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE36_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
)
PHASE24_SEMANTICS_TEST_PATH = (
    REPO_ROOT / "tests/test_phase24_count_distinct_semantics.py"
)
PHASE24_IR_TEST_PATH = REPO_ROOT / "tests/test_phase24_count_distinct_ir.py"
PHASE24_SQL_TEST_PATH = REPO_ROOT / "tests/test_phase24_count_distinct_sql.py"
PHASE24_CLI_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase24_cli_json_output_hardening.py"
)
PHASE26_TEXT_TRANSFORM_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_count_distinct_text_transform_semantics.py"
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
PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE31_NUMERIC_BOUNDARY_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_numeric_promotion_decimal_boundary.py"
)
PHASE36_ENUM_TEST_PATH = REPO_ROOT / "tests/test_phase36_enum_support_resolution.py"
PHASE36_ANY_BYTES_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_any_bytes_json_support_posture.py"
)
PHASE36_UUID_TEST_PATH = REPO_ROOT / "tests/test_phase36_uuid_support_completion.py"
PHASE36_SCALAR_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_expanded_scalar_operator_matrix.py"
)
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


def test_phase37_slice4_spec_exists_and_has_required_sections() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 37 Count Distinct Expression Widening Boundary v1",
        "## Status",
        "## Current Accepted Count-distinct Surface",
        "## Current Deferred State",
        "## Decision",
        "## Future Candidate Constraints",
        "## Explicit Exclusions",
        "## SQL Portability And Collation",
        "## Fail-closed Diagnostics",
        "## Phase 36 Type Boundary Preservation",
        "## Public Surface Stability",
        "Phase 37 Slice 4 is `count_distinct(expression)` Widening Boundary",
        "docs/spec/static-audit only",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_slice4_authorizes_no_behavior_source_or_output_changes() -> None:
    spec = _spec()
    plan = _phase37_plan()

    for required in (
        "Slice 4 does not change semantic acceptance",
        "Slice 4 authorizes no behavior change",
        "does not implement broad `count_distinct(expression)`",
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
        "| 4 | `count_distinct(expression)` Widening Boundary | "
        "readiness/spec/tests first; no initial behavior change |"
    ) in plan
    assert "Later slices may recommend implementation" in plan
    assert "Gate 1 and Gate 2 authorization" in plan


def test_current_count_distinct_surface_is_locked_in_existing_evidence() -> None:
    spec = _spec()
    current_evidence = _combined_current_deferred_evidence()
    phase24_semantics = _read(PHASE24_SEMANTICS_TEST_PATH)
    phase26_text = _read(PHASE26_TEXT_TRANSFORM_TEST_PATH)
    phase31_matrix = _read(PHASE31_MATRIX_TEST_PATH)
    aggregate_source = _read(AGGREGATES_SOURCE_PATH)
    combined = (
        f"{spec} {current_evidence} {phase24_semantics} "
        f"{phase26_text} {phase31_matrix} {aggregate_source}"
    )

    for required in (
        "`count_distinct(field)`",
        "`count_distinct(source.field)`",
        "`count_distinct(lower/trim Text chain)`",
        "`Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`",
        "result is `Int not null`",
        "exactly one `Text` field leaf",
        "count_distinct(lower(field))",
        "count_distinct(trim(field))",
        "count_distinct(lower(trim(field)))",
        "count_distinct(trim(lower(field)))",
        "count_distinct(lower(source.field))",
        "value = count_distinct(lower(status))",
        "value = count_distinct(trim(status))",
        "value = count_distinct(lower(trim(status)))",
        "value = count_distinct(lower(orders.status))",
        "unique_normalized = count_distinct(lower(trim(status)))",
        'COUNT_DISTINCT_AGGREGATE_NAME = "count_distinct"',
        "is_supported_count_distinct_argument",
        "_is_lower_trim_text_transform_chain",
    ):
        assert required in combined, required


def test_broad_count_distinct_expression_remains_deferred_today() -> None:
    spec = _spec()
    current_evidence = _combined_current_deferred_evidence()
    existing_tests = " ".join(
        _read(path)
        for path in (
            PHASE24_SEMANTICS_TEST_PATH,
            PHASE24_IR_TEST_PATH,
            PHASE24_SQL_TEST_PATH,
            PHASE24_CLI_JSON_TEST_PATH,
            PHASE26_TEXT_TRANSFORM_TEST_PATH,
            PHASE26_IR_TEST_PATH,
            PHASE26_SQL_TEST_PATH,
            PHASE26_CLI_JSON_TEST_PATH,
            PHASE31_MATRIX_TEST_PATH,
        )
    )
    combined = f"{spec} {current_evidence} {existing_tests}"

    for required in (
        "Broad `count_distinct(expression)` remains deferred and fail-closed today",
        "generalized `count_distinct(expression)` beyond direct fields and lower/trim",
        "count_distinct(amount + amount)",
        "value = count_distinct(len(status))",
        "value = count_distinct(lower(status) + trim(status))",
        "value = count_distinct(lower(status) + lower(region))",
        "value = count_distinct(lower(1))",
        "value = count_distinct(lower(amount))",
        "value = count_distinct()",
        "value = count_distinct(lower(status), trim(status))",
        "value = count_distinct(lower(avg(status)))",
        "value = count_distinct(lower(status)) + 1",
        "PIE-S2315",
        "PIE-S2309",
        "PIE-S2311",
        "PIE-S2310",
        "PIE-S2313",
        "PIE-S2308",
    ):
        assert required in combined, required


def test_future_narrow_text_candidate_constraints_are_locked() -> None:
    spec = _spec()

    for required in (
        "`count_distinct(expression)` is a future implementation candidate only",
        "narrow Text deterministic-transform family",
        "direct aliased aggregate projections only",
        "no-GROUP and grouped contexts only",
        "exactly one direct input `Text` field leaf",
        "deterministic Text transforms only",
        "current lower/trim behavior remains byte-compatible",
        "result would remain `Int not null`",
        "aggregate name remains an aggregate, not a scalar builtin",
        "unsupported forms must fail closed before SQL lowering",
        "does not decide a new expression language",
        "Any behavior implementation requires a later Gate 1 and Gate 2 authorization",
    ):
        assert required in spec, required


def test_future_widening_exclusions_are_locked() -> None:
    spec = _spec()

    for required in (
        "broad scalar expressions",
        "numeric expressions",
        "Date/Timestamp expressions",
        "UUID expressions",
        "Decimal expressions",
        "multi-field expressions",
        "literal-only forms such as `count_distinct(1)`",
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
        "multi-input traversal",
        "Enum arguments",
        "`Any` arguments",
        "Bytes arguments",
        "Json arguments",
        "Unknown or unresolved arguments",
        "Decimal precision-scale widening",
        "Decimal literal support",
        "Decimal multiplication support",
        "Decimal division support",
        "mixed Decimal promotion widening",
        "UUID expansion beyond current Phase 36 boundaries",
        "collation/normalization semantics expansion",
        "public MySQL API expansion",
        "runtime/database execution",
    ):
        assert required in spec, required


def test_generic_distinct_syntax_remains_deferred() -> None:
    spec = _spec()
    current_evidence = _combined_current_deferred_evidence()
    phase24_semantics = _read(PHASE24_SEMANTICS_TEST_PATH)
    combined = f"{spec} {current_evidence} {phase24_semantics}"

    for required in (
        "generic `DISTINCT`",
        "generic `count(distinct field)` syntax",
        "Generic `count(distinct field)` syntax remains deferred and prohibited",
        "`count_distinct(...)` remains the current aggregate spelling",
        "generic aggregate modifiers",
        "No new aggregate functions, modifiers, filters, window functions",
        "test_count_distinct_is_aggregate_only_and_ir_authorized",
        "count_distinct",
    ):
        assert required in combined, required


def test_sql_portability_collation_and_fail_closed_diagnostics_are_required() -> None:
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
        "Current lower/trim Text-chain SQL bytes remain the compatibility baseline",
        "does not introduce collation semantics",
        "Unicode normalization semantics",
        "locale-sensitive folding",
        "Unsupported `count_distinct(expression)` shapes must fail closed",
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
        "_SUPPORTED_COUNT_DISTINCT_ARGUMENT_TYPES",
        '_COUNT_DISTINCT_TRANSFORM_NAMES = frozenset({"lower", "trim"})',
        "count_distinct expects a direct field or lower/trim",
        "supports only Bool, Int, Float",
        "Decimal, Text, Date, Timestamp, or UUID",
        "_is_count_distinct_text_transform_argument",
    ):
        assert source_evidence in combined_sql, source_evidence


def test_phase36_type_boundaries_are_preserved_for_count_distinct_boundary() -> None:
    spec = _spec()
    phase36 = _normalized(PHASE36_PLAN_PATH)
    phase36_enum = _normalized(PHASE36_ENUM_TEST_PATH)
    any_bytes_json = _normalized(PHASE36_ANY_BYTES_JSON_TEST_PATH)
    uuid = _normalized(PHASE36_UUID_TEST_PATH)
    scalar_matrix = _normalized(PHASE36_SCALAR_MATRIX_TEST_PATH)
    numeric_boundary = _read(PHASE31_NUMERIC_BOUNDARY_TEST_PATH)
    combined = (
        f"{spec} {phase36} {phase36_enum} {any_bytes_json} "
        f"{uuid} {scalar_matrix} {numeric_boundary}"
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
        "`count_distinct` over `Any`, `Bytes`, `Json`, and Enum remains `PIE-S2314`",
        "UUID remains `limited_frozen` with no behavior expansion",
        "no Decimal precision/scale carrier",
        "Decimal multiplication support",
        "Decimal division support",
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
