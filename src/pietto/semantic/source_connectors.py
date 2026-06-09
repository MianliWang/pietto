"""Static signature validation for built-in source connectors."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    NameExpr,
    Node,
    Script,
    SourceDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import TypeKind, ValueType, ValueTypeKind

_POSTGRES_TABLE = "postgres.table"


def check_source_connectors(
    script: Script,
    expression_value_types: Mapping[Expression, ValueType],
) -> list[Diagnostic]:
    """Validate source connectors against the minimal built-in catalog."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, SourceDef):
            continue
        diagnostic = _check_connector(
            definition.connector,
            expression_value_types,
        )
        if diagnostic is not None:
            diagnostics.append(diagnostic)
    return diagnostics


def _check_connector(
    expression: Expression,
    expression_value_types: Mapping[Expression, ValueType],
) -> Diagnostic | None:
    """Validate one connector call without database access or introspection."""

    if not isinstance(expression, CallExpr):
        return _connector_diagnostic(
            expression,
            message="Invalid source connector expression",
        )

    argument_types = tuple(
        expression_value_types.get(argument) for argument in expression.arguments
    )
    if any(
        value_type is not None and value_type.kind is ValueTypeKind.UNKNOWN
        for value_type in argument_types
    ):
        return None

    connector_name = _callee_name(expression)
    if connector_name != _POSTGRES_TABLE:
        return _connector_diagnostic(
            expression,
            message=f"Unknown source connector: {connector_name}",
        )

    if len(argument_types) != 1:
        return _invalid_arguments_diagnostic(expression, connector_name)

    argument_type = argument_types[0]
    if (
        argument_type is None
        or argument_type.resolved_type.kind is not TypeKind.BUILTIN
        or argument_type.resolved_type.name != "Text"
    ):
        return _invalid_arguments_diagnostic(expression, connector_name)
    return None


def _callee_name(expression: CallExpr) -> str:
    """Return the source-level name of a connector call target."""

    if isinstance(expression.callee, NameExpr):
        return expression.callee.name
    assert isinstance(expression.callee, DottedNameExpr)
    return ".".join(expression.callee.parts)


def _invalid_arguments_diagnostic(
    expression: CallExpr,
    connector_name: str,
) -> Diagnostic:
    """Report a known connector call with incompatible arguments."""

    return _connector_diagnostic(
        expression,
        message=f"Invalid source connector arguments for {connector_name}",
    )


def _connector_diagnostic(node: Node, *, message: str) -> Diagnostic:
    """Create a connector diagnostic at the complete connector expression."""

    span = node.span
    return Diagnostic(
        code="PIE-S2306",
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
