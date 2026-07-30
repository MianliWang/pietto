"""Private schema-v2 module export requests and facade surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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
from pietto.ast_nodes import (
    ExportItem,
    ExportStatement,
    ModuleDeclarationKind,
    Span,
)

__all__: tuple[str, ...] = ()


class ProjectModuleExportEntryOrigin(StrEnum):
    """The exact direct origin of one resolved facade entry."""

    LOCAL_DECLARATION = "local_declaration"
    EXPLICIT_REEXPORT = "explicit_reexport"


class ProjectImportedBindingCandidateProof(StrEnum):
    """The only imported-binding proof accepted by the Slice 6 seam."""

    EXPLICIT_NAMED_IMPORT = "explicit_named_import"


class ProjectModuleExportIssueStatus(StrEnum):
    """Private fail-closed classifications retained for Slice 8 adaptation."""

    UNRESOLVED_EXPORT_BINDING = "unresolved_export_binding"
    AMBIGUOUS_LOCAL_DECLARATION = "ambiguous_local_declaration"
    AMBIGUOUS_CANDIDATE_SET = "ambiguous_candidate_set"
    INELIGIBLE_OR_INCONSISTENT_CANDIDATE = "ineligible_or_inconsistent_candidate"
    DUPLICATE_SOURCE_REQUEST = "duplicate_source_request"


_ELIGIBLE_EXPORT_KIND_MAP = {
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
_ELIGIBLE_NAMESPACE_KIND_PAIRS = frozenset(_ELIGIBLE_EXPORT_KIND_MAP.values())


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleExportRequest:
    """One exact source export item owned by one logical module."""

    owning_module_path: str
    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    local_name: str
    module_statement_position: int
    item_position: int
    source_item: ExportItem

    def __post_init__(self) -> None:
        """Reject request facts inconsistent with the retained source item."""

        ProjectModuleIdentity(path=self.owning_module_path)
        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Module export request requires a namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Module export request requires a declaration kind.")
        if type(self.local_name) is not str or not self.local_name:
            raise ValueError("Module export request requires a non-empty local name.")
        if (
            type(self.module_statement_position) is not int
            or self.module_statement_position < 0
        ):
            raise ValueError(
                "Module export statement position must be a non-negative integer."
            )
        if type(self.item_position) is not int or self.item_position < 0:
            raise ValueError(
                "Module export item position must be a non-negative integer."
            )
        if type(self.source_item) is not ExportItem:
            raise TypeError("Module export request requires an export item.")
        expected = _ELIGIBLE_EXPORT_KIND_MAP[self.source_item.declaration_kind]
        if (
            expected != (self.namespace, self.declaration_kind)
            or self.source_item.local_name != self.local_name
        ):
            raise ValueError(
                "Module export request must match its retained export item."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectImportedExportCandidate:
    """One caller-resolved explicit named imported local binding candidate."""

    owning_module_path: str
    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    local_binding_name: str
    target_identity: ProjectNominalDeclarationIdentity
    proof: ProjectImportedBindingCandidateProof
    module_statement_position: int
    item_position: int
    source_span: Span

    def __post_init__(self) -> None:
        """Reject facts outside the narrow explicit named-import seam."""

        ProjectModuleIdentity(path=self.owning_module_path)
        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Imported export candidate requires a namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Imported export candidate requires a declaration kind.")
        if (
            self.namespace,
            self.declaration_kind,
        ) not in _ELIGIBLE_NAMESPACE_KIND_PAIRS:
            raise ValueError("Imported export candidate requires an eligible kind.")
        if type(self.local_binding_name) is not str or not self.local_binding_name:
            raise ValueError(
                "Imported export candidate requires a non-empty local binding name."
            )
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError(
                "Imported export candidate requires a nominal target identity."
            )
        if type(self.proof) is not ProjectImportedBindingCandidateProof:
            raise TypeError("Imported export candidate requires an exact proof.")
        if (
            type(self.module_statement_position) is not int
            or self.module_statement_position < 0
        ):
            raise ValueError(
                "Imported binding statement position must be non-negative."
            )
        if type(self.item_position) is not int or self.item_position < 0:
            raise ValueError("Imported binding item position must be non-negative.")
        if type(self.source_span) is not Span:
            raise TypeError("Imported export candidate requires a source span.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleExportEntry:
    """One resolved local export or direct explicit named re-export."""

    owning_module_path: str
    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    exposed_name: str
    origin: ProjectModuleExportEntryOrigin
    target_identity: ProjectNominalDeclarationIdentity
    request: ProjectModuleExportRequest
    resolved_from: ProjectDeclarationOccurrence | ProjectImportedExportCandidate

    def __post_init__(self) -> None:
        """Reject entries inconsistent with their request and exact origin."""

        ProjectModuleIdentity(path=self.owning_module_path)
        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Module export entry requires a namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Module export entry requires a declaration kind.")
        if type(self.exposed_name) is not str or not self.exposed_name:
            raise ValueError("Module export entry requires an exposed name.")
        if type(self.origin) is not ProjectModuleExportEntryOrigin:
            raise TypeError("Module export entry requires an exact origin.")
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Module export entry requires a target identity.")
        if type(self.request) is not ProjectModuleExportRequest:
            raise TypeError("Module export entry requires a source request.")
        if (
            self.owning_module_path != self.request.owning_module_path
            or self.namespace is not self.request.namespace
            or self.declaration_kind is not self.request.declaration_kind
            or self.exposed_name != self.request.local_name
        ):
            raise ValueError("Module export entry must match its source request.")

        if self.origin is ProjectModuleExportEntryOrigin.LOCAL_DECLARATION:
            if type(self.resolved_from) is not ProjectDeclarationOccurrence:
                raise TypeError(
                    "Local module export entry requires a declaration occurrence."
                )
            expected_identity = ProjectNominalDeclarationIdentity(
                module_path=self.owning_module_path,
                namespace=self.namespace,
                declaration_kind=self.declaration_kind,
                declared_name=self.request.local_name,
            )
            if (
                self.resolved_from.identity != self.target_identity
                or self.target_identity != expected_identity
            ):
                raise ValueError(
                    "Local module export entry must retain its local identity."
                )
        else:
            if type(self.resolved_from) is not ProjectImportedExportCandidate:
                raise TypeError(
                    "Explicit re-export entry requires an imported candidate."
                )
            if (
                self.resolved_from.owning_module_path != self.owning_module_path
                or self.resolved_from.namespace is not self.namespace
                or self.resolved_from.declaration_kind is not self.declaration_kind
                or self.resolved_from.local_binding_name != self.request.local_name
                or self.resolved_from.target_identity != self.target_identity
                or self.target_identity.namespace is not self.namespace
                or self.target_identity.declaration_kind is not self.declaration_kind
            ):
                raise ValueError(
                    "Explicit re-export entry must retain its imported target."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleExportIssue:
    """One deterministic private export-validation issue fact."""

    status: ProjectModuleExportIssueStatus
    request: ProjectModuleExportRequest
    local_occurrences: tuple[ProjectDeclarationOccurrence, ...] = ()
    imported_candidates: tuple[ProjectImportedExportCandidate, ...] = ()
    prior_requests: tuple[ProjectModuleExportRequest, ...] = ()

    def __post_init__(self) -> None:
        """Reject malformed or status-inconsistent issue evidence."""

        if type(self.status) is not ProjectModuleExportIssueStatus:
            raise TypeError("Module export issue requires an exact status.")
        if type(self.request) is not ProjectModuleExportRequest:
            raise TypeError("Module export issue requires a source request.")
        if type(self.local_occurrences) is not tuple or any(
            type(item) is not ProjectDeclarationOccurrence
            for item in self.local_occurrences
        ):
            raise TypeError("Module export issue occurrences must be a tuple.")
        if type(self.imported_candidates) is not tuple or any(
            type(item) is not ProjectImportedExportCandidate
            for item in self.imported_candidates
        ):
            raise TypeError("Module export issue candidates must be a tuple.")
        if type(self.prior_requests) is not tuple or any(
            type(item) is not ProjectModuleExportRequest for item in self.prior_requests
        ):
            raise TypeError("Module export issue prior requests must be a tuple.")

        expected_local_identity = ProjectNominalDeclarationIdentity(
            module_path=self.request.owning_module_path,
            namespace=self.request.namespace,
            declaration_kind=self.request.declaration_kind,
            declared_name=self.request.local_name,
        )
        if any(
            occurrence.identity != expected_local_identity
            for occurrence in self.local_occurrences
        ):
            raise ValueError(
                "Module export issue local evidence must match its request."
            )
        if any(
            candidate.owning_module_path != self.request.owning_module_path
            or candidate.local_binding_name != self.request.local_name
            for candidate in self.imported_candidates
        ):
            raise ValueError(
                "Module export issue imported evidence must match its request owner and name."
            )
        request_position = (
            self.request.module_statement_position,
            self.request.item_position,
        )
        if any(
            prior.owning_module_path != self.request.owning_module_path
            or prior.namespace is not self.request.namespace
            or prior.declaration_kind is not self.request.declaration_kind
            or prior.local_name != self.request.local_name
            or (prior.module_statement_position, prior.item_position)
            >= request_position
            for prior in self.prior_requests
        ):
            raise ValueError(
                "Duplicate export evidence must contain only earlier exact requests."
            )

        exact_imported_candidates = tuple(
            candidate
            for candidate in self.imported_candidates
            if candidate.namespace is self.request.namespace
            and candidate.declaration_kind is self.request.declaration_kind
            and candidate.target_identity.namespace is candidate.namespace
            and candidate.target_identity.declaration_kind is candidate.declaration_kind
        )
        if self.status is ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING:
            valid = not (
                self.local_occurrences
                or self.imported_candidates
                or self.prior_requests
            )
        elif self.status is ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION:
            valid = len(self.local_occurrences) > 1 and not self.prior_requests
        elif self.status is ProjectModuleExportIssueStatus.AMBIGUOUS_CANDIDATE_SET:
            valid = (
                len(self.local_occurrences) <= 1
                and len(self.local_occurrences) + len(exact_imported_candidates) > 1
                and len(exact_imported_candidates) == len(self.imported_candidates)
                and not self.prior_requests
            )
        elif (
            self.status
            is ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE
        ):
            valid = (
                bool(self.imported_candidates)
                and len(self.local_occurrences) <= 1
                and len(exact_imported_candidates) < len(self.imported_candidates)
                and not self.prior_requests
            )
        else:
            valid = (
                bool(self.prior_requests)
                and not self.local_occurrences
                and not self.imported_candidates
            )
        if not valid:
            raise ValueError(
                "Module export issue evidence must prove its exact status."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleExportSurface:
    """One immutable private facade for one parsed logical module."""

    module: ProjectLogicalModule
    requests: tuple[ProjectModuleExportRequest, ...] = ()
    entries: tuple[ProjectModuleExportEntry, ...] = ()
    issues: tuple[ProjectModuleExportIssue, ...] = ()

    def __post_init__(self) -> None:
        """Reject reordered, foreign, or malformed facade facts."""

        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Module export surface requires a logical module.")
        if self.module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
            raise ValueError("Module export surface requires explicit-module mode.")
        if self.module.parsed_input is None:
            raise ValueError("Module export surface requires a parsed module.")
        if type(self.requests) is not tuple or any(
            type(item) is not ProjectModuleExportRequest for item in self.requests
        ):
            raise TypeError("Module export surface requests must be a tuple.")
        if type(self.entries) is not tuple or any(
            type(item) is not ProjectModuleExportEntry for item in self.entries
        ):
            raise TypeError("Module export surface entries must be a tuple.")
        if type(self.issues) is not tuple or any(
            type(item) is not ProjectModuleExportIssue for item in self.issues
        ):
            raise TypeError("Module export surface issues must be a tuple.")

        expected_requests: list[ProjectModuleExportRequest] = []
        for statement_position, statement in enumerate(
            self.module.parsed_input.script.module_statements
        ):
            if type(statement) is not ExportStatement:
                continue
            for item_position, source_item in enumerate(statement.items):
                namespace, declaration_kind = _ELIGIBLE_EXPORT_KIND_MAP[
                    source_item.declaration_kind
                ]
                expected_requests.append(
                    ProjectModuleExportRequest(
                        owning_module_path=self.module.path,
                        namespace=namespace,
                        declaration_kind=declaration_kind,
                        local_name=source_item.local_name,
                        module_statement_position=statement_position,
                        item_position=item_position,
                        source_item=source_item,
                    )
                )
        if self.requests != tuple(expected_requests):
            raise ValueError(
                "Module export surface must retain every source-ordered request."
            )
        if any(
            entry.owning_module_path != self.module.path
            or entry.request not in self.requests
            for entry in self.entries
        ):
            raise ValueError("Module export surface entries must belong to its module.")
        if any(
            issue.request.owning_module_path != self.module.path
            or issue.request not in self.requests
            for issue in self.issues
        ):
            raise ValueError("Module export surface issues must belong to its module.")
        request_positions = {
            request: position for position, request in enumerate(self.requests)
        }
        entry_positions = tuple(
            request_positions[entry.request] for entry in self.entries
        )
        if entry_positions != tuple(sorted(entry_positions)) or len(
            set(entry_positions)
        ) != len(entry_positions):
            raise ValueError(
                "Module export surface entries must be unique and request ordered."
            )
        issue_rank = {
            ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST: 0,
            ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION: 1,
            ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE: 2,
            ProjectModuleExportIssueStatus.AMBIGUOUS_CANDIDATE_SET: 3,
            ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING: 4,
        }
        issue_keys = tuple(
            (request_positions[issue.request], issue_rank[issue.status])
            for issue in self.issues
        )
        if issue_keys != tuple(sorted(issue_keys)) or len(
            {(request_positions[issue.request], issue.status) for issue in self.issues}
        ) != len(self.issues):
            raise ValueError(
                "Module export surface issues must be unique and request ordered."
            )
        entry_requests = {entry.request for entry in self.entries}
        for request in self.requests:
            resolution_issues = tuple(
                issue
                for issue in self.issues
                if issue.request == request
                and issue.status
                is not ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST
            )
            if (request in entry_requests) + len(resolution_issues) != 1:
                raise ValueError(
                    "Each module export request requires one exact resolution outcome."
                )

    @property
    def export_statements(self) -> tuple[ExportStatement, ...]:
        """Return every retained export statement in module-statement order."""

        assert self.module.parsed_input is not None
        return tuple(
            statement
            for statement in self.module.parsed_input.script.module_statements
            if type(statement) is ExportStatement
        )

    def find_namespace_kind_name(
        self,
        namespace: ProjectSymbolNamespace,
        declaration_kind: ProjectSymbolKind,
        exposed_name: str,
    ) -> tuple[ProjectModuleExportEntry, ...]:
        """Return every entry in one exact facade lookup bucket."""

        if type(namespace) is not ProjectSymbolNamespace:
            raise TypeError("Module export lookup requires a namespace.")
        if type(declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Module export lookup requires a declaration kind.")
        if type(exposed_name) is not str:
            raise TypeError("Module export lookup requires an exposed name.")
        return tuple(
            entry
            for entry in self.entries
            if entry.namespace is namespace
            and entry.declaration_kind is declaration_kind
            and entry.exposed_name == exposed_name
        )

    def find_target_identity(
        self,
        identity: ProjectNominalDeclarationIdentity,
    ) -> tuple[ProjectModuleExportEntry, ...]:
        """Return every source-ordered entry for one exact target identity."""

        if type(identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Module export lookup requires a nominal identity.")
        return tuple(
            entry for entry in self.entries if entry.target_identity == identity
        )

    def is_local_declaration_visible(
        self,
        identity: ProjectNominalDeclarationIdentity,
    ) -> bool:
        """Return whether one exact local identity has a resolved local export."""

        if type(identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Module visibility lookup requires a nominal identity.")
        return any(
            entry.origin is ProjectModuleExportEntryOrigin.LOCAL_DECLARATION
            and entry.target_identity == identity
            for entry in self.entries
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleExportSurfaceSet:
    """An immutable selected-input-ordered set of private module facades."""

    surfaces: tuple[ProjectModuleExportSurface, ...] = ()

    def __post_init__(self) -> None:
        """Reject malformed, duplicate, or reordered facade sets."""

        if type(self.surfaces) is not tuple:
            raise TypeError("Project module export surfaces must be a tuple.")
        module_paths: set[str] = set()
        for position, surface in enumerate(self.surfaces):
            if type(surface) is not ProjectModuleExportSurface:
                raise TypeError("Project export set requires module surfaces.")
            if surface.module.position != position:
                raise ValueError(
                    "Project export surfaces must retain selected-input order."
                )
            if surface.module.path in module_paths:
                raise ValueError("Project export surface paths must be unique.")
            module_paths.add(surface.module.path)

    def find_module_path(
        self,
        module_path: str,
    ) -> tuple[ProjectModuleExportSurface, ...]:
        """Return the exact surface for a valid module path, or an empty tuple."""

        try:
            ProjectModuleIdentity(path=module_path)
        except (TypeError, ValueError):
            return ()
        return tuple(
            surface for surface in self.surfaces if surface.module.path == module_path
        )

    def find_target_identity(
        self,
        identity: ProjectNominalDeclarationIdentity,
    ) -> tuple[ProjectModuleExportEntry, ...]:
        """Return every selected-input-ordered entry for one target identity."""

        if type(identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Project export lookup requires a nominal identity.")
        return tuple(
            entry
            for surface in self.surfaces
            for entry in surface.entries
            if entry.target_identity == identity
        )


def _build_project_module_export_surface_set(
    catalogs: ProjectModuleCatalogSet,
    *,
    imported_binding_candidates: tuple[ProjectImportedExportCandidate, ...] = (),
) -> ProjectModuleExportSurfaceSet:
    """Build direct module facades without resolving imports or traversing graphs."""

    if type(catalogs) is not ProjectModuleCatalogSet:
        raise TypeError("Module export builder requires a project catalog set.")
    if type(imported_binding_candidates) is not tuple or any(
        type(item) is not ProjectImportedExportCandidate
        for item in imported_binding_candidates
    ):
        raise TypeError("Imported export candidates must be a tuple.")

    surfaces: list[ProjectModuleExportSurface] = []
    for catalog in catalogs.catalogs:
        module = catalog.module
        assert module.parsed_input is not None
        requests: list[ProjectModuleExportRequest] = []
        entries: list[ProjectModuleExportEntry] = []
        issues: list[ProjectModuleExportIssue] = []
        prior_by_key: dict[
            tuple[ProjectSymbolNamespace, ProjectSymbolKind, str],
            list[ProjectModuleExportRequest],
        ] = {}

        for statement_position, statement in enumerate(
            module.parsed_input.script.module_statements
        ):
            if type(statement) is not ExportStatement:
                continue
            for item_position, source_item in enumerate(statement.items):
                namespace, declaration_kind = _ELIGIBLE_EXPORT_KIND_MAP[
                    source_item.declaration_kind
                ]
                request = ProjectModuleExportRequest(
                    owning_module_path=module.path,
                    namespace=namespace,
                    declaration_kind=declaration_kind,
                    local_name=source_item.local_name,
                    module_statement_position=statement_position,
                    item_position=item_position,
                    source_item=source_item,
                )
                requests.append(request)
                request_key = (namespace, declaration_kind, request.local_name)
                prior_requests = prior_by_key.setdefault(request_key, [])
                if prior_requests:
                    issues.append(
                        ProjectModuleExportIssue(
                            status=ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST,
                            request=request,
                            prior_requests=tuple(prior_requests),
                        )
                    )
                prior_requests.append(request)

                identity = ProjectNominalDeclarationIdentity(
                    module_path=module.path,
                    namespace=namespace,
                    declaration_kind=declaration_kind,
                    declared_name=request.local_name,
                )
                local_occurrences = catalogs.find_identity(identity)
                same_owner_name_candidates = tuple(
                    candidate
                    for candidate in imported_binding_candidates
                    if candidate.owning_module_path == module.path
                    and candidate.local_binding_name == request.local_name
                )
                exact_imported_candidates = tuple(
                    candidate
                    for candidate in same_owner_name_candidates
                    if candidate.namespace is namespace
                    and candidate.declaration_kind is declaration_kind
                    and candidate.target_identity.namespace is candidate.namespace
                    and candidate.target_identity.declaration_kind
                    is candidate.declaration_kind
                )
                inconsistent_candidates = tuple(
                    candidate
                    for candidate in same_owner_name_candidates
                    if candidate not in exact_imported_candidates
                )

                if len(local_occurrences) > 1:
                    issues.append(
                        ProjectModuleExportIssue(
                            status=ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION,
                            request=request,
                            local_occurrences=local_occurrences,
                            imported_candidates=same_owner_name_candidates,
                        )
                    )
                    continue
                if inconsistent_candidates:
                    issues.append(
                        ProjectModuleExportIssue(
                            status=ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE,
                            request=request,
                            local_occurrences=local_occurrences,
                            imported_candidates=same_owner_name_candidates,
                        )
                    )
                    continue

                candidate_count = len(local_occurrences) + len(
                    exact_imported_candidates
                )
                if candidate_count == 0:
                    issues.append(
                        ProjectModuleExportIssue(
                            status=ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING,
                            request=request,
                        )
                    )
                    continue
                if candidate_count > 1:
                    issues.append(
                        ProjectModuleExportIssue(
                            status=ProjectModuleExportIssueStatus.AMBIGUOUS_CANDIDATE_SET,
                            request=request,
                            local_occurrences=local_occurrences,
                            imported_candidates=exact_imported_candidates,
                        )
                    )
                    continue

                if local_occurrences:
                    occurrence = local_occurrences[0]
                    entries.append(
                        ProjectModuleExportEntry(
                            owning_module_path=module.path,
                            namespace=namespace,
                            declaration_kind=declaration_kind,
                            exposed_name=request.local_name,
                            origin=ProjectModuleExportEntryOrigin.LOCAL_DECLARATION,
                            target_identity=occurrence.identity,
                            request=request,
                            resolved_from=occurrence,
                        )
                    )
                else:
                    candidate = exact_imported_candidates[0]
                    entries.append(
                        ProjectModuleExportEntry(
                            owning_module_path=module.path,
                            namespace=namespace,
                            declaration_kind=declaration_kind,
                            exposed_name=request.local_name,
                            origin=ProjectModuleExportEntryOrigin.EXPLICIT_REEXPORT,
                            target_identity=candidate.target_identity,
                            request=request,
                            resolved_from=candidate,
                        )
                    )

        surfaces.append(
            ProjectModuleExportSurface(
                module=module,
                requests=tuple(requests),
                entries=tuple(entries),
                issues=tuple(issues),
            )
        )

    return ProjectModuleExportSurfaceSet(surfaces=tuple(surfaces))
