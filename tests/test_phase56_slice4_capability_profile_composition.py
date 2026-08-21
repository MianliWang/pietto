from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect
from typing import Any, cast

import pytest

import pietto
import pietto.semantic as semantic_package
import pietto.semantic.capability_composition as composition
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionBlocked,
    CapabilityProfileCompositionBlocker,
    CapabilityProfileCompositionBlockerKind,
    CapabilityProfileCompositionSuccess,
    EffectiveCapabilityProfileFactOccurrence,
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
from pietto.semantic.capability_lookup import Conflict, Found, lookup_capability
from pietto.semantic.capability_providers import canonical_capability_provider_inputs
from pietto.semantic.capability_profiles import (
    CapabilityProfileBaseOccurrence,
    CapabilityProfileFactOccurrence,
    CapabilityProfileIdentity,
    CapabilityProfileKind,
    CapabilityProfileReference,
    CapabilityProfileSchemaVersion,
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
    StaticCapabilityProfile,
)


def _reference(
    name: str,
    release: str = "profile release",
) -> CapabilityProfileReference:
    return CapabilityProfileReference(
        CapabilityProfileIdentity("pietto.targets", name),
        release,
    )


def _fact(
    subject: str,
    *,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    reference: str | None = None,
) -> CapabilityFact:
    return CapabilityFact(
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject=subject,
            operation="signature",
        ),
        support,
        CapabilityDisposition(CapabilityDispositionKind.NONE),
        (
            CapabilityEvidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase56_slice4_capability_profile_composition.py",
                subject if reference is None else reference,
            ),
        ),
    )


def _base(
    name: str = "base",
    *,
    profile_release: str = "profile release",
    family: str = "PostgreSQL",
    target_release: str = "16",
    facts: tuple[CapabilityFact, ...] = (),
) -> StaticCapabilityProfile:
    owner = _reference(name, profile_release)
    return StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        owner,
        CapabilityProfileTarget(
            CapabilityProfileTargetKind.DATABASE,
            family,
            target_release,
        ),
        CapabilityProfileKind.BASE,
        (),
        tuple(
            CapabilityProfileFactOccurrence(owner, position, fact)
            for position, fact in enumerate(facts)
        ),
    )


def _overlay(
    name: str,
    declared_base: CapabilityProfileReference,
    *,
    profile_release: str = "profile release",
    family: str = "PostgreSQL",
    target_release: str = "16",
    extension: str | None = None,
    facts: tuple[CapabilityFact, ...] = (),
) -> StaticCapabilityProfile:
    owner = _reference(name, profile_release)
    return StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        owner,
        CapabilityProfileTarget(
            CapabilityProfileTargetKind.EXTENSION,
            family,
            target_release,
            name if extension is None else extension,
            "extension release",
        ),
        CapabilityProfileKind.OVERLAY,
        (CapabilityProfileBaseOccurrence(owner, 0, declared_base),),
        tuple(
            CapabilityProfileFactOccurrence(owner, position, fact)
            for position, fact in enumerate(facts)
        ),
    )


def test_base_alone_composes_with_exact_authority() -> None:
    base = _base(facts=(_fact("base fact"),))
    result = compose_capability_profiles(base, ())

    assert isinstance(result, CapabilityProfileCompositionSuccess)
    assert result.base is base
    assert result.overlays == ()
    assert result.dependency_order == (base,)
    assert result.effective_occurrences[0].profile is base
    assert result.effective_occurrences[0].occurrence is base.capability_occurrences[0]


def _success(
    result: CapabilityProfileCompositionSuccess | CapabilityProfileCompositionBlocked,
) -> CapabilityProfileCompositionSuccess:
    assert isinstance(result, CapabilityProfileCompositionSuccess)
    return result


def _blocked(
    result: CapabilityProfileCompositionSuccess | CapabilityProfileCompositionBlocked,
) -> CapabilityProfileCompositionBlocked:
    assert isinstance(result, CapabilityProfileCompositionBlocked)
    return result


def test_direct_and_sibling_overlays_preserve_supplied_and_effective_order() -> None:
    base = _base(facts=(_fact("base"),))
    second = _overlay("second", base.profile, facts=(_fact("second"),))
    first = _overlay("first", base.profile, facts=(_fact("first"),))
    result = _success(compose_capability_profiles(base, (second, first)))

    assert result.base is base
    assert result.overlays == (second, first)
    assert result.dependency_order == (base, second, first)
    assert result.facts == (
        base.capability_occurrences[0].fact,
        second.capability_occurrences[0].fact,
        first.capability_occurrences[0].fact,
    )


def test_overlay_chain_derives_parent_first_order_separate_from_input_order() -> None:
    base = _base()
    parent = _overlay("parent", base.profile)
    child = _overlay("child", parent.profile)
    result = _success(compose_capability_profiles(base, (child, parent)))

    assert result.overlays == (child, parent)
    assert result.dependency_order == (base, parent, child)


@pytest.mark.parametrize(
    "missing",
    (
        _reference("base", "other release"),
        _reference("Base", "profile release"),
        CapabilityProfileReference(
            CapabilityProfileIdentity("Pietto.Targets", "base"),
            "profile release",
        ),
    ),
)
def test_unresolved_base_uses_exact_reference_without_fallback(
    missing: CapabilityProfileReference,
) -> None:
    base = _base()
    overlay = _overlay("overlay", missing)
    result = _blocked(compose_capability_profiles(base, (overlay,)))

    assert tuple(blocker.kind for blocker in result.blockers) == (
        CapabilityProfileCompositionBlockerKind.UNRESOLVED_BASE,
    )
    blocker = result.blockers[0]
    assert blocker.profiles == (overlay,)
    assert blocker.base_occurrences == overlay.base_occurrences
    assert blocker.reference_chain == (overlay.profile, missing)


def test_direct_self_cycle_retains_exact_closing_edge() -> None:
    base = _base()
    reference = _reference("self")
    overlay = _overlay("self", reference)
    result = _blocked(compose_capability_profiles(base, (overlay,)))

    blocker = next(
        blocker
        for blocker in result.blockers
        if blocker.kind is CapabilityProfileCompositionBlockerKind.CYCLE
    )
    assert blocker.profiles == (overlay,)
    assert blocker.base_occurrences == overlay.base_occurrences
    assert blocker.reference_chain == (reference, reference)


def test_two_overlay_cycle_preserves_supplied_cycle_start_and_closure() -> None:
    base = _base()
    first_reference = _reference("first")
    second_reference = _reference("second")
    first = _overlay("first", second_reference)
    second = _overlay("second", first_reference)
    result = _blocked(compose_capability_profiles(base, (first, second)))

    blocker = next(
        blocker
        for blocker in result.blockers
        if blocker.kind is CapabilityProfileCompositionBlockerKind.CYCLE
    )
    assert blocker.profiles == (first, second)
    assert blocker.base_occurrences == (
        first.base_occurrences[0],
        second.base_occurrences[0],
    )
    assert blocker.reference_chain == (
        first_reference,
        second_reference,
        first_reference,
    )


def test_longer_cycle_is_iterative_and_deterministic() -> None:
    base = _base()
    a_reference = _reference("a")
    b_reference = _reference("b")
    c_reference = _reference("c")
    a = _overlay("a", b_reference)
    b = _overlay("b", c_reference)
    c = _overlay("c", a_reference)

    first = _blocked(compose_capability_profiles(base, (b, c, a)))
    second = _blocked(compose_capability_profiles(base, (b, c, a)))
    cycle = next(
        blocker
        for blocker in first.blockers
        if blocker.kind is CapabilityProfileCompositionBlockerKind.CYCLE
    )
    assert first == second
    assert cycle.reference_chain == (b_reference, c_reference, a_reference, b_reference)


def test_duplicate_profile_reference_and_ambiguous_edge_report_no_winner() -> None:
    base = _base()
    first = _overlay("duplicate", base.profile, extension="first")
    second = _overlay("duplicate", base.profile, extension="second")
    child = _overlay("child", first.profile)
    result = _blocked(compose_capability_profiles(base, (first, second, child)))

    assert tuple(blocker.kind for blocker in result.blockers) == (
        CapabilityProfileCompositionBlockerKind.DUPLICATE_PROFILE_REFERENCE,
        CapabilityProfileCompositionBlockerKind.AMBIGUOUS_BASE_REFERENCE,
    )
    duplicate, ambiguous = result.blockers
    assert duplicate.profiles == (first, second)
    assert duplicate.reference_chain == (first.profile,)
    assert ambiguous.profiles == (child, first, second)
    assert ambiguous.base_occurrences == child.base_occurrences


def test_repeated_exact_profile_object_is_duplicate_selection() -> None:
    base = _base()
    overlay = _overlay("overlay", base.profile)
    result = _blocked(compose_capability_profiles(base, (overlay, overlay)))

    duplicate = result.blockers[0]
    assert duplicate.kind is (
        CapabilityProfileCompositionBlockerKind.DUPLICATE_PROFILE_REFERENCE
    )
    assert duplicate.profiles == (overlay, overlay)


def test_same_identity_with_different_releases_remains_distinct_and_exact() -> None:
    base = _base()
    version_one = _overlay("overlay", base.profile, profile_release="1")
    version_two = _overlay("overlay", base.profile, profile_release="2")
    child = _overlay("child", version_two.profile)
    result = _success(
        compose_capability_profiles(base, (child, version_one, version_two))
    )

    assert version_one.profile.identity == version_two.profile.identity
    assert version_one.profile != version_two.profile
    assert result.dependency_order == (base, version_one, version_two, child)


@pytest.mark.parametrize(
    ("family", "release", "kind"),
    (
        (
            "postgresql",
            "16",
            CapabilityProfileCompositionBlockerKind.TARGET_FAMILY_MISMATCH,
        ),
        (
            "PostgreSQL",
            "16 ",
            CapabilityProfileCompositionBlockerKind.TARGET_RELEASE_MISMATCH,
        ),
    ),
)
def test_overlay_host_target_requires_exact_family_and_release(
    family: str,
    release: str,
    kind: CapabilityProfileCompositionBlockerKind,
) -> None:
    base = _base()
    overlay = _overlay(
        "overlay",
        base.profile,
        family=family,
        target_release=release,
    )
    result = _blocked(compose_capability_profiles(base, (overlay,)))

    assert tuple(blocker.kind for blocker in result.blockers) == (kind,)
    assert result.blockers[0].profiles == (base, overlay)


def test_schema_version_mismatch_is_a_structural_blocker() -> None:
    base = _base()
    overlay = copy.copy(_overlay("overlay", base.profile))
    object.__setattr__(
        overlay,
        "schema_version",
        cast(CapabilityProfileSchemaVersion, object()),
    )
    result = _blocked(compose_capability_profiles(base, (overlay,)))

    assert tuple(blocker.kind for blocker in result.blockers) == (
        CapabilityProfileCompositionBlockerKind.SCHEMA_VERSION_MISMATCH,
    )
    assert result.blockers[0].profiles == (base, overlay)


def test_wrong_profile_kinds_are_structured_selection_blockers() -> None:
    declared_base = _reference("missing")
    wrong_base = _overlay("wrong-base", declared_base)
    invalid_base = _blocked(compose_capability_profiles(wrong_base, ()))
    assert tuple(blocker.kind for blocker in invalid_base.blockers) == (
        CapabilityProfileCompositionBlockerKind.INVALID_BASE_KIND,
    )

    base = _base()
    wrong_overlay = _base("wrong-overlay")
    invalid_overlay = _blocked(compose_capability_profiles(base, (wrong_overlay,)))
    assert tuple(blocker.kind for blocker in invalid_overlay.blockers) == (
        CapabilityProfileCompositionBlockerKind.INVALID_OVERLAY_KIND,
    )


def test_chain_to_another_selected_base_is_not_rooted_in_supplied_base() -> None:
    base = _base()
    other_base = _base("other-base")
    child = _overlay("child", other_base.profile)
    result = _blocked(compose_capability_profiles(base, (other_base, child)))

    assert tuple(blocker.kind for blocker in result.blockers) == (
        CapabilityProfileCompositionBlockerKind.INVALID_OVERLAY_KIND,
        CapabilityProfileCompositionBlockerKind.CHAIN_NOT_ROOTED,
    )
    unrooted = result.blockers[1]
    assert unrooted.profiles == (child, other_base)
    assert unrooted.reference_chain == (child.profile, other_base.profile)
    assert unrooted.base_occurrences == child.base_occurrences


@pytest.mark.parametrize("location", ("base-overlay", "overlay-overlay"))
def test_exact_duplicate_facts_across_profiles_retain_both_sources(
    location: str,
) -> None:
    duplicate = _fact("duplicate")
    if location == "base-overlay":
        base = _base(facts=(duplicate,))
        first = base
        second = _overlay("overlay", base.profile, facts=(duplicate,))
        overlays = (second,)
    else:
        base = _base()
        first = _overlay("first", base.profile, facts=(duplicate,))
        second = _overlay("second", base.profile, facts=(duplicate,))
        overlays = (first, second)
    result = _blocked(compose_capability_profiles(base, overlays))

    blocker = next(
        blocker
        for blocker in result.blockers
        if blocker.kind
        is CapabilityProfileCompositionBlockerKind.EXACT_DUPLICATE_CAPABILITY_FACT
    )
    assert blocker.profiles == (first, second)
    assert blocker.fact_occurrences == (
        first.capability_occurrences[0],
        second.capability_occurrences[0],
    )
    assert blocker.reference_chain == (first.profile, second.profile)


def test_distinct_same_key_facts_remain_successful_ordered_local_conflict() -> None:
    supported = _fact("shared", reference="supported")
    unsupported = _fact(
        "shared",
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        reference="unsupported",
    )
    unrelated = _fact("unrelated")
    base = _base(facts=(supported, unrelated))
    overlay = _overlay("overlay", base.profile, facts=(unsupported,))
    result = _success(compose_capability_profiles(base, (overlay,)))

    assert result.facts == (supported, unrelated, unsupported)
    assert lookup_capability(
        supported.key,
        result.facts,
        domain_complete=True,
    ) == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (supported, unsupported),
    )
    assert lookup_capability(
        unrelated.key,
        result.facts,
        domain_complete=True,
    ) == Found(unrelated)


def test_flattening_preserves_local_order_and_exact_profile_occurrence_authority() -> (
    None
):
    base_facts = (_fact("base-1"), _fact("base-2"))
    parent_facts = (_fact("parent-1"), _fact("parent-2"))
    child_facts = (_fact("child-1"), _fact("child-2"))
    base = _base(facts=base_facts)
    parent = _overlay("parent", base.profile, facts=parent_facts)
    child = _overlay("child", parent.profile, facts=child_facts)
    result = _success(compose_capability_profiles(base, (child, parent)))

    assert result.facts == (*base_facts, *parent_facts, *child_facts)
    expected = tuple(
        (profile, occurrence)
        for profile in (base, parent, child)
        for occurrence in profile.capability_occurrences
    )
    assert len(result.effective_occurrences) == len(expected)
    for item, (profile, occurrence) in zip(
        result.effective_occurrences,
        expected,
        strict=True,
    ):
        assert item.profile is profile
        assert item.occurrence is occurrence
        assert item.fact is occurrence.fact


def test_blocked_result_retains_complete_deterministic_independent_evidence() -> None:
    duplicate = _fact("duplicate")
    base = _base(facts=(duplicate,))
    overlay = _overlay(
        "overlay",
        _reference("missing"),
        family="postgresql",
        target_release="16 ",
        facts=(duplicate,),
    )
    result = _blocked(compose_capability_profiles(base, (overlay,)))

    assert tuple(blocker.kind for blocker in result.blockers) == (
        CapabilityProfileCompositionBlockerKind.TARGET_FAMILY_MISMATCH,
        CapabilityProfileCompositionBlockerKind.TARGET_RELEASE_MISMATCH,
        CapabilityProfileCompositionBlockerKind.UNRESOLVED_BASE,
        CapabilityProfileCompositionBlockerKind.EXACT_DUPLICATE_CAPABILITY_FACT,
    )
    assert result.base is base
    assert result.overlays == (overlay,)
    assert not hasattr(result, "dependency_order")
    assert not hasattr(result, "effective_occurrences")


def test_overlay_local_blockers_follow_supplied_overlay_authority_order() -> None:
    base = _base()
    unresolved = _overlay("unresolved", _reference("missing"))
    mismatched = _overlay("mismatched", base.profile, family="postgresql")
    result = _blocked(compose_capability_profiles(base, (unresolved, mismatched)))

    assert tuple(blocker.kind for blocker in result.blockers) == (
        CapabilityProfileCompositionBlockerKind.UNRESOLVED_BASE,
        CapabilityProfileCompositionBlockerKind.TARGET_FAMILY_MISMATCH,
    )
    assert result.blockers[0].profiles == (unresolved,)
    assert result.blockers[1].profiles == (base, mismatched)


def test_selection_blockers_follow_first_selected_profile_authority() -> None:
    base = _base()
    wrong_kind = _base("wrong-kind")
    first = _overlay("duplicate", base.profile, extension="first")
    second = _overlay("duplicate", base.profile, extension="second")
    result = _blocked(compose_capability_profiles(base, (wrong_kind, first, second)))

    assert tuple(blocker.kind for blocker in result.blockers) == (
        CapabilityProfileCompositionBlockerKind.INVALID_OVERLAY_KIND,
        CapabilityProfileCompositionBlockerKind.DUPLICATE_PROFILE_REFERENCE,
    )
    assert result.blockers[0].profiles == (wrong_kind,)
    assert result.blockers[1].profiles == (first, second)


def test_repeated_construction_is_value_deterministic() -> None:
    base = _base(facts=(_fact("base"),))
    first = _overlay("first", base.profile, facts=(_fact("first"),))
    second = _overlay("second", base.profile, facts=(_fact("second"),))

    results = tuple(
        compose_capability_profiles(base, (second, first)) for _attempt in range(3)
    )
    assert results[0] == results[1] == results[2]


def test_long_reverse_chain_uses_nonrecursive_dependency_ordering() -> None:
    base = _base()
    profiles: list[StaticCapabilityProfile] = []
    parent = base.profile
    for position in range(1100):
        overlay = _overlay(f"overlay-{position}", parent)
        profiles.append(overlay)
        parent = overlay.profile

    result = _success(compose_capability_profiles(base, tuple(reversed(profiles))))
    assert result.overlays == tuple(reversed(profiles))
    assert result.dependency_order == (base, *profiles)


def test_ordered_iterables_freeze_but_unordered_or_malformed_inputs_fail_closed() -> (
    None
):
    base = _base()
    overlay = _overlay("overlay", base.profile)
    generated = _success(
        compose_capability_profiles(base, (item for item in (overlay,)))
    )
    assert generated.overlays == (overlay,)

    with pytest.raises(ValueError, match="ordered overlay iterable"):
        compose_capability_profiles(base, {overlay})
    with pytest.raises(ValueError, match="exact base profile"):
        compose_capability_profiles(cast(Any, object()), ())
    with pytest.raises(ValueError, match="exact overlay profiles"):
        compose_capability_profiles(
            base,
            cast(tuple[StaticCapabilityProfile, ...], (object(),)),
        )


def test_result_carriers_are_private_frozen_slotted_and_reject_grafted_facts() -> None:
    base = _base(facts=(_fact("base"),))
    result = _success(compose_capability_profiles(base, ()))
    carriers = (
        CapabilityProfileCompositionBlocker,
        EffectiveCapabilityProfileFactOccurrence,
        CapabilityProfileCompositionSuccess,
        CapabilityProfileCompositionBlocked,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
    assert tuple(
        field.name for field in fields(CapabilityProfileCompositionSuccess)
    ) == (
        "base",
        "overlays",
        "dependency_order",
        "effective_occurrences",
    )
    with pytest.raises(FrozenInstanceError):
        result.overlays = ()  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(ValueError, match="canonical fact authority"):
        CapabilityProfileCompositionSuccess(base, (), (base,), ())
    overlay = _overlay("overlay", base.profile)
    with pytest.raises(ValueError, match="selected authority"):
        CapabilityProfileCompositionSuccess(
            base,
            (overlay, overlay),
            (base, overlay, overlay),
            result.effective_occurrences,
        )

    other = _base("other", facts=(_fact("other"),))
    with pytest.raises(ValueError, match="owner authority"):
        EffectiveCapabilityProfileFactOccurrence(
            other,
            base.capability_occurrences[0],
        )
    assert composition.__all__ == ()
    for name in (
        "CapabilityProfileCompositionSuccess",
        "CapabilityProfileCompositionBlocked",
        "compose_capability_profiles",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(semantic_package, name)


def test_blocker_carrier_rejects_malformed_evidence() -> None:
    base = _base()
    with pytest.raises(ValueError, match="exact kind"):
        CapabilityProfileCompositionBlocker(
            cast(CapabilityProfileCompositionBlockerKind, "cycle"),
            (base,),
            reference_chain=(base.profile,),
        )
    with pytest.raises(ValueError, match="exact profile tuple"):
        CapabilityProfileCompositionBlocker(
            CapabilityProfileCompositionBlockerKind.CYCLE,
            cast(tuple[StaticCapabilityProfile, ...], []),
            reference_chain=(base.profile,),
        )
    with pytest.raises(ValueError, match="reference chain"):
        CapabilityProfileCompositionBlocker(
            CapabilityProfileCompositionBlockerKind.CYCLE,
            (base,),
        )


def test_composition_does_not_consume_provider_completeness_or_requirements() -> None:
    key = CapabilityKey(
        CapabilityDomain.CONVERSION,
        subject="Int",
        operation="to",
    )
    provider_before = canonical_capability_provider_inputs(key)
    base = _base()
    result = _success(compose_capability_profiles(base, ()))
    provider_after = canonical_capability_provider_inputs(key)

    assert provider_before == provider_after
    assert result.effective_occurrences == ()
    assert not hasattr(result, "domain_complete")
    source = inspect.getsource(composition).lower()
    for forbidden in (
        "capability_providers",
        "canonical_capability_provider_inputs",
        "lookup_capability",
        "capabilityrequirement",
        "domain_complete",
        "profile_complete",
        "availability",
        "pathlib",
        "import os",
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "open(",
        "getcwd",
        "environ",
    ):
        assert forbidden not in source
