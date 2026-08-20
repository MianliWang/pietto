from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE36_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
)
EXPANDED_SCALAR_SPEC_PATH = (
    REPO_ROOT / "docs/spec/expanded-scalar-operator-matrix-v1.md"
)
PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE31_NUMERIC_BOUNDARY_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_numeric_promotion_decimal_boundary.py"
)
PHASE36_ENUM_TEST_PATH = REPO_ROOT / "tests/test_phase36_enum_support_resolution.py"
PHASE36_SCALAR_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_expanded_scalar_operator_matrix.py"
)
AGGREGATES_SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"

IN_PROGRESS_PHASE37_STATIC_AUDIT_PATTERNS = (
    "docs/spec/phase37-*.md",
    "tests/test_phase37_*.py",
)


def _phase37_plan() -> str:
    return _normalized(PHASE37_PLAN_PATH)


def _freeze_spec() -> str:
    return _normalized(FREEZE_SPEC_PATH)


def _phase36_plan() -> str:
    return _normalized(PHASE36_PLAN_PATH)


def _is_in_progress_phase37_static_audit_path(path: str) -> bool:
    return any(
        fnmatchcase(path, pattern)
        for pattern in IN_PROGRESS_PHASE37_STATIC_AUDIT_PATTERNS
    )


def test_phase37_slice2_is_tests_only_static_audit_no_behavior_change() -> None:
    plan = _phase37_plan()

    for required in (
        "| 2 | Current Aggregate Matrix And Deferred Register | "
        "tests-only/static-audit; no behavior change |",
        "Later slices may recommend implementation, but implementation requires separate",
        "Gate 1 and Gate 2 authorization",
        "Slice 1 starts Phase 37 without changing the compiler",
        "public status housekeeping remains future dedicated work",
        "package version remains `0.1.0`",
        "no package/workflow/release metadata change",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in plan, required


def test_current_accepted_aggregate_matrix_is_locked_in_existing_evidence() -> None:
    plan = _phase37_plan()
    freeze = _freeze_spec()
    phase31_matrix = _read(PHASE31_MATRIX_TEST_PATH)
    aggregate_source = _read(AGGREGATES_SOURCE_PATH)
    combined = f"{plan} {freeze} {phase31_matrix} {aggregate_source}"

    for required in (
        "`count()`",
        "`count(field)` / `count(source.field)`",
        "`count_distinct(field)` / `count_distinct(source.field)`",
        "`count_distinct(lower/trim Text chain)`",
        "`sum(field)` / `sum(source.field)`",
        "`avg(field)` / `avg(source.field)`",
        "`sum(...)` / `avg(...)` bounded numeric expressions",
        "Int/Float literal leaves inside `sum` / `avg`",
        "Decimal `+` and `-` expression participation",
        "`min(field)` / `max(field)`",
        "grouped aggregate projections",
        "`satisfying:`",
        "grouped result `order by:`",
        "Current aggregate names remain aggregate names, not scalar builtins",
        "Current Phase 25 `satisfying:` behavior is frozen",
        "Current Phase 27 grouped selected-output `order by` behavior is frozen",
    ):
        assert required in combined, required

    for source_evidence in (
        'COUNT_AGGREGATE_NAME = "count"',
        'COUNT_DISTINCT_AGGREGATE_NAME = "count_distinct"',
        'SUM_AGGREGATE_NAME = "sum"',
        'AVG_AGGREGATE_NAME = "avg"',
        'MIN_AGGREGATE_NAME = "min"',
        'MAX_AGGREGATE_NAME = "max"',
        "SEMANTIC_AGGREGATE_NAMES = AGGREGATE_NAMES",
        "is_supported_count_argument",
        "is_supported_count_distinct_argument",
        "is_supported_extrema_argument",
    ):
        assert source_evidence in aggregate_source, source_evidence

    for matrix_evidence in (
        "count_raw = count(raw)",
        "count_payload = count(payload)",
        "count_customer = count(customer_id)",
        "unique_normalized = count_distinct(lower(trim(status)))",
        "decimal_total_expr = sum(price + discount)",
        "decimal_average_expr = avg(price - discount)",
        "first_order_date = min(order_date)",
        "latest_created_at = max(created_at)",
        "test_postgres_and_private_mysql_sql_matrix_is_stable",
    ):
        assert matrix_evidence in phase31_matrix, matrix_evidence


def test_deferred_and_prohibited_aggregate_register_is_locked() -> None:
    plan = _phase37_plan()
    freeze = _freeze_spec()
    register = _normalized(DEFERRED_REGISTER_PATH)
    combined = f"{plan} {freeze} {register}"

    for required in (
        "`count(expression)`",
        "broad `count_distinct(expression)`",
        "generalized `count_distinct(expression)` beyond direct fields and lower/trim",
        "`min(expression)` / `max(expression)`",
        "`min(expression)` beyond direct fields",
        "`max(expression)` beyond direct fields",
        "aggregate filters",
        "window functions",
        "generic aggregate modifiers",
        "generic `DISTINCT` syntax",
        "`count(distinct field)`",
        "nested aggregates",
        "aggregate projection composition",
        "aggregate over projection aliases",
        "literal-only aggregate arguments",
        "literal-only aggregate expressions such as `sum(1)` and `avg(1)`",
        "division or modulo aggregate arguments",
        "Decimal literal/multiply/divide/mixed promotion",
        "UUID/Enum/Any/Bytes/Json aggregate expansion",
        "relationship/fanout-safe aggregates",
        "No new aggregate functions, modifiers, filters, window functions",
        "or expand aggregate behavior",
    ):
        assert required in combined, required


def test_expression_aggregate_widening_remains_fail_closed_by_existing_tests() -> None:
    phase31_matrix = _read(PHASE31_MATRIX_TEST_PATH)
    numeric_boundary = _read(PHASE31_NUMERIC_BOUNDARY_TEST_PATH)
    phase36_enum = _read(PHASE36_ENUM_TEST_PATH)
    scalar_matrix = _read(PHASE36_SCALAR_MATRIX_TEST_PATH)
    aggregate_source = _read(AGGREGATES_SOURCE_PATH)
    combined = (
        f"{phase31_matrix} {numeric_boundary} {phase36_enum} "
        f"{scalar_matrix} {aggregate_source}"
    )

    for required in (
        "value = count(1)",
        "value = count_distinct(len(status))",
        "value = count_distinct(amount + tax)",
        "value = min(amount + tax)",
        "value = max(score * weight)",
        "value = sum(1)",
        "value = avg(1)",
        "value = sum(avg(amount))",
        "value = sum(amount) + 1",
        "value = sum(amount / tax)",
        "value = sum(amount % tax)",
        "value = count_distinct(status)",
        "value = min(status)",
        "value = max(status)",
        "PIE-S2314",
        "PIE-S2311",
        "deferred_argument_expression_diagnostic",
        "nested_aggregate_diagnostic",
        "deferred_composition_diagnostic",
    ):
        assert required in combined, required


def test_phase36_type_boundaries_are_preserved_for_aggregate_slice2() -> None:
    plan = _phase37_plan()
    phase36 = _phase36_plan()
    expanded_scalar = _normalized(EXPANDED_SCALAR_SPEC_PATH)
    scalar_matrix = _normalized(PHASE36_SCALAR_MATRIX_TEST_PATH)
    combined = f"{plan} {phase36} {expanded_scalar} {scalar_matrix}"

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
        "Slice 5 is the only Phase 36 behavior change",
        "`count(Enum field)` now fails closed with diagnostic `PIE-S2314`",
        "`Bytes` / `Json` direct `count(field)` remains current accepted behavior",
        "`count_distinct` over `Any`, `Bytes`, `Json`, and Enum remains `PIE-S2314`",
    ):
        assert required in combined, required


def test_public_output_schema_and_release_surfaces_remain_unchanged() -> None:
    plan = _phase37_plan()
    freeze = _freeze_spec()
    combined = f"{plan} {freeze}"

    for required in (
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "package version remains `0.1.0`",
        "no package/workflow/release metadata change",
        "no tag/release/publish/upload/signing/attestation",
        "JSON behavior or schema changes",
        "fixture or golden changes",
        "script changes",
        "dependency changes",
        "package metadata changes",
        "CI changes",
        "public API changes",
    ):
        assert required in combined, required

    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")
