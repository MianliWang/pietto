from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto._metadata as metadata_package
import pietto._project as project_package
import pietto._project_explain as project_explain_package
import pietto._project_explain.extension_catalog_evidence_projection as projection_module
import pietto.semantic as semantic_package
import test_phase55_slice10_package_inspection_canonical_serialization as package_slice
import test_phase56_slice6_exact_capability_requirement_checking as checking_slice
import test_phase57_slice5_extension_catalog_construction_completeness_canonical as catalog_slice
import test_phase57_slice6_extension_catalog_declaration_availability_selection as availability_slice
import test_phase57_slice8_extension_signature_provider_checking_integration as provider_slice
import test_phase57_slice11_extension_catalog_inspection as inspection_slice
from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
    PackageCapabilityRequirementBinding,
    build_declared_capability_profile_availability,
)
from pietto._project.capability_inspection import (
    CapabilityInspectionFactSet,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingTargetContext,
    build_package_capability_checking_matrix,
)
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityOwner,
    select_extension_catalog,
)
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspectionFactSet,
    build_extension_catalog_inspection,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderContext,
)
from pietto._project.model import ProjectRoot
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
)
from pietto._project.package_load_plan import LoadedPackage
from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainRequirementTargetMatrix,
    _project_empty_requirement_target_matrix,
    _project_requirement_target_matrix,
)
from pietto._project_explain.extension_catalog_evidence_projection import (
    ProjectExplainCatalogAvailabilityOwnerKind,
    ProjectExplainCatalogCompletenessClaimKind,
    ProjectExplainCatalogCompletenessState,
    ProjectExplainCatalogEntryFamily,
    ProjectExplainCatalogExactGroupState,
    ProjectExplainCatalogExposure,
    ProjectExplainCatalogMatchability,
    ProjectExplainCatalogSelectionOutcome,
    ProjectExplainCatalogTypeReferenceKind,
    ProjectExplainCatalogUnmodeledReason,
    ProjectExplainExtensionCatalogAvailabilityDeclaration,
    ProjectExplainExtensionCatalogCallableIdentity,
    ProjectExplainExtensionCatalogCastIdentity,
    ProjectExplainExtensionCatalogCompletenessClaim,
    ProjectExplainExtensionCatalogCompletenessEvidence,
    ProjectExplainExtensionCatalogContextEvidence,
    ProjectExplainExtensionCatalogEntryEvidence,
    ProjectExplainExtensionCatalogEvidenceProjection,
    ProjectExplainExtensionCatalogExactGroupEvidence,
    ProjectExplainExtensionCatalogOperatorIdentity,
    ProjectExplainExtensionCatalogReference,
    ProjectExplainExtensionCatalogSelection,
    ProjectExplainExtensionCatalogSelectionCandidate,
    ProjectExplainExtensionCatalogSourceOccurrence,
    ProjectExplainExtensionCatalogSummary,
    ProjectExplainExtensionCatalogTarget,
    ProjectExplainExtensionCatalogTypeReference,
    ProjectExplainExtensionCatalogSelector,
    ProjectExplainExtensionRequirementEvidence,
    ProjectExplainPostgreSQLOperatorArity,
    _project_extension_catalog_evidence,
)
from pietto._project_explain.model import (
    ProjectExplainEvidencePosture,
    ProjectExplainLogicalPath,
    ProjectExplainLogicalPathKind,
)
from pietto._project_explain.package_requirement_projection import (
    ProjectExplainPackageRequirementProjection,
    _project_package_requirement_provenance,
)
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey
from pietto.semantic.capability_profiles import CapabilityRequirementCollection
from pietto.semantic.extension_catalog import (
    ExtensionCatalogCompletenessClaim,
    ExtensionCatalogCompletenessClaimKind,
    ExtensionCatalogCompletenessState,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogLookupScope,
    ExtensionCatalogUnmodeledReason,
    PostgreSQLCallableIdentity,
    PostgreSQLCastIdentity,
    PostgreSQLOperatorArity,
    PostgreSQLOperatorIdentity,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase58-slice5-project-explain-extension-catalog-evidence-v1.md"
)
SOURCE = (
    REPO_ROOT / "src/pietto/_project_explain/extension_catalog_evidence_projection.py"
)
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"


def _capability_facts(
    package_facts: PackageInspectionFactSet,
    requirements: CapabilityRequirementCollection,
    contexts: tuple[CapabilityCheckingTargetContext, ...],
) -> tuple[CapabilityInspectionFactSet, ...]:
    result: list[CapabilityInspectionFactSet] = []
    for package in package_facts.inspection.packages:
        loaded = cast(LoadedPackage, package.entry.package)
        binding = PackageCapabilityRequirementBinding(loaded, requirements)
        result.append(
            build_capability_inspection(
                build_package_capability_checking_matrix(
                    loaded,
                    binding,
                    contexts,
                )
            )
        )
    return tuple(result)


def _authorities(
    root: Path,
    provider_contexts: tuple[ExtensionSignatureProviderContext | None, ...],
    requirements: CapabilityRequirementCollection,
    *,
    blocked_targets: frozenset[int] = frozenset(),
) -> tuple[
    ProjectExplainPackageRequirementProjection,
    ProjectExplainRequirementTargetMatrix,
    PackageInspectionFactSet,
    tuple[CapabilityInspectionFactSet, ...],
    tuple[ExtensionCatalogInspectionFactSet | None, ...],
]:
    package_facts = package_slice._simple_inspection(
        root,
        root_path=".",
        dependency_path="dep",
        authored_path="dep",
    )
    contexts: list[CapabilityCheckingTargetContext] = []
    catalog_facts: list[ExtensionCatalogInspectionFactSet | None] = []
    for position, provider_context in enumerate(provider_contexts):
        composition = checking_slice._composition()
        availability = (
            build_declared_capability_profile_availability(
                checking_slice.slice5._compiler_ledger()
            )
            if position in blocked_targets
            else checking_slice._availability(composition)
        )
        assert isinstance(availability, DeclaredCapabilityProfileAvailabilityReady)
        contexts.append(
            CapabilityCheckingTargetContext(
                position,
                composition,
                availability,
                provider_context,
            )
        )
        catalog_facts.append(
            None
            if provider_context is None
            else build_extension_catalog_inspection(provider_context)
        )
    capability_facts = _capability_facts(
        package_facts,
        requirements,
        tuple(contexts),
    )
    package_projection = _project_package_requirement_provenance(
        package_facts,
        capability_facts,
    )
    matrix_projection = _project_requirement_target_matrix(
        package_projection,
        package_facts,
        capability_facts,
    )
    slots = tuple(
        facts
        for _package in package_facts.inspection.packages
        for facts in catalog_facts
    )
    return (
        package_projection,
        matrix_projection,
        package_facts,
        capability_facts,
        slots,
    )


def _project(
    authority: tuple[
        ProjectExplainPackageRequirementProjection,
        ProjectExplainRequirementTargetMatrix,
        PackageInspectionFactSet,
        tuple[CapabilityInspectionFactSet, ...],
        tuple[ExtensionCatalogInspectionFactSet | None, ...],
    ],
) -> ProjectExplainExtensionCatalogEvidenceProjection:
    return _project_extension_catalog_evidence(*authority)


def _selected_context(
    *,
    name: str = "selected",
) -> ExtensionSignatureProviderContext:
    catalog = inspection_slice._direct_catalog()
    key = inspection_slice._key(name, extension="example_extension")
    requirements = inspection_slice._requirements(key, name=name)
    selection = select_extension_catalog(
        availability_slice._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        ),
        catalog.metadata.target,
    )
    return inspection_slice._context(
        requirements,
        (0, catalog.exact_entry_groups[0].scope, selection),
    )


def test_exact_vocabularies_model_fields_and_private_surface() -> None:
    expected_enums = {
        ProjectExplainCatalogTypeReferenceKind: (
            ("PIETTO_LOGICAL", "pietto_logical"),
            ("POSTGRES_BUILTIN", "postgres_builtin"),
            ("EXTENSION_NATIVE", "extension_native"),
        ),
        ProjectExplainCatalogEntryFamily: (
            ("NATIVE_TYPE", "native_type"),
            ("SCALAR_FUNCTION", "scalar_function"),
            ("AGGREGATE", "aggregate"),
            ("OPERATOR", "operator"),
            ("CAST", "cast"),
        ),
        ProjectExplainPostgreSQLOperatorArity: (
            ("UNARY", "unary"),
            ("BINARY", "binary"),
        ),
        ProjectExplainCatalogSelectionOutcome: (
            ("UNDECLARED", "undeclared"),
            ("SELECTED", "selected"),
            ("AMBIGUOUS", "ambiguous"),
            ("CONFLICT", "conflict"),
        ),
        ProjectExplainCatalogAvailabilityOwnerKind: (
            ("COMPILER", "compiler"),
            ("PROJECT", "project"),
        ),
        ProjectExplainCatalogMatchability: (
            ("EXACT_MATCHABLE", "exact_matchable"),
            ("CATALOGED_UNMODELED", "cataloged_unmodeled"),
        ),
        ProjectExplainCatalogExposure: (
            ("DIRECT_SQL_SURFACE", "direct_sql_surface"),
            ("IMPLEMENTATION_SUPPORT", "implementation_support"),
            ("UNCLASSIFIED", "unclassified"),
        ),
        ProjectExplainCatalogExactGroupState: (
            ("UNIQUE", "unique"),
            ("CONSISTENT_DUPLICATE", "consistent_duplicate"),
            ("EVIDENCE_CONFLICT", "evidence_conflict"),
        ),
        ProjectExplainCatalogCompletenessState: (
            ("COMPLETE", "complete"),
            ("INCOMPLETE", "incomplete"),
            ("CONFLICT", "conflict"),
        ),
        ProjectExplainCatalogCompletenessClaimKind: (
            ("COMPLETE", "complete"),
            ("INCOMPLETE", "incomplete"),
        ),
    }
    for enumeration, expected in expected_enums.items():
        assert tuple((member.name, member.value) for member in enumeration) == expected
    assert tuple(
        (member.name, member.value) for member in ProjectExplainCatalogUnmodeledReason
    ) == tuple(
        (member.name, member.value) for member in ExtensionCatalogUnmodeledReason
    )

    expected_fields: dict[type[Any], tuple[str, ...]] = {
        ProjectExplainExtensionCatalogReference: ("namespace", "name", "release"),
        ProjectExplainExtensionCatalogTarget: (
            "database_family",
            "database_release",
            "extension_identity",
            "extension_release",
        ),
        ProjectExplainExtensionCatalogSourceOccurrence: (
            "position",
            "source_authority",
            "source_revision",
            "source_locator",
            "curation",
        ),
        ProjectExplainExtensionCatalogSummary: (
            "position",
            "reference",
            "target",
            "content_sha256",
            "canonical_byte_length",
            "source_occurrences",
        ),
        ProjectExplainExtensionCatalogTypeReference: (
            "kind",
            "logical_name",
            "logical_kind",
            "physical_name",
            "extension_identity",
        ),
        ProjectExplainExtensionCatalogCallableIdentity: ("sql_name", "input_types"),
        ProjectExplainExtensionCatalogOperatorIdentity: (
            "operator_name",
            "arity",
            "operand_types",
        ),
        ProjectExplainExtensionCatalogCastIdentity: ("source_type", "target_type"),
        ProjectExplainExtensionCatalogSelector: ("family", "identity"),
        ProjectExplainExtensionCatalogAvailabilityDeclaration: (
            "position",
            "owner_kind",
            "project_path",
            "catalog_position",
            "reference",
            "target",
            "content_sha256",
        ),
        ProjectExplainExtensionCatalogSelectionCandidate: (
            "catalog_position",
            "reference",
            "target",
            "content_sha256",
            "declaration_positions",
        ),
        ProjectExplainExtensionCatalogSelection: (
            "requested_target",
            "active_project_path",
            "outcome",
            "evidence_posture",
            "availability",
            "applicable_declaration_positions",
            "excluded_project_declaration_positions",
            "target_declaration_positions",
            "candidates",
            "selected_catalog_position",
        ),
        ProjectExplainExtensionCatalogEntryEvidence: (
            "entry_position",
            "entry_family",
            "matchability",
            "exposure",
            "unmodeled_reasons",
            "source_positions",
        ),
        ProjectExplainExtensionCatalogExactGroupEvidence: (
            "position",
            "state",
            "entries",
        ),
        ProjectExplainExtensionCatalogCompletenessClaim: (
            "position",
            "kind",
            "source_positions",
        ),
        ProjectExplainExtensionCatalogCompletenessEvidence: (
            "position",
            "state",
            "claims",
        ),
        ProjectExplainExtensionRequirementEvidence: (
            "requirement_position",
            "selector",
            "bridged_database_family",
            "selection",
            "selected_catalog_position",
            "exact_group",
            "unmodeled_blockers",
            "completeness",
        ),
        ProjectExplainExtensionCatalogContextEvidence: (
            "package_position",
            "target_position",
            "collection",
            "catalogs",
            "requirements",
        ),
        ProjectExplainExtensionCatalogEvidenceProjection: ("contexts",),
    }
    for carrier, expected in expected_fields.items():
        assert is_dataclass(carrier)
        assert tuple(field.name for field in fields(carrier)) == expected
        assert "__dict__" not in cast(Any, carrier).__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(cast(Any, carrier)).parameters.values()
        )

    reference = ProjectExplainExtensionCatalogReference(
        namespace="example",
        name="catalog",
        release="1",
    )
    with pytest.raises(FrozenInstanceError):
        reference.name = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        replace(reference, name=cast(Any, 1))
    assert project_explain_package.__all__ == projection_module.__all__ == ()
    for public in (pietto, project_package, metadata_package, semantic_package):
        for carrier in expected_fields:
            assert not hasattr(public, carrier.__name__)


def test_selected_catalog_package_target_order_and_slice4_agreement(
    tmp_path: Path,
) -> None:
    context = _selected_context()
    authority = _authorities(
        tmp_path,
        (context,),
        context.selectors.requirements,
    )
    projected = _project(authority)

    assert tuple(
        (item.package_position, item.target_position) for item in projected.contexts
    ) == ((0, 0), (1, 0))
    assert tuple(
        item.requirements[0].requirement_position for item in projected.contexts
    ) == (0, 1)
    first = projected.contexts[0]
    requirement = first.requirements[0]
    assert (
        requirement.selection.outcome is ProjectExplainCatalogSelectionOutcome.SELECTED
    )
    assert requirement.selection.evidence_posture is (
        ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION
    )
    assert requirement.selected_catalog_position == 0
    assert requirement.exact_group is not None
    assert requirement.exact_group.state is ProjectExplainCatalogExactGroupState.UNIQUE
    assert requirement.exact_group.entries[0].matchability is (
        ProjectExplainCatalogMatchability.EXACT_MATCHABLE
    )
    assert requirement.exact_group.entries[0].exposure is (
        ProjectExplainCatalogExposure.DIRECT_SQL_SURFACE
    )
    catalog = first.catalogs[0]
    assert catalog.content_sha256 == inspection_slice._direct_catalog().content_sha256
    assert catalog.target.extension_identity == "example_extension"
    assert catalog.source_occurrences
    assert all(
        source.source_locator.kind
        is ProjectExplainLogicalPathKind.UPSTREAM_SOURCE_LOCATOR
        for source in catalog.source_occurrences
    )


def test_five_typed_selector_families_and_multiple_requirement_order(
    tmp_path: Path,
) -> None:
    catalog = inspection_slice._direct_catalog()
    selection = select_extension_catalog(
        availability_slice._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        ),
        catalog.metadata.target,
    )
    builtin = inspection_slice._builtin("text")
    native = inspection_slice._native("native", "example_extension")
    scopes = (
        ExtensionCatalogLookupScope(ExtensionCatalogEntryFamily.NATIVE_TYPE, native),
        inspection_slice._scalar_scope("scalar", builtin),
        ExtensionCatalogLookupScope(
            ExtensionCatalogEntryFamily.AGGREGATE,
            PostgreSQLCallableIdentity("aggregate", (builtin,)),
        ),
        ExtensionCatalogLookupScope(
            ExtensionCatalogEntryFamily.OPERATOR,
            PostgreSQLOperatorIdentity(
                "<->",
                PostgreSQLOperatorArity.BINARY,
                (builtin, builtin),
            ),
        ),
        ExtensionCatalogLookupScope(
            ExtensionCatalogEntryFamily.CAST,
            PostgreSQLCastIdentity(builtin, native),
        ),
    )
    requirements = inspection_slice._requirements(
        *(
            inspection_slice._key(name, extension="example_extension")
            for name in (
                "native",
                "scalar",
                "aggregate",
                "operator",
                "cast",
            )
        ),
        name="typed-families",
    )
    context = inspection_slice._context(
        requirements,
        *((position, scope, selection) for position, scope in enumerate(scopes)),
    )
    projected = _project(_authorities(tmp_path, (context,), requirements))
    first = projected.contexts[0]

    assert tuple(
        requirement.requirement_position for requirement in first.requirements
    ) == tuple(range(5))
    assert tuple(
        requirement.selector.family for requirement in first.requirements
    ) == tuple(ProjectExplainCatalogEntryFamily)
    assert isinstance(
        first.requirements[0].selector.identity,
        ProjectExplainExtensionCatalogTypeReference,
    )
    assert isinstance(
        first.requirements[1].selector.identity,
        ProjectExplainExtensionCatalogCallableIdentity,
    )
    assert isinstance(
        first.requirements[2].selector.identity,
        ProjectExplainExtensionCatalogCallableIdentity,
    )
    assert isinstance(
        first.requirements[3].selector.identity,
        ProjectExplainExtensionCatalogOperatorIdentity,
    )
    assert isinstance(
        first.requirements[4].selector.identity,
        ProjectExplainExtensionCatalogCastIdentity,
    )


def test_selection_outcomes_preserve_no_winner_and_target_order(tmp_path: Path) -> None:
    target = availability_slice._target()
    scope = inspection_slice._synthetic_scope("missing")
    selected_catalog = availability_slice._artifact(target=target)
    selected = select_extension_catalog(
        availability_slice._availability(
            (
                ExtensionCatalogAvailabilityOwner.COMPILER,
                selected_catalog,
                None,
            ),
        ),
        target,
    )
    undeclared = select_extension_catalog(
        DeclaredExtensionCatalogAvailability(()), target
    )
    first = availability_slice._artifact(
        reference=availability_slice._reference("first"),
        target=target,
    )
    second = availability_slice._artifact(
        reference=availability_slice._reference("second"),
        target=target,
    )
    ambiguous = select_extension_catalog(
        availability_slice._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, first, None),
            (ExtensionCatalogAvailabilityOwner.COMPILER, second, None),
        ),
        target,
    )
    reference = availability_slice._reference("conflict")
    conflict_one = availability_slice._artifact(
        reference=reference,
        target=target,
        source_labels=("one",),
    )
    conflict_two = availability_slice._artifact(
        reference=reference,
        target=target,
        source_labels=("two",),
    )
    conflict = select_extension_catalog(
        availability_slice._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, conflict_one, None),
            (ExtensionCatalogAvailabilityOwner.COMPILER, conflict_two, None),
        ),
        target,
    )
    requirements = inspection_slice._requirements(
        inspection_slice._key("selection", extension="example_extension"),
        name="selection-outcomes",
    )
    contexts = tuple(
        inspection_slice._context(requirements, (0, scope, selection))
        for selection in (undeclared, selected, ambiguous, conflict)
    )
    projected = _project(_authorities(tmp_path, contexts, requirements))

    expected = tuple(ProjectExplainCatalogSelectionOutcome)
    assert (
        tuple(
            context.requirements[0].selection.outcome
            for context in projected.contexts[:4]
        )
        == expected
    )
    assert (
        tuple(
            context.requirements[0].selection.outcome
            for context in projected.contexts[4:]
        )
        == expected
    )
    for context in projected.contexts:
        selection = context.requirements[0].selection
        if selection.outcome in {
            ProjectExplainCatalogSelectionOutcome.AMBIGUOUS,
            ProjectExplainCatalogSelectionOutcome.CONFLICT,
        }:
            assert selection.selected_catalog_position is None
            assert (
                selection.evidence_posture is ProjectExplainEvidencePosture.CONFLICTING
            )


def test_compiler_project_availability_and_logical_paths(tmp_path: Path) -> None:
    catalog = inspection_slice._direct_catalog()
    active = ProjectRoot("active/project")
    excluded = ProjectRoot("excluded/project")
    availability = availability_slice._availability(
        (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        (ExtensionCatalogAvailabilityOwner.PROJECT, catalog, active),
        (ExtensionCatalogAvailabilityOwner.PROJECT, catalog, excluded),
    )
    selection = select_extension_catalog(
        availability,
        catalog.metadata.target,
        active,
    )
    requirements = inspection_slice._requirements(
        inspection_slice._key("availability", extension="example_extension"),
        name="availability",
    )
    context = inspection_slice._context(
        requirements,
        (0, catalog.exact_entry_groups[0].scope, selection),
    )
    projected = _project(_authorities(tmp_path, (context,), requirements))
    evidence = projected.contexts[0].requirements[0].selection

    assert tuple(item.owner_kind for item in evidence.availability) == (
        ProjectExplainCatalogAvailabilityOwnerKind.COMPILER,
        ProjectExplainCatalogAvailabilityOwnerKind.PROJECT,
        ProjectExplainCatalogAvailabilityOwnerKind.PROJECT,
    )
    assert evidence.applicable_declaration_positions == (0, 1)
    assert evidence.excluded_project_declaration_positions == (2,)
    assert evidence.candidates[0].declaration_positions == (0, 1)
    assert evidence.active_project_path == ProjectExplainLogicalPath(
        kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
        value="active/project",
    )


def test_real_unmodeled_source_and_exposure_evidence_are_bounded(
    tmp_path: Path,
) -> None:
    context = inspection_slice._production_context()
    projected = _project(
        _authorities(tmp_path, (context,), context.selectors.requirements)
    )
    first = projected.contexts[0]
    direct, _exact, unmodeled, support = first.requirements

    assert direct.selected_catalog_position is not None
    assert unmodeled.exact_group is None
    assert len(unmodeled.unmodeled_blockers) == 1
    blocker = unmodeled.unmodeled_blockers[0]
    assert blocker.matchability is ProjectExplainCatalogMatchability.CATALOGED_UNMODELED
    assert blocker.exposure is ProjectExplainCatalogExposure.DIRECT_SQL_SURFACE
    assert blocker.unmodeled_reasons == (
        ProjectExplainCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    )
    assert support.exact_group is not None
    assert support.exact_group.entries[0].exposure is (
        ProjectExplainCatalogExposure.IMPLEMENTATION_SUPPORT
    )
    selected = first.catalogs[cast(int, unmodeled.selected_catalog_position)]
    assert all(
        position < len(selected.source_occurrences)
        for position in blocker.source_positions
    )


def test_exact_group_conflict_and_unclassified_evidence_are_preserved(
    tmp_path: Path,
) -> None:
    conflict_catalog = provider_slice._catalog(
        (
            catalog_slice._scalar_entry((0,), result="text"),
            catalog_slice._scalar_entry((1,), result="int4"),
        ),
        source_count=2,
    )
    conflict_requirements = inspection_slice._requirements(
        inspection_slice._key("conflict", extension="example_extension"),
        name="exact-conflict",
    )
    conflict_context = inspection_slice._context(
        conflict_requirements,
        (
            0,
            conflict_catalog.exact_entry_groups[0].scope,
            provider_slice._selection(conflict_catalog),
        ),
    )
    conflict = (
        _project(
            _authorities(
                tmp_path / "conflict",
                (conflict_context,),
                conflict_requirements,
            )
        )
        .contexts[0]
        .requirements[0]
    )
    assert conflict.exact_group is not None
    assert conflict.exact_group.state is (
        ProjectExplainCatalogExactGroupState.EVIDENCE_CONFLICT
    )
    assert len(conflict.exact_group.entries) == 2

    rich_catalog = availability_slice._rich_artifact(
        availability_slice._reference("unclassified"),
        availability_slice._target(),
    )
    unclassified_requirements = inspection_slice._requirements(
        inspection_slice._key("unclassified", extension="example_extension"),
        name="unclassified",
    )
    unclassified_context = inspection_slice._context(
        unclassified_requirements,
        (
            0,
            inspection_slice._scalar_scope(
                "complex",
                inspection_slice._builtin("text"),
            ),
            provider_slice._selection(rich_catalog),
        ),
    )
    unclassified = (
        _project(
            _authorities(
                tmp_path / "unclassified",
                (unclassified_context,),
                unclassified_requirements,
            )
        )
        .contexts[0]
        .requirements[0]
    )
    assert len(unclassified.unmodeled_blockers) == 1
    assert unclassified.unmodeled_blockers[0].exposure is (
        ProjectExplainCatalogExposure.UNCLASSIFIED
    )


def _completeness_context(
    state: ExtensionCatalogCompletenessState | None,
) -> ExtensionSignatureProviderContext:
    scope = catalog_slice._scope(name="missing")
    claims: tuple[ExtensionCatalogCompletenessClaim, ...]
    if state is ExtensionCatalogCompletenessState.COMPLETE:
        claims = (
            ExtensionCatalogCompletenessClaim(
                scope,
                ExtensionCatalogCompletenessClaimKind.COMPLETE,
                (0,),
            ),
        )
    elif state is ExtensionCatalogCompletenessState.INCOMPLETE:
        claims = (
            ExtensionCatalogCompletenessClaim(
                scope,
                ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
                (0,),
            ),
        )
    elif state is ExtensionCatalogCompletenessState.CONFLICT:
        claims = (
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
        )
    else:
        claims = ()
    catalog = provider_slice._catalog(
        claims=claims,
        source_count=max(len(claims), 1),
    )
    requirements = inspection_slice._requirements(
        inspection_slice._key("completeness", extension="example_extension"),
        name=f"completeness-{state}",
    )
    selection = select_extension_catalog(
        availability_slice._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        ),
        catalog.metadata.target,
    )
    return inspection_slice._context(requirements, (0, scope, selection))


@pytest.mark.parametrize(
    "state",
    (
        ExtensionCatalogCompletenessState.COMPLETE,
        ExtensionCatalogCompletenessState.INCOMPLETE,
        ExtensionCatalogCompletenessState.CONFLICT,
        None,
    ),
)
def test_completeness_states_and_unavailable_authority(
    tmp_path: Path,
    state: ExtensionCatalogCompletenessState | None,
) -> None:
    context = _completeness_context(state)
    projected = _project(
        _authorities(tmp_path, (context,), context.selectors.requirements)
    )
    evidence = projected.contexts[0].requirements[0].completeness
    if state is None:
        assert evidence is None
    else:
        assert evidence is not None
        assert evidence.state.value == state.value
        expected = {
            ExtensionCatalogCompletenessState.COMPLETE: ("complete",),
            ExtensionCatalogCompletenessState.INCOMPLETE: ("incomplete",),
            ExtensionCatalogCompletenessState.CONFLICT: (
                "complete",
                "incomplete",
            ),
        }[state]
        assert tuple(claim.kind.value for claim in evidence.claims) == expected


def test_blocked_nonextension_and_empty_denominators_emit_no_contexts(
    tmp_path: Path,
) -> None:
    selected = _selected_context(name="blocked")
    blocked_authority = _authorities(
        tmp_path / "blocked",
        (selected,),
        selected.selectors.requirements,
        blocked_targets=frozenset({0}),
    )
    blocked_slots = tuple(None for _slot in blocked_authority[-1])
    assert (
        _project_extension_catalog_evidence(
            *blocked_authority[:-1],
            blocked_slots,
        ).contexts
        == ()
    )

    nonextension_requirements = inspection_slice._requirements(
        CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int"),
        name="nonextension",
    )
    nonextension = _authorities(
        tmp_path / "nonextension",
        (None,),
        nonextension_requirements,
    )
    assert _project(nonextension).contexts == ()

    package_projection, _matrix, package_facts, capability_facts, _slots = nonextension
    empty_matrix = _project_empty_requirement_target_matrix(package_projection)
    assert (
        _project_extension_catalog_evidence(
            package_projection,
            empty_matrix,
            package_facts,
            capability_facts,
            (),
        ).contexts
        == ()
    )


def test_slot_count_order_foreign_projection_and_grafts_fail_closed(
    tmp_path: Path,
) -> None:
    context = _selected_context(name="graft")
    authority = _authorities(tmp_path, (context,), context.selectors.requirements)
    package_projection, matrix, package_facts, capability_facts, slots = authority

    with pytest.raises(ValueError, match="slot"):
        _project_extension_catalog_evidence(
            package_projection,
            matrix,
            package_facts,
            capability_facts,
            slots[:-1],
        )
    selected_catalog = inspection_slice._direct_catalog()
    reordered_requirements = inspection_slice._requirements(
        inspection_slice._key("reordered", extension="example_extension"),
        name="reordered",
    )
    reordered_contexts = (
        inspection_slice._context(
            reordered_requirements,
            (
                0,
                selected_catalog.exact_entry_groups[0].scope,
                provider_slice._selection(selected_catalog),
            ),
        ),
        inspection_slice._context(
            reordered_requirements,
            (
                0,
                selected_catalog.exact_entry_groups[0].scope,
                provider_slice._undeclared_selection(selected_catalog.metadata.target),
            ),
        ),
    )
    reordered_authority = _authorities(
        tmp_path / "reordered",
        reordered_contexts,
        reordered_requirements,
    )
    with pytest.raises(ValueError, match="grafted catalog inspection authority"):
        _project_extension_catalog_evidence(
            *reordered_authority[:-1],
            tuple(reversed(reordered_authority[-1])),
        )
    foreign_context = _selected_context(name="foreign-context")
    foreign_facts = build_extension_catalog_inspection(foreign_context)
    with pytest.raises(ValueError, match="grafted catalog inspection authority"):
        _project_extension_catalog_evidence(
            package_projection,
            matrix,
            package_facts,
            capability_facts,
            (foreign_facts, *slots[1:]),
        )
    foreign_authority = _authorities(
        tmp_path / "foreign-projection",
        (foreign_context,),
        foreign_context.selectors.requirements,
    )
    with pytest.raises(ValueError, match="same exact Slice 3"):
        _project_extension_catalog_evidence(
            foreign_authority[0],
            matrix,
            package_facts,
            capability_facts,
            slots,
        )
    facts = cast(ExtensionCatalogInspectionFactSet, slots[0])
    copied = object.__new__(type(facts.inspection))
    for declared in fields(facts.inspection):
        object.__setattr__(
            copied, declared.name, getattr(facts.inspection, declared.name)
        )
    with pytest.raises(ValueError, match="grafted projection"):
        _project_extension_catalog_evidence(
            package_projection,
            matrix,
            package_facts,
            capability_facts,
            (
                ExtensionCatalogInspectionFactSet(
                    inspection=cast(Any, copied),
                    canonical_bytes=facts.canonical_bytes,
                    authority=facts.authority,
                ),
                *slots[1:],
            ),
        )


def _walk(value: object) -> tuple[object, ...]:
    values = [value]
    if is_dataclass(value) and not isinstance(value, type):
        for declared in fields(value):
            values.extend(_walk(getattr(value, declared.name)))
    elif isinstance(value, tuple):
        for item in value:
            values.extend(_walk(item))
    return tuple(values)


def test_output_is_detached_and_retained_later_surfaces_are_absent(
    tmp_path: Path,
) -> None:
    context = inspection_slice._production_context()
    projected = _project(
        _authorities(tmp_path, (context,), context.selectors.requirements)
    )
    forbidden_types = {
        "ExtensionCatalogInspectionFactSet",
        "ExtensionCatalogInspection",
        "ExtensionSignatureProviderContext",
        "ExtensionCatalogSelectionResult",
        "ConstructedExtensionCatalog",
        "CapabilityFact",
        "CapabilityEvidence",
        "Found",
        "Absent",
        "Unknown",
        "Conflict",
        "ProjectRoot",
        "Path",
    }
    assert not {type(value).__name__ for value in _walk(projected)} & forbidden_types
    source = SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        "select_extension_catalog(",
        "extension_signature_provider_authority(",
        "lookup_capability(",
        "check_package_capability_requirements(",
        "ProjectExplainPortability",
        "ProjectExplainPayload",
        "CrossSectionReference",
        "import json",
        "serialize",
        "render_",
        "argparse",
        "pathlib",
        "import os",
        "open(",
        "import requests",
        "socket",
    ):
        assert forbidden not in source


def test_spec_lifecycle_package_smoke_and_workflow_lock_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for required in (
        "ExtensionCatalogInspectionFactSet",
        "package order × target order",
        "typed physical selector",
        "CATALOGED_UNMODELED",
        "PHASE58_SLICE5_SELF_OWNED_OPEN = 0",
        "Slice 6 remains `UNSTARTED / NOT AUTHORIZED`",
    ):
        assert required in normalized
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    for required in (
        'f"{prefix}/_project_explain/extension_catalog_evidence_projection.py"',
        '"installed private project explain extension catalog evidence projection import"',
        "import pietto._project_explain.extension_catalog_evidence_projection",
    ):
        assert required in package_smoke
