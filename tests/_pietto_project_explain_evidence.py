from __future__ import annotations

from pathlib import Path
from typing import cast


import _pietto_project_package as package_slice
import _pietto_project_capability as checking_slice
import _pietto_project_extension_availability as availability_slice
import _pietto_project_extension_inspection as inspection_slice
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
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
)
from pietto._project.package_load_plan import LoadedPackage
from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainRequirementTargetMatrix,
    _project_requirement_target_matrix,
)
from pietto._project_explain.extension_catalog_evidence_projection import (
    ProjectExplainExtensionCatalogEvidenceProjection,
    _project_extension_catalog_evidence,
)
from pietto._project_explain.package_requirement_projection import (
    ProjectExplainPackageRequirementProjection,
    _project_package_requirement_provenance,
)
from pietto.semantic.capability_profiles import CapabilityRequirementCollection


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
                checking_slice._compiler_ledger()
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
