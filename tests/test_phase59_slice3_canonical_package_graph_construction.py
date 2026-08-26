from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pietto
import pietto._project as project_package
import pietto._project.package_graph as package_graph
from pietto._project.model import ProjectDiscoveryErrorKind
from pietto._project.package_graph import (
    PackageGraphOutcome,
    PackageGraphResult,
    _build_package_graph,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    PackageInspectionOutcome,
    _build_package_inspection_fact_set,
)
from pietto._project.package_load_plan import PackageLoadPlanBlockerKind
import test_phase55_slice10_package_inspection_canonical_serialization as upstream


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "src/pietto/_project/package_graph.py"
SPEC = REPO_ROOT / "docs/spec/phase59-slice3-canonical-package-graph-construction-v1.md"


def _result(facts: PackageInspectionFactSet) -> PackageGraphResult:
    result = _build_package_graph(facts)
    assert type(result) is PackageGraphResult
    return result


def test_real_root_only_authority_constructs_one_complete_package_graph(
    tmp_path: Path,
) -> None:
    digest = upstream._write_package(tmp_path, "root")
    facts = _build_package_inspection_fact_set(upstream._plan(tmp_path, "root", digest))

    result = _result(facts)

    assert result.outcome is PackageGraphOutcome.SUCCESS
    assert result.snapshot is not None
    assert result.blockers == result.errors == ()
    assert result.snapshot.dependencies == ()
    assert len(result.snapshot.packages) == facts.inspection.package_count == 1
    graph_package = result.snapshot.packages[0]
    inspected = facts.inspection.packages[0]
    assert graph_package.ref.scope is result.snapshot.scope
    assert graph_package.ref.position == inspected.position == 0
    assert graph_package.coordinate is inspected.coordinate
    assert graph_package.content_digest is inspected.content_digest
    assert graph_package.role is inspected.role


def test_real_dependency_authority_preserves_package_order_target_and_witness(
    tmp_path: Path,
) -> None:
    facts = upstream._simple_inspection(tmp_path)
    result = _result(facts)
    assert result.snapshot is not None
    snapshot = result.snapshot
    inspection = facts.inspection

    assert len(snapshot.packages) == inspection.package_count == 2
    assert tuple(package.ref.position for package in snapshot.packages) == (0, 1)
    assert tuple(package.coordinate for package in snapshot.packages) == tuple(
        package.coordinate for package in inspection.packages
    )
    assert tuple(package.content_digest for package in snapshot.packages) == tuple(
        package.content_digest for package in inspection.packages
    )
    assert len(snapshot.dependencies) == 1
    link = snapshot.dependencies[0]
    inspected_dependency = inspection.packages[-1].dependencies[0]
    assert link.declaring_package == snapshot.packages[-1].ref
    assert (
        link.resolved_package.position == inspected_dependency.target_package_position
    )
    assert link.witness is inspected_dependency.edge.occurrence
    assert link.ref.declaration_position == inspected_dependency.position
    assert link.ref.scope is snapshot.scope


def test_real_upstream_package_and_dependency_order_is_never_sorted(
    tmp_path: Path,
) -> None:
    forward = upstream._two_dependency_inspection(
        tmp_path / "forward",
        reverse=False,
    )
    backward = upstream._two_dependency_inspection(
        tmp_path / "backward",
        reverse=True,
    )

    for facts in (forward, backward):
        result = _result(facts)
        assert result.snapshot is not None
        assert tuple(
            package.coordinate for package in result.snapshot.packages
        ) == tuple(package.coordinate for package in facts.inspection.packages)
        assert tuple(
            link.witness.coordinate.identity.name
            for link in result.snapshot.dependencies
        ) == tuple(
            dependency.edge.occurrence.coordinate.identity.name
            for package in facts.inspection.packages
            for dependency in package.dependencies
        )

    forward_result = _result(forward)
    backward_result = _result(backward)
    assert forward_result.snapshot is not None
    assert backward_result.snapshot is not None
    assert tuple(
        link.witness.coordinate.identity.name
        for link in forward_result.snapshot.dependencies
    ) == ("one", "two")
    assert tuple(
        link.witness.coordinate.identity.name
        for link in backward_result.snapshot.dependencies
    ) == ("two", "one")


def test_real_parallel_equal_endpoint_declarations_remain_distinct_links(
    tmp_path: Path,
) -> None:
    dependency_digest = upstream._write_package(tmp_path, "dep", name="dep")
    declaration = (
        "example",
        "dep",
        "1.0.0",
        dependency_digest,
        "../dep",
    )
    root_digest = upstream._write_package(
        tmp_path,
        "root",
        dependencies=(declaration, declaration),
    )
    facts = _build_package_inspection_fact_set(
        upstream._plan(tmp_path, "root", root_digest)
    )

    result = _result(facts)
    assert result.snapshot is not None
    links = result.snapshot.dependencies
    inspected = facts.inspection.packages[-1].dependencies

    assert len(links) == len(inspected) == 2
    assert links[0].declaring_package == links[1].declaring_package
    assert links[0].resolved_package == links[1].resolved_package
    assert links[0].ref != links[1].ref
    assert tuple(link.ref.declaration_position for link in links) == (0, 1)
    assert links[0].witness is inspected[0].edge.occurrence
    assert links[1].witness is inspected[1].edge.occurrence
    assert links[0].witness is not links[1].witness


def test_repeated_real_construction_preserves_local_facts_with_fresh_scope(
    tmp_path: Path,
) -> None:
    facts = upstream._simple_inspection(tmp_path)

    first = _result(facts)
    second = _result(facts)

    assert first.snapshot is not None and second.snapshot is not None
    assert first.snapshot.scope is not second.snapshot.scope
    assert tuple(package.ref.position for package in first.snapshot.packages) == tuple(
        package.ref.position for package in second.snapshot.packages
    )
    assert tuple(
        (package.coordinate, package.content_digest, package.role)
        for package in first.snapshot.packages
    ) == tuple(
        (package.coordinate, package.content_digest, package.role)
        for package in second.snapshot.packages
    )
    assert tuple(
        (link.ref.declaring_package.position, link.ref.declaration_position)
        for link in first.snapshot.dependencies
    ) == tuple(
        (link.ref.declaring_package.position, link.ref.declaration_position)
        for link in second.snapshot.dependencies
    )
    assert all(
        left.ref != right.ref and left.witness is right.witness
        for left, right in zip(
            first.snapshot.dependencies,
            second.snapshot.dependencies,
            strict=True,
        )
    )


def test_real_cycle_rejection_preserves_exact_blockers_without_snapshot(
    tmp_path: Path,
) -> None:
    child_digest = upstream._write_package(
        tmp_path,
        "deps/child",
        name="child",
        dependencies=(("example", "root", "1.0.0", "a" * 64, "../../root"),),
    )
    root_digest = upstream._write_package(
        tmp_path,
        "root",
        dependencies=(("example", "child", "1.0.0", child_digest, "../deps/child"),),
    )
    facts = _build_package_inspection_fact_set(
        upstream._plan(tmp_path, "root", root_digest)
    )
    assert facts.inspection.outcome is PackageInspectionOutcome.REJECTED

    result = _result(facts)

    assert result.outcome is PackageGraphOutcome.REJECTED
    assert result.snapshot is None
    assert result.blockers is facts.inspection.plan_result.blockers
    assert result.blockers[0].kind is PackageLoadPlanBlockerKind.CYCLE
    assert result.errors == ()


def test_real_dependency_path_error_preserves_exact_errors_without_snapshot(
    tmp_path: Path,
) -> None:
    root_digest = upstream._write_package(
        tmp_path,
        "root",
        dependencies=(("example", "outside", "1.0.0", "a" * 64, "../../outside"),),
    )
    facts = _build_package_inspection_fact_set(
        upstream._plan(tmp_path, "root", root_digest)
    )
    assert facts.inspection.outcome is PackageInspectionOutcome.ERROR

    result = _result(facts)

    assert result.outcome is PackageGraphOutcome.ERROR
    assert result.snapshot is None
    assert result.errors is facts.inspection.plan_result.errors
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.PROJECT_PATH
    assert result.blockers == ()


def test_inconsistent_success_authority_fails_closed_as_error(
    tmp_path: Path,
) -> None:
    facts = upstream._simple_inspection(tmp_path)
    dependency = facts.inspection.packages[-1].dependencies[0]
    object.__setattr__(dependency, "target_package_position", 99)

    result = _result(facts)

    assert result.outcome is PackageGraphOutcome.ERROR
    assert result.snapshot is None
    assert result.blockers == ()
    assert len(result.errors) == 1
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.PROJECT_RESOURCE
    assert "does not resolve" in result.errors[0].message


def test_construction_is_private_pure_and_has_no_merge_or_later_products() -> None:
    source = inspect.getsource(package_graph._build_package_graph)
    tree = ast.parse(source)
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not {"sorted", "set", "frozenset", "dict", "list"} & calls
    for forbidden in (
        "_locate_root_package",
        "_load_root_package",
        "_build_package_load_plan",
        "_build_package_inspection_fact_set",
        "open(",
        "Path(",
        "to_json",
        "sha256",
        "uuid",
        "bfs",
        "dfs",
        "shortest",
    ):
        assert forbidden not in source.lower()
    assert package_graph.__all__ == ()
    assert not hasattr(pietto, "_build_package_graph")
    assert not hasattr(project_package, "_build_package_graph")


def test_slice3_spec_freezes_exact_authority_outcomes_and_lifecycle() -> None:
    document = SPEC.read_text(encoding="utf-8")
    normalized = " ".join(document.split())

    for required in (
        "PackageInspectionFactSet -> PackageGraphResult",
        "dependency.edge.occurrence",
        "target only `target_package_position`",
        "Parallel equal-endpoint declarations remain separate",
        "Slice 3 adds no canonical bytes",
        "Slice 4 remains unimplemented and unauthorized",
        "Construct canonical Phase 59 package graph",
    ):
        assert required in normalized
    assert "Slice 3 current" in normalized
    assert "Slice 4 next/unstarted" in normalized
