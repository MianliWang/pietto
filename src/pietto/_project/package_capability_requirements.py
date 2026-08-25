"""Private package-owned capability requirement binding construction."""

from __future__ import annotations

from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
)
from pietto._project.package_load_plan import LoadedDependencyPackage, LoadedPackage
from pietto._project.package_loader import LoadedRootPackage
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementOccurrence,
)

__all__: tuple[str, ...] = ()


def _package_capability_requirement_binding(
    package: LoadedPackage,
) -> PackageCapabilityRequirementBinding | None:
    """Build one binding from an already-loaded package's own declaration."""

    if type(package) not in {LoadedRootPackage, LoadedDependencyPackage}:
        raise TypeError("Package requirement binding requires an exact loaded package.")
    declaration = package.catalog.root_package.manifest.capability_requirements
    if declaration is None:
        return None
    occurrences = tuple(
        CapabilityRequirementOccurrence(declaration.identity, position, key)
        for position, key in enumerate(declaration.keys)
    )
    requirements = CapabilityRequirementCollection(
        declaration.identity,
        occurrences,
    )
    return PackageCapabilityRequirementBinding(package, requirements)
