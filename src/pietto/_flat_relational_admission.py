"""Private syntax availability shared by existing compiler entrypoints."""

from __future__ import annotations

from pietto import ast_nodes as ast
from pietto._syntax_admission import source_order
from pietto.ast_nodes import (
    AnyExpr,
    AuthoredJoinKind,
    Definition,
    JoinClause,
    QueryDef,
    SetRelationDef,
    Span,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()

# Shared by single-file, LEGACY_FLAT, PACKAGE_ROOT and an EXPLICIT_MODULES
# project whose operation did not complete, so each message holds in all four.
_EXPLICIT_MODULES = "an EXPLICIT_MODULES project (schema version 2)"

_KNOWN_DEFINITIONS = frozenset(
    {
        ast.TypeDef,
        ast.EnumDef,
        ast.ShapeDef,
        ast.ConstraintDef,
        ast.DeriveDef,
        ast.SourceDef,
        ast.TableDef,
        ast.QueryDef,
        ast.SetRelationDef,
    }
)


def unsupported_join(clause: JoinClause) -> bool:
    return clause.on_clause is not None or clause.kind not in {
        AuthoredJoinKind.INNER,
        AuthoredJoinKind.LEFT,
    }


def availability_diagnostic(span: Span, message: str) -> Diagnostic:
    return Diagnostic(
        code="PIE-S2334",
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


def legacy_flat_refused(script: ast.Script) -> tuple[JoinClause | AnyExpr, ...]:
    """Each JOIN and each any(...) of a LEGACY_FLAT project's script, which
    has neither in the current syntax: in any definition or relationship
    predicate, nested or not."""

    from pietto.semantic.inline_functions import _tree_nodes

    return tuple(
        node for node in _tree_nodes(script) if isinstance(node, (JoinClause, AnyExpr))
    )


def legacy_flat_refusals(script: ast.Script) -> tuple[Diagnostic, ...]:
    """PIE-S2334 of each JOIN and each any(...) of a LEGACY_FLAT project's
    script, once each in source order: a JOIN of any kind and target at its
    `on`, or at the JOIN without one, and an any(...) at the any(...). The
    tree holds a repeated comparison-chain operand once per comparison, so
    exact duplicates are dropped."""

    found = []
    for node in legacy_flat_refused(script):
        if type(node) is JoinClause:
            found.append(
                availability_diagnostic(
                    node.span if node.on_clause is None else node.on_clause.span,
                    f"JOIN {node.target_binding_name}: a schema_version = 1 "
                    "project has no JOIN in the current syntax; set "
                    "schema_version = 2 to check it.",
                )
            )
        else:
            found.append(
                availability_diagnostic(
                    node.span,
                    "any(...): a schema_version = 1 project has no any(...) in "
                    "the current syntax; set schema_version = 2 to check it.",
                )
            )
    return tuple(sorted(dict.fromkeys(found), key=source_order))


def syntax_diagnostics(
    definition: Definition, *, allow_distinct: bool = False, allow_joins: bool = False
) -> tuple[Diagnostic, ...]:
    if type(definition) not in _KNOWN_DEFINITIONS:
        return (
            availability_diagnostic(
                definition.span, "Definition semantics are not implemented."
            ),
        )
    if isinstance(definition, SetRelationDef):
        return (
            availability_diagnostic(
                definition.body.operator_span,
                "Set operations are available only when "
                f"{_EXPLICIT_MODULES} completes them.",
            ),
        )
    if not isinstance(definition, (TableDef, QueryDef)):
        return ()
    diagnostics = []
    for clause in () if allow_joins else definition.join_clauses:
        if clause.kind not in {AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT}:
            diagnostics.append(
                availability_diagnostic(
                    clause.span,
                    f"{clause.kind.value.upper()} JOIN is available only when "
                    f"{_EXPLICIT_MODULES} completes it.",
                )
            )
        if clause.on_clause is not None:
            diagnostics.append(
                availability_diagnostic(
                    clause.on_clause.span,
                    "JOIN-local ON is available only when "
                    f"{_EXPLICIT_MODULES} completes it.",
                )
            )
    if definition.distinct_clause is not None and not allow_distinct:
        diagnostics.append(
            availability_diagnostic(
                definition.distinct_clause.span,
                f"SELECT DISTINCT is available only when {_EXPLICIT_MODULES} "
                "completes it.",
            )
        )
    return tuple(diagnostics)
