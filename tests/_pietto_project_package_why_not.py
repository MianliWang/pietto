from __future__ import annotations

from pathlib import Path
from typing import cast


import _pietto_project_package as package_upstream
import _pietto_project_package_graph as model_upstream
from pietto._project.package_graph import (
    PackageGraphDependency,
    PackageGraphOutcome,
    PackageGraphProvenancePath,
    PackageGraphScope,
    PackageGraphSnapshot,
    _build_package_graph,
    _derive_package_graph_why_not,  # noqa: F401
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    _build_package_inspection_fact_set,
)


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
