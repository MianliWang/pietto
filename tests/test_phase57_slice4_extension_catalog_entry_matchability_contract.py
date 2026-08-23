from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
import hashlib
import inspect
from pathlib import Path
from typing import Any, cast
import unicodedata

import pytest

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_inspection as inspection
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
    ExtensionAggregateCatalogEntry,
    ExtensionCastCatalogEntry,
    ExtensionCatalogDeclarationTypeUse,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogEntryEvidence,
    ExtensionCatalogExposure,
    ExtensionCatalogMatchability,
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
from pietto.semantic.generic_compatibility import LogicalTypeIdentity
from pietto.semantic.model import TypeKind


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT / "docs/spec/phase57-extension-catalog-entry-matchability-contract-v1.md"
)
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)
EXPECTED_RETAINED_ROUTE = (
    (
        "5",
        "Deterministic catalog construction, ordering/conflicts, scoped completeness, canonical bytes, and content SHA-256",
    ),
    (
        "6",
        "Compiler/project catalog declaration and availability, exact PostgreSQL-release × extension-release selection",
    ),
    (
        "7",
        "Structured EXTENSION_SIGNATURE requirement selector authority",
    ),
    (
        "8",
        "EXTENSION_SIGNATURE provider integration using typed selectors, target-scoped catalog lookup, exact checking propagation, and matrix compatibility",
    ),
    ("9", "First concrete production catalog: pgvector"),
    (
        "10",
        "Second concrete production catalog: pg_trgm, plus ltree lightweight representability probe and PostGIS representability/stress audit without full-support claims",
    ),
    (
        "11",
        "Separate private extension-catalog inspection/canonical representation and Phase 58/59 provenance readiness",
    ),
    (
        "12",
        "Extension-catalog pure boundary, differential vectors, Python 3.12/3.13, hash-seed, relocation, and E2E hardening",
    ),
    ("13", "Completion audit and Phase 58 handoff"),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table_rows(section: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
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


def _native(
    name: str = "native_type",
    extension_identity: str = "example_extension",
) -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
        physical_name=name,
        extension_identity=extension_identity,
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
    *,
    matchability: ExtensionCatalogMatchability = (
        ExtensionCatalogMatchability.EXACT_MATCHABLE
    ),
    exposure: ExtensionCatalogExposure = ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
    reasons: tuple[ExtensionCatalogUnmodeledReason, ...] = (),
    positions: tuple[int, ...] = (0,),
) -> ExtensionCatalogEntryEvidence:
    return ExtensionCatalogEntryEvidence(
        matchability,
        exposure,
        reasons,
        positions,
    )


def _callable_declaration(
    name: str,
    input_types: tuple[ExtensionCatalogDeclarationTypeUse, ...],
) -> PostgreSQLCallableDeclaration:
    references = tuple(
        type_use.exact_type
        for type_use in input_types
        if type_use.kind is ExtensionCatalogDeclarationTypeUseKind.EXACT
    )
    identity = (
        PostgreSQLCallableIdentity(name, cast(Any, references))
        if len(references) == len(input_types)
        else None
    )
    return PostgreSQLCallableDeclaration(name, input_types, identity)


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


def test_declaration_type_use_preserves_exact_or_unmodeled_shape_without_forgery() -> (
    None
):
    exact = _exact(_builtin("text"))
    array = _unmodeled(
        " text[] ",
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    )
    modified = _unmodeled(
        " vector(3) ",
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    )
    polymorphic = _unmodeled(
        " anycompatiblearray ",
        ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE,
    )
    assert tuple(ExtensionCatalogDeclarationTypeUseKind) == (
        ExtensionCatalogDeclarationTypeUseKind.EXACT,
        ExtensionCatalogDeclarationTypeUseKind.UNMODELED,
    )
    assert tuple(
        field.name for field in fields(ExtensionCatalogDeclarationTypeUse)
    ) == (
        "kind",
        "exact_type",
        "source_spelling",
        "unmodeled_reasons",
    )
    assert exact.exact_type == _builtin("text")
    assert exact.source_spelling is None
    assert array.source_spelling == " text[] "
    assert modified.source_spelling == " vector(3) "
    assert polymorphic.source_spelling == " anycompatiblearray "
    assert array.exact_type is modified.exact_type is polymorphic.exact_type is None
    assert unicodedata.normalize("NFD", "týpe[]") != "týpe[]"
    assert _unmodeled(
        "týpe[]",
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    ) != _unmodeled(
        unicodedata.normalize("NFD", "týpe[]"),
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    )
    with pytest.raises(ValueError, match="requires an exact type"):
        ExtensionCatalogDeclarationTypeUse(ExtensionCatalogDeclarationTypeUseKind.EXACT)
    with pytest.raises(ValueError, match="forbids unmodeled data"):
        ExtensionCatalogDeclarationTypeUse(
            ExtensionCatalogDeclarationTypeUseKind.EXACT,
            exact_type=_builtin(),
            source_spelling="text",
        )
    with pytest.raises(ValueError, match="requires reasons"):
        ExtensionCatalogDeclarationTypeUse(
            ExtensionCatalogDeclarationTypeUseKind.UNMODELED,
            source_spelling="text[]",
        )


def test_matchability_exposure_and_source_evidence_are_orthogonal_and_fail_closed() -> (
    None
):
    assert tuple(ExtensionCatalogMatchability) == (
        ExtensionCatalogMatchability.EXACT_MATCHABLE,
        ExtensionCatalogMatchability.CATALOGED_UNMODELED,
    )
    assert tuple(ExtensionCatalogExposure) == (
        ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
        ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT,
        ExtensionCatalogExposure.UNCLASSIFIED,
    )
    exact_support = _evidence(exposure=ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT)
    unmodeled_direct = _evidence(
        matchability=ExtensionCatalogMatchability.CATALOGED_UNMODELED,
        exposure=ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
        reasons=(ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,),
        positions=(2, 1, 2),
    )
    unclassified = _evidence(exposure=ExtensionCatalogExposure.UNCLASSIFIED)
    assert exact_support.matchability is ExtensionCatalogMatchability.EXACT_MATCHABLE
    assert unmodeled_direct.exposure is ExtensionCatalogExposure.DIRECT_SQL_SURFACE
    assert unmodeled_direct.source_positions == (2, 1, 2)
    assert unclassified.exposure is ExtensionCatalogExposure.UNCLASSIFIED
    with pytest.raises(ValueError, match="forbids unmodeled reasons"):
        _evidence(reasons=(ExtensionCatalogUnmodeledReason.DEFAULT_ARGUMENTS,))
    with pytest.raises(ValueError, match="requires reasons"):
        _evidence(matchability=ExtensionCatalogMatchability.CATALOGED_UNMODELED)
    with pytest.raises(ValueError, match="non-negative exact integers"):
        _evidence(positions=(True,))
    with pytest.raises(ValueError, match="at least one source position"):
        _evidence(positions=())
    with pytest.raises(ValueError, match="ordered iterable"):
        ExtensionCatalogEntryEvidence(
            ExtensionCatalogMatchability.EXACT_MATCHABLE,
            ExtensionCatalogExposure.UNCLASSIFIED,
            (),
            cast(Any, {1, 2}),
        )


def test_native_type_entry_preserves_physical_identity_and_optional_logical_mapping() -> (
    None
):
    entry = ExtensionNativeTypeCatalogEntry(
        _native("native_vector"),
        _logical("Text"),
        _evidence(exposure=ExtensionCatalogExposure.UNCLASSIFIED),
    )
    assert tuple(field.name for field in fields(ExtensionNativeTypeCatalogEntry)) == (
        "type_identity",
        "logical_mapping",
        "evidence",
    )
    assert (
        entry.type_identity.kind is ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE
    )
    assert entry.logical_mapping is not None
    assert (
        entry.logical_mapping.kind is ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL
    )
    for forbidden in ("coercion", "promotion", "typmod", "implicit"):
        assert not hasattr(entry, forbidden)
    with pytest.raises(ValueError, match="EXTENSION_NATIVE"):
        ExtensionNativeTypeCatalogEntry(_builtin(), None, _evidence())
    with pytest.raises(ValueError, match="PIETTO_LOGICAL"):
        ExtensionNativeTypeCatalogEntry(_native(), _builtin(), _evidence())


def test_scalar_function_entry_preserves_semantic_metadata_and_conservative_shape() -> (
    None
):
    text_use = _exact(_builtin("text"))
    exact = ExtensionScalarFunctionCatalogEntry(
        _callable_declaration("normalize", (text_use,)),
        text_use,
        PostgreSQLNullCallBehavior.STRICT,
        PostgreSQLVolatility.IMMUTABLE,
        PostgreSQLParallelSafety.SAFE,
        False,
        False,
        False,
        False,
        _evidence(),
    )
    assert tuple(
        field.name for field in fields(ExtensionScalarFunctionCatalogEntry)
    ) == (
        "declaration",
        "result_type",
        "null_call_behavior",
        "volatility",
        "parallel_safety",
        "has_default_arguments",
        "is_variadic",
        "returns_set",
        "has_polymorphic_or_pseudo_types",
        "evidence",
    )
    assert exact.declaration.identity == PostgreSQLCallableIdentity(
        "normalize",
        (_builtin("text"),),
    )
    assert tuple(PostgreSQLNullCallBehavior) == (
        PostgreSQLNullCallBehavior.UNKNOWN,
        PostgreSQLNullCallBehavior.CALLED_ON_NULL_INPUT,
        PostgreSQLNullCallBehavior.STRICT,
    )
    assert tuple(PostgreSQLVolatility) == (
        PostgreSQLVolatility.UNKNOWN,
        PostgreSQLVolatility.IMMUTABLE,
        PostgreSQLVolatility.STABLE,
        PostgreSQLVolatility.VOLATILE,
    )
    assert tuple(PostgreSQLParallelSafety) == (
        PostgreSQLParallelSafety.UNKNOWN,
        PostgreSQLParallelSafety.UNSAFE,
        PostgreSQLParallelSafety.RESTRICTED,
        PostgreSQLParallelSafety.SAFE,
    )

    input_type = _unmodeled(
        "text[]",
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    )
    result_type = _unmodeled(
        "record",
        ExtensionCatalogUnmodeledReason.TABLE_OR_COMPOSITE_RETURN,
    )
    reasons = (
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
        ExtensionCatalogUnmodeledReason.TABLE_OR_COMPOSITE_RETURN,
        ExtensionCatalogUnmodeledReason.DEFAULT_ARGUMENTS,
        ExtensionCatalogUnmodeledReason.VARIADIC_ARGUMENTS,
        ExtensionCatalogUnmodeledReason.SET_RETURNING,
        ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE,
    )
    complex_entry = ExtensionScalarFunctionCatalogEntry(
        _callable_declaration("complex", (input_type,)),
        result_type,
        PostgreSQLNullCallBehavior.UNKNOWN,
        PostgreSQLVolatility.UNKNOWN,
        PostgreSQLParallelSafety.UNKNOWN,
        True,
        True,
        True,
        True,
        _evidence(
            matchability=ExtensionCatalogMatchability.CATALOGED_UNMODELED,
            reasons=reasons,
        ),
    )
    assert complex_entry.declaration.identity is None
    assert complex_entry.evidence.unmodeled_reasons == reasons
    with pytest.raises(ValueError, match="cannot be exact-matchable"):
        ExtensionScalarFunctionCatalogEntry(
            _callable_declaration("defaulted", (text_use,)),
            text_use,
            PostgreSQLNullCallBehavior.UNKNOWN,
            PostgreSQLVolatility.UNKNOWN,
            PostgreSQLParallelSafety.UNKNOWN,
            True,
            False,
            False,
            False,
            _evidence(),
        )


def test_aggregate_entry_distinguishes_ordinary_ordered_and_hypothetical_forms() -> (
    None
):
    value = _exact(_builtin("int8"))
    ordinary = ExtensionAggregateCatalogEntry(
        PostgreSQLAggregateKind.ORDINARY,
        _callable_declaration("sum", (value,)),
        value,
        PostgreSQLParallelSafety.SAFE,
        False,
        False,
        _evidence(),
    )
    assert tuple(PostgreSQLAggregateKind) == (
        PostgreSQLAggregateKind.ORDINARY,
        PostgreSQLAggregateKind.ORDERED_SET,
        PostgreSQLAggregateKind.HYPOTHETICAL_SET,
    )
    assert (
        ordinary.evidence.matchability is ExtensionCatalogMatchability.EXACT_MATCHABLE
    )
    for kind in (
        PostgreSQLAggregateKind.ORDERED_SET,
        PostgreSQLAggregateKind.HYPOTHETICAL_SET,
    ):
        entry = ExtensionAggregateCatalogEntry(
            kind,
            _callable_declaration("rank_like", (value,)),
            value,
            PostgreSQLParallelSafety.UNKNOWN,
            True,
            False,
            _evidence(
                matchability=ExtensionCatalogMatchability.CATALOGED_UNMODELED,
                reasons=(
                    ExtensionCatalogUnmodeledReason.ORDERED_SET_OR_HYPOTHETICAL_SET_AGGREGATE,
                    ExtensionCatalogUnmodeledReason.DIRECT_ARGUMENTS,
                ),
            ),
        )
        assert entry.kind is kind
    with pytest.raises(ValueError, match="cannot be exact-matchable"):
        ExtensionAggregateCatalogEntry(
            PostgreSQLAggregateKind.ORDERED_SET,
            _callable_declaration("ordered", (value,)),
            value,
            PostgreSQLParallelSafety.UNKNOWN,
            False,
            False,
            _evidence(),
        )
    for forbidden in ("transition", "combine", "moving", "planner", "lowering"):
        assert not hasattr(ordinary, forbidden)


def test_operator_entry_preserves_identity_result_and_unmodeled_declarations() -> None:
    native = _exact(_native("vector"))
    result = _exact(_builtin("float8"))
    identity = PostgreSQLOperatorIdentity(
        "<->",
        PostgreSQLOperatorArity.BINARY,
        (_native("vector"), _native("vector")),
    )
    exact = ExtensionOperatorCatalogEntry(
        "<->",
        PostgreSQLOperatorArity.BINARY,
        (native, native),
        identity,
        result,
        _evidence(),
    )
    assert exact.identity is identity
    assert exact.result_type is result
    unmodeled_result = _unmodeled(
        "record",
        ExtensionCatalogUnmodeledReason.TABLE_OR_COMPOSITE_RETURN,
    )
    cataloged = ExtensionOperatorCatalogEntry(
        "=>",
        PostgreSQLOperatorArity.UNARY,
        (native,),
        PostgreSQLOperatorIdentity(
            "=>",
            PostgreSQLOperatorArity.UNARY,
            (_native("vector"),),
        ),
        unmodeled_result,
        _evidence(
            matchability=ExtensionCatalogMatchability.CATALOGED_UNMODELED,
            reasons=(ExtensionCatalogUnmodeledReason.TABLE_OR_COMPOSITE_RETURN,),
        ),
    )
    assert cataloged.identity is not None
    for forbidden in ("commutator", "negator", "ranking", "operator_class"):
        assert not hasattr(exact, forbidden)


def test_cast_entry_preserves_direction_context_method_and_unmodeled_source() -> None:
    source = _exact(_builtin("text"))
    target = _exact(_native("vector"))
    exact = ExtensionCastCatalogEntry(
        source,
        target,
        PostgreSQLCastIdentity(_builtin("text"), _native("vector")),
        PostgreSQLCastContext.EXPLICIT_ONLY,
        PostgreSQLCastMethod.FUNCTION,
        _evidence(),
    )
    assert tuple(PostgreSQLCastContext) == (
        PostgreSQLCastContext.UNKNOWN,
        PostgreSQLCastContext.EXPLICIT_ONLY,
        PostgreSQLCastContext.ASSIGNMENT,
        PostgreSQLCastContext.IMPLICIT,
    )
    assert tuple(PostgreSQLCastMethod) == (
        PostgreSQLCastMethod.UNKNOWN,
        PostgreSQLCastMethod.FUNCTION,
        PostgreSQLCastMethod.BINARY,
        PostgreSQLCastMethod.INOUT,
    )
    assert exact.identity == PostgreSQLCastIdentity(_builtin("text"), _native("vector"))
    array_source = _unmodeled(
        "text[]",
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    )
    cataloged = ExtensionCastCatalogEntry(
        array_source,
        target,
        None,
        PostgreSQLCastContext.UNKNOWN,
        PostgreSQLCastMethod.UNKNOWN,
        _evidence(
            matchability=ExtensionCatalogMatchability.CATALOGED_UNMODELED,
            reasons=(ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,),
        ),
    )
    assert cataloged.source_type.source_spelling == "text[]"
    assert cataloged.identity is None
    assert (
        ExtensionCastCatalogEntry(
            target,
            source,
            PostgreSQLCastIdentity(_native("vector"), _builtin("text")),
            PostgreSQLCastContext.EXPLICIT_ONLY,
            PostgreSQLCastMethod.FUNCTION,
            _evidence(),
        )
        != exact
    )
    for forbidden in ("search", "ranking", "execute", "implementation_function"):
        assert not hasattr(exact, forbidden)


def test_five_entry_families_are_private_frozen_typed_and_non_executable() -> None:
    carriers = (
        ExtensionNativeTypeCatalogEntry,
        ExtensionScalarFunctionCatalogEntry,
        ExtensionAggregateCatalogEntry,
        ExtensionOperatorCatalogEntry,
        ExtensionCastCatalogEntry,
    )
    assert len(carriers) == 5
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert getattr(carrier, "__dataclass_params__").frozen
        assert "__dict__" not in carrier.__slots__
    evidence = _evidence()
    with pytest.raises(FrozenInstanceError):
        evidence.exposure = (  # pyright: ignore[reportAttributeAccessIssue]
            ExtensionCatalogExposure.UNCLASSIFIED
        )
    symbols = tuple(carrier.__name__ for carrier in carriers) + (
        "ExtensionCatalogDeclarationTypeUse",
        "ExtensionCatalogMatchability",
        "ExtensionCatalogExposure",
    )
    for module in (pietto, semantic_package, project_package):
        assert all(not hasattr(module, symbol) for symbol in symbols)


def test_module_has_no_provider_runtime_lowering_or_concrete_entries() -> None:
    source = inspect.getsource(extension_catalog)
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported_modules == {
        "__future__",
        "collections.abc",
        "dataclasses",
        "enum",
        "pathlib",
        "pietto.semantic.generic_compatibility",
    }
    for forbidden in (
        "canonical_capability_provider_inputs",
        "lookup_capability",
        "catalog_complete",
        "content_digest",
        "database connection",
        "create extension",
        "subprocess",
        "requests",
        "socket",
        "getcwd",
        "environ",
        "sql snippet",
        "lowering template",
        "emitter callback",
        "renderer hook",
        "pgvector",
        "pg_trgm",
        "postgis",
        "timescaledb",
    ):
        assert forbidden not in source.lower()
    assert extension_catalog.__all__ == ()
    for path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/semantic/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
    ):
        assert "extension_catalog" not in _read(path)
    assert "extension_catalog" not in inspect.getsource(providers)
    assert "extension_catalog" not in inspect.getsource(inspection)
    assert "extension_catalog" not in inspect.getsource(package_manifest)


def test_slice2_slice3_and_phase56_predecessors_remain_exact() -> None:
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
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )
    corpus = vectors.differential_vectors()
    accepted = tuple(
        vector
        for vector in corpus
        if vector.expected_status is pure_boundary.CapabilityPureStatus.OK
    )
    assert (len(corpus), len(accepted), len(corpus) - len(accepted)) == (
        125,
        16,
        109,
    )
    assert _corpus_digest() == EXPECTED_CORPUS_DIGEST
    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_spec_lifecycle_route_and_package_smoke_are_exact() -> None:
    spec = _read(SPEC)
    families = _section(spec, "Five Typed Entry Families")
    for name in (
        "ExtensionNativeTypeCatalogEntry",
        "ExtensionScalarFunctionCatalogEntry",
        "ExtensionAggregateCatalogEntry",
        "ExtensionOperatorCatalogEntry",
        "ExtensionCastCatalogEntry",
    ):
        assert f"`{name}`" in families
    assert _table_rows(_section(spec, "Retained Slice Ownership"))[1:] == (
        EXPECTED_RETAINED_ROUTE
    )
    distinctions = " ".join(_section(spec, "State Distinctions").split())
    for term in (
        "unmodeled is not invalid",
        "unmodeled is not absent",
        "unmodeled is not unsupported",
        "unmodeled is not conflict",
    ):
        assert term in distinctions
    non_scope = " ".join(_section(spec, "Exact Non-scope").split())
    for term in (
        "catalog construction",
        "scoped completeness",
        "canonical bytes",
        "provider routing",
        "concrete extension entries",
        "runtime",
        "lowering",
        "public output",
    ):
        assert term in non_scope

    roadmap = _read(ROADMAP)
    assert "Phase 57 is active, Slices 1–9 are completed, and Slice 10 is current" in (
        roadmap
    )
    status_rows = _table_rows(_read(STATUS))[1:]
    assert status_rows == (
        ("Package and CLI", "`0.1.0`"),
        ("Phase 55", "`COMPLETED`"),
        ("Phase 56", "`COMPLETED`"),
        ("Phase 57", "`ACTIVE`"),
        ("Slices 1–9", "`COMPLETED`"),
        ("Slice 10", "`CURRENT`"),
        ("Next", "`PHASE57_SLICE10_END_TO_END`"),
    )
    status = _read(STATUS)
    assert "Live Git and natural exact-head CI own\nSlice 10 completion" in status
    assert "does\nnot authorize Slice 11" in status
    package_smoke = _read(PACKAGE_SMOKE)
    assert 'f"{prefix}/semantic/extension_catalog.py"' in package_smoke
    assert '"import pietto.semantic.extension_catalog"' in package_smoke
