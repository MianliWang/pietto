from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path

import pytest

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
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
COUNT_EXPRESSION_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-expression-mvp-decision-v1.md"
)
COUNT_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md"
)
MIN_MAX_SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"
FILTER_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md"
)
DECIMAL_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-decimal-aggregate-expression-boundary-v1.md"
)
CURRENT_MATRIX_TEST_PATH = REPO_ROOT / "tests/test_phase37_current_aggregate_matrix.py"
NESTED_COMPOSITION_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_nested_aggregate_composition_hardening.py"
)
FILTER_DISTINCT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py"
)
DECIMAL_BOUNDARY_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_decimal_aggregate_expression_boundary.py"
)
PHASE21_GROUP_BY_TEST_PATH = (
    REPO_ROOT / "tests/test_phase21_group_by_semantic_validation.py"
)
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

IN_PROGRESS_PHASE37_STATIC_AUDIT_PATTERNS = (
    "docs/spec/phase37-*.md",
    "tests/test_phase37_*.py",
)
SOURCE_PREFIX = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    customer_id: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    price: Decimal not null\n"
    "    discount: Decimal not null\n"
    "    order_date: Date\n"
    "    created_at: Timestamp\n"
    'source orders: Order is postgres.table("orders")\n'
)


def _boundary_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PHASE37_PLAN_PATH,
            FREEZE_SPEC_PATH,
            DEFERRED_REGISTER_PATH,
            COUNT_EXPRESSION_SPEC_PATH,
            COUNT_DISTINCT_SPEC_PATH,
            MIN_MAX_SPEC_PATH,
            FILTER_DISTINCT_SPEC_PATH,
            DECIMAL_SPEC_PATH,
            CURRENT_MATRIX_TEST_PATH,
            NESTED_COMPOSITION_TEST_PATH,
            FILTER_DISTINCT_TEST_PATH,
            DECIMAL_BOUNDARY_TEST_PATH,
            PHASE21_GROUP_BY_TEST_PATH,
            PHASE25_SATISFYING_TEST_PATH,
            PHASE27_GROUPED_ORDER_TEST_PATH,
            PHASE31_MATRIX_TEST_PATH,
        )
    )


def _parse(source: str):
    result = parse_source(source, path="phase37-slice9-grouped-hardening.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _parser_codes(source: str) -> list[str]:
    result = parse_source(source, path="phase37-slice9-grouped-hardening.pietto")
    return [diagnostic.code for diagnostic in result.diagnostics]


def _semantic_error_codes(source: str) -> list[str]:
    result = analyze(_parse(source))
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _grouped_relation(
    *,
    projections: tuple[str, ...],
    satisfying: str | None = None,
    order_items: tuple[str, ...] = (),
) -> str:
    select_body = "".join(f"        {projection}\n" for projection in projections)
    satisfying_body = (
        "" if satisfying is None else f"    satisfying:\n        {satisfying}\n"
    )
    order_body = (
        ""
        if not order_items
        else "    order by:\n" + "".join(f"        {item}\n" for item in order_items)
    )
    return (
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        f"{select_body}"
        f"{satisfying_body}"
        f"{order_body}"
    )


def _no_group_relation(*, projections: tuple[str, ...]) -> str:
    select_body = "".join(f"        {projection}\n" for projection in projections)
    return (
        SOURCE_PREFIX + "table no_group_orders:\n"
        "    from orders\n"
        "    select:\n"
        f"{select_body}"
    )


def _is_in_progress_phase37_static_audit_path(path: str) -> bool:
    return any(
        fnmatchcase(path, pattern)
        for pattern in IN_PROGRESS_PHASE37_STATIC_AUDIT_PATTERNS
    )


def test_slice9_scope_is_tests_only_behavior_hardening() -> None:
    evidence = _boundary_evidence()

    for required in (
        "| 9 | Grouped Aggregate Interaction Hardening | tests-only; no behavior change |",
        "grouped aggregate projections",
        "`satisfying:`",
        "grouped result `order by:`",
        "Current Phase 25 `satisfying:` behavior is frozen",
        "Current Phase 27 grouped selected-output `order by` behavior is frozen",
        "`count(expression)`",
        "broad `count_distinct(expression)`",
        "`min(expression)` / `max(expression)`",
        "nested aggregates",
        "aggregate projection composition",
        "aggregate over projection aliases",
        "aggregate filters",
        "window functions",
        "generic `DISTINCT` syntax",
        "relationship/fanout-safe aggregates",
        "Package version remains `0.1.0`",
    ):
        assert required in evidence, required

    for prohibited in (
        "Slice 9 implements",
        "Slice 9 widens",
        "Slice 9 adds new accepted syntax",
        "Slice 9 changes diagnostic behavior",
    ):
        assert prohibited not in evidence, prohibited


@pytest.mark.parametrize(
    "projection",
    [
        "total = count()",
        "count_customer = count(customer_id)",
        "unique_status = count_distinct(status)",
        "unique_normalized = count_distinct(lower(trim(status)))",
        "total_amount = sum(amount)",
        "average_score = avg(score)",
        "total_expr = sum(amount + tax)",
        "weighted = avg(score * weight)",
        "decimal_total = sum(price + discount)",
        "smallest_amount = min(amount)",
        "first_order_date = min(order_date)",
        "largest_amount = max(amount)",
        "latest_created_at = max(created_at)",
    ],
)
def test_grouped_aggregate_projection_rows_remain_accepted(projection: str) -> None:
    source = _grouped_relation(
        projections=("region", projection),
        satisfying=None,
        order_items=(),
    )

    assert _semantic_error_codes(source) == []


def test_grouped_selected_outputs_remain_valid_for_satisfying_and_order_by() -> None:
    source = _grouped_relation(
        projections=(
            "r = region",
            "total_amount = sum(amount + tax)",
            "unique_normalized = count_distinct(lower(trim(status)))",
        ),
        satisfying='total_amount > 1000 and r != "test"',
        order_items=("total_amount desc", "r asc", "unique_normalized"),
    )

    assert _semantic_error_codes(source) == []


def test_no_group_aggregate_behavior_remains_distinct_from_grouped_behavior() -> None:
    valid_no_group = _no_group_relation(
        projections=(
            "total_amount = sum(amount)",
            "unique_status = count_distinct(status)",
        )
    )
    invalid_no_group_satisfying = (
        SOURCE_PREFIX + "table invalid_no_group_satisfying:\n"
        "    from orders\n"
        "    select:\n"
        "        total_amount = sum(amount)\n"
        "    satisfying:\n"
        "        total_amount > 1000\n"
    )

    assert _semantic_error_codes(valid_no_group) == []
    assert _semantic_error_codes(invalid_no_group_satisfying) == ["PIE-S2323"]


@pytest.mark.parametrize(
    ("projections", "expected_codes"),
    [
        (("customer_id", "total = count()"), ["PIE-S2318"]),
        (("label = lower(region)", "total = count()"), ["PIE-S2319"]),
        (("region",), ["PIE-S2320"]),
        (("region", "count()"), ["PIE-S2313"]),
    ],
)
def test_grouped_projection_boundaries_remain_rejected(
    projections: tuple[str, ...],
    expected_codes: list[str],
) -> None:
    assert _semantic_error_codes(_grouped_relation(projections=projections)) == (
        expected_codes
    )


@pytest.mark.parametrize(
    ("satisfying", "expected_codes"),
    [
        ("sum(amount) > 1000", ["PIE-S2308"]),
        ("missing > 0", ["PIE-S2324"]),
        ("amount > 1000", ["PIE-S2325"]),
        ("total_amount + 1 > 1000", ["PIE-S2327"]),
    ],
)
def test_satisfying_selected_output_boundary_remains_fail_closed(
    satisfying: str,
    expected_codes: list[str],
) -> None:
    projections = (
        "region",
        "total_amount = sum(amount)",
    )

    assert (
        _semantic_error_codes(
            _grouped_relation(projections=projections, satisfying=satisfying)
        )
        == expected_codes
    )


def test_computed_satisfying_output_remains_deferred() -> None:
    projections = (
        "region",
        "computed = amount + amount",
        "total_amount = sum(amount)",
    )

    assert _semantic_error_codes(
        _grouped_relation(projections=projections, satisfying="computed > 1000")
    ) == ["PIE-S2319", "PIE-S2326"]


@pytest.mark.parametrize(
    ("order_item", "expected_codes"),
    [
        ("sum(amount)", ["PIE-S2321"]),
        ("total + 1", ["PIE-S2321"]),
        ("amount", ["PIE-S2321"]),
        ("missing", ["PIE-S2321"]),
        ("orders.region", ["PIE-S2321"]),
    ],
)
def test_grouped_order_by_selected_output_boundary_remains_fail_closed(
    order_item: str,
    expected_codes: list[str],
) -> None:
    projections = (
        "region",
        "total = count()",
    )

    assert (
        _semantic_error_codes(
            _grouped_relation(projections=projections, order_items=(order_item,))
        )
        == expected_codes
    )


def test_computed_grouped_order_output_remains_deferred() -> None:
    projections = (
        "region",
        "computed = amount + amount",
        "total = count()",
    )

    assert _semantic_error_codes(
        _grouped_relation(projections=projections, order_items=("computed",))
    ) == ["PIE-S2319", "PIE-S2321"]


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("total = sum(avg(amount))", "PIE-S2311"),
        ("total = count(count())", "PIE-S2311"),
        ("total = sum(amount) + 1", "PIE-S2310"),
        ("total = lower(min(amount))", "PIE-S2310"),
        ("total = sum(total_amount)", "PIE-S2102"),
        # Phase 39 Slice 3 accepts "total = count(amount + tax)" semantically.
        ("total = count(1)", "PIE-S2315"),
        ("total = count_distinct(amount + tax)", "PIE-S2315"),
        ("total = min(amount + tax)", "PIE-S2315"),
        ("total = max(amount + tax)", "PIE-S2315"),
    ],
)
def test_grouped_deferred_aggregate_surfaces_remain_rejected(
    projection: str,
    expected_code: str,
) -> None:
    source = _grouped_relation(
        projections=("region", "total_amount = sum(amount)", projection),
    )

    assert _semantic_error_codes(source) == [expected_code]


@pytest.mark.parametrize(
    "projection",
    [
        "total = count(distinct customer_id)",
        "total = sum(amount) filter where amount > 0",
        "total = sum(amount) FILTER (WHERE amount > 0)",
        "total = sum(amount) over (region)",
        "total = sum(amount) within group (order by amount)",
        "total = count(*)",
    ],
)
def test_grouped_sql_like_aggregate_syntax_remains_parser_rejected(
    projection: str,
) -> None:
    source = _grouped_relation(projections=("region", projection))

    assert "PIE-P1000" in _parser_codes(source)


def test_grouped_relationship_and_fanout_safe_aggregate_work_remains_deferred() -> None:
    evidence = _boundary_evidence()

    for required in (
        "relationship/fanout-safe aggregates",
        "relationship/JOIN behavior",
        "relation composition",
        "endpoint-qualified lookup",
        "runtime/database execution",
        "public MySQL API expansion",
    ):
        assert required in evidence, required


def test_public_output_schema_and_release_surfaces_remain_unchanged() -> None:
    evidence = f"{_boundary_evidence()} {_read(PHASE31_DIAGNOSTIC_TEST_PATH)}"

    for required in (
        "no source/compiler behavior change",
        "grammar",
        "generated ANTLR",
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
        assert required in evidence, required

    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")
