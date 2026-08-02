"""Private schema-v2 cross-module relation resolution and minimal row facts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar, cast

from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.module_bindings import (
    ProjectModuleBindingEnvironment,
    ProjectModuleBindingEnvironmentSet,
    ProjectModuleBindingIssue,
    ProjectModuleBindingIssueStatus,
    ProjectResolvedImportedBinding,
)
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.module_catalog import (
    ProjectDeclarationOccurrence,
    ProjectModuleCatalog,
    ProjectModuleCatalogSet,
    ProjectNominalDeclarationIdentity,
)
from pietto._project.module_exports import (
    ProjectModuleExportIssue,
    ProjectModuleExportIssueStatus,
    ProjectModuleExportSurface,
    ProjectModuleExportSurfaceSet,
)
from pietto._project.module_graph import (
    ProjectModuleCycle,
    ProjectModuleDiagnosticSet,
    ProjectModuleGraph,
)
from pietto._project.module_resolution import (
    ProjectModuleTypeSourceResolutionEnvironment,
    ProjectTypeSourceResolutionIssue,
    ProjectTypeSourceResolutionIssueStatus,
    ProjectTypeSourceResolutionSet,
    _dependency_first_vertices,
    _suppressing_diagnostics_for_binding_issues,
    _suppressing_diagnostics_for_cycle,
    _suppressing_diagnostics_for_export_issues,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    FromClause,
    NameExpr,
    Nullability,
    QueryDef,
    SelectItem,
    ShapeDef,
    SourceDef,
    Span,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()

_RELATION_KINDS = frozenset(
    {
        ProjectSymbolKind.SOURCE,
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    }
)
_COLLISION_ISSUE_STATUSES = frozenset(
    {
        ProjectModuleBindingIssueStatus.LOCAL_DECLARATION_COLLISION,
        ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION,
    }
)
_DefinitionT = SourceDef | TableDef | QueryDef
_KeyT = TypeVar("_KeyT")
_ValueT = TypeVar("_ValueT")


class ProjectModuleRelationResolutionIssueStatus(StrEnum):
    """Closed private failure and suppression facts for Slice 10."""

    AMBIGUOUS_LOCAL_RELATION_NAME = "ambiguous_local_relation_name"
    UNKNOWN_RELATION_REFERENCE = "unknown_relation_reference"
    UNKNOWN_DIRECT_FIELD = "unknown_direct_field"
    LOCAL_RELATION_CYCLE = "local_relation_cycle"
    MODULE_GRAPH_CYCLE_BLOCKED = "module_graph_cycle_blocked"
    MODULE_DIAGNOSTIC_BLOCKED = "module_diagnostic_blocked"
    TYPE_SOURCE_DIAGNOSTIC_BLOCKED = "type_source_diagnostic_blocked"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResolvedModuleRelationSymbol:
    """One module-local relation name bound to one exact nominal declaration."""

    owning_module_path: str
    local_name: str
    target_identity: ProjectNominalDeclarationIdentity
    target_occurrence: ProjectDeclarationOccurrence
    local_occurrence: ProjectDeclarationOccurrence | None = None
    imported_binding: ProjectResolvedImportedBinding | None = None

    def __post_init__(self) -> None:
        """Reject facts that collapse a local alias and nominal identity."""

        ProjectModuleIdentity(path=self.owning_module_path)
        if type(self.local_name) is not str or not self.local_name:
            raise ValueError("Resolved relation symbol requires a local name.")
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Resolved relation symbol requires a target identity.")
        if type(self.target_occurrence) is not ProjectDeclarationOccurrence:
            raise TypeError("Resolved relation symbol requires a target occurrence.")
        _validate_relation_identity(self.target_identity)
        if self.target_occurrence.identity != self.target_identity:
            raise ValueError("Resolved relation target occurrence must match identity.")
        local = self.local_occurrence
        imported = self.imported_binding
        if (local is None) == (imported is None):
            raise ValueError(
                "Resolved relation symbol requires exactly one binding source."
            )
        if local is not None:
            if type(local) is not ProjectDeclarationOccurrence:
                raise TypeError("Local relation symbol requires an occurrence.")
            if (
                local is not self.target_occurrence
                or local.identity != self.target_identity
                or self.target_identity.module_path != self.owning_module_path
                or self.target_identity.declared_name != self.local_name
            ):
                raise ValueError("Local relation symbol must retain local identity.")
        else:
            if type(imported) is not ProjectResolvedImportedBinding:
                raise TypeError("Imported relation symbol requires a binding.")
            if (
                imported.identity.owning_module_path != self.owning_module_path
                or imported.identity.local_binding_name != self.local_name
                or imported.target_identity != self.target_identity
                or imported.identity.namespace is not ProjectSymbolNamespace.RELATION
                or imported.identity.declaration_kind
                is not self.target_identity.declaration_kind
            ):
                raise ValueError(
                    "Imported relation symbol must preserve local and target identity."
                )

    @property
    def declaration_kind(self) -> ProjectSymbolKind:
        """Return the exact relation-producing target declaration kind."""

        return self.target_identity.declaration_kind


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationReference:
    """One exact TableDef or QueryDef from-clause reference."""

    owner: ProjectDeclarationOccurrence
    from_clause: FromClause

    def __post_init__(self) -> None:
        """Require the reference to match its retained relation AST site."""

        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Module relation reference requires an owner occurrence.")
        if type(self.from_clause) is not FromClause:
            raise TypeError("Module relation reference requires a FromClause.")
        definition = self.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            raise ValueError("Module relation reference must match its retained AST.")
        relation_definition = cast(TableDef | QueryDef, definition)
        if (
            self.owner.identity.declaration_kind
            not in {ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY}
            or relation_definition.from_clause is not self.from_clause
        ):
            raise ValueError("Module relation reference must match its retained AST.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResolvedModuleRelationReference:
    """One exact module relation reference resolved to one nominal target."""

    reference: ProjectModuleRelationReference
    target_symbol: ProjectResolvedModuleRelationSymbol

    def __post_init__(self) -> None:
        """Require relation-namespace lookup through the exact local name."""

        if type(self.reference) is not ProjectModuleRelationReference:
            raise TypeError("Resolved relation reference requires a reference.")
        if type(self.target_symbol) is not ProjectResolvedModuleRelationSymbol:
            raise TypeError("Resolved relation reference requires a target symbol.")
        if (
            self.target_symbol.owning_module_path
            != self.reference.owner.identity.module_path
            or self.target_symbol.local_name != self.reference.from_clause.source_name
        ):
            raise ValueError("Resolved relation reference must use its local lookup.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationRowFact:
    """One minimal row availability fact for a relation-producing declaration."""

    owner: ProjectDeclarationOccurrence
    state: ProjectRelationRowSchemaState

    def __post_init__(self) -> None:
        """Require an existing row-state carrier and one relation declaration."""

        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Module relation row fact requires an owner occurrence.")
        _validate_relation_identity(self.owner.identity)
        if type(self.state) is not ProjectRelationRowSchemaState:
            raise TypeError("Module relation row fact requires an exact row state.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationResolutionIssue:
    """One typed emitted or root-suppressed Slice 10 relation issue."""

    status: ProjectModuleRelationResolutionIssueStatus
    owning_module_path: str
    local_name: str | None
    location: SourceLocation
    related_locations: tuple[SourceLocation, ...] = ()
    diagnostic: Diagnostic | None = None
    occurrences: tuple[ProjectDeclarationOccurrence, ...] = ()
    reference: ProjectModuleRelationReference | None = None
    select_item: SelectItem | None = None
    binding_issues: tuple[ProjectModuleBindingIssue, ...] = ()
    module_cycle: ProjectModuleCycle | None = None
    relation_cycle: tuple[ProjectDeclarationOccurrence, ...] = ()
    type_source_issues: tuple[ProjectTypeSourceResolutionIssue, ...] = ()
    suppressing_diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        """Reject mixed evidence and incorrect one-way diagnostic adaptation."""

        if type(self.status) is not ProjectModuleRelationResolutionIssueStatus:
            raise TypeError("Relation issue requires an exact status.")
        ProjectModuleIdentity(path=self.owning_module_path)
        if self.local_name is not None and (
            type(self.local_name) is not str or not self.local_name
        ):
            raise ValueError("Relation issue local name must be non-empty.")
        if type(self.location) is not SourceLocation:
            raise TypeError("Relation issue requires a source location.")
        _require_tuple_items(
            self.related_locations,
            SourceLocation,
            "Relation issue related locations",
        )
        _require_tuple_items(
            self.occurrences,
            ProjectDeclarationOccurrence,
            "Relation issue occurrences",
        )
        _require_tuple_items(
            self.binding_issues,
            ProjectModuleBindingIssue,
            "Relation issue binding issues",
        )
        _require_tuple_items(
            self.relation_cycle,
            ProjectDeclarationOccurrence,
            "Relation issue cycle",
        )
        _require_tuple_items(
            self.type_source_issues,
            ProjectTypeSourceResolutionIssue,
            "Relation issue type/source roots",
        )
        _require_tuple_items(
            self.suppressing_diagnostics,
            Diagnostic,
            "Relation issue suppressing diagnostics",
        )
        if self.diagnostic is not None:
            if type(self.diagnostic) is not Diagnostic:
                raise TypeError("Relation issue diagnostic must be a Diagnostic.")
            if (
                self.diagnostic.severity is not Severity.ERROR
                or self.diagnostic.location != self.location
                or self.diagnostic.suggestion is not None
                or self.suppressing_diagnostics
            ):
                raise ValueError("Emitted relation diagnostic must be exact.")
        elif not self.suppressing_diagnostics:
            raise ValueError("Suppressed relation issue requires its root.")
        _validate_issue_evidence(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationResolutionEnvironment:
    """One dependency-ordered module-local relation and row-fact result."""

    module: ProjectLogicalModule
    symbols: tuple[ProjectResolvedModuleRelationSymbol, ...] = ()
    references: tuple[ProjectModuleRelationReference, ...] = ()
    resolutions: tuple[ProjectResolvedModuleRelationReference, ...] = ()
    row_facts: tuple[ProjectModuleRelationRowFact, ...] = ()
    issues: tuple[ProjectModuleRelationResolutionIssue, ...] = ()
    _symbols_by_name: Mapping[str, tuple[ProjectResolvedModuleRelationSymbol, ...]] = (
        field(init=False, repr=False, compare=False, hash=False)
    )
    _resolutions_by_from_clause: Mapping[
        FromClause, tuple[ProjectResolvedModuleRelationReference, ...]
    ] = field(init=False, repr=False, compare=False, hash=False)
    _row_facts_by_definition: Mapping[
        _DefinitionT, tuple[ProjectModuleRelationRowFact, ...]
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Copy lookup buckets and reject reordered or foreign facts."""

        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Relation environment requires a logical module.")
        if (
            self.module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or self.module.parsed_input is None
        ):
            raise ValueError("Relation environment requires a parsed module.")
        _require_tuple_items(
            self.symbols,
            ProjectResolvedModuleRelationSymbol,
            "Relation environment symbols",
        )
        _require_tuple_items(
            self.references,
            ProjectModuleRelationReference,
            "Relation environment references",
        )
        _require_tuple_items(
            self.resolutions,
            ProjectResolvedModuleRelationReference,
            "Relation environment resolutions",
        )
        _require_tuple_items(
            self.row_facts,
            ProjectModuleRelationRowFact,
            "Relation environment row facts",
        )
        _require_tuple_items(
            self.issues,
            ProjectModuleRelationResolutionIssue,
            "Relation environment issues",
        )
        module_path = self.module.path
        if any(symbol.owning_module_path != module_path for symbol in self.symbols):
            raise ValueError("Relation environment symbols must be module-local.")
        if any(
            reference.owner.identity.module_path != module_path
            for reference in self.references
        ):
            raise ValueError("Relation environment references must be module-local.")
        if any(
            resolution.reference not in self.references
            for resolution in self.resolutions
        ):
            raise ValueError("Relation resolutions require retained references.")
        if any(
            fact.owner.identity.module_path != module_path for fact in self.row_facts
        ):
            raise ValueError("Relation row facts must be module-local.")
        if any(issue.owning_module_path != module_path for issue in self.issues):
            raise ValueError("Relation environment issues must be module-local.")

        symbols: dict[str, list[ProjectResolvedModuleRelationSymbol]] = {}
        for symbol in self.symbols:
            symbols.setdefault(symbol.local_name, []).append(symbol)
        if any(len(items) != 1 for items in symbols.values()):
            raise ValueError("Relation symbol buckets cannot select a winner.")
        resolutions: dict[FromClause, list[ProjectResolvedModuleRelationReference]] = {}
        for resolution in self.resolutions:
            resolutions.setdefault(resolution.reference.from_clause, []).append(
                resolution
            )
        row_facts: dict[_DefinitionT, list[ProjectModuleRelationRowFact]] = {}
        for fact in self.row_facts:
            definition = fact.owner.definition
            if type(definition) not in {SourceDef, TableDef, QueryDef}:
                raise ValueError("Relation row fact requires a relation definition.")
            row_facts.setdefault(cast(_DefinitionT, definition), []).append(fact)
        if any(
            len(items) != 1 for items in (*resolutions.values(), *row_facts.values())
        ):
            raise ValueError("Relation AST lookup buckets must be unambiguous.")
        object.__setattr__(self, "_symbols_by_name", _tuple_mapping(symbols))
        object.__setattr__(
            self,
            "_resolutions_by_from_clause",
            _tuple_mapping(resolutions),
        )
        object.__setattr__(
            self,
            "_row_facts_by_definition",
            _tuple_mapping(row_facts),
        )

    def find_relation_name(
        self, local_name: str
    ) -> tuple[ProjectResolvedModuleRelationSymbol, ...]:
        """Return the complete exact local relation-name bucket."""

        if type(local_name) is not str:
            raise TypeError("Relation-name lookup requires a string.")
        return self._symbols_by_name.get(local_name, ())

    def find_from_clause(
        self, from_clause: FromClause
    ) -> tuple[ProjectResolvedModuleRelationReference, ...]:
        """Return one exact resolution for a retained from-clause, or empty."""

        if type(from_clause) is not FromClause:
            raise TypeError("From-clause lookup requires a FromClause.")
        return self._resolutions_by_from_clause.get(from_clause, ())

    def find_definition(
        self, definition: _DefinitionT
    ) -> tuple[ProjectModuleRelationRowFact, ...]:
        """Return one exact row fact for a retained relation definition."""

        if type(definition) not in {SourceDef, TableDef, QueryDef}:
            raise TypeError("Row-fact lookup requires a relation definition.")
        return self._row_facts_by_definition.get(definition, ())


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationResolutionSet:
    """The complete private schema-v2 Slice 10 resolution product."""

    dependency_order: tuple[ProjectModuleIdentity, ...] = ()
    environments: tuple[ProjectModuleRelationResolutionEnvironment, ...] = ()
    issues: tuple[ProjectModuleRelationResolutionIssue, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    _environments_by_path: Mapping[str, ProjectModuleRelationResolutionEnvironment] = (
        field(init=False, repr=False, compare=False, hash=False)
    )
    _symbols_by_target_identity: Mapping[
        ProjectNominalDeclarationIdentity,
        tuple[ProjectResolvedModuleRelationSymbol, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Require dependency order and exact issue-to-diagnostic projection."""

        _require_tuple_items(
            self.dependency_order,
            ProjectModuleIdentity,
            "Relation dependency order",
        )
        _require_tuple_items(
            self.environments,
            ProjectModuleRelationResolutionEnvironment,
            "Relation environments",
        )
        _require_tuple_items(
            self.issues,
            ProjectModuleRelationResolutionIssue,
            "Relation issues",
        )
        _require_tuple_items(self.diagnostics, Diagnostic, "Relation diagnostics")
        paths = tuple(environment.module.path for environment in self.environments)
        if paths != tuple(identity.path for identity in self.dependency_order):
            raise ValueError("Relation environments must follow dependency order.")
        if len(set(paths)) != len(paths):
            raise ValueError("Relation environment paths must be unique.")
        expected = tuple(
            issue.diagnostic for issue in self.issues if issue.diagnostic is not None
        )
        if self.diagnostics != expected:
            raise ValueError("Relation diagnostics must project exact issues.")
        object.__setattr__(
            self,
            "_environments_by_path",
            MappingProxyType(
                {
                    environment.module.path: environment
                    for environment in self.environments
                }
            ),
        )
        symbols: dict[
            ProjectNominalDeclarationIdentity,
            list[ProjectResolvedModuleRelationSymbol],
        ] = {}
        for environment in self.environments:
            for symbol in environment.symbols:
                symbols.setdefault(symbol.target_identity, []).append(symbol)
        object.__setattr__(
            self,
            "_symbols_by_target_identity",
            _tuple_mapping(symbols),
        )

    def find_module_path(
        self, module_path: str
    ) -> tuple[ProjectModuleRelationResolutionEnvironment, ...]:
        """Return one exact acyclic module environment, or empty."""

        try:
            ProjectModuleIdentity(path=module_path)
        except (TypeError, ValueError):
            return ()
        environment = self._environments_by_path.get(module_path)
        return () if environment is None else (environment,)

    def find_target_identity(
        self, identity: ProjectNominalDeclarationIdentity
    ) -> tuple[ProjectResolvedModuleRelationSymbol, ...]:
        """Return every local/imported symbol retaining one nominal target."""

        if type(identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Target lookup requires a nominal identity.")
        return self._symbols_by_target_identity.get(identity, ())


@dataclass(slots=True)
class _RelationResolutionDraft:
    module: ProjectLogicalModule
    catalog: ProjectModuleCatalog
    binding_environment: ProjectModuleBindingEnvironment
    type_source_environment: ProjectModuleTypeSourceResolutionEnvironment
    symbols: list[ProjectResolvedModuleRelationSymbol]
    references: list[ProjectModuleRelationReference]
    resolutions: list[ProjectResolvedModuleRelationReference]
    row_facts: dict[ProjectDeclarationOccurrence, ProjectModuleRelationRowFact]
    issues: list[ProjectModuleRelationResolutionIssue]
    blocked_names: set[str]
    ambiguous_names: set[str]


@dataclass(frozen=True, slots=True)
class _LocalRelationCycle:
    occurrences: tuple[ProjectDeclarationOccurrence, ...]
    references: tuple[ProjectModuleRelationReference, ...]


def _build_project_module_relation_resolution_set(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    module_diagnostics: ProjectModuleDiagnosticSet,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
) -> ProjectModuleRelationResolutionSet:
    """Build pure dependency-first schema-v2 relation and minimal row facts."""

    _validate_builder_inputs(
        modules,
        catalogs,
        exports,
        bindings,
        graph,
        module_diagnostics,
        type_source_resolutions,
    )
    dependency_vertices = _dependency_first_vertices(graph)
    dependency_order = tuple(vertex.identity for vertex in dependency_vertices)
    if dependency_order != type_source_resolutions.dependency_order:
        raise ValueError("Slice 10 must reuse the exact Slice 9 dependency order.")

    cyclic_paths = {
        member.identity.path
        for cycle in graph.cycles
        for member in cycle.component.members
    }
    cycle_by_path = {
        member.identity.path: cycle
        for cycle in graph.cycles
        for member in cycle.component.members
    }
    catalog_by_path = {catalog.module_path: catalog for catalog in catalogs.catalogs}
    binding_by_path = {
        environment.module.path: environment for environment in bindings.environments
    }
    type_source_by_path = {
        environment.module.path: environment
        for environment in type_source_resolutions.environments
    }
    surface_by_path = {surface.module.path: surface for surface in exports.surfaces}
    environment_by_path: dict[str, ProjectModuleRelationResolutionEnvironment] = {}
    row_fact_by_identity: dict[
        ProjectNominalDeclarationIdentity, ProjectModuleRelationRowFact
    ] = {}
    environments: list[ProjectModuleRelationResolutionEnvironment] = []
    all_issues: list[ProjectModuleRelationResolutionIssue] = []

    for vertex in dependency_vertices:
        module = vertex.module
        draft = _RelationResolutionDraft(
            module=module,
            catalog=catalog_by_path[module.path],
            binding_environment=binding_by_path[module.path],
            type_source_environment=type_source_by_path[module.path],
            symbols=[],
            references=[],
            resolutions=[],
            row_facts={},
            issues=[],
            blocked_names=set(),
            ambiguous_names=set(),
        )
        _collect_module_diagnostic_blockers(draft, module_diagnostics)
        _collect_local_symbols(draft)
        _collect_imported_symbols(
            draft,
            catalogs=catalogs,
            target_surface_by_path=surface_by_path,
            environment_by_path=environment_by_path,
            cyclic_paths=cyclic_paths,
            cycle_by_path=cycle_by_path,
            module_diagnostics=module_diagnostics,
        )
        _collect_and_resolve_references(draft)
        cycles = _local_relation_cycles(draft)
        _append_local_cycle_issues(draft, cycles)
        _build_module_row_facts(
            draft,
            catalogs=catalogs,
            type_source_resolutions=type_source_resolutions,
            row_fact_by_identity=row_fact_by_identity,
            cycles=cycles,
        )
        ordered_issues = tuple(sorted(draft.issues, key=_issue_source_key))
        environment = ProjectModuleRelationResolutionEnvironment(
            module=module,
            symbols=tuple(draft.symbols),
            references=tuple(draft.references),
            resolutions=tuple(draft.resolutions),
            row_facts=tuple(
                draft.row_facts[occurrence]
                for occurrence in draft.catalog.occurrences
                if occurrence in draft.row_facts
            ),
            issues=ordered_issues,
        )
        environments.append(environment)
        environment_by_path[module.path] = environment
        all_issues.extend(ordered_issues)
        for fact in environment.row_facts:
            if len(catalogs.find_identity(fact.owner.identity)) == 1:
                row_fact_by_identity[fact.owner.identity] = fact

    cycle_issues = _module_cycle_issues(graph, module_diagnostics)
    all_issues.extend(cycle_issues)
    issue_tuple = tuple(all_issues)
    return ProjectModuleRelationResolutionSet(
        dependency_order=dependency_order,
        environments=tuple(environments),
        issues=issue_tuple,
        diagnostics=tuple(
            issue.diagnostic for issue in issue_tuple if issue.diagnostic is not None
        ),
    )


def _collect_module_diagnostic_blockers(
    draft: _RelationResolutionDraft,
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> None:
    binding_buckets: dict[str, list[ProjectModuleBindingIssue]] = {}
    for issue in draft.binding_environment.issues:
        if issue.status is ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST:
            continue
        kind = issue.request.identity.declaration_kind
        if (
            kind not in _RELATION_KINDS
            and issue.status not in _COLLISION_ISSUE_STATUSES
        ):
            continue
        binding_buckets.setdefault(
            issue.request.identity.local_binding_name, []
        ).append(issue)

    for local_name, issues in binding_buckets.items():
        issue_tuple = tuple(issues)
        roots = _suppressing_diagnostics_for_binding_issues(
            issue_tuple,
            module_diagnostics,
        )
        if not roots:
            raise ValueError("Blocked relation binding requires a Slice 8 root.")
        request = min(
            (issue.request for issue in issue_tuple),
            key=lambda item: (item.module_statement_position, item.item_position),
        )
        span = (
            request.source_item.local_name_span
            or request.source_item.exported_name_span
        )
        location = _location(span, fallback_path=draft.module.path)
        draft.issues.append(
            ProjectModuleRelationResolutionIssue(
                status=ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
                owning_module_path=draft.module.path,
                local_name=local_name,
                location=location,
                related_locations=_ordered_related_locations(
                    location,
                    tuple(root.location for root in roots),
                ),
                binding_issues=issue_tuple,
                suppressing_diagnostics=roots,
            )
        )
        draft.blocked_names.add(local_name)

    export_buckets: dict[str, list[ProjectModuleExportIssue]] = {}
    for fact in module_diagnostics.facts:
        for issue in fact.export_issues:
            if (
                issue.request.owning_module_path != draft.module.path
                or issue.status
                is not ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION
                or issue.request.declaration_kind not in _RELATION_KINDS
            ):
                continue
            export_buckets.setdefault(issue.request.local_name, []).append(issue)

    for local_name, issues in export_buckets.items():
        issue_tuple = tuple(issues)
        roots = _suppressing_diagnostics_for_export_issues(
            issue_tuple,
            module_diagnostics,
        )
        occurrences = tuple(
            occurrence
            for issue in issue_tuple
            for occurrence in issue.local_occurrences
        )
        if not roots or len(occurrences) < 2:
            raise ValueError("Blocked relation export requires its Slice 8 root.")
        location = roots[0].location
        draft.issues.append(
            ProjectModuleRelationResolutionIssue(
                status=ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
                owning_module_path=draft.module.path,
                local_name=local_name,
                location=location,
                related_locations=_ordered_related_locations(
                    location,
                    tuple(
                        _location(
                            occurrence.definition.span,
                            fallback_path=draft.module.path,
                        )
                        for occurrence in occurrences
                    ),
                ),
                occurrences=occurrences,
                suppressing_diagnostics=roots,
            )
        )
        draft.blocked_names.add(local_name)


def _collect_local_symbols(draft: _RelationResolutionDraft) -> None:
    buckets: dict[str, list[ProjectDeclarationOccurrence]] = {}
    for occurrence in draft.catalog.occurrences:
        if occurrence.identity.declaration_kind in _RELATION_KINDS:
            buckets.setdefault(occurrence.identity.declared_name, []).append(occurrence)

    source_duplicate_roots = _source_duplicate_roots(draft.type_source_environment)
    for local_name, occurrences in buckets.items():
        occurrence_tuple = tuple(occurrences)
        if len(occurrences) > 1:
            draft.ambiguous_names.add(local_name)
            if local_name in draft.blocked_names:
                continue
            type_source_issues = source_duplicate_roots.get(local_name, ())
            if type_source_issues:
                roots = tuple(
                    issue.diagnostic
                    for issue in type_source_issues
                    if issue.diagnostic is not None
                )
                if not roots:
                    raise ValueError("Slice 9 source duplicate requires its root.")
                location = roots[0].location
                draft.issues.append(
                    ProjectModuleRelationResolutionIssue(
                        status=ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED,
                        owning_module_path=draft.module.path,
                        local_name=local_name,
                        location=location,
                        related_locations=_ordered_related_locations(
                            location,
                            tuple(root.location for root in roots),
                        ),
                        occurrences=occurrence_tuple,
                        type_source_issues=type_source_issues,
                        suppressing_diagnostics=roots,
                    )
                )
            else:
                draft.issues.append(
                    _duplicate_relation_issue(
                        draft.module.path,
                        local_name,
                        occurrence_tuple,
                    )
                )
            continue
        if local_name not in draft.blocked_names:
            draft.symbols.append(
                _local_relation_symbol(draft.module.path, occurrences[0])
            )


def _collect_imported_symbols(
    draft: _RelationResolutionDraft,
    *,
    catalogs: ProjectModuleCatalogSet,
    target_surface_by_path: Mapping[str, ProjectModuleExportSurface],
    environment_by_path: Mapping[str, ProjectModuleRelationResolutionEnvironment],
    cyclic_paths: set[str],
    cycle_by_path: Mapping[str, ProjectModuleCycle],
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> None:
    for binding in draft.binding_environment.bindings:
        if binding.identity.declaration_kind not in _RELATION_KINDS:
            continue
        local_name = binding.identity.local_binding_name
        if local_name in draft.blocked_names:
            continue
        direct_facade_path = binding.target_module_path
        surface = target_surface_by_path.get(direct_facade_path)
        if surface is None or binding.resolved_entry not in surface.entries:
            raise ValueError("Imported relation requires its exact target facade.")
        nominal_target_path = binding.target_identity.module_path
        cycle_path = None
        if direct_facade_path in cyclic_paths:
            cycle_path = direct_facade_path
        elif nominal_target_path in cyclic_paths:
            cycle_path = nominal_target_path
        if cycle_path is not None:
            cycle = cycle_by_path[cycle_path]
            roots = _suppressing_diagnostics_for_cycle(cycle, module_diagnostics)
            if not roots:
                raise ValueError("Cyclic relation target requires PIE-S2703.")
            span = (
                binding.request.source_item.local_name_span
                or binding.request.source_item.exported_name_span
            )
            location = _location(span, fallback_path=draft.module.path)
            draft.issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
                    owning_module_path=draft.module.path,
                    local_name=local_name,
                    location=location,
                    related_locations=_ordered_related_locations(
                        location,
                        tuple(root.location for root in roots),
                    ),
                    module_cycle=cycle,
                    suppressing_diagnostics=roots,
                )
            )
            draft.blocked_names.add(local_name)
            continue
        target_environment = environment_by_path.get(nominal_target_path)
        if target_environment is None:
            raise ValueError("Imported nominal relation target must precede importer.")
        target_symbols = tuple(
            symbol
            for symbol in target_environment.symbols
            if symbol.local_occurrence is not None
            and symbol.target_identity == binding.target_identity
        )
        if len(target_symbols) != 1:
            roots = tuple(
                issue.diagnostic
                for issue in target_environment.issues
                if issue.local_name == binding.target_identity.declared_name
                and issue.diagnostic is not None
            )
            if not roots:
                roots = tuple(
                    diagnostic
                    for issue in target_environment.issues
                    if issue.local_name == binding.target_identity.declared_name
                    for diagnostic in issue.suppressing_diagnostics
                )
            if not roots:
                raise ValueError("Blocked nominal relation target requires its root.")
            span = (
                binding.request.source_item.local_name_span
                or binding.request.source_item.exported_name_span
            )
            location = _location(span, fallback_path=draft.module.path)
            draft.issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
                    owning_module_path=draft.module.path,
                    local_name=local_name,
                    location=location,
                    related_locations=_ordered_related_locations(
                        location,
                        tuple(root.location for root in roots),
                    ),
                    occurrences=tuple(catalogs.find_identity(binding.target_identity)),
                    suppressing_diagnostics=tuple(dict.fromkeys(roots)),
                )
            )
            draft.blocked_names.add(local_name)
            continue
        occurrences = catalogs.find_identity(binding.target_identity)
        if len(occurrences) != 1:
            raise ValueError("Imported relation target must have one exact occurrence.")
        draft.symbols.append(
            ProjectResolvedModuleRelationSymbol(
                owning_module_path=draft.module.path,
                local_name=local_name,
                target_identity=binding.target_identity,
                target_occurrence=occurrences[0],
                imported_binding=binding,
            )
        )


def _collect_and_resolve_references(draft: _RelationResolutionDraft) -> None:
    symbols_by_name = {symbol.local_name: symbol for symbol in draft.symbols}
    for occurrence in draft.catalog.occurrences:
        definition = occurrence.definition
        if type(definition) not in {TableDef, QueryDef}:
            continue
        relation_definition = cast(TableDef | QueryDef, definition)
        reference = ProjectModuleRelationReference(
            owner=occurrence,
            from_clause=relation_definition.from_clause,
        )
        draft.references.append(reference)
        local_name = relation_definition.from_clause.source_name
        if local_name in draft.blocked_names or local_name in draft.ambiguous_names:
            continue
        symbol = symbols_by_name.get(local_name)
        if symbol is None:
            location = _location(
                relation_definition.from_clause.span,
                fallback_path=draft.module.path,
            )
            draft.issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_REFERENCE,
                    owning_module_path=draft.module.path,
                    local_name=local_name,
                    location=location,
                    diagnostic=_diagnostic(
                        code="PIE-S2301",
                        message=f"Unknown relation: {local_name}",
                        location=location,
                    ),
                    reference=reference,
                )
            )
            continue
        draft.resolutions.append(
            ProjectResolvedModuleRelationReference(
                reference=reference,
                target_symbol=symbol,
            )
        )


def _local_relation_cycles(
    draft: _RelationResolutionDraft,
) -> tuple[_LocalRelationCycle, ...]:
    local_symbols = tuple(
        symbol
        for symbol in draft.symbols
        if symbol.local_occurrence is not None
        and symbol.declaration_kind
        in {ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY}
    )
    occurrence_order = {
        symbol.target_occurrence: symbol.target_occurrence.declaration_position
        for symbol in local_symbols
    }
    resolution_by_owner = {
        resolution.reference.owner: resolution for resolution in draft.resolutions
    }
    edge_by_origin: dict[
        ProjectDeclarationOccurrence,
        tuple[ProjectDeclarationOccurrence, ProjectModuleRelationReference],
    ] = {}
    for symbol in local_symbols:
        origin = symbol.target_occurrence
        resolution = resolution_by_owner.get(origin)
        if resolution is None:
            continue
        target = resolution.target_symbol.target_occurrence
        if (
            target in occurrence_order
            and target.identity.module_path == draft.module.path
        ):
            edge_by_origin[origin] = (target, resolution.reference)

    state: dict[ProjectDeclarationOccurrence, int] = {}
    stack: list[ProjectDeclarationOccurrence] = []
    stack_references: list[ProjectModuleRelationReference] = []
    stack_indexes: dict[ProjectDeclarationOccurrence, int] = {}
    cycles_by_members: dict[
        frozenset[ProjectDeclarationOccurrence], _LocalRelationCycle
    ] = {}

    def visit(occurrence: ProjectDeclarationOccurrence) -> None:
        state[occurrence] = 1
        stack_indexes[occurrence] = len(stack)
        stack.append(occurrence)
        edge = edge_by_origin.get(occurrence)
        if edge is not None:
            target, reference = edge
            target_state = state.get(target, 0)
            if target_state == 0:
                stack_references.append(reference)
                visit(target)
                stack_references.pop()
            elif target_state == 1:
                start = stack_indexes[target]
                cycle = _canonical_local_cycle(
                    tuple(stack[start:]),
                    tuple((*stack_references[start:], reference)),
                    occurrence_order,
                )
                cycles_by_members.setdefault(frozenset(cycle.occurrences), cycle)
        stack.pop()
        stack_indexes.pop(occurrence)
        state[occurrence] = 2

    for occurrence in sorted(occurrence_order, key=occurrence_order.__getitem__):
        if state.get(occurrence, 0) == 0:
            visit(occurrence)
    return tuple(
        sorted(
            cycles_by_members.values(),
            key=lambda cycle: tuple(
                occurrence_order[item] for item in cycle.occurrences
            ),
        )
    )


def _canonical_local_cycle(
    occurrences: tuple[ProjectDeclarationOccurrence, ...],
    references: tuple[ProjectModuleRelationReference, ...],
    occurrence_order: Mapping[ProjectDeclarationOccurrence, int],
) -> _LocalRelationCycle:
    if not occurrences or len(occurrences) != len(references):
        raise ValueError("Local relation cycle requires aligned nodes and edges.")
    start = min(
        range(len(occurrences)),
        key=lambda position: occurrence_order[occurrences[position]],
    )
    return _LocalRelationCycle(
        occurrences=(*occurrences[start:], *occurrences[:start]),
        references=(*references[start:], *references[:start]),
    )


def _append_local_cycle_issues(
    draft: _RelationResolutionDraft,
    cycles: tuple[_LocalRelationCycle, ...],
) -> None:
    for cycle in cycles:
        closing_reference = cycle.references[-1]
        location = _location(
            closing_reference.from_clause.span,
            fallback_path=draft.module.path,
        )
        names = tuple(item.identity.declared_name for item in cycle.occurrences)
        message = f"Relation cycle detected: {' -> '.join((*names, names[0]))}"
        draft.issues.append(
            ProjectModuleRelationResolutionIssue(
                status=ProjectModuleRelationResolutionIssueStatus.LOCAL_RELATION_CYCLE,
                owning_module_path=draft.module.path,
                local_name=names[0],
                location=location,
                related_locations=_ordered_related_locations(
                    location,
                    tuple(
                        _location(
                            occurrence.definition.span,
                            fallback_path=draft.module.path,
                        )
                        for occurrence in cycle.occurrences
                    ),
                ),
                diagnostic=_diagnostic(
                    code="PIE-S2302",
                    message=message,
                    location=location,
                ),
                relation_cycle=cycle.occurrences,
            )
        )


def _build_module_row_facts(
    draft: _RelationResolutionDraft,
    *,
    catalogs: ProjectModuleCatalogSet,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
    row_fact_by_identity: Mapping[
        ProjectNominalDeclarationIdentity, ProjectModuleRelationRowFact
    ],
    cycles: tuple[_LocalRelationCycle, ...],
) -> None:
    cycle_members = {occurrence for cycle in cycles for occurrence in cycle.occurrences}
    local_symbol_by_occurrence = {
        symbol.local_occurrence: symbol
        for symbol in draft.symbols
        if symbol.local_occurrence is not None
    }
    resolution_by_owner = {
        resolution.reference.owner: resolution for resolution in draft.resolutions
    }

    for occurrence in draft.catalog.occurrences:
        if type(occurrence.definition) is not SourceDef:
            continue
        if occurrence not in local_symbol_by_occurrence:
            state = _blocked_state(
                ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED
            )
        else:
            state = _source_row_state(
                draft,
                occurrence,
                catalogs=catalogs,
                type_source_resolutions=type_source_resolutions,
            )
        draft.row_facts[occurrence] = ProjectModuleRelationRowFact(
            owner=occurrence,
            state=state,
        )

    pending: list[ProjectDeclarationOccurrence] = []
    for occurrence in draft.catalog.occurrences:
        if type(occurrence.definition) not in {TableDef, QueryDef}:
            continue
        if occurrence not in local_symbol_by_occurrence:
            state = _blocked_state(
                ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED
            )
        elif occurrence in cycle_members:
            state = _blocked_state(ProjectRelationRowSchemaReason.CYCLE_BLOCKED)
        elif occurrence not in resolution_by_owner:
            state = _blocked_state(
                ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED
            )
        else:
            pending.append(occurrence)
            continue
        draft.row_facts[occurrence] = ProjectModuleRelationRowFact(
            owner=occurrence,
            state=state,
        )

    while pending:
        progressed = False
        next_pending: list[ProjectDeclarationOccurrence] = []
        for occurrence in pending:
            resolution = resolution_by_owner[occurrence]
            target_occurrence = resolution.target_symbol.target_occurrence
            target_fact = draft.row_facts.get(target_occurrence)
            if target_fact is None:
                target_fact = row_fact_by_identity.get(
                    resolution.target_symbol.target_identity
                )
            if target_fact is None:
                next_pending.append(occurrence)
                continue
            state = _relation_row_state(
                draft,
                occurrence,
                resolution,
                target_fact.state,
            )
            draft.row_facts[occurrence] = ProjectModuleRelationRowFact(
                owner=occurrence,
                state=state,
            )
            progressed = True
        if not progressed:
            raise ValueError("Acyclic local relation graph must make finite progress.")
        pending = next_pending


def _source_row_state(
    draft: _RelationResolutionDraft,
    occurrence: ProjectDeclarationOccurrence,
    *,
    catalogs: ProjectModuleCatalogSet,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
) -> ProjectRelationRowSchemaState:
    source = occurrence.definition
    assert type(source) is SourceDef
    resolutions = draft.type_source_environment.find_source(source)
    if len(resolutions) != 1:
        _append_type_source_blocker(draft, occurrence, source)
        return _unknown_state(ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA)
    shape_occurrence = resolutions[0].target_symbol.target_occurrence
    shape = shape_occurrence.definition
    if type(shape) is not ShapeDef:
        raise ValueError("Resolved source shape target must be a ShapeDef.")
    type_environments = type_source_resolutions.find_module_path(
        shape_occurrence.identity.module_path
    )
    if len(type_environments) != 1:
        return _unknown_state(ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA)
    type_environment = type_environments[0]
    fields: dict[str, ProjectRowField] = {}
    for field_def in shape.fields:
        if field_def.name in fields:
            return _unknown_state(ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA)
        type_facts = type_environment.find_type_expr(field_def.type_expr)
        if len(type_facts) != 1 or (
            type_facts[0].canonical_kind is ProjectResolvedTypeKind.UNKNOWN
        ):
            _append_type_source_blocker(draft, occurrence, source, field_def.type_expr)
            return _unknown_state(ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA)
        fields[field_def.name] = ProjectRowField(
            name=field_def.name,
            resolved_type=_resolved_row_type(type_facts[0], catalogs),
            nullability=_row_field_nullability(field_def.type_expr.nullability),
            field_def=field_def,
        )
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=ProjectRowSchema(fields=fields),
        reason=ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
    )


def _append_type_source_blocker(
    draft: _RelationResolutionDraft,
    occurrence: ProjectDeclarationOccurrence,
    source: SourceDef,
    type_expr: object | None = None,
) -> None:
    issues = tuple(
        issue
        for issue in draft.type_source_environment.issues
        if (
            issue.source_reference is not None
            and issue.source_reference.source is source
        )
        or (
            type_expr is not None
            and issue.type_reference is not None
            and issue.type_reference.type_expr is type_expr
        )
    )
    roots = tuple(
        dict.fromkeys(
            diagnostic
            for issue in issues
            for diagnostic in (
                (issue.diagnostic,)
                if issue.diagnostic is not None
                else issue.suppressing_diagnostics
            )
        )
    )
    if not roots:
        return
    location = _location(source.span, fallback_path=draft.module.path)
    candidate = ProjectModuleRelationResolutionIssue(
        status=ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED,
        owning_module_path=draft.module.path,
        local_name=source.name,
        location=location,
        related_locations=_ordered_related_locations(
            location,
            tuple(root.location for root in roots),
        ),
        occurrences=(occurrence,),
        type_source_issues=issues,
        suppressing_diagnostics=roots,
    )
    if not any(
        issue.status is candidate.status
        and issue.local_name == candidate.local_name
        and issue.type_source_issues == candidate.type_source_issues
        for issue in draft.issues
    ):
        draft.issues.append(candidate)


def _resolved_row_type(
    resolution: object,
    catalogs: ProjectModuleCatalogSet,
) -> ProjectResolvedType:
    from pietto._project.module_resolution import ProjectResolvedModuleTypeReference

    if type(resolution) is not ProjectResolvedModuleTypeReference:
        raise TypeError("Row type requires a resolved module type reference.")
    if resolution.canonical_kind is ProjectResolvedTypeKind.BUILTIN:
        return ProjectResolvedType(
            name=resolution.canonical_name,
            kind=ProjectResolvedTypeKind.BUILTIN,
        )
    identity = resolution.canonical_target_identity
    if identity is None:
        raise ValueError("Known nominal row type requires a target identity.")
    occurrences = catalogs.find_identity(identity)
    if len(occurrences) != 1:
        raise ValueError("Known nominal row type requires one target occurrence.")
    occurrence = occurrences[0]
    return ProjectResolvedType(
        name=resolution.canonical_name,
        kind=resolution.canonical_kind,
        symbol=ProjectSymbol(
            namespace=identity.namespace,
            kind=identity.declaration_kind,
            name=identity.declared_name,
            path=identity.module_path,
            location=_location(
                occurrence.definition.span,
                fallback_path=identity.module_path,
            ),
            definition=occurrence.definition,
        ),
    )


def _relation_row_state(
    draft: _RelationResolutionDraft,
    occurrence: ProjectDeclarationOccurrence,
    resolution: ProjectResolvedModuleRelationReference,
    upstream_state: ProjectRelationRowSchemaState,
) -> ProjectRelationRowSchemaState:
    if upstream_state.status is ProjectRelationRowSchemaStatus.UNKNOWN:
        return _unknown_state(ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN)
    if upstream_state.status is ProjectRelationRowSchemaStatus.DEFERRED:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        )
    if upstream_state.status is ProjectRelationRowSchemaStatus.BLOCKED:
        return _blocked_state(ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED)
    source_schema = upstream_state.schema
    if source_schema is None or source_schema.is_unknown:
        raise ValueError("Concrete upstream row state requires a concrete schema.")
    definition = occurrence.definition
    assert type(definition) in {TableDef, QueryDef}
    relation_definition = cast(TableDef | QueryDef, definition)
    if (
        relation_definition.let_clause is not None
        or relation_definition.group_by_clause is not None
        or any(
            type(item.expression) not in {NameExpr, DottedNameExpr}
            for item in relation_definition.select_items
        )
    ):
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR,
        )

    fields: dict[str, ProjectRowField] = {}
    diagnostics: list[ProjectModuleRelationResolutionIssue] = []
    duplicate = False
    for item in relation_definition.select_items:
        decoded = _direct_field_names(
            item,
            source_name=relation_definition.from_clause.source_name,
        )
        if decoded is None:
            field_text = _field_text(item)
            location = _location(item.expression.span, fallback_path=draft.module.path)
            diagnostics.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.UNKNOWN_DIRECT_FIELD,
                    owning_module_path=draft.module.path,
                    local_name=field_text,
                    location=location,
                    diagnostic=_diagnostic(
                        code="PIE-S2102",
                        message=f"Unknown field: {field_text}",
                        location=location,
                    ),
                    reference=resolution.reference,
                    select_item=item,
                )
            )
            continue
        output_name, lookup_name = decoded
        source_field = source_schema.fields.get(lookup_name)
        if source_field is None:
            field_text = _field_text(item)
            location = _location(item.expression.span, fallback_path=draft.module.path)
            diagnostics.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.UNKNOWN_DIRECT_FIELD,
                    owning_module_path=draft.module.path,
                    local_name=field_text,
                    location=location,
                    diagnostic=_diagnostic(
                        code="PIE-S2102",
                        message=f"Unknown field: {field_text}",
                        location=location,
                    ),
                    reference=resolution.reference,
                    select_item=item,
                )
            )
            continue
        if output_name in fields:
            duplicate = True
            continue
        fields[output_name] = ProjectRowField(
            name=output_name,
            resolved_type=source_field.resolved_type,
            nullability=source_field.nullability,
            field_def=source_field.field_def,
        )
    draft.issues.extend(diagnostics)
    if diagnostics:
        return _unknown_state(ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA)
    if duplicate:
        return _unknown_state(ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME)
    reason = (
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
        if resolution.target_symbol.declaration_kind is ProjectSymbolKind.SOURCE
        else ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
    )
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=ProjectRowSchema(fields=fields),
        reason=reason,
    )


def _direct_field_names(
    item: SelectItem,
    *,
    source_name: str,
) -> tuple[str, str] | None:
    expression = item.expression
    if type(expression) is NameExpr:
        return item.alias or expression.name, expression.name
    if type(expression) is DottedNameExpr and (
        len(expression.parts) == 2 and expression.parts[0] == source_name
    ):
        return item.alias or expression.parts[1], expression.parts[1]
    return None


def _field_text(item: SelectItem) -> str:
    expression = item.expression
    if type(expression) is NameExpr:
        return expression.name
    if type(expression) is DottedNameExpr:
        return ".".join(expression.parts)
    raise ValueError("Unknown direct field issue requires a name expression.")


def _source_duplicate_roots(
    environment: ProjectModuleTypeSourceResolutionEnvironment,
) -> dict[str, tuple[ProjectTypeSourceResolutionIssue, ...]]:
    result: dict[str, list[ProjectTypeSourceResolutionIssue]] = {}
    for issue in environment.issues:
        if (
            issue.status
            is ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_SOURCE_NAME
            and issue.local_name is not None
        ):
            result.setdefault(issue.local_name, []).append(issue)
    return {name: tuple(issues) for name, issues in result.items()}


def _duplicate_relation_issue(
    module_path: str,
    local_name: str,
    occurrences: tuple[ProjectDeclarationOccurrence, ...],
) -> ProjectModuleRelationResolutionIssue:
    primary = occurrences[1]
    location = _location(primary.definition.span, fallback_path=module_path)
    return ProjectModuleRelationResolutionIssue(
        status=ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME,
        owning_module_path=module_path,
        local_name=local_name,
        location=location,
        related_locations=_ordered_related_locations(
            location,
            tuple(
                _location(occurrence.definition.span, fallback_path=module_path)
                for occurrence in occurrences
            ),
        ),
        diagnostic=_diagnostic(
            code="PIE-S2001",
            message=f"Duplicate symbol name in relation namespace: {local_name}",
            location=location,
        ),
        occurrences=occurrences,
    )


def _local_relation_symbol(
    module_path: str,
    occurrence: ProjectDeclarationOccurrence,
) -> ProjectResolvedModuleRelationSymbol:
    return ProjectResolvedModuleRelationSymbol(
        owning_module_path=module_path,
        local_name=occurrence.identity.declared_name,
        target_identity=occurrence.identity,
        target_occurrence=occurrence,
        local_occurrence=occurrence,
    )


def _module_cycle_issues(
    graph: ProjectModuleGraph,
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> tuple[ProjectModuleRelationResolutionIssue, ...]:
    issues: list[ProjectModuleRelationResolutionIssue] = []
    for cycle in graph.cycles:
        roots = _suppressing_diagnostics_for_cycle(cycle, module_diagnostics)
        if not roots:
            raise ValueError("Cyclic module requires one PIE-S2703 root.")
        for member in cycle.component.members:
            location = roots[0].location
            issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
                    owning_module_path=member.identity.path,
                    local_name=None,
                    location=location,
                    related_locations=_ordered_related_locations(
                        location,
                        tuple(root.location for root in roots),
                    ),
                    module_cycle=cycle,
                    suppressing_diagnostics=roots,
                )
            )
    return tuple(
        sorted(
            issues,
            key=lambda issue: graph.find_path(issue.owning_module_path)[0].position,
        )
    )


def _unknown_state(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectRelationRowSchemaState:
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        schema=ProjectRowSchema(is_unknown=True),
        reason=reason,
    )


def _blocked_state(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectRelationRowSchemaState:
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.BLOCKED,
        schema=None,
        reason=reason,
    )


def _row_field_nullability(nullability: Nullability) -> ProjectRowFieldNullability:
    if nullability is Nullability.NOT_NULL:
        return ProjectRowFieldNullability.NON_NULL
    if nullability is Nullability.NULLABLE:
        return ProjectRowFieldNullability.NULLABLE
    return ProjectRowFieldNullability.UNKNOWN


def _validate_builder_inputs(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    module_diagnostics: ProjectModuleDiagnosticSet,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
) -> None:
    if type(modules) is not tuple or any(
        type(module) is not ProjectLogicalModule for module in modules
    ):
        raise TypeError("Relation resolver requires a logical-module tuple.")
    expected_types = (
        (catalogs, ProjectModuleCatalogSet),
        (exports, ProjectModuleExportSurfaceSet),
        (bindings, ProjectModuleBindingEnvironmentSet),
        (graph, ProjectModuleGraph),
        (module_diagnostics, ProjectModuleDiagnosticSet),
        (type_source_resolutions, ProjectTypeSourceResolutionSet),
    )
    for value, expected_type in expected_types:
        if type(value) is not expected_type:
            raise TypeError(f"Relation resolver requires {expected_type.__name__}.")
    lengths = {
        len(modules),
        len(catalogs.catalogs),
        len(exports.surfaces),
        len(bindings.environments),
        len(graph.vertices),
    }
    if len(lengths) != 1:
        raise ValueError("Relation resolver inputs must cover every module.")
    for position, (module, catalog, surface, environment, vertex) in enumerate(
        zip(
            modules,
            catalogs.catalogs,
            exports.surfaces,
            bindings.environments,
            graph.vertices,
            strict=True,
        )
    ):
        if (
            module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or module.position != position
            or module.parsed_input is None
            or catalog.module is not module
            or surface.module is not module
            or environment.module is not module
            or vertex.module is not module
        ):
            raise ValueError("Relation resolver inputs must retain module order.")


def _validate_relation_identity(
    identity: ProjectNominalDeclarationIdentity,
) -> None:
    if (
        identity.namespace is not ProjectSymbolNamespace.RELATION
        or identity.declaration_kind not in _RELATION_KINDS
    ):
        raise ValueError("Resolved identity is not relation-producing.")


def _validate_issue_evidence(issue: ProjectModuleRelationResolutionIssue) -> None:
    status = issue.status
    code = None if issue.diagnostic is None else issue.diagnostic.code
    if (
        status
        is ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME
    ):
        valid = (
            len(issue.occurrences) > 1
            and issue.reference is None
            and issue.select_item is None
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and code == "PIE-S2001"
        )
    elif (
        status is ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_REFERENCE
    ):
        valid = (
            issue.reference is not None
            and issue.select_item is None
            and not issue.occurrences
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and code == "PIE-S2301"
        )
    elif status is ProjectModuleRelationResolutionIssueStatus.UNKNOWN_DIRECT_FIELD:
        valid = (
            issue.reference is not None
            and issue.select_item is not None
            and not issue.occurrences
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and code == "PIE-S2102"
        )
    elif status is ProjectModuleRelationResolutionIssueStatus.LOCAL_RELATION_CYCLE:
        valid = (
            len(issue.relation_cycle) > 0
            and issue.reference is None
            and issue.select_item is None
            and not issue.occurrences
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.type_source_issues
            and code == "PIE-S2302"
        )
    elif (
        status is ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
    ):
        valid = (
            issue.module_cycle is not None
            and issue.reference is None
            and issue.select_item is None
            and not issue.occurrences
            and not issue.binding_issues
            and not issue.relation_cycle
            and not issue.type_source_issues
            and issue.diagnostic is None
            and tuple(root.code for root in issue.suppressing_diagnostics)
            == ("PIE-S2703",)
        )
    elif status is ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED:
        valid = (
            issue.local_name is not None
            and (bool(issue.binding_issues) != bool(issue.occurrences))
            and issue.reference is None
            and issue.select_item is None
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and issue.diagnostic is None
            and bool(issue.suppressing_diagnostics)
        )
    else:
        valid = (
            issue.local_name is not None
            and bool(issue.occurrences)
            and bool(issue.type_source_issues)
            and issue.reference is None
            and issue.select_item is None
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and issue.diagnostic is None
            and bool(issue.suppressing_diagnostics)
        )
    if not valid:
        raise ValueError("Relation issue evidence must prove its exact status.")


def _diagnostic(*, code: str, message: str, location: SourceLocation) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=location,
    )


def _location(span: Span, *, fallback_path: str) -> SourceLocation:
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _ordered_related_locations(
    primary: SourceLocation,
    locations: tuple[SourceLocation, ...],
) -> tuple[SourceLocation, ...]:
    unique = {
        (
            location.path or "",
            location.line,
            location.column,
            location.end_line if location.end_line is not None else -1,
            location.end_column if location.end_column is not None else -1,
        ): location
        for location in locations
        if location != primary
    }
    return tuple(unique[key] for key in sorted(unique))


def _issue_source_key(
    issue: ProjectModuleRelationResolutionIssue,
) -> tuple[object, ...]:
    rank = {
        status: position
        for position, status in enumerate(ProjectModuleRelationResolutionIssueStatus)
    }
    location = issue.location
    return (
        location.line,
        location.column,
        location.end_line if location.end_line is not None else -1,
        location.end_column if location.end_column is not None else -1,
        rank[issue.status],
        issue.local_name or "",
    )


def _tuple_mapping(
    values: Mapping[_KeyT, list[_ValueT]],
) -> Mapping[_KeyT, tuple[_ValueT, ...]]:
    return MappingProxyType({key: tuple(items) for key, items in values.items()})


def _require_tuple_items(
    values: tuple[object, ...], item_type: type, label: str
) -> None:
    if type(values) is not tuple or any(type(item) is not item_type for item in values):
        raise TypeError(f"{label} must be a tuple of {item_type.__name__} values.")
