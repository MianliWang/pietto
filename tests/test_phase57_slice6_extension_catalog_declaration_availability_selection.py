from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import hashlib
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_availability as profile_availability
import pietto._project.capability_checking as checking
import pietto._project.capability_inspection as capability_inspection
import pietto._project.capability_matrix as matrix
import pietto._project.capability_pure_boundary as pure_boundary
import pietto._project.extension_catalog_availability as catalog_availability
import pietto._project.package_manifest as package_manifest
import pietto.semantic as semantic_package
import pietto.semantic.capability_aggregates as aggregates
import pietto.semantic.capability_contexts as contexts
import pietto.semantic.capability_inventory as inventory
import pietto.semantic.capability_providers as providers
import pietto.semantic.capability_signatures as signatures
import pietto.semantic.capability_windows as windows
from pietto._project.capability_inspection import CapabilityInspectionFormat
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityDeclaration,
    ExtensionCatalogAvailabilityOwner,
    ExtensionCatalogSelectionCandidate,
    ExtensionCatalogSelectionCandidateIdentity,
    ExtensionCatalogSelectionOutcome,
    ExtensionCatalogSelectionResult,
    select_extension_catalog,
)
from pietto._project.model import ProjectRoot
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
)
from pietto.semantic.capability_lookup import Unknown, lookup_capability
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
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
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
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


def test_declaration_owners_project_root_and_collection_invariants_are_exact() -> None:
    catalog = _artifact()
    project = ProjectRoot("logical/project")
    compiler = ExtensionCatalogAvailabilityDeclaration(
        ExtensionCatalogAvailabilityOwner.COMPILER,
        0,
        catalog,
    )
    declared = ExtensionCatalogAvailabilityDeclaration(
        ExtensionCatalogAvailabilityOwner.PROJECT,
        1,
        catalog,
        project,
    )
    availability = DeclaredExtensionCatalogAvailability((compiler, declared))

    assert tuple(ExtensionCatalogAvailabilityOwner) == (
        ExtensionCatalogAvailabilityOwner.COMPILER,
        ExtensionCatalogAvailabilityOwner.PROJECT,
    )
    assert tuple(
        field.name for field in fields(ExtensionCatalogAvailabilityDeclaration)
    ) == (
        "owner",
        "position",
        "catalog",
        "project",
    )
    assert tuple(field.name for field in fields(ProjectRoot)) == ("path",)
    assert compiler.reference is catalog.metadata.catalog
    assert compiler.target is catalog.metadata.target
    assert compiler.content_sha256 == catalog.content_sha256
    assert availability.declarations == (compiler, declared)
    assert not hasattr(ExtensionCatalogAvailabilityOwner, "PACKAGE")

    with pytest.raises(ValueError, match="forbids a project root"):
        ExtensionCatalogAvailabilityDeclaration(
            ExtensionCatalogAvailabilityOwner.COMPILER,
            0,
            catalog,
            project,
        )
    with pytest.raises(ValueError, match="requires an exact project root"):
        ExtensionCatalogAvailabilityDeclaration(
            ExtensionCatalogAvailabilityOwner.PROJECT,
            0,
            catalog,
        )
    with pytest.raises(ValueError, match="exact owner"):
        ExtensionCatalogAvailabilityDeclaration(cast(Any, "package"), 0, catalog)
    with pytest.raises(ValueError, match="non-negative position"):
        ExtensionCatalogAvailabilityDeclaration(
            ExtensionCatalogAvailabilityOwner.COMPILER,
            True,
            catalog,
        )
    with pytest.raises(ValueError, match="dense and ordered"):
        DeclaredExtensionCatalogAvailability(
            (
                ExtensionCatalogAvailabilityDeclaration(
                    ExtensionCatalogAvailabilityOwner.COMPILER,
                    1,
                    catalog,
                ),
            )
        )


def test_project_applicability_is_exact_additive_and_has_no_path_fallback() -> None:
    target = _target()
    catalog = _artifact(target=target)
    project = ProjectRoot("logical/project")
    equal_project = ProjectRoot("logical/project")
    other = ProjectRoot("logical/other")
    child = ProjectRoot("logical/project/child")
    availability = _availability(
        (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        (ExtensionCatalogAvailabilityOwner.PROJECT, catalog, project),
        (ExtensionCatalogAvailabilityOwner.PROJECT, catalog, other),
    )

    compiler_only = select_extension_catalog(availability, target)
    assert compiler_only.outcome is ExtensionCatalogSelectionOutcome.SELECTED
    assert compiler_only.applicable_declarations == (availability.declarations[0],)
    assert compiler_only.excluded_project_declarations == availability.declarations[1:]

    matching = select_extension_catalog(availability, target, equal_project)
    assert matching.outcome is ExtensionCatalogSelectionOutcome.SELECTED
    assert matching.active_project is equal_project
    assert matching.applicable_declarations == availability.declarations[:2]
    assert matching.excluded_project_declarations == (availability.declarations[2],)
    assert matching.candidates[0].declarations == availability.declarations[:2]

    child_scope = select_extension_catalog(availability, target, child)
    assert child_scope.applicable_declarations == (availability.declarations[0],)
    assert child_scope.excluded_project_declarations == availability.declarations[1:]

    project_only = _availability(
        (ExtensionCatalogAvailabilityOwner.PROJECT, catalog, other),
    )
    undeclared = select_extension_catalog(project_only, target, project)
    assert undeclared.outcome is ExtensionCatalogSelectionOutcome.UNDECLARED
    assert undeclared.applicable_declarations == ()
    assert undeclared.excluded_project_declarations == project_only.declarations


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("database_family", "OtherSQL"),
        ("database_release", "18.0"),
        ("extension_identity", "other_extension"),
        ("extension_release", "3.0"),
    ),
)
def test_selection_requires_all_four_exact_target_dimensions(
    field_name: str,
    replacement: str,
) -> None:
    target = _target()
    catalog = _artifact(target=target)
    availability = _availability(
        (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
    )

    assert (
        select_extension_catalog(availability, target).outcome
        is ExtensionCatalogSelectionOutcome.SELECTED
    )
    changed = replace(target, **{field_name: replacement})
    result = select_extension_catalog(availability, changed)
    assert result.outcome is ExtensionCatalogSelectionOutcome.UNDECLARED
    assert result.applicable_declarations == availability.declarations
    assert result.target_declarations == result.candidates == ()


def test_selected_deduplicates_repeated_and_reconstructed_artifact_authority() -> None:
    target = _target()
    first = _artifact(target=target)
    reconstructed = _artifact(target=_target())
    project = ProjectRoot("logical/project")
    assert first == reconstructed and first is not reconstructed
    assert first.canonical_bytes == reconstructed.canonical_bytes
    assert first.content_sha256 == reconstructed.content_sha256

    declaration_specs = (
        (ExtensionCatalogAvailabilityOwner.COMPILER, first, None),
        (ExtensionCatalogAvailabilityOwner.COMPILER, first, None),
        (ExtensionCatalogAvailabilityOwner.PROJECT, reconstructed, project),
    )
    forward = select_extension_catalog(
        _availability(*declaration_specs),
        target,
        project,
    )
    backward = select_extension_catalog(
        _availability(*reversed(declaration_specs)),
        target,
        project,
    )

    assert (
        forward.outcome is backward.outcome is ExtensionCatalogSelectionOutcome.SELECTED
    )
    assert len(forward.candidates) == len(backward.candidates) == 1
    assert forward.candidates[0].identity == backward.candidates[0].identity
    assert len(forward.candidates[0].declarations) == 3
    assert len(backward.candidates[0].declarations) == 3
    assert forward.selected_catalog == backward.selected_catalog == first
    assert not hasattr(forward, "winner")
    assert not hasattr(forward, "precedence")


def test_undeclared_distinguishes_existence_other_target_and_other_project() -> None:
    target = _target()
    catalog = _artifact(target=target)
    empty = DeclaredExtensionCatalogAvailability(())
    assert (
        select_extension_catalog(empty, target).outcome
        is ExtensionCatalogSelectionOutcome.UNDECLARED
    )

    other_target = replace(target, extension_release="other")
    compiler = _availability(
        (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
    )
    assert (
        select_extension_catalog(compiler, other_target).outcome
        is ExtensionCatalogSelectionOutcome.UNDECLARED
    )

    project_only = _availability(
        (
            ExtensionCatalogAvailabilityOwner.PROJECT,
            catalog,
            ProjectRoot("logical/other"),
        ),
    )
    assert (
        select_extension_catalog(
            project_only,
            target,
            ProjectRoot("logical/project"),
        ).outcome
        is ExtensionCatalogSelectionOutcome.UNDECLARED
    )


def test_distinct_catalog_references_are_ambiguous_without_quality_ranking() -> None:
    target = _target()
    plain = _artifact(reference=_reference("plain"), target=target)
    rich = _rich_artifact(_reference("rich"), target)
    project = ProjectRoot("logical/project")
    availability = _availability(
        (ExtensionCatalogAvailabilityOwner.COMPILER, plain, None),
        (ExtensionCatalogAvailabilityOwner.PROJECT, rich, project),
    )
    result = select_extension_catalog(availability, target, project)

    assert result.outcome is ExtensionCatalogSelectionOutcome.AMBIGUOUS
    assert result.selected_catalog is None
    assert len(result.candidates) == 2
    assert {candidate.catalog for candidate in result.candidates} == {plain, rich}
    assert result.target_declarations == availability.declarations
    assert any(
        group.state is ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT
        for group in rich.exact_entry_groups
    )
    assert any(
        group.state is ExtensionCatalogCompletenessState.CONFLICT
        for group in rich.completeness_groups
    )


def test_same_digest_does_not_alias_distinct_catalog_references() -> None:
    target = _target()
    first_reference = _reference("first")
    second_reference = _reference("second")
    same_digest = "0" * 64
    assert ExtensionCatalogSelectionCandidateIdentity(
        first_reference,
        target,
        same_digest,
    ) != ExtensionCatalogSelectionCandidateIdentity(
        second_reference,
        target,
        same_digest,
    )

    first = _artifact(reference=first_reference, target=target)
    second = _artifact(reference=second_reference, target=target)
    object.__setattr__(second, "content_sha256", first.content_sha256)
    result = select_extension_catalog(
        _availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, first, None),
            (ExtensionCatalogAvailabilityOwner.COMPILER, second, None),
        ),
        target,
    )
    assert result.outcome is ExtensionCatalogSelectionOutcome.AMBIGUOUS
    assert len(result.candidates) == 2
    assert {candidate.identity.content_sha256 for candidate in result.candidates} == {
        first.content_sha256
    }


def test_coordinate_content_conflict_is_stronger_than_additional_ambiguity() -> None:
    target = _target()
    reference = _reference("conflicted")
    first = _artifact(reference=reference, target=target)
    second = _artifact(
        reference=_reference("conflicted"),
        target=_target(),
        source_labels=("different",),
    )
    additional = _artifact(reference=_reference("additional"), target=target)
    project = ProjectRoot("logical/project")
    availability = _availability(
        (ExtensionCatalogAvailabilityOwner.COMPILER, first, None),
        (ExtensionCatalogAvailabilityOwner.PROJECT, second, project),
        (ExtensionCatalogAvailabilityOwner.COMPILER, additional, None),
    )
    result = select_extension_catalog(availability, target, project)

    assert first.metadata.catalog == second.metadata.catalog
    assert first.metadata.target == second.metadata.target
    assert first.content_sha256 != second.content_sha256
    assert result.outcome is ExtensionCatalogSelectionOutcome.CONFLICT
    assert result.selected_catalog is None
    assert len(result.candidates) == 3
    assert result.target_declarations == availability.declarations
    assert (
        sum(
            candidate.identity.reference == reference for candidate in result.candidates
        )
        == 2
    )


def test_internal_catalog_conflicts_and_unmodeled_entries_remain_selectable() -> None:
    target = _target()
    catalog = _rich_artifact(_reference("rich-selected"), target)
    result = select_extension_catalog(
        _availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        ),
        target,
    )

    assert result.outcome is ExtensionCatalogSelectionOutcome.SELECTED
    assert result.selected_catalog is catalog
    assert any(
        group.state is ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT
        for group in catalog.exact_entry_groups
    )
    assert any(
        entry.evidence.matchability is ExtensionCatalogMatchability.CATALOGED_UNMODELED
        for entry in catalog.entries
    )
    assert any(
        group.state is ExtensionCatalogCompletenessState.CONFLICT
        for group in catalog.completeness_groups
    )


def test_selection_result_is_private_immutable_and_slice7_ready() -> None:
    target = _target()
    catalog = _artifact(target=target)
    result = select_extension_catalog(
        _availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        ),
        target,
    )

    assert tuple(field.name for field in fields(ExtensionCatalogSelectionResult)) == (
        "outcome",
        "requested_target",
        "active_project",
        "availability",
        "applicable_declarations",
        "excluded_project_declarations",
        "target_declarations",
        "candidates",
        "selected_catalog",
    )
    for carrier in (
        ExtensionCatalogAvailabilityDeclaration,
        DeclaredExtensionCatalogAvailability,
        ExtensionCatalogSelectionCandidateIdentity,
        ExtensionCatalogSelectionCandidate,
        ExtensionCatalogSelectionResult,
    ):
        assert is_dataclass(carrier)
        assert "__dict__" not in carrier.__slots__
    with pytest.raises(FrozenInstanceError):
        result.selected_catalog = None  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(TypeError, match="canonical selection"):
        ExtensionCatalogSelectionCandidate()
    with pytest.raises(TypeError, match="canonical selection"):
        ExtensionCatalogSelectionResult()
    assert result.selected_catalog is catalog
    assert result.candidates[0].catalog is catalog
    assert result.candidates[0].identity.target is target

    symbols = (
        "ExtensionCatalogAvailabilityDeclaration",
        "DeclaredExtensionCatalogAvailability",
        "ExtensionCatalogSelectionResult",
    )
    assert catalog_availability.__all__ == ()
    for module in (pietto, semantic_package, project_package):
        assert all(not hasattr(module, symbol) for symbol in symbols)


def test_selection_module_has_no_quality_provider_profile_runtime_or_package_policy() -> (
    None
):
    source = inspect.getsource(catalog_availability)
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
        "pietto._project.model",
        "pietto.semantic.extension_catalog",
    }
    for forbidden in (
        ".entries",
        "exact_entry_groups",
        "completeness_groups",
        "matchability",
        "exposure",
        "capability_",
        "profile",
        "installed",
        "installation",
        "package",
        "pathlib",
        "import os",
        "subprocess",
        "requests",
        "socket",
        "open(",
        "getcwd",
        "environ",
        "resolve(",
        "parent",
        "latest",
        "semver",
        "winner",
        "precedence",
        "override",
    ):
        assert forbidden not in source.lower()
    assert "extension_catalog" not in inspect.getsource(profile_availability)
    for module in (
        providers,
        checking,
        matrix,
        capability_inspection,
        package_manifest,
    ):
        assert "extension_catalog_availability" not in inspect.getsource(module)


def test_slice2_through_slice5_and_phase56_authorities_remain_unchanged() -> None:
    first = _artifact()
    second = _artifact()
    before_bytes = first.canonical_bytes
    before_digest = first.content_sha256
    select_extension_catalog(
        _availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, first, None),
        ),
        first.metadata.target,
    )
    assert first.canonical_bytes == second.canonical_bytes == before_bytes
    assert first.content_sha256 == second.content_sha256 == before_digest

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
    assert (len(corpus), len(accepted), len(corpus) - len(accepted)) == (125, 16, 109)
    assert _corpus_digest() == EXPECTED_CORPUS_DIGEST
    assert 'version = "0.1.0"' in (REPO_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )

    source = inspect.getsource(catalog_availability).lower()
    assert all(
        name not in source for name in ("pgvector", "pg_trgm", "postgis", "timescaledb")
    )
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    assert 'f"{prefix}/_project/extension_catalog_availability.py"' in package_smoke
    assert '"import pietto._project.extension_catalog_availability"' in package_smoke


def test_slice6_spec_lifecycle_and_slice7_boundary_are_exact() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for heading in (
        "Declaration Authority",
        "Project Applicability",
        "Exact Candidate Identity",
        "Selection Algebra",
        "No-winner And Separation Boundaries",
        "Revised Slice 8 Provider Handoff",
    ):
        assert f"## {heading}\n" in spec
    for term in (
        "COMPILER",
        "PROJECT",
        "UNDECLARED",
        "SELECTED",
        "AMBIGUOUS",
        "CONFLICT",
        "ExtensionCatalogReference",
        "ExtensionCatalogTarget",
        "content_sha256",
        "ProjectRoot",
    ):
        assert term in spec
    assert "Revised Slice 8 remains unstarted and unauthorized" in " ".join(
        spec.split()
    )

    roadmap = ROADMAP.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    assert "Phase 57 is active, Slices 1–11 are completed, and Slice 12 is current" in (
        roadmap
    )
    assert "Slice 6 declares constructed catalogs available" in roadmap
    assert "| Slices 1–11 | `COMPLETED` |" in status
    assert "| Slice 12 | `CURRENT` |" in status
    assert "| Next | `PHASE57_SLICE12_END_TO_END` |" in status
    assert "does\nnot authorize Slice 13" in status
