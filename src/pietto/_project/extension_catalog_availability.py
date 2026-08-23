"""Private extension-catalog availability and exact target selection."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from enum import StrEnum

from pietto._project.model import ProjectRoot
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionCatalogReference,
    ExtensionCatalogTarget,
)

__all__: tuple[str, ...] = ()


class ExtensionCatalogAvailabilityOwner(StrEnum):
    COMPILER = "compiler"
    PROJECT = "project"


@dataclass(frozen=True, slots=True)
class ExtensionCatalogAvailabilityDeclaration:
    owner: ExtensionCatalogAvailabilityOwner
    position: int
    catalog: ConstructedExtensionCatalog
    project: ProjectRoot | None = None

    def __post_init__(self) -> None:
        if type(self.owner) is not ExtensionCatalogAvailabilityOwner:
            raise ValueError("catalog availability requires an exact owner")
        if type(self.position) is not int or self.position < 0:
            raise ValueError("catalog availability requires a non-negative position")
        if type(self.catalog) is not ConstructedExtensionCatalog:
            raise ValueError("catalog availability requires an exact catalog artifact")
        if self.owner is ExtensionCatalogAvailabilityOwner.COMPILER:
            if self.project is not None:
                raise ValueError("compiler catalog availability forbids a project root")
        elif type(self.project) is not ProjectRoot:
            raise ValueError(
                "project catalog availability requires an exact project root"
            )

    @property
    def reference(self) -> ExtensionCatalogReference:
        return self.catalog.metadata.catalog

    @property
    def target(self) -> ExtensionCatalogTarget:
        return self.catalog.metadata.target

    @property
    def content_sha256(self) -> str:
        return self.catalog.content_sha256


def _freeze_declarations(
    values: Iterable[ExtensionCatalogAvailabilityDeclaration],
) -> tuple[ExtensionCatalogAvailabilityDeclaration, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError("catalog availability requires an ordered iterable")
    try:
        declarations = tuple(values)
    except TypeError as exc:
        raise ValueError("catalog availability requires an ordered iterable") from exc
    if any(
        type(declaration) is not ExtensionCatalogAvailabilityDeclaration
        for declaration in declarations
    ):
        raise ValueError("catalog availability requires exact declarations")
    if any(
        declaration.position != position
        for position, declaration in enumerate(declarations)
    ):
        raise ValueError("catalog availability positions must be dense and ordered")
    return declarations


@dataclass(frozen=True, slots=True)
class DeclaredExtensionCatalogAvailability:
    declarations: tuple[ExtensionCatalogAvailabilityDeclaration, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "declarations",
            _freeze_declarations(self.declarations),
        )


@dataclass(frozen=True, slots=True)
class ExtensionCatalogSelectionCandidateIdentity:
    reference: ExtensionCatalogReference
    target: ExtensionCatalogTarget
    content_sha256: str

    def __post_init__(self) -> None:
        if type(self.reference) is not ExtensionCatalogReference:
            raise ValueError("catalog candidate identity requires an exact reference")
        if type(self.target) is not ExtensionCatalogTarget:
            raise ValueError("catalog candidate identity requires an exact target")
        if (
            type(self.content_sha256) is not str
            or len(self.content_sha256) != 64
            or any(
                character not in "0123456789abcdef" for character in self.content_sha256
            )
        ):
            raise ValueError("catalog candidate identity requires exact SHA-256 text")


def _candidate_identity(
    catalog: ConstructedExtensionCatalog,
) -> ExtensionCatalogSelectionCandidateIdentity:
    return ExtensionCatalogSelectionCandidateIdentity(
        catalog.metadata.catalog,
        catalog.metadata.target,
        catalog.content_sha256,
    )


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogSelectionCandidate:
    identity: ExtensionCatalogSelectionCandidateIdentity
    catalog: ConstructedExtensionCatalog
    declarations: tuple[ExtensionCatalogAvailabilityDeclaration, ...]

    def __new__(cls) -> ExtensionCatalogSelectionCandidate:
        raise TypeError("catalog selection candidates require canonical selection")


class ExtensionCatalogSelectionOutcome(StrEnum):
    UNDECLARED = "undeclared"
    SELECTED = "selected"
    AMBIGUOUS = "ambiguous"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogSelectionResult:
    outcome: ExtensionCatalogSelectionOutcome
    requested_target: ExtensionCatalogTarget
    active_project: ProjectRoot | None
    availability: DeclaredExtensionCatalogAvailability
    applicable_declarations: tuple[ExtensionCatalogAvailabilityDeclaration, ...]
    excluded_project_declarations: tuple[ExtensionCatalogAvailabilityDeclaration, ...]
    target_declarations: tuple[ExtensionCatalogAvailabilityDeclaration, ...]
    candidates: tuple[ExtensionCatalogSelectionCandidate, ...]
    selected_catalog: ConstructedExtensionCatalog | None

    def __new__(cls) -> ExtensionCatalogSelectionResult:
        raise TypeError("catalog selection results require canonical selection")


def _candidate_sort_key(
    identity: ExtensionCatalogSelectionCandidateIdentity,
) -> tuple[str, ...]:
    return (
        identity.reference.identity.namespace,
        identity.reference.identity.name,
        identity.reference.release,
        identity.target.database_family,
        identity.target.database_release,
        identity.target.extension_identity,
        identity.target.extension_release,
        identity.content_sha256,
    )


def _new_candidate(
    identity: ExtensionCatalogSelectionCandidateIdentity,
    declarations: tuple[ExtensionCatalogAvailabilityDeclaration, ...],
) -> ExtensionCatalogSelectionCandidate:
    candidate = object.__new__(ExtensionCatalogSelectionCandidate)
    object.__setattr__(candidate, "identity", identity)
    object.__setattr__(candidate, "catalog", declarations[0].catalog)
    object.__setattr__(candidate, "declarations", declarations)
    return candidate


def _selection_result(
    outcome: ExtensionCatalogSelectionOutcome,
    requested_target: ExtensionCatalogTarget,
    active_project: ProjectRoot | None,
    availability: DeclaredExtensionCatalogAvailability,
    applicable_declarations: tuple[ExtensionCatalogAvailabilityDeclaration, ...],
    excluded_project_declarations: tuple[ExtensionCatalogAvailabilityDeclaration, ...],
    target_declarations: tuple[ExtensionCatalogAvailabilityDeclaration, ...],
    candidates: tuple[ExtensionCatalogSelectionCandidate, ...],
) -> ExtensionCatalogSelectionResult:
    result = object.__new__(ExtensionCatalogSelectionResult)
    object.__setattr__(result, "outcome", outcome)
    object.__setattr__(result, "requested_target", requested_target)
    object.__setattr__(result, "active_project", active_project)
    object.__setattr__(result, "availability", availability)
    object.__setattr__(
        result,
        "applicable_declarations",
        applicable_declarations,
    )
    object.__setattr__(
        result,
        "excluded_project_declarations",
        excluded_project_declarations,
    )
    object.__setattr__(result, "target_declarations", target_declarations)
    object.__setattr__(result, "candidates", candidates)
    object.__setattr__(
        result,
        "selected_catalog",
        candidates[0].catalog
        if outcome is ExtensionCatalogSelectionOutcome.SELECTED
        else None,
    )
    return result


def select_extension_catalog(
    availability: DeclaredExtensionCatalogAvailability,
    requested_target: ExtensionCatalogTarget,
    active_project: ProjectRoot | None = None,
) -> ExtensionCatalogSelectionResult:
    if type(availability) is not DeclaredExtensionCatalogAvailability:
        raise ValueError("catalog selection requires exact declared availability")
    if type(requested_target) is not ExtensionCatalogTarget:
        raise ValueError("catalog selection requires an exact target")
    if active_project is not None and type(active_project) is not ProjectRoot:
        raise ValueError("catalog selection requires an exact active project root")

    applicable: list[ExtensionCatalogAvailabilityDeclaration] = []
    excluded: list[ExtensionCatalogAvailabilityDeclaration] = []
    for declaration in availability.declarations:
        if declaration.owner is ExtensionCatalogAvailabilityOwner.COMPILER:
            applicable.append(declaration)
        elif active_project is not None and declaration.project == active_project:
            applicable.append(declaration)
        else:
            excluded.append(declaration)

    target_declarations = tuple(
        declaration
        for declaration in applicable
        if declaration.target == requested_target
    )
    declarations_by_identity: dict[
        ExtensionCatalogSelectionCandidateIdentity,
        list[ExtensionCatalogAvailabilityDeclaration],
    ] = {}
    for declaration in target_declarations:
        declarations_by_identity.setdefault(
            _candidate_identity(declaration.catalog),
            [],
        ).append(declaration)
    candidates = tuple(
        _new_candidate(identity, tuple(declarations_by_identity[identity]))
        for identity in sorted(declarations_by_identity, key=_candidate_sort_key)
    )

    digests_by_coordinate: dict[
        tuple[ExtensionCatalogReference, ExtensionCatalogTarget],
        set[str],
    ] = {}
    for candidate in candidates:
        digests_by_coordinate.setdefault(
            (candidate.identity.reference, candidate.identity.target),
            set(),
        ).add(candidate.identity.content_sha256)

    if not candidates:
        outcome = ExtensionCatalogSelectionOutcome.UNDECLARED
    elif any(len(digests) > 1 for digests in digests_by_coordinate.values()):
        outcome = ExtensionCatalogSelectionOutcome.CONFLICT
    elif len(candidates) > 1:
        outcome = ExtensionCatalogSelectionOutcome.AMBIGUOUS
    else:
        outcome = ExtensionCatalogSelectionOutcome.SELECTED
    return _selection_result(
        outcome,
        requested_target,
        active_project,
        availability,
        tuple(applicable),
        tuple(excluded),
        target_declarations,
        candidates,
    )
