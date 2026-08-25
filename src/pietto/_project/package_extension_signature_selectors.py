"""Private loaded-package extension-signature selector binding."""

from __future__ import annotations

from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
)
from pietto._project.package_load_plan import LoadedDependencyPackage, LoadedPackage
from pietto._project.package_loader import LoadedRootPackage
from pietto._project.package_manifest import PackageManifestCapabilityRequirements
from pietto.semantic.extension_signature_requirements import (
    ExtensionSignatureRequirementSelectorOccurrence,
    ExtensionSignatureRequirementSelectors,
)

__all__: tuple[str, ...] = ()


def _package_extension_signature_requirement_selectors(
    package: LoadedPackage,
    binding: PackageCapabilityRequirementBinding | None,
) -> ExtensionSignatureRequirementSelectors | None:
    """Bind one loaded package's exact typed selector sidecar when schema v3."""

    if type(package) not in {LoadedRootPackage, LoadedDependencyPackage}:
        raise TypeError("Package extension selectors require an exact loaded package.")
    manifest = package.catalog.root_package.manifest
    declaration = manifest.capability_requirements
    if binding is None:
        if declaration is not None and declaration.extension_signature_selectors:
            raise ValueError("Unbound package requirements forbid selector authority.")
        return None
    if type(binding) is not PackageCapabilityRequirementBinding:
        raise TypeError("Package extension selectors require an exact binding.")
    if binding.package is not package:
        raise ValueError("Package extension selectors require exact package ownership.")
    if type(declaration) is not PackageManifestCapabilityRequirements:
        raise ValueError("Package extension selectors require declared requirements.")
    if (
        binding.requirements.identity is not declaration.identity
        or len(binding.requirements.occurrences) != len(declaration.keys)
        or any(
            occurrence.key is not key
            for occurrence, key in zip(
                binding.requirements.occurrences,
                declaration.keys,
                strict=True,
            )
        )
    ):
        raise ValueError("Package extension selectors require exact binding authority.")
    if manifest.schema_version == 1:
        raise ValueError("Schema-v1 packages forbid requirement bindings.")
    if manifest.schema_version == 2:
        return None
    return ExtensionSignatureRequirementSelectors(
        binding.requirements,
        tuple(
            ExtensionSignatureRequirementSelectorOccurrence(
                occurrence.requirement_position,
                occurrence.selector,
            )
            for occurrence in declaration.extension_signature_selectors
        ),
    )
