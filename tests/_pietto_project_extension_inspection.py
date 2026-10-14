from __future__ import annotations

from pathlib import Path


import _pietto_project_extension_catalog as slice5
import _pietto_project_extension_availability as slice6
import _pietto_project_extension_provider as slice8
from pietto._project.extension_catalog_availability import (
    ExtensionCatalogAvailabilityOwner,
    ExtensionCatalogSelectionResult,
    select_extension_catalog,
)
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspection,
    ExtensionCatalogInspectionCatalog,
    ExtensionCatalogInspectionFactSet,
    build_extension_catalog_inspection,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderContext,
    ExtensionSignatureProviderSelectionOccurrence,
)
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityKey,
)
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
)
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogExposure,
    ExtensionCatalogLookupScope,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    PostgreSQLCallableIdentity,
)
from pietto.semantic.extension_catalog_pg_trgm import (
    PG_TRGM_V16_POSTGRESQL18_CATALOG,
)
from pietto.semantic.extension_catalog_pgvector import (
    PGVECTOR_V086_POSTGRESQL18_CATALOG,
)
from pietto.semantic.extension_signature_requirements import (
    ExtensionSignatureRequirementSelector,
    ExtensionSignatureRequirementSelectorOccurrence,
    ExtensionSignatureRequirementSelectors,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase57-extension-catalog-inspection-v1.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_INSPECTION_BYTES = 540042
EXPECTED_INSPECTION_SHA256 = (
    "7710033bd7b1b939bee3f3da1f4d354b7d53db385a36e61f538bc4aacf8fb4ce"
)
EXPECTED_PGVECTOR_SHA256 = (
    "686e68fe9d60c20cb276e2b26007d310ff8877a5b4a8274e5c9194116fa74654"
)
EXPECTED_PG_TRGM_SHA256 = (
    "09eb10a0660a05ca180d43a23f1eda7aaf4b6198f5de249591317194cc9576b7"
)
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)


def _builtin(name: str) -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
        physical_name=name,
    )


def _native(name: str, owner: str) -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
        physical_name=name,
        extension_identity=owner,
    )


def _scalar_scope(
    name: str,
    *inputs: ExtensionCatalogTypeReference,
) -> ExtensionCatalogLookupScope:
    return ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity(name, inputs),
    )


def _key(
    name: str,
    *,
    extension: str,
    operation: str = "exact signature",
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject=name,
        operation=operation,
        operands=("semantic", "text", "only"),
        context="typed selector is separate",
        dialect="postgresql",
        extension=extension,
    )


def _requirements(
    *keys: CapabilityKey,
    name: str = "slice11",
) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity("consumer", name)
    return CapabilityRequirementCollection(
        identity,
        tuple(
            CapabilityRequirementOccurrence(identity, position, key)
            for position, key in enumerate(keys)
        ),
    )


def _context(
    requirements: CapabilityRequirementCollection,
    *bindings: tuple[
        int,
        ExtensionCatalogLookupScope,
        ExtensionCatalogSelectionResult,
    ],
) -> ExtensionSignatureProviderContext:
    return ExtensionSignatureProviderContext(
        ExtensionSignatureRequirementSelectors(
            requirements,
            tuple(
                ExtensionSignatureRequirementSelectorOccurrence(
                    position,
                    ExtensionSignatureRequirementSelector(scope),
                )
                for position, scope, _selection in bindings
            ),
        ),
        tuple(
            ExtensionSignatureProviderSelectionOccurrence(position, selection)
            for position, _scope, selection in bindings
        ),
    )


def _production_context(
    *,
    rebuild: bool = False,
    reverse_allocation: bool = False,
) -> ExtensionSignatureProviderContext:
    if rebuild and reverse_allocation:
        pg_trgm = inspection_module_for_test_pg_trgm()
        pgvector = inspection_module_for_test_pgvector()
    elif rebuild:
        pgvector = inspection_module_for_test_pgvector()
        pg_trgm = inspection_module_for_test_pg_trgm()
    else:
        pgvector = PGVECTOR_V086_POSTGRESQL18_CATALOG
        pg_trgm = PG_TRGM_V16_POSTGRESQL18_CATALOG
    availability = slice6._availability(
        (ExtensionCatalogAvailabilityOwner.COMPILER, pgvector, None),
        (ExtensionCatalogAvailabilityOwner.COMPILER, pg_trgm, None),
    )
    vector_selection = select_extension_catalog(availability, pgvector.metadata.target)
    trgm_selection = select_extension_catalog(availability, pg_trgm.metadata.target)
    requirements = _requirements(
        _key("pgvector direct", extension="vector"),
        _key("pg_trgm direct", extension="pg_trgm"),
        _key("pg_trgm unmodeled", extension="pg_trgm"),
        _key("pg_trgm support", extension="pg_trgm"),
        name="production-golden",
    )
    vector = _native("vector", "vector")
    text = _builtin("text")
    return _context(
        requirements,
        (
            0,
            _scalar_scope("l2_distance", vector, vector),
            vector_selection,
        ),
        (1, _scalar_scope("similarity", text, text), trgm_selection),
        (2, _scalar_scope("show_trgm", text), trgm_selection),
        (3, _scalar_scope("similarity_op", text, text), trgm_selection),
    )


def inspection_module_for_test_pgvector() -> ConstructedExtensionCatalog:
    import pietto.semantic.extension_catalog_pgvector as module

    return module._build_pgvector_catalog()


def inspection_module_for_test_pg_trgm() -> ConstructedExtensionCatalog:
    import pietto.semantic.extension_catalog_pg_trgm as module

    return module._build_pg_trgm_catalog()


def _inspection(
    context: ExtensionSignatureProviderContext,
) -> ExtensionCatalogInspectionFactSet:
    return build_extension_catalog_inspection(context)


def _catalog(
    inspection: ExtensionCatalogInspection,
    extension: str,
) -> ExtensionCatalogInspectionCatalog:
    return next(
        catalog
        for catalog in inspection.catalogs
        if catalog.target.extension_identity == extension
    )


def _corpus_digest() -> str:
    return slice5._corpus_digest()


def _synthetic_scope(name: str = "shared") -> ExtensionCatalogLookupScope:
    return _scalar_scope(name, _builtin("text"))


def _direct_catalog(
    *,
    reference_name: str = "direct",
    database_release: str = "17.4",
    result: str = "text",
    exposure: ExtensionCatalogExposure = ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
) -> ConstructedExtensionCatalog:
    return slice8._catalog(
        (slice5._scalar_entry((0,), result=result, exposure=exposure),),
        target=slice6._target(database_release=database_release),
        reference=slice6._reference(reference_name),
        source_count=1,
    )
