"""Detached editor facts projected from one semantic analysis: a single file
whose check succeeds, or each module that a project editor check keeps."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from pietto.ast_nodes import (
    BlockRelationDef,
    Definition,
    Node,
    Script,
    SetRelationDef,
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
class EditorFacts:
    """The pure editor projection for one source document."""

    declarations: tuple[EditorDeclaration, ...] = ()
    uses: tuple[EditorUse, ...] = ()


def single_file_editor_facts(
    script: Script, model: SemanticModel, *, path: str | None = None
) -> EditorFacts:
    """Project exact single-file type and FROM resolutions into pure values."""

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
    span = node.span
    return SourceLocation(
        path=span.path if span.path is not None else path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
