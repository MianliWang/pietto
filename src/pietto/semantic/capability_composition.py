"""Private deterministic static capability-profile composition."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from enum import StrEnum

from pietto.semantic.capability_facts import CapabilityFact
from pietto.semantic.capability_profiles import (
    CapabilityProfileBaseOccurrence,
    CapabilityProfileFactOccurrence,
    CapabilityProfileKind,
    CapabilityProfileReference,
    StaticCapabilityProfile,
)

__all__: tuple[str, ...] = ()


class CapabilityProfileCompositionBlockerKind(StrEnum):
    INVALID_BASE_KIND = "invalid_base_kind"
    INVALID_OVERLAY_KIND = "invalid_overlay_kind"
    DUPLICATE_PROFILE_REFERENCE = "duplicate_profile_reference"
    UNRESOLVED_BASE = "unresolved_base"
    AMBIGUOUS_BASE_REFERENCE = "ambiguous_base_reference"
    CYCLE = "cycle"
    CHAIN_NOT_ROOTED = "chain_not_rooted"
    TARGET_FAMILY_MISMATCH = "target_family_mismatch"
    TARGET_RELEASE_MISMATCH = "target_release_mismatch"
    SCHEMA_VERSION_MISMATCH = "schema_version_mismatch"
    EXACT_DUPLICATE_CAPABILITY_FACT = "exact_duplicate_capability_fact"


@dataclass(frozen=True, slots=True)
class CapabilityProfileCompositionBlocker:
    kind: CapabilityProfileCompositionBlockerKind
    profiles: tuple[StaticCapabilityProfile, ...]
    base_occurrences: tuple[CapabilityProfileBaseOccurrence, ...] = ()
    fact_occurrences: tuple[CapabilityProfileFactOccurrence, ...] = ()
    reference_chain: tuple[CapabilityProfileReference, ...] = ()

    def __post_init__(self) -> None:
        if type(self.kind) is not CapabilityProfileCompositionBlockerKind:
            raise ValueError("composition blocker requires an exact kind")
        if type(self.profiles) is not tuple or not self.profiles:
            raise ValueError("composition blocker requires an exact profile tuple")
        if any(
            type(profile) is not StaticCapabilityProfile for profile in self.profiles
        ):
            raise ValueError("composition blocker requires exact profiles")
        if type(self.base_occurrences) is not tuple or any(
            type(occurrence) is not CapabilityProfileBaseOccurrence
            for occurrence in self.base_occurrences
        ):
            raise ValueError("composition blocker requires exact base occurrences")
        if type(self.fact_occurrences) is not tuple or any(
            type(occurrence) is not CapabilityProfileFactOccurrence
            for occurrence in self.fact_occurrences
        ):
            raise ValueError("composition blocker requires exact fact occurrences")
        if type(self.reference_chain) is not tuple or not self.reference_chain:
            raise ValueError("composition blocker requires an exact reference chain")
        if any(
            type(reference) is not CapabilityProfileReference
            for reference in self.reference_chain
        ):
            raise ValueError("composition blocker requires exact profile references")


@dataclass(frozen=True, slots=True)
class EffectiveCapabilityProfileFactOccurrence:
    profile: StaticCapabilityProfile
    occurrence: CapabilityProfileFactOccurrence

    def __post_init__(self) -> None:
        if type(self.profile) is not StaticCapabilityProfile:
            raise ValueError("effective occurrence requires an exact profile")
        if type(self.occurrence) is not CapabilityProfileFactOccurrence:
            raise ValueError("effective occurrence requires an exact fact occurrence")
        if self.occurrence.owner is not self.profile.profile:
            raise ValueError("effective occurrence requires exact owner authority")

    @property
    def fact(self) -> CapabilityFact:
        return self.occurrence.fact


@dataclass(frozen=True, slots=True)
class CapabilityProfileCompositionSuccess:
    base: StaticCapabilityProfile
    overlays: tuple[StaticCapabilityProfile, ...]
    dependency_order: tuple[StaticCapabilityProfile, ...]
    effective_occurrences: tuple[EffectiveCapabilityProfileFactOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.base) is not StaticCapabilityProfile:
            raise ValueError("successful composition requires an exact base")
        if self.base.kind is not CapabilityProfileKind.BASE:
            raise ValueError("successful composition requires a BASE profile")
        if type(self.overlays) is not tuple or any(
            type(profile) is not StaticCapabilityProfile for profile in self.overlays
        ):
            raise ValueError("successful composition requires an exact overlay tuple")
        if any(
            profile.kind is not CapabilityProfileKind.OVERLAY
            for profile in self.overlays
        ):
            raise ValueError("successful composition requires OVERLAY profiles")
        if type(self.dependency_order) is not tuple or any(
            type(profile) is not StaticCapabilityProfile
            for profile in self.dependency_order
        ):
            raise ValueError("successful composition requires an exact profile order")
        selected_ids = {id(self.base), *(id(profile) for profile in self.overlays)}
        ordered_ids = {id(profile) for profile in self.dependency_order}
        if (
            not self.dependency_order
            or self.dependency_order[0] is not self.base
            or len(self.dependency_order) != len(self.overlays) + 1
            or len(selected_ids) != len(self.overlays) + 1
            or ordered_ids != selected_ids
        ):
            raise ValueError("successful composition requires exact selected authority")
        if type(self.effective_occurrences) is not tuple or any(
            type(item) is not EffectiveCapabilityProfileFactOccurrence
            for item in self.effective_occurrences
        ):
            raise ValueError(
                "successful composition requires exact effective occurrences"
            )
        expected = tuple(
            (id(profile), id(occurrence))
            for profile in self.dependency_order
            for occurrence in profile.capability_occurrences
        )
        actual = tuple(
            (id(item.profile), id(item.occurrence))
            for item in self.effective_occurrences
        )
        if actual != expected:
            raise ValueError("successful composition requires canonical fact authority")

    @property
    def facts(self) -> tuple[CapabilityFact, ...]:
        return tuple(item.fact for item in self.effective_occurrences)


@dataclass(frozen=True, slots=True)
class CapabilityProfileCompositionBlocked:
    base: StaticCapabilityProfile
    overlays: tuple[StaticCapabilityProfile, ...]
    blockers: tuple[CapabilityProfileCompositionBlocker, ...]

    def __post_init__(self) -> None:
        if type(self.base) is not StaticCapabilityProfile:
            raise ValueError("blocked composition requires an exact base")
        if type(self.overlays) is not tuple or any(
            type(profile) is not StaticCapabilityProfile for profile in self.overlays
        ):
            raise ValueError("blocked composition requires an exact overlay tuple")
        if (
            type(self.blockers) is not tuple
            or not self.blockers
            or any(
                type(blocker) is not CapabilityProfileCompositionBlocker
                for blocker in self.blockers
            )
        ):
            raise ValueError("blocked composition requires exact blocker evidence")


type CapabilityProfileCompositionResult = (
    CapabilityProfileCompositionSuccess | CapabilityProfileCompositionBlocked
)


def _freeze_overlays(
    overlays: Iterable[StaticCapabilityProfile],
) -> tuple[StaticCapabilityProfile, ...]:
    if isinstance(overlays, (str, bytes, Mapping, Set)):
        raise ValueError("profile composition requires an ordered overlay iterable")
    try:
        frozen = tuple(overlays)
    except TypeError as exc:
        raise ValueError(
            "profile composition requires an ordered overlay iterable"
        ) from exc
    if any(type(profile) is not StaticCapabilityProfile for profile in frozen):
        raise ValueError("profile composition requires exact overlay profiles")
    return frozen


def _append_blocker(
    blockers: list[CapabilityProfileCompositionBlocker],
    kind: CapabilityProfileCompositionBlockerKind,
    profiles: tuple[StaticCapabilityProfile, ...],
    *,
    base_occurrences: tuple[CapabilityProfileBaseOccurrence, ...] = (),
    fact_occurrences: tuple[CapabilityProfileFactOccurrence, ...] = (),
    reference_chain: tuple[CapabilityProfileReference, ...],
) -> None:
    blockers.append(
        CapabilityProfileCompositionBlocker(
            kind,
            profiles,
            base_occurrences,
            fact_occurrences,
            reference_chain,
        )
    )


def compose_capability_profiles(
    base: StaticCapabilityProfile,
    overlays: Iterable[StaticCapabilityProfile],
) -> CapabilityProfileCompositionResult:
    """Compose one exact base and ordered additive overlays without inference."""

    if type(base) is not StaticCapabilityProfile:
        raise ValueError("profile composition requires an exact base profile")
    frozen_overlays = _freeze_overlays(overlays)
    selected = (base, *frozen_overlays)
    blockers: list[CapabilityProfileCompositionBlocker] = []

    profiles_by_reference: dict[
        CapabilityProfileReference,
        list[StaticCapabilityProfile],
    ] = {}
    for profile in selected:
        profiles_by_reference.setdefault(profile.profile, []).append(profile)
    duplicate_references = {
        reference
        for reference, profiles in profiles_by_reference.items()
        if len(profiles) > 1
    }
    emitted_duplicate_references: set[CapabilityProfileReference] = set()
    if base.kind is not CapabilityProfileKind.BASE:
        _append_blocker(
            blockers,
            CapabilityProfileCompositionBlockerKind.INVALID_BASE_KIND,
            (base,),
            reference_chain=(base.profile,),
        )
    if base.profile in duplicate_references:
        emitted_duplicate_references.add(base.profile)
        _append_blocker(
            blockers,
            CapabilityProfileCompositionBlockerKind.DUPLICATE_PROFILE_REFERENCE,
            tuple(profiles_by_reference[base.profile]),
            reference_chain=(base.profile,),
        )

    unique_profiles = {
        reference: profiles[0]
        for reference, profiles in profiles_by_reference.items()
        if len(profiles) == 1
    }
    parent_by_reference: dict[
        CapabilityProfileReference,
        CapabilityProfileReference,
    ] = {}
    edge_by_reference: dict[
        CapabilityProfileReference,
        CapabilityProfileBaseOccurrence,
    ] = {}
    for profile in frozen_overlays:
        if profile.kind is not CapabilityProfileKind.OVERLAY:
            _append_blocker(
                blockers,
                CapabilityProfileCompositionBlockerKind.INVALID_OVERLAY_KIND,
                (profile,),
                reference_chain=(profile.profile,),
            )
        if (
            profile.profile in duplicate_references
            and profile.profile not in emitted_duplicate_references
        ):
            emitted_duplicate_references.add(profile.profile)
            _append_blocker(
                blockers,
                CapabilityProfileCompositionBlockerKind.DUPLICATE_PROFILE_REFERENCE,
                tuple(profiles_by_reference[profile.profile]),
                reference_chain=(profile.profile,),
            )
        if profile.schema_version is not base.schema_version:
            _append_blocker(
                blockers,
                CapabilityProfileCompositionBlockerKind.SCHEMA_VERSION_MISMATCH,
                (base, profile),
                reference_chain=(base.profile, profile.profile),
            )
        if profile.kind is not CapabilityProfileKind.OVERLAY:
            continue
        if profile.target.family != base.target.family:
            _append_blocker(
                blockers,
                CapabilityProfileCompositionBlockerKind.TARGET_FAMILY_MISMATCH,
                (base, profile),
                reference_chain=(base.profile, profile.profile),
            )
        if profile.target.release != base.target.release:
            _append_blocker(
                blockers,
                CapabilityProfileCompositionBlockerKind.TARGET_RELEASE_MISMATCH,
                (base, profile),
                reference_chain=(base.profile, profile.profile),
            )
        occurrence = profile.base_occurrences[0]
        matches = profiles_by_reference.get(occurrence.base, ())
        if not matches:
            _append_blocker(
                blockers,
                CapabilityProfileCompositionBlockerKind.UNRESOLVED_BASE,
                (profile,),
                base_occurrences=(occurrence,),
                reference_chain=(profile.profile, occurrence.base),
            )
        elif len(matches) > 1:
            _append_blocker(
                blockers,
                CapabilityProfileCompositionBlockerKind.AMBIGUOUS_BASE_REFERENCE,
                (profile, *matches),
                base_occurrences=(occurrence,),
                reference_chain=(profile.profile, occurrence.base),
            )
        elif profile.profile not in duplicate_references:
            parent_by_reference[profile.profile] = matches[0].profile
            edge_by_reference[profile.profile] = occurrence

    processed: set[CapabilityProfileReference] = set()
    unrooted_terminals: set[CapabilityProfileReference] = set()
    for profile in frozen_overlays:
        start = profile.profile
        if start in processed or start not in parent_by_reference:
            continue
        path: list[CapabilityProfileReference] = []
        positions: dict[CapabilityProfileReference, int] = {}
        current = start
        while True:
            if current == base.profile:
                processed.update(path)
                break
            if current in positions:
                cycle_start = positions[current]
                cycle = (*path[cycle_start:], current)
                cycle_nodes = cycle[:-1]
                _append_blocker(
                    blockers,
                    CapabilityProfileCompositionBlockerKind.CYCLE,
                    tuple(unique_profiles[reference] for reference in cycle_nodes),
                    base_occurrences=tuple(
                        edge_by_reference[reference] for reference in cycle_nodes
                    ),
                    reference_chain=cycle,
                )
                processed.update(path)
                break
            if current in processed:
                processed.update(path)
                break
            positions[current] = len(path)
            path.append(current)
            parent = parent_by_reference.get(current)
            if parent is None:
                terminal = unique_profiles.get(current)
                if (
                    terminal is not None
                    and terminal.kind is CapabilityProfileKind.BASE
                    and current not in unrooted_terminals
                ):
                    unrooted_terminals.add(current)
                    _append_blocker(
                        blockers,
                        CapabilityProfileCompositionBlockerKind.CHAIN_NOT_ROOTED,
                        tuple(unique_profiles[reference] for reference in path),
                        base_occurrences=tuple(
                            edge_by_reference[reference]
                            for reference in path
                            if reference in edge_by_reference
                        ),
                        reference_chain=tuple(path),
                    )
                processed.update(path)
                break
            current = parent

    fact_sources: dict[
        CapabilityFact,
        list[tuple[StaticCapabilityProfile, CapabilityProfileFactOccurrence]],
    ] = {}
    for profile in selected:
        for occurrence in profile.capability_occurrences:
            fact_sources.setdefault(occurrence.fact, []).append((profile, occurrence))
    for sources in fact_sources.values():
        if len(sources) > 1:
            _append_blocker(
                blockers,
                CapabilityProfileCompositionBlockerKind.EXACT_DUPLICATE_CAPABILITY_FACT,
                tuple(profile for profile, _occurrence in sources),
                fact_occurrences=tuple(occurrence for _profile, occurrence in sources),
                reference_chain=tuple(
                    profile.profile for profile, _occurrence in sources
                ),
            )

    if blockers:
        return CapabilityProfileCompositionBlocked(
            base,
            frozen_overlays,
            tuple(blockers),
        )

    dependency_order = [base]
    ordered_ids = {id(base)}
    remaining = list(frozen_overlays)
    # ponytail: stable O(n²) selection; use an indexed queue if profile counts grow.
    while remaining:
        for position, profile in enumerate(remaining):
            parent = unique_profiles[parent_by_reference[profile.profile]]
            if id(parent) in ordered_ids:
                dependency_order.append(profile)
                ordered_ids.add(id(profile))
                remaining.pop(position)
                break
        else:
            raise AssertionError("validated profile graph must have a dependency order")
    effective_occurrences = tuple(
        EffectiveCapabilityProfileFactOccurrence(profile, occurrence)
        for profile in dependency_order
        for occurrence in profile.capability_occurrences
    )
    return CapabilityProfileCompositionSuccess(
        base,
        frozen_overlays,
        tuple(dependency_order),
        effective_occurrences,
    )
