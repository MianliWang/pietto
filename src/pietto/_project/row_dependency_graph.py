"""Private project row-level dependency graph scaffold."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
)
from pietto._project.model import (
    ProjectParsedInput,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectRowFieldProvenanceKind,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
)
from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    FromClause,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    SourceDef,
    TableDef,
    UnaryExpr,
)
from pietto.errors import SourceLocation

_DerivedRelation = TableDef | QueryDef

_SEMANTIC_AGGREGATE_NAMES = frozenset(
    {"count", "count_distinct", "sum", "avg", "min", "max"}
)


class ProjectRowDependencyGraphStatus(StrEnum):
    """Private availability status for one relation row dependency graph."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


class ProjectRowDependencyGraphReason(StrEnum):
    """Private deterministic reason for one row dependency graph."""

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


class ProjectRowDependencyNodeKind(StrEnum):
    """Private row dependency graph node kinds."""

    OUTPUT_FIELD = "output_field"
    UPSTREAM_FIELD = "upstream_field"
    LET_BINDING = "let_binding"


class ProjectRowDependencyEdgeKind(StrEnum):
    """Private row dependency graph edge kinds."""

    DIRECT_PROJECTION = "direct_projection"
    RENAMED_PROJECTION = "renamed_projection"
    COMPUTED_EXPRESSION = "computed_expression"
    LET_OUTPUT = "let_output"
    LET_EXPRESSION = "let_expression"


@dataclass(frozen=True, slots=True)
class ProjectRowDependencyNode:
    """One private row-level dependency graph node."""

    kind: ProjectRowDependencyNodeKind
    name: str
    relation_name: str | None = None
    output_name: str | None = None
    binding_name: str | None = None
    source_name: str | None = None
    field_name: str | None = None

    def __post_init__(self) -> None:
        """Validate private node invariants."""

        if not isinstance(self.kind, ProjectRowDependencyNodeKind):
            raise ValueError("Project row dependency node requires a kind")


@dataclass(frozen=True, slots=True)
class ProjectRowDependencyEdge:
    """One private row-level dependency graph edge."""

    kind: ProjectRowDependencyEdgeKind
    from_node: ProjectRowDependencyNode
    to_node: ProjectRowDependencyNode
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        """Validate private edge invariants."""

        if not isinstance(self.kind, ProjectRowDependencyEdgeKind):
            raise ValueError("Project row dependency edge requires a kind")


@dataclass(frozen=True, slots=True)
class ProjectRelationRowDependencyGraph:
    """Private row-level dependency graph for one project relation."""

    status: ProjectRowDependencyGraphStatus
    reason: ProjectRowDependencyGraphReason
    nodes: tuple[ProjectRowDependencyNode, ...] = ()
    edges: tuple[ProjectRowDependencyEdge, ...] = ()

    def __post_init__(self) -> None:
        """Copy graph collections into immutable tuples and validate status."""

        if not isinstance(self.status, ProjectRowDependencyGraphStatus):
            raise ValueError("Project row dependency graph requires a status")
        if not isinstance(self.reason, ProjectRowDependencyGraphReason):
            raise ValueError("Project row dependency graph requires a reason")
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))


def build_project_relation_row_dependency_graphs(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema],
    relation_row_schemas: Mapping[_DerivedRelation, ProjectRowSchema],
    relation_row_schema_states: Mapping[
        _DerivedRelation, ProjectRelationRowSchemaState
    ],
    relation_let_scope_facts: Mapping[_DerivedRelation, ProjectRelationLetScopeFacts],
) -> dict[_DerivedRelation, ProjectRelationRowDependencyGraph]:
    """Build private row-level dependency graph scaffolds for project relations."""

    graphs: dict[_DerivedRelation, ProjectRelationRowDependencyGraph] = {}
    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue
            graphs[definition] = _build_relation_row_dependency_graph(
                definition,
                fallback_path=parsed_input.path,
                relation_resolutions=relation_resolutions,
                source_row_schemas=source_row_schemas,
                relation_row_schemas=relation_row_schemas,
                relation_row_schema_states=relation_row_schema_states,
                relation_let_scope_facts=relation_let_scope_facts,
            )
    return graphs


def _build_relation_row_dependency_graph(
    definition: _DerivedRelation,
    *,
    fallback_path: str,
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema],
    relation_row_schemas: Mapping[_DerivedRelation, ProjectRowSchema],
    relation_row_schema_states: Mapping[
        _DerivedRelation, ProjectRelationRowSchemaState
    ],
    relation_let_scope_facts: Mapping[_DerivedRelation, ProjectRelationLetScopeFacts],
) -> ProjectRelationRowDependencyGraph:
    state = relation_row_schema_states.get(definition)
    if state is None:
        return _non_concrete_graph(
            status=ProjectRowDependencyGraphStatus.BLOCKED,
            reason=ProjectRowDependencyGraphReason.MISSING_ROW_SCHEMA_STATE,
        )
    if state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        return _non_concrete_graph(
            status=ProjectRowDependencyGraphStatus(state.status.value),
            reason=_reason_from_row_schema_reason(state.reason),
        )

    output_schema = relation_row_schemas.get(definition)
    if output_schema is None or output_schema.is_unknown:
        return _non_concrete_graph(
            status=ProjectRowDependencyGraphStatus.UNKNOWN,
            reason=ProjectRowDependencyGraphReason.MISSING_ROW_SCHEMA,
        )

    upstream_symbol = relation_resolutions.get(definition.from_clause)
    input_schema = _input_schema(
        upstream_symbol,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
    )
    if upstream_symbol is None or input_schema is None or input_schema.is_unknown:
        return _non_concrete_graph(
            status=ProjectRowDependencyGraphStatus.UNKNOWN,
            reason=ProjectRowDependencyGraphReason.MISSING_UPSTREAM_SCHEMA,
        )

    builder = _GraphBuilder()
    let_facts = relation_let_scope_facts.get(definition)
    concrete_let_names = _concrete_let_names(let_facts)

    _add_output_edges(
        builder,
        definition,
        fallback_path=fallback_path,
        upstream_symbol=upstream_symbol,
        input_schema=input_schema,
        output_schema=output_schema,
        concrete_let_names=concrete_let_names,
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
        reason=_reason_from_row_schema_reason(state.reason),
        nodes=tuple(builder.nodes),
        edges=tuple(builder.edges),
    )


def _add_output_edges(
    builder: _GraphBuilder,
    definition: _DerivedRelation,
    *,
    fallback_path: str,
    upstream_symbol: ProjectSymbol,
    input_schema: ProjectRowSchema,
    output_schema: ProjectRowSchema,
    concrete_let_names: frozenset[str],
) -> None:
    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is None or output_name not in output_schema.fields:
            continue

        output_node = _output_node(definition, output_name)
        builder.add_node(output_node)
        lookup_name = _direct_lookup_name(
            item.expression,
            relation_qualifier=definition.from_clause.source_name,
        )
        if lookup_name is not None and lookup_name in input_schema.fields:
            edge_kind = (
                ProjectRowDependencyEdgeKind.RENAMED_PROJECTION
                if output_name != lookup_name
                else ProjectRowDependencyEdgeKind.DIRECT_PROJECTION
            )
            builder.add_edge(
                ProjectRowDependencyEdge(
                    kind=edge_kind,
                    from_node=output_node,
                    to_node=_upstream_field_node(upstream_symbol, lookup_name),
                    location=_expression_location(
                        item.expression,
                        fallback_path=fallback_path,
                    ),
                )
            )
            continue

        output_field = output_schema.fields[output_name]
        provenance_kind = (
            output_field.provenance.kind
            if output_field.provenance is not None
            else ProjectRowFieldProvenanceKind.UNKNOWN
        )
        if (
            provenance_kind is ProjectRowFieldProvenanceKind.LET_DERIVED
            and isinstance(item.expression, NameExpr)
            and item.expression.name in concrete_let_names
        ):
            builder.add_edge(
                ProjectRowDependencyEdge(
                    kind=ProjectRowDependencyEdgeKind.LET_OUTPUT,
                    from_node=output_node,
                    to_node=_let_binding_node(definition, item.expression.name),
                    location=_expression_location(
                        item.expression,
                        fallback_path=fallback_path,
                    ),
                )
            )
            continue

        if provenance_kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION:
            for dependency_node in _expression_dependency_nodes(
                item.expression,
                definition=definition,
                upstream_symbol=upstream_symbol,
                input_schema=input_schema,
                allowed_let_names=concrete_let_names,
            ):
                builder.add_edge(
                    ProjectRowDependencyEdge(
                        kind=ProjectRowDependencyEdgeKind.COMPUTED_EXPRESSION,
                        from_node=output_node,
                        to_node=dependency_node,
                        location=_expression_location(
                            item.expression,
                            fallback_path=fallback_path,
                        ),
                    )
                )


def _add_let_expression_edges(
    builder: _GraphBuilder,
    definition: _DerivedRelation,
    *,
    fallback_path: str,
    upstream_symbol: ProjectSymbol,
    input_schema: ProjectRowSchema,
    let_facts: ProjectRelationLetScopeFacts | None,
) -> None:
    if let_facts is None or let_facts.status is not ProjectLetScopeFactsStatus.CONCRETE:
        return

    prior_let_names: set[str] = set()
    seen_names: set[str] = set()
    for binding in let_facts.bindings:
        if binding.name in seen_names:
            continue
        seen_names.add(binding.name)
        if binding.name not in let_facts.value_types:
            continue

        binding_node = _let_binding_node(definition, binding.name)
        builder.add_node(binding_node)
        for dependency_node in _expression_dependency_nodes(
            binding.expression,
            definition=definition,
            upstream_symbol=upstream_symbol,
            input_schema=input_schema,
            allowed_let_names=frozenset(prior_let_names),
        ):
            builder.add_edge(
                ProjectRowDependencyEdge(
                    kind=ProjectRowDependencyEdgeKind.LET_EXPRESSION,
                    from_node=binding_node,
                    to_node=dependency_node,
                    location=_expression_location(
                        binding.expression,
                        fallback_path=fallback_path,
                    ),
                )
            )
        prior_let_names.add(binding.name)


def _expression_dependency_nodes(
    expression: Expression,
    *,
    definition: _DerivedRelation,
    upstream_symbol: ProjectSymbol,
    input_schema: ProjectRowSchema,
    allowed_let_names: frozenset[str],
) -> tuple[ProjectRowDependencyNode, ...]:
    if _contains_semantic_aggregate(expression):
        return ()

    nodes: list[ProjectRowDependencyNode] = []

    def add(node: ProjectRowDependencyNode) -> None:
        if node not in nodes:
            nodes.append(node)

    def visit(current: Expression) -> None:
        if isinstance(current, LiteralExpr):
            return
        if isinstance(current, NameExpr):
            if current.name in input_schema.fields:
                add(_upstream_field_node(upstream_symbol, current.name))
                return
            if current.name in allowed_let_names:
                add(_let_binding_node(definition, current.name))
            return
        if isinstance(current, DottedNameExpr):
            lookup_name = _direct_lookup_name(
                current,
                relation_qualifier=definition.from_clause.source_name,
            )
            if lookup_name is not None and lookup_name in input_schema.fields:
                add(_upstream_field_node(upstream_symbol, lookup_name))
            return
        if isinstance(current, CallExpr):
            for argument in current.arguments:
                visit(argument)
            return
        for child in _child_expressions(current):
            visit(child)

    visit(expression)
    return tuple(nodes)


def _input_schema(
    upstream_symbol: ProjectSymbol | None,
    *,
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema],
    relation_row_schemas: Mapping[_DerivedRelation, ProjectRowSchema],
) -> ProjectRowSchema | None:
    if upstream_symbol is None:
        return None
    if upstream_symbol.kind is ProjectSymbolKind.SOURCE and isinstance(
        upstream_symbol.definition,
        SourceDef,
    ):
        return source_row_schemas.get(upstream_symbol.definition)
    if upstream_symbol.kind in (
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    ) and isinstance(upstream_symbol.definition, (TableDef, QueryDef)):
        return relation_row_schemas.get(upstream_symbol.definition)
    return None


def _non_concrete_graph(
    *,
    status: ProjectRowDependencyGraphStatus,
    reason: ProjectRowDependencyGraphReason,
) -> ProjectRelationRowDependencyGraph:
    return ProjectRelationRowDependencyGraph(status=status, reason=reason)


def _reason_from_row_schema_reason(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectRowDependencyGraphReason:
    return ProjectRowDependencyGraphReason(reason.value)


def _concrete_let_names(
    let_facts: ProjectRelationLetScopeFacts | None,
) -> frozenset[str]:
    if let_facts is None or let_facts.status is not ProjectLetScopeFactsStatus.CONCRETE:
        return frozenset()
    return frozenset(let_facts.value_types)


def _projection_output_name(item: SelectItem) -> str | None:
    expression = item.expression
    if item.alias is not None:
        return item.alias
    if isinstance(expression, NameExpr):
        return expression.name
    if isinstance(expression, DottedNameExpr):
        return expression.parts[-1]
    return None


def _direct_lookup_name(
    expression: Expression,
    *,
    relation_qualifier: str | None,
) -> str | None:
    if isinstance(expression, NameExpr):
        return expression.name
    if (
        isinstance(expression, DottedNameExpr)
        and relation_qualifier is not None
        and len(expression.parts) == 2
        and expression.parts[0] == relation_qualifier
    ):
        return expression.parts[1]
    return None


def _output_node(
    definition: _DerivedRelation,
    output_name: str,
) -> ProjectRowDependencyNode:
    return ProjectRowDependencyNode(
        kind=ProjectRowDependencyNodeKind.OUTPUT_FIELD,
        name=output_name,
        relation_name=definition.name,
        output_name=output_name,
    )


def _upstream_field_node(
    upstream_symbol: ProjectSymbol,
    field_name: str,
) -> ProjectRowDependencyNode:
    return ProjectRowDependencyNode(
        kind=ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
        name=f"{upstream_symbol.name}.{field_name}",
        relation_name=upstream_symbol.name,
        source_name=upstream_symbol.name,
        field_name=field_name,
    )


def _let_binding_node(
    definition: _DerivedRelation,
    binding_name: str,
) -> ProjectRowDependencyNode:
    return ProjectRowDependencyNode(
        kind=ProjectRowDependencyNodeKind.LET_BINDING,
        name=binding_name,
        relation_name=definition.name,
        binding_name=binding_name,
    )


def _contains_semantic_aggregate(expression: Expression) -> bool:
    if (
        isinstance(expression, CallExpr)
        and isinstance(expression.callee, NameExpr)
        and expression.callee.name in _SEMANTIC_AGGREGATE_NAMES
    ):
        return True
    return any(
        _contains_semantic_aggregate(child) for child in _child_expressions(expression)
    )


def _child_expressions(expression: Expression) -> tuple[Expression, ...]:
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, BinaryExpr):
        return (expression.left, expression.right)
    if isinstance(expression, ComparisonExpr):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    return ()


def _expression_location(
    expression: Expression,
    *,
    fallback_path: str,
) -> SourceLocation:
    span = expression.span
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


class _GraphBuilder:
    """Accumulate deterministic private graph nodes and edges."""

    def __init__(self) -> None:
        self.nodes: list[ProjectRowDependencyNode] = []
        self.edges: list[ProjectRowDependencyEdge] = []

    def add_node(self, node: ProjectRowDependencyNode) -> None:
        if node not in self.nodes:
            self.nodes.append(node)

    def add_edge(self, edge: ProjectRowDependencyEdge) -> None:
        self.add_node(edge.from_node)
        self.add_node(edge.to_node)
        if edge not in self.edges:
            self.edges.append(edge)
