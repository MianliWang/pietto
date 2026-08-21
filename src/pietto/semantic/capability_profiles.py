"""Private static capability-profile and exact-requirement schema."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

from pietto.semantic.capability_facts import CapabilityFact, CapabilityKey

__all__: tuple[str, ...] = ()

_Occurrence = TypeVar("_Occurrence")


class CapabilityProfileSchemaVersion(StrEnum):
    PROFILE_V1 = "pietto.capability-profile.v1"


class CapabilityProfileKind(StrEnum):
    BASE = "base"
    OVERLAY = "overlay"


class CapabilityProfileTargetKind(StrEnum):
    DATABASE = "database"
    EXTENSION = "extension"


def _require_text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} requires exact nonblank text")
    return value


def _require_optional_text(value: object | None, label: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, label)


def _freeze_occurrences(
    values: Iterable[_Occurrence],
    item_type: type[_Occurrence],
    label: str,
) -> tuple[_Occurrence, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{label} requires an iterable")
    try:
        frozen = tuple(values)
    except TypeError as exc:
        raise ValueError(f"{label} requires an iterable") from exc
    if any(type(value) is not item_type for value in frozen):
        raise ValueError(f"{label} requires exact occurrences")
    for position, value in enumerate(frozen):
        if getattr(value, "position", None) != position:
            raise ValueError(f"{label} positions must be dense and source ordered")
    return frozen


@dataclass(frozen=True, slots=True)
class CapabilityProfileIdentity:
    namespace: str
    name: str

    def __post_init__(self) -> None:
        _require_text(self.namespace, "profile namespace")
        _require_text(self.name, "profile name")


@dataclass(frozen=True, slots=True)
class CapabilityProfileReference:
    identity: CapabilityProfileIdentity
    release: str

    def __post_init__(self) -> None:
        if type(self.identity) is not CapabilityProfileIdentity:
            raise ValueError("profile reference requires an exact identity")
        _require_text(self.release, "profile release")


@dataclass(frozen=True, slots=True)
class CapabilityProfileTarget:
    kind: CapabilityProfileTargetKind
    family: str
    release: str
    extension_identity: str | None = None
    extension_release: str | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not CapabilityProfileTargetKind:
            raise ValueError("profile target requires an exact kind")
        _require_text(self.family, "target family")
        _require_text(self.release, "target release")
        extension_identity = _require_optional_text(
            self.extension_identity,
            "extension identity",
        )
        extension_release = _require_optional_text(
            self.extension_release,
            "extension release",
        )
        has_extension = extension_identity is not None or extension_release is not None
        if self.kind is CapabilityProfileTargetKind.DATABASE and has_extension:
            raise ValueError("database targets forbid extension identity")
        if self.kind is CapabilityProfileTargetKind.EXTENSION and (
            extension_identity is None or extension_release is None
        ):
            raise ValueError("extension targets require exact extension identity")


@dataclass(frozen=True, slots=True)
class CapabilityProfileBaseOccurrence:
    owner: CapabilityProfileReference
    position: int
    base: CapabilityProfileReference

    def __post_init__(self) -> None:
        if type(self.owner) is not CapabilityProfileReference:
            raise ValueError("profile base occurrence requires an exact owner")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("profile base occurrence requires a non-negative position")
        if type(self.base) is not CapabilityProfileReference:
            raise ValueError("profile base occurrence requires an exact base")


@dataclass(frozen=True, slots=True)
class CapabilityProfileFactOccurrence:
    owner: CapabilityProfileReference
    position: int
    fact: CapabilityFact

    def __post_init__(self) -> None:
        if type(self.owner) is not CapabilityProfileReference:
            raise ValueError("profile fact occurrence requires an exact owner")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("profile fact occurrence requires a non-negative position")
        if type(self.fact) is not CapabilityFact:
            raise ValueError("profile fact occurrence requires an exact fact")


@dataclass(frozen=True, slots=True)
class StaticCapabilityProfile:
    schema_version: CapabilityProfileSchemaVersion
    profile: CapabilityProfileReference
    target: CapabilityProfileTarget
    kind: CapabilityProfileKind
    base_occurrences: tuple[CapabilityProfileBaseOccurrence, ...]
    capability_occurrences: tuple[CapabilityProfileFactOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not CapabilityProfileSchemaVersion:
            raise ValueError("capability profile requires an exact schema version")
        if type(self.profile) is not CapabilityProfileReference:
            raise ValueError("capability profile requires an exact profile reference")
        if type(self.target) is not CapabilityProfileTarget:
            raise ValueError("capability profile requires an exact target")
        if type(self.kind) is not CapabilityProfileKind:
            raise ValueError("capability profile requires an exact kind")
        required_target_kind = (
            CapabilityProfileTargetKind.DATABASE
            if self.kind is CapabilityProfileKind.BASE
            else CapabilityProfileTargetKind.EXTENSION
        )
        if self.target.kind is not required_target_kind:
            raise ValueError(
                f"{self.kind.name} capability profiles require "
                f"{required_target_kind.name} targets"
            )
        bases = _freeze_occurrences(
            self.base_occurrences,
            CapabilityProfileBaseOccurrence,
            "profile base occurrences",
        )
        capabilities = _freeze_occurrences(
            self.capability_occurrences,
            CapabilityProfileFactOccurrence,
            "profile capability occurrences",
        )
        object.__setattr__(self, "base_occurrences", bases)
        object.__setattr__(self, "capability_occurrences", capabilities)

        for occurrence in (*bases, *capabilities):
            if occurrence.owner is not self.profile:
                raise ValueError("profile occurrences require exact owner authority")

        first_base_position: dict[CapabilityProfileReference, int] = {}
        for occurrence in bases:
            first = first_base_position.setdefault(occurrence.base, occurrence.position)
            if first != occurrence.position:
                raise ValueError(
                    f"profile base position {occurrence.position} duplicates position {first}"
                )
        if self.kind is CapabilityProfileKind.BASE and bases:
            raise ValueError("BASE capability profiles forbid a base declaration")
        if self.kind is CapabilityProfileKind.OVERLAY and len(bases) != 1:
            raise ValueError("OVERLAY capability profiles require one exact base")

        first_fact_position: dict[CapabilityFact, int] = {}
        for occurrence in capabilities:
            first = first_fact_position.setdefault(occurrence.fact, occurrence.position)
            if first != occurrence.position:
                raise ValueError(
                    f"profile fact position {occurrence.position} duplicates position {first}"
                )


@dataclass(frozen=True, slots=True)
class CapabilityRequirementCollectionIdentity:
    namespace: str
    name: str

    def __post_init__(self) -> None:
        _require_text(self.namespace, "requirement namespace")
        _require_text(self.name, "requirement name")


@dataclass(frozen=True, slots=True)
class CapabilityRequirementOccurrence:
    owner: CapabilityRequirementCollectionIdentity
    position: int
    key: CapabilityKey

    def __post_init__(self) -> None:
        if type(self.owner) is not CapabilityRequirementCollectionIdentity:
            raise ValueError("requirement occurrence requires an exact owner")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("requirement occurrence requires a non-negative position")
        if type(self.key) is not CapabilityKey:
            raise ValueError("requirement occurrence requires an exact key")


@dataclass(frozen=True, slots=True)
class CapabilityRequirementCollection:
    identity: CapabilityRequirementCollectionIdentity
    occurrences: tuple[CapabilityRequirementOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.identity) is not CapabilityRequirementCollectionIdentity:
            raise ValueError("requirement collection requires an exact identity")
        occurrences = _freeze_occurrences(
            self.occurrences,
            CapabilityRequirementOccurrence,
            "requirement occurrences",
        )
        object.__setattr__(self, "occurrences", occurrences)
        first_key_position: dict[CapabilityKey, int] = {}
        for occurrence in occurrences:
            if occurrence.owner is not self.identity:
                raise ValueError("requirements require exact owner authority")
            first = first_key_position.setdefault(occurrence.key, occurrence.position)
            if first != occurrence.position:
                raise ValueError(
                    f"requirement position {occurrence.position} duplicates position {first}"
                )
