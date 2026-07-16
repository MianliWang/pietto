"""Private fail-closed capability fact lookup."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pietto.semantic.capability_facts import (
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Found:
    """One exact capability fact matched the requested key."""

    fact: CapabilityFact

    def __post_init__(self) -> None:
        """Require one exact private fact carrier."""

        if type(self.fact) is not CapabilityFact:
            raise ValueError("Found requires an exact capability fact")


@dataclass(frozen=True, slots=True)
class Absent:
    """A complete lookup domain has no fact for the requested key."""

    key: CapabilityKey
    reason: CapabilityReasonCode = CapabilityReasonCode.NO_CATALOG_ENTRY

    def __post_init__(self) -> None:
        """Restrict absence to exact-key complete-domain evidence."""

        if type(self.key) is not CapabilityKey:
            raise ValueError("Absent requires an exact capability key")
        if self.reason is not CapabilityReasonCode.NO_CATALOG_ENTRY:
            raise ValueError("Absent requires NO_CATALOG_ENTRY")


@dataclass(frozen=True, slots=True)
class Unknown:
    """An incomplete lookup domain cannot decide the requested key."""

    reason: CapabilityReasonCode

    def __post_init__(self) -> None:
        """Reject absence-only and conflict-only reasons."""

        if type(self.reason) is not CapabilityReasonCode:
            raise ValueError("Unknown requires an exact capability reason")
        if self.reason in {
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityReasonCode.CONFLICTING_EVIDENCE,
        }:
            raise ValueError("Unknown forbids absence and conflict reasons")


@dataclass(frozen=True, slots=True)
class Conflict:
    """Distinct facts make the exact-key lookup contradictory."""

    reason: CapabilityReasonCode
    evidence: tuple[CapabilityFact, ...]

    def __post_init__(self) -> None:
        """Freeze ordered, distinct, same-key conflicting evidence."""

        if self.reason is not CapabilityReasonCode.CONFLICTING_EVIDENCE:
            raise ValueError("Conflict requires CONFLICTING_EVIDENCE")
        if isinstance(self.evidence, (str, bytes)):
            raise ValueError("Conflict evidence requires an iterable of facts")
        try:
            evidence = tuple(self.evidence)
        except TypeError as exc:
            raise ValueError("Conflict evidence requires an iterable of facts") from exc
        if len(evidence) < 2:
            raise ValueError("Conflict requires at least two facts")
        if any(type(fact) is not CapabilityFact for fact in evidence):
            raise ValueError("Conflict requires exact capability facts")
        if len(set(evidence)) != len(evidence):
            raise ValueError("Conflict requires mutually distinct facts")
        first_key = evidence[0].key
        if any(fact.key != first_key for fact in evidence[1:]):
            raise ValueError("Conflict requires one exact capability key")
        object.__setattr__(self, "evidence", evidence)


type CapabilityLookupResult = Found | Absent | Unknown | Conflict


def lookup_capability(
    key: CapabilityKey,
    facts: Iterable[CapabilityFact],
    *,
    domain_complete: bool,
    unknown_reason: CapabilityReasonCode | None = None,
) -> CapabilityLookupResult:
    """Resolve one exact key without normalization, inference, or fallback."""

    if type(key) is not CapabilityKey:
        raise ValueError("Capability lookup requires an exact key")
    if type(domain_complete) is not bool:
        raise ValueError("Capability lookup requires an exact completeness flag")
    if unknown_reason is not None:
        if type(unknown_reason) is not CapabilityReasonCode:
            raise ValueError("Capability lookup requires an exact unknown reason")
        if unknown_reason in {
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityReasonCode.CONFLICTING_EVIDENCE,
        }:
            raise ValueError("Capability lookup forbids an inadmissible unknown reason")
    if isinstance(facts, (str, bytes)):
        raise ValueError("Capability lookup facts require an iterable")
    try:
        frozen_facts = tuple(facts)
    except TypeError as exc:
        raise ValueError("Capability lookup facts require an iterable") from exc
    if any(type(fact) is not CapabilityFact for fact in frozen_facts):
        raise ValueError("Capability lookup requires exact capability facts")

    matches: list[CapabilityFact] = []
    seen: set[CapabilityFact] = set()
    for fact in frozen_facts:
        if fact.key == key and fact not in seen:
            seen.add(fact)
            matches.append(fact)

    if len(matches) == 1:
        return Found(matches[0])
    if len(matches) > 1:
        return Conflict(CapabilityReasonCode.CONFLICTING_EVIDENCE, tuple(matches))
    if domain_complete:
        if unknown_reason is not None:
            raise ValueError("Complete-domain absence forbids an unknown reason")
        return Absent(key)
    return Unknown(
        CapabilityReasonCode.NOT_EVIDENCED if unknown_reason is None else unknown_reason
    )
