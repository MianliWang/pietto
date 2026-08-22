"""Private declared profile availability and package requirement ownership."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto._project.model import ProjectRoot
from pietto._project.package_load_plan import LoadedDependencyPackage, LoadedPackage
from pietto._project.package_loader import LoadedRootPackage
from pietto.semantic.capability_profiles import (
    CapabilityProfileReference,
    CapabilityRequirementCollection,
    StaticCapabilityProfile,
)

__all__: tuple[str, ...] = ()


class CompilerCapabilityProfileAvailabilityAuthority(StrEnum):
    COMPILER = "compiler"


type CapabilityProfileAvailabilityOwner = (
    CompilerCapabilityProfileAvailabilityAuthority | ProjectRoot
)


@dataclass(frozen=True, slots=True)
class CapabilityProfileAvailabilityOccurrence:
    owner: CapabilityProfileAvailabilityOwner
    position: int
    profile: StaticCapabilityProfile

    def __post_init__(self) -> None:
        if type(self.owner) not in {
            CompilerCapabilityProfileAvailabilityAuthority,
            ProjectRoot,
        }:
            raise ValueError("profile availability requires an exact owner")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("profile availability requires a non-negative position")
        if type(self.profile) is not StaticCapabilityProfile:
            raise ValueError("profile availability requires an exact profile")

    @property
    def reference(self) -> CapabilityProfileReference:
        return self.profile.profile


def _validate_occurrences(
    occurrences: object,
    label: str,
) -> tuple[CapabilityProfileAvailabilityOccurrence, ...]:
    frozen = _validate_occurrences_without_positions(occurrences, label)
    if any(
        occurrence.position != position for position, occurrence in enumerate(frozen)
    ):
        raise ValueError(f"{label} positions must be dense and declaration ordered")
    return frozen


@dataclass(frozen=True, slots=True)
class CompilerCapabilityProfileAvailabilityLedger:
    occurrences: tuple[CapabilityProfileAvailabilityOccurrence, ...]

    def __post_init__(self) -> None:
        occurrences = _validate_occurrences(self.occurrences, "compiler availability")
        if any(
            occurrence.owner
            is not CompilerCapabilityProfileAvailabilityAuthority.COMPILER
            for occurrence in occurrences
        ):
            raise ValueError("compiler availability requires compiler owner authority")


@dataclass(frozen=True, slots=True)
class ProjectCapabilityProfileAvailabilityLedger:
    project: ProjectRoot
    occurrences: tuple[CapabilityProfileAvailabilityOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.project) is not ProjectRoot:
            raise ValueError("project availability requires an exact project root")
        occurrences = _validate_occurrences(self.occurrences, "project availability")
        if any(occurrence.owner is not self.project for occurrence in occurrences):
            raise ValueError("project availability requires exact project authority")


class DeclaredCapabilityProfileAvailabilityBlockerKind(StrEnum):
    EXACT_DUPLICATE_AVAILABILITY_DECLARATION = (
        "exact_duplicate_availability_declaration"
    )
    AMBIGUOUS_PROFILE_REFERENCE = "ambiguous_profile_reference"


@dataclass(frozen=True, slots=True)
class DeclaredCapabilityProfileAvailabilityBlocker:
    kind: DeclaredCapabilityProfileAvailabilityBlockerKind
    occurrences: tuple[CapabilityProfileAvailabilityOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.kind) is not DeclaredCapabilityProfileAvailabilityBlockerKind:
            raise ValueError("availability blocker requires an exact kind")
        occurrences = _validate_occurrences_without_positions(
            self.occurrences,
            "availability blocker",
        )
        if len(occurrences) < 2:
            raise ValueError("availability blocker requires multiple occurrences")
        reference = occurrences[0].reference
        if any(occurrence.reference != reference for occurrence in occurrences[1:]):
            raise ValueError("availability blocker requires one exact reference")
        if self.kind is (
            DeclaredCapabilityProfileAvailabilityBlockerKind.EXACT_DUPLICATE_AVAILABILITY_DECLARATION
        ):
            first = occurrences[0]
            if any(
                occurrence.owner is not first.owner
                or occurrence.profile is not first.profile
                for occurrence in occurrences[1:]
            ):
                raise ValueError(
                    "duplicate availability blocker requires one exact authority"
                )
        elif len({id(occurrence.profile) for occurrence in occurrences}) < 2:
            raise ValueError(
                "ambiguous availability blocker requires distinct profile authorities"
            )

    @property
    def reference(self) -> CapabilityProfileReference:
        return self.occurrences[0].reference


def _validate_occurrences_without_positions(
    occurrences: object,
    label: str,
) -> tuple[CapabilityProfileAvailabilityOccurrence, ...]:
    if type(occurrences) is not tuple or any(
        type(occurrence) is not CapabilityProfileAvailabilityOccurrence
        for occurrence in occurrences
    ):
        raise ValueError(f"{label} requires exact availability occurrences")
    return occurrences


@dataclass(frozen=True, slots=True)
class DeclaredCapabilityProfileReferenceBucket:
    reference: CapabilityProfileReference
    profile: StaticCapabilityProfile
    occurrences: tuple[CapabilityProfileAvailabilityOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.reference) is not CapabilityProfileReference:
            raise ValueError("availability bucket requires an exact reference")
        if type(self.profile) is not StaticCapabilityProfile:
            raise ValueError("availability bucket requires an exact profile")
        occurrences = _validate_occurrences_without_positions(
            self.occurrences,
            "availability bucket",
        )
        if not occurrences or any(
            occurrence.profile is not self.profile
            or occurrence.reference != self.reference
            for occurrence in occurrences
        ):
            raise ValueError("availability bucket requires one exact profile authority")


@dataclass(frozen=True, slots=True)
class DeclaredCapabilityProfileAvailabilityReady:
    compiler: CompilerCapabilityProfileAvailabilityLedger
    project: ProjectCapabilityProfileAvailabilityLedger | None
    occurrences: tuple[CapabilityProfileAvailabilityOccurrence, ...]
    reference_buckets: tuple[DeclaredCapabilityProfileReferenceBucket, ...]

    def __post_init__(self) -> None:
        expected = _validate_availability_authority(
            self.compiler,
            self.project,
            self.occurrences,
        )
        if type(self.reference_buckets) is not tuple or any(
            type(bucket) is not DeclaredCapabilityProfileReferenceBucket
            for bucket in self.reference_buckets
        ):
            raise ValueError("ready availability requires exact reference buckets")
        expected_groups: dict[
            CapabilityProfileReference,
            list[CapabilityProfileAvailabilityOccurrence],
        ] = {}
        for occurrence in expected:
            expected_groups.setdefault(occurrence.reference, []).append(occurrence)
        if tuple(bucket.reference for bucket in self.reference_buckets) != tuple(
            expected_groups
        ):
            raise ValueError("ready availability requires exact declaration authority")
        for bucket, group in zip(
            self.reference_buckets,
            expected_groups.values(),
            strict=True,
        ):
            if len(bucket.occurrences) != len(group) or any(
                actual is not authority
                for actual, authority in zip(bucket.occurrences, group, strict=True)
            ):
                raise ValueError(
                    "ready availability requires exact declaration authority"
                )

    @property
    def profiles(self) -> tuple[StaticCapabilityProfile, ...]:
        return tuple(bucket.profile for bucket in self.reference_buckets)


@dataclass(frozen=True, slots=True)
class DeclaredCapabilityProfileAvailabilityBlocked:
    compiler: CompilerCapabilityProfileAvailabilityLedger
    project: ProjectCapabilityProfileAvailabilityLedger | None
    occurrences: tuple[CapabilityProfileAvailabilityOccurrence, ...]
    blockers: tuple[DeclaredCapabilityProfileAvailabilityBlocker, ...]

    def __post_init__(self) -> None:
        expected = _validate_availability_authority(
            self.compiler,
            self.project,
            self.occurrences,
        )
        if (
            type(self.blockers) is not tuple
            or not self.blockers
            or any(
                type(blocker) is not DeclaredCapabilityProfileAvailabilityBlocker
                for blocker in self.blockers
            )
        ):
            raise ValueError("blocked availability requires exact blocker evidence")
        expected_ids = {id(occurrence) for occurrence in expected}
        if any(
            id(occurrence) not in expected_ids
            for blocker in self.blockers
            for occurrence in blocker.occurrences
        ):
            raise ValueError("blocked availability requires declared blocker authority")


type DeclaredCapabilityProfileAvailabilityResult = (
    DeclaredCapabilityProfileAvailabilityReady
    | DeclaredCapabilityProfileAvailabilityBlocked
)


def _validate_availability_authority(
    compiler: object,
    project: object,
    occurrences: object,
) -> tuple[CapabilityProfileAvailabilityOccurrence, ...]:
    if type(compiler) is not CompilerCapabilityProfileAvailabilityLedger:
        raise ValueError("availability result requires exact compiler authority")
    if (
        project is not None
        and type(project) is not ProjectCapabilityProfileAvailabilityLedger
    ):
        raise ValueError("availability result requires exact project authority")
    expected = compiler.occurrences + (() if project is None else project.occurrences)
    actual = _validate_occurrences_without_positions(occurrences, "availability result")
    if len(actual) != len(expected) or any(
        left is not right for left, right in zip(actual, expected, strict=True)
    ):
        raise ValueError("availability result requires exact declaration ledgers")
    return expected


def build_declared_capability_profile_availability(
    compiler: CompilerCapabilityProfileAvailabilityLedger,
    project: ProjectCapabilityProfileAvailabilityLedger | None = None,
) -> DeclaredCapabilityProfileAvailabilityResult:
    if type(compiler) is not CompilerCapabilityProfileAvailabilityLedger:
        raise ValueError("availability construction requires an exact compiler ledger")
    if (
        project is not None
        and type(project) is not ProjectCapabilityProfileAvailabilityLedger
    ):
        raise ValueError("availability construction requires an exact project ledger")
    occurrences = compiler.occurrences + (
        () if project is None else project.occurrences
    )
    combined_positions = {
        id(occurrence): position for position, occurrence in enumerate(occurrences)
    }
    duplicate_groups: dict[
        tuple[int, int],
        list[CapabilityProfileAvailabilityOccurrence],
    ] = {}
    reference_groups: dict[
        CapabilityProfileReference,
        list[CapabilityProfileAvailabilityOccurrence],
    ] = {}
    for occurrence in occurrences:
        duplicate_groups.setdefault(
            (id(occurrence.owner), id(occurrence.profile)),
            [],
        ).append(occurrence)
        reference_groups.setdefault(occurrence.reference, []).append(occurrence)

    blocker_records: list[
        tuple[int, int, DeclaredCapabilityProfileAvailabilityBlocker]
    ] = []
    for group in duplicate_groups.values():
        if len(group) > 1:
            blocker_records.append(
                (
                    combined_positions[id(group[0])],
                    0,
                    DeclaredCapabilityProfileAvailabilityBlocker(
                        DeclaredCapabilityProfileAvailabilityBlockerKind.EXACT_DUPLICATE_AVAILABILITY_DECLARATION,
                        tuple(group),
                    ),
                )
            )
    for group in reference_groups.values():
        if len({id(occurrence.profile) for occurrence in group}) > 1:
            blocker_records.append(
                (
                    combined_positions[id(group[0])],
                    1,
                    DeclaredCapabilityProfileAvailabilityBlocker(
                        DeclaredCapabilityProfileAvailabilityBlockerKind.AMBIGUOUS_PROFILE_REFERENCE,
                        tuple(group),
                    ),
                )
            )
    if blocker_records:
        blocker_records.sort(key=lambda record: (record[0], record[1]))
        return DeclaredCapabilityProfileAvailabilityBlocked(
            compiler,
            project,
            occurrences,
            tuple(record[2] for record in blocker_records),
        )

    buckets = tuple(
        DeclaredCapabilityProfileReferenceBucket(
            reference,
            group[0].profile,
            tuple(group),
        )
        for reference, group in reference_groups.items()
    )
    return DeclaredCapabilityProfileAvailabilityReady(
        compiler,
        project,
        occurrences,
        buckets,
    )


@dataclass(frozen=True, slots=True)
class PackageCapabilityRequirementBinding:
    package: LoadedPackage
    requirements: CapabilityRequirementCollection

    def __post_init__(self) -> None:
        if type(self.package) not in {LoadedRootPackage, LoadedDependencyPackage}:
            raise ValueError("package requirements require an exact loaded package")
        if type(self.requirements) is not CapabilityRequirementCollection:
            raise ValueError(
                "package requirements require an exact requirement collection"
            )
