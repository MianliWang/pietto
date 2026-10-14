from __future__ import annotations

from pathlib import Path
from typing import cast


import _pietto_project_package as package_upstream
import _pietto_project_capability as checking_upstream
import _pietto_project_extension_catalog as catalog_upstream
import _pietto_project_extension_provider as provider_upstream
import _pietto_project_requirements as requirement_upstream
import _pietto_project_extension_selectors as selector_upstream
from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
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
    ExtensionCatalogAvailabilityDeclaration,
    ExtensionCatalogAvailabilityOwner,
    select_extension_catalog,
)
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspectionFactSet,
    build_extension_catalog_inspection,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderContext,
    ExtensionSignatureProviderSelectionOccurrence,
)
from pietto._project.package_capability_requirements import (
    _package_capability_requirement_binding,
)
from pietto._project.package_extension_signature_selectors import (
    _package_extension_signature_requirement_selectors,
)
from pietto._project.package_graph import (
    PackageGraphOutcome,
    PackageGraphSnapshot,
    _build_package_graph,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    _build_package_inspection_fact_set,
)
from pietto._project.package_load_plan import LoadedPackage
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityKey,
    CapabilitySupport,
)
from pietto.semantic.extension_catalog import ConstructedExtensionCatalog


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "src/pietto/_project/package_graph.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase59-slice5-capability-catalog-typed-negative-evidence-provenance-v1.md"
)


def _entry(key: CapabilityKey) -> str:
    return requirement_upstream._entry(
        key.domain.value,
        subject=key.subject,
        operation=key.operation,
        operands=key.operands,
        context=key.context,
        dialect=key.dialect,
        extension=key.extension,
    )


def _package_facts(
    project: Path,
    package_path: str,
    digest: str,
) -> PackageInspectionFactSet:
    return _build_package_inspection_fact_set(
        package_upstream._plan(project, package_path, digest)
    )


def _capability_facts(
    package_facts: PackageInspectionFactSet,
    contexts: tuple[CapabilityCheckingTargetContext, ...],
) -> tuple[CapabilityInspectionFactSet, ...]:
    result: list[CapabilityInspectionFactSet] = []
    for package in package_facts.inspection.packages:
        loaded = cast(LoadedPackage, package.entry.package)
        binding = _package_capability_requirement_binding(loaded)
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


def _empty_catalog_slots(
    capability_facts: tuple[CapabilityInspectionFactSet, ...],
) -> tuple[None, ...]:
    return tuple(
        None
        for facts in capability_facts
        for _column in facts.inspection.matrix.columns
    )


def _snapshot(
    package_facts: PackageInspectionFactSet,
    capability_facts: tuple[CapabilityInspectionFactSet, ...],
    catalog_facts: tuple[ExtensionCatalogInspectionFactSet | None, ...],
) -> PackageGraphSnapshot:
    result = _build_package_graph(
        package_facts,
        capability_facts=capability_facts,
        extension_catalog_facts=catalog_facts,
    )
    assert result.outcome is PackageGraphOutcome.SUCCESS
    assert result.snapshot is not None
    return result.snapshot


def _generic_authority(
    tmp_path: Path,
) -> tuple[
    PackageInspectionFactSet,
    tuple[CapabilityInspectionFactSet, ...],
    PackageGraphSnapshot,
]:
    satisfied_key = checking_upstream._SUPPORTED_PROVIDER_FACT.key
    unsupported_key = checking_upstream._UNSUPPORTED_PROVIDER_FACT.key
    absent_key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="catalog_membership",
        context="builtin_registry",
    )
    omitted_key = next(
        fact.key
        for fact in checking_upstream._PROVIDER_FACTS
        if fact.key not in {satisfied_key, unsupported_key}
        and fact.support is CapabilitySupport.SUPPORTED
    )
    conflict_key = checking_upstream._COUNT_CONFLICT_KEY
    keys = (
        satisfied_key,
        unsupported_key,
        absent_key,
        omitted_key,
        conflict_key,
    )
    digest = requirement_upstream._write_package(
        tmp_path,
        "root",
        declaration=requirement_upstream._declaration(*map(_entry, keys)),
    )
    package_facts = _package_facts(tmp_path, "root", digest)
    composition = checking_upstream._composition(
        checking_upstream._target_fact(satisfied_key, reference="satisfied"),
        checking_upstream._target_fact(unsupported_key, reference="unsupported"),
        checking_upstream._target_fact(absent_key, reference="absent"),
        checking_upstream._target_fact(conflict_key, reference="conflict"),
    )
    ready = checking_upstream._availability(composition)
    blocked = build_declared_capability_profile_availability(
        checking_upstream._compiler_ledger()
    )
    assert type(ready) is DeclaredCapabilityProfileAvailabilityReady
    assert type(blocked) is DeclaredCapabilityProfileAvailabilityReady
    contexts = (
        CapabilityCheckingTargetContext(0, composition, ready),
        CapabilityCheckingTargetContext(1, composition, blocked),
    )
    capability_facts = _capability_facts(package_facts, contexts)
    snapshot = _snapshot(
        package_facts,
        capability_facts,
        _empty_catalog_slots(capability_facts),
    )
    return package_facts, capability_facts, snapshot


def _availability(
    *catalogs: ConstructedExtensionCatalog,
) -> DeclaredExtensionCatalogAvailability:
    return DeclaredExtensionCatalogAvailability(
        tuple(
            ExtensionCatalogAvailabilityDeclaration(
                ExtensionCatalogAvailabilityOwner.COMPILER,
                position,
                catalog,
            )
            for position, catalog in enumerate(catalogs)
        )
    )


def _extension_authority(
    tmp_path: Path,
) -> tuple[
    PackageInspectionFactSet,
    tuple[CapabilityInspectionFactSet, ...],
    tuple[ExtensionCatalogInspectionFactSet, ...],
    PackageGraphSnapshot,
]:
    manifest = selector_upstream._manifest(
        requirements=(
            selector_upstream._requirement(
                operation="shared",
                extension="example_extension",
            ),
        ),
        selectors=(
            selector_upstream._selector(
                0,
                "scalar_function",
                sql_name="shared",
                input_types=(("postgres_builtin", "text"),),
            ),
        ),
    )
    _, digest = selector_upstream._write_package(tmp_path, "root", manifest)
    package_facts = _package_facts(tmp_path, "root", digest)
    loaded = cast(LoadedPackage, package_facts.inspection.packages[0].entry.package)
    binding = _package_capability_requirement_binding(loaded)
    assert binding is not None
    selectors = _package_extension_signature_requirement_selectors(loaded, binding)
    assert selectors is not None
    key = binding.requirements.occurrences[0].key

    selected_catalog = provider_upstream._catalog(
        (catalog_upstream._scalar_entry((1, 0, 1), name="shared"),),
        reference=provider_upstream._reference("selected"),
        source_count=2,
    )
    ambiguous_catalogs = (
        provider_upstream._catalog(
            (catalog_upstream._scalar_entry(name="shared"),),
            reference=provider_upstream._reference("ambiguous-a"),
        ),
        provider_upstream._catalog(
            (catalog_upstream._scalar_entry(name="shared"),),
            reference=provider_upstream._reference("ambiguous-b"),
        ),
    )
    conflict_reference = provider_upstream._reference("conflict")
    conflict_catalogs = (
        provider_upstream._catalog(
            (catalog_upstream._scalar_entry(name="shared"),),
            reference=conflict_reference,
            source_count=1,
        ),
        provider_upstream._catalog(
            (catalog_upstream._scalar_entry(name="shared"),),
            reference=conflict_reference,
            source_count=2,
        ),
    )
    target = selected_catalog.metadata.target
    selections = (
        select_extension_catalog(_availability(selected_catalog), target),
        select_extension_catalog(DeclaredExtensionCatalogAvailability(()), target),
        select_extension_catalog(_availability(*ambiguous_catalogs), target),
        select_extension_catalog(_availability(*conflict_catalogs), target),
    )
    composition = checking_upstream._composition(
        checking_upstream._target_fact(key, reference="extension target"),
    )
    profile_availability = checking_upstream._availability(composition)
    contexts: list[CapabilityCheckingTargetContext] = []
    catalog_facts: list[ExtensionCatalogInspectionFactSet] = []
    for position, selection in enumerate(selections):
        provider_context = ExtensionSignatureProviderContext(
            selectors,
            (ExtensionSignatureProviderSelectionOccurrence(0, selection),),
        )
        contexts.append(
            CapabilityCheckingTargetContext(
                position,
                composition,
                profile_availability,
                provider_context,
            )
        )
        catalog_facts.append(build_extension_catalog_inspection(provider_context))
    capability_facts = (
        build_capability_inspection(
            build_package_capability_checking_matrix(
                loaded,
                binding,
                tuple(contexts),
            )
        ),
    )
    frozen_catalog_facts = tuple(catalog_facts)
    snapshot = _snapshot(
        package_facts,
        capability_facts,
        frozen_catalog_facts,
    )
    return package_facts, capability_facts, frozen_catalog_facts, snapshot
