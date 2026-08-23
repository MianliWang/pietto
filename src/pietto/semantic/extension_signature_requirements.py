"""Private typed selectors for extension-signature requirements."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from enum import StrEnum

from pietto.semantic.capability_facts import CapabilityDomain
from pietto.semantic.capability_profiles import CapabilityRequirementCollection
from pietto.semantic.extension_catalog import (
    ExtensionCatalogEntryFamily,
    ExtensionCatalogLookupScope,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    PostgreSQLCallableIdentity,
    PostgreSQLCastIdentity,
    PostgreSQLOperatorIdentity,
)

__all__: tuple[str, ...] = ()


class ExtensionSignatureDialectFamilyBridge(StrEnum):
    POSTGRESQL = "postgresql"

    @property
    def database_family(self) -> str:
        return "PostgreSQL"


def extension_signature_dialect_family_bridge(
    dialect: object,
) -> ExtensionSignatureDialectFamilyBridge | None:
    if type(dialect) is not str:
        return None
    if dialect == ExtensionSignatureDialectFamilyBridge.POSTGRESQL.value:
        return ExtensionSignatureDialectFamilyBridge.POSTGRESQL
    return None


@dataclass(frozen=True, slots=True)
class ExtensionSignatureRequirementSelector:
    scope: ExtensionCatalogLookupScope

    def __post_init__(self) -> None:
        if type(self.scope) is not ExtensionCatalogLookupScope:
            raise ValueError("extension signature selector requires an exact scope")


@dataclass(frozen=True, slots=True)
class ExtensionSignatureRequirementSelectorOccurrence:
    requirement_position: int
    selector: ExtensionSignatureRequirementSelector

    def __post_init__(self) -> None:
        if type(self.requirement_position) is not int or self.requirement_position < 0:
            raise ValueError("extension signature selector requires an exact position")
        if type(self.selector) is not ExtensionSignatureRequirementSelector:
            raise ValueError(
                "extension signature selector occurrence requires a selector"
            )


def _freeze_selector_occurrences(
    values: Iterable[ExtensionSignatureRequirementSelectorOccurrence],
) -> tuple[ExtensionSignatureRequirementSelectorOccurrence, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError("extension signature selectors require an ordered iterable")
    try:
        occurrences = tuple(values)
    except TypeError as exc:
        raise ValueError(
            "extension signature selectors require an ordered iterable"
        ) from exc
    if any(
        type(occurrence) is not ExtensionSignatureRequirementSelectorOccurrence
        for occurrence in occurrences
    ):
        raise ValueError("extension signature selectors require exact occurrences")
    return occurrences


def _selector_type_references(
    scope: ExtensionCatalogLookupScope,
) -> tuple[ExtensionCatalogTypeReference, ...]:
    identity = scope.identity
    if scope.family is ExtensionCatalogEntryFamily.NATIVE_TYPE:
        if isinstance(identity, ExtensionCatalogTypeReference):
            return (identity,)
    elif scope.family in {
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        ExtensionCatalogEntryFamily.AGGREGATE,
    }:
        if isinstance(identity, PostgreSQLCallableIdentity):
            return identity.input_types
    elif scope.family is ExtensionCatalogEntryFamily.OPERATOR:
        if isinstance(identity, PostgreSQLOperatorIdentity):
            return identity.operand_types
    elif scope.family is ExtensionCatalogEntryFamily.CAST:
        if isinstance(identity, PostgreSQLCastIdentity):
            return (identity.source_type, identity.target_type)
    raise ValueError("extension signature selector has an invalid scope identity")


def _validate_extension_owners(
    selector: ExtensionSignatureRequirementSelector,
    extension: str,
) -> None:
    for reference in _selector_type_references(selector.scope):
        if (
            reference.kind is ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE
            and reference.extension_identity != extension
        ):
            raise ValueError(
                "extension signature selector type owner must match the requirement"
            )


@dataclass(frozen=True, slots=True)
class ExtensionSignatureRequirementSelectors:
    requirements: CapabilityRequirementCollection
    occurrences: tuple[ExtensionSignatureRequirementSelectorOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.requirements) is not CapabilityRequirementCollection:
            raise ValueError("extension signature selectors require exact requirements")
        occurrences = _freeze_selector_occurrences(self.occurrences)
        for occurrence in occurrences:
            if occurrence.requirement_position >= len(self.requirements.occurrences):
                raise ValueError(
                    "extension signature selector position must resolve a requirement"
                )
            requirement = self.requirements.occurrences[occurrence.requirement_position]
            key = requirement.key
            if key.domain is not CapabilityDomain.EXTENSION_SIGNATURE:
                raise ValueError(
                    "extension signature selector requires an EXTENSION_SIGNATURE requirement"
                )
            if key.dialect is None:
                raise ValueError(
                    "extension signature selector requirement requires a dialect"
                )
            if key.extension is None:
                raise ValueError(
                    "extension signature selector requirement requires an extension"
                )
            if extension_signature_dialect_family_bridge(key.dialect) is None:
                raise ValueError(
                    "extension signature selector requirement has no dialect-family bridge"
                )
            _validate_extension_owners(occurrence.selector, key.extension)

        expected_positions = tuple(
            requirement.position
            for requirement in self.requirements.occurrences
            if requirement.key.domain is CapabilityDomain.EXTENSION_SIGNATURE
        )
        actual_positions = tuple(
            occurrence.requirement_position for occurrence in occurrences
        )
        if actual_positions != expected_positions:
            raise ValueError(
                "extension signature selectors must cover each requirement exactly once in source order"
            )
        object.__setattr__(self, "occurrences", occurrences)
