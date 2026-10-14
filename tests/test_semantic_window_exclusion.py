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
    AuthoredWindowFrameExclusion,
    QueryDef,
    WindowExpr,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.window_semantics import (
    ExcludedFrameMembershipView,
    GroupsFrameLogicalView,
    PeerComparisonEvidence,
    PeerComparisonOutcome,
    PeerGroupConstructionFailure,
    PeerGroupPartition,
    RangeFrameBoundRole,
    RangeFrameLogicalView,
    ValidatedFrame,
    ValidatedWindowSpecification,
    WindowComponentOrigin,
    WindowFrameApplicability,
    WindowFrameEmptinessClassification,
    WindowFrameExclusion,
    WindowFunctionFramePolicy,
    WindowFunctionFramePolicyKind,
    WindowSpecificationValidationFailure,
    WindowValidationIssueKind,
    authored_window_specification_from_ast,
    build_peer_group_partition,
    exclude_frame_membership,
    groups_frame_interval,
    range_frame_logical_view,
    resolve_authored_window_specification,
    resolve_range_current_row_boundary,
    rows_frame_position_interval,
    validate_resolved_window_specification,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase60-slice7-exclude-semantics-v1.md"
FRAME_IDENTITY = _window_identity.WindowFunctionIdentity(
    namespace=("slice7",),
    name="exclude_value_contract",
    role=_window_identity.WindowFunctionRole.WINDOW_FUNCTION,
)
FRAME_POLICY = WindowFunctionFramePolicy(
    identity=FRAME_IDENTITY,
    kind=WindowFunctionFramePolicyKind.FRAME_SENSITIVE,
)
EXCLUSION_CASES = (
    (
        "no others",
        AuthoredWindowFrameExclusion.NO_OTHERS,
        WindowFrameExclusion.NO_OTHERS,
    ),
    (
        "current row",
        AuthoredWindowFrameExclusion.CURRENT_ROW,
        WindowFrameExclusion.CURRENT_ROW,
    ),
    ("group", AuthoredWindowFrameExclusion.GROUP, WindowFrameExclusion.GROUP),
    ("ties", AuthoredWindowFrameExclusion.TIES, WindowFrameExclusion.TIES),
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
        path="slice7.pietto",
    )
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert type(expression) is WindowExpr
    return expression


def _validated(
    frame: str,
    *,
    order_by: tuple[str, ...] = ("id",),
) -> ValidatedWindowSpecification:
    expression = _window(frame, order_by=order_by)
    authored = authored_window_specification_from_ast(expression.spec)
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    result = validate_resolved_window_specification(
        resolved,
        function_identity=FRAME_IDENTITY,
        function_policy=FRAME_POLICY,
    )
    assert type(result) is ValidatedWindowSpecification
    assert type(result.frame) is ValidatedFrame
    return result


def _peer_authority(
    specification: ValidatedWindowSpecification,
    outcomes: tuple[PeerComparisonOutcome, ...],
    *,
    partition_size: int,
) -> PeerGroupPartition | PeerGroupConstructionFailure:
    order_by = specification.resolved.order_by
    if not order_by:
        assert outcomes == ()
        comparisons: tuple[PeerComparisonEvidence, ...] = ()
    else:
        assert len(order_by) == 1
        assert len(outcomes) == partition_size - 1
        comparisons = tuple(
            PeerComparisonEvidence(
                left_row_position=left,
                right_row_position=left + 1,
                order_key_position=0,
                ordering=order_by[0],
                outcome=outcome,
            )
            for left, outcome in enumerate(outcomes)
        )
    return build_peer_group_partition(
        partition_size=partition_size,
        order_by=order_by,
        comparisons=comparisons,
    )


def _three_row_current_group(
    specification: ValidatedWindowSpecification,
) -> PeerGroupPartition:
    result = _peer_authority(
        specification,
        (
            PeerComparisonOutcome.NOT_EQUAL,
            PeerComparisonOutcome.NOT_EQUAL,
            PeerComparisonOutcome.EQUAL,
            PeerComparisonOutcome.EQUAL,
            PeerComparisonOutcome.NOT_EQUAL,
            PeerComparisonOutcome.NOT_EQUAL,
            PeerComparisonOutcome.NOT_EQUAL,
        ),
        partition_size=8,
    )
    assert type(result) is PeerGroupPartition
    assert (result.group_for_position(3).start, result.group_for_position(3).stop) == (
        2,
        5,
    )
    return result


@pytest.mark.parametrize("unit", ("rows", "range", "groups"))
@pytest.mark.parametrize(
    ("source_mode", "authored_exclusion", "effective_exclusion"),
    EXCLUSION_CASES,
)
def test_all_exclude_modes_parse_into_existing_authored_and_resolved_models(
    unit: str,
    source_mode: str,
    authored_exclusion: AuthoredWindowFrameExclusion,
    effective_exclusion: WindowFrameExclusion,
) -> None:
    expression = _window(f"{unit} current row exclude {source_mode}")
    assert expression.spec.frame.exclusion is authored_exclusion
    authored = authored_window_specification_from_ast(expression.spec)
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    assert resolved.frame.authored is expression.spec.frame
    assert resolved.frame.origin is WindowComponentOrigin.LOCALLY_AUTHORED
    assert resolved.frame.exclusion is effective_exclusion


def test_omitted_exclusion_and_explicit_no_others_remain_authorship_distinct() -> None:
    omitted = _validated("rows current row")
    explicit = _validated("rows current row exclude no others")
    assert omitted.resolved.authored.frame.exclusion is (
        AuthoredWindowFrameExclusion.OMITTED
    )
    assert explicit.resolved.authored.frame.exclusion is (
        AuthoredWindowFrameExclusion.NO_OTHERS
    )
    assert omitted.resolved.frame.exclusion is WindowFrameExclusion.NO_OTHERS
    assert explicit.resolved.frame.exclusion is WindowFrameExclusion.NO_OTHERS
    assert omitted.resolved.authored.frame != explicit.resolved.authored.frame


def test_standalone_exclude_is_rejected_and_new_words_remain_contextual() -> None:
    standalone = parse_source(_source("exclude ties"))
    assert standalone.ast is None
    assert standalone.diagnostics

    contextual = parse_source(
        "shape Row:\n"
        "    exclude: Int not null\n"
        "    no: Int not null\n"
        "    others: Int not null\n"
        "    ties: Int not null\n"
        'source ties: Row is postgres.table("ties")\n'
        "query others:\n"
        "    from ties\n"
        "    select:\n"
        "        exclude\n"
        "        no\n"
    )
    assert contextual.diagnostics == ()
    assert contextual.ast is not None


@pytest.mark.parametrize(
    ("source_mode", "expected_positions", "expected_spans"),
    (
        ("no others", (1, 2, 3, 4, 5, 6), (range(1, 7),)),
        ("current row", (1, 2, 4, 5, 6), (range(1, 3), range(4, 7))),
        ("group", (1, 5, 6), (range(1, 2), range(5, 7))),
        ("ties", (1, 3, 5, 6), (range(1, 2), range(3, 4), range(5, 7))),
    ),
)
def test_exact_four_mode_truth_table_is_removal_only(
    source_mode: str,
    expected_positions: tuple[int, ...],
    expected_spans: tuple[range, ...],
) -> None:
    specification = _validated(
        f"rows between 2 preceding and 3 following exclude {source_mode}"
    )
    peers = _three_row_current_group(specification)
    result = exclude_frame_membership(
        specification,
        partition_size=8,
        base_positions=range(1, 7),
        current_position=3,
        peer_authority=peers,
    )
    assert type(result) is ExcludedFrameMembershipView
    assert tuple(result.positions) == expected_positions
    assert result.spans == expected_spans


@pytest.mark.parametrize("unit", ("rows", "range", "groups"))
def test_same_clipped_membership_and_peers_have_unit_independent_exclusion(
    unit: str,
) -> None:
    specification = _validated(
        f"{unit} between unbounded preceding and unbounded following exclude group"
    )
    peers = _three_row_current_group(specification)
    result = exclude_frame_membership(
        specification,
        partition_size=8,
        base_positions=range(0, 8),
        current_position=3,
        peer_authority=peers,
    )
    assert type(result) is ExcludedFrameMembershipView
    assert tuple(result.positions) == (0, 1, 5, 6, 7)


def test_rows_range_and_groups_base_owners_feed_exclusion_after_clipping() -> None:
    rows = _validated("rows between 2 preceding and 2 following exclude current row")
    rows_base = rows_frame_position_interval(
        cast(ValidatedFrame, rows.frame),
        partition_size=8,
        current_position=3,
    )
    rows_result = exclude_frame_membership(
        rows,
        partition_size=8,
        base_positions=rows_base.positions,
        current_position=3,
    )
    assert type(rows_result) is ExcludedFrameMembershipView
    assert tuple(rows_base.positions) == (1, 2, 3, 4, 5)
    assert tuple(rows_result.positions) == (1, 2, 4, 5)

    range_specification = _validated("range current row exclude current row")
    range_view = range_frame_logical_view(range_specification)
    assert type(range_view) is RangeFrameLogicalView
    range_peers = _three_row_current_group(range_specification)
    range_start = resolve_range_current_row_boundary(
        range_view,
        role=RangeFrameBoundRole.START,
        peers=range_peers,
        current_position=3,
    )
    range_stop = (
        resolve_range_current_row_boundary(
            range_view,
            role=RangeFrameBoundRole.END,
            peers=range_peers,
            current_position=3,
        )
        + 1
    )
    range_result = exclude_frame_membership(
        range_specification,
        partition_size=8,
        base_positions=range(range_start, range_stop),
        current_position=3,
    )
    assert type(range_result) is ExcludedFrameMembershipView
    assert (range_start, range_stop) == (2, 5)
    assert tuple(range_result.positions) == (2, 4)

    groups = _validated("groups current row exclude current row")
    groups_peers = _three_row_current_group(groups)
    groups_base = groups_frame_interval(
        GroupsFrameLogicalView(specification=groups, peers=groups_peers),
        current_position=3,
    )
    groups_result = exclude_frame_membership(
        groups,
        partition_size=8,
        base_positions=groups_base.row_positions,
        current_position=3,
    )
    assert type(groups_result) is ExcludedFrameMembershipView
    assert tuple(groups_base.row_positions) == (2, 3, 4)
    assert tuple(groups_result.positions) == (2, 4)


@pytest.mark.parametrize("unit", ("rows", "range", "groups"))
@pytest.mark.parametrize(
    ("source_mode", "expected"),
    (("current row", (0, 1, 3, 4)), ("group", ()), ("ties", (2,))),
)
def test_no_order_by_uses_one_partition_wide_peer_group(
    unit: str,
    source_mode: str,
    expected: tuple[int, ...],
) -> None:
    specification = _validated(
        f"{unit} between unbounded preceding and unbounded following "
        f"exclude {source_mode}",
        order_by=(),
    )
    peers = _peer_authority(specification, (), partition_size=5)
    assert type(peers) is PeerGroupPartition
    assert tuple((group.start, group.stop) for group in peers.groups) == ((0, 5),)
    result = exclude_frame_membership(
        specification,
        partition_size=5,
        base_positions=range(0, 5),
        current_position=2,
        peer_authority=peers,
    )
    assert type(result) is ExcludedFrameMembershipView
    assert tuple(result.positions) == expected


@pytest.mark.parametrize("source_mode", ("group", "ties"))
def test_group_and_ties_propagate_unresolved_peer_authority_fail_closed(
    source_mode: str,
) -> None:
    specification = _validated(
        "rows between unbounded preceding and unbounded following "
        f"exclude {source_mode}"
    )
    failure = _peer_authority(
        specification,
        (PeerComparisonOutcome.UNRESOLVED, PeerComparisonOutcome.EQUAL),
        partition_size=3,
    )
    assert type(failure) is PeerGroupConstructionFailure
    result = exclude_frame_membership(
        specification,
        partition_size=3,
        base_positions=range(0, 3),
        current_position=1,
        peer_authority=failure,
    )
    assert result is failure


@pytest.mark.parametrize(
    ("source_mode", "expected"),
    (("no others", (0, 1, 2)), ("current row", (0, 2))),
)
def test_no_others_and_current_row_do_not_require_peer_resolution(
    source_mode: str,
    expected: tuple[int, ...],
) -> None:
    specification = _validated(
        "rows between unbounded preceding and unbounded following "
        f"exclude {source_mode}"
    )
    failure = _peer_authority(
        specification,
        (PeerComparisonOutcome.UNRESOLVED, PeerComparisonOutcome.EQUAL),
        partition_size=3,
    )
    assert type(failure) is PeerGroupConstructionFailure
    result = exclude_frame_membership(
        specification,
        partition_size=3,
        base_positions=range(0, 3),
        current_position=1,
        peer_authority=failure,
    )
    assert type(result) is ExcludedFrameMembershipView
    assert result.peers is None
    assert tuple(result.positions) == expected


@pytest.mark.parametrize(
    ("source_mode", "expected"),
    (("current row", (1,)), ("group", ()), ("ties", ())),
)
def test_current_row_outside_base_frame_is_never_added(
    source_mode: str,
    expected: tuple[int, ...],
) -> None:
    specification = _validated(
        f"rows between 1 preceding and 1 preceding exclude {source_mode}"
    )
    peers = _peer_authority(
        specification,
        (
            PeerComparisonOutcome.NOT_EQUAL,
            PeerComparisonOutcome.EQUAL,
            PeerComparisonOutcome.EQUAL,
            PeerComparisonOutcome.NOT_EQUAL,
        ),
        partition_size=5,
    )
    assert type(peers) is PeerGroupPartition
    assert (peers.group_for_position(2).start, peers.group_for_position(2).stop) == (
        1,
        4,
    )
    result = exclude_frame_membership(
        specification,
        partition_size=5,
        base_positions=range(1, 2),
        current_position=2,
        peer_authority=peers,
    )
    assert type(result) is ExcludedFrameMembershipView
    assert tuple(result.positions) == expected
    assert 2 not in result.positions


def test_exclusion_can_empty_legal_frames_without_mutating_validation() -> None:
    rows = _validated("rows current row exclude current row")
    assert cast(ValidatedFrame, rows.frame).classification is (
        WindowFrameEmptinessClassification.ALWAYS_EMPTY
    )
    rows_base = rows_frame_position_interval(
        cast(ValidatedFrame, rows.frame),
        partition_size=4,
        current_position=2,
    )
    rows_result = exclude_frame_membership(
        rows,
        partition_size=4,
        base_positions=rows_base.positions,
        current_position=2,
    )
    assert type(rows_result) is ExcludedFrameMembershipView
    assert rows_result.frame is rows.frame
    assert tuple(rows_base.positions) == (2,)
    assert rows_result.empty

    groups = _validated("groups current row exclude group")
    assert cast(ValidatedFrame, groups.frame).classification is (
        WindowFrameEmptinessClassification.ALWAYS_EMPTY
    )
    peers = _three_row_current_group(groups)
    groups_base = groups_frame_interval(
        GroupsFrameLogicalView(specification=groups, peers=peers),
        current_position=3,
    )
    groups_result = exclude_frame_membership(
        groups,
        partition_size=8,
        base_positions=groups_base.row_positions,
        current_position=3,
        peer_authority=peers,
    )
    assert type(groups_result) is ExcludedFrameMembershipView
    assert groups_result.frame is groups.frame
    assert tuple(groups_base.row_positions) == (2, 3, 4)
    assert groups_result.empty


def test_exclusion_view_is_frozen_lazy_span_authority() -> None:
    specification = _validated("rows between 2 preceding and 3 following exclude ties")
    peers = _three_row_current_group(specification)
    base = range(1, 7)
    result = exclude_frame_membership(
        specification,
        partition_size=8,
        base_positions=base,
        current_position=3,
        peer_authority=peers,
    )
    assert type(result) is ExcludedFrameMembershipView
    assert tuple(field.name for field in fields(ExcludedFrameMembershipView)) == (
        "specification",
        "partition_size",
        "base_positions",
        "current_position",
        "peers",
        "spans",
    )
    assert result.base_positions is base
    assert result.peers is peers
    assert result.current_peer_group is peers.group_for_position(3)
    assert all(type(span) is range for span in result.spans)
    assert not hasattr(result, "rows")
    assert not hasattr(result, "members")
    assert not isinstance(result.positions, (list, tuple))
    assert tuple(result.positions) == (1, 3, 5, 6)
    with pytest.raises(ValueError, match="complete, ordered, and exact"):
        replace(result, spans=(range(1, 7),))
    with pytest.raises(TypeError, match="unit-range tuple"):
        replace(
            result,
            spans=(range(1, 2), range(3, 5, 2), range(5, 7)),
        )


def test_group_and_ties_require_matching_canonical_peer_authority() -> None:
    specification = _validated(
        "rows between unbounded preceding and unbounded following exclude group"
    )
    with pytest.raises(TypeError, match="canonical peer authority"):
        exclude_frame_membership(
            specification,
            partition_size=8,
            base_positions=range(0, 8),
            current_position=3,
        )
    mismatched = _peer_authority(
        specification,
        (
            PeerComparisonOutcome.NOT_EQUAL,
            PeerComparisonOutcome.NOT_EQUAL,
            PeerComparisonOutcome.NOT_EQUAL,
        ),
        partition_size=4,
    )
    assert type(mismatched) is PeerGroupPartition
    with pytest.raises(ValueError, match="same partition size"):
        exclude_frame_membership(
            specification,
            partition_size=8,
            base_positions=range(0, 8),
            current_position=3,
            peer_authority=mismatched,
        )


@pytest.mark.parametrize("call", CURRENT_FUNCTION_CALLS)
def test_current_functions_recognize_exclude_then_reject_the_explicit_frame(
    call: str,
) -> None:
    parsed = parse_source(
        _source("rows current row exclude ties", call=call),
        path="policy.pietto",
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
        "explicit ROWS frame is not allowed"
    )
    validation = window_analysis._validate_recognized_window_specification(expression)
    assert type(validation) is WindowSpecificationValidationFailure
    assert tuple(issue.kind for issue in validation.issues) == (
        WindowValidationIssueKind.EXPLICIT_FRAME_FORBIDDEN,
    )


def test_lowering_filter_later_owner_and_public_boundaries_remain_exact() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "EXCLUDE NO OTHERS",
        "EXCLUDE CURRENT ROW",
        "EXCLUDE GROUP",
        "EXCLUDE TIES",
        "partition -> ordering -> peer groups -> base frame bounds -> partition clipping -> EXCLUDE -> function evaluation",
        "frame including EXCLUDE -> candidate rows -> aggregate FILTER selects aggregate inputs",
        "Slice 8 owns query-local named-window resolution and inheritance",
        "Slice 9 owns the first legal frame-sensitive functions and production explicit-frame SQL activation",
        "Slice 10 owns backend capability gating",
        "Add Phase 60 EXCLUDE semantics",
    ):
        assert evidence in document

    assert tuple(field.name for field in fields(ir_model.WindowSpecIR)) == (
        "partition_by",
        "order_by",
        "span",
        "frame",
    )
    assert hasattr(ir_model, "WindowFrameIR")
    assert not hasattr(ir_model, "ExcludedFrameIR")
    assert not hasattr(ir_model, "AggregateWindowCallIR")
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
        assert not any("exclude" in name.lower() for name in names)
