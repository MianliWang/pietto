from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import pietto.ir.model as ir_model
import pietto.semantic.window_analysis as window_analysis
from pietto import _window_identity
from pietto.ast_nodes import (
    AuthoredWindowFrameKind,
    LiteralExpr,
    OrderItem,
    QueryDef,
    WindowExpr,
    WindowFrameBoundKind,
    WindowFrameUnit,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.window_semantics import (
    AuthoredWindowSpecification,
    GroupsFrameInterval,
    GroupsFrameLogicalView,
    PeerComparisonEvidence,
    PeerComparisonOutcome,
    PeerGroupConstructionFailure,
    PeerGroupInterval,
    PeerGroupPartition,
    RangeFrameBoundRole,
    RangeFrameLogicalView,
    RowsFramePositionInterval,
    ValidatedFrame,
    ValidatedWindowSpecification,
    WindowFrameApplicability,
    WindowFrameEmptinessClassification,
    WindowFunctionFramePolicy,
    WindowFunctionFramePolicyKind,
    WindowSpecificationValidationFailure,
    WindowValidationIssueKind,
    authored_window_specification_from_ast,
    build_peer_group_partition,
    groups_frame_interval,
    range_frame_logical_view,
    resolve_authored_window_specification,
    resolve_range_current_row_boundary,
    rows_frame_position_interval,
    validate_resolved_window_specification,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase60-slice6-groups-peer-semantics-v1.md"
FRAME_IDENTITY = _window_identity.WindowFunctionIdentity(
    namespace=("slice6",),
    name="group_value_contract",
    role=_window_identity.WindowFunctionRole.WINDOW_FUNCTION,
)
FRAME_POLICY = WindowFunctionFramePolicy(
    identity=FRAME_IDENTITY,
    kind=WindowFunctionFramePolicyKind.FRAME_SENSITIVE,
)
BOUND_CASES = (
    ("unbounded preceding", WindowFrameBoundKind.UNBOUNDED_PRECEDING, None),
    ("2 preceding", WindowFrameBoundKind.OFFSET_PRECEDING, 2),
    ("current row", WindowFrameBoundKind.CURRENT_ROW, None),
    ("3 following", WindowFrameBoundKind.OFFSET_FOLLOWING, 3),
    ("unbounded following", WindowFrameBoundKind.UNBOUNDED_FOLLOWING, None),
)
CURRENT_FUNCTION_CALLS = (
    "row_number()",
    "rank()",
    "dense_rank()",
    "percent_rank()",
    "cume_dist()",
    "ntile(4)",
    "lag(value, 1, value)",
    "lead(value, 1, value)",
)


def _source(
    frame: str,
    *,
    call: str = "row_number()",
    order_by: tuple[str, ...] = ("id",),
) -> str:
    ordering = (
        "            order by:\n"
        + "".join(f"                {item}\n" for item in order_by)
        if order_by
        else ""
    )
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    secondary: Int not null\n"
        "    value: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query framed:\n"
        "    from rows\n"
        "    select:\n"
        f"        result = {call} window:\n"
        f"{ordering}"
        f"            {frame}\n"
    )


def _window(
    frame: str,
    *,
    call: str = "row_number()",
    order_by: tuple[str, ...] = ("id",),
) -> WindowExpr:
    parsed = parse_source(
        _source(frame, call=call, order_by=order_by),
        path="slice6.pietto",
    )
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert type(expression) is WindowExpr
    return expression


def _validated_frame(
    frame: str,
    *,
    order_by: tuple[str, ...] = ("id",),
) -> ValidatedWindowSpecification:
    expression = _window(frame, order_by=order_by)
    authored = authored_window_specification_from_ast(expression.spec)
    return _validated_authored(authored)


def _validated_authored(
    authored: AuthoredWindowSpecification,
) -> ValidatedWindowSpecification:
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    result = validate_resolved_window_specification(
        resolved,
        function_identity=FRAME_IDENTITY,
        function_policy=FRAME_POLICY,
        argument_expressions=(),
    )
    assert type(result) is ValidatedWindowSpecification
    assert type(result.frame) is ValidatedFrame
    return result


def _peer_partition(
    order_by: tuple[OrderItem, ...],
    outcomes: tuple[tuple[PeerComparisonOutcome, ...], ...],
    *,
    partition_size: int | None = None,
) -> PeerGroupPartition | PeerGroupConstructionFailure:
    size = len(outcomes) + 1 if partition_size is None else partition_size
    comparisons = tuple(
        PeerComparisonEvidence(
            left_row_position=left,
            right_row_position=left + 1,
            order_key_position=key,
            ordering=ordering,
            outcome=outcome,
        )
        for left, row_outcomes in enumerate(outcomes)
        for key, (ordering, outcome) in enumerate(
            zip(order_by, row_outcomes, strict=True)
        )
    )
    return build_peer_group_partition(
        partition_size=size,
        order_by=order_by,
        comparisons=comparisons,
    )


def _three_unequal_groups(order_by: tuple[OrderItem, ...]) -> PeerGroupPartition:
    outcomes = (
        (PeerComparisonOutcome.EQUAL,),
        (PeerComparisonOutcome.EQUAL,),
        (PeerComparisonOutcome.NOT_EQUAL,),
        (PeerComparisonOutcome.NOT_EQUAL,),
        (PeerComparisonOutcome.EQUAL,),
        (PeerComparisonOutcome.EQUAL,),
        (PeerComparisonOutcome.EQUAL,),
    )
    result = _peer_partition(order_by, outcomes)
    assert type(result) is PeerGroupPartition
    return result


@pytest.mark.parametrize(("source", "kind", "offset"), BOUND_CASES)
def test_every_groups_bound_spelling_reaches_existing_frame_model(
    source: str,
    kind: WindowFrameBoundKind,
    offset: int | None,
) -> None:
    shorthand = _window(f"groups {source}").spec.frame
    as_start = _window(f"groups between {source} and unbounded following").spec.frame
    as_end = _window(f"groups between unbounded preceding and {source}").spec.frame
    assert shorthand.kind is AuthoredWindowFrameKind.SHORTHAND
    assert as_start.kind is AuthoredWindowFrameKind.BETWEEN
    assert as_end.kind is AuthoredWindowFrameKind.BETWEEN
    assert all(
        frame.unit is WindowFrameUnit.GROUPS for frame in (shorthand, as_start, as_end)
    )
    assert shorthand.start is not None and shorthand.start.kind is kind
    assert as_start.start is not None and as_start.start.kind is kind
    assert as_end.end is not None and as_end.end.kind is kind
    for bound in (shorthand.start, as_start.start, as_end.end):
        if offset is None:
            assert bound.offset is None
        else:
            assert type(bound.offset) is LiteralExpr
            assert bound.offset.value == offset


def test_peer_groups_require_complete_multi_key_comparison_evidence() -> None:
    validated = _validated_frame(
        "groups current row",
        order_by=("id asc", "secondary desc"),
    )
    order_by = validated.resolved.order_by
    outcomes = (
        (PeerComparisonOutcome.EQUAL, PeerComparisonOutcome.EQUAL),
        (PeerComparisonOutcome.EQUAL, PeerComparisonOutcome.NOT_EQUAL),
        (PeerComparisonOutcome.EQUAL, PeerComparisonOutcome.EQUAL),
    )
    result = _peer_partition(order_by, outcomes)
    assert type(result) is PeerGroupPartition
    assert tuple((group.start, group.stop) for group in result.groups) == (
        (0, 2),
        (2, 4),
    )
    assert tuple(result.groups[0].positions) == (0, 1)
    assert tuple(result.groups[1].positions) == (2, 3)
    assert len(result.comparisons) == 6
    assert all(
        comparison.ordering is order_by[comparison.order_key_position]
        for comparison in result.comparisons
    )


def test_unresolved_phase64_comparison_produces_no_partial_groups() -> None:
    validated = _validated_frame("groups current row")
    order_by = validated.resolved.order_by
    result = _peer_partition(
        order_by,
        (
            (PeerComparisonOutcome.EQUAL,),
            (PeerComparisonOutcome.UNRESOLVED,),
        ),
    )
    assert type(result) is PeerGroupConstructionFailure
    assert len(result.unresolved) == 1
    assert result.unresolved[0].outcome is PeerComparisonOutcome.UNRESOLVED
    assert not hasattr(result, "groups")


def test_non_equal_key_resolves_peer_false_despite_other_unresolved_key() -> None:
    validated = _validated_frame(
        "groups current row",
        order_by=("id", "secondary"),
    )
    result = _peer_partition(
        validated.resolved.order_by,
        (
            (
                PeerComparisonOutcome.NOT_EQUAL,
                PeerComparisonOutcome.UNRESOLVED,
            ),
        ),
    )
    assert type(result) is PeerGroupPartition
    assert tuple((group.start, group.stop) for group in result.groups) == (
        (0, 1),
        (1, 2),
    )


def test_peer_comparison_matrix_rejects_missing_or_reordered_authority() -> None:
    validated = _validated_frame(
        "groups current row",
        order_by=("id", "secondary"),
    )
    order_by = validated.resolved.order_by
    comparison = PeerComparisonEvidence(
        left_row_position=0,
        right_row_position=1,
        order_key_position=0,
        ordering=order_by[0],
        outcome=PeerComparisonOutcome.EQUAL,
    )
    with pytest.raises(ValueError, match="cover every adjacent row and key"):
        build_peer_group_partition(
            partition_size=2,
            order_by=order_by,
            comparisons=(comparison,),
        )
    with pytest.raises(ValueError, match="complete-key order"):
        build_peer_group_partition(
            partition_size=2,
            order_by=order_by,
            comparisons=(
                replace(comparison, order_key_position=1, ordering=order_by[1]),
                comparison,
            ),
        )


def test_no_order_by_builds_one_partition_wide_peer_group() -> None:
    result = build_peer_group_partition(
        partition_size=5,
        order_by=(),
        comparisons=(),
    )
    assert type(result) is PeerGroupPartition
    assert tuple(
        (group.group_index, group.start, group.stop) for group in result.groups
    ) == ((0, 0, 5),)
    assert tuple(result.groups[0].positions) == (0, 1, 2, 3, 4)


def test_ordering_direction_does_not_redefine_peer_equality() -> None:
    ascending = _validated_frame("groups current row", order_by=("id asc",))
    descending = _validated_frame("groups current row", order_by=("id desc",))
    outcomes = (
        (PeerComparisonOutcome.EQUAL,),
        (PeerComparisonOutcome.NOT_EQUAL,),
        (PeerComparisonOutcome.EQUAL,),
    )
    asc_groups = _peer_partition(ascending.resolved.order_by, outcomes)
    desc_groups = _peer_partition(descending.resolved.order_by, outcomes)
    assert type(asc_groups) is PeerGroupPartition
    assert type(desc_groups) is PeerGroupPartition
    assert tuple((group.start, group.stop) for group in asc_groups.groups) == tuple(
        (group.start, group.stop) for group in desc_groups.groups
    )


def test_groups_current_row_selects_the_complete_current_peer_group() -> None:
    validated = _validated_frame("groups current row")
    peers = _three_unequal_groups(validated.resolved.order_by)
    view = GroupsFrameLogicalView(specification=validated, peers=peers)
    singleton = groups_frame_interval(view, current_position=3)
    four_rows = groups_frame_interval(view, current_position=5)
    assert tuple(singleton.group_indices) == (1,)
    assert tuple(singleton.row_positions) == (3,)
    assert tuple(four_rows.group_indices) == (2,)
    assert tuple(four_rows.row_positions) == (4, 5, 6, 7)


def test_groups_offsets_count_groups_not_unequal_row_counts() -> None:
    validated = _validated_frame("groups between 1 preceding and 1 following")
    peers = _three_unequal_groups(validated.resolved.order_by)
    interval = groups_frame_interval(
        GroupsFrameLogicalView(specification=validated, peers=peers),
        current_position=3,
    )
    assert tuple(interval.group_indices) == (0, 1, 2)
    assert tuple(interval.row_positions) == tuple(range(8))
    assert (interval.row_start, interval.row_stop) == (0, 8)


@pytest.mark.parametrize(
    ("frame", "current", "groups", "rows"),
    (
        ("groups between 3 preceding and 1 preceding", 0, (), ()),
        ("groups between 1 following and 2 following", 5, (), ()),
        ("groups current row", 5, (2,), (4, 5, 6, 7)),
    ),
)
def test_groups_clipping_is_group_interval_intersection(
    frame: str,
    current: int,
    groups: tuple[int, ...],
    rows: tuple[int, ...],
) -> None:
    validated = _validated_frame(frame)
    peers = _three_unequal_groups(validated.resolved.order_by)
    interval = groups_frame_interval(
        GroupsFrameLogicalView(specification=validated, peers=peers),
        current_position=current,
    )
    assert tuple(interval.group_indices) == groups
    assert tuple(interval.row_positions) == rows
    assert interval.empty is (not groups)


def test_legal_empty_groups_is_not_structural_invalidity() -> None:
    validated = _validated_frame("groups between 1 preceding and 3 preceding")
    assert type(validated.frame) is ValidatedFrame
    assert validated.frame.classification is (
        WindowFrameEmptinessClassification.POSSIBLY_EMPTY
    )
    peers = _three_unequal_groups(validated.resolved.order_by)
    interval = groups_frame_interval(
        GroupsFrameLogicalView(specification=validated, peers=peers),
        current_position=5,
    )
    assert (interval.start_group, interval.stop_group) == (1, 0)
    assert interval.empty


@pytest.mark.parametrize("offset", ("-1", "true", "1.5", "id"))
def test_groups_offsets_require_nonnegative_integer_literal_evidence(
    offset: str,
) -> None:
    validated = _validated_frame(f"groups {offset} preceding")
    peers = _three_unequal_groups(validated.resolved.order_by)
    with pytest.raises(ValueError, match="nonnegative integer literal evidence"):
        groups_frame_interval(
            GroupsFrameLogicalView(specification=validated, peers=peers),
            current_position=3,
        )


def test_range_current_row_consumes_the_same_canonical_peer_authority() -> None:
    range_expression = _window("range current row")
    authored = authored_window_specification_from_ast(range_expression.spec)
    range_validated = _validated_authored(authored)
    groups_authored = replace(
        authored,
        frame=replace(authored.frame, unit=WindowFrameUnit.GROUPS),
    )
    groups_validated = _validated_authored(groups_authored)
    assert range_validated.resolved.order_by is groups_validated.resolved.order_by

    range_view = range_frame_logical_view(range_validated)
    assert type(range_view) is RangeFrameLogicalView
    peers = _three_unequal_groups(range_view.order_by)
    groups_view = GroupsFrameLogicalView(
        specification=groups_validated,
        peers=peers,
    )
    range_start = resolve_range_current_row_boundary(
        range_view,
        role=RangeFrameBoundRole.START,
        peers=peers,
        current_position=5,
    )
    range_end = resolve_range_current_row_boundary(
        range_view,
        role=RangeFrameBoundRole.END,
        peers=peers,
        current_position=5,
    )
    groups_interval = groups_frame_interval(groups_view, current_position=5)
    assert (range_start, range_end + 1) == (
        groups_interval.row_start,
        groups_interval.row_stop,
    )


def test_rows_current_row_remains_one_physical_position() -> None:
    validated = _validated_frame("rows current row")
    assert type(validated.frame) is ValidatedFrame
    interval = rows_frame_position_interval(
        validated.frame,
        partition_size=8,
        current_position=5,
    )
    assert type(interval) is RowsFramePositionInterval
    assert tuple(interval.positions) == (5,)


def test_peer_authority_exposes_exclude_readiness_without_excluding() -> None:
    validated = _validated_frame("groups current row")
    peers = _three_unequal_groups(validated.resolved.order_by)
    group = peers.group_for_position(5)
    current_position = 5
    assert tuple(group.positions) == (4, 5, 6, 7)
    assert (group.start, current_position, group.stop) == (4, 5, 8)
    assert not hasattr(peers, "excluded")


@pytest.mark.parametrize("call", CURRENT_FUNCTION_CALLS)
def test_every_current_function_rejects_authored_groups_after_recognition(
    call: str,
) -> None:
    parsed = parse_source(
        _source("groups current row", call=call), path="policy.pietto"
    )
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    expression = cast(QueryDef, parsed.ast.definitions[-1]).select_items[0].expression
    assert type(expression) is WindowExpr
    semantic = analyze(parsed.ast)
    matching = tuple(item for item in semantic.diagnostics if item.code == "PIE-S2104")
    assert len(matching) == 1
    assert matching[0].message == (
        f"Invalid window frame for function {expression.identity.name}: "
        "explicit GROUPS frame is not allowed"
    )
    validation = window_analysis._validate_recognized_window_specification(expression)
    assert type(validation) is WindowSpecificationValidationFailure
    assert validation.resolved.authored.frame is expression.spec.frame
    assert tuple(issue.kind for issue in validation.issues) == (
        WindowValidationIssueKind.EXPLICIT_FRAME_FORBIDDEN,
    )


def test_groups_is_lazy_and_adds_no_ir_or_sql_renderer() -> None:
    assert tuple(field.name for field in fields(PeerGroupInterval)) == (
        "group_index",
        "start",
        "stop",
    )
    assert tuple(field.name for field in fields(GroupsFrameLogicalView)) == (
        "specification",
        "peers",
    )
    assert tuple(field.name for field in fields(GroupsFrameInterval)) == (
        "peers",
        "start_group",
        "stop_group",
    )
    assert not hasattr(ir_model, "GroupsFrameIR")
    for relative in (
        "src/pietto/sql/expressions.py",
        "src/pietto/sql/mysql_expressions.py",
    ):
        tree = ast.parse((REPO_ROOT / relative).read_text(encoding="utf-8"))
        names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        }
        assert not any("groups_frame" in name.lower() for name in names)


def test_groups_keyword_remains_contextual_outside_frame_clause() -> None:
    source = (
        "shape Row:\n"
        "    groups: Int not null\n"
        'source groups: Row is postgres.table("groups")\n'
        "query selected:\n"
        "    from groups\n"
        "    select:\n"
        "        groups\n"
    )
    parsed = parse_source(source)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None


def test_slice6_spec_locks_peer_groups_lowering_and_later_owners() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "peer(a, b) iff every resolved ordering-key comparison is EQUAL",
        "no ORDER BY produces one partition-wide peer group",
        "GROUPS <bound>",
        "GROUPS BETWEEN <start> AND <end>",
        "GROUPS CURRENT ROW selects the complete current peer group",
        "GROUPS offsets count peer groups, not rows",
        "RANGE CURRENT ROW consumes the same PeerGroupPartition",
        "Phase 64 owns typed comparison, collation, NULL, NaN, and coercion details",
        "Slice 7 owns EXCLUDE effects",
        "Slice 9 owns the first legal frame-sensitive callers and SQL activation",
        "A2/M17/D0",
        "Slice 7 is neither implemented nor authorized",
        "Add Phase 60 GROUPS and peer semantics",
    ):
        assert evidence in document
