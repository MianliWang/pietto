from __future__ import annotations

from pathlib import Path
from typing import Any, cast


import _pietto_project_extension_catalog as slice5  # noqa: F401
import _pietto_project_extension_availability as slice6
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityOwner,
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
    CapabilityDomain,
    CapabilityKey,
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
    ExtensionCatalogDeclarationTypeUse,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogEntryEvidence,
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
    PostgreSQLCallableDeclaration,
    PostgreSQLCallableIdentity,
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
