"""Static signature validation for built-in source connectors."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping, Sequence

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    Node,
    Script,
    SourceDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import TypeKind, ValueType, ValueTypeKind

_POSTGRES_TABLE = "postgres.table"
_MYSQL_TABLE = "mysql.table"
_KNOWN_CONNECTORS = (_POSTGRES_TABLE, _MYSQL_TABLE)


def check_table_names(
    script: Script,
    reported: Sequence[Diagnostic],
) -> list[Diagnostic]:
    """Require one `<table>` or `<schema>.<table>` string per single-file connector.

    Single-file IR copies the argument as a static string, so an argument that
    is not a string literal is reported at the argument, unless `reported` (the
    connector argument and signature diagnostics) already has one inside the
    connector call. An unknown connector, or a known one without exactly one
    argument, is reported on the call when `reported` has nothing inside it.
    Project mode takes physical names from its emission contract instead, so
    only single-file analysis runs this check.
    """

    # Sorted diagnostic starts per path, so each connector is one lookup.
    starts: dict[str | None, list[tuple[int, int]]] = {}
    for reported_diagnostic in reported:
        location = reported_diagnostic.location
        starts.setdefault(location.path, []).append((location.line, location.column))
    for positions in starts.values():
        positions.sort()
    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, SourceDef):
            continue
        connector = definition.connector
        if not isinstance(connector, CallExpr):
            continue
        connector_name = _callee_name(connector)
        if connector_name not in _KNOWN_CONNECTORS or len(connector.arguments) != 1:
            # The signature check leaves a call with an Unknown argument to that
            # argument's error; an argument without one, such as an unquoted
            # dotted name, leaves the call's own error to this check.
            if not _has_start_within(starts, connector):
                diagnostics.append(
                    _invalid_arguments_diagnostic(connector, connector_name)
                    if connector_name in _KNOWN_CONNECTORS
                    else _connector_diagnostic(
                        connector,
                        message=f"Unknown source connector: {connector_name}",
                    )
                )
            continue
        argument = connector.arguments[0]
        if not isinstance(argument, LiteralExpr) or not isinstance(argument.value, str):
            if not _has_start_within(starts, connector):
                diagnostics.append(
                    _connector_diagnostic(
                        argument,
                        message=(
                            f"Invalid source connector arguments for {connector_name}: "
                            'expected a string literal "<table>" or "<schema>.<table>"'
                        ),
                    )
                )
            continue
        if connector_name == _MYSQL_TABLE and not argument.value:
            continue
        parts = argument.value.split(".")
        if (len(parts) == 1 and parts[0]) or (len(parts) == 2 and all(parts)):
            continue
        diagnostics.append(
            _connector_diagnostic(
                argument,
                message=(
                    f"Invalid source connector arguments for {connector_name}: "
                    "expected <table> or <schema>.<table>"
                ),
            )
        )
    return diagnostics


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
    if connector_name not in _KNOWN_CONNECTORS:
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
    if connector_name == _MYSQL_TABLE:
        argument = expression.arguments[0]
        if (
            not isinstance(argument, LiteralExpr)
            or not isinstance(argument.value, str)
            or not argument.value
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


def _has_start_within(
    starts: Mapping[str | None, Sequence[tuple[int, int]]], node: Node
) -> bool:
    """Return whether a sorted diagnostic start lies inside one node's half-open span."""

    span = node.span
    positions = starts.get(span.path, ())
    index = bisect_left(positions, (span.line, span.column))
    end = (span.end_line, span.end_column)
    return index < len(positions) and positions[index] < end


def _connector_diagnostic(node: Node, *, message: str) -> Diagnostic:
    """Create a connector diagnostic at one connector expression or argument."""

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
