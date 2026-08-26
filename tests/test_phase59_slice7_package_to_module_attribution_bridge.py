from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import pietto
import pietto._project as project_package
import test_phase55_slice10_package_inspection_canonical_serialization as package_upstream
from pietto._project.package_graph import (
    PackageGraphDeclaration,
    PackageGraphDeclarationRef,
    PackageGraphModule,
    PackageGraphModuleRef,
    PackageGraphOutcome,
    PackageGraphPackageRef,
    PackageGraphSnapshot,
    _build_package_graph,
    _derive_package_graph_provenance_paths,
    _package_graph_direct_provenance_steps,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    _build_package_inspection_fact_set,
)
from pietto._project.package_loader import (
    LoadedRootPackage,
    PackageParsedModule,
    _PackageModuleContent,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "src/pietto/_project/package_graph.py"
SPEC = REPO_ROOT / "docs/spec/phase59-slice7-package-to-module-attribution-bridge-v1.md"


def _facts(project: Path, digest: str) -> PackageInspectionFactSet:
    return _build_package_inspection_fact_set(
        package_upstream._plan(project, "root", digest)
    )


def _snapshot(facts: PackageInspectionFactSet) -> PackageGraphSnapshot:
    result = _build_package_graph(facts)
    assert result.outcome is PackageGraphOutcome.SUCCESS
    assert result.snapshot is not None
    return result.snapshot


def test_one_package_module_and_declaration_retain_exact_authority(
    tmp_path: Path,
) -> None:
    digest = package_upstream._write_package(tmp_path, "root")
    facts = _facts(tmp_path, digest)
    snapshot = _snapshot(facts)
    loaded = facts.inspection.packages[0].entry.package

    assert type(loaded) is LoadedRootPackage
    assert len(snapshot.modules) == len(snapshot.declarations) == 1
    module = snapshot.modules[0]
    declaration = snapshot.declarations[0]
    assert module.package == snapshot.packages[0].ref
    assert module.package_authority is loaded
    assert module.witness is loaded.modules[0]
    assert type(module.witness) is PackageParsedModule
    assert declaration.module == module.ref
    assert declaration.witness is module.witness.script.definitions[0]
    assert snapshot.module(module.ref) is module
    assert snapshot.declaration(declaration.ref) is declaration


def test_module_and_declaration_order_follow_loaded_source_authority(
    tmp_path: Path,
) -> None:
    digest = package_upstream._write_package(
        tmp_path,
        "root",
        assets=(
            ("z.pietto", b"shape First:\n    id: Int\n"),
            (
                "a.pietto",
                b"shape Second:\n    id: Int\n\nshape Third:\n    id: Int\n",
            ),
        ),
    )
    snapshot = _snapshot(_facts(tmp_path, digest))

    assert tuple(module.ref.position for module in snapshot.modules) == (0, 1)
    assert tuple(module.witness.identity.path for module in snapshot.modules) == (
        "z.pietto",
        "a.pietto",
    )
    assert tuple(
        (declaration.ref.module.position, declaration.ref.position)
        for declaration in snapshot.declarations
    ) == ((0, 0), (1, 0), (1, 1))
    assert tuple(declaration.witness.name for declaration in snapshot.declarations) == (
        "First",
        "Second",
        "Third",
    )


def test_equal_module_paths_names_and_source_bytes_never_merge_packages(
    tmp_path: Path,
) -> None:
    source = b"shape Shared:\n    id: Int\n"
    dep_digest = package_upstream._write_package(
        tmp_path,
        "dep",
        name="dep",
        assets=(("main.pietto", source),),
    )
    root_digest = package_upstream._write_package(
        tmp_path,
        "root",
        assets=(("main.pietto", source),),
        dependencies=(("example", "dep", "1.0.0", dep_digest, "../dep"),),
    )
    facts = _facts(tmp_path, root_digest)
    snapshot = _snapshot(facts)

    assert len(snapshot.packages) == len(snapshot.modules) == 2
    dependency_module, root_module = snapshot.modules
    assert type(dependency_module.witness) is _PackageModuleContent
    assert type(root_module.witness) is PackageParsedModule
    assert dependency_module.witness.identity == root_module.witness.identity
    assert dependency_module.witness.source.content == source
    assert root_module.witness.source.content == source
    assert dependency_module.ref != root_module.ref
    assert dependency_module.ref.package.position == 0
    assert root_module.ref.package.position == 1
    assert dependency_module.package_authority is (
        facts.inspection.packages[0].entry.package
    )
    assert root_module.package_authority is facts.inspection.packages[1].entry.package

    dependency_declaration, root_declaration = snapshot.declarations
    assert (
        dependency_declaration.witness.name
        == root_declaration.witness.name
        == ("Shared")
    )
    assert dependency_declaration.ref != root_declaration.ref
    assert dependency_declaration.ref.module.package.position == 0
    assert root_declaration.ref.module.package.position == 1


def test_package_dependency_does_not_create_module_visibility_or_slice6_steps(
    tmp_path: Path,
) -> None:
    dep_digest = package_upstream._write_package(tmp_path, "dep", name="dep")
    root_digest = package_upstream._write_package(
        tmp_path,
        "root",
        dependencies=(("example", "dep", "1.0.0", dep_digest, "../dep"),),
    )
    snapshot = _snapshot(_facts(tmp_path, root_digest))
    direct_witnesses = tuple(
        step.witness for step in _package_graph_direct_provenance_steps(snapshot)
    )

    assert not any(
        type(witness) in {PackageGraphModule, PackageGraphDeclaration}
        for witness in direct_witnesses
    )
    with pytest.raises(TypeError, match="supported graph ref"):
        _derive_package_graph_provenance_paths(
            snapshot,
            snapshot.packages[-1].ref,
            cast(PackageGraphPackageRef, snapshot.modules[0].ref),
        )
    assert snapshot.modules[0].package == snapshot.packages[0].ref
    assert snapshot.modules[1].package == snapshot.packages[1].ref


def test_foreign_wrong_domain_and_grafted_package_ownership_fail_closed(
    tmp_path: Path,
) -> None:
    dep_digest = package_upstream._write_package(tmp_path, "dep", name="dep")
    root_digest = package_upstream._write_package(
        tmp_path,
        "root",
        dependencies=(("example", "dep", "1.0.0", dep_digest, "../dep"),),
    )
    facts = _facts(tmp_path, root_digest)
    first = _snapshot(facts)
    second = _snapshot(facts)

    with pytest.raises(ValueError, match="foreign snapshot"):
        first.module(second.modules[0].ref)
    with pytest.raises(ValueError, match="foreign snapshot"):
        first.declaration(second.declarations[0].ref)
    with pytest.raises(TypeError, match="module ref"):
        first.module(cast(PackageGraphModuleRef, first.packages[0].ref))
    with pytest.raises(TypeError, match="declaration ref"):
        first.declaration(cast(PackageGraphDeclarationRef, first.modules[0].ref))

    grafted = replace(
        first.modules[1],
        package=first.packages[1].ref,
        ref=PackageGraphModuleRef(first.scope, first.packages[1].ref, 0),
        package_authority=first.modules[0].package_authority,
        witness=first.modules[0].witness,
    )
    with pytest.raises(ValueError, match="foreign package authority"):
        replace(first, modules=(first.modules[0], grafted))


def test_inconsistent_successful_module_order_fails_without_partial_snapshot(
    tmp_path: Path,
) -> None:
    digest = package_upstream._write_package(tmp_path, "root")
    facts = _facts(tmp_path, digest)
    module = facts.inspection.packages[0].entry.package.modules[0]
    object.__setattr__(module, "position", 1)

    result = _build_package_graph(facts)

    assert result.outcome is PackageGraphOutcome.ERROR
    assert result.snapshot is None
    assert "module order" in result.errors[0].message


def test_reconstruction_preserves_local_coordinates_with_fresh_scope(
    tmp_path: Path,
) -> None:
    digest = package_upstream._write_package(
        tmp_path,
        "root",
        assets=(
            ("one.pietto", b"shape One:\n    id: Int\n"),
            ("two.pietto", b"shape Two:\n    id: Int\n"),
        ),
    )
    facts = _facts(tmp_path, digest)
    first = _snapshot(facts)
    second = _snapshot(facts)

    assert first.scope is not second.scope
    assert tuple(
        (module.ref.package.position, module.ref.position, module.witness.identity.path)
        for module in first.modules
    ) == tuple(
        (module.ref.package.position, module.ref.position, module.witness.identity.path)
        for module in second.modules
    )
    assert tuple(
        (
            declaration.ref.module.package.position,
            declaration.ref.module.position,
            declaration.ref.position,
            declaration.witness.name,
        )
        for declaration in first.declarations
    ) == tuple(
        (
            declaration.ref.module.package.position,
            declaration.ref.module.position,
            declaration.ref.position,
            declaration.witness.name,
        )
        for declaration in second.declarations
    )
    assert all(
        left.ref != right.ref and left.witness is right.witness
        for left, right in zip(first.modules, second.modules, strict=True)
    )


def test_bridge_is_private_and_contains_no_visibility_lineage_or_later_behavior() -> (
    None
):
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "pietto._project.package_loader" in imported_modules
    assert "pietto.ast_nodes" in imported_modules
    assert (
        not {
            "pietto._project.module_attribution",
            "pietto._project.module_bindings",
            "pietto._project.module_catalog",
            "pietto._project.module_exports",
            "pietto._project.module_resolution",
            "pietto._project.module_relation_resolution",
            "pietto._project.module_semantic_fact_preservation",
            "pietto._project.row_lineage",
            "pietto._project_explain",
        }
        & imported_modules
    )
    snapshot_fields = tuple(field.name for field in fields(PackageGraphSnapshot))
    assert snapshot_fields[-2:] == ("modules", "declarations")
    assert not any("field" in name or "lineage" in name for name in snapshot_fields)
    assert tuple(field.name for field in fields(PackageGraphModuleRef)) == (
        "scope",
        "package",
        "position",
    )
    assert tuple(field.name for field in fields(PackageGraphDeclarationRef)) == (
        "scope",
        "module",
        "position",
    )
    assert tuple(field.name for field in fields(PackageGraphModule)) == (
        "ref",
        "package",
        "package_authority",
        "witness",
    )
    assert tuple(field.name for field in fields(PackageGraphDeclaration)) == (
        "ref",
        "module",
        "witness",
    )
    assert project_package.__all__ == ()
    assert not hasattr(pietto, "PackageGraphModuleRef")
    assert not hasattr(project_package, "PackageGraphModuleRef")


def test_slice7_spec_freezes_package_qualification_islands_and_lifecycle() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "ownership and occurrence attribution only",
        "PackageGraphModuleRef",
        "PackageGraphDeclarationRef",
        "same `main.pietto` module",
        "does not expose, import, re-export, resolve, or bind",
        "Slice 6 direct-step union",
        "do not traverse module/declaration occurrences",
        "Project Explain v1 and existing CLI remain zero-delta",
        "Slice 7 current",
        "Slice 8 next/unstarted",
        "Add Phase 59 package-to-module attribution",
    ):
        assert required in normalized
