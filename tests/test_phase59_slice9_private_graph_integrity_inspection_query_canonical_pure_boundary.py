from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import pietto
import pietto._project as project_package
import test_phase59_slice2_private_package_graph_model_snapshot_identity as model_upstream
import test_phase59_slice5_capability_catalog_typed_negative_evidence_provenance as slice5
import test_phase59_slice6_direct_transitive_why_not_provenance as slice6
import test_phase59_slice8_semantic_field_lineage_integration as slice8

from pietto._project.package_graph import (
    PackageGraphDependency,
    PackageGraphPackageRef,
    PackageGraphSelectorRef,
    PackageGraphSnapshot,
)
from pietto._project.package_graph_inspection import (
    PackageGraphInspectionDomain,
    PackageGraphInspectionLinkKind,
    PackageGraphInspectionRecordKind,
    PackageGraphInspectionRef,
    PackageGraphInspectionStateKind,
    PackageGraphPureStatus,
    PackageGraphQueryDirection,
    _encode_inspection,
    _evaluate_package_graph_inspection,
    _inspection_ref,
    _inspect_package_graph,
    _query_package_graph_direct_downstream,
    _query_package_graph_direct_upstream,
    _query_package_graph_paths,
    _query_package_graph_why,
    _query_package_graph_why_not,
    _validate_package_graph_integrity,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "src/pietto/_project/package_graph_inspection.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase59-slice9-private-graph-integrity-inspection-query-canonical-pure-boundary-v1.md"
)


def _source(expression: str = "id") -> bytes:
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    amount: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    select:\n"
        f"        value = {expression}\n"
    ).encode()


def _forge_snapshot(
    snapshot: PackageGraphSnapshot,
    **changes: object,
) -> PackageGraphSnapshot:
    forged = object.__new__(PackageGraphSnapshot)
    for item in fields(PackageGraphSnapshot):
        object.__setattr__(
            forged,
            item.name,
            changes.get(item.name, getattr(snapshot, item.name)),
        )
    return forged


def _value(record: object, name: str) -> object:
    record_fields = getattr(record, "fields")
    matches = tuple(item.value for item in record_fields if item.name == name)
    assert len(matches) == 1
    return matches[0]


def test_equivalent_runtime_scopes_have_identical_private_canonical_data(
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
    first = slice8._snapshot(tmp_path / "first", source)
    second = slice8._snapshot(tmp_path / "second", source)

    assert first.scope is not second.scope
    assert first.packages[0].ref != second.packages[0].ref
    first_inspection = _inspect_package_graph(first)
    second_inspection = _inspect_package_graph(second)
    assert first_inspection == second_inspection
    assert first_inspection.canonical_bytes == second_inspection.canonical_bytes
    assert (
        _evaluate_package_graph_inspection(first_inspection).status
        is PackageGraphPureStatus.OK
    )


def test_integrity_rejects_dangling_foreign_wrong_domain_and_cross_package_grafts(
    tmp_path: Path,
) -> None:
    snapshot, _inspection, _authorities = slice8._multi_package_snapshot(
        tmp_path / "multi",
        _source(),
    )
    dependency = snapshot.dependencies[0]
    dangling = replace(
        dependency,
        resolved_package=PackageGraphPackageRef(snapshot.scope, 99),
    )
    with pytest.raises(ValueError, match="does not resolve"):
        _validate_package_graph_integrity(
            _forge_snapshot(snapshot, dependencies=(dangling,))
        )

    foreign = slice8._snapshot(tmp_path / "foreign", _source())
    foreign_dependency = object.__new__(PackageGraphDependency)
    for item in fields(PackageGraphDependency):
        object.__setattr__(
            foreign_dependency,
            item.name,
            (
                foreign.packages[0].ref
                if item.name == "resolved_package"
                else getattr(dependency, item.name)
            ),
        )
    with pytest.raises(ValueError, match="foreign snapshot"):
        _validate_package_graph_integrity(
            _forge_snapshot(snapshot, dependencies=(foreign_dependency,))
        )

    wrong_domain = object.__new__(PackageGraphDependency)
    for item in fields(PackageGraphDependency):
        object.__setattr__(
            wrong_domain,
            item.name,
            (
                cast(PackageGraphPackageRef, snapshot.modules[0].ref)
                if item.name == "resolved_package"
                else getattr(dependency, item.name)
            ),
        )
    with pytest.raises(TypeError, match="package ref"):
        _validate_package_graph_integrity(
            _forge_snapshot(snapshot, dependencies=(wrong_domain,))
        )

    first_lineage = snapshot.source_lineage[0]
    foreign_upstream = next(
        item.upstream
        for item in snapshot.source_lineage
        if item.upstream.declaration.module.package
        != first_lineage.output.declaration.module.package
    )
    grafted_lineage = replace(first_lineage, upstream=foreign_upstream)
    with pytest.raises(ValueError, match="complete exact semantic projection"):
        _validate_package_graph_integrity(
            _forge_snapshot(
                snapshot,
                source_lineage=(grafted_lineage, *snapshot.source_lineage[1:]),
            )
        )


def test_integrity_rejects_wrong_selector_and_nonexistent_lineage_input(
    tmp_path: Path,
) -> None:
    _package, _capabilities, _catalogs, snapshot = slice5._extension_authority(tmp_path)
    evaluation = snapshot.capability_evaluations[0]
    wrong_selector = PackageGraphSelectorRef(
        snapshot.scope,
        evaluation.ref.requirement.package,
        99,
    )
    forged_evaluation = replace(evaluation, selector=wrong_selector)
    with pytest.raises(ValueError, match="exact selector attribution"):
        _validate_package_graph_integrity(
            _forge_snapshot(
                snapshot,
                capability_evaluations=(
                    forged_evaluation,
                    *snapshot.capability_evaluations[1:],
                ),
            )
        )

    semantic = slice8._snapshot(tmp_path / "semantic", _source("id + amount"))
    lineage = semantic.expression_lineage[0]
    missing = replace(
        lineage.upstream,
        position=99,
    )
    forged_lineage = replace(lineage, upstream=missing)
    with pytest.raises(ValueError, match="complete exact semantic projection"):
        _validate_package_graph_integrity(
            _forge_snapshot(
                semantic,
                expression_lineage=(
                    forged_lineage,
                    *semantic.expression_lineage[1:],
                ),
            )
        )


def test_malformed_why_not_attachment_fails_and_parallel_occurrences_remain_valid(
    tmp_path: Path,
) -> None:
    _package, _capabilities, _catalogs, snapshot = slice5._extension_authority(
        tmp_path / "why"
    )
    start = snapshot.packages[0].ref
    why_not = next(
        result
        for evidence in snapshot.catalog_evidence
        if (
            result := slice6._derive_package_graph_why_not(
                snapshot, start, evidence.ref
            )
        )
    )
    foreign_terminal = next(
        evaluation.evidence
        for evaluation in snapshot.capability_evaluations
        if evaluation.evidence is not why_not[0].terminal_evidence
    )
    with pytest.raises(ValueError, match="terminate its exact path"):
        replace(why_not[0], terminal_evidence=foreign_terminal)

    repeated = slice8._snapshot(
        tmp_path / "parallel",
        _source("amount + amount"),
    )
    _validate_package_graph_integrity(repeated)
    inspection = _inspect_package_graph(repeated)
    repeated_links = tuple(
        link
        for link in inspection.links
        if link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
    )
    assert len(repeated_links) == 2
    assert repeated_links[0].source == repeated_links[1].source
    assert repeated_links[0].target == repeated_links[1].target
    assert repeated_links[0].ordinal != repeated_links[1].ordinal


def test_canonical_data_excludes_runtime_scope_and_preserves_order_multiplicity_states(
    tmp_path: Path,
) -> None:
    snapshot = slice8._snapshot(tmp_path / "ordered", _source("amount + amount"))
    inspection = _inspect_package_graph(snapshot)
    scope_text = repr(snapshot.scope).encode()
    assert scope_text not in inspection.canonical_bytes
    assert str(id(snapshot.scope)).encode() not in inspection.canonical_bytes
    assert b"PackageGraphScope" not in inspection.canonical_bytes
    assert b"0x" not in inspection.canonical_bytes

    repeated = tuple(
        link
        for link in inspection.links
        if link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
    )
    assert len(repeated) == 2
    reversed_links = tuple(
        replace(link, ordinal=position)
        for position, link in enumerate(reversed(inspection.links))
    )
    provisional = replace(inspection, links=reversed_links, canonical_bytes=b"")
    reversed_inspection = replace(
        provisional,
        canonical_bytes=_encode_inspection(provisional),
    )
    assert (
        _evaluate_package_graph_inspection(reversed_inspection).status
        is PackageGraphPureStatus.OK
    )
    assert reversed_inspection.canonical_bytes != inspection.canonical_bytes

    non_concrete = slice8._snapshot(
        tmp_path / "states",
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
    state_inspection = _inspect_package_graph(non_concrete)
    assert any(
        state.kind is PackageGraphInspectionStateKind.RELATION_LINEAGE
        and state.status == "unknown"
        and state.reason == "duplicate_output_name"
        for state in state_inspection.states
    )
    assert any(
        state.kind is PackageGraphInspectionStateKind.LET_LINEAGE
        and state.status == "absent"
        and state.reason == "no_let_clause"
        for state in state_inspection.states
    )


def test_expandable_fact_changes_canonical_data_without_changing_occurrence_identity() -> (
    None
):
    scope = model_upstream.PackageGraphScope()
    first_package = model_upstream._package(scope, 0, digest="a" * 64)
    first = PackageGraphSnapshot(scope, (first_package,), ())
    changed_package = replace(first_package, content_digest="b" * 64)
    changed = PackageGraphSnapshot(scope, (changed_package,), ())

    assert first_package.ref == changed_package.ref
    first_inspection = _inspect_package_graph(first)
    changed_inspection = _inspect_package_graph(changed)
    assert first_inspection.records[0].ref == changed_inspection.records[0].ref
    assert first_inspection.canonical_bytes != changed_inspection.canonical_bytes


def test_pure_evaluator_rejects_malformed_ref_domain_dangling_and_bytes(
    tmp_path: Path,
) -> None:
    snapshot = slice8._snapshot(tmp_path, _source("id + amount"))
    inspection = _inspect_package_graph(snapshot)
    expression_position = next(
        position
        for position, link in enumerate(inspection.links)
        if link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
    )
    expression = inspection.links[expression_position]

    wrong_domain = replace(expression, target=inspection.records[0].ref)
    wrong_links = (
        *inspection.links[:expression_position],
        wrong_domain,
        *inspection.links[expression_position + 1 :],
    )
    assert (
        _evaluate_package_graph_inspection(
            replace(inspection, links=wrong_links)
        ).status
        is PackageGraphPureStatus.WRONG_DOMAIN
    )

    dangling = replace(
        expression,
        target=PackageGraphInspectionRef(
            PackageGraphInspectionDomain.FIELD,
            (0, 0, 0, 999),
        ),
    )
    dangling_links = (
        *inspection.links[:expression_position],
        dangling,
        *inspection.links[expression_position + 1 :],
    )
    assert (
        _evaluate_package_graph_inspection(
            replace(inspection, links=dangling_links)
        ).status
        is PackageGraphPureStatus.DANGLING_REF
    )

    malformed_record = replace(
        inspection.records[0],
        ref=PackageGraphInspectionRef(PackageGraphInspectionDomain.PACKAGE, ()),
    )
    assert (
        _evaluate_package_graph_inspection(
            replace(inspection, records=(malformed_record, *inspection.records[1:]))
        ).status
        is PackageGraphPureStatus.MALFORMED_REF
    )
    assert (
        _evaluate_package_graph_inspection(
            replace(inspection, canonical_bytes=b"forged")
        ).status
        is PackageGraphPureStatus.CANONICAL_MISMATCH
    )


def test_direct_and_derived_queries_preserve_every_parallel_route_both_directions(
    tmp_path: Path,
) -> None:
    snapshot = slice8._snapshot(tmp_path, _source("amount + amount"))
    inspection = _inspect_package_graph(snapshot)
    expression_links = tuple(
        link
        for link in inspection.links
        if link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
    )
    assert len(expression_links) == 2
    output = expression_links[0].source
    upstream = expression_links[0].target
    assert expression_links[1].source == output
    assert expression_links[1].target == upstream

    assert (
        tuple(
            link
            for link in _query_package_graph_direct_upstream(inspection, output)
            if link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
        )
        == expression_links
    )
    assert (
        tuple(
            link
            for link in _query_package_graph_direct_downstream(inspection, upstream)
            if link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
        )
        == expression_links
    )

    package = next(
        record.ref
        for record in inspection.records
        if record.kind is PackageGraphInspectionRecordKind.PACKAGE
    )
    forward = _query_package_graph_paths(inspection, package, upstream)
    computed_routes = tuple(
        path
        for path in forward
        if any(
            link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
            for link in path.links
        )
    )
    assert len(computed_routes) == 2
    assert computed_routes[0] != computed_routes[1]

    reverse = _query_package_graph_paths(
        inspection,
        upstream,
        output,
        PackageGraphQueryDirection.DOWNSTREAM,
    )
    assert len(reverse) == 2
    assert all(
        path.direction is PackageGraphQueryDirection.DOWNSTREAM for path in reverse
    )


def test_why_and_why_not_queries_retain_exact_terminal_and_all_paths(
    tmp_path: Path,
) -> None:
    _package, _capabilities, _catalogs, snapshot = slice5._extension_authority(tmp_path)
    inspection = _inspect_package_graph(snapshot)
    start = _inspection_ref(snapshot.packages[0].ref)
    terminal = next(
        evidence
        for evidence in snapshot.catalog_evidence
        if slice6._derive_package_graph_why_not(
            snapshot,
            snapshot.packages[0].ref,
            evidence.ref,
        )
    )
    end = _inspection_ref(terminal.ref)
    why = _query_package_graph_why(inspection, start, end)
    why_not = _query_package_graph_why_not(inspection, start, end)
    runtime_why_not = slice6._derive_package_graph_why_not(
        snapshot,
        snapshot.packages[0].ref,
        terminal.ref,
    )

    assert len(why) == len(why_not) == len(runtime_why_not)
    assert all(item.path in why and item.terminal.ref == end for item in why_not)
    assert all(
        item.terminal.kind is PackageGraphInspectionRecordKind.CATALOG_EVIDENCE
        for item in why_not
    )


def test_equivalent_explicit_inputs_produce_equal_inspection_and_query_results(
    tmp_path: Path,
) -> None:
    first = _inspect_package_graph(
        slice8._snapshot(tmp_path / "first", _source("id + amount"))
    )
    second = _inspect_package_graph(
        slice8._snapshot(tmp_path / "second", _source("id + amount"))
    )
    first_expression = next(
        link
        for link in first.links
        if link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
    )
    second_expression = next(
        link
        for link in second.links
        if link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
    )
    assert first_expression.source == second_expression.source
    assert first_expression.target == second_expression.target
    assert _query_package_graph_paths(
        first,
        first_expression.source,
        first_expression.target,
    ) == _query_package_graph_paths(
        second,
        second_expression.source,
        second_expression.target,
    )


def test_inspection_stores_only_direct_links_without_reverse_index_or_path_closure(
    tmp_path: Path,
) -> None:
    inspection = _inspect_package_graph(
        slice8._snapshot(tmp_path, _source("id + amount"))
    )
    assert tuple(item.name for item in fields(type(inspection))) == (
        "records",
        "links",
        "states",
        "canonical_bytes",
    )
    assert not any(
        token in item.name
        for item in fields(type(inspection))
        for token in ("reverse", "closure", "all_paths", "shortest", "winner")
    )


def test_private_boundary_has_no_ambient_io_public_or_persistence_surface() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(
        module == name or module.startswith(f"{name}.")
        for module in imported
        for name in (
            "os",
            "pathlib",
            "socket",
            "urllib",
            "http",
            "requests",
            "pickle",
            "uuid",
            "time",
        )
    )
    for forbidden in (
        "repr(",
        "id(",
        "getcwd",
        "environ",
        "open(",
        "package_loader",
        "shortest",
        "preferred",
        "best_path",
        "canonical_winner",
        "lru_cache",
        "parse_canonical",
        "from_json",
        "ProjectExplain",
        "pietto._project_explain",
    ):
        assert forbidden not in source
    assert project_package.__all__ == ()
    assert not hasattr(pietto, "PackageGraphInspection")
    assert not hasattr(project_package, "PackageGraphInspection")
    for public_path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
        REPO_ROOT / "src/pietto/cli.py",
        *(REPO_ROOT / "src/pietto/_project_explain").glob("*.py"),
    ):
        assert "package_graph_inspection" not in public_path.read_text(encoding="utf-8")


def test_slice9_package_inventory_spec_and_lifecycle_are_private_and_exact() -> None:
    smoke = (REPO_ROOT / "scripts/package_smoke.py").read_text(encoding="utf-8")
    assert 'f"{prefix}/_project/package_graph_inspection.py"' in smoke
    assert "installed private Phase 59 package graph inspection import" in smoke
    assert "import pietto._project.package_graph_inspection" in smoke

    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "comprehensive referential integrity",
        "runtime snapshot scope",
        "typed local coordinates",
        "authoritative ordering and multiplicity",
        "direct upstream",
        "direct downstream",
        "all authoritative why paths",
        "no reverse index",
        "pure evaluator",
        "no canonical parser or reconstruction",
        "Project Explain v1 and CLI remain zero-delta",
        "Slice 9 current",
        "Slice 10 next/unstarted",
        "Add Phase 59 private graph inspection",
    ):
        assert required in normalized
