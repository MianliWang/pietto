"""Private schema-v2 module graph and public diagnostic adaptation."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import json
from types import MappingProxyType

from pietto._project.module_bindings import (
    ProjectModuleBindingEnvironmentSet,
    ProjectModuleBindingIssue,
    ProjectModuleBindingIssueStatus,
    ProjectModuleImportRequest,
)
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.module_exports import (
    ProjectModuleExportIssue,
    ProjectModuleExportIssueStatus,
    ProjectModuleExportRequest,
    ProjectModuleExportSurfaceSet,
)
from pietto._project.selected_input_index import ProjectSelectedInputIndex
from pietto.ast_nodes import Span
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleGraphVertex:
    """One selected explicit-module graph vertex."""

    identity: ProjectModuleIdentity
    position: int
    module: ProjectLogicalModule = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Reject a vertex detached from its selected logical module."""

        if type(self.identity) is not ProjectModuleIdentity:
            raise TypeError("Module graph vertex requires a module identity.")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("Module graph vertex position must be non-negative.")
        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Module graph vertex requires a logical module.")
        if (
            self.module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or self.module.identity != self.identity
            or self.module.position != self.position
            or self.module.parsed_input is None
        ):
            raise ValueError("Module graph vertex must match one parsed module.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleImportEvidenceEdge:
    """One source import request proving one selected dependency."""

    origin: ProjectModuleGraphVertex
    target: ProjectModuleGraphVertex
    request: ProjectModuleImportRequest

    def __post_init__(self) -> None:
        """Reject evidence that rewrites either endpoint."""

        if (
            type(self.origin) is not ProjectModuleGraphVertex
            or type(self.target) is not ProjectModuleGraphVertex
        ):
            raise TypeError("Module evidence edge requires graph vertices.")
        if type(self.request) is not ProjectModuleImportRequest:
            raise TypeError("Module evidence edge requires an import request.")
        if (
            self.request.identity.owning_module_path != self.origin.identity.path
            or self.request.target_module_path != self.target.identity.path
        ):
            raise ValueError("Module evidence edge must retain exact endpoints.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleDependencyEdge:
    """One canonical origin-target dependency with complete evidence."""

    origin: ProjectModuleGraphVertex
    target: ProjectModuleGraphVertex
    evidence_edges: tuple[ProjectModuleImportEvidenceEdge, ...]

    def __post_init__(self) -> None:
        """Require a complete source-ordered evidence bucket."""

        if (
            type(self.origin) is not ProjectModuleGraphVertex
            or type(self.target) is not ProjectModuleGraphVertex
        ):
            raise TypeError("Module dependency edge requires graph vertices.")
        _require_tuple_items(
            self.evidence_edges,
            ProjectModuleImportEvidenceEdge,
            "Module dependency evidence",
        )
        if not self.evidence_edges:
            raise ValueError("Module dependency edge requires source evidence.")
        if any(
            item.origin != self.origin or item.target != self.target
            for item in self.evidence_edges
        ):
            raise ValueError("Module dependency evidence must match its endpoints.")
        keys = tuple(_request_source_key(item.request) for item in self.evidence_edges)
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise ValueError("Module dependency evidence must be unique and ordered.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleStronglyConnectedComponent:
    """One canonical selected-order strongly connected component."""

    members: tuple[ProjectModuleGraphVertex, ...]
    internal_edges: tuple[ProjectModuleDependencyEdge, ...] = ()

    def __post_init__(self) -> None:
        """Reject empty, reordered, or externally connected components."""

        _require_tuple_items(
            self.members,
            ProjectModuleGraphVertex,
            "Module component members",
        )
        _require_tuple_items(
            self.internal_edges,
            ProjectModuleDependencyEdge,
            "Module component edges",
        )
        if not self.members:
            raise ValueError("Module component requires at least one member.")
        positions = tuple(member.position for member in self.members)
        if positions != tuple(sorted(positions)) or len(set(positions)) != len(
            positions
        ):
            raise ValueError("Module component members must be selected ordered.")
        member_set = set(self.members)
        if any(
            edge.origin not in member_set or edge.target not in member_set
            for edge in self.internal_edges
        ):
            raise ValueError("Module component edges must be internal.")
        edge_keys = tuple(_dependency_edge_key(edge) for edge in self.internal_edges)
        if edge_keys != tuple(sorted(edge_keys)) or len(set(edge_keys)) != len(
            edge_keys
        ):
            raise ValueError("Module component edges must be canonical ordered.")

    @property
    def is_cyclic(self) -> bool:
        """Return whether this component proves a cycle."""

        return len(self.members) > 1 or any(
            edge.origin == edge.target for edge in self.internal_edges
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleCycleWitness:
    """One canonical simple cycle witness without a repeated closing vertex."""

    vertices: tuple[ProjectModuleGraphVertex, ...]
    edges: tuple[ProjectModuleDependencyEdge, ...]

    def __post_init__(self) -> None:
        """Require a closed endpoint-exact cycle."""

        _require_tuple_items(
            self.vertices,
            ProjectModuleGraphVertex,
            "Module cycle witness vertices",
        )
        _require_tuple_items(
            self.edges,
            ProjectModuleDependencyEdge,
            "Module cycle witness edges",
        )
        if not self.vertices or len(self.vertices) != len(self.edges):
            raise ValueError("Module cycle witness requires equal non-empty tuples.")
        if len(set(self.vertices)) != len(self.vertices):
            raise ValueError("Module cycle witness vertices must be unique.")
        for position, edge in enumerate(self.edges):
            if (
                edge.origin != self.vertices[position]
                or edge.target != self.vertices[(position + 1) % len(self.vertices)]
            ):
                raise ValueError("Module cycle witness edges must close exactly.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleCycle:
    """One cyclic SCC and its canonical witness."""

    component: ProjectModuleStronglyConnectedComponent
    witness: ProjectModuleCycleWitness

    def __post_init__(self) -> None:
        """Reject a witness outside its cyclic component."""

        if type(self.component) is not ProjectModuleStronglyConnectedComponent:
            raise TypeError("Module cycle requires a component.")
        if type(self.witness) is not ProjectModuleCycleWitness:
            raise TypeError("Module cycle requires a witness.")
        if not self.component.is_cyclic or not set(self.witness.vertices) <= set(
            self.component.members
        ):
            raise ValueError("Module cycle witness must belong to a cyclic component.")
        if any(
            edge not in self.component.internal_edges for edge in self.witness.edges
        ):
            raise ValueError("Module cycle witness edges must belong to its component.")


class ProjectModuleGraphIssueStatus(StrEnum):
    """Closed graph-only issue categories for diagnostic adaptation."""

    UNRESOLVED_TARGET_MODULE = "unresolved_target_module"
    DUPLICATE_OR_CONFLICTING_MODULE_IDENTITY = (
        "duplicate_or_conflicting_module_identity"
    )
    MODULE_IMPORT_CYCLE = "module_import_cycle"
    UNSUPPORTED_EXPLICIT_MODULE_REFERENCE = "unsupported_explicit_module_reference"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleGraphIssue:
    """One graph issue with complete retained source evidence."""

    status: ProjectModuleGraphIssueStatus
    owning_vertex: ProjectModuleGraphVertex
    requests: tuple[ProjectModuleImportRequest, ...] = ()
    cycle: ProjectModuleCycle | None = None
    conflicting_vertices: tuple[ProjectModuleGraphVertex, ...] = ()
    binding_issues: tuple[ProjectModuleBindingIssue, ...] = ()

    def __post_init__(self) -> None:
        """Reject evidence that cannot prove the selected status."""

        if type(self.status) is not ProjectModuleGraphIssueStatus:
            raise TypeError("Module graph issue requires an exact status.")
        if type(self.owning_vertex) is not ProjectModuleGraphVertex:
            raise TypeError("Module graph issue requires an owning vertex.")
        _require_tuple_items(
            self.requests,
            ProjectModuleImportRequest,
            "Module graph issue requests",
        )
        _require_tuple_items(
            self.conflicting_vertices,
            ProjectModuleGraphVertex,
            "Module graph issue conflicting vertices",
        )
        _require_tuple_items(
            self.binding_issues,
            ProjectModuleBindingIssue,
            "Module graph issue binding issues",
        )
        if self.cycle is not None and type(self.cycle) is not ProjectModuleCycle:
            raise TypeError("Module graph issue cycle must be exact.")

        if self.status is ProjectModuleGraphIssueStatus.UNRESOLVED_TARGET_MODULE:
            valid = (
                bool(self.requests)
                and self.cycle is None
                and not self.conflicting_vertices
                and bool(self.binding_issues)
                and all(
                    request.identity.owning_module_path
                    == self.owning_vertex.identity.path
                    and request.target_module_path
                    == self.requests[0].target_module_path
                    and request.module_statement_position
                    == self.requests[0].module_statement_position
                    for request in self.requests
                )
                and all(
                    issue.status
                    is ProjectModuleBindingIssueStatus.UNRESOLVED_TARGET_MODULE
                    and issue.request in self.requests
                    for issue in self.binding_issues
                )
            )
        elif (
            self.status
            is ProjectModuleGraphIssueStatus.DUPLICATE_OR_CONFLICTING_MODULE_IDENTITY
        ):
            valid = (
                not self.requests
                and self.cycle is None
                and len(self.conflicting_vertices) > 1
                and not self.binding_issues
                and all(
                    vertex.identity == self.owning_vertex.identity
                    for vertex in self.conflicting_vertices
                )
            )
        elif self.status is ProjectModuleGraphIssueStatus.MODULE_IMPORT_CYCLE:
            valid = (
                not self.requests
                and self.cycle is not None
                and self.owning_vertex == self.cycle.component.members[0]
                and not self.conflicting_vertices
                and not self.binding_issues
            )
        else:
            valid = (
                bool(self.requests)
                and self.cycle is None
                and not self.conflicting_vertices
                and not self.binding_issues
                and all(
                    request.identity.owning_module_path
                    == self.owning_vertex.identity.path
                    for request in self.requests
                )
            )
        if not valid:
            raise ValueError("Module graph issue evidence must prove its status.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleGraph:
    """The complete deterministic selected-module dependency graph."""

    vertices: tuple[ProjectModuleGraphVertex, ...] = ()
    evidence_edges: tuple[ProjectModuleImportEvidenceEdge, ...] = ()
    edges: tuple[ProjectModuleDependencyEdge, ...] = ()
    components: tuple[ProjectModuleStronglyConnectedComponent, ...] = ()
    cycles: tuple[ProjectModuleCycle, ...] = ()
    issues: tuple[ProjectModuleGraphIssue, ...] = ()
    _vertices_by_path: Mapping[str, ProjectModuleGraphVertex] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    _outgoing_by_vertex: Mapping[
        ProjectModuleGraphVertex,
        tuple[ProjectModuleDependencyEdge, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Validate total coverage, canonical order, and copied lookups."""

        _require_tuple_items(
            self.vertices,
            ProjectModuleGraphVertex,
            "Module graph vertices",
        )
        _require_tuple_items(
            self.evidence_edges,
            ProjectModuleImportEvidenceEdge,
            "Module graph evidence edges",
        )
        _require_tuple_items(
            self.edges,
            ProjectModuleDependencyEdge,
            "Module graph dependency edges",
        )
        _require_tuple_items(
            self.components,
            ProjectModuleStronglyConnectedComponent,
            "Module graph components",
        )
        _require_tuple_items(self.cycles, ProjectModuleCycle, "Module graph cycles")
        _require_tuple_items(
            self.issues,
            ProjectModuleGraphIssue,
            "Module graph issues",
        )
        if tuple(vertex.position for vertex in self.vertices) != tuple(
            range(len(self.vertices))
        ):
            raise ValueError("Module graph vertices must retain selected order.")
        if len({vertex.identity for vertex in self.vertices}) != len(self.vertices):
            raise ValueError("Module graph vertex identities must be unique.")
        vertex_set = set(self.vertices)
        evidence_keys = tuple(_evidence_edge_key(edge) for edge in self.evidence_edges)
        if evidence_keys != tuple(sorted(evidence_keys)) or len(
            set(evidence_keys)
        ) != len(evidence_keys):
            raise ValueError("Module graph evidence must be source ordered.")
        if any(
            edge.origin not in vertex_set or edge.target not in vertex_set
            for edge in self.evidence_edges
        ):
            raise ValueError("Module graph evidence endpoints must be vertices.")
        edge_keys = tuple(_dependency_edge_key(edge) for edge in self.edges)
        if edge_keys != tuple(sorted(edge_keys)) or len(set(edge_keys)) != len(
            edge_keys
        ):
            raise ValueError("Module graph edges must be canonical ordered.")
        expected_buckets = {
            (origin, target): tuple(
                evidence
                for evidence in self.evidence_edges
                if evidence.origin == origin and evidence.target == target
            )
            for origin, target in ((edge.origin, edge.target) for edge in self.edges)
        }
        if any(
            edge.evidence_edges != expected_buckets[(edge.origin, edge.target)]
            for edge in self.edges
        ):
            raise ValueError("Module graph canonical edges require complete evidence.")

        component_members = tuple(
            member for component in self.components for member in component.members
        )
        if set(component_members) != vertex_set or len(component_members) != len(
            vertex_set
        ):
            raise ValueError("Module graph components must partition all vertices.")
        component_keys = tuple(
            component.members[0].position for component in self.components
        )
        if component_keys != tuple(sorted(component_keys)):
            raise ValueError("Module graph components must be canonical ordered.")
        expected_cycles = tuple(
            component for component in self.components if component.is_cyclic
        )
        if tuple(cycle.component for cycle in self.cycles) != expected_cycles:
            raise ValueError("Module graph cycles must cover every cyclic component.")
        issue_keys = tuple(_graph_issue_order(issue) for issue in self.issues)
        if issue_keys != tuple(sorted(issue_keys)):
            raise ValueError("Module graph issues must be deterministic ordered.")

        vertices_by_path = {vertex.identity.path: vertex for vertex in self.vertices}
        outgoing_by_vertex = {
            vertex: tuple(edge for edge in self.edges if edge.origin == vertex)
            for vertex in self.vertices
        }
        object.__setattr__(
            self,
            "_vertices_by_path",
            MappingProxyType(dict(vertices_by_path)),
        )
        object.__setattr__(
            self,
            "_outgoing_by_vertex",
            MappingProxyType(dict(outgoing_by_vertex)),
        )

    def find_path(self, module_path: str) -> tuple[ProjectModuleGraphVertex, ...]:
        """Return one exact selected vertex, or an empty tuple."""

        try:
            ProjectModuleIdentity(path=module_path)
        except (TypeError, ValueError):
            return ()
        vertex = self._vertices_by_path.get(module_path)
        return () if vertex is None else (vertex,)

    def outgoing(
        self,
        vertex: ProjectModuleGraphVertex,
    ) -> tuple[ProjectModuleDependencyEdge, ...]:
        """Return canonical target-ordered outgoing dependencies."""

        if type(vertex) is not ProjectModuleGraphVertex:
            raise TypeError("Module graph adjacency lookup requires a vertex.")
        return self._outgoing_by_vertex.get(vertex, ())


class ProjectModuleDiagnosticOrigin(StrEnum):
    """The exact private structured source of one public diagnostic."""

    GRAPH = "graph"
    EXPORT = "export"
    BINDING = "binding"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleDiagnosticFact:
    """One ordered public diagnostic plus complete private source evidence."""

    origin: ProjectModuleDiagnosticOrigin
    diagnostic: Diagnostic
    module_position: int
    module_statement_position: int | None
    item_position: int | None
    related_locations: tuple[SourceLocation, ...] = ()
    graph_issues: tuple[ProjectModuleGraphIssue, ...] = ()
    export_issues: tuple[ProjectModuleExportIssue, ...] = ()
    binding_issues: tuple[ProjectModuleBindingIssue, ...] = ()

    def __post_init__(self) -> None:
        """Reject unstructured, multi-origin, or unordered evidence."""

        if type(self.origin) is not ProjectModuleDiagnosticOrigin:
            raise TypeError("Module diagnostic fact requires an exact origin.")
        if type(self.diagnostic) is not Diagnostic:
            raise TypeError("Module diagnostic fact requires a Diagnostic.")
        if type(self.module_position) is not int or self.module_position < 0:
            raise ValueError("Module diagnostic position must be non-negative.")
        for value in (self.module_statement_position, self.item_position):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Module diagnostic source positions must be valid.")
        _require_tuple_items(
            self.related_locations,
            SourceLocation,
            "Module diagnostic related locations",
        )
        _require_tuple_items(
            self.graph_issues,
            ProjectModuleGraphIssue,
            "Module diagnostic graph issues",
        )
        _require_tuple_items(
            self.export_issues,
            ProjectModuleExportIssue,
            "Module diagnostic export issues",
        )
        _require_tuple_items(
            self.binding_issues,
            ProjectModuleBindingIssue,
            "Module diagnostic binding issues",
        )
        evidence_counts = tuple(
            bool(values)
            for values in (
                self.graph_issues,
                self.export_issues,
                self.binding_issues,
            )
        )
        if sum(evidence_counts) != 1:
            raise ValueError("Module diagnostic fact requires one structured origin.")
        expected_origin = (
            ProjectModuleDiagnosticOrigin.GRAPH
            if self.graph_issues
            else ProjectModuleDiagnosticOrigin.EXPORT
            if self.export_issues
            else ProjectModuleDiagnosticOrigin.BINDING
        )
        if self.origin is not expected_origin:
            raise ValueError("Module diagnostic origin must match its evidence.")
        if self.diagnostic.code not in _DIAGNOSTIC_CODE_RANK:
            raise ValueError("Module diagnostic fact requires a Slice 8 code.")
        if self.diagnostic.severity is not Severity.ERROR:
            raise ValueError("Module diagnostics are fail-closed errors.")
        if self.diagnostic.suggestion is not None:
            raise ValueError("Module diagnostics do not carry suggestions.")
        if self.related_locations != _ordered_locations(self.related_locations):
            raise ValueError("Module diagnostic related locations must be ordered.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleDiagnosticSet:
    """One immutable deterministically ordered module diagnostic result."""

    facts: tuple[ProjectModuleDiagnosticFact, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        """Require exact fact order and a lossless public projection."""

        _require_tuple_items(
            self.facts,
            ProjectModuleDiagnosticFact,
            "Project module diagnostic facts",
        )
        _require_tuple_items(
            self.diagnostics,
            Diagnostic,
            "Project module diagnostics",
        )
        if tuple(sorted(self.facts, key=_diagnostic_fact_order)) != self.facts:
            raise ValueError("Project module diagnostics must be canonical ordered.")
        if self.diagnostics != tuple(fact.diagnostic for fact in self.facts):
            raise ValueError("Project module diagnostics must project exact facts.")


def _build_project_module_graph(
    selected_input_index: ProjectSelectedInputIndex,
    modules: tuple[ProjectLogicalModule, ...],
    bindings: ProjectModuleBindingEnvironmentSet,
) -> ProjectModuleGraph:
    """Build the pure selected-module graph from exact Slice 7 requests."""

    _validate_graph_builder_inputs(selected_input_index, modules, bindings)
    vertices = tuple(
        ProjectModuleGraphVertex(
            identity=module.identity,
            position=module.position,
            module=module,
        )
        for module in modules
    )
    vertex_by_path = {vertex.identity.path: vertex for vertex in vertices}
    evidence_edges: list[ProjectModuleImportEvidenceEdge] = []
    unresolved_groups: dict[
        tuple[int, int, str],
        tuple[list[ProjectModuleImportRequest], list[ProjectModuleBindingIssue]],
    ] = {}

    for environment in bindings.environments:
        origin = vertex_by_path[environment.module.path]
        issues_by_request = {
            request: tuple(
                issue for issue in environment.issues if issue.request == request
            )
            for request in environment.requests
        }
        for request in environment.requests:
            selected_target = selected_input_index.find_path(request.target_module_path)
            if selected_target is None:
                unresolved = tuple(
                    issue
                    for issue in issues_by_request[request]
                    if issue.status
                    is ProjectModuleBindingIssueStatus.UNRESOLVED_TARGET_MODULE
                )
                if len(unresolved) != 1:
                    raise ValueError(
                        "Unresolved graph targets require exact Slice 7 evidence."
                    )
                key = (
                    origin.position,
                    request.module_statement_position,
                    request.target_module_path,
                )
                grouped_requests, grouped_issues = unresolved_groups.setdefault(
                    key, ([], [])
                )
                grouped_requests.append(request)
                grouped_issues.extend(unresolved)
                continue
            target = vertex_by_path.get(selected_target.identity.path)
            if target is None:
                raise ValueError("Selected graph target requires one exact vertex.")
            evidence_edges.append(
                ProjectModuleImportEvidenceEdge(
                    origin=origin,
                    target=target,
                    request=request,
                )
            )

    evidence_tuple = tuple(evidence_edges)
    edge_buckets: dict[
        tuple[ProjectModuleGraphVertex, ProjectModuleGraphVertex],
        list[ProjectModuleImportEvidenceEdge],
    ] = {}
    for evidence in evidence_tuple:
        edge_buckets.setdefault((evidence.origin, evidence.target), []).append(evidence)
    edges = tuple(
        ProjectModuleDependencyEdge(
            origin=origin,
            target=target,
            evidence_edges=tuple(edge_buckets[(origin, target)]),
        )
        for origin, target in sorted(
            edge_buckets,
            key=lambda pair: (pair[0].position, pair[1].position),
        )
    )
    components = _strongly_connected_components(vertices, edges)
    cycles = tuple(
        ProjectModuleCycle(
            component=component,
            witness=_canonical_cycle_witness(component),
        )
        for component in components
        if component.is_cyclic
    )
    graph_issues: list[ProjectModuleGraphIssue] = []
    for (origin_position, _statement_position, _target), (
        requests,
        binding_issues,
    ) in unresolved_groups.items():
        graph_issues.append(
            ProjectModuleGraphIssue(
                status=ProjectModuleGraphIssueStatus.UNRESOLVED_TARGET_MODULE,
                owning_vertex=vertices[origin_position],
                requests=tuple(requests),
                binding_issues=tuple(binding_issues),
            )
        )
    graph_issues.extend(
        ProjectModuleGraphIssue(
            status=ProjectModuleGraphIssueStatus.MODULE_IMPORT_CYCLE,
            owning_vertex=cycle.component.members[0],
            cycle=cycle,
        )
        for cycle in cycles
    )
    return ProjectModuleGraph(
        vertices=vertices,
        evidence_edges=evidence_tuple,
        edges=edges,
        components=components,
        cycles=cycles,
        issues=tuple(sorted(graph_issues, key=_graph_issue_order)),
    )


def _build_project_module_diagnostic_set(
    graph: ProjectModuleGraph,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
) -> ProjectModuleDiagnosticSet:
    """Adapt exact private issue facts into ordered public diagnostics."""

    if type(graph) is not ProjectModuleGraph:
        raise TypeError("Module diagnostic adapter requires a module graph.")
    if type(exports) is not ProjectModuleExportSurfaceSet:
        raise TypeError("Module diagnostic adapter requires export surfaces.")
    if type(bindings) is not ProjectModuleBindingEnvironmentSet:
        raise TypeError("Module diagnostic adapter requires binding environments.")
    if len(graph.vertices) != len(exports.surfaces) or len(graph.vertices) != len(
        bindings.environments
    ):
        raise ValueError("Module diagnostic inputs must cover the same modules.")

    module_positions = {
        vertex.identity.path: vertex.position for vertex in graph.vertices
    }
    facts: list[ProjectModuleDiagnosticFact] = [
        _diagnostic_fact_from_graph_issue(issue) for issue in graph.issues
    ]
    unresolved_requests = {
        request
        for issue in graph.issues
        if issue.status is ProjectModuleGraphIssueStatus.UNRESOLVED_TARGET_MODULE
        for request in issue.requests
    }

    collision_buckets: dict[
        tuple[str, str],
        list[ProjectModuleBindingIssue],
    ] = {}
    blocking_import_names: set[tuple[str, str]] = set()
    for environment in bindings.environments:
        for issue in environment.issues:
            if (
                issue.status
                is not ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST
            ):
                blocking_import_names.add(
                    (
                        issue.request.identity.owning_module_path,
                        issue.request.identity.local_binding_name,
                    )
                )
            if issue.status in {
                ProjectModuleBindingIssueStatus.LOCAL_DECLARATION_COLLISION,
                ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION,
            }:
                key = (
                    issue.request.identity.owning_module_path,
                    issue.request.identity.local_binding_name,
                )
                collision_buckets.setdefault(key, []).append(issue)

    collision_requests: set[ProjectModuleImportRequest] = set()
    for collision_issues in collision_buckets.values():
        collision_requests.update(issue.request for issue in collision_issues)
        owner_path = collision_issues[0].request.identity.owning_module_path
        facts.append(
            _diagnostic_fact_from_binding_collision(
                tuple(collision_issues),
                module_position=module_positions[owner_path],
            )
        )

    emitted_export_problem_keys: set[tuple[str, object, object, str]] = set()
    for surface in exports.surfaces:
        issues_by_request = {
            request: tuple(
                issue for issue in surface.issues if issue.request == request
            )
            for request in surface.requests
        }
        for request in surface.requests:
            request_issues = issues_by_request[request]
            if not request_issues:
                continue
            duplicate = tuple(
                issue
                for issue in request_issues
                if issue.status
                is ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST
            )
            resolution = tuple(
                issue
                for issue in request_issues
                if issue.status
                is not ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST
            )
            if duplicate:
                fact = _diagnostic_fact_from_export_issues(
                    request,
                    request_issues,
                    module_position=surface.module.position,
                )
            elif (
                resolution
                and resolution[0].status
                in {
                    ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING,
                    ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE,
                }
                and (request.owning_module_path, request.local_name)
                in blocking_import_names
            ):
                continue
            else:
                fact = _diagnostic_fact_from_export_issues(
                    request,
                    request_issues,
                    module_position=surface.module.position,
                )
            facts.append(fact)
            emitted_export_problem_keys.add(
                (
                    request.owning_module_path,
                    request.namespace,
                    request.declaration_kind,
                    request.local_name,
                )
            )

    for environment in bindings.environments:
        issues_by_request = {
            request: tuple(
                issue for issue in environment.issues if issue.request == request
            )
            for request in environment.requests
        }
        for request in environment.requests:
            if request in unresolved_requests or request in collision_requests:
                continue
            request_issues = tuple(
                issue
                for issue in issues_by_request[request]
                if issue.status
                is not ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST
            )
            if not request_issues:
                continue
            target_key = (
                request.target_module_path,
                request.identity.namespace,
                request.identity.declaration_kind,
                request.exported_name,
            )
            if target_key in emitted_export_problem_keys:
                continue
            facts.append(
                _diagnostic_fact_from_binding_issues(
                    request_issues,
                    module_position=environment.module.position,
                )
            )

    ordered_facts = tuple(sorted(facts, key=_diagnostic_fact_order))
    return ProjectModuleDiagnosticSet(
        facts=ordered_facts,
        diagnostics=tuple(fact.diagnostic for fact in ordered_facts),
    )


def _validate_graph_builder_inputs(
    selected_input_index: ProjectSelectedInputIndex,
    modules: tuple[ProjectLogicalModule, ...],
    bindings: ProjectModuleBindingEnvironmentSet,
) -> None:
    if type(selected_input_index) is not ProjectSelectedInputIndex:
        raise TypeError("Module graph builder requires a selected-input index.")
    if type(modules) is not tuple or any(
        type(module) is not ProjectLogicalModule for module in modules
    ):
        raise TypeError("Module graph builder requires a logical-module tuple.")
    if type(bindings) is not ProjectModuleBindingEnvironmentSet:
        raise TypeError("Module graph builder requires binding environments.")
    if len(modules) != len(selected_input_index.entries) or len(modules) != len(
        bindings.environments
    ):
        raise ValueError("Module graph inputs must cover the same modules.")
    for position, (module, entry, environment) in enumerate(
        zip(
            modules,
            selected_input_index.entries,
            bindings.environments,
            strict=True,
        )
    ):
        if (
            module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or module.position != position
            or module.parsed_input is None
            or entry.position != position
            or entry.identity != module.identity
            or environment.module is not module
        ):
            raise ValueError("Module graph inputs must retain selected module order.")


def _strongly_connected_components(
    vertices: tuple[ProjectModuleGraphVertex, ...],
    edges: tuple[ProjectModuleDependencyEdge, ...],
) -> tuple[ProjectModuleStronglyConnectedComponent, ...]:
    adjacency = {
        vertex: tuple(edge for edge in edges if edge.origin == vertex)
        for vertex in vertices
    }
    reverse_adjacency = {
        vertex: tuple(
            sorted(
                (edge for edge in edges if edge.target == vertex),
                key=lambda edge: edge.origin.position,
            )
        )
        for vertex in vertices
    }
    visited: set[ProjectModuleGraphVertex] = set()
    finish_order: list[ProjectModuleGraphVertex] = []
    for root in vertices:
        if root in visited:
            continue
        visited.add(root)
        walk_stack: list[tuple[ProjectModuleGraphVertex, int]] = [(root, 0)]
        while walk_stack:
            vertex, next_index = walk_stack[-1]
            outgoing = adjacency[vertex]
            if next_index < len(outgoing):
                walk_stack[-1] = (vertex, next_index + 1)
                target = outgoing[next_index].target
                if target not in visited:
                    visited.add(target)
                    walk_stack.append((target, 0))
            else:
                finish_order.append(vertex)
                walk_stack.pop()

    assigned: set[ProjectModuleGraphVertex] = set()
    member_sets: list[tuple[ProjectModuleGraphVertex, ...]] = []
    for root in reversed(finish_order):
        if root in assigned:
            continue
        assigned.add(root)
        members: list[ProjectModuleGraphVertex] = []
        reverse_stack = [root]
        while reverse_stack:
            vertex = reverse_stack.pop()
            members.append(vertex)
            for edge in reversed(reverse_adjacency[vertex]):
                origin = edge.origin
                if origin not in assigned:
                    assigned.add(origin)
                    reverse_stack.append(origin)
        member_sets.append(tuple(sorted(members, key=lambda item: item.position)))

    components = tuple(
        ProjectModuleStronglyConnectedComponent(
            members=members,
            internal_edges=tuple(
                edge
                for edge in edges
                if edge.origin in set(members) and edge.target in set(members)
            ),
        )
        for members in sorted(member_sets, key=lambda items: items[0].position)
    )
    return components


def _canonical_cycle_witness(
    component: ProjectModuleStronglyConnectedComponent,
) -> ProjectModuleCycleWitness:
    if not component.is_cyclic:
        raise ValueError("Canonical cycle witness requires a cyclic component.")
    start = component.members[0]
    member_set = set(component.members)
    adjacency = {
        vertex: tuple(
            edge
            for edge in component.internal_edges
            if edge.origin == vertex and edge.target in member_set
        )
        for vertex in component.members
    }
    candidates: list[tuple[ProjectModuleDependencyEdge, ...]] = []
    for first_edge in adjacency[start]:
        if first_edge.target == start:
            candidates.append((first_edge,))
            continue
        suffix = _shortest_dependency_path(
            origin=first_edge.target,
            target=start,
            adjacency=adjacency,
        )
        if suffix:
            candidates.append((first_edge, *suffix))
    if not candidates:
        raise AssertionError("Cyclic component requires a canonical witness.")
    edges = min(
        candidates,
        key=lambda items: (
            len(items),
            tuple(edge.target.position for edge in items),
        ),
    )
    return ProjectModuleCycleWitness(
        vertices=tuple(edge.origin for edge in edges),
        edges=edges,
    )


def _shortest_dependency_path(
    *,
    origin: ProjectModuleGraphVertex,
    target: ProjectModuleGraphVertex,
    adjacency: Mapping[
        ProjectModuleGraphVertex,
        tuple[ProjectModuleDependencyEdge, ...],
    ],
) -> tuple[ProjectModuleDependencyEdge, ...]:
    queue: deque[ProjectModuleGraphVertex] = deque((origin,))
    visited = {origin}
    previous: dict[ProjectModuleGraphVertex, ProjectModuleDependencyEdge] = {}
    while queue:
        vertex = queue.popleft()
        for edge in adjacency[vertex]:
            next_vertex = edge.target
            if next_vertex in visited:
                continue
            visited.add(next_vertex)
            previous[next_vertex] = edge
            if next_vertex == target:
                path: list[ProjectModuleDependencyEdge] = []
                cursor = target
                while cursor != origin:
                    previous_edge = previous[cursor]
                    path.append(previous_edge)
                    cursor = previous_edge.origin
                return tuple(reversed(path))
            queue.append(next_vertex)
    return ()


def _diagnostic_fact_from_graph_issue(
    issue: ProjectModuleGraphIssue,
) -> ProjectModuleDiagnosticFact:
    if type(issue) is not ProjectModuleGraphIssue:
        raise TypeError("Graph diagnostic adaptation requires a graph issue.")
    if issue.status is ProjectModuleGraphIssueStatus.UNRESOLVED_TARGET_MODULE:
        request = issue.requests[0]
        primary = _location(
            request.source_statement.target_span,
            fallback_path=issue.owning_vertex.identity.path,
        )
        diagnostic = _diagnostic(
            code="PIE-S2701",
            message=(
                "Unresolved module import target: "
                f"{_quoted_target(request.target_module_path)}"
            ),
            location=primary,
        )
        related = _related_locations(
            primary,
            tuple(
                _location(
                    item.source_statement.target_span,
                    fallback_path=issue.owning_vertex.identity.path,
                )
                for item in issue.requests
            ),
        )
        statement_position = request.module_statement_position
        item_position = request.item_position
    elif (
        issue.status
        is ProjectModuleGraphIssueStatus.DUPLICATE_OR_CONFLICTING_MODULE_IDENTITY
    ):
        path = issue.owning_vertex.identity.path
        primary = SourceLocation(
            path=path,
            line=1,
            column=1,
            end_line=1,
            end_column=1,
        )
        diagnostic = _diagnostic(
            code="PIE-S2702",
            message=f"Duplicate or conflicting module identity: {path}",
            location=primary,
        )
        related = _related_locations(
            primary,
            tuple(
                SourceLocation(
                    path=vertex.identity.path,
                    line=1,
                    column=1,
                    end_line=1,
                    end_column=1,
                )
                for vertex in issue.conflicting_vertices
            ),
        )
        statement_position = None
        item_position = None
    elif issue.status is ProjectModuleGraphIssueStatus.MODULE_IMPORT_CYCLE:
        assert issue.cycle is not None
        closing_edge = issue.cycle.witness.edges[-1]
        request = closing_edge.evidence_edges[0].request
        primary = _location(
            request.source_statement.target_span,
            fallback_path=closing_edge.origin.identity.path,
        )
        paths = tuple(vertex.identity.path for vertex in issue.cycle.witness.vertices)
        diagnostic = _diagnostic(
            code="PIE-S2703",
            message=f"Module import cycle detected: {' -> '.join((*paths, paths[0]))}",
            location=primary,
        )
        related = _related_locations(
            primary,
            tuple(
                _location(
                    edge.evidence_edges[0].request.source_statement.target_span,
                    fallback_path=edge.origin.identity.path,
                )
                for edge in issue.cycle.witness.edges
            ),
        )
        statement_position = request.module_statement_position
        item_position = request.item_position
    else:
        request = issue.requests[0]
        primary = _location(
            request.source_statement.target_span,
            fallback_path=issue.owning_vertex.identity.path,
        )
        diagnostic = _diagnostic(
            code="PIE-S2707",
            message=(
                "Unsupported explicit-module reference: "
                f"{_quoted_target(request.target_module_path)}"
            ),
            location=primary,
        )
        related = _related_locations(
            primary,
            tuple(
                _location(
                    item.source_statement.target_span,
                    fallback_path=issue.owning_vertex.identity.path,
                )
                for item in issue.requests
            ),
        )
        statement_position = request.module_statement_position
        item_position = request.item_position
    return ProjectModuleDiagnosticFact(
        origin=ProjectModuleDiagnosticOrigin.GRAPH,
        diagnostic=diagnostic,
        module_position=issue.owning_vertex.position,
        module_statement_position=statement_position,
        item_position=item_position,
        related_locations=related,
        graph_issues=(issue,),
    )


def _diagnostic_fact_from_export_issues(
    request: ProjectModuleExportRequest,
    issues: tuple[ProjectModuleExportIssue, ...],
    *,
    module_position: int,
) -> ProjectModuleDiagnosticFact:
    if not issues or any(issue.request != request for issue in issues):
        raise ValueError("Export diagnostic adaptation requires one request.")
    duplicate = next(
        (
            issue
            for issue in issues
            if issue.status is ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST
        ),
        None,
    )
    issue = duplicate or next(
        item
        for item in issues
        if item.status is not ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST
    )
    kind_and_name = f"{request.source_item.declaration_kind.value} {request.local_name}"
    if issue.status is ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST:
        code = "PIE-S2704"
        message = f"Duplicate export request: {kind_and_name}"
    elif issue.status is ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING:
        code = "PIE-S2704"
        message = f"Unknown export binding: {kind_and_name}"
    elif issue.status is ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION:
        code = "PIE-S2704"
        message = f"Ambiguous local export declaration: {kind_and_name}"
    elif (
        issue.status
        is ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE
    ):
        code = "PIE-S2704"
        message = f"Invalid imported export candidate: {kind_and_name}"
    else:
        code = "PIE-S2706"
        message = f"Export binding name is ambiguous: {request.local_name}"
    primary = _location(
        request.source_item.local_name_span,
        fallback_path=request.owning_module_path,
    )
    related_spans = (
        tuple(
            item.source_item.local_name_span
            for source_issue in issues
            for item in source_issue.prior_requests
        )
        + tuple(
            occurrence.definition.span
            for source_issue in issues
            for occurrence in source_issue.local_occurrences
        )
        + tuple(
            candidate.source_span
            for source_issue in issues
            for candidate in source_issue.imported_candidates
        )
    )
    return ProjectModuleDiagnosticFact(
        origin=ProjectModuleDiagnosticOrigin.EXPORT,
        diagnostic=_diagnostic(code=code, message=message, location=primary),
        module_position=module_position,
        module_statement_position=request.module_statement_position,
        item_position=request.item_position,
        related_locations=_related_locations(
            primary,
            tuple(
                _location(span, fallback_path=request.owning_module_path)
                for span in related_spans
            ),
        ),
        export_issues=issues,
    )


def _diagnostic_fact_from_binding_collision(
    issues: tuple[ProjectModuleBindingIssue, ...],
    *,
    module_position: int,
) -> ProjectModuleDiagnosticFact:
    if not issues:
        raise ValueError("Binding collision adaptation requires issue evidence.")
    requests = tuple(
        sorted(
            {issue.request for issue in issues},
            key=_request_source_key,
        )
    )
    request = requests[0]
    local_issues = tuple(
        issue
        for issue in issues
        if issue.status is ProjectModuleBindingIssueStatus.LOCAL_DECLARATION_COLLISION
    )
    if local_issues:
        message = (
            "Import binding collides with a local declaration: "
            f"{request.identity.local_binding_name}"
        )
    else:
        message = (
            f"Import binding name is ambiguous: {request.identity.local_binding_name}"
        )
    primary_span = _import_binding_span(request)
    primary = _location(
        primary_span,
        fallback_path=request.identity.owning_module_path,
    )
    related_spans = (
        tuple(
            occurrence.definition.span
            for issue in issues
            for occurrence in issue.local_occurrences
        )
        + tuple(
            _import_binding_span(competing)
            for issue in issues
            for competing in issue.competing_requests
        )
        + tuple(_import_binding_span(item) for item in requests)
    )
    return ProjectModuleDiagnosticFact(
        origin=ProjectModuleDiagnosticOrigin.BINDING,
        diagnostic=_diagnostic(code="PIE-S2706", message=message, location=primary),
        module_position=module_position,
        module_statement_position=request.module_statement_position,
        item_position=request.item_position,
        related_locations=_related_locations(
            primary,
            tuple(
                _location(span, fallback_path=request.identity.owning_module_path)
                for span in related_spans
            ),
        ),
        binding_issues=issues,
    )


def _diagnostic_fact_from_binding_issues(
    issues: tuple[ProjectModuleBindingIssue, ...],
    *,
    module_position: int,
) -> ProjectModuleDiagnosticFact:
    if not issues or any(issue.request != issues[0].request for issue in issues):
        raise ValueError("Binding diagnostic adaptation requires one request.")
    request = issues[0].request
    issue = issues[0]
    kind = request.source_item.declaration_kind.value
    target = _quoted_target(request.target_module_path)
    if issue.status is ProjectModuleBindingIssueStatus.UNKNOWN_EXPORTED_NAME:
        code = "PIE-S2705"
        message = (
            f"Unknown imported declaration: {kind} {request.exported_name} "
            f"from {target}"
        )
        primary_span = request.source_item.exported_name_span
    elif (
        issue.status
        is ProjectModuleBindingIssueStatus.PRIVATE_OR_UNEXPORTED_DECLARATION
    ):
        code = "PIE-S2705"
        message = (
            "Imported declaration is private or not exported: "
            f"{kind} {request.exported_name} from {target}"
        )
        primary_span = request.source_item.exported_name_span
    elif issue.status is ProjectModuleBindingIssueStatus.INCONSISTENT_TARGET_FACADE:
        code = "PIE-S2707"
        message = f"Inconsistent explicit-module target facade: {target}"
        primary_span = request.source_statement.target_span
    elif issue.status is ProjectModuleBindingIssueStatus.AMBIGUOUS_TARGET_FACADE:
        code = "PIE-S2707"
        message = f"Ambiguous explicit-module target facade: {target}"
        primary_span = request.source_statement.target_span
    else:
        raise ValueError("Binding issue requires collision or target adaptation.")
    primary = _location(
        primary_span,
        fallback_path=request.identity.owning_module_path,
    )
    related_spans = tuple(
        occurrence.definition.span
        for source_issue in issues
        for occurrence in (
            *source_issue.target_occurrences,
            *source_issue.local_occurrences,
        )
    ) + tuple(
        _import_binding_span(item)
        for source_issue in issues
        for item in (
            *source_issue.competing_requests,
            *source_issue.prior_requests,
        )
    )
    return ProjectModuleDiagnosticFact(
        origin=ProjectModuleDiagnosticOrigin.BINDING,
        diagnostic=_diagnostic(code=code, message=message, location=primary),
        module_position=module_position,
        module_statement_position=request.module_statement_position,
        item_position=request.item_position,
        related_locations=_related_locations(
            primary,
            tuple(
                _location(span, fallback_path=request.identity.owning_module_path)
                for span in related_spans
            ),
        ),
        binding_issues=issues,
    )


def _graph_issue_order(issue: ProjectModuleGraphIssue) -> tuple[int, int, int, str]:
    status_rank = tuple(ProjectModuleGraphIssueStatus).index(issue.status)
    if issue.requests:
        statement_position = issue.requests[0].module_statement_position
        target = issue.requests[0].target_module_path
    else:
        statement_position = -1
        target = issue.owning_vertex.identity.path
    return (status_rank, issue.owning_vertex.position, statement_position, target)


_DIAGNOSTIC_CODE_RANK = {f"PIE-S270{position}": position for position in range(1, 8)}


def _diagnostic_fact_order(
    fact: ProjectModuleDiagnosticFact,
) -> tuple[int, int, int, int, str, str]:
    return (
        _DIAGNOSTIC_CODE_RANK[fact.diagnostic.code],
        fact.module_position,
        -1
        if fact.module_statement_position is None
        else fact.module_statement_position,
        -1 if fact.item_position is None else fact.item_position,
        fact.diagnostic.location.path or "",
        fact.diagnostic.message,
    )


def _request_source_key(request: ProjectModuleImportRequest) -> tuple[int, int]:
    return (request.module_statement_position, request.item_position)


def _evidence_edge_key(
    edge: ProjectModuleImportEvidenceEdge,
) -> tuple[int, int, int]:
    return (
        edge.origin.position,
        edge.request.module_statement_position,
        edge.request.item_position,
    )


def _dependency_edge_key(edge: ProjectModuleDependencyEdge) -> tuple[int, int]:
    return (edge.origin.position, edge.target.position)


def _import_binding_span(request: ProjectModuleImportRequest) -> Span:
    return (
        request.source_item.local_name_span
        if request.source_item.local_name_span is not None
        else request.source_item.exported_name_span
    )


def _location(span: Span, *, fallback_path: str) -> SourceLocation:
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _location_order(
    location: SourceLocation,
) -> tuple[str, int, int, int, int]:
    return (
        location.path or "",
        location.line,
        location.column,
        -1 if location.end_line is None else location.end_line,
        -1 if location.end_column is None else location.end_column,
    )


def _ordered_locations(
    locations: tuple[SourceLocation, ...],
) -> tuple[SourceLocation, ...]:
    return tuple(sorted(set(locations), key=_location_order))


def _related_locations(
    primary: SourceLocation,
    locations: tuple[SourceLocation, ...],
) -> tuple[SourceLocation, ...]:
    return _ordered_locations(tuple(item for item in locations if item != primary))


def _quoted_target(target: str) -> str:
    return json.dumps(target, ensure_ascii=True)


def _diagnostic(*, code: str, message: str, location: SourceLocation) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=location,
    )


def _require_tuple_items(
    values: object,
    expected_type: type[object],
    label: str,
) -> None:
    if type(values) is not tuple or any(
        type(item) is not expected_type for item in values
    ):
        raise TypeError(f"{label} must be a tuple.")
