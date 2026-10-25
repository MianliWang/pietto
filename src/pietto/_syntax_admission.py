"""Pre-admission gate for parsed forms whose semantics are not yet available."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
from threading import Event
from typing import Any, cast

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
from pietto.errors import Diagnostic, ParseCancelled, Severity, SourceLocation

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
# Legacy JOINs infer an omitted `from` only from relationships. Modern JOINs
# explicitly name their input and bind its source in semantic resolution.
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
            if (
                not join.uses_named_input
                and join.source_binding_name is None
                and (join.on_clause is not None or join.kind is AuthoredJoinKind.CROSS)
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


def _follows_select(declaration: Any) -> bool:
    """Whether a named-window declaration comes after its body's select.

    The lets after FROM hold their windows as relation steps, so a window
    straight in the body is the one written after select.
    """

    return type(declaration.parentCtx).__name__ == "TableBodyContext"


def modern_spelling_diagnostics(
    tree: object, *, path: str | Path | None = None, cancel: Event | None = None
) -> tuple[Diagnostic, ...]:
    """Reject retired spelling before the shared builder normalizes it away."""

    from antlr4 import ParserRuleContext
    from antlr4.tree.Tree import TerminalNodeImpl

    from pietto.errors import source_path

    diagnostics: list[Diagnostic] = []
    pending = [tree]
    while pending:
        if cancel is not None and cancel.is_set():
            raise ParseCancelled
        node = pending.pop()
        if not isinstance(node, ParserRuleContext):
            continue
        context: Any = node  # its generated rule accessors
        kind = type(node).__name__
        terminals = [
            child.getSymbol()
            for child in node.children or ()
            if isinstance(child, TerminalNodeImpl)
        ]
        text = [token.text for token in terminals]
        token = None
        suggestion = None
        if kind == "SourceDefinitionContext" and "is" in text:
            token = terminals[text.index("is")]
            suggestion = "Bind the source with '=' instead of 'is'."
        elif kind == "NullabilityModifierContext":
            # The modifier's type expression belongs to an alias, a field, ...
            owner = getattr(node.parentCtx, "parentCtx", None)
            if "not" in text:
                token = terminals[0]
                suggestion = (
                    "Write 'T' instead of 'T not null'; a bare type is never None."
                )
            elif type(owner).__name__ == "TypeDefinitionContext":
                # An alias names a non-null type; each value states `| None`.
                token = terminals[0]
                suggestion = "Declare 'type Name = T' and write 'Name | None' where a value may be None."
            elif "nullable" in text:
                token = terminals[0]
                suggestion = "Write 'T | None' instead of 'T nullable'."
        elif kind == "LiteralContext" and text and text[0] in {"true", "false", "null"}:
            token = terminals[0]
            suggestion = (
                "Use "
                + {"true": "True", "false": "False", "null": "None"}[text[0]]
                + "."
            )
        elif kind in {
            "ComparisonExpressionContext",
            "QualifyComparisonExpressionContext",
        }:
            if "between" in text:
                token = terminals[text.index("between")]
                suggestion = "Write 'lower <= value <= upper' instead of 'value between lower and upper'."
            elif "null" in text:
                token = terminals[text.index("null")]
                suggestion = "Write 'is None' or 'is not None'."
        elif (
            kind in {"PrimaryExpressionContext", "QualifyPrimaryExpressionContext"}
            and "cast" in text
        ):
            token = terminals[text.index("cast")]
            suggestion = "Use 'Float(value)' for the supported Int-to-Float conversion; other conversions remain unsupported."
        elif (
            kind in {"ConstraintBodyContext", "DeriveBodyContext"}
            and "return" not in text
        ):
            token = node.start
            suggestion = "Add 'return' before the body expression."
        elif (
            kind
            in {
                "UniqueDefinitionContext",
                "IndexDefinitionContext",
                "CheckDefinitionContext",
            }
            and "=" not in text
        ):
            token = node.start
            suggestion = "Use 'name = unique(fields)', 'name = index(fields)', or 'name = check(predicate)'."
        elif kind == "ImportStatementContext" and text and text[0] == "import":
            token = node.start
            suggestion = 'Write from "path" import kind Name, retaining each explicit declaration kind.'
        elif kind == "ExportStatementContext" and ":" in text:
            token = terminals[text.index(":")]
            suggestion = (
                "Write 'export kind Name' or a parenthesized list with explicit kinds."
            )
        elif kind == "RelationshipDefinitionContext":
            token = node.start
            suggestion = "Declare a shape-typed 'relationship Name(role: Shape, ...):' predicate; source-bound metadata requires an explicit migration review."
        elif kind == "JoinClauseContext" and context.start.text in {"semi", "anti"}:
            # Every semi/anti JOIN becomes an any() filter, never a left join.
            join = context.start.text
            target = context.identifier(0).getText()
            negation = "not " if join == "anti" else ""
            if "as" in text:
                token = terminals[text.index("as")]
                alias = context.identifier(1).getText()
                suggestion = (
                    f"Write 'where {negation}any(predicate for {alias} in {target})' "
                    f"instead of '{join} join {target} as {alias}'; relationship "
                    "traversal requires an explicit migration review."
                )
            else:
                token = context.start
                suggestion = (
                    f"Write 'where {negation}any(predicate for {target} in {target})' "
                    f"instead of '{join} join {target} on predicate'."
                )
        elif kind == "JoinClauseContext" and "as" in text:
            token = terminals[text.index("as")]
            suggestion = "Name the input with 'let alias = relation', then write 'left join alias on predicate'; relationship traversal requires an explicit migration review."
        elif kind == "EnumDefinitionContext" and ":" not in text:
            token = context.enumLine().start
            suggestion = (
                "Write ':' after the enum name, as in 'enum Status: active, suspended'."
            )
        elif kind == "LetClauseContext":
            token = node.start
            suggestion = "Write each new query name as 'let name = expression'."
        elif kind == "SatisfyingClauseContext" and "satisfying" in text:
            token = node.start
            suggestion = (
                "Use 'having predicate', or 'having:' followed by an indented block."
            )
        elif kind == "NamedWindowDeclarationContext" and (not text or text[0] != "let"):
            token = node.start
            suggestion = (
                "Name the window with 'let name = window(...)' among the lets "
                "after FROM and every JOIN, before 'where', 'group by' and 'select'."
            )
        elif kind == "NamedWindowDeclarationContext" and _follows_select(node):
            token = node.start
            suggestion = (
                "Move the window before 'select', among the lets after FROM and "
                "every JOIN, before 'where' and 'group by'."
            )
        elif (
            kind in {"WindowSpecContext", "QualifyInlineWindowSpecContext"}
            and ":" in text
        ):
            token = terminals[text.index(":")]
            suggestion = "Use 'window(partition by ... order by ...)' with parentheses."
        elif (
            kind
            in {
                "GroupByClauseContext",
                "SelectClauseContext",
                "OrderByClauseContext",
                "PartitionByClauseContext",
                "WhereClauseContext",
                "SatisfyingClauseContext",
            }
            and ":" in text
        ):
            colon = terminals[text.index(":")]
            following_start = next(
                (
                    child.start
                    for child in node.children or ()
                    if isinstance(child, ParserRuleContext)
                    and child.start is not None
                    and child.start.start > colon.start
                ),
                None,
            )
            if (
                following_start is not None
                and following_start.line == colon.line
                and (following_start.text or "").strip()
            ):
                token = colon
                suggestion = "Omit ':' for a single-line clause; keep ':' before an indented block."
        elif kind == "VersionDeclContext" and any("_" in (item or "") for item in text):
            token = next(item for item in terminals if "_" in (item.text or ""))
            suggestion = "Keep the existing numeric version metadata spelling without digit separators."
        if token is not None:
            # Text output prints only the message, so it states the fix too.
            diagnostics.append(
                Diagnostic(
                    code="PIE-P1000",
                    severity=Severity.ERROR,
                    message="This spelling is not accepted by the modern syntax. "
                    f"{suggestion}",
                    location=SourceLocation(
                        path=source_path(path), line=token.line, column=token.column + 1
                    ),
                    suggestion=suggestion,
                )
            )
        pending.extend(reversed(node.children or ()))
    return tuple(
        sorted(diagnostics, key=lambda item: (item.location.line, item.location.column))
    )
