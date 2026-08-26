from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import pietto
import pietto._project as project_package
import test_phase55_slice10_package_inspection_canonical_serialization as package_upstream
import test_phase56_slice6_exact_capability_requirement_checking as checking_upstream
import test_phase57_slice5_extension_catalog_construction_completeness_canonical as catalog_upstream
import test_phase57_slice8_extension_signature_provider_checking_integration as provider_upstream
import test_phase58_slice10_package_capability_requirement_declaration as requirement_upstream
import test_phase58_slice12_package_extension_signature_selector_authority as selector_upstream
from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
    build_declared_capability_profile_availability,
)
from pietto._project.capability_checking import (
    CapabilityRequirementCheck,
    CapabilityRequirementStatus,
    PackageCapabilityRequirementsBlocked,
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
    ExtensionCatalogSelectionOutcome,
    select_extension_catalog,
)
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspectionFactSet,
    ExtensionCatalogInspectionLookupVariant,
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
    PackageGraphCapabilityEvaluationRef,
    PackageGraphCatalogEvidenceRef,
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
from pietto.semantic.capability_lookup import Absent, Conflict, Unknown
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
        checking_upstream.slice5._compiler_ledger()
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


def test_capability_statuses_blockers_and_target_order_retain_exact_witnesses(
    tmp_path: Path,
) -> None:
    _package_facts_value, capability_facts, snapshot = _generic_authority(tmp_path)
    target_zero = tuple(
        evaluation
        for evaluation in snapshot.capability_evaluations
        if evaluation.ref.target_position == 0
    )
    target_one = tuple(
        evaluation
        for evaluation in snapshot.capability_evaluations
        if evaluation.ref.target_position == 1
    )

    assert tuple(
        cast(CapabilityRequirementCheck, item.evidence).status for item in target_zero
    ) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.UNSUPPORTED,
        CapabilityRequirementStatus.ABSENT,
        CapabilityRequirementStatus.UNKNOWN,
        CapabilityRequirementStatus.CONFLICT,
    )
    checks = tuple(
        cast(CapabilityRequirementCheck, item.evidence) for item in target_zero
    )
    assert isinstance(checks[2].provider_result, Absent)
    assert isinstance(checks[3].target_result, Unknown)
    assert isinstance(checks[4].provider_result, Conflict)
    assert checks[4].provider_result.evidence
    assert all(
        type(item.evidence) is PackageCapabilityRequirementsBlocked
        and item.cell.check is None
        and item.evidence is item.cell.column.result
        for item in target_one
    )
    assert tuple(
        (
            evaluation.ref.requirement.position,
            evaluation.ref.target_position,
        )
        for evaluation in snapshot.capability_evaluations
    ) == tuple(
        (requirement_position, target_position)
        for requirement_position in range(5)
        for target_position in range(2)
    )
    assert all(
        evaluation.facts is capability_facts[0]
        for evaluation in snapshot.capability_evaluations
    )
    assert snapshot.catalog_evidence == ()
    with pytest.raises(ValueError, match="every fact-set matrix cell"):
        replace(
            snapshot,
            capability_evaluations=snapshot.capability_evaluations[:-1],
        )


def test_equal_key_packages_remain_distinct_and_impossible_mapping_fails_closed(
    tmp_path: Path,
) -> None:
    key = checking_upstream._SUPPORTED_PROVIDER_FACT.key
    declaration = requirement_upstream._declaration(_entry(key))
    dep_digest = requirement_upstream._write_package(
        tmp_path,
        "dep",
        name="dep",
        declaration=declaration,
    )
    root_digest = requirement_upstream._write_package(
        tmp_path,
        "root",
        declaration=declaration,
        dependencies=(("example", "dep", "1.0.0", dep_digest, "../dep"),),
    )
    package_facts = _package_facts(tmp_path, "root", root_digest)
    composition = checking_upstream._composition(
        checking_upstream._target_fact(key),
    )
    contexts = (
        CapabilityCheckingTargetContext(
            0,
            composition,
            checking_upstream._availability(composition),
        ),
    )
    capability_facts = _capability_facts(package_facts, contexts)
    slots = _empty_catalog_slots(capability_facts)
    first = _snapshot(package_facts, capability_facts, slots)
    second = _snapshot(package_facts, capability_facts, slots)

    assert len(first.capability_evaluations) == 2
    left, right = first.capability_evaluations
    assert left.cell.check is not None and right.cell.check is not None
    assert left.cell.check.occurrence.key == right.cell.check.occurrence.key
    assert left.ref.requirement.package.position == 0
    assert right.ref.requirement.package.position == 1
    assert left.ref != right.ref
    assert first.scope is not second.scope
    assert tuple(
        (
            item.ref.requirement.package.position,
            item.ref.requirement.position,
            item.ref.target_position,
        )
        for item in first.capability_evaluations
    ) == tuple(
        (
            item.ref.requirement.package.position,
            item.ref.requirement.position,
            item.ref.target_position,
        )
        for item in second.capability_evaluations
    )

    failed = _build_package_graph(
        package_facts,
        capability_facts=(capability_facts[1], capability_facts[0]),
        extension_catalog_facts=slots,
    )
    assert failed.outcome is PackageGraphOutcome.ERROR
    assert failed.snapshot is None
    assert "exact package occurrence order" in failed.errors[0].message


def test_selector_unbound_and_zero_target_inputs_create_no_synthetic_evidence(
    tmp_path: Path,
) -> None:
    manifest = selector_upstream._manifest(
        schema_version=2,
        requirements=(selector_upstream._requirement(),),
    )
    _, digest = selector_upstream._write_package(tmp_path, "root", manifest)
    package_facts = _package_facts(tmp_path, "root", digest)
    loaded = cast(LoadedPackage, package_facts.inspection.packages[0].entry.package)
    binding = _package_capability_requirement_binding(loaded)
    assert binding is not None
    key = binding.requirements.occurrences[0].key
    composition = checking_upstream._composition(
        checking_upstream._target_fact(key),
    )
    contexts = (
        CapabilityCheckingTargetContext(
            0,
            composition,
            checking_upstream._availability(composition),
        ),
    )
    capability_facts = _capability_facts(package_facts, contexts)
    snapshot = _snapshot(package_facts, capability_facts, (None,))

    assert len(snapshot.requirements) == len(snapshot.capability_evaluations) == 1
    assert snapshot.selectors == snapshot.catalog_evidence == ()
    evaluation = snapshot.capability_evaluations[0]
    assert evaluation.selector is None
    assert type(evaluation.evidence) is CapabilityRequirementCheck
    assert evaluation.evidence.status is CapabilityRequirementStatus.UNKNOWN

    zero_facts = _capability_facts(package_facts, ())
    zero = _snapshot(package_facts, zero_facts, ())
    assert len(zero.requirements) == 1
    assert zero.capability_evaluations == zero.catalog_evidence == ()


def test_catalog_outcomes_sources_and_provider_evidence_remain_separate(
    tmp_path: Path,
) -> None:
    package_facts, capability_facts, catalog_facts, snapshot = _extension_authority(
        tmp_path
    )
    assert len(snapshot.capability_evaluations) == len(snapshot.catalog_evidence) == 4
    assert tuple(
        evidence.provider.selection.outcome for evidence in snapshot.catalog_evidence
    ) == (
        ExtensionCatalogSelectionOutcome.SELECTED,
        ExtensionCatalogSelectionOutcome.UNDECLARED,
        ExtensionCatalogSelectionOutcome.AMBIGUOUS,
        ExtensionCatalogSelectionOutcome.CONFLICT,
    )
    assert tuple(
        cast(CapabilityRequirementCheck, evaluation.evidence).status
        for evaluation in snapshot.capability_evaluations
    ) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.UNKNOWN,
        CapabilityRequirementStatus.UNKNOWN,
        CapabilityRequirementStatus.UNKNOWN,
    )
    selected = snapshot.catalog_evidence[0]
    assert selected.facts is catalog_facts[0]
    assert selected.provider is catalog_facts[0].inspection.provider_occurrences[0]
    assert (
        selected.provider.lookup.variant
        is ExtensionCatalogInspectionLookupVariant.FOUND
    )
    selected_catalog = selected.facts.inspection.catalogs[0]
    assert tuple(source.position for source in selected_catalog.source_occurrences) == (
        0,
        1,
    )
    assert selected_catalog.entries[0].evidence.source_positions == (1, 0, 1)
    assert selected.provider.selection.selected_catalog_position == 0
    assert selected_catalog.reference.name == "selected"
    assert selected_catalog.content_sha256
    assert all(
        evidence.facts is catalog_facts[evidence.ref.target_position]
        for evidence in snapshot.catalog_evidence
    )
    assert all(
        evaluation.facts is capability_facts[0]
        for evaluation in snapshot.capability_evaluations
    )
    for invalid_slots in (
        catalog_facts[:-1],
        (*catalog_facts, None),
    ):
        failed = _build_package_graph(
            package_facts,
            capability_facts=capability_facts,
            extension_catalog_facts=invalid_slots,
        )
        assert failed.outcome is PackageGraphOutcome.ERROR
        assert failed.snapshot is None
        assert "one exact slot" in failed.errors[0].message


def test_refs_reject_foreign_wrong_domain_and_grafted_catalog_authority(
    tmp_path: Path,
) -> None:
    package_facts, capability_facts, catalog_facts, first = _extension_authority(
        tmp_path
    )
    second = _snapshot(package_facts, capability_facts, catalog_facts)
    capability = first.capability_evaluations[0]
    catalog = first.catalog_evidence[0]

    assert first.capability_evaluation(capability.ref) is capability
    assert first.catalog_evidence_occurrence(catalog.ref) is catalog
    with pytest.raises(ValueError, match="foreign snapshot"):
        first.capability_evaluation(second.capability_evaluations[0].ref)
    with pytest.raises(ValueError, match="foreign snapshot"):
        first.catalog_evidence_occurrence(second.catalog_evidence[0].ref)
    with pytest.raises(TypeError, match="Capability evaluation"):
        first.capability_evaluation(
            cast(PackageGraphCapabilityEvaluationRef, catalog.ref)
        )
    with pytest.raises(TypeError, match="Catalog evidence"):
        first.catalog_evidence_occurrence(
            cast(PackageGraphCatalogEvidenceRef, capability.ref)
        )

    grafted = replace(catalog, facts=catalog_facts[1])
    with pytest.raises(ValueError, match="foreign provider context"):
        replace(
            first,
            catalog_evidence=(grafted, *first.catalog_evidence[1:]),
        )
    assert tuple(
        field.name for field in fields(PackageGraphCapabilityEvaluationRef)
    ) == (
        "scope",
        "requirement",
        "target_position",
    )
    assert tuple(field.name for field in fields(PackageGraphCatalogEvidenceRef)) == (
        "scope",
        "selector",
        "target_position",
    )


def test_model_is_private_attaches_only_existing_facts_and_defers_later_domains() -> (
    None
):
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    builder = ast.get_source_segment(
        source,
        next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_build_package_graph"
        ),
    )
    assert builder is not None

    assert {
        "pietto._project.capability_checking",
        "pietto._project.capability_inspection",
        "pietto._project.capability_matrix",
        "pietto._project.extension_catalog_inspection",
    } <= imported_modules
    assert not any(
        module.startswith("pietto._project_explain") for module in imported_modules
    )
    for forbidden in (
        "check_package_capability_requirements",
        "build_package_capability_checking_matrix",
        "select_extension_catalog",
        "extension_signature_provider_authority",
        "lookup_capability",
        "bfs",
        "dfs",
        "shortest",
        "to_json",
        "canonical_bytes =",
        "installation",
    ):
        assert forbidden not in builder
    assert project_package.__all__ == ()
    assert not hasattr(pietto, "PackageGraphCapabilityEvaluationRef")
    assert not hasattr(project_package, "PackageGraphCapabilityEvaluationRef")


def test_slice5_spec_freezes_attachment_semantics_deferrals_and_lifecycle() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "provenance attachment, not capability evaluation",
        "package -> requirement -> selector when applicable -> target/context",
        "UNKNOWN != ABSENT",
        "omission != UNSUPPORTED",
        "BLOCKED != checked UNKNOWN",
        "Sparse positive topology",
        "No checking, provider reselection, catalog rebuilding, or inference",
        "Project Explain v1 and existing CLI remain zero-delta",
        "Slice 5 current",
        "Slice 6 next/unstarted",
        "Attach Phase 59 capability catalog provenance",
    ):
        assert required in normalized
