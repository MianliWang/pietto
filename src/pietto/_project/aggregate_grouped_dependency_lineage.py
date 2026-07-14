"""Private aggregate/grouped dependency and lineage readiness."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Never

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectAggregateGroupedClauseReadinessReason,
    ProjectAggregateGroupedClauseReadinessStatus,
    ProjectRelationClauseDependencyKind,
    build_project_aggregate_grouped_clause_readiness,
)
from pietto._project.aggregate_grouped_schema import ProjectGroupKeyFact
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsReason,
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
    build_project_relation_let_scope_facts,
)
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectRelationRowSchemaStatus,
    ProjectRowField,
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
)
from pietto._project.row_dependency_graph import (
    ProjectRelationRowDependencyGraph,
    ProjectRowDependencyEdge,
    ProjectRowDependencyEdgeKind,
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
    _GraphBuilder,
    _add_let_expression_edges,
    _expression_location,
    _let_binding_node,
    _output_node,
    _upstream_field_node,
)
from pietto._project.row_lineage import (
    ProjectRelationRowLineage,
    ProjectRowLineageFactKind,
    ProjectRowLineageReason,
    ProjectRowLineageSegmentKind,
    ProjectRowLineageStatus,
    _expand_relation_row_lineages,
    _is_lineage_edge_kind,
    _lineage_fact_from_edge,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    SourceDef,
    TableDef,
)
from pietto.errors import SourceLocation
from pietto.semantic.aggregates import (
    COUNT_AGGREGATE_NAME,
    aggregate_argument_can_use_let_scope,
    child_expressions,
    effective_semantic_aggregate_argument_expression,
    semantic_aggregate_call_name,
)

__all__: tuple[str, ...] = ()

_DerivedRelation = TableDef | QueryDef


@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedDependencyLineageReadiness:
    """Atomic helper-only dependency and lineage over one Slice 8 result."""

    definition: TableDef | QueryDef
    clause_readiness: ProjectAggregateGroupedClauseReadiness
    dependency_graph: ProjectRelationRowDependencyGraph
    lineage: ProjectRelationRowLineage

    def __post_init__(self) -> None:
        """Validate nested identity, atomicity, and complete output coverage."""

        if not isinstance(self.definition, (TableDef, QueryDef)):
            raise ValueError("Dependency-lineage readiness requires a relation")
        if not isinstance(
            self.clause_readiness,
            ProjectAggregateGroupedClauseReadiness,
        ):
            raise ValueError("Dependency-lineage readiness requires clause readiness")
        if self.clause_readiness.definition is not self.definition:
            raise ValueError("Dependency-lineage definition identity mismatch")
        if not isinstance(
            self.dependency_graph,
            ProjectRelationRowDependencyGraph,
        ):
            raise ValueError("Dependency-lineage readiness requires a graph")
        if not isinstance(self.lineage, ProjectRelationRowLineage):
            raise ValueError("Dependency-lineage readiness requires lineage")
        if (
            self.dependency_graph.status.value != self.lineage.status.value
            or self.dependency_graph.reason.value != self.lineage.reason.value
        ):
            raise ValueError("Dependency graph and lineage outcome mismatch")

        graph = self.dependency_graph
        lineage = self.lineage
        if graph.status is not ProjectRowDependencyGraphStatus.CONCRETE:
            if graph.nodes or graph.edges or lineage.facts:
                raise ValueError("Non-concrete dependency-lineage must be empty")
            _validate_non_concrete_outcome(self.clause_readiness, graph)
            return

        if lineage.status is not ProjectRowLineageStatus.CONCRETE:
            raise ValueError("Concrete graph requires concrete lineage")
        if (
            self.clause_readiness.status
            is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
        ):
            raise ValueError("Concrete dependency-lineage requires ready clauses")

        finalization = self.clause_readiness.finalization
        if (
            finalization.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or finalization.state.schema is None
        ):
            raise ValueError("Concrete dependency-lineage requires finalized schema")
        if graph.reason.value != finalization.state.reason.value:
            raise ValueError("Concrete dependency-lineage reason mismatch")

        upstream_symbol = _schema_upstream_symbol(finalization.state.schema)
        _validate_graph_shape(
            self.definition,
            finalization.state.schema,
            finalization.aggregate_result_facts,
            upstream_symbol,
            graph,
        )
        _validate_lineage_shape(
            self.definition,
            upstream_symbol,
            graph,
            lineage,
        )


@dataclass(frozen=True, slots=True)
class _SelectedOutput:
    item: SelectItem
    field: ProjectRowField
    aggregate_fact: ProjectAggregateResultFact | None


class _ClassifiedFailure(Exception):
    """One expected atomic helper-local failure."""

    def __init__(
        self,
        status: ProjectRowDependencyGraphStatus,
        reason: ProjectRowDependencyGraphReason,
    ) -> None:
        super().__init__(status.value, reason.value)
        self.status = status
        self.reason = reason


def build_project_aggregate_grouped_dependency_lineage_readiness(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    upstream_lineage: ProjectRelationRowLineage | None,
    fallback_path: str,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> ProjectAggregateGroupedDependencyLineageReadiness:
    """Build one atomic helper-only dependency and lineage readiness result."""

    clause_readiness = build_project_aggregate_grouped_clause_readiness(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path=fallback_path,
        let_scope_facts=let_scope_facts,
    )
    if (
        clause_readiness.status
        is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    ):
        status, reason = _mapped_readiness_failure(clause_readiness)
        return _failed_readiness(
            definition=definition,
            clause_readiness=clause_readiness,
            status=status,
            reason=reason,
        )

    try:
        dependency_graph = _build_dependency_graph(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path=fallback_path,
            clause_readiness=clause_readiness,
            let_scope_facts=let_scope_facts,
        )
        lineage = _build_lineage(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            upstream_lineage=upstream_lineage,
            dependency_graph=dependency_graph,
        )
    except _ClassifiedFailure as failure:
        return _failed_readiness(
            definition=definition,
            clause_readiness=clause_readiness,
            status=failure.status,
            reason=failure.reason,
        )

    return ProjectAggregateGroupedDependencyLineageReadiness(
        definition=definition,
        clause_readiness=clause_readiness,
        dependency_graph=dependency_graph,
        lineage=lineage,
    )


def _build_dependency_graph(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
    clause_readiness: ProjectAggregateGroupedClauseReadiness,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> ProjectRelationRowDependencyGraph:
    finalization = clause_readiness.finalization
    schema = finalization.state.schema
    if schema is None or schema.is_unknown:
        _conflicting_failure()
    assert schema is not None

    _validate_uniform_upstream_symbol(schema, upstream_symbol)
    selected_outputs = _selected_outputs(
        definition,
        schema,
        finalization.aggregate_result_facts,
    )
    group_keys = _retained_group_keys(clause_readiness, input_schema)
    let_facts = _let_scope_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        let_scope_facts=let_scope_facts,
    )

    builder = _GraphBuilder()
    for selected in selected_outputs:
        output_node = _output_node(definition, selected.field.name)
        builder.add_node(output_node)
        if selected.field.result_role is ProjectRowResultRole.GROUP_KEY:
            _add_group_key_edge(
                builder,
                definition=definition,
                selected=selected,
                input_schema=input_schema,
                upstream_symbol=upstream_symbol,
                group_keys=group_keys,
                fallback_path=fallback_path,
            )
            continue
        if selected.field.result_role is not ProjectRowResultRole.AGGREGATE_RESULT:
            _conflicting_failure()
        _add_aggregate_edges(
            builder,
            definition=definition,
            selected=selected,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            let_facts=let_facts,
            fallback_path=fallback_path,
        )

    _add_let_expression_edges(
        builder,
        definition,
        fallback_path=fallback_path,
        upstream_symbol=upstream_symbol,
        input_schema=input_schema,
        let_facts=let_facts,
    )
    return ProjectRelationRowDependencyGraph(
        status=ProjectRowDependencyGraphStatus.CONCRETE,
        reason=ProjectRowDependencyGraphReason(finalization.state.reason.value),
        nodes=tuple(builder.nodes),
        edges=tuple(builder.edges),
    )


def _selected_outputs(
    definition: _DerivedRelation,
    schema: ProjectRowSchema,
    aggregate_result_facts: Mapping[str, ProjectAggregateResultFact],
) -> tuple[_SelectedOutput, ...]:
    if len(definition.select_items) != len(schema.fields):
        _conflicting_failure()

    outputs: list[_SelectedOutput] = []
    for item, (output_name, field) in zip(
        definition.select_items,
        schema.fields.items(),
        strict=True,
    ):
        if _projection_output_name(item) != output_name or field.name != output_name:
            _conflicting_failure()
        aggregate_fact = aggregate_result_facts.get(output_name)
        if field.result_role is ProjectRowResultRole.GROUP_KEY:
            if aggregate_fact is not None:
                _conflicting_failure()
        elif field.result_role is ProjectRowResultRole.AGGREGATE_RESULT:
            if not isinstance(aggregate_fact, ProjectAggregateResultFact):
                _conflicting_failure()
        else:
            _conflicting_failure()
        outputs.append(
            _SelectedOutput(
                item=item,
                field=field,
                aggregate_fact=aggregate_fact,
            )
        )
    return tuple(outputs)


def _retained_group_keys(
    clause_readiness: ProjectAggregateGroupedClauseReadiness,
    input_schema: ProjectRowSchema,
) -> tuple[ProjectGroupKeyFact, ...]:
    group_keys: list[ProjectGroupKeyFact] = []
    for dependency in clause_readiness.dependency_facts:
        if dependency.kind is not ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT:
            continue
        fact = dependency.target_occurrence
        if (
            not isinstance(fact, ProjectGroupKeyFact)
            or dependency.source_occurrence is not fact.item
            or dependency.target_field is not fact.input_field
            or input_schema.fields.get(fact.field_identity) is not fact.input_field
        ):
            _conflicting_failure()
        group_keys.append(fact)
    return tuple(group_keys)


def _let_scope_facts(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> ProjectRelationLetScopeFacts:
    upstream_definition = upstream_symbol.definition
    if not isinstance(upstream_definition, (SourceDef, TableDef, QueryDef)):
        _conflicting_failure()
    facts = let_scope_facts
    if facts is None:
        facts = build_project_relation_let_scope_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_definition=upstream_definition,
        )
    elif definition.let_clause is None:
        if (
            facts.status is not ProjectLetScopeFactsStatus.ABSENT
            or facts.clause is not None
        ):
            _conflicting_failure()
    elif facts.clause is not definition.let_clause:
        _conflicting_failure()
    if facts.status in {
        ProjectLetScopeFactsStatus.ABSENT,
        ProjectLetScopeFactsStatus.CONCRETE,
    }:
        return facts
    if facts.status is ProjectLetScopeFactsStatus.BLOCKED:
        _conflicting_failure()
    if facts.reason is ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED:
        _invalid_failure()
    _unavailable_failure()


def _add_group_key_edge(
    builder: _GraphBuilder,
    *,
    definition: _DerivedRelation,
    selected: _SelectedOutput,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    group_keys: tuple[ProjectGroupKeyFact, ...],
    fallback_path: str,
) -> None:
    lookup_name = _direct_lookup_name(
        selected.item.expression,
        relation_qualifier=definition.from_clause.source_name,
    )
    if lookup_name is None:
        _conflicting_failure()
    input_field = input_schema.fields.get(lookup_name)
    matching = tuple(
        fact
        for fact in group_keys
        if fact.field_identity == lookup_name and fact.input_field is input_field
    )
    if input_field is None or len(matching) != 1:
        _conflicting_failure()

    builder.add_edge(
        ProjectRowDependencyEdge(
            kind=(
                ProjectRowDependencyEdgeKind.DIRECT_PROJECTION
                if selected.field.name == lookup_name
                else ProjectRowDependencyEdgeKind.RENAMED_PROJECTION
            ),
            from_node=_output_node(definition, selected.field.name),
            to_node=_upstream_field_node(upstream_symbol, lookup_name),
            location=_expression_location(
                selected.item.expression,
                fallback_path=fallback_path,
            ),
        )
    )


def _add_aggregate_edges(
    builder: _GraphBuilder,
    *,
    definition: _DerivedRelation,
    selected: _SelectedOutput,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_facts: ProjectRelationLetScopeFacts,
    fallback_path: str,
) -> None:
    fact = selected.aggregate_fact
    call = selected.item.expression
    if not isinstance(fact, ProjectAggregateResultFact) or not isinstance(
        call,
        CallExpr,
    ):
        _conflicting_failure()
    function_name = semantic_aggregate_call_name(call)
    if function_name is None:
        _conflicting_failure()
    if (
        function_name != fact.function
        or selected.item.alias != fact.output_name
        or selected.field.name != fact.output_name
        or len(call.arguments) != fact.argument_count
        or fact.grouped is not (definition.group_by_clause is not None)
    ):
        _conflicting_failure()

    output_node = _output_node(definition, selected.field.name)
    if fact.argument_count == 0:
        if function_name != COUNT_AGGREGATE_NAME:
            _conflicting_failure()
        builder.add_edge(
            ProjectRowDependencyEdge(
                kind=ProjectRowDependencyEdgeKind.AGGREGATE_RELATION_INPUT,
                from_node=output_node,
                to_node=_relation_input_node(upstream_symbol),
                location=_expression_location(call, fallback_path=fallback_path),
            )
        )
        return
    if fact.argument_count != 1:
        _conflicting_failure()

    argument = call.arguments[0]
    expansions = (
        let_facts.binding_expressions
        if let_facts.status is ProjectLetScopeFactsStatus.CONCRETE
        else None
    )
    effective_argument = effective_semantic_aggregate_argument_expression(
        function_name,
        argument,
        let_expansions=expansions,
    )
    if aggregate_argument_can_use_let_scope(
        function_name,
        argument,
        expansions,
    ):
        if (
            not isinstance(argument, NameExpr)
            or argument.name not in let_facts.value_types
        ):
            _invalid_failure()
        builder.add_edge(
            ProjectRowDependencyEdge(
                kind=ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT,
                from_node=output_node,
                to_node=_let_binding_node(definition, argument.name),
                location=_expression_location(
                    argument,
                    fallback_path=fallback_path,
                ),
            )
        )
        return

    dependencies = _aggregate_field_dependencies(
        effective_argument,
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path=fallback_path,
    )
    if not dependencies:
        _invalid_failure()
    for dependency_node, location in dependencies:
        builder.add_edge(
            ProjectRowDependencyEdge(
                kind=ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT,
                from_node=output_node,
                to_node=dependency_node,
                location=location,
            )
        )


def _aggregate_field_dependencies(
    expression: Expression,
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> tuple[tuple[ProjectRowDependencyNode, SourceLocation], ...]:
    dependencies: list[tuple[ProjectRowDependencyNode, SourceLocation]] = []
    seen: set[tuple[int, str]] = set()

    def add(field_name: str, occurrence: Expression) -> None:
        key = (id(upstream_symbol), field_name)
        if key in seen:
            return
        seen.add(key)
        dependencies.append(
            (
                _upstream_field_node(upstream_symbol, field_name),
                _expression_location(occurrence, fallback_path=fallback_path),
            )
        )

    def visit(current: Expression) -> None:
        if isinstance(current, LiteralExpr):
            return
        if isinstance(current, NameExpr):
            if current.name not in input_schema.fields:
                _unavailable_failure()
            add(current.name, current)
            return
        if isinstance(current, DottedNameExpr):
            lookup_name = _direct_lookup_name(
                current,
                relation_qualifier=definition.from_clause.source_name,
            )
            if lookup_name is None:
                _invalid_failure()
            if lookup_name not in input_schema.fields:
                _unavailable_failure()
            add(lookup_name, current)
            return
        children = child_expressions(current)
        if not children:
            _invalid_failure()
        for child in children:
            visit(child)

    visit(expression)
    return tuple(dependencies)


def _build_lineage(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    upstream_lineage: ProjectRelationRowLineage | None,
    dependency_graph: ProjectRelationRowDependencyGraph,
) -> ProjectRelationRowLineage:
    base_lineage = ProjectRelationRowLineage(
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
    base_lineages: dict[_DerivedRelation, ProjectRelationRowLineage] = {
        definition: base_lineage
    }
    definitions_by_name: dict[str, _DerivedRelation] = {definition.name: definition}
    preexpanded_lineages: dict[_DerivedRelation, ProjectRelationRowLineage] = {}
    upstream_definition = upstream_symbol.definition
    if upstream_symbol.kind is ProjectSymbolKind.SOURCE and isinstance(
        upstream_definition,
        SourceDef,
    ):
        if upstream_lineage is not None:
            _conflicting_failure()
    elif upstream_symbol.kind in {
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    } and isinstance(upstream_definition, (TableDef, QueryDef)):
        if (
            upstream_lineage is None
            or upstream_lineage.status is not ProjectRowLineageStatus.CONCRETE
            or upstream_definition is definition
            or upstream_definition.name in definitions_by_name
            or not _lineage_belongs_to(
                upstream_lineage,
                upstream_definition,
                input_schema,
            )
        ):
            _conflicting_failure()
        base_lineages[upstream_definition] = upstream_lineage
        definitions_by_name[upstream_definition.name] = upstream_definition
        preexpanded_lineages[upstream_definition] = upstream_lineage
    else:
        _conflicting_failure()

    expanded = _expand_relation_row_lineages(
        base_lineages,
        relation_definitions_by_name=definitions_by_name,
        preexpanded_lineages=preexpanded_lineages,
    )
    lineage = expanded.get(definition)
    if lineage is None:
        _conflicting_failure()
    return lineage


def _lineage_belongs_to(
    lineage: ProjectRelationRowLineage,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
) -> bool:
    binding_names = {
        binding.name
        for binding in (
            () if definition.let_clause is None else definition.let_clause.bindings
        )
    }
    if any(
        (
            fact.output_segment.kind is ProjectRowLineageSegmentKind.OUTPUT_FIELD
            and (
                fact.output_segment.relation_name != definition.name
                or (fact.output_segment.output_name or fact.output_segment.name)
                not in input_schema.fields
            )
        )
        or (
            fact.output_segment.kind is ProjectRowLineageSegmentKind.LET_BINDING
            and (
                fact.output_segment.relation_name != definition.name
                or (fact.output_segment.binding_name or fact.output_segment.name)
                not in binding_names
            )
        )
        or fact.output_segment.kind
        not in {
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            ProjectRowLineageSegmentKind.LET_BINDING,
        }
        for fact in lineage.facts
    ):
        return False
    output_segments = tuple(
        fact.output_segment
        for fact in lineage.facts
        if fact.output_segment.kind is ProjectRowLineageSegmentKind.OUTPUT_FIELD
    )
    output_names = {segment.output_name or segment.name for segment in output_segments}
    return lineage.reason in {
        ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE,
        ProjectRowLineageReason.TABLE_UPSTREAM_CONCRETE,
        ProjectRowLineageReason.RELATION_UPSTREAM_CONCRETE,
    } and output_names <= set(input_schema.fields)


def _validate_uniform_upstream_symbol(
    schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
) -> None:
    for field in schema.fields.values():
        provenance = field.provenance
        if (
            not isinstance(provenance, ProjectRowFieldProvenance)
            or provenance.symbol is not upstream_symbol
        ):
            _conflicting_failure()


def _schema_upstream_symbol(schema: ProjectRowSchema) -> ProjectSymbol:
    upstream_symbol: ProjectSymbol | None = None
    for field in schema.fields.values():
        provenance = field.provenance
        if (
            not isinstance(provenance, ProjectRowFieldProvenance)
            or provenance.symbol is None
        ):
            raise ValueError("Finalized output requires exact upstream provenance")
        if upstream_symbol is None:
            upstream_symbol = provenance.symbol
        elif provenance.symbol is not upstream_symbol:
            raise ValueError("Finalized output provenance symbols must agree")
    if upstream_symbol is None:
        raise ValueError("Finalized output schema cannot be empty")
    return upstream_symbol


def _validate_non_concrete_outcome(
    clause_readiness: ProjectAggregateGroupedClauseReadiness,
    graph: ProjectRelationRowDependencyGraph,
) -> None:
    if clause_readiness.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE:
        if (
            graph.status is ProjectRowDependencyGraphStatus.UNKNOWN
            and graph.reason
            in {
                ProjectRowDependencyGraphReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
                ProjectRowDependencyGraphReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
            }
        ) or (
            graph.status is ProjectRowDependencyGraphStatus.BLOCKED
            and graph.reason
            is ProjectRowDependencyGraphReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
        ):
            return
        raise ValueError("Concrete clauses have invalid helper-local failure")

    expected_status, expected_reason = _mapped_readiness_failure(clause_readiness)
    if graph.status is not expected_status or graph.reason is not expected_reason:
        raise ValueError("Non-concrete readiness mapping mismatch")


def _validate_graph_shape(
    definition: _DerivedRelation,
    schema: ProjectRowSchema,
    aggregate_result_facts: Mapping[str, ProjectAggregateResultFact],
    upstream_symbol: ProjectSymbol,
    graph: ProjectRelationRowDependencyGraph,
) -> None:
    if len(set(graph.nodes)) != len(graph.nodes) or len(set(graph.edges)) != len(
        graph.edges
    ):
        raise ValueError("Concrete dependency graph requires unique facts")
    if any(
        edge.from_node not in graph.nodes or edge.to_node not in graph.nodes
        for edge in graph.edges
    ):
        raise ValueError("Concrete dependency graph has foreign edge endpoint")
    edge_nodes = {
        node for edge in graph.edges for node in (edge.from_node, edge.to_node)
    }
    if any(
        node.kind is not ProjectRowDependencyNodeKind.LET_BINDING
        for node in set(graph.nodes) - edge_nodes
    ):
        raise ValueError("Concrete dependency graph forbids orphan non-let nodes")

    output_nodes = tuple(
        node
        for node in graph.nodes
        if node.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD
    )
    if output_nodes != tuple(
        _output_node(definition, output_name) for output_name in schema.fields
    ):
        raise ValueError("Concrete dependency graph output order mismatch")

    output_order = {name: index for index, name in enumerate(schema.fields)}
    binding_order = {
        binding.name: index
        for index, binding in enumerate(
            () if definition.let_clause is None else definition.let_clause.bindings
        )
    }
    for node in graph.nodes:
        if node.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
            if node not in output_nodes:
                raise ValueError("Concrete dependency graph has foreign output node")
        elif node.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD:
            if node.field_name is None or node != _upstream_field_node(
                upstream_symbol, node.field_name
            ):
                raise ValueError("Concrete dependency graph has invalid field node")
        elif node.kind is ProjectRowDependencyNodeKind.LET_BINDING:
            if node.name not in binding_order or node != _let_binding_node(
                definition, node.name
            ):
                raise ValueError("Concrete dependency graph has invalid let node")
        elif node.kind is ProjectRowDependencyNodeKind.RELATION_INPUT:
            if node != _relation_input_node(upstream_symbol):
                raise ValueError("Concrete dependency graph has invalid relation node")
        else:
            raise ValueError("Concrete dependency graph has unsupported node kind")

    last_output_index = -1
    last_binding_index = -1
    reached_let_edges = False
    for edge in graph.edges:
        if edge.from_node.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
            if reached_let_edges:
                raise ValueError("Output dependencies must precede let ancestry")
            output_name = edge.from_node.output_name or edge.from_node.name
            output_index = output_order.get(output_name)
            if output_index is None or output_index < last_output_index:
                raise ValueError("Output dependency order mismatch")
            last_output_index = output_index
            continue
        reached_let_edges = True
        binding_index = binding_order.get(edge.from_node.name)
        if binding_index is None or binding_index < last_binding_index:
            raise ValueError("Let dependency order mismatch")
        last_binding_index = binding_index

    selected_items = dict(zip(schema.fields, definition.select_items, strict=True))
    for output_name, field in schema.fields.items():
        outgoing = tuple(
            edge
            for edge in graph.edges
            if edge.from_node.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD
            and (edge.from_node.output_name or edge.from_node.name) == output_name
        )
        if field.result_role is ProjectRowResultRole.GROUP_KEY:
            provenance = field.provenance
            selected_item = selected_items[output_name]
            lookup_name = _direct_lookup_name(
                selected_item.expression,
                relation_qualifier=definition.from_clause.source_name,
            )
            expected_kind = (
                ProjectRowDependencyEdgeKind.DIRECT_PROJECTION
                if output_name == lookup_name
                else ProjectRowDependencyEdgeKind.RENAMED_PROJECTION
            )
            if (
                not isinstance(provenance, ProjectRowFieldProvenance)
                or provenance.kind
                is not ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
                or lookup_name is None
                or len(outgoing) != 1
                or outgoing[0].kind is not expected_kind
                or outgoing[0].to_node
                != _upstream_field_node(upstream_symbol, lookup_name)
            ):
                raise ValueError("Group-key output dependency mismatch")
            continue
        provenance = field.provenance
        aggregate_fact = aggregate_result_facts.get(output_name)
        if (
            not isinstance(provenance, ProjectRowFieldProvenance)
            or provenance.kind is not ProjectRowFieldProvenanceKind.AGGREGATE
            or not isinstance(aggregate_fact, ProjectAggregateResultFact)
        ):
            raise ValueError("Aggregate output requires exact result fact")
        argument_edges = tuple(
            edge
            for edge in outgoing
            if edge.kind is ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT
        )
        relation_edges = tuple(
            edge
            for edge in outgoing
            if edge.kind is ProjectRowDependencyEdgeKind.AGGREGATE_RELATION_INPUT
        )
        if aggregate_fact.argument_count == 0:
            relation_target = None if not relation_edges else relation_edges[0].to_node
            if (
                aggregate_fact.function != COUNT_AGGREGATE_NAME
                or argument_edges
                or len(relation_edges) != 1
                or len(outgoing) != 1
                or relation_target is None
                or relation_target.kind
                is not ProjectRowDependencyNodeKind.RELATION_INPUT
                or relation_target.field_name is not None
                or relation_target.output_name is not None
                or relation_target.binding_name is not None
                or relation_target.name != upstream_symbol.name
                or relation_target.relation_name != upstream_symbol.name
                or relation_target.source_name != upstream_symbol.name
            ):
                raise ValueError("No-argument aggregate dependency mismatch")
        elif (
            aggregate_fact.argument_count != 1
            or not argument_edges
            or relation_edges
            or len(outgoing) != len(argument_edges)
            or len({edge.to_node for edge in argument_edges}) != len(argument_edges)
            or any(
                edge.to_node.kind
                not in {
                    ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
                    ProjectRowDependencyNodeKind.LET_BINDING,
                }
                for edge in argument_edges
            )
            or any(
                edge.to_node.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
                and (
                    edge.to_node.relation_name != upstream_symbol.name
                    or edge.to_node.source_name != upstream_symbol.name
                    or edge.to_node.field_name is None
                    or edge.to_node.name
                    != f"{upstream_symbol.name}.{edge.to_node.field_name}"
                )
                for edge in argument_edges
            )
            or any(
                edge.to_node.kind is ProjectRowDependencyNodeKind.LET_BINDING
                and (
                    edge.to_node.relation_name != definition.name
                    or edge.to_node.binding_name != edge.to_node.name
                )
                for edge in argument_edges
            )
        ):
            raise ValueError("Aggregate argument dependency mismatch")

    for edge in graph.edges:
        if edge.from_node.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
            continue
        if (
            edge.kind is not ProjectRowDependencyEdgeKind.LET_EXPRESSION
            or edge.from_node.kind is not ProjectRowDependencyNodeKind.LET_BINDING
            or edge.from_node.relation_name != definition.name
            or edge.from_node.binding_name != edge.from_node.name
            or edge.to_node.kind
            not in {
                ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
                ProjectRowDependencyNodeKind.LET_BINDING,
            }
            or (
                edge.to_node.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
                and (
                    edge.to_node.relation_name != upstream_symbol.name
                    or edge.to_node.source_name != upstream_symbol.name
                )
            )
            or (
                edge.to_node.kind is ProjectRowDependencyNodeKind.LET_BINDING
                and edge.to_node.relation_name != definition.name
            )
        ):
            raise ValueError("Non-output dependency must be a let expression")


def _validate_lineage_shape(
    definition: _DerivedRelation,
    upstream_symbol: ProjectSymbol,
    graph: ProjectRelationRowDependencyGraph,
    lineage: ProjectRelationRowLineage,
) -> None:
    if len(set(lineage.facts)) != len(lineage.facts):
        raise ValueError("Concrete lineage requires unique facts")

    expected_immediate = tuple(
        _lineage_fact_from_edge(
            edge,
            definition=definition,
            upstream_symbol=upstream_symbol,
        )
        for edge in graph.edges
    )
    immediate_index = 0
    current_immediate = None
    for fact in lineage.facts:
        if fact.kind is ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY:
            if (
                current_immediate is None
                or current_immediate.kind
                is ProjectRowLineageFactKind.AGGREGATE_RELATION_INPUT
                or fact.output_segment != current_immediate.output_segment
                or fact.location != current_immediate.location
                or fact.upstream_segment.kind
                is ProjectRowLineageSegmentKind.OUTPUT_FIELD
            ):
                raise ValueError("Lineage transitive expansion mismatch")
            continue
        if (
            immediate_index >= len(expected_immediate)
            or fact != expected_immediate[immediate_index]
        ):
            raise ValueError("Lineage immediate edge conversion mismatch")
        current_immediate = fact
        immediate_index += 1

    if immediate_index != len(expected_immediate):
        raise ValueError("Lineage must retain every immediate graph edge")


def _mapped_readiness_failure(
    readiness: ProjectAggregateGroupedClauseReadiness,
) -> tuple[ProjectRowDependencyGraphStatus, ProjectRowDependencyGraphReason]:
    if (
        readiness.reason
        is ProjectAggregateGroupedClauseReadinessReason.SCHEMA_FINALIZATION_NON_CONCRETE
    ):
        state = readiness.finalization.state
        return (
            ProjectRowDependencyGraphStatus(state.status.value),
            ProjectRowDependencyGraphReason(state.reason.value),
        )
    if (
        readiness.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
        and readiness.reason
        is ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
    ):
        return (
            ProjectRowDependencyGraphStatus.UNKNOWN,
            ProjectRowDependencyGraphReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
        )
    if (
        readiness.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
        and readiness.reason
        in {
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE,
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        }
    ):
        return (
            ProjectRowDependencyGraphStatus.UNKNOWN,
            ProjectRowDependencyGraphReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        )
    if (
        readiness.status is ProjectAggregateGroupedClauseReadinessStatus.DEFERRED
        and readiness.reason
        is ProjectAggregateGroupedClauseReadinessReason.UNSUPPORTED_CLAUSE_FAMILY
    ):
        return (
            ProjectRowDependencyGraphStatus.DEFERRED,
            ProjectRowDependencyGraphReason.AGGREGATE_OR_GROUPED_DEFERRED,
        )
    if (
        readiness.status is ProjectAggregateGroupedClauseReadinessStatus.BLOCKED
        and readiness.reason
        in {
            ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT,
            ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS,
        }
    ):
        return (
            ProjectRowDependencyGraphStatus.BLOCKED,
            ProjectRowDependencyGraphReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        )
    raise ValueError("Unsupported clause-readiness outcome")


def _failed_readiness(
    *,
    definition: _DerivedRelation,
    clause_readiness: ProjectAggregateGroupedClauseReadiness,
    status: ProjectRowDependencyGraphStatus,
    reason: ProjectRowDependencyGraphReason,
) -> ProjectAggregateGroupedDependencyLineageReadiness:
    return ProjectAggregateGroupedDependencyLineageReadiness(
        definition=definition,
        clause_readiness=clause_readiness,
        dependency_graph=ProjectRelationRowDependencyGraph(
            status=status,
            reason=reason,
        ),
        lineage=ProjectRelationRowLineage(
            status=ProjectRowLineageStatus(status.value),
            reason=ProjectRowLineageReason(reason.value),
        ),
    )


def _projection_output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _direct_lookup_name(
    expression: Expression,
    *,
    relation_qualifier: str,
) -> str | None:
    if isinstance(expression, NameExpr):
        return expression.name
    if (
        isinstance(expression, DottedNameExpr)
        and len(expression.parts) == 2
        and expression.parts[0] == relation_qualifier
    ):
        return expression.parts[1]
    return None


def _relation_input_node(upstream_symbol: ProjectSymbol) -> ProjectRowDependencyNode:
    upstream_definition = upstream_symbol.definition
    if upstream_symbol.kind is ProjectSymbolKind.SOURCE and isinstance(
        upstream_definition,
        SourceDef,
    ):
        return ProjectRowDependencyNode(
            kind=ProjectRowDependencyNodeKind.RELATION_INPUT,
            name=upstream_symbol.name,
            relation_name=upstream_symbol.name,
            source_name=upstream_symbol.name,
        )
    if upstream_symbol.kind in {
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    } and isinstance(upstream_definition, (TableDef, QueryDef)):
        return ProjectRowDependencyNode(
            kind=ProjectRowDependencyNodeKind.RELATION_INPUT,
            name=upstream_symbol.name,
            relation_name=upstream_symbol.name,
            source_name=upstream_symbol.name,
        )
    _conflicting_failure()


def _unavailable_failure() -> Never:
    raise _ClassifiedFailure(
        ProjectRowDependencyGraphStatus.UNKNOWN,
        ProjectRowDependencyGraphReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
    )


def _invalid_failure() -> Never:
    raise _ClassifiedFailure(
        ProjectRowDependencyGraphStatus.UNKNOWN,
        ProjectRowDependencyGraphReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
    )


def _conflicting_failure() -> Never:
    raise _ClassifiedFailure(
        ProjectRowDependencyGraphStatus.BLOCKED,
        ProjectRowDependencyGraphReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
    )
