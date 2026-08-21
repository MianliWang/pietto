"""Private deterministic dependency blocker rejection diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.package_load_plan import (
    PackageDependencyOccurrence,
    PackageLoadPlanBlocker,
    PackageLoadPlanBlockerKind,
    PackageLoadPlanResult,
    _package_content_digest,
    _package_coordinate,
    _package_physical_identity,
)
from pietto._project.package_manifest import PackageCoordinate

__all__: tuple[str, ...] = ()


class PackageConflictReason(StrEnum):
    IDENTITY_DIFFERENT_PHYSICAL_ROOT = "identity_different_physical_root"
    PHYSICAL_ROOT_INCOMPATIBLE_COORDINATE = "physical_root_incompatible_coordinate"
    INCOMPATIBLE_CONTENT_DIGEST_PIN = "incompatible_content_digest_pin"
    INCOMPATIBLE_OCCURRENCES = "incompatible_occurrences"


@dataclass(frozen=True, slots=True, init=False)
class PackageRejectionDiagnostic:
    blocker: PackageLoadPlanBlocker = field(repr=False)
    conflict_reasons: tuple[PackageConflictReason, ...]
    message: str

    def __new__(cls) -> PackageRejectionDiagnostic:
        raise TypeError(
            "Package rejection diagnostics require canonical blocker rendering."
        )

    @property
    def kind(self) -> PackageLoadPlanBlockerKind:
        return self.blocker.kind

    @property
    def occurrences(self) -> tuple[PackageDependencyOccurrence, ...]:
        return self.blocker.occurrences


@dataclass(frozen=True, slots=True, init=False)
class PackageRejectionProduct:
    plan_result: PackageLoadPlanResult = field(repr=False)
    diagnostics: tuple[PackageRejectionDiagnostic, ...]

    def __new__(cls) -> PackageRejectionProduct:
        raise TypeError("Package rejection products require canonical diagnostics.")

    @property
    def rejected(self) -> bool:
        return self.plan_result.plan is None


def _diagnose_package_load_result(
    plan_result: PackageLoadPlanResult,
) -> PackageRejectionProduct:
    """Transform exact blockers into ordered private rejection diagnostics."""

    if type(plan_result) is not PackageLoadPlanResult:
        raise TypeError("Package rejection diagnostics require an exact plan result.")
    if plan_result.plan is not None and (plan_result.errors or plan_result.blockers):
        raise ValueError("Successful package plans forbid rejection evidence.")

    diagnostics = tuple(_diagnose_blocker(blocker) for blocker in plan_result.blockers)
    product = object.__new__(PackageRejectionProduct)
    object.__setattr__(product, "plan_result", plan_result)
    object.__setattr__(product, "diagnostics", diagnostics)
    return product


def _diagnose_blocker(
    blocker: PackageLoadPlanBlocker,
) -> PackageRejectionDiagnostic:
    if type(blocker) is not PackageLoadPlanBlocker:
        raise TypeError("Package rejection diagnostics require exact blockers.")
    if blocker.kind is PackageLoadPlanBlockerKind.CYCLE:
        reasons: tuple[PackageConflictReason, ...] = ()
        message = "Dependency cycle: " + " | ".join(
            _occurrence_text(occurrence) for occurrence in blocker.occurrences
        )
    elif blocker.kind is PackageLoadPlanBlockerKind.CONFLICT:
        reasons = _conflict_reasons(blocker)
        reason_text = "; ".join(_reason_text(reason) for reason in reasons)
        message = (
            f"Dependency conflict ({reason_text}): "
            + " | ".join(
                _occurrence_text(occurrence) for occurrence in blocker.occurrences
            )
            + ". No package winner was selected."
        )
    elif blocker.kind is PackageLoadPlanBlockerKind.DIAMOND:
        reasons = ()
        target = (
            _coordinate_text(_package_coordinate(blocker.packages[0]))
            if blocker.packages
            else _coordinate_text(blocker.location.occurrence.coordinate)
        )
        message = (
            "Dependency diamond: "
            + " | ".join(
                _occurrence_text(occurrence) for occurrence in blocker.occurrences
            )
            + f" converge on {target}; the no-winner policy rejects deduplication."
        )
    else:
        raise ValueError("Package rejection diagnostics require a known blocker kind.")

    diagnostic = object.__new__(PackageRejectionDiagnostic)
    object.__setattr__(diagnostic, "blocker", blocker)
    object.__setattr__(diagnostic, "conflict_reasons", reasons)
    object.__setattr__(diagnostic, "message", message)
    return diagnostic


def _conflict_reasons(
    blocker: PackageLoadPlanBlocker,
) -> tuple[PackageConflictReason, ...]:
    current = blocker.location.occurrence
    if not blocker.packages:
        return (PackageConflictReason.INCOMPATIBLE_OCCURRENCES,)
    existing = blocker.packages[0]
    existing_coordinate = _package_coordinate(existing)
    same_physical_root = (
        blocker.location.directory_state.physical_identity
        == _package_physical_identity(existing)
    )
    reasons: list[PackageConflictReason] = []
    if same_physical_root and current.coordinate != existing_coordinate:
        reasons.append(PackageConflictReason.PHYSICAL_ROOT_INCOMPATIBLE_COORDINATE)
    if (
        not same_physical_root
        and current.coordinate.identity == existing_coordinate.identity
    ):
        reasons.append(PackageConflictReason.IDENTITY_DIFFERENT_PHYSICAL_ROOT)
    if current.content_digest_pin != _package_content_digest(existing):
        reasons.append(PackageConflictReason.INCOMPATIBLE_CONTENT_DIGEST_PIN)
    if not reasons:
        reasons.append(PackageConflictReason.INCOMPATIBLE_OCCURRENCES)
    return tuple(reasons)


def _occurrence_text(occurrence: PackageDependencyOccurrence) -> str:
    declaring = _coordinate_text(_package_coordinate(occurrence.declaring_package))
    dependency = _coordinate_text(occurrence.coordinate)
    return (
        f"{declaring} --dependency[{occurrence.position}] "
        f"path={occurrence.declaration.path!r} "
        f"resolved={occurrence.resolved_project_path!r}--> {dependency}"
    )


def _coordinate_text(coordinate: PackageCoordinate) -> str:
    if type(coordinate) is not PackageCoordinate:
        raise TypeError("Package rejection text requires a package coordinate.")
    return (
        f"namespace={coordinate.identity.namespace!r}, "
        f"name={coordinate.identity.name!r}, "
        f"version={coordinate.exact_version!r}"
    )


def _reason_text(reason: PackageConflictReason) -> str:
    return {
        PackageConflictReason.IDENTITY_DIFFERENT_PHYSICAL_ROOT: (
            "one identity resolves to incompatible local package authorities"
        ),
        PackageConflictReason.PHYSICAL_ROOT_INCOMPATIBLE_COORDINATE: (
            "one local package authority has incompatible coordinates"
        ),
        PackageConflictReason.INCOMPATIBLE_CONTENT_DIGEST_PIN: (
            "incompatible content digest pins"
        ),
        PackageConflictReason.INCOMPATIBLE_OCCURRENCES: (
            "non-identical dependency occurrences converge on one authority"
        ),
    }[reason]
