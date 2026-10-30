"""Private schema-v2 module graph and public diagnostic adaptation."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
import json
import posixpath
from types import MappingProxyType

from pietto._project.module_bindings import (
    ProjectModuleBindingEnvironment,
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
    ProjectImportedExportCandidate,
    ProjectModuleExportIssue,
    ProjectModuleExportIssueStatus,
    ProjectModuleExportRequest,
    ProjectModuleExportSurfaceSet,
)
from pietto._project.model import ProjectParsedInput, ProjectSymbolKind
from pietto._project.selected_input_index import ProjectSelectedInputIndex
from pietto.ast_nodes import ImportStatement, ModuleDeclarationKind, Span
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()

# An unresolved import target names at most this many selected paths.
_TARGET_CANDIDATE_LIMIT = 3


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
class _ProjectModuleGraphCanonicalAuthority:
    """Derive one complete private graph projection from its authority root."""

    binding_authority: ProjectModuleBindingEnvironmentSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    vertices: tuple[ProjectModuleGraphVertex, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    evidence_edges: tuple[ProjectModuleImportEvidenceEdge, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    edges: tuple[ProjectModuleDependencyEdge, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    components: tuple[ProjectModuleStronglyConnectedComponent, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    cycles: tuple[ProjectModuleCycle, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    issues: tuple[ProjectModuleGraphIssue, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Derive every non-init graph product from the retained root only."""

        if type(self.binding_authority) is not ProjectModuleBindingEnvironmentSet:
            raise TypeError("Module graph authority requires exact binding authority.")
        products = _derive_binding_authority_graph(self.binding_authority)
        for name, value in zip(
            ("vertices", "evidence_edges", "edges", "components", "cycles", "issues"),
            products,
            strict=True,
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleGraph:
    """The complete deterministic selected-module dependency graph."""

    binding_authority: ProjectModuleBindingEnvironmentSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    _canonical_authority: _ProjectModuleGraphCanonicalAuthority = field(
        repr=False,
        compare=False,
        hash=False,
    )
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

        if type(self.binding_authority) is not ProjectModuleBindingEnvironmentSet:
            raise TypeError("Module graph requires exact binding authority.")
        if type(self._canonical_authority) is not _ProjectModuleGraphCanonicalAuthority:
            raise TypeError("Module graph requires exact canonical authority.")
        if self.binding_authority is not self._canonical_authority.binding_authority:
            raise ValueError(
                "Module graph canonical authority must exactly match binding authority root."
            )
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
        if len(self.vertices) != len(self.binding_authority.environments) or any(
            vertex.identity != environment.module.identity
            or vertex.position != position
            or vertex.module is not environment.module
            for position, (vertex, environment) in enumerate(
                zip(
                    self.vertices,
                    self.binding_authority.environments,
                    strict=True,
                )
            )
        ):
            raise ValueError(
                "Module graph vertices must exactly match binding authority."
            )
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

        (
            expected_vertices,
            expected_evidence,
            expected_edges,
            expected_components,
            expected_cycles,
            expected_issues,
        ) = _derive_binding_authority_graph(self.binding_authority)
        if self.vertices != expected_vertices or any(
            vertex.module is not environment.module
            for vertex, environment in zip(
                self.vertices,
                self.binding_authority.environments,
                strict=True,
            )
        ):
            raise ValueError(
                "Module graph vertices must exactly match binding authority."
            )
        if self.evidence_edges != expected_evidence or any(
            actual.request is not expected_item.request
            for actual, expected_item in zip(
                self.evidence_edges,
                expected_evidence,
                strict=True,
            )
        ):
            raise ValueError(
                "Module graph evidence must exactly match binding authority."
            )
        if self.edges != expected_edges:
            raise ValueError(
                "Module graph edges must exactly match binding authority evidence."
            )
        if self.components != expected_components:
            raise ValueError(
                "Module graph components must exactly match canonical graph edges."
            )
        if self.cycles != expected_cycles:
            raise ValueError(
                "Module graph cycles must exactly match canonical components."
            )
        if self.issues != expected_issues:
            raise ValueError(
                "Module graph issues must exactly match binding authority."
            )
        if any(
            edge.origin is not self.vertices[edge.origin.position]
            or edge.target is not self.vertices[edge.target.position]
            or any(
                retained is not evidence
                for retained, evidence in zip(
                    edge.evidence_edges,
                    (
                        item
                        for item in self.evidence_edges
                        if item.origin is edge.origin and item.target is edge.target
                    ),
                    strict=True,
                )
            )
            for edge in self.edges
        ):
            raise ValueError(
                "Module graph edges must retain exact graph evidence objects."
            )
        if any(
            any(
                member is not self.vertices[member.position]
                for member in component.members
            )
            or any(
                edge is not self.edges[self.edges.index(edge)]
                for edge in component.internal_edges
            )
            for component in self.components
        ):
            raise ValueError("Module graph components must retain exact graph objects.")
        if any(
            cycle.component
            is not self.components[self.components.index(cycle.component)]
            or any(
                vertex is not self.vertices[vertex.position]
                for vertex in cycle.witness.vertices
            )
            or any(
                edge is not self.edges[self.edges.index(edge)]
                for edge in cycle.witness.edges
            )
            for cycle in self.cycles
        ):
            raise ValueError("Module graph cycles must retain exact graph objects.")
        if any(
            issue.owning_vertex is not self.vertices[issue.owning_vertex.position]
            or (
                issue.cycle is not None
                and issue.cycle is not self.cycles[self.cycles.index(issue.cycle)]
            )
            or any(
                actual is not expected_item
                for actual, expected_item in zip(
                    issue.requests,
                    expected_issue.requests,
                    strict=True,
                )
            )
            or any(
                actual is not expected_item
                for actual, expected_item in zip(
                    issue.binding_issues,
                    expected_issue.binding_issues,
                    strict=True,
                )
            )
            for issue, expected_issue in zip(
                self.issues,
                expected_issues,
                strict=True,
            )
        ):
            raise ValueError("Module graph issues must retain exact authority objects.")
        canonical_tuples = (
            ("vertices", self.vertices, self._canonical_authority.vertices),
            (
                "evidence edges",
                self.evidence_edges,
                self._canonical_authority.evidence_edges,
            ),
            ("edges", self.edges, self._canonical_authority.edges),
            ("components", self.components, self._canonical_authority.components),
            ("cycles", self.cycles, self._canonical_authority.cycles),
            ("issues", self.issues, self._canonical_authority.issues),
        )
        if any(
            len(actual) != len(canonical)
            or any(
                supplied is not retained
                for supplied, retained in zip(actual, canonical, strict=True)
            )
            for _name, actual, canonical in canonical_tuples
        ):
            raise ValueError(
                "Module graph values must retain exact canonical authority objects."
            )

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
class _ProjectModuleDiagnosticCanonicalAuthority:
    """Derive one diagnostic projection from its exact private input roots."""

    graph: ProjectModuleGraph = field(repr=False, compare=False, hash=False)
    exports: ProjectModuleExportSurfaceSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    binding_authority: ProjectModuleBindingEnvironmentSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    facts: tuple[ProjectModuleDiagnosticFact, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Derive both products only from the retained exact roots."""

        facts, diagnostics = _derive_project_module_diagnostic_products(
            self.graph,
            self.exports,
            self.binding_authority,
        )
        object.__setattr__(self, "facts", facts)
        object.__setattr__(self, "diagnostics", diagnostics)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleDiagnosticSet:
    """One immutable deterministically ordered module diagnostic result."""

    _canonical_authority: _ProjectModuleDiagnosticCanonicalAuthority = field(
        repr=False,
        compare=False,
        hash=False,
    )

    facts: tuple[ProjectModuleDiagnosticFact, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        """Require exact fact order and a lossless public projection."""

        if (
            type(self._canonical_authority)
            is not _ProjectModuleDiagnosticCanonicalAuthority
        ):
            raise TypeError(
                "Project module diagnostic set requires exact canonical authority."
            )
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
        canonical = self._canonical_authority
        if (
            len(self.facts) != len(canonical.facts)
            or len(self.diagnostics) != len(canonical.diagnostics)
            or any(
                supplied is not retained
                for supplied, retained in zip(self.facts, canonical.facts, strict=True)
            )
            or any(
                supplied is not retained
                for supplied, retained in zip(
                    self.diagnostics,
                    canonical.diagnostics,
                    strict=True,
                )
            )
        ):
            raise ValueError(
                "Project module diagnostics must retain exact canonical authority objects."
            )


def _build_project_module_graph(
    selected_input_index: ProjectSelectedInputIndex,
    modules: tuple[ProjectLogicalModule, ...],
    bindings: ProjectModuleBindingEnvironmentSet,
) -> ProjectModuleGraph:
    """Build the pure selected-module graph from exact Slice 7 requests."""

    _validate_graph_builder_inputs(selected_input_index, modules, bindings)
    canonical_authority = _ProjectModuleGraphCanonicalAuthority(
        binding_authority=bindings,
    )
    return ProjectModuleGraph(
        binding_authority=bindings,
        _canonical_authority=canonical_authority,
        vertices=canonical_authority.vertices,
        evidence_edges=canonical_authority.evidence_edges,
        edges=canonical_authority.edges,
        components=canonical_authority.components,
        cycles=canonical_authority.cycles,
        issues=canonical_authority.issues,
    )


def _derive_project_module_diagnostic_products(
    graph: ProjectModuleGraph,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
) -> tuple[tuple[ProjectModuleDiagnosticFact, ...], tuple[Diagnostic, ...]]:
    """Adapt exact-root issue facts into ordered public diagnostic products."""

    if type(graph) is not ProjectModuleGraph:
        raise TypeError("Module diagnostic adapter requires a module graph.")
    if type(exports) is not ProjectModuleExportSurfaceSet:
        raise TypeError("Module diagnostic adapter requires export surfaces.")
    if type(bindings) is not ProjectModuleBindingEnvironmentSet:
        raise TypeError("Module diagnostic adapter requires binding environments.")
    if graph.binding_authority is not bindings:
        raise ValueError(
            "Module diagnostic roots must retain exact graph binding authority."
        )
    if len(graph.vertices) != len(exports.surfaces) or len(graph.vertices) != len(
        bindings.environments
    ):
        raise ValueError("Module diagnostic inputs must cover the same modules.")
    if any(
        surface.module is not vertex.module or environment.module is not vertex.module
        for vertex, surface, environment in zip(
            graph.vertices,
            exports.surfaces,
            bindings.environments,
            strict=True,
        )
    ):
        raise ValueError(
            "Module diagnostic roots must retain exact selected module authority."
        )

    module_positions = {
        vertex.identity.path: vertex.position for vertex in graph.vertices
    }
    module_paths = tuple(vertex.identity.path for vertex in graph.vertices)
    facts: list[ProjectModuleDiagnosticFact] = [
        _diagnostic_fact_from_graph_issue(issue, module_paths=module_paths)
        for issue in graph.issues
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
                    declared_kinds=_declared_kinds(surface.module, request.local_name),
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

    environments_by_path = {
        environment.module.path: environment for environment in bindings.environments
    }
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
                    target_environment=environments_by_path.get(
                        request.target_module_path
                    ),
                )
            )

    ordered_facts = tuple(sorted(facts, key=_diagnostic_fact_order))
    return ordered_facts, tuple(fact.diagnostic for fact in ordered_facts)


def _build_project_module_diagnostic_set(
    graph: ProjectModuleGraph,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
) -> ProjectModuleDiagnosticSet:
    """Build one self-verifying private module diagnostic projection."""

    canonical_authority = _ProjectModuleDiagnosticCanonicalAuthority(
        graph=graph,
        exports=exports,
        binding_authority=bindings,
    )
    return ProjectModuleDiagnosticSet(
        _canonical_authority=canonical_authority,
        facts=canonical_authority.facts,
        diagnostics=canonical_authority.diagnostics,
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


def _derive_binding_authority_graph(
    binding_authority: ProjectModuleBindingEnvironmentSet,
) -> tuple[
    tuple[ProjectModuleGraphVertex, ...],
    tuple[ProjectModuleImportEvidenceEdge, ...],
    tuple[ProjectModuleDependencyEdge, ...],
    tuple[ProjectModuleStronglyConnectedComponent, ...],
    tuple[ProjectModuleCycle, ...],
    tuple[ProjectModuleGraphIssue, ...],
]:
    """Derive every ordered graph fact from one complete binding authority."""

    if type(binding_authority) is not ProjectModuleBindingEnvironmentSet:
        raise TypeError("Module graph authority requires exact binding authority.")
    vertices = tuple(
        ProjectModuleGraphVertex(
            identity=environment.module.identity,
            position=environment.module.position,
            module=environment.module,
        )
        for environment in binding_authority.environments
    )

    vertex_by_path = {vertex.identity.path: vertex for vertex in vertices}
    evidence_edges: list[ProjectModuleImportEvidenceEdge] = []
    unresolved_groups: dict[
        tuple[int, int, str],
        tuple[list[ProjectModuleImportRequest], list[ProjectModuleBindingIssue]],
    ] = {}
    for environment in binding_authority.environments:
        origin = vertex_by_path[environment.module.path]
        issues_by_request = {
            request: tuple(
                issue for issue in environment.issues if issue.request == request
            )
            for request in environment.requests
        }
        for request in environment.requests:
            selected_targets = binding_authority.find_module_path(
                request.target_module_path
            )
            if not selected_targets:
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
                    key,
                    ([], []),
                )
                grouped_requests.append(request)
                grouped_issues.extend(unresolved)
                continue
            target = vertex_by_path[selected_targets[0].module.path]
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
    return (
        vertices,
        evidence_tuple,
        edges,
        components,
        cycles,
        tuple(sorted(graph_issues, key=_graph_issue_order)),
    )


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
    *,
    module_paths: tuple[str, ...] = (),
) -> ProjectModuleDiagnosticFact:
    if type(issue) is not ProjectModuleGraphIssue:
        raise TypeError("Graph diagnostic adaptation requires a graph issue.")
    if issue.status is ProjectModuleGraphIssueStatus.UNRESOLVED_TARGET_MODULE:
        request = issue.requests[0]
        primary = _location(
            request.source_statement.target_span,
            fallback_path=issue.owning_vertex.identity.path,
        )
        candidates = _unresolved_target_candidates(request, module_paths)
        diagnostic = _diagnostic(
            code="PIE-S2701",
            message=(
                "Unresolved module import target: "
                f"{_copyable_path(request.target_module_path)}"
                + (
                    "; did you mean "
                    + " or ".join(_copyable_path(path) for path in candidates)
                    + "? An import path is the project-root-relative path of a "
                    "selected source, with / separators"
                    if candidates
                    else ""
                )
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
                f"{_copyable_path(request.target_module_path)}"
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
    declared_kinds: tuple[ProjectSymbolKind, ...] = (),
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
        if declared_kinds:
            # The module declares the name with another kind only.
            message += f"; {request.local_name} is {_kinds_text(declared_kinds)}"
    elif issue.status is ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION:
        code = "PIE-S2704"
        message = f"Ambiguous local export declaration: {kind_and_name}"
    elif (
        issue.status
        is ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE
    ):
        code = "PIE-S2704"
        message = f"Invalid imported export candidate: {kind_and_name}"
        imported_kinds = tuple(
            item
            for item in ProjectSymbolKind
            if any(
                candidate.declaration_kind is item
                for candidate in issue.imported_candidates
            )
        )
        if imported_kinds and request.source_item.declaration_kind not in (
            imported_kinds
        ):
            # The module imports the name with another kind only.
            message += f"; {request.local_name} is {_kinds_text(imported_kinds)}"
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
    target_environment: ProjectModuleBindingEnvironment | None = None,
) -> ProjectModuleDiagnosticFact:
    if not issues or any(issue.request != issues[0].request for issue in issues):
        raise ValueError("Binding diagnostic adaptation requires one request.")
    request = issues[0].request
    issue = issues[0]
    kind = request.source_item.declaration_kind.value
    target = _copyable_path(request.target_module_path)
    target_spans: tuple[Span, ...] = ()
    if issue.status is ProjectModuleBindingIssueStatus.UNKNOWN_EXPORTED_NAME:
        code = "PIE-S2705"
        imported = f"{kind} {request.exported_name} from {target}"
        message = f"Unknown imported declaration: {imported}"
        # The target module may hold the name only as imports of its own,
        # which it does not export, or re-exports while they fail.
        held = _target_imports(request, target_environment)
        if held and target_environment is not None and len(issue.target_surfaces) == 1:
            held_set = set(held)
            failed = any(
                item.request in held_set
                and item.status
                is not ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST
                for item in target_environment.issues
            )
            exported = any(
                item.namespace is request.identity.namespace
                and item.declaration_kind is request.identity.declaration_kind
                and item.local_name == request.exported_name
                for item in issue.target_surfaces[0].requests
            )
            if not exported:
                target_spans = tuple(_import_binding_span(item) for item in held)
                message = f"Imported declaration is private or not exported: {imported}"
            elif failed:
                target_spans = tuple(_import_binding_span(item) for item in held)
                message = (
                    f"Imported declaration is unavailable: {imported}, whose own"
                    f" import of {request.exported_name} fails"
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
    elif (
        issue.status is ProjectModuleBindingIssueStatus.INCONSISTENT_TARGET_FACADE
        and (mismatch := _kind_mismatch(issue)) is not None
    ):
        code = "PIE-S2705"
        message = mismatch
        primary_span = request.source_item.exported_name_span
        # A re-exported entry points at the import binding it re-exports.
        target_spans = tuple(
            entry.resolved_from.source_span
            for entry in issue.target_entries
            if type(entry.resolved_from) is ProjectImportedExportCandidate
        )
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
    related_spans = (
        tuple(
            occurrence.definition.span
            for source_issue in issues
            for occurrence in (
                *source_issue.target_occurrences,
                *source_issue.local_occurrences,
            )
        )
        + tuple(
            _import_binding_span(item)
            for source_issue in issues
            for item in (
                *source_issue.competing_requests,
                *source_issue.prior_requests,
            )
        )
        + target_spans
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


def _target_imports(
    request: ProjectModuleImportRequest,
    environment: ProjectModuleBindingEnvironment | None,
) -> tuple[ProjectModuleImportRequest, ...]:
    """The target module's own import bindings of the requested name and
    kind, in source order; a module that imports from itself has none but
    the request."""

    if environment is None:
        return ()
    return tuple(
        item
        for item in environment.requests
        if item != request
        and item.identity.local_binding_name == request.exported_name
        and item.identity.namespace is request.identity.namespace
        and item.identity.declaration_kind is request.identity.declaration_kind
    )


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


def _copyable_path(path: str) -> str:
    """An import target, as written or as a selected path to copy, quoted as
    a Pietto string: a non-ASCII character stays as it is. Only a control
    character is shown as a JSON \\u00XX escape, which a Pietto string does
    not accept."""

    return json.dumps(path, ensure_ascii=False)


def _kind_mismatch(issue: ProjectModuleBindingIssue) -> str | None:
    """The PIE-S2705 message of an import whose one target module has the name
    only with another kind, or has the requested kind but does not export it;
    None when the facade itself is inconsistent."""

    request = issue.request
    if len(issue.target_surfaces) != 1:
        return None
    imported = (
        f"{request.source_item.declaration_kind.value} {request.exported_name} "
        f"from {_copyable_path(request.target_module_path)}"
    )
    if any(
        occurrence.identity.namespace is request.identity.namespace
        and occurrence.identity.declaration_kind is request.identity.declaration_kind
        for occurrence in issue.target_occurrences
    ):
        return f"Imported declaration is private or not exported: {imported}"
    exported = {entry.declaration_kind for entry in issue.target_entries}
    declared = {
        occurrence.identity.declaration_kind for occurrence in issue.target_occurrences
    }
    kinds = tuple(item for item in ProjectSymbolKind if item in exported | declared)
    if not kinds:
        return None
    message = (
        f"Imported declaration has another kind: {imported} is {_kinds_text(kinds)}"
    )
    if len(kinds) == 1 and kinds[0] in exported:
        message += f"; write {kinds[0].value} {request.exported_name}"
    return message


def _kinds_text(kinds: tuple[ProjectSymbolKind, ...]) -> str:
    """`a source`, or `a shape and a query`, in declaration-kind order."""

    words = tuple(
        f"{'an' if item.value[0] in 'aeiou' else 'a'} {item.value}" for item in kinds
    )
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"


def _declared_kinds(
    module: ProjectLogicalModule, name: str
) -> tuple[ProjectSymbolKind, ...]:
    """The kinds of a module's own declarations of a name, as its catalog
    classifies them, in declaration-kind order."""

    from pietto._project.model import _classify_project_definition
    from pietto._project.module_catalog import _block_view_of
    from pietto.ast_nodes import BlockRelationDef

    assert module.parsed_input is not None
    kinds = {
        _classify_project_definition(
            _block_view_of(definition)
            if type(definition) is BlockRelationDef
            else definition
        )[1]
        for definition in module.parsed_input.script.definitions
        if definition.name == name
    }
    return tuple(item for item in ProjectSymbolKind if item in kinds)


def _unresolved_target_candidates(
    request: ProjectModuleImportRequest, module_paths: tuple[str, ...]
) -> tuple[str, ...]:
    """The selected module paths an unresolved import target may have meant:
    the target written relative to the importing module, with `\\`, `./`, a
    leading `/`, `..` or another letter case, without `.pietto`, or as a
    path's last parts. Sorted and bounded; no candidate is chosen. A path
    that is not valid UTF-8 is none, since no Pietto string spells it."""

    written = request.target_module_path.replace("\\", "/").strip("/")
    if not written:
        return ()
    importer = posixpath.dirname(request.identity.owning_module_path)
    forms = {
        posixpath.normpath(form)
        for base in (written, posixpath.join(importer, written))
        for form in (base, f"{base}.pietto")
    }
    folded = {form.casefold() for form in forms}
    tail = "/" + posixpath.normpath(written)
    return tuple(
        sorted(
            path
            for path in module_paths
            if (path.casefold() in folded or path.endswith(tail)) and _spellable(path)
        )
    )[:_TARGET_CANDIDATE_LIMIT]


def _spellable(path: str) -> bool:
    """Whether a Pietto string can spell a selected path: one that is not
    valid UTF-8, such as a file name byte read as \\udcff, has no text in a
    UTF-8 source."""

    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


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


# How each unknown-name diagnostic starts, before the name, and the kinds of
# declaration a module may import to give that name.
_IMPORT_HINT_KINDS: Mapping[tuple[str, str], tuple[ModuleDeclarationKind, ...]] = (
    MappingProxyType(
        {
            ("PIE-S2604", "Unknown relationship parameter shape: "): (
                ModuleDeclarationKind.SHAPE,
            ),
            ("PIE-S2303", "Unknown source shape: "): (ModuleDeclarationKind.SHAPE,),
            ("PIE-S2002", "Unknown type: "): (
                ModuleDeclarationKind.TYPE,
                ModuleDeclarationKind.ENUM,
                ModuleDeclarationKind.SHAPE,
            ),
            ("PIE-S2301", "Unknown relation: "): (
                ModuleDeclarationKind.SOURCE,
                ModuleDeclarationKind.TABLE,
                ModuleDeclarationKind.QUERY,
            ),
            ("PIE-S2103", "Unknown function: "): (),
        }
    )
)
# An import hint names at most this many exporting modules.
_IMPORT_HINT_LIMIT = 3


def import_hints(
    diagnostics: tuple[Diagnostic, ...],
    modules: tuple[ProjectParsedInput, ...],
    exports: Callable[[], ProjectModuleExportSurfaceSet],
) -> tuple[Diagnostic, ...]:
    """Say where another selected module exports an unknown type, shape or
    relation of a module, and how to import it, or that an unknown function
    is a def of another module, which a module cannot import. Every exporter
    is listed in path order, up to a bound; none is chosen. An exporter is a
    resolved entry of a module's export surface, which ``exports`` builds
    once a diagnostic asks: an export that is refused (PIE-S2704, a
    duplicate request included), a re-export whose own import fails, or one
    of a module whose path is not valid UTF-8, which no import can spell, is
    none. A module that already declares or imports the name, of either
    namespace, gets no import hint, since that import would collide with the
    declaration or binding (PIE-S2706). A message that already has a hint, and every code, span and
    order, are kept. With no hint the same tuple is returned, since readers
    may compare diagnostics by identity."""

    surfaces: ProjectModuleExportSurfaceSet | None = None
    hinted = list(diagnostics)
    for position, diagnostic in enumerate(diagnostics):
        kinds = next(
            (
                value
                for (code, prefix), value in _IMPORT_HINT_KINDS.items()
                if diagnostic.code == code and diagnostic.message.startswith(prefix)
            ),
            None,
        )
        if kinds is None or ";" in diagnostic.message:
            continue
        name = diagnostic.message.partition(": ")[2]
        others = tuple(
            module
            for module in sorted(modules, key=lambda item: item.path)
            if module.path != diagnostic.location.path
        )
        if not kinds:
            files = tuple(
                module.path
                for module in others
                if any(item.name == name for item in module.scalar_callables)
            )
            if files:
                hinted[position] = replace(
                    diagnostic,
                    message=f"{diagnostic.message}; {name} is a def of "
                    f"{_listed(files)}, which a module cannot import: "
                    "declare it in this module",
                )
            continue
        if any(
            name
            in {
                *(getattr(item, "name", None) for item in module.script.definitions),
                *(
                    item.local_name or item.exported_name
                    for statement in module.script.module_statements
                    if isinstance(statement, ImportStatement)
                    for item in statement.items
                ),
            }
            for module in modules
            if module.path == diagnostic.location.path
        ):
            continue
        if surfaces is None:
            surfaces = exports()
        exporters = tuple(
            (module.path, ModuleDeclarationKind(entry.declaration_kind.value))
            for module in others
            if _spellable(module.path)
            for surface in surfaces.find_module_path(module.path)
            for entry in surface.entries
            if entry.exposed_name == name
            and entry.declaration_kind.value in {kind.value for kind in kinds}
            and not any(
                issue.request.local_name == name
                and issue.request.declaration_kind is entry.declaration_kind
                for issue in surface.issues
            )
        )
        exporters = tuple(dict.fromkeys(exporters))
        if not exporters:
            continue
        shown = exporters[:_IMPORT_HINT_LIMIT]
        exported_kinds = {kind for _, kind in exporters}
        if len(exported_kinds) == 1:
            (kind,) = exported_kinds
            head = (
                f"{name} is {_kinds_text((ProjectSymbolKind(kind.value),))} "
                f"exported by {_listed(tuple(path for path, _ in exporters))}"
            )
        else:
            head = f"{name} is exported by " + _listed(
                tuple(
                    f"{path} ({_kinds_text((ProjectSymbolKind(kind.value),))})"
                    for path, kind in exporters
                )
            )
        imports = " or ".join(
            f"from {_copyable_path(path)} import ({kind.value} {name})"
            for path, kind in shown
        )
        hinted[position] = replace(
            diagnostic,
            message=f"{diagnostic.message}; {head}: import it with {imports}",
        )
    if all(new is old for new, old in zip(hinted, diagnostics, strict=True)):
        return diagnostics
    return tuple(hinted)


def _listed(items: tuple[str, ...]) -> str:
    """`a`, `a and b`, or the first of many and how many more."""

    if len(items) > _IMPORT_HINT_LIMIT:
        shown = items[:_IMPORT_HINT_LIMIT]
        return f"{', '.join(shown)} and {len(items) - len(shown)} more"
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"
