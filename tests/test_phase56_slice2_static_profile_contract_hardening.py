from __future__ import annotations

from typing import cast
import unicodedata

import pytest

from pietto.semantic.capability_facts import (
    CapabilityDisposition,
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidence,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilitySupport,
)
from pietto.semantic.capability_profiles import (
    CapabilityProfileBaseOccurrence,
    CapabilityProfileFactOccurrence,
    CapabilityProfileIdentity,
    CapabilityProfileKind,
    CapabilityProfileReference,
    CapabilityProfileSchemaVersion,
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
    StaticCapabilityProfile,
)


def _reference(
    name: str = "postgresql-base",
    release: str = "profile release",
) -> CapabilityProfileReference:
    return CapabilityProfileReference(
        CapabilityProfileIdentity("pietto.targets", name),
        release,
    )


def _target(kind: CapabilityProfileTargetKind) -> CapabilityProfileTarget:
    if kind is CapabilityProfileTargetKind.DATABASE:
        return CapabilityProfileTarget(kind, "PostgreSQL", "database release")
    return CapabilityProfileTarget(
        kind,
        "PostgreSQL",
        "database release",
        "PostGIS",
        "extension release",
    )


def _fact(key: CapabilityKey) -> CapabilityFact:
    return CapabilityFact(
        key,
        CapabilitySupport.SUPPORTED,
        CapabilityDisposition(CapabilityDispositionKind.NONE),
        (
            CapabilityEvidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase56_slice2_static_profile_contract_hardening.py",
                "slice 2 invariant",
            ),
        ),
    )


def _profile(
    kind: CapabilityProfileKind,
    target_kind: CapabilityProfileTargetKind,
    *,
    owner: CapabilityProfileReference | None = None,
    base: CapabilityProfileReference | None = None,
    facts: tuple[CapabilityFact, ...] = (),
) -> StaticCapabilityProfile:
    profile = _reference("profile") if owner is None else owner
    bases = (
        ()
        if kind is CapabilityProfileKind.BASE
        else (
            CapabilityProfileBaseOccurrence(
                profile,
                0,
                _reference("declared-base") if base is None else base,
            ),
        )
    )
    return StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        profile,
        _target(target_kind),
        kind,
        bases,
        tuple(
            CapabilityProfileFactOccurrence(profile, position, fact)
            for position, fact in enumerate(facts)
        ),
    )


def test_base_database_and_overlay_extension_pairs_are_valid() -> None:
    base = _profile(
        CapabilityProfileKind.BASE,
        CapabilityProfileTargetKind.DATABASE,
    )
    overlay = _profile(
        CapabilityProfileKind.OVERLAY,
        CapabilityProfileTargetKind.EXTENSION,
    )

    assert base.target.kind is CapabilityProfileTargetKind.DATABASE
    assert overlay.target.kind is CapabilityProfileTargetKind.EXTENSION
    assert base.capability_occurrences == overlay.capability_occurrences == ()


@pytest.mark.parametrize(
    ("kind", "target_kind", "message"),
    (
        (
            CapabilityProfileKind.BASE,
            CapabilityProfileTargetKind.EXTENSION,
            "BASE.*DATABASE",
        ),
        (
            CapabilityProfileKind.OVERLAY,
            CapabilityProfileTargetKind.DATABASE,
            "OVERLAY.*EXTENSION",
        ),
    ),
)
def test_other_profile_target_pairs_fail_closed(
    kind: CapabilityProfileKind,
    target_kind: CapabilityProfileTargetKind,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _profile(kind, target_kind)


def test_release_and_identity_dimensions_remain_exact_opaque_text() -> None:
    composed = "Café"
    identity = CapabilityProfileIdentity(" Namespace ", composed)
    reference = CapabilityProfileReference(identity, " profile RC + vendor ")
    other_release = CapabilityProfileReference(identity, "profile RC + vendor")
    other_name = CapabilityProfileReference(
        CapabilityProfileIdentity(
            " Namespace ",
            unicodedata.normalize("NFD", composed),
        ),
        reference.release,
    )
    target = CapabilityProfileTarget(
        CapabilityProfileTargetKind.EXTENSION,
        "PostgreSQL",
        "database RC",
        "PostGIS",
        "extension RC",
    )

    assert reference.release == " profile RC + vendor "
    assert reference != other_release
    assert reference != other_name
    assert reference.identity != CapabilityProfileIdentity(" namespace ", composed)
    assert target.release != target.extension_release != reference.release
    assert target != CapabilityProfileTarget(
        CapabilityProfileTargetKind.EXTENSION,
        target.family,
        "database rc",
        target.extension_identity,
        target.extension_release,
    )


def test_self_and_unresolved_bases_remain_declaration_data() -> None:
    owner = _reference("postgis-overlay", "3.4")
    self_base = _profile(
        CapabilityProfileKind.OVERLAY,
        CapabilityProfileTargetKind.EXTENSION,
        owner=owner,
        base=owner,
    )
    unresolved = _reference("not-loaded", "arbitrary release")
    unresolved_base = _profile(
        CapabilityProfileKind.OVERLAY,
        CapabilityProfileTargetKind.EXTENSION,
        owner=owner,
        base=unresolved,
    )

    assert self_base.base_occurrences[0].base is owner
    assert unresolved_base.base_occurrences[0].base is unresolved


def test_iterables_are_frozen_and_bool_positions_fail_closed() -> None:
    owner = _reference("generated")
    key = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        subject="feature",
        operation="signature",
    )
    fact_occurrence = CapabilityProfileFactOccurrence(owner, 0, _fact(key))
    profile = StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        owner,
        _target(CapabilityProfileTargetKind.DATABASE),
        CapabilityProfileKind.BASE,
        cast(tuple[CapabilityProfileBaseOccurrence, ...], (item for item in ())),
        cast(
            tuple[CapabilityProfileFactOccurrence, ...],
            (item for item in (fact_occurrence,)),
        ),
    )
    requirement_owner = CapabilityRequirementCollectionIdentity("consumer", "one")
    requirement = CapabilityRequirementOccurrence(requirement_owner, 0, key)
    requirements = CapabilityRequirementCollection(
        requirement_owner,
        cast(
            tuple[CapabilityRequirementOccurrence, ...],
            (item for item in (requirement,)),
        ),
    )

    assert profile.capability_occurrences == (fact_occurrence,)
    assert requirements.occurrences == (requirement,)
    with pytest.raises(ValueError, match="non-negative position"):
        CapabilityProfileFactOccurrence(owner, True, fact_occurrence.fact)
    with pytest.raises(ValueError, match="non-negative position"):
        CapabilityRequirementOccurrence(requirement_owner, False, key)


def test_sparse_and_foreign_owner_occurrences_fail_closed() -> None:
    owner = _reference()
    foreign_owner = _reference()
    fact = _fact(
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="feature",
            operation="signature",
        )
    )
    assert owner == foreign_owner and owner is not foreign_owner
    with pytest.raises(ValueError, match="dense and source ordered"):
        StaticCapabilityProfile(
            CapabilityProfileSchemaVersion.PROFILE_V1,
            owner,
            _target(CapabilityProfileTargetKind.DATABASE),
            CapabilityProfileKind.BASE,
            (),
            (CapabilityProfileFactOccurrence(owner, 1, fact),),
        )
    with pytest.raises(ValueError, match="exact owner authority"):
        StaticCapabilityProfile(
            CapabilityProfileSchemaVersion.PROFILE_V1,
            owner,
            _target(CapabilityProfileTargetKind.DATABASE),
            CapabilityProfileKind.BASE,
            (),
            (CapabilityProfileFactOccurrence(foreign_owner, 0, fact),),
        )


def test_target_scope_does_not_normalize_or_restrict_capability_key_scope() -> None:
    dialect_key = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        subject="database feature",
        operation="signature",
        dialect="postgresql",
    )
    base = _profile(
        CapabilityProfileKind.BASE,
        CapabilityProfileTargetKind.DATABASE,
        facts=(_fact(dialect_key),),
    )
    unscoped_key = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        subject="extension feature",
        operation="signature",
    )
    overlay = _profile(
        CapabilityProfileKind.OVERLAY,
        CapabilityProfileTargetKind.EXTENSION,
        facts=(_fact(unscoped_key),),
    )

    assert base.target.family == "PostgreSQL"
    assert base.capability_occurrences[0].fact.key.dialect == "postgresql"
    assert overlay.capability_occurrences[0].fact.key.extension is None
