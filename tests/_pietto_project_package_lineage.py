from __future__ import annotations

from pathlib import Path


import _pietto_semantic_identity as semantic_upstream
import _pietto_project_package as package_upstream

from pietto._project.package_graph import (
    PackageGraphOutcome,
    PackageGraphSnapshot,
    _build_package_graph,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    _build_package_inspection_fact_set,
)
from pietto._project.module_package_neutral_identity import (
    ProjectModulePackageNeutralIdentityFactSet,
)


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
