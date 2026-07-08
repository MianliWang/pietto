"""Private immutable models for project discovery and configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, TypeVar

from pietto.ast_nodes import (
    ConstraintDef,
    Definition,
    DeriveDef,
    DottedNameExpr,
    EnumDef,
    FieldDef,
    FromClause,
    NameExpr,
    Nullability,
    QueryDef,
    Script,
    SelectItem,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
    TypeExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

if TYPE_CHECKING:
    from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts
    from pietto._project.row_dependency_graph import ProjectRelationRowDependencyGraph

_Key = TypeVar("_Key")
_Value = TypeVar("_Value")

_PROJECT_BUILTIN_TYPE_NAMES = frozenset(
    {
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    }
)


def _readonly_mapping(
    values: Mapping[_Key, _Value] | None = None,
) -> Mapping[_Key, _Value]:
    """Copy values into an immutable private mapping."""

    return MappingProxyType(dict(values or {}))


class ProjectDiscoveryErrorKind(StrEnum):
    """Private project discovery error categories."""

    PROJECT_ROOT = "project_root"
    CONFIG_READ = "config_read"
    CONFIG_PARSE = "config_parse"
    CONFIG_SCHEMA = "config_schema"
    PROJECT_PATH = "project_path"
    PROJECT_GLOB = "project_glob"
    PROJECT_RESOURCE = "project_resource"
    SOURCE_READ = "source_read"


@dataclass(frozen=True, slots=True)
class ProjectRoot:
    """Established project root as a project-relative identity."""

    path: str


@dataclass(frozen=True, slots=True)
class ProjectConfigPath:
    """Project configuration path relative to the established root."""

    path: str


@dataclass(frozen=True, slots=True)
class ProjectInput:
    """One explicitly selected project input."""

    path: str
    status: str


@dataclass(frozen=True, slots=True)
class ProjectParsedInput:
    """One successfully parsed selected project input for later semantics."""

    path: str
    script: Script


@dataclass(frozen=True, slots=True)
class ProjectSourceConfig:
    """Private project source pattern configuration."""

    include_patterns: tuple[str, ...]
    exclude_patterns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Private parsed project configuration."""

    schema_version: int
    sources: ProjectSourceConfig


@dataclass(frozen=True, slots=True)
class ProjectDiscoveryError:
    """One private project discovery error."""

    kind: ProjectDiscoveryErrorKind
    message: str
    path: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectDiscoveryResult:
    """Private project discovery result for future project-mode orchestration."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    inputs: tuple[ProjectInput, ...]
    errors: tuple[ProjectDiscoveryError, ...]

    @property
    def ok(self) -> bool:
        """Return whether discovery completed without private project errors."""

        return not self.errors


@dataclass(frozen=True, slots=True)
class ProjectConfigLoadResult:
    """Private project configuration load result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    config: ProjectConfig | None
    errors: tuple[ProjectDiscoveryError, ...]

    @property
    def ok(self) -> bool:
        """Return whether configuration loading completed without errors."""

        return not self.errors


@dataclass(frozen=True, slots=True)
class ProjectParseCheckResult:
    """Private parse-only project check result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    inputs: tuple[ProjectInput, ...]
    errors: tuple[ProjectDiscoveryError, ...]
    diagnostics: tuple[Diagnostic, ...]
    parsed_inputs: tuple[ProjectParsedInput, ...] = ()

    @property
    def ok(self) -> bool:
        """Return whether parse-only project check completed without errors."""

        return not self.errors and not any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        )


class ProjectSymbolNamespace(StrEnum):
    """Project-wide namespace assigned to a top-level symbol."""

    TYPE = "type"
    RELATION = "relation"
    CALLABLE = "callable"


class ProjectSymbolKind(StrEnum):
    """Project-wide kind assigned to a top-level symbol."""

    TYPE_ALIAS = "type"
    ENUM = "enum"
    SHAPE = "shape"
    SOURCE = "source"
    TABLE = "table"
    QUERY = "query"
    CONSTRAINT = "constraint"
    DERIVE = "derive"


@dataclass(frozen=True, slots=True)
class ProjectSymbol:
    """One private project-wide top-level symbol."""

    namespace: ProjectSymbolNamespace
    kind: ProjectSymbolKind
    name: str
    path: str
    location: SourceLocation
    definition: Definition


class ProjectResolvedTypeKind(StrEnum):
    """Project-private type resolution fact kind."""

    BUILTIN = "builtin"
    TYPE_ALIAS = "type"
    ENUM = "enum"
    SHAPE = "shape"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProjectResolvedType:
    """One project-private resolved type name fact."""

    name: str
    kind: ProjectResolvedTypeKind
    symbol: ProjectSymbol | None = None


class ProjectRowFieldNullability(StrEnum):
    """Project-private row field nullability fact."""

    NON_NULL = "non_null"
    NULLABLE = "nullable"
    UNKNOWN = "unknown"


class ProjectRowFieldProvenanceKind(StrEnum):
    """Project-private row field provenance categories for future slices."""

    SOURCE_FIELD = "source_field"
    DIRECT_PROJECTION = "direct_projection"
    DERIVED_EXPRESSION = "derived_expression"
    LET_DERIVED = "let_derived"
    EXPRESSION = "expression"
    AGGREGATE = "aggregate"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProjectRowFieldProvenance:
    """Inert private origin metadata for a future project row field."""

    kind: ProjectRowFieldProvenanceKind
    symbol: ProjectSymbol | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class ProjectRowField:
    """One private project row field scaffold fact."""

    name: str
    resolved_type: ProjectResolvedType
    nullability: ProjectRowFieldNullability
    field_def: FieldDef | None = None
    provenance: ProjectRowFieldProvenance | None = None


@dataclass(frozen=True, slots=True)
class ProjectRowSchema:
    """Ordered private project row schema scaffold."""

    fields: Mapping[str, ProjectRowField] = field(
        default_factory=lambda: _readonly_mapping()
    )
    is_unknown: bool = False

    def __post_init__(self) -> None:
        """Copy row field maps into immutable mappings."""

        object.__setattr__(self, "fields", _readonly_mapping(self.fields))


class ProjectRelationRowSchemaStatus(StrEnum):
    """Private relation row schema availability states for future propagation."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


class ProjectRelationRowSchemaReason(StrEnum):
    """Private relation row schema availability reasons."""

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


@dataclass(frozen=True, slots=True)
class ProjectRelationRowSchemaState:
    """Private relation row schema availability carrier."""

    status: ProjectRelationRowSchemaStatus
    schema: ProjectRowSchema | None
    reason: ProjectRelationRowSchemaReason

    def __post_init__(self) -> None:
        """Validate private availability carrier invariants."""

        if not isinstance(self.status, ProjectRelationRowSchemaStatus):
            raise ValueError("Project relation row schema state requires a status")
        if not isinstance(self.reason, ProjectRelationRowSchemaReason):
            raise ValueError("Project relation row schema state requires a reason")

        if self.status is ProjectRelationRowSchemaStatus.CONCRETE:
            if self.schema is None:
                raise ValueError("Concrete relation row schema state requires schema")
            if self.schema.is_unknown:
                raise ValueError("Concrete relation row schema state cannot be unknown")
            return

        if self.status is ProjectRelationRowSchemaStatus.UNKNOWN:
            if self.schema is None:
                raise ValueError("Unknown relation row schema state requires schema")
            if not self.schema.is_unknown:
                raise ValueError(
                    "Unknown relation row schema state requires unknown schema"
                )
            return

        if self.schema is not None:
            raise ValueError(
                "Deferred or blocked relation row schema state forbids schema"
            )


class _ProjectDirectFieldProjectionStatus(StrEnum):
    """Private status for one direct-field projection candidate."""

    SUPPORTED = "supported"
    INVALID = "invalid"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class _ProjectDirectFieldProjection:
    """Private decoded direct-field projection candidate."""

    status: _ProjectDirectFieldProjectionStatus
    output_name: str | None = None
    lookup_name: str | None = None
    field_text: str | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class _ProjectRelationRowSchemaResult:
    """Private result for one relation row schema build attempt."""

    schema: ProjectRowSchema | None
    diagnostics: tuple[Diagnostic, ...] = ()
    state_reason: ProjectRelationRowSchemaReason | None = None


@dataclass(frozen=True, slots=True)
class _ProjectRelationRowSchemasResult:
    """Private result for all project relation row schemas."""

    relation_row_schemas: dict[TableDef | QueryDef, ProjectRowSchema]
    relation_row_schema_states: dict[TableDef | QueryDef, ProjectRelationRowSchemaState]
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencyNode:
    """One private relation dependency graph node."""

    symbol: ProjectSymbol


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencySource:
    """One private source location for a future relation dependency edge."""

    from_clause: FromClause


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencyEdge:
    """One private relation dependency graph edge."""

    origin: ProjectRelationDependencyNode
    target: ProjectRelationDependencyNode
    dependency_source: ProjectRelationDependencySource


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencyCycle:
    """One private relation dependency cycle fact."""

    nodes: tuple[ProjectRelationDependencyNode, ...]
    edges: tuple[ProjectRelationDependencyEdge, ...]

    def __post_init__(self) -> None:
        """Copy cycle collections into immutable tuples."""

        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencyGraph:
    """Private relation dependency graph scaffold."""

    nodes: tuple[ProjectRelationDependencyNode, ...] = ()
    edges: tuple[ProjectRelationDependencyEdge, ...] = ()
    cycles: tuple[ProjectRelationDependencyCycle, ...] = ()

    def __post_init__(self) -> None:
        """Copy graph collections into immutable tuples."""

        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "cycles", tuple(self.cycles))


@dataclass(frozen=True, slots=True)
class ProjectSemanticCatalog:
    """Private project semantic catalog populated before reference resolution."""

    type_symbols: Mapping[str, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )
    relation_symbols: Mapping[str, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )
    callable_symbols: Mapping[str, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )

    def __post_init__(self) -> None:
        """Copy symbol maps into immutable mappings."""

        object.__setattr__(
            self,
            "type_symbols",
            _readonly_mapping(self.type_symbols),
        )
        object.__setattr__(
            self,
            "relation_symbols",
            _readonly_mapping(self.relation_symbols),
        )
        object.__setattr__(
            self,
            "callable_symbols",
            _readonly_mapping(self.callable_symbols),
        )


@dataclass(frozen=True, slots=True)
class ProjectSemanticModel:
    """Private project-wide semantic model scaffold."""

    root: ProjectRoot
    config_path: ProjectConfigPath
    inputs: tuple[ProjectParsedInput, ...]
    catalog: ProjectSemanticCatalog
    type_resolutions: Mapping[TypeExpr, ProjectResolvedType] = field(
        default_factory=lambda: _readonly_mapping()
    )
    source_shape_resolutions: Mapping[SourceDef, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )
    relation_resolutions: Mapping[FromClause, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema] = field(
        default_factory=lambda: _readonly_mapping()
    )
    relation_row_schemas: Mapping[TableDef | QueryDef, ProjectRowSchema] = field(
        default_factory=lambda: _readonly_mapping()
    )
    relation_row_schema_states: Mapping[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ] = field(default_factory=lambda: _readonly_mapping())
    relation_let_scope_facts: Mapping[
        TableDef | QueryDef, ProjectRelationLetScopeFacts
    ] = field(default_factory=lambda: _readonly_mapping())
    relation_row_dependency_graphs: Mapping[
        TableDef | QueryDef, ProjectRelationRowDependencyGraph
    ] = field(default_factory=lambda: _readonly_mapping())
    relation_dependency_graph: ProjectRelationDependencyGraph = field(
        default_factory=ProjectRelationDependencyGraph
    )

    def __post_init__(self) -> None:
        """Copy private project semantic maps into immutable mappings."""

        object.__setattr__(
            self,
            "type_resolutions",
            _readonly_mapping(self.type_resolutions),
        )
        object.__setattr__(
            self,
            "source_shape_resolutions",
            _readonly_mapping(self.source_shape_resolutions),
        )
        object.__setattr__(
            self,
            "relation_resolutions",
            _readonly_mapping(self.relation_resolutions),
        )
        object.__setattr__(
            self,
            "source_row_schemas",
            _readonly_mapping(self.source_row_schemas),
        )
        object.__setattr__(
            self,
            "relation_row_schemas",
            _readonly_mapping(self.relation_row_schemas),
        )
        object.__setattr__(
            self,
            "relation_row_schema_states",
            _readonly_mapping(self.relation_row_schema_states),
        )
        object.__setattr__(
            self,
            "relation_let_scope_facts",
            _readonly_mapping(self.relation_let_scope_facts),
        )
        object.__setattr__(
            self,
            "relation_row_dependency_graphs",
            _readonly_mapping(self.relation_row_dependency_graphs),
        )


@dataclass(frozen=True, slots=True)
class ProjectSemanticResult:
    """Private project-wide semantic scaffold result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    model: ProjectSemanticModel | None
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        """Return whether project semantic scaffolding completed without errors."""

        return self.model is not None and not any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        )


def build_empty_project_semantic_result(
    parse_result: ProjectParseCheckResult,
) -> ProjectSemanticResult:
    """Build the private project semantic scaffold from parse-only input."""

    if (
        not parse_result.ok
        or parse_result.root is None
        or parse_result.config_path is None
    ):
        return ProjectSemanticResult(
            root=parse_result.root,
            config_path=parse_result.config_path,
            model=None,
        )

    catalog, catalog_diagnostics = _build_project_semantic_catalog(
        parse_result.parsed_inputs
    )
    relation_dependency_graph = _build_project_relation_dependency_graph(
        parsed_inputs=parse_result.parsed_inputs,
        catalog=catalog,
    )
    if catalog_diagnostics:
        return ProjectSemanticResult(
            root=parse_result.root,
            config_path=parse_result.config_path,
            model=ProjectSemanticModel(
                root=parse_result.root,
                config_path=parse_result.config_path,
                inputs=parse_result.parsed_inputs,
                catalog=catalog,
                relation_dependency_graph=relation_dependency_graph,
            ),
            diagnostics=catalog_diagnostics,
        )

    type_resolutions, source_shape_resolutions, type_diagnostics = (
        _build_project_type_namespace_facts(
            parsed_inputs=parse_result.parsed_inputs,
            catalog=catalog,
        )
    )
    source_row_schemas = _build_project_source_row_schemas(
        source_shape_resolutions=source_shape_resolutions,
        type_resolutions=type_resolutions,
    )
    relation_resolutions, relation_diagnostics = (
        _build_project_relation_namespace_facts(
            parsed_inputs=parse_result.parsed_inputs,
            catalog=catalog,
        )
    )
    relation_dependency_graph = _build_project_relation_dependency_graph(
        parsed_inputs=parse_result.parsed_inputs,
        catalog=catalog,
        relation_resolutions=relation_resolutions,
    )
    relation_row_schema_result = _build_project_relation_row_schemas(
        parsed_inputs=parse_result.parsed_inputs,
        relation_resolutions=relation_resolutions,
        source_row_schemas=source_row_schemas,
        relation_dependency_graph=relation_dependency_graph,
    )
    relation_let_scope_facts = _build_project_relation_let_scope_facts(
        parsed_inputs=parse_result.parsed_inputs,
        relation_resolutions=relation_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schema_result.relation_row_schemas,
        relation_row_schema_states=relation_row_schema_result.relation_row_schema_states,
    )
    relation_row_dependency_graphs = _build_project_relation_row_dependency_graphs(
        parsed_inputs=parse_result.parsed_inputs,
        relation_resolutions=relation_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schema_result.relation_row_schemas,
        relation_row_schema_states=(
            relation_row_schema_result.relation_row_schema_states
        ),
        relation_let_scope_facts=relation_let_scope_facts,
    )
    cycle_diagnostics = _build_project_relation_cycle_diagnostics(
        relation_dependency_graph
    )
    return ProjectSemanticResult(
        root=parse_result.root,
        config_path=parse_result.config_path,
        model=ProjectSemanticModel(
            root=parse_result.root,
            config_path=parse_result.config_path,
            inputs=parse_result.parsed_inputs,
            catalog=catalog,
            type_resolutions=type_resolutions,
            source_shape_resolutions=source_shape_resolutions,
            source_row_schemas=source_row_schemas,
            relation_resolutions=relation_resolutions,
            relation_row_schemas=relation_row_schema_result.relation_row_schemas,
            relation_row_schema_states=(
                relation_row_schema_result.relation_row_schema_states
            ),
            relation_let_scope_facts=relation_let_scope_facts,
            relation_row_dependency_graphs=relation_row_dependency_graphs,
            relation_dependency_graph=relation_dependency_graph,
        ),
        diagnostics=(
            *type_diagnostics,
            *relation_diagnostics,
            *relation_row_schema_result.diagnostics,
            *cycle_diagnostics,
        ),
    )


def _build_project_relation_dependency_graph(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    catalog: ProjectSemanticCatalog,
    relation_resolutions: Mapping[FromClause, ProjectSymbol] | None = None,
) -> ProjectRelationDependencyGraph:
    """Build the private relation dependency graph."""

    nodes = tuple(
        ProjectRelationDependencyNode(symbol=symbol)
        for symbol in catalog.relation_symbols.values()
        if symbol.kind in (ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY)
    )
    node_by_name = {node.symbol.name: node for node in nodes}
    resolutions = relation_resolutions or {}
    edges: list[ProjectRelationDependencyEdge] = []

    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue

            origin = node_by_name.get(definition.name)
            if origin is None:
                continue

            target_symbol = resolutions.get(definition.from_clause)
            if target_symbol is None or target_symbol.kind not in (
                ProjectSymbolKind.TABLE,
                ProjectSymbolKind.QUERY,
            ):
                continue

            target = node_by_name.get(target_symbol.name)
            if target is None:
                continue

            edges.append(
                ProjectRelationDependencyEdge(
                    origin=origin,
                    target=target,
                    dependency_source=ProjectRelationDependencySource(
                        from_clause=definition.from_clause
                    ),
                )
            )

    graph_edges = tuple(edges)
    cycles = _detect_project_relation_dependency_cycles(
        nodes=nodes,
        edges=graph_edges,
    )
    return ProjectRelationDependencyGraph(nodes=nodes, edges=graph_edges, cycles=cycles)


def _detect_project_relation_dependency_cycles(
    *,
    nodes: tuple[ProjectRelationDependencyNode, ...],
    edges: tuple[ProjectRelationDependencyEdge, ...],
) -> tuple[ProjectRelationDependencyCycle, ...]:
    """Detect private relation dependency cycles without emitting diagnostics."""

    if not nodes or not edges:
        return ()

    node_order = {node.symbol.name: index for index, node in enumerate(nodes)}
    edges_by_origin: dict[str, list[ProjectRelationDependencyEdge]] = {
        node.symbol.name: [] for node in nodes
    }
    for edge in edges:
        origin_name = edge.origin.symbol.name
        target_name = edge.target.symbol.name
        if origin_name not in node_order or target_name not in node_order:
            continue
        edges_by_origin[origin_name].append(edge)

    for origin_edges in edges_by_origin.values():
        origin_edges.sort(key=lambda edge: node_order[edge.target.symbol.name])

    state: dict[str, int] = {}
    stack_nodes: list[ProjectRelationDependencyNode] = []
    stack_edges: list[ProjectRelationDependencyEdge] = []
    stack_indexes: dict[str, int] = {}
    cycles_by_members: dict[tuple[int, ...], ProjectRelationDependencyCycle] = {}

    def visit(node: ProjectRelationDependencyNode) -> None:
        node_name = node.symbol.name
        state[node_name] = 1
        stack_indexes[node_name] = len(stack_nodes)
        stack_nodes.append(node)

        for edge in edges_by_origin[node_name]:
            target_name = edge.target.symbol.name
            target_state = state.get(target_name, 0)
            if target_state == 0:
                stack_edges.append(edge)
                visit(edge.target)
                stack_edges.pop()
            elif target_state == 1:
                cycle_start = stack_indexes[target_name]
                cycle = _canonical_project_relation_dependency_cycle(
                    nodes=tuple(stack_nodes[cycle_start:]),
                    edges=tuple((*stack_edges[cycle_start:], edge)),
                    node_order=node_order,
                )
                cycle_key = tuple(
                    sorted(
                        node_order[cycle_node.symbol.name] for cycle_node in cycle.nodes
                    )
                )
                cycles_by_members.setdefault(cycle_key, cycle)

        stack_nodes.pop()
        stack_indexes.pop(node_name)
        state[node_name] = 2

    for node in nodes:
        if state.get(node.symbol.name, 0) == 0:
            visit(node)

    return tuple(
        sorted(
            cycles_by_members.values(),
            key=lambda cycle: tuple(
                node_order[cycle_node.symbol.name] for cycle_node in cycle.nodes
            ),
        )
    )


def _canonical_project_relation_dependency_cycle(
    *,
    nodes: tuple[ProjectRelationDependencyNode, ...],
    edges: tuple[ProjectRelationDependencyEdge, ...],
    node_order: Mapping[str, int],
) -> ProjectRelationDependencyCycle:
    """Rotate one cycle to its lowest graph-node-order participant."""

    if not nodes:
        raise AssertionError("Relation dependency cycle requires at least one node")
    start = min(
        range(len(nodes)),
        key=lambda index: node_order[nodes[index].symbol.name],
    )
    return ProjectRelationDependencyCycle(
        nodes=(*nodes[start:], *nodes[:start]),
        edges=(*edges[start:], *edges[:start]),
    )


def _build_project_relation_cycle_diagnostics(
    graph: ProjectRelationDependencyGraph,
) -> tuple[Diagnostic, ...]:
    """Build project relation cycle diagnostics from private cycle facts."""

    return tuple(_project_relation_cycle_diagnostic(cycle) for cycle in graph.cycles)


def _project_relation_cycle_diagnostic(
    cycle: ProjectRelationDependencyCycle,
) -> Diagnostic:
    """Build one project relation cycle diagnostic."""

    if not cycle.edges:
        raise AssertionError("Relation dependency cycle requires at least one edge")

    closing_edge = cycle.edges[-1]
    span = closing_edge.dependency_source.from_clause.span
    return Diagnostic(
        code="PIE-S2302",
        severity=Severity.ERROR,
        message=f"Relation cycle detected: {_project_relation_cycle_path(cycle)}",
        location=SourceLocation(
            path=span.path or closing_edge.origin.symbol.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _project_relation_cycle_path(
    cycle: ProjectRelationDependencyCycle,
) -> str:
    """Return the user-facing relation cycle path."""

    if not cycle.nodes:
        raise AssertionError("Relation dependency cycle requires at least one node")

    node_names = tuple(node.symbol.name for node in cycle.nodes)
    return " -> ".join((*node_names, node_names[0]))


def _build_project_relation_namespace_facts(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    catalog: ProjectSemanticCatalog,
) -> tuple[dict[FromClause, ProjectSymbol], tuple[Diagnostic, ...]]:
    """Resolve top-level project relation namespace references."""

    relation_resolutions: dict[FromClause, ProjectSymbol] = {}
    diagnostics: list[Diagnostic] = []

    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue

            from_clause = definition.from_clause
            symbol = catalog.relation_symbols.get(from_clause.source_name)
            if symbol is None:
                diagnostics.append(_unknown_project_relation_diagnostic(from_clause))
                continue
            relation_resolutions[from_clause] = symbol

    return relation_resolutions, tuple(diagnostics)


def _build_project_relation_row_schemas(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema],
    relation_dependency_graph: ProjectRelationDependencyGraph,
) -> _ProjectRelationRowSchemasResult:
    """Build private relation row schemas for supported project projections."""

    relation_row_schemas: dict[TableDef | QueryDef, ProjectRowSchema] = {}
    relation_row_schema_states: dict[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ] = {}
    diagnostics: list[Diagnostic] = []
    cycle_relation_names = {
        node.symbol.name
        for cycle in relation_dependency_graph.cycles
        for node in cycle.nodes
    }
    relation_definitions = tuple(
        definition
        for parsed_input in parsed_inputs
        for definition in parsed_input.script.definitions
        if isinstance(definition, (TableDef, QueryDef))
    )

    for definition in relation_definitions:
        if definition.name in cycle_relation_names:
            _set_project_relation_row_schema_state(
                relation_row_schema_states,
                definition,
                status=ProjectRelationRowSchemaStatus.BLOCKED,
                schema=None,
                reason=ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
            )
            continue
        if definition.from_clause not in relation_resolutions:
            _set_project_relation_row_schema_state(
                relation_row_schema_states,
                definition,
                status=ProjectRelationRowSchemaStatus.BLOCKED,
                schema=None,
                reason=ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
            )
            continue
        if definition.group_by_clause is not None:
            _set_project_relation_row_schema_state(
                relation_row_schema_states,
                definition,
                status=ProjectRelationRowSchemaStatus.DEFERRED,
                schema=None,
                reason=ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR,
            )

    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue
            if definition in relation_row_schema_states:
                continue

            source_symbol = relation_resolutions.get(definition.from_clause)
            if (
                source_symbol is None
                or source_symbol.kind is not ProjectSymbolKind.SOURCE
            ):
                continue

            source = source_symbol.definition
            if not isinstance(source, SourceDef):
                continue

            source_schema = source_row_schemas.get(source)
            if source_schema is None:
                continue

            relation_schema_result = _project_direct_relation_row_schema(
                definition,
                source_schema=source_schema,
                source_symbol=source_symbol,
                upstream_definition=source,
                fallback_path=parsed_input.path,
            )
            diagnostics.extend(relation_schema_result.diagnostics)
            schema = relation_schema_result.schema
            _record_project_relation_row_schema_result(
                relation_row_schemas=relation_row_schemas,
                relation_row_schema_states=relation_row_schema_states,
                definition=definition,
                schema=schema,
                state_reason=relation_schema_result.state_reason,
                concrete_reason=(ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE),
            )

    definition_paths = {
        definition: parsed_input.path
        for parsed_input in parsed_inputs
        for definition in parsed_input.script.definitions
        if isinstance(definition, (TableDef, QueryDef))
    }
    while True:
        propagated = False
        for definition in relation_definitions:
            if definition in relation_row_schema_states:
                continue

            upstream_symbol = relation_resolutions.get(definition.from_clause)
            if upstream_symbol is None or upstream_symbol.kind not in (
                ProjectSymbolKind.TABLE,
                ProjectSymbolKind.QUERY,
            ):
                continue

            upstream_relation = upstream_symbol.definition
            if not isinstance(upstream_relation, (TableDef, QueryDef)):
                continue

            upstream_state = relation_row_schema_states.get(upstream_relation)
            if upstream_state is not None:
                if upstream_state.status is ProjectRelationRowSchemaStatus.UNKNOWN:
                    schema = ProjectRowSchema(is_unknown=True)
                    relation_row_schemas[definition] = schema
                    _set_project_relation_row_schema_state(
                        relation_row_schema_states,
                        definition,
                        status=ProjectRelationRowSchemaStatus.UNKNOWN,
                        schema=schema,
                        reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
                    )
                    propagated = True
                    continue
                if upstream_state.status is ProjectRelationRowSchemaStatus.DEFERRED:
                    _set_project_relation_row_schema_state(
                        relation_row_schema_states,
                        definition,
                        status=ProjectRelationRowSchemaStatus.DEFERRED,
                        schema=None,
                        reason=ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
                    )
                    propagated = True
                    continue
                if upstream_state.status is ProjectRelationRowSchemaStatus.BLOCKED:
                    _set_project_relation_row_schema_state(
                        relation_row_schema_states,
                        definition,
                        status=ProjectRelationRowSchemaStatus.BLOCKED,
                        schema=None,
                        reason=ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
                    )
                    propagated = True
                    continue

            upstream_schema = relation_row_schemas.get(upstream_relation)
            if upstream_schema is None:
                continue
            if upstream_schema.is_unknown:
                schema = ProjectRowSchema(is_unknown=True)
                relation_row_schemas[definition] = schema
                _set_project_relation_row_schema_state(
                    relation_row_schema_states,
                    definition,
                    status=ProjectRelationRowSchemaStatus.UNKNOWN,
                    schema=schema,
                    reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
                )
                propagated = True
                continue

            relation_schema_result = _project_direct_relation_row_schema(
                definition,
                source_schema=upstream_schema,
                source_symbol=upstream_symbol,
                upstream_definition=upstream_relation,
                upstream_state=upstream_state,
                fallback_path=definition_paths[definition],
            )
            diagnostics.extend(relation_schema_result.diagnostics)
            schema = relation_schema_result.schema
            _record_project_relation_row_schema_result(
                relation_row_schemas=relation_row_schemas,
                relation_row_schema_states=relation_row_schema_states,
                definition=definition,
                schema=schema,
                state_reason=relation_schema_result.state_reason,
                concrete_reason=(
                    ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
                ),
            )
            propagated = True
        if not propagated:
            break

    return _ProjectRelationRowSchemasResult(
        relation_row_schemas=relation_row_schemas,
        relation_row_schema_states=relation_row_schema_states,
        diagnostics=tuple(diagnostics),
    )


def _build_project_relation_let_scope_facts(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema],
    relation_row_schemas: Mapping[TableDef | QueryDef, ProjectRowSchema],
    relation_row_schema_states: Mapping[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
) -> dict[TableDef | QueryDef, ProjectRelationLetScopeFacts]:
    """Build private relation-local let scope facts for project relations."""

    from pietto._project.let_scope_facts import build_project_relation_let_scope_facts

    facts: dict[TableDef | QueryDef, ProjectRelationLetScopeFacts] = {}
    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue

            upstream_definition: SourceDef | TableDef | QueryDef | None = None
            input_schema: ProjectRowSchema | None = None
            upstream_state: ProjectRelationRowSchemaState | None = None
            upstream_symbol = relation_resolutions.get(definition.from_clause)
            if upstream_symbol is None:
                upstream_state = ProjectRelationRowSchemaState(
                    status=ProjectRelationRowSchemaStatus.BLOCKED,
                    schema=None,
                    reason=(ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED),
                )
            elif upstream_symbol.kind is ProjectSymbolKind.SOURCE and isinstance(
                upstream_symbol.definition, SourceDef
            ):
                upstream_definition = upstream_symbol.definition
                input_schema = source_row_schemas.get(upstream_definition)
            elif upstream_symbol.kind in (
                ProjectSymbolKind.TABLE,
                ProjectSymbolKind.QUERY,
            ) and isinstance(upstream_symbol.definition, (TableDef, QueryDef)):
                upstream_definition = upstream_symbol.definition
                upstream_state = relation_row_schema_states.get(upstream_definition)
                input_schema = relation_row_schemas.get(upstream_definition)

            facts[definition] = build_project_relation_let_scope_facts(
                definition=definition,
                input_schema=input_schema,
                upstream_definition=upstream_definition,
                upstream_state=upstream_state,
            )

    return facts


def _build_project_relation_row_dependency_graphs(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema],
    relation_row_schemas: Mapping[TableDef | QueryDef, ProjectRowSchema],
    relation_row_schema_states: Mapping[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
    relation_let_scope_facts: Mapping[
        TableDef | QueryDef, ProjectRelationLetScopeFacts
    ],
) -> dict[TableDef | QueryDef, ProjectRelationRowDependencyGraph]:
    """Build private row-level dependency graphs for project relations."""

    from pietto._project.row_dependency_graph import (
        build_project_relation_row_dependency_graphs,
    )

    return build_project_relation_row_dependency_graphs(
        parsed_inputs=parsed_inputs,
        relation_resolutions=relation_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        relation_row_schema_states=relation_row_schema_states,
        relation_let_scope_facts=relation_let_scope_facts,
    )


def _record_project_relation_row_schema_result(
    *,
    relation_row_schemas: dict[TableDef | QueryDef, ProjectRowSchema],
    relation_row_schema_states: dict[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
    definition: TableDef | QueryDef,
    schema: ProjectRowSchema | None,
    state_reason: ProjectRelationRowSchemaReason | None,
    concrete_reason: ProjectRelationRowSchemaReason,
) -> None:
    """Record one private relation row schema and availability state."""

    if schema is None:
        _set_project_relation_row_schema_state(
            relation_row_schema_states,
            definition,
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=(
                state_reason or ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
            ),
        )
        return

    relation_row_schemas[definition] = schema
    if schema.is_unknown:
        _set_project_relation_row_schema_state(
            relation_row_schema_states,
            definition,
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            schema=schema,
            reason=state_reason or ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        )
        return

    _set_project_relation_row_schema_state(
        relation_row_schema_states,
        definition,
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=schema,
        reason=concrete_reason,
    )


def _set_project_relation_row_schema_state(
    relation_row_schema_states: dict[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
    definition: TableDef | QueryDef,
    *,
    status: ProjectRelationRowSchemaStatus,
    schema: ProjectRowSchema | None,
    reason: ProjectRelationRowSchemaReason,
) -> None:
    """Set one private relation row schema availability state."""

    relation_row_schema_states[definition] = ProjectRelationRowSchemaState(
        status=status,
        schema=schema,
        reason=reason,
    )


def _project_direct_relation_row_schema(
    definition: TableDef | QueryDef,
    *,
    source_schema: ProjectRowSchema,
    source_symbol: ProjectSymbol,
    upstream_definition: SourceDef | TableDef | QueryDef,
    upstream_state: ProjectRelationRowSchemaState | None = None,
    fallback_path: str,
) -> _ProjectRelationRowSchemaResult:
    """Project direct fields and supported computed aliases from one input."""

    from pietto._project.let_scope_facts import (
        ProjectLetScopeFactsStatus,
        build_project_relation_let_scope_facts,
    )
    from pietto._project.row_expression_schema import (
        ProjectExpressionSchemaOriginKind,
        ProjectExpressionSchemaStatus,
        adapt_project_row_expression_schema,
    )
    from pietto._project.row_expression_type_facts import (
        build_project_row_expression_value_types,
    )

    fields: dict[str, ProjectRowField] = {}
    diagnostics: list[Diagnostic] = []
    is_unknown = False
    unknown_reason: ProjectRelationRowSchemaReason | None = None
    if source_schema.is_unknown:
        return _ProjectRelationRowSchemaResult(
            schema=ProjectRowSchema(is_unknown=True),
            state_reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        )

    expression_value_types = build_project_row_expression_value_types(
        expressions=(
            item.expression
            for item in definition.select_items
            if item.alias is not None
        ),
        input_schema=source_schema,
        relation_qualifier=definition.from_clause.source_name,
    )
    let_scope_facts = build_project_relation_let_scope_facts(
        definition=definition,
        input_schema=source_schema,
        upstream_definition=upstream_definition,
        upstream_state=upstream_state,
    )
    let_value_types = (
        let_scope_facts.value_types
        if let_scope_facts.status is ProjectLetScopeFactsStatus.CONCRETE
        else None
    )

    for item in definition.select_items:
        projection = _project_direct_field_projection(
            item,
            source_name=definition.from_clause.source_name,
            fallback_path=fallback_path,
        )
        if projection.status is _ProjectDirectFieldProjectionStatus.DEFERRED:
            if item.alias is None:
                return _ProjectRelationRowSchemaResult(
                    schema=None,
                    state_reason=(
                        ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
                    ),
                )

            result = adapt_project_row_expression_schema(
                expression=item.expression,
                output_name=item.alias,
                input_schema=source_schema,
                upstream_state=None,
                relation_qualifier=definition.from_clause.source_name,
                expression_value_types=expression_value_types,
                fallback_path=fallback_path,
            )
            if result.status is not ProjectExpressionSchemaStatus.CONCRETE:
                return _ProjectRelationRowSchemaResult(
                    schema=None,
                    state_reason=(
                        ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
                    ),
                )

            if item.alias in fields:
                is_unknown = True
                unknown_reason = (
                    unknown_reason
                    or ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
                )
                continue

            if result.resolved_type is None or result.nullability is None:
                raise AssertionError("Concrete computed projection requires type facts")

            fields[item.alias] = ProjectRowField(
                name=item.alias,
                resolved_type=result.resolved_type,
                nullability=result.nullability,
                field_def=None,
                provenance=ProjectRowFieldProvenance(
                    kind=ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION,
                    symbol=source_symbol,
                    location=result.location,
                ),
            )
            continue

        if projection.status is _ProjectDirectFieldProjectionStatus.INVALID:
            diagnostics.append(_project_unknown_direct_field_diagnostic(projection))
            is_unknown = True
            unknown_reason = ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA
            continue

        output_name = projection.output_name
        lookup_name = projection.lookup_name
        if output_name is None or lookup_name is None:
            raise AssertionError("Supported direct projection requires field names")

        if output_name in fields:
            is_unknown = True
            unknown_reason = (
                unknown_reason or ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
            )
            continue

        source_field = source_schema.fields.get(lookup_name)
        if source_field is None:
            result = adapt_project_row_expression_schema(
                expression=item.expression,
                output_name=output_name,
                input_schema=source_schema,
                upstream_state=upstream_state,
                relation_qualifier=definition.from_clause.source_name,
                expression_value_types=expression_value_types,
                let_value_types=let_value_types,
                fallback_path=fallback_path,
            )
            if (
                result.status is ProjectExpressionSchemaStatus.CONCRETE
                and result.origin is ProjectExpressionSchemaOriginKind.LET_DERIVED
            ):
                if result.resolved_type is None or result.nullability is None:
                    raise AssertionError(
                        "Concrete let-derived projection requires type facts"
                    )

                fields[output_name] = ProjectRowField(
                    name=output_name,
                    resolved_type=result.resolved_type,
                    nullability=result.nullability,
                    field_def=None,
                    provenance=ProjectRowFieldProvenance(
                        kind=ProjectRowFieldProvenanceKind.LET_DERIVED,
                        symbol=source_symbol,
                        location=result.location,
                    ),
                )
                continue

            diagnostics.append(_project_unknown_direct_field_diagnostic(projection))
            is_unknown = True
            unknown_reason = ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA
            continue

        fields[output_name] = ProjectRowField(
            name=output_name,
            resolved_type=source_field.resolved_type,
            nullability=source_field.nullability,
            field_def=source_field.field_def,
            provenance=ProjectRowFieldProvenance(
                kind=ProjectRowFieldProvenanceKind.DIRECT_PROJECTION,
                symbol=source_symbol,
                location=projection.location,
            ),
        )

    if is_unknown or diagnostics:
        return _ProjectRelationRowSchemaResult(
            schema=ProjectRowSchema(is_unknown=True),
            diagnostics=tuple(diagnostics),
            state_reason=unknown_reason
            or ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        )

    return _ProjectRelationRowSchemaResult(schema=ProjectRowSchema(fields=fields))


def _project_direct_field_projection(
    item: SelectItem,
    *,
    source_name: str,
    fallback_path: str,
) -> _ProjectDirectFieldProjection:
    """Decode one direct field projection or direct field rename candidate."""

    expression = item.expression
    if isinstance(expression, NameExpr):
        lookup_name = expression.name
        return _ProjectDirectFieldProjection(
            status=_ProjectDirectFieldProjectionStatus.SUPPORTED,
            output_name=item.alias or lookup_name,
            lookup_name=lookup_name,
            field_text=lookup_name,
            location=_project_expression_location(
                expression,
                fallback_path=fallback_path,
            ),
        )
    if isinstance(expression, DottedNameExpr):
        if len(expression.parts) != 2 or expression.parts[0] != source_name:
            return _ProjectDirectFieldProjection(
                status=_ProjectDirectFieldProjectionStatus.INVALID,
                field_text=_project_dotted_field_text(expression),
                location=_project_expression_location(
                    expression,
                    fallback_path=fallback_path,
                ),
            )
        field_name = expression.parts[1]
        return _ProjectDirectFieldProjection(
            status=_ProjectDirectFieldProjectionStatus.SUPPORTED,
            output_name=item.alias or field_name,
            lookup_name=field_name,
            field_text=_project_dotted_field_text(expression),
            location=_project_expression_location(
                expression,
                fallback_path=fallback_path,
            ),
        )

    return _ProjectDirectFieldProjection(
        status=_ProjectDirectFieldProjectionStatus.DEFERRED
    )


def _project_dotted_field_text(expression: DottedNameExpr) -> str:
    """Return the user-facing dotted field reference text."""

    return ".".join(expression.parts)


def _build_project_type_namespace_facts(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    catalog: ProjectSemanticCatalog,
) -> tuple[
    dict[TypeExpr, ProjectResolvedType],
    dict[SourceDef, ProjectSymbol],
    tuple[Diagnostic, ...],
]:
    """Resolve top-level project type namespace references."""

    type_resolutions: dict[TypeExpr, ProjectResolvedType] = {}
    source_shape_resolutions: dict[SourceDef, ProjectSymbol] = {}
    diagnostics: list[Diagnostic] = []

    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            for type_expr in _iter_project_type_expressions(definition):
                resolved_type = _resolve_project_type(type_expr, catalog)
                type_resolutions[type_expr] = resolved_type
                if resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN:
                    diagnostics.append(_unknown_project_type_diagnostic(type_expr))

            if isinstance(definition, SourceDef):
                symbol, diagnostic = _resolve_project_source_shape(
                    definition,
                    catalog,
                )
                if symbol is not None:
                    source_shape_resolutions[definition] = symbol
                if diagnostic is not None:
                    diagnostics.append(diagnostic)

    return type_resolutions, source_shape_resolutions, tuple(diagnostics)


def _build_project_source_row_schemas(
    *,
    source_shape_resolutions: Mapping[SourceDef, ProjectSymbol],
    type_resolutions: Mapping[TypeExpr, ProjectResolvedType],
) -> dict[SourceDef, ProjectRowSchema]:
    """Build private source row schemas from already-resolved source shapes."""

    source_row_schemas: dict[SourceDef, ProjectRowSchema] = {}
    for source, shape_symbol in source_shape_resolutions.items():
        shape = shape_symbol.definition
        if not isinstance(shape, ShapeDef):
            continue

        fields: dict[str, ProjectRowField] = {}
        skip_schema = False
        for field_def in shape.fields:
            resolved_type = type_resolutions.get(field_def.type_expr)
            if (
                resolved_type is None
                or resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN
            ):
                skip_schema = True
                break
            if field_def.name in fields:
                continue
            fields[field_def.name] = ProjectRowField(
                name=field_def.name,
                resolved_type=resolved_type,
                nullability=_project_row_field_nullability(field_def.type_expr),
                field_def=field_def,
                provenance=ProjectRowFieldProvenance(
                    kind=ProjectRowFieldProvenanceKind.SOURCE_FIELD,
                    symbol=shape_symbol,
                    location=_project_field_location(
                        field_def,
                        fallback_path=shape_symbol.path,
                    ),
                ),
            )
        if not skip_schema:
            source_row_schemas[source] = ProjectRowSchema(fields=fields)

    return source_row_schemas


def _project_row_field_nullability(
    type_expr: TypeExpr,
) -> ProjectRowFieldNullability:
    """Map parsed type nullability to project-private row field nullability."""

    if type_expr.nullability is Nullability.NOT_NULL:
        return ProjectRowFieldNullability.NON_NULL
    if type_expr.nullability is Nullability.NULLABLE:
        return ProjectRowFieldNullability.NULLABLE
    return ProjectRowFieldNullability.UNKNOWN


def _project_field_location(
    field_def: FieldDef,
    *,
    fallback_path: str,
) -> SourceLocation:
    """Convert one shape field span into a private project source location."""

    span = field_def.span
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _project_expression_location(
    expression: NameExpr | DottedNameExpr,
    *,
    fallback_path: str,
) -> SourceLocation:
    """Convert one projection expression span into a private project location."""

    span = expression.span
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _iter_project_type_expressions(definition: Definition) -> tuple[TypeExpr, ...]:
    """Return supported top-level type expressions in source order."""

    if isinstance(definition, TypeDef):
        return (definition.base,)
    if isinstance(definition, (ConstraintDef, DeriveDef)):
        return tuple(parameter.type for parameter in definition.parameters) + (
            definition.return_type,
        )
    if isinstance(definition, ShapeDef):
        return tuple(field.type_expr for field in definition.fields)
    return ()


def _resolve_project_type(
    type_expr: TypeExpr,
    catalog: ProjectSemanticCatalog,
) -> ProjectResolvedType:
    """Resolve one project type reference without alias expansion."""

    if type_expr.name in _PROJECT_BUILTIN_TYPE_NAMES:
        return ProjectResolvedType(
            name=type_expr.name,
            kind=ProjectResolvedTypeKind.BUILTIN,
        )

    symbol = catalog.type_symbols.get(type_expr.name)
    if symbol is None:
        return ProjectResolvedType(
            name=type_expr.name,
            kind=ProjectResolvedTypeKind.UNKNOWN,
        )

    if symbol.kind is ProjectSymbolKind.TYPE_ALIAS:
        kind = ProjectResolvedTypeKind.TYPE_ALIAS
    elif symbol.kind is ProjectSymbolKind.ENUM:
        kind = ProjectResolvedTypeKind.ENUM
    elif symbol.kind is ProjectSymbolKind.SHAPE:
        kind = ProjectResolvedTypeKind.SHAPE
    else:
        raise AssertionError(f"Unsupported project type symbol kind: {symbol.kind}")
    return ProjectResolvedType(name=type_expr.name, kind=kind, symbol=symbol)


def _resolve_project_source_shape(
    source: SourceDef,
    catalog: ProjectSemanticCatalog,
) -> tuple[ProjectSymbol | None, Diagnostic | None]:
    """Resolve a source shape binding against the project type namespace."""

    if source.shape_name is None:
        return None, None

    symbol = catalog.type_symbols.get(source.shape_name)
    if symbol is None:
        return None, _project_source_shape_diagnostic(
            source,
            message=f"Unknown source shape: {source.shape_name}",
        )
    if symbol.kind is not ProjectSymbolKind.SHAPE:
        return None, _project_source_shape_diagnostic(
            source,
            message=f"Source shape must refer to a shape: {source.shape_name}",
        )
    return symbol, None


def _build_project_semantic_catalog(
    parsed_inputs: tuple[ProjectParsedInput, ...],
) -> tuple[ProjectSemanticCatalog, tuple[Diagnostic, ...]]:
    """Collect deterministic top-level project symbols before resolution."""

    type_symbols: dict[str, ProjectSymbol] = {}
    relation_symbols: dict[str, ProjectSymbol] = {}
    callable_symbols: dict[str, ProjectSymbol] = {}
    diagnostics: list[Diagnostic] = []

    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            symbol = _project_symbol(parsed_input, definition)
            namespace = _symbol_map(
                symbol,
                type_symbols=type_symbols,
                relation_symbols=relation_symbols,
                callable_symbols=callable_symbols,
            )
            if symbol.name in namespace:
                diagnostics.append(_duplicate_project_symbol_diagnostic(symbol))
                continue
            namespace[symbol.name] = symbol

    return (
        ProjectSemanticCatalog(
            type_symbols=type_symbols,
            relation_symbols=relation_symbols,
            callable_symbols=callable_symbols,
        ),
        tuple(diagnostics),
    )


def _project_symbol(
    parsed_input: ProjectParsedInput,
    definition: Definition,
) -> ProjectSymbol:
    """Create one private project symbol for a top-level definition."""

    namespace, kind = _classify_project_definition(definition)
    location = _definition_location(definition, path=parsed_input.path)
    return ProjectSymbol(
        namespace=namespace,
        kind=kind,
        name=definition.name,
        path=parsed_input.path,
        location=location,
        definition=definition,
    )


def _classify_project_definition(
    definition: Definition,
) -> tuple[ProjectSymbolNamespace, ProjectSymbolKind]:
    """Classify a top-level definition into the Phase 45 hybrid namespace."""

    if isinstance(definition, TypeDef):
        return ProjectSymbolNamespace.TYPE, ProjectSymbolKind.TYPE_ALIAS
    if isinstance(definition, EnumDef):
        return ProjectSymbolNamespace.TYPE, ProjectSymbolKind.ENUM
    if isinstance(definition, ShapeDef):
        return ProjectSymbolNamespace.TYPE, ProjectSymbolKind.SHAPE
    if isinstance(definition, SourceDef):
        return ProjectSymbolNamespace.RELATION, ProjectSymbolKind.SOURCE
    if isinstance(definition, TableDef):
        return ProjectSymbolNamespace.RELATION, ProjectSymbolKind.TABLE
    if isinstance(definition, QueryDef):
        return ProjectSymbolNamespace.RELATION, ProjectSymbolKind.QUERY
    if isinstance(definition, ConstraintDef):
        return ProjectSymbolNamespace.CALLABLE, ProjectSymbolKind.CONSTRAINT
    if isinstance(definition, DeriveDef):
        return ProjectSymbolNamespace.CALLABLE, ProjectSymbolKind.DERIVE
    raise AssertionError(f"Unsupported project definition: {type(definition).__name__}")


def _symbol_map(
    symbol: ProjectSymbol,
    *,
    type_symbols: dict[str, ProjectSymbol],
    relation_symbols: dict[str, ProjectSymbol],
    callable_symbols: dict[str, ProjectSymbol],
) -> dict[str, ProjectSymbol]:
    """Return the mutable catalog map for a classified project symbol."""

    if symbol.namespace is ProjectSymbolNamespace.TYPE:
        return type_symbols
    if symbol.namespace is ProjectSymbolNamespace.RELATION:
        return relation_symbols
    if symbol.namespace is ProjectSymbolNamespace.CALLABLE:
        return callable_symbols
    raise AssertionError(f"Unsupported project namespace: {symbol.namespace}")


def _definition_location(definition: Definition, *, path: str) -> SourceLocation:
    """Convert a top-level definition span into a project diagnostic location."""

    span = definition.span
    return SourceLocation(
        path=span.path or path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _duplicate_project_symbol_diagnostic(symbol: ProjectSymbol) -> Diagnostic:
    """Report a duplicate at the later project definition's complete span."""

    return Diagnostic(
        code="PIE-S2001",
        severity=Severity.ERROR,
        message=(
            "Duplicate symbol name in "
            f"{symbol.namespace.value} namespace: {symbol.name}"
        ),
        location=symbol.location,
    )


def _unknown_project_type_diagnostic(type_expr: TypeExpr) -> Diagnostic:
    """Report an unresolved project type name at the type expression span."""

    span = type_expr.span
    return Diagnostic(
        code="PIE-S2002",
        severity=Severity.ERROR,
        message=f"Unknown type: {type_expr.name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _project_source_shape_diagnostic(
    source: SourceDef,
    *,
    message: str,
) -> Diagnostic:
    """Report an invalid project source shape binding."""

    span = source.span
    return Diagnostic(
        code="PIE-S2303",
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


def _unknown_project_relation_diagnostic(from_clause: FromClause) -> Diagnostic:
    """Report an unresolved project relation input at the from-clause span."""

    span = from_clause.span
    return Diagnostic(
        code="PIE-S2301",
        severity=Severity.ERROR,
        message=f"Unknown relation: {from_clause.source_name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _project_unknown_direct_field_diagnostic(
    projection: _ProjectDirectFieldProjection,
) -> Diagnostic:
    """Report an unknown direct field reference at its expression span."""

    if projection.field_text is None or projection.location is None:
        raise AssertionError("Unknown direct field diagnostic requires field text")

    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=f"Unknown field: {projection.field_text}",
        location=projection.location,
    )
