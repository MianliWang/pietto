"""Private extension-catalog inspection and canonical representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar, cast

from pietto._project.extension_catalog_availability import (
    ExtensionCatalogAvailabilityDeclaration,
    ExtensionCatalogAvailabilityOwner,
    ExtensionCatalogSelectionCandidate,
    ExtensionCatalogSelectionOutcome,
    ExtensionCatalogSelectionResult,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderAuthority,
    ExtensionSignatureProviderContext,
    extension_signature_provider_authority,
    extension_signature_provider_inputs,
)
from pietto.semantic.capability_facts import (
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
from pietto.semantic.capability_providers import CanonicalCapabilityProviderInputs
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionAggregateCatalogEntry,
    ExtensionCastCatalogEntry,
    ExtensionCatalogCompletenessClaimKind,
    ExtensionCatalogCompletenessState,
    ExtensionCatalogDeclarationTypeUse,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogEntryEvidence,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogExactEntryGroupState,
    ExtensionCatalogExposure,
    ExtensionCatalogLookupScope,
    ExtensionCatalogMatchability,
    ExtensionCatalogReference,
    ExtensionCatalogTarget,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    ExtensionCatalogUnmodeledReason,
    ExtensionNativeTypeCatalogEntry,
    ExtensionOperatorCatalogEntry,
    ExtensionScalarFunctionCatalogEntry,
    PostgreSQLAggregateKind,
    PostgreSQLCallableDeclaration,
    PostgreSQLCallableIdentity,
    PostgreSQLCastContext,
    PostgreSQLCastIdentity,
    PostgreSQLCastMethod,
    PostgreSQLNullCallBehavior,
    PostgreSQLOperatorArity,
    PostgreSQLOperatorIdentity,
    PostgreSQLParallelSafety,
    PostgreSQLVolatility,
)
from pietto.semantic.extension_signature_requirements import (
    extension_signature_dialect_family_bridge,
)
from pietto.semantic.model import TypeKind

__all__: tuple[str, ...] = ()


class ExtensionCatalogInspectionFormat(StrEnum):
    EXTENSION_CATALOG_INSPECTION_V1 = "pietto.extension-catalog-inspection.v1"


class ExtensionCatalogInspectionLookupVariant(StrEnum):
    FOUND = "found"
    ABSENT = "absent"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class _ConstructorClosed:
    __slots__ = ()

    def __new__(cls) -> _ConstructorClosed:
        raise TypeError("Extension-catalog inspection records require derivation")


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCatalogReference(_ConstructorClosed):
    namespace: str
    name: str
    release: str


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionTarget(_ConstructorClosed):
    database_family: str
    database_release: str
    extension_identity: str
    extension_release: str


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionTypeReference(_ConstructorClosed):
    kind: ExtensionCatalogTypeReferenceKind
    logical_name: str | None
    logical_kind: TypeKind | None
    physical_name: str | None
    extension_identity: str | None


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionTypeUse(_ConstructorClosed):
    kind: ExtensionCatalogDeclarationTypeUseKind
    exact_type: ExtensionCatalogInspectionTypeReference | None
    source_spelling: str | None
    unmodeled_reasons: tuple[ExtensionCatalogUnmodeledReason, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCallableIdentity(_ConstructorClosed):
    sql_name: str
    input_types: tuple[ExtensionCatalogInspectionTypeReference, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionOperatorIdentity(_ConstructorClosed):
    operator_name: str
    arity: PostgreSQLOperatorArity
    operand_types: tuple[ExtensionCatalogInspectionTypeReference, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCastIdentity(_ConstructorClosed):
    source_type: ExtensionCatalogInspectionTypeReference
    target_type: ExtensionCatalogInspectionTypeReference


type _InspectionLookupIdentity = (
    ExtensionCatalogInspectionTypeReference
    | ExtensionCatalogInspectionCallableIdentity
    | ExtensionCatalogInspectionOperatorIdentity
    | ExtensionCatalogInspectionCastIdentity
)


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionLookupScope(_ConstructorClosed):
    family: ExtensionCatalogEntryFamily
    identity: _InspectionLookupIdentity


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCallableDeclaration(_ConstructorClosed):
    sql_name: str
    input_types: tuple[ExtensionCatalogInspectionTypeUse, ...]
    identity: ExtensionCatalogInspectionCallableIdentity | None


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionEntryEvidence(_ConstructorClosed):
    matchability: ExtensionCatalogMatchability
    exposure: ExtensionCatalogExposure
    unmodeled_reasons: tuple[ExtensionCatalogUnmodeledReason, ...]
    source_positions: tuple[int, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionNativeTypeEntry(_ConstructorClosed):
    position: int
    type_identity: ExtensionCatalogInspectionTypeReference
    logical_mapping: ExtensionCatalogInspectionTypeReference | None
    evidence: ExtensionCatalogInspectionEntryEvidence


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionScalarFunctionEntry(_ConstructorClosed):
    position: int
    declaration: ExtensionCatalogInspectionCallableDeclaration
    result_type: ExtensionCatalogInspectionTypeUse
    null_call_behavior: PostgreSQLNullCallBehavior
    volatility: PostgreSQLVolatility
    parallel_safety: PostgreSQLParallelSafety
    has_default_arguments: bool
    is_variadic: bool
    returns_set: bool
    has_polymorphic_or_pseudo_types: bool
    evidence: ExtensionCatalogInspectionEntryEvidence


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionAggregateEntry(_ConstructorClosed):
    position: int
    kind: PostgreSQLAggregateKind
    declaration: ExtensionCatalogInspectionCallableDeclaration
    result_type: ExtensionCatalogInspectionTypeUse
    parallel_safety: PostgreSQLParallelSafety
    has_direct_arguments: bool
    is_variadic: bool
    evidence: ExtensionCatalogInspectionEntryEvidence


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionOperatorEntry(_ConstructorClosed):
    position: int
    operator_name: str
    arity: PostgreSQLOperatorArity
    operand_types: tuple[ExtensionCatalogInspectionTypeUse, ...]
    identity: ExtensionCatalogInspectionOperatorIdentity | None
    result_type: ExtensionCatalogInspectionTypeUse
    evidence: ExtensionCatalogInspectionEntryEvidence


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCastEntry(_ConstructorClosed):
    position: int
    source_type: ExtensionCatalogInspectionTypeUse
    target_type: ExtensionCatalogInspectionTypeUse
    identity: ExtensionCatalogInspectionCastIdentity | None
    context: PostgreSQLCastContext
    method: PostgreSQLCastMethod
    evidence: ExtensionCatalogInspectionEntryEvidence


type _InspectionEntry = (
    ExtensionCatalogInspectionNativeTypeEntry
    | ExtensionCatalogInspectionScalarFunctionEntry
    | ExtensionCatalogInspectionAggregateEntry
    | ExtensionCatalogInspectionOperatorEntry
    | ExtensionCatalogInspectionCastEntry
)
type _CatalogEntry = (
    ExtensionNativeTypeCatalogEntry
    | ExtensionScalarFunctionCatalogEntry
    | ExtensionAggregateCatalogEntry
    | ExtensionOperatorCatalogEntry
    | ExtensionCastCatalogEntry
)


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionSourceOccurrence(_ConstructorClosed):
    position: int
    source_authority: str
    source_revision: str
    source_locator: str
    curation: str


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionExactEntryGroup(_ConstructorClosed):
    position: int
    scope: ExtensionCatalogInspectionLookupScope
    state: ExtensionCatalogExactEntryGroupState
    entry_positions: tuple[int, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCompletenessClaim(_ConstructorClosed):
    position: int
    scope: ExtensionCatalogInspectionLookupScope
    kind: ExtensionCatalogCompletenessClaimKind
    source_positions: tuple[int, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCompletenessGroup(_ConstructorClosed):
    position: int
    scope: ExtensionCatalogInspectionLookupScope
    state: ExtensionCatalogCompletenessState
    claim_positions: tuple[int, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCatalog(_ConstructorClosed):
    position: int
    reference: ExtensionCatalogInspectionCatalogReference
    target: ExtensionCatalogInspectionTarget
    content_sha256: str
    canonical_byte_length: int
    source_occurrences: tuple[ExtensionCatalogInspectionSourceOccurrence, ...]
    entries: tuple[_InspectionEntry, ...]
    exact_entry_groups: tuple[ExtensionCatalogInspectionExactEntryGroup, ...]
    completeness_claims: tuple[ExtensionCatalogInspectionCompletenessClaim, ...]
    completeness_groups: tuple[ExtensionCatalogInspectionCompletenessGroup, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionKey(_ConstructorClosed):
    domain: CapabilityDomain
    subject: str | None
    operation: str | None
    operands: tuple[str, ...]
    context: str | None
    dialect: str | None
    extension: str | None


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCapabilityEvidence(_ConstructorClosed):
    source: CapabilityEvidenceSource
    source_path: str
    source_reference: str
    reason: CapabilityReasonCode | None
    dialect: str | None
    backend: str | None
    extension: str | None


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionCapabilityFact(_ConstructorClosed):
    key: ExtensionCatalogInspectionKey
    support: CapabilitySupport
    disposition_kind: CapabilityDispositionKind
    disposition_owner: str | None
    disposition_reason: str | None
    evidence: tuple[ExtensionCatalogInspectionCapabilityEvidence, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionAvailabilityDeclaration(_ConstructorClosed):
    position: int
    owner: ExtensionCatalogAvailabilityOwner
    project_path: str | None
    catalog_position: int
    reference: ExtensionCatalogInspectionCatalogReference
    target: ExtensionCatalogInspectionTarget
    content_sha256: str


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionSelectionCandidate(_ConstructorClosed):
    catalog_position: int
    reference: ExtensionCatalogInspectionCatalogReference
    target: ExtensionCatalogInspectionTarget
    content_sha256: str
    declaration_positions: tuple[int, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionSelection(_ConstructorClosed):
    requested_target: ExtensionCatalogInspectionTarget
    active_project_path: str | None
    outcome: ExtensionCatalogSelectionOutcome
    availability: tuple[ExtensionCatalogInspectionAvailabilityDeclaration, ...]
    applicable_declaration_positions: tuple[int, ...]
    excluded_project_declaration_positions: tuple[int, ...]
    target_declaration_positions: tuple[int, ...]
    candidates: tuple[ExtensionCatalogInspectionSelectionCandidate, ...]
    selected_catalog_position: int | None


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionProviderInputs(_ConstructorClosed):
    key: ExtensionCatalogInspectionKey
    domain_complete: bool
    unknown_reason: CapabilityReasonCode | None
    facts: tuple[ExtensionCatalogInspectionCapabilityFact, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionLookup(_ConstructorClosed):
    variant: ExtensionCatalogInspectionLookupVariant
    reason: CapabilityReasonCode | None
    facts: tuple[ExtensionCatalogInspectionCapabilityFact, ...]


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspectionProviderOccurrence(_ConstructorClosed):
    requirement_position: int
    key: ExtensionCatalogInspectionKey
    selector_scope: ExtensionCatalogInspectionLookupScope
    bridged_database_family: str
    selection: ExtensionCatalogInspectionSelection
    selected_catalog_position: int | None
    exact_group_position: int | None
    unmodeled_blocker_entry_positions: tuple[int, ...]
    completeness_group_position: int | None
    provider_inputs: ExtensionCatalogInspectionProviderInputs
    lookup: ExtensionCatalogInspectionLookup


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogInspection(_ConstructorClosed):
    format: ExtensionCatalogInspectionFormat
    requirement_namespace: str
    requirement_name: str
    catalogs: tuple[ExtensionCatalogInspectionCatalog, ...]
    provider_occurrences: tuple[ExtensionCatalogInspectionProviderOccurrence, ...]
    context: ExtensionSignatureProviderContext = field(
        repr=False,
        compare=False,
        hash=False,
    )


_Derived = TypeVar("_Derived")


def _derived(carrier: type[_Derived], /, **attributes: object) -> _Derived:
    result = object.__new__(carrier)
    for name, value in attributes.items():
        object.__setattr__(result, name, value)
    return cast(_Derived, result)


def _project_reference(
    reference: ExtensionCatalogReference,
) -> ExtensionCatalogInspectionCatalogReference:
    return _derived(
        ExtensionCatalogInspectionCatalogReference,
        namespace=reference.identity.namespace,
        name=reference.identity.name,
        release=reference.release,
    )


def _project_target(target: ExtensionCatalogTarget) -> ExtensionCatalogInspectionTarget:
    return _derived(
        ExtensionCatalogInspectionTarget,
        database_family=target.database_family,
        database_release=target.database_release,
        extension_identity=target.extension_identity,
        extension_release=target.extension_release,
    )


def _project_type_reference(
    reference: ExtensionCatalogTypeReference,
) -> ExtensionCatalogInspectionTypeReference:
    logical = reference.logical_type
    return _derived(
        ExtensionCatalogInspectionTypeReference,
        kind=reference.kind,
        logical_name=None if logical is None else logical.name,
        logical_kind=None if logical is None else logical.kind,
        physical_name=reference.physical_name,
        extension_identity=reference.extension_identity,
    )


def _project_type_use(
    type_use: ExtensionCatalogDeclarationTypeUse,
) -> ExtensionCatalogInspectionTypeUse:
    return _derived(
        ExtensionCatalogInspectionTypeUse,
        kind=type_use.kind,
        exact_type=(
            None
            if type_use.exact_type is None
            else _project_type_reference(type_use.exact_type)
        ),
        source_spelling=type_use.source_spelling,
        unmodeled_reasons=type_use.unmodeled_reasons,
    )


def _project_callable_identity(
    identity: PostgreSQLCallableIdentity,
) -> ExtensionCatalogInspectionCallableIdentity:
    return _derived(
        ExtensionCatalogInspectionCallableIdentity,
        sql_name=identity.sql_name,
        input_types=tuple(
            _project_type_reference(reference) for reference in identity.input_types
        ),
    )


def _project_operator_identity(
    identity: PostgreSQLOperatorIdentity,
) -> ExtensionCatalogInspectionOperatorIdentity:
    return _derived(
        ExtensionCatalogInspectionOperatorIdentity,
        operator_name=identity.operator_name,
        arity=identity.arity,
        operand_types=tuple(
            _project_type_reference(reference) for reference in identity.operand_types
        ),
    )


def _project_cast_identity(
    identity: PostgreSQLCastIdentity,
) -> ExtensionCatalogInspectionCastIdentity:
    return _derived(
        ExtensionCatalogInspectionCastIdentity,
        source_type=_project_type_reference(identity.source_type),
        target_type=_project_type_reference(identity.target_type),
    )


def _project_scope(
    scope: ExtensionCatalogLookupScope,
) -> ExtensionCatalogInspectionLookupScope:
    identity = scope.identity
    if isinstance(identity, ExtensionCatalogTypeReference):
        projected: _InspectionLookupIdentity = _project_type_reference(identity)
    elif isinstance(identity, PostgreSQLCallableIdentity):
        projected = _project_callable_identity(identity)
    elif isinstance(identity, PostgreSQLOperatorIdentity):
        projected = _project_operator_identity(identity)
    elif isinstance(identity, PostgreSQLCastIdentity):
        projected = _project_cast_identity(identity)
    else:
        raise TypeError("Inspection requires an exact lookup identity")
    return _derived(
        ExtensionCatalogInspectionLookupScope,
        family=scope.family,
        identity=projected,
    )


def _project_declaration(
    declaration: PostgreSQLCallableDeclaration,
) -> ExtensionCatalogInspectionCallableDeclaration:
    return _derived(
        ExtensionCatalogInspectionCallableDeclaration,
        sql_name=declaration.sql_name,
        input_types=tuple(
            _project_type_use(type_use) for type_use in declaration.input_types
        ),
        identity=(
            None
            if declaration.identity is None
            else _project_callable_identity(declaration.identity)
        ),
    )


def _project_entry_evidence(
    evidence: ExtensionCatalogEntryEvidence,
) -> ExtensionCatalogInspectionEntryEvidence:
    return _derived(
        ExtensionCatalogInspectionEntryEvidence,
        matchability=evidence.matchability,
        exposure=evidence.exposure,
        unmodeled_reasons=evidence.unmodeled_reasons,
        source_positions=evidence.source_positions,
    )


def _project_entry(position: int, entry: _CatalogEntry) -> _InspectionEntry:
    evidence = _project_entry_evidence(entry.evidence)
    if isinstance(entry, ExtensionNativeTypeCatalogEntry):
        return _derived(
            ExtensionCatalogInspectionNativeTypeEntry,
            position=position,
            type_identity=_project_type_reference(entry.type_identity),
            logical_mapping=(
                None
                if entry.logical_mapping is None
                else _project_type_reference(entry.logical_mapping)
            ),
            evidence=evidence,
        )
    if isinstance(entry, ExtensionScalarFunctionCatalogEntry):
        return _derived(
            ExtensionCatalogInspectionScalarFunctionEntry,
            position=position,
            declaration=_project_declaration(entry.declaration),
            result_type=_project_type_use(entry.result_type),
            null_call_behavior=entry.null_call_behavior,
            volatility=entry.volatility,
            parallel_safety=entry.parallel_safety,
            has_default_arguments=entry.has_default_arguments,
            is_variadic=entry.is_variadic,
            returns_set=entry.returns_set,
            has_polymorphic_or_pseudo_types=entry.has_polymorphic_or_pseudo_types,
            evidence=evidence,
        )
    if isinstance(entry, ExtensionAggregateCatalogEntry):
        return _derived(
            ExtensionCatalogInspectionAggregateEntry,
            position=position,
            kind=entry.kind,
            declaration=_project_declaration(entry.declaration),
            result_type=_project_type_use(entry.result_type),
            parallel_safety=entry.parallel_safety,
            has_direct_arguments=entry.has_direct_arguments,
            is_variadic=entry.is_variadic,
            evidence=evidence,
        )
    if isinstance(entry, ExtensionOperatorCatalogEntry):
        return _derived(
            ExtensionCatalogInspectionOperatorEntry,
            position=position,
            operator_name=entry.operator_name,
            arity=entry.arity,
            operand_types=tuple(
                _project_type_use(type_use) for type_use in entry.operand_types
            ),
            identity=(
                None
                if entry.identity is None
                else _project_operator_identity(entry.identity)
            ),
            result_type=_project_type_use(entry.result_type),
            evidence=evidence,
        )
    if isinstance(entry, ExtensionCastCatalogEntry):
        return _derived(
            ExtensionCatalogInspectionCastEntry,
            position=position,
            source_type=_project_type_use(entry.source_type),
            target_type=_project_type_use(entry.target_type),
            identity=(
                None
                if entry.identity is None
                else _project_cast_identity(entry.identity)
            ),
            context=entry.context,
            method=entry.method,
            evidence=evidence,
        )
    raise TypeError("Inspection requires one exact catalog entry family")


def _occurrence_positions(
    values: tuple[object, ...],
    members: tuple[object, ...],
) -> tuple[int, ...]:
    used: set[int] = set()
    positions: list[int] = []
    for member in members:
        position = next(
            (
                candidate_position
                for candidate_position, candidate in enumerate(values)
                if candidate_position not in used and candidate is member
            ),
            None,
        )
        if position is None:
            raise ValueError("Inspection member is foreign to its catalog authority")
        used.add(position)
        positions.append(position)
    return tuple(positions)


def _project_catalog(
    position: int,
    catalog: ConstructedExtensionCatalog,
) -> ExtensionCatalogInspectionCatalog:
    entries = cast(tuple[object, ...], catalog.entries)
    claims = cast(tuple[object, ...], catalog.completeness_claims)
    return _derived(
        ExtensionCatalogInspectionCatalog,
        position=position,
        reference=_project_reference(catalog.metadata.catalog),
        target=_project_target(catalog.metadata.target),
        content_sha256=catalog.content_sha256,
        canonical_byte_length=len(catalog.canonical_bytes),
        source_occurrences=tuple(
            _derived(
                ExtensionCatalogInspectionSourceOccurrence,
                position=occurrence.position,
                source_authority=occurrence.provenance.source_authority,
                source_revision=occurrence.provenance.source_revision,
                source_locator=occurrence.provenance.source_locator,
                curation=occurrence.provenance.curation,
            )
            for occurrence in catalog.metadata.source_occurrences
        ),
        entries=tuple(
            _project_entry(entry_position, entry)
            for entry_position, entry in enumerate(catalog.entries)
        ),
        exact_entry_groups=tuple(
            _derived(
                ExtensionCatalogInspectionExactEntryGroup,
                position=group_position,
                scope=_project_scope(group.scope),
                state=group.state,
                entry_positions=_occurrence_positions(
                    entries,
                    cast(tuple[object, ...], group.entries),
                ),
            )
            for group_position, group in enumerate(catalog.exact_entry_groups)
        ),
        completeness_claims=tuple(
            _derived(
                ExtensionCatalogInspectionCompletenessClaim,
                position=claim_position,
                scope=_project_scope(claim.scope),
                kind=claim.kind,
                source_positions=claim.source_positions,
            )
            for claim_position, claim in enumerate(catalog.completeness_claims)
        ),
        completeness_groups=tuple(
            _derived(
                ExtensionCatalogInspectionCompletenessGroup,
                position=group_position,
                scope=_project_scope(group.scope),
                state=group.state,
                claim_positions=_occurrence_positions(
                    claims,
                    cast(tuple[object, ...], group.claims),
                ),
            )
            for group_position, group in enumerate(catalog.completeness_groups)
        ),
    )


def _catalog_key(catalog: ConstructedExtensionCatalog) -> tuple[str, ...]:
    reference = catalog.metadata.catalog
    target = catalog.metadata.target
    return (
        reference.identity.namespace,
        reference.identity.name,
        reference.release,
        target.database_family,
        target.database_release,
        target.extension_identity,
        target.extension_release,
        catalog.content_sha256,
    )


def _reachable_catalogs(
    context: ExtensionSignatureProviderContext,
) -> tuple[ConstructedExtensionCatalog, ...]:
    by_key: dict[tuple[str, ...], ConstructedExtensionCatalog] = {}
    for occurrence in context.selections:
        selection = occurrence.selection
        for declaration in selection.availability.declarations:
            by_key.setdefault(_catalog_key(declaration.catalog), declaration.catalog)
        for candidate in selection.candidates:
            by_key.setdefault(_catalog_key(candidate.catalog), candidate.catalog)
        if selection.selected_catalog is not None:
            by_key.setdefault(
                _catalog_key(selection.selected_catalog),
                selection.selected_catalog,
            )
    return tuple(by_key[key] for key in sorted(by_key))


def _project_key(key: CapabilityKey) -> ExtensionCatalogInspectionKey:
    return _derived(
        ExtensionCatalogInspectionKey,
        domain=key.domain,
        subject=key.subject,
        operation=key.operation,
        operands=key.operands,
        context=key.context,
        dialect=key.dialect,
        extension=key.extension,
    )


def _project_capability_evidence(
    evidence: CapabilityEvidence,
) -> ExtensionCatalogInspectionCapabilityEvidence:
    return _derived(
        ExtensionCatalogInspectionCapabilityEvidence,
        source=evidence.source,
        source_path=evidence.source_path,
        source_reference=evidence.source_reference,
        reason=evidence.reason,
        dialect=evidence.dialect,
        backend=evidence.backend,
        extension=evidence.extension,
    )


def _project_fact(fact: CapabilityFact) -> ExtensionCatalogInspectionCapabilityFact:
    return _derived(
        ExtensionCatalogInspectionCapabilityFact,
        key=_project_key(fact.key),
        support=fact.support,
        disposition_kind=fact.disposition.kind,
        disposition_owner=fact.disposition.owner,
        disposition_reason=fact.disposition.reason,
        evidence=tuple(
            _project_capability_evidence(evidence) for evidence in fact.evidence
        ),
    )


def _project_provider_inputs(
    inputs: CanonicalCapabilityProviderInputs,
) -> ExtensionCatalogInspectionProviderInputs:
    return _derived(
        ExtensionCatalogInspectionProviderInputs,
        key=_project_key(inputs.key),
        domain_complete=inputs.domain_complete,
        unknown_reason=inputs.unknown_reason,
        facts=tuple(_project_fact(fact) for fact in inputs.facts),
    )


def _project_lookup(
    result: Found | Absent | Unknown | Conflict,
) -> ExtensionCatalogInspectionLookup:
    if type(result) is Found:
        variant = ExtensionCatalogInspectionLookupVariant.FOUND
        reason = None
        facts = (_project_fact(result.fact),)
    elif type(result) is Absent:
        variant = ExtensionCatalogInspectionLookupVariant.ABSENT
        reason = result.reason
        facts = ()
    elif type(result) is Unknown:
        variant = ExtensionCatalogInspectionLookupVariant.UNKNOWN
        reason = result.reason
        facts = ()
    elif type(result) is Conflict:
        variant = ExtensionCatalogInspectionLookupVariant.CONFLICT
        reason = result.reason
        facts = tuple(_project_fact(fact) for fact in result.evidence)
    else:
        raise TypeError("Inspection requires an exact capability lookup result")
    return _derived(
        ExtensionCatalogInspectionLookup,
        variant=variant,
        reason=reason,
        facts=facts,
    )


def _catalog_position(
    catalog_positions: dict[tuple[str, ...], int],
    catalog: ConstructedExtensionCatalog,
) -> int:
    return catalog_positions[_catalog_key(catalog)]


def _project_availability_declaration(
    declaration: ExtensionCatalogAvailabilityDeclaration,
    catalog_positions: dict[tuple[str, ...], int],
) -> ExtensionCatalogInspectionAvailabilityDeclaration:
    return _derived(
        ExtensionCatalogInspectionAvailabilityDeclaration,
        position=declaration.position,
        owner=declaration.owner,
        project_path=None if declaration.project is None else declaration.project.path,
        catalog_position=_catalog_position(catalog_positions, declaration.catalog),
        reference=_project_reference(declaration.reference),
        target=_project_target(declaration.target),
        content_sha256=declaration.content_sha256,
    )


def _project_candidate(
    candidate: ExtensionCatalogSelectionCandidate,
    catalog_positions: dict[tuple[str, ...], int],
) -> ExtensionCatalogInspectionSelectionCandidate:
    return _derived(
        ExtensionCatalogInspectionSelectionCandidate,
        catalog_position=_catalog_position(catalog_positions, candidate.catalog),
        reference=_project_reference(candidate.identity.reference),
        target=_project_target(candidate.identity.target),
        content_sha256=candidate.identity.content_sha256,
        declaration_positions=tuple(
            declaration.position for declaration in candidate.declarations
        ),
    )


def _project_selection(
    selection: ExtensionCatalogSelectionResult,
    catalog_positions: dict[tuple[str, ...], int],
) -> ExtensionCatalogInspectionSelection:
    return _derived(
        ExtensionCatalogInspectionSelection,
        requested_target=_project_target(selection.requested_target),
        active_project_path=(
            None if selection.active_project is None else selection.active_project.path
        ),
        outcome=selection.outcome,
        availability=tuple(
            _project_availability_declaration(declaration, catalog_positions)
            for declaration in selection.availability.declarations
        ),
        applicable_declaration_positions=tuple(
            declaration.position for declaration in selection.applicable_declarations
        ),
        excluded_project_declaration_positions=tuple(
            declaration.position
            for declaration in selection.excluded_project_declarations
        ),
        target_declaration_positions=tuple(
            declaration.position for declaration in selection.target_declarations
        ),
        candidates=tuple(
            _project_candidate(candidate, catalog_positions)
            for candidate in selection.candidates
        ),
        selected_catalog_position=(
            None
            if selection.selected_catalog is None
            else _catalog_position(catalog_positions, selection.selected_catalog)
        ),
    )


def _authority_group_position(
    authority: ExtensionSignatureProviderAuthority,
) -> int | None:
    group = authority.exact_group
    catalog = authority.selected_catalog
    if group is None:
        return None
    if catalog is None:
        raise ValueError("Exact provider group requires a selected catalog")
    position = next(
        (
            position
            for position, candidate in enumerate(catalog.exact_entry_groups)
            if candidate is group
        ),
        None,
    )
    if position is None:
        raise ValueError("Exact provider group is foreign to the selected catalog")
    return position


def _authority_completeness_position(
    authority: ExtensionSignatureProviderAuthority,
) -> int | None:
    group = authority.completeness_group
    catalog = authority.selected_catalog
    if group is None:
        return None
    if catalog is None:
        raise ValueError("Completeness provider group requires a selected catalog")
    position = next(
        (
            position
            for position, candidate in enumerate(catalog.completeness_groups)
            if candidate is group
        ),
        None,
    )
    if position is None:
        raise ValueError(
            "Completeness provider group is foreign to the selected catalog"
        )
    return position


def _project_provider_occurrence(
    context: ExtensionSignatureProviderContext,
    occurrence_position: int,
    catalog_positions: dict[tuple[str, ...], int],
) -> ExtensionCatalogInspectionProviderOccurrence:
    selector_occurrence = context.selectors.occurrences[occurrence_position]
    selection_occurrence = context.selections[occurrence_position]
    requirement = context.selectors.requirements.occurrences[
        selector_occurrence.requirement_position
    ]
    authority = extension_signature_provider_authority(context, requirement)
    inputs = extension_signature_provider_inputs(authority)
    result = lookup_capability(
        inputs.key,
        inputs.facts,
        domain_complete=inputs.domain_complete,
        unknown_reason=inputs.unknown_reason,
    )
    bridge = extension_signature_dialect_family_bridge(requirement.key.dialect)
    if bridge is None:
        raise ValueError("Inspected selector requires the frozen dialect bridge")
    catalog = authority.selected_catalog
    blockers = cast(tuple[object, ...], authority.unmodeled_blockers)
    return _derived(
        ExtensionCatalogInspectionProviderOccurrence,
        requirement_position=requirement.position,
        key=_project_key(requirement.key),
        selector_scope=_project_scope(selector_occurrence.selector.scope),
        bridged_database_family=bridge.database_family,
        selection=_project_selection(selection_occurrence.selection, catalog_positions),
        selected_catalog_position=(
            None if catalog is None else _catalog_position(catalog_positions, catalog)
        ),
        exact_group_position=_authority_group_position(authority),
        unmodeled_blocker_entry_positions=(
            ()
            if catalog is None
            else _occurrence_positions(
                cast(tuple[object, ...], catalog.entries),
                blockers,
            )
        ),
        completeness_group_position=_authority_completeness_position(authority),
        provider_inputs=_project_provider_inputs(inputs),
        lookup=_project_lookup(result),
    )


def _derive_inspection(
    context: ExtensionSignatureProviderContext,
) -> ExtensionCatalogInspection:
    if type(context) is not ExtensionSignatureProviderContext:
        raise TypeError(
            "Extension-catalog inspection requires an exact provider context"
        )
    artifacts = _reachable_catalogs(context)
    catalog_positions = {
        _catalog_key(catalog): position for position, catalog in enumerate(artifacts)
    }
    identity = context.selectors.requirements.identity
    return _derived(
        ExtensionCatalogInspection,
        format=ExtensionCatalogInspectionFormat.EXTENSION_CATALOG_INSPECTION_V1,
        requirement_namespace=identity.namespace,
        requirement_name=identity.name,
        catalogs=tuple(
            _project_catalog(position, catalog)
            for position, catalog in enumerate(artifacts)
        ),
        provider_occurrences=tuple(
            _project_provider_occurrence(context, position, catalog_positions)
            for position in range(len(context.selectors.occurrences))
        ),
        context=context,
    )


def _frame(payload: bytes) -> bytes:
    return len(payload).to_bytes(8, "big") + payload


def _encode_inspection_value(value: object) -> bytes:
    if value is None:
        return b"n"
    if type(value) is bool:
        return b"b1" if value else b"b0"
    if type(value) is int:
        if value < 0:
            raise ValueError("Canonical inspection integers must be non-negative")
        return b"i" + _frame(str(value).encode("ascii"))
    if isinstance(value, StrEnum):
        return (
            b"e"
            + _frame(type(value).__qualname__.encode("utf-8"))
            + _frame(value.value.encode("utf-8"))
        )
    if type(value) is str:
        return b"s" + _frame(value.encode("utf-8"))
    if type(value) is tuple:
        return (
            b"t"
            + len(value).to_bytes(8, "big")
            + b"".join(_frame(_encode_inspection_value(item)) for item in value)
        )
    raise TypeError("Inspection canonical encoding received an unsupported value")


def _reference_value(
    reference: ExtensionCatalogInspectionCatalogReference,
) -> tuple[object, ...]:
    return ("reference", reference.namespace, reference.name, reference.release)


def _target_value(target: ExtensionCatalogInspectionTarget) -> tuple[object, ...]:
    return (
        "target",
        target.database_family,
        target.database_release,
        target.extension_identity,
        target.extension_release,
    )


def _type_reference_value(
    reference: ExtensionCatalogInspectionTypeReference,
) -> tuple[object, ...]:
    return (
        "type_reference",
        reference.kind,
        reference.logical_name,
        reference.logical_kind,
        reference.physical_name,
        reference.extension_identity,
    )


def _type_use_value(
    type_use: ExtensionCatalogInspectionTypeUse,
) -> tuple[object, ...]:
    return (
        "type_use",
        type_use.kind,
        (
            None
            if type_use.exact_type is None
            else _type_reference_value(type_use.exact_type)
        ),
        type_use.source_spelling,
        type_use.unmodeled_reasons,
    )


def _identity_value(identity: _InspectionLookupIdentity) -> tuple[object, ...]:
    if isinstance(identity, ExtensionCatalogInspectionTypeReference):
        return _type_reference_value(identity)
    if isinstance(identity, ExtensionCatalogInspectionCallableIdentity):
        return (
            "callable_identity",
            identity.sql_name,
            tuple(_type_reference_value(item) for item in identity.input_types),
        )
    if isinstance(identity, ExtensionCatalogInspectionOperatorIdentity):
        return (
            "operator_identity",
            identity.operator_name,
            identity.arity,
            tuple(_type_reference_value(item) for item in identity.operand_types),
        )
    if isinstance(identity, ExtensionCatalogInspectionCastIdentity):
        return (
            "cast_identity",
            _type_reference_value(identity.source_type),
            _type_reference_value(identity.target_type),
        )
    raise TypeError("Inspection encoding requires a typed lookup identity")


def _scope_value(
    scope: ExtensionCatalogInspectionLookupScope,
) -> tuple[object, ...]:
    return ("scope", scope.family, _identity_value(scope.identity))


def _declaration_value(
    declaration: ExtensionCatalogInspectionCallableDeclaration,
) -> tuple[object, ...]:
    return (
        "declaration",
        declaration.sql_name,
        tuple(_type_use_value(item) for item in declaration.input_types),
        (
            None
            if declaration.identity is None
            else _identity_value(declaration.identity)
        ),
    )


def _entry_evidence_value(
    evidence: ExtensionCatalogInspectionEntryEvidence,
) -> tuple[object, ...]:
    return (
        "entry_evidence",
        evidence.matchability,
        evidence.exposure,
        evidence.unmodeled_reasons,
        evidence.source_positions,
    )


def _entry_value(entry: _InspectionEntry) -> tuple[object, ...]:
    if isinstance(entry, ExtensionCatalogInspectionNativeTypeEntry):
        return (
            "native_type_entry",
            entry.position,
            _type_reference_value(entry.type_identity),
            (
                None
                if entry.logical_mapping is None
                else _type_reference_value(entry.logical_mapping)
            ),
            _entry_evidence_value(entry.evidence),
        )
    if isinstance(entry, ExtensionCatalogInspectionScalarFunctionEntry):
        return (
            "scalar_function_entry",
            entry.position,
            _declaration_value(entry.declaration),
            _type_use_value(entry.result_type),
            entry.null_call_behavior,
            entry.volatility,
            entry.parallel_safety,
            entry.has_default_arguments,
            entry.is_variadic,
            entry.returns_set,
            entry.has_polymorphic_or_pseudo_types,
            _entry_evidence_value(entry.evidence),
        )
    if isinstance(entry, ExtensionCatalogInspectionAggregateEntry):
        return (
            "aggregate_entry",
            entry.position,
            entry.kind,
            _declaration_value(entry.declaration),
            _type_use_value(entry.result_type),
            entry.parallel_safety,
            entry.has_direct_arguments,
            entry.is_variadic,
            _entry_evidence_value(entry.evidence),
        )
    if isinstance(entry, ExtensionCatalogInspectionOperatorEntry):
        return (
            "operator_entry",
            entry.position,
            entry.operator_name,
            entry.arity,
            tuple(_type_use_value(item) for item in entry.operand_types),
            None if entry.identity is None else _identity_value(entry.identity),
            _type_use_value(entry.result_type),
            _entry_evidence_value(entry.evidence),
        )
    if isinstance(entry, ExtensionCatalogInspectionCastEntry):
        return (
            "cast_entry",
            entry.position,
            _type_use_value(entry.source_type),
            _type_use_value(entry.target_type),
            None if entry.identity is None else _identity_value(entry.identity),
            entry.context,
            entry.method,
            _entry_evidence_value(entry.evidence),
        )
    raise TypeError("Inspection encoding requires one exact entry family")


def _catalog_value(
    catalog: ExtensionCatalogInspectionCatalog,
) -> tuple[object, ...]:
    return (
        "catalog",
        catalog.position,
        _reference_value(catalog.reference),
        _target_value(catalog.target),
        catalog.content_sha256,
        catalog.canonical_byte_length,
        tuple(
            (
                "source",
                source.position,
                source.source_authority,
                source.source_revision,
                source.source_locator,
                source.curation,
            )
            for source in catalog.source_occurrences
        ),
        tuple(_entry_value(entry) for entry in catalog.entries),
        tuple(
            (
                "exact_group",
                group.position,
                _scope_value(group.scope),
                group.state,
                group.entry_positions,
            )
            for group in catalog.exact_entry_groups
        ),
        tuple(
            (
                "completeness_claim",
                claim.position,
                _scope_value(claim.scope),
                claim.kind,
                claim.source_positions,
            )
            for claim in catalog.completeness_claims
        ),
        tuple(
            (
                "completeness_group",
                group.position,
                _scope_value(group.scope),
                group.state,
                group.claim_positions,
            )
            for group in catalog.completeness_groups
        ),
    )


def _key_value(key: ExtensionCatalogInspectionKey) -> tuple[object, ...]:
    return (
        "key",
        key.domain,
        key.subject,
        key.operation,
        key.operands,
        key.context,
        key.dialect,
        key.extension,
    )


def _fact_value(
    fact: ExtensionCatalogInspectionCapabilityFact,
) -> tuple[object, ...]:
    return (
        "fact",
        _key_value(fact.key),
        fact.support,
        fact.disposition_kind,
        fact.disposition_owner,
        fact.disposition_reason,
        tuple(
            (
                "capability_evidence",
                evidence.source,
                evidence.source_path,
                evidence.source_reference,
                evidence.reason,
                evidence.dialect,
                evidence.backend,
                evidence.extension,
            )
            for evidence in fact.evidence
        ),
    )


def _selection_value(
    selection: ExtensionCatalogInspectionSelection,
) -> tuple[object, ...]:
    return (
        "selection",
        _target_value(selection.requested_target),
        selection.active_project_path,
        selection.outcome,
        tuple(
            (
                "availability",
                declaration.position,
                declaration.owner,
                declaration.project_path,
                declaration.catalog_position,
                _reference_value(declaration.reference),
                _target_value(declaration.target),
                declaration.content_sha256,
            )
            for declaration in selection.availability
        ),
        selection.applicable_declaration_positions,
        selection.excluded_project_declaration_positions,
        selection.target_declaration_positions,
        tuple(
            (
                "candidate",
                candidate.catalog_position,
                _reference_value(candidate.reference),
                _target_value(candidate.target),
                candidate.content_sha256,
                candidate.declaration_positions,
            )
            for candidate in selection.candidates
        ),
        selection.selected_catalog_position,
    )


def _provider_occurrence_value(
    occurrence: ExtensionCatalogInspectionProviderOccurrence,
) -> tuple[object, ...]:
    return (
        "provider_occurrence",
        occurrence.requirement_position,
        _key_value(occurrence.key),
        _scope_value(occurrence.selector_scope),
        occurrence.bridged_database_family,
        _selection_value(occurrence.selection),
        occurrence.selected_catalog_position,
        occurrence.exact_group_position,
        occurrence.unmodeled_blocker_entry_positions,
        occurrence.completeness_group_position,
        (
            "provider_inputs",
            _key_value(occurrence.provider_inputs.key),
            occurrence.provider_inputs.domain_complete,
            occurrence.provider_inputs.unknown_reason,
            tuple(_fact_value(fact) for fact in occurrence.provider_inputs.facts),
        ),
        (
            "lookup",
            occurrence.lookup.variant,
            occurrence.lookup.reason,
            tuple(_fact_value(fact) for fact in occurrence.lookup.facts),
        ),
    )


def _serialize_extension_catalog_inspection(
    inspection: ExtensionCatalogInspection,
) -> bytes:
    return _encode_inspection_value(
        (
            "extension_catalog_inspection",
            inspection.format,
            inspection.requirement_namespace,
            inspection.requirement_name,
            tuple(_catalog_value(catalog) for catalog in inspection.catalogs),
            tuple(
                _provider_occurrence_value(occurrence)
                for occurrence in inspection.provider_occurrences
            ),
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class _ExtensionCatalogInspectionAuthority:
    context: ExtensionSignatureProviderContext = field(
        repr=False,
        compare=False,
        hash=False,
    )
    inspection: ExtensionCatalogInspection = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    canonical_bytes: bytes = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        inspection = _derive_inspection(self.context)
        object.__setattr__(self, "inspection", inspection)
        object.__setattr__(
            self,
            "canonical_bytes",
            _serialize_extension_catalog_inspection(inspection),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionCatalogInspectionFactSet:
    inspection: ExtensionCatalogInspection
    canonical_bytes: bytes
    authority: _ExtensionCatalogInspectionAuthority = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.authority) is not _ExtensionCatalogInspectionAuthority:
            raise TypeError(
                "Extension-catalog inspection facts require exact authority"
            )
        if self.inspection is not self.authority.inspection:
            raise ValueError(
                "Extension-catalog inspection rejects a grafted projection"
            )
        if self.canonical_bytes is not self.authority.canonical_bytes:
            raise ValueError("Extension-catalog inspection rejects grafted bytes")
        if self.inspection.context is not self.authority.context:
            raise ValueError("Extension-catalog inspection rejects a foreign context")


def build_extension_catalog_inspection(
    context: ExtensionSignatureProviderContext,
) -> ExtensionCatalogInspectionFactSet:
    """Project one exact provider context without selection or provider changes."""

    authority = _ExtensionCatalogInspectionAuthority(context=context)
    return ExtensionCatalogInspectionFactSet(
        inspection=authority.inspection,
        canonical_bytes=authority.canonical_bytes,
        authority=authority,
    )
