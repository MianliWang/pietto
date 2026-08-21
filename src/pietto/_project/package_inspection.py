"""Private deterministic package inspection and canonical serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.model import ProjectDiscoveryError, ProjectDiscoveryErrorKind
from pietto._project.package_pure_boundary import (
    PACKAGE_PURE_ABSENT,
    PackagePureDocument,
    PackagePureField,
    PackagePureRecord,
    PackagePureStatus,
    PackagePureValue,
    evaluate_package_document,
    package_pure_enumeration,
    package_pure_integer,
    package_pure_text,
)
from pietto._project.package_load_plan import (
    DependencyLocatorKind,
    LoadedDependencyPackage,
    LocatedDependencyPackage,
    PackageDependencyEdge,
    PackageDependencyOccurrence,
    PackageLoadPlan,
    PackageLoadPlanBlocker,
    PackageLoadPlanBlockerKind,
    PackageLoadPlanEntry,
    PackageLoadPlanResult,
    _normalize_dependency_path,
    _package_catalog,
    _package_content_digest,
    _package_coordinate,
    _package_pinned_root,
    _package_project_path,
)
from pietto._project.package_loader import LoadedRootPackage
from pietto._project.package_manifest import (
    PackageCoordinate,
    PackageModuleSourceAsset,
    TypedRootPackageAssetCatalog,
    _is_valid_content_digest_pin,
)
from pietto._project.package_rejection import (
    PackageConflictReason,
    PackageRejectionDiagnostic,
    PackageRejectionProduct,
    _diagnose_package_load_result,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()


class PackageInspectionFormat(StrEnum):
    PACKAGE_INSPECTION_V1 = "pietto.package-inspection.v1"


class PackageInspectionOutcome(StrEnum):
    SUCCESS = "success"
    REJECTED = "rejected"
    ERROR = "error"


class PackageInspectionPackageRole(StrEnum):
    DEPENDENCY = "dependency"
    ROOT = "root"


class PackageInspectionAssetKind(StrEnum):
    MODULE_SOURCE = "module_source"


@dataclass(frozen=True, slots=True, init=False)
class PackageInspectionAsset:
    position: int
    kind: PackageInspectionAssetKind
    path: str
    asset: PackageModuleSourceAsset = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> PackageInspectionAsset:
        raise TypeError("Package inspection assets require canonical construction.")


@dataclass(frozen=True, slots=True, init=False)
class PackageInspectionDependency:
    position: int
    coordinate: PackageCoordinate
    content_digest_pin: str
    locator_kind: DependencyLocatorKind
    authored_path: str
    resolved_project_path: str
    target_package_position: int
    edge: PackageDependencyEdge = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> PackageInspectionDependency:
        raise TypeError(
            "Package inspection dependencies require canonical construction."
        )


@dataclass(frozen=True, slots=True, init=False)
class PackageInspectionPackage:
    position: int
    role: PackageInspectionPackageRole
    coordinate: PackageCoordinate
    project_path: str
    content_digest: str
    assets: tuple[PackageInspectionAsset, ...]
    dependencies: tuple[PackageInspectionDependency, ...]
    entry: PackageLoadPlanEntry = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> PackageInspectionPackage:
        raise TypeError("Inspected packages require canonical construction.")


@dataclass(frozen=True, slots=True, init=False)
class PackageInspectionError:
    position: int
    kind: ProjectDiscoveryErrorKind
    message: str
    path: str | None
    error: ProjectDiscoveryError = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> PackageInspectionError:
        raise TypeError("Package inspection errors require canonical construction.")


@dataclass(frozen=True, slots=True, init=False)
class PackageInspectionDiagnostic:
    position: int
    code: str
    severity: Severity
    message: str
    path: str | None
    line: int
    column: int
    end_line: int | None
    end_column: int | None
    suggestion: str | None
    diagnostic: Diagnostic = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> PackageInspectionDiagnostic:
        raise TypeError(
            "Package inspection diagnostics require canonical construction."
        )


@dataclass(frozen=True, slots=True, init=False)
class PackageInspectionRejectionOccurrence:
    position: int
    dependency_position: int
    declaring_coordinate: PackageCoordinate
    declaring_project_path: str
    declaring_content_digest: str
    coordinate: PackageCoordinate
    content_digest_pin: str
    locator_kind: DependencyLocatorKind
    authored_path: str
    resolved_project_path: str
    occurrence: PackageDependencyOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> PackageInspectionRejectionOccurrence:
        raise TypeError("Package rejection occurrences require canonical construction.")


@dataclass(frozen=True, slots=True, init=False)
class PackageInspectionRejection:
    position: int
    kind: PackageLoadPlanBlockerKind
    conflict_reasons: tuple[PackageConflictReason, ...]
    occurrences: tuple[PackageInspectionRejectionOccurrence, ...]
    message: str
    diagnostic: PackageRejectionDiagnostic = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> PackageInspectionRejection:
        raise TypeError("Package rejections require canonical construction.")


@dataclass(frozen=True, slots=True, init=False)
class PackageInspection:
    format: PackageInspectionFormat
    outcome: PackageInspectionOutcome
    root_coordinate: PackageCoordinate | None
    package_count: int
    packages: tuple[PackageInspectionPackage, ...]
    errors: tuple[PackageInspectionError, ...]
    diagnostics: tuple[PackageInspectionDiagnostic, ...]
    rejections: tuple[PackageInspectionRejection, ...]
    plan_result: PackageLoadPlanResult = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> PackageInspection:
        raise TypeError("Package inspections require canonical construction.")


@dataclass(frozen=True, slots=True, kw_only=True)
class _PackageInspectionAuthority:
    """One exact plan-result authority and all products derived from it."""

    plan_result: PackageLoadPlanResult = field(repr=False, compare=False, hash=False)
    rejection_product: PackageRejectionProduct = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    inspection: PackageInspection = field(
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
        _validate_plan_result(self.plan_result)
        rejection_product = _diagnose_package_load_result(self.plan_result)
        if rejection_product.plan_result is not self.plan_result:
            raise ValueError("Package rejection must retain the exact plan result.")
        inspection = _derive_package_inspection(
            self.plan_result,
            rejection_product,
        )
        object.__setattr__(self, "rejection_product", rejection_product)
        object.__setattr__(self, "inspection", inspection)
        object.__setattr__(
            self,
            "canonical_bytes",
            _serialize_package_inspection(inspection),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageInspectionFactSet:
    """One exact private package inspection and its canonical bytes."""

    inspection: PackageInspection
    canonical_bytes: bytes
    authority: _PackageInspectionAuthority = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.authority) is not _PackageInspectionAuthority:
            raise TypeError("Package inspection facts require an exact authority.")
        if self.inspection is not self.authority.inspection:
            raise ValueError(
                "Package inspection facts require the exact derived inspection."
            )
        if self.canonical_bytes is not self.authority.canonical_bytes:
            raise ValueError(
                "Package inspection facts require the exact derived canonical bytes."
            )


def _build_package_inspection_fact_set(
    plan_result: PackageLoadPlanResult,
) -> PackageInspectionFactSet:
    """Derive one private inspection without reloading or replanning."""

    authority = _PackageInspectionAuthority(plan_result=plan_result)
    return PackageInspectionFactSet(
        inspection=authority.inspection,
        canonical_bytes=authority.canonical_bytes,
        authority=authority,
    )


def _validate_plan_result(plan_result: PackageLoadPlanResult) -> None:
    if type(plan_result) is not PackageLoadPlanResult:
        raise TypeError("Package inspection requires an exact load-plan result.")
    _require_tuple(plan_result.errors, ProjectDiscoveryError, "Plan errors")
    _require_tuple(plan_result.blockers, PackageLoadPlanBlocker, "Plan blockers")
    _require_tuple(plan_result.diagnostics, Diagnostic, "Plan diagnostics")
    for error in plan_result.errors:
        _validate_discovery_error(error)
    for diagnostic in plan_result.diagnostics:
        _validate_diagnostic(diagnostic)

    has_error_diagnostic = any(
        diagnostic.severity is Severity.ERROR for diagnostic in plan_result.diagnostics
    )
    if plan_result.plan is not None:
        if plan_result.errors or plan_result.blockers or has_error_diagnostic:
            raise ValueError("Successful package plans forbid failure evidence.")
        _validate_plan(plan_result.plan)
        return
    if not (plan_result.errors or plan_result.blockers or has_error_diagnostic):
        raise ValueError("Failed package plans require exact failure evidence.")
    if plan_result.errors and plan_result.blockers:
        raise ValueError("Package errors and blockers are mutually exclusive.")
    if plan_result.blockers and has_error_diagnostic:
        raise ValueError("Package blockers forbid parser error diagnostics.")
    for blocker in plan_result.blockers:
        _validate_blocker(blocker)


def _validate_plan(plan: PackageLoadPlan) -> None:
    if type(plan) is not PackageLoadPlan:
        raise TypeError("Package inspection requires an exact plan.")
    if type(plan.root_package) is not LoadedRootPackage:
        raise TypeError("Package plans require an exact loaded root.")
    _require_tuple(plan.entries, PackageLoadPlanEntry, "Plan entries")
    if not plan.entries or plan.entries[-1].package is not plan.root_package:
        raise ValueError("Package plans require the root as their final entry.")

    # ponytail: identity scans suit small local plans; index only if size matters.
    for position, entry in enumerate(plan.entries):
        if entry.position != position:
            raise ValueError("Package plan entry positions must be dense and ordered.")
        if sum(candidate.package is entry.package for candidate in plan.entries) != 1:
            raise ValueError("Package plans require one entry per exact package.")
        if position < len(plan.entries) - 1 and entry.package is plan.root_package:
            raise ValueError("Package plan roots may appear only as the final entry.")
        _validate_loaded_package(entry.package)
        _require_tuple(
            entry.dependencies,
            PackageDependencyEdge,
            "Plan entry dependencies",
        )
        declarations = _package_catalog(
            entry.package
        ).root_package.manifest.dependencies
        if len(entry.dependencies) != len(declarations):
            raise ValueError("Package plan entries must retain every dependency.")
        for dependency_position, edge in enumerate(entry.dependencies):
            occurrence = edge.occurrence
            _validate_occurrence(occurrence)
            if occurrence.declaring_package is not entry.package:
                raise ValueError("Package dependency authority must match its entry.")
            if occurrence.position != dependency_position or (
                occurrence.declaration is not declarations[dependency_position]
            ):
                raise ValueError("Package dependencies must retain declaration order.")
            target_positions = tuple(
                candidate.position
                for candidate in plan.entries
                if candidate.package is edge.package
            )
            if len(target_positions) != 1:
                raise ValueError("Package dependencies require one exact plan target.")
            target_position = target_positions[0]
            if target_position >= entry.position:
                raise ValueError("Package plans require dependency-first postorder.")
            if occurrence.coordinate != _package_coordinate(edge.package) or (
                occurrence.content_digest_pin != _package_content_digest(edge.package)
            ):
                raise ValueError(
                    "Package dependency pins must match their exact target."
                )


def _validate_loaded_package(
    package: LoadedRootPackage | LoadedDependencyPackage,
) -> None:
    if type(package) not in {LoadedRootPackage, LoadedDependencyPackage}:
        raise TypeError("Package inspection requires exact loaded packages.")
    catalog = _package_catalog(package)
    if type(catalog) is not TypedRootPackageAssetCatalog:
        raise TypeError("Loaded packages require an exact typed asset catalog.")
    _require_tuple(catalog.assets, PackageModuleSourceAsset, "Typed package assets")
    manifest_assets = catalog.root_package.manifest.assets
    if len(catalog.assets) != len(manifest_assets):
        raise ValueError("Typed package assets must cover the manifest catalog.")
    for position, (asset, manifest_asset) in enumerate(
        zip(catalog.assets, manifest_assets, strict=True)
    ):
        if manifest_asset.kind != PackageInspectionAssetKind.MODULE_SOURCE.value or (
            asset.path != manifest_asset.path
        ):
            raise ValueError(
                f"Typed package asset {position} must mirror its manifest entry."
            )
    modules = package.modules
    if type(modules) is not tuple or len(modules) != len(catalog.assets):
        raise ValueError("Loaded packages must retain every typed module asset.")
    for position, (module, asset) in enumerate(
        zip(modules, catalog.assets, strict=True)
    ):
        if (
            module.position != position
            or module.asset is not asset
            or module.identity.path != asset.path
        ):
            raise ValueError("Loaded package modules must retain asset order.")
    if not _is_valid_content_digest_pin(_package_content_digest(package)):
        raise ValueError("Loaded package content digests must be exact SHA-256 text.")


def _validate_occurrence(occurrence: PackageDependencyOccurrence) -> None:
    if type(occurrence) is not PackageDependencyOccurrence:
        raise TypeError("Package inspection requires exact dependency occurrences.")
    declaring = occurrence.declaring_package
    _validate_loaded_package(declaring)
    declarations = _package_catalog(declaring).root_package.manifest.dependencies
    if occurrence.position < 0 or occurrence.position >= len(declarations):
        raise ValueError("Dependency occurrence positions must name a declaration.")
    declaration = declarations[occurrence.position]
    if occurrence.declaration is not declaration:
        raise ValueError("Dependency occurrences must retain exact declarations.")
    if (
        occurrence.coordinate.identity.namespace != declaration.namespace
        or occurrence.coordinate.identity.name != declaration.name
        or occurrence.coordinate.exact_version != declaration.version
        or occurrence.content_digest_pin != declaration.sha256
        or occurrence.locator_kind is not DependencyLocatorKind.LOCAL_DIRECTORY
    ):
        raise ValueError("Dependency occurrences must mirror their declarations.")
    resolved = _normalize_dependency_path(
        _package_project_path(declaring),
        declaration.path,
    )
    if resolved is None or occurrence.resolved_project_path != resolved:
        raise ValueError("Dependency occurrences require their exact resolved path.")


def _validate_blocker(blocker: PackageLoadPlanBlocker) -> None:
    if type(blocker) is not PackageLoadPlanBlocker:
        raise TypeError("Package inspection requires exact plan blockers.")
    if type(blocker.kind) is not PackageLoadPlanBlockerKind:
        raise TypeError("Package blockers require an exact kind.")
    _require_tuple(
        blocker.occurrences,
        PackageDependencyOccurrence,
        "Blocker occurrences",
    )
    if not blocker.occurrences:
        raise ValueError("Package blockers require occurrence evidence.")
    for occurrence in blocker.occurrences:
        _validate_occurrence(occurrence)
    if type(blocker.location) is not LocatedDependencyPackage or (
        blocker.location.occurrence is not blocker.occurrences[-1]
    ):
        raise ValueError("Package blockers require the exact closing location.")
    if blocker.location.pinned_root is not _package_pinned_root(
        blocker.location.occurrence.declaring_package
    ):
        raise ValueError("Package blocker locations require exact root authority.")
    if type(blocker.packages) is not tuple or any(
        type(package) not in {LoadedRootPackage, LoadedDependencyPackage}
        for package in blocker.packages
    ):
        raise TypeError("Package blockers require exact loaded packages.")
    for package in blocker.packages:
        _validate_loaded_package(package)
    if blocker.kind is PackageLoadPlanBlockerKind.CYCLE:
        if len(blocker.packages) != len(blocker.occurrences):
            raise ValueError("Cycle blockers require the complete occurrence chain.")
    elif blocker.kind is PackageLoadPlanBlockerKind.CONFLICT:
        if len(blocker.packages) != 1 or len(blocker.occurrences) not in {1, 2}:
            raise ValueError("Conflict blockers require exact conflicting evidence.")
    elif blocker.kind is PackageLoadPlanBlockerKind.DIAMOND:
        if len(blocker.packages) != 1 or len(blocker.occurrences) != 2:
            raise ValueError("Diamond blockers require both incoming authorities.")


def _validate_discovery_error(error: ProjectDiscoveryError) -> None:
    if type(error.kind) is not ProjectDiscoveryErrorKind:
        raise TypeError("Package discovery errors require an exact kind.")
    if type(error.message) is not str:
        raise TypeError("Package discovery error messages must be text.")
    if error.path is not None and type(error.path) is not str:
        raise TypeError("Package discovery error paths must be text when present.")


def _validate_diagnostic(diagnostic: Diagnostic) -> None:
    if (
        type(diagnostic.code) is not str
        or type(diagnostic.severity) is not Severity
        or type(diagnostic.message) is not str
        or type(diagnostic.location) is not SourceLocation
        or (
            diagnostic.suggestion is not None and type(diagnostic.suggestion) is not str
        )
    ):
        raise TypeError("Package parser diagnostics require exact stable fields.")
    location = diagnostic.location
    if location.path is not None and type(location.path) is not str:
        raise TypeError("Package diagnostic paths must be text when present.")
    for value in (location.line, location.column):
        if type(value) is not int or value < 0:
            raise ValueError("Package diagnostic positions must be non-negative.")
    for value in (location.end_line, location.end_column):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Package diagnostic end positions must be non-negative.")


def _derive_package_inspection(
    plan_result: PackageLoadPlanResult,
    rejection_product: PackageRejectionProduct,
) -> PackageInspection:
    plan = plan_result.plan
    packages = () if plan is None else _derive_packages(plan)
    errors = tuple(
        _derive_error(position, error)
        for position, error in enumerate(plan_result.errors)
    )
    diagnostics = tuple(
        _derive_diagnostic(position, diagnostic)
        for position, diagnostic in enumerate(plan_result.diagnostics)
    )
    rejections = tuple(
        _derive_rejection(position, diagnostic)
        for position, diagnostic in enumerate(rejection_product.diagnostics)
    )
    if plan is not None:
        outcome = PackageInspectionOutcome.SUCCESS
        root_coordinate = _package_coordinate(plan.root_package)
    elif rejections:
        outcome = PackageInspectionOutcome.REJECTED
        root_coordinate = None
    else:
        outcome = PackageInspectionOutcome.ERROR
        root_coordinate = None

    inspection = object.__new__(PackageInspection)
    object.__setattr__(
        inspection,
        "format",
        PackageInspectionFormat.PACKAGE_INSPECTION_V1,
    )
    object.__setattr__(inspection, "outcome", outcome)
    object.__setattr__(inspection, "root_coordinate", root_coordinate)
    object.__setattr__(inspection, "package_count", len(packages))
    object.__setattr__(inspection, "packages", packages)
    object.__setattr__(inspection, "errors", errors)
    object.__setattr__(inspection, "diagnostics", diagnostics)
    object.__setattr__(inspection, "rejections", rejections)
    object.__setattr__(inspection, "plan_result", plan_result)
    return inspection


def _derive_packages(plan: PackageLoadPlan) -> tuple[PackageInspectionPackage, ...]:
    packages: list[PackageInspectionPackage] = []
    for entry in plan.entries:
        catalog = _package_catalog(entry.package)
        assets = tuple(
            _derive_asset(position, asset)
            for position, asset in enumerate(catalog.assets)
        )
        dependencies: list[PackageInspectionDependency] = []
        for edge in entry.dependencies:
            target_position = next(
                candidate.position
                for candidate in plan.entries
                if candidate.package is edge.package
            )
            dependencies.append(_derive_dependency(edge, target_position))
        package = object.__new__(PackageInspectionPackage)
        object.__setattr__(package, "position", entry.position)
        object.__setattr__(
            package,
            "role",
            (
                PackageInspectionPackageRole.ROOT
                if entry.package is plan.root_package
                else PackageInspectionPackageRole.DEPENDENCY
            ),
        )
        object.__setattr__(package, "coordinate", _package_coordinate(entry.package))
        object.__setattr__(
            package, "project_path", _package_project_path(entry.package)
        )
        object.__setattr__(
            package,
            "content_digest",
            _package_content_digest(entry.package),
        )
        object.__setattr__(package, "assets", assets)
        object.__setattr__(package, "dependencies", tuple(dependencies))
        object.__setattr__(package, "entry", entry)
        packages.append(package)
    return tuple(packages)


def _derive_asset(
    position: int,
    asset: PackageModuleSourceAsset,
) -> PackageInspectionAsset:
    projected = object.__new__(PackageInspectionAsset)
    object.__setattr__(projected, "position", position)
    object.__setattr__(
        projected,
        "kind",
        PackageInspectionAssetKind.MODULE_SOURCE,
    )
    object.__setattr__(projected, "path", asset.path)
    object.__setattr__(projected, "asset", asset)
    return projected


def _derive_dependency(
    edge: PackageDependencyEdge,
    target_position: int,
) -> PackageInspectionDependency:
    occurrence = edge.occurrence
    projected = object.__new__(PackageInspectionDependency)
    object.__setattr__(projected, "position", occurrence.position)
    object.__setattr__(projected, "coordinate", occurrence.coordinate)
    object.__setattr__(
        projected,
        "content_digest_pin",
        occurrence.content_digest_pin,
    )
    object.__setattr__(projected, "locator_kind", occurrence.locator_kind)
    object.__setattr__(projected, "authored_path", occurrence.declaration.path)
    object.__setattr__(
        projected,
        "resolved_project_path",
        occurrence.resolved_project_path,
    )
    object.__setattr__(projected, "target_package_position", target_position)
    object.__setattr__(projected, "edge", edge)
    return projected


def _derive_error(
    position: int,
    error: ProjectDiscoveryError,
) -> PackageInspectionError:
    projected = object.__new__(PackageInspectionError)
    object.__setattr__(projected, "position", position)
    object.__setattr__(projected, "kind", error.kind)
    object.__setattr__(projected, "message", error.message)
    object.__setattr__(projected, "path", error.path)
    object.__setattr__(projected, "error", error)
    return projected


def _derive_diagnostic(
    position: int,
    diagnostic: Diagnostic,
) -> PackageInspectionDiagnostic:
    location = diagnostic.location
    projected = object.__new__(PackageInspectionDiagnostic)
    object.__setattr__(projected, "position", position)
    object.__setattr__(projected, "code", diagnostic.code)
    object.__setattr__(projected, "severity", diagnostic.severity)
    object.__setattr__(projected, "message", diagnostic.message)
    object.__setattr__(projected, "path", location.path)
    object.__setattr__(projected, "line", location.line)
    object.__setattr__(projected, "column", location.column)
    object.__setattr__(projected, "end_line", location.end_line)
    object.__setattr__(projected, "end_column", location.end_column)
    object.__setattr__(projected, "suggestion", diagnostic.suggestion)
    object.__setattr__(projected, "diagnostic", diagnostic)
    return projected


def _derive_rejection(
    position: int,
    diagnostic: PackageRejectionDiagnostic,
) -> PackageInspectionRejection:
    occurrences = tuple(
        _derive_rejection_occurrence(occurrence_position, occurrence)
        for occurrence_position, occurrence in enumerate(diagnostic.occurrences)
    )
    projected = object.__new__(PackageInspectionRejection)
    object.__setattr__(projected, "position", position)
    object.__setattr__(projected, "kind", diagnostic.kind)
    object.__setattr__(projected, "conflict_reasons", diagnostic.conflict_reasons)
    object.__setattr__(projected, "occurrences", occurrences)
    object.__setattr__(projected, "message", diagnostic.message)
    object.__setattr__(projected, "diagnostic", diagnostic)
    return projected


def _derive_rejection_occurrence(
    position: int,
    occurrence: PackageDependencyOccurrence,
) -> PackageInspectionRejectionOccurrence:
    declaring = occurrence.declaring_package
    projected = object.__new__(PackageInspectionRejectionOccurrence)
    object.__setattr__(projected, "position", position)
    object.__setattr__(projected, "dependency_position", occurrence.position)
    object.__setattr__(
        projected,
        "declaring_coordinate",
        _package_coordinate(declaring),
    )
    object.__setattr__(
        projected,
        "declaring_project_path",
        _package_project_path(declaring),
    )
    object.__setattr__(
        projected,
        "declaring_content_digest",
        _package_content_digest(declaring),
    )
    object.__setattr__(projected, "coordinate", occurrence.coordinate)
    object.__setattr__(
        projected,
        "content_digest_pin",
        occurrence.content_digest_pin,
    )
    object.__setattr__(projected, "locator_kind", occurrence.locator_kind)
    object.__setattr__(projected, "authored_path", occurrence.declaration.path)
    object.__setattr__(
        projected,
        "resolved_project_path",
        occurrence.resolved_project_path,
    )
    object.__setattr__(projected, "occurrence", occurrence)
    return projected


def _serialize_package_inspection(inspection: PackageInspection) -> bytes:
    """Evaluate one explicit portable document into the frozen Slice 10 bytes."""

    if type(inspection) is not PackageInspection:
        raise TypeError("Canonical package serialization requires an inspection.")
    outcome = evaluate_package_document(_package_pure_document(inspection))
    if outcome.status is not PackagePureStatus.OK or outcome.canonical_bytes is None:
        raise ValueError(
            "Canonical package payload must evaluate exactly: "
            f"{outcome.status.value} at record {outcome.record_position} "
            f"field {outcome.field_position}."
        )
    return outcome.canonical_bytes


def _package_pure_document(inspection: PackageInspection) -> PackagePureDocument:
    """Project one authority-derived inspection into explicit portable values."""

    emitted: list[PackagePureRecord] = []
    _pure_record(
        emitted,
        "inspection",
        ("format", _pure_enumeration(inspection.format)),
        ("outcome", _pure_enumeration(inspection.outcome)),
        ("packages", _pure_integer(inspection.package_count)),
        ("errors", _pure_integer(len(inspection.errors))),
        ("diagnostics", _pure_integer(len(inspection.diagnostics))),
        ("rejections", _pure_integer(len(inspection.rejections))),
    )
    if inspection.root_coordinate is not None:
        coordinate = inspection.root_coordinate
        _pure_record(
            emitted,
            "root",
            ("namespace", _pure_text(coordinate.identity.namespace)),
            ("name", _pure_text(coordinate.identity.name)),
            ("version", _pure_text(coordinate.exact_version)),
        )
    for package in inspection.packages:
        _project_package(emitted, package)
    for error in inspection.errors:
        _pure_record(
            emitted,
            "error",
            ("error", _pure_integer(error.position)),
            ("kind", _pure_enumeration(error.kind)),
            ("message", _pure_text(error.message)),
            ("path", _pure_optional_text(error.path)),
        )
    for diagnostic in inspection.diagnostics:
        _pure_record(
            emitted,
            "diagnostic",
            ("diagnostic", _pure_integer(diagnostic.position)),
            ("code", _pure_text(diagnostic.code)),
            ("severity", _pure_enumeration(diagnostic.severity)),
            ("message", _pure_text(diagnostic.message)),
            ("path", _pure_optional_text(diagnostic.path)),
            ("line", _pure_integer(diagnostic.line)),
            ("column", _pure_integer(diagnostic.column)),
            ("end_line", _pure_optional_integer(diagnostic.end_line)),
            ("end_column", _pure_optional_integer(diagnostic.end_column)),
            ("suggestion", _pure_optional_text(diagnostic.suggestion)),
        )
    for rejection in inspection.rejections:
        _project_rejection(emitted, rejection)
    return PackagePureDocument(records=tuple(emitted))


def _project_package(
    emitted: list[PackagePureRecord],
    package: PackageInspectionPackage,
) -> None:
    coordinate = package.coordinate
    _pure_record(
        emitted,
        "package",
        ("package", _pure_integer(package.position)),
        ("role", _pure_enumeration(package.role)),
        ("namespace", _pure_text(coordinate.identity.namespace)),
        ("name", _pure_text(coordinate.identity.name)),
        ("version", _pure_text(coordinate.exact_version)),
        ("project_path", _pure_text(package.project_path)),
        ("content_digest", _pure_text(package.content_digest)),
        ("assets", _pure_integer(len(package.assets))),
        ("dependencies", _pure_integer(len(package.dependencies))),
    )
    for asset in package.assets:
        _pure_record(
            emitted,
            "asset",
            ("package", _pure_integer(package.position)),
            ("asset", _pure_integer(asset.position)),
            ("kind", _pure_enumeration(asset.kind)),
            ("path", _pure_text(asset.path)),
        )
    for dependency in package.dependencies:
        coordinate = dependency.coordinate
        _pure_record(
            emitted,
            "dependency",
            ("package", _pure_integer(package.position)),
            ("dependency", _pure_integer(dependency.position)),
            ("namespace", _pure_text(coordinate.identity.namespace)),
            ("name", _pure_text(coordinate.identity.name)),
            ("version", _pure_text(coordinate.exact_version)),
            ("content_digest_pin", _pure_text(dependency.content_digest_pin)),
            ("locator_kind", _pure_enumeration(dependency.locator_kind)),
            ("authored_path", _pure_text(dependency.authored_path)),
            (
                "resolved_project_path",
                _pure_text(dependency.resolved_project_path),
            ),
            (
                "target_package",
                _pure_integer(dependency.target_package_position),
            ),
        )


def _project_rejection(
    emitted: list[PackagePureRecord],
    rejection: PackageInspectionRejection,
) -> None:
    _pure_record(
        emitted,
        "rejection",
        ("rejection", _pure_integer(rejection.position)),
        ("kind", _pure_enumeration(rejection.kind)),
        ("conflict_reasons", _pure_integer(len(rejection.conflict_reasons))),
        ("occurrences", _pure_integer(len(rejection.occurrences))),
        ("message", _pure_text(rejection.message)),
    )
    for position, reason in enumerate(rejection.conflict_reasons):
        _pure_record(
            emitted,
            "rejection_reason",
            ("rejection", _pure_integer(rejection.position)),
            ("reason", _pure_integer(position)),
            ("value", _pure_enumeration(reason)),
        )
    for occurrence in rejection.occurrences:
        declaring = occurrence.declaring_coordinate
        coordinate = occurrence.coordinate
        _pure_record(
            emitted,
            "rejection_occurrence",
            ("rejection", _pure_integer(rejection.position)),
            ("occurrence", _pure_integer(occurrence.position)),
            (
                "dependency_position",
                _pure_integer(occurrence.dependency_position),
            ),
            (
                "declaring_namespace",
                _pure_text(declaring.identity.namespace),
            ),
            ("declaring_name", _pure_text(declaring.identity.name)),
            ("declaring_version", _pure_text(declaring.exact_version)),
            (
                "declaring_project_path",
                _pure_text(occurrence.declaring_project_path),
            ),
            (
                "declaring_content_digest",
                _pure_text(occurrence.declaring_content_digest),
            ),
            ("namespace", _pure_text(coordinate.identity.namespace)),
            ("name", _pure_text(coordinate.identity.name)),
            ("version", _pure_text(coordinate.exact_version)),
            (
                "content_digest_pin",
                _pure_text(occurrence.content_digest_pin),
            ),
            ("locator_kind", _pure_enumeration(occurrence.locator_kind)),
            ("authored_path", _pure_text(occurrence.authored_path)),
            (
                "resolved_project_path",
                _pure_text(occurrence.resolved_project_path),
            ),
        )


def _pure_record(
    emitted: list[PackagePureRecord],
    kind: str,
    *fields: tuple[str, PackagePureValue],
) -> None:
    emitted.append(
        PackagePureRecord(
            kind=kind,
            fields=tuple(
                PackagePureField(key=key, value=value) for key, value in fields
            ),
        )
    )


def _pure_text(value: str) -> PackagePureValue:
    if type(value) is not str:
        raise TypeError("Portable package text must be exact text.")
    return package_pure_text(value)


def _pure_enumeration(value: StrEnum) -> PackagePureValue:
    if not isinstance(value, StrEnum):
        raise TypeError("Portable package enumerations must be exact enums.")
    return package_pure_enumeration(value.value)


def _pure_integer(value: int) -> PackagePureValue:
    if type(value) is not int or value < 0:
        raise ValueError("Portable package integers must be non-negative.")
    return package_pure_integer(value)


def _pure_optional_text(value: str | None) -> PackagePureValue:
    return PACKAGE_PURE_ABSENT if value is None else _pure_text(value)


def _pure_optional_integer(value: int | None) -> PackagePureValue:
    return PACKAGE_PURE_ABSENT if value is None else _pure_integer(value)


def _require_tuple(values: object, item_type: type, label: str) -> None:
    if type(values) is not tuple or any(
        type(value) is not item_type for value in values
    ):
        raise TypeError(f"{label} must retain exact ordered values.")
