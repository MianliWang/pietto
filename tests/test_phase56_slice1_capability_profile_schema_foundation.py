from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect
import unicodedata

import pytest

import pietto
import pietto.semantic as semantic_package
import pietto.semantic.capability_profiles as profiles
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
from pietto.semantic.capability_lookup import (
    Absent,
    Conflict,
    Found,
    Unknown,
    lookup_capability,
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


def _key(
    subject: str = "feature",
    *,
    dialect: str | None = None,
    extension: str | None = None,
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        subject=subject,
        operation="signature",
        operands=("Int",),
        context="expression",
        dialect=dialect,
        extension=extension,
    )


def _fact(
    key: CapabilityKey,
    *,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    reference: str = "one",
    disposition: CapabilityDisposition | None = None,
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
                "tests/test_phase56_slice1_capability_profile_schema_foundation.py",
                reference,
            ),
        ),
    )


def _profile_reference(
    name: str = "postgresql-base",
    release: str = "2026.08 vendor build",
) -> CapabilityProfileReference:
    return CapabilityProfileReference(
        CapabilityProfileIdentity("pietto.targets", name),
        release,
    )


def _database_target() -> CapabilityProfileTarget:
    return CapabilityProfileTarget(
        CapabilityProfileTargetKind.DATABASE,
        "PostgreSQL",
        "16.2 (Debian 16.2-1)",
    )


def test_profile_schema_identity_release_and_exact_text_are_distinct() -> None:
    composed = "Café"
    decomposed = unicodedata.normalize("NFD", composed)
    identity = CapabilityProfileIdentity(" Exact.Namespace ", composed)
    other = CapabilityProfileIdentity(" Exact.Namespace ", decomposed)
    reference = CapabilityProfileReference(identity, "release 01+vendor")

    assert identity.namespace == " Exact.Namespace "
    assert identity.name == composed
    assert identity != other
    assert reference.identity is identity
    assert reference.release == "release 01+vendor"
    assert CapabilityProfileSchemaVersion.PROFILE_V1.value == (
        "pietto.capability-profile.v1"
    )
    assert reference.release != CapabilityProfileSchemaVersion.PROFILE_V1.value
    with pytest.raises(ValueError, match="nonblank"):
        CapabilityProfileIdentity("   ", "name")
    with pytest.raises(ValueError, match="nonblank"):
        CapabilityProfileReference(identity, "\t")


def test_target_identity_separates_database_and_extension_releases() -> None:
    database = _database_target()
    extension = CapabilityProfileTarget(
        CapabilityProfileTargetKind.EXTENSION,
        "PostgreSQL",
        "16.2",
        "PostGIS",
        "3.4.1 vendor release",
    )

    assert database.release == "16.2 (Debian 16.2-1)"
    assert database.extension_identity is database.extension_release is None
    assert extension.family == database.family
    assert extension.release != extension.extension_release
    assert extension.extension_identity == "PostGIS"
    assert not hasattr(database, "installed")
    assert not hasattr(database, "connection")
    with pytest.raises(ValueError, match="forbid extension"):
        CapabilityProfileTarget(
            CapabilityProfileTargetKind.DATABASE,
            "PostgreSQL",
            "16",
            "PostGIS",
            "3",
        )
    with pytest.raises(ValueError, match="require exact extension"):
        CapabilityProfileTarget(
            CapabilityProfileTargetKind.EXTENSION,
            "PostgreSQL",
            "16",
            "PostGIS",
        )


def test_base_and_overlay_profiles_retain_exact_base_declaration_authority() -> None:
    base_reference = _profile_reference()
    base = StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        base_reference,
        _database_target(),
        CapabilityProfileKind.BASE,
        (),
        (),
    )
    overlay_reference = _profile_reference("postgis-overlay", "3.4.1")
    base_occurrence = CapabilityProfileBaseOccurrence(
        overlay_reference,
        0,
        base_reference,
    )
    overlay = StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        overlay_reference,
        CapabilityProfileTarget(
            CapabilityProfileTargetKind.EXTENSION,
            "PostgreSQL",
            "16.2",
            "PostGIS",
            "3.4.1",
        ),
        CapabilityProfileKind.OVERLAY,
        (base_occurrence,),
        (),
    )

    assert base.base_occurrences == ()
    assert overlay.base_occurrences == (base_occurrence,)
    assert overlay.base_occurrences[0].owner is overlay_reference
    assert overlay.base_occurrences[0].base is base_reference
    self_base = CapabilityProfileBaseOccurrence(overlay_reference, 0, overlay_reference)
    assert StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        overlay_reference,
        overlay.target,
        CapabilityProfileKind.OVERLAY,
        (self_base,),
        (),
    ).base_occurrences == (self_base,)
    with pytest.raises(ValueError, match="BASE.*forbid"):
        StaticCapabilityProfile(
            CapabilityProfileSchemaVersion.PROFILE_V1,
            base_reference,
            base.target,
            CapabilityProfileKind.BASE,
            (CapabilityProfileBaseOccurrence(base_reference, 0, overlay_reference),),
            (),
        )
    with pytest.raises(ValueError, match="require one exact base"):
        StaticCapabilityProfile(
            CapabilityProfileSchemaVersion.PROFILE_V1,
            overlay_reference,
            overlay.target,
            CapabilityProfileKind.OVERLAY,
            (),
            (),
        )
    duplicate_bases = (
        CapabilityProfileBaseOccurrence(overlay_reference, 0, base_reference),
        CapabilityProfileBaseOccurrence(overlay_reference, 1, base_reference),
    )
    with pytest.raises(ValueError, match="position 1 duplicates position 0"):
        StaticCapabilityProfile(
            CapabilityProfileSchemaVersion.PROFILE_V1,
            overlay_reference,
            overlay.target,
            CapabilityProfileKind.OVERLAY,
            duplicate_bases,
            (),
        )


def test_profile_occurrences_preserve_order_duplicates_and_key_local_conflicts() -> (
    None
):
    owner = _profile_reference()
    key = _key()
    supported = _fact(key, reference="supported")
    unsupported = _fact(
        key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        reference="unsupported",
    )
    occurrences = (
        CapabilityProfileFactOccurrence(owner, 0, supported),
        CapabilityProfileFactOccurrence(owner, 1, unsupported),
    )
    profile = StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        owner,
        _database_target(),
        CapabilityProfileKind.BASE,
        (),
        occurrences,
    )

    assert profile.capability_occurrences == occurrences
    assert tuple(item.fact.support for item in profile.capability_occurrences) == (
        CapabilitySupport.SUPPORTED,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    assert isinstance(
        lookup_capability(key, (supported, unsupported), domain_complete=True),
        Conflict,
    )
    duplicate = CapabilityProfileFactOccurrence(owner, 1, supported)
    with pytest.raises(ValueError, match="position 1 duplicates position 0"):
        StaticCapabilityProfile(
            CapabilityProfileSchemaVersion.PROFILE_V1,
            owner,
            _database_target(),
            CapabilityProfileKind.BASE,
            (),
            (occurrences[0], duplicate),
        )
    foreign_owner = _profile_reference()
    with pytest.raises(ValueError, match="exact owner authority"):
        StaticCapabilityProfile(
            CapabilityProfileSchemaVersion.PROFILE_V1,
            owner,
            _database_target(),
            CapabilityProfileKind.BASE,
            (),
            (CapabilityProfileFactOccurrence(foreign_owner, 0, supported),),
        )


def test_support_and_disposition_remain_orthogonal_profile_facts() -> None:
    owner = _profile_reference()
    deferred = CapabilityDisposition(
        CapabilityDispositionKind.DEFERRED,
        "Phase 60",
        "later native mapping",
    )
    fact = _fact(_key(), disposition=deferred)
    profile = StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        owner,
        _database_target(),
        CapabilityProfileKind.BASE,
        (),
        (CapabilityProfileFactOccurrence(owner, 0, fact),),
    )

    retained = profile.capability_occurrences[0].fact
    assert retained is fact
    assert retained.support is CapabilitySupport.SUPPORTED
    assert retained.disposition is deferred
    assert lookup_capability(fact.key, (fact,), domain_complete=True) == Found(fact)


def test_requirement_collection_is_ordered_exact_positive_conjunction_data() -> None:
    identity = CapabilityRequirementCollectionIdentity("consumer", "compiler")
    exact = _key("Feature")
    case_distinct = _key("feature")
    dialect_distinct = _key("Feature", dialect="postgresql")
    occurrences = (
        CapabilityRequirementOccurrence(identity, 0, exact),
        CapabilityRequirementOccurrence(identity, 1, case_distinct),
        CapabilityRequirementOccurrence(identity, 2, dialect_distinct),
    )
    requirements = CapabilityRequirementCollection(identity, occurrences)

    assert requirements.occurrences == occurrences
    assert tuple(item.key for item in requirements.occurrences) == (
        exact,
        case_distinct,
        dialect_distinct,
    )
    assert CapabilityRequirementCollection(identity, ()).occurrences == ()
    assert tuple(field.name for field in fields(CapabilityRequirementOccurrence)) == (
        "owner",
        "position",
        "key",
    )
    assert tuple(field.name for field in fields(CapabilityRequirementCollection)) == (
        "identity",
        "occurrences",
    )
    with pytest.raises(ValueError, match="position 1 duplicates position 0"):
        CapabilityRequirementCollection(
            identity,
            (
                CapabilityRequirementOccurrence(identity, 0, exact),
                CapabilityRequirementOccurrence(identity, 1, exact),
            ),
        )
    foreign = CapabilityRequirementCollectionIdentity("consumer", "compiler")
    with pytest.raises(ValueError, match="exact owner authority"):
        CapabilityRequirementCollection(
            identity,
            (CapabilityRequirementOccurrence(foreign, 0, exact),),
        )


def test_dense_occurrence_positions_and_exact_types_fail_closed() -> None:
    owner = _profile_reference()
    fact = _fact(_key())
    with pytest.raises(ValueError, match="dense and source ordered"):
        StaticCapabilityProfile(
            CapabilityProfileSchemaVersion.PROFILE_V1,
            owner,
            _database_target(),
            CapabilityProfileKind.BASE,
            (),
            (CapabilityProfileFactOccurrence(owner, 1, fact),),
        )
    requirement_owner = CapabilityRequirementCollectionIdentity("n", "r")
    with pytest.raises(ValueError, match="dense and source ordered"):
        CapabilityRequirementCollection(
            requirement_owner,
            (CapabilityRequirementOccurrence(requirement_owner, 2, _key()),),
        )
    with pytest.raises(ValueError, match="exact occurrences"):
        CapabilityRequirementCollection(
            requirement_owner,
            (object(),),  # pyright: ignore[reportArgumentType]
        )


def test_existing_lookup_outcomes_and_reserved_domains_remain_exact() -> None:
    key = _key()
    first = _fact(key, reference="first")
    second = _fact(key, reference="second")

    assert lookup_capability(key, (first, first), domain_complete=True) == Found(first)
    assert isinstance(
        lookup_capability(key, (first, second), domain_complete=True), Conflict
    )
    missing = _key("missing")
    assert lookup_capability(missing, (), domain_complete=True) == Absent(missing)
    assert lookup_capability(missing, (), domain_complete=False) == Unknown(
        CapabilityReasonCode.NOT_EVIDENCED
    )
    assert CapabilityDomain.EXTENSION_SIGNATURE.value == "extension_signature"
    assert CapabilityDomain.CONVERSION.value == "conversion"


def test_profile_schema_has_no_later_phase_behavior_or_ambient_state() -> None:
    source = inspect.getsource(profiles)
    for forbidden in (
        "lookup_capability",
        "domain_complete",
        "profile_complete",
        "effective_profile",
        "compose",
        "cycle",
        "satisfied",
        "wildcard",
        "fallback",
        "priority",
        "ranking",
        "database connection",
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
        assert forbidden not in source.lower()
    assert "backend" not in tuple(
        field.name for field in fields(CapabilityProfileTarget)
    )
    assert "release" not in tuple(field.name for field in fields(CapabilityKey))


def test_profile_schema_is_private_frozen_slotted_and_not_publicly_wired() -> None:
    assert profiles.__all__ == ()
    carriers = (
        CapabilityProfileIdentity,
        CapabilityProfileReference,
        CapabilityProfileTarget,
        CapabilityProfileBaseOccurrence,
        CapabilityProfileFactOccurrence,
        StaticCapabilityProfile,
        CapabilityRequirementCollectionIdentity,
        CapabilityRequirementOccurrence,
        CapabilityRequirementCollection,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
    identity = CapabilityProfileIdentity("n", "p")
    with pytest.raises(FrozenInstanceError):
        identity.name = "other"  # pyright: ignore[reportAttributeAccessIssue]
    for name in (
        "CapabilityProfileIdentity",
        "StaticCapabilityProfile",
        "CapabilityRequirementCollection",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(semantic_package, name)
