"""Private project row-level lineage carrier for project relations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
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
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
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
    DUPLICATE_GROUP_KEY = "duplicate_group_key"
    UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT = "unavailable_aggregate_or_grouped_fact"
    INVALID_AGGREGATE_OR_GROUPED_OUTPUT = "invalid_aggregate_or_grouped_output"
    AGGREGATE_OR_GROUPED_DEFERRED = "aggregate_grouped_deferred"
    CONFLICTING_AGGREGATE_OR_GROUPED_FACTS = "conflicting_aggregate_or_grouped_facts"
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
    """Private lineage segment kinds."""

    SOURCE_FIELD = "source_field"
    UPSTREAM_FIELD = "upstream_field"
    OUTPUT_FIELD = "output_field"
    LET_BINDING = "let_binding"
    RELATION_INPUT = "relation_input"


class ProjectRowLineageFactKind(StrEnum):
    """Private lineage fact kinds."""

    DIRECT_PROJECTION = "direct_projection"
    RENAMED_PROJECTION = "renamed_projection"
    COMPUTED_EXPRESSION = "computed_expression"
    LET_OUTPUT = "let_output"
    LET_EXPRESSION = "let_expression"
    TRANSITIVE_DEPENDENCY = "transitive_dependency"
    AGGREGATE_ARGUMENT = "aggregate_argument"
    AGGREGATE_RELATION_INPUT = "aggregate_relation_input"


@dataclass(frozen=True, slots=True)
class ProjectRowLineageSegment:
    """One private row lineage segment."""

    kind: ProjectRowLineageSegmentKind
    name: str
    relation_name: str | None = None
    source_name: str | None = None
    field_name: str | None = None
    output_name: str | None = None
    binding_name: str | None = None

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
    """Build private row lineage carriers for project relations."""

    definitions: list[_DerivedRelation] = []
    relation_definitions_by_name: dict[str, _DerivedRelation] = {}
    base_lineages: dict[_DerivedRelation, ProjectRelationRowLineage] = {}
    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue
            definitions.append(definition)
            relation_definitions_by_name[definition.name] = definition
            base_lineages[definition] = _build_relation_row_lineage(
                definition,
                relation_resolutions=relation_resolutions,
                relation_row_schemas=relation_row_schemas,
                relation_row_schema_states=relation_row_schema_states,
                relation_row_dependency_graphs=relation_row_dependency_graphs,
            )

    expanded_lineages = _expand_relation_row_lineages(
        base_lineages,
        relation_definitions_by_name=relation_definitions_by_name,
    )
    return {
        definition: expanded_lineages[definition]
        for definition in definitions
        if definition in expanded_lineages
    }


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
    row_schema = relation_row_schemas.get(definition)
    graph = relation_row_dependency_graphs.get(definition)
    upstream_symbol = relation_resolutions.get(definition.from_clause)
    return _build_relation_row_lineage_from_bundle(
        definition=definition,
        upstream_symbol=upstream_symbol,
        row_schema=row_schema,
        state=state,
        dependency_graph=graph,
    )


def _build_relation_row_lineage_from_bundle(
    *,
    definition: _DerivedRelation,
    upstream_symbol: ProjectSymbol | None,
    row_schema: ProjectRowSchema | None,
    state: ProjectRelationRowSchemaState | None,
    dependency_graph: ProjectRelationRowDependencyGraph | None,
) -> ProjectRelationRowLineage:
    """Build one ordinary immediate lineage from a complete local bundle."""

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

    if row_schema is None or row_schema.is_unknown:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus.UNKNOWN,
            reason=ProjectRowLineageReason.MISSING_ROW_SCHEMA,
        )

    if dependency_graph is None:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus.BLOCKED,
            reason=ProjectRowLineageReason.MISSING_DEPENDENCY_GRAPH,
        )
    if dependency_graph.status.value != ProjectRowLineageStatus.CONCRETE.value:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus(dependency_graph.status.value),
            reason=ProjectRowLineageReason(dependency_graph.reason.value),
        )

    if upstream_symbol is None:
        return _non_concrete_lineage(
            status=ProjectRowLineageStatus.BLOCKED,
            reason=ProjectRowLineageReason.UNRESOLVED_RELATION_BLOCKED,
        )

    return ProjectRelationRowLineage(
        status=ProjectRowLineageStatus.CONCRETE,
        reason=ProjectRowLineageReason(dependency_graph.reason.value),
        facts=tuple(
            _lineage_fact_from_edge(
                edge,
                definition=definition,
                upstream_symbol=upstream_symbol,
            )
            for edge in dependency_graph.edges
            if _is_lineage_edge_kind(edge.kind)
        ),
    )


def build_project_relation_row_lineage(
    *,
    definition: _DerivedRelation,
    upstream_symbol: ProjectSymbol | None,
    row_schema: ProjectRowSchema | None,
    state: ProjectRelationRowSchemaState | None,
    dependency_graph: ProjectRelationRowDependencyGraph | None,
    upstream_lineage: ProjectRelationRowLineage | None,
) -> ProjectRelationRowLineage:
    """Build one expanded ordinary lineage from a completed upstream bundle."""

    base_lineage = _build_relation_row_lineage_from_bundle(
        definition=definition,
        upstream_symbol=upstream_symbol,
        row_schema=row_schema,
        state=state,
        dependency_graph=dependency_graph,
    )
    if base_lineage.status is not ProjectRowLineageStatus.CONCRETE:
        return base_lineage
    if upstream_symbol is None:
        return base_lineage

    upstream_definition = upstream_symbol.definition
    if upstream_symbol.kind is ProjectSymbolKind.SOURCE and isinstance(
        upstream_definition,
        SourceDef,
    ):
        if upstream_lineage is not None:
            raise ValueError("Source-upstream lineage must be absent")
        return _expand_relation_row_lineages(
            {definition: base_lineage},
            relation_definitions_by_name={definition.name: definition},
        )[definition]
    if upstream_symbol.kind not in {
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    } or not isinstance(upstream_definition, (TableDef, QueryDef)):
        raise ValueError("Ordinary lineage requires one immediate upstream")
    if (
        upstream_definition is definition
        or upstream_lineage is None
        or upstream_lineage.status is not ProjectRowLineageStatus.CONCRETE
    ):
        raise ValueError("Relation-upstream lineage must be complete")

    expanded = _expand_relation_row_lineages(
        {
            upstream_definition: upstream_lineage,
            definition: base_lineage,
        },
        relation_definitions_by_name={
            upstream_definition.name: upstream_definition,
            definition.name: definition,
        },
        preexpanded_lineages={upstream_definition: upstream_lineage},
    )
    return expanded[definition]


def _lineage_fact_from_edge(
    edge: ProjectRowDependencyEdge,
    *,
    definition: _DerivedRelation,
    upstream_symbol: ProjectSymbol,
) -> ProjectRowLineageFact:
    return ProjectRowLineageFact(
        kind=ProjectRowLineageFactKind(edge.kind.value),
        output_segment=_lineage_segment_from_node(
            edge.from_node,
            definition=definition,
            upstream_symbol=upstream_symbol,
        ),
        upstream_segment=_lineage_segment_from_node(
            edge.to_node,
            definition=definition,
            upstream_symbol=upstream_symbol,
        ),
        location=edge.location,
    )


def _lineage_segment_from_node(
    node: ProjectRowDependencyNode,
    *,
    definition: _DerivedRelation,
    upstream_symbol: ProjectSymbol,
) -> ProjectRowLineageSegment:
    if node.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
        return ProjectRowLineageSegment(
            kind=ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            name=node.name,
            relation_name=node.relation_name or definition.name,
            output_name=node.output_name or node.name,
        )
    if node.kind is ProjectRowDependencyNodeKind.LET_BINDING:
        binding_name = node.binding_name or node.name
        return ProjectRowLineageSegment(
            kind=ProjectRowLineageSegmentKind.LET_BINDING,
            name=binding_name,
            relation_name=node.relation_name or definition.name,
            binding_name=binding_name,
        )
    if node.kind is ProjectRowDependencyNodeKind.RELATION_INPUT:
        return ProjectRowLineageSegment(
            kind=ProjectRowLineageSegmentKind.RELATION_INPUT,
            name=node.name,
            relation_name=node.relation_name or upstream_symbol.name,
            source_name=node.source_name or upstream_symbol.name,
        )
    return _upstream_segment_from_node(node, upstream_symbol=upstream_symbol)


def _upstream_segment_from_node(
    node: ProjectRowDependencyNode,
    *,
    upstream_symbol: ProjectSymbol,
) -> ProjectRowLineageSegment:
    field_name = node.field_name
    node_name = node.name
    relation_name = node.relation_name or upstream_symbol.name
    source_name = node.source_name or upstream_symbol.name
    if node.kind is not ProjectRowDependencyNodeKind.UPSTREAM_FIELD:
        raise ValueError("Unsupported project row dependency node kind")
    if upstream_symbol.kind is ProjectSymbolKind.SOURCE and isinstance(
        upstream_symbol.definition,
        SourceDef,
    ):
        return ProjectRowLineageSegment(
            kind=ProjectRowLineageSegmentKind.SOURCE_FIELD,
            name=node_name,
            source_name=source_name,
            field_name=field_name,
        )
    return ProjectRowLineageSegment(
        kind=ProjectRowLineageSegmentKind.UPSTREAM_FIELD,
        name=node_name,
        relation_name=relation_name,
        field_name=field_name,
    )


def _expand_relation_row_lineages(
    base_lineages: Mapping[_DerivedRelation, ProjectRelationRowLineage],
    *,
    relation_definitions_by_name: Mapping[str, _DerivedRelation],
    preexpanded_lineages: Mapping[_DerivedRelation, ProjectRelationRowLineage]
    | None = None,
) -> dict[_DerivedRelation, ProjectRelationRowLineage]:
    expanded: dict[_DerivedRelation, ProjectRelationRowLineage] = dict(
        preexpanded_lineages or {}
    )
    active: set[_DerivedRelation] = set()

    def expand(definition: _DerivedRelation) -> ProjectRelationRowLineage:
        if definition in expanded:
            return expanded[definition]

        base_lineage = base_lineages[definition]
        if base_lineage.status is not ProjectRowLineageStatus.CONCRETE:
            expanded[definition] = base_lineage
            return base_lineage

        if definition in active:
            return base_lineage

        active.add(definition)
        facts: list[ProjectRowLineageFact] = []
        fact_keys: set[_LineageFactKey] = set()

        def add_fact(fact: ProjectRowLineageFact) -> None:
            key = _lineage_fact_key(fact)
            if key in fact_keys:
                return
            fact_keys.add(key)
            facts.append(fact)

        for fact in base_lineage.facts:
            add_fact(fact)
            for upstream_segment in _transitive_upstream_segments(
                fact.upstream_segment,
                current_relation_name=fact.output_segment.relation_name,
                base_lineages=base_lineages,
                expanded_lineages=expanded,
                relation_definitions_by_name=relation_definitions_by_name,
                expand=expand,
                visited_segments=set(),
            ):
                add_fact(
                    ProjectRowLineageFact(
                        kind=ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
                        output_segment=fact.output_segment,
                        upstream_segment=upstream_segment,
                        location=fact.location,
                    )
                )

        active.remove(definition)
        expanded_lineage = ProjectRelationRowLineage(
            status=base_lineage.status,
            reason=base_lineage.reason,
            facts=tuple(facts),
        )
        expanded[definition] = expanded_lineage
        return expanded_lineage

    for definition in base_lineages:
        expand(definition)
    return expanded


def _transitive_upstream_segments(
    segment: ProjectRowLineageSegment,
    *,
    current_relation_name: str | None,
    base_lineages: Mapping[_DerivedRelation, ProjectRelationRowLineage],
    expanded_lineages: Mapping[_DerivedRelation, ProjectRelationRowLineage],
    relation_definitions_by_name: Mapping[str, _DerivedRelation],
    expand: _LineageExpander,
    visited_segments: set[_LineageSegmentKey],
) -> tuple[ProjectRowLineageSegment, ...]:
    segment_key = _lineage_segment_key(segment)
    if segment_key in visited_segments:
        return ()
    visited_segments.add(segment_key)

    if segment.kind is ProjectRowLineageSegmentKind.UPSTREAM_FIELD:
        return _relation_transitive_upstream_segments(
            segment,
            current_relation_name=current_relation_name,
            expanded_lineages=expanded_lineages,
            relation_definitions_by_name=relation_definitions_by_name,
            expand=expand,
        )
    if segment.kind is ProjectRowLineageSegmentKind.LET_BINDING:
        return _let_transitive_upstream_segments(
            segment,
            current_relation_name=current_relation_name,
            base_lineages=base_lineages,
            expanded_lineages=expanded_lineages,
            relation_definitions_by_name=relation_definitions_by_name,
            expand=expand,
            visited_segments=visited_segments,
        )
    return ()


def _relation_transitive_upstream_segments(
    segment: ProjectRowLineageSegment,
    *,
    current_relation_name: str | None,
    expanded_lineages: Mapping[_DerivedRelation, ProjectRelationRowLineage],
    relation_definitions_by_name: Mapping[str, _DerivedRelation],
    expand: _LineageExpander,
) -> tuple[ProjectRowLineageSegment, ...]:
    relation_name = segment.relation_name
    output_name = segment.field_name or segment.output_name or segment.name
    if relation_name is None or output_name is None:
        return ()

    upstream_definition = relation_definitions_by_name.get(relation_name)
    if upstream_definition is None:
        return ()
    if upstream_definition.name == current_relation_name:
        return ()

    upstream_lineage = expanded_lineages.get(upstream_definition)
    if upstream_lineage is None:
        upstream_lineage = expand(upstream_definition)
    if upstream_lineage.status is not ProjectRowLineageStatus.CONCRETE:
        return ()

    return tuple(
        fact.upstream_segment
        for fact in upstream_lineage.facts
        if _segment_matches_output(fact.output_segment, output_name)
    )


def _let_transitive_upstream_segments(
    segment: ProjectRowLineageSegment,
    *,
    current_relation_name: str | None,
    base_lineages: Mapping[_DerivedRelation, ProjectRelationRowLineage],
    expanded_lineages: Mapping[_DerivedRelation, ProjectRelationRowLineage],
    relation_definitions_by_name: Mapping[str, _DerivedRelation],
    expand: _LineageExpander,
    visited_segments: set[_LineageSegmentKey],
) -> tuple[ProjectRowLineageSegment, ...]:
    relation_name = segment.relation_name or current_relation_name
    binding_name = segment.binding_name or segment.name
    if relation_name is None:
        return ()

    definition = relation_definitions_by_name.get(relation_name)
    if definition is None:
        return ()

    base_lineage = base_lineages.get(definition)
    if (
        base_lineage is None
        or base_lineage.status is not ProjectRowLineageStatus.CONCRETE
    ):
        return ()

    segments: list[ProjectRowLineageSegment] = []
    for fact in base_lineage.facts:
        if not _segment_matches_let_binding(fact.output_segment, binding_name):
            continue
        segments.append(fact.upstream_segment)
        segments.extend(
            _transitive_upstream_segments(
                fact.upstream_segment,
                current_relation_name=relation_name,
                base_lineages=base_lineages,
                expanded_lineages=expanded_lineages,
                relation_definitions_by_name=relation_definitions_by_name,
                expand=expand,
                visited_segments=visited_segments,
            )
        )
    return _dedupe_segments(segments)


def _segment_matches_output(
    segment: ProjectRowLineageSegment,
    output_name: str,
) -> bool:
    return (
        segment.kind is ProjectRowLineageSegmentKind.OUTPUT_FIELD
        and (segment.output_name or segment.name) == output_name
    )


def _segment_matches_let_binding(
    segment: ProjectRowLineageSegment,
    binding_name: str,
) -> bool:
    return (
        segment.kind is ProjectRowLineageSegmentKind.LET_BINDING
        and (segment.binding_name or segment.name) == binding_name
    )


def _dedupe_segments(
    segments: list[ProjectRowLineageSegment],
) -> tuple[ProjectRowLineageSegment, ...]:
    deduped: list[ProjectRowLineageSegment] = []
    seen: set[_LineageSegmentKey] = set()
    for segment in segments:
        key = _lineage_segment_key(segment)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(segment)
    return tuple(deduped)


def _is_lineage_edge_kind(kind: ProjectRowDependencyEdgeKind) -> bool:
    return kind in {
        ProjectRowDependencyEdgeKind.DIRECT_PROJECTION,
        ProjectRowDependencyEdgeKind.RENAMED_PROJECTION,
        ProjectRowDependencyEdgeKind.COMPUTED_EXPRESSION,
        ProjectRowDependencyEdgeKind.LET_OUTPUT,
        ProjectRowDependencyEdgeKind.LET_EXPRESSION,
        ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT,
        ProjectRowDependencyEdgeKind.AGGREGATE_RELATION_INPUT,
    }


def _lineage_fact_key(fact: ProjectRowLineageFact) -> _LineageFactKey:
    return (
        fact.kind,
        _lineage_segment_key(fact.output_segment),
        _lineage_segment_key(fact.upstream_segment),
    )


def _lineage_segment_key(segment: ProjectRowLineageSegment) -> _LineageSegmentKey:
    return (
        segment.kind,
        segment.name,
        segment.relation_name,
        segment.source_name,
        segment.field_name,
        segment.output_name,
        segment.binding_name,
    )


type _LineageSegmentKey = tuple[
    ProjectRowLineageSegmentKind,
    str,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
]
type _LineageFactKey = tuple[
    ProjectRowLineageFactKind,
    _LineageSegmentKey,
    _LineageSegmentKey,
]
type _LineageExpander = Callable[[_DerivedRelation], ProjectRelationRowLineage]


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
