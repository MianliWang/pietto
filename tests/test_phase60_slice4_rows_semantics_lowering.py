from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import pietto.ast_nodes as ast_nodes
import pietto.ir.model as ir_model
import pietto.semantic.window_analysis as window_analysis
import pietto.semantic.window_navigation_analysis as navigation_analysis
import pietto.semantic.window_semantics as window_semantics
from pietto import _window_identity
from pietto.ast_nodes import (
    AuthoredWindowFrameExclusion,
    AuthoredWindowFrameKind,
    BinaryExpr,
    LiteralExpr,
    QueryDef,
    WindowExpr,
    WindowFrameBoundKind,
    WindowFrameUnit,
)
from pietto.ir.lowering import lower_expr
from pietto.ir.model import WindowSpecIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
)
from pietto.semantic.window_semantics import (
    AuthoredWindowSpecification,
    RowsFramePositionInterval,
    StructurallyInvalidFrame,
    ValidatedFrame,
    ValidatedWindowSpecification,
    WindowFrameEmptinessClassification,
    WindowFunctionFramePolicy,
    WindowFunctionFramePolicyKind,
    WindowSpecificationValidationFailure,
    WindowValidationIssueKind,
    authored_window_specification_from_ast,
    resolve_authored_window_specification,
    rows_frame_position_interval,
    validate_resolved_window_specification,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase60-slice4-rows-semantics-lowering-v1.md"
FRAME_IDENTITY = _window_identity.WindowFunctionIdentity(
    namespace=("slice4",),
    name="frame_value_contract",
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


def _source(frame: str, *, call: str = "row_number()") -> str:
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    value: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query framed:\n"
        "    from rows\n"
        "    select:\n"
        f"        result = {call} window:\n"
        "            order by:\n"
        "                id\n"
        f"            {frame}\n"
    )


def _window(frame: str, *, call: str = "row_number()") -> WindowExpr:
    parsed = parse_source(_source(frame, call=call), path="slice4.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert type(expression) is WindowExpr
    return expression


def _validated_rows(frame: str) -> ValidatedWindowSpecification:
    expression = _window(frame)
    authored = authored_window_specification_from_ast(expression.spec)
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=window_semantics.WindowFrameApplicability.APPLICABLE,
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


def test_authored_frame_types_are_one_ast_owned_model_reused_by_semantics() -> None:
    assert ast_nodes.AuthoredWindowFrame is window_semantics.AuthoredWindowFrame
    assert ast_nodes.WindowFrameBound is window_semantics.WindowFrameBound
    assert ast_nodes.WindowFrameBoundKind is window_semantics.WindowFrameBoundKind
    assert ast_nodes.WindowFrameUnit is window_semantics.WindowFrameUnit
    assert tuple(field.name for field in fields(ast_nodes.WindowSpec)) == (
        "span",
        "partition_by",
        "order_by",
        "frame",
    )
    omitted = _window("rows current row").spec
    assert omitted.frame.kind is AuthoredWindowFrameKind.SHORTHAND
    assert omitted.frame.exclusion is AuthoredWindowFrameExclusion.OMITTED


@pytest.mark.parametrize(("source", "kind", "offset"), BOUND_CASES)
def test_every_rows_bound_spelling_parses_as_shorthand_existing_model(
    source: str,
    kind: WindowFrameBoundKind,
    offset: int | None,
) -> None:
    frame = _window(f"rows {source}").spec.frame
    assert frame.kind is AuthoredWindowFrameKind.SHORTHAND
    assert frame.unit is WindowFrameUnit.ROWS
    assert frame.start is not None and frame.start.kind is kind
    assert frame.end is None
    if offset is None:
        assert frame.start.offset is None
    else:
        assert type(frame.start.offset) is LiteralExpr
        assert frame.start.offset.value == offset


@pytest.mark.parametrize(("source", "kind", "offset"), BOUND_CASES)
def test_every_rows_bound_spelling_parses_in_both_between_positions(
    source: str,
    kind: WindowFrameBoundKind,
    offset: int | None,
) -> None:
    as_start = _window(f"rows between {source} and unbounded following").spec.frame
    as_end = _window(f"rows between unbounded preceding and {source}").spec.frame
    assert as_start.kind is AuthoredWindowFrameKind.BETWEEN
    assert as_end.kind is AuthoredWindowFrameKind.BETWEEN
    assert as_start.start is not None and as_start.start.kind is kind
    assert as_end.end is not None and as_end.end.kind is kind
    for bound in (as_start.start, as_end.end):
        if offset is None:
            assert bound.offset is None
        else:
            assert type(bound.offset) is LiteralExpr
            assert bound.offset.value == offset


def test_offset_expression_and_authored_provenance_retain_exact_objects() -> None:
    expression = _window("rows id + 1 preceding")
    frame = expression.spec.frame
    assert frame.start is not None
    assert type(frame.start.offset) is BinaryExpr
    authored = authored_window_specification_from_ast(expression.spec)
    assert authored.span is expression.spec.span
    assert authored.partition_by is expression.spec.partition_by
    assert authored.order_by is expression.spec.order_by
    assert authored.frame is frame
    assert authored.frame.start is not None
    assert authored.frame.start is frame.start
    assert authored.frame.start.offset is frame.start.offset


def test_shorthand_and_between_current_row_remain_distinct_through_resolution() -> None:
    shorthand = _window("rows 2 preceding").spec
    between = _window("rows between 2 preceding and current row").spec
    shorthand_authored = authored_window_specification_from_ast(shorthand)
    between_authored = authored_window_specification_from_ast(between)
    shorthand_resolved = resolve_authored_window_specification(
        shorthand_authored,
        frame_applicability=window_semantics.WindowFrameApplicability.APPLICABLE,
    )
    between_resolved = resolve_authored_window_specification(
        between_authored,
        frame_applicability=window_semantics.WindowFrameApplicability.APPLICABLE,
    )
    assert shorthand.frame.kind is AuthoredWindowFrameKind.SHORTHAND
    assert between.frame.kind is AuthoredWindowFrameKind.BETWEEN
    assert shorthand.frame.end is None
    assert between.frame.end is not None
    assert shorthand_resolved.frame.start is shorthand.frame.start
    assert between_resolved.frame.start is between.frame.start
    assert shorthand_resolved.frame.end == between_resolved.frame.end
    assert shorthand_resolved.frame != between_resolved.frame


def test_slice3_still_owns_structural_invalidity_for_rows() -> None:
    expression = _window("rows between unbounded following and unbounded preceding")
    authored = authored_window_specification_from_ast(expression.spec)
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=window_semantics.WindowFrameApplicability.APPLICABLE,
    )
    result = validate_resolved_window_specification(
        resolved,
        function_identity=FRAME_IDENTITY,
        function_policy=FRAME_POLICY,
    )
    assert type(result) is WindowSpecificationValidationFailure
    assert tuple(issue.kind for issue in result.issues) == (
        WindowValidationIssueKind.STRUCTURALLY_INVALID_FRAME,
    )
    failure = result.issues[0].structural_failure
    assert type(failure) is StructurallyInvalidFrame
    assert (
        failure.classification
        is WindowFrameEmptinessClassification.STRUCTURALLY_INVALID
    )


@pytest.mark.parametrize(
    ("frame", "current", "expected", "boundaries"),
    (
        ("rows between 1 preceding and 1 following", 2, (1, 2, 3), (1, 4)),
        ("rows between 2 preceding and current row", 0, (0,), (0, 1)),
        ("rows between 3 preceding and 1 preceding", 0, (), (0, 0)),
        ("rows between 1 following and 2 following", 4, (), (5, 5)),
        ("rows current row", 3, (3,), (3, 4)),
    ),
)
def test_rows_clipping_is_interval_intersection_not_endpoint_membership_clamping(
    frame: str,
    current: int,
    expected: tuple[int, ...],
    boundaries: tuple[int, int],
) -> None:
    validated = _validated_rows(frame)
    assert type(validated.frame) is ValidatedFrame
    interval = rows_frame_position_interval(
        validated.frame,
        partition_size=5,
        current_position=current,
    )
    assert type(interval) is RowsFramePositionInterval
    assert (interval.start, interval.stop) == boundaries
    assert interval.positions == range(*boundaries)
    assert tuple(interval.positions) == expected
    assert interval.empty is (not expected)


def test_rows_current_row_is_each_exact_physical_position_without_peer_input() -> None:
    validated = _validated_rows("rows current row")
    assert type(validated.frame) is ValidatedFrame
    first = rows_frame_position_interval(
        validated.frame,
        partition_size=4,
        current_position=1,
    )
    second = rows_frame_position_interval(
        validated.frame,
        partition_size=4,
        current_position=2,
    )
    assert tuple(first.positions) == (1,)
    assert tuple(second.positions) == (2,)
    assert "peer" not in rows_frame_position_interval.__annotations__


def test_legal_same_side_rows_empty_is_not_structural_invalidity() -> None:
    validated = _validated_rows("rows between 1 preceding and 3 preceding")
    assert type(validated.frame) is ValidatedFrame
    assert validated.frame.classification is (
        WindowFrameEmptinessClassification.POSSIBLY_EMPTY
    )
    interval = rows_frame_position_interval(
        validated.frame,
        partition_size=5,
        current_position=4,
    )
    assert (interval.start, interval.stop) == (3, 2)
    assert interval.empty
    assert tuple(interval.positions) == ()


@pytest.mark.parametrize("offset", ("-1", "true", "1.5", "id"))
def test_rows_offsets_require_existing_nonnegative_integer_literal_evidence(
    offset: str,
) -> None:
    validated = _validated_rows(f"rows {offset} preceding")
    assert type(validated.frame) is ValidatedFrame
    with pytest.raises(ValueError, match="nonnegative integer literal evidence"):
        rows_frame_position_interval(
            validated.frame,
            partition_size=5,
            current_position=2,
        )


@pytest.mark.parametrize("offset", (0, 1, 10**80))
def test_rows_nonnegative_integer_literal_distances_have_no_artificial_ceiling(
    offset: int,
) -> None:
    validated = _validated_rows(f"rows between current row and {offset} following")
    assert type(validated.frame) is ValidatedFrame
    interval = rows_frame_position_interval(
        validated.frame,
        partition_size=5,
        current_position=2,
    )
    expected_stop = 3 if offset == 0 else 4 if offset == 1 else 5
    assert (interval.start, interval.stop) == (2, expected_stop)


def test_rows_base_frame_fails_closed_for_non_rows_and_owned_later_exclusion() -> None:
    expression = _window("rows current row")
    frame = expression.spec.frame
    range_authored = AuthoredWindowSpecification(
        span=expression.spec.span,
        partition_by=expression.spec.partition_by,
        order_by=expression.spec.order_by,
        frame=replace(frame, unit=WindowFrameUnit.RANGE),
    )
    ties_authored = replace(
        range_authored,
        frame=replace(
            frame,
            exclusion=AuthoredWindowFrameExclusion.TIES,
        ),
    )
    for authored, message in (
        (range_authored, "requires ROWS frame semantics"),
        (ties_authored, "requires EXCLUDE NO OTHERS"),
    ):
        resolved = resolve_authored_window_specification(
            authored,
            frame_applicability=window_semantics.WindowFrameApplicability.APPLICABLE,
        )
        result = validate_resolved_window_specification(
            resolved,
            function_identity=FRAME_IDENTITY,
            function_policy=FRAME_POLICY,
        )
        assert type(result) is ValidatedWindowSpecification
        assert type(result.frame) is ValidatedFrame
        with pytest.raises(ValueError, match=message):
            rows_frame_position_interval(
                result.frame,
                partition_size=5,
                current_position=2,
            )


def test_rows_interval_is_frozen_lazy_range_state_without_member_list() -> None:
    interval = RowsFramePositionInterval(partition_size=5, start=4, stop=2)
    assert tuple(field.name for field in fields(RowsFramePositionInterval)) == (
        "partition_size",
        "start",
        "stop",
    )
    assert interval.positions == range(4, 2)
    assert interval.empty
    assert not hasattr(interval, "members")
    assert not hasattr(interval, "rows")
    with pytest.raises(ValueError):
        replace(interval, start=6)


@pytest.mark.parametrize("call", CURRENT_FUNCTION_CALLS)
def test_every_current_function_rejects_authored_rows_at_function_policy(
    call: str,
) -> None:
    parsed = parse_source(_source("rows current row", call=call), path="policy.pietto")
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
    assert expression not in semantic.model.expression_value_types
    validation = window_analysis._validate_recognized_window_specification(expression)
    assert type(validation) is WindowSpecificationValidationFailure
    assert validation.resolved.authored.frame is expression.spec.frame
    assert tuple(issue.kind for issue in validation.issues) == (
        WindowValidationIssueKind.EXPLICIT_FRAME_FORBIDDEN,
    )


def test_ir_lowering_cannot_silently_drop_a_forged_explicit_frame() -> None:
    expression = _window("rows current row")
    parsed = parse_source(_source("rows current row"))
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    forged = replace(
        semantic.model,
        expression_value_types={
            expression: ValueType(
                resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
                nullability=EffectiveNullability.NON_NULL,
            )
        },
    )
    lowered = lower_expr(expression, forged)
    assert lowered.expression is None
    assert len(lowered.diagnostics) == 1
    assert lowered.diagnostics[0].code == "PIE-I1000"
    assert "validated explicit window frame lowering authority" in (
        lowered.diagnostics[0].message
    )


def test_no_unreachable_frame_ir_or_production_sql_renderer_is_introduced() -> None:
    assert tuple(field.name for field in fields(WindowSpecIR)) == (
        "partition_by",
        "order_by",
        "span",
    )
    assert not hasattr(ir_model, "RowsFrameIR")
    assert not hasattr(ir_model, "WindowFrameIR")
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
        assert not any("rows_frame" in name.lower() for name in names)
    assert "validated explicit window frame lowering authority" in (
        REPO_ROOT / "src/pietto/ir/lowering.py"
    ).read_text(encoding="utf-8")


def test_new_frame_words_remain_contextual_identifiers_outside_frame_clause() -> None:
    source = (
        "shape Row:\n"
        "    rows: Int not null\n"
        "    current: Int not null\n"
        "    row: Int not null\n"
        "    unbounded: Int not null\n"
        "    preceding: Int not null\n"
        "    following: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query current:\n"
        "    from rows\n"
        "    select:\n"
        "        row\n"
        "        unbounded\n"
        "        preceding\n"
        "        following\n"
    )
    parsed = parse_source(source)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None


@pytest.mark.parametrize(
    "frame",
    (
        "groups current row",
        "rows current row exclude ties",
    ),
)
def test_later_frame_surfaces_remain_unreachable(frame: str) -> None:
    parsed = parse_source(_source(frame))
    assert parsed.ast is None
    assert parsed.diagnostics


def test_slice9_and_phase65_function_ownership_is_not_pulled_forward() -> None:
    current = {
        identity.name for identity, _policy in window_analysis._RANKING_POLICIES
    } | {definition[0].name for definition in window_analysis._DISTRIBUTION_FUNCTIONS}
    current |= {
        identity.name
        for identity, _direction in (navigation_analysis._NAVIGATION_IDENTITIES)
    }
    assert current == {
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
    }
    assert {"first_value", "last_value", "nth_value"}.isdisjoint(current)
    assert {"first_value", "last_value", "nth_value"}.isdisjoint(
        ir_model._WINDOW_ARGUMENT_ARITIES
    )
    assert not hasattr(ir_model, "AggregateWindowCallIR")


def test_slice4_spec_locks_canonical_lowering_and_activation_sequence() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "ROWS <bound>",
        "ROWS BETWEEN <start> AND <end>",
        "UNBOUNDED PRECEDING",
        "<expression SQL> PRECEDING",
        "CURRENT ROW",
        "<expression SQL> FOLLOWING",
        "UNBOUNDED FOLLOWING",
        "13-slice route unchanged",
        "Slices 4-7 establish frame semantics and canonical lowering contracts",
        "Slice 9 introduces the first legal frame-sensitive value-function callers",
        "Slice 10 owns backend capability gating",
        "Slice 11 owns broad real authored advanced-window E2E",
        "No successful explicit-frame SQL occurrence is required before Slice 9",
        "A2/M20/D0",
        "Slice 5 is neither implemented nor authorized",
        "Add Phase 60 ROWS semantics infrastructure",
    ):
        assert evidence in document
