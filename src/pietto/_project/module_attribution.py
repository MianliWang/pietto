"""Private occurrence-safe module attribution, provenance, and lineage facts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar, cast

from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedTypeKind,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
    _PROJECT_BUILTIN_TYPE_NAMES,
)
from pietto._project.module_bindings import (
    ProjectImportedBindingIdentity,
    ProjectModuleBindingEnvironmentSet,
    ProjectModuleImportRequest,
    ProjectResolvedImportedBinding,
)
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
    ProjectImportedExportCandidate,
    ProjectModuleExportEntry,
    ProjectModuleExportEntryOrigin,
    ProjectModuleExportSurfaceSet,
)
from pietto._project.module_graph import ProjectModuleGraph, ProjectModuleGraphVertex
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationRowFact,
    ProjectModuleRelationReference,
    ProjectModuleRelationResolutionSet,
    ProjectResolvedModuleRelationReference,
    ProjectResolvedModuleRelationSymbol,
)
from pietto._project.module_resolution import (
    ProjectModuleSourceShapeReference,
    ProjectModuleTypeReference,
    ProjectModuleTypeReferenceRole,
    ProjectResolvedModuleTypeReference,
    ProjectResolvedNominalSymbol,
    ProjectTypeSourceResolutionSet,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    FromClause,
    NameExpr,
    QueryDef,
    SelectItem,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
    TypeExpr,
)

__all__: tuple[str, ...] = ()

_KeyT = TypeVar("_KeyT")
_ValueT = TypeVar("_ValueT")
_ItemT = TypeVar("_ItemT")
_RELATION_KINDS = frozenset(
    {
        ProjectSymbolKind.SOURCE,
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    }
)


class ProjectModuleReferenceRole(StrEnum):
    """Closed occurrence roles covered by concrete Slice 5-10 semantics."""

    TYPE_ALIAS_BASE = "type_alias_base"
    SHAPE_FIELD_TYPE = "shape_field_type"
    SOURCE_SHAPE = "source_shape"
    RELATION_FROM = "relation_from"
    ROW_FIELD = "row_field"


class ProjectModuleDependencyKind(StrEnum):
    """Identity-safe direct dependency categories owned by Slice 11."""

    TYPE_REFERENCE = "type_reference"
    SOURCE_SHAPE_REFERENCE = "source_shape_reference"
    RELATION_REFERENCE = "relation_reference"
    ROW_FIELD_REFERENCE = "row_field_reference"


class ProjectModuleRowFieldKind(StrEnum):
    """Distinct schema, source-row, and relation-output field identities."""

    SHAPE_FIELD = "shape_field"
    SOURCE_FIELD = "source_field"
    RELATION_OUTPUT = "relation_output"


class ProjectModuleProjectionKind(StrEnum):
    """The only row projection kinds concrete before Slice 11."""

    DIRECT = "direct"
    RENAMED = "renamed"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectDeclarationOccurrenceIdentity:
    """Semantic locator for one selected declaration occurrence."""

    identity: ProjectNominalDeclarationIdentity
    module_position: int
    declaration_position: int

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Declaration occurrence identity requires a nominal ID.")
        _validate_position(self.module_position, "module")
        _validate_position(self.declaration_position, "declaration")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleImportOccurrenceIdentity:
    """One exact source import item without retained AST identity semantics."""

    binding_identity: ProjectImportedBindingIdentity
    target_module_path: str
    exported_name: str
    module_statement_position: int
    item_position: int

    def __post_init__(self) -> None:
        if type(self.binding_identity) is not ProjectImportedBindingIdentity:
            raise TypeError("Import occurrence requires a local binding identity.")
        if type(self.target_module_path) is not str:
            raise TypeError(
                "Import occurrence target module path must be text evidence."
            )
        if type(self.exported_name) is not str or not self.exported_name:
            raise ValueError("Import occurrence requires an exported name.")
        _validate_position(self.module_statement_position, "import statement")
        _validate_position(self.item_position, "import item")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleFacadeOccurrenceIdentity:
    """One exact resolved export-facade item occurrence."""

    owning_module_path: str
    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    exposed_name: str
    module_statement_position: int
    item_position: int

    def __post_init__(self) -> None:
        ProjectModuleIdentity(path=self.owning_module_path)
        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Facade occurrence requires a namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Facade occurrence requires a declaration kind.")
        if type(self.exposed_name) is not str or not self.exposed_name:
            raise ValueError("Facade occurrence requires an exposed name.")
        _validate_position(self.module_statement_position, "export statement")
        _validate_position(self.item_position, "export item")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleReferenceOccurrenceIdentity:
    """One exact owner, role, and source-member reference occurrence."""

    owner: ProjectDeclarationOccurrenceIdentity
    role: ProjectModuleReferenceRole
    member_position: int

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Reference occurrence requires an owner occurrence.")
        if type(self.role) is not ProjectModuleReferenceRole:
            raise TypeError("Reference occurrence requires an exact role.")
        _validate_position(self.member_position, "reference member")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRowFieldIdentity:
    """One occurrence-safe shape, source, or relation row field identity."""

    owner: ProjectDeclarationOccurrenceIdentity
    kind: ProjectModuleRowFieldKind
    field_position: int
    name: str

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Row field identity requires an owner occurrence.")
        if type(self.kind) is not ProjectModuleRowFieldKind:
            raise TypeError("Row field identity requires an exact kind.")
        _validate_position(self.field_position, "row field")
        if type(self.name) is not str or not self.name:
            raise ValueError("Row field identity requires a name.")
        owner_kind = self.owner.identity.declaration_kind
        expected = {
            ProjectModuleRowFieldKind.SHAPE_FIELD: {ProjectSymbolKind.SHAPE},
            ProjectModuleRowFieldKind.SOURCE_FIELD: {ProjectSymbolKind.SOURCE},
            ProjectModuleRowFieldKind.RELATION_OUTPUT: {
                ProjectSymbolKind.TABLE,
                ProjectSymbolKind.QUERY,
            },
        }[self.kind]
        if owner_kind not in expected:
            raise ValueError("Row field kind does not match its owner declaration.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleDeclarationAttribution:
    """One selected-module attribution for one declaration occurrence."""

    identity: ProjectDeclarationOccurrenceIdentity
    occurrence: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Declaration attribution requires an occurrence ID.")
        if type(self.occurrence) is not ProjectDeclarationOccurrence:
            raise TypeError("Declaration attribution requires retained evidence.")
        if _declaration_identity(self.occurrence) != self.identity:
            raise ValueError("Declaration attribution evidence does not match.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleImportAttribution:
    """One importing-module attribution for one exact import item."""

    identity: ProjectModuleImportOccurrenceIdentity
    request: ProjectModuleImportRequest = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectModuleImportOccurrenceIdentity:
            raise TypeError("Import attribution requires an import occurrence ID.")
        if type(self.request) is not ProjectModuleImportRequest:
            raise TypeError("Import attribution requires retained request evidence.")
        if _import_identity(self.request) != self.identity:
            raise ValueError("Import attribution evidence does not match.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleFacadeAttribution:
    """One direct local or explicit re-export facade attribution."""

    identity: ProjectModuleFacadeOccurrenceIdentity
    origin: ProjectModuleExportEntryOrigin
    target_identity: ProjectNominalDeclarationIdentity
    target_occurrence: ProjectDeclarationOccurrenceIdentity
    entry: ProjectModuleExportEntry = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectModuleFacadeOccurrenceIdentity:
            raise TypeError("Facade attribution requires a facade occurrence ID.")
        if type(self.origin) is not ProjectModuleExportEntryOrigin:
            raise TypeError("Facade attribution requires an exact origin.")
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Facade attribution requires a nominal target.")
        if type(self.target_occurrence) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Facade attribution requires a target occurrence.")
        if type(self.entry) is not ProjectModuleExportEntry:
            raise TypeError("Facade attribution requires retained entry evidence.")
        if (
            _facade_identity(self.entry) != self.identity
            or self.entry.origin is not self.origin
            or self.entry.target_identity != self.target_identity
            or self.target_occurrence.identity != self.target_identity
        ):
            raise ValueError("Facade attribution evidence does not match.")


_ReferenceSite = TypeExpr | SourceDef | FromClause | SelectItem


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleReferenceAttribution:
    """One raw source reference attribution independent of resolution outcome."""

    identity: ProjectModuleReferenceOccurrenceIdentity
    owner_occurrence: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    site: _ReferenceSite = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectModuleReferenceOccurrenceIdentity:
            raise TypeError("Reference attribution requires a reference ID.")
        if type(self.owner_occurrence) is not ProjectDeclarationOccurrence:
            raise TypeError("Reference attribution requires retained owner evidence.")
        if _declaration_identity(self.owner_occurrence) != self.identity.owner:
            raise ValueError("Reference attribution owner evidence does not match.")
        _validate_reference_site(
            self.identity,
            self.owner_occurrence,
            self.site,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleAccessHop:
    """One exact import occurrence resolved through one direct facade entry."""

    import_occurrence: ProjectModuleImportOccurrenceIdentity
    facade_occurrence: ProjectModuleFacadeOccurrenceIdentity
    facade_origin: ProjectModuleExportEntryOrigin
    target_identity: ProjectNominalDeclarationIdentity

    def __post_init__(self) -> None:
        if type(self.import_occurrence) is not ProjectModuleImportOccurrenceIdentity:
            raise TypeError("Access hop requires an import occurrence.")
        if type(self.facade_occurrence) is not ProjectModuleFacadeOccurrenceIdentity:
            raise TypeError("Access hop requires a facade occurrence.")
        if type(self.facade_origin) is not ProjectModuleExportEntryOrigin:
            raise TypeError("Access hop requires an exact facade origin.")
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Access hop requires a nominal target.")
        binding = self.import_occurrence.binding_identity
        facade = self.facade_occurrence
        if (
            self.import_occurrence.target_module_path != facade.owning_module_path
            or self.import_occurrence.exported_name != facade.exposed_name
            or binding.namespace is not facade.namespace
            or binding.declaration_kind is not facade.declaration_kind
            or self.target_identity.namespace is not facade.namespace
            or self.target_identity.declaration_kind is not facade.declaration_kind
        ):
            raise ValueError("Access hop identities do not form one direct route.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleOriginPath:
    """One complete local lookup to exact nominal declaration occurrence path."""

    owning_module_path: str
    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    local_name: str
    target_occurrence: ProjectDeclarationOccurrenceIdentity
    local_occurrence: ProjectDeclarationOccurrenceIdentity | None = None
    import_occurrence: ProjectModuleImportOccurrenceIdentity | None = None
    hops: tuple[ProjectModuleAccessHop, ...] = ()

    def __post_init__(self) -> None:
        ProjectModuleIdentity(path=self.owning_module_path)
        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Origin path requires a namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Origin path requires a declaration kind.")
        if type(self.local_name) is not str or not self.local_name:
            raise ValueError("Origin path requires a local lookup name.")
        if type(self.target_occurrence) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Origin path requires a target occurrence.")
        _require_tuple(self.hops, ProjectModuleAccessHop, "Origin path hops")
        if (self.local_occurrence is None) == (self.import_occurrence is None):
            raise ValueError("Origin path requires exactly one local source.")
        target = self.target_occurrence.identity
        if target.namespace is not self.namespace or (
            target.declaration_kind is not self.declaration_kind
        ):
            raise ValueError("Origin path target namespace or kind mismatch.")
        if self.local_occurrence is not None:
            if type(self.local_occurrence) is not ProjectDeclarationOccurrenceIdentity:
                raise TypeError("Local origin path requires an occurrence.")
            if (
                self.local_occurrence != self.target_occurrence
                or target.module_path != self.owning_module_path
                or target.declared_name != self.local_name
                or self.hops
            ):
                raise ValueError("Local origin path must be one exact self path.")
            return
        imported = self.import_occurrence
        if type(imported) is not ProjectModuleImportOccurrenceIdentity:
            raise TypeError("Imported origin path requires an import occurrence.")
        binding = imported.binding_identity
        if (
            binding.owning_module_path != self.owning_module_path
            or binding.namespace is not self.namespace
            or binding.declaration_kind is not self.declaration_kind
            or binding.local_binding_name != self.local_name
            or not self.hops
            or self.hops[0].import_occurrence != imported
            or any(hop.target_identity != target for hop in self.hops)
        ):
            raise ValueError("Imported origin path does not match its local binding.")
        for current, following in zip(self.hops, self.hops[1:], strict=False):
            if (
                current.facade_origin
                is not ProjectModuleExportEntryOrigin.EXPLICIT_REEXPORT
                or following.import_occurrence.binding_identity.owning_module_path
                != current.facade_occurrence.owning_module_path
                or following.import_occurrence.binding_identity.local_binding_name
                != current.facade_occurrence.exposed_name
            ):
                raise ValueError("Origin path re-export hops are not contiguous.")
        if (
            self.hops[-1].facade_origin
            is not ProjectModuleExportEntryOrigin.LOCAL_DECLARATION
            or self.hops[-1].facade_occurrence.owning_module_path != target.module_path
        ):
            raise ValueError("Imported origin path must terminate at a local facade.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleReferenceProvenanceHop:
    """One direct reference occurrence to one nominal target occurrence."""

    reference: ProjectModuleReferenceOccurrenceIdentity
    target: ProjectDeclarationOccurrenceIdentity
    origin: ProjectModuleOriginPath

    def __post_init__(self) -> None:
        if type(self.reference) is not ProjectModuleReferenceOccurrenceIdentity:
            raise TypeError("Provenance hop requires a reference occurrence.")
        if type(self.target) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Provenance hop requires a target occurrence.")
        if type(self.origin) is not ProjectModuleOriginPath:
            raise TypeError("Provenance hop requires an origin path.")
        if (
            self.origin.target_occurrence != self.target
            or self.origin.owning_module_path
            != self.reference.owner.identity.module_path
        ):
            raise ValueError("Provenance hop target and origin disagree.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleReferenceProvenancePath:
    """One complete direct-and-alias reference path to a concrete terminal."""

    reference: ProjectModuleReferenceOccurrenceIdentity
    hops: tuple[ProjectModuleReferenceProvenanceHop, ...] = ()
    terminal_builtin: str | None = None
    terminal_reference: ProjectModuleReferenceOccurrenceIdentity | None = None
    terminal_target: ProjectDeclarationOccurrenceIdentity | None = None

    def __post_init__(self) -> None:
        if type(self.reference) is not ProjectModuleReferenceOccurrenceIdentity:
            raise TypeError("Provenance path requires a reference occurrence.")
        _require_tuple(
            self.hops, ProjectModuleReferenceProvenanceHop, "Provenance hops"
        )
        if (self.terminal_builtin is None) == (self.terminal_target is None):
            raise ValueError("Provenance path requires exactly one terminal.")
        if self.terminal_builtin is not None and (
            type(self.terminal_builtin) is not str
            or self.terminal_builtin not in _PROJECT_BUILTIN_TYPE_NAMES
        ):
            raise ValueError("Provenance builtin terminal must be canonical.")
        if self.terminal_builtin is None:
            if self.terminal_reference is not None:
                raise ValueError("Nominal provenance forbids a builtin reference.")
        elif (
            type(self.terminal_reference)
            is not ProjectModuleReferenceOccurrenceIdentity
        ):
            raise TypeError("Builtin provenance requires its terminal reference.")
        if (
            self.terminal_target is not None
            and type(self.terminal_target) is not ProjectDeclarationOccurrenceIdentity
        ):
            raise TypeError("Provenance nominal terminal must be an occurrence.")
        if self.hops:
            if self.hops[0].reference != self.reference:
                raise ValueError("Provenance path must start at its reference.")
            for current, following in zip(self.hops, self.hops[1:], strict=False):
                if following.reference.owner != current.target:
                    raise ValueError("Provenance alias hops are not contiguous.")
            if self.terminal_target is not None and (
                self.hops[-1].target != self.terminal_target
            ):
                raise ValueError("Provenance nominal terminal is not the final hop.")
            if self.terminal_reference is not None and (
                self.terminal_reference.owner != self.hops[-1].target
            ):
                raise ValueError("Builtin provenance terminal is not contiguous.")
        elif self.terminal_target is not None:
            raise ValueError("Nominal provenance terminal requires a hop.")
        elif self.terminal_reference != self.reference:
            raise ValueError("Direct builtin provenance must retain its reference.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleReferenceProvenance:
    """Every complete concrete path for one exact reference occurrence."""

    reference: ProjectModuleReferenceOccurrenceIdentity
    paths: tuple[ProjectModuleReferenceProvenancePath, ...]

    def __post_init__(self) -> None:
        if type(self.reference) is not ProjectModuleReferenceOccurrenceIdentity:
            raise TypeError("Reference provenance requires a reference occurrence.")
        _require_tuple(
            self.paths,
            ProjectModuleReferenceProvenancePath,
            "Reference provenance paths",
        )
        if not self.paths or any(
            path.reference != self.reference for path in self.paths
        ):
            raise ValueError("Reference provenance requires matching paths.")
        if len(set(self.paths)) != len(self.paths):
            raise ValueError("Reference provenance forbids duplicate exact paths.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleImportDependencyFact:
    """One selected-target module dependency evidence occurrence."""

    import_occurrence: ProjectModuleImportOccurrenceIdentity
    origin: ProjectModuleIdentity
    target: ProjectModuleIdentity

    def __post_init__(self) -> None:
        if type(self.import_occurrence) is not ProjectModuleImportOccurrenceIdentity:
            raise TypeError("Module dependency requires import evidence.")
        if (
            type(self.origin) is not ProjectModuleIdentity
            or type(self.target) is not ProjectModuleIdentity
        ):
            raise TypeError("Module dependency requires logical module endpoints.")
        if (
            self.import_occurrence.binding_identity.owning_module_path
            != self.origin.path
            or self.import_occurrence.target_module_path != self.target.path
        ):
            raise ValueError("Module dependency endpoints do not match evidence.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleDependencyFact:
    """One identity-safe direct semantic or row-field dependency."""

    kind: ProjectModuleDependencyKind
    reference: ProjectModuleReferenceOccurrenceIdentity
    target_declaration: ProjectDeclarationOccurrenceIdentity | None = None
    target_row_field: ProjectModuleRowFieldIdentity | None = None
    origin_path: ProjectModuleOriginPath | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectModuleDependencyKind:
            raise TypeError("Dependency fact requires an exact kind.")
        if type(self.reference) is not ProjectModuleReferenceOccurrenceIdentity:
            raise TypeError("Dependency fact requires a reference occurrence.")
        if (self.target_declaration is None) == (self.target_row_field is None):
            raise ValueError("Dependency fact requires exactly one target domain.")
        if self.kind is ProjectModuleDependencyKind.ROW_FIELD_REFERENCE:
            if self.target_row_field is None:
                raise ValueError("Row dependency requires a row-field target.")
        elif self.target_declaration is None:
            raise ValueError("Nominal dependency requires a declaration target.")
        if self.origin_path is None:
            raise ValueError("Concrete dependency requires its exact origin path.")
        target_owner = (
            self.target_declaration
            if self.target_declaration is not None
            else cast(ProjectModuleRowFieldIdentity, self.target_row_field).owner
        )
        if (
            self.origin_path.target_occurrence != target_owner
            or self.origin_path.owning_module_path
            != self.reference.owner.identity.module_path
        ):
            raise ValueError("Dependency target and origin path disagree.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleSourceFieldOrigin:
    """One concrete source-row field and its exact shape-field origin."""

    source_field: ProjectModuleRowFieldIdentity
    shape_field: ProjectModuleRowFieldIdentity
    source_shape_provenance: ProjectModuleReferenceProvenancePath

    def __post_init__(self) -> None:
        if type(self.source_field) is not ProjectModuleRowFieldIdentity or (
            self.source_field.kind is not ProjectModuleRowFieldKind.SOURCE_FIELD
        ):
            raise TypeError("Source field origin requires a source-row field.")
        if type(self.shape_field) is not ProjectModuleRowFieldIdentity or (
            self.shape_field.kind is not ProjectModuleRowFieldKind.SHAPE_FIELD
        ):
            raise TypeError("Source field origin requires a shape field.")
        if (
            type(self.source_shape_provenance)
            is not ProjectModuleReferenceProvenancePath
        ):
            raise TypeError("Source field origin requires shape provenance.")
        if (
            self.source_shape_provenance.reference.owner != self.source_field.owner
            or self.source_shape_provenance.reference.role
            is not ProjectModuleReferenceRole.SOURCE_SHAPE
            or self.source_shape_provenance.terminal_target != self.shape_field.owner
            or self.source_field.field_position != self.shape_field.field_position
            or self.source_field.name != self.shape_field.name
        ):
            raise ValueError("Source and shape field origin facts do not align.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRowLineageHop:
    """One direct or renamed projection to one immediate upstream field."""

    reference: ProjectModuleReferenceOccurrenceIdentity
    projection_kind: ProjectModuleProjectionKind
    output_field: ProjectModuleRowFieldIdentity
    upstream_field: ProjectModuleRowFieldIdentity
    relation_origin: ProjectModuleOriginPath

    def __post_init__(self) -> None:
        if type(self.reference) is not ProjectModuleReferenceOccurrenceIdentity or (
            self.reference.role is not ProjectModuleReferenceRole.ROW_FIELD
        ):
            raise TypeError("Row lineage hop requires a row-field reference.")
        if type(self.projection_kind) is not ProjectModuleProjectionKind:
            raise TypeError("Row lineage hop requires a projection kind.")
        if type(self.output_field) is not ProjectModuleRowFieldIdentity or (
            self.output_field.kind is not ProjectModuleRowFieldKind.RELATION_OUTPUT
        ):
            raise TypeError("Row lineage hop requires a relation output.")
        if type(self.upstream_field) is not ProjectModuleRowFieldIdentity:
            raise TypeError("Row lineage hop requires an upstream field.")
        if type(self.relation_origin) is not ProjectModuleOriginPath:
            raise TypeError("Row lineage hop requires a relation origin path.")
        if (
            self.reference.owner != self.output_field.owner
            or self.reference.member_position != self.output_field.field_position
            or self.relation_origin.target_occurrence != self.upstream_field.owner
            or self.relation_origin.owning_module_path
            != self.reference.owner.identity.module_path
        ):
            raise ValueError("Row lineage hop occurrence identities do not align.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRowLineagePath:
    """One complete downstream-to-source identity-safe row lineage path."""

    output_field: ProjectModuleRowFieldIdentity
    root_field: ProjectModuleRowFieldIdentity
    hops: tuple[ProjectModuleRowLineageHop, ...] = ()

    def __post_init__(self) -> None:
        if type(self.output_field) is not ProjectModuleRowFieldIdentity:
            raise TypeError("Row lineage path requires an output field.")
        if type(self.root_field) is not ProjectModuleRowFieldIdentity or (
            self.root_field.kind is not ProjectModuleRowFieldKind.SOURCE_FIELD
        ):
            raise TypeError("Row lineage path requires a source-field root.")
        _require_tuple(self.hops, ProjectModuleRowLineageHop, "Row lineage hops")
        if not self.hops:
            if self.output_field != self.root_field:
                raise ValueError("Zero-hop lineage must be its source-field root.")
            return
        if self.hops[0].output_field != self.output_field:
            raise ValueError("Row lineage path must start at its output field.")
        for current, following in zip(self.hops, self.hops[1:], strict=False):
            if current.upstream_field != following.output_field:
                raise ValueError("Row lineage hops are not contiguous.")
        if self.hops[-1].upstream_field != self.root_field:
            raise ValueError("Row lineage path must terminate at its root field.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRowFieldLineage:
    """Every complete path for one concrete row field occurrence."""

    field: ProjectModuleRowFieldIdentity
    paths: tuple[ProjectModuleRowLineagePath, ...]

    def __post_init__(self) -> None:
        if type(self.field) is not ProjectModuleRowFieldIdentity:
            raise TypeError("Row field lineage requires a field identity.")
        _require_tuple(self.paths, ProjectModuleRowLineagePath, "Row field paths")
        if not self.paths or any(
            path.output_field != self.field for path in self.paths
        ):
            raise ValueError("Concrete row field lineage requires complete paths.")
        if len(set(self.paths)) != len(self.paths):
            raise ValueError("Row field lineage forbids duplicate exact paths.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationLineage:
    """One row-state-aligned lineage result for one relation occurrence."""

    owner: ProjectDeclarationOccurrenceIdentity
    status: ProjectRelationRowSchemaStatus
    reason: ProjectRelationRowSchemaReason
    fields: tuple[ProjectModuleRowFieldLineage, ...] = ()

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity or (
            self.owner.identity.declaration_kind not in _RELATION_KINDS
        ):
            raise TypeError("Relation lineage requires a relation occurrence.")
        if type(self.status) is not ProjectRelationRowSchemaStatus:
            raise TypeError("Relation lineage requires an exact status.")
        if type(self.reason) is not ProjectRelationRowSchemaReason:
            raise TypeError("Relation lineage requires an exact reason.")
        _require_tuple(self.fields, ProjectModuleRowFieldLineage, "Lineage fields")
        if self.status is not ProjectRelationRowSchemaStatus.CONCRETE:
            if self.fields:
                raise ValueError("Non-concrete relation lineage must be empty.")
            return
        if any(field.field.owner != self.owner for field in self.fields):
            raise ValueError("Relation lineage fields must belong to its owner.")
        positions = tuple(field.field.field_position for field in self.fields)
        if positions != tuple(sorted(positions)) or len(set(positions)) != len(
            positions
        ):
            raise ValueError("Relation lineage fields must be unique and ordered.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleAttributionFactSet:
    """Complete private Slice 11 attribution, provenance, and lineage sidecar."""

    declarations: tuple[ProjectModuleDeclarationAttribution, ...] = ()
    imports: tuple[ProjectModuleImportAttribution, ...] = ()
    facades: tuple[ProjectModuleFacadeAttribution, ...] = ()
    references: tuple[ProjectModuleReferenceAttribution, ...] = ()
    origins: tuple[ProjectModuleOriginPath, ...] = ()
    reference_provenance: tuple[ProjectModuleReferenceProvenance, ...] = ()
    module_dependencies: tuple[ProjectModuleImportDependencyFact, ...] = ()
    dependencies: tuple[ProjectModuleDependencyFact, ...] = ()
    source_field_origins: tuple[ProjectModuleSourceFieldOrigin, ...] = ()
    row_lineages: tuple[ProjectModuleRelationLineage, ...] = ()
    _origins_by_target: Mapping[
        ProjectNominalDeclarationIdentity,
        tuple[ProjectModuleOriginPath, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)
    _provenance_by_reference: Mapping[
        ProjectModuleReferenceOccurrenceIdentity,
        tuple[ProjectModuleReferenceProvenance, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)
    _dependencies_by_reference: Mapping[
        ProjectModuleReferenceOccurrenceIdentity,
        tuple[ProjectModuleDependencyFact, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)
    _source_origins_by_field: Mapping[
        ProjectModuleRowFieldIdentity,
        tuple[ProjectModuleSourceFieldOrigin, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)
    _row_lineages_by_owner: Mapping[
        ProjectDeclarationOccurrenceIdentity,
        tuple[ProjectModuleRelationLineage, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        collections: tuple[
            tuple[tuple[object, ...], type[object], str],
            ...,
        ] = (
            (self.declarations, ProjectModuleDeclarationAttribution, "declarations"),
            (self.imports, ProjectModuleImportAttribution, "imports"),
            (self.facades, ProjectModuleFacadeAttribution, "facades"),
            (self.references, ProjectModuleReferenceAttribution, "references"),
            (self.origins, ProjectModuleOriginPath, "origins"),
            (
                self.reference_provenance,
                ProjectModuleReferenceProvenance,
                "reference provenance",
            ),
            (
                self.module_dependencies,
                ProjectModuleImportDependencyFact,
                "module dependencies",
            ),
            (self.dependencies, ProjectModuleDependencyFact, "dependencies"),
            (
                self.source_field_origins,
                ProjectModuleSourceFieldOrigin,
                "source field origins",
            ),
            (self.row_lineages, ProjectModuleRelationLineage, "row lineages"),
        )
        for values, item_type, label in collections:
            _require_tuple(values, item_type, f"Fact-set {label}")
            if len(set(values)) != len(values):
                raise ValueError(f"Fact-set {label} must not repeat exact facts.")
        _require_unique(self.declarations, lambda item: item.identity, "declarations")
        _require_unique(self.imports, lambda item: item.identity, "imports")
        _require_unique(self.facades, lambda item: item.identity, "facades")
        _require_unique(self.references, lambda item: item.identity, "references")
        _require_unique(
            self.reference_provenance,
            lambda item: item.reference,
            "reference provenance",
        )
        _require_unique(
            self.source_field_origins,
            lambda item: item.source_field,
            "source field origins",
        )
        _require_unique(self.row_lineages, lambda item: item.owner, "row lineages")
        declaration_ids = {item.identity for item in self.declarations}
        import_ids = {item.identity for item in self.imports}
        facades_by_id = {item.identity: item for item in self.facades}
        reference_ids = {item.identity for item in self.references}
        origin_paths = set(self.origins)
        lineage_by_field = {
            field_lineage.field: field_lineage
            for lineage in self.row_lineages
            for field_lineage in lineage.fields
        }
        source_origins_by_field = {
            item.source_field: item for item in self.source_field_origins
        }
        if any(item.target_occurrence not in declaration_ids for item in self.facades):
            raise ValueError("Facade attribution target must be a declaration.")
        for origin in self.origins:
            if origin.target_occurrence not in declaration_ids:
                raise ValueError("Origin target must be a declaration attribution.")
            if origin.local_occurrence is not None:
                if origin.local_occurrence not in declaration_ids:
                    raise ValueError("Local origin must use a declaration attribution.")
            elif origin.import_occurrence not in import_ids:
                raise ValueError("Imported origin must use an import attribution.")
            for hop in origin.hops:
                facade = facades_by_id.get(hop.facade_occurrence)
                if hop.import_occurrence not in import_ids or facade is None:
                    raise ValueError(
                        "Origin hops require retained import and facade facts."
                    )
                if (
                    facade.origin is not hop.facade_origin
                    or facade.target_identity != hop.target_identity
                    or facade.target_occurrence != origin.target_occurrence
                ):
                    raise ValueError(
                        "Origin hop must match its retained facade attribution."
                    )
        if any(item.identity.owner not in declaration_ids for item in self.references):
            raise ValueError("Reference owner must be a declaration attribution.")
        provenance_paths: set[ProjectModuleReferenceProvenancePath] = set()
        relation_origins_by_owner: dict[
            ProjectDeclarationOccurrenceIdentity,
            set[ProjectModuleOriginPath],
        ] = {}
        for provenance in self.reference_provenance:
            if provenance.reference not in reference_ids:
                raise ValueError("Provenance requires a raw reference attribution.")
            for path in provenance.paths:
                provenance_paths.add(path)
                if path.terminal_target is not None and (
                    path.terminal_target not in declaration_ids
                ):
                    raise ValueError("Provenance terminal must be a declaration.")
                if path.terminal_reference is not None and (
                    path.terminal_reference not in reference_ids
                ):
                    raise ValueError("Builtin terminal requires a raw reference.")
                if any(
                    hop.reference not in reference_ids
                    or hop.target not in declaration_ids
                    or hop.origin not in origin_paths
                    for hop in path.hops
                ):
                    raise ValueError("Provenance hops must close over retained facts.")
                if (
                    provenance.reference.role
                    is ProjectModuleReferenceRole.RELATION_FROM
                    and path.hops
                ):
                    relation_origins_by_owner.setdefault(
                        provenance.reference.owner,
                        set(),
                    ).add(path.hops[0].origin)
        if any(
            item.import_occurrence not in import_ids
            for item in self.module_dependencies
        ):
            raise ValueError("Module dependency requires an import attribution.")
        for dependency in self.dependencies:
            if dependency.reference not in reference_ids:
                raise ValueError("Dependency requires a raw reference attribution.")
            if dependency.origin_path not in origin_paths:
                raise ValueError("Dependency requires a retained origin path.")
            if dependency.target_declaration is not None and (
                dependency.target_declaration not in declaration_ids
            ):
                raise ValueError("Dependency target must be a declaration attribution.")
            if dependency.target_row_field is not None and (
                dependency.target_row_field.owner not in declaration_ids
            ):
                raise ValueError("Row dependency owner must be a declaration.")
            if dependency.target_row_field is not None and (
                dependency.target_row_field not in lineage_by_field
            ):
                raise ValueError("Row dependency target must be a retained row field.")
        for source_origin in self.source_field_origins:
            if (
                source_origin.source_field.owner not in declaration_ids
                or source_origin.shape_field.owner not in declaration_ids
            ):
                raise ValueError("Source-field origin owners must be declarations.")
            if source_origin.source_shape_provenance not in provenance_paths:
                raise ValueError("Source-field origin provenance must be retained.")
            source_lineage = lineage_by_field.get(source_origin.source_field)
            if source_lineage is None:
                raise ValueError("Source-field origin requires its retained row field.")
            if (
                len(source_lineage.paths) != 1
                or source_lineage.paths[0].root_field != source_origin.source_field
                or source_lineage.paths[0].hops
            ):
                raise ValueError(
                    "Source-field origin requires one zero-hop retained lineage."
                )
        for lineage in self.row_lineages:
            if lineage.owner not in declaration_ids:
                raise ValueError("Row lineage owner must be a declaration.")
            for field_lineage in lineage.fields:
                for path in field_lineage.paths:
                    if path.root_field not in source_origins_by_field:
                        raise ValueError(
                            "Row lineage root requires a source-field origin."
                        )
                    if path.output_field not in lineage_by_field or any(
                        hop.output_field not in lineage_by_field
                        or hop.upstream_field not in lineage_by_field
                        for hop in path.hops
                    ):
                        raise ValueError("Row lineage path fields must be retained.")
                    if any(
                        hop.reference not in reference_ids
                        or hop.relation_origin not in origin_paths
                        for hop in path.hops
                    ):
                        raise ValueError(
                            "Row lineage paths must close over retained facts."
                        )
                    if any(
                        hop.relation_origin
                        not in relation_origins_by_owner.get(
                            hop.reference.owner,
                            set(),
                        )
                        for hop in path.hops
                    ):
                        raise ValueError(
                            "Row lineage route must match retained relation provenance."
                        )
        expected_dependencies = {
            ProjectModuleDependencyFact(
                kind=_dependency_kind(hop.reference.role),
                reference=hop.reference,
                target_declaration=hop.target,
                origin_path=hop.origin,
            )
            for provenance in self.reference_provenance
            for path in provenance.paths
            for hop in path.hops
        }
        expected_dependencies.update(
            ProjectModuleDependencyFact(
                kind=ProjectModuleDependencyKind.ROW_FIELD_REFERENCE,
                reference=hop.reference,
                target_row_field=hop.upstream_field,
                origin_path=hop.relation_origin,
            )
            for lineage in self.row_lineages
            for field_lineage in lineage.fields
            for path in field_lineage.paths
            for hop in path.hops
        )
        if set(self.dependencies) != expected_dependencies:
            raise ValueError("Dependencies must exactly match retained paths.")
        object.__setattr__(
            self,
            "_origins_by_target",
            _tuple_mapping(
                _bucket(self.origins, lambda item: item.target_occurrence.identity)
            ),
        )
        object.__setattr__(
            self,
            "_provenance_by_reference",
            _tuple_mapping(
                _bucket(self.reference_provenance, lambda item: item.reference)
            ),
        )
        object.__setattr__(
            self,
            "_dependencies_by_reference",
            _tuple_mapping(_bucket(self.dependencies, lambda item: item.reference)),
        )
        object.__setattr__(
            self,
            "_source_origins_by_field",
            _tuple_mapping(
                _bucket(self.source_field_origins, lambda item: item.source_field)
            ),
        )
        object.__setattr__(
            self,
            "_row_lineages_by_owner",
            _tuple_mapping(_bucket(self.row_lineages, lambda item: item.owner)),
        )

    def find_origin_target(
        self,
        identity: ProjectNominalDeclarationIdentity,
    ) -> tuple[ProjectModuleOriginPath, ...]:
        """Return every deterministic local/import route to one nominal target."""

        if type(identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Origin lookup requires a nominal identity.")
        return self._origins_by_target.get(identity, ())

    def find_reference_provenance(
        self,
        reference: ProjectModuleReferenceOccurrenceIdentity,
    ) -> tuple[ProjectModuleReferenceProvenance, ...]:
        """Return one exact concrete provenance outcome, or an empty tuple."""

        if type(reference) is not ProjectModuleReferenceOccurrenceIdentity:
            raise TypeError("Provenance lookup requires a reference occurrence.")
        return self._provenance_by_reference.get(reference, ())

    def find_reference_dependencies(
        self,
        reference: ProjectModuleReferenceOccurrenceIdentity,
    ) -> tuple[ProjectModuleDependencyFact, ...]:
        """Return every exact direct dependency for one reference occurrence."""

        if type(reference) is not ProjectModuleReferenceOccurrenceIdentity:
            raise TypeError("Dependency lookup requires a reference occurrence.")
        return self._dependencies_by_reference.get(reference, ())

    def find_source_field_origin(
        self,
        field_identity: ProjectModuleRowFieldIdentity,
    ) -> tuple[ProjectModuleSourceFieldOrigin, ...]:
        """Return one exact source-field origin, or an empty tuple."""

        if type(field_identity) is not ProjectModuleRowFieldIdentity:
            raise TypeError("Source origin lookup requires a row-field identity.")
        return self._source_origins_by_field.get(field_identity, ())

    def find_row_lineage(
        self,
        owner: ProjectDeclarationOccurrenceIdentity,
    ) -> tuple[ProjectModuleRelationLineage, ...]:
        """Return one exact relation lineage state, or an empty tuple."""

        if type(owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Row lineage lookup requires an owner occurrence.")
        return self._row_lineages_by_owner.get(owner, ())


def _build_project_module_attribution_fact_set(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
    relation_resolutions: ProjectModuleRelationResolutionSet,
) -> ProjectModuleAttributionFactSet:
    """Build pure occurrence-safe facts from the complete Slice 5-10 sidecars."""

    _validate_builder_inputs(
        modules,
        catalogs,
        exports,
        bindings,
        graph,
        type_source_resolutions,
        relation_resolutions,
    )
    declarations = tuple(
        ProjectModuleDeclarationAttribution(
            identity=_declaration_identity(occurrence),
            occurrence=occurrence,
        )
        for catalog in catalogs.catalogs
        for occurrence in catalog.occurrences
    )
    imports = tuple(
        ProjectModuleImportAttribution(
            identity=_import_identity(request),
            request=request,
        )
        for environment in bindings.environments
        for request in environment.requests
    )
    facades = tuple(
        _facade_attribution(entry, catalogs)
        for surface in exports.surfaces
        for entry in surface.entries
    )
    references = _collect_reference_attributions(catalogs)

    local_origins = tuple(
        ProjectModuleOriginPath(
            owning_module_path=attribution.identity.identity.module_path,
            namespace=attribution.identity.identity.namespace,
            declaration_kind=attribution.identity.identity.declaration_kind,
            local_name=attribution.identity.identity.declared_name,
            target_occurrence=attribution.identity,
            local_occurrence=attribution.identity,
        )
        for attribution in declarations
    )
    imported_origins = tuple(
        _binding_origin_path(binding, catalogs, exports, bindings)
        for environment in bindings.environments
        for binding in environment.bindings
    )
    origins = (*local_origins, *imported_origins)
    if len(set(origins)) != len(origins):
        raise ValueError("Origin builder produced duplicate complete paths.")
    local_origin_by_occurrence = {
        origin.local_occurrence: origin
        for origin in local_origins
        if origin.local_occurrence is not None
    }
    imported_origin_by_occurrence = {
        origin.import_occurrence: origin
        for origin in imported_origins
        if origin.import_occurrence is not None
    }

    provenance_by_reference: dict[
        ProjectModuleReferenceOccurrenceIdentity,
        ProjectModuleReferenceProvenance,
    ] = {}
    alias_resolution_by_owner = _alias_resolution_index(type_source_resolutions)
    for environment in type_source_resolutions.environments:
        for resolution in environment.type_resolutions:
            if resolution.canonical_kind is ProjectResolvedTypeKind.UNKNOWN:
                continue
            path = _type_provenance_path(
                resolution,
                alias_resolution_by_owner=alias_resolution_by_owner,
                local_origins=local_origin_by_occurrence,
                imported_origins=imported_origin_by_occurrence,
                active=frozenset(),
            )
            reference = path.reference
            _insert_one(
                provenance_by_reference,
                reference,
                ProjectModuleReferenceProvenance(
                    reference=reference,
                    paths=(path,),
                ),
                "type reference provenance",
            )
        for resolution in environment.source_shape_resolutions:
            reference = _source_reference_identity(resolution.reference)
            target = _declaration_identity(resolution.target_symbol.target_occurrence)
            origin = _origin_for_nominal_symbol(
                resolution.target_symbol,
                local_origin_by_occurrence,
                imported_origin_by_occurrence,
            )
            path = ProjectModuleReferenceProvenancePath(
                reference=reference,
                hops=(
                    ProjectModuleReferenceProvenanceHop(
                        reference=reference,
                        target=target,
                        origin=origin,
                    ),
                ),
                terminal_target=target,
            )
            _insert_one(
                provenance_by_reference,
                reference,
                ProjectModuleReferenceProvenance(
                    reference=reference,
                    paths=(path,),
                ),
                "source-shape provenance",
            )
    for environment in relation_resolutions.environments:
        for resolution in environment.resolutions:
            reference = _relation_reference_identity(resolution.reference)
            target = _declaration_identity(resolution.target_symbol.target_occurrence)
            origin = _origin_for_relation_symbol(
                resolution.target_symbol,
                local_origin_by_occurrence,
                imported_origin_by_occurrence,
            )
            path = ProjectModuleReferenceProvenancePath(
                reference=reference,
                hops=(
                    ProjectModuleReferenceProvenanceHop(
                        reference=reference,
                        target=target,
                        origin=origin,
                    ),
                ),
                terminal_target=target,
            )
            _insert_one(
                provenance_by_reference,
                reference,
                ProjectModuleReferenceProvenance(
                    reference=reference,
                    paths=(path,),
                ),
                "relation provenance",
            )
    reference_provenance = tuple(
        provenance_by_reference[attribution.identity]
        for attribution in references
        if attribution.identity in provenance_by_reference
    )

    module_dependencies = tuple(
        ProjectModuleImportDependencyFact(
            import_occurrence=_import_identity(edge.request),
            origin=edge.origin.identity,
            target=edge.target.identity,
        )
        for edge in graph.evidence_edges
    )
    import_attribution_ids = {item.identity for item in imports}
    if any(
        fact.import_occurrence not in import_attribution_ids
        for fact in module_dependencies
    ):
        raise ValueError("Module dependency lacks its import attribution.")

    dependencies: list[ProjectModuleDependencyFact] = []
    dependency_seen: set[ProjectModuleDependencyFact] = set()
    for provenance in reference_provenance:
        for path in provenance.paths:
            for hop in path.hops:
                dependency = ProjectModuleDependencyFact(
                    kind=_dependency_kind(hop.reference.role),
                    reference=hop.reference,
                    target_declaration=hop.target,
                    origin_path=hop.origin,
                )
                _append_exact_unique(dependencies, dependency_seen, dependency)

    source_field_origins, row_lineages, row_dependencies = _build_row_facts(
        catalogs,
        relation_resolutions,
        provenance_by_reference,
        local_origin_by_occurrence,
        imported_origin_by_occurrence,
    )
    for dependency in row_dependencies:
        _append_exact_unique(dependencies, dependency_seen, dependency)

    reference_ids = {attribution.identity for attribution in references}
    if any(item.reference not in reference_ids for item in reference_provenance):
        raise ValueError("Concrete provenance lacks its raw reference attribution.")
    if any(item.reference not in reference_ids for item in dependencies):
        raise ValueError("Concrete dependency lacks its raw reference attribution.")
    reference_order = {
        attribution.identity: position
        for position, attribution in enumerate(references)
    }
    dependencies.sort(key=lambda item: reference_order[item.reference])

    return ProjectModuleAttributionFactSet(
        declarations=declarations,
        imports=imports,
        facades=facades,
        references=references,
        origins=origins,
        reference_provenance=reference_provenance,
        module_dependencies=module_dependencies,
        dependencies=tuple(dependencies),
        source_field_origins=source_field_origins,
        row_lineages=row_lineages,
    )


def _collect_reference_attributions(
    catalogs: ProjectModuleCatalogSet,
) -> tuple[ProjectModuleReferenceAttribution, ...]:
    attributions: list[ProjectModuleReferenceAttribution] = []
    for catalog in catalogs.catalogs:
        for occurrence in catalog.occurrences:
            owner = _declaration_identity(occurrence)
            definition = occurrence.definition
            if type(definition) is TypeDef:
                attributions.append(
                    ProjectModuleReferenceAttribution(
                        identity=ProjectModuleReferenceOccurrenceIdentity(
                            owner=owner,
                            role=ProjectModuleReferenceRole.TYPE_ALIAS_BASE,
                            member_position=0,
                        ),
                        owner_occurrence=occurrence,
                        site=definition.base,
                    )
                )
            elif type(definition) is ShapeDef:
                for position, field_def in enumerate(definition.fields):
                    attributions.append(
                        ProjectModuleReferenceAttribution(
                            identity=ProjectModuleReferenceOccurrenceIdentity(
                                owner=owner,
                                role=ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
                                member_position=position,
                            ),
                            owner_occurrence=occurrence,
                            site=field_def.type_expr,
                        )
                    )
            elif type(definition) is SourceDef and definition.shape_name is not None:
                attributions.append(
                    ProjectModuleReferenceAttribution(
                        identity=ProjectModuleReferenceOccurrenceIdentity(
                            owner=owner,
                            role=ProjectModuleReferenceRole.SOURCE_SHAPE,
                            member_position=0,
                        ),
                        owner_occurrence=occurrence,
                        site=definition,
                    )
                )
            if type(definition) not in {TableDef, QueryDef}:
                continue
            relation = cast(TableDef | QueryDef, definition)
            attributions.append(
                ProjectModuleReferenceAttribution(
                    identity=ProjectModuleReferenceOccurrenceIdentity(
                        owner=owner,
                        role=ProjectModuleReferenceRole.RELATION_FROM,
                        member_position=0,
                    ),
                    owner_occurrence=occurrence,
                    site=relation.from_clause,
                )
            )
            let_names = (
                frozenset()
                if relation.let_clause is None
                else frozenset(item.name for item in relation.let_clause.bindings)
            )
            for position, item in enumerate(relation.select_items):
                expression = item.expression
                if type(expression) not in {NameExpr, DottedNameExpr} or (
                    type(expression) is NameExpr and expression.name in let_names
                ):
                    continue
                attributions.append(
                    ProjectModuleReferenceAttribution(
                        identity=ProjectModuleReferenceOccurrenceIdentity(
                            owner=owner,
                            role=ProjectModuleReferenceRole.ROW_FIELD,
                            member_position=position,
                        ),
                        owner_occurrence=occurrence,
                        site=item,
                    )
                )
    identities = tuple(item.identity for item in attributions)
    if len(set(identities)) != len(identities):
        raise ValueError("Reference attributions must retain unique occurrences.")
    return tuple(attributions)


def _facade_attribution(
    entry: ProjectModuleExportEntry,
    catalogs: ProjectModuleCatalogSet,
) -> ProjectModuleFacadeAttribution:
    occurrences = catalogs.find_identity(entry.target_identity)
    if len(occurrences) != 1:
        raise ValueError("Resolved facade target must have one exact occurrence.")
    return ProjectModuleFacadeAttribution(
        identity=_facade_identity(entry),
        origin=entry.origin,
        target_identity=entry.target_identity,
        target_occurrence=_declaration_identity(occurrences[0]),
        entry=entry,
    )


def _binding_origin_path(
    initial: ProjectResolvedImportedBinding,
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
) -> ProjectModuleOriginPath:
    hops: list[ProjectModuleAccessHop] = []
    current = initial
    visited: set[ProjectModuleImportOccurrenceIdentity] = set()
    while True:
        import_occurrence = _import_identity(current.request)
        if import_occurrence in visited:
            raise ValueError("Explicit re-export origin path must be acyclic.")
        visited.add(import_occurrence)
        entry = _exact_facade_entry(current, exports)
        hops.append(
            ProjectModuleAccessHop(
                import_occurrence=import_occurrence,
                facade_occurrence=_facade_identity(entry),
                facade_origin=entry.origin,
                target_identity=current.target_identity,
            )
        )
        if entry.origin is ProjectModuleExportEntryOrigin.LOCAL_DECLARATION:
            break
        candidate = entry.resolved_from
        if type(candidate) is not ProjectImportedExportCandidate:
            raise TypeError("Explicit re-export requires its imported candidate.")
        matches = tuple(
            binding
            for environment in bindings.environments
            for binding in environment.bindings
            if _candidate_matches_binding(candidate, binding)
        )
        if len(matches) != 1:
            raise ValueError("Explicit re-export candidate requires one exact binding.")
        current = matches[0]
        if current.target_identity != initial.target_identity:
            raise ValueError("Re-export path cannot rewrite nominal target identity.")
    occurrences = catalogs.find_identity(initial.target_identity)
    if len(occurrences) != 1:
        raise ValueError("Imported origin target must have one exact occurrence.")
    return ProjectModuleOriginPath(
        owning_module_path=initial.identity.owning_module_path,
        namespace=initial.identity.namespace,
        declaration_kind=initial.identity.declaration_kind,
        local_name=initial.identity.local_binding_name,
        target_occurrence=_declaration_identity(occurrences[0]),
        import_occurrence=_import_identity(initial.request),
        hops=tuple(hops),
    )


def _exact_facade_entry(
    binding: ProjectResolvedImportedBinding,
    exports: ProjectModuleExportSurfaceSet,
) -> ProjectModuleExportEntry:
    surfaces = exports.find_module_path(binding.target_module_path)
    if len(surfaces) != 1:
        raise ValueError("Resolved binding requires one exact direct facade.")
    expected = binding.resolved_entry
    matches = tuple(
        entry
        for entry in surfaces[0].entries
        if entry.namespace is binding.identity.namespace
        and entry.declaration_kind is binding.identity.declaration_kind
        and entry.exposed_name == binding.request.exported_name
        and entry.target_identity == binding.target_identity
        and entry.origin is expected.origin
        and entry.request.module_statement_position
        == expected.request.module_statement_position
        and entry.request.item_position == expected.request.item_position
    )
    if len(matches) != 1:
        raise ValueError("Resolved binding direct facade must have one exact entry.")
    return matches[0]


def _candidate_matches_binding(
    candidate: ProjectImportedExportCandidate,
    binding: ProjectResolvedImportedBinding,
) -> bool:
    expected_span = (
        binding.request.source_item.local_name_span
        or binding.request.source_item.exported_name_span
    )
    return (
        candidate.owning_module_path == binding.identity.owning_module_path
        and candidate.namespace is binding.identity.namespace
        and candidate.declaration_kind is binding.identity.declaration_kind
        and candidate.local_binding_name == binding.identity.local_binding_name
        and candidate.target_identity == binding.target_identity
        and candidate.module_statement_position
        == binding.request.module_statement_position
        and candidate.item_position == binding.request.item_position
        and candidate.source_span == expected_span
    )


def _alias_resolution_index(
    resolutions: ProjectTypeSourceResolutionSet,
) -> Mapping[
    ProjectDeclarationOccurrenceIdentity,
    ProjectResolvedModuleTypeReference,
]:
    result: dict[
        ProjectDeclarationOccurrenceIdentity,
        ProjectResolvedModuleTypeReference,
    ] = {}
    for environment in resolutions.environments:
        for resolution in environment.type_resolutions:
            if (
                resolution.reference.role
                is not ProjectModuleTypeReferenceRole.TYPE_ALIAS_BASE
            ):
                continue
            _insert_one(
                result,
                _declaration_identity(resolution.reference.owner),
                resolution,
                "type alias base resolution",
            )
    return MappingProxyType(result)


def _type_provenance_path(
    resolution: ProjectResolvedModuleTypeReference,
    *,
    alias_resolution_by_owner: Mapping[
        ProjectDeclarationOccurrenceIdentity,
        ProjectResolvedModuleTypeReference,
    ],
    local_origins: Mapping[
        ProjectDeclarationOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
    imported_origins: Mapping[
        ProjectModuleImportOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
    active: frozenset[ProjectModuleReferenceOccurrenceIdentity],
) -> ProjectModuleReferenceProvenancePath:
    first_reference = _type_reference_identity(resolution.reference)
    current = resolution
    visited = set(active)
    hops: list[ProjectModuleReferenceProvenanceHop] = []
    while True:
        reference = _type_reference_identity(current.reference)
        if reference in visited:
            raise ValueError("Concrete type provenance must be acyclic.")
        visited.add(reference)
        if current.direct_kind is ProjectResolvedTypeKind.BUILTIN:
            return ProjectModuleReferenceProvenancePath(
                reference=first_reference,
                hops=tuple(hops),
                terminal_builtin=current.canonical_name,
                terminal_reference=reference,
            )
        symbol = current.direct_symbol
        if symbol is None:
            raise ValueError("Concrete nominal type provenance requires a symbol.")
        target = _declaration_identity(symbol.target_occurrence)
        origin = _origin_for_nominal_symbol(symbol, local_origins, imported_origins)
        hops.append(
            ProjectModuleReferenceProvenanceHop(
                reference=reference,
                target=target,
                origin=origin,
            )
        )
        if current.direct_kind is not ProjectResolvedTypeKind.TYPE_ALIAS:
            return ProjectModuleReferenceProvenancePath(
                reference=first_reference,
                hops=tuple(hops),
                terminal_target=target,
            )
        next_resolution = alias_resolution_by_owner.get(target)
        if next_resolution is None:
            raise ValueError("Concrete alias provenance requires its base resolution.")
        current = next_resolution


def _origin_for_nominal_symbol(
    symbol: ProjectResolvedNominalSymbol,
    local_origins: Mapping[
        ProjectDeclarationOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
    imported_origins: Mapping[
        ProjectModuleImportOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
) -> ProjectModuleOriginPath:
    if type(symbol) is not ProjectResolvedNominalSymbol:
        raise TypeError("Nominal origin lookup requires a resolved symbol.")
    if symbol.local_occurrence is not None:
        key = _declaration_identity(symbol.local_occurrence)
        result = local_origins.get(key)
    else:
        assert symbol.imported_binding is not None
        result = imported_origins.get(_import_identity(symbol.imported_binding.request))
    if result is None or result.target_occurrence != _declaration_identity(
        symbol.target_occurrence
    ):
        raise ValueError("Resolved nominal symbol lacks one exact origin path.")
    return result


def _origin_for_relation_symbol(
    symbol: ProjectResolvedModuleRelationSymbol,
    local_origins: Mapping[
        ProjectDeclarationOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
    imported_origins: Mapping[
        ProjectModuleImportOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
) -> ProjectModuleOriginPath:
    if type(symbol) is not ProjectResolvedModuleRelationSymbol:
        raise TypeError("Relation origin lookup requires a resolved symbol.")
    if symbol.local_occurrence is not None:
        result = local_origins.get(_declaration_identity(symbol.local_occurrence))
    else:
        assert symbol.imported_binding is not None
        result = imported_origins.get(_import_identity(symbol.imported_binding.request))
    if result is None or result.target_occurrence != _declaration_identity(
        symbol.target_occurrence
    ):
        raise ValueError("Resolved relation symbol lacks one exact origin path.")
    return result


def _build_row_facts(
    catalogs: ProjectModuleCatalogSet,
    relation_resolutions: ProjectModuleRelationResolutionSet,
    provenance_by_reference: Mapping[
        ProjectModuleReferenceOccurrenceIdentity,
        ProjectModuleReferenceProvenance,
    ],
    local_origins: Mapping[
        ProjectDeclarationOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
    imported_origins: Mapping[
        ProjectModuleImportOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
) -> tuple[
    tuple[ProjectModuleSourceFieldOrigin, ...],
    tuple[ProjectModuleRelationLineage, ...],
    tuple[ProjectModuleDependencyFact, ...],
]:
    facts = tuple(
        fact
        for environment in relation_resolutions.environments
        for fact in environment.row_facts
    )
    resolution_by_owner = {
        _declaration_identity(resolution.reference.owner): resolution
        for environment in relation_resolutions.environments
        for resolution in environment.resolutions
    }
    lineage_by_owner: dict[
        ProjectDeclarationOccurrenceIdentity,
        ProjectModuleRelationLineage,
    ] = {}
    source_origins: list[ProjectModuleSourceFieldOrigin] = []
    row_dependencies: list[ProjectModuleDependencyFact] = []
    row_dependency_seen: set[ProjectModuleDependencyFact] = set()

    for fact in facts:
        owner = _declaration_identity(fact.owner)
        definition = fact.owner.definition
        if type(definition) is not SourceDef:
            continue
        if fact.state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
            lineage_by_owner[owner] = _empty_lineage(fact)
            continue
        schema = fact.state.schema
        if schema is None or schema.is_unknown:
            raise ValueError("Concrete source row fact requires a concrete schema.")
        reference = ProjectModuleReferenceOccurrenceIdentity(
            owner=owner,
            role=ProjectModuleReferenceRole.SOURCE_SHAPE,
            member_position=0,
        )
        provenance = provenance_by_reference.get(reference)
        if provenance is None or len(provenance.paths) != 1:
            raise ValueError("Concrete source requires one exact shape provenance.")
        provenance_path = provenance.paths[0]
        shape_owner = provenance_path.terminal_target
        if shape_owner is None:
            raise ValueError("Concrete source shape must terminate nominally.")
        shape_occurrences = catalogs.find_identity(shape_owner.identity)
        if len(shape_occurrences) != 1:
            raise ValueError("Concrete source shape requires one occurrence.")
        shape = shape_occurrences[0].definition
        if type(shape) is not ShapeDef:
            raise ValueError("Concrete source shape terminal must be a ShapeDef.")
        if tuple(schema.fields) != tuple(field_def.name for field_def in shape.fields):
            raise ValueError("Concrete source schema must retain exact shape order.")
        field_lineages: list[ProjectModuleRowFieldLineage] = []
        for position, field_def in enumerate(shape.fields):
            source_field = ProjectModuleRowFieldIdentity(
                owner=owner,
                kind=ProjectModuleRowFieldKind.SOURCE_FIELD,
                field_position=position,
                name=field_def.name,
            )
            shape_field = ProjectModuleRowFieldIdentity(
                owner=shape_owner,
                kind=ProjectModuleRowFieldKind.SHAPE_FIELD,
                field_position=position,
                name=field_def.name,
            )
            source_origins.append(
                ProjectModuleSourceFieldOrigin(
                    source_field=source_field,
                    shape_field=shape_field,
                    source_shape_provenance=provenance_path,
                )
            )
            path = ProjectModuleRowLineagePath(
                output_field=source_field,
                root_field=source_field,
            )
            field_lineages.append(
                ProjectModuleRowFieldLineage(
                    field=source_field,
                    paths=(path,),
                )
            )
        lineage_by_owner[owner] = ProjectModuleRelationLineage(
            owner=owner,
            status=fact.state.status,
            reason=fact.state.reason,
            fields=tuple(field_lineages),
        )

    pending: list[ProjectModuleRelationRowFact] = []
    for fact in facts:
        definition = fact.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            continue
        if fact.state.status is ProjectRelationRowSchemaStatus.CONCRETE:
            pending.append(fact)
        else:
            owner = _declaration_identity(fact.owner)
            lineage_by_owner[owner] = _empty_lineage(fact)

    while pending:
        progressed = False
        next_pending: list[ProjectModuleRelationRowFact] = []
        for fact in pending:
            owner = _declaration_identity(fact.owner)
            resolution = resolution_by_owner.get(owner)
            if resolution is None:
                raise ValueError("Concrete relation row requires one exact resolution.")
            target_owner = _declaration_identity(
                resolution.target_symbol.target_occurrence
            )
            upstream = lineage_by_owner.get(target_owner)
            if upstream is None:
                next_pending.append(fact)
                continue
            if upstream.status is not ProjectRelationRowSchemaStatus.CONCRETE:
                raise ValueError("Concrete relation row requires concrete upstream.")
            lineage, dependencies = _concrete_relation_lineage(
                fact,
                resolution,
                upstream,
                local_origins=local_origins,
                imported_origins=imported_origins,
            )
            lineage_by_owner[owner] = lineage
            for dependency in dependencies:
                _append_exact_unique(
                    row_dependencies,
                    row_dependency_seen,
                    dependency,
                )
            progressed = True
        if not progressed:
            raise ValueError("Concrete acyclic row lineage must make finite progress.")
        pending = next_pending

    expected_owners = tuple(_declaration_identity(fact.owner) for fact in facts)
    if set(lineage_by_owner) != set(expected_owners):
        raise ValueError("Row lineage must cover every retained row fact.")
    row_lineages = tuple(
        lineage_by_owner[owner]
        for owner in sorted(
            expected_owners,
            key=lambda item: (item.module_position, item.declaration_position),
        )
    )
    source_origins.sort(
        key=lambda item: (
            item.source_field.owner.module_position,
            item.source_field.owner.declaration_position,
            item.source_field.field_position,
        )
    )
    return tuple(source_origins), row_lineages, tuple(row_dependencies)


def _concrete_relation_lineage(
    fact: ProjectModuleRelationRowFact,
    resolution: ProjectResolvedModuleRelationReference,
    upstream: ProjectModuleRelationLineage,
    *,
    local_origins: Mapping[
        ProjectDeclarationOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
    imported_origins: Mapping[
        ProjectModuleImportOccurrenceIdentity,
        ProjectModuleOriginPath,
    ],
) -> tuple[
    ProjectModuleRelationLineage,
    tuple[ProjectModuleDependencyFact, ...],
]:
    owner = _declaration_identity(fact.owner)
    definition = fact.owner.definition
    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("Concrete relation lineage requires a table or query.")
    relation = cast(TableDef | QueryDef, definition)
    schema = fact.state.schema
    if schema is None or schema.is_unknown:
        raise ValueError("Concrete relation lineage requires a concrete schema.")
    upstream_by_name = {item.field.name: item for item in upstream.fields}
    if len(upstream_by_name) != len(upstream.fields):
        raise ValueError("Concrete upstream lineage fields must have unique names.")
    relation_origin = _origin_for_relation_symbol(
        resolution.target_symbol,
        local_origins,
        imported_origins,
    )
    fields: list[ProjectModuleRowFieldLineage] = []
    dependencies: list[ProjectModuleDependencyFact] = []
    dependency_seen: set[ProjectModuleDependencyFact] = set()
    output_names: list[str] = []
    for position, item in enumerate(relation.select_items):
        decoded = _direct_field_names(
            item,
            source_name=relation.from_clause.source_name,
        )
        if decoded is None:
            raise ValueError("Concrete Slice 11 lineage requires direct fields only.")
        output_name, lookup_name = decoded
        output_names.append(output_name)
        upstream_lineage = upstream_by_name.get(lookup_name)
        if upstream_lineage is None:
            raise ValueError("Concrete lineage requires one upstream field.")
        output_field = ProjectModuleRowFieldIdentity(
            owner=owner,
            kind=ProjectModuleRowFieldKind.RELATION_OUTPUT,
            field_position=position,
            name=output_name,
        )
        reference = ProjectModuleReferenceOccurrenceIdentity(
            owner=owner,
            role=ProjectModuleReferenceRole.ROW_FIELD,
            member_position=position,
        )
        projection_kind = (
            ProjectModuleProjectionKind.DIRECT
            if output_name == lookup_name
            else ProjectModuleProjectionKind.RENAMED
        )
        paths: list[ProjectModuleRowLineagePath] = []
        for upstream_path in upstream_lineage.paths:
            hop = ProjectModuleRowLineageHop(
                reference=reference,
                projection_kind=projection_kind,
                output_field=output_field,
                upstream_field=upstream_lineage.field,
                relation_origin=relation_origin,
            )
            paths.append(
                ProjectModuleRowLineagePath(
                    output_field=output_field,
                    root_field=upstream_path.root_field,
                    hops=(hop, *upstream_path.hops),
                )
            )
        fields.append(
            ProjectModuleRowFieldLineage(
                field=output_field,
                paths=tuple(paths),
            )
        )
        dependency = ProjectModuleDependencyFact(
            kind=ProjectModuleDependencyKind.ROW_FIELD_REFERENCE,
            reference=reference,
            target_row_field=upstream_lineage.field,
            origin_path=relation_origin,
        )
        _append_exact_unique(dependencies, dependency_seen, dependency)
    if tuple(schema.fields) != tuple(output_names):
        raise ValueError("Concrete lineage outputs must retain exact schema order.")
    return (
        ProjectModuleRelationLineage(
            owner=owner,
            status=fact.state.status,
            reason=fact.state.reason,
            fields=tuple(fields),
        ),
        tuple(dependencies),
    )


def _empty_lineage(
    fact: ProjectModuleRelationRowFact,
) -> ProjectModuleRelationLineage:
    if fact.state.status is ProjectRelationRowSchemaStatus.CONCRETE:
        raise ValueError("Concrete row facts require concrete lineage.")
    return ProjectModuleRelationLineage(
        owner=_declaration_identity(fact.owner),
        status=fact.state.status,
        reason=fact.state.reason,
    )


def _validate_builder_inputs(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
    relation_resolutions: ProjectModuleRelationResolutionSet,
) -> None:
    if type(modules) is not tuple or any(
        type(module) is not ProjectLogicalModule for module in modules
    ):
        raise TypeError("Attribution builder requires a logical-module tuple.")
    expected_types = (
        (catalogs, ProjectModuleCatalogSet),
        (exports, ProjectModuleExportSurfaceSet),
        (bindings, ProjectModuleBindingEnvironmentSet),
        (graph, ProjectModuleGraph),
        (type_source_resolutions, ProjectTypeSourceResolutionSet),
        (relation_resolutions, ProjectModuleRelationResolutionSet),
    )
    for value, expected_type in expected_types:
        if type(value) is not expected_type:
            raise TypeError(f"Attribution builder requires {expected_type.__name__}.")
    lengths = {
        len(modules),
        len(catalogs.catalogs),
        len(exports.surfaces),
        len(bindings.environments),
        len(graph.vertices),
    }
    if len(lengths) != 1:
        raise ValueError("Attribution inputs must cover every selected module.")
    for position, values in enumerate(
        zip(
            modules,
            catalogs.catalogs,
            exports.surfaces,
            bindings.environments,
            graph.vertices,
            strict=True,
        )
    ):
        module, catalog, surface, environment, vertex = values
        if (
            module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or module.position != position
            or module.parsed_input is None
            or catalog.module is not module
            or surface.module is not module
            or environment.module is not module
            or vertex.module is not module
        ):
            raise ValueError("Attribution inputs must retain selected module order.")
    expected_dependency_order = _dependency_first_identities(graph)
    if (
        type_source_resolutions.dependency_order != expected_dependency_order
        or relation_resolutions.dependency_order != expected_dependency_order
    ):
        raise ValueError(
            "Attribution resolvers require the exact graph dependency order."
        )
    dependency_paths = tuple(
        identity.path for identity in type_source_resolutions.dependency_order
    )
    if dependency_paths != tuple(
        environment.module.path for environment in type_source_resolutions.environments
    ) or dependency_paths != tuple(
        environment.module.path for environment in relation_resolutions.environments
    ):
        raise ValueError(
            "Attribution resolver environments must be dependency ordered."
        )
    cyclic_paths = {
        member.identity.path
        for cycle in graph.cycles
        for member in cycle.component.members
    }
    expected_acyclic = {module.path for module in modules} - cyclic_paths
    if set(dependency_paths) != expected_acyclic:
        raise ValueError("Attribution resolvers must cover every acyclic module.")

    catalog_by_path = {catalog.module.path: catalog for catalog in catalogs.catalogs}
    type_environment_by_path = {
        environment.module.path: environment
        for environment in type_source_resolutions.environments
    }
    for environment in relation_resolutions.environments:
        catalog = catalog_by_path[environment.module.path]
        type_environment = type_environment_by_path[environment.module.path]
        expected_type_references: list[ProjectModuleReferenceOccurrenceIdentity] = []
        expected_source_references: list[ProjectModuleReferenceOccurrenceIdentity] = []
        expected_relation_references: list[
            ProjectModuleReferenceOccurrenceIdentity
        ] = []
        for occurrence in catalog.occurrences:
            owner = _declaration_identity(occurrence)
            definition = occurrence.definition
            if type(definition) is TypeDef:
                expected_type_references.append(
                    ProjectModuleReferenceOccurrenceIdentity(
                        owner=owner,
                        role=ProjectModuleReferenceRole.TYPE_ALIAS_BASE,
                        member_position=0,
                    )
                )
            elif type(definition) is ShapeDef:
                expected_type_references.extend(
                    ProjectModuleReferenceOccurrenceIdentity(
                        owner=owner,
                        role=ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
                        member_position=position,
                    )
                    for position in range(len(definition.fields))
                )
            elif type(definition) is SourceDef and definition.shape_name is not None:
                expected_source_references.append(
                    ProjectModuleReferenceOccurrenceIdentity(
                        owner=owner,
                        role=ProjectModuleReferenceRole.SOURCE_SHAPE,
                        member_position=0,
                    )
                )
            if type(definition) in {TableDef, QueryDef}:
                expected_relation_references.append(
                    ProjectModuleReferenceOccurrenceIdentity(
                        owner=owner,
                        role=ProjectModuleReferenceRole.RELATION_FROM,
                        member_position=0,
                    )
                )
        actual_type_references = tuple(
            _type_reference_identity(resolution.reference)
            for resolution in type_environment.type_resolutions
        )
        if actual_type_references != tuple(expected_type_references):
            raise ValueError("Type resolutions must cover exact catalog references.")
        actual_source_references = tuple(
            _source_reference_identity(reference)
            for reference in type_environment.source_shape_references
        )
        if actual_source_references != tuple(expected_source_references):
            raise ValueError("Source references must cover exact catalog references.")
        actual_relation_references = tuple(
            _relation_reference_identity(reference)
            for reference in environment.references
        )
        if actual_relation_references != tuple(expected_relation_references):
            raise ValueError("Relation references must cover exact catalog references.")
        expected = tuple(
            occurrence
            for occurrence in catalog.occurrences
            if occurrence.identity.declaration_kind in _RELATION_KINDS
        )
        actual = tuple(fact.owner for fact in environment.row_facts)
        if actual != expected:
            raise ValueError("Relation row facts must cover exact catalog occurrences.")

    expected_pairs = {
        (evidence.origin, evidence.target) for evidence in graph.evidence_edges
    }
    actual_pairs = {(edge.origin, edge.target) for edge in graph.edges}
    if actual_pairs != expected_pairs:
        raise ValueError("Module canonical edges must cover every evidence pair.")
    for edge in graph.edges:
        expected_evidence = tuple(
            evidence
            for evidence in graph.evidence_edges
            if (evidence.origin, evidence.target) == (edge.origin, edge.target)
        )
        if edge.evidence_edges != expected_evidence:
            raise ValueError("Module canonical edge evidence must be complete.")
    for component in graph.components:
        member_set = set(component.members)
        expected_internal = tuple(
            edge
            for edge in graph.edges
            if edge.origin in member_set and edge.target in member_set
        )
        if component.internal_edges != expected_internal:
            raise ValueError("Module component internal edges must be complete.")


def _dependency_first_identities(
    graph: ProjectModuleGraph,
) -> tuple[ProjectModuleIdentity, ...]:
    """Recompute the exact Slice 9 dependency-first order at this boundary."""

    cyclic = {member for cycle in graph.cycles for member in cycle.component.members}
    valid = tuple(vertex for vertex in graph.vertices if vertex not in cyclic)
    valid_set = set(valid)
    remaining_dependencies: dict[
        ProjectModuleGraphVertex,
        set[ProjectModuleGraphVertex],
    ] = {
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
    return tuple(vertex.identity for vertex in emitted)


def _declaration_identity(
    occurrence: ProjectDeclarationOccurrence,
) -> ProjectDeclarationOccurrenceIdentity:
    if type(occurrence) is not ProjectDeclarationOccurrence:
        raise TypeError("Declaration identity requires an occurrence.")
    return ProjectDeclarationOccurrenceIdentity(
        identity=occurrence.identity,
        module_position=occurrence.module_position,
        declaration_position=occurrence.declaration_position,
    )


def _import_identity(
    request: ProjectModuleImportRequest,
) -> ProjectModuleImportOccurrenceIdentity:
    if type(request) is not ProjectModuleImportRequest:
        raise TypeError("Import identity requires one retained request.")
    return ProjectModuleImportOccurrenceIdentity(
        binding_identity=request.identity,
        target_module_path=request.target_module_path,
        exported_name=request.exported_name,
        module_statement_position=request.module_statement_position,
        item_position=request.item_position,
    )


def _facade_identity(
    entry: ProjectModuleExportEntry,
) -> ProjectModuleFacadeOccurrenceIdentity:
    if type(entry) is not ProjectModuleExportEntry:
        raise TypeError("Facade identity requires one retained entry.")
    return ProjectModuleFacadeOccurrenceIdentity(
        owning_module_path=entry.owning_module_path,
        namespace=entry.namespace,
        declaration_kind=entry.declaration_kind,
        exposed_name=entry.exposed_name,
        module_statement_position=entry.request.module_statement_position,
        item_position=entry.request.item_position,
    )


def _type_reference_identity(
    reference: ProjectModuleTypeReference,
) -> ProjectModuleReferenceOccurrenceIdentity:
    if type(reference) is not ProjectModuleTypeReference:
        raise TypeError("Type reference identity requires one retained reference.")
    role = {
        ProjectModuleTypeReferenceRole.TYPE_ALIAS_BASE: (
            ProjectModuleReferenceRole.TYPE_ALIAS_BASE
        ),
        ProjectModuleTypeReferenceRole.SHAPE_FIELD_TYPE: (
            ProjectModuleReferenceRole.SHAPE_FIELD_TYPE
        ),
    }[reference.role]
    return ProjectModuleReferenceOccurrenceIdentity(
        owner=_declaration_identity(reference.owner),
        role=role,
        member_position=reference.member_position,
    )


def _source_reference_identity(
    reference: ProjectModuleSourceShapeReference,
) -> ProjectModuleReferenceOccurrenceIdentity:
    if type(reference) is not ProjectModuleSourceShapeReference:
        raise TypeError("Source reference identity requires one retained reference.")
    return ProjectModuleReferenceOccurrenceIdentity(
        owner=_declaration_identity(reference.owner),
        role=ProjectModuleReferenceRole.SOURCE_SHAPE,
        member_position=0,
    )


def _relation_reference_identity(
    reference: ProjectModuleRelationReference,
) -> ProjectModuleReferenceOccurrenceIdentity:
    if type(reference) is not ProjectModuleRelationReference:
        raise TypeError("Relation reference identity requires one retained reference.")
    return ProjectModuleReferenceOccurrenceIdentity(
        owner=_declaration_identity(reference.owner),
        role=ProjectModuleReferenceRole.RELATION_FROM,
        member_position=0,
    )


def _dependency_kind(
    role: ProjectModuleReferenceRole,
) -> ProjectModuleDependencyKind:
    if role in {
        ProjectModuleReferenceRole.TYPE_ALIAS_BASE,
        ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
    }:
        return ProjectModuleDependencyKind.TYPE_REFERENCE
    if role is ProjectModuleReferenceRole.SOURCE_SHAPE:
        return ProjectModuleDependencyKind.SOURCE_SHAPE_REFERENCE
    if role is ProjectModuleReferenceRole.RELATION_FROM:
        return ProjectModuleDependencyKind.RELATION_REFERENCE
    raise ValueError("Row-field dependencies are built from row lineage.")


def _validate_reference_site(
    identity: ProjectModuleReferenceOccurrenceIdentity,
    owner_occurrence: ProjectDeclarationOccurrence,
    site: _ReferenceSite,
) -> None:
    definition = owner_occurrence.definition
    position = identity.member_position
    if identity.role is ProjectModuleReferenceRole.TYPE_ALIAS_BASE:
        valid = (
            type(definition) is TypeDef and position == 0 and (definition.base is site)
        )
    elif identity.role is ProjectModuleReferenceRole.SHAPE_FIELD_TYPE:
        valid = (
            type(definition) is ShapeDef
            and position < len(definition.fields)
            and definition.fields[position].type_expr is site
        )
    elif identity.role is ProjectModuleReferenceRole.SOURCE_SHAPE:
        valid = (
            type(definition) is SourceDef
            and definition.shape_name is not None
            and position == 0
            and definition is site
        )
    elif identity.role is ProjectModuleReferenceRole.RELATION_FROM:
        if type(definition) not in {TableDef, QueryDef}:
            valid = False
        else:
            relation = cast(TableDef | QueryDef, definition)
            valid = position == 0 and relation.from_clause is site
    else:
        if type(definition) not in {TableDef, QueryDef}:
            valid = False
        else:
            relation = cast(TableDef | QueryDef, definition)
            valid = (
                position < len(relation.select_items)
                and relation.select_items[position] is site
                and type(relation.select_items[position].expression)
                in {NameExpr, DottedNameExpr}
            )
    if not valid:
        raise ValueError("Reference attribution does not match its retained site.")


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


def _validate_position(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} position must be a non-negative integer.")


def _require_tuple(values: object, item_type: type, label: str) -> None:
    if type(values) is not tuple or any(type(item) is not item_type for item in values):
        raise TypeError(f"{label} must be a tuple of {item_type.__name__} values.")


def _require_unique(
    values: tuple[_ItemT, ...],
    key: Callable[[_ItemT], object],
    label: str,
) -> None:
    keys = tuple(key(item) for item in values)
    if len(set(keys)) != len(keys):
        raise ValueError(f"Fact-set {label} identities must be unique.")


def _bucket(
    values: tuple[_ValueT, ...],
    key: Callable[[_ValueT], _KeyT],
) -> dict[_KeyT, list[_ValueT]]:
    buckets: dict[_KeyT, list[_ValueT]] = {}
    for value in values:
        buckets.setdefault(key(value), []).append(value)
    return buckets


def _tuple_mapping(
    values: Mapping[_KeyT, list[_ValueT]],
) -> Mapping[_KeyT, tuple[_ValueT, ...]]:
    return MappingProxyType({key: tuple(items) for key, items in values.items()})


def _insert_one(
    values: dict[_KeyT, _ValueT],
    key: _KeyT,
    value: _ValueT,
    label: str,
) -> None:
    if key in values:
        raise ValueError(f"Duplicate {label} occurrence.")
    values[key] = value


def _append_exact_unique(
    values: list[_ValueT],
    seen: set[_ValueT],
    value: _ValueT,
) -> None:
    if value in seen:
        return
    seen.add(value)
    values.append(value)
