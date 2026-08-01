"""Private schema-v2 named-import binding environments."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from pietto._project.model import ProjectSymbolKind, ProjectSymbolNamespace
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.module_catalog import (
    ProjectDeclarationOccurrence,
    ProjectModuleCatalogSet,
    ProjectNominalDeclarationIdentity,
)
from pietto._project.module_exports import (
    ProjectImportedBindingCandidateProof,
    ProjectImportedExportCandidate,
    ProjectModuleExportEntry,
    ProjectModuleExportSurface,
    ProjectModuleExportSurfaceSet,
    _build_project_module_export_surface_set,
)
from pietto._project.selected_input_index import ProjectSelectedInputIndex
from pietto.ast_nodes import (
    ImportItem,
    ImportStatement,
    ModuleDeclarationKind,
)

__all__: tuple[str, ...] = ()


_IMPORT_KIND_MAP = {
    ModuleDeclarationKind.TYPE: (
        ProjectSymbolNamespace.TYPE,
        ProjectSymbolKind.TYPE_ALIAS,
    ),
    ModuleDeclarationKind.ENUM: (
        ProjectSymbolNamespace.TYPE,
        ProjectSymbolKind.ENUM,
    ),
    ModuleDeclarationKind.SHAPE: (
        ProjectSymbolNamespace.TYPE,
        ProjectSymbolKind.SHAPE,
    ),
    ModuleDeclarationKind.SOURCE: (
        ProjectSymbolNamespace.RELATION,
        ProjectSymbolKind.SOURCE,
    ),
    ModuleDeclarationKind.TABLE: (
        ProjectSymbolNamespace.RELATION,
        ProjectSymbolKind.TABLE,
    ),
    ModuleDeclarationKind.QUERY: (
        ProjectSymbolNamespace.RELATION,
        ProjectSymbolKind.QUERY,
    ),
}
_ELIGIBLE_NAMESPACE_KIND_PAIRS = frozenset(_IMPORT_KIND_MAP.values())


class ProjectModuleBindingIssueStatus(StrEnum):
    """Private fail-closed import and local-binding classifications."""

    UNRESOLVED_TARGET_MODULE = "unresolved_target_module"
    UNKNOWN_EXPORTED_NAME = "unknown_exported_name"
    PRIVATE_OR_UNEXPORTED_DECLARATION = "private_or_unexported_declaration"
    INCONSISTENT_TARGET_FACADE = "inconsistent_target_facade"
    AMBIGUOUS_TARGET_FACADE = "ambiguous_target_facade"
    LOCAL_DECLARATION_COLLISION = "local_declaration_collision"
    IMPORT_BINDING_COLLISION = "import_binding_collision"
    DUPLICATE_SOURCE_REQUEST = "duplicate_source_request"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectImportedBindingIdentity:
    """The exact local identity owned by one importing module."""

    owning_module_path: str
    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    local_binding_name: str

    def __post_init__(self) -> None:
        """Reject values outside the eligible local-binding identity domain."""

        ProjectModuleIdentity(path=self.owning_module_path)
        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Imported binding identity requires a namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Imported binding identity requires a declaration kind.")
        if (
            self.namespace,
            self.declaration_kind,
        ) not in _ELIGIBLE_NAMESPACE_KIND_PAIRS:
            raise ValueError("Imported binding identity requires an eligible kind.")
        if type(self.local_binding_name) is not str or not self.local_binding_name:
            raise ValueError(
                "Imported binding identity requires a non-empty local name."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleImportRequest:
    """One exact source import item owned by one logical module."""

    identity: ProjectImportedBindingIdentity
    target_module_path: str
    exported_name: str
    module_statement_position: int
    item_position: int
    source_statement: ImportStatement
    source_item: ImportItem

    def __post_init__(self) -> None:
        """Reject request facts inconsistent with their retained AST values."""

        if type(self.identity) is not ProjectImportedBindingIdentity:
            raise TypeError("Module import request requires a binding identity.")
        if type(self.target_module_path) is not str:
            raise TypeError("Module import request requires a raw target string.")
        if type(self.exported_name) is not str or not self.exported_name:
            raise ValueError("Module import request requires an exported name.")
        if (
            type(self.module_statement_position) is not int
            or self.module_statement_position < 0
        ):
            raise ValueError(
                "Module import statement position must be a non-negative integer."
            )
        if type(self.item_position) is not int or self.item_position < 0:
            raise ValueError(
                "Module import item position must be a non-negative integer."
            )
        if type(self.source_statement) is not ImportStatement:
            raise TypeError("Module import request requires an import statement.")
        if type(self.source_item) is not ImportItem:
            raise TypeError("Module import request requires an import item.")
        namespace, declaration_kind = _IMPORT_KIND_MAP[
            self.source_item.declaration_kind
        ]
        local_binding_name = (
            self.source_item.local_name
            if self.source_item.local_name is not None
            else self.source_item.exported_name
        )
        if (
            self.source_statement.target != self.target_module_path
            or self.item_position >= len(self.source_statement.items)
            or self.source_statement.items[self.item_position] is not self.source_item
            or namespace is not self.identity.namespace
            or declaration_kind is not self.identity.declaration_kind
            or self.source_item.exported_name != self.exported_name
            or local_binding_name != self.identity.local_binding_name
        ):
            raise ValueError("Module import request must match its retained AST item.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResolvedImportedBinding:
    """One unambiguous local binding to one direct target-facade entry."""

    identity: ProjectImportedBindingIdentity
    target_module_path: str
    target_identity: ProjectNominalDeclarationIdentity
    request: ProjectModuleImportRequest
    resolved_entry: ProjectModuleExportEntry

    def __post_init__(self) -> None:
        """Reject bindings that rewrite either local or nominal identity."""

        if type(self.identity) is not ProjectImportedBindingIdentity:
            raise TypeError("Resolved import requires a binding identity.")
        ProjectModuleIdentity(path=self.target_module_path)
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Resolved import requires a nominal target identity.")
        if type(self.request) is not ProjectModuleImportRequest:
            raise TypeError("Resolved import requires a source request.")
        if type(self.resolved_entry) is not ProjectModuleExportEntry:
            raise TypeError("Resolved import requires a target-facade entry.")
        if (
            self.identity != self.request.identity
            or self.target_module_path != self.request.target_module_path
            or self.resolved_entry.owning_module_path != self.target_module_path
            or self.resolved_entry.namespace is not self.identity.namespace
            or self.resolved_entry.declaration_kind
            is not self.identity.declaration_kind
            or self.resolved_entry.exposed_name != self.request.exported_name
            or self.resolved_entry.target_identity != self.target_identity
            or self.target_identity.namespace is not self.identity.namespace
            or self.target_identity.declaration_kind
            is not self.identity.declaration_kind
        ):
            raise ValueError("Resolved import must retain its exact identities.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleBindingIssue:
    """One deterministic private import or binding-collision fact."""

    status: ProjectModuleBindingIssueStatus
    request: ProjectModuleImportRequest
    target_surfaces: tuple[ProjectModuleExportSurface, ...] = ()
    target_entries: tuple[ProjectModuleExportEntry, ...] = ()
    target_occurrences: tuple[ProjectDeclarationOccurrence, ...] = ()
    local_occurrences: tuple[ProjectDeclarationOccurrence, ...] = ()
    competing_requests: tuple[ProjectModuleImportRequest, ...] = ()
    prior_requests: tuple[ProjectModuleImportRequest, ...] = ()

    def __post_init__(self) -> None:
        """Reject malformed or status-inconsistent issue evidence."""

        if type(self.status) is not ProjectModuleBindingIssueStatus:
            raise TypeError("Module binding issue requires an exact status.")
        if type(self.request) is not ProjectModuleImportRequest:
            raise TypeError("Module binding issue requires a source request.")
        _require_tuple_items(
            self.target_surfaces,
            ProjectModuleExportSurface,
            "Module binding issue target surfaces",
        )
        _require_tuple_items(
            self.target_entries,
            ProjectModuleExportEntry,
            "Module binding issue target entries",
        )
        _require_tuple_items(
            self.target_occurrences,
            ProjectDeclarationOccurrence,
            "Module binding issue target occurrences",
        )
        _require_tuple_items(
            self.local_occurrences,
            ProjectDeclarationOccurrence,
            "Module binding issue local occurrences",
        )
        _require_tuple_items(
            self.competing_requests,
            ProjectModuleImportRequest,
            "Module binding issue competing requests",
        )
        _require_tuple_items(
            self.prior_requests,
            ProjectModuleImportRequest,
            "Module binding issue prior requests",
        )

        if any(
            surface.module.path != self.request.target_module_path
            for surface in self.target_surfaces
        ):
            raise ValueError("Target surfaces must match the requested module.")
        if any(
            entry.owning_module_path != self.request.target_module_path
            or entry.exposed_name != self.request.exported_name
            for entry in self.target_entries
        ):
            raise ValueError("Target entries must match the requested module and name.")
        if any(
            occurrence.identity.module_path != self.request.target_module_path
            for occurrence in self.target_occurrences
        ):
            raise ValueError("Target occurrences must match the requested module.")
        if any(
            occurrence.identity.module_path != self.request.identity.owning_module_path
            or occurrence.identity.declared_name
            != self.request.identity.local_binding_name
            for occurrence in self.local_occurrences
        ):
            raise ValueError("Local occurrences must match the importing binding.")
        if any(
            item.identity.owning_module_path != self.request.identity.owning_module_path
            or item.identity.local_binding_name
            != self.request.identity.local_binding_name
            or item == self.request
            for item in self.competing_requests
        ):
            raise ValueError("Competing requests must prove one local-name collision.")
        request_position = (
            self.request.module_statement_position,
            self.request.item_position,
        )
        if any(
            _request_exact_key(item) != _request_exact_key(self.request)
            or (
                item.module_statement_position,
                item.item_position,
            )
            >= request_position
            for item in self.prior_requests
        ):
            raise ValueError("Prior requests must be earlier exact duplicates.")

        surface_entries = tuple(
            entry for surface in self.target_surfaces for entry in surface.entries
        )
        if self.target_entries and any(
            entry not in surface_entries for entry in self.target_entries
        ):
            raise ValueError("Target entries must belong to the retained surfaces.")

        no_target_evidence = not (
            self.target_surfaces or self.target_entries or self.target_occurrences
        )
        no_local_evidence = not self.local_occurrences
        no_competing_evidence = not self.competing_requests
        no_prior_evidence = not self.prior_requests

        if self.status is ProjectModuleBindingIssueStatus.UNRESOLVED_TARGET_MODULE:
            valid = (
                no_target_evidence
                and no_local_evidence
                and no_competing_evidence
                and no_prior_evidence
            )
        elif self.status is ProjectModuleBindingIssueStatus.UNKNOWN_EXPORTED_NAME:
            surface = (
                self.target_surfaces[0] if len(self.target_surfaces) == 1 else None
            )
            valid = (
                surface is not None
                and not self.target_entries
                and not self.target_occurrences
                and not any(
                    entry.exposed_name == self.request.exported_name
                    for entry in surface.entries
                )
                and no_local_evidence
                and no_competing_evidence
                and no_prior_evidence
            )
        elif (
            self.status
            is ProjectModuleBindingIssueStatus.PRIVATE_OR_UNEXPORTED_DECLARATION
        ):
            surface = (
                self.target_surfaces[0] if len(self.target_surfaces) == 1 else None
            )
            valid = (
                surface is not None
                and not self.target_entries
                and bool(self.target_occurrences)
                and all(
                    occurrence.identity.declared_name == self.request.exported_name
                    and occurrence.identity.namespace is self.request.identity.namespace
                    and occurrence.identity.declaration_kind
                    is self.request.identity.declaration_kind
                    for occurrence in self.target_occurrences
                )
                and not any(
                    entry.exposed_name == self.request.exported_name
                    for entry in surface.entries
                )
                and no_local_evidence
                and no_competing_evidence
                and no_prior_evidence
            )
        elif self.status is ProjectModuleBindingIssueStatus.INCONSISTENT_TARGET_FACADE:
            if len(self.target_surfaces) == 1:
                surface = self.target_surfaces[0]
                name_entries = tuple(
                    entry
                    for entry in surface.entries
                    if entry.exposed_name == self.request.exported_name
                )
                exact_entries = tuple(
                    entry
                    for entry in name_entries
                    if entry.namespace is self.request.identity.namespace
                    and entry.declaration_kind is self.request.identity.declaration_kind
                )
                named_occurrences = all(
                    occurrence.identity.declared_name == self.request.exported_name
                    for occurrence in self.target_occurrences
                )
                exact_occurrences = tuple(
                    occurrence
                    for occurrence in self.target_occurrences
                    if occurrence.identity.namespace is self.request.identity.namespace
                    and occurrence.identity.declaration_kind
                    is self.request.identity.declaration_kind
                )
                target_evidence_is_inconsistent = (
                    self.target_entries == name_entries
                    and not exact_entries
                    and named_occurrences
                    and (
                        bool(name_entries)
                        or (bool(self.target_occurrences) and not exact_occurrences)
                    )
                )
            else:
                target_evidence_is_inconsistent = len(self.target_surfaces) > 1 or bool(
                    self.target_occurrences
                )
            valid = (
                target_evidence_is_inconsistent
                and no_local_evidence
                and no_competing_evidence
                and no_prior_evidence
            )
        elif self.status is ProjectModuleBindingIssueStatus.AMBIGUOUS_TARGET_FACADE:
            surface = (
                self.target_surfaces[0] if len(self.target_surfaces) == 1 else None
            )
            exact_entries = (
                ()
                if surface is None
                else tuple(
                    entry
                    for entry in surface.entries
                    if entry.exposed_name == self.request.exported_name
                    and entry.namespace is self.request.identity.namespace
                    and entry.declaration_kind is self.request.identity.declaration_kind
                )
            )
            valid = (
                len(exact_entries) > 1
                and self.target_entries == exact_entries
                and not self.target_occurrences
                and no_local_evidence
                and no_competing_evidence
                and no_prior_evidence
            )
        elif self.status is ProjectModuleBindingIssueStatus.LOCAL_DECLARATION_COLLISION:
            valid = (
                no_target_evidence
                and bool(self.local_occurrences)
                and no_competing_evidence
                and no_prior_evidence
            )
        elif self.status is ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION:
            valid = (
                no_target_evidence
                and no_local_evidence
                and bool(self.competing_requests)
                and no_prior_evidence
            )
        else:
            valid = (
                no_target_evidence
                and no_local_evidence
                and no_competing_evidence
                and bool(self.prior_requests)
            )
        if not valid:
            raise ValueError("Module binding issue evidence must prove its status.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleBindingEnvironment:
    """One immutable local import environment for one parsed module."""

    module: ProjectLogicalModule
    requests: tuple[ProjectModuleImportRequest, ...] = ()
    bindings: tuple[ProjectResolvedImportedBinding, ...] = ()
    issues: tuple[ProjectModuleBindingIssue, ...] = ()
    _bindings_by_identity: Mapping[
        ProjectImportedBindingIdentity,
        tuple[ProjectResolvedImportedBinding, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Reject incomplete, reordered, foreign, or winner-selecting facts."""

        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Module binding environment requires a logical module.")
        if self.module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
            raise ValueError("Module binding environment requires explicit mode.")
        if self.module.parsed_input is None:
            raise ValueError("Module binding environment requires a parsed module.")
        _require_tuple_items(
            self.requests,
            ProjectModuleImportRequest,
            "Module binding environment requests",
        )
        _require_tuple_items(
            self.bindings,
            ProjectResolvedImportedBinding,
            "Module binding environment bindings",
        )
        _require_tuple_items(
            self.issues,
            ProjectModuleBindingIssue,
            "Module binding environment issues",
        )
        if self.requests != _build_import_requests(self.module):
            raise ValueError("Module binding environment must retain every request.")
        request_positions = {
            request: position for position, request in enumerate(self.requests)
        }
        if any(
            binding.request not in request_positions
            or binding.identity.owning_module_path != self.module.path
            for binding in self.bindings
        ):
            raise ValueError("Module bindings must belong to their environment.")
        if any(
            issue.request not in request_positions
            or issue.request.identity.owning_module_path != self.module.path
            for issue in self.issues
        ):
            raise ValueError("Module binding issues must belong to their environment.")
        binding_positions = tuple(
            request_positions[binding.request] for binding in self.bindings
        )
        if binding_positions != tuple(sorted(binding_positions)) or len(
            set(binding_positions)
        ) != len(binding_positions):
            raise ValueError("Module bindings must be unique and request ordered.")
        issue_rank = {
            status: position
            for position, status in enumerate(ProjectModuleBindingIssueStatus)
        }
        issue_keys = tuple(
            (request_positions[issue.request], issue_rank[issue.status])
            for issue in self.issues
        )
        if issue_keys != tuple(sorted(issue_keys)) or len(
            {(request_positions[issue.request], issue.status) for issue in self.issues}
        ) != len(self.issues):
            raise ValueError(
                "Module binding issues must be unique and request ordered."
            )

        binding_requests = {binding.request for binding in self.bindings}
        blocking_issue_requests = {
            issue.request
            for issue in self.issues
            if issue.status
            is not ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST
        }
        if binding_requests & blocking_issue_requests:
            raise ValueError("A colliding or unresolved request cannot have a winner.")
        if binding_requests | blocking_issue_requests != set(self.requests):
            raise ValueError("Every import request requires one resolution outcome.")

        issues_by_request = {
            request: tuple(issue for issue in self.issues if issue.request == request)
            for request in self.requests
        }
        local_definitions_by_name: dict[str, list[tuple[int, object]]] = {}
        for position, definition in enumerate(
            self.module.parsed_input.script.definitions
        ):
            local_definitions_by_name.setdefault(definition.name, []).append(
                (position, definition)
            )
        requests_by_local_name: dict[str, list[ProjectModuleImportRequest]] = {}
        prior_requests_by_exact_key: dict[
            tuple[str, str, ProjectSymbolNamespace, ProjectSymbolKind, str, str],
            list[ProjectModuleImportRequest],
        ] = {}
        for request in self.requests:
            requests_by_local_name.setdefault(
                request.identity.local_binding_name, []
            ).append(request)

        collision_requests: set[ProjectModuleImportRequest] = set()
        for request in self.requests:
            request_issues = issues_by_request[request]
            local_definitions = tuple(
                local_definitions_by_name.get(
                    request.identity.local_binding_name,
                    (),
                )
            )
            local_issues = tuple(
                issue
                for issue in request_issues
                if issue.status
                is ProjectModuleBindingIssueStatus.LOCAL_DECLARATION_COLLISION
            )
            if bool(local_definitions) != bool(local_issues):
                raise ValueError("Local declaration collisions require exact evidence.")
            if local_definitions:
                collision_requests.add(request)
                if len(local_issues) != 1 or len(
                    local_issues[0].local_occurrences
                ) != len(local_definitions):
                    raise ValueError(
                        "Local declaration collisions require complete evidence."
                    )
                for occurrence, (position, definition) in zip(
                    local_issues[0].local_occurrences,
                    local_definitions,
                    strict=True,
                ):
                    if (
                        occurrence.module_position != self.module.position
                        or occurrence.declaration_position != position
                        or occurrence.definition is not definition
                    ):
                        raise ValueError(
                            "Local collision evidence must retain source definitions."
                        )

            competing_requests = tuple(
                item
                for item in requests_by_local_name[request.identity.local_binding_name]
                if item != request
            )
            competing_issues = tuple(
                issue
                for issue in request_issues
                if issue.status
                is ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION
            )
            if bool(competing_requests) != bool(competing_issues):
                raise ValueError("Import binding collisions require exact evidence.")
            if competing_requests:
                collision_requests.add(request)
                if (
                    len(competing_issues) != 1
                    or competing_issues[0].competing_requests != competing_requests
                ):
                    raise ValueError(
                        "Import binding collisions require complete evidence."
                    )

            exact_key = _request_exact_key(request)
            prior_requests = tuple(
                prior_requests_by_exact_key.setdefault(exact_key, [])
            )
            duplicate_issues = tuple(
                issue
                for issue in request_issues
                if issue.status
                is ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST
            )
            if bool(prior_requests) != bool(duplicate_issues):
                raise ValueError("Duplicate requests require exact prior evidence.")
            if prior_requests and (
                len(duplicate_issues) != 1
                or duplicate_issues[0].prior_requests != prior_requests
            ):
                raise ValueError("Duplicate requests require complete prior evidence.")
            prior_requests_by_exact_key[exact_key].append(request)

        if binding_requests & collision_requests:
            raise ValueError("A colliding local binding cannot have a winner.")

        by_identity: dict[
            ProjectImportedBindingIdentity,
            list[ProjectResolvedImportedBinding],
        ] = {}
        for binding in self.bindings:
            by_identity.setdefault(binding.identity, []).append(binding)
        if any(len(items) != 1 for items in by_identity.values()):
            raise ValueError("Binding lookup buckets cannot select among candidates.")
        object.__setattr__(
            self,
            "_bindings_by_identity",
            MappingProxyType(
                {identity: tuple(items) for identity, items in by_identity.items()}
            ),
        )

    @property
    def import_statements(self) -> tuple[ImportStatement, ...]:
        """Return every retained import statement in module-statement order."""

        assert self.module.parsed_input is not None
        return tuple(
            statement
            for statement in self.module.parsed_input.script.module_statements
            if type(statement) is ImportStatement
        )

    def find_identity(
        self,
        identity: ProjectImportedBindingIdentity,
    ) -> tuple[ProjectResolvedImportedBinding, ...]:
        """Return the exact unambiguous local binding, or an empty tuple."""

        if type(identity) is not ProjectImportedBindingIdentity:
            raise TypeError("Module binding lookup requires a binding identity.")
        return self._bindings_by_identity.get(identity, ())


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleBindingEnvironmentSet:
    """Selected-input-ordered private module binding environments."""

    environments: tuple[ProjectModuleBindingEnvironment, ...] = ()
    imported_export_candidates: tuple[ProjectImportedExportCandidate, ...] = ()
    _environments_by_path: Mapping[str, ProjectModuleBindingEnvironment] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject reordered environments or rewritten Slice 6 candidates."""

        _require_tuple_items(
            self.environments,
            ProjectModuleBindingEnvironment,
            "Project module binding environments",
        )
        _require_tuple_items(
            self.imported_export_candidates,
            ProjectImportedExportCandidate,
            "Project imported export candidates",
        )
        environments_by_path: dict[str, ProjectModuleBindingEnvironment] = {}
        for position, environment in enumerate(self.environments):
            if environment.module.position != position:
                raise ValueError(
                    "Project binding environments must retain selected-input order."
                )
            if environment.module.path in environments_by_path:
                raise ValueError("Project binding environment paths must be unique.")
            environments_by_path[environment.module.path] = environment
        expected_candidates = tuple(
            _export_candidate(binding)
            for environment in self.environments
            for binding in environment.bindings
        )
        if self.imported_export_candidates != expected_candidates:
            raise ValueError(
                "Project binding environments must retain exact Slice 6 candidates."
            )
        object.__setattr__(
            self,
            "_environments_by_path",
            MappingProxyType(dict(environments_by_path)),
        )

    def find_module_path(
        self,
        module_path: str,
    ) -> tuple[ProjectModuleBindingEnvironment, ...]:
        """Return one exact environment for a valid module path, or empty."""

        try:
            ProjectModuleIdentity(path=module_path)
        except (TypeError, ValueError):
            return ()
        environment = self._environments_by_path.get(module_path)
        return () if environment is None else (environment,)


def _build_project_module_binding_environment_set(
    selected_input_index: ProjectSelectedInputIndex,
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
) -> ProjectModuleBindingEnvironmentSet:
    """Resolve named imports through one direct-facade candidate backfill."""

    _validate_builder_inputs(selected_input_index, modules, catalogs)
    local_facades = _build_project_module_export_surface_set(catalogs)
    initial_environments = _resolve_binding_environments(
        selected_input_index=selected_input_index,
        modules=modules,
        catalogs=catalogs,
        facades=local_facades,
    )
    backfilled_facades = _build_project_module_export_surface_set(
        catalogs,
        imported_binding_candidates=initial_environments.imported_export_candidates,
    )
    return _resolve_binding_environments(
        selected_input_index=selected_input_index,
        modules=modules,
        catalogs=catalogs,
        facades=backfilled_facades,
    )


def _resolve_binding_environments(
    *,
    selected_input_index: ProjectSelectedInputIndex,
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    facades: ProjectModuleExportSurfaceSet,
) -> ProjectModuleBindingEnvironmentSet:
    environments: list[ProjectModuleBindingEnvironment] = []
    for module in modules:
        requests = _build_import_requests(module)
        exact_prior_by_key: dict[
            tuple[str, str, ProjectSymbolNamespace, ProjectSymbolKind, str, str],
            list[ProjectModuleImportRequest],
        ] = {}
        requests_by_local_name: dict[str, list[ProjectModuleImportRequest]] = {}
        resolution_entries: dict[
            ProjectModuleImportRequest,
            ProjectModuleExportEntry | None,
        ] = {}
        issues_by_request: dict[
            ProjectModuleImportRequest,
            list[ProjectModuleBindingIssue],
        ] = {request: [] for request in requests}

        module_catalogs = catalogs.find_module_path(module.path)
        if len(module_catalogs) != 1:
            raise ValueError("Binding builder requires one exact owner catalog.")
        owner_catalog = module_catalogs[0]

        for request in requests:
            requests_by_local_name.setdefault(
                request.identity.local_binding_name, []
            ).append(request)
            exact_key = _request_exact_key(request)
            prior_requests = exact_prior_by_key.setdefault(exact_key, [])
            if prior_requests:
                issues_by_request[request].append(
                    ProjectModuleBindingIssue(
                        status=ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST,
                        request=request,
                        prior_requests=tuple(prior_requests),
                    )
                )
            prior_requests.append(request)

            selected_target = selected_input_index.find_path(request.target_module_path)
            if selected_target is None:
                resolution_entries[request] = None
                issues_by_request[request].append(
                    ProjectModuleBindingIssue(
                        status=ProjectModuleBindingIssueStatus.UNRESOLVED_TARGET_MODULE,
                        request=request,
                    )
                )
                continue

            target_surfaces = facades.find_module_path(request.target_module_path)
            target_catalogs = catalogs.find_module_path(request.target_module_path)
            if len(target_surfaces) != 1 or len(target_catalogs) != 1:
                resolution_entries[request] = None
                issues_by_request[request].append(
                    ProjectModuleBindingIssue(
                        status=ProjectModuleBindingIssueStatus.INCONSISTENT_TARGET_FACADE,
                        request=request,
                        target_surfaces=target_surfaces,
                        target_occurrences=tuple(
                            occurrence
                            for catalog in target_catalogs
                            for occurrence in catalog.occurrences
                        ),
                    )
                )
                continue

            target_surface = target_surfaces[0]
            target_catalog = target_catalogs[0]
            name_entries = tuple(
                entry
                for entry in target_surface.entries
                if entry.exposed_name == request.exported_name
            )
            exact_entries = tuple(
                entry
                for entry in name_entries
                if entry.namespace is request.identity.namespace
                and entry.declaration_kind is request.identity.declaration_kind
            )
            name_occurrences = tuple(
                occurrence
                for occurrence in target_catalog.occurrences
                if occurrence.identity.declared_name == request.exported_name
            )
            exact_occurrences = tuple(
                occurrence
                for occurrence in name_occurrences
                if occurrence.identity.namespace is request.identity.namespace
                and occurrence.identity.declaration_kind
                is request.identity.declaration_kind
            )

            if len(exact_entries) > 1:
                resolution_entries[request] = None
                issues_by_request[request].append(
                    ProjectModuleBindingIssue(
                        status=ProjectModuleBindingIssueStatus.AMBIGUOUS_TARGET_FACADE,
                        request=request,
                        target_surfaces=target_surfaces,
                        target_entries=exact_entries,
                    )
                )
            elif len(exact_entries) == 1:
                resolution_entries[request] = exact_entries[0]
            elif name_entries or (name_occurrences and not exact_occurrences):
                resolution_entries[request] = None
                issues_by_request[request].append(
                    ProjectModuleBindingIssue(
                        status=ProjectModuleBindingIssueStatus.INCONSISTENT_TARGET_FACADE,
                        request=request,
                        target_surfaces=target_surfaces,
                        target_entries=name_entries,
                        target_occurrences=name_occurrences,
                    )
                )
            elif exact_occurrences:
                resolution_entries[request] = None
                issues_by_request[request].append(
                    ProjectModuleBindingIssue(
                        status=ProjectModuleBindingIssueStatus.PRIVATE_OR_UNEXPORTED_DECLARATION,
                        request=request,
                        target_surfaces=target_surfaces,
                        target_occurrences=exact_occurrences,
                    )
                )
            else:
                resolution_entries[request] = None
                issues_by_request[request].append(
                    ProjectModuleBindingIssue(
                        status=ProjectModuleBindingIssueStatus.UNKNOWN_EXPORTED_NAME,
                        request=request,
                        target_surfaces=target_surfaces,
                    )
                )

        bindings: list[ProjectResolvedImportedBinding] = []
        for request in requests:
            local_occurrences = tuple(
                occurrence
                for occurrence in owner_catalog.occurrences
                if occurrence.identity.declared_name
                == request.identity.local_binding_name
            )
            if local_occurrences:
                issues_by_request[request].append(
                    ProjectModuleBindingIssue(
                        status=ProjectModuleBindingIssueStatus.LOCAL_DECLARATION_COLLISION,
                        request=request,
                        local_occurrences=local_occurrences,
                    )
                )
            local_name_requests = requests_by_local_name[
                request.identity.local_binding_name
            ]
            competing_requests = tuple(
                item for item in local_name_requests if item != request
            )
            if competing_requests:
                issues_by_request[request].append(
                    ProjectModuleBindingIssue(
                        status=ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION,
                        request=request,
                        competing_requests=competing_requests,
                    )
                )

            target_entry = resolution_entries[request]
            blocking_issues = tuple(
                issue
                for issue in issues_by_request[request]
                if issue.status
                is not ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST
            )
            if target_entry is not None and not blocking_issues:
                bindings.append(
                    ProjectResolvedImportedBinding(
                        identity=request.identity,
                        target_module_path=request.target_module_path,
                        target_identity=target_entry.target_identity,
                        request=request,
                        resolved_entry=target_entry,
                    )
                )

        issues = tuple(
            issue
            for request in requests
            for issue in sorted(
                issues_by_request[request],
                key=lambda item: tuple(ProjectModuleBindingIssueStatus).index(
                    item.status
                ),
            )
        )
        environments.append(
            ProjectModuleBindingEnvironment(
                module=module,
                requests=requests,
                bindings=tuple(bindings),
                issues=issues,
            )
        )

    environment_tuple = tuple(environments)
    candidates = tuple(
        _export_candidate(binding)
        for environment in environment_tuple
        for binding in environment.bindings
    )
    return ProjectModuleBindingEnvironmentSet(
        environments=environment_tuple,
        imported_export_candidates=candidates,
    )


def _build_import_requests(
    module: ProjectLogicalModule,
) -> tuple[ProjectModuleImportRequest, ...]:
    if type(module) is not ProjectLogicalModule:
        raise TypeError("Module import request builder requires a logical module.")
    if module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
        raise ValueError("Module import request builder rejects legacy modules.")
    if module.parsed_input is None:
        raise ValueError("Module import request builder requires a parsed module.")

    requests: list[ProjectModuleImportRequest] = []
    for statement_position, statement in enumerate(
        module.parsed_input.script.module_statements
    ):
        if type(statement) is not ImportStatement:
            continue
        for item_position, source_item in enumerate(statement.items):
            namespace, declaration_kind = _IMPORT_KIND_MAP[source_item.declaration_kind]
            local_binding_name = (
                source_item.local_name
                if source_item.local_name is not None
                else source_item.exported_name
            )
            requests.append(
                ProjectModuleImportRequest(
                    identity=ProjectImportedBindingIdentity(
                        owning_module_path=module.path,
                        namespace=namespace,
                        declaration_kind=declaration_kind,
                        local_binding_name=local_binding_name,
                    ),
                    target_module_path=statement.target,
                    exported_name=source_item.exported_name,
                    module_statement_position=statement_position,
                    item_position=item_position,
                    source_statement=statement,
                    source_item=source_item,
                )
            )
    return tuple(requests)


def _export_candidate(
    binding: ProjectResolvedImportedBinding,
) -> ProjectImportedExportCandidate:
    source_span = (
        binding.request.source_item.local_name_span
        if binding.request.source_item.local_name_span is not None
        else binding.request.source_item.exported_name_span
    )
    return ProjectImportedExportCandidate(
        owning_module_path=binding.identity.owning_module_path,
        namespace=binding.identity.namespace,
        declaration_kind=binding.identity.declaration_kind,
        local_binding_name=binding.identity.local_binding_name,
        target_identity=binding.target_identity,
        proof=ProjectImportedBindingCandidateProof.EXPLICIT_NAMED_IMPORT,
        module_statement_position=binding.request.module_statement_position,
        item_position=binding.request.item_position,
        source_span=source_span,
    )


def _validate_builder_inputs(
    selected_input_index: ProjectSelectedInputIndex,
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
) -> None:
    if type(selected_input_index) is not ProjectSelectedInputIndex:
        raise TypeError("Module binding builder requires a selected-input index.")
    if type(modules) is not tuple or any(
        type(module) is not ProjectLogicalModule for module in modules
    ):
        raise TypeError("Module binding builder requires a logical-module tuple.")
    if type(catalogs) is not ProjectModuleCatalogSet:
        raise TypeError("Module binding builder requires a project catalog set.")
    if len(modules) != len(catalogs.catalogs) or len(modules) != len(
        selected_input_index.entries
    ):
        raise ValueError("Module binding builder inputs must cover the same modules.")
    for position, (module, catalog, selected_entry) in enumerate(
        zip(
            modules,
            catalogs.catalogs,
            selected_input_index.entries,
            strict=True,
        )
    ):
        if (
            module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or module.position != position
            or module.parsed_input is None
            or catalog.module is not module
            or selected_entry.position != position
            or selected_entry.identity.path != module.path
        ):
            raise ValueError(
                "Module binding builder inputs must retain selected-input order."
            )


def _request_exact_key(
    request: ProjectModuleImportRequest,
) -> tuple[str, str, ProjectSymbolNamespace, ProjectSymbolKind, str, str]:
    return (
        request.identity.owning_module_path,
        request.target_module_path,
        request.identity.namespace,
        request.identity.declaration_kind,
        request.exported_name,
        request.identity.local_binding_name,
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
