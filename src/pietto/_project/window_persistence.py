"""Private all-or-none persistence for validated window result outputs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
)
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
)
from pietto._project.row_dependency_graph import (
    ProjectRelationRowDependencyGraph,
    ProjectRowDependencyEdge,
    ProjectRowDependencyEdgeKind,
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
)
from pietto._project.row_lineage import (
    ProjectRelationRowLineage,
    ProjectRowLineageReason,
    ProjectRowLineageStatus,
    build_project_relation_row_lineage,
)
from pietto._project.window_semantics import (
    WindowDependencyEdge,
    WindowDependencyOccurrence,
    WindowDependencyRole,
    WindowResultProjectFact,
    build_window_result_project_fact,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    TableDef,
    WindowExpr,
)
from pietto.semantic.model import EffectiveNullability, TypeKind, ValueTypeKind
from pietto.semantic.window_semantics import (
    WindowExpressionUnsupported,
    WindowResultAvailabilityKind,
)

__all__: tuple[str, ...] = ()

_DerivedRelation = TableDef | QueryDef

_WINDOW_EDGE_KINDS = {
    WindowDependencyRole.RELATION_INPUT: (
        ProjectRowDependencyEdgeKind.WINDOW_RELATION_INPUT
    ),
    WindowDependencyRole.WINDOW_ARGUMENT: ProjectRowDependencyEdgeKind.WINDOW_ARGUMENT,
    WindowDependencyRole.WINDOW_DEFAULT: ProjectRowDependencyEdgeKind.WINDOW_DEFAULT,
    WindowDependencyRole.WINDOW_PARTITION: (
        ProjectRowDependencyEdgeKind.WINDOW_PARTITION
    ),
    WindowDependencyRole.WINDOW_ORDER: ProjectRowDependencyEdgeKind.WINDOW_ORDER,
}


@dataclass(frozen=True, slots=True)
class ProjectWindowPersistenceBundle:
    """One validated final project row bundle after the WINDOW-stage overlay."""

    definition: _DerivedRelation
    state: ProjectRelationRowSchemaState
    aggregate_result_facts: Mapping[str, ProjectAggregateResultFact]
    window_result_facts: Mapping[str, WindowResultProjectFact]
    dependency_graph: ProjectRelationRowDependencyGraph
    lineage: ProjectRelationRowLineage

    def __post_init__(self) -> None:
        if type(self.definition) not in {TableDef, QueryDef}:
            raise TypeError("window persistence requires an exact relation")
        if type(self.state) is not ProjectRelationRowSchemaState:
            raise TypeError("window persistence requires an exact row state")
        if type(self.dependency_graph) is not ProjectRelationRowDependencyGraph:
            raise TypeError("window persistence requires an exact dependency graph")
        if type(self.lineage) is not ProjectRelationRowLineage:
            raise TypeError("window persistence requires an exact lineage")

        aggregate_result_facts = MappingProxyType(dict(self.aggregate_result_facts))
        window_result_facts = MappingProxyType(dict(self.window_result_facts))
        object.__setattr__(self, "aggregate_result_facts", aggregate_result_facts)
        object.__setattr__(self, "window_result_facts", window_result_facts)

        if (
            self.dependency_graph.status.value != self.state.status.value
            or self.dependency_graph.reason.value != self.state.reason.value
            or self.lineage.status.value != self.state.status.value
            or self.lineage.reason.value != self.state.reason.value
        ):
            raise ValueError("window persistence state, graph, and lineage must agree")

        if self.state.status is ProjectRelationRowSchemaStatus.CONCRETE:
            schema = self.state.schema
            if schema is None or schema.is_unknown:
                raise ValueError("concrete window persistence requires a schema")
            _validate_concrete_fact_mapping(
                definition=self.definition,
                schema=schema,
                window_result_facts=window_result_facts,
            )
            return

        if aggregate_result_facts or window_result_facts:
            raise ValueError("non-concrete window persistence forbids result facts")
        if self.dependency_graph.nodes or self.dependency_graph.edges:
            raise ValueError("non-concrete window persistence forbids graph facts")
        if self.lineage.facts:
            raise ValueError("non-concrete window persistence forbids lineage facts")
        if self.state.status is ProjectRelationRowSchemaStatus.UNKNOWN:
            schema = self.state.schema
            if schema is None or schema.fields or not schema.is_unknown:
                raise ValueError("unknown window persistence requires empty schema")
        elif self.state.schema is not None:
            raise ValueError("deferred or blocked window persistence forbids schema")


def build_project_window_persistence(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    upstream_lineage: ProjectRelationRowLineage | None,
    fallback_path: str,
    let_scope_facts: ProjectRelationLetScopeFacts,
    base_state: ProjectRelationRowSchemaState,
    base_aggregate_result_facts: Mapping[str, ProjectAggregateResultFact],
    base_dependency_graph: ProjectRelationRowDependencyGraph,
    base_lineage: ProjectRelationRowLineage,
) -> ProjectWindowPersistenceBundle:
    """Overlay every selected window result or publish one atomic failure."""

    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("definition must be an exact TableDef or QueryDef")
    if type(input_schema) is not ProjectRowSchema or input_schema.is_unknown:
        raise ValueError("window persistence requires a concrete input schema")
    if type(upstream_symbol) is not ProjectSymbol:
        raise TypeError("upstream_symbol must be an exact ProjectSymbol")
    if type(let_scope_facts) is not ProjectRelationLetScopeFacts:
        raise TypeError("let_scope_facts must be exact project let facts")
    if type(base_state) is not ProjectRelationRowSchemaState:
        raise TypeError("base_state must be an exact row state")
    if type(base_dependency_graph) is not ProjectRelationRowDependencyGraph:
        raise TypeError("base dependency graph must be exact")
    if type(base_lineage) is not ProjectRelationRowLineage:
        raise TypeError("base lineage must be exact")

    window_items = tuple(
        (ordinal, item)
        for ordinal, item in enumerate(definition.select_items)
        if type(item.expression) is WindowExpr
    )
    if not window_items:
        return ProjectWindowPersistenceBundle(
            definition=definition,
            state=base_state,
            aggregate_result_facts=base_aggregate_result_facts,
            window_result_facts={},
            dependency_graph=base_dependency_graph,
            lineage=base_lineage,
        )

    if base_state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        return ProjectWindowPersistenceBundle(
            definition=definition,
            state=base_state,
            aggregate_result_facts={},
            window_result_facts={},
            dependency_graph=base_dependency_graph,
            lineage=base_lineage,
        )
    if (
        base_dependency_graph.status is not ProjectRowDependencyGraphStatus.CONCRETE
        or base_lineage.status is not ProjectRowLineageStatus.CONCRETE
        or base_dependency_graph.reason.value != base_state.reason.value
        or base_lineage.reason.value != base_state.reason.value
    ):
        return _failed_bundle(
            definition,
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            reason=ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
        )

    base_schema = base_state.schema
    if base_schema is None or base_schema.is_unknown:
        return _failed_bundle(
            definition,
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            reason=ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
        )
    if _has_window_output_collision(definition):
        return _failed_bundle(
            definition,
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            reason=ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        )
    if not _base_schema_matches_definition(definition, base_schema):
        return _failed_bundle(
            definition,
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            reason=ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
        )

    let_value_types = (
        let_scope_facts.value_types
        if let_scope_facts.status is ProjectLetScopeFactsStatus.CONCRETE
        else None
    )
    let_expressions = (
        let_scope_facts.binding_expressions
        if let_scope_facts.status is ProjectLetScopeFactsStatus.CONCRETE
        else None
    )
    facts: dict[str, WindowResultProjectFact] = {}
    for selected_output_ordinal, item in window_items:
        source_id = item.expression.span.path or fallback_path
        result = build_window_result_project_fact(
            definition=definition,
            item=item,
            selected_output_ordinal=selected_output_ordinal,
            source_id=source_id,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            let_value_types=let_value_types,
            let_expressions=let_expressions,
        )
        if result is None:
            return _failed_bundle(
                definition,
                status=ProjectRelationRowSchemaStatus.UNKNOWN,
                reason=ProjectRelationRowSchemaReason.UNAVAILABLE_WINDOW_RESULT_FACT,
            )
        if isinstance(result, WindowExpressionUnsupported):
            return _failed_bundle(
                definition,
                status=ProjectRelationRowSchemaStatus.UNKNOWN,
                reason=ProjectRelationRowSchemaReason.INVALID_WINDOW_OUTPUT,
            )
        if type(result) is not WindowResultProjectFact:
            return _failed_bundle(
                definition,
                status=ProjectRelationRowSchemaStatus.BLOCKED,
                reason=ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
            )

        availability = result.semantic_fact.result
        if availability.kind is WindowResultAvailabilityKind.UNKNOWN:
            return _failed_bundle(
                definition,
                status=ProjectRelationRowSchemaStatus.UNKNOWN,
                reason=ProjectRelationRowSchemaReason.UNAVAILABLE_WINDOW_RESULT_FACT,
            )
        if availability.kind is WindowResultAvailabilityKind.DEFERRED:
            return _failed_bundle(
                definition,
                status=ProjectRelationRowSchemaStatus.DEFERRED,
                reason=ProjectRelationRowSchemaReason.WINDOW_RESULT_DEFERRED,
            )
        if availability.kind is WindowResultAvailabilityKind.BLOCKED:
            return _failed_bundle(
                definition,
                status=ProjectRelationRowSchemaStatus.BLOCKED,
                reason=ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
            )
        if not _window_fact_matches_source(
            fact=result,
            definition=definition,
            item=item,
            selected_output_ordinal=selected_output_ordinal,
            source_id=source_id,
            input_schema=input_schema,
            base_schema=base_schema,
            upstream_symbol=upstream_symbol,
            let_scope_facts=let_scope_facts,
        ):
            return _failed_bundle(
                definition,
                status=ProjectRelationRowSchemaStatus.BLOCKED,
                reason=ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
            )

        output_name = result.result_identity.output_name
        if output_name in facts:
            return _failed_bundle(
                definition,
                status=ProjectRelationRowSchemaStatus.BLOCKED,
                reason=ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
            )
        facts[output_name] = result

    final_schema = _final_schema(
        definition=definition,
        base_schema=base_schema,
        window_result_facts=facts,
    )
    state = ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=final_schema,
        reason=base_state.reason,
    )
    graph = _overlay_dependency_graph(
        definition=definition,
        base_graph=base_dependency_graph,
        window_result_facts=facts,
        reason=base_state.reason,
    )
    lineage = build_project_relation_row_lineage(
        definition=definition,
        upstream_symbol=upstream_symbol,
        row_schema=final_schema,
        state=state,
        dependency_graph=graph,
        upstream_lineage=upstream_lineage,
    )
    return ProjectWindowPersistenceBundle(
        definition=definition,
        state=state,
        aggregate_result_facts=base_aggregate_result_facts,
        window_result_facts=facts,
        dependency_graph=graph,
        lineage=lineage,
    )


def _window_fact_matches_source(
    *,
    fact: WindowResultProjectFact,
    definition: _DerivedRelation,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: ProjectRowSchema,
    base_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_scope_facts: ProjectRelationLetScopeFacts,
) -> bool:
    identity = fact.result_identity
    occurrence = identity.occurrence
    semantic_fact = fact.semantic_fact
    if (
        item.alias is None
        or identity.definition is not definition
        or identity.output_name != item.alias
        or identity.role is not ProjectRowResultRole.WINDOW_RESULT
        or semantic_fact.expression is not item.expression
        or semantic_fact.occurrence != occurrence
        or occurrence.source_id != source_id
        or occurrence.relation_name != definition.name
        or occurrence.selected_output_ordinal != selected_output_ordinal
        or occurrence.span != item.expression.span
    ):
        return False
    availability = semantic_fact.result
    value_type = availability.value_type
    if (
        availability.kind is not WindowResultAvailabilityKind.CONCRETE
        or value_type is None
        or value_type.kind is not ValueTypeKind.KNOWN
        or value_type.resolved_type.kind is not TypeKind.BUILTIN
        or value_type.nullability
        not in {
            EffectiveNullability.NON_NULL,
            EffectiveNullability.NULLABLE,
        }
    ):
        return False
    if fact.provenance.symbol is not upstream_symbol:
        return False
    return all(
        _window_dependency_matches_base(
            occurrence=dependency,
            definition=definition,
            input_schema=input_schema,
            base_schema=base_schema,
            upstream_symbol=upstream_symbol,
            let_scope_facts=let_scope_facts,
        )
        for dependency in fact.dependency_occurrences
    )


def _window_dependency_matches_base(
    *,
    occurrence: WindowDependencyOccurrence,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    base_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_scope_facts: ProjectRelationLetScopeFacts,
) -> bool:
    target = occurrence.target
    if target.kind is ProjectRowDependencyNodeKind.RELATION_INPUT:
        return (
            occurrence.target_result_role is None
            and target.name == upstream_symbol.name
            and target.relation_name == upstream_symbol.name
            and target.source_name == upstream_symbol.name
        )
    if target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD:
        return (
            occurrence.target_result_role is None
            and target.field_name is not None
            and target.field_name in input_schema.fields
            and target.name == f"{upstream_symbol.name}.{target.field_name}"
            and target.relation_name == upstream_symbol.name
            and target.source_name == upstream_symbol.name
        )
    if target.kind is ProjectRowDependencyNodeKind.LET_BINDING:
        return (
            occurrence.target_result_role is None
            and let_scope_facts.status is ProjectLetScopeFactsStatus.CONCRETE
            and target.binding_name is not None
            and target.binding_name in let_scope_facts.value_types
            and target.name == target.binding_name
            and target.relation_name == definition.name
        )
    if target.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
        output_name = target.output_name or target.name
        field = base_schema.fields.get(output_name)
        return (
            field is not None
            and target.relation_name == definition.name
            and occurrence.target_result_role
            in {
                ProjectRowResultRole.GROUP_KEY,
                ProjectRowResultRole.AGGREGATE_RESULT,
            }
            and field.result_role is occurrence.target_result_role
        )
    return False


def _final_schema(
    *,
    definition: _DerivedRelation,
    base_schema: ProjectRowSchema,
    window_result_facts: Mapping[str, WindowResultProjectFact],
) -> ProjectRowSchema:
    fields: dict[str, ProjectRowField] = {}
    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is None:
            raise ValueError("concrete window persistence requires named outputs")
        if type(item.expression) is not WindowExpr:
            field = base_schema.fields.get(output_name)
            if field is None:
                raise ValueError("base window persistence schema is incomplete")
            fields[output_name] = field
            continue

        fact = window_result_facts.get(output_name)
        if fact is None:
            raise ValueError("window persistence requires every selected fact")
        value_type = fact.semantic_fact.result.value_type
        if value_type is None:
            raise ValueError("concrete window persistence requires a value type")
        fields[output_name] = ProjectRowField(
            name=output_name,
            resolved_type=ProjectResolvedType(
                name=value_type.resolved_type.name,
                kind=ProjectResolvedTypeKind.BUILTIN,
            ),
            nullability=(
                ProjectRowFieldNullability.NON_NULL
                if value_type.nullability is EffectiveNullability.NON_NULL
                else ProjectRowFieldNullability.NULLABLE
            ),
            field_def=None,
            provenance=fact.provenance,
            result_role=ProjectRowResultRole.WINDOW_RESULT,
        )
    return ProjectRowSchema(fields=fields)


def _overlay_dependency_graph(
    *,
    definition: _DerivedRelation,
    base_graph: ProjectRelationRowDependencyGraph,
    window_result_facts: Mapping[str, WindowResultProjectFact],
    reason: ProjectRelationRowSchemaReason,
) -> ProjectRelationRowDependencyGraph:
    base_output_edges: dict[str, list[ProjectRowDependencyEdge]] = {}
    base_non_output_edges: list[ProjectRowDependencyEdge] = []
    base_output_nodes: dict[str, ProjectRowDependencyNode] = {}
    for node in base_graph.nodes:
        if node.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
            base_output_nodes[node.output_name or node.name] = node
    for edge in base_graph.edges:
        if edge.from_node.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
            output_name = edge.from_node.output_name or edge.from_node.name
            base_output_edges.setdefault(output_name, []).append(edge)
        else:
            base_non_output_edges.append(edge)

    nodes: list[ProjectRowDependencyNode] = []
    edges: list[ProjectRowDependencyEdge] = []

    def add_node(node: ProjectRowDependencyNode) -> None:
        if node not in nodes:
            nodes.append(node)

    def add_edge(edge: ProjectRowDependencyEdge) -> None:
        add_node(edge.from_node)
        add_node(edge.to_node)
        if edge not in edges:
            edges.append(edge)

    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is None:
            raise ValueError("concrete window graph requires named outputs")
        if type(item.expression) is not WindowExpr:
            output_node = base_output_nodes.get(output_name)
            if output_node is None:
                raise ValueError("base graph is missing one output node")
            add_node(output_node)
            for edge in base_output_edges.get(output_name, ()):
                add_edge(edge)
            continue

        fact = window_result_facts[output_name]
        output_node = ProjectRowDependencyNode(
            kind=ProjectRowDependencyNodeKind.OUTPUT_FIELD,
            name=output_name,
            relation_name=definition.name,
            output_name=output_name,
        )
        add_node(output_node)
        for dependency in fact.dependency_edges:
            occurrence = _first_dependency_occurrence(fact, dependency)
            add_edge(
                ProjectRowDependencyEdge(
                    kind=_WINDOW_EDGE_KINDS[dependency.role],
                    from_node=output_node,
                    to_node=dependency.target,
                    location=occurrence.location,
                )
            )

    for edge in base_non_output_edges:
        add_edge(edge)
    for node in base_graph.nodes:
        add_node(node)
    return ProjectRelationRowDependencyGraph(
        status=ProjectRowDependencyGraphStatus.CONCRETE,
        reason=ProjectRowDependencyGraphReason(reason.value),
        nodes=tuple(nodes),
        edges=tuple(edges),
    )


def _first_dependency_occurrence(
    fact: WindowResultProjectFact,
    edge: WindowDependencyEdge,
) -> WindowDependencyOccurrence:
    return next(
        occurrence
        for occurrence in fact.dependency_occurrences
        if occurrence.role is edge.role
        and occurrence.target == edge.target
        and occurrence.target_result_role is edge.target_result_role
    )


def _failed_bundle(
    definition: _DerivedRelation,
    *,
    status: ProjectRelationRowSchemaStatus,
    reason: ProjectRelationRowSchemaReason,
) -> ProjectWindowPersistenceBundle:
    state = ProjectRelationRowSchemaState(
        status=status,
        schema=(
            ProjectRowSchema(is_unknown=True)
            if status is ProjectRelationRowSchemaStatus.UNKNOWN
            else None
        ),
        reason=reason,
    )
    return ProjectWindowPersistenceBundle(
        definition=definition,
        state=state,
        aggregate_result_facts={},
        window_result_facts={},
        dependency_graph=ProjectRelationRowDependencyGraph(
            status=ProjectRowDependencyGraphStatus(status.value),
            reason=ProjectRowDependencyGraphReason(reason.value),
        ),
        lineage=ProjectRelationRowLineage(
            status=ProjectRowLineageStatus(status.value),
            reason=ProjectRowLineageReason(reason.value),
        ),
    )


def _base_schema_matches_definition(
    definition: _DerivedRelation,
    base_schema: ProjectRowSchema,
) -> bool:
    expected = tuple(
        output_name
        for item in definition.select_items
        if type(item.expression) is not WindowExpr
        if (output_name := _projection_output_name(item)) is not None
    )
    return tuple(base_schema.fields) == expected and len(expected) == len(
        tuple(
            item
            for item in definition.select_items
            if type(item.expression) is not WindowExpr
        )
    )


def _has_window_output_collision(definition: _DerivedRelation) -> bool:
    output_names = tuple(
        _projection_output_name(item) for item in definition.select_items
    )
    counts = Counter(name for name in output_names if name is not None)
    return any(
        item.alias is not None and counts[item.alias] != 1
        for item in definition.select_items
        if type(item.expression) is WindowExpr
    )


def _projection_output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _validate_concrete_fact_mapping(
    *,
    definition: _DerivedRelation,
    schema: ProjectRowSchema,
    window_result_facts: Mapping[str, WindowResultProjectFact],
) -> None:
    for output_name, fact in window_result_facts.items():
        if type(fact) is not WindowResultProjectFact:
            raise TypeError("window result mapping requires exact facts")
        if (
            fact.result_identity.definition is not definition
            or fact.result_identity.output_name != output_name
        ):
            raise ValueError("window result mapping identity mismatch")
        field = schema.fields.get(output_name)
        if field is None or field.result_role is not ProjectRowResultRole.WINDOW_RESULT:
            raise ValueError("window result mapping requires schema field")
    for output_name, field in schema.fields.items():
        has_fact = output_name in window_result_facts
        if field.result_role is ProjectRowResultRole.WINDOW_RESULT:
            if not has_fact:
                raise ValueError("WINDOW_RESULT field requires one project fact")
        elif has_fact:
            raise ValueError("non-window field forbids a window result fact")
