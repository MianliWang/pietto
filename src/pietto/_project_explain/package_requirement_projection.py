"""Private package and requirement provenance projection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
)
from pietto._project.capability_inspection import (
    CapabilityInspection,
    CapabilityInspectionFactSet,
    CapabilityInspectionFormat,
    CapabilityInspectionKey,
    CapabilityInspectionPackage,
    CapabilityInspectionPackageRole,
    CapabilityInspectionRequirement,
    CapabilityInspectionRequirementDeclaration,
)
from pietto._project.package_inspection import (
    PackageInspection,
    PackageInspectionAsset,
    PackageInspectionAssetKind,
    PackageInspectionDependency,
    PackageInspectionFactSet,
    PackageInspectionFormat,
    PackageInspectionOutcome,
    PackageInspectionPackage,
    PackageInspectionPackageRole,
    PackageCoordinate,
)
from pietto._project.package_load_plan import (
    DependencyLocatorKind,
    PackageLoadPlan,
)
from .model import (
    ProjectExplainLogicalPath,
    ProjectExplainLogicalPathKind,
    ProjectExplainRequirementStage,
)
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey
from pietto.semantic.capability_profiles import (
    CapabilityRequirementOccurrence,
)
from pietto.errors import Severity

__all__: tuple[str, ...] = ()

_LOWER_HEX = frozenset("0123456789abcdef")


class ProjectExplainPackageRole(StrEnum):
    ROOT = "root"
    DEPENDENCY = "dependency"


class ProjectExplainPackageAssetKind(StrEnum):
    MODULE_SOURCE = "module_source"


class ProjectExplainDependencyLocatorKind(StrEnum):
    LOCAL_DIRECTORY = "local_directory"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainPackageCoordinate:
    namespace: str
    name: str
    release: str

    def __post_init__(self) -> None:
        _require_non_empty_text(self.namespace, "package coordinate namespace")
        _require_non_empty_text(self.name, "package coordinate name")
        _require_non_empty_text(self.release, "package coordinate release")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainPackageAsset:
    position: int
    kind: ProjectExplainPackageAssetKind
    path: ProjectExplainLogicalPath

    def __post_init__(self) -> None:
        _require_position(self.position, "package asset position")
        if type(self.kind) is not ProjectExplainPackageAssetKind:
            raise TypeError("Project Explain package assets require an exact kind.")
        _require_logical_path(
            self.path,
            ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
            "package asset path",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainDirectDependency:
    position: int
    target_package_position: int
    coordinate: ProjectExplainPackageCoordinate
    content_digest_pin: str
    locator_kind: ProjectExplainDependencyLocatorKind
    project_path: ProjectExplainLogicalPath

    def __post_init__(self) -> None:
        _require_position(self.position, "dependency position")
        _require_position(self.target_package_position, "dependency target position")
        if type(self.coordinate) is not ProjectExplainPackageCoordinate:
            raise TypeError("Project Explain dependencies require an exact coordinate.")
        _require_sha256(self.content_digest_pin, "dependency content digest pin")
        if type(self.locator_kind) is not ProjectExplainDependencyLocatorKind:
            raise TypeError("Project Explain dependencies require an exact locator.")
        _require_logical_path(
            self.project_path,
            ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            "dependency project path",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainPackage:
    position: int
    role: ProjectExplainPackageRole
    coordinate: ProjectExplainPackageCoordinate
    project_path: ProjectExplainLogicalPath
    content_digest: str
    assets: tuple[ProjectExplainPackageAsset, ...]
    dependencies: tuple[ProjectExplainDirectDependency, ...]

    def __post_init__(self) -> None:
        _require_position(self.position, "package position")
        if type(self.role) is not ProjectExplainPackageRole:
            raise TypeError("Project Explain packages require an exact role.")
        if type(self.coordinate) is not ProjectExplainPackageCoordinate:
            raise TypeError("Project Explain packages require an exact coordinate.")
        _require_logical_path(
            self.project_path,
            ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            "package project path",
        )
        _require_sha256(self.content_digest, "package content digest")
        _require_dense_tuple(
            self.assets,
            ProjectExplainPackageAsset,
            "package assets",
        )
        _require_dense_tuple(
            self.dependencies,
            ProjectExplainDirectDependency,
            "package dependencies",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainRequirementCollectionIdentity:
    namespace: str
    name: str

    def __post_init__(self) -> None:
        _require_non_empty_text(self.namespace, "requirement namespace")
        _require_non_empty_text(self.name, "requirement name")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainCapabilityKey:
    domain: CapabilityDomain
    subject: str | None
    operation: str | None
    operands: tuple[str, ...]
    context: str | None
    dialect: str | None
    extension: str | None

    def __post_init__(self) -> None:
        if type(self.domain) is not CapabilityDomain:
            raise TypeError("Project Explain capability keys require an exact domain.")
        subject = _require_optional_nonblank_text(self.subject, "capability subject")
        operation = _require_optional_nonblank_text(
            self.operation,
            "capability operation",
        )
        if subject is None and operation is None:
            raise ValueError(
                "Project Explain capability keys require a subject or operation."
            )
        if type(self.operands) is not tuple:
            raise TypeError("Project Explain capability operands must be a tuple.")
        for operand in self.operands:
            _require_nonblank_text(operand, "capability operand")
        _require_optional_nonblank_text(self.context, "capability context")
        dialect = _require_optional_nonblank_text(
            self.dialect,
            "capability dialect",
        )
        extension = _require_optional_nonblank_text(
            self.extension,
            "capability extension",
        )
        if extension is not None and dialect is None:
            raise ValueError("Project Explain capability extensions require a dialect.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainRequirementCollection:
    declared_by: int
    requested_by: int
    package_role: ProjectExplainPackageRole
    identity: ProjectExplainRequirementCollectionIdentity
    requirement_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_position(self.declared_by, "collection declaring package")
        _require_position(self.requested_by, "collection requesting package")
        if type(self.package_role) is not ProjectExplainPackageRole:
            raise TypeError("Requirement collections require an exact package role.")
        if type(self.identity) is not ProjectExplainRequirementCollectionIdentity:
            raise TypeError("Requirement collections require an exact identity.")
        _require_ordered_positions(
            self.requirement_positions,
            "collection requirement positions",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainRequirementRequest:
    position: int
    stage: ProjectExplainRequirementStage
    declared_by: int
    requested_by: int
    package_role: ProjectExplainPackageRole
    collection: ProjectExplainRequirementCollectionIdentity
    occurrence_position: int
    key: ProjectExplainCapabilityKey

    def __post_init__(self) -> None:
        _require_position(self.position, "requirement position")
        if (
            type(self.stage) is not ProjectExplainRequirementStage
            or self.stage is not ProjectExplainRequirementStage.REQUEST
        ):
            raise ValueError("Slice 3 requirements must be REQUEST records.")
        _require_position(self.declared_by, "requirement declaring package")
        _require_position(self.requested_by, "requirement requesting package")
        if type(self.package_role) is not ProjectExplainPackageRole:
            raise TypeError("Requirements require an exact package role.")
        if type(self.collection) is not ProjectExplainRequirementCollectionIdentity:
            raise TypeError("Requirements require an exact collection identity.")
        _require_position(self.occurrence_position, "requirement occurrence position")
        if type(self.key) is not ProjectExplainCapabilityKey:
            raise TypeError("Requirements require an exact detached capability key.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainPackageRequirementProjection:
    root_package_position: int
    packages: tuple[ProjectExplainPackage, ...]
    requirement_collections: tuple[ProjectExplainRequirementCollection, ...]
    requirements: tuple[ProjectExplainRequirementRequest, ...]

    def __post_init__(self) -> None:
        _require_position(self.root_package_position, "root package position")
        _require_dense_tuple(self.packages, ProjectExplainPackage, "packages")
        if not self.packages:
            raise ValueError("Project Explain projections require packages.")
        if self.root_package_position >= len(self.packages):
            raise ValueError("The root package position must name a package.")
        roots = tuple(
            package
            for package in self.packages
            if package.role is ProjectExplainPackageRole.ROOT
        )
        if len(roots) != 1 or roots[0].position != self.root_package_position:
            raise ValueError("Project Explain projections require one exact root.")
        _validate_dependency_references(self.packages)
        _require_exact_tuple(
            self.requirement_collections,
            ProjectExplainRequirementCollection,
            "requirement collections",
        )
        _require_dense_tuple(
            self.requirements,
            ProjectExplainRequirementRequest,
            "requirements",
        )
        _validate_requirement_references(
            self.root_package_position,
            self.packages,
            self.requirement_collections,
            self.requirements,
        )


def _project_package_requirement_provenance(
    package_facts: PackageInspectionFactSet,
    capability_facts: tuple[CapabilityInspectionFactSet, ...],
) -> ProjectExplainPackageRequirementProjection:
    """Project exact private authorities without reloading or rechecking."""

    inspection = _require_package_authority(package_facts)
    if type(capability_facts) is not tuple or any(
        type(facts) is not CapabilityInspectionFactSet for facts in capability_facts
    ):
        raise TypeError("Slice 3 requires an exact capability fact-set tuple.")
    if len(capability_facts) != len(inspection.packages):
        raise ValueError("Slice 3 requires one capability fact set per package.")

    bindings = tuple(
        _require_capability_authority(facts, package)
        for package, facts in zip(
            inspection.packages,
            capability_facts,
            strict=True,
        )
    )
    packages = tuple(_project_package(package) for package in inspection.packages)
    root_package_position = next(
        package.position
        for package in packages
        if package.role is ProjectExplainPackageRole.ROOT
    )
    collections: list[ProjectExplainRequirementCollection] = []
    requirements: list[ProjectExplainRequirementRequest] = []

    for package, facts, binding in zip(
        packages,
        capability_facts,
        bindings,
        strict=True,
    ):
        if binding is None:
            continue
        private_requirements = facts.inspection.requirements
        identity = ProjectExplainRequirementCollectionIdentity(
            namespace=binding.requirements.identity.namespace,
            name=binding.requirements.identity.name,
        )
        first_position = len(requirements)
        for private_requirement in private_requirements:
            requirements.append(
                ProjectExplainRequirementRequest(
                    position=len(requirements),
                    stage=ProjectExplainRequirementStage.REQUEST,
                    declared_by=package.position,
                    requested_by=root_package_position,
                    package_role=package.role,
                    collection=identity,
                    occurrence_position=private_requirement.position,
                    key=_project_capability_key(private_requirement.key),
                )
            )
        collections.append(
            ProjectExplainRequirementCollection(
                declared_by=package.position,
                requested_by=root_package_position,
                package_role=package.role,
                identity=identity,
                requirement_positions=tuple(range(first_position, len(requirements))),
            )
        )

    return ProjectExplainPackageRequirementProjection(
        root_package_position=root_package_position,
        packages=packages,
        requirement_collections=tuple(collections),
        requirements=tuple(requirements),
    )


def _require_package_authority(
    facts: PackageInspectionFactSet,
) -> PackageInspection:
    if type(facts) is not PackageInspectionFactSet:
        raise TypeError("Slice 3 requires an exact package inspection fact set.")
    if (
        facts.inspection is not facts.authority.inspection
        or facts.canonical_bytes is not facts.authority.canonical_bytes
    ):
        raise ValueError("Slice 3 rejects grafted package inspection authority.")
    inspection = facts.inspection
    if (
        type(inspection) is not PackageInspection
        or inspection.format is not PackageInspectionFormat.PACKAGE_INSPECTION_V1
        or inspection.outcome is not PackageInspectionOutcome.SUCCESS
        or inspection.plan_result is not facts.authority.plan_result
        or type(inspection.plan_result.plan) is not PackageLoadPlan
        or inspection.errors
        or inspection.rejections
        or inspection.plan_result.errors
        or inspection.plan_result.blockers
        or any(
            diagnostic.severity is Severity.ERROR
            for diagnostic in inspection.plan_result.diagnostics
        )
    ):
        raise ValueError("Slice 3 requires one successful package inspection.")
    if (
        type(inspection.packages) is not tuple
        or inspection.package_count != len(inspection.packages)
        or not inspection.packages
        or any(
            type(package) is not PackageInspectionPackage
            for package in inspection.packages
        )
    ):
        raise ValueError("Slice 3 requires exact ordered inspected packages.")
    plan = inspection.plan_result.plan
    assert type(plan) is PackageLoadPlan
    if len(plan.entries) != len(inspection.packages):
        raise ValueError("Package inspection and load-plan counts must agree.")
    for position, (package, entry) in enumerate(
        zip(inspection.packages, plan.entries, strict=True)
    ):
        if (
            package.position != position
            or package.entry is not entry
            or entry.position != position
            or type(package.role) is not PackageInspectionPackageRole
            or type(package.coordinate) is not PackageCoordinate
            or type(package.assets) is not tuple
            or any(
                type(asset) is not PackageInspectionAsset for asset in package.assets
            )
            or tuple(asset.position for asset in package.assets)
            != tuple(range(len(package.assets)))
            or type(package.dependencies) is not tuple
            or any(
                type(dependency) is not PackageInspectionDependency
                for dependency in package.dependencies
            )
            or tuple(dependency.position for dependency in package.dependencies)
            != tuple(range(len(package.dependencies)))
        ):
            raise ValueError("Package inspection order must retain exact plan entries.")
    roots = tuple(
        package
        for package in inspection.packages
        if package.role is PackageInspectionPackageRole.ROOT
    )
    if (
        len(roots) != 1
        or inspection.root_coordinate is None
        or roots[0].coordinate != inspection.root_coordinate
    ):
        raise ValueError("Package inspection must retain one exact root.")
    return inspection


def _require_capability_authority(
    facts: CapabilityInspectionFactSet,
    package: PackageInspectionPackage,
) -> PackageCapabilityRequirementBinding | None:
    if (
        facts.inspection is not facts.authority.inspection
        or facts.canonical_bytes is not facts.authority.canonical_bytes
    ):
        raise ValueError("Slice 3 rejects grafted capability inspection authority.")
    inspection = facts.inspection
    if (
        type(inspection) is not CapabilityInspection
        or inspection.format is not CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1
        or type(inspection.package) is not CapabilityInspectionPackage
        or inspection.matrix is not facts.authority.matrix
        or inspection.package.package is not package.entry.package
        or inspection.matrix.package is not package.entry.package
        or type(inspection.requirements) is not tuple
        or any(
            type(requirement) is not CapabilityInspectionRequirement
            for requirement in inspection.requirements
        )
    ):
        raise ValueError("Capability facts must retain exact package authority order.")
    expected_role = (
        CapabilityInspectionPackageRole.ROOT
        if package.role is PackageInspectionPackageRole.ROOT
        else CapabilityInspectionPackageRole.DEPENDENCY
    )
    coordinate = package.coordinate
    if (
        inspection.package.role is not expected_role
        or inspection.package.namespace != coordinate.identity.namespace
        or inspection.package.name != coordinate.identity.name
        or inspection.package.release != coordinate.exact_version
        or inspection.package.content_digest != package.content_digest
    ):
        raise ValueError("Capability and package detached identity must agree exactly.")

    binding = inspection.matrix.binding
    if inspection.requirement_declaration is (
        CapabilityInspectionRequirementDeclaration.UNDECLARED
    ):
        if (
            binding is not None
            or inspection.requirement_namespace is not None
            or inspection.requirement_name is not None
            or inspection.requirement_count != 0
            or inspection.requirements
        ):
            raise ValueError(
                "Undeclared capability facts must contain no requirements."
            )
        return None
    if (
        inspection.requirement_declaration
        is not CapabilityInspectionRequirementDeclaration.DECLARED
        or type(binding) is not PackageCapabilityRequirementBinding
        or binding.package is not package.entry.package
        or inspection.requirement_namespace != binding.requirements.identity.namespace
        or inspection.requirement_name != binding.requirements.identity.name
        or inspection.requirement_count != len(binding.requirements.occurrences)
        or len(inspection.requirements) != len(binding.requirements.occurrences)
    ):
        raise ValueError("Declared capability facts require one exact binding.")
    for position, (projected, occurrence) in enumerate(
        zip(
            inspection.requirements,
            binding.requirements.occurrences,
            strict=True,
        )
    ):
        _require_private_requirement(projected, occurrence, position)
    return binding


def _require_private_requirement(
    projected: CapabilityInspectionRequirement,
    occurrence: CapabilityRequirementOccurrence,
    position: int,
) -> None:
    if (
        type(projected) is not CapabilityInspectionRequirement
        or type(occurrence) is not CapabilityRequirementOccurrence
        or projected.position != position
        or occurrence.position != position
        or projected.row.occurrence is not occurrence
        or projected.key.key is not occurrence.key
        or not _inspection_key_matches(projected.key, occurrence.key)
    ):
        raise ValueError("Capability requirements must retain exact source authority.")


def _inspection_key_matches(
    projected: CapabilityInspectionKey,
    key: CapabilityKey,
) -> bool:
    return (
        projected.domain is key.domain
        and projected.subject == key.subject
        and projected.operation == key.operation
        and projected.operands == key.operands
        and projected.context == key.context
        and projected.dialect == key.dialect
        and projected.extension == key.extension
    )


def _project_package(
    package: PackageInspectionPackage,
) -> ProjectExplainPackage:
    return ProjectExplainPackage(
        position=package.position,
        role=(
            ProjectExplainPackageRole.ROOT
            if package.role is PackageInspectionPackageRole.ROOT
            else ProjectExplainPackageRole.DEPENDENCY
        ),
        coordinate=_project_coordinate(package.coordinate),
        project_path=ProjectExplainLogicalPath(
            kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            value=package.project_path,
        ),
        content_digest=package.content_digest,
        assets=tuple(_project_asset(asset) for asset in package.assets),
        dependencies=tuple(
            _project_dependency(dependency) for dependency in package.dependencies
        ),
    )


def _project_coordinate(
    coordinate: PackageCoordinate,
) -> ProjectExplainPackageCoordinate:
    if type(coordinate) is not PackageCoordinate:
        raise TypeError("Slice 3 requires exact private package coordinates.")
    return ProjectExplainPackageCoordinate(
        namespace=coordinate.identity.namespace,
        name=coordinate.identity.name,
        release=coordinate.exact_version,
    )


def _project_asset(asset: PackageInspectionAsset) -> ProjectExplainPackageAsset:
    if (
        type(asset) is not PackageInspectionAsset
        or asset.kind is not PackageInspectionAssetKind.MODULE_SOURCE
    ):
        raise TypeError("Slice 3 requires exact module-source assets.")
    return ProjectExplainPackageAsset(
        position=asset.position,
        kind=ProjectExplainPackageAssetKind.MODULE_SOURCE,
        path=ProjectExplainLogicalPath(
            kind=ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
            value=asset.path,
        ),
    )


def _project_dependency(
    dependency: PackageInspectionDependency,
) -> ProjectExplainDirectDependency:
    if (
        type(dependency) is not PackageInspectionDependency
        or dependency.locator_kind is not DependencyLocatorKind.LOCAL_DIRECTORY
    ):
        raise TypeError("Slice 3 requires exact local-directory dependencies.")
    return ProjectExplainDirectDependency(
        position=dependency.position,
        target_package_position=dependency.target_package_position,
        coordinate=_project_coordinate(dependency.coordinate),
        content_digest_pin=dependency.content_digest_pin,
        locator_kind=ProjectExplainDependencyLocatorKind.LOCAL_DIRECTORY,
        project_path=ProjectExplainLogicalPath(
            kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            value=dependency.resolved_project_path,
        ),
    )


def _project_capability_key(
    key: CapabilityInspectionKey,
) -> ProjectExplainCapabilityKey:
    if type(key) is not CapabilityInspectionKey:
        raise TypeError("Slice 3 requires exact inspected capability keys.")
    return ProjectExplainCapabilityKey(
        domain=key.domain,
        subject=key.subject,
        operation=key.operation,
        operands=key.operands,
        context=key.context,
        dialect=key.dialect,
        extension=key.extension,
    )


def _validate_dependency_references(
    packages: tuple[ProjectExplainPackage, ...],
) -> None:
    for package in packages:
        for dependency in package.dependencies:
            if dependency.target_package_position >= len(packages):
                raise ValueError("Direct dependencies must name a target package.")
            if dependency.target_package_position >= package.position:
                raise ValueError(
                    "Direct dependencies must preserve dependency-first package order."
                )
            target = packages[dependency.target_package_position]
            if (
                dependency.coordinate != target.coordinate
                or dependency.content_digest_pin != target.content_digest
            ):
                raise ValueError(
                    "Direct dependency identity and digest must match its target."
                )


def _validate_requirement_references(
    root_package_position: int,
    packages: tuple[ProjectExplainPackage, ...],
    collections: tuple[ProjectExplainRequirementCollection, ...],
    requirements: tuple[ProjectExplainRequirementRequest, ...],
) -> None:
    # ponytail: linear scans suit local projections; index if package scale matters.
    for collection in collections:
        if collection.declared_by >= len(packages):
            raise ValueError("Requirement collections must name a package.")
        package = packages[collection.declared_by]
        if (
            collection.requested_by != root_package_position
            or collection.package_role is not package.role
            or sum(
                candidate.declared_by == collection.declared_by
                for candidate in collections
            )
            != 1
        ):
            raise ValueError("Requirement collection package references are invalid.")

        owned = tuple(
            requirement
            for requirement in requirements
            if requirement.declared_by == collection.declared_by
            and requirement.collection == collection.identity
        )
        if tuple(
            requirement.position for requirement in owned
        ) != collection.requirement_positions or tuple(
            requirement.occurrence_position for requirement in owned
        ) != tuple(range(len(owned))):
            raise ValueError(
                "Requirement collections must retain exact occurrence positions."
            )

    for requirement in requirements:
        if requirement.declared_by >= len(packages):
            raise ValueError("Requirements must name a declaring package.")
        package = packages[requirement.declared_by]
        matching_collections = tuple(
            collection
            for collection in collections
            if collection.declared_by == requirement.declared_by
            and collection.identity == requirement.collection
        )
        if (
            requirement.requested_by != root_package_position
            or requirement.package_role is not package.role
            or len(matching_collections) != 1
            or requirement.position not in matching_collections[0].requirement_positions
        ):
            raise ValueError(
                "Requirement package and collection references are invalid."
            )


def _require_non_empty_text(value: object, label: str) -> None:
    if type(value) is not str:
        raise TypeError(f"Project Explain {label} must be exact text.")
    if not value:
        raise ValueError(f"Project Explain {label} must be non-empty.")


def _require_nonblank_text(value: object, label: str) -> None:
    if type(value) is not str:
        raise TypeError(f"Project Explain {label} must be exact text.")
    if not value.strip():
        raise ValueError(f"Project Explain {label} must be nonblank.")


def _require_optional_nonblank_text(value: object | None, label: str) -> str | None:
    if value is None:
        return None
    _require_nonblank_text(value, label)
    assert type(value) is str
    return value


def _require_position(value: object, label: str) -> None:
    if type(value) is not int:
        raise TypeError(f"Project Explain {label} must be an exact integer.")
    if value < 0:
        raise ValueError(f"Project Explain {label} must be non-negative.")


def _require_sha256(value: object, label: str) -> None:
    if type(value) is not str:
        raise TypeError(f"Project Explain {label} must be exact text.")
    if len(value) != 64 or any(character not in _LOWER_HEX for character in value):
        raise ValueError(f"Project Explain {label} must be lowercase SHA-256 text.")


def _require_logical_path(
    value: object,
    kind: ProjectExplainLogicalPathKind,
    label: str,
) -> None:
    if type(value) is not ProjectExplainLogicalPath:
        raise TypeError(f"Project Explain {label} must be an exact logical path.")
    if value.kind is not kind:
        raise ValueError(f"Project Explain {label} has the wrong logical path kind.")


def _require_exact_tuple(values: object, item_type: type, label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"Project Explain {label} must be an exact tuple.")
    if any(type(value) is not item_type for value in values):
        raise TypeError(
            f"Project Explain {label} must contain exact {item_type.__name__} values."
        )


def _require_dense_tuple(values: object, item_type: type, label: str) -> None:
    _require_exact_tuple(values, item_type, label)
    assert type(values) is tuple
    if tuple(value.position for value in values) != tuple(range(len(values))):
        raise ValueError(
            f"Project Explain {label} positions must be dense and ordered."
        )


def _require_ordered_positions(values: object, label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"Project Explain {label} must be an exact tuple.")
    for value in values:
        _require_position(value, label)
    if any(left >= right for left, right in zip(values, values[1:])):
        raise ValueError(f"Project Explain {label} must be strictly source ordered.")
