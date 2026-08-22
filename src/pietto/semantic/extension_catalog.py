"""Private extension-catalog identity, target, and source-provenance schema."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath

__all__: tuple[str, ...] = ()


class ExtensionCatalogSchemaVersion(StrEnum):
    EXTENSION_CATALOG_V1 = "pietto.extension-catalog.v1"


def _require_text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} requires exact nonblank text")
    return value


def _require_source_locator(value: object) -> str:
    locator = _require_text(value, "source locator")
    windows_path = PureWindowsPath(locator)
    if (
        PurePosixPath(locator).is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.root)
    ):
        raise ValueError("source locator forbids a host absolute path")
    return locator


@dataclass(frozen=True, slots=True)
class ExtensionCatalogIdentity:
    namespace: str
    name: str

    def __post_init__(self) -> None:
        _require_text(self.namespace, "catalog namespace")
        _require_text(self.name, "catalog name")


@dataclass(frozen=True, slots=True)
class ExtensionCatalogReference:
    identity: ExtensionCatalogIdentity
    release: str

    def __post_init__(self) -> None:
        if type(self.identity) is not ExtensionCatalogIdentity:
            raise ValueError("catalog reference requires an exact identity")
        _require_text(self.release, "catalog release")


@dataclass(frozen=True, slots=True)
class ExtensionCatalogTarget:
    database_family: str
    database_release: str
    extension_identity: str
    extension_release: str

    def __post_init__(self) -> None:
        _require_text(self.database_family, "database family")
        _require_text(self.database_release, "database release")
        _require_text(self.extension_identity, "extension identity")
        _require_text(self.extension_release, "extension release")


@dataclass(frozen=True, slots=True)
class ExtensionCatalogSourceProvenance:
    source_authority: str
    source_revision: str
    source_locator: str
    curation: str

    def __post_init__(self) -> None:
        _require_text(self.source_authority, "source authority")
        _require_text(self.source_revision, "source revision")
        _require_source_locator(self.source_locator)
        _require_text(self.curation, "source curation")


@dataclass(frozen=True, slots=True)
class ExtensionCatalogSourceOccurrence:
    owner: ExtensionCatalogReference
    position: int
    provenance: ExtensionCatalogSourceProvenance

    def __post_init__(self) -> None:
        if type(self.owner) is not ExtensionCatalogReference:
            raise ValueError("catalog source occurrence requires an exact owner")
        if type(self.position) is not int or self.position < 0:
            raise ValueError(
                "catalog source occurrence requires a non-negative position"
            )
        if type(self.provenance) is not ExtensionCatalogSourceProvenance:
            raise ValueError("catalog source occurrence requires exact provenance")


def _freeze_source_occurrences(
    values: Iterable[ExtensionCatalogSourceOccurrence],
) -> tuple[ExtensionCatalogSourceOccurrence, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError("catalog source occurrences require an ordered iterable")
    try:
        occurrences = tuple(values)
    except TypeError as exc:
        raise ValueError(
            "catalog source occurrences require an ordered iterable"
        ) from exc
    if any(
        type(value) is not ExtensionCatalogSourceOccurrence for value in occurrences
    ):
        raise ValueError("catalog sources require exact occurrences")
    if any(
        occurrence.position != position
        for position, occurrence in enumerate(occurrences)
    ):
        raise ValueError("catalog source positions must be dense and source ordered")
    return occurrences


@dataclass(frozen=True, slots=True)
class ExtensionCatalogMetadata:
    schema_version: ExtensionCatalogSchemaVersion
    catalog: ExtensionCatalogReference
    target: ExtensionCatalogTarget
    source_occurrences: tuple[ExtensionCatalogSourceOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not ExtensionCatalogSchemaVersion:
            raise ValueError("catalog metadata requires an exact schema version")
        if type(self.catalog) is not ExtensionCatalogReference:
            raise ValueError("catalog metadata requires an exact catalog reference")
        if type(self.target) is not ExtensionCatalogTarget:
            raise ValueError("catalog metadata requires an exact target")
        occurrences = _freeze_source_occurrences(self.source_occurrences)
        if any(occurrence.owner is not self.catalog for occurrence in occurrences):
            raise ValueError("catalog sources require exact owner authority")
        object.__setattr__(self, "source_occurrences", occurrences)
