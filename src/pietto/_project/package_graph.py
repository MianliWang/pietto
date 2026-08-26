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
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspection,
    ExtensionCatalogInspectionFactSet,
    ExtensionCatalogInspectionLookupVariant,
    ExtensionCatalogInspectionProviderOccurrence,
)
from pietto._project.model import ProjectDiscoveryError, ProjectDiscoveryErrorKind
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
)

type PackageGraphDirectProvenanceWitness = (
    PackageGraphDependency
    | PackageGraphRequirement
    | PackageGraphSelector
    | PackageGraphCapabilityEvaluation
    | PackageGraphCatalogEvidence
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
    assert type(witness) is PackageGraphCatalogEvidence
    return witness.capability


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
    assert type(witness) is PackageGraphCatalogEvidence
    return witness.ref


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
