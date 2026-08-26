"""Private Phase 59 package-graph value model and runtime scope authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
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
    PackageDependencyOccurrence,
    PackageLoadPlanBlocker,
)
from pietto._project.package_manifest import (
    PackageCoordinate,
    _is_valid_content_digest_pin,
)
from pietto.errors import Diagnostic, Severity
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


@dataclass(frozen=True, slots=True)
class PackageGraphSnapshot:
    """One immutable ordered package/dependency graph domain snapshot."""

    scope: PackageGraphScope
    packages: tuple[PackageGraphPackage, ...]
    dependencies: tuple[PackageGraphDependency, ...]
    requirement_collections: tuple[PackageGraphRequirementCollection, ...] = ()
    requirements: tuple[PackageGraphRequirement, ...] = ()
    selectors: tuple[PackageGraphSelector, ...] = ()

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


def _require_exact_tuple(
    values: tuple[object, ...],
    item_type: type[object],
    label: str,
) -> None:
    if type(values) is not tuple or any(
        type(value) is not item_type for value in values
    ):
        raise TypeError(f"{label} require an exact tuple of {item_type.__name__}.")


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


def _build_package_graph(facts: PackageInspectionFactSet) -> PackageGraphResult:
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
                binding = _package_capability_requirement_binding(package.entry.package)
                selector_authority = _package_extension_signature_requirement_selectors(
                    package.entry.package,
                    binding,
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
                if binding is not None:
                    requirements.extend(
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
                if selector_authority is not None:
                    selectors.extend(
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
            snapshot = PackageGraphSnapshot(
                scope=scope,
                packages=packages,
                dependencies=tuple(dependencies),
                requirement_collections=tuple(requirement_collections),
                requirements=tuple(requirements),
                selectors=tuple(selectors),
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
    except (TypeError, ValueError) as error:
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
