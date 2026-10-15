"""Pre-admission gate for parsed forms whose semantics are not yet available."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import cast

from pietto.ast_nodes import (
    BlockRelationDef,
    CaptureClause,
    LetRelationDef,
    Node,
    QueryDef,
    QueryParameter,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    Script,
    SelectBody,
    Span,
    TableDef,
    TableFunctionFromClause,
    TypeExpr,
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


# Families whose semantics exist only for EXPLICIT_MODULES projects.
_EXPLICIT_MODULES_ADMITTED: frozenset[type[Node]] = frozenset(
    {
        LetRelationDef,
        ValuesBody,
        RelationExistsExpr,
        RelationScalarExpr,
        RelationMembershipExpr,
        CaptureClause,
    }
)
# Expression families admitted only inside a FROM-based relation body; in a
# shape, constraint, type argument or VALUES row they stay gated.
_BODY_ONLY: frozenset[type[Node]] = frozenset(
    {RelationExistsExpr, RelationScalarExpr, RelationMembershipExpr}
)
_BODIES: frozenset[type[Node]] = frozenset({TableDef, QueryDef, SelectBody})
# D70.07: one table or query declares at most this many relation lets.
_MAX_RELATION_LETS = 64


def explicit_modules_admits(kind: type[Node]) -> bool:
    """Whether EXPLICIT_MODULES admits one gated family (read at call time)."""

    return kind in _EXPLICIT_MODULES_ADMITTED


def _diagnostic(code: str, message: str, span: Span) -> Diagnostic:
    return Diagnostic(
        code=code,
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


def source_order(item: Diagnostic) -> tuple[str, int, int, str, int, int]:
    """The (path, line, column, code, end) order of pre-admission diagnostics."""

    location = item.location
    return (
        location.path or "",
        location.line,
        location.column,
        item.code,
        location.end_line or 0,
        location.end_column or 0,
    )


def unadmitted_syntax_diagnostics(
    script: Script, *, explicit_modules: bool = False
) -> tuple[Diagnostic, ...]:
    """Report every parsed occurrence of a form no existing reader may see.

    Single-file and LEGACY_FLAT callers keep every family gated; an
    EXPLICIT_MODULES caller admits the families its readers implement, up to
    ``_MAX_RELATION_LETS`` relation lets per table or query, and the header of
    an entry query built as a ``QueryDef`` (its FROM reads a relation and it
    declares no relation let), whose parameter types are still read; headers
    of any other body stay unadmitted. An EXISTS, scalar or IN read is admitted
    only inside a relation body.
    """

    found: list[Diagnostic] = []
    pending: list[tuple[object, bool]] = [(script, False)]
    while pending:
        value, body = pending.pop()
        kind = type(value)
        if kind is tuple:
            pending.extend((item, body) for item in cast(tuple[object, ...], value))
            continue
        if (
            kind is Span
            or kind.__module__ != "pietto.ast_nodes"
            or not is_dataclass(value)
        ):
            continue
        family = _UNADMITTED.get(cast(type[Node], kind))
        if family is not None and not (
            explicit_modules
            and kind in _EXPLICIT_MODULES_ADMITTED
            and (body or kind not in _BODY_ONLY)
        ):
            found.append(_diagnostic(*family, cast(Node, value).span))
        if explicit_modules and kind is BlockRelationDef:
            found.extend(
                _diagnostic(
                    "PIE-S2357",
                    "A table or query declares at most "
                    f"{_MAX_RELATION_LETS} relation lets.",
                    let.span,
                )
                for let in cast(BlockRelationDef, value).let_relations[
                    _MAX_RELATION_LETS:
                ]
            )
        body = (body or kind in _BODIES) and kind is not TypeExpr
        for item in fields(value):
            child = getattr(value, item.name)
            if explicit_modules and kind is QueryDef and item.name == "parameters":
                # The header is admitted; a form inside a parameter type is not.
                child = tuple(
                    parameter.type
                    for parameter in cast(tuple[QueryParameter, ...], child)
                )
            pending.append((child, body))
    return tuple(sorted(found, key=source_order))
