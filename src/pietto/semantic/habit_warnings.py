"""Warnings for spellings that a Python reader misreads in SQL (owner decision
S4): `/` of two `Int` values truncates (PIE-S2106) and a `None` option of an
`in` list never matches (PIE-S2107). Both are accepted and emitted as written,
in every check mode; `--`, which SQL reads as a comment, is PIE-P1009 of the
parser.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import fields, is_dataclass

from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    Expression,
    FunctionDef,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    Script,
    Span,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.expressions import (
    _is_canonical_builtin,
    always_null,
    infer_row_expression,
)
from pietto.semantic.inline_functions import def_body_schemas
from pietto.semantic.model import SemanticModel, ValueType, ValueTypeKind

__all__: tuple[str, ...] = ()

_INT_DIVISION = (
    "`/` of two Int values truncates in SQL (`7 / 2` is 3, not 3.5); "
    "write `Float(x) / y` for a fractional result"
)
_NULL_OPTION = (
    "A `None` option never matches: SQL tests `x == None`, which is never true; "
    'to match None too, write `x == "a" or x is None`'
)
_NULL_NOT_IN_OPTION = (
    "A `None` option makes `not in` never true: SQL tests `x != None`, which is "
    'never true; write `x != "a" and x is not None`'
)


def habit_warnings(
    parsed: Script,
    analyzed: Script,
    model: SemanticModel,
    diagnostics: Sequence[Diagnostic],
) -> tuple[Diagnostic, ...]:
    """The S4 warnings of ``parsed``, in source order of each walk: tables and
    queries as ``analyzed`` types them, then each ``def`` body over its declared
    parameters. A `def` body is reported where it is written, not at a call."""

    defined = {item.name for item in parsed.definitions if type(item) is FunctionDef}
    # Analysis types a def's body at each call, where nothing is written.
    calls = {
        node.span
        for node in _nodes(parsed.definitions)
        if type(node) is CallExpr
        and type(node.callee) is NameExpr
        and node.callee.name in defined
    }
    errors = {
        _key(item.location) for item in diagnostics if item.severity is Severity.ERROR
    }
    found = list(
        _warnings(
            (
                node
                for node in _nodes(analyzed.definitions)
                if isinstance(node, Expression)
                and node.span.occurrence == 0
                and node.span not in calls
            ),
            model.expression_value_types,
            model,
            errors,
        )
    )
    for function, schema in def_body_schemas(parsed):
        types: dict[Expression, ValueType] = {}
        infer_row_expression(function.body, schema, types, [], report_unknown_name=True)
        found.extend(
            _warnings(
                (
                    node
                    for node in _nodes(function.body)
                    if isinstance(node, Expression)
                ),
                types,
                model,
                errors,
            )
        )
    # One written expression that analysis reads twice is reported once.
    return tuple(dict.fromkeys(found))


def _warnings(
    nodes: Iterator[Expression],
    types: Mapping[Expression, ValueType],
    model: SemanticModel,
    errors: set[tuple[object, ...]],
) -> Iterator[Diagnostic]:
    for node in nodes:
        if (
            type(node) is BinaryExpr
            and node.operator == "/"
            and all(
                not always_null(operand) and _is_int(types.get(operand), model)
                for operand in (node.left, node.right)
            )
        ):
            yield _warning("PIE-S2106", _INT_DIVISION, node.span)
        elif (
            type(node) is MembershipExpr
            and not _is_null(node.value)
            and any(_is_null(option) for option in node.options)
            and not all(_is_null(option) for option in node.options)
            and _key(node.span) not in errors
        ):
            message = _NULL_NOT_IN_OPTION if node.negated else _NULL_OPTION
            yield _warning("PIE-S2107", message, node.span)


def _is_int(value_type: ValueType | None, model: SemanticModel) -> bool:
    return (
        value_type is not None
        and value_type.kind is ValueTypeKind.KNOWN
        and _is_canonical_builtin(value_type, "Int", model.type_expansions)
    )


def _is_null(expression: Expression) -> bool:
    return type(expression) is LiteralExpr and expression.value is None


def _nodes(root: object) -> Iterator[object]:
    """Every AST node at or below ``root``, parents before children."""

    pending = [root]
    while pending:
        value = pending.pop()
        if type(value) is tuple:
            pending.extend(reversed(value))
            continue
        if (
            type(value) is Span
            or not is_dataclass(value)
            or type(value).__module__ != "pietto.ast_nodes"
        ):
            continue
        yield value
        pending.extend(
            reversed([getattr(value, field.name) for field in fields(value)])
        )


def _key(location: SourceLocation | Span) -> tuple[object, ...]:
    return (
        location.path,
        location.line,
        location.column,
        location.end_line,
        location.end_column,
    )


def _warning(code: str, message: str, span: Span) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.WARNING,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
