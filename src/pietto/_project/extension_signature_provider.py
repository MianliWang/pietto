"""Private target-scoped extension-signature capability provider."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass

from pietto._project.extension_catalog_availability import (
    ExtensionCatalogSelectionCandidate,
    ExtensionCatalogSelectionCandidateIdentity,
    ExtensionCatalogSelectionOutcome,
    ExtensionCatalogSelectionResult,
)
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
from pietto.semantic.capability_profiles import CapabilityRequirementOccurrence
from pietto.semantic.capability_providers import CanonicalCapabilityProviderInputs
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionAggregateCatalogEntry,
    ExtensionCastCatalogEntry,
    ExtensionCatalogCompletenessGroup,
    ExtensionCatalogCompletenessState,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogExactEntryGroup,
    ExtensionCatalogExactEntryGroupState,
    ExtensionCatalogExposure,
    ExtensionCatalogLookupScope,
    ExtensionCatalogMatchability,
    ExtensionCatalogTarget,
    ExtensionNativeTypeCatalogEntry,
    ExtensionOperatorCatalogEntry,
    ExtensionScalarFunctionCatalogEntry,
    PostgreSQLCallableIdentity,
    PostgreSQLCastIdentity,
    PostgreSQLOperatorIdentity,
    _entry_family,
)
from pietto.semantic.extension_signature_requirements import (
    ExtensionSignatureRequirementSelectorOccurrence,
    ExtensionSignatureRequirementSelectors,
    extension_signature_dialect_family_bridge,
)

__all__: tuple[str, ...] = ()

type _CatalogEntry = (
    ExtensionNativeTypeCatalogEntry
    | ExtensionScalarFunctionCatalogEntry
    | ExtensionAggregateCatalogEntry
    | ExtensionOperatorCatalogEntry
    | ExtensionCastCatalogEntry
)


def _freeze_selection_occurrences(
    values: Iterable[ExtensionSignatureProviderSelectionOccurrence],
) -> tuple[ExtensionSignatureProviderSelectionOccurrence, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError("extension provider selections require an ordered iterable")
    try:
        occurrences = tuple(values)
    except TypeError as exc:
        raise ValueError(
            "extension provider selections require an ordered iterable"
        ) from exc
    if any(
        type(occurrence) is not ExtensionSignatureProviderSelectionOccurrence
        for occurrence in occurrences
    ):
        raise ValueError("extension provider selections require exact occurrences")
    return occurrences


def _validate_selection_result(selection: ExtensionCatalogSelectionResult) -> None:
    if type(selection) is not ExtensionCatalogSelectionResult:
        raise ValueError("extension provider requires an exact catalog selection")
    if type(selection.outcome) is not ExtensionCatalogSelectionOutcome:
        raise ValueError("extension provider selection requires an exact outcome")
    if type(selection.requested_target) is not ExtensionCatalogTarget:
        raise ValueError("extension provider selection requires an exact target")
    if type(selection.candidates) is not tuple or any(
        type(candidate) is not ExtensionCatalogSelectionCandidate
        for candidate in selection.candidates
    ):
        raise ValueError("extension provider selection has invalid candidates")
    for candidate in selection.candidates:
        if (
            type(candidate.identity) is not ExtensionCatalogSelectionCandidateIdentity
            or type(candidate.catalog) is not ConstructedExtensionCatalog
            or candidate.identity.target != selection.requested_target
            or candidate.catalog.metadata.target != selection.requested_target
        ):
            raise ValueError("extension provider candidate target authority disagrees")
    selected = selection.selected_catalog
    if selection.outcome is ExtensionCatalogSelectionOutcome.SELECTED:
        if (
            type(selected) is not ConstructedExtensionCatalog
            or selected.metadata.target != selection.requested_target
            or not any(
                candidate.catalog is selected for candidate in selection.candidates
            )
        ):
            raise ValueError("extension provider selected target authority disagrees")
    elif selected is not None:
        raise ValueError("unselected extension provider authority forbids a catalog")


@dataclass(frozen=True, slots=True)
class ExtensionSignatureProviderSelectionOccurrence:
    requirement_position: int
    selection: ExtensionCatalogSelectionResult

    def __post_init__(self) -> None:
        if type(self.requirement_position) is not int or self.requirement_position < 0:
            raise ValueError("extension provider selection requires an exact position")
        _validate_selection_result(self.selection)


@dataclass(frozen=True, slots=True)
class ExtensionSignatureProviderContext:
    selectors: ExtensionSignatureRequirementSelectors
    selections: tuple[ExtensionSignatureProviderSelectionOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.selectors) is not ExtensionSignatureRequirementSelectors:
            raise ValueError("extension provider context requires exact selectors")
        selections = _freeze_selection_occurrences(self.selections)
        expected_positions = tuple(
            occurrence.requirement_position for occurrence in self.selectors.occurrences
        )
        actual_positions = tuple(
            occurrence.requirement_position for occurrence in selections
        )
        if actual_positions != expected_positions:
            raise ValueError(
                "extension provider selections must cover each selector exactly once in source order"
            )
        object.__setattr__(self, "selections", selections)


@dataclass(frozen=True, slots=True, init=False)
class ExtensionSignatureProviderAuthority:
    requirement: CapabilityRequirementOccurrence
    selector_occurrence: ExtensionSignatureRequirementSelectorOccurrence
    selection_occurrence: ExtensionSignatureProviderSelectionOccurrence
    selected_catalog: ConstructedExtensionCatalog | None
    scope: ExtensionCatalogLookupScope
    exact_group: ExtensionCatalogExactEntryGroup | None
    unmodeled_blockers: tuple[_CatalogEntry, ...]
    completeness_group: ExtensionCatalogCompletenessGroup | None
    provider_inputs: CanonicalCapabilityProviderInputs

    def __new__(cls) -> ExtensionSignatureProviderAuthority:
        raise TypeError("extension provider authority requires canonical construction")


def _unknown_inputs(
    key: CapabilityKey,
    reason: CapabilityReasonCode,
) -> CanonicalCapabilityProviderInputs:
    return CanonicalCapabilityProviderInputs(key, (), False, reason)


def _entry_evidence(
    catalog: ConstructedExtensionCatalog,
    key: CapabilityKey,
    member_position: int,
    entry: _CatalogEntry,
) -> tuple[CapabilityEvidence, ...]:
    reference = catalog.metadata.catalog
    return tuple(
        CapabilityEvidence(
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            catalog.metadata.source_occurrences[
                source_position
            ].provenance.source_locator,
            (
                f"{reference.identity.namespace}/{reference.identity.name}"
                f"@{reference.release} sha256:{catalog.content_sha256} "
                f"member:{member_position} evidence:{evidence_position} "
                f"source:{source_position}"
            ),
            dialect=key.dialect,
            extension=key.extension,
        )
        for evidence_position, source_position in enumerate(
            entry.evidence.source_positions
        )
    )


def _fact(
    key: CapabilityKey,
    catalog: ConstructedExtensionCatalog,
    members: tuple[tuple[int, _CatalogEntry], ...],
) -> CapabilityFact:
    return CapabilityFact(
        key,
        CapabilitySupport.SUPPORTED,
        CapabilityDisposition(CapabilityDispositionKind.NONE),
        tuple(
            evidence
            for member_position, entry in members
            for evidence in _entry_evidence(catalog, key, member_position, entry)
        ),
    )


def _unmodeled_entry_is_relevant(
    entry: _CatalogEntry,
    scope: ExtensionCatalogLookupScope,
) -> bool:
    if (
        entry.evidence.matchability
        is not ExtensionCatalogMatchability.CATALOGED_UNMODELED
        or _entry_family(entry) is not scope.family
    ):
        return False
    identity = scope.identity
    if isinstance(entry, ExtensionNativeTypeCatalogEntry):
        return entry.type_identity == identity
    if isinstance(
        entry,
        (ExtensionScalarFunctionCatalogEntry, ExtensionAggregateCatalogEntry),
    ):
        assert isinstance(identity, PostgreSQLCallableIdentity)
        return (
            entry.declaration.identity == identity
            if entry.declaration.identity is not None
            else entry.declaration.sql_name == identity.sql_name
        )
    if isinstance(entry, ExtensionOperatorCatalogEntry):
        assert isinstance(identity, PostgreSQLOperatorIdentity)
        return (
            entry.identity == identity
            if entry.identity is not None
            else entry.operator_name == identity.operator_name
            and entry.arity is identity.arity
        )
    assert isinstance(entry, ExtensionCastCatalogEntry)
    assert isinstance(identity, PostgreSQLCastIdentity)
    known_endpoints = 0
    for type_use, expected in (
        (entry.source_type, identity.source_type),
        (entry.target_type, identity.target_type),
    ):
        if type_use.kind is ExtensionCatalogDeclarationTypeUseKind.EXACT:
            known_endpoints += 1
            if type_use.exact_type != expected:
                return False
    return known_endpoints < 2 or entry.identity == identity


def _matching_group(
    catalog: ConstructedExtensionCatalog,
    scope: ExtensionCatalogLookupScope,
) -> ExtensionCatalogExactEntryGroup | None:
    matches = tuple(
        group for group in catalog.exact_entry_groups if group.scope == scope
    )
    if len(matches) > 1:
        raise ValueError("extension catalog has duplicate exact lookup groups")
    return None if not matches else matches[0]


def _matching_completeness_group(
    catalog: ConstructedExtensionCatalog,
    scope: ExtensionCatalogLookupScope,
) -> ExtensionCatalogCompletenessGroup | None:
    matches = tuple(
        group for group in catalog.completeness_groups if group.scope == scope
    )
    if len(matches) > 1:
        raise ValueError("extension catalog has duplicate completeness groups")
    return None if not matches else matches[0]


def _new_authority(
    requirement: CapabilityRequirementOccurrence,
    selector_occurrence: ExtensionSignatureRequirementSelectorOccurrence,
    selection_occurrence: ExtensionSignatureProviderSelectionOccurrence,
    selected_catalog: ConstructedExtensionCatalog | None,
    exact_group: ExtensionCatalogExactEntryGroup | None,
    unmodeled_blockers: tuple[_CatalogEntry, ...],
    completeness_group: ExtensionCatalogCompletenessGroup | None,
    provider_inputs: CanonicalCapabilityProviderInputs,
) -> ExtensionSignatureProviderAuthority:
    authority = object.__new__(ExtensionSignatureProviderAuthority)
    object.__setattr__(authority, "requirement", requirement)
    object.__setattr__(authority, "selector_occurrence", selector_occurrence)
    object.__setattr__(authority, "selection_occurrence", selection_occurrence)
    object.__setattr__(authority, "selected_catalog", selected_catalog)
    object.__setattr__(authority, "scope", selector_occurrence.selector.scope)
    object.__setattr__(authority, "exact_group", exact_group)
    object.__setattr__(authority, "unmodeled_blockers", unmodeled_blockers)
    object.__setattr__(authority, "completeness_group", completeness_group)
    object.__setattr__(authority, "provider_inputs", provider_inputs)
    return authority


def _derive_authority(
    requirement: CapabilityRequirementOccurrence,
    selector_occurrence: ExtensionSignatureRequirementSelectorOccurrence,
    selection_occurrence: ExtensionSignatureProviderSelectionOccurrence,
) -> ExtensionSignatureProviderAuthority:
    if requirement.position != selector_occurrence.requirement_position or (
        requirement.position != selection_occurrence.requirement_position
    ):
        raise ValueError("extension provider authority positions must agree")
    key = requirement.key
    if key.domain is not CapabilityDomain.EXTENSION_SIGNATURE:
        raise ValueError("extension provider authority requires an extension signature")
    selection = selection_occurrence.selection
    _validate_selection_result(selection)
    scope = selector_occurrence.selector.scope
    selected_catalog = selection.selected_catalog

    bridge = extension_signature_dialect_family_bridge(key.dialect)
    if (
        bridge is None
        or key.extension != selection.requested_target.extension_identity
        or bridge.database_family != selection.requested_target.database_family
    ):
        return _new_authority(
            requirement,
            selector_occurrence,
            selection_occurrence,
            selected_catalog,
            None,
            (),
            None,
            _unknown_inputs(
                key,
                CapabilityReasonCode.EXTENSION_CATALOG_TARGET_MISMATCH,
            ),
        )

    selection_reasons = {
        ExtensionCatalogSelectionOutcome.UNDECLARED: (
            CapabilityReasonCode.EXTENSION_CATALOG_UNDECLARED
        ),
        ExtensionCatalogSelectionOutcome.AMBIGUOUS: (
            CapabilityReasonCode.EXTENSION_CATALOG_SELECTION_AMBIGUOUS
        ),
        ExtensionCatalogSelectionOutcome.CONFLICT: (
            CapabilityReasonCode.EXTENSION_CATALOG_SELECTION_CONFLICT
        ),
    }
    if selection.outcome is not ExtensionCatalogSelectionOutcome.SELECTED:
        return _new_authority(
            requirement,
            selector_occurrence,
            selection_occurrence,
            None,
            None,
            (),
            None,
            _unknown_inputs(key, selection_reasons[selection.outcome]),
        )
    assert selected_catalog is not None

    exact_group = _matching_group(selected_catalog, scope)
    if exact_group is not None:
        if exact_group.state is ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT:
            facts = tuple(
                _fact(key, selected_catalog, ((position, entry),))
                for position, entry in enumerate(exact_group.entries)
            )
            inputs = CanonicalCapabilityProviderInputs(key, facts, False)
        else:
            entry = exact_group.entries[0]
            if (
                entry.evidence.matchability
                is not ExtensionCatalogMatchability.EXACT_MATCHABLE
            ):
                raise ValueError("exact lookup group requires exact-matchable entries")
            inputs = (
                CanonicalCapabilityProviderInputs(
                    key,
                    (
                        _fact(
                            key,
                            selected_catalog,
                            tuple(enumerate(exact_group.entries)),
                        ),
                    ),
                    False,
                )
                if entry.evidence.exposure
                is ExtensionCatalogExposure.DIRECT_SQL_SURFACE
                else _unknown_inputs(
                    key,
                    CapabilityReasonCode.EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE,
                )
            )
        return _new_authority(
            requirement,
            selector_occurrence,
            selection_occurrence,
            selected_catalog,
            exact_group,
            (),
            None,
            inputs,
        )

    blockers = tuple(
        entry
        for entry in selected_catalog.entries
        if _unmodeled_entry_is_relevant(entry, scope)
    )
    if blockers:
        return _new_authority(
            requirement,
            selector_occurrence,
            selection_occurrence,
            selected_catalog,
            None,
            blockers,
            None,
            _unknown_inputs(
                key,
                CapabilityReasonCode.EXTENSION_CATALOGED_UNMODELED,
            ),
        )

    completeness = _matching_completeness_group(selected_catalog, scope)
    if completeness is None:
        inputs = _unknown_inputs(
            key,
            CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE,
        )
    elif completeness.state is ExtensionCatalogCompletenessState.COMPLETE:
        inputs = CanonicalCapabilityProviderInputs(key, (), True)
    elif completeness.state is ExtensionCatalogCompletenessState.INCOMPLETE:
        inputs = _unknown_inputs(
            key,
            CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_INCOMPLETE,
        )
    else:
        inputs = _unknown_inputs(
            key,
            CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_CONFLICT,
        )
    return _new_authority(
        requirement,
        selector_occurrence,
        selection_occurrence,
        selected_catalog,
        None,
        (),
        completeness,
        inputs,
    )


def extension_signature_provider_authority(
    context: ExtensionSignatureProviderContext,
    requirement: CapabilityRequirementOccurrence,
) -> ExtensionSignatureProviderAuthority:
    if type(context) is not ExtensionSignatureProviderContext:
        raise ValueError("extension provider requires an exact context")
    if type(requirement) is not CapabilityRequirementOccurrence:
        raise ValueError("extension provider requires an exact requirement")
    requirements = context.selectors.requirements.occurrences
    if (
        requirement.position >= len(requirements)
        or requirements[requirement.position] is not requirement
    ):
        raise ValueError("extension provider rejects foreign requirement authority")
    selector = next(
        (
            occurrence
            for occurrence in context.selectors.occurrences
            if occurrence.requirement_position == requirement.position
        ),
        None,
    )
    selection = next(
        (
            occurrence
            for occurrence in context.selections
            if occurrence.requirement_position == requirement.position
        ),
        None,
    )
    if selector is None or selection is None:
        raise ValueError("extension provider requirement lacks exact authority")
    return _derive_authority(requirement, selector, selection)


def extension_signature_provider_inputs(
    authority: ExtensionSignatureProviderAuthority,
) -> CanonicalCapabilityProviderInputs:
    if type(authority) is not ExtensionSignatureProviderAuthority:
        raise ValueError("extension provider inputs require exact authority")
    expected = _derive_authority(
        authority.requirement,
        authority.selector_occurrence,
        authority.selection_occurrence,
    )
    if (
        authority.selected_catalog is not expected.selected_catalog
        or authority.scope is not expected.scope
        or authority.exact_group is not expected.exact_group
        or len(authority.unmodeled_blockers) != len(expected.unmodeled_blockers)
        or any(
            actual is not derived
            for actual, derived in zip(
                authority.unmodeled_blockers,
                expected.unmodeled_blockers,
                strict=True,
            )
        )
        or authority.completeness_group is not expected.completeness_group
        or authority.provider_inputs != expected.provider_inputs
    ):
        raise ValueError("extension provider authority rejects grafted inputs")
    return authority.provider_inputs
