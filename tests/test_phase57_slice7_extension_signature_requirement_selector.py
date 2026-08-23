from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
import hashlib
import inspect
from pathlib import Path
from typing import Any, Callable, cast

import pytest

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_checking as checking
import pietto._project.capability_matrix as matrix
import pietto._project.capability_pure_boundary as pure_boundary
import pietto.semantic as semantic_package
import pietto.semantic.capability_providers as providers
import pietto.semantic.extension_signature_requirements as selectors
from pietto._project.capability_inspection import CapabilityInspectionFormat
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityDeclaration,
    ExtensionCatalogAvailabilityOwner,
    ExtensionCatalogSelectionOutcome,
    select_extension_catalog,
)
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityKey,
    CapabilityReasonCode,
)
from pietto.semantic.capability_lookup import Unknown, lookup_capability
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
)
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogIdentity,
    ExtensionCatalogLookupScope,
    ExtensionCatalogMetadata,
    ExtensionCatalogReference,
    ExtensionCatalogSchemaVersion,
    ExtensionCatalogTarget,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    PostgreSQLCallableIdentity,
    PostgreSQLCastIdentity,
    PostgreSQLOperatorArity,
    PostgreSQLOperatorIdentity,
    _construct_extension_catalog,
)
from pietto.semantic.extension_signature_requirements import (
    ExtensionSignatureDialectFamilyBridge,
    ExtensionSignatureRequirementSelector,
    ExtensionSignatureRequirementSelectorOccurrence,
    ExtensionSignatureRequirementSelectors,
    extension_signature_dialect_family_bridge,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase57-extension-signature-requirement-selector-v1.md"
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)


def _key(
    name: str,
    *,
    dialect: str | None = "postgresql",
    extension: str | None = "example_extension",
    operation: str = "semantic request",
    operands: tuple[str, ...] = (),
    context: str | None = None,
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject=name,
        operation=operation,
        operands=operands,
        context=context,
        dialect=dialect,
        extension=extension,
    )


def _requirements(
    *keys: CapabilityKey,
    name: str = "requirements",
) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity("consumer", name)
    return CapabilityRequirementCollection(
        identity,
        tuple(
            CapabilityRequirementOccurrence(identity, position, key)
            for position, key in enumerate(keys)
        ),
    )


def _builtin(name: str = "text") -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
        physical_name=name,
    )


def _native(
    name: str = "example_type",
    owner: str = "example_extension",
) -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
        physical_name=name,
        extension_identity=owner,
    )


def _scope(
    family: ExtensionCatalogEntryFamily,
    *,
    owner: str = "example_extension",
    cast_native_source: bool = False,
) -> ExtensionCatalogLookupScope:
    if family is ExtensionCatalogEntryFamily.NATIVE_TYPE:
        identity: object = _native(owner=owner)
    elif family in {
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        ExtensionCatalogEntryFamily.AGGREGATE,
    }:
        identity = PostgreSQLCallableIdentity("example_fn", (_native(owner=owner),))
    elif family is ExtensionCatalogEntryFamily.OPERATOR:
        identity = PostgreSQLOperatorIdentity(
            "##",
            PostgreSQLOperatorArity.BINARY,
            (_native(owner=owner), _builtin()),
        )
    else:
        identity = PostgreSQLCastIdentity(
            _native(owner=owner) if cast_native_source else _builtin(),
            _builtin() if cast_native_source else _native(owner=owner),
        )
    return ExtensionCatalogLookupScope(family, cast(Any, identity))


def _selector(
    family: ExtensionCatalogEntryFamily,
    *,
    owner: str = "example_extension",
    cast_native_source: bool = False,
) -> ExtensionSignatureRequirementSelector:
    return ExtensionSignatureRequirementSelector(
        _scope(
            family,
            owner=owner,
            cast_native_source=cast_native_source,
        )
    )


def _selector_occurrence(
    position: int,
    selector: ExtensionSignatureRequirementSelector,
) -> ExtensionSignatureRequirementSelectorOccurrence:
    return ExtensionSignatureRequirementSelectorOccurrence(position, selector)


def _artifact() -> ConstructedExtensionCatalog:
    reference = ExtensionCatalogReference(
        ExtensionCatalogIdentity("org.example", "synthetic"),
        "catalog-release",
    )
    metadata = ExtensionCatalogMetadata(
        ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
        reference,
        ExtensionCatalogTarget(
            "PostgreSQL",
            "17",
            "example_extension",
            "extension-release",
        ),
        (),
    )
    result = _construct_extension_catalog(metadata, (), ())
    assert result.ok and result.catalog is not None
    return result.catalog


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


def test_capability_key_stays_exactly_seven_field_semantic_identity() -> None:
    assert tuple(field.name for field in fields(CapabilityKey)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    first = _key(
        "semantic:subject",
        operation="physical-looking|but-semantic",
        operands=("builtin:text", "extension:example_extension:type"),
        context="cast:source->target",
    )
    equal = _key(
        "semantic:subject",
        operation="physical-looking|but-semantic",
        operands=("builtin:text", "extension:example_extension:type"),
        context="cast:source->target",
    )
    changed = _key(
        "semantic:subject",
        operation="physical-looking|but-semantic",
        operands=("builtin:text", "extension:example_extension:other"),
        context="cast:source->target",
    )
    assert first == equal
    assert hash(first) == hash(equal)
    assert first != changed
    assert not hasattr(first, "family")
    assert not hasattr(first, "release")
    assert not hasattr(first, "selector")


def test_closed_postgresql_dialect_family_bridge_preserves_both_vocabularies() -> None:
    bridge = extension_signature_dialect_family_bridge("postgresql")
    assert bridge is ExtensionSignatureDialectFamilyBridge.POSTGRESQL
    assert bridge.value == "postgresql"
    assert bridge.database_family == "PostgreSQL"

    key = _key("bridge")
    target = ExtensionCatalogTarget(
        "PostgreSQL",
        "17",
        "example_extension",
        "release",
    )
    assert key.dialect == "postgresql"
    assert target.database_family == "PostgreSQL"
    assert bridge.database_family == target.database_family

    for invalid in (
        "PostgreSQL",
        "POSTGRESQL",
        "postgres",
        " postgresql ",
        "postgresql ",
        None,
    ):
        assert extension_signature_dialect_family_bridge(invalid) is None


def test_sidecar_binds_all_five_families_in_requirement_source_order() -> None:
    ordinary = CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int")
    families = tuple(ExtensionCatalogEntryFamily)
    requirements = _requirements(
        ordinary,
        *(_key(f"semantic-{family.value}") for family in families),
    )
    occurrences = tuple(
        _selector_occurrence(position, _selector(family))
        for position, family in enumerate(families, start=1)
    )
    sidecar = ExtensionSignatureRequirementSelectors(requirements, occurrences)

    assert sidecar.requirements is requirements
    assert sidecar.occurrences == occurrences
    assert tuple(item.requirement_position for item in sidecar.occurrences) == (
        1,
        2,
        3,
        4,
        5,
    )
    assert tuple(item.selector.scope.family for item in sidecar.occurrences) == families
    assert (
        sidecar.occurrences[1].selector.scope.identity
        == sidecar.occurrences[2].selector.scope.identity
    )
    assert (
        sidecar.occurrences[1].selector.scope != sidecar.occurrences[2].selector.scope
    )


def test_selector_coverage_rejects_missing_duplicate_extra_and_foreign_positions() -> (
    None
):
    first = _selector(ExtensionCatalogEntryFamily.NATIVE_TYPE)
    second = _selector(ExtensionCatalogEntryFamily.SCALAR_FUNCTION)
    requirements = _requirements(_key("first"), _key("second"))

    with pytest.raises(ValueError, match="cover each requirement exactly once"):
        ExtensionSignatureRequirementSelectors(
            requirements,
            (_selector_occurrence(0, first),),
        )
    with pytest.raises(ValueError, match="cover each requirement exactly once"):
        ExtensionSignatureRequirementSelectors(
            requirements,
            (
                _selector_occurrence(0, first),
                _selector_occurrence(0, first),
                _selector_occurrence(1, second),
            ),
        )
    with pytest.raises(ValueError, match="resolve a requirement"):
        ExtensionSignatureRequirementSelectors(
            requirements,
            (
                _selector_occurrence(0, first),
                _selector_occurrence(1, second),
                _selector_occurrence(2, second),
            ),
        )

    non_extension = _requirements(
        CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int")
    )
    assert ExtensionSignatureRequirementSelectors(non_extension, ()).occurrences == ()
    with pytest.raises(ValueError, match="EXTENSION_SIGNATURE requirement"):
        ExtensionSignatureRequirementSelectors(
            non_extension,
            (_selector_occurrence(0, first),),
        )


def test_selector_bound_requirement_requires_mapped_dialect_and_extension() -> None:
    selector = _selector(ExtensionCatalogEntryFamily.NATIVE_TYPE)
    no_dialect = _requirements(_key("no-dialect", dialect=None, extension=None))
    with pytest.raises(ValueError, match="requires a dialect"):
        ExtensionSignatureRequirementSelectors(
            no_dialect,
            (_selector_occurrence(0, selector),),
        )

    no_extension = _requirements(_key("no-extension", extension=None))
    with pytest.raises(ValueError, match="requires an extension"):
        ExtensionSignatureRequirementSelectors(
            no_extension,
            (_selector_occurrence(0, selector),),
        )


@pytest.mark.parametrize(
    "dialect",
    ("PostgreSQL", "POSTGRESQL", "postgres", " postgresql ", "postgresql "),
)
def test_selector_binding_rejects_every_unmapped_dialect_without_normalization(
    dialect: str,
) -> None:
    requirements = _requirements(_key("unmapped", dialect=dialect))
    with pytest.raises(ValueError, match="no dialect-family bridge"):
        ExtensionSignatureRequirementSelectors(
            requirements,
            (_selector_occurrence(0, _selector(ExtensionCatalogEntryFamily.CAST)),),
        )


@pytest.mark.parametrize(
    "selector_factory",
    (
        lambda: _selector(ExtensionCatalogEntryFamily.NATIVE_TYPE, owner="foreign"),
        lambda: _selector(
            ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
            owner="foreign",
        ),
        lambda: _selector(ExtensionCatalogEntryFamily.AGGREGATE, owner="foreign"),
        lambda: _selector(ExtensionCatalogEntryFamily.OPERATOR, owner="foreign"),
        lambda: _selector(ExtensionCatalogEntryFamily.CAST, owner="foreign"),
        lambda: _selector(
            ExtensionCatalogEntryFamily.CAST,
            owner="foreign",
            cast_native_source=True,
        ),
    ),
)
def test_extension_native_owner_must_match_bound_key_extension(
    selector_factory: Callable[[], ExtensionSignatureRequirementSelector],
) -> None:
    requirements = _requirements(_key("owner"))
    with pytest.raises(ValueError, match="type owner must match"):
        ExtensionSignatureRequirementSelectors(
            requirements,
            (_selector_occurrence(0, selector_factory()),),
        )


def test_builtin_only_selectors_need_no_physical_extension_owner() -> None:
    requirements = _requirements(_key("builtin-only"))
    callable_identity = PostgreSQLCallableIdentity("builtin_fn", (_builtin(),))
    selector = ExtensionSignatureRequirementSelector(
        ExtensionCatalogLookupScope(
            ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
            callable_identity,
        )
    )
    sidecar = ExtensionSignatureRequirementSelectors(
        requirements,
        (_selector_occurrence(0, selector),),
    )
    assert sidecar.occurrences[0].selector is selector


def test_semantic_keys_and_physical_selectors_remain_independent_authorities() -> None:
    shared_selector = _selector(ExtensionCatalogEntryFamily.OPERATOR)
    two_keys = _requirements(
        _key("semantic-one", operation="one"),
        _key("semantic-two", operation="two"),
    )
    sidecar = ExtensionSignatureRequirementSelectors(
        two_keys,
        (
            _selector_occurrence(0, shared_selector),
            _selector_occurrence(1, shared_selector),
        ),
    )
    assert two_keys.occurrences[0].key != two_keys.occurrences[1].key
    assert sidecar.occurrences[0].selector is sidecar.occurrences[1].selector

    semantic_key = _key("same-semantic-key")
    first_requirements = _requirements(semantic_key, name="first")
    second_requirements = _requirements(semantic_key, name="second")
    first = ExtensionSignatureRequirementSelectors(
        first_requirements,
        (_selector_occurrence(0, _selector(ExtensionCatalogEntryFamily.NATIVE_TYPE)),),
    )
    second = ExtensionSignatureRequirementSelectors(
        second_requirements,
        (_selector_occurrence(0, _selector(ExtensionCatalogEntryFamily.CAST)),),
    )
    assert (
        first_requirements.occurrences[0].key == second_requirements.occurrences[0].key
    )
    assert first.occurrences[0].selector != second.occurrences[0].selector


def test_selector_module_has_no_hidden_key_grammar_provider_or_runtime_behavior() -> (
    None
):
    source = inspect.getsource(selectors)
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
        "pietto.semantic.capability_facts",
        "pietto.semantic.capability_profiles",
        "pietto.semantic.extension_catalog",
    }
    for forbidden in (
        ".subject",
        ".operation",
        ".operands",
        ".context",
        ".lower(",
        ".casefold(",
        ".title(",
        ".capitalize(",
        ".split(",
        "registry",
        "alias",
        "fallback",
        "capability_providers",
        "capability_checking",
        "capability_matrix",
        "select_extension_catalog",
        "pathlib",
        "import os",
        "subprocess",
        "requests",
        "socket",
        "open(",
        "getcwd",
        "environ",
    ):
        assert forbidden not in source.lower()


def test_legacy_provider_and_checker_paths_remain_unbound_and_unknown() -> None:
    key = CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject="legacy",
        operation="lookup",
    )
    inputs = providers.canonical_capability_provider_inputs(key)
    assert inputs.facts == ()
    assert inputs.domain_complete is False
    assert lookup_capability(
        key,
        inputs.facts,
        domain_complete=inputs.domain_complete,
        unknown_reason=inputs.unknown_reason,
    ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert "extension_signature_requirements" not in inspect.getsource(checking)
    assert "extension_signature_requirements" not in inspect.getsource(matrix)


def test_predecessor_artifact_selection_inspection_and_corpus_remain_frozen() -> None:
    artifact = _artifact()
    before_bytes = artifact.canonical_bytes
    before_digest = artifact.content_sha256
    selection = select_extension_catalog(
        DeclaredExtensionCatalogAvailability(
            (
                ExtensionCatalogAvailabilityDeclaration(
                    ExtensionCatalogAvailabilityOwner.COMPILER,
                    0,
                    artifact,
                ),
            )
        ),
        artifact.metadata.target,
    )
    requirements = _requirements(_key("frozen"))
    ExtensionSignatureRequirementSelectors(
        requirements,
        (_selector_occurrence(0, _selector(ExtensionCatalogEntryFamily.CAST)),),
    )
    assert selection.outcome is ExtensionCatalogSelectionOutcome.SELECTED
    assert selection.selected_catalog is artifact
    assert artifact.canonical_bytes == before_bytes
    assert artifact.content_sha256 == before_digest
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


def test_selector_carriers_are_private_frozen_slotted_and_packaged() -> None:
    carriers = (
        ExtensionSignatureRequirementSelector,
        ExtensionSignatureRequirementSelectorOccurrence,
        ExtensionSignatureRequirementSelectors,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert "__dict__" not in carrier.__slots__
    requirements = _requirements(_key("immutable"))
    sidecar = ExtensionSignatureRequirementSelectors(
        requirements,
        (_selector_occurrence(0, _selector(ExtensionCatalogEntryFamily.CAST)),),
    )
    with pytest.raises(FrozenInstanceError):
        sidecar.occurrences = ()  # pyright: ignore[reportAttributeAccessIssue]
    assert selectors.__all__ == ()
    for module in (pietto, semantic_package, project_package):
        assert all(not hasattr(module, carrier.__name__) for carrier in carriers)
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    assert 'f"{prefix}/semantic/extension_signature_requirements.py"' in package_smoke
    assert '"import pietto.semantic.extension_signature_requirements"' in package_smoke


def test_revised_slice7_spec_route_lifecycle_and_slice8_boundary_are_exact() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for heading in (
        "Semantic Key And Typed Selector",
        "Closed PostgreSQL Dialect-family Bridge",
        "Requirement Binding And Coverage",
        "Five-family Selector Authority",
        "Extension-owner Consistency",
        "Revised Slice 8 Handoff",
    ):
        assert f"## {heading}\n" in spec
    for term in (
        "postgresql",
        "PostgreSQL",
        "NATIVE_TYPE",
        "SCALAR_FUNCTION",
        "AGGREGATE",
        "OPERATOR",
        "CAST",
        "Unknown(NOT_EVIDENCED)",
        "13",
    ):
        assert term in spec

    roadmap = ROADMAP.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    assert "Phase 57 is active, Slices 1–12 are completed, and Slice 13 is current" in (
        roadmap
    )
    assert "The revised route has exactly 13 slices" in " ".join(roadmap.split())
    assert "| Slices 1–12 | `COMPLETED` |" in status
    assert "| Slice 13 | `CURRENT` |" in status
    assert "| Phase 58 | `UNSTARTED / NOT AUTHORIZED` |" in status
    assert "| Next | `PHASE57_SLICE13_END_TO_END` |" in status
    assert "does not authorize Phase 58" in " ".join(status.split())
