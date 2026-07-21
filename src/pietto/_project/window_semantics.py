"""Private project carriers for future window result readiness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto._project.model import (
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectSymbol,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
)
from pietto.ast_nodes import QueryDef, TableDef
from pietto.errors import SourceLocation
from pietto.semantic.window_semantics import (
    WindowExpressionSemanticFact,
    WindowOccurrenceIdentity,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowResultIdentity:
    """One explicit project-local output identity for a window result."""

    definition: TableDef | QueryDef
    output_name: str
    occurrence: WindowOccurrenceIdentity
    role: ProjectRowResultRole = ProjectRowResultRole.WINDOW_RESULT

    def __post_init__(self) -> None:
        if type(self.definition) not in {TableDef, QueryDef}:
            raise TypeError("definition must be an exact TableDef or QueryDef")
        if type(self.output_name) is not str:
            raise TypeError("output_name must be an exact string")
        if not self.output_name.strip():
            raise ValueError("output_name must be nonblank")
        if type(self.occurrence) is not WindowOccurrenceIdentity:
            raise TypeError("occurrence must be an exact WindowOccurrenceIdentity")
        if type(self.role) is not ProjectRowResultRole:
            raise TypeError("role must be an exact ProjectRowResultRole")
        if self.role is not ProjectRowResultRole.WINDOW_RESULT:
            raise ValueError("window result identity role must be WINDOW_RESULT")
        if self.definition.name != self.occurrence.relation_name:
            raise ValueError("definition name must equal occurrence relation_name")


class WindowDependencyRole(StrEnum):
    """Source-ordered dependency roles for private window readiness."""

    RELATION_INPUT = "relation_input"
    WINDOW_ARGUMENT = "window_argument"
    WINDOW_DEFAULT = "window_default"
    WINDOW_PARTITION = "window_partition"
    WINDOW_ORDER = "window_order"


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowDependencyOccurrence:
    """One duplicate-preserving resolved dependency occurrence."""

    global_ordinal: int
    role_ordinal: int
    role: WindowDependencyRole
    target: ProjectRowDependencyNode
    location: SourceLocation

    def __post_init__(self) -> None:
        if type(self.global_ordinal) is not int:
            raise TypeError("global_ordinal must be an exact integer")
        if self.global_ordinal < 0:
            raise ValueError("global_ordinal must be nonnegative")
        if type(self.role_ordinal) is not int:
            raise TypeError("role_ordinal must be an exact integer")
        if self.role_ordinal < 0:
            raise ValueError("role_ordinal must be nonnegative")
        if type(self.role) is not WindowDependencyRole:
            raise TypeError("role must be an exact WindowDependencyRole")
        if type(self.target) is not ProjectRowDependencyNode:
            raise TypeError("target must be an exact ProjectRowDependencyNode")
        if type(self.location) is not SourceLocation:
            raise TypeError("location must be an exact SourceLocation")
        if self.role is WindowDependencyRole.RELATION_INPUT:
            if self.target.kind is not ProjectRowDependencyNodeKind.RELATION_INPUT:
                raise ValueError("RELATION_INPUT requires a relation-input target")
        elif self.target.kind not in {
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
            ProjectRowDependencyNodeKind.LET_BINDING,
        }:
            raise ValueError(
                "window expression dependencies require upstream-field or let targets"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowDependencyEdge:
    """One first-occurrence-deduplicated role and target pair."""

    role: WindowDependencyRole
    target: ProjectRowDependencyNode

    def __post_init__(self) -> None:
        if type(self.role) is not WindowDependencyRole:
            raise TypeError("role must be an exact WindowDependencyRole")
        if type(self.target) is not ProjectRowDependencyNode:
            raise TypeError("target must be an exact ProjectRowDependencyNode")
        if self.role is WindowDependencyRole.RELATION_INPUT:
            if self.target.kind is not ProjectRowDependencyNodeKind.RELATION_INPUT:
                raise ValueError("RELATION_INPUT requires a relation-input target")
        elif self.target.kind not in {
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
            ProjectRowDependencyNodeKind.LET_BINDING,
        }:
            raise ValueError(
                "window expression dependencies require upstream-field or let targets"
            )


def deduplicate_window_dependency_edges(
    occurrences: tuple[WindowDependencyOccurrence, ...],
) -> tuple[WindowDependencyEdge, ...]:
    """Return role-target edges in deterministic first-occurrence order."""

    if type(occurrences) is not tuple:
        raise TypeError("occurrences must be an exact tuple")
    if any(type(item) is not WindowDependencyOccurrence for item in occurrences):
        raise TypeError("occurrences must contain exact WindowDependencyOccurrence")

    seen: list[tuple[WindowDependencyRole, ProjectRowDependencyNode]] = []
    edges: list[WindowDependencyEdge] = []
    for occurrence in occurrences:
        key = (occurrence.role, occurrence.target)
        if key in seen:
            continue
        seen.append(key)
        edges.append(
            WindowDependencyEdge(
                role=occurrence.role,
                target=occurrence.target,
            )
        )
    return tuple(edges)


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowResultProjectFact:
    """Atomic private result, dependency, and immediate-provenance evidence."""

    semantic_fact: WindowExpressionSemanticFact
    result_identity: WindowResultIdentity
    dependency_occurrences: tuple[WindowDependencyOccurrence, ...]
    dependency_edges: tuple[WindowDependencyEdge, ...]
    provenance: ProjectRowFieldProvenance

    def __post_init__(self) -> None:
        if type(self.semantic_fact) is not WindowExpressionSemanticFact:
            raise TypeError("semantic_fact must be exact WindowExpressionSemanticFact")
        if type(self.result_identity) is not WindowResultIdentity:
            raise TypeError("result_identity must be an exact WindowResultIdentity")
        if type(self.dependency_occurrences) is not tuple:
            raise TypeError("dependency_occurrences must be an exact tuple")
        if any(
            type(item) is not WindowDependencyOccurrence
            for item in self.dependency_occurrences
        ):
            raise TypeError(
                "dependency_occurrences require exact WindowDependencyOccurrence"
            )
        if type(self.dependency_edges) is not tuple:
            raise TypeError("dependency_edges must be an exact tuple")
        if any(
            type(item) is not WindowDependencyEdge for item in self.dependency_edges
        ):
            raise TypeError("dependency_edges require exact WindowDependencyEdge")
        if type(self.provenance) is not ProjectRowFieldProvenance:
            raise TypeError("provenance must be an exact ProjectRowFieldProvenance")

        if self.semantic_fact.occurrence != self.result_identity.occurrence:
            raise ValueError("semantic and result occurrences must match")
        if (
            self.result_identity.definition.name
            != self.semantic_fact.occurrence.relation_name
        ):
            raise ValueError("output relation identity must be consistent")

        expected_global_ordinals = tuple(range(len(self.dependency_occurrences)))
        if (
            tuple(item.global_ordinal for item in self.dependency_occurrences)
            != expected_global_ordinals
        ):
            raise ValueError("dependency global ordinals must be contiguous")

        role_order = tuple(WindowDependencyRole)
        role_positions = tuple(
            role_order.index(item.role) for item in self.dependency_occurrences
        )
        if role_positions != tuple(sorted(role_positions)):
            raise ValueError("dependency occurrences must preserve role block order")
        for role in role_order:
            role_occurrences = tuple(
                item for item in self.dependency_occurrences if item.role is role
            )
            if tuple(item.role_ordinal for item in role_occurrences) != tuple(
                range(len(role_occurrences))
            ):
                raise ValueError("dependency role ordinals must be contiguous")

        expected_edges = deduplicate_window_dependency_edges(
            self.dependency_occurrences
        )
        if self.dependency_edges != expected_edges:
            raise ValueError("dependency edges must equal first-occurrence derivation")

        relation_occurrences = tuple(
            item
            for item in self.dependency_occurrences
            if item.role is WindowDependencyRole.RELATION_INPUT
        )
        relation_edges = tuple(
            item
            for item in self.dependency_edges
            if item.role is WindowDependencyRole.RELATION_INPUT
        )
        argument_count = len(self.semantic_fact.expression.call.arguments)
        if argument_count == 0:
            if len(relation_occurrences) != 1 or len(relation_edges) != 1:
                raise ValueError(
                    "zero-argument window readiness requires one relation input"
                )
        elif relation_occurrences or relation_edges:
            raise ValueError("nonzero-argument window readiness forbids relation input")

        if type(self.provenance.kind) is not ProjectRowFieldProvenanceKind:
            raise TypeError(
                "provenance kind must be an exact ProjectRowFieldProvenanceKind"
            )
        if self.provenance.kind is not ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION:
            raise ValueError("window result provenance must be DERIVED_EXPRESSION")
        if (
            self.provenance.symbol is not None
            and type(self.provenance.symbol) is not ProjectSymbol
        ):
            raise TypeError("provenance symbol must be an exact ProjectSymbol")
        if (
            self.provenance.location is not None
            and type(self.provenance.location) is not SourceLocation
        ):
            raise TypeError("provenance location must be an exact SourceLocation")
        span = self.semantic_fact.occurrence.span
        expected_location = SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        )
        if self.provenance.location != expected_location:
            raise ValueError("provenance location must match occurrence location")
