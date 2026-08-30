from __future__ import annotations

import dataclasses
import re
import textwrap
from typing import Any, cast


import pytest

import pietto
import pietto.ast_nodes as ast_nodes
from pietto import _window_identity
from pietto._project.model import ProjectRowResultRole, ProjectRowSchema
from pietto._project.row_expression_schema import (
    ProjectExpressionSchemaOriginKind,
    ProjectExpressionSchemaReason,
    ProjectExpressionSchemaStatus,
    adapt_project_row_expression_schema,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    OrderItem,
    QueryDef,
    Span,
    WindowExpr,
    WindowSpec,
)
from pietto.errors import Severity
from pietto.ir.lowering import lower_expr
from pietto.ir.model import WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze


TEMPORARY_BRIDGE_MESSAGE = (
    "Window syntax is recognized, but WindowSpec AST preservation starts in "
    "Phase 53 Slice 3."
)

WINDOW_FUNCTION_NAMES = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
)

IDENTITY_CASES = (
    ("rank", (), "rank"),
    ("analytics.rank", ("analytics",), "rank"),
    ("Org.Analytics.Rank", ("Org", "Analytics"), "Rank"),
    ("Window", (), "Window"),
    ("WINDOW", (), "WINDOW"),
    ("vendor.Unrelated", ("vendor",), "Unrelated"),
)
CANONICAL_CASES = (
    ("order_only", "order by:\n    observed_at", 0, (None,)),
    ("partition_only", "partition by:\n    account_id", 1, ()),
    (
        "combined",
        "partition by:\n    account_id\norder by:\n    observed_at desc",
        1,
        ("desc",),
    ),
    (
        "multiple_partition",
        "partition by:\n    account_id\n    region",
        2,
        (),
    ),
    (
        "multiple_order",
        "order by:\n    observed_at\n    sequence_id asc",
        0,
        (None, "asc"),
    ),
    (
        "blank_lines",
        "\npartition by:\n\n    account_id\n\norder by:\n\n    observed_at\n",
        1,
        (None,),
    ),
    ("ascending", "order by:\n    observed_at asc", 0, ("asc",)),
    ("descending", "order by:\n    observed_at desc", 0, ("desc",)),
)
CALL_ARGUMENT_CASES = (
    ("row_number()", ()),
    ("lag(value, 1)", ("value", 1)),
    ("lead(value, 2, fallback,)", ("value", 2, "fallback")),
)
CANDIDATE_IDENTITY_CASES = (*WINDOW_FUNCTION_NAMES, "custom", "Window", "WINDOW")
QUALIFIED_IDENTITY_CASES = (
    ("analytics.rank", ("analytics",), "rank"),
    ("Org.Analytics.Rank", ("Org", "Analytics"), "Rank"),
    ("vendor.extension.lead", ("vendor", "extension"), "lead"),
)
SPAN_CASES = (
    (
        "order_only",
        "order by:\n    observed_at",
        (4, 14, 6, 28),
        (4, 14, 4, 26),
        (4, 27, 6, 28),
    ),
    (
        "partition_only",
        "partition by:\n    region",
        (4, 14, 6, 23),
        (4, 14, 4, 26),
        (4, 27, 6, 23),
    ),
    (
        "combined",
        "partition by:\n    account_id\norder by:\n    observed_at desc",
        (4, 14, 8, 33),
        (4, 14, 4, 26),
        (4, 27, 8, 33),
    ),
)
DIRECTION_CASES = (
    ("observed_at", None, (6, 17, 6, 28)),
    ("observed_at asc", "asc", (6, 17, 6, 32)),
    ("observed_at desc", "desc", (6, 17, 6, 33)),
)
MALFORMED_CASES = (
    ("missing_colon", "order by:\n    observed_at", " window:\n", " window\n"),
    ("empty_window", "", None, None),
    ("empty_partition", "partition by:\n", None, None),
    ("empty_order", "order by:\n", None, None),
    (
        "duplicate_partition",
        "partition by:\n    account_id\npartition by:\n    region",
        None,
        None,
    ),
    (
        "duplicate_order",
        "order by:\n    observed_at\norder by:\n    sequence_id",
        None,
        None,
    ),
    (
        "reversed",
        "order by:\n    observed_at\npartition by:\n    account_id",
        None,
        None,
    ),
    ("unknown_clause", "cluster by:\n    account_id", None, None),
    ("nulls_first", "order by:\n    observed_at nulls first", None, None),
    ("malformed_order", "order by:\n    observed_at +", None, None),
    ("malformed_partition", "partition by:\n    account_id +", None, None),
)
VALID_BRIDGE_CASES = (
    "order by:\n    observed_at",
    "partition by:\n    account_id",
    "partition by:\n    account_id\norder by:\n    observed_at desc",
)
SEMANTIC_IDENTITY_CASES = (
    ("rank", "Unknown function: rank"),
    ("analytics.rank", "Unknown function: analytics.rank"),
    ("Org.Analytics.Rank", "Unknown function: Org.Analytics.Rank"),
)


def _window_query(
    body: str,
    *,
    projection: str = "rn = row_number()",
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
) -> str:
    body_text = textwrap.dedent(body).strip("\n") + "\n"
    return (
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        + "".join(f"        {item}\n" for item in before)
        + f"        {projection} window:\n"
        + textwrap.indent(body_text, "            ")
        + "".join(f"        {item}\n" for item in after)
    )


def _semantic_window_source(call: str) -> str:
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    observed_at: Timestamp not null\n"
        'source rows: Row is postgres.table("rows")\n'
        + _window_query("order by:\n    observed_at", projection=f"rn = {call}")
    )


def _window_expression(source: str) -> WindowExpr:
    result = parse_source(source, path="window-slice3.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert isinstance(expression, WindowExpr)
    return expression


def _span_tuple(span: Span) -> tuple[int, int, int, int]:
    return span.line, span.column, span.end_line, span.end_column


def _literal_argument_value(expression: Expression) -> str | int:
    if isinstance(expression, NameExpr):
        return expression.name
    assert isinstance(expression, LiteralExpr)
    assert isinstance(expression.value, (str, int))
    return expression.value


def test_window_identity_role_shape_validation_and_privacy_are_exact() -> None:
    role = _window_identity.WindowFunctionRole.WINDOW_FUNCTION
    identity = _window_identity.WindowFunctionIdentity((), "rank", role)
    assert tuple(_window_identity.WindowFunctionRole) == (role,)
    assert role.value == "window_function"
    assert dataclasses.is_dataclass(identity)
    assert identity.__slots__ == ("namespace", "name", "role")
    assert _window_identity.__all__ == ()
    assert not hasattr(pietto, "WindowFunctionIdentity")
    assert not hasattr(ast_nodes, "WindowFunctionIdentity")
    invalid = (
        (([], "rank", role), TypeError, "namespace must be an exact tuple"),
        (((1,), "rank", role), TypeError, "namespace components must be strings"),
        ((("",), "rank", role), ValueError, "namespace components must be non-empty"),
        (((), 1, role), TypeError, "name must be a string"),
        (((), "", role), ValueError, "name must be non-empty"),
        (
            ((), "rank", "window_function"),
            TypeError,
            "role must be a WindowFunctionRole",
        ),
    )
    for arguments, error_type, message in invalid:
        with pytest.raises(error_type, match=re.escape(message)):
            _window_identity.WindowFunctionIdentity(*cast(Any, arguments))


@pytest.mark.parametrize(("call", "namespace", "name"), IDENTITY_CASES)
def test_window_identity_namespace_name_case_and_hash_are_preserved(
    call: str,
    namespace: tuple[str, ...],
    name: str,
) -> None:
    expression = _window_expression(
        _window_query("order by:\n    observed_at", projection=f"rn = {call}()")
    )
    expected = _window_identity.WindowFunctionIdentity(
        namespace,
        name,
        _window_identity.WindowFunctionRole.WINDOW_FUNCTION,
    )
    assert expression.identity == expected
    assert hash(expression.identity) == hash(expected)
    assert repr(expression.identity) == repr(expected)


def test_window_spec_constructor_invariants_and_hash_are_exact() -> None:
    span = Span(path="constructor.pietto", line=1, column=1, end_line=1, end_column=2)
    expression = NameExpr(span=span, name="id")
    item = OrderItem(span=span, expression=expression, direction=None)
    spec = WindowSpec(span=span, partition_by=(expression,), order_by=(item,))
    assert spec == WindowSpec(span=span, partition_by=(expression,), order_by=(item,))
    assert hash(spec) == hash(
        WindowSpec(span=span, partition_by=(expression,), order_by=(item,))
    )
    empty = WindowSpec(span=span, partition_by=(), order_by=())
    assert not empty.has_components
    invalid = (
        (([], (item,)), TypeError, "partition_by must be an exact tuple"),
        (((expression,), []), TypeError, "order_by must be an exact tuple"),
        (
            ((object(),), (item,)),
            TypeError,
            "partition_by items must be Expression instances",
        ),
        (
            ((expression,), (object(),)),
            TypeError,
            "order_by items must be OrderItem instances",
        ),
    )
    for arguments, error_type, message in invalid:
        with pytest.raises(error_type, match=re.escape(message)):
            WindowSpec(
                span=span,
                partition_by=cast(Any, arguments[0]),
                order_by=cast(Any, arguments[1]),
            )


@pytest.mark.parametrize(
    ("name", "body", "partition_count", "directions"),
    CANONICAL_CASES,
    ids=[case[0] for case in CANONICAL_CASES],
)
def test_parser_preserves_canonical_window_shapes(
    name: str,
    body: str,
    partition_count: int,
    directions: tuple[str | None, ...],
) -> None:
    expression = _window_expression(_window_query(body))
    assert len(expression.spec.partition_by) == partition_count, name
    assert tuple(item.direction for item in expression.spec.order_by) == directions
    assert expression.identity.name == "row_number"
    assert expression.identity.namespace == ()


@pytest.mark.parametrize(("call", "expected"), CALL_ARGUMENT_CASES)
def test_parser_preserves_call_arguments_and_trailing_comma(
    call: str,
    expected: tuple[str | int, ...],
) -> None:
    expression = _window_expression(
        _window_query("order by:\n    observed_at", projection=f"value = {call}")
    )
    assert tuple(
        _literal_argument_value(item) for item in expression.call.arguments
    ) == (expected)


@pytest.mark.parametrize("function_name", CANDIDATE_IDENTITY_CASES)
def test_parser_preserves_function_candidate_identity(function_name: str) -> None:
    expression = _window_expression(
        _window_query(
            "order by:\n    observed_at",
            projection=f"value = {function_name}()",
        )
    )
    assert expression.identity.namespace == ()
    assert expression.identity.name == function_name
    assert (
        expression.identity.role is _window_identity.WindowFunctionRole.WINDOW_FUNCTION
    )


def test_value_modifier_authorship_is_source_located_and_use_local() -> None:
    expression = _window_expression(
        _window_query(
            "order by:\n    observed_at",
            projection=("value = nth_value(value, 2) from last ignore nulls"),
        )
    )
    assert expression.nth_direction is not None
    assert expression.nth_direction.kind is ast_nodes.WindowNthDirectionKind.LAST
    assert expression.null_treatment is not None
    assert expression.null_treatment.kind is ast_nodes.WindowNullTreatmentKind.IGNORE
    assert expression.nth_direction.span.path == "window-slice3.pietto"
    assert expression.null_treatment.span.path == "window-slice3.pietto"


@pytest.mark.parametrize(("call", "namespace", "name"), QUALIFIED_IDENTITY_CASES)
def test_parser_preserves_qualified_identity_namespace_and_case(
    call: str,
    namespace: tuple[str, ...],
    name: str,
) -> None:
    expression = _window_expression(
        _window_query("partition by:\n    id", projection=f"value = {call}()")
    )
    assert expression.identity.namespace == namespace
    assert expression.identity.name == name
    assert isinstance(expression.call.callee, DottedNameExpr)
    assert expression.call.callee.parts == (*namespace, name)


def test_multiple_window_and_ordinary_select_items_preserve_order_aliases_and_independence() -> (
    None
):
    source = (
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        rn = row_number() window:\n"
        "            order by:\n"
        "                observed_at\n"
        "        value\n"
        "        previous = lag(value, 1) window:\n"
        "            partition by:\n"
        "                account_id\n"
    )
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[-1])
    assert tuple(item.alias for item in relation.select_items) == (
        None,
        "rn",
        None,
        "previous",
    )
    first = cast(WindowExpr, relation.select_items[1].expression)
    second = cast(WindowExpr, relation.select_items[3].expression)
    assert first is not second
    assert first.spec != second.spec
    assert first.identity.name == "row_number"
    assert second.identity.name == "lag"


@pytest.mark.parametrize(
    ("name", "body", "expression_span", "call_span", "spec_span"),
    SPAN_CASES,
    ids=[case[0] for case in SPAN_CASES],
)
def test_window_ast_spans_are_exact(
    name: str,
    body: str,
    expression_span: tuple[int, int, int, int],
    call_span: tuple[int, int, int, int],
    spec_span: tuple[int, int, int, int],
) -> None:
    source = _window_query(body)
    result = parse_source(source, path=f"span-{name}.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[-1])
    item = relation.select_items[0]
    expression = cast(WindowExpr, item.expression)
    assert _span_tuple(expression.span) == expression_span
    assert _span_tuple(expression.call.span) == call_span
    assert _span_tuple(expression.spec.span) == spec_span
    assert _span_tuple(expression.call.callee.span) == (4, 14, 4, 24)
    assert _span_tuple(item.span) == (4, 9, *expression_span[2:])


@pytest.mark.parametrize(("item_source", "direction", "item_span"), DIRECTION_CASES)
def test_window_order_direction_and_spans_are_exact(
    item_source: str,
    direction: str | None,
    item_span: tuple[int, int, int, int],
) -> None:
    expression = _window_expression(_window_query(f"order by:\n    {item_source}"))
    item = expression.spec.order_by[0]
    assert item.direction == direction
    assert _span_tuple(item.span) == item_span
    assert _span_tuple(item.expression.span) == (6, 17, 6, 28)


def test_window_order_integer_literal_bypasses_final_order_ordinal_rejection() -> None:
    expression = _window_expression(_window_query("order by:\n    1"))
    item = expression.spec.order_by[0]
    assert isinstance(item.expression, LiteralExpr)
    assert item.expression.value == 1
    final_order = parse_source(
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    order by:\n"
        "        1\n"
    )
    assert final_order.ast is None
    assert len(final_order.diagnostics) == 1
    assert final_order.diagnostics[0].message == (
        "Ordinal ORDER BY expressions are not supported."
    )


@pytest.mark.parametrize(
    ("name", "body", "old", "new"),
    MALFORMED_CASES,
    ids=[case[0] for case in MALFORMED_CASES],
)
def test_slice2_malformed_and_deferred_window_syntax_remains_rejected(
    name: str,
    body: str,
    old: str | None,
    new: str | None,
) -> None:
    source = _window_query(body)
    if old is not None and new is not None:
        source = source.replace(old, new, 1)
    result = parse_source(source, path=f"malformed-{name}.pietto")
    assert result.ast is None, name
    assert result.diagnostics
    assert all(
        diagnostic.code in {"PIE-P1000", "PIE-P1005"}
        and diagnostic.severity is Severity.ERROR
        for diagnostic in result.diagnostics
    )


@pytest.mark.parametrize("body", VALID_BRIDGE_CASES)
def test_valid_window_parse_retires_temporary_slice2_bridge(body: str) -> None:
    result = parse_source(_window_query(body))
    assert result.ast is not None
    assert result.diagnostics == ()
    assert TEMPORARY_BRIDGE_MESSAGE not in repr(result)


@pytest.mark.parametrize(("call", "message"), SEMANTIC_IDENTITY_CASES)
def test_semantic_check_fails_closed_with_existing_unknown_function_diagnostic(
    call: str,
    message: str,
) -> None:
    result = parse_source(
        _semantic_window_source(f"{call}()"), path="semantic-window.pietto"
    )
    assert result.diagnostics == ()
    assert result.ast is not None
    expression = cast(QueryDef, result.ast.definitions[-1]).select_items[0].expression
    semantic = analyze(result.ast)
    matching = tuple(item for item in semantic.diagnostics if item.code == "PIE-S2103")
    if call == "rank":
        assert matching == ()
        assert expression in semantic.model.expression_value_types
        return
    assert len(matching) == 1
    diagnostic = matching[0]
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.message == message
    assert diagnostic.location.path == "semantic-window.pietto"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == _span_tuple(cast(WindowExpr, expression).call.span)


def test_window_expression_publishes_no_semantic_value_type_fact() -> None:
    result = parse_source(_semantic_window_source("row_number()"))
    assert result.diagnostics == ()
    assert result.ast is not None
    expression = cast(
        WindowExpr,
        cast(QueryDef, result.ast.definitions[-1]).select_items[0].expression,
    )
    semantic = analyze(result.ast)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    assert expression in semantic.model.expression_value_types
    assert semantic.model.expression_value_types[expression].resolved_type.name == "Int"
    assert expression.call not in semantic.model.expression_value_types
    assert all(
        argument not in semantic.model.expression_value_types
        for argument in expression.call.arguments
    )


def test_ir_lowering_fails_closed_on_missing_window_expression_fact() -> None:
    result = parse_source(_semantic_window_source("row_number()"))
    assert result.ast is not None
    expression = cast(
        WindowExpr,
        cast(QueryDef, result.ast.definitions[-1]).select_items[0].expression,
    )
    semantic = analyze(result.ast)
    lowered = lower_expr(expression, semantic.model)
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == "row_number"
    assert lowered.expression.arguments == ()
    assert lowered.diagnostics == ()


def test_project_parse_only_path_remains_deferred_without_window_result_dependency_or_lineage() -> (
    None
):
    expression = _window_expression(_window_query("order by:\n    observed_at"))
    adapted = adapt_project_row_expression_schema(
        expression=expression,
        output_name="rn",
        input_schema=ProjectRowSchema(fields={}),
        upstream_state=None,
        relation_qualifier=None,
        expression_value_types={},
    )
    assert adapted.status is ProjectExpressionSchemaStatus.UNKNOWN
    assert adapted.reason is ProjectExpressionSchemaReason.MISSING_VALUE_TYPE
    assert adapted.origin is ProjectExpressionSchemaOriginKind.UNKNOWN
    assert adapted.dependency_placeholders == ()
    assert adapted.lineage_placeholders == ()
    assert ProjectRowResultRole.WINDOW_RESULT.value == "window_result"


# Phase 53 Slice 13 reader migration.
