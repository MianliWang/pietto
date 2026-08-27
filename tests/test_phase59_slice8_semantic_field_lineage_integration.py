from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import test_phase54_package_neutral_identity_layering as semantic_upstream
import test_phase55_slice10_package_inspection_canonical_serialization as package_upstream

from pietto._project.package_graph import (
    PackageGraphCurrentWindowLineage,
    PackageGraphDeclarationRef,
    PackageGraphExpressionLineage,
    PackageGraphExpressionLineageKind,
    PackageGraphField,
    PackageGraphFieldRef,
    PackageGraphLetRef,
    PackageGraphOutcome,
    PackageGraphProjectionLineage,
    PackageGraphSnapshot,
    _build_package_graph,
    _derive_package_graph_provenance_paths,
    _package_graph_direct_provenance_steps,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    _build_package_inspection_fact_set,
)
from pietto._project.module_package_neutral_identity import (
    ProjectModulePackageNeutralIdentityFactSet,
)
from pietto._project.module_semantic_fact_preservation import ProjectModuleSelectFact
from pietto._project.window_semantics import WindowDependencyRole


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "src/pietto/_project/package_graph.py"
SPEC = REPO_ROOT / "docs/spec/phase59-slice8-semantic-field-lineage-integration-v1.md"


def _snapshot(tmp_path: Path, source: bytes) -> PackageGraphSnapshot:
    package_root = tmp_path / "package"
    digest = package_upstream._write_package(
        package_root,
        "root",
        assets=(("main.pietto", source),),
    )
    inspection = _build_package_inspection_fact_set(
        package_upstream._plan(package_root, "root", digest)
    )
    _, semantic = semantic_upstream._semantic_project(
        tmp_path / "semantic",
        {"main.pietto": source.decode("utf-8")},
    )
    authority = semantic.module_package_identity_facts
    assert authority is not None
    result = _build_package_graph(
        inspection,
        module_identity_facts=(authority,),
    )
    assert result.outcome is PackageGraphOutcome.SUCCESS
    assert result.snapshot is not None
    return result.snapshot


def _multi_package_snapshot(
    tmp_path: Path,
    source: bytes,
) -> tuple[
    PackageGraphSnapshot,
    PackageInspectionFactSet,
    tuple[ProjectModulePackageNeutralIdentityFactSet, ...],
]:
    package_root = tmp_path / "packages"
    dependency_digest = package_upstream._write_package(
        package_root,
        "dep",
        name="dep",
        assets=(("main.pietto", source),),
    )
    root_digest = package_upstream._write_package(
        package_root,
        "root",
        assets=(("main.pietto", source),),
        dependencies=(("example", "dep", "1.0.0", dependency_digest, "../dep"),),
    )
    inspection = _build_package_inspection_fact_set(
        package_upstream._plan(package_root, "root", root_digest)
    )
    authorities: list[ProjectModulePackageNeutralIdentityFactSet] = []
    for package_name in ("dep", "root"):
        _, semantic = semantic_upstream._semantic_project(
            tmp_path / f"semantic-{package_name}",
            {"main.pietto": source.decode("utf-8")},
        )
        authority = semantic.module_package_identity_facts
        assert authority is not None
        authorities.append(authority)
    result = _build_package_graph(
        inspection,
        module_identity_facts=tuple(authorities),
    )
    assert result.outcome is PackageGraphOutcome.SUCCESS
    assert result.snapshot is not None
    return result.snapshot, inspection, tuple(authorities)


def test_direct_field_occurrences_join_existing_semantic_authority(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(
        tmp_path,
        (
            "shape Row:\n"
            "    id: Int not null\n"
            'source rows: Row is postgres.table("rows")\n'
            "query result:\n"
            "    from rows\n"
            "    select:\n"
            "        renamed = id\n"
        ).encode(),
    )

    assert tuple(field.name for field in snapshot.fields) == (
        "id",
        "id",
        "renamed",
    )
    projection = snapshot.projection_lineage[0]
    assert type(projection) is PackageGraphProjectionLineage
    assert snapshot.field(projection.output).name == "renamed"
    assert snapshot.field(projection.upstream).name == "id"
    paths = _derive_package_graph_provenance_paths(
        snapshot,
        snapshot.packages[0].ref,
        projection.output,
    )
    assert paths
    assert isinstance(projection.output, PackageGraphFieldRef)
    authority = snapshot.semantic_authorities[0].witness
    assert (
        snapshot.source_lineage[0].witness
        is (authority.authority.attribution.source_field_origins[0])
    )
    assert projection.kind.value == "renamed"
    assert projection.witness.projection_kind is projection.kind


def test_computed_lineage_preserves_nary_order_and_repeated_input_occurrences(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(
        tmp_path,
        (
            "shape Row:\n"
            "    amount: Int not null\n"
            'source rows: Row is postgres.table("rows")\n'
            "query result:\n"
            "    from rows\n"
            "    select:\n"
            "        gross = amount * amount\n"
        ).encode(),
    )

    computed = tuple(
        item
        for item in snapshot.expression_lineage
        if item.kind is PackageGraphExpressionLineageKind.COMPUTED
    )
    assert len(computed) == 2
    assert tuple(item.input_position for item in computed) == (0, 1)
    assert computed[0].output == computed[1].output
    assert computed[0].upstream == computed[1].upstream
    assert computed[0].witness is not computed[1].witness
    direct = _package_graph_direct_provenance_steps(snapshot)
    assert sum(step.witness is item for step in direct for item in computed) == 2

    paths = _derive_package_graph_provenance_paths(
        snapshot,
        snapshot.packages[0].ref,
        computed[0].upstream,
    )
    via_computation = tuple(
        path
        for path in paths
        if any(
            type(step.witness) is PackageGraphExpressionLineage for step in path.steps
        )
    )
    assert len(via_computation) == 2


def test_let_lineage_retains_binding_and_reference_occurrence_ledgers(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(
        tmp_path,
        (
            "shape Row:\n"
            "    id: Int not null\n"
            "    amount: Int not null\n"
            'source rows: Row is postgres.table("rows")\n'
            "query result:\n"
            "    from rows\n"
            "    let:\n"
            "        gross = amount + id\n"
            "    select:\n"
            "        gross\n"
        ).encode(),
    )

    assert len(snapshot.let_bindings) == 1
    binding = snapshot.let_bindings[0]
    assert binding.witness.binding.name == "gross"
    let_inputs = tuple(
        item
        for item in snapshot.expression_lineage
        if item.kind is PackageGraphExpressionLineageKind.LET_EXPRESSION
    )
    let_output = tuple(
        item
        for item in snapshot.expression_lineage
        if item.kind is PackageGraphExpressionLineageKind.LET_OUTPUT
    )
    assert tuple(item.input_position for item in let_inputs) == (0, 1)
    assert all(item.output == binding.ref for item in let_inputs)
    assert len(let_output) == 1
    assert let_output[0].upstream == binding.ref
    assert isinstance(let_output[0].upstream, PackageGraphLetRef)


def test_aggregate_lineage_retains_ordered_inputs_and_exact_aggregate_evidence(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(
        tmp_path,
        (
            "shape Row:\n"
            "    amount: Int not null\n"
            'source rows: Row is postgres.table("rows")\n'
            "query result:\n"
            "    from rows\n"
            "    select:\n"
            "        total = sum(amount + amount)\n"
        ).encode(),
    )

    aggregate = tuple(
        item
        for item in snapshot.expression_lineage
        if item.kind is PackageGraphExpressionLineageKind.AGGREGATE
    )
    assert len(aggregate) == 2
    assert tuple(item.input_position for item in aggregate) == (0, 1)
    assert aggregate[0].upstream == aggregate[1].upstream
    assert aggregate[0].aggregate_evidence is aggregate[1].aggregate_evidence
    assert type(aggregate[0].owner_witness) is ProjectModuleSelectFact
    assert aggregate[0].owner_witness.aggregate_result_fact is (
        aggregate[0].aggregate_evidence
    )


def test_current_window_lineage_retains_roles_order_multiplicity_without_frames(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(
        tmp_path,
        (
            "shape Row:\n"
            "    id: Int not null\n"
            "    amount: Int not null\n"
            "    category: Text nullable\n"
            'source rows: Row is postgres.table("rows")\n'
            "query result:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "        previous = lag(amount, 2, amount) window:\n"
            "            partition by:\n"
            "                category\n"
            "            order by:\n"
            "                id desc\n"
        ).encode(),
    )

    window = snapshot.current_window_lineage
    assert len(window) == 4
    assert tuple(item.role for item in window) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_DEFAULT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.global_position for item in window) == (0, 1, 2, 3)
    assert tuple(item.role_position for item in window) == (0, 0, 0, 0)
    assert window[0].upstream == window[1].upstream
    assert window[0].witness is not window[1].witness
    assert all(type(item) is PackageGraphCurrentWindowLineage for item in window)
    assert not any(
        "frame" in item.name
        for carrier in (
            PackageGraphCurrentWindowLineage,
            PackageGraphSnapshot,
            PackageGraphField,
        )
        for item in fields(carrier)
    )


def test_non_concrete_states_retain_exact_typed_evidence_without_partial_edges(
    tmp_path: Path,
) -> None:
    duplicate = _snapshot(
        tmp_path / "duplicate",
        (
            "shape Row:\n"
            "    id: Int not null\n"
            "    amount: Int not null\n"
            'source rows: Row is postgres.table("rows")\n'
            "query result:\n"
            "    from rows\n"
            "    select:\n"
            "        value = id\n"
            "        value = amount\n"
        ).encode(),
    )
    state = duplicate.relation_lineage_states[0]
    assert state.status.value == "unknown"
    assert state.reason.value == "duplicate_output_name"
    assert state.witness.state.status is state.status
    assert not any(
        item.output.declaration == state.declaration
        for item in duplicate.expression_lineage
    )
    assert any(
        item.status.value == "absent" and item.reason.value == "no_let_clause"
        for item in duplicate.let_lineage_states
    )

    unsupported = _snapshot(
        tmp_path / "unsupported",
        (
            "shape Row:\n"
            "    id: Int not null\n"
            'source rows: Row is postgres.table("rows")\n'
            "query result:\n"
            "    from rows\n"
            "    select:\n"
            "        mystery = mystery_window() window:\n"
            "            order by:\n"
            "                id\n"
        ).encode(),
    )
    window_state = unsupported.current_window_lineage_states[0]
    assert window_state.status.value == "unknown"
    assert window_state.reason == "unsupported window function identity"
    assert window_state.witness.reason == window_state.reason
    assert unsupported.current_window_lineage == ()


def test_equal_fields_across_packages_stay_distinct_and_dependencies_add_no_lineage(
    tmp_path: Path,
) -> None:
    source = (
        "shape Row:\n"
        "    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
    ).encode()
    snapshot, inspection, authorities = _multi_package_snapshot(tmp_path, source)

    outputs = tuple(field for field in snapshot.fields if field.name == "id")
    assert {field.ref.declaration.module.package.position for field in outputs} == {
        0,
        1,
    }
    assert all(
        item.output.declaration.module.package
        == item.upstream.declaration.module.package
        for item in (
            *snapshot.source_lineage,
            *snapshot.projection_lineage,
            *snapshot.expression_lineage,
        )
    )

    rebuilt = _build_package_graph(
        inspection,
        module_identity_facts=authorities,
    )
    assert rebuilt.outcome is PackageGraphOutcome.SUCCESS
    assert rebuilt.snapshot is not None
    assert rebuilt.snapshot.scope is not snapshot.scope
    assert tuple(
        (
            field.ref.declaration.module.package.position,
            field.ref.declaration.module.position,
            field.ref.declaration.position,
            field.ref.position,
            field.name,
        )
        for field in rebuilt.snapshot.fields
    ) == tuple(
        (
            field.ref.declaration.module.package.position,
            field.ref.declaration.module.position,
            field.ref.declaration.position,
            field.ref.position,
            field.name,
        )
        for field in snapshot.fields
    )


def test_foreign_wrong_domain_and_impossible_semantic_joins_fail_closed(
    tmp_path: Path,
) -> None:
    source = (
        "shape Row:\n"
        "    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
    ).encode()
    first = _snapshot(tmp_path / "first", source)
    second = _snapshot(tmp_path / "second", source)
    with pytest.raises(ValueError, match="foreign snapshot"):
        first.field(second.fields[0].ref)
    with pytest.raises(TypeError, match="exact field ref"):
        first.field(cast(PackageGraphFieldRef, first.packages[0].ref))
    with pytest.raises(ValueError, match="one snapshot scope"):
        replace(first.source_lineage[0], upstream=second.fields[0].ref)
    with pytest.raises(TypeError, match="declaration ref"):
        PackageGraphFieldRef(
            first.scope,
            cast(PackageGraphDeclarationRef, first.packages[0].ref),
            0,
        )

    package_root = tmp_path / "impossible-package"
    digest = package_upstream._write_package(
        package_root,
        "root",
        assets=(("main.pietto", source),),
    )
    inspection = _build_package_inspection_fact_set(
        package_upstream._plan(package_root, "root", digest)
    )
    _, foreign_semantic = semantic_upstream._semantic_project(
        tmp_path / "foreign-semantic",
        {
            "main.pietto": source.decode()
            .replace("    id: Int not null\n", "    other: Int not null\n", 1)
            .replace("        id\n", "        other\n", 1)
        },
    )
    foreign_authority = foreign_semantic.module_package_identity_facts
    assert foreign_authority is not None
    failed = _build_package_graph(
        inspection,
        module_identity_facts=(foreign_authority,),
    )
    assert failed.outcome is PackageGraphOutcome.ERROR
    assert failed.snapshot is None
    assert "exact package module bytes and order" in failed.errors[0].message


def test_snapshot_rejects_lossy_projection_relabeling_and_equal_window_grafts(
    tmp_path: Path,
) -> None:
    computed = _snapshot(
        tmp_path / "computed",
        (
            "shape Row:\n"
            "    amount: Int not null\n"
            'source rows: Row is postgres.table("rows")\n'
            "query result:\n"
            "    from rows\n"
            "    select:\n"
            "        gross = amount + amount\n"
        ).encode(),
    )
    with pytest.raises(ValueError, match="complete exact semantic projection"):
        replace(computed, expression_lineage=())
    with pytest.raises(ValueError, match="kind must retain exact evidence"):
        replace(
            computed.expression_lineage[0],
            kind=PackageGraphExpressionLineageKind.LET_OUTPUT,
        )

    window = _snapshot(
        tmp_path / "window",
        (
            "shape Row:\n"
            "    id: Int not null\n"
            'source rows: Row is postgres.table("rows")\n'
            "query result:\n"
            "    from rows\n"
            "    select:\n"
            "        position = rank() window:\n"
            "            order by:\n"
            "                id\n"
        ).encode(),
    )
    with pytest.raises(ValueError, match="exact input order"):
        replace(
            window.current_window_lineage[0],
            witness=replace(window.current_window_lineage[0].witness),
        )


def test_slice8_surface_is_private_typed_on_demand_and_has_no_later_behavior() -> None:
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
            "reverse_indexes",
            "transitive_closure",
            "canonical_bytes",
            "serialized_graph",
            "window_frames",
        }
        & snapshot_fields
    )
    for forbidden in (
        "Node[Any]",
        "Edge[Any]",
        "shortest_path",
        "preferred_path",
        "best_path",
        "lru_cache",
        "to_json",
        "serialize_graph",
        "frame_identity",
        "frame_lowering",
        "pietto._project_explain",
    ):
        assert forbidden not in source
    assert tuple(field.name for field in fields(PackageGraphExpressionLineage)) == (
        "kind",
        "output",
        "upstream",
        "role",
        "container_position",
        "input_position",
        "owner_witness",
        "witness",
        "aggregate_evidence",
    )
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "snapshot-scoped",
        "package/module/declaration-qualified",
        "source",
        "direct",
        "renamed",
        "computed",
        "let",
        "aggregate",
        "current-window",
        "Phase 60",
        "Project Explain v1",
        "Slice 8 current",
        "Slice 9 next/unstarted",
        "Add Phase 59 semantic field lineage",
    ):
        assert required in normalized
