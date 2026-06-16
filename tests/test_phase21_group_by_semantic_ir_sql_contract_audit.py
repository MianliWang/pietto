from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-21-group-by-contract-planning.md"


def _read() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized() -> str:
    return " ".join(_read().split())


def test_phase21_slice3_contract_status_is_documented() -> None:
    plan = _normalized()

    for required in (
        "Phase 21 Slice 3 is complete as GROUP BY semantic, IR, SQL, and diagnostics contract work only",
        "These slices are docs/audit only",
        "They do not implement GROUP BY or any compiler behavior",
        "Slice 3 records the future GROUP BY semantic, IR, SQL, and diagnostic contract",
        "It remains docs/audit only and reserves no new diagnostic codes",
    ):
        assert required in plan


def test_future_slice_plan_is_full_group_by_mvp_sequence() -> None:
    plan = _normalized()

    for required in (
        "Slice 1: Candidate Decision**: complete",
        "Slice 2: Syntax And Clause-Scope Contract**: complete as docs/audit only",
        "Slice 3: Semantic / IR / SQL / Diagnostics Contract**: current docs/audit-only slice",
        "Slice 4: Parser + AST parse-only implementation",
        "expected to begin parse-only implementation after the Slice 3 contract is complete",
        "Slice 4 is not a completion audit",
        "Slice 5: Semantic grouped relation validation and grouped output schema",
        "Slice 6: IR group key lowering",
        "Slice 7: PostgreSQL/MySQL SQL lowering and goldens",
        "Slice 8: CLI / invalid-shape hardening / no-regression checks",
        "Slice 9: GROUP BY completion audit",
    ):
        assert required in plan

    assert "Slice 4: Completion Audit" not in plan
    assert "Slice 4: Completion Audit And Status Lock" not in plan


def test_grouped_semantic_mode_and_scope_split_are_locked() -> None:
    plan = _normalized()

    for required in (
        "a relation is grouped when a future parsed AST contains a non-empty `group by:` key list",
        "`where` remains input row scope and filters rows before grouping",
        "`select` observes grouped result scope",
        "may project only declared group keys and direct aggregate projections",
        "result predicates, HAVING-like user syntax, and grouped `order by` remain deferred",
    ):
        assert required in plan


def test_group_key_identity_duplicates_and_unknown_cascades_are_locked() -> None:
    plan = _normalized()

    for required in (
        "valid bare field keys and single-input qualified field keys compare by resolved input field identity",
        "in single-input scope, `status` and `orders.status` are equivalent",
        "both resolve to the same input field",
        "duplicate group keys diagnose the later duplicate key",
        "preserve the first source-ordered key",
        "unknown group fields emit the primary unknown group field diagnostic",
        "suppress secondary invalid-form, duplicate-key, and non-grouped-projection cascades",
    ):
        assert required in plan


def test_grouped_select_rules_are_locked() -> None:
    plan = _normalized()

    for required in (
        "group key projection is allowed when the projection expression resolves to a declared group key",
        "aggregate projection is allowed when it is a direct aggregate call in the Phase 20 aggregate surface",
        "aggregate projection requires an explicit alias",
        "non-grouped plain field projection is rejected",
        "scalar expressions involving group keys, such as `label = lower(status)`, are deferred or rejected for v1",
        "pure grouping or distinct-style output without any aggregate remains deferred",
    ):
        assert required in plan


def test_semantic_output_schema_rules_are_locked() -> None:
    plan = _normalized()

    for required in (
        "group key projections preserve the input field type and nullability",
        "aliased group key projections preserve the input field type and nullability",
        "`count() -> Int not null`",
        "`sum(Int) -> Int nullable`",
        "`sum(Float) -> Float nullable`",
        "`avg(Int) -> Float nullable`",
        "`avg(Float) -> Float nullable`",
        "invalid grouped projections with stable output names publish unknown schema fields",
        "invalid unaliased projections suppress output fields",
    ):
        assert required in plan


def test_future_ir_group_keys_direction_is_locked() -> None:
    plan = _normalized()

    for required in (
        "future `RelationIR` should add `group_keys: tuple[FieldRefIR, ...] = ()`",
        "group keys should reuse `FieldRefIR`",
        "rather than introduce a separate `GroupKeyIR` for v1",
        "lowered group keys preserve accepted unique key source order",
        "an empty `group_keys` tuple preserves existing no-GROUP IR bytes and behavior",
    ):
        assert required in plan


def test_future_sql_shape_and_grouped_order_by_deferral_are_locked() -> None:
    text = _read()
    plan = _normalized()

    assert "SELECT\nFROM\nWHERE\nGROUP BY\nLIMIT" in text
    for required in (
        "Grouped `ORDER BY` remains deferred in v1",
        "render `GROUP BY` after `WHERE` and before `LIMIT`",
        "using the existing field-rendering and identifier-quoting rules",
        "Existing no-GROUP SQL bytes remain unchanged when `group_keys == ()`",
    ):
        assert required in plan


def test_malformed_grouped_ir_fail_closed_policy_is_locked() -> None:
    plan = _normalized()

    for required in (
        "Malformed grouped IR must fail closed with backend diagnostics",
        "rather than emit partial unsafe SQL",
        "unresolved group fields",
        "duplicate or non-field group keys",
        "grouped `order_by`",
        "unsupported aggregate shapes",
        "cannot be rendered deterministically",
    ):
        assert required in plan


def test_diagnostic_categories_only_no_codes_reserved() -> None:
    plan = _normalized()

    for required in (
        "Slice 3 diagnostic categories are descriptive only",
        "Future implementation may define diagnostic codes only when semantic behavior is authorized",
        "invalid group key expression",
        "unknown group field",
        "duplicate group key",
        "aggregate in group key",
        "non-grouped projection",
        "scalar group-key expression deferred",
        "grouped `order by` deferred",
        "grouped pure distinct output deferred",
        "malformed grouped IR fail-closed backend diagnostic",
        "cascade suppression for unknown group keys and unknown aggregate arguments",
    ):
        assert required in plan


def test_slice3_hard_non_goals_remain_locked() -> None:
    plan = _normalized()

    for required in (
        "Phase 21 Slice 3 does not implement or authorize",
        "GROUP BY implementation",
        "grammar or source syntax changes",
        "generated ANTLR changes",
        "parser or AST changes",
        "semantic model changes",
        "Semantic IR model, export, builder, or lowering changes",
        "PostgreSQL or MySQL SQL renderer changes",
        "CLI, JSON, or public API changes",
        "fixture, SQL golden, or `scripts/check_goldens.py` changes",
        "new diagnostic codes",
        "SQL HAVING user syntax",
        "`satisfying`, `filter`, post-select `where`, or `such that` implementation",
        "relationship-driven query behavior",
        "aggregate expression argument implementation",
        "Decimal aggregate semantics",
        "rollup, cube, or grouping sets",
        "window functions",
        "nested results",
        "runtime or database execution",
    ):
        assert required in plan


def test_plan_does_not_claim_group_by_is_implemented() -> None:
    plan = _normalized()

    forbidden_claims = (
        "GROUP BY is implemented",
        "implements GROUP BY",
        "GROUP BY implementation is complete",
        "Phase 21 implements GROUP BY",
    )
    for forbidden in forbidden_claims:
        assert forbidden not in plan
