from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
from typing import cast

import pytest

import pietto.ir.model as ir_model
import pietto.semantic.window_analysis as window_analysis
import pietto.semantic.window_navigation_analysis as navigation_analysis
from pietto import _window_identity
from pietto.ast_nodes import (
    AuthoredWindowFrameKind,
    BinaryExpr,
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
    PeerComparisonEvidence,
    PeerComparisonOutcome,
    PeerGroupPartition,
    RangeFrameBoundRole,
    RangeFrameLogicalView,
    RangeOffsetArithmeticRequirement,
    RangeOffsetOrderingFailure,
    RangeOffsetOrientation,
    RangeOrderDirection,
    RangePeerBoundaryKind,
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
    range_frame_logical_view,
    resolve_authored_window_specification,
    resolve_range_current_row_boundary,
    rows_frame_position_interval,
    validate_resolved_window_specification,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase60-slice5-range-semantics-lowering-v1.md"
FRAME_IDENTITY = _window_identity.WindowFunctionIdentity(
    namespace=("slice5",),
    name="range_value_contract",
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
        "    delta: Int not null\n"
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
        path="slice5.pietto",
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
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    result = validate_resolved_window_specification(
        resolved,
        function_identity=FRAME_IDENTITY,
        function_policy=FRAME_POLICY,
        argument_expressions=expression.call.arguments,
    )
    assert type(result) is ValidatedWindowSpecification
    assert type(result.frame) is ValidatedFrame
    return result


def _peer_partition(
    order_by: tuple[OrderItem, ...],
    outcomes: tuple[tuple[PeerComparisonOutcome, ...], ...],
    *,
    partition_size: int = 5,
) -> PeerGroupPartition:
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
    result = build_peer_group_partition(
        partition_size=partition_size,
        order_by=order_by,
        comparisons=comparisons,
    )
    assert type(result) is PeerGroupPartition
    return result


@pytest.mark.parametrize(("source", "kind", "offset"), BOUND_CASES)
def test_every_range_bound_spelling_reaches_existing_authored_model(
    source: str,
    kind: WindowFrameBoundKind,
    offset: int | None,
) -> None:
    shorthand = _window(f"range {source}").spec.frame
    as_start = _window(f"range between {source} and unbounded following").spec.frame
    as_end = _window(f"range between unbounded preceding and {source}").spec.frame
    assert shorthand.kind is AuthoredWindowFrameKind.SHORTHAND
    assert as_start.kind is AuthoredWindowFrameKind.BETWEEN
    assert as_end.kind is AuthoredWindowFrameKind.BETWEEN
    assert all(
        frame.unit is WindowFrameUnit.RANGE for frame in (shorthand, as_start, as_end)
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


def test_range_offset_expression_and_shorthand_provenance_are_exact() -> None:
    expression = _window("range delta + 1 preceding")
    frame = expression.spec.frame
    assert frame.start is not None
    assert type(frame.start.offset) is BinaryExpr
    authored = authored_window_specification_from_ast(expression.spec)
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    assert authored.frame is frame
    assert authored.frame.start is frame.start
    assert resolved.frame.start is frame.start
    assert resolved.frame.end is not None
    assert resolved.frame.end.kind is WindowFrameBoundKind.CURRENT_ROW


def test_range_shorthand_and_between_remain_distinct() -> None:
    shorthand = _validated_frame("range 2 preceding")
    between = _validated_frame("range between 2 preceding and current row")
    assert shorthand.resolved.authored.frame.kind is AuthoredWindowFrameKind.SHORTHAND
    assert between.resolved.authored.frame.kind is AuthoredWindowFrameKind.BETWEEN
    assert shorthand.resolved.authored.frame.end is None
    assert between.resolved.authored.frame.end is not None
    assert shorthand.frame != between.frame


@pytest.mark.parametrize(
    ("direction", "preceding", "following"),
    (
        (
            "asc",
            RangeOffsetOrientation.LOWER_ORDERING_VALUES,
            RangeOffsetOrientation.HIGHER_ORDERING_VALUES,
        ),
        (
            "desc",
            RangeOffsetOrientation.HIGHER_ORDERING_VALUES,
            RangeOffsetOrientation.LOWER_ORDERING_VALUES,
        ),
    ),
)
def test_range_offset_orientation_is_explicit_and_direction_aware(
    direction: str,
    preceding: RangeOffsetOrientation,
    following: RangeOffsetOrientation,
) -> None:
    validated = _validated_frame(
        "range between delta preceding and delta following",
        order_by=(f"id {direction}",),
    )
    view = range_frame_logical_view(validated)
    assert type(view) is RangeFrameLogicalView
    assert tuple(requirement.role for requirement in view.offset_requirements) == (
        RangeFrameBoundRole.START,
        RangeFrameBoundRole.END,
    )
    assert tuple(requirement.direction for requirement in view.offset_requirements) == (
        RangeOrderDirection(direction),
        RangeOrderDirection(direction),
    )
    assert tuple(
        requirement.orientation for requirement in view.offset_requirements
    ) == (preceding, following)
    opposite = range_frame_logical_view(
        _validated_frame(
            "range between delta preceding and delta following",
            order_by=(f"id {'desc' if direction == 'asc' else 'asc'}",),
        )
    )
    assert type(opposite) is RangeFrameLogicalView
    assert view.offset_requirements[0].orientation is not (
        opposite.offset_requirements[0].orientation
    )


@pytest.mark.parametrize("order_by", ((), ("id", "secondary")))
def test_offset_range_requires_exactly_one_ordering_key(
    order_by: tuple[str, ...],
) -> None:
    validated = _validated_frame("range 2 preceding", order_by=order_by)
    result = range_frame_logical_view(validated)
    assert type(result) is RangeOffsetOrderingFailure
    assert result.order_key_count == len(order_by)
    assert result.specification is validated


@pytest.mark.parametrize("order_by", ((), ("id",), ("id", "secondary")))
def test_non_offset_range_does_not_require_one_ordering_key(
    order_by: tuple[str, ...],
) -> None:
    validated = _validated_frame(
        "range between unbounded preceding and current row",
        order_by=order_by,
    )
    result = range_frame_logical_view(validated)
    assert type(result) is RangeFrameLogicalView
    assert result.offset_requirements == ()
    assert not result.requires_phase64_arithmetic
    assert result.order_by is validated.resolved.order_by


def test_phase64_requirement_seam_retains_exact_expressions_without_evaluation() -> (
    None
):
    validated = _validated_frame(
        "range between delta preceding and delta preceding",
        order_by=("id desc",),
    )
    result = range_frame_logical_view(validated)
    assert type(result) is RangeFrameLogicalView
    assert result.requires_phase64_arithmetic
    assert len(result.offset_requirements) == 2
    requirement = result.offset_requirements[0]
    assert type(requirement) is RangeOffsetArithmeticRequirement
    assert requirement.offset_expression is requirement.bound.offset
    assert requirement.ordering_expression is validated.resolved.order_by[0].expression
    assert requirement.direction is RangeOrderDirection.DESC
    assert requirement.orientation is RangeOffsetOrientation.HIGHER_ORDERING_VALUES
    assert not hasattr(requirement, "compatible")
    assert not hasattr(requirement, "result")
    assert not hasattr(requirement, "value")
    assert type(validated.frame) is ValidatedFrame
    assert validated.frame.classification is (
        WindowFrameEmptinessClassification.POSSIBLY_EMPTY
    )


def test_range_current_row_uses_explicit_peer_boundaries_without_comparison() -> None:
    validated = _validated_frame("range current row")
    view = range_frame_logical_view(validated)
    assert type(view) is RangeFrameLogicalView
    assert view.start_peer_boundary is RangePeerBoundaryKind.FIRST_PEER
    assert view.end_peer_boundary is RangePeerBoundaryKind.LAST_PEER
    peers = _peer_partition(
        view.order_by,
        (
            (PeerComparisonOutcome.NOT_EQUAL,),
            (PeerComparisonOutcome.EQUAL,),
            (PeerComparisonOutcome.EQUAL,),
            (PeerComparisonOutcome.NOT_EQUAL,),
        ),
    )
    assert (
        resolve_range_current_row_boundary(
            view,
            role=RangeFrameBoundRole.START,
            peers=peers,
            current_position=2,
        )
        == 1
    )
    assert (
        resolve_range_current_row_boundary(
            view,
            role=RangeFrameBoundRole.END,
            peers=peers,
            current_position=2,
        )
        == 3
    )
    assert tuple((group.start, group.stop) for group in peers.groups) == (
        (0, 1),
        (1, 4),
        (4, 5),
    )


def test_unordered_range_requires_whole_partition_peer_evidence() -> None:
    validated = _validated_frame("range current row", order_by=())
    view = range_frame_logical_view(validated)
    assert type(view) is RangeFrameLogicalView
    assert view.requires_whole_partition_peer_evidence
    peers = _peer_partition(view.order_by, ())
    assert (
        resolve_range_current_row_boundary(
            view,
            role=RangeFrameBoundRole.START,
            peers=peers,
            current_position=2,
        )
        == 0
    )
    assert (
        resolve_range_current_row_boundary(
            view,
            role=RangeFrameBoundRole.END,
            peers=peers,
            current_position=2,
        )
        == 4
    )


def test_range_view_is_lazy_logical_and_not_rows_index_arithmetic() -> None:
    validated = _validated_frame(
        "range between delta preceding and current row",
        order_by=("id",),
    )
    view = range_frame_logical_view(validated)
    assert type(view) is RangeFrameLogicalView
    assert tuple(field.name for field in fields(RangeFrameLogicalView)) == (
        "specification",
        "offset_requirements",
    )
    for forbidden in ("rows", "members", "positions", "current_ordering_value"):
        assert not hasattr(view, forbidden)
    assert view.frame is validated.frame
    assert validated.frame.resolved.start is not None
    assert view.offset_requirements[0].offset_expression is (
        validated.frame.resolved.start.offset
    )


@pytest.mark.parametrize("call", CURRENT_FUNCTION_CALLS)
def test_every_current_function_rejects_authored_range_after_recognition(
    call: str,
) -> None:
    parsed = parse_source(_source("range current row", call=call), path="policy.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    expression = cast(QueryDef, parsed.ast.definitions[-1]).select_items[0].expression
    assert type(expression) is WindowExpr
    semantic = analyze(parsed.ast)
    matching = tuple(item for item in semantic.diagnostics if item.code == "PIE-S2104")
    assert len(matching) == 1
    assert matching[0].message == (
        f"Invalid window frame for function {expression.identity.name}: "
        "explicit RANGE frame is not allowed"
    )
    validation = window_analysis._validate_recognized_window_specification(expression)
    assert type(validation) is WindowSpecificationValidationFailure
    assert validation.resolved.authored.frame is expression.spec.frame
    assert tuple(issue.kind for issue in validation.issues) == (
        WindowValidationIssueKind.EXPLICIT_FRAME_FORBIDDEN,
    )


def test_rows_semantics_remain_exact_after_range_addition() -> None:
    validated = _validated_frame("rows between 1 preceding and 1 following")
    assert type(validated.frame) is ValidatedFrame
    interval = rows_frame_position_interval(
        validated.frame,
        partition_size=5,
        current_position=2,
    )
    assert type(interval) is RowsFramePositionInterval
    assert tuple(interval.positions) == (1, 2, 3)


def test_later_function_ownership_remains_unreachable() -> None:
    current = {
        identity.name for identity, _policy in window_analysis._RANKING_POLICIES
    } | {definition[0].name for definition in window_analysis._DISTRIBUTION_FUNCTIONS}
    current |= {
        identity.name
        for identity, _direction in (
            *navigation_analysis._NAVIGATION_IDENTITIES,
            *navigation_analysis._FRAME_VALUE_IDENTITIES,
        )
    }
    assert {"first_value", "last_value", "nth_value"}.issubset(current)
    assert not hasattr(ir_model, "RangeFrameIR")


def test_slice9_uses_shared_frame_ir_without_range_specific_ir() -> None:
    assert tuple(field.name for field in fields(ir_model.WindowSpecIR)) == (
        "partition_by",
        "order_by",
        "span",
        "frame",
    )
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
        assert not any("range_frame" in name.lower() for name in names)


def test_range_keyword_remains_contextual_outside_frame_clause() -> None:
    source = (
        "shape Row:\n"
        "    range: Int not null\n"
        'source range: Row is postgres.table("range")\n'
        "query selected:\n"
        "    from range\n"
        "    select:\n"
        "        range\n"
    )
    parsed = parse_source(source)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None


def test_slice5_spec_locks_lowering_and_cross_slice_ownership() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "RANGE <bound>",
        "RANGE BETWEEN <start> AND <end>",
        "ASC PRECEDING -> LOWER_ORDERING_VALUES",
        "DESC PRECEDING -> HIGHER_ORDERING_VALUES",
        "An offset RANGE requires exactly one resolved ordering key",
        "Slice 6 owns real peer computation and GROUPS semantics",
        "Phase 64 owns RANGE type, coercion, comparison, and arithmetic evidence",
        "Slice 9 owns the first legal frame-sensitive callers and SQL activation",
        "No successful explicit-frame SQL occurrence is required before Slice 9",
        "A2/M17/D0",
        "Slice 6 is neither implemented nor authorized",
        "Add Phase 60 RANGE semantics infrastructure",
    ):
        assert evidence in document
