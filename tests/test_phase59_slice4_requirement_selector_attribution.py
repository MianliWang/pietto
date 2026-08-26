from __future__ import annotations

import ast
from pathlib import Path
from typing import cast

import pytest

from pietto._project.package_graph import (
    PackageGraphOutcome,
    PackageGraphRequirementDeclaration,
    PackageGraphRequirementRef,
    PackageGraphSelectorRef,
    _build_package_graph,
)
from pietto._project.package_inspection import _build_package_inspection_fact_set
from pietto._project.package_manifest import (
    PackageManifestExtensionSignatureSelectorOccurrence,
)
import test_phase55_slice10_package_inspection_canonical_serialization as package_upstream
import test_phase58_slice10_package_capability_requirement_declaration as requirement_upstream
import test_phase58_slice12_package_extension_signature_selector_authority as selector_upstream


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "src/pietto/_project/package_graph.py"
SPEC = REPO_ROOT / "docs/spec/phase59-slice4-requirement-selector-attribution-v1.md"


def _graph(project: Path, package_path: str, digest: str):
    facts = _build_package_inspection_fact_set(
        package_upstream._plan(project, package_path, digest)
    )
    result = _build_package_graph(facts)
    assert result.outcome is PackageGraphOutcome.SUCCESS
    assert result.snapshot is not None
    return facts, result.snapshot


def test_undeclared_and_declared_empty_remain_distinct_without_occurrences(
    tmp_path: Path,
) -> None:
    undeclared_root = tmp_path / "undeclared"
    undeclared_digest = requirement_upstream._write_package(
        undeclared_root,
        "root",
        declaration="",
    )
    _, undeclared = _graph(undeclared_root, "root", undeclared_digest)

    empty_root = tmp_path / "empty"
    empty_digest = requirement_upstream._write_package(
        empty_root,
        "root",
        declaration=requirement_upstream._declaration(),
    )
    _, declared_empty = _graph(empty_root, "root", empty_digest)

    assert undeclared.requirements == declared_empty.requirements == ()
    assert undeclared.selectors == declared_empty.selectors == ()
    assert len(undeclared.requirement_collections) == 1
    assert len(declared_empty.requirement_collections) == 1
    undeclared_collection = undeclared.requirement_collections[0]
    declared_collection = declared_empty.requirement_collections[0]
    assert (
        undeclared_collection.declaration
        is PackageGraphRequirementDeclaration.UNDECLARED
    )
    assert undeclared_collection.binding is None
    assert undeclared_collection.selectors is None
    assert (
        declared_collection.declaration is PackageGraphRequirementDeclaration.DECLARED
    )
    assert declared_collection.binding is not None
    assert declared_collection.binding.requirements.occurrences == ()
    assert declared_collection.selectors is None


def test_declared_requirements_preserve_exact_package_local_order_and_witnesses(
    tmp_path: Path,
) -> None:
    declaration = requirement_upstream._declaration(
        requirement_upstream._entry("logical_type", subject="Int"),
        requirement_upstream._entry("logical_type", subject="Text"),
    )
    digest = requirement_upstream._write_package(
        tmp_path,
        "root",
        declaration=declaration,
    )

    _, snapshot = _graph(tmp_path, "root", digest)
    collection = snapshot.requirement_collections[0]
    assert collection.binding is not None
    occurrences = collection.binding.requirements.occurrences

    assert tuple(requirement.ref.position for requirement in snapshot.requirements) == (
        0,
        1,
    )
    assert tuple(
        requirement.witness.key.subject for requirement in snapshot.requirements
    ) == (
        "Int",
        "Text",
    )
    assert snapshot.requirements[0].witness is occurrences[0]
    assert snapshot.requirements[1].witness is occurrences[1]
    assert all(
        requirement.ref.package == snapshot.packages[0].ref
        for requirement in snapshot.requirements
    )


def test_equal_keys_in_distinct_packages_remain_distinct_authored_occurrences(
    tmp_path: Path,
) -> None:
    declaration = requirement_upstream._declaration(
        requirement_upstream._entry("logical_type", subject="Int"),
    )
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

    _, snapshot = _graph(tmp_path, "root", root_digest)

    assert len(snapshot.packages) == len(snapshot.requirement_collections) == 2
    assert len(snapshot.requirements) == 2
    first, second = snapshot.requirements
    assert first.witness.key == second.witness.key
    assert first.ref != second.ref
    assert first.ref.package.position == 0
    assert second.ref.package.position == 1
    assert tuple(
        requirement.ref.package.position for requirement in snapshot.requirements
    ) == (
        0,
        1,
    )


def test_schema3_selectors_are_distinct_and_cover_exact_requirement_occurrences(
    tmp_path: Path,
) -> None:
    manifest = selector_upstream._manifest(
        schema_version=3,
        requirements=(
            selector_upstream._requirement(operation="distance"),
            selector_upstream._requirement(operation="l2_distance"),
        ),
        selectors=(
            selector_upstream._selector(0, "native_type"),
            selector_upstream._selector(1, "native_type"),
        ),
    )
    _, digest = selector_upstream._write_package(tmp_path, "root", manifest)

    _, snapshot = _graph(tmp_path, "root", digest)
    collection = snapshot.requirement_collections[0]
    assert collection.selectors is not None
    selector_witnesses = collection.selectors.occurrences

    assert len(snapshot.requirements) == len(snapshot.selectors) == 2
    assert type(snapshot.requirements[0].ref) is PackageGraphRequirementRef
    assert type(snapshot.selectors[0].ref) is PackageGraphSelectorRef
    assert snapshot.requirements[0].ref != snapshot.selectors[0].ref
    assert tuple(selector.ref.position for selector in snapshot.selectors) == (0, 1)
    assert tuple(selector.requirement.position for selector in snapshot.selectors) == (
        0,
        1,
    )
    assert snapshot.selectors[0].witness is selector_witnesses[0]
    assert snapshot.selectors[1].witness is selector_witnesses[1]
    assert (
        snapshot.selectors[0].witness.selector == snapshot.selectors[1].witness.selector
    )
    assert snapshot.selectors[0].ref != snapshot.selectors[1].ref


def test_schema2_extension_requirement_remains_valid_and_selector_unbound(
    tmp_path: Path,
) -> None:
    manifest = selector_upstream._manifest(
        schema_version=2,
        requirements=(selector_upstream._requirement(),),
    )
    _, digest = selector_upstream._write_package(tmp_path, "root", manifest)

    _, snapshot = _graph(tmp_path, "root", digest)

    assert len(snapshot.requirements) == 1
    assert snapshot.selectors == ()
    collection = snapshot.requirement_collections[0]
    assert collection.declaration is PackageGraphRequirementDeclaration.DECLARED
    assert collection.binding is not None
    assert collection.selectors is None


def test_requirement_and_selector_lookups_reject_foreign_and_wrong_domains(
    tmp_path: Path,
) -> None:
    manifest = selector_upstream._manifest(
        requirements=(selector_upstream._requirement(),),
        selectors=(selector_upstream._selector(0, "native_type"),),
    )
    _, digest = selector_upstream._write_package(tmp_path, "root", manifest)
    _, first = _graph(tmp_path, "root", digest)
    _, second = _graph(tmp_path, "root", digest)

    requirement = first.requirements[0]
    selector = first.selectors[0]
    assert first.requirement(requirement.ref) is requirement
    assert first.selector(selector.ref) is selector
    with pytest.raises(ValueError, match="foreign snapshot"):
        first.requirement(second.requirements[0].ref)
    with pytest.raises(ValueError, match="foreign snapshot"):
        first.selector(second.selectors[0].ref)
    with pytest.raises(TypeError, match="requirement ref"):
        first.requirement(cast(PackageGraphRequirementRef, selector.ref))
    with pytest.raises(TypeError, match="selector ref"):
        first.selector(cast(PackageGraphSelectorRef, requirement.ref))


def test_impossible_selector_coverage_fails_closed_without_partial_graph(
    tmp_path: Path,
) -> None:
    manifest = selector_upstream._manifest(
        requirements=(selector_upstream._requirement(),),
        selectors=(selector_upstream._selector(0, "native_type"),),
    )
    _, digest = selector_upstream._write_package(tmp_path, "root", manifest)
    facts = _build_package_inspection_fact_set(
        package_upstream._plan(tmp_path, "root", digest)
    )
    loaded_manifest = facts.inspection.packages[
        0
    ].entry.package.catalog.root_package.manifest
    declaration = loaded_manifest.capability_requirements
    assert declaration is not None
    selector = declaration.extension_signature_selectors[0]
    assert type(selector) is PackageManifestExtensionSignatureSelectorOccurrence
    object.__setattr__(selector, "requirement_position", 1)

    result = _build_package_graph(facts)

    assert result.outcome is PackageGraphOutcome.ERROR
    assert result.snapshot is None
    assert result.errors
    assert "position" in result.errors[0].message


def test_repeated_attribution_preserves_coordinates_and_package_topology(
    tmp_path: Path,
) -> None:
    declaration = requirement_upstream._declaration(
        requirement_upstream._entry("logical_type", subject="Int"),
    )
    digest = requirement_upstream._write_package(
        tmp_path,
        "root",
        declaration=declaration,
    )
    facts = _build_package_inspection_fact_set(
        package_upstream._plan(tmp_path, "root", digest)
    )

    first = _build_package_graph(facts)
    second = _build_package_graph(facts)
    assert first.snapshot is not None and second.snapshot is not None
    assert first.snapshot.scope is not second.snapshot.scope
    assert len(first.snapshot.packages) == len(second.snapshot.packages) == 1
    assert first.snapshot.dependencies == second.snapshot.dependencies == ()
    assert tuple(
        (requirement.ref.package.position, requirement.ref.position)
        for requirement in first.snapshot.requirements
    ) == tuple(
        (requirement.ref.package.position, requirement.ref.position)
        for requirement in second.snapshot.requirements
    )
    assert first.snapshot.requirements[0].ref != second.snapshot.requirements[0].ref


def test_attribution_is_private_and_contains_no_checking_or_later_domains() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert (
        not {
            "pietto._project.capability_checking",
            "pietto._project.capability_matrix",
            "pietto._project.extension_signature_provider",
            "pietto._project.extension_catalog_availability",
            "pietto._project.extension_catalog_inspection",
            "pietto._project_explain",
        }
        & imported_modules
    )
    builder_source = ast.get_source_segment(
        source,
        next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_build_package_graph"
        ),
    )
    assert builder_source is not None
    for forbidden in (
        "check_package_capability_requirements",
        "build_package_capability_checking_matrix",
        "select_extension_catalog",
        "lookup_capability",
        "to_json",
        "canonical_bytes =",
    ):
        assert forbidden not in builder_source


def test_slice4_spec_freezes_exact_states_identity_order_and_lifecycle() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "Binding absent | `UNDECLARED`",
        "Binding present with empty collection | `DECLARED`",
        "snapshot scope + owning package ref + package-local requirement position",
        "selector requirement refs to use `witness.requirement_position`",
        "Schema-v2 `EXTENSION_SIGNATURE` requirements remain valid",
        "Slice 4 current",
        "Slice 5 next/unstarted",
        "Add Phase 59 requirement selector attribution",
    ):
        assert required in normalized
