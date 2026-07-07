"""Private immutable models for project discovery and configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar

from pietto.ast_nodes import (
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    FromClause,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
    TypeExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

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
            relation_resolutions=relation_resolutions,
            relation_dependency_graph=relation_dependency_graph,
        ),
        diagnostics=(*type_diagnostics, *relation_diagnostics, *cycle_diagnostics),
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
