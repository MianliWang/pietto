"""Private exact package capability-requirement checking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
    DeclaredCapabilityProfileReferenceBucket,
    PackageCapabilityRequirementBinding,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderAuthority,
    ExtensionSignatureProviderContext,
    extension_signature_provider_authority,
    extension_signature_provider_inputs,
)
from pietto._project.package_load_plan import LoadedDependencyPackage, LoadedPackage
from pietto._project.package_loader import LoadedRootPackage
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionSuccess,
    EffectiveCapabilityProfileFactOccurrence,
)
from pietto.semantic.capability_facts import CapabilityDomain, CapabilitySupport
from pietto.semantic.capability_lookup import (
    Absent,
    CapabilityLookupResult,
    Conflict,
    Found,
    Unknown,
    lookup_capability,
)
from pietto.semantic.capability_profiles import (
    CapabilityRequirementOccurrence,
    StaticCapabilityProfile,
)
from pietto.semantic.capability_providers import (
    CanonicalCapabilityProviderInputs,
    canonical_capability_provider_inputs,
)

__all__: tuple[str, ...] = ()


class CapabilityRequirementStatus(StrEnum):
    SATISFIED = "satisfied"
    UNSUPPORTED = "unsupported"
    ABSENT = "absent"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class SelectedProfileAvailabilityBlockerKind(StrEnum):
    PROFILE_NOT_DECLARED_AVAILABLE = "profile_not_declared_available"
    PROFILE_AUTHORITY_MISMATCH = "profile_authority_mismatch"


@dataclass(frozen=True, slots=True)
class SelectedProfileAvailabilityBlocker:
    kind: SelectedProfileAvailabilityBlockerKind
    profile: StaticCapabilityProfile
    bucket: DeclaredCapabilityProfileReferenceBucket | None

    def __post_init__(self) -> None:
        if type(self.kind) is not SelectedProfileAvailabilityBlockerKind:
            raise ValueError("checking blocker requires an exact kind")
        if type(self.profile) is not StaticCapabilityProfile:
            raise ValueError("checking blocker requires an exact selected profile")
        if (
            self.kind
            is SelectedProfileAvailabilityBlockerKind.PROFILE_NOT_DECLARED_AVAILABLE
        ):
            if self.bucket is not None:
                raise ValueError(
                    "undeclared profile blocker forbids an availability bucket"
                )
            return
        if type(self.bucket) is not DeclaredCapabilityProfileReferenceBucket:
            raise ValueError("authority mismatch blocker requires an exact bucket")
        if (
            self.bucket.reference != self.profile.profile
            or self.bucket.profile is self.profile
        ):
            raise ValueError(
                "authority mismatch blocker requires a foreign exact authority"
            )


def _lookup_result_matches(
    actual: CapabilityLookupResult,
    expected: CapabilityLookupResult,
) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, Found):
        return isinstance(actual, Found) and actual.fact is expected.fact
    if isinstance(expected, Absent):
        return (
            isinstance(actual, Absent)
            and actual.key is expected.key
            and actual.reason is expected.reason
        )
    if isinstance(expected, Unknown):
        return isinstance(actual, Unknown) and actual.reason is expected.reason
    assert isinstance(actual, Conflict) and isinstance(expected, Conflict)
    return (
        actual.reason is expected.reason
        and len(actual.evidence) == len(expected.evidence)
        and all(
            left is right
            for left, right in zip(actual.evidence, expected.evidence, strict=True)
        )
    )


def _provider_inputs_match(
    actual: CanonicalCapabilityProviderInputs,
    expected: CanonicalCapabilityProviderInputs,
) -> bool:
    return (
        actual.key is expected.key
        and actual.domain_complete is expected.domain_complete
        and actual.unknown_reason is expected.unknown_reason
        and len(actual.facts) == len(expected.facts)
        and all(
            left is right
            for left, right in zip(actual.facts, expected.facts, strict=True)
        )
    )


def _derive_requirement_status(
    target_result: CapabilityLookupResult,
    provider_result: CapabilityLookupResult,
) -> CapabilityRequirementStatus:
    if type(target_result) is Conflict or type(provider_result) is Conflict:
        return CapabilityRequirementStatus.CONFLICT
    if any(
        type(result) is Found
        and result.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
        for result in (target_result, provider_result)
    ):
        return CapabilityRequirementStatus.UNSUPPORTED
    if type(provider_result) is Absent:
        return CapabilityRequirementStatus.ABSENT
    if type(target_result) is Unknown or type(provider_result) is Unknown:
        return CapabilityRequirementStatus.UNKNOWN
    if (
        type(target_result) is Found
        and target_result.fact.support is CapabilitySupport.SUPPORTED
        and type(provider_result) is Found
        and provider_result.fact.support is CapabilitySupport.SUPPORTED
    ):
        return CapabilityRequirementStatus.SATISFIED
    raise AssertionError("capability requirement lookup algebra must be total")


@dataclass(frozen=True, slots=True)
class CapabilityRequirementCheck:
    occurrence: CapabilityRequirementOccurrence
    target_occurrences: tuple[EffectiveCapabilityProfileFactOccurrence, ...]
    target_result: CapabilityLookupResult
    provider_inputs: CanonicalCapabilityProviderInputs
    provider_result: CapabilityLookupResult
    status: CapabilityRequirementStatus
    extension_signature_provider_authority: (
        ExtensionSignatureProviderAuthority | None
    ) = field(default=None, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if type(self.occurrence) is not CapabilityRequirementOccurrence:
            raise ValueError("requirement check requires an exact occurrence")
        if type(self.target_occurrences) is not tuple or any(
            type(item) is not EffectiveCapabilityProfileFactOccurrence
            for item in self.target_occurrences
        ):
            raise ValueError("requirement check requires exact target occurrences")
        if any(
            item.fact.key != self.occurrence.key for item in self.target_occurrences
        ):
            raise ValueError("requirement check requires exact-key target occurrences")
        if type(self.target_result) not in {Found, Absent, Unknown, Conflict}:
            raise ValueError("requirement check requires an exact target result")
        if type(self.provider_inputs) is not CanonicalCapabilityProviderInputs:
            raise ValueError("requirement check requires exact provider inputs")
        if type(self.provider_result) not in {Found, Absent, Unknown, Conflict}:
            raise ValueError("requirement check requires an exact provider result")
        if type(self.status) is not CapabilityRequirementStatus:
            raise ValueError("requirement check requires an exact status")

        expected_target = lookup_capability(
            self.occurrence.key,
            tuple(item.fact for item in self.target_occurrences),
            domain_complete=False,
        )
        authority = self.extension_signature_provider_authority
        if authority is None:
            expected_inputs = canonical_capability_provider_inputs(self.occurrence.key)
        else:
            if type(authority) is not ExtensionSignatureProviderAuthority:
                raise ValueError(
                    "requirement check requires exact extension provider authority"
                )
            if authority.requirement is not self.occurrence:
                raise ValueError(
                    "requirement check requires matching extension provider authority"
                )
            expected_inputs = extension_signature_provider_inputs(authority)
        expected_provider = lookup_capability(
            expected_inputs.key,
            expected_inputs.facts,
            domain_complete=expected_inputs.domain_complete,
            unknown_reason=expected_inputs.unknown_reason,
        )
        if not _lookup_result_matches(self.target_result, expected_target):
            raise ValueError("requirement check requires canonical target lookup")
        if authority is None and not _provider_inputs_match(
            self.provider_inputs,
            expected_inputs,
        ):
            raise ValueError("requirement check requires canonical provider inputs")
        if authority is not None and self.provider_inputs is not expected_inputs:
            raise ValueError(
                "requirement check requires canonical extension provider inputs"
            )
        if not _lookup_result_matches(self.provider_result, expected_provider):
            raise ValueError("requirement check requires canonical provider lookup")
        if self.status is not _derive_requirement_status(
            expected_target,
            expected_provider,
        ):
            raise ValueError("requirement check requires canonical status")


def _validate_common_authority(
    package: object,
    composition: object,
    availability: object,
) -> None:
    if type(package) not in {LoadedRootPackage, LoadedDependencyPackage}:
        raise ValueError("capability checking requires an exact loaded package")
    if type(composition) is not CapabilityProfileCompositionSuccess:
        raise ValueError("capability checking requires a successful composition")
    if type(availability) is not DeclaredCapabilityProfileAvailabilityReady:
        raise ValueError("capability checking requires ready availability")


def _selected_profile_availability_blockers(
    composition: CapabilityProfileCompositionSuccess,
    availability: DeclaredCapabilityProfileAvailabilityReady,
) -> tuple[SelectedProfileAvailabilityBlocker, ...]:
    buckets = {bucket.reference: bucket for bucket in availability.reference_buckets}
    blockers: list[SelectedProfileAvailabilityBlocker] = []
    for profile in composition.dependency_order:
        bucket = buckets.get(profile.profile)
        if bucket is None:
            blockers.append(
                SelectedProfileAvailabilityBlocker(
                    SelectedProfileAvailabilityBlockerKind.PROFILE_NOT_DECLARED_AVAILABLE,
                    profile,
                    None,
                )
            )
        elif bucket.profile is not profile:
            blockers.append(
                SelectedProfileAvailabilityBlocker(
                    SelectedProfileAvailabilityBlockerKind.PROFILE_AUTHORITY_MISMATCH,
                    profile,
                    bucket,
                )
            )
    return tuple(blockers)


def _build_requirement_check(
    occurrence: CapabilityRequirementOccurrence,
    composition: CapabilityProfileCompositionSuccess,
    extension_authority: ExtensionSignatureProviderAuthority | None = None,
) -> CapabilityRequirementCheck:
    target_occurrences = tuple(
        item
        for item in composition.effective_occurrences
        if item.fact.key == occurrence.key
    )
    target_result = lookup_capability(
        occurrence.key,
        tuple(item.fact for item in target_occurrences),
        domain_complete=False,
    )
    if extension_authority is None:
        provider_inputs = canonical_capability_provider_inputs(occurrence.key)
    else:
        if extension_authority.requirement is not occurrence:
            raise ValueError("extension provider authority must match its requirement")
        provider_inputs = extension_authority.provider_inputs
    provider_result = lookup_capability(
        provider_inputs.key,
        provider_inputs.facts,
        domain_complete=provider_inputs.domain_complete,
        unknown_reason=provider_inputs.unknown_reason,
    )
    return CapabilityRequirementCheck(
        occurrence,
        target_occurrences,
        target_result,
        provider_inputs,
        provider_result,
        _derive_requirement_status(target_result, provider_result),
        extension_authority,
    )


@dataclass(frozen=True, slots=True)
class PackageCapabilityRequirementsUndeclared:
    package: LoadedPackage
    composition: CapabilityProfileCompositionSuccess
    availability: DeclaredCapabilityProfileAvailabilityReady

    def __post_init__(self) -> None:
        _validate_common_authority(self.package, self.composition, self.availability)


@dataclass(frozen=True, slots=True)
class PackageCapabilityRequirementsBlocked:
    package: LoadedPackage
    binding: PackageCapabilityRequirementBinding
    composition: CapabilityProfileCompositionSuccess
    availability: DeclaredCapabilityProfileAvailabilityReady
    blockers: tuple[SelectedProfileAvailabilityBlocker, ...]

    def __post_init__(self) -> None:
        _validate_common_authority(self.package, self.composition, self.availability)
        if type(self.binding) is not PackageCapabilityRequirementBinding:
            raise ValueError("blocked capability checking requires an exact binding")
        if self.binding.package is not self.package:
            raise ValueError(
                "blocked capability checking requires exact package authority"
            )
        if (
            type(self.blockers) is not tuple
            or not self.blockers
            or any(
                type(blocker) is not SelectedProfileAvailabilityBlocker
                for blocker in self.blockers
            )
        ):
            raise ValueError("blocked capability checking requires exact blockers")
        expected = _selected_profile_availability_blockers(
            self.composition,
            self.availability,
        )
        if len(self.blockers) != len(expected) or any(
            actual.kind is not authority.kind
            or actual.profile is not authority.profile
            or actual.bucket is not authority.bucket
            for actual, authority in zip(self.blockers, expected, strict=True)
        ):
            raise ValueError("blocked capability checking requires canonical blockers")


def _check_matches(
    actual: CapabilityRequirementCheck,
    expected: CapabilityRequirementCheck,
) -> bool:
    return (
        actual.occurrence is expected.occurrence
        and len(actual.target_occurrences) == len(expected.target_occurrences)
        and all(
            left is right
            for left, right in zip(
                actual.target_occurrences,
                expected.target_occurrences,
                strict=True,
            )
        )
        and _lookup_result_matches(actual.target_result, expected.target_result)
        and _provider_inputs_match(actual.provider_inputs, expected.provider_inputs)
        and _lookup_result_matches(actual.provider_result, expected.provider_result)
        and actual.status is expected.status
        and actual.extension_signature_provider_authority
        is expected.extension_signature_provider_authority
    )


@dataclass(frozen=True, slots=True)
class PackageCapabilityRequirementsChecked:
    package: LoadedPackage
    binding: PackageCapabilityRequirementBinding
    composition: CapabilityProfileCompositionSuccess
    availability: DeclaredCapabilityProfileAvailabilityReady
    checks: tuple[CapabilityRequirementCheck, ...]

    def __post_init__(self) -> None:
        _validate_common_authority(self.package, self.composition, self.availability)
        if type(self.binding) is not PackageCapabilityRequirementBinding:
            raise ValueError("checked capability requirements require an exact binding")
        if self.binding.package is not self.package:
            raise ValueError(
                "checked capability requirements require exact package authority"
            )
        if _selected_profile_availability_blockers(self.composition, self.availability):
            raise ValueError(
                "checked capability requirements require available profiles"
            )
        if type(self.checks) is not tuple or any(
            type(check) is not CapabilityRequirementCheck for check in self.checks
        ):
            raise ValueError("checked capability requirements require exact checks")
        occurrences = self.binding.requirements.occurrences
        if len(self.checks) != len(occurrences):
            raise ValueError(
                "checked capability requirements require one check per occurrence"
            )
        for check, occurrence in zip(self.checks, occurrences, strict=True):
            if check.occurrence is not occurrence:
                raise ValueError(
                    "checked capability requirements require declaration order"
                )
            expected = _build_requirement_check(
                occurrence,
                self.composition,
                check.extension_signature_provider_authority,
            )
            if not _check_matches(check, expected):
                raise ValueError(
                    "checked capability requirements require canonical checks"
                )

    @property
    def all_satisfied(self) -> bool:
        return all(
            check.status is CapabilityRequirementStatus.SATISFIED
            for check in self.checks
        )


type PackageCapabilityRequirementsResult = (
    PackageCapabilityRequirementsUndeclared
    | PackageCapabilityRequirementsBlocked
    | PackageCapabilityRequirementsChecked
)


def check_package_capability_requirements(
    package: LoadedPackage,
    binding: PackageCapabilityRequirementBinding | None,
    composition: CapabilityProfileCompositionSuccess,
    availability: DeclaredCapabilityProfileAvailabilityReady,
    extension_signature_provider_context: (
        ExtensionSignatureProviderContext | None
    ) = None,
) -> PackageCapabilityRequirementsResult:
    _validate_common_authority(package, composition, availability)
    if (
        extension_signature_provider_context is not None
        and type(extension_signature_provider_context)
        is not ExtensionSignatureProviderContext
    ):
        raise ValueError("capability checking requires an exact provider context")
    if binding is None:
        if extension_signature_provider_context is not None:
            raise ValueError("undeclared capability checking forbids provider context")
        return PackageCapabilityRequirementsUndeclared(
            package,
            composition,
            availability,
        )
    if type(binding) is not PackageCapabilityRequirementBinding:
        raise ValueError("capability checking requires an exact requirement binding")
    if binding.package is not package:
        raise ValueError(
            "capability checking rejects foreign package binding authority"
        )
    if (
        extension_signature_provider_context is not None
        and extension_signature_provider_context.selectors.requirements
        is not binding.requirements
    ):
        raise ValueError(
            "capability checking rejects a foreign requirement provider context"
        )
    blockers = _selected_profile_availability_blockers(composition, availability)
    if blockers:
        return PackageCapabilityRequirementsBlocked(
            package,
            binding,
            composition,
            availability,
            blockers,
        )
    checks = tuple(
        _build_requirement_check(
            occurrence,
            composition,
            (
                None
                if extension_signature_provider_context is None
                or occurrence.key.domain is not CapabilityDomain.EXTENSION_SIGNATURE
                else extension_signature_provider_authority(
                    extension_signature_provider_context,
                    occurrence,
                )
            ),
        )
        for occurrence in binding.requirements.occurrences
    )
    return PackageCapabilityRequirementsChecked(
        package,
        binding,
        composition,
        availability,
        checks,
    )
