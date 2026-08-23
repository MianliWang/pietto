from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
import hashlib
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_inspection as capability_inspection
import pietto._project.capability_pure_boundary as pure_boundary
import pietto._project.package_manifest as package_manifest
import pietto.semantic as semantic_package
import pietto.semantic.capability_aggregates as aggregates
import pietto.semantic.capability_contexts as contexts
import pietto.semantic.capability_inventory as inventory
import pietto.semantic.capability_providers as providers
import pietto.semantic.capability_signatures as signatures
import pietto.semantic.capability_windows as windows
import pietto.semantic.extension_catalog as extension_catalog
from pietto._project.capability_inspection import CapabilityInspectionFormat
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
)
from pietto.semantic.capability_lookup import Unknown, lookup_capability
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionAggregateCatalogEntry,
    ExtensionCastCatalogEntry,
    ExtensionCatalogCompletenessClaim,
    ExtensionCatalogCompletenessClaimKind,
    ExtensionCatalogCompletenessState,
    ExtensionCatalogConstructionResult,
    ExtensionCatalogDeclarationTypeUse,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogEntryEvidence,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogExactEntryGroupState,
    ExtensionCatalogExposure,
    ExtensionCatalogIdentity,
    ExtensionCatalogLookupScope,
    ExtensionCatalogMatchability,
    ExtensionCatalogMetadata,
    ExtensionCatalogReference,
    ExtensionCatalogSchemaVersion,
    ExtensionCatalogSourceOccurrence,
    ExtensionCatalogSourceProvenance,
    ExtensionCatalogStructuralFailureKind,
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
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
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


def test_constructed_catalog_is_immutable_and_reconstructed_owner_is_value_exact() -> (
    None
):
    first_metadata = _metadata()
    second_metadata = _metadata()
    assert first_metadata.catalog == first_metadata.source_occurrences[0].owner
    assert first_metadata.catalog is not first_metadata.source_occurrences[0].owner
    assert first_metadata.catalog == second_metadata.catalog
    assert first_metadata.catalog is not second_metadata.catalog

    first = _artifact((_scalar_entry(),), metadata=first_metadata)
    second = _artifact((_scalar_entry(),), metadata=second_metadata)
    assert first.entries == second.entries
    assert first.canonical_bytes == second.canonical_bytes
    assert first.content_sha256 == second.content_sha256
    assert first.metadata.source_occurrences == first_metadata.source_occurrences
    assert tuple(field.name for field in fields(ConstructedExtensionCatalog)) == (
        "metadata",
        "entries",
        "exact_entry_groups",
        "completeness_claims",
        "completeness_groups",
        "canonical_bytes",
        "content_sha256",
    )
    assert is_dataclass(ConstructedExtensionCatalog)
    assert "__dict__" not in ConstructedExtensionCatalog.__slots__
    with pytest.raises(FrozenInstanceError):
        first.content_sha256 = "0" * 64  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(TypeError, match="canonical construction"):
        ConstructedExtensionCatalog()
    with pytest.raises(TypeError, match="canonical construction"):
        ExtensionCatalogConstructionResult()


def test_structural_failures_prevent_artifact_bytes_and_preserve_failure_multiplicity() -> (
    None
):
    metadata = _metadata(source_count=1)
    scope = _scope()
    entry = _scalar_entry((3, 3))
    claim = ExtensionCatalogCompletenessClaim(
        scope,
        ExtensionCatalogCompletenessClaimKind.COMPLETE,
        (4,),
    )
    result = _construct_extension_catalog(metadata, (entry,), (claim,))
    assert not result.ok
    assert result.catalog is None
    assert tuple(failure.kind for failure in result.failures) == (
        ExtensionCatalogStructuralFailureKind.ENTRY_SOURCE_POSITION_OUT_OF_RANGE,
        ExtensionCatalogStructuralFailureKind.ENTRY_SOURCE_POSITION_OUT_OF_RANGE,
        ExtensionCatalogStructuralFailureKind.COMPLETENESS_SOURCE_POSITION_OUT_OF_RANGE,
    )
    assert tuple(failure.source_position for failure in result.failures) == (3, 3, 4)

    invalid_collections = _construct_extension_catalog(
        metadata,
        cast(Any, {_scalar_entry()}),
        cast(Any, {claim}),
    )
    assert tuple(failure.kind for failure in invalid_collections.failures) == (
        ExtensionCatalogStructuralFailureKind.INVALID_ENTRY_COLLECTION,
        ExtensionCatalogStructuralFailureKind.INVALID_COMPLETENESS_COLLECTION,
    )

    forged = _metadata(source_count=1)
    occurrence = forged.source_occurrences[0]
    object.__setattr__(occurrence, "position", 2)
    object.__setattr__(occurrence, "owner", _reference(name="foreign"))
    owner_failures = _construct_extension_catalog(forged, (), ())
    assert owner_failures.catalog is None
    assert tuple(failure.kind for failure in owner_failures.failures) == (
        ExtensionCatalogStructuralFailureKind.SOURCE_POSITION_SEQUENCE_MISMATCH,
        ExtensionCatalogStructuralFailureKind.SOURCE_OWNER_MISMATCH,
    )


def test_five_family_exact_grouping_distinguishes_duplicates_and_conflicts() -> None:
    entries = (
        _native_entry(),
        _scalar_entry((0,)),
        _aggregate_entry(),
        _operator_entry(),
        _cast_entry(),
    )
    unique = _artifact(entries)
    assert tuple(ExtensionCatalogEntryFamily) == (
        ExtensionCatalogEntryFamily.NATIVE_TYPE,
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        ExtensionCatalogEntryFamily.AGGREGATE,
        ExtensionCatalogEntryFamily.OPERATOR,
        ExtensionCatalogEntryFamily.CAST,
    )
    assert {group.scope.family for group in unique.exact_entry_groups} == set(
        ExtensionCatalogEntryFamily
    )
    assert all(
        group.state is ExtensionCatalogExactEntryGroupState.UNIQUE
        for group in unique.exact_entry_groups
    )
    callable_groups = tuple(
        group
        for group in unique.exact_entry_groups
        if group.scope.family
        in {
            ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
            ExtensionCatalogEntryFamily.AGGREGATE,
        }
    )
    assert callable_groups[0].scope.identity == callable_groups[1].scope.identity
    assert callable_groups[0].scope != callable_groups[1].scope

    duplicate = _artifact((_scalar_entry((1, 0, 1)), _scalar_entry((0,))))
    duplicate_group = duplicate.exact_entry_groups[0]
    assert (
        duplicate_group.state
        is ExtensionCatalogExactEntryGroupState.CONSISTENT_DUPLICATE
    )
    assert len(duplicate_group.entries) == 2
    assert {entry.evidence.source_positions for entry in duplicate_group.entries} == {
        (0,),
        (1, 0, 1),
    }

    conflict = _artifact(
        (
            _scalar_entry((0,), volatility=PostgreSQLVolatility.IMMUTABLE),
            _scalar_entry((1,), volatility=PostgreSQLVolatility.VOLATILE),
            _scalar_entry((2,), name="unrelated"),
        )
    )
    states = {
        cast(PostgreSQLCallableIdentity, group.scope.identity).sql_name: group.state
        for group in conflict.exact_entry_groups
    }
    assert states == {
        "shared": ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT,
        "unrelated": ExtensionCatalogExactEntryGroupState.UNIQUE,
    }
    shared = next(
        group
        for group in conflict.exact_entry_groups
        if cast(PostgreSQLCallableIdentity, group.scope.identity).sql_name == "shared"
    )
    assert len(shared.entries) == 2
    assert not hasattr(shared, "winner")
    assert not hasattr(shared, "precedence")


def test_every_entry_family_keeps_semantic_payload_conflict_local() -> None:
    catalog = _artifact(
        (
            _native_entry((0,), mapping="Text"),
            _native_entry((1,), mapping=None),
            _scalar_entry((0,), result="text"),
            _scalar_entry(
                (1,),
                result="varchar",
                exposure=ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT,
                null_call=PostgreSQLNullCallBehavior.CALLED_ON_NULL_INPUT,
                volatility=PostgreSQLVolatility.STABLE,
                parallel=PostgreSQLParallelSafety.RESTRICTED,
            ),
            _aggregate_entry((0,), parallel=PostgreSQLParallelSafety.SAFE),
            _aggregate_entry((1,), parallel=PostgreSQLParallelSafety.UNSAFE),
            _operator_entry((0,), result="float8"),
            _operator_entry((1,), result="numeric"),
            _cast_entry((0,)),
            _cast_entry(
                (1,),
                context=PostgreSQLCastContext.IMPLICIT,
                method=PostgreSQLCastMethod.BINARY,
            ),
        )
    )
    assert len(catalog.exact_entry_groups) == 5
    assert all(
        group.state is ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT
        for group in catalog.exact_entry_groups
    )
    assert all(len(group.entries) == 2 for group in catalog.exact_entry_groups)


def test_unmodeled_declarations_are_retained_exactly_without_lookup_identity() -> None:
    spelling = " VecTór(\n3) "
    entry = _unmodeled_entry(spelling)
    catalog = _artifact((entry,))
    assert catalog.entries == (entry,)
    assert catalog.exact_entry_groups == ()
    assert entry.declaration.identity is None
    assert entry.declaration.input_types[0].source_spelling == spelling
    assert spelling.encode("utf-8") in catalog.canonical_bytes

    changed_spelling = _artifact((_unmodeled_entry(" vectór(\n3) "),))
    changed_reason = _artifact(
        (
            _unmodeled_entry(
                spelling,
                ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE,
            ),
        )
    )
    assert changed_spelling.canonical_bytes != catalog.canonical_bytes
    assert changed_reason.canonical_bytes != catalog.canonical_bytes
    assert changed_spelling.content_sha256 != catalog.content_sha256
    assert changed_reason.content_sha256 != catalog.content_sha256


def test_entry_and_completeness_permutations_are_identity_invariant() -> None:
    entries = (
        _scalar_entry((1, 0)),
        _native_entry((0,)),
        _unmodeled_entry(positions=(2,)),
        _operator_entry((1,)),
    )
    claims = (
        ExtensionCatalogCompletenessClaim(
            _scope(name="zeta"),
            ExtensionCatalogCompletenessClaimKind.COMPLETE,
            (0,),
        ),
        ExtensionCatalogCompletenessClaim(
            _scope(name="alpha"),
            ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
            (2, 1),
        ),
    )
    forward = _artifact(entries, claims)
    backward = _artifact(tuple(reversed(entries)), tuple(reversed(claims)))
    assert forward.entries == backward.entries
    assert forward.completeness_claims == backward.completeness_claims
    assert forward.exact_entry_groups == backward.exact_entry_groups
    assert forward.completeness_groups == backward.completeness_groups
    assert forward.canonical_bytes == backward.canonical_bytes
    assert forward.content_sha256 == backward.content_sha256

    source_order_a = _artifact(
        (_scalar_entry((0,)),),
        metadata=_metadata(source_count=2, provenance_order=(0, 1)),
    )
    source_order_b = _artifact(
        (_scalar_entry((0,)),),
        metadata=_metadata(source_count=2, provenance_order=(1, 0)),
    )
    evidence_order_a = _artifact((_scalar_entry((0, 1)),))
    evidence_order_b = _artifact((_scalar_entry((1, 0)),))
    assert source_order_a.canonical_bytes != source_order_b.canonical_bytes
    assert evidence_order_a.canonical_bytes != evidence_order_b.canonical_bytes


def test_callable_operator_and_unmodeled_reason_orders_are_byte_significant() -> None:
    text = _exact(_builtin("text"))
    native = _exact(_native())

    def scalar(
        inputs: tuple[ExtensionCatalogDeclarationTypeUse, ...],
    ) -> ExtensionScalarFunctionCatalogEntry:
        return ExtensionScalarFunctionCatalogEntry(
            _declaration("ordered", inputs),
            text,
            PostgreSQLNullCallBehavior.STRICT,
            PostgreSQLVolatility.IMMUTABLE,
            PostgreSQLParallelSafety.SAFE,
            False,
            False,
            False,
            False,
            _evidence(),
        )

    callable_forward = _artifact((scalar((text, native)),))
    callable_backward = _artifact((scalar((native, text)),))

    def operator(
        operands: tuple[
            ExtensionCatalogDeclarationTypeUse,
            ExtensionCatalogDeclarationTypeUse,
        ],
    ) -> ExtensionOperatorCatalogEntry:
        physical = cast(
            tuple[ExtensionCatalogTypeReference, ExtensionCatalogTypeReference],
            tuple(operand.exact_type for operand in operands),
        )
        return ExtensionOperatorCatalogEntry(
            "<=>",
            PostgreSQLOperatorArity.BINARY,
            operands,
            PostgreSQLOperatorIdentity(
                "<=>",
                PostgreSQLOperatorArity.BINARY,
                physical,
            ),
            text,
            _evidence(),
        )

    operator_forward = _artifact((operator((text, native)),))
    operator_backward = _artifact((operator((native, text)),))

    reasons = (
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
        ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE,
    )

    def complex_entry(
        ordered_reasons: tuple[ExtensionCatalogUnmodeledReason, ...],
    ) -> ExtensionScalarFunctionCatalogEntry:
        unmodeled = _unmodeled("opaque[]", *ordered_reasons)
        return ExtensionScalarFunctionCatalogEntry(
            _declaration("complex_order", (unmodeled,)),
            text,
            PostgreSQLNullCallBehavior.UNKNOWN,
            PostgreSQLVolatility.UNKNOWN,
            PostgreSQLParallelSafety.UNKNOWN,
            False,
            False,
            False,
            False,
            _evidence(
                matchability=ExtensionCatalogMatchability.CATALOGED_UNMODELED,
                reasons=ordered_reasons,
            ),
        )

    reasons_forward = _artifact((complex_entry(reasons),))
    reasons_backward = _artifact((complex_entry(tuple(reversed(reasons))),))

    pairs = (
        (callable_forward, callable_backward),
        (operator_forward, operator_backward),
        (reasons_forward, reasons_backward),
    )
    assert all(
        first.canonical_bytes != second.canonical_bytes for first, second in pairs
    )
    assert all(first.content_sha256 != second.content_sha256 for first, second in pairs)


def test_scoped_completeness_is_family_local_evidence_without_global_authority() -> (
    None
):
    scalar_scope = _scope(ExtensionCatalogEntryFamily.SCALAR_FUNCTION, "missing")
    aggregate_scope = _scope(ExtensionCatalogEntryFamily.AGGREGATE, "missing")
    unrelated_scope = _scope(ExtensionCatalogEntryFamily.SCALAR_FUNCTION, "other")
    assert scalar_scope.identity == aggregate_scope.identity
    assert scalar_scope != aggregate_scope

    complete_claims = (
        ExtensionCatalogCompletenessClaim(
            scalar_scope,
            ExtensionCatalogCompletenessClaimKind.COMPLETE,
            (0,),
        ),
        ExtensionCatalogCompletenessClaim(
            scalar_scope,
            ExtensionCatalogCompletenessClaimKind.COMPLETE,
            (1, 0, 1),
        ),
        ExtensionCatalogCompletenessClaim(
            aggregate_scope,
            ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
            (2,),
        ),
    )
    corroborated = _artifact((), complete_claims)
    states = {group.scope: group.state for group in corroborated.completeness_groups}
    assert states == {
        scalar_scope: ExtensionCatalogCompletenessState.COMPLETE,
        aggregate_scope: ExtensionCatalogCompletenessState.INCOMPLETE,
    }
    scalar_group = next(
        group
        for group in corroborated.completeness_groups
        if group.scope == scalar_scope
    )
    assert len(scalar_group.claims) == 2
    assert {claim.source_positions for claim in scalar_group.claims} == {
        (0,),
        (1, 0, 1),
    }
    assert unrelated_scope not in states

    conflict = _artifact(
        (),
        (
            *complete_claims,
            ExtensionCatalogCompletenessClaim(
                scalar_scope,
                ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
                (2,),
            ),
        ),
    )
    conflict_state = {
        group.scope: group.state for group in conflict.completeness_groups
    }
    assert conflict_state[scalar_scope] is ExtensionCatalogCompletenessState.CONFLICT
    assert (
        conflict_state[aggregate_scope] is ExtensionCatalogCompletenessState.INCOMPLETE
    )
    assert not hasattr(conflict, "catalog_complete")
    assert not hasattr(conflict, "complete")

    entry_conflict = _artifact(
        (
            _scalar_entry((0,), volatility=PostgreSQLVolatility.IMMUTABLE),
            _scalar_entry((1,), volatility=PostgreSQLVolatility.VOLATILE),
        ),
        (
            ExtensionCatalogCompletenessClaim(
                ExtensionCatalogLookupScope(
                    ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
                    PostgreSQLCallableIdentity("shared", (_builtin("text"),)),
                ),
                ExtensionCatalogCompletenessClaimKind.COMPLETE,
                (2,),
            ),
        ),
    )
    assert (
        entry_conflict.exact_entry_groups[0].state
        is ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT
    )
    assert (
        entry_conflict.completeness_groups[0].state
        is ExtensionCatalogCompletenessState.COMPLETE
    )


def test_canonical_bytes_and_sha256_are_semantic_sensitive_and_ambient_free() -> None:
    scope = _scope()
    claim = ExtensionCatalogCompletenessClaim(
        scope,
        ExtensionCatalogCompletenessClaimKind.COMPLETE,
        (0,),
    )
    baseline = _artifact(
        (_scalar_entry((0,)), _unmodeled_entry(positions=(1,))), (claim,)
    )
    assert (
        baseline.content_sha256 == hashlib.sha256(baseline.canonical_bytes).hexdigest()
    )
    assert len(baseline.content_sha256) == 64
    assert set(baseline.content_sha256) <= set("0123456789abcdef")
    assert baseline.content_sha256.encode() not in baseline.canonical_bytes
    assert b"pietto.extension-catalog.v1" in baseline.canonical_bytes

    variants = (
        _artifact(
            (_scalar_entry((0,)), _unmodeled_entry(positions=(1,))),
            (claim,),
            metadata=_metadata(name="other"),
        ),
        _artifact(
            (_scalar_entry((0,)), _unmodeled_entry(positions=(1,))),
            (claim,),
            metadata=_metadata(catalog_release="catalog-release-2"),
        ),
        _artifact(
            (_scalar_entry((0,)), _unmodeled_entry(positions=(1,))),
            (claim,),
            metadata=_metadata(database_release="18.0"),
        ),
        _artifact(
            (_scalar_entry((0,)), _unmodeled_entry(positions=(1,))),
            (claim,),
            metadata=_metadata(extension_release="3.0"),
        ),
        _artifact(
            (_scalar_entry((0,)), _unmodeled_entry(positions=(1,))),
            (claim,),
            metadata=_metadata(source_authority="other/upstream"),
        ),
        _artifact(
            (_scalar_entry((0,), result="varchar"), _unmodeled_entry(positions=(1,))),
            (claim,),
        ),
        _artifact(
            (
                _scalar_entry(
                    (0,), exposure=ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT
                ),
                _unmodeled_entry(positions=(1,)),
            ),
            (claim,),
        ),
        _artifact((_unmodeled_entry("Other(3)", positions=(0,)),), (claim,)),
        _artifact(
            (
                _unmodeled_entry(
                    reason=ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE,
                    positions=(0,),
                ),
            ),
            (claim,),
        ),
        _artifact((_scalar_entry((1,)), _unmodeled_entry(positions=(0,))), (claim,)),
        _artifact(
            (_scalar_entry((0,)), _unmodeled_entry(positions=(1,))),
            (
                ExtensionCatalogCompletenessClaim(
                    scope,
                    ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
                    (0,),
                ),
            ),
        ),
        _artifact(
            (_scalar_entry((0,)), _unmodeled_entry(positions=(1,))),
            (
                ExtensionCatalogCompletenessClaim(
                    _scope(name="different"),
                    ExtensionCatalogCompletenessClaimKind.COMPLETE,
                    (0,),
                ),
            ),
        ),
        _artifact(
            (
                _scalar_entry((0,), volatility=PostgreSQLVolatility.IMMUTABLE),
                _scalar_entry((1,), volatility=PostgreSQLVolatility.VOLATILE),
                _unmodeled_entry(positions=(1,)),
            ),
            (claim,),
        ),
    )
    assert all(item.canonical_bytes != baseline.canonical_bytes for item in variants)
    assert all(item.content_sha256 != baseline.content_sha256 for item in variants)

    source = inspect.getsource(extension_catalog)
    tree = ast.parse(source)
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported == {
        "__future__",
        "collections.abc",
        "dataclasses",
        "enum",
        "pathlib",
        "pietto.semantic.generic_compatibility",
    }
    for forbidden in (
        "import os",
        "subprocess",
        "requests",
        "socket",
        "getcwd",
        "environ",
        "datetime",
        "timestamp",
        "repr(",
        "id(",
        "database connection",
        "create extension",
    ):
        assert forbidden not in source.lower()


def test_slice5_remains_private_and_preserves_phase56_and_package_boundaries() -> None:
    symbols = (
        "ConstructedExtensionCatalog",
        "ExtensionCatalogConstructionResult",
        "ExtensionCatalogEntryFamily",
        "ExtensionCatalogLookupScope",
        "ExtensionCatalogCompletenessClaim",
        "ExtensionCatalogExactEntryGroup",
        "ExtensionCatalogCompletenessGroup",
    )
    assert extension_catalog.__all__ == ()
    for module in (pietto, semantic_package, project_package):
        assert all(not hasattr(module, symbol) for symbol in symbols)
    for path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/semantic/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
    ):
        assert "extension_catalog" not in path.read_text(encoding="utf-8")

    facts = tuple(fact for family in _provider_families() for fact in family)
    assert tuple(field.name for field in fields(CapabilityKey)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert not any(
        fact.key.domain is CapabilityDomain.EXTENSION_SIGNATURE for fact in facts
    )
    key = CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject="synthetic",
        operation="signature",
    )
    provider = providers.canonical_capability_provider_inputs(key)
    assert provider.facts == ()
    assert provider.domain_complete is False
    assert lookup_capability(
        key,
        provider.facts,
        domain_complete=provider.domain_complete,
        unknown_reason=provider.unknown_reason,
    ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert "extension_catalog" not in inspect.getsource(providers)
    assert "extension_catalog" not in inspect.getsource(capability_inspection)
    assert "extension_catalog" not in inspect.getsource(package_manifest)
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )
    corpus = vectors.differential_vectors()
    accepted = tuple(
        vector
        for vector in corpus
        if vector.expected_status is pure_boundary.CapabilityPureStatus.OK
    )
    assert (len(corpus), len(accepted), len(corpus) - len(accepted)) == (125, 16, 109)
    assert _corpus_digest() == EXPECTED_CORPUS_DIGEST
    assert 'version = "0.1.0"' in (REPO_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    assert 'f"{prefix}/semantic/extension_catalog.py"' in package_smoke
    assert '"import pietto.semantic.extension_catalog"' in package_smoke


def test_slice5_spec_lifecycle_and_slice6_boundary_are_exact() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for heading in (
        "Constructed Catalog",
        "Structural Failures",
        "Exact Entry Grouping",
        "Cataloged-unmodeled Declarations",
        "Scoped Completeness",
        "Canonical Bytes And SHA-256",
        "Privacy And Non-scope",
        "Slice 6 Handoff",
    ):
        assert f"## {heading}\n" in spec
    for term in (
        "UNIQUE",
        "CONSISTENT_DUPLICATE",
        "EVIDENCE_CONFLICT",
        "COMPLETE",
        "INCOMPLETE",
        "CONFLICT",
        "NO_AUTHORITY",
        "8-byte big-endian",
        "UTF-8",
        "SHA-256(canonical catalog bytes)",
    ):
        assert term in spec
    assert "Slice 6 remains unstarted and unauthorized" in spec

    roadmap = ROADMAP.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    assert "Phase 57 is active, Slices 1–8 are completed, and Slice 9 is current" in (
        roadmap
    )
    assert "Slice 5 constructs one deterministic private catalog artifact" in roadmap
    assert "| Slices 1–8 | `COMPLETED` |" in status
    assert "| Slice 9 | `CURRENT` |" in status
    assert "| Next | `PHASE57_SLICE9_END_TO_END` |" in status
    assert "does\nnot authorize Slice 10" in status
