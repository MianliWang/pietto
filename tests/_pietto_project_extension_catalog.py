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
from pietto.semantic.capability_facts import (
    CapabilityFact,
)
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionAggregateCatalogEntry,
    ExtensionCastCatalogEntry,
    ExtensionCatalogCompletenessClaim,
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
    _construct_extension_catalog,
)
from pietto.semantic.generic_compatibility import LogicalTypeIdentity
from pietto.semantic.model import TypeKind


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase57-extension-catalog-construction-completeness-canonical-v1.md"
)
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)


def _reference(
    namespace: str = "org.example.catalogs",
    name: str = "synthetic",
    release: str = "catalog-release-1",
) -> ExtensionCatalogReference:
    return ExtensionCatalogReference(
        ExtensionCatalogIdentity(namespace, name),
        release,
    )


def _target(
    *,
    database_release: str = "17.4",
    extension_release: str = "2.0",
) -> ExtensionCatalogTarget:
    return ExtensionCatalogTarget(
        "PostgreSQL",
        database_release,
        "example_extension",
        extension_release,
    )


def _provenance(
    position: int,
    *,
    authority: str = "example/upstream",
) -> ExtensionCatalogSourceProvenance:
    return ExtensionCatalogSourceProvenance(
        authority,
        f"revision-{position}",
        f"sql/source-{position}.sql:declaration",
        f"curation-{position}",
    )


def _metadata(
    *,
    namespace: str = "org.example.catalogs",
    name: str = "synthetic",
    catalog_release: str = "catalog-release-1",
    database_release: str = "17.4",
    extension_release: str = "2.0",
    source_authority: str = "example/upstream",
    source_count: int = 3,
    provenance_order: tuple[int, ...] | None = None,
) -> ExtensionCatalogMetadata:
    catalog = _reference(namespace, name, catalog_release)
    reconstructed_owner = _reference(namespace, name, catalog_release)
    order = provenance_order or tuple(range(source_count))
    return ExtensionCatalogMetadata(
        ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
        catalog,
        _target(
            database_release=database_release,
            extension_release=extension_release,
        ),
        tuple(
            ExtensionCatalogSourceOccurrence(
                reconstructed_owner,
                position,
                _provenance(source_position, authority=source_authority),
            )
            for position, source_position in enumerate(order)
        ),
    )


def _logical(name: str = "Text") -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL,
        logical_type=LogicalTypeIdentity(name=name, kind=TypeKind.BUILTIN),
    )


def _builtin(name: str = "text") -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
        physical_name=name,
    )


def _native(name: str = "native") -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
        physical_name=name,
        extension_identity="example_extension",
    )


def _exact(
    reference: ExtensionCatalogTypeReference,
) -> ExtensionCatalogDeclarationTypeUse:
    return ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.EXACT,
        exact_type=reference,
    )


def _unmodeled(
    spelling: str,
    *reasons: ExtensionCatalogUnmodeledReason,
) -> ExtensionCatalogDeclarationTypeUse:
    return ExtensionCatalogDeclarationTypeUse(
        ExtensionCatalogDeclarationTypeUseKind.UNMODELED,
        source_spelling=spelling,
        unmodeled_reasons=reasons,
    )


def _evidence(
    positions: tuple[int, ...] = (0,),
    *,
    exposure: ExtensionCatalogExposure = ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
    matchability: ExtensionCatalogMatchability = (
        ExtensionCatalogMatchability.EXACT_MATCHABLE
    ),
    reasons: tuple[ExtensionCatalogUnmodeledReason, ...] = (),
) -> ExtensionCatalogEntryEvidence:
    return ExtensionCatalogEntryEvidence(
        matchability,
        exposure,
        reasons,
        positions,
    )


def _declaration(
    name: str,
    inputs: tuple[ExtensionCatalogDeclarationTypeUse, ...],
) -> PostgreSQLCallableDeclaration:
    physical = tuple(
        type_use.exact_type
        for type_use in inputs
        if type_use.kind is ExtensionCatalogDeclarationTypeUseKind.EXACT
    )
    identity = (
        PostgreSQLCallableIdentity(name, cast(Any, physical))
        if len(physical) == len(inputs)
        else None
    )
    return PostgreSQLCallableDeclaration(name, inputs, identity)


def _native_entry(
    positions: tuple[int, ...] = (0,),
    *,
    mapping: str | None = "Text",
) -> ExtensionNativeTypeCatalogEntry:
    return ExtensionNativeTypeCatalogEntry(
        _native(),
        _logical(mapping) if mapping is not None else None,
        _evidence(positions),
    )


def _scalar_entry(
    positions: tuple[int, ...] = (0,),
    *,
    name: str = "shared",
    result: str = "text",
    exposure: ExtensionCatalogExposure = ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
    null_call: PostgreSQLNullCallBehavior = PostgreSQLNullCallBehavior.STRICT,
    volatility: PostgreSQLVolatility = PostgreSQLVolatility.IMMUTABLE,
    parallel: PostgreSQLParallelSafety = PostgreSQLParallelSafety.SAFE,
) -> ExtensionScalarFunctionCatalogEntry:
    text = _exact(_builtin("text"))
    return ExtensionScalarFunctionCatalogEntry(
        _declaration(name, (text,)),
        _exact(_builtin(result)),
        null_call,
        volatility,
        parallel,
        False,
        False,
        False,
        False,
        _evidence(positions, exposure=exposure),
    )


def _aggregate_entry(
    positions: tuple[int, ...] = (0,),
    *,
    parallel: PostgreSQLParallelSafety = PostgreSQLParallelSafety.SAFE,
) -> ExtensionAggregateCatalogEntry:
    text = _exact(_builtin("text"))
    return ExtensionAggregateCatalogEntry(
        PostgreSQLAggregateKind.ORDINARY,
        _declaration("shared", (text,)),
        _exact(_builtin("text")),
        parallel,
        False,
        False,
        _evidence(positions),
    )


def _operator_entry(
    positions: tuple[int, ...] = (0,),
    *,
    result: str = "float8",
) -> ExtensionOperatorCatalogEntry:
    operand = _exact(_native())
    return ExtensionOperatorCatalogEntry(
        "<->",
        PostgreSQLOperatorArity.BINARY,
        (operand, operand),
        PostgreSQLOperatorIdentity(
            "<->",
            PostgreSQLOperatorArity.BINARY,
            (_native(), _native()),
        ),
        _exact(_builtin(result)),
        _evidence(positions),
    )


def _cast_entry(
    positions: tuple[int, ...] = (0,),
    *,
    context: PostgreSQLCastContext = PostgreSQLCastContext.EXPLICIT_ONLY,
    method: PostgreSQLCastMethod = PostgreSQLCastMethod.FUNCTION,
) -> ExtensionCastCatalogEntry:
    return ExtensionCastCatalogEntry(
        _exact(_builtin("text")),
        _exact(_native()),
        PostgreSQLCastIdentity(_builtin("text"), _native()),
        context,
        method,
        _evidence(positions),
    )


def _unmodeled_entry(
    spelling: str = " VecTór(\n3) ",
    reason: ExtensionCatalogUnmodeledReason = (
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM
    ),
    positions: tuple[int, ...] = (0,),
) -> ExtensionScalarFunctionCatalogEntry:
    unmodeled = _unmodeled(spelling, reason)
    return ExtensionScalarFunctionCatalogEntry(
        _declaration("complex", (unmodeled,)),
        _exact(_builtin("text")),
        PostgreSQLNullCallBehavior.UNKNOWN,
        PostgreSQLVolatility.UNKNOWN,
        PostgreSQLParallelSafety.UNKNOWN,
        False,
        False,
        False,
        False,
        _evidence(
            positions,
            matchability=ExtensionCatalogMatchability.CATALOGED_UNMODELED,
            reasons=(reason,),
        ),
    )


def _scope(
    family: ExtensionCatalogEntryFamily = ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
    name: str = "missing",
) -> ExtensionCatalogLookupScope:
    return ExtensionCatalogLookupScope(
        family,
        PostgreSQLCallableIdentity(name, (_builtin("text"),)),
    )


def _artifact(
    entries: tuple[object, ...],
    claims: tuple[ExtensionCatalogCompletenessClaim, ...] = (),
    *,
    metadata: ExtensionCatalogMetadata | None = None,
) -> ConstructedExtensionCatalog:
    result = _construct_extension_catalog(
        metadata or _metadata(),
        cast(Any, entries),
        claims,
    )
    assert result.ok
    assert result.failures == ()
    assert result.catalog is not None
    return result.catalog


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
