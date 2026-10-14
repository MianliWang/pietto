from __future__ import annotations

from pathlib import Path
from typing import cast

import _pietto_project_capability as checking_slice
import _pietto_project_package as package_slice
from pietto._project.capability_availability import PackageCapabilityRequirementBinding
from pietto._project.capability_inspection import (
    CapabilityInspectionFactSet,
    build_capability_inspection,
)
from pietto._project.capability_matrix import build_package_capability_checking_matrix
from pietto._project.package_inspection import PackageInspectionFactSet
from pietto._project.package_load_plan import LoadedPackage
from pietto._project_explain.package_requirement_projection import (
    ProjectExplainPackageRequirementProjection,
    _project_package_requirement_provenance,
)
from pietto.semantic.capability_facts import CapabilityKey
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
)


def _requirements(
    namespace: str,
    name: str,
    *keys: CapabilityKey,
) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity(namespace, name)
    return CapabilityRequirementCollection(
        identity,
        tuple(
            CapabilityRequirementOccurrence(identity, position, key)
            for position, key in enumerate(keys)
        ),
    )


def _capability_facts(
    package_facts: PackageInspectionFactSet,
    collections: tuple[CapabilityRequirementCollection | None, ...],
) -> tuple[CapabilityInspectionFactSet, ...]:
    assert len(collections) == len(package_facts.inspection.packages)
    composition = checking_slice._composition()
    context = checking_slice._context(0, composition)
    result: list[CapabilityInspectionFactSet] = []
    for package, collection in zip(
        package_facts.inspection.packages,
        collections,
        strict=True,
    ):
        loaded = cast(LoadedPackage, package.entry.package)
        binding = (
            None
            if collection is None
            else PackageCapabilityRequirementBinding(loaded, collection)
        )
        matrix = build_package_capability_checking_matrix(
            loaded,
            binding,
            (context,),
        )
        result.append(build_capability_inspection(matrix))
    return tuple(result)


def _simple_authority(
    root: Path,
    *,
    dependency: CapabilityRequirementCollection | None = None,
    project: CapabilityRequirementCollection | None = None,
) -> tuple[
    PackageInspectionFactSet,
    tuple[CapabilityInspectionFactSet, ...],
]:
    package_facts = package_slice._simple_inspection(
        root,
        root_path=".",
        dependency_path="dep",
        authored_path="dep",
    )
    return package_facts, _capability_facts(
        package_facts,
        (dependency, project),
    )


def _projection(
    root: Path,
    *,
    dependency: CapabilityRequirementCollection | None = None,
    project: CapabilityRequirementCollection | None = None,
) -> ProjectExplainPackageRequirementProjection:
    package_facts, capability_facts = _simple_authority(
        root,
        dependency=dependency,
        project=project,
    )
    return _project_package_requirement_provenance(
        package_facts,
        capability_facts,
    )
