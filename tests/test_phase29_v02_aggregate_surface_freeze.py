from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-29-v02-stabilization-boundary.md"
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"

PHASE24_PLAN_PATH = REPO_ROOT / "docs/plan/phase-24-aggregate-function-expansion-ii.md"
PHASE25_PLAN_PATH = REPO_ROOT / "docs/plan/phase-25-result-predicate-satisfying-mvp.md"
PHASE26_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-26-aggregate-expression-arguments-numeric-foundation.md"
)

PHASE24_DECIMAL_SEMANTICS_PATH = (
    REPO_ROOT / "tests/test_phase24_decimal_aggregate_semantics.py"
)
PHASE24_DECIMAL_IR_PATH = REPO_ROOT / "tests/test_phase24_decimal_aggregate_ir.py"
PHASE24_DECIMAL_SQL_PATH = REPO_ROOT / "tests/test_phase24_decimal_aggregate_sql.py"
PHASE26_TEXT_TRANSFORM_SEMANTICS_PATH = (
    REPO_ROOT / "tests/test_phase26_count_distinct_text_transform_semantics.py"
)
PHASE25_SATISFYING_SEMANTICS_PATH = (
    REPO_ROOT / "tests/test_phase25_satisfying_semantics.py"
)
SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice3_plan_status_and_links_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 29 Slice 3 is complete as aggregate-surface freeze contract "
        "and static audit work only",
        "docs/spec/v02-aggregate-surface-freeze-v1.md",
        "tests/test_phase29_v02_aggregate_surface_freeze.py",
        "Status: complete as aggregate-surface freeze contract and static "
        "audit work only",
        "uv run pytest tests/test_phase29_v02_aggregate_surface_freeze.py",
        "uv run pytest tests/test_phase29_v02_deferred_feature_register.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/validate.py",
        "Freeze v0.2 aggregate surface",
    ):
        assert required in plan

    for later_slice in (
        "### Slice 4: Core Type System Gap Matrix Status: planned only",
        "### Slice 5: v0.2 Exit Criteria And Validation Strategy Status: planned only",
        "### Slice 6: Completion Audit And Status Lock Status: planned only",
    ):
        assert later_slice in plan


def test_freeze_spec_boundary_is_docs_static_audit_only() -> None:
    spec = _normalized(FREEZE_SPEC_PATH)

    assert FREEZE_SPEC_PATH.is_file()
    for required in (
        "Phase 29 Slice 3 is complete as an aggregate-surface freeze contract "
        "and static audit slice only",
        "For v0.2, the Phase 19 through Phase 28 aggregate surface is frozen "
        "except for bug fixes and audit-only clarifications",
        "It does not authorize implementation",
        "source behavior changes",
        "grammar changes",
        "generated ANTLR changes",
        "semantic behavior changes",
        "aggregate behavior changes",
        "IR behavior changes",
        "SQL lowering changes",
        "CLI behavior changes",
        "JSON behavior or schema changes",
        "diagnostic behavior changes",
        "fixture or golden changes",
        "public MySQL API expansion",
        "JSON v2",
        "new aggregate features",
    ):
        assert required in spec


def test_complete_current_accepted_surface_is_frozen() -> None:
    spec = _normalized(FREEZE_SPEC_PATH)

    for required in (
        "`count()`",
        "`count(field)`",
        "`count(source.field)`",
        "`count_distinct(field)`",
        "`count_distinct(source.field)`",
        "`sum(field)`",
        "`sum(source.field)`",
        "`avg(field)`",
        "`avg(source.field)`",
        "`min(field)`",
        "`min(source.field)`",
        "`max(field)`",
        "`max(source.field)`",
        "`Int not null`",
        "Grouped aggregate projections remain part of the v0.2 surface",
        "Current Phase 25 `satisfying:` behavior is frozen",
        "Current Phase 27 grouped selected-output `order by` behavior is frozen",
        "Phase 26 accepted selected `sum(...)` and `avg(...)` numeric expression",
        "Phase 28 accepted Int and Float numeric literal leaves",
    ):
        assert required in spec


def test_count_distinct_text_transform_subset_is_included_and_grounded() -> None:
    spec = _normalized(FREEZE_SPEC_PATH)
    phase26_plan = _normalized(PHASE26_PLAN_PATH)
    phase26_semantics = _read(PHASE26_TEXT_TRANSFORM_SEMANTICS_PATH)

    for required in (
        "current bounded `count_distinct(...)` Text transform subset from Phase 26",
        "chains composed only of `lower(...)` and `trim(...)` over exactly one "
        "Text field leaf",
        "`count_distinct(lower(field))`",
        "`count_distinct(trim(field))`",
        "`count_distinct(lower(trim(field)))`",
        "`count_distinct(trim(lower(field)))`",
        "single-input qualified forms such as `count_distinct(lower(source.field))`",
        "This subset does not generalize `count_distinct(expression)`",
        "non-Text leaves",
        "multiple field leaves",
        "`len(...)`",
        "`matches(...)`",
        "arbitrary scalar calls",
        "nested aggregates",
    ):
        assert required in spec

    for evidence in (
        "`count_distinct` Text transform",
        "count_distinct(Text transform expression) -> Int not null",
        "`lower` / `trim` Text transform expression arguments over exactly one",
        "count_distinct(lower(status))",
        "count_distinct(trim(status))",
        "count_distinct(lower(trim(status)))",
        "count_distinct(trim(lower(status)))",
        "count_distinct(lower(orders.status))",
    ):
        assert evidence in phase26_plan or evidence in phase26_semantics


def test_decimal_extrema_surface_is_included_and_grounded() -> None:
    spec = _normalized(FREEZE_SPEC_PATH)
    phase24_plan = _normalized(PHASE24_PLAN_PATH)
    decimal_semantics = _read(PHASE24_DECIMAL_SEMANTICS_PATH)
    decimal_ir = _read(PHASE24_DECIMAL_IR_PATH)
    decimal_sql = _read(PHASE24_DECIMAL_SQL_PATH)
    aggregate_source = _read(SEMANTIC_AGGREGATES_PATH)

    for required in (
        "`sum(Decimal)`",
        "`avg(Decimal)`",
        "`min(Decimal)`",
        "`max(Decimal)`",
        "Decimal aggregate results remain logical Pietto `Decimal nullable`",
        "current direct-field extrema type surface includes `Int`, `Float`, "
        "`Decimal`, `Date`, and `Timestamp`",
    ):
        assert required in spec

    for evidence in (
        "`sum(Decimal)`, `avg(Decimal)`, `min(Decimal)`, and `max(Decimal)`",
        "`MIN`, and `MAX` without casts",
        "Decimal aggregate results are logical Pietto `Decimal nullable` values",
    ):
        assert evidence in phase24_plan

    for evidence in (
        "smallest_amount = min(amount)",
        "largest_amount = max(amount)",
        "smallest_amount = min(orders.amount)",
        "largest_amount = max(orders.amount)",
    ):
        assert evidence in decimal_semantics

    for evidence in (
        '"min"',
        '"max"',
        '"Decimal"',
    ):
        assert evidence in decimal_ir

    for evidence in (
        "MIN",
        "MAX",
        "Decimal",
    ):
        assert evidence in decimal_sql

    assert "def is_supported_extrema_argument(value_type: ValueType) -> bool:" in (
        aggregate_source
    )
    for evidence in ("Int", "Float", "Decimal", "Date", "Timestamp"):
        assert evidence in aggregate_source


def test_satisfying_boundary_matches_current_phase25_contract() -> None:
    spec = _normalized(FREEZE_SPEC_PATH)
    phase25_plan = _normalized(PHASE25_PLAN_PATH)
    phase25_semantics = _read(PHASE25_SATISFYING_SEMANTICS_PATH)

    for required in (
        "`where` remains row-level pre-aggregate filtering",
        "`satisfying:` is GROUP BY-only result-level filtering lowered as `HAVING`",
        "`satisfying:` resolves names only against selected output names",
        "referenced selected outputs must be group-key projection outputs or "
        "supported aggregate projection outputs under the current implementation",
        "renamed outputs expose the output alias",
        "no-GROUP `satisfying:` remains rejected",
        "row-level input fields that are not selected outputs remain rejected",
        "dotted references inside `satisfying:` remain rejected",
        "computed scalar projection outputs inside `satisfying:` remain deferred",
        "direct aggregate calls inside `satisfying:` remain rejected",
        "unsupported predicate forms remain rejected",
    ):
        assert required in spec

    for evidence in (
        "`where` remains pre-aggregate input-row filtering",
        "The MVP satisfying scope is select output names only",
        "The MVP is GROUP BY-only",
        "direct aggregate calls inside `satisfying`",
        "dotted field references inside satisfying",
        "row-level non-group field references inside satisfying",
    ):
        assert evidence in phase25_plan

    for evidence in (
        "test_grouped_satisfying_over_aggregate_alias_is_accepted",
        "test_grouped_satisfying_over_group_key_alias_is_accepted",
        "test_no_group_satisfying_is_rejected",
        "test_input_field_reference_in_satisfying_must_use_select_output",
        "test_computed_projection_output_in_satisfying_is_deferred",
        "test_aggregate_calls_inside_satisfying_use_invalid_context_diagnostic",
        "test_satisfying_resolves_aggregate_expression_projection_alias",
    ):
        assert evidence in phase25_semantics


def test_rejected_v02_aggregate_expansions_are_locked() -> None:
    spec = _normalized(FREEZE_SPEC_PATH)

    for rejected in (
        "`count(expression)`",
        "generalized `count_distinct(expression)` beyond direct fields and "
        "lower/trim Text transform chains over one Text field",
        "`min(expression)` beyond direct fields",
        "`max(expression)` beyond direct fields",
        "nested aggregates",
        "aggregate projection composition such as `sum(x) + 1`",
        "literal-only aggregate expressions such as `sum(1)` and `avg(1)`",
        "division or modulo aggregate expression arguments",
        "arbitrary scalar calls inside aggregate arguments",
        "window functions",
        "aggregate filters",
        "aggregate internal ordering",
        "arbitrary grouped `ORDER BY` expressions",
        "ordinal ordering",
        "broad `ORDER BY` / `LIMIT` redesign",
        "new aggregate functions",
        "generic aggregate modifiers",
    ):
        assert rejected in spec


def test_deferred_register_cross_link_preserves_aggregate_freeze_decision() -> None:
    register = _normalized(REGISTER_PATH)
    aggregate_row = next(
        line
        for line in _read(REGISTER_PATH).splitlines()
        if line.startswith("| Aggregate expansion |")
    )

    assert "docs/spec/v02-aggregate-surface-freeze-v1.md" in register
    assert "| bug fixes only |" in aggregate_row
    assert "generalized `count_distinct(expression)`" in aggregate_row
    assert "does not expand the aggregate surface" in aggregate_row


def test_forbidden_scope_is_not_authorized() -> None:
    plan_and_spec = f"{_normalized(PLAN_PATH)} {_normalized(FREEZE_SPEC_PATH)}"

    for required in (
        "no source implementation",
        "no aggregate expansion",
        "no new aggregate diagnostics",
        "no fixture or golden changes",
        "no diagnostic behavior changes",
        "no source implementation, grammar, generated ANTLR, AST, parser, "
        "runtime, project, relationship/JOIN, schema introspection, "
        "type-system, dependency, lockfile, package metadata, CI, or public "
        "MySQL API changes",
    ):
        assert required in plan_and_spec

    for forbidden in (
        "Slice 3 implements aggregate expansion",
        "Slice 3 implements JSON v2",
        "Slice 3 changes diagnostic behavior",
        "Slice 3 changes SQL lowering",
        "Slice 3 changes semantic behavior",
        "Slice 3 adds public MySQL API",
        "Slice 3 adds a new aggregate feature",
        "DateTime primitive is allowed",
        "Currency primitive is allowed",
        "Money primitive is allowed",
    ):
        assert forbidden not in plan_and_spec
