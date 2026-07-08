"""Private project row-level lineage carrier for direct projections."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from pietto._project.model import (
    ProjectParsedInput,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
)
from pietto._project.row_dependency_graph import (
    ProjectRelationRowDependencyGraph,
    ProjectRowDependencyEdge,
    ProjectRowDependencyEdgeKind,
)
from pietto.ast_nodes import FromClause, QueryDef, SourceDef, TableDef
from pietto.errors import SourceLocation

_DerivedRelation = TableDef | QueryDef


class ProjectRowLineageStatus(StrEnum):
    """Private availability status for one relation row lineage carrier."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


class ProjectRowLineageReason(StrEnum):
    """Private deterministic reason for one relation row lineage carrier."""

    DIRECT_SOURCE_CONCRETE = "direct_source_concrete"
    TABLE_UPSTREAM_CONCRETE = "table_upstream_concrete"
    RELATION_UPSTREAM_CONCRETE = "relation_upstream_concrete"
    UNKNOWN_SCHEMA = "unknown_schema"
    DUPLICATE_OUTPUT_NAME = "duplicate_output_name"
    DEFERRED_PHASE48_BEHAVIOR = "deferred_phase48_behavior"
    UNRESOLVED_RELATION_BLOCKED = "unresolved_relation_blocked"
    CYCLE_BLOCKED = "cycle_blocked"
    UPSTREAM_UNKNOWN = "upstream_unknown"
    UPSTREAM_DEFERRED = "upstream_deferred"
    UPSTREAM_BLOCKED = "upstream_blocked"
    MISSING_ROW_SCHEMA_STATE = "missing_row_schema_state"
    MISSING_ROW_SCHEMA = "missing_row_schema"
    MISSING_UPSTREAM_SCHEMA = "missing_upstream_schema"
    MISSING_DEPENDENCY_GRAPH = "missing_dependency_graph"


class ProjectRowLineageSegmentKind(StrEnum):
    """Private minimal lineage segment kinds."""

    SOURCE_FIELD = "source_field"
    UPSTREAM_FIELD = "upstream_field"
    OUTPUT_FIELD = "output_field"


class ProjectRowLineageFactKind(StrEnum):
    """Private minimal lineage fact kinds."""

    DIRECT_PROJECTION = "direct_projection"
    RENAMED_PROJECTION = "renamed_projection"


@dataclass(frozen=True, slots=True)
class ProjectRowLineageSegment:
    """One private row lineage segment."""

    kind: ProjectRowLineageSegmentKind
    name: str
    relation_name: str | None = None
    source_name: str | None = None
    field_name: str | None = None
    output_name: str | None = None

    def __post_init__(self) -> None:
        """Validate private segment invariants."""

        if not isinstance(self.kind, ProjectRowLineageSegmentKind):
            raise ValueError("Project row lineage segment requires a kind")


@dataclass(frozen=True, slots=True)
class ProjectRowLineageFact:
    """One private immediate row lineage fact."""

    kind: ProjectRowLineageFactKind
    output_segment: ProjectRowLineageSegment
    upstream_segment: ProjectRowLineageSegment
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        """Validate private fact invariants."""

        if not isinstance(self.kind, ProjectRowLineageFactKind):
            raise ValueError("Project row lineage fact requires a kind")


@dataclass(frozen=True, slots=True)
class ProjectRelationRowLineage:
    """Private minimal row lineage facts for one project relation."""

    status: ProjectRowLineageStatus
    reason: ProjectRowLineageReason
    facts: tuple[ProjectRowLineageFact, ...] = ()

    def __post_init__(self) -> None:
        """Copy fact collections into immutable tuples and validate status."""

        if not isinstance(self.status, ProjectRowLineageStatus):
            raise ValueError("Project row lineage requires a status")
        if not isinstance(self.reason, ProjectRowLineageReason):
            raise ValueError("Project row lineage requires a reason")
        object.__setattr__(self, "facts", tuple(self.facts))
        if self.status is not ProjectRowLineageStatus.CONCRETE and self.facts:
            raise ValueError("Non-concrete project row lineage forbids facts")


def build_project_relation_row_lineages(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    relation_row_schemas: Mapping[_DerivedRelation, ProjectRowSchema],
    relation_row_schema_states: Mapping[
        _DerivedRelation, ProjectRelationRowSchemaState
    ],
    relation_row_dependency_graphs: Mapping[
        _DerivedRelation, ProjectRelationRowDependencyGraph
    ],
) -> dict[_DerivedRelation, ProjectRelationRowLineage]:
    """Build private minimal row lineage carriers for project relations."""

    lineages: dict[_DerivedRelation, ProjectRelationRowLineage] = {}
    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue
            lineages[definition] = _build_relation_row_lineage(
                definition,
                relation_resolutions=relation_resolutions,
                relation_row_schemas=relation_row_schemas,
                relation_row_schema_states=relation_row_schema_states,
                relation_row_dependency_graphs=relation_row_dependency_graphs,
            )
    return lineages


def _build_relation_row_lineage(
    definition: _DerivedRelation,
    *,
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    relation_row_schemas: Mapping[_DerivedRelation, ProjectRowSchema],
    relation_row_schema_states: Mapping[
        _DerivedRelation, ProjectRelationRowSchemaState
    ],
    relation_row_dependency_graphs: Mapping[
        _DerivedRelation, ProjectRelationRowDependencyGraph
    ],
) -> ProjectRelationRowLineage:
    state = relation_row_schema_states.get(definition)
    if state is None:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus.BLOCKED,
            reason=ProjectRowLineageReason.MISSING_ROW_SCHEMA_STATE,
        )
    if state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus(state.status.value),
            reason=_reason_from_row_schema_reason(state.reason),
        )

    row_schema = relation_row_schemas.get(definition)
    if row_schema is None or row_schema.is_unknown:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus.UNKNOWN,
            reason=ProjectRowLineageReason.MISSING_ROW_SCHEMA,
        )

    graph = relation_row_dependency_graphs.get(definition)
    if graph is None:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus.BLOCKED,
            reason=ProjectRowLineageReason.MISSING_DEPENDENCY_GRAPH,
        )
    if graph.status.value != ProjectRowLineageStatus.CONCRETE.value:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus(graph.status.value),
            reason=ProjectRowLineageReason(graph.reason.value),
        )

    upstream_symbol = relation_resolutions.get(definition.from_clause)
    if upstream_symbol is None:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus.BLOCKED,
            reason=ProjectRowLineageReason.UNRESOLVED_RELATION_BLOCKED,
        )

    return ProjectRelationRowLineage(
        status=ProjectRowLineageStatus.CONCRETE,
        reason=ProjectRowLineageReason(graph.reason.value),
        facts=tuple(
            _direct_or_renamed_lineage_fact(
                edge,
                definition=definition,
                upstream_symbol=upstream_symbol,
            )
            for edge in graph.edges
            if edge.kind
            in (
                ProjectRowDependencyEdgeKind.DIRECT_PROJECTION,
                ProjectRowDependencyEdgeKind.RENAMED_PROJECTION,
            )
        ),
    )


def _direct_or_renamed_lineage_fact(
    edge: ProjectRowDependencyEdge,
    *,
    definition: _DerivedRelation,
    upstream_symbol: ProjectSymbol,
) -> ProjectRowLineageFact:
    return ProjectRowLineageFact(
        kind=ProjectRowLineageFactKind(edge.kind.value),
        output_segment=ProjectRowLineageSegment(
            kind=ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            name=edge.from_node.name,
            relation_name=definition.name,
            output_name=edge.from_node.output_name or edge.from_node.name,
        ),
        upstream_segment=_upstream_segment(edge, upstream_symbol=upstream_symbol),
        location=edge.location,
    )


def _upstream_segment(
    edge: ProjectRowDependencyEdge,
    *,
    upstream_symbol: ProjectSymbol,
) -> ProjectRowLineageSegment:
    field_name = edge.to_node.field_name
    if upstream_symbol.kind is ProjectSymbolKind.SOURCE and isinstance(
        upstream_symbol.definition,
        SourceDef,
    ):
        return ProjectRowLineageSegment(
            kind=ProjectRowLineageSegmentKind.SOURCE_FIELD,
            name=edge.to_node.name,
            source_name=upstream_symbol.name,
            field_name=field_name,
        )

    return ProjectRowLineageSegment(
        kind=ProjectRowLineageSegmentKind.UPSTREAM_FIELD,
        name=edge.to_node.name,
        relation_name=upstream_symbol.name,
        field_name=field_name,
    )


def _non_concrete_lineage(
    *,
    status: ProjectRowLineageStatus,
    reason: ProjectRowLineageReason,
) -> ProjectRelationRowLineage:
    return ProjectRelationRowLineage(status=status, reason=reason)


def _reason_from_row_schema_reason(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectRowLineageReason:
    return ProjectRowLineageReason(reason.value)
