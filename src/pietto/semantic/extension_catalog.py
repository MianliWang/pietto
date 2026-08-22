"""Private extension-catalog identity, target, and source-provenance schema."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath

from pietto.semantic.generic_compatibility import LogicalTypeIdentity

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


class ExtensionCatalogTypeReferenceKind(StrEnum):
    PIETTO_LOGICAL = "pietto_logical"
    POSTGRES_BUILTIN = "postgres_builtin"
    EXTENSION_NATIVE = "extension_native"


@dataclass(frozen=True, slots=True)
class ExtensionCatalogTypeReference:
    kind: ExtensionCatalogTypeReferenceKind
    logical_type: LogicalTypeIdentity | None = None
    physical_name: str | None = None
    extension_identity: str | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ExtensionCatalogTypeReferenceKind:
            raise ValueError("catalog type reference requires an exact kind")
        if self.kind is ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL:
            if type(self.logical_type) is not LogicalTypeIdentity:
                raise ValueError("Pietto logical reference requires exact authority")
            if self.physical_name is not None or self.extension_identity is not None:
                raise ValueError("Pietto logical reference forbids physical identity")
            return
        if self.logical_type is not None:
            raise ValueError("PostgreSQL type reference forbids logical authority")
        _require_text(self.physical_name, "PostgreSQL physical type name")
        if self.kind is ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN:
            if self.extension_identity is not None:
                raise ValueError("PostgreSQL builtin reference forbids extension owner")
            return
        _require_text(self.extension_identity, "extension identity")


def _require_postgresql_type_reference(
    value: object,
    label: str,
) -> ExtensionCatalogTypeReference:
    if type(value) is not ExtensionCatalogTypeReference:
        raise ValueError(f"{label} requires an exact catalog type reference")
    if value.kind is ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL:
        raise ValueError(f"{label} requires a PostgreSQL-side type reference")
    return value


def _freeze_postgresql_type_references(
    values: Iterable[ExtensionCatalogTypeReference],
    label: str,
) -> tuple[ExtensionCatalogTypeReference, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError(f"{label} requires an ordered iterable")
    try:
        references = tuple(values)
    except TypeError as exc:
        raise ValueError(f"{label} requires an ordered iterable") from exc
    for reference in references:
        _require_postgresql_type_reference(reference, label)
    return references


@dataclass(frozen=True, slots=True)
class PostgreSQLCallableIdentity:
    sql_name: str
    input_types: tuple[ExtensionCatalogTypeReference, ...]

    def __post_init__(self) -> None:
        _require_text(self.sql_name, "PostgreSQL callable name")
        object.__setattr__(
            self,
            "input_types",
            _freeze_postgresql_type_references(
                self.input_types,
                "PostgreSQL callable input types",
            ),
        )


class PostgreSQLOperatorArity(StrEnum):
    UNARY = "unary"
    BINARY = "binary"


@dataclass(frozen=True, slots=True)
class PostgreSQLOperatorIdentity:
    operator_name: str
    arity: PostgreSQLOperatorArity
    operand_types: tuple[ExtensionCatalogTypeReference, ...]

    def __post_init__(self) -> None:
        _require_text(self.operator_name, "PostgreSQL operator name")
        if type(self.arity) is not PostgreSQLOperatorArity:
            raise ValueError("PostgreSQL operator requires an exact arity")
        operands = _freeze_postgresql_type_references(
            self.operand_types,
            "PostgreSQL operator operand types",
        )
        expected_arity = 1 if self.arity is PostgreSQLOperatorArity.UNARY else 2
        if len(operands) != expected_arity:
            raise ValueError("PostgreSQL operator arity must match its operands")
        object.__setattr__(self, "operand_types", operands)


@dataclass(frozen=True, slots=True)
class PostgreSQLCastIdentity:
    source_type: ExtensionCatalogTypeReference
    target_type: ExtensionCatalogTypeReference

    def __post_init__(self) -> None:
        _require_postgresql_type_reference(
            self.source_type,
            "PostgreSQL cast source",
        )
        _require_postgresql_type_reference(
            self.target_type,
            "PostgreSQL cast target",
        )
