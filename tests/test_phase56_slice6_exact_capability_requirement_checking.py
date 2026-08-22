from __future__ import annotations

from collections import Counter
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto._project as project_package
import pietto._project.capability_checking as checking
import test_phase56_slice3_canonical_capability_providers as slice3
import test_phase56_slice4_capability_profile_composition as slice4
import test_phase56_slice5_declared_profile_availability as slice5

from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
    PackageCapabilityRequirementBinding,
    build_declared_capability_profile_availability,
)
from pietto._project.capability_checking import (
    CapabilityRequirementCheck,
    CapabilityRequirementStatus,
    PackageCapabilityRequirementsBlocked,
    PackageCapabilityRequirementsChecked,
    PackageCapabilityRequirementsUndeclared,
    SelectedProfileAvailabilityBlocker,
    SelectedProfileAvailabilityBlockerKind,
    check_package_capability_requirements,
)
from pietto._project.package_load_plan import LoadedDependencyPackage
from pietto._project.package_loader import LoadedRootPackage
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionSuccess,
    compose_capability_profiles,
)
from pietto.semantic.capability_facts import (
    CapabilityDisposition,
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidence,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)
from pietto.semantic.capability_lookup import Absent, Conflict, Found, Unknown
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
)
from pietto.semantic.capability_providers import canonical_capability_provider_inputs


_PROVIDER_FACTS = slice3._all_facts()
_SUPPORTED_PROVIDER_FACT = next(
    fact for fact in _PROVIDER_FACTS if fact.support is CapabilitySupport.SUPPORTED
)
_UNSUPPORTED_PROVIDER_FACT = next(
    fact
    for fact in _PROVIDER_FACTS
    if fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
)
_COUNT_CONFLICT_KEY = next(
    key
    for key, count in Counter(fact.key for fact in _PROVIDER_FACTS).items()
    if count > 1
)


@pytest.fixture(scope="module")
def loaded_packages(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[LoadedRootPackage, LoadedDependencyPackage]:
    return slice5._loaded_packages(tmp_path_factory.mktemp("slice6-packages"))


def _target_fact(
    key: CapabilityKey,
    *,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    disposition: CapabilityDisposition | None = None,
    reference: str = "target declaration",
) -> CapabilityFact:
    return CapabilityFact(
        key,
        support,
        CapabilityDisposition(CapabilityDispositionKind.NONE)
        if disposition is None
        else disposition,
        (
            CapabilityEvidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase56_slice6_exact_capability_requirement_checking.py",
                reference,
            ),
        ),
    )


def _requirements(*keys: CapabilityKey) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity("consumer", "slice6")
    return CapabilityRequirementCollection(
        identity,
        tuple(
            CapabilityRequirementOccurrence(identity, position, key)
            for position, key in enumerate(keys)
        ),
    )


def _composition(
    *facts: CapabilityFact,
) -> CapabilityProfileCompositionSuccess:
    base = slice4._base(facts=tuple(facts))
    result = compose_capability_profiles(base, ())
    assert isinstance(result, CapabilityProfileCompositionSuccess)
    return result


def _availability(
    composition: CapabilityProfileCompositionSuccess,
    *profiles: object,
) -> DeclaredCapabilityProfileAvailabilityReady:
    selected = (
        composition.dependency_order
        if not profiles
        else cast(tuple[Any, ...], profiles)
    )
    result = build_declared_capability_profile_availability(
        slice5._compiler_ledger(*selected)
    )
    assert isinstance(result, DeclaredCapabilityProfileAvailabilityReady)
    return result


def _binding(
    package: LoadedRootPackage | LoadedDependencyPackage,
    *keys: CapabilityKey,
) -> PackageCapabilityRequirementBinding:
    return PackageCapabilityRequirementBinding(package, _requirements(*keys))


def _checked(
    package: LoadedRootPackage | LoadedDependencyPackage,
    composition: CapabilityProfileCompositionSuccess,
    *keys: CapabilityKey,
    availability: DeclaredCapabilityProfileAvailabilityReady | None = None,
) -> PackageCapabilityRequirementsChecked:
    result = check_package_capability_requirements(
        package,
        _binding(package, *keys),
        composition,
        _availability(composition) if availability is None else availability,
    )
    assert isinstance(result, PackageCapabilityRequirementsChecked)
    return result


def test_no_requirement_binding_is_undeclared_not_empty_success(
    tmp_path: Path,
) -> None:
    package, _dependency = slice5._loaded_packages(tmp_path)
    base = slice4._base()
    composition = compose_capability_profiles(base, ())
    assert isinstance(composition, CapabilityProfileCompositionSuccess)
    availability = build_declared_capability_profile_availability(
        slice5._compiler_ledger(base)
    )
    assert isinstance(availability, DeclaredCapabilityProfileAvailabilityReady)
    result = check_package_capability_requirements(
        package,
        None,
        composition,
        availability,
    )

    assert isinstance(result, PackageCapabilityRequirementsUndeclared)
    assert result.package is package
    assert result.composition is composition
    assert result.availability is availability
    assert not hasattr(result, "checks")


def test_explicit_empty_binding_is_checked_and_vacuously_satisfied(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    composition = _composition()
    result = _checked(package, composition)

    assert isinstance(result, PackageCapabilityRequirementsChecked)
    assert result.binding.requirements.occurrences == ()
    assert result.checks == ()
    assert result.all_satisfied is True


def test_foreign_binding_package_authority_is_rejected(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, dependency = loaded_packages
    composition = _composition()
    with pytest.raises(ValueError, match="foreign package binding authority"):
        check_package_capability_requirements(
            package,
            _binding(dependency),
            composition,
            _availability(composition),
        )


def test_selected_base_not_declared_available_blocks_without_checks(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, _dependency = loaded_packages
    composition = _composition()
    availability = build_declared_capability_profile_availability(
        slice5._compiler_ledger()
    )
    assert isinstance(availability, DeclaredCapabilityProfileAvailabilityReady)

    def forbidden(_key: CapabilityKey) -> Any:
        raise AssertionError("blocked checking invoked canonical provider")

    monkeypatch.setattr(checking, "canonical_capability_provider_inputs", forbidden)
    result = check_package_capability_requirements(
        package,
        _binding(package, _SUPPORTED_PROVIDER_FACT.key),
        composition,
        availability,
    )

    assert isinstance(result, PackageCapabilityRequirementsBlocked)
    assert not hasattr(result, "checks")
    assert tuple(blocker.kind for blocker in result.blockers) == (
        SelectedProfileAvailabilityBlockerKind.PROFILE_NOT_DECLARED_AVAILABLE,
    )
    assert result.blockers[0].profile is composition.base
    assert result.blockers[0].bucket is None


def test_selected_overlay_not_declared_available_is_blocked(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    base = slice4._base()
    overlay = slice4._overlay("overlay", base.profile)
    composition = compose_capability_profiles(base, (overlay,))
    assert isinstance(composition, CapabilityProfileCompositionSuccess)
    availability = _availability(composition, base)
    result = check_package_capability_requirements(
        package,
        _binding(package),
        composition,
        availability,
    )

    assert isinstance(result, PackageCapabilityRequirementsBlocked)
    assert tuple(blocker.profile for blocker in result.blockers) == (overlay,)


def test_same_reference_foreign_profile_authority_is_blocked_without_substitution(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    composition = _composition()
    foreign = slice4._base()
    assert foreign == composition.base and foreign is not composition.base
    availability = _availability(composition, foreign)
    result = check_package_capability_requirements(
        package,
        _binding(package),
        composition,
        availability,
    )

    assert isinstance(result, PackageCapabilityRequirementsBlocked)
    blocker = result.blockers[0]
    assert (
        blocker.kind
        is SelectedProfileAvailabilityBlockerKind.PROFILE_AUTHORITY_MISMATCH
    )
    assert blocker.profile is composition.base
    assert blocker.bucket is availability.reference_buckets[0]
    assert blocker.bucket is not None
    assert blocker.bucket.profile is foreign


def test_all_availability_blockers_follow_composition_dependency_order(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    base = slice4._base()
    parent = slice4._overlay("parent", base.profile)
    child = slice4._overlay("child", parent.profile)
    composition = compose_capability_profiles(base, (child, parent))
    assert isinstance(composition, CapabilityProfileCompositionSuccess)
    foreign_base = slice4._base()
    availability = _availability(composition, foreign_base)
    result = check_package_capability_requirements(
        package,
        _binding(package),
        composition,
        availability,
    )

    assert isinstance(result, PackageCapabilityRequirementsBlocked)
    assert tuple(blocker.profile for blocker in result.blockers) == (
        base,
        parent,
        child,
    )
    assert tuple(blocker.kind for blocker in result.blockers) == (
        SelectedProfileAvailabilityBlockerKind.PROFILE_AUTHORITY_MISMATCH,
        SelectedProfileAvailabilityBlockerKind.PROFILE_NOT_DECLARED_AVAILABLE,
        SelectedProfileAvailabilityBlockerKind.PROFILE_NOT_DECLARED_AVAILABLE,
    )


def test_extra_unselected_available_profile_does_not_affect_checking(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    composition = _composition()
    extra = slice4._base("extra")
    availability = _availability(composition, composition.base, extra)
    result = check_package_capability_requirements(
        package,
        _binding(package),
        composition,
        availability,
    )

    assert isinstance(result, PackageCapabilityRequirementsChecked)
    assert result.availability.profiles == (composition.base, extra)


def test_distinct_supported_target_and_provider_evidence_is_satisfied(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    target = _target_fact(_SUPPORTED_PROVIDER_FACT.key)
    result = _checked(package, _composition(target), target.key)
    check = result.checks[0]

    assert check.status is CapabilityRequirementStatus.SATISFIED
    assert isinstance(check.target_result, Found)
    assert isinstance(check.provider_result, Found)
    assert check.target_result.fact is target
    assert check.provider_result.fact is _SUPPORTED_PROVIDER_FACT
    assert check.target_result.fact != check.provider_result.fact
    assert result.all_satisfied is True


def test_target_explicitly_unsupported_is_unsupported(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    target = _target_fact(
        _SUPPORTED_PROVIDER_FACT.key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    check = _checked(package, _composition(target), target.key).checks[0]

    assert check.status is CapabilityRequirementStatus.UNSUPPORTED
    assert isinstance(check.target_result, Found)
    assert check.target_result.fact is target


def test_provider_explicitly_unsupported_is_unsupported(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    target = _target_fact(_UNSUPPORTED_PROVIDER_FACT.key)
    check = _checked(package, _composition(target), target.key).checks[0]

    assert check.status is CapabilityRequirementStatus.UNSUPPORTED
    assert isinstance(check.provider_result, Found)
    assert check.provider_result.fact is _UNSUPPORTED_PROVIDER_FACT


def test_provider_complete_zero_match_is_absent(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="catalog_membership",
        context="builtin_registry",
    )
    target = _target_fact(key)
    check = _checked(package, _composition(target), key).checks[0]

    assert check.status is CapabilityRequirementStatus.ABSENT
    assert isinstance(check.target_result, Found)
    assert isinstance(check.provider_result, Absent)


def test_target_omission_never_becomes_absent(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = _SUPPORTED_PROVIDER_FACT.key
    check = _checked(package, _composition(), key).checks[0]

    assert check.status is CapabilityRequirementStatus.UNKNOWN
    assert check.target_result == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert isinstance(check.provider_result, Found)


@pytest.mark.parametrize(
    "domain",
    (
        CapabilityDomain.CONVERSION,
        CapabilityDomain.DIALECT_LOWERING,
        CapabilityDomain.EXTENSION_SIGNATURE,
    ),
)
def test_target_supported_reserved_domain_remains_provider_unknown(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
    domain: CapabilityDomain,
) -> None:
    package, _dependency = loaded_packages
    key = CapabilityKey(domain, subject="future", operation="lookup")
    target = _target_fact(key)
    check = _checked(package, _composition(target), key).checks[0]

    assert check.status is CapabilityRequirementStatus.UNKNOWN
    assert isinstance(check.target_result, Found)
    assert check.provider_result == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_both_target_and_provider_unknown_retain_both_axes(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = CapabilityKey(CapabilityDomain.CONVERSION, subject="Int", operation="to")
    check = _checked(package, _composition(), key).checks[0]

    assert check.status is CapabilityRequirementStatus.UNKNOWN
    assert check.target_result == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert check.provider_result == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


@pytest.mark.parametrize(
    ("key", "reason"),
    (
        (
            CapabilityKey(
                CapabilityDomain.BINARY_OPERATOR,
                subject="Int",
                operation="/",
                operands=("Int", "Int", "unknown"),
                context="expression",
            ),
            CapabilityReasonCode.NO_CURRENT_RESULT_RULE,
        ),
        (
            CapabilityKey(
                CapabilityDomain.SCALAR_FUNCTION,
                subject="Text",
                operation="matches",
                operands=("Text", "Bool", "unknown"),
                context="expression",
                dialect="mysql",
            ),
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
        ),
    ),
)
def test_bounded_provider_unknown_reasons_survive_checker_join(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
    key: CapabilityKey,
    reason: CapabilityReasonCode,
) -> None:
    package, _dependency = loaded_packages
    target = _target_fact(key)
    check = _checked(package, _composition(target), key).checks[0]

    assert check.status is CapabilityRequirementStatus.UNKNOWN
    assert isinstance(check.target_result, Found)
    assert check.provider_result == Unknown(reason)


def test_existing_count_shape_provider_conflict_remains_conflict(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    target = _target_fact(_COUNT_CONFLICT_KEY)
    check = _checked(package, _composition(target), _COUNT_CONFLICT_KEY).checks[0]
    expected = tuple(
        fact for fact in _PROVIDER_FACTS if fact.key == _COUNT_CONFLICT_KEY
    )

    assert check.status is CapabilityRequirementStatus.CONFLICT
    assert isinstance(check.provider_result, Conflict)
    assert check.provider_result.evidence == expected


def test_target_same_key_conflict_preserves_effective_order(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = _SUPPORTED_PROVIDER_FACT.key
    supported = _target_fact(key, reference="supported")
    unsupported = _target_fact(
        key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        reference="unsupported",
    )
    base = slice4._base(facts=(supported,))
    overlay = slice4._overlay("overlay", base.profile, facts=(unsupported,))
    composition = compose_capability_profiles(base, (overlay,))
    assert isinstance(composition, CapabilityProfileCompositionSuccess)
    check = _checked(package, composition, key).checks[0]

    assert check.status is CapabilityRequirementStatus.CONFLICT
    assert check.target_occurrences == composition.effective_occurrences
    assert isinstance(check.target_result, Conflict)
    assert check.target_result.evidence == (supported, unsupported)


def test_conflict_precedes_explicit_unsupported_on_other_axis(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    target = _target_fact(
        _COUNT_CONFLICT_KEY,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    check = _checked(package, _composition(target), _COUNT_CONFLICT_KEY).checks[0]

    assert check.status is CapabilityRequirementStatus.CONFLICT
    assert isinstance(check.target_result, Found)
    assert check.target_result.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    assert isinstance(check.provider_result, Conflict)


def test_disposition_does_not_change_supported_truth(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    disposition = CapabilityDisposition(
        CapabilityDispositionKind.DEFERRED,
        "Phase 60",
        "separate roadmap posture",
    )
    target = _target_fact(
        _SUPPORTED_PROVIDER_FACT.key,
        disposition=disposition,
    )
    check = _checked(package, _composition(target), target.key).checks[0]

    assert check.status is CapabilityRequirementStatus.SATISFIED
    assert isinstance(check.target_result, Found)
    assert check.target_result.fact.disposition is disposition


def test_requirement_and_matching_fact_orders_are_exact(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    first_key = _SUPPORTED_PROVIDER_FACT.key
    second_provider = next(
        fact
        for fact in _PROVIDER_FACTS
        if fact.key != first_key and fact.support is CapabilitySupport.SUPPORTED
    )
    first_target = _target_fact(first_key, reference="first")
    second_target = _target_fact(second_provider.key, reference="second")
    result = _checked(
        package,
        _composition(second_target, first_target),
        first_key,
        second_provider.key,
    )

    assert tuple(check.occurrence.key for check in result.checks) == (
        first_key,
        second_provider.key,
    )
    assert result.checks[0].target_occurrences[0].fact is first_target
    assert result.checks[1].target_occurrences[0].fact is second_target
    for check in result.checks:
        canonical = canonical_capability_provider_inputs(check.occurrence.key)
        assert check.provider_inputs.facts == canonical.facts


def test_unsatisfied_requirements_remain_checked_and_do_not_poison_neighbors(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    satisfied = _target_fact(_SUPPORTED_PROVIDER_FACT.key)
    missing = CapabilityKey(
        CapabilityDomain.CONVERSION,
        subject="missing",
        operation="convert",
    )
    result = _checked(
        package,
        _composition(satisfied),
        missing,
        satisfied.key,
    )

    assert tuple(check.status for check in result.checks) == (
        CapabilityRequirementStatus.UNKNOWN,
        CapabilityRequirementStatus.SATISFIED,
    )
    assert isinstance(result, PackageCapabilityRequirementsChecked)
    assert result.all_satisfied is False


def test_profile_target_does_not_normalize_requirement_key() -> None:
    key = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        subject="feature",
        operation="signature",
    )
    target = _target_fact(key)
    composition = _composition(target)

    assert composition.base.target.family == "PostgreSQL"
    assert composition.effective_occurrences[0].fact.key is key
    assert key.dialect is None


def test_result_carriers_are_private_frozen_slotted_and_antigraft(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    target = _target_fact(_SUPPORTED_PROVIDER_FACT.key)
    composition = _composition(target)
    availability = _availability(composition)
    checked = _checked(package, composition, target.key, availability=availability)
    carriers = (
        SelectedProfileAvailabilityBlocker,
        CapabilityRequirementCheck,
        PackageCapabilityRequirementsUndeclared,
        PackageCapabilityRequirementsBlocked,
        PackageCapabilityRequirementsChecked,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
    assert tuple(CapabilityRequirementStatus) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.UNSUPPORTED,
        CapabilityRequirementStatus.ABSENT,
        CapabilityRequirementStatus.UNKNOWN,
        CapabilityRequirementStatus.CONFLICT,
    )
    assert tuple(field.name for field in fields(CapabilityRequirementCheck)) == (
        "occurrence",
        "target_occurrences",
        "target_result",
        "provider_inputs",
        "provider_result",
        "status",
    )
    with pytest.raises(FrozenInstanceError):
        setattr(checked, "checks", ())
    foreign_occurrence = _requirements(target.key).occurrences[0]
    foreign_check = replace(checked.checks[0], occurrence=foreign_occurrence)
    with pytest.raises(ValueError, match="declaration order"):
        PackageCapabilityRequirementsChecked(
            package,
            checked.binding,
            composition,
            availability,
            (foreign_check,),
        )
    assert checking.__all__ == ()
    for name in (
        "CapabilityRequirementStatus",
        "CapabilityRequirementCheck",
        "PackageCapabilityRequirementsChecked",
        "check_package_capability_requirements",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)


def test_checker_has_no_public_runtime_or_database_semantics() -> None:
    source = inspect.getsource(checking).lower()
    for forbidden in (
        "target.family",
        "target.release",
        "database connection",
        "installed",
        "pathlib",
        "import os",
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "open(",
        "getcwd",
        "environ",
        "threshold",
        "ranking",
        "fallback",
        "wildcard",
    ):
        assert forbidden not in source
