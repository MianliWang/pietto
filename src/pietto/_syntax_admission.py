"""Pre-admission gate for parsed forms whose semantics are not yet available."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import cast

from pietto.ast_nodes import (
    CaptureClause,
    LetRelationDef,
    Node,
    QueryParameter,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    Script,
    Span,
    TableFunctionFromClause,
    ValuesBody,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()

# One closed entry per approved family, in planned unlock order.
_UNADMITTED: dict[type[Node], tuple[str, str]] = {
    LetRelationDef: (
        "PIE-S2345",
        "Let relation declaration semantics are not implemented.",
    ),
    QueryParameter: (
        "PIE-S2346",
        "Query header parameter semantics are not implemented.",
    ),
    ValuesBody: ("PIE-S2347", "VALUES body semantics are not implemented."),
    RelationScalarExpr: (
        "PIE-S2348",
        "Scalar relation read semantics are not implemented.",
    ),
    RelationExistsExpr: (
        "PIE-S2349",
        "EXISTS relation reference semantics are not implemented.",
    ),
    RelationMembershipExpr: (
        "PIE-S2350",
        "IN relation reference semantics are not implemented.",
    ),
    CaptureClause: ("PIE-S2351", "Capture line semantics are not implemented."),
    TableFunctionFromClause: (
        "PIE-S2352",
        "Table-function FROM input semantics are not implemented.",
    ),
}


def unadmitted_syntax_diagnostics(script: Script) -> tuple[Diagnostic, ...]:
    """Report every parsed occurrence of a form no existing reader may see."""

    found: list[Diagnostic] = []
    pending: list[object] = [script]
    while pending:
        value = pending.pop()
        kind = type(value)
        if kind is tuple:
            pending.extend(cast(tuple[object, ...], value))
            continue
        if (
            kind is Span
            or kind.__module__ != "pietto.ast_nodes"
            or not is_dataclass(value)
        ):
            continue
        family = _UNADMITTED.get(cast(type[Node], kind))
        if family is not None:
            span = cast(Node, value).span
            found.append(
                Diagnostic(
                    code=family[0],
                    severity=Severity.ERROR,
                    message=family[1],
                    location=SourceLocation(
                        path=span.path,
                        line=span.line,
                        column=span.column,
                        end_line=span.end_line,
                        end_column=span.end_column,
                    ),
                )
            )
        pending.extend(getattr(value, item.name) for item in fields(value))
    return tuple(
        sorted(
            found,
            key=lambda item: (
                item.location.path or "",
                item.location.line,
                item.location.column,
                item.code,
                item.location.end_line or 0,
                item.location.end_column or 0,
            ),
        )
    )
