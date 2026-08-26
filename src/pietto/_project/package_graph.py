"""Private Phase 59 package-graph value model and runtime scope authority."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto._project.model import ProjectDiscoveryError, ProjectDiscoveryErrorKind
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


@dataclass(frozen=True, slots=True)
class PackageGraphSnapshot:
    """One immutable ordered package/dependency graph domain snapshot."""

    scope: PackageGraphScope
    packages: tuple[PackageGraphPackage, ...]
    dependencies: tuple[PackageGraphDependency, ...]

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
            snapshot = PackageGraphSnapshot(
                scope=scope,
                packages=packages,
                dependencies=tuple(dependencies),
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
