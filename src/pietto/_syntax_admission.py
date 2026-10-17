"""Pre-admission gate for parsed forms whose semantics are not yet available."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import cast

from pietto.ast_nodes import (
    AuthoredJoinKind,
    BlockRelationDef,
    CaptureClause,
    FromClause,
    FunctionDef,
    JoinClause,
    LetRelationDef,
    ModuleDeclarationKind,
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

# One closed entry per approved family, in planned unlock order. The messages
# hold in single-file, LEGACY_FLAT and PACKAGE_ROOT checks and in an
# EXPLICIT_MODULES project, which still gates the positions they name.
_EXPLICIT_MODULES = "EXPLICIT_MODULES projects (schema version 2)"
_IN_BODY = f"inside a FROM-based relation body in {_EXPLICIT_MODULES}"
_UNADMITTED: dict[type[Node], tuple[str, str]] = {
    LetRelationDef: (
        "PIE-S2345",
        f"Relation let declarations are available only in {_EXPLICIT_MODULES}.",
    ),
    QueryParameter: (
        "PIE-S2346",
        f"Query header parameters are available only in {_EXPLICIT_MODULES}, "
        "on a query that reads a relation with FROM and has no relation let "
        "reading a table function.",
    ),
    ValuesBody: (
        "PIE-S2347",
        f"Typed VALUES bodies are available only in {_EXPLICIT_MODULES}.",
    ),
    RelationScalarExpr: (
        "PIE-S2348",
        f"Scalar relation reads are available only {_IN_BODY}.",
    ),
    RelationExistsExpr: (
        "PIE-S2349",
        f"EXISTS relation reads are available only {_IN_BODY}.",
    ),
    RelationMembershipExpr: (
        "PIE-S2350",
        f"IN relation reads are available only {_IN_BODY}.",
    ),
    CaptureClause: (
        "PIE-S2351",
        f"Capture lines are available only in {_EXPLICIT_MODULES}.",
    ),
    TableFunctionFromClause: (
        "PIE-S2352",
        f"Table-function FROM inputs are available only in {_EXPLICIT_MODULES}.",
    ),
    FunctionDef: (
        "PIE-S2379",
        "Inline `def` functions are available only in single files and "
        f"{_EXPLICIT_MODULES}.",
    ),
}
# Semantics infer an omitted `from` only from relationships: a JOIN with
# `on` and a CROSS JOIN keep naming their source in every mode.
_SOURCE_REQUIRED = (
    "PIE-S2378",
    "A JOIN with `on`, or a CROSS JOIN, must name its source binding with `from`.",
)


# Families whose semantics exist only for EXPLICIT_MODULES projects.
_EXPLICIT_MODULES_ADMITTED: frozenset[type[Node]] = frozenset(
    {
        LetRelationDef,
        ValuesBody,
        TableFunctionFromClause,
        RelationExistsExpr,
        RelationScalarExpr,
        RelationMembershipExpr,
        CaptureClause,
        FunctionDef,
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


def admitted_header(definition: Node) -> bool:
    """An entry query whose own body reads a relation with ``from``; its
    relation lets may read the header too (Phase70 S11), unless one of them
    reads a table function: like a table-function body of its own, such a
    query keeps its header unadmitted."""

    if type(definition) is QueryDef:
        return True
    if type(definition) is not BlockRelationDef:
        return False
    block = cast(BlockRelationDef, definition)
    return (
        block.kind is ModuleDeclarationKind.QUERY
        and type(block.body) is SelectBody
        and type(cast(SelectBody, block.body).from_clause) is FromClause
        and not any(
            type(let.body) is SelectBody
            and type(cast(SelectBody, let.body).from_clause) is TableFunctionFromClause
            for let in block.let_relations
        )
    )


def unadmitted_syntax_diagnostics(
    script: Script, *, explicit_modules: bool = False, single_file: bool = False
) -> tuple[Diagnostic, ...]:
    """Report every parsed occurrence of a form no existing reader may see.

    Single-file and LEGACY_FLAT callers keep every family gated, except that
    a single-file caller admits inline ``def`` functions; an
    EXPLICIT_MODULES caller admits the families its readers implement, up to
    ``_MAX_RELATION_LETS`` relation lets per table or query, and the header of
    an entry query whose own body reads a relation with ``from``, with or
    without relation lets (none reading a table function), whose parameter
    types are still read; headers of any other body stay unadmitted. An
    EXISTS, scalar or IN read is admitted only inside a relation body.
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
            or single_file
            and kind is FunctionDef
        ):
            found.append(_diagnostic(*family, cast(Node, value).span))
        if kind is JoinClause:
            join = cast(JoinClause, value)
            if join.source_binding_name is None and (
                join.on_clause is not None or join.kind is AuthoredJoinKind.CROSS
            ):
                found.append(_diagnostic(*_SOURCE_REQUIRED, join.span))
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
            if (
                explicit_modules
                and item.name == "parameters"
                and admitted_header(cast(Node, value))
            ):
                # The header is admitted; a form inside a parameter type is not.
                child = tuple(
                    parameter.type
                    for parameter in cast(tuple[QueryParameter, ...], child)
                )
            pending.append((child, body))
    return tuple(sorted(found, key=source_order))
