from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto._project as project_package
import pietto._project.capability_checking as checking
import pietto._project.capability_inspection as capability_inspection
import pietto._project.capability_matrix as matrix_module
import pietto._project.extension_catalog_availability as catalog_availability
import pietto._project.extension_signature_provider as provider_module
import pietto.semantic as semantic_package
import pietto.semantic.capability_providers as semantic_providers
import test_phase56_slice6_exact_capability_requirement_checking as phase56
import test_phase57_slice5_extension_catalog_construction_completeness_canonical as slice5
import test_phase57_slice6_extension_catalog_declaration_availability_selection as slice6
from pietto._project.capability_availability import PackageCapabilityRequirementBinding
from pietto._project.capability_checking import (
    CapabilityRequirementCheck,
    CapabilityRequirementStatus,
    PackageCapabilityRequirementsChecked,
    check_package_capability_requirements,
)
from pietto._project.capability_inspection import (
    CapabilityInspectionCheck,
    CapabilityInspectionFormat,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingTargetContext,
    build_package_capability_checking_matrix,
)
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityOwner,
    ExtensionCatalogSelectionOutcome,
    ExtensionCatalogSelectionResult,
    select_extension_catalog,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderAuthority,
    ExtensionSignatureProviderContext,
    ExtensionSignatureProviderSelectionOccurrence,
    extension_signature_provider_authority,
    extension_signature_provider_inputs,
)
from pietto.semantic.capability_facts import (
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidenceSource,
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
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
)
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionAggregateCatalogEntry,
    ExtensionCastCatalogEntry,
    ExtensionCatalogCompletenessClaim,
    ExtensionCatalogCompletenessClaimKind,
    ExtensionCatalogCompletenessState,
    ExtensionCatalogDeclarationTypeUse,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogEntryEvidence,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogExactEntryGroupState,
    ExtensionCatalogExposure,
    ExtensionCatalogIdentity,
    ExtensionCatalogLookupScope,
    ExtensionCatalogMatchability,
    ExtensionCatalogReference,
    ExtensionCatalogTarget,
    ExtensionCatalogTypeReference,
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
    ExtensionSignatureRequirementSelector,
    ExtensionSignatureRequirementSelectorOccurrence,
    ExtensionSignatureRequirementSelectors,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase57-extension-signature-provider-checking-integration-v1.md"
)
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)

type _Entry = (
    ExtensionNativeTypeCatalogEntry
    | ExtensionScalarFunctionCatalogEntry
    | ExtensionAggregateCatalogEntry
    | ExtensionOperatorCatalogEntry
    | ExtensionCastCatalogEntry
)


def _key(name: str, *, extension: str = "example_extension") -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject=f"semantic {name}",
        operation="opaque request text",
        operands=("not", "a", "physical", "identity"),
        context="not parsed",
        dialect="postgresql",
        extension=extension,
    )


def _requirements(
    *keys: CapabilityKey,
    name: str = "slice8",
) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity("consumer", name)
    return CapabilityRequirementCollection(
        identity,
        tuple(
            CapabilityRequirementOccurrence(identity, position, key)
            for position, key in enumerate(keys)
        ),
    )


def _reference(name: str = "slice8") -> ExtensionCatalogReference:
    return ExtensionCatalogReference(
        ExtensionCatalogIdentity("org.example.catalogs", name),
        "catalog-release",
    )


def _target(
    *,
    database_family: str = "PostgreSQL",
    database_release: str = "17.4",
    extension_identity: str = "example_extension",
    extension_release: str = "2.0",
) -> ExtensionCatalogTarget:
    return ExtensionCatalogTarget(
        database_family,
        database_release,
        extension_identity,
        extension_release,
    )


def _catalog(
    entries: tuple[_Entry, ...] = (),
    claims: tuple[ExtensionCatalogCompletenessClaim, ...] = (),
    *,
    target: ExtensionCatalogTarget | None = None,
    reference: ExtensionCatalogReference | None = None,
    source_count: int = 1,
) -> ConstructedExtensionCatalog:
    return slice6._artifact(
        reference=reference or _reference(),
        target=target or _target(),
        source_labels=tuple(f"source-{position}" for position in range(source_count)),
        entries=cast(Any, entries),
        claims=claims,
    )


def _selection(catalog: ConstructedExtensionCatalog) -> ExtensionCatalogSelectionResult:
    return select_extension_catalog(
        slice6._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        ),
        catalog.metadata.target,
    )


def _undeclared_selection(
    target: ExtensionCatalogTarget | None = None,
) -> ExtensionCatalogSelectionResult:
    return select_extension_catalog(
        DeclaredExtensionCatalogAvailability(()),
        target or _target(),
    )


def _context(
    requirements: CapabilityRequirementCollection,
    *bindings: tuple[
        int,
        ExtensionCatalogLookupScope,
        ExtensionCatalogSelectionResult,
    ],
) -> ExtensionSignatureProviderContext:
    selectors = ExtensionSignatureRequirementSelectors(
        requirements,
        tuple(
            ExtensionSignatureRequirementSelectorOccurrence(
                position,
                ExtensionSignatureRequirementSelector(scope),
            )
            for position, scope, _selection_result in bindings
        ),
    )
    return ExtensionSignatureProviderContext(
        selectors,
        tuple(
            ExtensionSignatureProviderSelectionOccurrence(position, selection)
            for position, _scope, selection in bindings
        ),
    )


def _lookup(
    scope: ExtensionCatalogLookupScope,
    selection: ExtensionCatalogSelectionResult,
    *,
    key: CapabilityKey | None = None,
) -> tuple[ExtensionSignatureProviderAuthority, Found | Absent | Unknown | Conflict]:
    requirement_key = key or _key("lookup")
    requirements = _requirements(requirement_key)
    context = _context(requirements, (0, scope, selection))
    authority = extension_signature_provider_authority(
        context,
        requirements.occurrences[0],
    )
    inputs = extension_signature_provider_inputs(authority)
    return authority, lookup_capability(
        inputs.key,
        inputs.facts,
        domain_complete=inputs.domain_complete,
        unknown_reason=inputs.unknown_reason,
    )


def _unmodeled_evidence(
    position: int = 0,
    *,
    exposure: ExtensionCatalogExposure = ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
) -> ExtensionCatalogEntryEvidence:
    return ExtensionCatalogEntryEvidence(
        ExtensionCatalogMatchability.CATALOGED_UNMODELED,
        exposure,
        (ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,),
        (position,),
    )


def _unmodeled_type(
    spelling: str = "opaque(type)",
) -> ExtensionCatalogDeclarationTypeUse:
    return ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.UNMODELED,
        source_spelling=spelling,
        unmodeled_reasons=(ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,),
    )


def _exact_type(
    reference: ExtensionCatalogTypeReference,
) -> ExtensionCatalogDeclarationTypeUse:
    return ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.EXACT,
        exact_type=reference,
    )


def _callable_declaration(
    name: str,
    inputs: tuple[ExtensionCatalogDeclarationTypeUse, ...],
) -> PostgreSQLCallableDeclaration:
    exact = tuple(type_use.exact_type for type_use in inputs)
    return PostgreSQLCallableDeclaration(
        name,
        inputs,
        (
            PostgreSQLCallableIdentity(name, cast(Any, exact))
            if all(reference is not None for reference in exact)
            else None
        ),
    )


def _provider_result_for_entry(
    entry: _Entry,
) -> tuple[ExtensionSignatureProviderAuthority, Found | Absent | Unknown | Conflict]:
    catalog = _catalog((entry,))
    assert len(catalog.exact_entry_groups) == 1
    return _lookup(catalog.exact_entry_groups[0].scope, _selection(catalog))


def test_context_binds_multiple_selectors_and_precomputed_selections_by_position() -> (
    None
):
    first_catalog = _catalog((slice5._native_entry(),))
    second_catalog = _catalog((slice5._cast_entry(),), reference=_reference("cast"))
    first_scope = first_catalog.exact_entry_groups[0].scope
    second_scope = second_catalog.exact_entry_groups[0].scope
    requirements = _requirements(_key("first"), _key("second"))
    first_selection = _selection(first_catalog)
    second_selection = _selection(second_catalog)
    context = _context(
        requirements,
        (0, first_scope, first_selection),
        (1, second_scope, second_selection),
    )

    assert context.selectors.requirements is requirements
    assert tuple(item.requirement_position for item in context.selections) == (0, 1)
    first = extension_signature_provider_authority(
        context,
        requirements.occurrences[0],
    )
    second = extension_signature_provider_authority(
        context,
        requirements.occurrences[1],
    )
    assert first.selection_occurrence.selection is first_selection
    assert second.selection_occurrence.selection is second_selection
    assert first.selected_catalog is first_catalog
    assert second.selected_catalog is second_catalog


def test_context_rejects_missing_duplicate_extra_and_nonselector_bindings() -> None:
    catalog = _catalog((slice5._native_entry(),))
    scope = catalog.exact_entry_groups[0].scope
    selection = _selection(catalog)
    requirements = _requirements(_key("first"), _key("second"))
    selectors = ExtensionSignatureRequirementSelectors(
        requirements,
        tuple(
            ExtensionSignatureRequirementSelectorOccurrence(
                position,
                ExtensionSignatureRequirementSelector(scope),
            )
            for position in (0, 1)
        ),
    )
    occurrences = (
        ExtensionSignatureProviderSelectionOccurrence(0, selection),
        ExtensionSignatureProviderSelectionOccurrence(1, selection),
    )
    assert ExtensionSignatureProviderContext(selectors, occurrences).selections == (
        occurrences
    )
    for invalid in (
        occurrences[:1],
        (occurrences[0], occurrences[0]),
        (*occurrences, ExtensionSignatureProviderSelectionOccurrence(2, selection)),
    ):
        with pytest.raises(ValueError, match="cover each selector exactly once"):
            ExtensionSignatureProviderContext(selectors, invalid)

    nonextension = CapabilityKey(CapabilityDomain.CONVERSION, subject="conversion")
    mixed = _requirements(nonextension, _key("extension"), name="mixed")
    mixed_selectors = ExtensionSignatureRequirementSelectors(
        mixed,
        (
            ExtensionSignatureRequirementSelectorOccurrence(
                1,
                ExtensionSignatureRequirementSelector(scope),
            ),
        ),
    )
    with pytest.raises(ValueError, match="cover each selector exactly once"):
        ExtensionSignatureProviderContext(
            mixed_selectors,
            (ExtensionSignatureProviderSelectionOccurrence(0, selection),),
        )
    with pytest.raises(ValueError, match="ordered iterable"):
        ExtensionSignatureProviderContext(selectors, cast(Any, {occurrences[0]}))


def test_context_rejects_an_internally_inconsistent_selection_target() -> None:
    catalog = _catalog((slice5._native_entry(),))
    selection = _selection(catalog)
    object.__setattr__(selection, "requested_target", _target(database_release="18"))
    with pytest.raises(ValueError, match="target"):
        ExtensionSignatureProviderSelectionOccurrence(0, selection)


def test_slice6_selection_outcomes_map_to_distinct_unknown_reasons() -> None:
    scope = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity("missing", (slice5._builtin(),)),
    )
    undeclared = _undeclared_selection()
    first = _catalog(reference=_reference("first"))
    second = _catalog(reference=_reference("second"))
    ambiguous = select_extension_catalog(
        slice6._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, first, None),
            (ExtensionCatalogAvailabilityOwner.COMPILER, second, None),
        ),
        _target(),
    )
    conflict_first = _catalog(reference=_reference("conflict"), source_count=1)
    conflict_second = _catalog(reference=_reference("conflict"), source_count=2)
    conflict = select_extension_catalog(
        slice6._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, conflict_first, None),
            (ExtensionCatalogAvailabilityOwner.COMPILER, conflict_second, None),
        ),
        _target(),
    )
    assert tuple(result.outcome for result in (undeclared, ambiguous, conflict)) == (
        ExtensionCatalogSelectionOutcome.UNDECLARED,
        ExtensionCatalogSelectionOutcome.AMBIGUOUS,
        ExtensionCatalogSelectionOutcome.CONFLICT,
    )
    expected = (
        CapabilityReasonCode.EXTENSION_CATALOG_UNDECLARED,
        CapabilityReasonCode.EXTENSION_CATALOG_SELECTION_AMBIGUOUS,
        CapabilityReasonCode.EXTENSION_CATALOG_SELECTION_CONFLICT,
    )
    for selection, reason in zip(
        (undeclared, ambiguous, conflict), expected, strict=True
    ):
        authority, result = _lookup(scope, selection)
        assert result == Unknown(reason)
        assert authority.selection_occurrence.selection is selection
        assert authority.selected_catalog is None


@pytest.mark.parametrize(
    "target",
    (
        _target(database_family="PostgreSQL "),
        _target(extension_identity="other_extension"),
    ),
    ids=("database-family", "extension-identity"),
)
def test_target_affinity_mismatch_is_unknown_not_absent(
    target: ExtensionCatalogTarget,
) -> None:
    catalog = _catalog((slice5._native_entry(),), target=target)
    scope = catalog.exact_entry_groups[0].scope
    authority, result = _lookup(scope, _selection(catalog))
    assert result == Unknown(CapabilityReasonCode.EXTENSION_CATALOG_TARGET_MISMATCH)
    assert authority.selected_catalog is catalog
    assert authority.exact_group is None


def test_release_stays_outside_key_and_does_not_trigger_fallback() -> None:
    entry = slice5._native_entry()
    first = _catalog(
        (entry,), target=_target(database_release="16", extension_release="1")
    )
    second = _catalog(
        (entry,), target=_target(database_release="17", extension_release="2")
    )
    scope = first.exact_entry_groups[0].scope
    key = _key("release-free")
    first_authority, first_result = _lookup(scope, _selection(first), key=key)
    second_authority, second_result = _lookup(scope, _selection(second), key=key)
    assert isinstance(first_result, Found) and isinstance(second_result, Found)
    assert first_result.fact.key is second_result.fact.key is key
    assert first_authority.selection_occurrence.selection.requested_target != (
        second_authority.selection_occurrence.selection.requested_target
    )


@pytest.mark.parametrize(
    "entry",
    (
        slice5._native_entry(),
        slice5._scalar_entry(),
        slice5._aggregate_entry(),
        slice5._operator_entry(),
        slice5._cast_entry(),
    ),
    ids=("native", "scalar", "aggregate", "operator", "cast"),
)
def test_all_five_exact_typed_families_project_supported_found(entry: _Entry) -> None:
    authority, result = _provider_result_for_entry(entry)
    assert isinstance(result, Found)
    assert result.fact.key is authority.requirement.key
    assert result.fact.support is CapabilitySupport.SUPPORTED
    assert result.fact.disposition.kind is CapabilityDispositionKind.NONE
    assert result.fact.evidence
    assert all(
        evidence.source is CapabilityEvidenceSource.SEMANTIC_CATALOG
        and evidence.dialect == "postgresql"
        and evidence.extension == "example_extension"
        for evidence in result.fact.evidence
    )
    assert authority.scope is authority.selector_occurrence.selector.scope
    assert authority.exact_group is not None
    assert authority.exact_group.scope == authority.scope


def test_lookup_never_crosses_equal_callable_identity_between_families() -> None:
    catalog = _catalog((slice5._scalar_entry(name="shared"),))
    scalar_scope = catalog.exact_entry_groups[0].scope
    assert isinstance(scalar_scope.identity, PostgreSQLCallableIdentity)
    aggregate_scope = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.AGGREGATE,
        scalar_scope.identity,
    )
    _authority, result = _lookup(aggregate_scope, _selection(catalog))
    assert result == Unknown(
        CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE
    )


@pytest.mark.parametrize(
    ("exposure", "expected_type"),
    (
        (ExtensionCatalogExposure.DIRECT_SQL_SURFACE, Found),
        (ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT, Unknown),
        (ExtensionCatalogExposure.UNCLASSIFIED, Unknown),
    ),
)
def test_exact_entry_requires_direct_sql_surface_provider_eligibility(
    exposure: ExtensionCatalogExposure,
    expected_type: type[Found] | type[Unknown],
) -> None:
    authority, result = _provider_result_for_entry(
        slice5._scalar_entry(exposure=exposure)
    )
    assert type(result) is expected_type
    assert authority.exact_group is not None
    if isinstance(result, Unknown):
        assert result.reason is (
            CapabilityReasonCode.EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE
        )


def test_consistent_duplicate_is_one_fact_with_full_private_provenance() -> None:
    catalog = _catalog(
        (slice5._scalar_entry((0,)), slice5._scalar_entry((1,))),
        source_count=2,
    )
    group = catalog.exact_entry_groups[0]
    assert group.state is ExtensionCatalogExactEntryGroupState.CONSISTENT_DUPLICATE
    authority, result = _lookup(group.scope, _selection(catalog))
    assert isinstance(result, Found)
    assert len(result.fact.evidence) == 2
    assert authority.exact_group is group
    assert tuple(evidence.source_path for evidence in result.fact.evidence) == (
        "sql/source-0.sql:declaration",
        "sql/source-1.sql:declaration",
    )


def test_evidence_conflict_projects_every_overlapping_member_as_distinct_fact() -> None:
    catalog = _catalog(
        (
            slice5._scalar_entry((0,), volatility=PostgreSQLVolatility.IMMUTABLE),
            slice5._scalar_entry((0,), volatility=PostgreSQLVolatility.VOLATILE),
        )
    )
    group = catalog.exact_entry_groups[0]
    assert group.state is ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT
    authority, result = _lookup(group.scope, _selection(catalog))
    assert isinstance(result, Conflict)
    assert len(result.evidence) == len(group.entries) == 2
    assert len(set(result.evidence)) == 2
    assert all(
        fact.key is authority.requirement.key
        and fact.support is CapabilitySupport.SUPPORTED
        and fact.disposition.kind is CapabilityDispositionKind.NONE
        for fact in result.evidence
    )
    references = tuple(fact.evidence[0].source_reference for fact in result.evidence)
    assert references[0] != references[1]
    assert {"member:0", "member:1"} == {
        reference.split(" evidence:")[0].rsplit(" ", 1)[-1] for reference in references
    }
    assert authority.exact_group is group


def _fallback_unmodeled_case(
    family: ExtensionCatalogEntryFamily,
    *,
    relevant: bool,
) -> tuple[ExtensionCatalogLookupScope, _Entry]:
    builtin = slice5._builtin
    if family is ExtensionCatalogEntryFamily.NATIVE_TYPE:
        scope = ExtensionCatalogLookupScope(family, slice5._native("wanted"))
        entry: _Entry = ExtensionNativeTypeCatalogEntry(
            slice5._native("wanted" if relevant else "other"),
            None,
            _unmodeled_evidence(),
        )
    elif family in {
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        ExtensionCatalogEntryFamily.AGGREGATE,
    }:
        scope = ExtensionCatalogLookupScope(
            family,
            PostgreSQLCallableIdentity("wanted", (builtin(),)),
        )
        declaration = _callable_declaration(
            "wanted" if relevant else "other",
            (_unmodeled_type(),),
        )
        if family is ExtensionCatalogEntryFamily.SCALAR_FUNCTION:
            entry = ExtensionScalarFunctionCatalogEntry(
                declaration,
                _exact_type(builtin()),
                PostgreSQLNullCallBehavior.UNKNOWN,
                PostgreSQLVolatility.UNKNOWN,
                PostgreSQLParallelSafety.UNKNOWN,
                False,
                False,
                False,
                False,
                _unmodeled_evidence(),
            )
        else:
            entry = ExtensionAggregateCatalogEntry(
                PostgreSQLAggregateKind.ORDINARY,
                declaration,
                _exact_type(builtin()),
                PostgreSQLParallelSafety.UNKNOWN,
                False,
                False,
                _unmodeled_evidence(),
            )
    elif family is ExtensionCatalogEntryFamily.OPERATOR:
        scope = ExtensionCatalogLookupScope(
            family,
            PostgreSQLOperatorIdentity(
                "##",
                PostgreSQLOperatorArity.BINARY,
                (builtin(), builtin("int4")),
            ),
        )
        entry = ExtensionOperatorCatalogEntry(
            "##" if relevant else "@@",
            PostgreSQLOperatorArity.BINARY,
            (_unmodeled_type(), _exact_type(builtin("int4"))),
            None,
            _exact_type(builtin()),
            _unmodeled_evidence(),
        )
    else:
        scope = ExtensionCatalogLookupScope(
            family,
            PostgreSQLCastIdentity(builtin(), builtin("int4")),
        )
        entry = ExtensionCastCatalogEntry(
            _exact_type(builtin() if relevant else builtin("bool")),
            _unmodeled_type(),
            None,
            PostgreSQLCastContext.UNKNOWN,
            PostgreSQLCastMethod.UNKNOWN,
            _unmodeled_evidence(),
        )
    return scope, entry


@pytest.mark.parametrize("family", tuple(ExtensionCatalogEntryFamily))
@pytest.mark.parametrize("relevant", (True, False), ids=("relevant", "unrelated"))
def test_cataloged_unmodeled_relevance_is_family_local_and_blocks_only_when_relevant(
    family: ExtensionCatalogEntryFamily,
    relevant: bool,
) -> None:
    scope, entry = _fallback_unmodeled_case(family, relevant=relevant)
    claim = ExtensionCatalogCompletenessClaim(
        scope,
        ExtensionCatalogCompletenessClaimKind.COMPLETE,
        (0,),
    )
    catalog = _catalog((entry,), (claim,))
    authority, result = _lookup(scope, _selection(catalog))
    if relevant:
        assert result == Unknown(CapabilityReasonCode.EXTENSION_CATALOGED_UNMODELED)
        assert authority.unmodeled_blockers == (entry,)
        assert authority.completeness_group is None
    else:
        assert isinstance(result, Absent)
        assert authority.unmodeled_blockers == ()
        assert authority.completeness_group is not None
        assert authority.completeness_group.state is (
            ExtensionCatalogCompletenessState.COMPLETE
        )


def test_cast_with_neither_exact_endpoint_is_potentially_relevant() -> None:
    scope = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.CAST,
        PostgreSQLCastIdentity(slice5._builtin(), slice5._builtin("int4")),
    )
    entry = ExtensionCastCatalogEntry(
        _unmodeled_type("source"),
        _unmodeled_type("target"),
        None,
        PostgreSQLCastContext.UNKNOWN,
        PostgreSQLCastMethod.UNKNOWN,
        _unmodeled_evidence(),
    )
    catalog = _catalog((entry,))
    authority, result = _lookup(scope, _selection(catalog))
    assert result == Unknown(CapabilityReasonCode.EXTENSION_CATALOGED_UNMODELED)
    assert authority.unmodeled_blockers == (entry,)


@pytest.mark.parametrize(
    "family",
    (
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        ExtensionCatalogEntryFamily.AGGREGATE,
        ExtensionCatalogEntryFamily.OPERATOR,
    ),
)
def test_unmodeled_exact_identity_equality_overrides_name_only_fallback(
    family: ExtensionCatalogEntryFamily,
) -> None:
    builtin = slice5._builtin
    if family in {
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        ExtensionCatalogEntryFamily.AGGREGATE,
    }:
        declaration = _callable_declaration("wanted", (_exact_type(builtin()),))
        mismatched_scope = ExtensionCatalogLookupScope(
            family,
            PostgreSQLCallableIdentity("wanted", (builtin("int4"),)),
        )
        if family is ExtensionCatalogEntryFamily.SCALAR_FUNCTION:
            entry: _Entry = ExtensionScalarFunctionCatalogEntry(
                declaration,
                _unmodeled_type("result"),
                PostgreSQLNullCallBehavior.UNKNOWN,
                PostgreSQLVolatility.UNKNOWN,
                PostgreSQLParallelSafety.UNKNOWN,
                False,
                False,
                False,
                False,
                _unmodeled_evidence(),
            )
        else:
            entry = ExtensionAggregateCatalogEntry(
                PostgreSQLAggregateKind.ORDINARY,
                declaration,
                _unmodeled_type("result"),
                PostgreSQLParallelSafety.UNKNOWN,
                False,
                False,
                _unmodeled_evidence(),
            )
    else:
        entry = ExtensionOperatorCatalogEntry(
            "##",
            PostgreSQLOperatorArity.BINARY,
            (_exact_type(builtin()), _exact_type(builtin("int4"))),
            PostgreSQLOperatorIdentity(
                "##",
                PostgreSQLOperatorArity.BINARY,
                (builtin(), builtin("int4")),
            ),
            _unmodeled_type("result"),
            _unmodeled_evidence(),
        )
        mismatched_scope = ExtensionCatalogLookupScope(
            family,
            PostgreSQLOperatorIdentity(
                "##",
                PostgreSQLOperatorArity.BINARY,
                (builtin("int4"), builtin("int4")),
            ),
        )
    complete = ExtensionCatalogCompletenessClaim(
        mismatched_scope,
        ExtensionCatalogCompletenessClaimKind.COMPLETE,
        (0,),
    )
    catalog = _catalog((entry,), (complete,))
    authority, result = _lookup(mismatched_scope, _selection(catalog))
    assert isinstance(result, Absent)
    assert authority.unmodeled_blockers == ()


@pytest.mark.parametrize(
    ("claims", "expected"),
    (
        ((ExtensionCatalogCompletenessClaimKind.COMPLETE,), Absent),
        (
            (ExtensionCatalogCompletenessClaimKind.INCOMPLETE,),
            CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_INCOMPLETE,
        ),
        (
            (
                ExtensionCatalogCompletenessClaimKind.COMPLETE,
                ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
            ),
            CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_CONFLICT,
        ),
        ((), CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE),
    ),
)
def test_zero_match_uses_only_exact_scoped_completeness(
    claims: tuple[ExtensionCatalogCompletenessClaimKind, ...],
    expected: type[Absent] | CapabilityReasonCode,
) -> None:
    scope = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity("missing", (slice5._builtin(),)),
    )
    catalog_claims = tuple(
        ExtensionCatalogCompletenessClaim(scope, kind, (0,)) for kind in claims
    )
    catalog = _catalog((), catalog_claims)
    authority, result = _lookup(scope, _selection(catalog))
    if expected is Absent:
        assert result == Absent(authority.requirement.key)
    else:
        assert result == Unknown(cast(CapabilityReasonCode, expected))


def test_unrelated_conflict_unmodeled_and_completeness_do_not_poison_lookup() -> None:
    conflicting = (
        slice5._scalar_entry((0,), name="other", result="text"),
        slice5._scalar_entry((0,), name="other", result="int4"),
    )
    requested = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.CAST,
        PostgreSQLCastIdentity(slice5._builtin(), slice5._builtin("int4")),
    )
    complete = ExtensionCatalogCompletenessClaim(
        requested,
        ExtensionCatalogCompletenessClaimKind.COMPLETE,
        (0,),
    )
    catalog = _catalog(conflicting, (complete,))
    assert catalog.exact_entry_groups[0].state is (
        ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT
    )
    _authority, result = _lookup(requested, _selection(catalog))
    assert isinstance(result, Absent)


def _checked_result(
    tmp_path: Path,
    requirements: CapabilityRequirementCollection,
    context: ExtensionSignatureProviderContext | None,
    *target_keys: CapabilityKey,
) -> PackageCapabilityRequirementsChecked:
    package, _dependency = phase56.slice5._loaded_packages(tmp_path)
    composition = phase56._composition(
        *(phase56._target_fact(key) for key in target_keys)
    )
    binding = PackageCapabilityRequirementBinding(package, requirements)
    result = check_package_capability_requirements(
        package,
        binding,
        composition,
        phase56._availability(composition),
        context,
    )
    assert isinstance(result, PackageCapabilityRequirementsChecked)
    return result


def test_checker_preserves_status_algebra_and_nonextension_provider_path(
    tmp_path: Path,
) -> None:
    found_entry = slice5._native_entry()
    found_catalog = _catalog((found_entry,), reference=_reference("found"))
    found_scope = found_catalog.exact_entry_groups[0].scope
    absent_scope = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity("absent", (slice5._builtin(),)),
    )
    absent_catalog = _catalog(
        (),
        (
            ExtensionCatalogCompletenessClaim(
                absent_scope,
                ExtensionCatalogCompletenessClaimKind.COMPLETE,
                (0,),
            ),
        ),
        reference=_reference("absent"),
    )
    conflict_catalog = _catalog(
        (
            slice5._scalar_entry((0,), volatility=PostgreSQLVolatility.IMMUTABLE),
            slice5._scalar_entry((0,), volatility=PostgreSQLVolatility.VOLATILE),
        ),
        reference=_reference("evidence-conflict"),
    )
    conflict_scope = conflict_catalog.exact_entry_groups[0].scope
    keys = tuple(_key(name) for name in ("found", "absent", "unknown", "conflict"))
    nonextension = phase56._UNSUPPORTED_PROVIDER_FACT.key
    requirements = _requirements(*keys, nonextension, name="checker")
    context = _context(
        requirements,
        (0, found_scope, _selection(found_catalog)),
        (1, absent_scope, _selection(absent_catalog)),
        (2, absent_scope, _undeclared_selection()),
        (3, conflict_scope, _selection(conflict_catalog)),
    )
    result = _checked_result(tmp_path, requirements, context, *keys, nonextension)
    assert tuple(check.status for check in result.checks) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.ABSENT,
        CapabilityRequirementStatus.UNKNOWN,
        CapabilityRequirementStatus.CONFLICT,
        CapabilityRequirementStatus.UNSUPPORTED,
    )
    assert result.checks[-1].extension_signature_provider_authority is None
    assert result.checks[-1].provider_inputs == (
        semantic_providers.canonical_capability_provider_inputs(nonextension)
    )


def test_checker_legacy_extension_and_profile_omission_remain_unknown(
    tmp_path: Path,
) -> None:
    catalog = _catalog((slice5._native_entry(),))
    scope = catalog.exact_entry_groups[0].scope
    key = _key("legacy")
    requirements = _requirements(key, name="legacy")
    context = _context(requirements, (0, scope, _selection(catalog)))
    omission = _checked_result(tmp_path / "omission", requirements, context)
    legacy = _checked_result(tmp_path / "legacy", requirements, None, key)
    assert omission.checks[0].status is CapabilityRequirementStatus.UNKNOWN
    assert isinstance(omission.checks[0].provider_result, Found)
    assert legacy.checks[0].provider_result == Unknown(
        CapabilityReasonCode.NOT_EVIDENCED
    )
    assert legacy.checks[0].extension_signature_provider_authority is None


def test_checker_rejects_foreign_context_and_grafted_provider_inputs(
    tmp_path: Path,
) -> None:
    catalog = _catalog((slice5._native_entry(),))
    scope = catalog.exact_entry_groups[0].scope
    key = _key("authority")
    requirements = _requirements(key, name="authority")
    context = _context(requirements, (0, scope, _selection(catalog)))
    foreign_requirements = _requirements(key, name="authority")
    assert (
        foreign_requirements == requirements
        and foreign_requirements is not requirements
    )
    foreign_context = _context(
        foreign_requirements,
        (0, scope, _selection(catalog)),
    )
    package, _dependency = phase56.slice5._loaded_packages(tmp_path)
    composition = phase56._composition(phase56._target_fact(key))
    binding = PackageCapabilityRequirementBinding(package, requirements)
    with pytest.raises(ValueError, match="foreign requirement provider context"):
        check_package_capability_requirements(
            package,
            binding,
            composition,
            phase56._availability(composition),
            foreign_context,
        )

    checked = check_package_capability_requirements(
        package,
        binding,
        composition,
        phase56._availability(composition),
        context,
    )
    assert isinstance(checked, PackageCapabilityRequirementsChecked)
    with pytest.raises(ValueError, match="canonical extension provider inputs"):
        replace(
            checked.checks[0],
            provider_inputs=semantic_providers.canonical_capability_provider_inputs(
                key
            ),
        )


def test_matrix_distinguishes_provider_context_and_delegates_once_per_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = _catalog((slice5._native_entry(),), reference=_reference("matrix-found"))
    scope = catalog.exact_entry_groups[0].scope
    absent_catalog = _catalog(
        (),
        (
            ExtensionCatalogCompletenessClaim(
                scope,
                ExtensionCatalogCompletenessClaimKind.COMPLETE,
                (0,),
            ),
        ),
        reference=_reference("matrix-absent"),
    )
    key = _key("matrix")
    requirements = _requirements(key, name="matrix")
    found_context = _context(requirements, (0, scope, _selection(catalog)))
    absent_context = _context(
        requirements,
        (0, scope, _selection(absent_catalog)),
    )
    package, _dependency = phase56.slice5._loaded_packages(tmp_path)
    composition = phase56._composition(phase56._target_fact(key))
    availability = phase56._availability(composition)
    binding = PackageCapabilityRequirementBinding(package, requirements)
    contexts = (
        CapabilityCheckingTargetContext(0, composition, availability, found_context),
        CapabilityCheckingTargetContext(1, composition, availability, absent_context),
    )

    original = matrix_module.check_package_capability_requirements
    calls = 0

    def counted(*args: object) -> object:
        nonlocal calls
        calls += 1
        return original(*cast(Any, args))

    monkeypatch.setattr(
        catalog_availability,
        "select_extension_catalog",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("catalog selection was rerun")
        ),
    )
    monkeypatch.setattr(matrix_module, "check_package_capability_requirements", counted)
    matrix = build_package_capability_checking_matrix(package, binding, contexts)
    assert calls == len(contexts) == 2
    assert tuple(cell.check.status for cell in matrix.rows[0].cells if cell.check) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.ABSENT,
    )
    with pytest.raises(ValueError, match="duplicates position 0"):
        build_package_capability_checking_matrix(
            package,
            binding,
            (
                contexts[0],
                CapabilityCheckingTargetContext(
                    1,
                    composition,
                    availability,
                    found_context,
                ),
            ),
        )


def test_matrix_column_context_supports_multiple_extension_selections(
    tmp_path: Path,
) -> None:
    first_catalog = _catalog((slice5._native_entry(),), reference=_reference("multi-a"))
    second_catalog = _catalog((slice5._cast_entry(),), reference=_reference("multi-b"))
    first_scope = first_catalog.exact_entry_groups[0].scope
    second_scope = second_catalog.exact_entry_groups[0].scope
    first_key, second_key = _key("multi-a"), _key("multi-b")
    requirements = _requirements(first_key, second_key, name="matrix-multiple")
    provider_context = _context(
        requirements,
        (0, first_scope, _selection(first_catalog)),
        (1, second_scope, _selection(second_catalog)),
    )
    package, _dependency = phase56.slice5._loaded_packages(tmp_path)
    composition = phase56._composition(
        phase56._target_fact(first_key),
        phase56._target_fact(second_key),
    )
    availability = phase56._availability(composition)
    matrix = build_package_capability_checking_matrix(
        package,
        PackageCapabilityRequirementBinding(package, requirements),
        (
            CapabilityCheckingTargetContext(
                0,
                composition,
                availability,
                provider_context,
            ),
        ),
    )
    assert tuple(
        row.cells[0].check.status for row in matrix.rows if row.cells[0].check
    ) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.SATISFIED,
    )


def test_capability_inspection_shape_and_phase56_corpus_remain_compatible(
    tmp_path: Path,
) -> None:
    catalog = _catalog((slice5._native_entry(),))
    before_bytes = catalog.canonical_bytes
    before_digest = catalog.content_sha256
    scope = catalog.exact_entry_groups[0].scope
    key = _key("inspection")
    requirements = _requirements(key, name="inspection")
    provider_context = _context(requirements, (0, scope, _selection(catalog)))
    package, _dependency = phase56.slice5._loaded_packages(tmp_path)
    composition = phase56._composition(phase56._target_fact(key))
    matrix = build_package_capability_checking_matrix(
        package,
        PackageCapabilityRequirementBinding(package, requirements),
        (
            CapabilityCheckingTargetContext(
                0,
                composition,
                phase56._availability(composition),
                provider_context,
            ),
        ),
    )
    inspection = build_capability_inspection(matrix)
    assert (
        inspection.inspection.format
        is CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1
    )
    assert inspection.canonical_bytes.startswith(b"inspection")
    assert tuple(field.name for field in fields(CapabilityInspectionCheck)) == (
        "target_occurrences",
        "target_lookup",
        "provider_domain_complete",
        "provider_unknown_reason",
        "provider_lookup",
        "status",
        "check",
    )
    assert catalog.canonical_bytes is before_bytes
    assert catalog.content_sha256 == before_digest
    assert slice5._corpus_digest() == EXPECTED_CORPUS_DIGEST


def test_legacy_semantic_provider_and_public_private_boundaries_are_zero_delta() -> (
    None
):
    key = _key("legacy-provider")
    inputs = semantic_providers.canonical_capability_provider_inputs(key)
    assert inputs.facts == () and inputs.domain_complete is False
    assert lookup_capability(
        inputs.key,
        inputs.facts,
        domain_complete=inputs.domain_complete,
        unknown_reason=inputs.unknown_reason,
    ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert "extension_catalog" not in inspect.getsource(semantic_providers)
    assert (
        capability_inspection.CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value
        == ("pietto.capability-inspection.v1")
    )
    assert provider_module.__all__ == ()
    for module in (pietto, semantic_package, project_package):
        for carrier in (
            ExtensionSignatureProviderSelectionOccurrence,
            ExtensionSignatureProviderContext,
            ExtensionSignatureProviderAuthority,
        ):
            assert not hasattr(module, carrier.__name__)


def test_provider_carriers_checks_and_matrix_context_are_closed_exact_shapes() -> None:
    assert tuple(field.name for field in fields(ExtensionSignatureProviderContext)) == (
        "selectors",
        "selections",
    )
    assert tuple(
        field.name for field in fields(ExtensionSignatureProviderAuthority)
    ) == (
        "requirement",
        "selector_occurrence",
        "selection_occurrence",
        "selected_catalog",
        "scope",
        "exact_group",
        "unmodeled_blockers",
        "completeness_group",
        "provider_inputs",
    )
    assert tuple(field.name for field in fields(CapabilityRequirementCheck))[-1] == (
        "extension_signature_provider_authority"
    )
    assert tuple(field.name for field in fields(CapabilityCheckingTargetContext)) == (
        "position",
        "composition",
        "availability",
        "extension_signature_provider_context",
    )
    for carrier in (
        ExtensionSignatureProviderSelectionOccurrence,
        ExtensionSignatureProviderContext,
        ExtensionSignatureProviderAuthority,
    ):
        assert is_dataclass(carrier) and "__dict__" not in carrier.__slots__
    with pytest.raises(TypeError):
        ExtensionSignatureProviderAuthority()
    selection = _undeclared_selection()
    occurrence = ExtensionSignatureProviderSelectionOccurrence(0, selection)
    with pytest.raises(FrozenInstanceError):
        occurrence.requirement_position = 1  # pyright: ignore[reportAttributeAccessIssue]


def test_provider_checker_matrix_never_reselect_or_add_runtime_behavior() -> None:
    source = "\n".join(
        inspect.getsource(module)
        for module in (provider_module, checking, matrix_module)
    ).lower()
    assert "select_extension_catalog" not in source
    for forbidden in (
        "create extension",
        "database connection",
        "server_version",
        "installed",
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "open(",
        "getcwd",
        "environ",
        "latest",
        "ranking",
        "fallback",
        "lowering",
    ):
        assert forbidden not in source


def test_slice8_spec_lifecycle_reader_closure_and_package_smoke_are_exact() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for heading in (
        "Provider Context Authority",
        "Target Affinity",
        "Selection And Lookup Algebra",
        "Exact Groups And Evidence Projection",
        "Cataloged-unmodeled Relevance",
        "Scoped Completeness",
        "Checker And Matrix Integration",
        "Compatibility And Non-scope",
    ):
        assert f"## {heading}\n" in spec
    for term in (
        "UNDECLARED",
        "AMBIGUOUS",
        "CONFLICT",
        "SELECTED",
        "EXACT_MATCHABLE",
        "DIRECT_SQL_SURFACE",
        "CONSISTENT_DUPLICATE",
        "EVIDENCE_CONFLICT",
        "CATALOGED_UNMODELED",
        "pietto.capability-inspection.v1",
        "Unknown(NOT_EVIDENCED)",
    ):
        assert term in spec
    roadmap = ROADMAP.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    assert "Phase 57 is active, Slices 1–12 are completed, and Slice 13 is current" in (
        roadmap
    )
    assert "| Slices 1–12 | `COMPLETED` |" in status
    assert "| Slice 13 | `CURRENT` |" in status
    assert "| Phase 58 | `UNSTARTED / NOT AUTHORIZED` |" in status
    assert "| Next | `PHASE57_SLICE13_END_TO_END` |" in status
    assert "does not authorize Phase 58" in " ".join(status.split())
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    assert 'f"{prefix}/_project/extension_signature_provider.py"' in package_smoke
    assert '"import pietto._project.extension_signature_provider"' in package_smoke
    assert 'version = "0.1.0"' in (REPO_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )
