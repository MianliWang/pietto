from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast


import _pietto_capability_differential_vectors as vectors
import pietto._project.capability_pure_boundary as pure_boundary
import pietto.semantic.capability_aggregates as aggregates
import pietto.semantic.capability_contexts as contexts
import pietto.semantic.capability_inventory as inventory
import pietto.semantic.capability_signatures as signatures
import pietto.semantic.capability_windows as windows
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityDeclaration,
    ExtensionCatalogAvailabilityOwner,
)
from pietto._project.model import ProjectRoot
from pietto.semantic.capability_facts import (
    CapabilityFact,
)
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionCatalogCompletenessClaim,
    ExtensionCatalogCompletenessClaimKind,
    ExtensionCatalogDeclarationTypeUse,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogEntryEvidence,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogExposure,
    ExtensionCatalogIdentity,
    ExtensionCatalogLookupScope,
    ExtensionCatalogMatchability,
    ExtensionCatalogMetadata,
    ExtensionCatalogReference,
    ExtensionCatalogSchemaVersion,
    ExtensionCatalogSourceOccurrence,
    ExtensionCatalogSourceProvenance,
    ExtensionCatalogTarget,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    ExtensionCatalogUnmodeledReason,
    ExtensionScalarFunctionCatalogEntry,
    PostgreSQLCallableDeclaration,
    PostgreSQLCallableIdentity,
    PostgreSQLNullCallBehavior,
    PostgreSQLParallelSafety,
    PostgreSQLVolatility,
    _construct_extension_catalog,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase57-extension-catalog-declaration-availability-selection-v1.md"
)
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)


def _reference(
    name: str = "synthetic",
    *,
    release: str = "catalog-release-1",
) -> ExtensionCatalogReference:
    return ExtensionCatalogReference(
        ExtensionCatalogIdentity("org.example.catalogs", name),
        release,
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


def _metadata(
    reference: ExtensionCatalogReference,
    target: ExtensionCatalogTarget,
    source_labels: tuple[str, ...] = (),
) -> ExtensionCatalogMetadata:
    owner = ExtensionCatalogReference(
        ExtensionCatalogIdentity(
            reference.identity.namespace,
            reference.identity.name,
        ),
        reference.release,
    )
    return ExtensionCatalogMetadata(
        ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
        reference,
        target,
        tuple(
            ExtensionCatalogSourceOccurrence(
                owner,
                position,
                ExtensionCatalogSourceProvenance(
                    "example/upstream",
                    label,
                    f"sql/{label}.sql:declaration",
                    f"curation-{label}",
                ),
            )
            for position, label in enumerate(source_labels)
        ),
    )


def _artifact(
    *,
    reference: ExtensionCatalogReference | None = None,
    target: ExtensionCatalogTarget | None = None,
    source_labels: tuple[str, ...] = (),
    entries: tuple[object, ...] = (),
    claims: tuple[ExtensionCatalogCompletenessClaim, ...] = (),
) -> ConstructedExtensionCatalog:
    result = _construct_extension_catalog(
        _metadata(reference or _reference(), target or _target(), source_labels),
        cast(Any, entries),
        claims,
    )
    assert result.ok and result.catalog is not None
    assert result.failures == ()
    return result.catalog


def _builtin(name: str = "text") -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
        physical_name=name,
    )


def _exact(name: str = "text") -> ExtensionCatalogDeclarationTypeUse:
    return ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.EXACT,
        exact_type=_builtin(name),
    )


def _callable(name: str) -> PostgreSQLCallableDeclaration:
    text = _exact()
    return PostgreSQLCallableDeclaration(
        name,
        (text,),
        PostgreSQLCallableIdentity(name, (_builtin(),)),
    )


def _exact_evidence(position: int) -> ExtensionCatalogEntryEvidence:
    return ExtensionCatalogEntryEvidence(
        ExtensionCatalogMatchability.EXACT_MATCHABLE,
        ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
        (),
        (position,),
    )


def _scalar_entry(
    position: int,
    volatility: PostgreSQLVolatility,
) -> ExtensionScalarFunctionCatalogEntry:
    return ExtensionScalarFunctionCatalogEntry(
        _callable("rich"),
        _exact(),
        PostgreSQLNullCallBehavior.STRICT,
        volatility,
        PostgreSQLParallelSafety.SAFE,
        False,
        False,
        False,
        False,
        _exact_evidence(position),
    )


def _unmodeled_entry(position: int) -> ExtensionScalarFunctionCatalogEntry:
    reason = ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM
    input_type = ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.UNMODELED,
        source_spelling="opaque[]",
        unmodeled_reasons=(reason,),
    )
    return ExtensionScalarFunctionCatalogEntry(
        PostgreSQLCallableDeclaration("complex", (input_type,), None),
        _exact(),
        PostgreSQLNullCallBehavior.UNKNOWN,
        PostgreSQLVolatility.UNKNOWN,
        PostgreSQLParallelSafety.UNKNOWN,
        False,
        False,
        False,
        False,
        ExtensionCatalogEntryEvidence(
            ExtensionCatalogMatchability.CATALOGED_UNMODELED,
            ExtensionCatalogExposure.UNCLASSIFIED,
            (reason,),
            (position,),
        ),
    )


def _rich_artifact(
    reference: ExtensionCatalogReference,
    target: ExtensionCatalogTarget,
) -> ConstructedExtensionCatalog:
    scope = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity("missing", (_builtin(),)),
    )
    return _artifact(
        reference=reference,
        target=target,
        source_labels=("first", "second", "third"),
        entries=(
            _scalar_entry(0, PostgreSQLVolatility.IMMUTABLE),
            _scalar_entry(1, PostgreSQLVolatility.VOLATILE),
            _unmodeled_entry(2),
        ),
        claims=(
            ExtensionCatalogCompletenessClaim(
                scope,
                ExtensionCatalogCompletenessClaimKind.COMPLETE,
                (0,),
            ),
            ExtensionCatalogCompletenessClaim(
                scope,
                ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
                (1,),
            ),
        ),
    )


def _availability(
    *declarations: tuple[
        ExtensionCatalogAvailabilityOwner,
        ConstructedExtensionCatalog,
        ProjectRoot | None,
    ],
) -> DeclaredExtensionCatalogAvailability:
    return DeclaredExtensionCatalogAvailability(
        tuple(
            ExtensionCatalogAvailabilityDeclaration(
                owner,
                position,
                catalog,
                project,
            )
            for position, (owner, catalog, project) in enumerate(declarations)
        )
    )


def _provider_families() -> tuple[tuple[CapabilityFact, ...], ...]:
    return (
        inventory._CAPABILITY_FACTS,
        signatures._CAPABILITY_SIGNATURE_FACTS,
        contexts._CAPABILITY_CONTEXT_FACTS,
        aggregates._AGGREGATE_CAPABILITY_FACTS,
        windows._WINDOW_CAPABILITY_FACTS,
    )


def _corpus_digest() -> str:
    rows: list[str] = []
    for vector in vectors.differential_vectors():
        outcome = pure_boundary.evaluate_capability_document(vector.document)
        matched = (
            outcome.status is vector.expected_status
            and outcome.record_position == vector.expected_record_position
            and outcome.field_position == vector.expected_field_position
            and outcome.canonical_bytes == vector.expected_bytes
        )
        record = outcome.record_position if outcome.record_position is not None else "-"
        field = outcome.field_position if outcome.field_position is not None else "-"
        rows.append(
            f"{vector.vector_id}:{outcome.status.value}:{record}:{field}:{matched}"
        )
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()
