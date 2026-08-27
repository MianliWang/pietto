from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
from typing import cast

import pytest

import pietto
import pietto._project as project_package
import test_phase55_slice10_package_inspection_canonical_serialization as package_upstream
import test_phase56_slice6_exact_capability_requirement_checking as checking_upstream
import test_phase58_slice10_package_capability_requirement_declaration as requirement_upstream
import test_phase59_slice2_private_package_graph_model_snapshot_identity as model_upstream
import test_phase59_slice5_capability_catalog_typed_negative_evidence_provenance as slice5_upstream
from pietto._project.capability_checking import (
    CapabilityRequirementCheck,
    CapabilityRequirementStatus,
    PackageCapabilityRequirementsBlocked,
)
from pietto._project.capability_matrix import CapabilityCheckingTargetContext
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspectionProviderOccurrence,
)
from pietto._project.package_graph import (
    PackageGraphCapabilityEvaluation,
    PackageGraphCapabilityEvaluationRef,
    PackageGraphCatalogEvidence,
    PackageGraphDependency,
    PackageGraphDirectProvenanceStep,
    PackageGraphOutcome,
    PackageGraphPackageRef,
    PackageGraphProvenancePath,
    PackageGraphScope,
    PackageGraphSnapshot,
    PackageGraphWhyNot,
    _build_package_graph,
    _derive_package_graph_provenance_paths,
    _derive_package_graph_why_not,
    _package_graph_direct_provenance_steps,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    _build_package_inspection_fact_set,
)
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "src/pietto/_project/package_graph.py"
SPEC = REPO_ROOT / "docs/spec/phase59-slice6-direct-transitive-why-not-provenance-v1.md"


def _snapshot(facts: PackageInspectionFactSet) -> PackageGraphSnapshot:
    result = _build_package_graph(facts)
    assert result.outcome is PackageGraphOutcome.SUCCESS
    assert result.snapshot is not None
    return result.snapshot


def _root_graph(
    project: Path, digest: str
) -> tuple[PackageInspectionFactSet, PackageGraphSnapshot]:
    facts = _build_package_inspection_fact_set(
        package_upstream._plan(project, "root", digest)
    )
    return facts, _snapshot(facts)


def _diamond(
    *,
    reverse: bool = False,
) -> PackageGraphSnapshot:
    scope = PackageGraphScope()
    leaf = model_upstream._package(scope, 0, name="leaf")
    mid = model_upstream._package(scope, 1, name="mid")
    root = model_upstream._package(scope, 2, name="root")
    mid_leaf = model_upstream._dependency(mid, leaf, 0)
    root_first = model_upstream._dependency(root, mid if reverse else leaf, 0)
    root_second = model_upstream._dependency(root, leaf if reverse else mid, 1)
    return PackageGraphSnapshot(
        scope,
        (leaf, mid, root),
        (mid_leaf, root_first, root_second),
    )


def _chain(
    project: Path,
) -> tuple[PackageInspectionFactSet, PackageGraphSnapshot]:
    leaf_digest = package_upstream._write_package(project, "leaf", name="leaf")
    mid_digest = package_upstream._write_package(
        project,
        "mid",
        name="mid",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    root_digest = package_upstream._write_package(
        project,
        "root",
        dependencies=(("example", "mid", "1.0.0", mid_digest, "../mid"),),
    )
    return _root_graph(project, root_digest)


def _path_coordinates(
    paths: tuple[PackageGraphProvenancePath, ...],
) -> tuple[tuple[tuple[int, int, int], ...], ...]:
    return tuple(
        tuple(
            (
                witness.declaring_package.position,
                witness.ref.declaration_position,
                witness.resolved_package.position,
            )
            for step in path.steps
            for witness in (cast(PackageGraphDependency, step.witness),)
        )
        for path in paths
    )


def test_one_direct_dependency_retains_exact_one_step_witness(tmp_path: Path) -> None:
    leaf_digest = package_upstream._write_package(tmp_path, "leaf", name="leaf")
    root_digest = package_upstream._write_package(
        tmp_path,
        "root",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    _facts, snapshot = _root_graph(tmp_path, root_digest)
    dependency = snapshot.dependencies[0]

    paths = _derive_package_graph_provenance_paths(
        snapshot,
        dependency.declaring_package,
        dependency.resolved_package,
    )

    assert len(paths) == 1
    assert paths[0].start == dependency.declaring_package
    assert paths[0].end == dependency.resolved_package
    assert len(paths[0].steps) == 1
    assert paths[0].steps[0].witness is dependency


def test_requirement_selector_capability_and_catalog_paths_keep_exact_witnesses(
    tmp_path: Path,
) -> None:
    _package_facts, _capability_facts, _catalog_facts, snapshot = (
        slice5_upstream._extension_authority(tmp_path)
    )
    start = snapshot.packages[0].ref
    requirement = snapshot.requirements[0]
    selector = snapshot.selectors[0]
    evaluation = snapshot.capability_evaluations[0]
    catalog = snapshot.catalog_evidence[0]

    endpoints = (
        (requirement.ref, (requirement,)),
        (selector.ref, (requirement, selector)),
        (evaluation.ref, (requirement, selector, evaluation)),
        (catalog.ref, (requirement, selector, evaluation, catalog)),
    )
    for end, witnesses in endpoints:
        paths = _derive_package_graph_provenance_paths(snapshot, start, end)
        assert len(paths) == 1
        assert tuple(step.witness for step in paths[0].steps) == witnesses
        assert all(
            step.witness is witness
            for step, witness in zip(paths[0].steps, witnesses, strict=True)
        )

    direct = _package_graph_direct_provenance_steps(snapshot)
    expected = (
        *snapshot.dependencies,
        *snapshot.requirements,
        *snapshot.selectors,
        *snapshot.capability_evaluations,
        *snapshot.catalog_evidence,
        *snapshot.modules,
        *snapshot.declarations,
        *snapshot.fields,
        *snapshot.let_bindings,
        *snapshot.source_lineage,
        *snapshot.projection_lineage,
        *snapshot.expression_lineage,
        *snapshot.current_window_lineage,
    )
    assert len(direct) == len(expected)
    assert all(
        step.witness is witness for step, witness in zip(direct, expected, strict=True)
    )


def test_real_multi_hop_dependency_route_is_complete_and_ordered(
    tmp_path: Path,
) -> None:
    _facts, snapshot = _chain(tmp_path)
    paths = _derive_package_graph_provenance_paths(
        snapshot,
        snapshot.packages[-1].ref,
        snapshot.packages[0].ref,
    )

    assert len(paths) == 1
    assert len(paths[0].steps) == 2
    dependencies = tuple(
        cast(PackageGraphDependency, step.witness) for step in paths[0].steps
    )
    assert tuple(
        dependency.witness.coordinate.identity.name for dependency in dependencies
    ) == ("mid", "leaf")


def test_all_routes_keep_shorter_longer_and_authoritative_order() -> None:
    forward = _diamond()
    backward = _diamond(reverse=True)
    start = forward.packages[-1].ref
    end = forward.packages[0].ref
    forward_paths = _derive_package_graph_provenance_paths(forward, start, end)
    backward_paths = _derive_package_graph_provenance_paths(
        backward,
        backward.packages[-1].ref,
        backward.packages[0].ref,
    )

    assert tuple(len(path.steps) for path in forward_paths) == (1, 2)
    assert tuple(len(path.steps) for path in backward_paths) == (2, 1)
    forward_dependencies = tuple(
        cast(PackageGraphDependency, step.witness) for step in forward_paths[1].steps
    )
    assert tuple(
        dependency.witness.coordinate.identity.name
        for dependency in forward_dependencies
    ) == ("mid", "leaf")

    rebuilt = _diamond()
    rebuilt_paths = _derive_package_graph_provenance_paths(
        rebuilt,
        rebuilt.packages[-1].ref,
        rebuilt.packages[0].ref,
    )
    assert forward.scope is not rebuilt.scope
    assert _path_coordinates(forward_paths) == _path_coordinates(rebuilt_paths)
    assert forward_paths[0].start != rebuilt_paths[0].start


def test_parallel_equal_endpoint_occurrences_produce_distinct_paths(
    tmp_path: Path,
) -> None:
    dependency_digest = package_upstream._write_package(
        tmp_path,
        "leaf",
        name="leaf",
    )
    declaration = (
        "example",
        "leaf",
        "1.0.0",
        dependency_digest,
        "../leaf",
    )
    root_digest = package_upstream._write_package(
        tmp_path,
        "root",
        dependencies=(declaration, declaration),
    )
    _facts, snapshot = _root_graph(tmp_path, root_digest)
    paths = _derive_package_graph_provenance_paths(
        snapshot,
        snapshot.packages[-1].ref,
        snapshot.packages[0].ref,
    )

    assert len(paths) == 2
    assert tuple(len(path.steps) for path in paths) == (1, 1)
    first = cast(PackageGraphDependency, paths[0].steps[0].witness)
    second = cast(PackageGraphDependency, paths[1].steps[0].witness)
    assert first.ref.declaration_position == 0
    assert second.ref.declaration_position == 1
    assert first.ref != second.ref
    assert first.declaring_package == second.declaring_package
    assert first.resolved_package == second.resolved_package
    assert first.witness is not second.witness


def test_foreign_snapshot_and_wrong_endpoint_domains_fail_closed(
    tmp_path: Path,
) -> None:
    first = _diamond()
    second = _diamond()

    with pytest.raises(ValueError, match="foreign snapshot"):
        _derive_package_graph_provenance_paths(
            first,
            first.packages[-1].ref,
            second.packages[0].ref,
        )
    with pytest.raises(TypeError, match="package start ref"):
        _derive_package_graph_provenance_paths(
            first,
            cast(PackageGraphPackageRef, first.dependencies[0].ref),
            first.packages[0].ref,
        )
    with pytest.raises(TypeError, match="supported graph ref"):
        _derive_package_graph_provenance_paths(
            first,
            first.packages[-1].ref,
            cast(PackageGraphPackageRef, first.dependencies[0].ref),
        )
    with pytest.raises(TypeError, match="exact witness"):
        PackageGraphDirectProvenanceStep(first.packages[0])  # type: ignore[arg-type]

    _package_facts, _capability_facts, _catalog_facts, evidence_snapshot = (
        slice5_upstream._extension_authority(tmp_path)
    )
    with pytest.raises(ValueError, match="foreign snapshot"):
        _derive_package_graph_why_not(
            evidence_snapshot,
            second.packages[0].ref,
            evidence_snapshot.capability_evaluations[0].ref,
        )
    with pytest.raises(TypeError, match="supported graph ref"):
        _derive_package_graph_why_not(
            evidence_snapshot,
            evidence_snapshot.packages[0].ref,
            cast(PackageGraphCapabilityEvaluationRef, first.dependencies[0].ref),
        )


def test_capability_why_not_preserves_every_typed_terminal_distinction(
    tmp_path: Path,
) -> None:
    _package_facts, _capability_facts, snapshot = slice5_upstream._generic_authority(
        tmp_path
    )
    start = snapshot.packages[0].ref
    checked = tuple(
        evaluation
        for evaluation in snapshot.capability_evaluations
        if evaluation.ref.target_position == 0
    )
    blocked = tuple(
        evaluation
        for evaluation in snapshot.capability_evaluations
        if evaluation.ref.target_position == 1
    )

    assert _derive_package_graph_why_not(snapshot, start, checked[0].ref) == ()
    expected_statuses = (
        CapabilityRequirementStatus.UNSUPPORTED,
        CapabilityRequirementStatus.ABSENT,
        CapabilityRequirementStatus.UNKNOWN,
        CapabilityRequirementStatus.CONFLICT,
    )
    for evaluation, status in zip(checked[1:], expected_statuses, strict=True):
        why_not = _derive_package_graph_why_not(snapshot, start, evaluation.ref)
        assert len(why_not) == 1
        assert why_not[0].terminal_evidence is evaluation.evidence
        assert type(why_not[0].terminal_evidence) is CapabilityRequirementCheck
        assert why_not[0].terminal_evidence.status is status
        assert why_not[0].positive_path.end == evaluation.ref
        assert why_not[0].positive_path.steps[-1].witness is evaluation

    for evaluation in blocked:
        why_not = _derive_package_graph_why_not(snapshot, start, evaluation.ref)
        assert len(why_not) == 1
        assert why_not[0].terminal_evidence is evaluation.evidence
        assert type(why_not[0].terminal_evidence) is (
            PackageCapabilityRequirementsBlocked
        )
    absent = cast(CapabilityRequirementCheck, checked[2].evidence)
    unknown = cast(CapabilityRequirementCheck, checked[3].evidence)
    unsupported = cast(CapabilityRequirementCheck, checked[1].evidence)
    assert absent.status is not unknown.status
    assert unknown.status is not unsupported.status


def test_catalog_why_not_uses_exact_provider_and_never_success(
    tmp_path: Path,
) -> None:
    _package_facts, _capability_facts, _catalog_facts, snapshot = (
        slice5_upstream._extension_authority(tmp_path)
    )
    start = snapshot.packages[0].ref
    assert (
        _derive_package_graph_why_not(
            snapshot,
            start,
            snapshot.catalog_evidence[0].ref,
        )
        == ()
    )

    outcomes: list[str] = []
    for evidence in snapshot.catalog_evidence[1:]:
        why_not = _derive_package_graph_why_not(snapshot, start, evidence.ref)
        assert len(why_not) == 1
        terminal = why_not[0].terminal_evidence
        assert type(terminal) is ExtensionCatalogInspectionProviderOccurrence
        assert terminal is evidence.provider
        assert why_not[0].positive_path.steps[-1].witness is evidence
        outcomes.append(terminal.selection.outcome.value)
    assert tuple(outcomes) == ("undeclared", "ambiguous", "conflict")


def test_missing_positive_edge_and_zero_targets_create_no_why_not(
    tmp_path: Path,
) -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="catalog_membership",
        context="builtin_registry",
    )
    leaf_digest = requirement_upstream._write_package(
        tmp_path,
        "leaf",
        name="leaf",
    )
    root_digest = requirement_upstream._write_package(
        tmp_path,
        "root",
        declaration=requirement_upstream._declaration(slice5_upstream._entry(key)),
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    package_facts = slice5_upstream._package_facts(tmp_path, "root", root_digest)
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
    capability_facts = slice5_upstream._capability_facts(package_facts, contexts)
    snapshot = slice5_upstream._snapshot(
        package_facts,
        capability_facts,
        slice5_upstream._empty_catalog_slots(capability_facts),
    )
    evaluation = snapshot.capability_evaluations[0]
    assert evaluation.ref.requirement.package == snapshot.packages[-1].ref
    assert (
        _derive_package_graph_provenance_paths(
            snapshot,
            snapshot.packages[0].ref,
            evaluation.ref,
        )
        == ()
    )
    assert (
        _derive_package_graph_why_not(
            snapshot,
            snapshot.packages[0].ref,
            evaluation.ref,
        )
        == ()
    )

    zero_facts = slice5_upstream._capability_facts(package_facts, ())
    zero = slice5_upstream._snapshot(package_facts, zero_facts, ())
    assert zero.capability_evaluations == zero.catalog_evidence == ()
    assert not any(
        type(step.witness)
        in {PackageGraphCapabilityEvaluation, PackageGraphCatalogEvidence}
        for step in _package_graph_direct_provenance_steps(zero)
    )


def test_path_model_remains_private_on_demand_without_cached_query_surface() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    snapshot = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PackageGraphSnapshot"
    )
    snapshot_fields = {
        node.target.id
        for node in snapshot.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert (
        not {
            "all_paths",
            "transitive_closure",
            "all_why",
            "all_why_not",
            "reverse_indexes",
        }
        & snapshot_fields
    )
    assert tuple(field.name for field in fields(PackageGraphDirectProvenanceStep)) == (
        "witness",
    )
    assert tuple(field.name for field in fields(PackageGraphProvenancePath)) == (
        "start",
        "end",
        "steps",
    )
    assert tuple(field.name for field in fields(PackageGraphWhyNot)) == (
        "positive_path",
        "terminal_evidence",
    )

    derivation_names = {
        "_package_graph_direct_provenance_steps",
        "_derive_package_graph_provenance_paths",
        "_derive_package_graph_why_not",
    }
    derivation_source = "\n".join(
        ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in derivation_names
    )
    for forbidden in (
        "sorted(",
        "shortest",
        "preferred",
        "best_path",
        "canonical_winner",
        "lru_cache",
        "reverse_index",
        "to_json",
        "serialize",
    ):
        assert forbidden not in derivation_source
    assert "Node[Any]" not in source
    assert "Edge[Any]" not in source
    assert "dict[str, object]" not in source
    assert "pietto._project.module_package_neutral_identity" in source
    assert "pietto._project.module_attribution" in source
    assert "pietto._project.module_semantic_fact_preservation" in source
    assert "pietto._project.module_bindings" not in source
    assert "pietto._project.module_exports" not in source
    assert "pietto._project.module_resolution" not in source
    assert "pietto._project.module_relation_resolution" not in source
    assert "pietto._project.row_lineage" not in source
    assert "pietto._project_explain" not in source
    assert project_package.__all__ == ()
    assert not hasattr(pietto, "PackageGraphProvenancePath")
    assert not hasattr(project_package, "PackageGraphProvenancePath")


def test_slice6_spec_freezes_all_path_why_not_and_lifecycle_boundaries() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "Direct links remain authority",
        "Transitive paths are pure derived results",
        "positive provenance path + exact typed terminal non-success evidence",
        "Every complete authoritative path is returned",
        "A direct shorter route does not suppress a longer route",
        "No sorting or deduplication occurs",
        "Missing positive edges",
        "PackageGraphSnapshot` gains no field",
        "Slice 7 owns package-to-module attribution",
        "Slice 9 owns general private queries",
        "Project Explain v1 and existing CLI remain zero-delta",
        "Slice 6 current",
        "Slice 7 next/unstarted",
        "Add Phase 59 direct and why-not provenance",
    ):
        assert required in normalized
