"""Private deterministic module inspection and canonical serialization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar

from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedTypeKind,
    ProjectRowFieldNullability,
    ProjectRowResultRole,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleAttributionFactSet,
    ProjectModuleDependencyFact,
    ProjectModuleDependencyKind,
    ProjectModuleOriginPath,
    ProjectModuleProjectionKind,
    ProjectModuleReferenceRole,
    ProjectModuleRelationLineage,
    ProjectModuleRowFieldIdentity,
    ProjectModuleRowFieldKind,
)
from pietto._project.module_bindings import (
    ProjectModuleBindingEnvironment,
    ProjectModuleBindingEnvironmentSet,
    ProjectModuleBindingIssueStatus,
    ProjectModuleImportRequest,
)
from pietto._project.module_carrier import (
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.module_catalog import (
    ProjectModuleCatalogSet,
    ProjectNominalDeclarationIdentity,
)
from pietto._project.module_exports import (
    ProjectModuleExportEntryOrigin,
    ProjectModuleExportIssueStatus,
    ProjectModuleExportRequest,
    ProjectModuleExportSurface,
    ProjectModuleExportSurfaceSet,
)
from pietto._project.module_graph import (
    ProjectModuleGraph,
    ProjectModuleGraphIssueStatus,
)
from pietto._project.module_package_neutral_identity import (
    ProjectLayeredAvailability,
    ProjectLayeredDeclarationAsset,
    ProjectLayeredLoaderReadiness,
    ProjectLayeredLoaderReadinessFact,
    ProjectLayeredLoaderReadinessReason,
    ProjectLayeredModuleAsset,
    ProjectLayeredOwnerIdentity,
    ProjectLayeredSourceDigestIdentity,
    ProjectModulePackageNeutralIdentityFactSet,
)
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionIssueStatus,
    ProjectModuleRelationResolutionSet,
    ProjectResolvedModuleRelationReference,
)
from pietto._project.module_resolution import (
    ProjectModuleTypeReferenceRole,
    ProjectResolvedModuleSourceShapeReference,
    ProjectResolvedModuleTypeReference,
    ProjectTypeSourceResolutionIssueStatus,
    ProjectTypeSourceResolutionSet,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSemanticFactSet,
)

__all__: tuple[str, ...] = ()

_Key = TypeVar("_Key")
_Value = TypeVar("_Value")

_INSPECTION_ABSENT_TOKEN = "n:"

_INSPECTION_ESCAPES: Mapping[str, str] = MappingProxyType(
    {
        "\\": "\\\\",
        "\t": "\\t",
        "\n": "\\n",
        "\r": "\\r",
    }
)

_INSPECTION_DELETE_CHARACTER = "\x7f"

_INSPECTION_FIRST_PRINTABLE = " "

_INSPECTION_SURROGATE_START = "\ud800"

_INSPECTION_SURROGATE_END = "\udfff"


class ProjectInspectionFormat(StrEnum):
    """The exact private canonical inspection format this Slice produces."""

    MODULE_INSPECTION_V1 = "pietto.module-inspection.v1"


class ProjectInspectionBinding(StrEnum):
    """How one inspected local lookup name reaches its nominal declaration."""

    LOCAL_DECLARATION = "local_declaration"
    IMPORTED_BINDING = "imported_binding"


class ProjectInspectionIssueFamily(StrEnum):
    """The exact issue families an inspected module record retains."""

    GRAPH = "graph"
    TYPE_SOURCE = "type_source"
    RELATION = "relation"


_INSPECTION_ISSUE_STATUS_VALUES: Mapping[
    ProjectInspectionIssueFamily, frozenset[str]
] = MappingProxyType(
    {
        ProjectInspectionIssueFamily.GRAPH: frozenset(
            member.value for member in ProjectModuleGraphIssueStatus
        ),
        ProjectInspectionIssueFamily.TYPE_SOURCE: frozenset(
            member.value for member in ProjectTypeSourceResolutionIssueStatus
        ),
        ProjectInspectionIssueFamily.RELATION: frozenset(
            member.value for member in ProjectModuleRelationResolutionIssueStatus
        ),
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionModuleCycle:
    """One ordered module cycle retained as blocking readiness evidence."""

    members: tuple[ProjectModuleIdentity, ...]

    def __post_init__(self) -> None:
        """Require a non-empty ordered tuple of exact module identities."""

        _require_tuple(self.members, ProjectModuleIdentity, "Inspection cycle members")
        if not self.members:
            raise ValueError("Inspection cycle requires at least one member.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionReadiness:
    """One inspected loader-readiness fact with its complete cycle evidence."""

    status: ProjectLayeredLoaderReadiness
    reason: ProjectLayeredLoaderReadinessReason
    cycles: tuple[ProjectInspectionModuleCycle, ...] = ()
    fact: ProjectLayeredLoaderReadinessFact = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject readiness that disagrees with its exact retained fact."""

        if type(self.status) is not ProjectLayeredLoaderReadiness:
            raise TypeError("Inspection readiness requires an exact status.")
        if type(self.reason) is not ProjectLayeredLoaderReadinessReason:
            raise TypeError("Inspection readiness requires an exact reason.")
        _require_tuple(
            self.cycles,
            ProjectInspectionModuleCycle,
            "Inspection readiness cycles",
        )
        if type(self.fact) is not ProjectLayeredLoaderReadinessFact:
            raise TypeError("Inspection readiness requires an exact Slice 13 fact.")
        if self.status is not self.fact.status or self.reason is not self.fact.reason:
            raise ValueError("Inspection readiness must mirror its exact fact.")
        if len(self.cycles) != len(self.fact.blocking_issues):
            raise ValueError("Inspection readiness must retain every blocking cycle.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionImportEvidence:
    """One inspected import request proving one selected module dependency."""

    target: ProjectModuleIdentity
    module_statement_position: int
    item_position: int

    def __post_init__(self) -> None:
        """Require an exact target identity and non-negative source positions."""

        if type(self.target) is not ProjectModuleIdentity:
            raise TypeError("Inspection import evidence requires a module identity.")
        _require_position(self.module_statement_position, "import evidence statement")
        _require_position(self.item_position, "import evidence item")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionGraph:
    """One inspected module-graph neighbourhood in canonical authority order."""

    component_members: tuple[ProjectModuleIdentity, ...]
    component_is_cyclic: bool
    dependency_targets: tuple[ProjectModuleIdentity, ...] = ()
    import_evidence: tuple[ProjectInspectionImportEvidence, ...] = ()

    def __post_init__(self) -> None:
        """Require a non-empty component and exact ordered neighbour tuples."""

        _require_tuple(
            self.component_members,
            ProjectModuleIdentity,
            "Inspection component members",
        )
        if not self.component_members:
            raise ValueError("Inspection graph requires a non-empty component.")
        if type(self.component_is_cyclic) is not bool:
            raise TypeError("Inspection graph requires an exact cyclic flag.")
        _require_tuple(
            self.dependency_targets,
            ProjectModuleIdentity,
            "Inspection dependency targets",
        )
        _require_tuple(
            self.import_evidence,
            ProjectInspectionImportEvidence,
            "Inspection import evidence",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionImport:
    """One inspected import request, its local alias, and its nominal target.

    The local alias and the nominal target are separate facts: a rename keeps
    the nominal identity of the exported declaration untouched.
    """

    local_name: str
    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    target_module_path: str
    exported_name: str
    module_statement_position: int
    item_position: int
    resolved_target: ProjectNominalDeclarationIdentity | None = None
    issue_statuses: tuple[ProjectModuleBindingIssueStatus, ...] = ()
    request: ProjectModuleImportRequest = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject an inspected import detached from its exact source request."""

        _require_text(self.local_name, "Inspection import local name")
        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Inspection import requires an exact namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Inspection import requires an exact declaration kind.")
        _require_text(self.target_module_path, "Inspection import target module path")
        _require_text(self.exported_name, "Inspection import exported name")
        _require_position(self.module_statement_position, "import statement")
        _require_position(self.item_position, "import item")
        if self.resolved_target is not None and (
            type(self.resolved_target) is not ProjectNominalDeclarationIdentity
        ):
            raise TypeError("Inspection import target must be a nominal identity.")
        _require_tuple(
            self.issue_statuses,
            ProjectModuleBindingIssueStatus,
            "Inspection import issue statuses",
        )
        if type(self.request) is not ProjectModuleImportRequest:
            raise TypeError("Inspection import requires an exact import request.")
        identity = self.request.identity
        if (
            self.local_name != identity.local_binding_name
            or self.namespace is not identity.namespace
            or self.declaration_kind is not identity.declaration_kind
            or self.target_module_path != self.request.target_module_path
            or self.exported_name != self.request.exported_name
            or self.module_statement_position != self.request.module_statement_position
            or self.item_position != self.request.item_position
        ):
            raise ValueError("Inspection import must mirror its exact request.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionExport:
    """One inspected export request and the facade entry it did or did not make."""

    local_name: str
    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    module_statement_position: int
    item_position: int
    exposed_name: str | None = None
    entry_origin: ProjectModuleExportEntryOrigin | None = None
    target_identity: ProjectNominalDeclarationIdentity | None = None
    issue_statuses: tuple[ProjectModuleExportIssueStatus, ...] = ()
    request: ProjectModuleExportRequest = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject an inspected export detached from its exact source request."""

        _require_text(self.local_name, "Inspection export local name")
        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Inspection export requires an exact namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Inspection export requires an exact declaration kind.")
        _require_position(self.module_statement_position, "export statement")
        _require_position(self.item_position, "export item")
        _require_optional_text(self.exposed_name, "Inspection export exposed name")
        if self.entry_origin is not None and (
            type(self.entry_origin) is not ProjectModuleExportEntryOrigin
        ):
            raise TypeError("Inspection export requires an exact entry origin.")
        if self.target_identity is not None and (
            type(self.target_identity) is not ProjectNominalDeclarationIdentity
        ):
            raise TypeError("Inspection export target must be a nominal identity.")
        resolved = self.exposed_name is not None
        if (self.entry_origin is not None) != resolved or (
            self.target_identity is not None
        ) != resolved:
            raise ValueError("Inspection export entry facts are one atomic tuple.")
        _require_tuple(
            self.issue_statuses,
            ProjectModuleExportIssueStatus,
            "Inspection export issue statuses",
        )
        if type(self.request) is not ProjectModuleExportRequest:
            raise TypeError("Inspection export requires an exact export request.")
        if (
            self.local_name != self.request.local_name
            or self.namespace is not self.request.namespace
            or self.declaration_kind is not self.request.declaration_kind
            or self.module_statement_position != self.request.module_statement_position
            or self.item_position != self.request.item_position
        ):
            raise ValueError("Inspection export must mirror its exact request.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionRowField:
    """One inspected concrete row field of one relation declaration."""

    name: str
    nullability: ProjectRowFieldNullability
    result_role: ProjectRowResultRole

    def __post_init__(self) -> None:
        """Require exact row-field facts."""

        _require_text(self.name, "Inspection row field name")
        if type(self.nullability) is not ProjectRowFieldNullability:
            raise TypeError("Inspection row field requires an exact nullability.")
        if type(self.result_role) is not ProjectRowResultRole:
            raise TypeError("Inspection row field requires an exact result role.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionDeclaration:
    """One inspected nominal declaration occurrence and its availability."""

    owner: ProjectLayeredOwnerIdentity
    identity: ProjectNominalDeclarationIdentity
    declaration_position: int
    availability: ProjectLayeredAvailability
    occurrence_count: int
    occurrence_index: int
    relation_status: ProjectRelationRowSchemaStatus | None = None
    relation_reason: ProjectRelationRowSchemaReason | None = None
    row_fields: tuple[ProjectInspectionRowField, ...] = ()
    asset: ProjectLayeredDeclarationAsset = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject an inspected declaration detached from its exact Slice 13 asset."""

        if type(self.owner) is not ProjectLayeredOwnerIdentity:
            raise TypeError("Inspection declaration requires an owner identity.")
        if type(self.identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Inspection declaration requires a nominal identity.")
        _require_position(self.declaration_position, "inspection declaration")
        if type(self.availability) is not ProjectLayeredAvailability:
            raise TypeError("Inspection declaration requires an exact availability.")
        _require_position(self.occurrence_count, "inspection occurrence count")
        _require_position(self.occurrence_index, "inspection occurrence index")
        if self.occurrence_count < 1 or self.occurrence_index >= self.occurrence_count:
            raise ValueError("Inspection occurrence index must sit inside its bucket.")
        if self.relation_status is not None and (
            type(self.relation_status) is not ProjectRelationRowSchemaStatus
        ):
            raise TypeError("Inspection relation status must be exact.")
        if self.relation_reason is not None and (
            type(self.relation_reason) is not ProjectRelationRowSchemaReason
        ):
            raise TypeError("Inspection relation reason must be exact.")
        if (self.relation_status is None) != (self.relation_reason is None):
            raise ValueError("Inspection relation state is one atomic tuple.")
        _require_tuple(
            self.row_fields,
            ProjectInspectionRowField,
            "Inspection declaration row fields",
        )
        if self.relation_status is None and self.row_fields:
            raise ValueError("Inspection row fields require a retained relation state.")
        if type(self.asset) is not ProjectLayeredDeclarationAsset:
            raise TypeError("Inspection declaration requires an exact Slice 13 asset.")
        if (
            self.owner is not self.asset.owner
            or self.identity is not self.asset.identity
            or self.declaration_position != self.asset.declaration_position
            or self.availability is not self.asset.availability
            or self.occurrence_count != len(self.asset.identity_occurrences)
        ):
            raise ValueError("Inspection declaration must mirror its exact asset.")
        state = self.asset.relation_state
        if state is None:
            if self.relation_status is not None:
                raise ValueError("Inspection relation state must mirror its asset.")
            return
        if (
            self.relation_status is not state.status
            or self.relation_reason is not state.reason
        ):
            raise ValueError("Inspection relation state must mirror its asset.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionOriginHop:
    """One explicit named re-export hop between a local name and its target."""

    import_target_module_path: str
    import_exported_name: str
    import_module_statement_position: int
    import_item_position: int
    facade_module_path: str
    facade_exposed_name: str
    facade_origin: ProjectModuleExportEntryOrigin
    target_identity: ProjectNominalDeclarationIdentity

    def __post_init__(self) -> None:
        """Require exact hop identities and non-negative source positions."""

        _require_text(self.import_target_module_path, "Inspection hop import target")
        _require_text(self.import_exported_name, "Inspection hop exported name")
        _require_position(self.import_module_statement_position, "hop statement")
        _require_position(self.import_item_position, "hop item")
        _require_text(self.facade_module_path, "Inspection hop facade module")
        _require_text(self.facade_exposed_name, "Inspection hop facade name")
        if type(self.facade_origin) is not ProjectModuleExportEntryOrigin:
            raise TypeError("Inspection hop requires an exact facade origin.")
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Inspection hop requires a nominal target identity.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionOrigin:
    """One inspected local lookup name and the nominal declaration it owns."""

    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    local_name: str
    binding: ProjectInspectionBinding
    target_module_path: str
    target_declaration_position: int
    target_declared_name: str
    hops: tuple[ProjectInspectionOriginHop, ...] = ()
    path: ProjectModuleOriginPath = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Reject an inspected origin detached from its exact Slice 11 path."""

        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Inspection origin requires an exact namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Inspection origin requires an exact declaration kind.")
        _require_text(self.local_name, "Inspection origin local name")
        if type(self.binding) is not ProjectInspectionBinding:
            raise TypeError("Inspection origin requires an exact binding kind.")
        _require_text(self.target_module_path, "Inspection origin target module path")
        _require_position(self.target_declaration_position, "inspection origin target")
        _require_text(self.target_declared_name, "Inspection origin target name")
        _require_tuple(
            self.hops,
            ProjectInspectionOriginHop,
            "Inspection origin hops",
        )
        if type(self.path) is not ProjectModuleOriginPath:
            raise TypeError("Inspection origin requires an exact Slice 11 path.")
        expected_binding = (
            ProjectInspectionBinding.IMPORTED_BINDING
            if self.path.import_occurrence is not None
            else ProjectInspectionBinding.LOCAL_DECLARATION
        )
        target = self.path.target_occurrence
        if (
            self.namespace is not self.path.namespace
            or self.declaration_kind is not self.path.declaration_kind
            or self.local_name != self.path.local_name
            or self.binding is not expected_binding
            or self.target_module_path != target.identity.module_path
            or self.target_declaration_position != target.declaration_position
            or self.target_declared_name != target.identity.declared_name
            or len(self.hops) != len(self.path.hops)
        ):
            raise ValueError("Inspection origin must mirror its exact Slice 11 path.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionDependency:
    """One inspected reference-to-target dependency fact."""

    kind: ProjectModuleDependencyKind
    reference_owner_declaration_position: int
    reference_role: ProjectModuleReferenceRole
    reference_member_position: int
    target_declaration: ProjectDeclarationOccurrenceIdentity | None = None
    target_row_field: ProjectModuleRowFieldIdentity | None = None
    fact: ProjectModuleDependencyFact = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Reject an inspected dependency detached from its exact Slice 11 fact."""

        if type(self.kind) is not ProjectModuleDependencyKind:
            raise TypeError("Inspection dependency requires an exact kind.")
        _require_position(
            self.reference_owner_declaration_position,
            "inspection dependency owner",
        )
        if type(self.reference_role) is not ProjectModuleReferenceRole:
            raise TypeError("Inspection dependency requires an exact reference role.")
        _require_position(
            self.reference_member_position,
            "inspection dependency member",
        )
        if self.target_declaration is not None and (
            type(self.target_declaration) is not ProjectDeclarationOccurrenceIdentity
        ):
            raise TypeError("Inspection dependency declaration target must be exact.")
        if self.target_row_field is not None and (
            type(self.target_row_field) is not ProjectModuleRowFieldIdentity
        ):
            raise TypeError("Inspection dependency row-field target must be exact.")
        if self.target_declaration is not None and self.target_row_field is not None:
            raise ValueError("Inspection dependency carries at most one target kind.")
        if type(self.fact) is not ProjectModuleDependencyFact:
            raise TypeError("Inspection dependency requires an exact Slice 11 fact.")
        reference = self.fact.reference
        if (
            self.kind is not self.fact.kind
            or self.target_declaration is not self.fact.target_declaration
            or self.target_row_field is not self.fact.target_row_field
            or self.reference_role is not reference.role
            or self.reference_member_position != reference.member_position
            or self.reference_owner_declaration_position
            != reference.owner.declaration_position
        ):
            raise ValueError("Inspection dependency must mirror its exact fact.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionLineageHop:
    """One inspected direct or renamed row-lineage hop."""

    projection_kind: ProjectModuleProjectionKind
    output_field_name: str
    upstream_field_name: str

    def __post_init__(self) -> None:
        """Require an exact projection kind and both field names."""

        if type(self.projection_kind) is not ProjectModuleProjectionKind:
            raise TypeError("Inspection lineage hop requires an exact projection kind.")
        _require_text(self.output_field_name, "Inspection lineage output field")
        _require_text(self.upstream_field_name, "Inspection lineage upstream field")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionLineagePath:
    """One inspected identity-distinct lineage path to one root field."""

    root_module_path: str
    root_owner_declaration_position: int
    root_field_position: int
    root_field_name: str
    hops: tuple[ProjectInspectionLineageHop, ...] = ()

    def __post_init__(self) -> None:
        """Require an exact root field identity and an ordered hop tuple."""

        _require_text(self.root_module_path, "Inspection lineage root module path")
        _require_position(
            self.root_owner_declaration_position,
            "inspection lineage root owner",
        )
        _require_position(self.root_field_position, "inspection lineage root field")
        _require_text(self.root_field_name, "Inspection lineage root field name")
        _require_tuple(
            self.hops,
            ProjectInspectionLineageHop,
            "Inspection lineage hops",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionFieldLineage:
    """One inspected output field and every identity-distinct path it retains."""

    kind: ProjectModuleRowFieldKind
    field_position: int
    name: str
    paths: tuple[ProjectInspectionLineagePath, ...] = ()

    def __post_init__(self) -> None:
        """Require an exact field identity and an ordered path tuple."""

        if type(self.kind) is not ProjectModuleRowFieldKind:
            raise TypeError("Inspection field lineage requires an exact field kind.")
        _require_position(self.field_position, "inspection field lineage")
        _require_text(self.name, "Inspection field lineage name")
        _require_tuple(
            self.paths,
            ProjectInspectionLineagePath,
            "Inspection field lineage paths",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionRowLineage:
    """One inspected relation lineage with its availability state."""

    owner_declaration_position: int
    status: ProjectRelationRowSchemaStatus
    reason: ProjectRelationRowSchemaReason
    fields: tuple[ProjectInspectionFieldLineage, ...] = ()
    lineage: ProjectModuleRelationLineage = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject an inspected lineage detached from its exact Slice 11 lineage."""

        _require_position(self.owner_declaration_position, "inspection row lineage")
        if type(self.status) is not ProjectRelationRowSchemaStatus:
            raise TypeError("Inspection row lineage requires an exact status.")
        if type(self.reason) is not ProjectRelationRowSchemaReason:
            raise TypeError("Inspection row lineage requires an exact reason.")
        _require_tuple(
            self.fields,
            ProjectInspectionFieldLineage,
            "Inspection row lineage fields",
        )
        if type(self.lineage) is not ProjectModuleRelationLineage:
            raise TypeError("Inspection row lineage requires an exact Slice 11 fact.")
        if (
            self.owner_declaration_position != self.lineage.owner.declaration_position
            or self.status is not self.lineage.status
            or self.reason is not self.lineage.reason
            or len(self.fields) != len(self.lineage.fields)
        ):
            raise ValueError("Inspection row lineage must mirror its exact fact.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionTypeResolution:
    """One inspected resolved type reference and its canonical target."""

    owner_declaration_position: int
    role: ProjectModuleTypeReferenceRole
    member_position: int
    direct_kind: ProjectResolvedTypeKind
    canonical_kind: ProjectResolvedTypeKind
    canonical_name: str
    canonical_target: ProjectNominalDeclarationIdentity | None = None
    alias_chain: tuple[ProjectNominalDeclarationIdentity, ...] = ()
    resolution: ProjectResolvedModuleTypeReference = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject an inspected type resolution detached from its Slice 9 fact."""

        _require_position(self.owner_declaration_position, "inspection type resolution")
        if type(self.role) is not ProjectModuleTypeReferenceRole:
            raise TypeError("Inspection type resolution requires an exact role.")
        _require_position(self.member_position, "inspection type member")
        if type(self.direct_kind) is not ProjectResolvedTypeKind:
            raise TypeError("Inspection type resolution requires a direct kind.")
        if type(self.canonical_kind) is not ProjectResolvedTypeKind:
            raise TypeError("Inspection type resolution requires a canonical kind.")
        _require_text(self.canonical_name, "Inspection canonical type name")
        if self.canonical_target is not None and (
            type(self.canonical_target) is not ProjectNominalDeclarationIdentity
        ):
            raise TypeError("Inspection canonical target must be a nominal identity.")
        _require_tuple(
            self.alias_chain,
            ProjectNominalDeclarationIdentity,
            "Inspection type alias chain",
        )
        if type(self.resolution) is not ProjectResolvedModuleTypeReference:
            raise TypeError("Inspection type resolution requires a Slice 9 fact.")
        reference = self.resolution.reference
        if (
            self.owner_declaration_position != reference.owner.declaration_position
            or self.role is not reference.role
            or self.member_position != reference.member_position
            or self.direct_kind is not self.resolution.direct_kind
            or self.canonical_kind is not self.resolution.canonical_kind
            or self.canonical_name != self.resolution.canonical_name
            or self.canonical_target is not self.resolution.canonical_target_identity
            or self.alias_chain is not self.resolution.alias_chain
        ):
            raise ValueError("Inspection type resolution must mirror its exact fact.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionSourceShapeResolution:
    """One inspected source declaration resolved to its shape declaration."""

    owner_declaration_position: int
    target_identity: ProjectNominalDeclarationIdentity
    resolution: ProjectResolvedModuleSourceShapeReference = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject an inspected source resolution detached from its Slice 9 fact."""

        _require_position(
            self.owner_declaration_position,
            "inspection source resolution",
        )
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Inspection source resolution requires a nominal target.")
        if type(self.resolution) is not ProjectResolvedModuleSourceShapeReference:
            raise TypeError("Inspection source resolution requires a Slice 9 fact.")
        if (
            self.owner_declaration_position
            != self.resolution.reference.owner.declaration_position
            or self.target_identity is not self.resolution.target_symbol.target_identity
        ):
            raise ValueError("Inspection source resolution must mirror its fact.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionRelationResolution:
    """One inspected relation reference, its lookup name, and its nominal target."""

    owner_declaration_position: int
    local_name: str
    target_identity: ProjectNominalDeclarationIdentity
    resolution: ProjectResolvedModuleRelationReference = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject an inspected relation resolution detached from its Slice 10 fact."""

        _require_position(
            self.owner_declaration_position,
            "inspection relation resolution",
        )
        _require_text(self.local_name, "Inspection relation lookup name")
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Inspection relation resolution requires a nominal target.")
        if type(self.resolution) is not ProjectResolvedModuleRelationReference:
            raise TypeError("Inspection relation resolution requires a Slice 10 fact.")
        symbol = self.resolution.target_symbol
        if (
            self.owner_declaration_position
            != self.resolution.reference.owner.declaration_position
            or self.local_name != symbol.local_name
            or self.target_identity is not symbol.target_identity
        ):
            raise ValueError("Inspection relation resolution must mirror its fact.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionLetBinding:
    """One inspected let binding ordinal and its value-type availability."""

    binding_ordinal: int
    has_value_type: bool

    def __post_init__(self) -> None:
        """Require an exact ordinal and an exact availability flag."""

        _require_position(self.binding_ordinal, "inspection let binding")
        if type(self.has_value_type) is not bool:
            raise TypeError("Inspection let binding requires an exact value flag.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionSelect:
    """One inspected selected output ordinal and its output name."""

    selected_output_ordinal: int
    output_name: str | None = None

    def __post_init__(self) -> None:
        """Require an exact ordinal and an optional non-empty output name."""

        _require_position(self.selected_output_ordinal, "inspection select")
        _require_optional_text(self.output_name, "Inspection select output name")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionClauseDependency:
    """One inspected clause dependency role, ordinal, and bucket status."""

    role: ProjectModuleFactOccurrenceRole
    source_ordinal: int
    status: ProjectModuleCandidateBucketStatus

    def __post_init__(self) -> None:
        """Require exact clause-dependency facts."""

        if type(self.role) is not ProjectModuleFactOccurrenceRole:
            raise TypeError("Inspection clause dependency requires an exact role.")
        _require_position(self.source_ordinal, "inspection clause dependency")
        if type(self.status) is not ProjectModuleCandidateBucketStatus:
            raise TypeError("Inspection clause dependency requires an exact status.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionWindowOutput:
    """One inspected window output ordinal, name, and bucket status."""

    selected_output_ordinal: int
    output_name: str | None = None
    status: ProjectModuleCandidateBucketStatus

    def __post_init__(self) -> None:
        """Require exact window-output facts."""

        _require_position(self.selected_output_ordinal, "inspection window output")
        _require_optional_text(self.output_name, "Inspection window output name")
        if type(self.status) is not ProjectModuleCandidateBucketStatus:
            raise TypeError("Inspection window output requires an exact status.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionSemanticFacts:
    """One inspected relation's preserved semantic facts."""

    owner_declaration_position: int
    status: ProjectRelationRowSchemaStatus
    reason: ProjectRelationRowSchemaReason
    let_bindings: tuple[ProjectInspectionLetBinding, ...] = ()
    selects: tuple[ProjectInspectionSelect, ...] = ()
    clause_dependencies: tuple[ProjectInspectionClauseDependency, ...] = ()
    window_outputs: tuple[ProjectInspectionWindowOutput, ...] = ()
    facts: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject inspected semantic facts detached from their Slice 12 fact."""

        _require_position(
            self.owner_declaration_position,
            "inspection semantic facts",
        )
        if type(self.status) is not ProjectRelationRowSchemaStatus:
            raise TypeError("Inspection semantic facts require an exact status.")
        if type(self.reason) is not ProjectRelationRowSchemaReason:
            raise TypeError("Inspection semantic facts require an exact reason.")
        _require_tuple(
            self.let_bindings,
            ProjectInspectionLetBinding,
            "Inspection let bindings",
        )
        _require_tuple(self.selects, ProjectInspectionSelect, "Inspection selects")
        _require_tuple(
            self.clause_dependencies,
            ProjectInspectionClauseDependency,
            "Inspection clause dependencies",
        )
        _require_tuple(
            self.window_outputs,
            ProjectInspectionWindowOutput,
            "Inspection window outputs",
        )
        if type(self.facts) is not ProjectModuleRelationSemanticFacts:
            raise TypeError("Inspection semantic facts require a Slice 12 fact.")
        if (
            self.owner_declaration_position != self.facts.owner.declaration_position
            or self.status is not self.facts.state.status
            or self.reason is not self.facts.state.reason
            or len(self.let_bindings) != len(self.facts.let_bindings)
            or len(self.selects) != len(self.facts.select_facts)
            or len(self.clause_dependencies) != len(self.facts.clause_dependencies)
            or len(self.window_outputs) != len(self.facts.window_outputs)
        ):
            raise ValueError("Inspection semantic facts must mirror their exact fact.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectInspectionIssue:
    """One inspected structural issue status, without any rendered message."""

    family: ProjectInspectionIssueFamily
    status: str
    local_name: str | None = None

    def __post_init__(self) -> None:
        """Require a status inside the exact family vocabulary."""

        if type(self.family) is not ProjectInspectionIssueFamily:
            raise TypeError("Inspection issue requires an exact family.")
        _require_text(self.status, "Inspection issue status")
        if self.status not in _INSPECTION_ISSUE_STATUS_VALUES[self.family]:
            raise ValueError("Inspection issue status must belong to its family.")
        _require_optional_text(self.local_name, "Inspection issue local name")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleInspectionRecord:
    """One complete inspected module in exact selected-input order."""

    module: ProjectModuleIdentity
    position: int
    digest: ProjectLayeredSourceDigestIdentity
    readiness: ProjectInspectionReadiness
    graph: ProjectInspectionGraph
    imports: tuple[ProjectInspectionImport, ...] = ()
    exports: tuple[ProjectInspectionExport, ...] = ()
    declarations: tuple[ProjectInspectionDeclaration, ...] = ()
    origins: tuple[ProjectInspectionOrigin, ...] = ()
    dependencies: tuple[ProjectInspectionDependency, ...] = ()
    row_lineage: tuple[ProjectInspectionRowLineage, ...] = ()
    type_resolutions: tuple[ProjectInspectionTypeResolution, ...] = ()
    source_shape_resolutions: tuple[ProjectInspectionSourceShapeResolution, ...] = ()
    relation_resolutions: tuple[ProjectInspectionRelationResolution, ...] = ()
    semantic_facts: tuple[ProjectInspectionSemanticFacts, ...] = ()
    issues: tuple[ProjectInspectionIssue, ...] = ()
    asset: ProjectLayeredModuleAsset = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Reject an inspected module detached from its exact Slice 13 asset."""

        if type(self.module) is not ProjectModuleIdentity:
            raise TypeError("Inspected module requires a module identity.")
        _require_position(self.position, "inspected module")
        if type(self.digest) is not ProjectLayeredSourceDigestIdentity:
            raise TypeError("Inspected module requires a source digest identity.")
        if type(self.readiness) is not ProjectInspectionReadiness:
            raise TypeError("Inspected module requires an inspection readiness.")
        if type(self.graph) is not ProjectInspectionGraph:
            raise TypeError("Inspected module requires an inspection graph.")
        _require_tuple(self.imports, ProjectInspectionImport, "Inspected imports")
        _require_tuple(self.exports, ProjectInspectionExport, "Inspected exports")
        _require_tuple(
            self.declarations,
            ProjectInspectionDeclaration,
            "Inspected declarations",
        )
        _require_tuple(self.origins, ProjectInspectionOrigin, "Inspected origins")
        _require_tuple(
            self.dependencies,
            ProjectInspectionDependency,
            "Inspected dependencies",
        )
        _require_tuple(
            self.row_lineage,
            ProjectInspectionRowLineage,
            "Inspected row lineage",
        )
        _require_tuple(
            self.type_resolutions,
            ProjectInspectionTypeResolution,
            "Inspected type resolutions",
        )
        _require_tuple(
            self.source_shape_resolutions,
            ProjectInspectionSourceShapeResolution,
            "Inspected source resolutions",
        )
        _require_tuple(
            self.relation_resolutions,
            ProjectInspectionRelationResolution,
            "Inspected relation resolutions",
        )
        _require_tuple(
            self.semantic_facts,
            ProjectInspectionSemanticFacts,
            "Inspected semantic facts",
        )
        _require_tuple(self.issues, ProjectInspectionIssue, "Inspected issues")
        if type(self.asset) is not ProjectLayeredModuleAsset:
            raise TypeError("Inspected module requires an exact Slice 13 asset.")
        if (
            self.module is not self.asset.module
            or self.position != self.asset.position
            or self.digest is not self.asset.digest
            or self.readiness.fact is not self.asset.readiness
        ):
            raise ValueError("Inspected module must mirror its exact Slice 13 asset.")
        if any(
            declaration.identity.module_path != self.module.path
            for declaration in self.declarations
        ):
            raise ValueError("Inspected declarations must belong to their module.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleInspection:
    """The one canonical private inspection projection of a schema-v2 project."""

    format: ProjectInspectionFormat
    owner: ProjectLayeredOwnerIdentity
    modules: tuple[ProjectModuleInspectionRecord, ...] = ()

    def __post_init__(self) -> None:
        """Require the exact private format, project owner, and module order."""

        if self.format is not ProjectInspectionFormat.MODULE_INSPECTION_V1:
            raise ValueError("Inspection requires the exact private format marker.")
        if type(self.owner) is not ProjectLayeredOwnerIdentity:
            raise TypeError("Inspection requires a project owner identity.")
        _require_tuple(
            self.modules,
            ProjectModuleInspectionRecord,
            "Inspection modules",
        )
        if any(
            record.position != position for position, record in enumerate(self.modules)
        ):
            raise ValueError("Inspection modules must follow selected-input order.")


@dataclass(frozen=True, slots=True, kw_only=True)
class _ProjectModuleInspectionAuthority:
    """Private exact inspection authority over the ten settled schema-v2 roots.

    The ten retained roots are the only constructor inputs. The canonical
    projection and its canonical serialized payload are derived from them at
    construction, so neither product can be supplied or grafted.
    """

    modules: tuple[ProjectLogicalModule, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    catalogs: ProjectModuleCatalogSet = field(repr=False, compare=False, hash=False)
    exports: ProjectModuleExportSurfaceSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    bindings: ProjectModuleBindingEnvironmentSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    graph: ProjectModuleGraph = field(repr=False, compare=False, hash=False)
    type_source_resolutions: ProjectTypeSourceResolutionSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    relation_resolutions: ProjectModuleRelationResolutionSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    attribution: ProjectModuleAttributionFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    semantic: ProjectModuleSemanticFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    package_identity: ProjectModulePackageNeutralIdentityFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    inspection: ProjectModuleInspection = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    canonical_bytes: bytes = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Validate the whole root set, then derive the projection and payload."""

        _validate_inspection_authority_roots(
            self.modules,
            self.catalogs,
            self.exports,
            self.bindings,
            self.graph,
            self.type_source_resolutions,
            self.relation_resolutions,
            self.attribution,
            self.semantic,
            self.package_identity,
        )
        inspection = _derive_inspection(
            self.modules,
            self.catalogs,
            self.exports,
            self.bindings,
            self.graph,
            self.type_source_resolutions,
            self.relation_resolutions,
            self.attribution,
            self.semantic,
            self.package_identity,
        )
        object.__setattr__(self, "inspection", inspection)
        object.__setattr__(self, "canonical_bytes", _serialize_inspection(inspection))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleInspectionFactSet:
    """Complete private Slice 14 inspection and canonical serialization product."""

    inspection: ProjectModuleInspection
    canonical_bytes: bytes
    authority: _ProjectModuleInspectionAuthority = field(
        repr=False,
        compare=False,
        hash=False,
    )
    _modules_by_path: Mapping[str, tuple[ProjectModuleInspectionRecord, ...]] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    _declarations_by_identity: Mapping[
        ProjectNominalDeclarationIdentity,
        tuple[ProjectInspectionDeclaration, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Require the exact derived projection and the exact derived payload."""

        if type(self.authority) is not _ProjectModuleInspectionAuthority:
            raise TypeError("Inspection fact set requires an exact private authority.")
        if self.inspection is not self.authority.inspection:
            raise ValueError(
                "Inspection fact set must retain the exact derived projection."
            )
        # A forged payload is rejected by object identity rather than by value,
        # because a value-equal payload can be produced from any projection.
        if self.canonical_bytes is not self.authority.canonical_bytes:
            raise ValueError(
                "Inspection fact set must retain the exact derived canonical bytes."
            )

        modules_by_path: dict[str, list[ProjectModuleInspectionRecord]] = {}
        declarations_by_identity: dict[
            ProjectNominalDeclarationIdentity,
            list[ProjectInspectionDeclaration],
        ] = {}
        for record in self.inspection.modules:
            modules_by_path.setdefault(record.module.path, []).append(record)
            for declaration in record.declarations:
                declarations_by_identity.setdefault(declaration.identity, []).append(
                    declaration
                )
        object.__setattr__(
            self,
            "_modules_by_path",
            _frozen_bucket_mapping(modules_by_path),
        )
        object.__setattr__(
            self,
            "_declarations_by_identity",
            _frozen_bucket_mapping(declarations_by_identity),
        )

    def find_module(
        self,
        module: ProjectModuleIdentity,
    ) -> tuple[ProjectModuleInspectionRecord, ...]:
        """Return the complete inspected-module bucket for one exact identity."""

        if type(module) is not ProjectModuleIdentity:
            raise TypeError("Inspection module lookup requires a module identity.")
        return self._modules_by_path.get(module.path, ())

    def find_declaration(
        self,
        identity: ProjectNominalDeclarationIdentity,
    ) -> tuple[ProjectInspectionDeclaration, ...]:
        """Return the complete declaration bucket without selecting a winner."""

        if type(identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Inspection declaration lookup requires an identity.")
        return self._declarations_by_identity.get(identity, ())


def _build_project_module_inspection_fact_set(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
    relation_resolutions: ProjectModuleRelationResolutionSet,
    attribution: ProjectModuleAttributionFactSet,
    semantic: ProjectModuleSemanticFactSet,
    package_identity: ProjectModulePackageNeutralIdentityFactSet,
) -> ProjectModuleInspectionFactSet:
    """Build the pure Slice 14 inspection product from ten exact shared roots."""

    authority = _ProjectModuleInspectionAuthority(
        modules=modules,
        catalogs=catalogs,
        exports=exports,
        bindings=bindings,
        graph=graph,
        type_source_resolutions=type_source_resolutions,
        relation_resolutions=relation_resolutions,
        attribution=attribution,
        semantic=semantic,
        package_identity=package_identity,
    )
    return ProjectModuleInspectionFactSet(
        inspection=authority.inspection,
        canonical_bytes=authority.canonical_bytes,
        authority=authority,
    )


def _validate_inspection_authority_roots(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
    relation_resolutions: ProjectModuleRelationResolutionSet,
    attribution: ProjectModuleAttributionFactSet,
    semantic: ProjectModuleSemanticFactSet,
    package_identity: ProjectModulePackageNeutralIdentityFactSet,
) -> None:
    """Prove the ten settled roots are one aligned exact authority root set."""

    _require_tuple(modules, ProjectLogicalModule, "Inspection authority modules")
    if type(catalogs) is not ProjectModuleCatalogSet:
        raise TypeError("Inspection authority requires exact module catalogs.")
    if type(exports) is not ProjectModuleExportSurfaceSet:
        raise TypeError("Inspection authority requires an exact export surface set.")
    if type(bindings) is not ProjectModuleBindingEnvironmentSet:
        raise TypeError("Inspection authority requires an exact binding set.")
    if type(graph) is not ProjectModuleGraph:
        raise TypeError("Inspection authority requires an exact module graph.")
    if type(type_source_resolutions) is not ProjectTypeSourceResolutionSet:
        raise TypeError("Inspection authority requires an exact Slice 9 set.")
    if type(relation_resolutions) is not ProjectModuleRelationResolutionSet:
        raise TypeError("Inspection authority requires an exact Slice 10 set.")
    if type(attribution) is not ProjectModuleAttributionFactSet:
        raise TypeError("Inspection authority requires an exact Slice 11 fact set.")
    if type(semantic) is not ProjectModuleSemanticFactSet:
        raise TypeError("Inspection authority requires an exact Slice 12 fact set.")
    if type(package_identity) is not ProjectModulePackageNeutralIdentityFactSet:
        raise TypeError("Inspection authority requires an exact Slice 13 fact set.")

    layered_authority = package_identity.authority
    if (
        layered_authority.modules is not modules
        or layered_authority.catalogs is not catalogs
        or layered_authority.attribution is not attribution
        or layered_authority.semantic is not semantic
    ):
        raise ValueError(
            "Inspection authority requires the exact Slice 13 module, catalog, and "
            "sidecar roots."
        )

    attribution_authority = attribution._authority
    if (
        attribution_authority.modules is not modules
        or attribution_authority.catalogs is not catalogs
        or attribution_authority.exports is not exports
        or attribution_authority.graph is not graph
        or attribution_authority.type_source_resolutions is not type_source_resolutions
        or attribution_authority.relation_resolutions is not relation_resolutions
        or attribution_authority.binding_authority is not bindings
        or attribution.binding_authority is not bindings
    ):
        raise ValueError("Inspection authority requires the exact Slice 11 roots.")

    semantic_authority = semantic.authority
    if (
        semantic_authority.modules is not modules
        or semantic_authority.catalogs is not catalogs
        or semantic_authority.relation_resolutions is not relation_resolutions
    ):
        raise ValueError("Inspection authority requires the exact Slice 12 roots.")

    if graph.binding_authority is not bindings:
        raise ValueError("Inspection authority requires the exact Slice 8 root.")

    if (
        semantic.dependency_order is not relation_resolutions.dependency_order
        or semantic.issues is not relation_resolutions.issues
    ):
        raise ValueError(
            "Inspection authority requires the exact shared dependency order and "
            "issues."
        )
    relation_environments = relation_resolutions.environments
    if len(semantic.environments) != len(relation_environments) or any(
        semantic_environment.resolution_environment is not relation_environment
        for semantic_environment, relation_environment in zip(
            semantic.environments,
            relation_environments,
            strict=True,
        )
    ):
        raise ValueError(
            "Inspection authority requires the exact Slice 10 environments."
        )

    module_count = len(modules)
    if (
        len(catalogs.catalogs) != module_count
        or len(exports.surfaces) != module_count
        or len(bindings.environments) != module_count
        or len(graph.vertices) != module_count
        or len(package_identity.module_assets) != module_count
    ):
        raise ValueError("Inspection authority requires one exact root per module.")
    for position, module in enumerate(modules):
        vertex = graph.vertices[position]
        asset = package_identity.module_assets[position]
        if (
            catalogs.catalogs[position].module is not module
            or exports.surfaces[position].module is not module
            or bindings.environments[position].module is not module
            or vertex.module is not module
            or vertex.position != position
            or asset.module != module.identity
            or asset.position != position
        ):
            raise ValueError(
                "Inspection authority requires aligned module, surface, graph, and "
                "asset roots."
            )

    expected_declarations = tuple(
        occurrence
        for catalog in catalogs.catalogs
        for occurrence in catalog.occurrences
    )
    declaration_assets = package_identity.declaration_assets
    if len(declaration_assets) != len(expected_declarations) or any(
        asset.occurrence is not occurrence
        for asset, occurrence in zip(
            declaration_assets,
            expected_declarations,
            strict=True,
        )
    ):
        raise ValueError(
            "Inspection authority requires the complete ordered Slice 13 declaration "
            "assets."
        )

    dependency_paths = tuple(identity.path for identity in semantic.dependency_order)
    if any(
        environment.module.path != path
        for environment, path in zip(
            relation_environments,
            dependency_paths,
            strict=True,
        )
    ):
        raise ValueError("Inspection authority requires exact Slice 10 module order.")
    type_source_paths = tuple(
        identity.path for identity in type_source_resolutions.dependency_order
    )
    if len(type_source_resolutions.environments) != len(type_source_paths) or any(
        environment.module.path != path
        for environment, path in zip(
            type_source_resolutions.environments,
            type_source_paths,
            strict=True,
        )
    ):
        raise ValueError("Inspection authority requires exact Slice 9 module order.")


def _derive_inspection(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
    relation_resolutions: ProjectModuleRelationResolutionSet,
    attribution: ProjectModuleAttributionFactSet,
    semantic: ProjectModuleSemanticFactSet,
    package_identity: ProjectModulePackageNeutralIdentityFactSet,
) -> ProjectModuleInspection:
    """Derive the one canonical inspection projection from the exact roots."""

    component_by_path: dict[str, tuple[tuple[ProjectModuleIdentity, ...], bool]] = {}
    for component in graph.components:
        members = tuple(member.identity for member in component.members)
        is_cyclic = component.is_cyclic
        for member in component.members:
            component_by_path[member.identity.path] = (members, is_cyclic)

    evidence_by_path: dict[str, list[ProjectInspectionImportEvidence]] = {}
    for evidence_edge in graph.evidence_edges:
        evidence_by_path.setdefault(evidence_edge.origin.identity.path, []).append(
            ProjectInspectionImportEvidence(
                target=evidence_edge.target.identity,
                module_statement_position=(
                    evidence_edge.request.module_statement_position
                ),
                item_position=evidence_edge.request.item_position,
            )
        )

    declaration_assets_by_path: dict[str, list[ProjectLayeredDeclarationAsset]] = {}
    for declaration_asset in package_identity.declaration_assets:
        declaration_assets_by_path.setdefault(
            declaration_asset.identity.module_path, []
        ).append(declaration_asset)
    occurrence_positions = _derive_occurrence_positions(
        package_identity.declaration_assets
    )

    origins_by_path: dict[str, list[ProjectModuleOriginPath]] = {}
    for origin_path in attribution.origins:
        origins_by_path.setdefault(origin_path.owning_module_path, []).append(
            origin_path
        )
    dependencies_by_path: dict[str, list[ProjectModuleDependencyFact]] = {}
    for dependency_fact in attribution.dependencies:
        dependencies_by_path.setdefault(
            dependency_fact.reference.owner.identity.module_path, []
        ).append(dependency_fact)
    lineages_by_path: dict[str, list[ProjectModuleRelationLineage]] = {}
    for relation_lineage in attribution.row_lineages:
        lineages_by_path.setdefault(
            relation_lineage.owner.identity.module_path, []
        ).append(relation_lineage)

    graph_issues_by_path: dict[str, list[ProjectInspectionIssue]] = {}
    for graph_issue in graph.issues:
        graph_issues_by_path.setdefault(
            graph_issue.owning_vertex.identity.path, []
        ).append(
            ProjectInspectionIssue(
                family=ProjectInspectionIssueFamily.GRAPH,
                status=graph_issue.status.value,
            )
        )
    type_source_issues_by_path: dict[str, list[ProjectInspectionIssue]] = {}
    for type_source_issue in type_source_resolutions.issues:
        type_source_issues_by_path.setdefault(
            type_source_issue.owning_module_path, []
        ).append(
            ProjectInspectionIssue(
                family=ProjectInspectionIssueFamily.TYPE_SOURCE,
                status=type_source_issue.status.value,
                local_name=type_source_issue.local_name,
            )
        )
    relation_issues_by_path: dict[str, list[ProjectInspectionIssue]] = {}
    for relation_issue in relation_resolutions.issues:
        relation_issues_by_path.setdefault(
            relation_issue.owning_module_path, []
        ).append(
            ProjectInspectionIssue(
                family=ProjectInspectionIssueFamily.RELATION,
                status=relation_issue.status.value,
                local_name=relation_issue.local_name,
            )
        )

    records: list[ProjectModuleInspectionRecord] = []
    for position, module in enumerate(modules):
        path = module.path
        asset = package_identity.module_assets[position]
        component_members, component_is_cyclic = component_by_path[path]
        vertex = graph.vertices[position]
        records.append(
            ProjectModuleInspectionRecord(
                module=asset.module,
                position=position,
                digest=asset.digest,
                readiness=_derive_readiness(asset.readiness),
                graph=ProjectInspectionGraph(
                    component_members=component_members,
                    component_is_cyclic=component_is_cyclic,
                    dependency_targets=tuple(
                        edge.target.identity for edge in graph.outgoing(vertex)
                    ),
                    import_evidence=tuple(evidence_by_path.get(path, ())),
                ),
                imports=_derive_imports(bindings.environments[position]),
                exports=_derive_exports(exports.surfaces[position]),
                declarations=_derive_declarations(
                    declaration_assets_by_path.get(path, ()),
                    occurrence_positions,
                ),
                origins=_derive_origins(origins_by_path.get(path, ())),
                dependencies=_derive_dependencies(dependencies_by_path.get(path, ())),
                row_lineage=_derive_row_lineage(lineages_by_path.get(path, ())),
                type_resolutions=_derive_type_resolutions(
                    type_source_resolutions,
                    path,
                ),
                source_shape_resolutions=_derive_source_shape_resolutions(
                    type_source_resolutions,
                    path,
                ),
                relation_resolutions=_derive_relation_resolutions(
                    relation_resolutions,
                    path,
                ),
                semantic_facts=_derive_semantic_facts(semantic, path),
                issues=(
                    *graph_issues_by_path.get(path, ()),
                    *type_source_issues_by_path.get(path, ()),
                    *relation_issues_by_path.get(path, ()),
                ),
                asset=asset,
            )
        )

    return ProjectModuleInspection(
        format=ProjectInspectionFormat.MODULE_INSPECTION_V1,
        owner=package_identity.owner,
        modules=tuple(records),
    )


def _derive_readiness(
    readiness: ProjectLayeredLoaderReadinessFact,
) -> ProjectInspectionReadiness:
    """Project one Slice 13 readiness fact and its complete cycle evidence."""

    cycles: list[ProjectInspectionModuleCycle] = []
    for issue in readiness.blocking_issues:
        cycle = issue.module_cycle
        if cycle is None:
            raise ValueError("Blocking readiness evidence requires a retained cycle.")
        cycles.append(
            ProjectInspectionModuleCycle(
                members=tuple(member.identity for member in cycle.component.members),
            )
        )
    return ProjectInspectionReadiness(
        status=readiness.status,
        reason=readiness.reason,
        cycles=tuple(cycles),
        fact=readiness,
    )


def _derive_imports(
    environment: ProjectModuleBindingEnvironment,
) -> tuple[ProjectInspectionImport, ...]:
    """Project one module's import requests, aliases, targets, and issues."""

    resolved_by_request: dict[int, ProjectNominalDeclarationIdentity] = {
        id(binding.request): binding.target_identity for binding in environment.bindings
    }
    issues_by_request: dict[int, list[ProjectModuleBindingIssueStatus]] = {}
    for issue in environment.issues:
        issues_by_request.setdefault(id(issue.request), []).append(issue.status)
    return tuple(
        ProjectInspectionImport(
            local_name=request.identity.local_binding_name,
            namespace=request.identity.namespace,
            declaration_kind=request.identity.declaration_kind,
            target_module_path=request.target_module_path,
            exported_name=request.exported_name,
            module_statement_position=request.module_statement_position,
            item_position=request.item_position,
            resolved_target=resolved_by_request.get(id(request)),
            issue_statuses=tuple(issues_by_request.get(id(request), ())),
            request=request,
        )
        for request in environment.requests
    )


def _derive_exports(
    surface: ProjectModuleExportSurface,
) -> tuple[ProjectInspectionExport, ...]:
    """Project one module's export requests, facade entries, and issues."""

    entries_by_request = {id(entry.request): entry for entry in surface.entries}
    issues_by_request: dict[int, list[ProjectModuleExportIssueStatus]] = {}
    for issue in surface.issues:
        issues_by_request.setdefault(id(issue.request), []).append(issue.status)
    projected: list[ProjectInspectionExport] = []
    for request in surface.requests:
        entry = entries_by_request.get(id(request))
        projected.append(
            ProjectInspectionExport(
                local_name=request.local_name,
                namespace=request.namespace,
                declaration_kind=request.declaration_kind,
                module_statement_position=request.module_statement_position,
                item_position=request.item_position,
                exposed_name=None if entry is None else entry.exposed_name,
                entry_origin=None if entry is None else entry.origin,
                target_identity=None if entry is None else entry.target_identity,
                issue_statuses=tuple(issues_by_request.get(id(request), ())),
                request=request,
            )
        )
    return tuple(projected)


def _derive_occurrence_positions(
    declaration_assets: Sequence[ProjectLayeredDeclarationAsset],
) -> Mapping[int, int]:
    """Index every occurrence inside its own shared identity bucket once.

    Every occurrence of one nominal identity retains the exact same bucket
    object, so each distinct bucket is walked exactly once. Re-scanning the
    bucket per declaration would cost one comparison for every pair of
    same-identity declarations, which a legitimate ambiguous project can make
    arbitrarily large.
    """

    positions: dict[int, int] = {}
    indexed_buckets: dict[int, None] = {}
    for declaration_asset in declaration_assets:
        bucket = declaration_asset.identity_occurrences
        bucket_key = id(bucket)
        if bucket_key in indexed_buckets:
            continue
        indexed_buckets[bucket_key] = None
        for position, occurrence in enumerate(bucket):
            positions[id(occurrence)] = position
    return MappingProxyType(positions)


def _derive_declarations(
    declaration_assets: Sequence[ProjectLayeredDeclarationAsset],
    occurrence_positions: Mapping[int, int],
) -> tuple[ProjectInspectionDeclaration, ...]:
    """Project one module's declarations, availability, and row fields."""

    projected: list[ProjectInspectionDeclaration] = []
    for declaration_asset in declaration_assets:
        occurrences = declaration_asset.identity_occurrences
        occurrence_index = occurrence_positions.get(
            id(declaration_asset.occurrence), -1
        )
        if occurrence_index < 0:
            raise ValueError("Inspected declaration must appear in its own bucket.")
        state = declaration_asset.relation_state
        schema = None if state is None else state.schema
        projected.append(
            ProjectInspectionDeclaration(
                owner=declaration_asset.owner,
                identity=declaration_asset.identity,
                declaration_position=declaration_asset.declaration_position,
                availability=declaration_asset.availability,
                occurrence_count=len(occurrences),
                occurrence_index=occurrence_index,
                relation_status=None if state is None else state.status,
                relation_reason=None if state is None else state.reason,
                row_fields=()
                if schema is None
                else tuple(
                    ProjectInspectionRowField(
                        name=row_field.name,
                        nullability=row_field.nullability,
                        result_role=row_field.result_role,
                    )
                    for row_field in schema.fields.values()
                ),
                asset=declaration_asset,
            )
        )
    return tuple(projected)


def _derive_origins(
    origin_paths: Sequence[ProjectModuleOriginPath],
) -> tuple[ProjectInspectionOrigin, ...]:
    """Project one module's local and imported origin paths with exact hops."""

    projected: list[ProjectInspectionOrigin] = []
    for origin_path in origin_paths:
        target = origin_path.target_occurrence
        projected.append(
            ProjectInspectionOrigin(
                namespace=origin_path.namespace,
                declaration_kind=origin_path.declaration_kind,
                local_name=origin_path.local_name,
                binding=(
                    ProjectInspectionBinding.IMPORTED_BINDING
                    if origin_path.import_occurrence is not None
                    else ProjectInspectionBinding.LOCAL_DECLARATION
                ),
                target_module_path=target.identity.module_path,
                target_declaration_position=target.declaration_position,
                target_declared_name=target.identity.declared_name,
                hops=tuple(
                    ProjectInspectionOriginHop(
                        import_target_module_path=(
                            hop.import_occurrence.target_module_path
                        ),
                        import_exported_name=hop.import_occurrence.exported_name,
                        import_module_statement_position=(
                            hop.import_occurrence.module_statement_position
                        ),
                        import_item_position=hop.import_occurrence.item_position,
                        facade_module_path=hop.facade_occurrence.owning_module_path,
                        facade_exposed_name=hop.facade_occurrence.exposed_name,
                        facade_origin=hop.facade_origin,
                        target_identity=hop.target_identity,
                    )
                    for hop in origin_path.hops
                ),
                path=origin_path,
            )
        )
    return tuple(projected)


def _derive_dependencies(
    dependency_facts: Sequence[ProjectModuleDependencyFact],
) -> tuple[ProjectInspectionDependency, ...]:
    """Project one module's reference-to-target dependency facts."""

    projected: list[ProjectInspectionDependency] = []
    for dependency_fact in dependency_facts:
        reference = dependency_fact.reference
        projected.append(
            ProjectInspectionDependency(
                kind=dependency_fact.kind,
                reference_owner_declaration_position=(
                    reference.owner.declaration_position
                ),
                reference_role=reference.role,
                reference_member_position=reference.member_position,
                target_declaration=dependency_fact.target_declaration,
                target_row_field=dependency_fact.target_row_field,
                fact=dependency_fact,
            )
        )
    return tuple(projected)


def _derive_row_lineage(
    relation_lineages: Sequence[ProjectModuleRelationLineage],
) -> tuple[ProjectInspectionRowLineage, ...]:
    """Project one module's complete relation row lineage."""

    projected: list[ProjectInspectionRowLineage] = []
    for relation_lineage in relation_lineages:
        projected.append(
            ProjectInspectionRowLineage(
                owner_declaration_position=(
                    relation_lineage.owner.declaration_position
                ),
                status=relation_lineage.status,
                reason=relation_lineage.reason,
                fields=tuple(
                    ProjectInspectionFieldLineage(
                        kind=field_lineage.field.kind,
                        field_position=field_lineage.field.field_position,
                        name=field_lineage.field.name,
                        paths=tuple(
                            ProjectInspectionLineagePath(
                                root_module_path=(
                                    lineage_path.root_field.owner.identity.module_path
                                ),
                                root_owner_declaration_position=(
                                    lineage_path.root_field.owner.declaration_position
                                ),
                                root_field_position=(
                                    lineage_path.root_field.field_position
                                ),
                                root_field_name=lineage_path.root_field.name,
                                hops=tuple(
                                    ProjectInspectionLineageHop(
                                        projection_kind=hop.projection_kind,
                                        output_field_name=hop.output_field.name,
                                        upstream_field_name=hop.upstream_field.name,
                                    )
                                    for hop in lineage_path.hops
                                ),
                            )
                            for lineage_path in field_lineage.paths
                        ),
                    )
                    for field_lineage in relation_lineage.fields
                ),
                lineage=relation_lineage,
            )
        )
    return tuple(projected)


def _derive_type_resolutions(
    type_source_resolutions: ProjectTypeSourceResolutionSet,
    module_path: str,
) -> tuple[ProjectInspectionTypeResolution, ...]:
    """Project one module's resolved type references in exact authority order."""

    environments = type_source_resolutions.find_module_path(module_path)
    if not environments:
        return ()
    return tuple(
        ProjectInspectionTypeResolution(
            owner_declaration_position=(
                resolution.reference.owner.declaration_position
            ),
            role=resolution.reference.role,
            member_position=resolution.reference.member_position,
            direct_kind=resolution.direct_kind,
            canonical_kind=resolution.canonical_kind,
            canonical_name=resolution.canonical_name,
            canonical_target=resolution.canonical_target_identity,
            alias_chain=resolution.alias_chain,
            resolution=resolution,
        )
        for resolution in environments[0].type_resolutions
    )


def _derive_source_shape_resolutions(
    type_source_resolutions: ProjectTypeSourceResolutionSet,
    module_path: str,
) -> tuple[ProjectInspectionSourceShapeResolution, ...]:
    """Project one module's resolved source shape references."""

    environments = type_source_resolutions.find_module_path(module_path)
    if not environments:
        return ()
    return tuple(
        ProjectInspectionSourceShapeResolution(
            owner_declaration_position=(
                resolution.reference.owner.declaration_position
            ),
            target_identity=resolution.target_symbol.target_identity,
            resolution=resolution,
        )
        for resolution in environments[0].source_shape_resolutions
    )


def _derive_relation_resolutions(
    relation_resolutions: ProjectModuleRelationResolutionSet,
    module_path: str,
) -> tuple[ProjectInspectionRelationResolution, ...]:
    """Project one module's resolved relation references."""

    environments = relation_resolutions.find_module_path(module_path)
    if not environments:
        return ()
    return tuple(
        ProjectInspectionRelationResolution(
            owner_declaration_position=(
                resolution.reference.owner.declaration_position
            ),
            local_name=resolution.target_symbol.local_name,
            target_identity=resolution.target_symbol.target_identity,
            resolution=resolution,
        )
        for resolution in environments[0].resolutions
    )


def _derive_semantic_facts(
    semantic: ProjectModuleSemanticFactSet,
    module_path: str,
) -> tuple[ProjectInspectionSemanticFacts, ...]:
    """Project one module's preserved semantic facts in exact authority order."""

    environments = semantic.find_module_path(module_path)
    if not environments:
        return ()
    return tuple(
        ProjectInspectionSemanticFacts(
            owner_declaration_position=relation_facts.owner.declaration_position,
            status=relation_facts.state.status,
            reason=relation_facts.state.reason,
            let_bindings=tuple(
                ProjectInspectionLetBinding(
                    binding_ordinal=let_binding.binding_ordinal,
                    has_value_type=let_binding.value_type is not None,
                )
                for let_binding in relation_facts.let_bindings
            ),
            selects=tuple(
                ProjectInspectionSelect(
                    selected_output_ordinal=select_fact.selected_output_ordinal,
                    output_name=select_fact.output_name,
                )
                for select_fact in relation_facts.select_facts
            ),
            clause_dependencies=tuple(
                ProjectInspectionClauseDependency(
                    role=clause_dependency.role,
                    source_ordinal=clause_dependency.source_ordinal,
                    status=clause_dependency.status,
                )
                for clause_dependency in relation_facts.clause_dependencies
            ),
            window_outputs=tuple(
                ProjectInspectionWindowOutput(
                    selected_output_ordinal=window_output.selected_output_ordinal,
                    output_name=window_output.output_name,
                    status=window_output.status,
                )
                for window_output in relation_facts.window_outputs
            ),
            facts=relation_facts,
        )
        for relation_facts in environments[0].relation_facts
    )


def _serialize_inspection(inspection: ProjectModuleInspection) -> bytes:
    """Serialize the canonical projection into one exact private byte string."""

    lines: list[str] = []
    _record(
        lines,
        "inspection",
        ("format", _enumeration(inspection.format)),
        ("modules", _integer(len(inspection.modules))),
    )
    _record(
        lines,
        "owner",
        ("kind", _enumeration(inspection.owner.kind)),
        ("namespace", _text(inspection.owner.namespace)),
        ("name", _text(inspection.owner.name)),
    )
    for record in inspection.modules:
        module = _integer(record.position)
        _record(
            lines, "module", ("module", module), ("path", _text(record.module.path))
        )
        _serialize_digest(lines, module, record)
        _serialize_readiness(lines, module, record)
        _serialize_graph(lines, module, record)
        _serialize_imports(lines, module, record)
        _serialize_exports(lines, module, record)
        _serialize_declarations(lines, module, record)
        _serialize_origins(lines, module, record)
        _serialize_dependencies(lines, module, record)
        _serialize_row_lineage(lines, module, record)
        _serialize_type_resolutions(lines, module, record)
        _serialize_relation_resolutions(lines, module, record)
        _serialize_semantic_facts(lines, module, record)
        _serialize_issues(lines, module, record)
    return ("\n".join(lines) + "\n").encode("utf-8")


def _serialize_digest(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's exact source digest identity."""

    _record(
        lines,
        "digest",
        ("module", module),
        ("algorithm", _enumeration(record.digest.algorithm)),
        ("digest", _text(record.digest.digest)),
        ("byte_count", _integer(record.digest.byte_count)),
    )


def _serialize_readiness(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's loader readiness and its complete cycle evidence."""

    readiness = record.readiness
    _record(
        lines,
        "readiness",
        ("module", module),
        ("status", _enumeration(readiness.status)),
        ("reason", _enumeration(readiness.reason)),
        ("cycles", _integer(len(readiness.cycles))),
    )
    for cycle_ordinal, cycle in enumerate(readiness.cycles):
        cycle_token = _integer(cycle_ordinal)
        _record(
            lines,
            "readiness_cycle",
            ("module", module),
            ("cycle", cycle_token),
            ("members", _integer(len(cycle.members))),
        )
        for member_ordinal, member in enumerate(cycle.members):
            _record(
                lines,
                "readiness_cycle_member",
                ("module", module),
                ("cycle", cycle_token),
                ("member", _integer(member_ordinal)),
                ("path", _text(member.path)),
            )


def _serialize_graph(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's graph component, dependencies, and import evidence."""

    module_graph = record.graph
    _record(
        lines,
        "graph",
        ("module", module),
        ("component_is_cyclic", _boolean(module_graph.component_is_cyclic)),
        ("component_members", _integer(len(module_graph.component_members))),
        ("dependency_targets", _integer(len(module_graph.dependency_targets))),
        ("import_evidence", _integer(len(module_graph.import_evidence))),
    )
    for ordinal, member in enumerate(module_graph.component_members):
        _record(
            lines,
            "graph_component_member",
            ("module", module),
            ("member", _integer(ordinal)),
            ("path", _text(member.path)),
        )
    for ordinal, target in enumerate(module_graph.dependency_targets):
        _record(
            lines,
            "graph_dependency_target",
            ("module", module),
            ("target", _integer(ordinal)),
            ("path", _text(target.path)),
        )
    for ordinal, evidence in enumerate(module_graph.import_evidence):
        _record(
            lines,
            "graph_import_evidence",
            ("module", module),
            ("evidence", _integer(ordinal)),
            ("path", _text(evidence.target.path)),
            (
                "module_statement_position",
                _integer(evidence.module_statement_position),
            ),
            ("item_position", _integer(evidence.item_position)),
        )


def _serialize_imports(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's import requests, aliases, targets, and issue buckets."""

    for ordinal, projected in enumerate(record.imports):
        request = _integer(ordinal)
        target = projected.resolved_target
        _record(
            lines,
            "import",
            ("module", module),
            ("request", request),
            ("local_name", _text(projected.local_name)),
            ("namespace", _enumeration(projected.namespace)),
            ("declaration_kind", _enumeration(projected.declaration_kind)),
            ("target_module_path", _text(projected.target_module_path)),
            ("exported_name", _text(projected.exported_name)),
            (
                "module_statement_position",
                _integer(projected.module_statement_position),
            ),
            ("item_position", _integer(projected.item_position)),
            (
                "resolved_module_path",
                _optional_text(None if target is None else target.module_path),
            ),
            (
                "resolved_namespace",
                _optional_enumeration(None if target is None else target.namespace),
            ),
            (
                "resolved_declaration_kind",
                _optional_enumeration(
                    None if target is None else target.declaration_kind
                ),
            ),
            (
                "resolved_declared_name",
                _optional_text(None if target is None else target.declared_name),
            ),
            ("issues", _integer(len(projected.issue_statuses))),
        )
        for issue_ordinal, status in enumerate(projected.issue_statuses):
            _record(
                lines,
                "import_issue",
                ("module", module),
                ("request", request),
                ("issue", _integer(issue_ordinal)),
                ("status", _enumeration(status)),
            )


def _serialize_exports(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's export requests, facade entries, and issue buckets."""

    for ordinal, projected in enumerate(record.exports):
        request = _integer(ordinal)
        target = projected.target_identity
        _record(
            lines,
            "export",
            ("module", module),
            ("request", request),
            ("local_name", _text(projected.local_name)),
            ("namespace", _enumeration(projected.namespace)),
            ("declaration_kind", _enumeration(projected.declaration_kind)),
            (
                "module_statement_position",
                _integer(projected.module_statement_position),
            ),
            ("item_position", _integer(projected.item_position)),
            ("exposed_name", _optional_text(projected.exposed_name)),
            ("entry_origin", _optional_enumeration(projected.entry_origin)),
            (
                "target_module_path",
                _optional_text(None if target is None else target.module_path),
            ),
            (
                "target_namespace",
                _optional_enumeration(None if target is None else target.namespace),
            ),
            (
                "target_declaration_kind",
                _optional_enumeration(
                    None if target is None else target.declaration_kind
                ),
            ),
            (
                "target_declared_name",
                _optional_text(None if target is None else target.declared_name),
            ),
            ("issues", _integer(len(projected.issue_statuses))),
        )
        for issue_ordinal, status in enumerate(projected.issue_statuses):
            _record(
                lines,
                "export_issue",
                ("module", module),
                ("request", request),
                ("issue", _integer(issue_ordinal)),
                ("status", _enumeration(status)),
            )


def _serialize_declarations(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's declarations, availability, and concrete row fields."""

    for projected in record.declarations:
        declaration = _integer(projected.declaration_position)
        _record(
            lines,
            "declaration",
            ("module", module),
            ("declaration", declaration),
            ("owner_kind", _enumeration(projected.owner.kind)),
            ("owner_namespace", _text(projected.owner.namespace)),
            ("owner_name", _text(projected.owner.name)),
            ("namespace", _enumeration(projected.identity.namespace)),
            ("declaration_kind", _enumeration(projected.identity.declaration_kind)),
            ("declared_name", _text(projected.identity.declared_name)),
            ("availability", _enumeration(projected.availability)),
            ("occurrence_count", _integer(projected.occurrence_count)),
            ("occurrence_index", _integer(projected.occurrence_index)),
            ("relation_status", _optional_enumeration(projected.relation_status)),
            ("relation_reason", _optional_enumeration(projected.relation_reason)),
            ("row_fields", _integer(len(projected.row_fields))),
        )
        for ordinal, row_field in enumerate(projected.row_fields):
            _record(
                lines,
                "declaration_row_field",
                ("module", module),
                ("declaration", declaration),
                ("field", _integer(ordinal)),
                ("name", _text(row_field.name)),
                ("nullability", _enumeration(row_field.nullability)),
                ("result_role", _enumeration(row_field.result_role)),
            )


def _serialize_origins(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's local and imported origin paths with exact hops."""

    for ordinal, projected in enumerate(record.origins):
        origin = _integer(ordinal)
        _record(
            lines,
            "origin",
            ("module", module),
            ("origin", origin),
            ("namespace", _enumeration(projected.namespace)),
            ("declaration_kind", _enumeration(projected.declaration_kind)),
            ("local_name", _text(projected.local_name)),
            ("binding", _enumeration(projected.binding)),
            ("target_module_path", _text(projected.target_module_path)),
            (
                "target_declaration_position",
                _integer(projected.target_declaration_position),
            ),
            ("target_declared_name", _text(projected.target_declared_name)),
            ("hops", _integer(len(projected.hops))),
        )
        for hop_ordinal, hop in enumerate(projected.hops):
            _record(
                lines,
                "origin_hop",
                ("module", module),
                ("origin", origin),
                ("hop", _integer(hop_ordinal)),
                (
                    "import_target_module_path",
                    _text(hop.import_target_module_path),
                ),
                ("import_exported_name", _text(hop.import_exported_name)),
                (
                    "import_module_statement_position",
                    _integer(hop.import_module_statement_position),
                ),
                ("import_item_position", _integer(hop.import_item_position)),
                ("facade_module_path", _text(hop.facade_module_path)),
                ("facade_exposed_name", _text(hop.facade_exposed_name)),
                ("facade_origin", _enumeration(hop.facade_origin)),
                ("target_module_path", _text(hop.target_identity.module_path)),
                ("target_declared_name", _text(hop.target_identity.declared_name)),
            )


def _serialize_dependencies(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's reference-to-target dependency facts."""

    for ordinal, projected in enumerate(record.dependencies):
        declaration_target = projected.target_declaration
        row_field_target = projected.target_row_field
        _record(
            lines,
            "dependency",
            ("module", module),
            ("dependency", _integer(ordinal)),
            ("kind", _enumeration(projected.kind)),
            (
                "reference_owner_declaration_position",
                _integer(projected.reference_owner_declaration_position),
            ),
            ("reference_role", _enumeration(projected.reference_role)),
            (
                "reference_member_position",
                _integer(projected.reference_member_position),
            ),
            (
                "target_declaration_module_path",
                _optional_text(
                    None
                    if declaration_target is None
                    else declaration_target.identity.module_path
                ),
            ),
            (
                "target_declaration_position",
                _optional_integer(
                    None
                    if declaration_target is None
                    else declaration_target.declaration_position
                ),
            ),
            (
                "target_declaration_declared_name",
                _optional_text(
                    None
                    if declaration_target is None
                    else declaration_target.identity.declared_name
                ),
            ),
            (
                "target_row_field_owner_declaration_position",
                _optional_integer(
                    None
                    if row_field_target is None
                    else row_field_target.owner.declaration_position
                ),
            ),
            (
                "target_row_field_kind",
                _optional_enumeration(
                    None if row_field_target is None else row_field_target.kind
                ),
            ),
            (
                "target_row_field_position",
                _optional_integer(
                    None
                    if row_field_target is None
                    else row_field_target.field_position
                ),
            ),
            (
                "target_row_field_name",
                _optional_text(
                    None if row_field_target is None else row_field_target.name
                ),
            ),
        )


def _serialize_row_lineage(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's complete relation row lineage."""

    for lineage_ordinal, projected in enumerate(record.row_lineage):
        lineage = _integer(lineage_ordinal)
        _record(
            lines,
            "row_lineage",
            ("module", module),
            ("lineage", lineage),
            (
                "owner_declaration_position",
                _integer(projected.owner_declaration_position),
            ),
            ("status", _enumeration(projected.status)),
            ("reason", _enumeration(projected.reason)),
            ("fields", _integer(len(projected.fields))),
        )
        for field_ordinal, field_lineage in enumerate(projected.fields):
            field_token = _integer(field_ordinal)
            _record(
                lines,
                "row_lineage_field",
                ("module", module),
                ("lineage", lineage),
                ("field", field_token),
                ("kind", _enumeration(field_lineage.kind)),
                ("field_position", _integer(field_lineage.field_position)),
                ("name", _text(field_lineage.name)),
                ("paths", _integer(len(field_lineage.paths))),
            )
            for path_ordinal, lineage_path in enumerate(field_lineage.paths):
                path_token = _integer(path_ordinal)
                _record(
                    lines,
                    "row_lineage_path",
                    ("module", module),
                    ("lineage", lineage),
                    ("field", field_token),
                    ("path", path_token),
                    ("root_module_path", _text(lineage_path.root_module_path)),
                    (
                        "root_owner_declaration_position",
                        _integer(lineage_path.root_owner_declaration_position),
                    ),
                    (
                        "root_field_position",
                        _integer(lineage_path.root_field_position),
                    ),
                    ("root_field_name", _text(lineage_path.root_field_name)),
                    ("hops", _integer(len(lineage_path.hops))),
                )
                for hop_ordinal, hop in enumerate(lineage_path.hops):
                    _record(
                        lines,
                        "row_lineage_hop",
                        ("module", module),
                        ("lineage", lineage),
                        ("field", field_token),
                        ("path", path_token),
                        ("hop", _integer(hop_ordinal)),
                        ("projection_kind", _enumeration(hop.projection_kind)),
                        ("output_field_name", _text(hop.output_field_name)),
                        ("upstream_field_name", _text(hop.upstream_field_name)),
                    )


def _serialize_type_resolutions(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's resolved type and source shape references."""

    for ordinal, projected in enumerate(record.type_resolutions):
        resolution = _integer(ordinal)
        target = projected.canonical_target
        _record(
            lines,
            "type_resolution",
            ("module", module),
            ("resolution", resolution),
            (
                "owner_declaration_position",
                _integer(projected.owner_declaration_position),
            ),
            ("role", _enumeration(projected.role)),
            ("member_position", _integer(projected.member_position)),
            ("direct_kind", _enumeration(projected.direct_kind)),
            ("canonical_kind", _enumeration(projected.canonical_kind)),
            ("canonical_name", _text(projected.canonical_name)),
            (
                "canonical_target_module_path",
                _optional_text(None if target is None else target.module_path),
            ),
            (
                "canonical_target_declared_name",
                _optional_text(None if target is None else target.declared_name),
            ),
            ("alias_chain", _integer(len(projected.alias_chain))),
        )
        for alias_ordinal, alias in enumerate(projected.alias_chain):
            _record(
                lines,
                "type_resolution_alias",
                ("module", module),
                ("resolution", resolution),
                ("alias", _integer(alias_ordinal)),
                ("module_path", _text(alias.module_path)),
                ("namespace", _enumeration(alias.namespace)),
                ("declaration_kind", _enumeration(alias.declaration_kind)),
                ("declared_name", _text(alias.declared_name)),
            )
    for ordinal, source_resolution in enumerate(record.source_shape_resolutions):
        _record(
            lines,
            "source_shape_resolution",
            ("module", module),
            ("resolution", _integer(ordinal)),
            (
                "owner_declaration_position",
                _integer(source_resolution.owner_declaration_position),
            ),
            (
                "target_module_path",
                _text(source_resolution.target_identity.module_path),
            ),
            (
                "target_declared_name",
                _text(source_resolution.target_identity.declared_name),
            ),
        )


def _serialize_relation_resolutions(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's resolved relation references."""

    for ordinal, projected in enumerate(record.relation_resolutions):
        _record(
            lines,
            "relation_resolution",
            ("module", module),
            ("resolution", _integer(ordinal)),
            (
                "owner_declaration_position",
                _integer(projected.owner_declaration_position),
            ),
            ("local_name", _text(projected.local_name)),
            (
                "target_module_path",
                _text(projected.target_identity.module_path),
            ),
            (
                "target_declared_name",
                _text(projected.target_identity.declared_name),
            ),
        )


def _serialize_semantic_facts(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's preserved semantic facts."""

    for ordinal, projected in enumerate(record.semantic_facts):
        facts = _integer(ordinal)
        _record(
            lines,
            "semantic_facts",
            ("module", module),
            ("facts", facts),
            (
                "owner_declaration_position",
                _integer(projected.owner_declaration_position),
            ),
            ("status", _enumeration(projected.status)),
            ("reason", _enumeration(projected.reason)),
            ("let_bindings", _integer(len(projected.let_bindings))),
            ("selects", _integer(len(projected.selects))),
            (
                "clause_dependencies",
                _integer(len(projected.clause_dependencies)),
            ),
            ("window_outputs", _integer(len(projected.window_outputs))),
        )
        for binding_ordinal, let_binding in enumerate(projected.let_bindings):
            _record(
                lines,
                "semantic_let_binding",
                ("module", module),
                ("facts", facts),
                ("binding", _integer(binding_ordinal)),
                ("binding_ordinal", _integer(let_binding.binding_ordinal)),
                ("has_value_type", _boolean(let_binding.has_value_type)),
            )
        for select_ordinal, select in enumerate(projected.selects):
            _record(
                lines,
                "semantic_select",
                ("module", module),
                ("facts", facts),
                ("select", _integer(select_ordinal)),
                (
                    "selected_output_ordinal",
                    _integer(select.selected_output_ordinal),
                ),
                ("output_name", _optional_text(select.output_name)),
            )
        for clause_ordinal, clause in enumerate(projected.clause_dependencies):
            _record(
                lines,
                "semantic_clause_dependency",
                ("module", module),
                ("facts", facts),
                ("dependency", _integer(clause_ordinal)),
                ("role", _enumeration(clause.role)),
                ("source_ordinal", _integer(clause.source_ordinal)),
                ("status", _enumeration(clause.status)),
            )
        for output_ordinal, window_output in enumerate(projected.window_outputs):
            _record(
                lines,
                "semantic_window_output",
                ("module", module),
                ("facts", facts),
                ("output", _integer(output_ordinal)),
                (
                    "selected_output_ordinal",
                    _integer(window_output.selected_output_ordinal),
                ),
                ("output_name", _optional_text(window_output.output_name)),
                ("status", _enumeration(window_output.status)),
            )


def _serialize_issues(
    lines: list[str],
    module: str,
    record: ProjectModuleInspectionRecord,
) -> None:
    """Emit one module's complete structural issue bucket without a winner."""

    for ordinal, projected in enumerate(record.issues):
        _record(
            lines,
            "issue",
            ("module", module),
            ("issue", _integer(ordinal)),
            ("family", _enumeration(projected.family)),
            ("status", _text(projected.status)),
            ("local_name", _optional_text(projected.local_name)),
        )


def _record(lines: list[str], kind: str, *pairs: tuple[str, str]) -> None:
    """Append one canonical record line in its exact declared key order."""

    lines.append(kind + "".join(f"\t{key}={token}" for key, token in pairs))


def _escape(value: str) -> str:
    """Escape one text payload into the canonical single-line representation."""

    escaped: list[str] = []
    for character in value:
        replacement = _INSPECTION_ESCAPES.get(character)
        if replacement is not None:
            escaped.append(replacement)
        elif (
            character < _INSPECTION_FIRST_PRINTABLE
            or character == _INSPECTION_DELETE_CHARACTER
        ):
            escaped.append(f"\\x{ord(character):02x}")
        elif _INSPECTION_SURROGATE_START <= character <= _INSPECTION_SURROGATE_END:
            # A POSIX path byte that the filesystem encoding cannot decode
            # reaches this projection as a lone surrogate, and UTF-8 refuses to
            # encode one. Escaping it keeps the payload total over every
            # retained text and keeps one unambiguous byte representation.
            escaped.append(f"\\u{ord(character):04x}")
        else:
            escaped.append(character)
    return "".join(escaped)


def _text(value: str) -> str:
    """Encode one exact text payload."""

    if type(value) is not str:
        raise TypeError("Canonical text payload must be text.")
    return f"s:{_escape(value)}"


def _integer(value: int) -> str:
    """Encode one exact non-negative canonical decimal payload."""

    if type(value) is not int or value < 0:
        raise ValueError("Canonical integer payload must be a non-negative integer.")
    return f"i:{value}"


def _boolean(value: bool) -> str:
    """Encode one exact boolean payload."""

    if type(value) is not bool:
        raise TypeError("Canonical boolean payload must be a boolean.")
    return "b:true" if value else "b:false"


def _enumeration(value: StrEnum) -> str:
    """Encode one exact enumeration payload by its declared value."""

    if not isinstance(value, StrEnum):
        raise TypeError("Canonical enumeration payload must be an enumeration.")
    return f"e:{_escape(value.value)}"


def _optional_text(value: str | None) -> str:
    """Encode one optional text payload, using the exact absence token."""

    return _INSPECTION_ABSENT_TOKEN if value is None else _text(value)


def _optional_integer(value: int | None) -> str:
    """Encode one optional integer payload, using the exact absence token."""

    return _INSPECTION_ABSENT_TOKEN if value is None else _integer(value)


def _optional_enumeration(value: StrEnum | None) -> str:
    """Encode one optional enumeration payload, using the exact absence token."""

    return _INSPECTION_ABSENT_TOKEN if value is None else _enumeration(value)


def _frozen_bucket_mapping(
    buckets: Mapping[_Key, list[_Value]],
) -> Mapping[_Key, tuple[_Value, ...]]:
    """Copy complete buckets into an immutable tuple-valued mapping."""

    return MappingProxyType({key: tuple(values) for key, values in buckets.items()})


def _require_tuple(values: object, item_type: type, label: str) -> None:
    """Require an exact tuple of one exact item type."""

    if type(values) is not tuple:
        raise TypeError(f"{label} must be a tuple.")
    if any(type(value) is not item_type for value in values):
        raise TypeError(f"{label} must retain exact items.")


def _require_text(value: object, label: str) -> None:
    """Require an exact text value.

    Every inspected text field is a verbatim projection of an upstream fact, and
    the upstream stages deliberately retain an unresolvable or empty decoded
    target, exported name, or output name and report it through their own issue
    facts. Re-validating the content here would reject a pre-existing accepted
    case, so this checks the exact type only.
    """

    if type(value) is not str:
        raise TypeError(f"{label} must be text.")


def _require_optional_text(value: object, label: str) -> None:
    """Require an exact optional text value."""

    if value is not None and type(value) is not str:
        raise TypeError(f"{label} must be text.")


def _require_position(value: object, label: str) -> None:
    """Require a non-negative integer position."""

    if type(value) is not int or value < 0:
        raise ValueError(f"{label} position must be a non-negative integer.")
