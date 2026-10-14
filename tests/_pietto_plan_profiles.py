"""Shared declared target-profile fixtures."""

from pietto.semantic import capability_aggregates as aggregates
from pietto.semantic import capability_inventory as inventory
from pietto.semantic import capability_signatures as signatures
from pietto.semantic import capability_windows as windows
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


def _database(family="postgresql", release="18"):
    return CapabilityProfileTarget(
        CapabilityProfileTargetKind.DATABASE, family, release
    )


def _profile(
    database,
    facts=(),
    *,
    name="declared",
    base=None,
    extension="test.extension",
    extension_release="1",
):
    """Explicit test declarations about real compiler facts, not observed DB support."""
    reference = CapabilityProfileReference(
        CapabilityProfileIdentity("slice13", name), "profile-release-7"
    )
    profile_target = (
        database
        if base is None
        else CapabilityProfileTarget(
            CapabilityProfileTargetKind.EXTENSION,
            database.family,
            database.release,
            extension,
            extension_release,
        )
    )
    return StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        reference,
        profile_target,
        CapabilityProfileKind.BASE if base is None else CapabilityProfileKind.OVERLAY,
        ()
        if base is None
        else (CapabilityProfileBaseOccurrence(reference, 0, base.profile),),
        tuple(
            CapabilityProfileFactOccurrence(reference, index, fact)
            for index, fact in enumerate(facts)
        ),
    )


REAL_FACTS = (
    *inventory._LOGICAL_TYPE_FACTS,
    *inventory._LITERAL_FACTS,
    *signatures._CAPABILITY_SIGNATURE_FACTS,
    *aggregates._AGGREGATE_SIGNATURE_FACTS,
    *windows._WINDOW_SIGNATURE_FACTS,
)
