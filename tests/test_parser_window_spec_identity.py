from __future__ import annotations

import dataclasses
import re
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
from pietto.parser_api import parse_source
from pietto.semantic import analyze


IDENTITY_CASES = (
    ("rank", (), "rank"),
    ("analytics.rank", ("analytics",), "rank"),
    ("Org.Analytics.Rank", ("Org", "Analytics"), "Rank"),
    ("Window", (), "Window"),
    ("WINDOW", (), "WINDOW"),
    ("vendor.Unrelated", ("vendor",), "Unrelated"),
)
CANONICAL_CASES = (
    ("empty_window", "", 0, ()),
    ("order_only", "order by observed_at", 0, (None,)),
    ("partition_only", "partition by account_id", 1, ()),
    ("combined", "partition by account_id order by observed_at desc", 1, ("desc",)),
    ("multiple_partition", "partition by account_id, region", 2, ()),
    ("multiple_order", "order by observed_at, sequence_id asc", 0, (None, "asc")),
    (
        "blank_lines",
        "\n\n    partition by account_id\n\n    order by observed_at\n",
        1,
        (None,),
    ),
    ("ascending", "order by observed_at asc", 0, ("asc",)),
    ("descending", "order by observed_at desc", 0, ("desc",)),
)
CALL_ARGUMENT_CASES = (
    ("row_number()", ()),
    ("lag(value, 1)", ("value", 1)),
    ("lead(value, 2, fallback,)", ("value", 2, "fallback")),
)
CANDIDATE_IDENTITY_CASES = (
    "row_number",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
    "custom",
)
QUALIFIED_IDENTITY_CASES = (
    ("analytics.rank", ("analytics",), "rank"),
    ("Org.Analytics.Rank", ("Org", "Analytics"), "Rank"),
    ("vendor.extension.lead", ("vendor", "extension"), "lead"),
)
SPAN_CASES = (
    (
        "order_only",
        "order by observed_at",
        (4, 14, 4, 55),
        (4, 14, 4, 26),
        (4, 27, 4, 55),
    ),
    (
        "partition_only",
        "partition by region",
        (4, 14, 4, 54),
        (4, 14, 4, 26),
        (4, 27, 4, 54),
    ),
    (
        "combined",
        "partition by account_id order by observed_at desc",
        (4, 14, 4, 84),
        (4, 14, 4, 26),
        (4, 27, 4, 84),
    ),
)
DIRECTION_CASES = (
    ("observed_at", None, (4, 43, 4, 54)),
    ("observed_at asc", "asc", (4, 43, 4, 58)),
    ("observed_at desc", "desc", (4, 43, 4, 59)),
)
MALFORMED_CASES = (
    ("empty_partition", "partition by", None, None),
    ("empty_order", "order by", None, None),
    ("duplicate_partition", "partition by account_id partition by region", None, None),
    ("duplicate_order", "order by observed_at order by sequence_id", None, None),
    ("reversed", "order by observed_at partition by account_id", None, None),
    ("unknown_clause", "cluster by account_id", None, None),
    ("nulls_first", "order by observed_at nulls first", None, None),
    ("malformed_order", "order by observed_at +", None, None),
    ("malformed_partition", "partition by account_id +", None, None),
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
    return (
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        + "".join(f"        {item}\n" for item in before)
        + f"        {projection} window({body})\n"
        + "".join(f"        {item}\n" for item in after)
    )


def _semantic_window_source(call: str) -> str:
    return (
        "shape Row:\n"
        "    id: Int\n"
        "    observed_at: Timestamp\n"
        'source rows: Row = postgres.table("rows")\n'
        + _window_query("order by observed_at", projection=f"rn = {call}")
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
        _window_query("order by observed_at", projection=f"rn = {call}()")
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


def test_empty_window_constructor_shapes_keep_identity_and_base_guards() -> None:
    span = Span(path="empty-window.pietto", line=1, column=1, end_line=1, end_column=2)
    callee = NameExpr(span=span, name="row_number")
    call = ast_nodes.CallExpr(span=span, callee=callee, arguments=())
    spec = WindowSpec(span=span, partition_by=(), order_by=())
    identity = _window_identity.WindowFunctionIdentity(
        (), "row_number", _window_identity.WindowFunctionRole.WINDOW_FUNCTION
    )
    base = ast_nodes.NamedWindowReference(span=span, name="root")
    inline = WindowExpr(span=span, call=call, spec=spec, identity=identity)
    direct = dataclasses.replace(
        inline, use_kind=ast_nodes.WindowUseKind.NAMED_DIRECT, base=base
    )
    extended = dataclasses.replace(
        direct, use_kind=ast_nodes.WindowUseKind.NAMED_EXTENDED
    )
    for expression in (inline, direct, extended):
        assert expression.call is call
        assert expression.spec is spec
        assert expression.identity is identity
        assert not expression.spec.has_components
    assert inline.use_kind is ast_nodes.WindowUseKind.INLINE
    assert inline.base is None
    assert direct.use_kind is ast_nodes.WindowUseKind.NAMED_DIRECT
    assert extended.use_kind is ast_nodes.WindowUseKind.NAMED_EXTENDED
    assert direct.base is extended.base is base
    nonempty = dataclasses.replace(spec, partition_by=(callee,))
    invalid = (
        (inline, {"base": base}, "inline window uses require only local components"),
        (direct, {"base": None}, "named window uses require one exact base reference"),
        (
            extended,
            {"base": None},
            "named window uses require one exact base reference",
        ),
        (
            direct,
            {"spec": nonempty},
            "direct named-window uses forbid local components",
        ),
    )
    for expression, changes, message in invalid:
        with pytest.raises(ValueError, match=message):
            dataclasses.replace(expression, **cast(Any, changes))
    with pytest.raises(TypeError, match="spec must be a WindowSpec"):
        dataclasses.replace(inline, spec=cast(Any, None))
    with pytest.raises(
        TypeError, match="window frame must be an exact AuthoredWindowFrame"
    ):
        dataclasses.replace(spec, frame=cast(Any, object()))


def test_empty_named_window_constructor_preserves_present_and_absent_specs() -> None:
    span = Span(path="empty-window.pietto", line=1, column=1, end_line=1, end_column=2)
    spec = WindowSpec(span=span, partition_by=(), order_by=())
    base = ast_nodes.NamedWindowReference(span=span, name="root")
    for reference in (None, base):
        declaration = ast_nodes.NamedWindowDeclaration(
            span=span, name="named", base=reference, spec=spec
        )
        absent = dataclasses.replace(declaration, spec=None)
        assert declaration.base is absent.base is reference
        assert declaration.spec is spec
        assert absent.spec is None
        assert declaration != absent
        with pytest.raises(
            TypeError, match="named-window declaration spec must be exact"
        ):
            dataclasses.replace(declaration, spec=cast(Any, object()))


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
    if name == "empty_window":
        assert not expression.spec.has_components
    assert tuple(item.direction for item in expression.spec.order_by) == directions
    assert expression.identity.name == "row_number"
    assert expression.identity.namespace == ()


@pytest.mark.parametrize(("call", "expected"), CALL_ARGUMENT_CASES)
def test_parser_preserves_call_arguments_and_trailing_comma(
    call: str,
    expected: tuple[str | int, ...],
) -> None:
    expression = _window_expression(
        _window_query("order by observed_at", projection=f"value = {call}")
    )
    assert tuple(
        _literal_argument_value(item) for item in expression.call.arguments
    ) == (expected)


@pytest.mark.parametrize("function_name", CANDIDATE_IDENTITY_CASES)
def test_parser_preserves_function_candidate_identity(function_name: str) -> None:
    expression = _window_expression(
        _window_query(
            "order by observed_at",
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
            "order by observed_at",
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
        _window_query("partition by id", projection=f"value = {call}()")
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
        "        rn = row_number() window(order by observed_at)\n"
        "        value\n"
        "        previous = lag(value, 1) window(partition by account_id)\n"
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
    assert expression.span.path == f"span-{name}.pietto"
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
    expression = _window_expression(_window_query(f"order by {item_source}"))
    item = expression.spec.order_by[0]
    assert item.direction == direction
    assert _span_tuple(item.span) == item_span
    assert _span_tuple(item.expression.span) == (4, 43, 4, 54)


def test_window_order_integer_literal_bypasses_final_order_ordinal_rejection() -> None:
    expression = _window_expression(_window_query("order by 1"))
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


def test_project_parse_only_path_remains_deferred_without_window_result_dependency_or_lineage() -> (
    None
):
    expression = _window_expression(_window_query("order by observed_at"))
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


def test_modern_parenthesized_windows_keep_inline_and_named_identities() -> None:
    from pietto.ast_nodes import AuthoredWindowFrameKind, WindowUseKind

    result = parse_source(
        "query q:\n"
        "    from rows\n"
        "    let base = window(partition by group_id)\n"
        "    select:\n"
        "        ranked = row_number() window(partition by group_id order by id desc rows between 2 preceding and current row exclude ties)\n"
        "        named = row_number() window base\n"
        "        extended = row_number() window base(order by id)\n"
    )
    assert result.diagnostics == ()
    assert result.ast is not None
    query = result.ast.definitions[0]
    assert isinstance(query, QueryDef)
    inline, named, extended = [item.expression for item in query.select_items]
    assert isinstance(inline, WindowExpr) and inline.use_kind is WindowUseKind.INLINE
    assert inline.spec.frame.kind is AuthoredWindowFrameKind.BETWEEN
    assert (
        isinstance(named, WindowExpr) and named.use_kind is WindowUseKind.NAMED_DIRECT
    )
    assert (
        isinstance(extended, WindowExpr)
        and extended.use_kind is WindowUseKind.NAMED_EXTENDED
    )
    assert query.named_windows[0].name == "base"


def test_modern_single_line_window_select_is_admitted() -> None:
    result = parse_source(
        "query q:\n    from rows\n    select ranked = row_number() window(order by id)\n"
    )
    assert result.diagnostics == ()
    assert result.ast is not None


def test_parenthesized_empty_windows_preserve_authored_use_and_declaration_identity() -> (
    None
):
    source = """query q:
    from rows
    let root = window()
    let alias = window root
    let extended_alias = window root()
    select:
        inline = row_number() window()
        direct = row_number() window root
        extended = row_number() window root()
"""
    result = parse_source(source, path="empty-window.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    query = result.ast.definitions[0]
    assert isinstance(query, QueryDef)
    inline, direct, extended = [item.expression for item in query.select_items]
    assert isinstance(inline, WindowExpr)
    assert isinstance(direct, WindowExpr)
    assert isinstance(extended, WindowExpr)
    assert inline.use_kind is ast_nodes.WindowUseKind.INLINE and inline.base is None
    assert direct.use_kind is ast_nodes.WindowUseKind.NAMED_DIRECT
    assert extended.use_kind is ast_nodes.WindowUseKind.NAMED_EXTENDED
    assert direct.base is not None and extended.base is not None
    assert direct.base.name == extended.base.name == "root"
    assert direct.base is not extended.base
    assert inline.spec is not direct.spec and direct.spec is not extended.spec
    for expression, spelling in zip(
        (inline, direct, extended),
        ("window()", "window root", "window root()"),
        strict=True,
    ):
        assert not expression.spec.has_components
        span = expression.spec.span
        assert span.path == "empty-window.pietto" and span.line == span.end_line
        assert (
            source.splitlines()[span.line - 1][span.column - 1 : span.end_column - 1]
            == spelling
        )
    root, alias, extended_alias = query.named_windows
    assert root.base is None and root.spec is not None
    assert not root.spec.has_components
    assert root.spec.span == root.span
    assert alias.base is not None and alias.base.name == "root" and alias.spec is None
    assert extended_alias.base is not None and extended_alias.base.name == "root"
    assert extended_alias.spec is not None and not extended_alias.spec.has_components
    assert extended_alias.spec.span == extended_alias.span
    assert root.spec is not extended_alias.spec
