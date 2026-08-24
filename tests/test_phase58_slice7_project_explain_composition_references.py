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
import pietto._project_explain.composition as composition_module
import pietto.semantic as semantic_package
import test_phase57_slice5_extension_catalog_construction_completeness_canonical as catalog_slice
import test_phase57_slice8_extension_signature_provider_checking_integration as provider_slice
import test_phase57_slice11_extension_catalog_inspection as inspection_slice
import test_phase58_slice5_project_explain_extension_catalog_evidence as slice5
import test_phase58_slice6_project_explain_portability_derivation as slice6
from pietto._project.extension_catalog_availability import (
    ExtensionCatalogAvailabilityOwner,
    select_extension_catalog,
)
from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainEvaluationState,
    ProjectExplainRequirementTargetMatrix,
    _project_empty_requirement_target_matrix,
)
from pietto._project_explain.composition import (
    ProjectExplainArtifactReference,
    ProjectExplainArtifactReferenceKind,
    ProjectExplainPayload,
    ProjectExplainRequirementExplanation,
    ProjectExplainRequirementTargetExplanation,
    _REFERENCE_ARITIES,
    _compose_project_explain_payload,
    _resolve_project_explain_reference,
)
from pietto._project_explain.extension_catalog_evidence_projection import (
    ProjectExplainCatalogCompletenessClaimKind,
    ProjectExplainCatalogCompletenessState,
    ProjectExplainCatalogEntryFamily,
    ProjectExplainCatalogExposure,
    ProjectExplainCatalogMatchability,
    ProjectExplainCatalogUnmodeledReason,
    ProjectExplainExtensionCatalogCompletenessClaim,
    ProjectExplainExtensionCatalogCompletenessEvidence,
    ProjectExplainExtensionCatalogEntryEvidence,
    ProjectExplainExtensionCatalogEvidenceProjection,
    _project_extension_catalog_evidence,
)
from pietto._project_explain.model import (
    ProjectExplainEnvelope,
    ProjectExplainFormat,
)
from pietto._project_explain.package_requirement_projection import (
    ProjectExplainPackageRequirementProjection,
)
from pietto._project_explain.portability_projection import (
    ProjectExplainProjectPortability,
    _derive_project_portability,
)
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey
from pietto.semantic.capability_profiles import CapabilityRequirementCollection


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT / "docs/spec/phase58-slice7-project-explain-composition-references-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project_explain/composition.py"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"

type _Sections = tuple[
    ProjectExplainPackageRequirementProjection,
    ProjectExplainRequirementTargetMatrix,
    ProjectExplainExtensionCatalogEvidenceProjection,
    ProjectExplainProjectPortability,
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sections(
    root: Path,
    provider_contexts: tuple[Any | None, ...],
    requirements: CapabilityRequirementCollection,
    *,
    blocked_targets: frozenset[int] = frozenset(),
) -> _Sections:
    authority = slice5._authorities(
        root,
        provider_contexts,
        requirements,
        blocked_targets=blocked_targets,
    )
    package, matrix, package_facts, capability_facts, slots = authority
    usable_slots = tuple(
        facts if evaluation.state is ProjectExplainEvaluationState.CHECKED else None
        for evaluation, facts in zip(
            matrix.package_target_evaluations,
            slots,
            strict=True,
        )
    )
    evidence = _project_extension_catalog_evidence(
        package,
        matrix,
        package_facts,
        capability_facts,
        usable_slots,
    )
    return package, matrix, evidence, _derive_project_portability(package, matrix)


def _selected_sections(
    root: Path,
    *,
    target_count: int = 1,
    name: str = "selected",
) -> _Sections:
    context = slice5._selected_context(name=name)
    return _sections(
        root,
        tuple(context for _position in range(target_count)),
        context.selectors.requirements,
    )


def _payload(sections: _Sections) -> ProjectExplainPayload:
    return _compose_project_explain_payload(*sections)


def _nonextension_sections(root: Path, *, name: str = "nonextension") -> _Sections:
    requirements = inspection_slice._requirements(
        CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int"),
        name=name,
    )
    return _sections(root, (None,), requirements)


def _blocked_sections(root: Path, *, name: str = "blocked") -> _Sections:
    context = slice5._selected_context(name=name)
    return _sections(
        root,
        (context,),
        context.selectors.requirements,
        blocked_targets=frozenset({0}),
    )


def _empty_sections(root: Path) -> _Sections:
    package, _matrix, _evidence, _portability = _selected_sections(root)
    matrix = _project_empty_requirement_target_matrix(package)
    evidence = ProjectExplainExtensionCatalogEvidenceProjection(contexts=())
    return package, matrix, evidence, _derive_project_portability(package, matrix)


def _unselected_sections(root: Path, *, conflict: bool) -> _Sections:
    target = slice5.availability_slice._target()
    if conflict:
        reference = slice5.availability_slice._reference("conflict")
        first = slice5.availability_slice._artifact(
            reference=reference,
            target=target,
            source_labels=("one",),
        )
        second = slice5.availability_slice._artifact(
            reference=reference,
            target=target,
            source_labels=("two",),
        )
        name = "conflict"
    else:
        first = slice5.availability_slice._artifact(
            reference=slice5.availability_slice._reference("first"),
            target=target,
        )
        second = slice5.availability_slice._artifact(
            reference=slice5.availability_slice._reference("second"),
            target=target,
        )
        name = "ambiguous"
    selection = select_extension_catalog(
        slice5.availability_slice._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, first, None),
            (ExtensionCatalogAvailabilityOwner.COMPILER, second, None),
        ),
        target,
    )
    requirements = inspection_slice._requirements(
        inspection_slice._key(name, extension="example_extension"),
        name=name,
    )
    context = inspection_slice._context(
        requirements,
        (0, inspection_slice._synthetic_scope("missing"), selection),
    )
    return _sections(root, (context,), requirements)


def _source_rich_sections(root: Path) -> _Sections:
    catalog = provider_slice._catalog(
        (catalog_slice._scalar_entry((0, 2), result="text"),),
        source_count=3,
    )
    requirements = inspection_slice._requirements(
        inspection_slice._key("sources", extension="example_extension"),
        name="sources",
    )
    context = inspection_slice._context(
        requirements,
        (
            0,
            catalog.exact_entry_groups[0].scope,
            provider_slice._selection(catalog),
        ),
    )
    package, matrix, projection, portability = _sections(
        root,
        (context,),
        requirements,
    )
    first_context = projection.contexts[0]
    first_requirement = first_context.requirements[0]
    blocker = ProjectExplainExtensionCatalogEntryEvidence(
        entry_position=0,
        entry_family=ProjectExplainCatalogEntryFamily.SCALAR_FUNCTION,
        matchability=ProjectExplainCatalogMatchability.CATALOGED_UNMODELED,
        exposure=ProjectExplainCatalogExposure.DIRECT_SQL_SURFACE,
        unmodeled_reasons=(ProjectExplainCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,),
        source_positions=(0,),
    )
    completeness = ProjectExplainExtensionCatalogCompletenessEvidence(
        position=0,
        state=ProjectExplainCatalogCompletenessState.COMPLETE,
        claims=(
            ProjectExplainExtensionCatalogCompletenessClaim(
                position=0,
                kind=ProjectExplainCatalogCompletenessClaimKind.COMPLETE,
                source_positions=(1, 2),
            ),
        ),
    )
    enriched_requirement = replace(
        first_requirement,
        unmodeled_blockers=(blocker,),
        completeness=completeness,
    )
    enriched_context = replace(
        first_context,
        requirements=(enriched_requirement,),
    )
    projection = replace(
        projection,
        contexts=(enriched_context, *projection.contexts[1:]),
    )
    return package, matrix, projection, portability


def test_exact_reference_vocabulary_arities_models_and_private_surface() -> None:
    assert tuple(
        (member.name, member.value) for member in ProjectExplainArtifactReferenceKind
    ) == (
        ("PACKAGE", "package"),
        ("REQUIREMENT", "requirement"),
        ("TARGET", "target"),
        ("PACKAGE_TARGET_EVALUATION", "package_target_evaluation"),
        ("MATRIX_CELL", "matrix_cell"),
        ("EXTENSION_CATALOG_CONTEXT", "extension_catalog_context"),
        ("EXTENSION_CATALOG", "extension_catalog"),
        ("EXTENSION_CATALOG_SOURCE", "extension_catalog_source"),
        ("EXTENSION_REQUIREMENT_EVIDENCE", "extension_requirement_evidence"),
        ("REQUIREMENT_PORTABILITY", "requirement_portability"),
        ("PROJECT_PORTABILITY", "project_portability"),
    )
    assert tuple(
        (kind, _REFERENCE_ARITIES[kind]) for kind in ProjectExplainArtifactReferenceKind
    ) == tuple(
        zip(
            ProjectExplainArtifactReferenceKind,
            (1, 1, 1, 2, 2, 2, 3, 4, 3, 1, 0),
            strict=True,
        )
    )

    expected_fields = {
        ProjectExplainArtifactReference: ("kind", "positions"),
        ProjectExplainRequirementTargetExplanation: (
            "target",
            "evaluation",
            "matrix_cell",
            "extension_evidence",
            "source_evidence",
        ),
        ProjectExplainRequirementExplanation: (
            "request",
            "declared_by",
            "requested_by",
            "targets",
            "portability",
        ),
        ProjectExplainPayload: (
            "package_requirements",
            "compatibility",
            "extension_catalog_evidence",
            "portability",
            "requirement_explanations",
        ),
    }
    for carrier, expected in expected_fields.items():
        assert is_dataclass(carrier)
        assert tuple(field.name for field in fields(carrier)) == expected
        assert "__dict__" not in cast(Any, carrier).__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(cast(Any, carrier)).parameters.values()
        )

    reference = ProjectExplainArtifactReference(
        kind=ProjectExplainArtifactReferenceKind.PACKAGE,
        positions=(0,),
    )
    with pytest.raises(FrozenInstanceError):
        reference.positions = (1,)  # type: ignore[misc]
    with pytest.raises(TypeError):
        replace(reference, positions=(cast(Any, True),))
    with pytest.raises(TypeError):
        replace(reference, positions=cast(Any, [0]))

    assert project_explain_package.__all__ == composition_module.__all__ == ()
    for public in (pietto, project_package, metadata_package, semantic_package):
        for carrier in expected_fields:
            assert not hasattr(public, carrier.__name__)


@pytest.mark.parametrize(
    "kind",
    tuple(ProjectExplainArtifactReferenceKind),
)
def test_reference_kind_rejects_wrong_arity(
    kind: ProjectExplainArtifactReferenceKind,
) -> None:
    arity = _REFERENCE_ARITIES[kind]
    with pytest.raises(ValueError, match="arity"):
        ProjectExplainArtifactReference(
            kind=kind,
            positions=tuple(range(arity + 1)),
        )


def test_resolver_exercises_every_reference_kind(tmp_path: Path) -> None:
    payload = _payload(_selected_sections(tmp_path))
    context = payload.extension_catalog_evidence.contexts[0]
    expected = (
        (
            ProjectExplainArtifactReferenceKind.PACKAGE,
            (0,),
            payload.package_requirements.packages[0],
        ),
        (
            ProjectExplainArtifactReferenceKind.REQUIREMENT,
            (0,),
            payload.package_requirements.requirements[0],
        ),
        (
            ProjectExplainArtifactReferenceKind.TARGET,
            (0,),
            payload.compatibility.targets[0],
        ),
        (
            ProjectExplainArtifactReferenceKind.PACKAGE_TARGET_EVALUATION,
            (0, 0),
            payload.compatibility.package_target_evaluations[0],
        ),
        (
            ProjectExplainArtifactReferenceKind.MATRIX_CELL,
            (0, 0),
            payload.compatibility.rows[0].cells[0],
        ),
        (
            ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_CONTEXT,
            (0, 0),
            context,
        ),
        (
            ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG,
            (0, 0, 0),
            context.catalogs[0],
        ),
        (
            ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_SOURCE,
            (0, 0, 0, 0),
            context.catalogs[0].source_occurrences[0],
        ),
        (
            ProjectExplainArtifactReferenceKind.EXTENSION_REQUIREMENT_EVIDENCE,
            (0, 0, 0),
            context.requirements[0],
        ),
        (
            ProjectExplainArtifactReferenceKind.REQUIREMENT_PORTABILITY,
            (0,),
            payload.portability.requirements[0],
        ),
        (
            ProjectExplainArtifactReferenceKind.PROJECT_PORTABILITY,
            (),
            payload.portability,
        ),
    )
    for kind, positions, value in expected:
        reference = ProjectExplainArtifactReference(kind=kind, positions=positions)
        assert _resolve_project_explain_reference(payload, reference) is value


@pytest.mark.parametrize(
    ("kind", "positions"),
    (
        (ProjectExplainArtifactReferenceKind.PACKAGE, (99,)),
        (ProjectExplainArtifactReferenceKind.REQUIREMENT, (99,)),
        (ProjectExplainArtifactReferenceKind.TARGET, (99,)),
        (ProjectExplainArtifactReferenceKind.PACKAGE_TARGET_EVALUATION, (99, 0)),
        (ProjectExplainArtifactReferenceKind.PACKAGE_TARGET_EVALUATION, (0, 99)),
        (ProjectExplainArtifactReferenceKind.MATRIX_CELL, (99, 0)),
        (ProjectExplainArtifactReferenceKind.MATRIX_CELL, (0, 99)),
        (ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_CONTEXT, (99, 0)),
        (ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG, (0, 0, 99)),
        (ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_SOURCE, (0, 0, 0, 99)),
        (
            ProjectExplainArtifactReferenceKind.EXTENSION_REQUIREMENT_EVIDENCE,
            (0, 0, 99),
        ),
        (ProjectExplainArtifactReferenceKind.REQUIREMENT_PORTABILITY, (99,)),
    ),
)
def test_resolver_rejects_out_of_range_coordinates(
    tmp_path: Path,
    kind: ProjectExplainArtifactReferenceKind,
    positions: tuple[int, ...],
) -> None:
    payload = _payload(_selected_sections(tmp_path))
    with pytest.raises(ValueError):
        _resolve_project_explain_reference(
            payload,
            ProjectExplainArtifactReference(kind=kind, positions=positions),
        )


def test_resolver_rejects_missing_and_duplicate_context_or_evidence(
    tmp_path: Path,
) -> None:
    missing = _payload(_nonextension_sections(tmp_path / "missing"))
    context_reference = ProjectExplainArtifactReference(
        kind=ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_CONTEXT,
        positions=(0, 0),
    )
    with pytest.raises(ValueError, match="one exact context"):
        _resolve_project_explain_reference(missing, context_reference)

    payload = _payload(_selected_sections(tmp_path / "selected"))
    projection = payload.extension_catalog_evidence
    original_contexts = projection.contexts
    object.__setattr__(
        projection, "contexts", (original_contexts[0], *original_contexts)
    )
    try:
        with pytest.raises(ValueError, match="one exact context"):
            _resolve_project_explain_reference(payload, context_reference)
    finally:
        object.__setattr__(projection, "contexts", original_contexts)

    context = projection.contexts[0]
    original_requirements = context.requirements
    object.__setattr__(context, "requirements", ())
    try:
        with pytest.raises(ValueError, match="one exact evidence"):
            _resolve_project_explain_reference(
                payload,
                ProjectExplainArtifactReference(
                    kind=(
                        ProjectExplainArtifactReferenceKind.EXTENSION_REQUIREMENT_EVIDENCE
                    ),
                    positions=(0, 0, 0),
                ),
            )
    finally:
        object.__setattr__(context, "requirements", original_requirements)


def test_requirement_explanations_preserve_request_target_and_result_order(
    tmp_path: Path,
) -> None:
    payload = _payload(_selected_sections(tmp_path, target_count=2))

    assert tuple(
        explanation.request.positions
        for explanation in payload.requirement_explanations
    ) == ((0,), (1,))
    dependency, root = payload.requirement_explanations
    assert dependency.declared_by.positions == (0,)
    assert dependency.requested_by.positions == (1,)
    assert root.declared_by.positions == root.requested_by.positions == (1,)
    for requirement_position, explanation in enumerate(
        payload.requirement_explanations
    ):
        assert explanation.portability.positions == (requirement_position,)
        assert tuple(target.target.positions for target in explanation.targets) == (
            (0,),
            (1,),
        )
        assert tuple(target.evaluation.positions for target in explanation.targets) == (
            (explanation.declared_by.positions[0], 0),
            (explanation.declared_by.positions[0], 1),
        )
        assert tuple(
            target.matrix_cell.positions for target in explanation.targets
        ) == (
            (requirement_position, 0),
            (requirement_position, 1),
        )
        assert all(
            target.extension_evidence is not None for target in explanation.targets
        )


def test_multiple_requirements_preserve_global_slice3_order(tmp_path: Path) -> None:
    catalog = inspection_slice._direct_catalog()
    selection = select_extension_catalog(
        slice5.availability_slice._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        ),
        catalog.metadata.target,
    )
    requirements = inspection_slice._requirements(
        inspection_slice._key("first", extension="example_extension"),
        inspection_slice._key("second", extension="example_extension"),
        name="multiple",
    )
    scope = catalog.exact_entry_groups[0].scope
    context = inspection_slice._context(
        requirements,
        (0, scope, selection),
        (1, scope, selection),
    )
    payload = _payload(_sections(tmp_path, (context,), requirements))

    assert tuple(
        explanation.request.positions[0]
        for explanation in payload.requirement_explanations
    ) == tuple(range(4))


def test_nonextension_blocked_and_ambiguous_evidence_rules_are_exact(
    tmp_path: Path,
) -> None:
    nonextension = _payload(_nonextension_sections(tmp_path / "nonextension"))
    assert all(
        target.extension_evidence is None and target.source_evidence == ()
        for explanation in nonextension.requirement_explanations
        for target in explanation.targets
    )

    blocked = _payload(_blocked_sections(tmp_path / "blocked"))
    assert all(
        target.extension_evidence is None and target.source_evidence == ()
        for explanation in blocked.requirement_explanations
        for target in explanation.targets
    )

    for conflict in (False, True):
        unselected = _payload(
            _unselected_sections(
                tmp_path / ("conflict" if conflict else "ambiguous"),
                conflict=conflict,
            )
        )
        assert all(
            target.extension_evidence is not None and target.source_evidence == ()
            for explanation in unselected.requirement_explanations
            for target in explanation.targets
        )


def test_source_reference_dedup_uses_catalog_then_occurrence_order_only(
    tmp_path: Path,
) -> None:
    sections = _source_rich_sections(tmp_path)
    payload = _payload(sections)
    first_context = payload.extension_catalog_evidence.contexts[0]
    first_target = payload.requirement_explanations[0].targets[0]

    assert tuple(reference.positions for reference in first_target.source_evidence) == (
        (0, 0, 0, 0),
        (0, 0, 0, 1),
        (0, 0, 0, 2),
    )
    assert len(first_context.catalogs[0].source_occurrences) == 3
    assert first_context is sections[2].contexts[0]
    assert tuple(
        source.position for source in first_context.catalogs[0].source_occurrences
    ) == (0, 1, 2)


def test_empty_target_denominator_retains_request_and_portability_links(
    tmp_path: Path,
) -> None:
    payload = _payload(_empty_sections(tmp_path))

    assert payload.compatibility.targets == ()
    assert payload.extension_catalog_evidence.contexts == ()
    assert payload.requirement_explanations
    for position, explanation in enumerate(payload.requirement_explanations):
        assert explanation.request.positions == (position,)
        assert explanation.targets == ()
        assert explanation.portability.positions == (position,)


def test_cross_section_root_and_portability_mismatches_fail_closed(
    tmp_path: Path,
) -> None:
    sections = _selected_sections(tmp_path / "selected")
    package, matrix, evidence, portability = sections
    with pytest.raises(TypeError, match="Slice 3"):
        _compose_project_explain_payload(
            cast(Any, object()), matrix, evidence, portability
        )
    with pytest.raises(TypeError, match="Slice 4"):
        _compose_project_explain_payload(
            package, cast(Any, object()), evidence, portability
        )
    with pytest.raises(TypeError, match="Slice 5"):
        _compose_project_explain_payload(
            package, matrix, cast(Any, object()), portability
        )
    with pytest.raises(TypeError, match="Slice 6"):
        _compose_project_explain_payload(package, matrix, evidence, cast(Any, object()))

    empty_package = slice6._package_projection(tmp_path / "empty-package", 0)
    with pytest.raises(ValueError, match="one matrix row"):
        _compose_project_explain_payload(
            empty_package,
            matrix,
            evidence,
            portability,
        )
    empty_portability = _empty_sections(tmp_path / "empty-portability")[3]
    with pytest.raises(ValueError, match="canonical Slice 6"):
        _compose_project_explain_payload(
            package,
            matrix,
            evidence,
            empty_portability,
        )

    requirement_portability = portability.requirements[0]
    original_position = requirement_portability.requirement_position
    object.__setattr__(requirement_portability, "requirement_position", 99)
    try:
        with pytest.raises(ValueError, match="canonical Slice 6"):
            _compose_project_explain_payload(
                package,
                matrix,
                evidence,
                portability,
            )
    finally:
        object.__setattr__(
            requirement_portability,
            "requirement_position",
            original_position,
        )


def test_missing_or_extra_extension_evidence_fails_closed(tmp_path: Path) -> None:
    checked = _selected_sections(tmp_path / "checked", name="shared")
    with pytest.raises(ValueError, match="complete Slice 5 evidence"):
        _compose_project_explain_payload(
            checked[0],
            checked[1],
            ProjectExplainExtensionCatalogEvidenceProjection(contexts=()),
            checked[3],
        )

    blocked = _blocked_sections(tmp_path / "blocked", name="shared")
    with pytest.raises(ValueError, match="Non-checked|forbid"):
        _compose_project_explain_payload(
            blocked[0],
            blocked[1],
            checked[2],
            blocked[3],
        )

    nonextension = _nonextension_sections(tmp_path / "nonextension", name="shared")
    with pytest.raises(ValueError, match="exact Slice 3 request context"):
        _compose_project_explain_payload(
            nonextension[0],
            nonextension[1],
            checked[2],
            nonextension[3],
        )


def test_context_request_target_catalog_and_source_grafts_fail_closed(
    tmp_path: Path,
) -> None:
    sections = _selected_sections(tmp_path)
    package, matrix, projection, portability = sections
    first_context = projection.contexts[0]

    wrong_requirement = replace(
        first_context.requirements[0],
        requirement_position=1,
    )
    wrong_request_context = replace(
        first_context,
        requirements=(wrong_requirement,),
    )
    wrong_request_projection = replace(
        projection,
        contexts=(wrong_request_context, *projection.contexts[1:]),
    )
    with pytest.raises(ValueError, match="exact Slice 3 request context"):
        _compose_project_explain_payload(
            package,
            matrix,
            wrong_request_projection,
            portability,
        )

    wrong_target_context = replace(first_context, target_position=99)
    wrong_target_projection = replace(
        projection,
        contexts=(wrong_target_context, *projection.contexts[1:]),
    )
    with pytest.raises(ValueError, match="out of range"):
        _compose_project_explain_payload(
            package,
            matrix,
            wrong_target_projection,
            portability,
        )

    original_contexts = projection.contexts
    object.__setattr__(projection, "contexts", tuple(reversed(original_contexts)))
    try:
        with pytest.raises(ValueError, match="package by target order"):
            _compose_project_explain_payload(package, matrix, projection, portability)
    finally:
        object.__setattr__(projection, "contexts", original_contexts)

    object.__setattr__(projection, "contexts", (first_context, first_context))
    try:
        with pytest.raises(ValueError, match="package by target order"):
            _compose_project_explain_payload(package, matrix, projection, portability)
    finally:
        object.__setattr__(projection, "contexts", original_contexts)

    catalog = first_context.catalogs[0]
    original_catalog_position = catalog.position
    object.__setattr__(catalog, "position", 1)
    try:
        with pytest.raises(ValueError, match="dense context order"):
            _compose_project_explain_payload(package, matrix, projection, portability)
    finally:
        object.__setattr__(catalog, "position", original_catalog_position)

    source = catalog.source_occurrences[0]
    original_source_position = source.position
    object.__setattr__(source, "position", 1)
    try:
        with pytest.raises(ValueError, match="dense occurrence order"):
            _compose_project_explain_payload(package, matrix, projection, portability)
    finally:
        object.__setattr__(source, "position", original_source_position)


def test_payload_retains_four_authorities_and_existing_envelope_accepts_it(
    tmp_path: Path,
) -> None:
    sections = _selected_sections(tmp_path)
    payload = _payload(sections)

    assert payload.package_requirements is sections[0]
    assert payload.compatibility is sections[1]
    assert payload.extension_catalog_evidence is sections[2]
    assert payload.portability is sections[3]
    envelope = ProjectExplainEnvelope[ProjectExplainPayload](
        format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
        ok=True,
        diagnostics=(),
        payload=payload,
    )
    assert envelope.payload is payload


def test_source_has_no_private_authority_graph_global_id_json_text_cli_or_io() -> None:
    source = _read(SOURCE)
    for forbidden in (
        "PackageInspectionFactSet",
        "CapabilityInspectionFactSet",
        "ExtensionCatalogInspectionFactSet",
        "ExtensionSignatureProviderContext",
        "lookup_capability(",
        "check_package_capability_requirements(",
        "select_extension_catalog(",
        "UUID",
        "global_id",
        "GraphNode",
        "GraphEdge",
        "import json",
        "json.dumps",
        "serialize",
        "render_",
        "argparse",
        "pietto.cli",
        "pathlib",
        "import os",
        "open(",
        "requests",
        "socket",
    ):
        assert forbidden not in source


def test_spec_package_inventory_and_retained_later_handoff_are_exact() -> None:
    document = _read(SPEC)
    normalized = " ".join(document.split())
    for required in (
        "PHASE58_SLICE7_SELF_OWNED_OPEN = 0",
        "REQUEST -> RESOLUTION -> RESULT",
        "deterministic artifact-local coordinates",
        "reference-level deduplication",
        "Slice 8 remains `UNSTARTED / NOT AUTHORIZED`",
        "Phase 59 retains the provenance and lineage graph",
    ):
        assert required in normalized

    package_smoke = _read(PACKAGE_SMOKE)
    for required in (
        'f"{prefix}/_project_explain/composition.py"',
        '"installed private project explain composition import"',
        "import pietto._project_explain.composition",
    ):
        assert required in package_smoke
