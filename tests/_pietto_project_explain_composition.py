from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any


import _pietto_project_extension_catalog as catalog_slice
import _pietto_project_extension_provider as provider_slice
import _pietto_project_extension_inspection as inspection_slice
import _pietto_project_explain_evidence as slice5
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
    ProjectExplainPayload,
    _compose_project_explain_payload,
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
