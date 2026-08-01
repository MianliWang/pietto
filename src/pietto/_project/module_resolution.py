"""Private schema-v2 cross-module type and source resolution facts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar

from pietto._project.model import (
    ProjectResolvedTypeKind,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
    _PROJECT_BUILTIN_TYPE_NAMES,
)
from pietto._project.module_bindings import (
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
    ProjectModuleGraphVertex,
)
from pietto.ast_nodes import ShapeDef, SourceDef, Span, TypeDef, TypeExpr
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()

_TYPE_KINDS = frozenset(
    {
        ProjectSymbolKind.TYPE_ALIAS,
        ProjectSymbolKind.ENUM,
        ProjectSymbolKind.SHAPE,
    }
)
_KeyT = TypeVar("_KeyT")
_ValueT = TypeVar("_ValueT")


class ProjectModuleTypeReferenceRole(StrEnum):
    """Closed schema-v2 type-reference roles owned by Slice 9."""

    TYPE_ALIAS_BASE = "type_alias_base"
    SHAPE_FIELD_TYPE = "shape_field_type"


class ProjectTypeSourceResolutionIssueStatus(StrEnum):
    """Closed private failure and suppression facts for Slice 9."""

    AMBIGUOUS_LOCAL_TYPE_NAME = "ambiguous_local_type_name"
    AMBIGUOUS_LOCAL_SOURCE_NAME = "ambiguous_local_source_name"
    UNKNOWN_TYPE_REFERENCE = "unknown_type_reference"
    TYPE_ALIAS_CYCLE = "type_alias_cycle"
    UNKNOWN_SOURCE_SHAPE_REFERENCE = "unknown_source_shape_reference"
    INCOMPATIBLE_SOURCE_SHAPE_KIND = "incompatible_source_shape_kind"
    MODULE_GRAPH_CYCLE_BLOCKED = "module_graph_cycle_blocked"
    MODULE_DIAGNOSTIC_BLOCKED = "module_diagnostic_blocked"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResolvedNominalSymbol:
    """One local lookup name bound to one exact nominal declaration."""

    owning_module_path: str
    local_name: str
    target_identity: ProjectNominalDeclarationIdentity
    target_occurrence: ProjectDeclarationOccurrence
    local_occurrence: ProjectDeclarationOccurrence | None = None
    imported_binding: ProjectResolvedImportedBinding | None = None

    def __post_init__(self) -> None:
        """Reject facts that collapse local and target identity."""

        ProjectModuleIdentity(path=self.owning_module_path)
        if type(self.local_name) is not str or not self.local_name:
            raise ValueError("Resolved nominal symbol requires a local name.")
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Resolved nominal symbol requires a target identity.")
        if type(self.target_occurrence) is not ProjectDeclarationOccurrence:
            raise TypeError("Resolved nominal symbol requires a target occurrence.")
        if self.target_occurrence.identity != self.target_identity:
            raise ValueError("Resolved nominal target occurrence must match identity.")
        local = self.local_occurrence
        imported = self.imported_binding
        if (local is None) == (imported is None):
            raise ValueError(
                "Resolved nominal symbol requires exactly one local binding source."
            )
        if local is not None:
            if type(local) is not ProjectDeclarationOccurrence:
                raise TypeError("Local nominal symbol requires an occurrence.")
            if (
                local is not self.target_occurrence
                or local.identity != self.target_identity
                or self.target_identity.module_path != self.owning_module_path
                or self.target_identity.declared_name != self.local_name
            ):
                raise ValueError("Local nominal symbol must retain local identity.")
        else:
            if type(imported) is not ProjectResolvedImportedBinding:
                raise TypeError("Imported nominal symbol requires a resolved binding.")
            if (
                imported.identity.owning_module_path != self.owning_module_path
                or imported.identity.local_binding_name != self.local_name
                or imported.target_identity != self.target_identity
                or imported.identity.namespace is not self.target_identity.namespace
                or imported.identity.declaration_kind
                is not self.target_identity.declaration_kind
            ):
                raise ValueError(
                    "Imported nominal symbol must preserve local and target identity."
                )
        _validate_slice9_identity(self.target_identity)

    @property
    def namespace(self) -> ProjectSymbolNamespace:
        """Return the exact existing namespace of the target declaration."""

        return self.target_identity.namespace

    @property
    def declaration_kind(self) -> ProjectSymbolKind:
        """Return the exact existing declaration kind of the target."""

        return self.target_identity.declaration_kind


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleTypeReference:
    """One exact schema-v2 type-bearing AST site."""

    owner: ProjectDeclarationOccurrence
    role: ProjectModuleTypeReferenceRole
    member_position: int
    type_expr: TypeExpr

    def __post_init__(self) -> None:
        """Require the role and position to match the retained AST."""

        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Module type reference requires an owner occurrence.")
        if type(self.role) is not ProjectModuleTypeReferenceRole:
            raise TypeError("Module type reference requires an exact role.")
        if type(self.member_position) is not int or self.member_position < 0:
            raise ValueError("Module type reference position must be non-negative.")
        if type(self.type_expr) is not TypeExpr:
            raise TypeError("Module type reference requires a TypeExpr.")
        definition = self.owner.definition
        if self.role is ProjectModuleTypeReferenceRole.TYPE_ALIAS_BASE:
            valid = (
                type(definition) is TypeDef
                and self.owner.identity.declaration_kind is ProjectSymbolKind.TYPE_ALIAS
                and self.member_position == 0
                and definition.base is self.type_expr
            )
        else:
            valid = (
                type(definition) is ShapeDef
                and self.owner.identity.declaration_kind is ProjectSymbolKind.SHAPE
                and self.member_position < len(definition.fields)
                and definition.fields[self.member_position].type_expr is self.type_expr
            )
        if not valid:
            raise ValueError("Module type reference must match its retained AST site.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResolvedModuleTypeReference:
    """Direct and canonical resolution of one module type reference."""

    reference: ProjectModuleTypeReference
    direct_kind: ProjectResolvedTypeKind
    direct_symbol: ProjectResolvedNominalSymbol | None
    canonical_kind: ProjectResolvedTypeKind
    canonical_name: str
    canonical_target_identity: ProjectNominalDeclarationIdentity | None
    alias_chain: tuple[ProjectNominalDeclarationIdentity, ...] = ()

    def __post_init__(self) -> None:
        """Require complete direct identity and canonical terminal facts."""

        if type(self.reference) is not ProjectModuleTypeReference:
            raise TypeError("Resolved module type requires a reference.")
        if type(self.direct_kind) is not ProjectResolvedTypeKind:
            raise TypeError("Resolved module type requires a direct kind.")
        if type(self.canonical_kind) is not ProjectResolvedTypeKind:
            raise TypeError("Resolved module type requires a canonical kind.")
        if type(self.canonical_name) is not str or not self.canonical_name:
            raise ValueError("Resolved module type requires a canonical name.")
        _require_tuple_items(
            self.alias_chain,
            ProjectNominalDeclarationIdentity,
            "Resolved module alias chain",
        )
        if len(set(self.alias_chain)) != len(self.alias_chain) or any(
            identity.namespace is not ProjectSymbolNamespace.TYPE
            or identity.declaration_kind is not ProjectSymbolKind.TYPE_ALIAS
            for identity in self.alias_chain
        ):
            raise ValueError("Resolved module alias chain must be unique aliases.")

        if self.direct_kind in {
            ProjectResolvedTypeKind.TYPE_ALIAS,
            ProjectResolvedTypeKind.ENUM,
            ProjectResolvedTypeKind.SHAPE,
        }:
            if type(self.direct_symbol) is not ProjectResolvedNominalSymbol:
                raise TypeError("Nominal direct type requires a resolved symbol.")
            expected_kind = _resolved_kind(self.direct_symbol.declaration_kind)
            if expected_kind is not self.direct_kind:
                raise ValueError("Direct type kind must match its nominal symbol.")
        elif self.direct_symbol is not None:
            raise ValueError("Builtin and unknown direct types forbid a symbol.")

        if self.direct_kind is ProjectResolvedTypeKind.TYPE_ALIAS:
            if not self.alias_chain or (
                self.direct_symbol is None
                or self.alias_chain[0] != self.direct_symbol.target_identity
            ):
                raise ValueError("Direct alias resolution requires its exact chain.")
        elif self.alias_chain:
            raise ValueError("Only a direct alias may carry an alias chain.")

        if self.canonical_kind is ProjectResolvedTypeKind.TYPE_ALIAS:
            raise ValueError("Canonical module type cannot terminate at an alias.")
        if self.canonical_kind in {
            ProjectResolvedTypeKind.ENUM,
            ProjectResolvedTypeKind.SHAPE,
        }:
            identity = self.canonical_target_identity
            if type(identity) is not ProjectNominalDeclarationIdentity:
                raise TypeError("Canonical nominal type requires a target identity.")
            if (
                _resolved_kind(identity.declaration_kind) is not self.canonical_kind
                or identity.declared_name != self.canonical_name
            ):
                raise ValueError("Canonical target must match kind and name.")
        elif self.canonical_target_identity is not None:
            raise ValueError("Builtin and unknown canonical types forbid a target.")
        if self.canonical_kind is ProjectResolvedTypeKind.UNKNOWN:
            if self.canonical_name != "<unknown>":
                raise ValueError("Unknown canonical module type uses <unknown>.")
        elif self.canonical_kind is ProjectResolvedTypeKind.BUILTIN:
            if self.canonical_name not in _PROJECT_BUILTIN_TYPE_NAMES:
                raise ValueError("Canonical builtin must use a builtin name.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleSourceShapeReference:
    """One exact SourceDef shape-name reference."""

    owner: ProjectDeclarationOccurrence
    source: SourceDef

    def __post_init__(self) -> None:
        """Require one shape-bearing source occurrence."""

        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Source shape reference requires an owner occurrence.")
        if type(self.source) is not SourceDef:
            raise TypeError("Source shape reference requires a SourceDef.")
        if (
            self.owner.definition is not self.source
            or self.owner.identity.declaration_kind is not ProjectSymbolKind.SOURCE
            or self.source.shape_name is None
        ):
            raise ValueError("Source shape reference must match a shaped source.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResolvedModuleSourceShapeReference:
    """One direct source-to-shape nominal resolution."""

    reference: ProjectModuleSourceShapeReference
    target_symbol: ProjectResolvedNominalSymbol

    def __post_init__(self) -> None:
        """Require an exact direct shape target."""

        if type(self.reference) is not ProjectModuleSourceShapeReference:
            raise TypeError("Resolved source shape requires a reference.")
        if type(self.target_symbol) is not ProjectResolvedNominalSymbol:
            raise TypeError("Resolved source shape requires a nominal symbol.")
        if (
            self.target_symbol.namespace is not ProjectSymbolNamespace.TYPE
            or self.target_symbol.declaration_kind is not ProjectSymbolKind.SHAPE
            or self.target_symbol.local_name != self.reference.source.shape_name
        ):
            raise ValueError("Resolved source shape requires the direct local shape.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectTypeSourceResolutionIssue:
    """One typed emitted or suppressed Slice 9 resolution issue."""

    status: ProjectTypeSourceResolutionIssueStatus
    owning_module_path: str
    local_name: str | None
    location: SourceLocation
    related_locations: tuple[SourceLocation, ...] = ()
    diagnostic: Diagnostic | None = None
    occurrences: tuple[ProjectDeclarationOccurrence, ...] = ()
    type_reference: ProjectModuleTypeReference | None = None
    source_reference: ProjectModuleSourceShapeReference | None = None
    binding_issues: tuple[ProjectModuleBindingIssue, ...] = ()
    cycle: ProjectModuleCycle | None = None
    alias_cycle: tuple[ProjectNominalDeclarationIdentity, ...] = ()
    suppressing_diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        """Reject untyped evidence, mixed roots, or incorrect adaptation."""

        if type(self.status) is not ProjectTypeSourceResolutionIssueStatus:
            raise TypeError("Type/source issue requires an exact status.")
        ProjectModuleIdentity(path=self.owning_module_path)
        if self.local_name is not None and (
            type(self.local_name) is not str or not self.local_name
        ):
            raise ValueError("Type/source issue local name must be non-empty.")
        if type(self.location) is not SourceLocation:
            raise TypeError("Type/source issue requires a source location.")
        _require_tuple_items(
            self.related_locations,
            SourceLocation,
            "Type/source issue related locations",
        )
        _require_tuple_items(
            self.occurrences,
            ProjectDeclarationOccurrence,
            "Type/source issue occurrences",
        )
        _require_tuple_items(
            self.binding_issues,
            ProjectModuleBindingIssue,
            "Type/source issue binding issues",
        )
        _require_tuple_items(
            self.alias_cycle,
            ProjectNominalDeclarationIdentity,
            "Type/source issue alias cycle",
        )
        _require_tuple_items(
            self.suppressing_diagnostics,
            Diagnostic,
            "Type/source issue suppressing diagnostics",
        )
        if self.diagnostic is not None:
            if type(self.diagnostic) is not Diagnostic:
                raise TypeError("Type/source issue diagnostic must be a Diagnostic.")
            if (
                self.diagnostic.severity is not Severity.ERROR
                or self.diagnostic.location != self.location
                or self.diagnostic.suggestion is not None
                or self.suppressing_diagnostics
            ):
                raise ValueError("Emitted type/source diagnostic must be exact.")
        elif not self.suppressing_diagnostics:
            raise ValueError("Suppressed type/source issue requires its root.")
        _validate_issue_evidence(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleTypeSourceResolutionEnvironment:
    """One dependency-ordered module-local type/source resolution result."""

    module: ProjectLogicalModule
    symbols: tuple[ProjectResolvedNominalSymbol, ...] = ()
    type_resolutions: tuple[ProjectResolvedModuleTypeReference, ...] = ()
    source_shape_references: tuple[ProjectModuleSourceShapeReference, ...] = ()
    source_shape_resolutions: tuple[ProjectResolvedModuleSourceShapeReference, ...] = ()
    issues: tuple[ProjectTypeSourceResolutionIssue, ...] = ()
    _type_symbols_by_name: Mapping[str, tuple[ProjectResolvedNominalSymbol, ...]] = (
        field(init=False, repr=False, compare=False, hash=False)
    )
    _source_symbols_by_name: Mapping[str, tuple[ProjectResolvedNominalSymbol, ...]] = (
        field(init=False, repr=False, compare=False, hash=False)
    )
    _type_resolutions_by_expr: Mapping[
        TypeExpr, tuple[ProjectResolvedModuleTypeReference, ...]
    ] = field(init=False, repr=False, compare=False, hash=False)
    _source_resolutions_by_source: Mapping[
        SourceDef, tuple[ProjectResolvedModuleSourceShapeReference, ...]
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Copy complete lookup buckets and reject foreign facts."""

        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Type/source environment requires a logical module.")
        if (
            self.module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or self.module.parsed_input is None
        ):
            raise ValueError("Type/source environment requires a parsed module.")
        _require_tuple_items(
            self.symbols,
            ProjectResolvedNominalSymbol,
            "Type/source environment symbols",
        )
        _require_tuple_items(
            self.type_resolutions,
            ProjectResolvedModuleTypeReference,
            "Type/source environment type resolutions",
        )
        _require_tuple_items(
            self.source_shape_references,
            ProjectModuleSourceShapeReference,
            "Type/source environment source references",
        )
        _require_tuple_items(
            self.source_shape_resolutions,
            ProjectResolvedModuleSourceShapeReference,
            "Type/source environment source resolutions",
        )
        _require_tuple_items(
            self.issues,
            ProjectTypeSourceResolutionIssue,
            "Type/source environment issues",
        )
        if any(
            symbol.owning_module_path != self.module.path for symbol in self.symbols
        ):
            raise ValueError("Environment symbols must use its local module path.")
        if any(
            resolution.reference.owner.identity.module_path != self.module.path
            for resolution in self.type_resolutions
        ):
            raise ValueError("Environment type resolutions must be module-local.")
        if any(
            reference.owner.identity.module_path != self.module.path
            for reference in self.source_shape_references
        ):
            raise ValueError("Environment source references must be module-local.")
        if any(
            resolution.reference not in self.source_shape_references
            for resolution in self.source_shape_resolutions
        ):
            raise ValueError("Source resolutions require retained references.")
        if any(issue.owning_module_path != self.module.path for issue in self.issues):
            raise ValueError("Environment issues must be module-local.")

        type_symbols: dict[str, list[ProjectResolvedNominalSymbol]] = {}
        source_symbols: dict[str, list[ProjectResolvedNominalSymbol]] = {}
        for symbol in self.symbols:
            if symbol.declaration_kind in _TYPE_KINDS:
                type_symbols.setdefault(symbol.local_name, []).append(symbol)
            else:
                source_symbols.setdefault(symbol.local_name, []).append(symbol)
        if any(
            len(items) != 1
            for items in (*type_symbols.values(), *source_symbols.values())
        ):
            raise ValueError("Environment symbol buckets cannot select a winner.")
        type_resolutions: dict[TypeExpr, list[ProjectResolvedModuleTypeReference]] = {}
        for resolution in self.type_resolutions:
            type_resolutions.setdefault(resolution.reference.type_expr, []).append(
                resolution
            )
        source_resolutions: dict[
            SourceDef, list[ProjectResolvedModuleSourceShapeReference]
        ] = {}
        for resolution in self.source_shape_resolutions:
            source_resolutions.setdefault(resolution.reference.source, []).append(
                resolution
            )
        object.__setattr__(
            self,
            "_type_symbols_by_name",
            _tuple_mapping(type_symbols),
        )
        object.__setattr__(
            self,
            "_source_symbols_by_name",
            _tuple_mapping(source_symbols),
        )
        object.__setattr__(
            self,
            "_type_resolutions_by_expr",
            _tuple_mapping(type_resolutions),
        )
        object.__setattr__(
            self,
            "_source_resolutions_by_source",
            _tuple_mapping(source_resolutions),
        )

    def find_type_name(
        self, local_name: str
    ) -> tuple[ProjectResolvedNominalSymbol, ...]:
        """Return the complete exact local type-name bucket."""

        if type(local_name) is not str:
            raise TypeError("Type-name lookup requires a string.")
        return self._type_symbols_by_name.get(local_name, ())

    def find_source_name(
        self, local_name: str
    ) -> tuple[ProjectResolvedNominalSymbol, ...]:
        """Return the complete exact local source-name bucket."""

        if type(local_name) is not str:
            raise TypeError("Source-name lookup requires a string.")
        return self._source_symbols_by_name.get(local_name, ())

    def find_type_expr(
        self, type_expr: TypeExpr
    ) -> tuple[ProjectResolvedModuleTypeReference, ...]:
        """Return the exact retained resolution for one AST TypeExpr."""

        if type(type_expr) is not TypeExpr:
            raise TypeError("Type-expression lookup requires a TypeExpr.")
        return self._type_resolutions_by_expr.get(type_expr, ())

    def find_source(
        self, source: SourceDef
    ) -> tuple[ProjectResolvedModuleSourceShapeReference, ...]:
        """Return an exact successful source-shape resolution, or empty."""

        if type(source) is not SourceDef:
            raise TypeError("Source-shape lookup requires a SourceDef.")
        return self._source_resolutions_by_source.get(source, ())


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectTypeSourceResolutionSet:
    """The complete private schema-v2 Slice 9 resolution product."""

    dependency_order: tuple[ProjectModuleIdentity, ...] = ()
    environments: tuple[ProjectModuleTypeSourceResolutionEnvironment, ...] = ()
    issues: tuple[ProjectTypeSourceResolutionIssue, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    _environments_by_path: Mapping[
        str, ProjectModuleTypeSourceResolutionEnvironment
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Require dependency order, unique paths, and exact diagnostics."""

        _require_tuple_items(
            self.dependency_order,
            ProjectModuleIdentity,
            "Type/source dependency order",
        )
        _require_tuple_items(
            self.environments,
            ProjectModuleTypeSourceResolutionEnvironment,
            "Type/source environments",
        )
        _require_tuple_items(
            self.issues,
            ProjectTypeSourceResolutionIssue,
            "Type/source issues",
        )
        _require_tuple_items(
            self.diagnostics,
            Diagnostic,
            "Type/source diagnostics",
        )
        environment_paths = tuple(item.module.path for item in self.environments)
        if environment_paths != tuple(item.path for item in self.dependency_order):
            raise ValueError("Type/source environments must follow dependency order.")
        if len(set(environment_paths)) != len(environment_paths):
            raise ValueError("Type/source environment paths must be unique.")
        expected_diagnostics = tuple(
            issue.diagnostic for issue in self.issues if issue.diagnostic is not None
        )
        if self.diagnostics != expected_diagnostics:
            raise ValueError("Type/source diagnostics must project exact issues.")
        by_path = {item.module.path: item for item in self.environments}
        object.__setattr__(
            self,
            "_environments_by_path",
            MappingProxyType(dict(by_path)),
        )

    def find_module_path(
        self, module_path: str
    ) -> tuple[ProjectModuleTypeSourceResolutionEnvironment, ...]:
        """Return one exact resolved environment, or an empty tuple."""

        try:
            ProjectModuleIdentity(path=module_path)
        except (TypeError, ValueError):
            return ()
        environment = self._environments_by_path.get(module_path)
        return () if environment is None else (environment,)


@dataclass(slots=True)
class _ModuleResolutionDraft:
    module: ProjectLogicalModule
    catalog: ProjectModuleCatalog
    symbols: list[ProjectResolvedNominalSymbol]
    type_references: list[ProjectModuleTypeReference]
    source_references: list[ProjectModuleSourceShapeReference]
    issues: list[ProjectTypeSourceResolutionIssue]
    blocked_type_names: set[str]
    blocked_source_names: set[str]
    ambiguous_type_names: set[str]
    ambiguous_source_names: set[str]


@dataclass(frozen=True, slots=True)
class _DirectTypeResolution:
    reference: ProjectModuleTypeReference
    kind: ProjectResolvedTypeKind
    symbol: ProjectResolvedNominalSymbol | None


@dataclass(frozen=True, slots=True)
class _CanonicalType:
    kind: ProjectResolvedTypeKind
    name: str
    target_identity: ProjectNominalDeclarationIdentity | None


_UNKNOWN_CANONICAL = _CanonicalType(
    kind=ProjectResolvedTypeKind.UNKNOWN,
    name="<unknown>",
    target_identity=None,
)


def _build_project_type_source_resolution_set(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> ProjectTypeSourceResolutionSet:
    """Build the pure dependency-first schema-v2 type/source resolution set."""

    _validate_builder_inputs(
        modules,
        catalogs,
        exports,
        bindings,
        graph,
        module_diagnostics,
    )
    dependency_vertices = _dependency_first_vertices(graph)
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
    environment_by_path = {
        environment.module.path: environment for environment in bindings.environments
    }
    surface_by_path = {surface.module.path: surface for surface in exports.surfaces}
    processed_paths: set[str] = set()
    drafts: list[_ModuleResolutionDraft] = []

    for vertex in dependency_vertices:
        module = vertex.module
        catalog = catalog_by_path[module.path]
        binding_environment = environment_by_path[module.path]
        draft = _ModuleResolutionDraft(
            module=module,
            catalog=catalog,
            symbols=[],
            type_references=_collect_type_references(catalog),
            source_references=_collect_source_references(catalog),
            issues=[],
            blocked_type_names=set(),
            blocked_source_names=set(),
            ambiguous_type_names=set(),
            ambiguous_source_names=set(),
        )
        _collect_module_diagnostic_blockers(
            draft,
            binding_environment.issues,
            module_diagnostics,
        )
        _collect_local_symbols(draft)
        _collect_imported_symbols(
            draft,
            binding_environment.bindings,
            catalogs=catalogs,
            target_surface_by_path=surface_by_path,
            processed_paths=processed_paths,
            cyclic_paths=cyclic_paths,
            cycle_by_path=cycle_by_path,
            module_diagnostics=module_diagnostics,
        )
        drafts.append(draft)
        processed_paths.add(module.path)

    direct_by_reference: dict[ProjectModuleTypeReference, _DirectTypeResolution] = {}
    for draft in drafts:
        for reference in draft.type_references:
            direct_by_reference[reference] = _resolve_direct_type(draft, reference)

    alias_base_by_identity: dict[
        ProjectNominalDeclarationIdentity, _DirectTypeResolution
    ] = {}
    alias_occurrence_by_identity: dict[
        ProjectNominalDeclarationIdentity, ProjectDeclarationOccurrence
    ] = {}
    for draft in drafts:
        local_symbol_identities = {
            symbol.target_identity
            for symbol in draft.symbols
            if symbol.local_occurrence is not None
            and symbol.declaration_kind is ProjectSymbolKind.TYPE_ALIAS
        }
        for reference in draft.type_references:
            if (
                reference.role is ProjectModuleTypeReferenceRole.TYPE_ALIAS_BASE
                and reference.owner.identity in local_symbol_identities
            ):
                alias_base_by_identity[reference.owner.identity] = direct_by_reference[
                    reference
                ]
                alias_occurrence_by_identity[reference.owner.identity] = reference.owner

    canonical_by_alias, cycle_issues = _expand_aliases(
        alias_base_by_identity,
        alias_occurrence_by_identity,
    )
    draft_by_path = {draft.module.path: draft for draft in drafts}
    for issue in cycle_issues:
        draft_by_path[issue.owning_module_path].issues.append(issue)

    environments: list[ProjectModuleTypeSourceResolutionEnvironment] = []
    all_issues: list[ProjectTypeSourceResolutionIssue] = []
    for draft in drafts:
        type_resolutions = tuple(
            _resolved_type_reference(
                direct_by_reference[reference],
                alias_base_by_identity,
                canonical_by_alias,
            )
            for reference in draft.type_references
        )
        source_resolutions = _resolve_source_shapes(draft)
        ordered_issues = tuple(sorted(draft.issues, key=_issue_source_key))
        environment = ProjectModuleTypeSourceResolutionEnvironment(
            module=draft.module,
            symbols=tuple(draft.symbols),
            type_resolutions=type_resolutions,
            source_shape_references=tuple(draft.source_references),
            source_shape_resolutions=source_resolutions,
            issues=ordered_issues,
        )
        environments.append(environment)
        all_issues.extend(ordered_issues)

    cycle_member_issues = _cycle_member_issues(
        graph,
        module_diagnostics,
    )
    all_issues.extend(cycle_member_issues)
    issue_tuple = tuple(all_issues)
    return ProjectTypeSourceResolutionSet(
        dependency_order=tuple(vertex.identity for vertex in dependency_vertices),
        environments=tuple(environments),
        issues=issue_tuple,
        diagnostics=tuple(
            issue.diagnostic for issue in issue_tuple if issue.diagnostic is not None
        ),
    )


def _dependency_first_vertices(
    graph: ProjectModuleGraph,
) -> tuple[ProjectModuleGraphVertex, ...]:
    cyclic = {member for cycle in graph.cycles for member in cycle.component.members}
    valid = tuple(vertex for vertex in graph.vertices if vertex not in cyclic)
    valid_set = set(valid)
    remaining_dependencies = {
        vertex: {
            edge.target for edge in graph.outgoing(vertex) if edge.target in valid_set
        }
        for vertex in valid
    }
    emitted: list[ProjectModuleGraphVertex] = []
    emitted_set: set[ProjectModuleGraphVertex] = set()
    while len(emitted) < len(valid):
        ready = tuple(
            vertex
            for vertex in valid
            if vertex not in emitted_set
            and remaining_dependencies[vertex] <= emitted_set
        )
        if not ready:
            raise ValueError("Acyclic module graph must have a dependency-first order.")
        chosen = min(ready, key=lambda item: item.position)
        emitted.append(chosen)
        emitted_set.add(chosen)
    return tuple(emitted)


def _collect_module_diagnostic_blockers(
    draft: _ModuleResolutionDraft,
    binding_issues: tuple[ProjectModuleBindingIssue, ...],
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> None:
    buckets: dict[
        tuple[ProjectSymbolNamespace, str], list[ProjectModuleBindingIssue]
    ] = {}
    for issue in binding_issues:
        if issue.status is ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST:
            continue
        kind = issue.request.identity.declaration_kind
        if kind in _TYPE_KINDS:
            namespace = ProjectSymbolNamespace.TYPE
        elif kind is ProjectSymbolKind.SOURCE:
            namespace = ProjectSymbolNamespace.RELATION
        else:
            continue
        buckets.setdefault(
            (namespace, issue.request.identity.local_binding_name), []
        ).append(issue)

    for (namespace, local_name), issues in buckets.items():
        issue_tuple = tuple(issues)
        roots = _suppressing_diagnostics_for_binding_issues(
            issue_tuple,
            module_diagnostics,
        )
        if not roots:
            raise ValueError("Blocked module binding requires a Slice 8 root.")
        request = min(
            (issue.request for issue in issue_tuple),
            key=lambda item: (item.module_statement_position, item.item_position),
        )
        span = (
            request.source_item.local_name_span
            or request.source_item.exported_name_span
        )
        location = _location(span, fallback_path=draft.module.path)
        related = _ordered_related_locations(
            location,
            tuple(root.location for root in roots),
        )
        draft.issues.append(
            ProjectTypeSourceResolutionIssue(
                status=ProjectTypeSourceResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
                owning_module_path=draft.module.path,
                local_name=local_name,
                location=location,
                related_locations=related,
                binding_issues=issue_tuple,
                suppressing_diagnostics=roots,
            )
        )
        if namespace is ProjectSymbolNamespace.TYPE:
            draft.blocked_type_names.add(local_name)
        else:
            draft.blocked_source_names.add(local_name)

    export_buckets: dict[
        tuple[ProjectSymbolNamespace, str], list[ProjectModuleExportIssue]
    ] = {}
    for fact in module_diagnostics.facts:
        for issue in fact.export_issues:
            if (
                issue.request.owning_module_path != draft.module.path
                or issue.status
                is not ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION
            ):
                continue
            kind = issue.request.declaration_kind
            if kind in _TYPE_KINDS:
                namespace = ProjectSymbolNamespace.TYPE
            elif kind is ProjectSymbolKind.SOURCE:
                namespace = ProjectSymbolNamespace.RELATION
            else:
                continue
            export_buckets.setdefault((namespace, issue.request.local_name), []).append(
                issue
            )

    for (namespace, local_name), issues in export_buckets.items():
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
            raise ValueError("Blocked local ambiguity requires its Slice 8 root.")
        location = roots[0].location
        draft.issues.append(
            ProjectTypeSourceResolutionIssue(
                status=ProjectTypeSourceResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
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
        if namespace is ProjectSymbolNamespace.TYPE:
            draft.blocked_type_names.add(local_name)
        else:
            draft.blocked_source_names.add(local_name)


def _collect_local_symbols(draft: _ModuleResolutionDraft) -> None:
    type_buckets: dict[str, list[ProjectDeclarationOccurrence]] = {}
    source_buckets: dict[str, list[ProjectDeclarationOccurrence]] = {}
    for occurrence in draft.catalog.occurrences:
        identity = occurrence.identity
        if identity.namespace is ProjectSymbolNamespace.TYPE and (
            identity.declaration_kind in _TYPE_KINDS
        ):
            type_buckets.setdefault(identity.declared_name, []).append(occurrence)
        elif identity.declaration_kind is ProjectSymbolKind.SOURCE:
            source_buckets.setdefault(identity.declared_name, []).append(occurrence)

    for local_name, occurrences in type_buckets.items():
        if len(occurrences) > 1:
            draft.ambiguous_type_names.add(local_name)
            if local_name not in draft.blocked_type_names:
                draft.issues.append(
                    _duplicate_issue(
                        draft.module.path,
                        local_name,
                        tuple(occurrences),
                        type_namespace=True,
                    )
                )
            continue
        if local_name not in draft.blocked_type_names:
            draft.symbols.append(_local_symbol(draft.module.path, occurrences[0]))

    for local_name, occurrences in source_buckets.items():
        if len(occurrences) > 1:
            draft.ambiguous_source_names.add(local_name)
            if local_name not in draft.blocked_source_names:
                draft.issues.append(
                    _duplicate_issue(
                        draft.module.path,
                        local_name,
                        tuple(occurrences),
                        type_namespace=False,
                    )
                )
            continue
        if local_name not in draft.blocked_source_names:
            draft.symbols.append(_local_symbol(draft.module.path, occurrences[0]))


def _collect_imported_symbols(
    draft: _ModuleResolutionDraft,
    imported_bindings: tuple[ProjectResolvedImportedBinding, ...],
    *,
    catalogs: ProjectModuleCatalogSet,
    target_surface_by_path: Mapping[str, ProjectModuleExportSurface],
    processed_paths: set[str],
    cyclic_paths: set[str],
    cycle_by_path: Mapping[str, ProjectModuleCycle],
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> None:
    for binding in imported_bindings:
        kind = binding.identity.declaration_kind
        if kind in _TYPE_KINDS:
            blocked_names = draft.blocked_type_names
        elif kind is ProjectSymbolKind.SOURCE:
            blocked_names = draft.blocked_source_names
        else:
            continue
        local_name = binding.identity.local_binding_name
        if local_name in blocked_names:
            continue
        surface = target_surface_by_path.get(binding.target_module_path)
        if surface is None or binding.resolved_entry not in surface.entries:
            raise ValueError("Imported resolution requires its exact target facade.")
        target_path = binding.target_identity.module_path
        if target_path in cyclic_paths:
            cycle = cycle_by_path[target_path]
            roots = _suppressing_diagnostics_for_cycle(cycle, module_diagnostics)
            if not roots:
                raise ValueError("Cyclic imported target requires PIE-S2703.")
            span = (
                binding.request.source_item.local_name_span
                or binding.request.source_item.exported_name_span
            )
            location = _location(span, fallback_path=draft.module.path)
            draft.issues.append(
                ProjectTypeSourceResolutionIssue(
                    status=ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
                    owning_module_path=draft.module.path,
                    local_name=local_name,
                    location=location,
                    related_locations=_ordered_related_locations(
                        location,
                        tuple(root.location for root in roots),
                    ),
                    cycle=cycle,
                    suppressing_diagnostics=roots,
                )
            )
            blocked_names.add(local_name)
            continue
        if target_path not in processed_paths:
            raise ValueError("Imported nominal target must precede its importer.")
        occurrences = catalogs.find_identity(binding.target_identity)
        if len(occurrences) != 1:
            raise ValueError("Imported nominal target must have one exact occurrence.")
        draft.symbols.append(
            ProjectResolvedNominalSymbol(
                owning_module_path=draft.module.path,
                local_name=local_name,
                target_identity=binding.target_identity,
                target_occurrence=occurrences[0],
                imported_binding=binding,
            )
        )


def _collect_type_references(
    catalog: ProjectModuleCatalog,
) -> list[ProjectModuleTypeReference]:
    references: list[ProjectModuleTypeReference] = []
    for occurrence in catalog.occurrences:
        definition = occurrence.definition
        if type(definition) is TypeDef:
            references.append(
                ProjectModuleTypeReference(
                    owner=occurrence,
                    role=ProjectModuleTypeReferenceRole.TYPE_ALIAS_BASE,
                    member_position=0,
                    type_expr=definition.base,
                )
            )
        elif type(definition) is ShapeDef:
            references.extend(
                ProjectModuleTypeReference(
                    owner=occurrence,
                    role=ProjectModuleTypeReferenceRole.SHAPE_FIELD_TYPE,
                    member_position=position,
                    type_expr=field_def.type_expr,
                )
                for position, field_def in enumerate(definition.fields)
            )
    return references


def _collect_source_references(
    catalog: ProjectModuleCatalog,
) -> list[ProjectModuleSourceShapeReference]:
    return [
        ProjectModuleSourceShapeReference(
            owner=occurrence,
            source=occurrence.definition,
        )
        for occurrence in catalog.occurrences
        if type(occurrence.definition) is SourceDef
        and occurrence.definition.shape_name is not None
    ]


def _resolve_direct_type(
    draft: _ModuleResolutionDraft,
    reference: ProjectModuleTypeReference,
) -> _DirectTypeResolution:
    name = reference.type_expr.name
    if name in _PROJECT_BUILTIN_TYPE_NAMES:
        return _DirectTypeResolution(
            reference=reference,
            kind=ProjectResolvedTypeKind.BUILTIN,
            symbol=None,
        )
    if name in draft.blocked_type_names or name in draft.ambiguous_type_names:
        return _DirectTypeResolution(
            reference=reference,
            kind=ProjectResolvedTypeKind.UNKNOWN,
            symbol=None,
        )
    candidates = tuple(
        symbol
        for symbol in draft.symbols
        if symbol.declaration_kind in _TYPE_KINDS and symbol.local_name == name
    )
    if len(candidates) > 1:
        raise ValueError("Type lookup cannot choose among candidates.")
    if candidates:
        symbol = candidates[0]
        return _DirectTypeResolution(
            reference=reference,
            kind=_resolved_kind(symbol.declaration_kind),
            symbol=symbol,
        )
    location = _location(reference.type_expr.span, fallback_path=draft.module.path)
    diagnostic = _diagnostic(
        code="PIE-S2002",
        message=f"Unknown type: {name}",
        location=location,
    )
    draft.issues.append(
        ProjectTypeSourceResolutionIssue(
            status=ProjectTypeSourceResolutionIssueStatus.UNKNOWN_TYPE_REFERENCE,
            owning_module_path=draft.module.path,
            local_name=name,
            location=location,
            diagnostic=diagnostic,
            type_reference=reference,
        )
    )
    return _DirectTypeResolution(
        reference=reference,
        kind=ProjectResolvedTypeKind.UNKNOWN,
        symbol=None,
    )


def _expand_aliases(
    alias_bases: Mapping[ProjectNominalDeclarationIdentity, _DirectTypeResolution],
    occurrences: Mapping[
        ProjectNominalDeclarationIdentity, ProjectDeclarationOccurrence
    ],
) -> tuple[
    dict[ProjectNominalDeclarationIdentity, _CanonicalType],
    tuple[ProjectTypeSourceResolutionIssue, ...],
]:
    order = {
        identity: (occurrence.module_position, occurrence.declaration_position)
        for identity, occurrence in occurrences.items()
    }
    canonical: dict[ProjectNominalDeclarationIdentity, _CanonicalType] = {}
    reported_cycles: set[frozenset[ProjectNominalDeclarationIdentity]] = set()
    issues: list[ProjectTypeSourceResolutionIssue] = []

    for start in sorted(alias_bases, key=order.__getitem__):
        if start in canonical:
            continue
        path: list[ProjectNominalDeclarationIdentity] = []
        positions: dict[ProjectNominalDeclarationIdentity, int] = {}
        cursor = start
        terminal: _CanonicalType
        while True:
            existing = canonical.get(cursor)
            if existing is not None:
                terminal = existing
                break
            cycle_start = positions.get(cursor)
            if cycle_start is not None:
                cycle = tuple(path[cycle_start:])
                cycle_key = frozenset(cycle)
                terminal = _UNKNOWN_CANONICAL
                for identity in cycle:
                    canonical[identity] = terminal
                if cycle_key not in reported_cycles:
                    anchor = min(cycle, key=order.__getitem__)
                    ordered_cycle = tuple(sorted(cycle, key=order.__getitem__))
                    anchor_occurrence = occurrences[anchor]
                    anchor_definition = anchor_occurrence.definition
                    assert type(anchor_definition) is TypeDef
                    location = _location(
                        anchor_definition.base.span,
                        fallback_path=anchor.module_path,
                    )
                    related = _ordered_related_locations(
                        location,
                        tuple(
                            _location(
                                _type_alias_base_span(occurrences[identity]),
                                fallback_path=identity.module_path,
                            )
                            for identity in ordered_cycle
                        ),
                    )
                    diagnostic = _diagnostic(
                        code="PIE-S2003",
                        message=f"Type alias cycle involving {anchor.declared_name}",
                        location=location,
                    )
                    issues.append(
                        ProjectTypeSourceResolutionIssue(
                            status=ProjectTypeSourceResolutionIssueStatus.TYPE_ALIAS_CYCLE,
                            owning_module_path=anchor.module_path,
                            local_name=anchor.declared_name,
                            location=location,
                            related_locations=related,
                            diagnostic=diagnostic,
                            occurrences=tuple(
                                occurrences[identity] for identity in ordered_cycle
                            ),
                            alias_cycle=ordered_cycle,
                        )
                    )
                    reported_cycles.add(cycle_key)
                break
            positions[cursor] = len(path)
            path.append(cursor)
            direct = alias_bases.get(cursor)
            if direct is None:
                terminal = _UNKNOWN_CANONICAL
                break
            if direct.kind is ProjectResolvedTypeKind.TYPE_ALIAS:
                assert direct.symbol is not None
                cursor = direct.symbol.target_identity
                continue
            terminal = _canonical_from_direct(direct)
            break
        for identity in reversed(path):
            canonical.setdefault(identity, terminal)

    return canonical, tuple(sorted(issues, key=_issue_source_key))


def _resolved_type_reference(
    direct: _DirectTypeResolution,
    alias_bases: Mapping[ProjectNominalDeclarationIdentity, _DirectTypeResolution],
    canonical_by_alias: Mapping[ProjectNominalDeclarationIdentity, _CanonicalType],
) -> ProjectResolvedModuleTypeReference:
    if direct.kind is ProjectResolvedTypeKind.TYPE_ALIAS:
        assert direct.symbol is not None
        target = direct.symbol.target_identity
        canonical = canonical_by_alias.get(target, _UNKNOWN_CANONICAL)
        alias_chain = _alias_chain(target, alias_bases)
    else:
        canonical = _canonical_from_direct(direct)
        alias_chain = ()
    return ProjectResolvedModuleTypeReference(
        reference=direct.reference,
        direct_kind=direct.kind,
        direct_symbol=direct.symbol,
        canonical_kind=canonical.kind,
        canonical_name=canonical.name,
        canonical_target_identity=canonical.target_identity,
        alias_chain=alias_chain,
    )


def _alias_chain(
    start: ProjectNominalDeclarationIdentity,
    alias_bases: Mapping[ProjectNominalDeclarationIdentity, _DirectTypeResolution],
) -> tuple[ProjectNominalDeclarationIdentity, ...]:
    chain: list[ProjectNominalDeclarationIdentity] = []
    seen: set[ProjectNominalDeclarationIdentity] = set()
    cursor = start
    while cursor not in seen:
        chain.append(cursor)
        seen.add(cursor)
        direct = alias_bases.get(cursor)
        if direct is None or direct.kind is not ProjectResolvedTypeKind.TYPE_ALIAS:
            break
        assert direct.symbol is not None
        cursor = direct.symbol.target_identity
    return tuple(chain)


def _resolve_source_shapes(
    draft: _ModuleResolutionDraft,
) -> tuple[ProjectResolvedModuleSourceShapeReference, ...]:
    resolutions: list[ProjectResolvedModuleSourceShapeReference] = []
    for reference in draft.source_references:
        name = reference.source.shape_name
        assert name is not None
        if name in draft.blocked_type_names or name in draft.ambiguous_type_names:
            continue
        if name in _PROJECT_BUILTIN_TYPE_NAMES:
            _append_source_issue(draft, reference, incompatible=True)
            continue
        candidates = tuple(
            symbol
            for symbol in draft.symbols
            if symbol.declaration_kind in _TYPE_KINDS and symbol.local_name == name
        )
        if len(candidates) > 1:
            raise ValueError("Source shape lookup cannot choose among candidates.")
        if not candidates:
            _append_source_issue(draft, reference, incompatible=False)
        elif candidates[0].declaration_kind is not ProjectSymbolKind.SHAPE:
            _append_source_issue(draft, reference, incompatible=True)
        else:
            resolutions.append(
                ProjectResolvedModuleSourceShapeReference(
                    reference=reference,
                    target_symbol=candidates[0],
                )
            )
    return tuple(resolutions)


def _append_source_issue(
    draft: _ModuleResolutionDraft,
    reference: ProjectModuleSourceShapeReference,
    *,
    incompatible: bool,
) -> None:
    name = reference.source.shape_name
    assert name is not None
    location = _location(reference.source.span, fallback_path=draft.module.path)
    status = (
        ProjectTypeSourceResolutionIssueStatus.INCOMPATIBLE_SOURCE_SHAPE_KIND
        if incompatible
        else ProjectTypeSourceResolutionIssueStatus.UNKNOWN_SOURCE_SHAPE_REFERENCE
    )
    message = (
        f"Source shape must refer to a shape: {name}"
        if incompatible
        else f"Unknown source shape: {name}"
    )
    draft.issues.append(
        ProjectTypeSourceResolutionIssue(
            status=status,
            owning_module_path=draft.module.path,
            local_name=name,
            location=location,
            diagnostic=_diagnostic(
                code="PIE-S2303",
                message=message,
                location=location,
            ),
            source_reference=reference,
        )
    )


def _duplicate_issue(
    module_path: str,
    local_name: str,
    occurrences: tuple[ProjectDeclarationOccurrence, ...],
    *,
    type_namespace: bool,
) -> ProjectTypeSourceResolutionIssue:
    primary_occurrence = occurrences[1]
    location = _location(primary_occurrence.definition.span, fallback_path=module_path)
    namespace = "type" if type_namespace else "relation"
    status = (
        ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_TYPE_NAME
        if type_namespace
        else ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_SOURCE_NAME
    )
    return ProjectTypeSourceResolutionIssue(
        status=status,
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
            message=f"Duplicate symbol name in {namespace} namespace: {local_name}",
            location=location,
        ),
        occurrences=occurrences,
    )


def _cycle_member_issues(
    graph: ProjectModuleGraph,
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> tuple[ProjectTypeSourceResolutionIssue, ...]:
    issues: list[ProjectTypeSourceResolutionIssue] = []
    for cycle in graph.cycles:
        roots = _suppressing_diagnostics_for_cycle(cycle, module_diagnostics)
        if not roots:
            raise ValueError("Cyclic module requires one PIE-S2703 root.")
        for member in cycle.component.members:
            location = roots[0].location
            issues.append(
                ProjectTypeSourceResolutionIssue(
                    status=ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
                    owning_module_path=member.identity.path,
                    local_name=None,
                    location=location,
                    related_locations=_ordered_related_locations(
                        location,
                        tuple(root.location for root in roots),
                    ),
                    cycle=cycle,
                    suppressing_diagnostics=roots,
                )
            )
    return tuple(
        sorted(
            issues,
            key=lambda item: graph.find_path(item.owning_module_path)[0].position,
        )
    )


def _suppressing_diagnostics_for_binding_issues(
    issues: tuple[ProjectModuleBindingIssue, ...],
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> tuple[Diagnostic, ...]:
    roots: list[Diagnostic] = []
    target_export_issues = tuple(
        export_issue
        for issue in issues
        for surface in issue.target_surfaces
        for export_issue in surface.issues
    )
    for fact in module_diagnostics.facts:
        direct = any(issue in fact.binding_issues for issue in issues)
        graph = any(
            issue in graph_issue.binding_issues
            for graph_issue in fact.graph_issues
            for issue in issues
        )
        export = any(
            export_issue in fact.export_issues for export_issue in target_export_issues
        )
        if direct or graph or export:
            roots.append(fact.diagnostic)
    return tuple(dict.fromkeys(roots))


def _suppressing_diagnostics_for_export_issues(
    issues: tuple[ProjectModuleExportIssue, ...],
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> tuple[Diagnostic, ...]:
    return tuple(
        fact.diagnostic
        for fact in module_diagnostics.facts
        if any(issue in fact.export_issues for issue in issues)
    )


def _suppressing_diagnostics_for_cycle(
    cycle: ProjectModuleCycle,
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> tuple[Diagnostic, ...]:
    return tuple(
        fact.diagnostic
        for fact in module_diagnostics.facts
        if any(issue.cycle == cycle for issue in fact.graph_issues)
    )


def _validate_builder_inputs(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> None:
    if type(modules) is not tuple or any(
        type(module) is not ProjectLogicalModule for module in modules
    ):
        raise TypeError("Type/source resolver requires a logical-module tuple.")
    if type(catalogs) is not ProjectModuleCatalogSet:
        raise TypeError("Type/source resolver requires module catalogs.")
    if type(exports) is not ProjectModuleExportSurfaceSet:
        raise TypeError("Type/source resolver requires export surfaces.")
    if type(bindings) is not ProjectModuleBindingEnvironmentSet:
        raise TypeError("Type/source resolver requires binding environments.")
    if type(graph) is not ProjectModuleGraph:
        raise TypeError("Type/source resolver requires a module graph.")
    if type(module_diagnostics) is not ProjectModuleDiagnosticSet:
        raise TypeError("Type/source resolver requires module diagnostics.")
    lengths = {
        len(modules),
        len(catalogs.catalogs),
        len(exports.surfaces),
        len(bindings.environments),
        len(graph.vertices),
    }
    if len(lengths) != 1:
        raise ValueError("Type/source resolver inputs must cover every module.")
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
            raise ValueError("Type/source resolver inputs must retain module order.")


def _validate_slice9_identity(identity: ProjectNominalDeclarationIdentity) -> None:
    valid = (
        identity.namespace is ProjectSymbolNamespace.TYPE
        and identity.declaration_kind in _TYPE_KINDS
    ) or (
        identity.namespace is ProjectSymbolNamespace.RELATION
        and identity.declaration_kind is ProjectSymbolKind.SOURCE
    )
    if not valid:
        raise ValueError("Resolved nominal identity is outside Slice 9 kinds.")


def _validate_issue_evidence(issue: ProjectTypeSourceResolutionIssue) -> None:
    status = issue.status
    emitted_code = None if issue.diagnostic is None else issue.diagnostic.code
    duplicate = status in {
        ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_TYPE_NAME,
        ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_SOURCE_NAME,
    }
    if duplicate:
        valid = (
            len(issue.occurrences) > 1
            and issue.type_reference is None
            and issue.source_reference is None
            and not issue.binding_issues
            and issue.cycle is None
            and not issue.alias_cycle
            and emitted_code == "PIE-S2001"
        )
    elif status is ProjectTypeSourceResolutionIssueStatus.UNKNOWN_TYPE_REFERENCE:
        valid = (
            issue.type_reference is not None
            and issue.source_reference is None
            and not issue.occurrences
            and not issue.binding_issues
            and issue.cycle is None
            and not issue.alias_cycle
            and emitted_code == "PIE-S2002"
        )
    elif status is ProjectTypeSourceResolutionIssueStatus.TYPE_ALIAS_CYCLE:
        valid = (
            len(issue.occurrences) == len(issue.alias_cycle) > 0
            and issue.type_reference is None
            and issue.source_reference is None
            and not issue.binding_issues
            and issue.cycle is None
            and emitted_code == "PIE-S2003"
        )
    elif status in {
        ProjectTypeSourceResolutionIssueStatus.UNKNOWN_SOURCE_SHAPE_REFERENCE,
        ProjectTypeSourceResolutionIssueStatus.INCOMPATIBLE_SOURCE_SHAPE_KIND,
    }:
        valid = (
            issue.source_reference is not None
            and issue.type_reference is None
            and not issue.occurrences
            and not issue.binding_issues
            and issue.cycle is None
            and not issue.alias_cycle
            and emitted_code == "PIE-S2303"
        )
    elif status is ProjectTypeSourceResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED:
        valid = (
            issue.local_name is not None
            and (bool(issue.binding_issues) != bool(issue.occurrences))
            and issue.type_reference is None
            and issue.source_reference is None
            and issue.cycle is None
            and not issue.alias_cycle
            and issue.diagnostic is None
            and bool(issue.suppressing_diagnostics)
        )
    else:
        valid = (
            issue.cycle is not None
            and not issue.binding_issues
            and issue.type_reference is None
            and issue.source_reference is None
            and not issue.occurrences
            and not issue.alias_cycle
            and issue.diagnostic is None
            and tuple(diagnostic.code for diagnostic in issue.suppressing_diagnostics)
            == ("PIE-S2703",)
        )
    if not valid:
        raise ValueError("Type/source issue evidence must prove its exact status.")


def _local_symbol(
    module_path: str,
    occurrence: ProjectDeclarationOccurrence,
) -> ProjectResolvedNominalSymbol:
    return ProjectResolvedNominalSymbol(
        owning_module_path=module_path,
        local_name=occurrence.identity.declared_name,
        target_identity=occurrence.identity,
        target_occurrence=occurrence,
        local_occurrence=occurrence,
    )


def _resolved_kind(kind: ProjectSymbolKind) -> ProjectResolvedTypeKind:
    if kind is ProjectSymbolKind.TYPE_ALIAS:
        return ProjectResolvedTypeKind.TYPE_ALIAS
    if kind is ProjectSymbolKind.ENUM:
        return ProjectResolvedTypeKind.ENUM
    if kind is ProjectSymbolKind.SHAPE:
        return ProjectResolvedTypeKind.SHAPE
    raise ValueError("Declaration kind is not a logical type.")


def _canonical_from_direct(direct: _DirectTypeResolution) -> _CanonicalType:
    if direct.kind is ProjectResolvedTypeKind.BUILTIN:
        return _CanonicalType(
            kind=direct.kind,
            name=direct.reference.type_expr.name,
            target_identity=None,
        )
    if direct.kind in {ProjectResolvedTypeKind.ENUM, ProjectResolvedTypeKind.SHAPE}:
        assert direct.symbol is not None
        return _CanonicalType(
            kind=direct.kind,
            name=direct.symbol.target_identity.declared_name,
            target_identity=direct.symbol.target_identity,
        )
    return _UNKNOWN_CANONICAL


def _type_alias_base_span(occurrence: ProjectDeclarationOccurrence) -> Span:
    definition = occurrence.definition
    if type(definition) is not TypeDef:
        raise TypeError("Alias occurrence requires a TypeDef.")
    return definition.base.span


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


def _issue_source_key(issue: ProjectTypeSourceResolutionIssue) -> tuple[object, ...]:
    status_rank = {
        status: position
        for position, status in enumerate(ProjectTypeSourceResolutionIssueStatus)
    }
    location = issue.location
    return (
        location.line,
        location.column,
        location.end_line if location.end_line is not None else -1,
        location.end_column if location.end_column is not None else -1,
        status_rank[issue.status],
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
