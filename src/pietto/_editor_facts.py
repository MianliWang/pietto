"""Detached editor facts projected from one semantic analysis: a single file
whose check succeeds, or each module that a project editor check keeps."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from pietto.ast_nodes import (
    BlockRelationDef,
    Definition,
    FieldDef,
    ImportStatement,
    LetBinding,
    LetRelationDef,
    Node,
    Script,
    SetRelationDef,
    SourceDef,
    Span,
)
from pietto.errors import SourceLocation
from pietto.semantic.model import SemanticModel


@dataclass(frozen=True, slots=True)
class EditorDeclaration:
    """One declaration location and display value detached from semantic state."""

    location: SourceLocation
    name: str
    kind: int
    detail: str


@dataclass(frozen=True, slots=True)
class EditorUse:
    """One exact authored use, never a name-based approximation."""

    location: SourceLocation
    detail: str
    target: EditorDeclaration | None


@dataclass(frozen=True, slots=True)
class EditorLink:
    """One import path occurrence and the path of the one module that the
    module graph resolved it to."""

    location: SourceLocation
    target: str


@dataclass(frozen=True, slots=True)
class EditorFacts:
    """The pure editor projection for one source document."""

    declarations: tuple[EditorDeclaration, ...] = ()
    uses: tuple[EditorUse, ...] = ()
    links: tuple[EditorLink, ...] = ()


def single_file_editor_facts(
    script: Script, model: SemanticModel, *, path: str | None = None
) -> EditorFacts:
    """Project exact single-file type and FROM resolutions, JOIN field reads
    and relationship calls into pure values."""

    declarations = tuple(
        declaration
        for definition in authored_declarations(script)
        if (declaration := _declaration(definition, path=path)) is not None
    )
    uses: list[EditorUse] = []
    for from_clause, target in model.from_resolutions.items():
        uses.append(
            EditorUse(
                location=_location(from_clause, path=path),
                detail=_display(target),
                target=_declaration(target, path=path),
            )
        )
    for type_expr, resolved in model.type_resolutions.items():
        # The hover shows the canonical type, as in a project; the target
        # stays the direct declaration, such as an alias. Analysis expands
        # every resolved type expression.
        canonical = model.type_expansions[type_expr]
        definition = resolved.definition
        target = (
            _declaration(definition, path=path)
            if isinstance(definition, Definition)
            else None
        )
        uses.append(
            EditorUse(
                location=_location(type_expr, path=path),
                detail=f"{canonical.kind.value} {canonical.name}",
                target=target,
            )
        )
    # Only the occurrence the author wrote: a copy that inlining a def or
    # expanding a relationship call adds has occurrence above 0.
    for joins in model.relation_joins.values():
        relations = {item.ordinal: item.relation for item in joins.inputs}
        for read_expression, read in joins.field_reads.items():
            if read_expression.span.occurrence:
                continue
            relation = relations[read.input]
            schema = (
                model.source_row_schemas.get(relation)
                if isinstance(relation, SourceDef)
                else None
            )
            row = None if schema is None else schema.fields.get(read.field)
            definition = None if row is None else row.definition
            uses.append(
                editor_use(
                    read_expression,
                    f"field {read.field}",
                    None
                    if definition is None
                    else editor_binding(definition, "field", path=path),
                    path=path,
                )
            )
    for call in model.relationship_calls:
        callee = call.call.callee
        if callee.span.occurrence:
            continue
        declaration = call.template.declaration
        uses.append(
            editor_use(
                callee,
                f"relationship {declaration.name}",
                _declaration(declaration, path=path),
                path=path,
            )
        )
    return EditorFacts(declarations=declarations, uses=tuple(uses))


def authored_declarations(script: Script) -> tuple[Node, ...]:
    """Every currently admitted named top-level declaration in source order."""

    declarations: Iterable[Node] = (
        *script.definitions,
        *script.relationship_templates,
        *script.constants,
    )
    return tuple(
        sorted(declarations, key=lambda item: (item.span.line, item.span.column))
    )


def editor_declaration(
    definition: Node, *, path: str | None = None
) -> EditorDeclaration | None:
    """Detach a named declaration, or refuse a node without that identity."""

    return _declaration(definition, path=path)


def editor_use(
    node: Node,
    detail: str,
    target: EditorDeclaration | None,
    *,
    path: str | None = None,
) -> EditorUse:
    """Build one detached use after its caller already proved its binding."""

    return EditorUse(location=_location(node, path=path), detail=detail, target=target)


def editor_binding(
    node: FieldDef | LetBinding | LetRelationDef, word: str, *, path: str | None = None
) -> EditorDeclaration:
    """Detach a field, `let` or relation-let target, which is no top-level
    declaration, after its caller proved the binding."""

    return EditorDeclaration(
        location=_location(node, path=path),
        name=node.name,
        kind=8 if word == "field" else 13,
        detail=f"{word} {node.name}",
    )


def editor_link(statement: ImportStatement, target: str, *, path: str) -> EditorLink:
    """Detach one import path after its caller resolved it to one module."""

    return EditorLink(
        location=_span_location(statement.target_span, path), target=target
    )


def _declaration(
    definition: Node, *, path: str | None = None
) -> EditorDeclaration | None:
    name = getattr(definition, "name", None)
    if not isinstance(name, str) or not name:
        return None
    kind = {
        "EnumDef": 10,
        "FunctionDef": 12,
        "RelationshipTemplate": 12,
        "SourceDef": 13,
        "ConstantDef": 14,
    }.get(type(definition).__name__, 5)
    return EditorDeclaration(
        location=_location(definition, path=path),
        name=name,
        kind=kind,
        detail=f"{_kind(definition)} {name}",
    )


def _display(definition: Definition) -> str:
    return f"{_kind(definition)} {definition.name}"


def _kind(definition: Node) -> str:
    """The authored declaration keyword, or `constant`, which has none."""

    if isinstance(definition, SetRelationDef | BlockRelationDef):
        return definition.kind.value
    name = type(definition).__name__
    return {
        "ConstantDef": "constant",
        "FunctionDef": "def",
        "RelationshipTemplate": "relationship",
    }.get(name, name.removesuffix("Def").lower())


def _location(node: Node, *, path: str | None = None) -> SourceLocation:
    return _span_location(node.span, path)


def _span_location(span: Span, path: str | None) -> SourceLocation:
    return SourceLocation(
        path=span.path if span.path is not None else path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
