"""Private Phase 59 package-graph value model and runtime scope authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import get_args

from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
)
from pietto._project.capability_checking import (
    CapabilityRequirementCheck,
    CapabilityRequirementStatus,
    PackageCapabilityRequirementsBlocked,
    PackageCapabilityRequirementsChecked,
)
from pietto._project.capability_inspection import CapabilityInspectionFactSet
from pietto._project.capability_matrix import (
    CapabilityCheckingMatrixCell,
    PackageCapabilityCheckingMatrix,
)
from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectAggregateGroupedClauseReadinessReason,
    ProjectAggregateGroupedClauseReadinessStatus,
)
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspection,
    ExtensionCatalogInspectionFactSet,
    ExtensionCatalogInspectionLookupVariant,
    ExtensionCatalogInspectionProviderOccurrence,
)
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsReason,
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
)
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowField,
    ProjectRowFieldProvenanceKind,
    ProjectSymbolNamespace,
)
from pietto._project.module_attribution import (
    ProjectModuleProjectionKind,
    ProjectModuleRowFieldIdentity,
    ProjectModuleRowFieldKind,
    ProjectModuleRowLineageHop,
    ProjectModuleSourceFieldOrigin,
)
from pietto._project.module_package_neutral_identity import (
    ProjectModulePackageNeutralIdentityFactSet,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleExpressionReferenceFact,
    ProjectModuleFactOccurrenceRole,
    ProjectModuleLetBindingFact,
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSelectFact,
    ProjectModuleWindowOutputFact,
)
from pietto._project.package_capability_requirements import (
    _package_capability_requirement_binding,
)
from pietto._project.package_extension_signature_selectors import (
    _package_extension_signature_requirement_selectors,
)
from pietto._project.package_inspection import (
    PackageInspection,
    PackageInspectionFactSet,
    PackageInspectionOutcome,
    PackageInspectionPackageRole,
)
from pietto._project.package_load_plan import (
    LoadedDependencyPackage,
    LoadedPackage,
    PackageDependencyOccurrence,
    PackageLoadPlanBlocker,
    _package_content_digest,
    _package_coordinate,
)
from pietto._project.package_loader import (
    LoadedRootPackage,
    PackageParsedModule,
    _PackageModuleContent,
)
from pietto._project.package_manifest import (
    PackageCoordinate,
    _is_valid_content_digest_pin,
)
from pietto._project.row_dependency_graph import ProjectRowDependencyNodeKind
from pietto._project.window_semantics import (
    WindowDependencyOccurrence,
    WindowDependencyRole,
)
from pietto.errors import Diagnostic, Severity
from pietto.ast_nodes import Definition
from pietto.semantic.capability_profiles import CapabilityRequirementOccurrence
from pietto.semantic.extension_signature_requirements import (
    ExtensionSignatureRequirementSelectorOccurrence,
    ExtensionSignatureRequirementSelectors,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class PackageGraphScope:
    """Opaque identity-equal owner for one runtime package-graph snapshot."""


@dataclass(frozen=True, slots=True)
class PackageGraphPackageRef:
    """One package occurrence coordinate owned by one runtime snapshot."""

    scope: PackageGraphScope
    position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Package graph package ref requires an exact scope.")
        if type(self.position) is not int or self.position < 0:
            raise ValueError(
                "Package graph package ref position must be a non-negative integer."
            )


@dataclass(frozen=True, slots=True)
class PackageGraphDependencyRef:
    """One authored dependency occurrence coordinate in one runtime snapshot."""

    scope: PackageGraphScope
    declaring_package: PackageGraphPackageRef
    declaration_position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Package graph dependency ref requires an exact scope.")
        if type(self.declaring_package) is not PackageGraphPackageRef:
            raise TypeError(
                "Package graph dependency ref requires a declaring package ref."
            )
        if self.declaring_package.scope is not self.scope:
            raise ValueError(
                "Package graph dependency ref and declaring package require the same scope."
            )
        if type(self.declaration_position) is not int or self.declaration_position < 0:
            raise ValueError(
                "Package graph dependency declaration position must be non-negative."
            )


@dataclass(frozen=True, slots=True)
class PackageGraphPackage:
    """One package occurrence plus separate semantic, content, and role facts."""

    ref: PackageGraphPackageRef
    coordinate: PackageCoordinate
    content_digest: str
    role: PackageInspectionPackageRole

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphPackageRef:
            raise TypeError("Package graph packages require an exact package ref.")
        if type(self.coordinate) is not PackageCoordinate:
            raise TypeError("Package graph packages require an exact coordinate.")
        if type(self.content_digest) is not str or not _is_valid_content_digest_pin(
            self.content_digest
        ):
            raise ValueError(
                "Package graph package content digest must be exact SHA-256 text."
            )
        if type(self.role) is not PackageInspectionPackageRole:
            raise TypeError("Package graph packages require an exact package role.")


@dataclass(frozen=True, slots=True)
class PackageGraphDependency:
    """One authored dependency occurrence and its exact resolves-to link."""

    ref: PackageGraphDependencyRef
    declaring_package: PackageGraphPackageRef
    resolved_package: PackageGraphPackageRef
    witness: PackageDependencyOccurrence

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphDependencyRef:
            raise TypeError(
                "Package graph dependencies require an exact dependency ref."
            )
        if (
            type(self.declaring_package) is not PackageGraphPackageRef
            or type(self.resolved_package) is not PackageGraphPackageRef
        ):
            raise TypeError(
                "Package graph dependencies require exact package endpoint refs."
            )
        if not (
            self.ref.scope
            is self.declaring_package.scope
            is self.resolved_package.scope
        ):
            raise ValueError(
                "Package graph dependency refs require the same snapshot scope."
            )
        if self.ref.declaring_package != self.declaring_package:
            raise ValueError(
                "Package graph dependency ref must name its declaring package."
            )
        if type(self.witness) is not PackageDependencyOccurrence:
            raise TypeError(
                "Package graph dependencies require an exact authored witness."
            )
        if self.witness.position != self.ref.declaration_position:
            raise ValueError(
                "Package graph dependency witness must retain its authored position."
            )


class PackageGraphRequirementDeclaration(StrEnum):
    """Closed package-owned requirement declaration states."""

    UNDECLARED = "undeclared"
    DECLARED = "declared"


@dataclass(frozen=True, slots=True)
class PackageGraphRequirementRef:
    """One authored requirement occurrence in one package and snapshot."""

    scope: PackageGraphScope
    package: PackageGraphPackageRef
    position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Package graph requirement ref requires an exact scope.")
        if type(self.package) is not PackageGraphPackageRef:
            raise TypeError("Package graph requirement ref requires a package ref.")
        if self.package.scope is not self.scope:
            raise ValueError(
                "Package graph requirement ref and package require the same scope."
            )
        if type(self.position) is not int or self.position < 0:
            raise ValueError("Package graph requirement position must be non-negative.")


@dataclass(frozen=True, slots=True)
class PackageGraphSelectorRef:
    """One package-owned selector occurrence in one runtime snapshot."""

    scope: PackageGraphScope
    package: PackageGraphPackageRef
    position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Package graph selector ref requires an exact scope.")
        if type(self.package) is not PackageGraphPackageRef:
            raise TypeError("Package graph selector ref requires a package ref.")
        if self.package.scope is not self.scope:
            raise ValueError(
                "Package graph selector ref and package require the same scope."
            )
        if type(self.position) is not int or self.position < 0:
            raise ValueError("Package graph selector position must be non-negative.")


@dataclass(frozen=True, slots=True)
class PackageGraphRequirementCollection:
    """One package occurrence's exact declared or undeclared authority."""

    package: PackageGraphPackageRef
    declaration: PackageGraphRequirementDeclaration
    binding: PackageCapabilityRequirementBinding | None = field(
        repr=False,
        compare=False,
        hash=False,
    )
    selectors: ExtensionSignatureRequirementSelectors | None = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.package) is not PackageGraphPackageRef:
            raise TypeError("Requirement collections require a package ref.")
        if type(self.declaration) is not PackageGraphRequirementDeclaration:
            raise TypeError("Requirement collections require a declaration state.")
        if self.declaration is PackageGraphRequirementDeclaration.UNDECLARED:
            if self.binding is not None or self.selectors is not None:
                raise ValueError("Undeclared requirements forbid binding authority.")
            return
        if type(self.binding) is not PackageCapabilityRequirementBinding:
            raise ValueError("Declared requirements require an exact binding.")
        if self.selectors is not None:
            if type(self.selectors) is not ExtensionSignatureRequirementSelectors:
                raise TypeError("Requirement selectors require exact authority.")
            if self.selectors.requirements is not self.binding.requirements:
                raise ValueError(
                    "Requirement selectors require exact binding authority."
                )


@dataclass(frozen=True, slots=True)
class PackageGraphRequirement:
    """One exact authored package requirement occurrence."""

    ref: PackageGraphRequirementRef
    package: PackageGraphPackageRef
    witness: CapabilityRequirementOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphRequirementRef:
            raise TypeError("Graph requirements require an exact requirement ref.")
        if type(self.package) is not PackageGraphPackageRef:
            raise TypeError("Graph requirements require a package ref.")
        if self.ref.package != self.package:
            raise ValueError("Graph requirement ref must name its package.")
        if type(self.witness) is not CapabilityRequirementOccurrence:
            raise TypeError("Graph requirements require an exact authored witness.")
        if self.witness.position != self.ref.position:
            raise ValueError("Graph requirement witness must retain authored position.")


@dataclass(frozen=True, slots=True)
class PackageGraphSelector:
    """One exact package-owned selector occurrence and covered requirement."""

    ref: PackageGraphSelectorRef
    package: PackageGraphPackageRef
    requirement: PackageGraphRequirementRef
    witness: ExtensionSignatureRequirementSelectorOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphSelectorRef:
            raise TypeError("Graph selectors require an exact selector ref.")
        if type(self.package) is not PackageGraphPackageRef:
            raise TypeError("Graph selectors require a package ref.")
        if type(self.requirement) is not PackageGraphRequirementRef:
            raise TypeError("Graph selectors require a requirement ref.")
        if not (
            self.ref.scope is self.package.scope is self.requirement.scope
            and self.ref.package == self.package == self.requirement.package
        ):
            raise ValueError("Graph selector refs require exact package ownership.")
        if type(self.witness) is not ExtensionSignatureRequirementSelectorOccurrence:
            raise TypeError("Graph selectors require an exact selector witness.")
        if self.witness.requirement_position != self.requirement.position:
            raise ValueError(
                "Graph selector must cover its exact requirement position."
            )


type PackageGraphModuleWitness = PackageParsedModule | _PackageModuleContent


@dataclass(frozen=True, slots=True)
class PackageGraphModuleRef:
    """One package-qualified loaded module occurrence in one snapshot."""

    scope: PackageGraphScope
    package: PackageGraphPackageRef
    position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Package graph module refs require an exact scope.")
        if type(self.package) is not PackageGraphPackageRef:
            raise TypeError("Package graph module refs require a package ref.")
        if self.package.scope is not self.scope:
            raise ValueError("Package graph module refs require the package scope.")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("Package graph module position must be non-negative.")


@dataclass(frozen=True, slots=True)
class PackageGraphDeclarationRef:
    """One package-qualified module declaration occurrence in one snapshot."""

    scope: PackageGraphScope
    module: PackageGraphModuleRef
    position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Package graph declaration refs require an exact scope.")
        if type(self.module) is not PackageGraphModuleRef:
            raise TypeError("Package graph declaration refs require a module ref.")
        if self.module.scope is not self.scope:
            raise ValueError("Package graph declaration refs require the module scope.")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("Package graph declaration position must be non-negative.")


@dataclass(frozen=True, slots=True)
class PackageGraphModule:
    """One exact loaded module occurrence with package ownership."""

    ref: PackageGraphModuleRef
    package: PackageGraphPackageRef
    package_authority: LoadedPackage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    witness: PackageGraphModuleWitness = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphModuleRef:
            raise TypeError("Graph modules require an exact module ref.")
        if type(self.package) is not PackageGraphPackageRef:
            raise TypeError("Graph modules require an exact package ref.")
        if self.ref.package != self.package:
            raise ValueError("Graph module ref must name its package.")
        if type(self.package_authority) not in {
            LoadedRootPackage,
            LoadedDependencyPackage,
        }:
            raise TypeError("Graph modules require exact loaded package authority.")
        if type(self.witness) not in {PackageParsedModule, _PackageModuleContent}:
            raise TypeError("Graph modules require an exact loaded module witness.")
        modules = self.package_authority.modules
        if (
            self.ref.position >= len(modules)
            or modules[self.ref.position] is not self.witness
            or self.witness.position != self.ref.position
        ):
            raise ValueError("Graph module must retain exact package module order.")


@dataclass(frozen=True, slots=True)
class PackageGraphDeclaration:
    """One exact source-ordered declaration owned by a graph module."""

    ref: PackageGraphDeclarationRef
    module: PackageGraphModuleRef
    witness: Definition = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphDeclarationRef:
            raise TypeError("Graph declarations require an exact declaration ref.")
        if type(self.module) is not PackageGraphModuleRef:
            raise TypeError("Graph declarations require an exact module ref.")
        if self.ref.module != self.module:
            raise ValueError("Graph declaration ref must name its module.")
        if type(self.witness) not in get_args(Definition):
            raise TypeError("Graph declarations require an exact AST definition.")


@dataclass(frozen=True, slots=True)
class PackageGraphSemanticAuthority:
    """One package occurrence's exact joined attribution/semantic authority."""

    package: PackageGraphPackageRef
    witness: ProjectModulePackageNeutralIdentityFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.package) is not PackageGraphPackageRef:
            raise TypeError("Graph semantic authority requires a package ref.")
        if type(self.witness) is not ProjectModulePackageNeutralIdentityFactSet:
            raise TypeError("Graph semantic authority requires exact joined facts.")


@dataclass(frozen=True, slots=True)
class PackageGraphFieldRef:
    """One declaration-qualified semantic field occurrence in one snapshot."""

    scope: PackageGraphScope
    declaration: PackageGraphDeclarationRef
    position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Package graph field refs require an exact scope.")
        if type(self.declaration) is not PackageGraphDeclarationRef:
            raise TypeError("Package graph field refs require a declaration ref.")
        if self.declaration.scope is not self.scope:
            raise ValueError("Package graph field refs require the declaration scope.")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("Package graph field position must be non-negative.")


@dataclass(frozen=True, slots=True)
class PackageGraphLetRef:
    """One declaration-qualified let-binding occurrence in one snapshot."""

    scope: PackageGraphScope
    declaration: PackageGraphDeclarationRef
    position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Package graph let refs require an exact scope.")
        if type(self.declaration) is not PackageGraphDeclarationRef:
            raise TypeError("Package graph let refs require a declaration ref.")
        if self.declaration.scope is not self.scope:
            raise ValueError("Package graph let refs require the declaration scope.")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("Package graph let position must be non-negative.")


type PackageGraphFieldWitness = ProjectModuleRowFieldIdentity | ProjectModuleSelectFact


@dataclass(frozen=True, slots=True)
class PackageGraphField:
    """One exact semantic field occurrence and its existing witness."""

    ref: PackageGraphFieldRef
    declaration: PackageGraphDeclarationRef
    kind: ProjectModuleRowFieldKind
    name: str
    semantic_field: ProjectRowField | None = field(
        repr=False,
        compare=False,
        hash=False,
    )
    witness: PackageGraphFieldWitness = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphFieldRef:
            raise TypeError("Graph fields require an exact field ref.")
        if type(self.declaration) is not PackageGraphDeclarationRef:
            raise TypeError("Graph fields require a declaration ref.")
        if self.ref.declaration != self.declaration:
            raise ValueError("Graph field ref must name its declaration.")
        if type(self.kind) is not ProjectModuleRowFieldKind:
            raise TypeError("Graph fields require an exact field kind.")
        if type(self.name) is not str or not self.name:
            raise ValueError("Graph fields require a non-empty name witness.")
        if self.semantic_field is not None and type(self.semantic_field) is not (
            ProjectRowField
        ):
            raise TypeError("Graph semantic fields require exact row-field evidence.")
        if type(self.witness) is ProjectModuleRowFieldIdentity:
            if (
                self.witness.kind is not self.kind
                or self.witness.field_position != self.ref.position
                or self.witness.name != self.name
            ):
                raise ValueError("Graph field identity witness does not align.")
            return
        if type(self.witness) is not ProjectModuleSelectFact:
            raise TypeError("Graph fields require exact typed field evidence.")
        if (
            self.kind is not ProjectModuleRowFieldKind.RELATION_OUTPUT
            or self.witness.selected_output_ordinal != self.ref.position
            or self.witness.field is not self.semantic_field
            or self.semantic_field is None
            or self.semantic_field.name != self.name
        ):
            raise ValueError("Graph selected-output field witness does not align.")


@dataclass(frozen=True, slots=True)
class PackageGraphLetBinding:
    """One exact source-ordered let-binding occurrence."""

    ref: PackageGraphLetRef
    declaration: PackageGraphDeclarationRef
    witness: ProjectModuleLetBindingFact = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphLetRef:
            raise TypeError("Graph let bindings require an exact let ref.")
        if type(self.declaration) is not PackageGraphDeclarationRef:
            raise TypeError("Graph let bindings require a declaration ref.")
        if self.ref.declaration != self.declaration:
            raise ValueError("Graph let ref must name its declaration.")
        if type(self.witness) is not ProjectModuleLetBindingFact:
            raise TypeError("Graph let bindings require exact semantic evidence.")
        if self.witness.binding_ordinal != self.ref.position:
            raise ValueError("Graph let binding must retain source order.")


@dataclass(frozen=True, slots=True)
class PackageGraphSourceLineage:
    """One exact source-row field to shape-field origin relationship."""

    output: PackageGraphFieldRef
    upstream: PackageGraphFieldRef
    witness: ProjectModuleSourceFieldOrigin = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.output) is not PackageGraphFieldRef
            or type(self.upstream) is not PackageGraphFieldRef
        ):
            raise TypeError("Source lineage requires exact field refs.")
        if self.output.scope is not self.upstream.scope:
            raise ValueError("Source lineage refs require one snapshot scope.")
        if type(self.witness) is not ProjectModuleSourceFieldOrigin:
            raise TypeError("Source lineage requires exact source-origin evidence.")


@dataclass(frozen=True, slots=True)
class PackageGraphProjectionLineage:
    """One exact direct or renamed projection relationship."""

    kind: ProjectModuleProjectionKind
    output: PackageGraphFieldRef
    upstream: PackageGraphFieldRef
    witness: ProjectModuleRowLineageHop = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectModuleProjectionKind:
            raise TypeError("Projection lineage requires an exact projection kind.")
        if (
            type(self.output) is not PackageGraphFieldRef
            or type(self.upstream) is not PackageGraphFieldRef
        ):
            raise TypeError("Projection lineage requires exact field refs.")
        if self.output.scope is not self.upstream.scope:
            raise ValueError("Projection lineage refs require one snapshot scope.")
        if type(self.witness) is not ProjectModuleRowLineageHop:
            raise TypeError("Projection lineage requires an exact lineage hop.")
        if self.witness.projection_kind is not self.kind:
            raise ValueError("Projection lineage kind must retain its exact witness.")


class PackageGraphExpressionLineageKind(StrEnum):
    """Closed non-window expression lineage relationship kinds."""

    COMPUTED = "computed"
    LET_OUTPUT = "let_output"
    LET_EXPRESSION = "let_expression"
    AGGREGATE = "aggregate"


type PackageGraphExpressionOutputRef = PackageGraphFieldRef | PackageGraphLetRef
type PackageGraphExpressionUpstreamRef = PackageGraphFieldRef | PackageGraphLetRef
type PackageGraphExpressionOwnerWitness = (
    ProjectModuleSelectFact | ProjectModuleLetBindingFact
)


@dataclass(frozen=True, slots=True)
class PackageGraphExpressionLineage:
    """One ordered computed, let, or aggregate input occurrence."""

    kind: PackageGraphExpressionLineageKind
    output: PackageGraphExpressionOutputRef
    upstream: PackageGraphExpressionUpstreamRef
    role: ProjectModuleFactOccurrenceRole
    container_position: int
    input_position: int
    owner_witness: PackageGraphExpressionOwnerWitness = field(
        repr=False,
        compare=False,
        hash=False,
    )
    witness: ProjectModuleExpressionReferenceFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    aggregate_evidence: ProjectAggregateResultFact | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.kind) is not PackageGraphExpressionLineageKind:
            raise TypeError("Expression lineage requires an exact kind.")
        if type(self.output) not in {PackageGraphFieldRef, PackageGraphLetRef} or (
            type(self.upstream) not in {PackageGraphFieldRef, PackageGraphLetRef}
        ):
            raise TypeError("Expression lineage requires exact typed refs.")
        if self.output.scope is not self.upstream.scope:
            raise ValueError("Expression lineage refs require one snapshot scope.")
        if type(self.role) is not ProjectModuleFactOccurrenceRole:
            raise TypeError("Expression lineage requires an exact role.")
        if type(self.container_position) is not int or self.container_position < 0:
            raise ValueError("Expression lineage container position is invalid.")
        if type(self.input_position) is not int or self.input_position < 0:
            raise ValueError("Expression lineage input position is invalid.")
        if type(self.witness) is not ProjectModuleExpressionReferenceFact:
            raise TypeError("Expression lineage requires an exact input witness.")
        if (
            self.witness.role is not self.role
            or self.witness.container_ordinal != self.container_position
            or self.witness.dependency_ordinal != self.input_position
            or self.witness.status is not ProjectModuleCandidateBucketStatus.CONCRETE
        ):
            raise ValueError("Expression lineage must retain one concrete input.")
        if type(self.owner_witness) is ProjectModuleSelectFact:
            if (
                type(self.output) is not PackageGraphFieldRef
                or self.owner_witness.selected_output_ordinal != self.container_position
                or self.input_position >= len(self.owner_witness.references)
                or self.owner_witness.references[self.input_position]
                is not self.witness
            ):
                raise ValueError("Selected expression lineage owner does not align.")
            expected_kind = (
                PackageGraphExpressionLineageKind.AGGREGATE
                if self.owner_witness.aggregate_result_fact is not None
                else (
                    PackageGraphExpressionLineageKind.LET_OUTPUT
                    if self.owner_witness.field is not None
                    and self.owner_witness.field.provenance is not None
                    and self.owner_witness.field.provenance.kind
                    is ProjectRowFieldProvenanceKind.LET_DERIVED
                    else PackageGraphExpressionLineageKind.COMPUTED
                )
            )
            if self.kind is not expected_kind:
                raise ValueError(
                    "Selected expression lineage kind must retain exact evidence."
                )
        elif type(self.owner_witness) is ProjectModuleLetBindingFact:
            if (
                type(self.output) is not PackageGraphLetRef
                or self.owner_witness.binding_ordinal != self.container_position
                or self.input_position >= len(self.owner_witness.references)
                or self.owner_witness.references[self.input_position]
                is not self.witness
            ):
                raise ValueError("Let expression lineage owner does not align.")
            if self.kind is not PackageGraphExpressionLineageKind.LET_EXPRESSION:
                raise ValueError(
                    "Let expression lineage kind must retain exact evidence."
                )
        else:
            raise TypeError("Expression lineage requires exact owner evidence.")
        if self.kind is PackageGraphExpressionLineageKind.AGGREGATE:
            if (
                type(self.owner_witness) is not ProjectModuleSelectFact
                or type(self.aggregate_evidence) is not ProjectAggregateResultFact
                or self.owner_witness.aggregate_result_fact
                is not self.aggregate_evidence
            ):
                raise ValueError("Aggregate lineage requires exact aggregate evidence.")
        elif self.aggregate_evidence is not None:
            raise ValueError("Non-aggregate lineage forbids aggregate evidence.")


type PackageGraphCurrentWindowUpstreamRef = (
    PackageGraphFieldRef | PackageGraphLetRef | PackageGraphDeclarationRef
)


@dataclass(frozen=True, slots=True)
class PackageGraphCurrentWindowLineage:
    """One existing current-window dependency occurrence, without frame facts."""

    output: PackageGraphFieldRef
    upstream: PackageGraphCurrentWindowUpstreamRef
    role: WindowDependencyRole
    global_position: int
    role_position: int
    output_witness: ProjectModuleWindowOutputFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    witness: WindowDependencyOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.output) is not PackageGraphFieldRef or type(self.upstream) not in {
            PackageGraphFieldRef,
            PackageGraphLetRef,
            PackageGraphDeclarationRef,
        }:
            raise TypeError("Current-window lineage requires exact typed refs.")
        if self.output.scope is not self.upstream.scope:
            raise ValueError("Current-window lineage refs require one snapshot scope.")
        if type(self.role) is not WindowDependencyRole:
            raise TypeError("Current-window lineage requires an exact role.")
        if type(self.output_witness) is not ProjectModuleWindowOutputFact:
            raise TypeError("Current-window lineage requires exact output evidence.")
        if type(self.witness) is not WindowDependencyOccurrence:
            raise TypeError("Current-window lineage requires exact input evidence.")
        if (
            self.output_witness.status
            is not ProjectModuleCandidateBucketStatus.CONCRETE
            or self.output_witness.project_fact is None
            or not any(
                self.witness is occurrence
                for occurrence in self.output_witness.project_fact.dependency_occurrences
            )
            or self.witness.role is not self.role
            or self.witness.global_ordinal != self.global_position
            or self.witness.role_ordinal != self.role_position
        ):
            raise ValueError("Current-window lineage must retain exact input order.")


@dataclass(frozen=True, slots=True)
class PackageGraphRelationLineageState:
    """One exact non-concrete relation-lineage status and reason."""

    declaration: PackageGraphDeclarationRef
    status: ProjectRelationRowSchemaStatus
    reason: ProjectRelationRowSchemaReason
    witness: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.declaration) is not PackageGraphDeclarationRef:
            raise TypeError("Relation lineage state requires a declaration ref.")
        if (
            type(self.status) is not ProjectRelationRowSchemaStatus
            or type(self.reason) is not ProjectRelationRowSchemaReason
        ):
            raise TypeError("Relation lineage state requires exact typed state.")
        if self.status is ProjectRelationRowSchemaStatus.CONCRETE:
            raise ValueError("Relation lineage states retain only non-concrete facts.")
        if (
            type(self.witness) is not ProjectModuleRelationSemanticFacts
            or self.witness.state.status is not self.status
            or self.witness.state.reason is not self.reason
        ):
            raise ValueError("Relation lineage state must retain exact evidence.")


@dataclass(frozen=True, slots=True)
class PackageGraphLetLineageState:
    """One exact non-concrete or absent let-lineage status and reason."""

    declaration: PackageGraphDeclarationRef
    status: ProjectLetScopeFactsStatus
    reason: ProjectLetScopeFactsReason
    witness: ProjectRelationLetScopeFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.declaration) is not PackageGraphDeclarationRef:
            raise TypeError("Let lineage state requires a declaration ref.")
        if (
            type(self.status) is not ProjectLetScopeFactsStatus
            or type(self.reason) is not ProjectLetScopeFactsReason
        ):
            raise TypeError("Let lineage state requires exact typed state.")
        if self.status is ProjectLetScopeFactsStatus.CONCRETE:
            raise ValueError("Let lineage states retain only non-concrete facts.")
        if (
            type(self.witness) is not ProjectRelationLetScopeFacts
            or self.witness.status is not self.status
            or self.witness.reason is not self.reason
        ):
            raise ValueError("Let lineage state must retain exact evidence.")


@dataclass(frozen=True, slots=True)
class PackageGraphAggregateLineageState:
    """One exact non-concrete aggregate/grouped lineage status and reason."""

    declaration: PackageGraphDeclarationRef
    status: ProjectAggregateGroupedClauseReadinessStatus
    reason: ProjectAggregateGroupedClauseReadinessReason
    witness: ProjectAggregateGroupedClauseReadiness = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.declaration) is not PackageGraphDeclarationRef:
            raise TypeError("Aggregate lineage state requires a declaration ref.")
        if type(self.status) is not ProjectAggregateGroupedClauseReadinessStatus or (
            type(self.reason) is not ProjectAggregateGroupedClauseReadinessReason
        ):
            raise TypeError("Aggregate lineage state requires exact typed state.")
        if self.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE:
            raise ValueError("Aggregate lineage states retain only non-concrete facts.")
        if (
            type(self.witness) is not ProjectAggregateGroupedClauseReadiness
            or self.witness.status is not self.status
            or self.witness.reason is not self.reason
        ):
            raise ValueError("Aggregate lineage state must retain exact evidence.")


@dataclass(frozen=True, slots=True)
class PackageGraphExpressionLineageState:
    """One exact unresolved expression-input occurrence without a guessed reason."""

    declaration: PackageGraphDeclarationRef
    role: ProjectModuleFactOccurrenceRole
    container_position: int
    input_position: int
    status: ProjectModuleCandidateBucketStatus
    witness: ProjectModuleExpressionReferenceFact = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.declaration) is not PackageGraphDeclarationRef:
            raise TypeError("Expression lineage state requires a declaration ref.")
        if (
            type(self.role) is not ProjectModuleFactOccurrenceRole
            or type(self.status) is not ProjectModuleCandidateBucketStatus
        ):
            raise TypeError("Expression lineage state requires exact typed state.")
        if self.status is ProjectModuleCandidateBucketStatus.CONCRETE:
            raise ValueError("Expression lineage states retain unresolved inputs only.")
        if (
            type(self.witness) is not ProjectModuleExpressionReferenceFact
            or self.witness.role is not self.role
            or self.witness.container_ordinal != self.container_position
            or self.witness.dependency_ordinal != self.input_position
            or self.witness.status is not self.status
        ):
            raise ValueError("Expression lineage state must retain exact evidence.")


@dataclass(frozen=True, slots=True)
class PackageGraphCurrentWindowLineageState:
    """One exact non-concrete current-window output status and reason."""

    declaration: PackageGraphDeclarationRef
    output_position: int
    status: ProjectModuleCandidateBucketStatus
    reason: str | None
    witness: ProjectModuleWindowOutputFact = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.declaration) is not PackageGraphDeclarationRef:
            raise TypeError("Window lineage state requires a declaration ref.")
        if type(self.output_position) is not int or self.output_position < 0:
            raise ValueError("Window lineage output position is invalid.")
        if type(self.status) is not ProjectModuleCandidateBucketStatus:
            raise TypeError("Window lineage state requires an exact status.")
        if self.status is ProjectModuleCandidateBucketStatus.CONCRETE:
            raise ValueError("Window lineage states retain non-concrete outputs only.")
        if self.reason is not None and (
            type(self.reason) is not str or not self.reason
        ):
            raise ValueError("Window lineage state reason must be non-empty.")
        if (
            type(self.witness) is not ProjectModuleWindowOutputFact
            or self.witness.selected_output_ordinal != self.output_position
            or self.witness.status is not self.status
            or self.witness.reason != self.reason
        ):
            raise ValueError("Window lineage state must retain exact evidence.")


@dataclass(frozen=True, slots=True)
class PackageGraphCapabilityEvaluationRef:
    """One requirement-by-target evaluation coordinate in one snapshot."""

    scope: PackageGraphScope
    requirement: PackageGraphRequirementRef
    target_position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Capability evaluation refs require an exact scope.")
        if type(self.requirement) is not PackageGraphRequirementRef:
            raise TypeError("Capability evaluation refs require a requirement ref.")
        if self.requirement.scope is not self.scope:
            raise ValueError(
                "Capability evaluation refs require the requirement snapshot scope."
            )
        if type(self.target_position) is not int or self.target_position < 0:
            raise ValueError(
                "Capability evaluation target position must be non-negative."
            )


@dataclass(frozen=True, slots=True)
class PackageGraphCatalogEvidenceRef:
    """One selector-by-target catalog evidence coordinate in one snapshot."""

    scope: PackageGraphScope
    selector: PackageGraphSelectorRef
    target_position: int

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Catalog evidence refs require an exact scope.")
        if type(self.selector) is not PackageGraphSelectorRef:
            raise TypeError("Catalog evidence refs require a selector ref.")
        if self.selector.scope is not self.scope:
            raise ValueError(
                "Catalog evidence refs require the selector snapshot scope."
            )
        if type(self.target_position) is not int or self.target_position < 0:
            raise ValueError("Catalog evidence target position must be non-negative.")


@dataclass(frozen=True, slots=True)
class PackageGraphCapabilityEvaluation:
    """One exact upstream checked or blocked requirement-target evaluation."""

    ref: PackageGraphCapabilityEvaluationRef
    selector: PackageGraphSelectorRef | None
    facts: CapabilityInspectionFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    cell: CapabilityCheckingMatrixCell = field(
        repr=False,
        compare=False,
        hash=False,
    )
    evidence: CapabilityRequirementCheck | PackageCapabilityRequirementsBlocked = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphCapabilityEvaluationRef:
            raise TypeError("Capability evaluations require an exact ref.")
        if self.selector is not None:
            if type(self.selector) is not PackageGraphSelectorRef:
                raise TypeError("Capability evaluations require an exact selector ref.")
            if (
                self.selector.scope is not self.ref.scope
                or self.selector.package != self.ref.requirement.package
            ):
                raise ValueError(
                    "Capability evaluation selector requires exact package ownership."
                )
        if type(self.facts) is not CapabilityInspectionFactSet:
            raise TypeError("Capability evaluations require exact inspection facts.")
        if type(self.cell) is not CapabilityCheckingMatrixCell:
            raise TypeError("Capability evaluations require an exact matrix cell.")
        if self.cell.column.position != self.ref.target_position:
            raise ValueError(
                "Capability evaluation ref must retain the target position."
            )
        if self.cell.check is None:
            if (
                type(self.cell.column.result)
                is not PackageCapabilityRequirementsBlocked
                or self.evidence is not self.cell.column.result
            ):
                raise ValueError(
                    "Blocked capability evaluations require exact blocker evidence."
                )
        elif (
            type(self.cell.column.result) is not PackageCapabilityRequirementsChecked
            or type(self.cell.check) is not CapabilityRequirementCheck
            or self.evidence is not self.cell.check
        ):
            raise ValueError(
                "Checked capability evaluations require the exact check evidence."
            )


@dataclass(frozen=True, slots=True)
class PackageGraphCatalogEvidence:
    """One exact catalog/provider/source fact attached to a selector evaluation."""

    ref: PackageGraphCatalogEvidenceRef
    capability: PackageGraphCapabilityEvaluationRef
    facts: ExtensionCatalogInspectionFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    provider: ExtensionCatalogInspectionProviderOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.ref) is not PackageGraphCatalogEvidenceRef:
            raise TypeError("Catalog evidence requires an exact ref.")
        if type(self.capability) is not PackageGraphCapabilityEvaluationRef:
            raise TypeError("Catalog evidence requires a capability evaluation ref.")
        if (
            self.capability.scope is not self.ref.scope
            or self.capability.target_position != self.ref.target_position
        ):
            raise ValueError(
                "Catalog and capability evidence require one snapshot target."
            )
        if type(self.facts) is not ExtensionCatalogInspectionFactSet:
            raise TypeError("Catalog evidence requires exact inspection facts.")
        if type(self.provider) is not ExtensionCatalogInspectionProviderOccurrence:
            raise TypeError("Catalog evidence requires an exact provider occurrence.")


@dataclass(frozen=True, slots=True)
class PackageGraphSnapshot:
    """One immutable ordered package/dependency graph domain snapshot."""

    scope: PackageGraphScope
    packages: tuple[PackageGraphPackage, ...]
    dependencies: tuple[PackageGraphDependency, ...]
    requirement_collections: tuple[PackageGraphRequirementCollection, ...] = ()
    requirements: tuple[PackageGraphRequirement, ...] = ()
    selectors: tuple[PackageGraphSelector, ...] = ()
    capability_evaluations: tuple[PackageGraphCapabilityEvaluation, ...] = ()
    catalog_evidence: tuple[PackageGraphCatalogEvidence, ...] = ()
    modules: tuple[PackageGraphModule, ...] = ()
    declarations: tuple[PackageGraphDeclaration, ...] = ()
    semantic_authorities: tuple[PackageGraphSemanticAuthority, ...] = ()
    fields: tuple[PackageGraphField, ...] = ()
    let_bindings: tuple[PackageGraphLetBinding, ...] = ()
    source_lineage: tuple[PackageGraphSourceLineage, ...] = ()
    projection_lineage: tuple[PackageGraphProjectionLineage, ...] = ()
    expression_lineage: tuple[PackageGraphExpressionLineage, ...] = ()
    current_window_lineage: tuple[PackageGraphCurrentWindowLineage, ...] = ()
    relation_lineage_states: tuple[PackageGraphRelationLineageState, ...] = ()
    let_lineage_states: tuple[PackageGraphLetLineageState, ...] = ()
    aggregate_lineage_states: tuple[PackageGraphAggregateLineageState, ...] = ()
    expression_lineage_states: tuple[PackageGraphExpressionLineageState, ...] = ()
    current_window_lineage_states: tuple[
        PackageGraphCurrentWindowLineageState,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if type(self.scope) is not PackageGraphScope:
            raise TypeError("Package graph snapshots require an exact scope.")
        _require_exact_tuple(
            self.packages,
            PackageGraphPackage,
            "Package graph snapshot packages",
        )
        _require_exact_tuple(
            self.dependencies,
            PackageGraphDependency,
            "Package graph snapshot dependencies",
        )
        _require_exact_tuple(
            self.requirement_collections,
            PackageGraphRequirementCollection,
            "Package graph requirement collections",
        )
        _require_exact_tuple(
            self.requirements,
            PackageGraphRequirement,
            "Package graph requirements",
        )
        _require_exact_tuple(
            self.selectors,
            PackageGraphSelector,
            "Package graph selectors",
        )
        _require_exact_tuple(
            self.capability_evaluations,
            PackageGraphCapabilityEvaluation,
            "Package graph capability evaluations",
        )
        _require_exact_tuple(
            self.catalog_evidence,
            PackageGraphCatalogEvidence,
            "Package graph catalog evidence",
        )
        _require_exact_tuple(
            self.modules,
            PackageGraphModule,
            "Package graph modules",
        )
        _require_exact_tuple(
            self.declarations,
            PackageGraphDeclaration,
            "Package graph declarations",
        )
        _require_exact_tuple(
            self.semantic_authorities,
            PackageGraphSemanticAuthority,
            "Package graph semantic authorities",
        )
        _require_exact_tuple(
            self.fields,
            PackageGraphField,
            "Package graph fields",
        )
        _require_exact_tuple(
            self.let_bindings,
            PackageGraphLetBinding,
            "Package graph let bindings",
        )
        _require_exact_tuple(
            self.source_lineage,
            PackageGraphSourceLineage,
            "Package graph source lineage",
        )
        _require_exact_tuple(
            self.projection_lineage,
            PackageGraphProjectionLineage,
            "Package graph projection lineage",
        )
        _require_exact_tuple(
            self.expression_lineage,
            PackageGraphExpressionLineage,
            "Package graph expression lineage",
        )
        _require_exact_tuple(
            self.current_window_lineage,
            PackageGraphCurrentWindowLineage,
            "Package graph current-window lineage",
        )
        _require_exact_tuple(
            self.relation_lineage_states,
            PackageGraphRelationLineageState,
            "Package graph relation lineage states",
        )
        _require_exact_tuple(
            self.let_lineage_states,
            PackageGraphLetLineageState,
            "Package graph let lineage states",
        )
        _require_exact_tuple(
            self.aggregate_lineage_states,
            PackageGraphAggregateLineageState,
            "Package graph aggregate lineage states",
        )
        _require_exact_tuple(
            self.expression_lineage_states,
            PackageGraphExpressionLineageState,
            "Package graph expression lineage states",
        )
        _require_exact_tuple(
            self.current_window_lineage_states,
            PackageGraphCurrentWindowLineageState,
            "Package graph current-window lineage states",
        )
        if not self.packages:
            raise ValueError(
                "Package graph snapshots require at least one package occurrence."
            )
        if any(package.ref.scope is not self.scope for package in self.packages):
            raise ValueError(
                "Package graph snapshot packages require the owning snapshot scope."
            )
        package_refs = tuple(package.ref for package in self.packages)
        if len(set(package_refs)) != len(package_refs):
            raise ValueError("Package graph snapshots require unique package refs.")
        if any(
            package.ref.position != position
            for position, package in enumerate(self.packages)
        ):
            raise ValueError(
                "Package graph snapshots require dense package positions in tuple order."
            )
        if any(
            dependency.ref.scope is not self.scope for dependency in self.dependencies
        ):
            raise ValueError(
                "Package graph snapshot dependencies require the owning snapshot scope."
            )
        dependency_refs = tuple(dependency.ref for dependency in self.dependencies)
        if len(set(dependency_refs)) != len(dependency_refs):
            raise ValueError("Package graph snapshots require unique dependency refs.")
        for dependency in self.dependencies:
            self.package(dependency.declaring_package)
            target = self.package(dependency.resolved_package)
            if (
                dependency.witness.coordinate != target.coordinate
                or dependency.witness.content_digest_pin != target.content_digest
            ):
                raise ValueError(
                    "Package graph dependency witness must resolve to its exact target."
                )
        _validate_requirement_attribution(self)
        _validate_provenance_attribution(self)
        _validate_module_attribution(self)
        _validate_semantic_lineage_attribution(self)

    def package(self, ref: PackageGraphPackageRef) -> PackageGraphPackage:
        """Resolve one exact owned package ref without semantic fallback."""

        if type(ref) is not PackageGraphPackageRef:
            raise TypeError("Package graph package lookup requires a package ref.")
        if ref.scope is not self.scope:
            raise ValueError("Package graph package ref belongs to a foreign snapshot.")
        if (
            type(ref.position) is not int
            or ref.position < 0
            or ref.position >= len(self.packages)
        ):
            raise ValueError("Package graph package ref does not resolve.")
        package = self.packages[ref.position]
        if package.ref != ref:
            raise ValueError("Package graph package ref does not resolve.")
        return package

    def dependency(
        self,
        ref: PackageGraphDependencyRef,
    ) -> PackageGraphDependency:
        """Resolve one exact owned dependency ref without traversal or indexes."""

        if type(ref) is not PackageGraphDependencyRef:
            raise TypeError(
                "Package graph dependency lookup requires a dependency ref."
            )
        if ref.scope is not self.scope:
            raise ValueError(
                "Package graph dependency ref belongs to a foreign snapshot."
            )
        # ponytail: local graphs use a linear scan; Slice 9 owns derived indexes.
        for dependency in self.dependencies:
            if dependency.ref == ref:
                return dependency
        raise ValueError("Package graph dependency ref was not found.")

    def requirement(
        self,
        ref: PackageGraphRequirementRef,
    ) -> PackageGraphRequirement:
        """Resolve one exact owned requirement ref without key lookup."""

        if type(ref) is not PackageGraphRequirementRef:
            raise TypeError("Requirement lookup requires a requirement ref.")
        if ref.scope is not self.scope:
            raise ValueError("Requirement ref belongs to a foreign snapshot.")
        # ponytail: local attribution uses scans; Slice 9 owns derived indexes.
        for requirement in self.requirements:
            if requirement.ref == ref:
                return requirement
        raise ValueError("Requirement ref was not found.")

    def selector(self, ref: PackageGraphSelectorRef) -> PackageGraphSelector:
        """Resolve one exact owned selector ref without semantic matching."""

        if type(ref) is not PackageGraphSelectorRef:
            raise TypeError("Selector lookup requires a selector ref.")
        if ref.scope is not self.scope:
            raise ValueError("Selector ref belongs to a foreign snapshot.")
        for selector in self.selectors:
            if selector.ref == ref:
                return selector
        raise ValueError("Selector ref was not found.")

    def capability_evaluation(
        self,
        ref: PackageGraphCapabilityEvaluationRef,
    ) -> PackageGraphCapabilityEvaluation:
        """Resolve one exact requirement-target evaluation occurrence."""

        if type(ref) is not PackageGraphCapabilityEvaluationRef:
            raise TypeError("Capability evaluation lookup requires an exact ref.")
        if ref.scope is not self.scope:
            raise ValueError("Capability evaluation ref belongs to a foreign snapshot.")
        # ponytail: local attribution uses scans; Slice 9 owns derived indexes.
        for evaluation in self.capability_evaluations:
            if evaluation.ref == ref:
                return evaluation
        raise ValueError("Capability evaluation ref was not found.")

    def catalog_evidence_occurrence(
        self,
        ref: PackageGraphCatalogEvidenceRef,
    ) -> PackageGraphCatalogEvidence:
        """Resolve one exact selector-target catalog evidence occurrence."""

        if type(ref) is not PackageGraphCatalogEvidenceRef:
            raise TypeError("Catalog evidence lookup requires an exact ref.")
        if ref.scope is not self.scope:
            raise ValueError("Catalog evidence ref belongs to a foreign snapshot.")
        # ponytail: local attribution uses scans; Slice 9 owns derived indexes.
        for evidence in self.catalog_evidence:
            if evidence.ref == ref:
                return evidence
        raise ValueError("Catalog evidence ref was not found.")

    def module(self, ref: PackageGraphModuleRef) -> PackageGraphModule:
        """Resolve one exact package-qualified module occurrence."""

        if type(ref) is not PackageGraphModuleRef:
            raise TypeError("Module lookup requires an exact module ref.")
        if ref.scope is not self.scope:
            raise ValueError("Module ref belongs to a foreign snapshot.")
        # ponytail: local attribution uses scans; Slice 9 owns derived indexes.
        for module in self.modules:
            if module.ref == ref:
                return module
        raise ValueError("Module ref was not found.")

    def declaration(
        self,
        ref: PackageGraphDeclarationRef,
    ) -> PackageGraphDeclaration:
        """Resolve one exact package-qualified declaration occurrence."""

        if type(ref) is not PackageGraphDeclarationRef:
            raise TypeError("Declaration lookup requires an exact declaration ref.")
        if ref.scope is not self.scope:
            raise ValueError("Declaration ref belongs to a foreign snapshot.")
        # ponytail: local attribution uses scans; Slice 9 owns derived indexes.
        for declaration in self.declarations:
            if declaration.ref == ref:
                return declaration
        raise ValueError("Declaration ref was not found.")

    def field(self, ref: PackageGraphFieldRef) -> PackageGraphField:
        """Resolve one exact declaration-qualified semantic field occurrence."""

        if type(ref) is not PackageGraphFieldRef:
            raise TypeError("Field lookup requires an exact field ref.")
        if ref.scope is not self.scope:
            raise ValueError("Field ref belongs to a foreign snapshot.")
        # ponytail: local attribution uses scans; Slice 9 owns derived indexes.
        for graph_field in self.fields:
            if graph_field.ref == ref:
                return graph_field
        raise ValueError("Field ref was not found.")

    def let_binding(self, ref: PackageGraphLetRef) -> PackageGraphLetBinding:
        """Resolve one exact declaration-qualified let-binding occurrence."""

        if type(ref) is not PackageGraphLetRef:
            raise TypeError("Let lookup requires an exact let ref.")
        if ref.scope is not self.scope:
            raise ValueError("Let ref belongs to a foreign snapshot.")
        # ponytail: local attribution uses scans; Slice 9 owns derived indexes.
        for binding in self.let_bindings:
            if binding.ref == ref:
                return binding
        raise ValueError("Let ref was not found.")


class PackageGraphOutcome(StrEnum):
    """Closed terminal outcomes for the private package-graph domain."""

    SUCCESS = "success"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class PackageGraphResult:
    """One complete snapshot or one ordered rejected/error terminal."""

    outcome: PackageGraphOutcome
    snapshot: PackageGraphSnapshot | None = None
    blockers: tuple[PackageLoadPlanBlocker, ...] = ()
    errors: tuple[ProjectDiscoveryError, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if type(self.outcome) is not PackageGraphOutcome:
            raise TypeError("Package graph results require an exact outcome.")
        if (
            self.snapshot is not None
            and type(self.snapshot) is not PackageGraphSnapshot
        ):
            raise TypeError("Package graph results require an exact snapshot.")
        _require_exact_tuple(
            self.blockers,
            PackageLoadPlanBlocker,
            "Package graph result blockers",
        )
        _require_exact_tuple(
            self.errors,
            ProjectDiscoveryError,
            "Package graph result errors",
        )
        _require_exact_tuple(
            self.diagnostics,
            Diagnostic,
            "Package graph result diagnostics",
        )
        has_error_diagnostic = any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        )
        if self.outcome is PackageGraphOutcome.SUCCESS:
            if self.snapshot is None:
                raise ValueError("Successful package graph results require a snapshot.")
            if self.blockers or self.errors or has_error_diagnostic:
                raise ValueError(
                    "Successful package graph results forbid terminal failure evidence."
                )
            return
        if self.outcome is PackageGraphOutcome.REJECTED:
            if self.snapshot is not None:
                raise ValueError("Rejected package graph results forbid a snapshot.")
            if not self.blockers:
                raise ValueError("Rejected package graph results require blockers.")
            if self.errors or has_error_diagnostic:
                raise ValueError(
                    "Rejected package graph results forbid competing error authority."
                )
            return
        if self.snapshot is not None:
            raise ValueError("Error package graph results forbid a snapshot.")
        if self.blockers:
            raise ValueError("Error package graph results forbid blockers.")
        if not self.errors and not has_error_diagnostic:
            raise ValueError(
                "Error package graph results require exact error evidence."
            )


type PackageGraphProvenanceRef = (
    PackageGraphPackageRef
    | PackageGraphRequirementRef
    | PackageGraphSelectorRef
    | PackageGraphCapabilityEvaluationRef
    | PackageGraphCatalogEvidenceRef
    | PackageGraphModuleRef
    | PackageGraphDeclarationRef
    | PackageGraphFieldRef
    | PackageGraphLetRef
)

type PackageGraphDirectProvenanceWitness = (
    PackageGraphDependency
    | PackageGraphRequirement
    | PackageGraphSelector
    | PackageGraphCapabilityEvaluation
    | PackageGraphCatalogEvidence
    | PackageGraphModule
    | PackageGraphDeclaration
    | PackageGraphField
    | PackageGraphLetBinding
    | PackageGraphSourceLineage
    | PackageGraphProjectionLineage
    | PackageGraphExpressionLineage
    | PackageGraphCurrentWindowLineage
)

type PackageGraphWhyNotEvidence = (
    CapabilityRequirementCheck
    | PackageCapabilityRequirementsBlocked
    | ExtensionCatalogInspectionProviderOccurrence
)


@dataclass(frozen=True, slots=True)
class PackageGraphDirectProvenanceStep:
    """One typed direct relationship retaining its exact graph witness."""

    witness: PackageGraphDirectProvenanceWitness

    def __post_init__(self) -> None:
        if type(self.witness) not in {
            PackageGraphDependency,
            PackageGraphRequirement,
            PackageGraphSelector,
            PackageGraphCapabilityEvaluation,
            PackageGraphCatalogEvidence,
            PackageGraphModule,
            PackageGraphDeclaration,
            PackageGraphField,
            PackageGraphLetBinding,
            PackageGraphSourceLineage,
            PackageGraphProjectionLineage,
            PackageGraphExpressionLineage,
            PackageGraphCurrentWindowLineage,
        }:
            raise TypeError("Direct provenance steps require an exact witness.")


@dataclass(frozen=True, slots=True)
class PackageGraphProvenancePath:
    """One ordered path of exact direct provenance occurrence steps."""

    start: PackageGraphPackageRef
    end: PackageGraphProvenanceRef
    steps: tuple[PackageGraphDirectProvenanceStep, ...]

    def __post_init__(self) -> None:
        if type(self.start) is not PackageGraphPackageRef:
            raise TypeError("Provenance paths require an exact package start ref.")
        end_scope = _provenance_ref_scope(self.end)
        if self.start.scope is not end_scope:
            raise ValueError("Provenance path endpoints require one snapshot scope.")
        if (
            type(self.steps) is not tuple
            or not self.steps
            or any(
                type(step) is not PackageGraphDirectProvenanceStep
                for step in self.steps
            )
        ):
            raise TypeError("Provenance paths require exact ordered direct steps.")
        if _direct_step_source(self.steps[0]) != self.start:
            raise ValueError("Provenance path must start at its package ref.")
        for current, following in zip(self.steps, self.steps[1:], strict=False):
            if _direct_step_target(current) != _direct_step_source(following):
                raise ValueError("Provenance path steps must be contiguous.")
        if _direct_step_target(self.steps[-1]) != self.end:
            raise ValueError("Provenance path must terminate at its exact end ref.")
        if any(
            _provenance_ref_scope(_direct_step_source(step)) is not self.start.scope
            or _provenance_ref_scope(_direct_step_target(step)) is not self.start.scope
            for step in self.steps
        ):
            raise ValueError("Provenance path steps require one snapshot scope.")


@dataclass(frozen=True, slots=True)
class PackageGraphWhyNot:
    """One positive provenance path plus exact typed terminal non-success evidence."""

    positive_path: PackageGraphProvenancePath
    terminal_evidence: PackageGraphWhyNotEvidence = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.positive_path) is not PackageGraphProvenancePath:
            raise TypeError("Why-not provenance requires an exact positive path.")
        last_witness = self.positive_path.steps[-1].witness
        if type(self.terminal_evidence) in {
            CapabilityRequirementCheck,
            PackageCapabilityRequirementsBlocked,
        }:
            if (
                type(last_witness) is not PackageGraphCapabilityEvaluation
                or last_witness.evidence is not self.terminal_evidence
            ):
                raise ValueError(
                    "Why-not capability evidence must terminate its exact path."
                )
            if (
                type(self.terminal_evidence) is CapabilityRequirementCheck
                and self.terminal_evidence.status
                is CapabilityRequirementStatus.SATISFIED
            ):
                raise ValueError("Satisfied capability evidence is not why-not.")
            return
        if (
            type(self.terminal_evidence)
            is not ExtensionCatalogInspectionProviderOccurrence
        ):
            raise TypeError(
                "Why-not provenance requires exact typed terminal evidence."
            )
        if (
            type(last_witness) is not PackageGraphCatalogEvidence
            or last_witness.provider is not self.terminal_evidence
        ):
            raise ValueError("Why-not catalog evidence must terminate its exact path.")
        if (
            self.terminal_evidence.selection.selected_catalog_position is not None
            and self.terminal_evidence.lookup.variant
            is ExtensionCatalogInspectionLookupVariant.FOUND
        ):
            raise ValueError("Successful catalog provider evidence is not why-not.")


def _require_exact_tuple(
    values: tuple[object, ...],
    item_type: type[object],
    label: str,
) -> None:
    if type(values) is not tuple or any(
        type(value) is not item_type for value in values
    ):
        raise TypeError(f"{label} require an exact tuple of {item_type.__name__}.")


def _provenance_ref_scope(ref: PackageGraphProvenanceRef) -> PackageGraphScope:
    if type(ref) not in {
        PackageGraphPackageRef,
        PackageGraphRequirementRef,
        PackageGraphSelectorRef,
        PackageGraphCapabilityEvaluationRef,
        PackageGraphCatalogEvidenceRef,
        PackageGraphModuleRef,
        PackageGraphDeclarationRef,
        PackageGraphFieldRef,
        PackageGraphLetRef,
    }:
        raise TypeError("Provenance endpoints require an exact typed graph ref.")
    return ref.scope


def _direct_step_source(
    step: PackageGraphDirectProvenanceStep,
) -> PackageGraphProvenanceRef:
    if type(step) is not PackageGraphDirectProvenanceStep:
        raise TypeError("Direct provenance source requires an exact step.")
    witness = step.witness
    if type(witness) is PackageGraphDependency:
        return witness.declaring_package
    if type(witness) is PackageGraphRequirement:
        return witness.package
    if type(witness) is PackageGraphSelector:
        return witness.requirement
    if type(witness) is PackageGraphCapabilityEvaluation:
        return witness.ref.requirement if witness.selector is None else witness.selector
    if type(witness) is PackageGraphCatalogEvidence:
        return witness.capability
    if type(witness) is PackageGraphModule:
        return witness.package
    if type(witness) is PackageGraphDeclaration:
        return witness.module
    if type(witness) is PackageGraphField:
        return witness.declaration
    if type(witness) is PackageGraphLetBinding:
        return witness.declaration
    if type(witness) is PackageGraphSourceLineage:
        return witness.output
    if type(witness) is PackageGraphProjectionLineage:
        return witness.output
    if type(witness) is PackageGraphExpressionLineage:
        return witness.output
    if type(witness) is PackageGraphCurrentWindowLineage:
        return witness.output
    raise AssertionError("Unsupported direct provenance witness.")


def _direct_step_target(
    step: PackageGraphDirectProvenanceStep,
) -> PackageGraphProvenanceRef:
    if type(step) is not PackageGraphDirectProvenanceStep:
        raise TypeError("Direct provenance target requires an exact step.")
    witness = step.witness
    if type(witness) is PackageGraphDependency:
        return witness.resolved_package
    if type(witness) is PackageGraphRequirement:
        return witness.ref
    if type(witness) is PackageGraphSelector:
        return witness.ref
    if type(witness) is PackageGraphCapabilityEvaluation:
        return witness.ref
    if type(witness) is PackageGraphCatalogEvidence:
        return witness.ref
    if type(witness) is PackageGraphModule:
        return witness.ref
    if type(witness) is PackageGraphDeclaration:
        return witness.ref
    if type(witness) is PackageGraphField:
        return witness.ref
    if type(witness) is PackageGraphLetBinding:
        return witness.ref
    if type(witness) is PackageGraphSourceLineage:
        return witness.upstream
    if type(witness) is PackageGraphProjectionLineage:
        return witness.upstream
    if type(witness) is PackageGraphExpressionLineage:
        return witness.upstream
    if type(witness) is PackageGraphCurrentWindowLineage:
        return witness.upstream
    raise AssertionError("Unsupported direct provenance witness.")


def _resolve_provenance_ref(
    snapshot: PackageGraphSnapshot,
    ref: PackageGraphProvenanceRef,
) -> None:
    if type(ref) is PackageGraphPackageRef:
        snapshot.package(ref)
        return
    if type(ref) is PackageGraphRequirementRef:
        snapshot.requirement(ref)
        return
    if type(ref) is PackageGraphSelectorRef:
        snapshot.selector(ref)
        return
    if type(ref) is PackageGraphCapabilityEvaluationRef:
        snapshot.capability_evaluation(ref)
        return
    if type(ref) is PackageGraphCatalogEvidenceRef:
        snapshot.catalog_evidence_occurrence(ref)
        return
    if type(ref) is PackageGraphModuleRef:
        snapshot.module(ref)
        return
    if type(ref) is PackageGraphDeclarationRef:
        snapshot.declaration(ref)
        return
    if type(ref) is PackageGraphFieldRef:
        snapshot.field(ref)
        return
    if type(ref) is PackageGraphLetRef:
        snapshot.let_binding(ref)
        return
    raise TypeError("Provenance endpoint requires an exact supported graph ref.")


def _package_graph_direct_provenance_steps(
    snapshot: PackageGraphSnapshot,
) -> tuple[PackageGraphDirectProvenanceStep, ...]:
    """Project current direct relationships without storing derived closure."""

    if type(snapshot) is not PackageGraphSnapshot:
        raise TypeError("Direct provenance requires an exact graph snapshot.")
    witnesses: list[PackageGraphDirectProvenanceWitness] = [
        *snapshot.dependencies,
        *snapshot.requirements,
        *snapshot.selectors,
        *snapshot.capability_evaluations,
        *snapshot.catalog_evidence,
        *snapshot.modules,
        *snapshot.declarations,
        *snapshot.fields,
        *snapshot.let_bindings,
        *snapshot.source_lineage,
        *snapshot.projection_lineage,
        *snapshot.expression_lineage,
        *snapshot.current_window_lineage,
    ]
    return tuple(PackageGraphDirectProvenanceStep(witness) for witness in witnesses)


def _derive_package_graph_provenance_paths(
    snapshot: PackageGraphSnapshot,
    start: PackageGraphPackageRef,
    end: PackageGraphProvenanceRef,
) -> tuple[PackageGraphProvenancePath, ...]:
    """Enumerate every current authoritative path in direct-step order."""

    if type(snapshot) is not PackageGraphSnapshot:
        raise TypeError("Provenance derivation requires an exact graph snapshot.")
    if type(start) is not PackageGraphPackageRef:
        raise TypeError("Provenance derivation requires a package start ref.")
    snapshot.package(start)
    _resolve_provenance_ref(snapshot, end)
    if start == end:
        return ()

    direct_steps = _package_graph_direct_provenance_steps(snapshot)
    paths: list[PackageGraphProvenancePath] = []

    # ponytail: local snapshots enumerate paths directly; Slice 9 owns indexes.
    def extend(
        current: PackageGraphProvenanceRef,
        prefix: tuple[PackageGraphDirectProvenanceStep, ...],
        visited: tuple[PackageGraphProvenanceRef, ...],
    ) -> None:
        for step in direct_steps:
            if _direct_step_source(step) != current:
                continue
            target = _direct_step_target(step)
            extended = (*prefix, step)
            if target == end:
                paths.append(PackageGraphProvenancePath(start, end, extended))
                continue
            if target in visited:
                continue
            extend(target, extended, (*visited, target))

    extend(start, (), (start,))
    return tuple(paths)


def _why_not_terminal_evidence(
    snapshot: PackageGraphSnapshot,
    end: PackageGraphCapabilityEvaluationRef | PackageGraphCatalogEvidenceRef,
) -> PackageGraphWhyNotEvidence | None:
    if type(end) is PackageGraphCapabilityEvaluationRef:
        evaluation = snapshot.capability_evaluation(end)
        evidence = evaluation.evidence
        if (
            type(evidence) is CapabilityRequirementCheck
            and evidence.status is CapabilityRequirementStatus.SATISFIED
        ):
            return None
        return evidence
    if type(end) is PackageGraphCatalogEvidenceRef:
        provider = snapshot.catalog_evidence_occurrence(end).provider
        if (
            provider.selection.selected_catalog_position is not None
            and provider.lookup.variant is ExtensionCatalogInspectionLookupVariant.FOUND
        ):
            return None
        return provider
    raise TypeError("Why-not requires a capability or catalog evidence end ref.")


def _derive_package_graph_why_not(
    snapshot: PackageGraphSnapshot,
    start: PackageGraphPackageRef,
    end: PackageGraphCapabilityEvaluationRef | PackageGraphCatalogEvidenceRef,
) -> tuple[PackageGraphWhyNot, ...]:
    """Attach exact typed non-success evidence to every positive path."""

    paths = _derive_package_graph_provenance_paths(snapshot, start, end)
    terminal = _why_not_terminal_evidence(snapshot, end)
    if terminal is None:
        return ()
    return tuple(PackageGraphWhyNot(path, terminal) for path in paths)


def _validate_requirement_attribution(snapshot: PackageGraphSnapshot) -> None:
    if not (
        snapshot.requirement_collections or snapshot.requirements or snapshot.selectors
    ):
        return
    if len(snapshot.requirement_collections) != len(snapshot.packages):
        raise ValueError("Requirement attribution requires one collection per package.")

    expected_requirements: list[
        tuple[PackageGraphPackageRef, CapabilityRequirementOccurrence]
    ] = []
    expected_selectors: list[
        tuple[
            PackageGraphPackageRef,
            int,
            ExtensionSignatureRequirementSelectorOccurrence,
        ]
    ] = []
    for package, collection in zip(
        snapshot.packages,
        snapshot.requirement_collections,
        strict=True,
    ):
        if collection.package != package.ref:
            raise ValueError("Requirement collection order must match package order.")
        binding = collection.binding
        if binding is None:
            continue
        expected_requirements.extend(
            (package.ref, occurrence) for occurrence in binding.requirements.occurrences
        )
        if collection.selectors is not None:
            expected_selectors.extend(
                (package.ref, position, occurrence)
                for position, occurrence in enumerate(collection.selectors.occurrences)
            )

    if len(snapshot.requirements) != len(expected_requirements):
        raise ValueError("Requirement attribution must retain every occurrence.")
    for requirement, (package_ref, witness) in zip(
        snapshot.requirements,
        expected_requirements,
        strict=True,
    ):
        if requirement.package != package_ref or requirement.witness is not witness:
            raise ValueError("Requirement attribution must retain exact package order.")

    if len(snapshot.selectors) != len(expected_selectors):
        raise ValueError("Selector attribution must retain every occurrence.")
    for selector, (package_ref, position, witness) in zip(
        snapshot.selectors,
        expected_selectors,
        strict=True,
    ):
        if (
            selector.package != package_ref
            or selector.ref.position != position
            or selector.witness is not witness
            or selector.requirement
            != PackageGraphRequirementRef(
                snapshot.scope,
                package_ref,
                witness.requirement_position,
            )
        ):
            raise ValueError("Selector attribution must retain exact coverage order.")


def _validate_provenance_attribution(snapshot: PackageGraphSnapshot) -> None:
    if not snapshot.capability_evaluations and not snapshot.catalog_evidence:
        return
    if snapshot.catalog_evidence and not snapshot.capability_evaluations:
        raise ValueError("Catalog evidence requires capability evaluations.")

    capability_refs = tuple(
        evaluation.ref for evaluation in snapshot.capability_evaluations
    )
    if len(set(capability_refs)) != len(capability_refs):
        raise ValueError("Capability evaluations require unique occurrence refs.")
    previous_capability_coordinate: tuple[int, int, int] | None = None
    for evaluation in snapshot.capability_evaluations:
        requirement = snapshot.requirement(evaluation.ref.requirement)
        package_position = requirement.package.position
        collection = snapshot.requirement_collections[package_position]
        matrix = _capability_matrix(evaluation.facts)
        if (
            collection.binding is None
            or matrix.binding is not collection.binding
            or matrix.package is not collection.binding.package
        ):
            raise ValueError(
                "Capability evaluations require exact package binding authority."
            )
        if evaluation.ref.requirement.position >= len(matrix.rows):
            raise ValueError("Capability evaluation requirement does not resolve.")
        row = matrix.rows[evaluation.ref.requirement.position]
        if row.occurrence is not requirement.witness:
            raise ValueError(
                "Capability evaluation must retain its exact requirement witness."
            )
        if evaluation.ref.target_position >= len(row.cells) or (
            evaluation.ref.target_position >= len(matrix.columns)
        ):
            raise ValueError("Capability evaluation target does not resolve.")
        if (
            row.cells[evaluation.ref.target_position] is not evaluation.cell
            or matrix.columns[evaluation.ref.target_position]
            is not evaluation.cell.column
        ):
            raise ValueError("Capability evaluation rejects a grafted matrix cell.")

        selector_matches = tuple(
            selector.ref
            for selector in snapshot.selectors
            if selector.requirement == requirement.ref
        )
        if len(selector_matches) > 1:
            raise ValueError("Capability evaluation selector mapping is ambiguous.")
        expected_selector = None if not selector_matches else selector_matches[0]
        if evaluation.selector != expected_selector:
            raise ValueError(
                "Capability evaluation must retain exact selector attribution."
            )

        coordinate = (
            package_position,
            requirement.ref.position,
            evaluation.ref.target_position,
        )
        if (
            previous_capability_coordinate is not None
            and coordinate <= previous_capability_coordinate
        ):
            raise ValueError(
                "Capability evaluations must retain package-requirement-target order."
            )
        previous_capability_coordinate = coordinate

    for position, evaluation in enumerate(snapshot.capability_evaluations):
        if any(
            earlier.facts is evaluation.facts
            for earlier in snapshot.capability_evaluations[:position]
        ):
            continue
        matrix = _capability_matrix(evaluation.facts)
        package_position = evaluation.ref.requirement.package.position
        requirements = tuple(
            requirement
            for requirement in snapshot.requirements
            if requirement.package.position == package_position
        )
        if len(requirements) != len(matrix.rows):
            raise ValueError(
                "Capability facts must cover every package requirement occurrence."
            )
        expected_refs: list[PackageGraphCapabilityEvaluationRef] = []
        for requirement, row in zip(requirements, matrix.rows, strict=True):
            if row.occurrence is not requirement.witness or len(row.cells) != len(
                matrix.columns
            ):
                raise ValueError(
                    "Capability facts must retain the complete target denominator."
                )
            expected_refs.extend(
                PackageGraphCapabilityEvaluationRef(
                    snapshot.scope,
                    requirement.ref,
                    target_position,
                )
                for target_position in range(len(row.cells))
            )
        actual_refs = tuple(
            candidate.ref
            for candidate in snapshot.capability_evaluations
            if candidate.facts is evaluation.facts
        )
        if actual_refs != tuple(expected_refs):
            raise ValueError(
                "Capability evaluations must retain every fact-set matrix cell."
            )

    catalog_refs = tuple(evidence.ref for evidence in snapshot.catalog_evidence)
    if len(set(catalog_refs)) != len(catalog_refs):
        raise ValueError("Catalog evidence requires unique occurrence refs.")
    previous_catalog_coordinate: tuple[int, int, int] | None = None
    for evidence in snapshot.catalog_evidence:
        capability = snapshot.capability_evaluation(evidence.capability)
        selector = snapshot.selector(evidence.ref.selector)
        if (
            capability.selector != selector.ref
            or capability.ref.requirement != selector.requirement
        ):
            raise ValueError(
                "Catalog evidence must attach to the exact selector evaluation."
            )
        inspection = _catalog_inspection(evidence.facts)
        provider_context = (
            capability.cell.column.context.extension_signature_provider_context
        )
        selector_position = selector.ref.position
        if (
            provider_context is None
            or inspection.context is not provider_context
            or selector_position >= len(inspection.provider_occurrences)
            or inspection.provider_occurrences[selector_position]
            is not evidence.provider
        ):
            raise ValueError(
                "Catalog evidence rejects foreign provider context authority."
            )
        if evidence.provider.requirement_position != selector.requirement.position:
            raise ValueError(
                "Catalog provider occurrence must retain exact requirement coverage."
            )
        check = capability.cell.check
        if (
            type(check) is not CapabilityRequirementCheck
            or type(capability.cell.column.result)
            is not PackageCapabilityRequirementsChecked
            or check.extension_signature_provider_authority is None
        ):
            raise ValueError(
                "Catalog evidence requires checked extension provider authority."
            )
        authority = check.extension_signature_provider_authority
        requirement = snapshot.requirement(capability.ref.requirement)
        if authority.requirement is not requirement.witness:
            raise ValueError(
                "Catalog evidence requires exact capability requirement authority."
            )
        if (
            authority.selector_occurrence
            is not provider_context.selectors.occurrences[selector_position]
            or authority.selection_occurrence
            is not provider_context.selections[selector_position]
        ):
            raise ValueError(
                "Catalog evidence requires exact selector and selection witnesses."
            )

        coordinate = (
            selector.package.position,
            evidence.ref.target_position,
            selector.ref.position,
        )
        if (
            previous_catalog_coordinate is not None
            and coordinate <= previous_catalog_coordinate
        ):
            raise ValueError(
                "Catalog evidence must retain package-target-selector order."
            )
        previous_catalog_coordinate = coordinate

    for evaluation in snapshot.capability_evaluations:
        matches = tuple(
            evidence
            for evidence in snapshot.catalog_evidence
            if evidence.capability == evaluation.ref
        )
        provider_context = (
            evaluation.cell.column.context.extension_signature_provider_context
        )
        requires_catalog = (
            evaluation.selector is not None
            and type(evaluation.cell.column.result)
            is PackageCapabilityRequirementsChecked
            and provider_context is not None
            and bool(provider_context.selectors.occurrences)
        )
        if len(matches) != int(requires_catalog):
            raise ValueError(
                "Catalog evidence coverage must match checked selector evaluations."
            )


def _validate_module_attribution(snapshot: PackageGraphSnapshot) -> None:
    if not snapshot.modules and not snapshot.declarations:
        return
    if snapshot.declarations and not snapshot.modules:
        raise ValueError("Declaration attribution requires graph modules.")

    module_refs = tuple(module.ref for module in snapshot.modules)
    if len(set(module_refs)) != len(module_refs):
        raise ValueError("Package graph modules require unique occurrence refs.")
    previous_module_coordinate: tuple[int, int] | None = None
    for module in snapshot.modules:
        package = snapshot.package(module.package)
        authority = module.package_authority
        if (
            _package_coordinate(authority) != package.coordinate
            or _package_content_digest(authority) != package.content_digest
        ):
            raise ValueError("Graph module retains foreign package authority.")
        expected_role = (
            PackageInspectionPackageRole.ROOT
            if type(authority) is LoadedRootPackage
            else PackageInspectionPackageRole.DEPENDENCY
        )
        if package.role is not expected_role:
            raise ValueError("Graph module package role disagrees with its authority.")
        coordinate = (module.package.position, module.ref.position)
        if previous_module_coordinate is not None and (
            coordinate <= previous_module_coordinate
        ):
            raise ValueError(
                "Graph modules must retain package then module occurrence order."
            )
        previous_module_coordinate = coordinate

    for package in snapshot.packages:
        modules = tuple(
            module for module in snapshot.modules if module.package == package.ref
        )
        if not modules:
            continue
        authority = modules[0].package_authority
        if len(modules) != len(authority.modules) or any(
            module.package_authority is not authority
            or module.ref.position != position
            or module.witness is not authority.modules[position]
            for position, module in enumerate(modules)
        ):
            raise ValueError(
                "Graph modules must retain every exact loaded module occurrence."
            )

    declaration_refs = tuple(declaration.ref for declaration in snapshot.declarations)
    if len(set(declaration_refs)) != len(declaration_refs):
        raise ValueError("Graph declarations require unique occurrence refs.")
    expected_declarations = tuple(
        (module.ref, position, definition)
        for module in snapshot.modules
        for position, definition in enumerate(module.witness.script.definitions)
    )
    if len(snapshot.declarations) != len(expected_declarations):
        raise ValueError("Graph declarations must retain every module definition.")
    for declaration, (module_ref, position, definition) in zip(
        snapshot.declarations,
        expected_declarations,
        strict=True,
    ):
        if (
            declaration.module != module_ref
            or declaration.ref.position != position
            or declaration.witness is not definition
        ):
            raise ValueError(
                "Graph declarations must retain exact module-local occurrence order."
            )


type _PackageGraphSemanticProjection = tuple[
    tuple[PackageGraphSemanticAuthority, ...],
    tuple[PackageGraphField, ...],
    tuple[PackageGraphLetBinding, ...],
    tuple[PackageGraphSourceLineage, ...],
    tuple[PackageGraphProjectionLineage, ...],
    tuple[PackageGraphExpressionLineage, ...],
    tuple[PackageGraphCurrentWindowLineage, ...],
    tuple[PackageGraphRelationLineageState, ...],
    tuple[PackageGraphLetLineageState, ...],
    tuple[PackageGraphAggregateLineageState, ...],
    tuple[PackageGraphExpressionLineageState, ...],
    tuple[PackageGraphCurrentWindowLineageState, ...],
]


def _build_semantic_lineage_projection(
    scope: PackageGraphScope,
    packages: tuple[PackageGraphPackage, ...],
    modules: tuple[PackageGraphModule, ...],
    declarations: tuple[PackageGraphDeclaration, ...],
    facts: tuple[ProjectModulePackageNeutralIdentityFactSet, ...],
) -> _PackageGraphSemanticProjection:
    """Project exact existing semantic facts without resolving semantics again."""

    semantic_authorities = tuple(
        PackageGraphSemanticAuthority(package=package.ref, witness=authority)
        for package, authority in zip(packages, facts, strict=True)
    )
    relations: dict[
        PackageGraphDeclarationRef,
        ProjectModuleRelationSemanticFacts,
    ] = {}

    for package, authority in zip(packages, facts, strict=True):
        package_modules = tuple(
            module for module in modules if module.package == package.ref
        )
        if len(authority.module_assets) != len(package_modules):
            raise ValueError(
                "Semantic authority must cover every package module occurrence."
            )
        for module, asset in zip(package_modules, authority.module_assets, strict=True):
            source_bytes = asset.snapshot.source_text.encode("utf-8")
            if (
                asset.position != module.ref.position
                or asset.module != module.witness.identity
                or source_bytes != module.witness.source.content
                or asset.digest.byte_count != len(source_bytes)
                or asset.digest.digest != asset.snapshot.sha256
            ):
                raise ValueError(
                    "Semantic authority must retain exact package module bytes and order."
                )

        package_declarations = tuple(
            declaration
            for declaration in declarations
            if declaration.module.package == package.ref
        )
        if len(authority.declaration_assets) != len(package_declarations):
            raise ValueError(
                "Semantic authority must cover every package declaration occurrence."
            )
        for declaration in package_declarations:
            matches = tuple(
                asset
                for asset in authority.declaration_assets
                if asset.occurrence.module_position == declaration.module.position
                and asset.declaration_position == declaration.ref.position
            )
            if len(matches) != 1:
                raise ValueError(
                    "Semantic declaration attribution must resolve exactly once."
                )
            asset = matches[0]
            if asset.identity.namespace is ProjectSymbolNamespace.RELATION:
                if len(asset.semantic_facts) != 1:
                    raise ValueError(
                        "Relation declarations require one exact semantic fact."
                    )
                relation = asset.semantic_facts[0]
                if relation.owner is not asset.occurrence:
                    raise ValueError(
                        "Relation semantic facts require exact declaration evidence."
                    )
                relations[declaration.ref] = relation
            elif asset.semantic_facts:
                raise ValueError(
                    "Non-relation declarations forbid relation semantic facts."
                )

    fields: list[PackageGraphField] = []
    field_refs: set[PackageGraphFieldRef] = set()

    def add_field(graph_field: PackageGraphField) -> None:
        if graph_field.ref in field_refs:
            existing = next(item for item in fields if item.ref == graph_field.ref)
            if (
                existing.kind is not graph_field.kind
                or existing.name != graph_field.name
                or existing.semantic_field is not graph_field.semantic_field
            ):
                raise ValueError("Semantic field occurrence attribution is ambiguous.")
            return
        field_refs.add(graph_field.ref)
        fields.append(graph_field)

    for declaration in declarations:
        package_ref = declaration.module.package
        authority = facts[package_ref.position]
        relation = relations.get(declaration.ref)
        origins = tuple(
            origin
            for origin in authority.authority.attribution.source_field_origins
            if _row_field_owner_matches_declaration(
                origin.source_field,
                declaration.ref,
            )
            or _row_field_owner_matches_declaration(
                origin.shape_field,
                declaration.ref,
            )
        )
        for origin in origins:
            identity = (
                origin.source_field
                if _row_field_owner_matches_declaration(
                    origin.source_field,
                    declaration.ref,
                )
                else origin.shape_field
            )
            semantic_field = None
            if identity.kind is ProjectModuleRowFieldKind.SOURCE_FIELD:
                if relation is None or relation.state.schema is None:
                    raise ValueError(
                        "Concrete source field requires exact semantic schema evidence."
                    )
                schema_fields = tuple(relation.state.schema.fields.values())
                if identity.field_position >= len(schema_fields):
                    raise ValueError("Source field position does not resolve.")
                semantic_field = schema_fields[identity.field_position]
                if semantic_field.name != identity.name:
                    raise ValueError("Source field name disagrees with semantic order.")
            add_field(
                PackageGraphField(
                    ref=PackageGraphFieldRef(
                        scope,
                        declaration.ref,
                        identity.field_position,
                    ),
                    declaration=declaration.ref,
                    kind=identity.kind,
                    name=identity.name,
                    semantic_field=semantic_field,
                    witness=identity,
                )
            )
        if relation is None:
            continue
        for select in relation.select_facts:
            if select.field is None:
                continue
            add_field(
                PackageGraphField(
                    ref=PackageGraphFieldRef(
                        scope,
                        declaration.ref,
                        select.selected_output_ordinal,
                    ),
                    declaration=declaration.ref,
                    kind=ProjectModuleRowFieldKind.RELATION_OUTPUT,
                    name=select.field.name,
                    semantic_field=select.field,
                    witness=select,
                )
            )

    let_bindings = tuple(
        PackageGraphLetBinding(
            ref=PackageGraphLetRef(
                scope,
                declaration.ref,
                binding.binding_ordinal,
            ),
            declaration=declaration.ref,
            witness=binding,
        )
        for declaration in declarations
        for relation in (
            () if declaration.ref not in relations else (relations[declaration.ref],)
        )
        for binding in relation.let_bindings
    )

    source_lineage: list[PackageGraphSourceLineage] = []
    projection_lineage: list[PackageGraphProjectionLineage] = []
    expression_lineage: list[PackageGraphExpressionLineage] = []
    current_window_lineage: list[PackageGraphCurrentWindowLineage] = []
    relation_states: list[PackageGraphRelationLineageState] = []
    let_states: list[PackageGraphLetLineageState] = []
    aggregate_states: list[PackageGraphAggregateLineageState] = []
    expression_states: list[PackageGraphExpressionLineageState] = []
    window_states: list[PackageGraphCurrentWindowLineageState] = []

    for package, authority in zip(packages, facts, strict=True):
        for origin in authority.authority.attribution.source_field_origins:
            source_lineage.append(
                PackageGraphSourceLineage(
                    output=_field_ref_for_identity(
                        fields,
                        package.ref,
                        origin.source_field,
                    ),
                    upstream=_field_ref_for_identity(
                        fields,
                        package.ref,
                        origin.shape_field,
                    ),
                    witness=origin,
                )
            )

        projection_by_reference: dict[object, ProjectModuleRowLineageHop] = {}
        for lineage in authority.authority.attribution.row_lineages:
            if lineage.status is not ProjectRelationRowSchemaStatus.CONCRETE:
                continue
            for field_lineage in lineage.fields:
                for path in field_lineage.paths:
                    for hop in path.hops:
                        previous = projection_by_reference.get(hop.reference)
                        if previous is not None:
                            if previous != hop:
                                raise ValueError(
                                    "Projection occurrence has conflicting lineage hops."
                                )
                            continue
                        projection_by_reference[hop.reference] = hop
                        projection_lineage.append(
                            PackageGraphProjectionLineage(
                                kind=hop.projection_kind,
                                output=_field_ref_for_identity(
                                    fields,
                                    package.ref,
                                    hop.output_field,
                                ),
                                upstream=_field_ref_for_identity(
                                    fields,
                                    package.ref,
                                    hop.upstream_field,
                                ),
                                witness=hop,
                            )
                        )

    projection_outputs = {item.output for item in projection_lineage}
    for declaration in declarations:
        relation = relations.get(declaration.ref)
        if relation is None:
            continue
        if relation.state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
            relation_states.append(
                PackageGraphRelationLineageState(
                    declaration=declaration.ref,
                    status=relation.state.status,
                    reason=relation.state.reason,
                    witness=relation,
                )
            )
        let_scope = relation.let_scope_facts
        if let_scope is not None and (
            let_scope.status is not ProjectLetScopeFactsStatus.CONCRETE
        ):
            let_states.append(
                PackageGraphLetLineageState(
                    declaration=declaration.ref,
                    status=let_scope.status,
                    reason=let_scope.reason,
                    witness=let_scope,
                )
            )
        readiness = relation.aggregate_grouped_clause_readiness
        if readiness is not None and (
            readiness.status
            is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
        ):
            aggregate_states.append(
                PackageGraphAggregateLineageState(
                    declaration=declaration.ref,
                    status=readiness.status,
                    reason=readiness.reason,
                    witness=readiness,
                )
            )

        all_references = tuple(
            reference
            for binding in relation.let_bindings
            for reference in binding.references
        ) + tuple(
            reference
            for select in relation.select_facts
            for reference in select.references
        )
        expression_states.extend(
            PackageGraphExpressionLineageState(
                declaration=declaration.ref,
                role=reference.role,
                container_position=reference.container_ordinal,
                input_position=reference.dependency_ordinal,
                status=reference.status,
                witness=reference,
            )
            for reference in all_references
            if reference.status is not ProjectModuleCandidateBucketStatus.CONCRETE
        )

        if (
            let_scope is not None
            and let_scope.status is ProjectLetScopeFactsStatus.CONCRETE
        ):
            for binding in relation.let_bindings:
                output = PackageGraphLetRef(
                    scope,
                    declaration.ref,
                    binding.binding_ordinal,
                )
                for reference in binding.references:
                    if (
                        reference.status
                        is not ProjectModuleCandidateBucketStatus.CONCRETE
                    ):
                        continue
                    expression_lineage.append(
                        PackageGraphExpressionLineage(
                            kind=PackageGraphExpressionLineageKind.LET_EXPRESSION,
                            output=output,
                            upstream=_expression_reference_target(
                                reference,
                                relation,
                                declaration.ref,
                                fields,
                                let_bindings,
                                relations,
                            ),
                            role=reference.role,
                            container_position=reference.container_ordinal,
                            input_position=reference.dependency_ordinal,
                            owner_witness=binding,
                            witness=reference,
                        )
                    )

        if relation.state.status is ProjectRelationRowSchemaStatus.CONCRETE:
            for select in relation.select_facts:
                if select.field is None:
                    continue
                output = PackageGraphFieldRef(
                    scope,
                    declaration.ref,
                    select.selected_output_ordinal,
                )
                if output in projection_outputs:
                    continue
                if select.aggregate_result_fact is not None:
                    kind = PackageGraphExpressionLineageKind.AGGREGATE
                elif (
                    select.field.provenance is not None
                    and select.field.provenance.kind
                    is ProjectRowFieldProvenanceKind.LET_DERIVED
                ):
                    kind = PackageGraphExpressionLineageKind.LET_OUTPUT
                else:
                    kind = PackageGraphExpressionLineageKind.COMPUTED
                for reference in select.references:
                    if (
                        reference.status
                        is not ProjectModuleCandidateBucketStatus.CONCRETE
                    ):
                        continue
                    expression_lineage.append(
                        PackageGraphExpressionLineage(
                            kind=kind,
                            output=output,
                            upstream=_expression_reference_target(
                                reference,
                                relation,
                                declaration.ref,
                                fields,
                                let_bindings,
                                relations,
                            ),
                            role=reference.role,
                            container_position=reference.container_ordinal,
                            input_position=reference.dependency_ordinal,
                            owner_witness=select,
                            witness=reference,
                            aggregate_evidence=select.aggregate_result_fact,
                        )
                    )

        for window in relation.window_outputs:
            if (
                window.status is not ProjectModuleCandidateBucketStatus.CONCRETE
                or window.project_fact is None
            ):
                window_states.append(
                    PackageGraphCurrentWindowLineageState(
                        declaration=declaration.ref,
                        output_position=window.selected_output_ordinal,
                        status=window.status,
                        reason=window.reason,
                        witness=window,
                    )
                )
                continue
            output = PackageGraphFieldRef(
                scope,
                declaration.ref,
                window.selected_output_ordinal,
            )
            _field_from_ref(fields, output)
            for occurrence in window.project_fact.dependency_occurrences:
                current_window_lineage.append(
                    PackageGraphCurrentWindowLineage(
                        output=output,
                        upstream=_window_dependency_target(
                            occurrence,
                            relation,
                            declaration.ref,
                            fields,
                            let_bindings,
                            relations,
                        ),
                        role=occurrence.role,
                        global_position=occurrence.global_ordinal,
                        role_position=occurrence.role_ordinal,
                        output_witness=window,
                        witness=occurrence,
                    )
                )

    return (
        semantic_authorities,
        tuple(fields),
        tuple(let_bindings),
        tuple(source_lineage),
        tuple(projection_lineage),
        tuple(expression_lineage),
        tuple(current_window_lineage),
        tuple(relation_states),
        tuple(let_states),
        tuple(aggregate_states),
        tuple(expression_states),
        tuple(window_states),
    )


def _row_field_owner_matches_declaration(
    identity: ProjectModuleRowFieldIdentity,
    declaration: PackageGraphDeclarationRef,
) -> bool:
    owner = identity.owner
    return (
        owner.module_position == declaration.module.position
        and owner.declaration_position == declaration.position
    )


def _field_ref_for_identity(
    fields: list[PackageGraphField],
    package: PackageGraphPackageRef,
    identity: ProjectModuleRowFieldIdentity,
) -> PackageGraphFieldRef:
    matches = tuple(
        graph_field.ref
        for graph_field in fields
        if graph_field.declaration.module.package == package
        and _row_field_owner_matches_declaration(identity, graph_field.declaration)
        and graph_field.ref.position == identity.field_position
        and graph_field.kind is identity.kind
        and graph_field.name == identity.name
    )
    if len(matches) != 1:
        raise ValueError("Semantic field identity must resolve exactly once.")
    return matches[0]


def _field_from_ref(
    fields: list[PackageGraphField],
    ref: PackageGraphFieldRef,
) -> PackageGraphField:
    matches = tuple(graph_field for graph_field in fields if graph_field.ref == ref)
    if len(matches) != 1:
        raise ValueError("Semantic field ref must resolve exactly once.")
    return matches[0]


def _declaration_ref_for_owner(
    relations: dict[PackageGraphDeclarationRef, ProjectModuleRelationSemanticFacts],
    package: PackageGraphPackageRef,
    owner: object,
) -> PackageGraphDeclarationRef:
    module_position = getattr(owner, "module_position", None)
    declaration_position = getattr(owner, "declaration_position", None)
    matches = tuple(
        declaration
        for declaration, relation in relations.items()
        if declaration.module.package == package
        and declaration.module.position == module_position
        and declaration.position == declaration_position
        and relation.owner.identity == getattr(owner, "identity", None)
    )
    if len(matches) != 1:
        raise ValueError("Semantic declaration owner must resolve exactly once.")
    return matches[0]


def _expression_reference_target(
    reference: ProjectModuleExpressionReferenceFact,
    relation: ProjectModuleRelationSemanticFacts,
    declaration: PackageGraphDeclarationRef,
    fields: list[PackageGraphField],
    let_bindings: tuple[PackageGraphLetBinding, ...],
    relations: dict[PackageGraphDeclarationRef, ProjectModuleRelationSemanticFacts],
) -> PackageGraphExpressionUpstreamRef:
    if reference.status is not ProjectModuleCandidateBucketStatus.CONCRETE:
        raise ValueError("Only concrete expression inputs create lineage.")
    if reference.input_field is not None:
        if relation.resolution is None:
            raise ValueError("Concrete input field requires exact relation resolution.")
        target_declaration = _declaration_ref_for_owner(
            relations,
            declaration.module.package,
            relation.resolution.target_symbol.target_occurrence,
        )
        matches = tuple(
            graph_field.ref
            for graph_field in fields
            if graph_field.declaration == target_declaration
            and graph_field.semantic_field is reference.input_field
        )
    elif reference.let_candidates:
        matches = tuple(
            binding.ref
            for binding in let_bindings
            if binding.declaration == declaration
            and any(
                binding.witness.binding is item for item in reference.let_candidates
            )
        )
    else:
        matches = tuple(
            graph_field.ref
            for graph_field in fields
            if graph_field.declaration == declaration
            and type(graph_field.witness) is ProjectModuleSelectFact
            and any(
                graph_field.witness.item is item
                for item in reference.selected_output_candidates
            )
        )
    if len(matches) != 1:
        raise ValueError("Concrete expression input must resolve exactly once.")
    return matches[0]


def _window_dependency_target(
    occurrence: WindowDependencyOccurrence,
    relation: ProjectModuleRelationSemanticFacts,
    declaration: PackageGraphDeclarationRef,
    fields: list[PackageGraphField],
    let_bindings: tuple[PackageGraphLetBinding, ...],
    relations: dict[PackageGraphDeclarationRef, ProjectModuleRelationSemanticFacts],
) -> PackageGraphCurrentWindowUpstreamRef:
    if relation.resolution is None:
        raise ValueError("Concrete window input requires exact relation resolution.")
    target_declaration = _declaration_ref_for_owner(
        relations,
        declaration.module.package,
        relation.resolution.target_symbol.target_occurrence,
    )
    target = occurrence.target
    if target.kind is ProjectRowDependencyNodeKind.RELATION_INPUT:
        return target_declaration
    if target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD:
        target_relation = relations[target_declaration]
        if target_relation.state.schema is None or target.field_name is None:
            raise ValueError("Window upstream field requires exact schema evidence.")
        semantic_field = target_relation.state.schema.fields.get(target.field_name)
        matches: tuple[PackageGraphCurrentWindowUpstreamRef, ...] = tuple(
            graph_field.ref
            for graph_field in fields
            if graph_field.declaration == target_declaration
            and graph_field.semantic_field is semantic_field
        )
    elif target.kind is ProjectRowDependencyNodeKind.LET_BINDING:
        matches = tuple(
            binding.ref
            for binding in let_bindings
            if binding.declaration == declaration
            and binding.witness.binding.name == target.binding_name
        )
    elif target.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
        matches = tuple(
            graph_field.ref
            for graph_field in fields
            if graph_field.declaration == declaration
            and graph_field.name == target.output_name
        )
    else:
        raise ValueError("Window input has an unsupported existing target kind.")
    if len(matches) != 1:
        raise ValueError("Concrete window input must resolve exactly once.")
    return matches[0]


def _validate_semantic_lineage_attribution(snapshot: PackageGraphSnapshot) -> None:
    semantic_collections = (
        snapshot.fields,
        snapshot.let_bindings,
        snapshot.source_lineage,
        snapshot.projection_lineage,
        snapshot.expression_lineage,
        snapshot.current_window_lineage,
        snapshot.relation_lineage_states,
        snapshot.let_lineage_states,
        snapshot.aggregate_lineage_states,
        snapshot.expression_lineage_states,
        snapshot.current_window_lineage_states,
    )
    if not snapshot.semantic_authorities:
        if any(semantic_collections):
            raise ValueError("Semantic graph facts require exact package authorities.")
        return
    if len(snapshot.semantic_authorities) != len(snapshot.packages) or any(
        authority.package != package.ref
        for package, authority in zip(
            snapshot.packages,
            snapshot.semantic_authorities,
            strict=True,
        )
    ):
        raise ValueError("Semantic authorities must retain exact package order.")

    actual_projection: _PackageGraphSemanticProjection = (
        snapshot.semantic_authorities,
        *semantic_collections,
    )
    expected_projection = _build_semantic_lineage_projection(
        snapshot.scope,
        snapshot.packages,
        snapshot.modules,
        snapshot.declarations,
        tuple(authority.witness for authority in snapshot.semantic_authorities),
    )
    for actual, expected in zip(
        actual_projection,
        expected_projection,
        strict=True,
    ):
        if len(actual) != len(expected) or any(
            not _same_semantic_projection_item(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected, strict=True)
        ):
            raise ValueError(
                "Semantic graph requires the complete exact semantic projection."
            )


def _same_semantic_projection_item(actual: object, expected: object) -> bool:
    """Compare one projected carrier plus every excluded authority witness."""

    if type(actual) is not type(expected) or actual != expected:
        return False
    if type(actual) is PackageGraphSemanticAuthority:
        assert type(expected) is PackageGraphSemanticAuthority
        return actual.witness is expected.witness
    if type(actual) is PackageGraphField:
        assert type(expected) is PackageGraphField
        return (
            actual.semantic_field is expected.semantic_field
            and actual.witness is expected.witness
        )
    if type(actual) is PackageGraphLetBinding:
        assert type(expected) is PackageGraphLetBinding
        return actual.witness is expected.witness
    if type(actual) is PackageGraphSourceLineage:
        assert type(expected) is PackageGraphSourceLineage
        return actual.witness is expected.witness
    if type(actual) is PackageGraphProjectionLineage:
        assert type(expected) is PackageGraphProjectionLineage
        return actual.witness is expected.witness
    if type(actual) is PackageGraphExpressionLineage:
        assert type(expected) is PackageGraphExpressionLineage
        return (
            actual.owner_witness is expected.owner_witness
            and actual.witness is expected.witness
            and actual.aggregate_evidence is expected.aggregate_evidence
        )
    if type(actual) is PackageGraphCurrentWindowLineage:
        assert type(expected) is PackageGraphCurrentWindowLineage
        return (
            actual.output_witness is expected.output_witness
            and actual.witness is expected.witness
        )
    if type(actual) in {
        PackageGraphRelationLineageState,
        PackageGraphLetLineageState,
        PackageGraphAggregateLineageState,
        PackageGraphExpressionLineageState,
        PackageGraphCurrentWindowLineageState,
    }:
        return getattr(actual, "witness") is getattr(expected, "witness")
    raise AssertionError("Unsupported semantic projection carrier.")


def _capability_matrix(
    facts: CapabilityInspectionFactSet,
) -> PackageCapabilityCheckingMatrix:
    if type(facts) is not CapabilityInspectionFactSet:
        raise TypeError("Package graph provenance requires exact capability facts.")
    inspection = facts.inspection
    authority = facts.authority
    if (
        inspection is not authority.inspection
        or facts.canonical_bytes is not authority.canonical_bytes
        or inspection.matrix is not authority.matrix
        or type(inspection.matrix) is not PackageCapabilityCheckingMatrix
    ):
        raise ValueError("Package graph provenance rejects grafted capability facts.")
    return inspection.matrix


def _catalog_inspection(
    facts: ExtensionCatalogInspectionFactSet,
) -> ExtensionCatalogInspection:
    if type(facts) is not ExtensionCatalogInspectionFactSet:
        raise TypeError("Package graph provenance requires exact catalog facts.")
    inspection = facts.inspection
    authority = facts.authority
    if (
        inspection is not authority.inspection
        or facts.canonical_bytes is not authority.canonical_bytes
        or inspection.context is not authority.context
        or type(inspection) is not ExtensionCatalogInspection
    ):
        raise ValueError("Package graph provenance rejects grafted catalog facts.")
    return inspection


def _validated_provenance_binding(
    expected: PackageCapabilityRequirementBinding | None,
    facts: CapabilityInspectionFactSet,
    package: object,
) -> PackageCapabilityRequirementBinding | None:
    matrix = _capability_matrix(facts)
    if matrix.package is not package:
        raise ValueError(
            "Capability facts must retain their exact package occurrence order."
        )
    actual = matrix.binding
    if expected is None:
        if actual is not None:
            raise ValueError("Undeclared package requirements reject supplied binding.")
        return None
    if type(actual) is not PackageCapabilityRequirementBinding:
        raise ValueError("Declared package requirements require supplied binding.")
    if actual.package is not expected.package:
        raise ValueError("Capability facts retain a foreign package binding.")
    actual_requirements = actual.requirements
    expected_requirements = expected.requirements
    if actual_requirements.identity != expected_requirements.identity or len(
        actual_requirements.occurrences
    ) != len(expected_requirements.occurrences):
        raise ValueError(
            "Capability facts do not match the package requirement collection."
        )
    for actual_occurrence, expected_occurrence in zip(
        actual_requirements.occurrences,
        expected_requirements.occurrences,
        strict=True,
    ):
        if (
            actual_occurrence.position != expected_occurrence.position
            or actual_occurrence.key != expected_occurrence.key
        ):
            raise ValueError(
                "Capability facts do not match exact requirement occurrences."
            )
    return actual


def _validate_provider_selectors(
    matrix: PackageCapabilityCheckingMatrix,
    selectors: ExtensionSignatureRequirementSelectors | None,
) -> None:
    expected = () if selectors is None else selectors.occurrences
    for context in matrix.contexts:
        provider_context = context.extension_signature_provider_context
        if provider_context is None:
            continue
        if (
            matrix.binding is None
            or provider_context.selectors.requirements
            is not matrix.binding.requirements
        ):
            raise ValueError(
                "Provider contexts require exact requirement collection authority."
            )
        actual = provider_context.selectors.occurrences
        if len(actual) != len(expected) or any(
            left.requirement_position != right.requirement_position
            or left.selector != right.selector
            for left, right in zip(actual, expected, strict=True)
        ):
            raise ValueError(
                "Provider contexts do not map exactly to graph selector occurrences."
            )


def _selector_ref_for_requirement(
    selectors: tuple[PackageGraphSelector, ...],
    requirement: PackageGraphRequirementRef,
) -> PackageGraphSelectorRef | None:
    matches = tuple(
        selector.ref for selector in selectors if selector.requirement == requirement
    )
    if len(matches) > 1:
        raise ValueError("Requirement provenance rejects ambiguous selector mapping.")
    return None if not matches else matches[0]


def _build_capability_evaluations(
    scope: PackageGraphScope,
    requirement_groups: tuple[tuple[PackageGraphRequirement, ...], ...],
    selector_groups: tuple[tuple[PackageGraphSelector, ...], ...],
    capability_facts: tuple[CapabilityInspectionFactSet, ...],
) -> tuple[PackageGraphCapabilityEvaluation, ...]:
    evaluations: list[PackageGraphCapabilityEvaluation] = []
    for requirements, selectors, facts in zip(
        requirement_groups,
        selector_groups,
        capability_facts,
        strict=True,
    ):
        matrix = _capability_matrix(facts)
        if len(matrix.rows) != len(requirements):
            raise ValueError(
                "Capability facts must retain every graph requirement occurrence."
            )
        for requirement, row in zip(requirements, matrix.rows, strict=True):
            if row.occurrence is not requirement.witness:
                raise ValueError(
                    "Capability facts must retain exact graph requirement witnesses."
                )
            if len(row.cells) != len(matrix.columns):
                raise ValueError(
                    "Capability facts must retain the complete target denominator."
                )
            selector = _selector_ref_for_requirement(selectors, requirement.ref)
            for target_position, cell in enumerate(row.cells):
                if (
                    cell.column is not matrix.columns[target_position]
                    or cell.column.position != target_position
                ):
                    raise ValueError(
                        "Capability facts must retain exact target context order."
                    )
                evidence: (
                    CapabilityRequirementCheck | PackageCapabilityRequirementsBlocked
                )
                if cell.check is None:
                    if (
                        type(cell.column.result)
                        is not PackageCapabilityRequirementsBlocked
                    ):
                        raise ValueError(
                            "Capability cells require checked or blocked evidence."
                        )
                    evidence = cell.column.result
                else:
                    if (
                        type(cell.column.result)
                        is not PackageCapabilityRequirementsChecked
                        or type(cell.check) is not CapabilityRequirementCheck
                    ):
                        raise ValueError(
                            "Capability cells require exact checked evidence."
                        )
                    evidence = cell.check
                evaluations.append(
                    PackageGraphCapabilityEvaluation(
                        ref=PackageGraphCapabilityEvaluationRef(
                            scope,
                            requirement.ref,
                            target_position,
                        ),
                        selector=selector,
                        facts=facts,
                        cell=cell,
                        evidence=evidence,
                    )
                )
    return tuple(evaluations)


def _build_catalog_evidence(
    scope: PackageGraphScope,
    selector_groups: tuple[tuple[PackageGraphSelector, ...], ...],
    capability_facts: tuple[CapabilityInspectionFactSet, ...],
    catalog_facts: tuple[ExtensionCatalogInspectionFactSet | None, ...],
) -> tuple[PackageGraphCatalogEvidence, ...]:
    expected_slots = sum(
        len(_capability_matrix(facts).columns) for facts in capability_facts
    )
    if len(catalog_facts) != expected_slots:
        raise ValueError(
            "Catalog facts require one exact slot per package target context."
        )
    evidence: list[PackageGraphCatalogEvidence] = []
    slot_position = 0
    for selectors, capability in zip(
        selector_groups,
        capability_facts,
        strict=True,
    ):
        matrix = _capability_matrix(capability)
        for column in matrix.columns:
            facts = catalog_facts[slot_position]
            slot_position += 1
            provider_context = column.context.extension_signature_provider_context
            requires_facts = (
                type(column.result) is PackageCapabilityRequirementsChecked
                and provider_context is not None
                and bool(provider_context.selectors.occurrences)
            )
            if not requires_facts:
                if facts is not None:
                    raise ValueError(
                        "Non-provider target contexts forbid catalog evidence."
                    )
                continue
            if type(facts) is not ExtensionCatalogInspectionFactSet:
                raise ValueError(
                    "Checked selector contexts require exact catalog evidence."
                )
            inspection = _catalog_inspection(facts)
            if inspection.context is not provider_context:
                raise ValueError(
                    "Catalog evidence requires the exact provider target context."
                )
            if len(inspection.provider_occurrences) != len(selectors):
                raise ValueError(
                    "Catalog evidence must retain every selector occurrence."
                )
            for selector, provider in zip(
                selectors,
                inspection.provider_occurrences,
                strict=True,
            ):
                if provider.requirement_position != selector.requirement.position:
                    raise ValueError(
                        "Catalog evidence must retain exact selector coverage."
                    )
                capability_ref = PackageGraphCapabilityEvaluationRef(
                    scope,
                    selector.requirement,
                    column.position,
                )
                evidence.append(
                    PackageGraphCatalogEvidence(
                        ref=PackageGraphCatalogEvidenceRef(
                            scope,
                            selector.ref,
                            column.position,
                        ),
                        capability=capability_ref,
                        facts=facts,
                        provider=provider,
                    )
                )
    return tuple(evidence)


def _build_package_graph(
    facts: PackageInspectionFactSet,
    *,
    capability_facts: tuple[CapabilityInspectionFactSet, ...] | None = None,
    extension_catalog_facts: (
        tuple[ExtensionCatalogInspectionFactSet | None, ...] | None
    ) = None,
    module_identity_facts: (
        tuple[ProjectModulePackageNeutralIdentityFactSet, ...] | None
    ) = None,
) -> PackageGraphResult:
    """Construct one package graph from exact retained inspection/plan authority."""

    if type(facts) is not PackageInspectionFactSet:
        raise TypeError("Package graph construction requires exact inspection facts.")
    inspection = facts.inspection
    if (
        type(inspection) is not PackageInspection
        or inspection is not facts.authority.inspection
        or facts.canonical_bytes is not facts.authority.canonical_bytes
        or inspection.plan_result is not facts.authority.plan_result
    ):
        return _package_graph_construction_error(
            "inspection facts do not retain one exact authority",
        )

    plan_result = inspection.plan_result
    try:
        if inspection.outcome is PackageInspectionOutcome.SUCCESS:
            if capability_facts is None:
                if extension_catalog_facts is not None:
                    raise ValueError("Catalog facts require explicit capability facts.")
            else:
                if (
                    type(capability_facts) is not tuple
                    or len(capability_facts) != len(inspection.packages)
                    or any(
                        type(item) is not CapabilityInspectionFactSet
                        for item in capability_facts
                    )
                ):
                    raise ValueError(
                        "Capability facts require one exact entry per package."
                    )
                if type(extension_catalog_facts) is not tuple or any(
                    item is not None
                    and type(item) is not ExtensionCatalogInspectionFactSet
                    for item in extension_catalog_facts
                ):
                    raise ValueError(
                        "Catalog facts require an exact ordered slot tuple."
                    )
            if module_identity_facts is not None and (
                type(module_identity_facts) is not tuple
                or len(module_identity_facts) != len(inspection.packages)
                or any(
                    type(item) is not ProjectModulePackageNeutralIdentityFactSet
                    for item in module_identity_facts
                )
            ):
                raise ValueError(
                    "Semantic facts require one exact joined authority per package."
                )
            scope = PackageGraphScope()
            packages = tuple(
                PackageGraphPackage(
                    ref=PackageGraphPackageRef(scope, package.position),
                    coordinate=package.coordinate,
                    content_digest=package.content_digest,
                    role=package.role,
                )
                for package in inspection.packages
            )
            dependencies: list[PackageGraphDependency] = []
            requirement_collections: list[PackageGraphRequirementCollection] = []
            requirements: list[PackageGraphRequirement] = []
            selectors: list[PackageGraphSelector] = []
            modules: list[PackageGraphModule] = []
            declarations: list[PackageGraphDeclaration] = []
            requirement_groups: list[tuple[PackageGraphRequirement, ...]] = []
            selector_groups: list[tuple[PackageGraphSelector, ...]] = []
            for package in inspection.packages:
                declaring_ref = PackageGraphPackageRef(scope, package.position)
                for dependency in package.dependencies:
                    dependencies.append(
                        PackageGraphDependency(
                            ref=PackageGraphDependencyRef(
                                scope,
                                declaring_ref,
                                dependency.position,
                            ),
                            declaring_package=declaring_ref,
                            resolved_package=PackageGraphPackageRef(
                                scope,
                                dependency.target_package_position,
                            ),
                            witness=dependency.edge.occurrence,
                        )
                    )
                package_authority = package.entry.package
                for module_witness in package_authority.modules:
                    module_ref = PackageGraphModuleRef(
                        scope,
                        declaring_ref,
                        module_witness.position,
                    )
                    modules.append(
                        PackageGraphModule(
                            ref=module_ref,
                            package=declaring_ref,
                            package_authority=package_authority,
                            witness=module_witness,
                        )
                    )
                    declarations.extend(
                        PackageGraphDeclaration(
                            ref=PackageGraphDeclarationRef(
                                scope,
                                module_ref,
                                position,
                            ),
                            module=module_ref,
                            witness=definition,
                        )
                        for position, definition in enumerate(
                            module_witness.script.definitions
                        )
                    )
                binding = _package_capability_requirement_binding(package_authority)
                package_capability_facts = (
                    None
                    if capability_facts is None
                    else capability_facts[package.position]
                )
                if package_capability_facts is not None:
                    binding = _validated_provenance_binding(
                        binding,
                        package_capability_facts,
                        package_authority,
                    )
                selector_authority = _package_extension_signature_requirement_selectors(
                    package_authority,
                    binding,
                )
                if package_capability_facts is not None:
                    _validate_provider_selectors(
                        _capability_matrix(package_capability_facts),
                        selector_authority,
                    )
                requirement_collections.append(
                    PackageGraphRequirementCollection(
                        package=declaring_ref,
                        declaration=(
                            PackageGraphRequirementDeclaration.UNDECLARED
                            if binding is None
                            else PackageGraphRequirementDeclaration.DECLARED
                        ),
                        binding=binding,
                        selectors=selector_authority,
                    )
                )
                package_requirements = (
                    ()
                    if binding is None
                    else tuple(
                        PackageGraphRequirement(
                            ref=PackageGraphRequirementRef(
                                scope,
                                declaring_ref,
                                occurrence.position,
                            ),
                            package=declaring_ref,
                            witness=occurrence,
                        )
                        for occurrence in binding.requirements.occurrences
                    )
                )
                requirements.extend(package_requirements)
                requirement_groups.append(package_requirements)
                package_selectors = (
                    ()
                    if selector_authority is None
                    else tuple(
                        PackageGraphSelector(
                            ref=PackageGraphSelectorRef(
                                scope,
                                declaring_ref,
                                position,
                            ),
                            package=declaring_ref,
                            requirement=PackageGraphRequirementRef(
                                scope,
                                declaring_ref,
                                occurrence.requirement_position,
                            ),
                            witness=occurrence,
                        )
                        for position, occurrence in enumerate(
                            selector_authority.occurrences
                        )
                    )
                )
                selectors.extend(package_selectors)
                selector_groups.append(package_selectors)
            capability_evaluations: tuple[
                PackageGraphCapabilityEvaluation,
                ...,
            ] = ()
            catalog_evidence: tuple[PackageGraphCatalogEvidence, ...] = ()
            if capability_facts is not None:
                assert extension_catalog_facts is not None
                capability_evaluations = _build_capability_evaluations(
                    scope,
                    tuple(requirement_groups),
                    tuple(selector_groups),
                    capability_facts,
                )
                catalog_evidence = _build_catalog_evidence(
                    scope,
                    tuple(selector_groups),
                    capability_facts,
                    extension_catalog_facts,
                )
            semantic_projection: _PackageGraphSemanticProjection = (
                (),
                (),
                (),
                (),
                (),
                (),
                (),
                (),
                (),
                (),
                (),
                (),
            )
            if module_identity_facts is not None:
                semantic_projection = _build_semantic_lineage_projection(
                    scope,
                    packages,
                    tuple(modules),
                    tuple(declarations),
                    module_identity_facts,
                )
            (
                semantic_authorities,
                graph_fields,
                let_bindings,
                source_lineage,
                projection_lineage,
                expression_lineage,
                current_window_lineage,
                relation_lineage_states,
                let_lineage_states,
                aggregate_lineage_states,
                expression_lineage_states,
                current_window_lineage_states,
            ) = semantic_projection
            snapshot = PackageGraphSnapshot(
                scope=scope,
                packages=packages,
                dependencies=tuple(dependencies),
                requirement_collections=tuple(requirement_collections),
                requirements=tuple(requirements),
                selectors=tuple(selectors),
                capability_evaluations=capability_evaluations,
                catalog_evidence=catalog_evidence,
                modules=tuple(modules),
                declarations=tuple(declarations),
                semantic_authorities=semantic_authorities,
                fields=graph_fields,
                let_bindings=let_bindings,
                source_lineage=source_lineage,
                projection_lineage=projection_lineage,
                expression_lineage=expression_lineage,
                current_window_lineage=current_window_lineage,
                relation_lineage_states=relation_lineage_states,
                let_lineage_states=let_lineage_states,
                aggregate_lineage_states=aggregate_lineage_states,
                expression_lineage_states=expression_lineage_states,
                current_window_lineage_states=current_window_lineage_states,
            )
            return PackageGraphResult(
                PackageGraphOutcome.SUCCESS,
                snapshot,
                diagnostics=plan_result.diagnostics,
            )
        if inspection.outcome is PackageInspectionOutcome.REJECTED:
            return PackageGraphResult(
                PackageGraphOutcome.REJECTED,
                blockers=plan_result.blockers,
                diagnostics=plan_result.diagnostics,
            )
        if inspection.outcome is PackageInspectionOutcome.ERROR:
            return PackageGraphResult(
                PackageGraphOutcome.ERROR,
                errors=plan_result.errors,
                diagnostics=plan_result.diagnostics,
            )
        raise ValueError("Package inspection requires an exact outcome.")
    except (AttributeError, TypeError, ValueError) as error:
        return _package_graph_construction_error(str(error))


def _package_graph_construction_error(message: str) -> PackageGraphResult:
    return PackageGraphResult(
        PackageGraphOutcome.ERROR,
        errors=(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                f"Package graph construction failed: {message}",
            ),
        ),
    )
