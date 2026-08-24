from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto._metadata as metadata_package
import pietto._project as project_package
import pietto._project_explain as project_explain_package
import pietto._project_explain.package_requirement_projection as projection_module
import pietto.semantic as semantic_package
import test_phase55_slice10_package_inspection_canonical_serialization as package_slice
import test_phase56_slice6_exact_capability_requirement_checking as checking_slice
import test_phase56_slice8_capability_inspection_representation as inspection_slice
import test_phase58_slice1_project_explain_portability_scope_lock as slice1
from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
)
from pietto._project.capability_inspection import (
    CapabilityInspectionFactSet,
    CapabilityInspectionPackageRole,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    build_package_capability_checking_matrix,
)
from pietto._project.model import ProjectDiscoveryError, ProjectDiscoveryErrorKind
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    PackageInspectionOutcome,
    _build_package_inspection_fact_set,
)
from pietto._project.package_load_plan import LoadedPackage
from pietto._project.package_manifest import PackageCoordinate, PackageIdentity
from pietto._project_explain.model import (
    ProjectExplainLogicalPath,
    ProjectExplainLogicalPathKind,
    ProjectExplainRequirementStage,
)
from pietto._project_explain.package_requirement_projection import (
    ProjectExplainCapabilityKey,
    ProjectExplainDependencyLocatorKind,
    ProjectExplainDirectDependency,
    ProjectExplainPackage,
    ProjectExplainPackageAsset,
    ProjectExplainPackageAssetKind,
    ProjectExplainPackageCoordinate,
    ProjectExplainPackageRequirementProjection,
    ProjectExplainPackageRole,
    ProjectExplainRequirementCollection,
    ProjectExplainRequirementCollectionIdentity,
    ProjectExplainRequirementRequest,
    _project_package_requirement_provenance,
)
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase58-slice3-project-explain-package-requirement-provenance-v1.md"
)
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
SOURCE = REPO_ROOT / "src/pietto/_project_explain/package_requirement_projection.py"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"

_INT_KEY = CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int")
_TEXT_KEY = CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Text")
_WINDOW_KEY = CapabilityKey(
    CapabilityDomain.WINDOW_FUNCTION,
    operation="row_number",
    dialect="postgresql",
)

EXPECTED_CHANGED_PATHS = frozenset(
    {
        "src/pietto/_project_explain/compatibility_matrix_projection.py",
        "docs/spec/phase58-slice4-project-explain-requirement-target-matrix-v1.md",
        "tests/test_phase58_slice4_project_explain_requirement_target_matrix.py",
        "tests/test_phase58_slice3_project_explain_package_requirement_provenance.py",
        "docs/roadmap.md",
        "docs/status.md",
        "scripts/package_smoke.py",
        "tests/test_phase58_slice2_project_explain_common_model_envelope.py",
        "tests/test_phase58_slice1_project_explain_portability_scope_lock.py",
        "tests/test_phase52_private_capability_fact_foundation.py",
        "tests/test_phase52_fail_closed_capability_lookup.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        *slice1.LIFECYCLE_READERS,
    }
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _requirements(
    namespace: str,
    name: str,
    *keys: CapabilityKey,
) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity(namespace, name)
    return CapabilityRequirementCollection(
        identity,
        tuple(
            CapabilityRequirementOccurrence(identity, position, key)
            for position, key in enumerate(keys)
        ),
    )


def _capability_facts(
    package_facts: PackageInspectionFactSet,
    collections: tuple[CapabilityRequirementCollection | None, ...],
) -> tuple[CapabilityInspectionFactSet, ...]:
    assert len(collections) == len(package_facts.inspection.packages)
    composition = checking_slice._composition()
    context = inspection_slice._context(0, composition)
    result: list[CapabilityInspectionFactSet] = []
    for package, collection in zip(
        package_facts.inspection.packages,
        collections,
        strict=True,
    ):
        loaded = cast(LoadedPackage, package.entry.package)
        binding = (
            None
            if collection is None
            else PackageCapabilityRequirementBinding(loaded, collection)
        )
        matrix = build_package_capability_checking_matrix(
            loaded,
            binding,
            (context,),
        )
        result.append(build_capability_inspection(matrix))
    return tuple(result)


def _simple_authority(
    root: Path,
    *,
    dependency: CapabilityRequirementCollection | None = None,
    project: CapabilityRequirementCollection | None = None,
) -> tuple[
    PackageInspectionFactSet,
    tuple[CapabilityInspectionFactSet, ...],
]:
    package_facts = package_slice._simple_inspection(
        root,
        root_path=".",
        dependency_path="dep",
        authored_path="dep",
    )
    return package_facts, _capability_facts(
        package_facts,
        (dependency, project),
    )


def _projection(
    root: Path,
    *,
    dependency: CapabilityRequirementCollection | None = None,
    project: CapabilityRequirementCollection | None = None,
) -> ProjectExplainPackageRequirementProjection:
    package_facts, capability_facts = _simple_authority(
        root,
        dependency=dependency,
        project=project,
    )
    return _project_package_requirement_provenance(
        package_facts,
        capability_facts,
    )


def test_exact_enum_vocabularies_and_immutable_model_shapes() -> None:
    assert [(item.name, item.value) for item in ProjectExplainPackageRole] == [
        ("ROOT", "root"),
        ("DEPENDENCY", "dependency"),
    ]
    assert [(item.name, item.value) for item in ProjectExplainPackageAssetKind] == [
        ("MODULE_SOURCE", "module_source"),
    ]
    assert [
        (item.name, item.value) for item in ProjectExplainDependencyLocatorKind
    ] == [("LOCAL_DIRECTORY", "local_directory")]

    expected_fields = {
        ProjectExplainPackageCoordinate: ("namespace", "name", "release"),
        ProjectExplainPackageAsset: ("position", "kind", "path"),
        ProjectExplainDirectDependency: (
            "position",
            "target_package_position",
            "coordinate",
            "content_digest_pin",
            "locator_kind",
            "project_path",
        ),
        ProjectExplainPackage: (
            "position",
            "role",
            "coordinate",
            "project_path",
            "content_digest",
            "assets",
            "dependencies",
        ),
        ProjectExplainRequirementCollectionIdentity: ("namespace", "name"),
        ProjectExplainCapabilityKey: (
            "domain",
            "subject",
            "operation",
            "operands",
            "context",
            "dialect",
            "extension",
        ),
        ProjectExplainRequirementCollection: (
            "declared_by",
            "requested_by",
            "package_role",
            "identity",
            "requirement_positions",
        ),
        ProjectExplainRequirementRequest: (
            "position",
            "stage",
            "declared_by",
            "requested_by",
            "package_role",
            "collection",
            "occurrence_position",
            "key",
        ),
        ProjectExplainPackageRequirementProjection: (
            "root_package_position",
            "packages",
            "requirement_collections",
            "requirements",
        ),
    }
    for carrier, names in expected_fields.items():
        assert tuple(field.name for field in fields(carrier)) == names
        assert carrier.__dataclass_params__.frozen
        assert "__dict__" not in carrier.__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )


def test_model_rejects_wrong_exact_types_bool_positions_and_mutation(
    tmp_path: Path,
) -> None:
    projection = _projection(tmp_path)
    with pytest.raises(FrozenInstanceError):
        setattr(projection, "root_package_position", 0)
    with pytest.raises(TypeError):
        ProjectExplainPackageAsset(
            position=cast(int, True),
            kind=ProjectExplainPackageAssetKind.MODULE_SOURCE,
            path=projection.packages[0].assets[0].path,
        )
    with pytest.raises(TypeError):
        ProjectExplainPackageCoordinate(
            namespace=cast(str, 1),
            name="name",
            release="1.0.0",
        )
    with pytest.raises(ValueError):
        ProjectExplainPackageCoordinate(namespace="", name="name", release="1.0.0")
    with pytest.raises(TypeError):
        ProjectExplainCapabilityKey(
            domain=cast(CapabilityDomain, "logical_type"),
            subject="Int",
            operation=None,
            operands=(),
            context=None,
            dialect=None,
            extension=None,
        )


def test_root_dependency_assets_and_direct_dependencies_preserve_authority_order(
    tmp_path: Path,
) -> None:
    projection = _projection(tmp_path)
    assert projection.root_package_position == 1
    assert tuple(package.position for package in projection.packages) == (0, 1)
    dependency, root = projection.packages
    assert (dependency.coordinate.namespace, dependency.coordinate.name) == (
        "example",
        "dep",
    )
    assert dependency.role is ProjectExplainPackageRole.DEPENDENCY
    assert dependency.project_path.kind is (
        ProjectExplainLogicalPathKind.PROJECT_RELATIVE
    )
    assert dependency.project_path.value == "dep"
    assert root.role is ProjectExplainPackageRole.ROOT
    assert root.project_path.value == "."
    assert tuple(asset.position for asset in root.assets) == (0, 1)
    assert tuple(asset.path.value for asset in root.assets) == (
        "a.pietto",
        "b.pietto",
    )
    assert all(
        asset.kind is ProjectExplainPackageAssetKind.MODULE_SOURCE
        and asset.path.kind is ProjectExplainLogicalPathKind.PACKAGE_RELATIVE
        for asset in (*dependency.assets, *root.assets)
    )
    assert len(root.dependencies) == 1
    direct = root.dependencies[0]
    assert direct.position == 0
    assert direct.target_package_position == dependency.position
    assert direct.coordinate == dependency.coordinate
    assert direct.content_digest_pin == dependency.content_digest
    assert direct.locator_kind is ProjectExplainDependencyLocatorKind.LOCAL_DIRECTORY
    assert direct.project_path.value == "dep"


def test_dependency_first_private_order_is_preserved_without_sorting(
    tmp_path: Path,
) -> None:
    first = package_slice._two_dependency_inspection(tmp_path / "first", reverse=False)
    second = package_slice._two_dependency_inspection(tmp_path / "second", reverse=True)
    first_projection = _project_package_requirement_provenance(
        first,
        _capability_facts(first, (None, None, None)),
    )
    second_projection = _project_package_requirement_provenance(
        second,
        _capability_facts(second, (None, None, None)),
    )
    assert tuple(package.coordinate.name for package in first_projection.packages) == (
        "one",
        "two",
        "root",
    )
    assert tuple(package.coordinate.name for package in second_projection.packages) == (
        "two",
        "one",
        "root",
    )
    assert first_projection.root_package_position == 2
    assert second_projection.root_package_position == 2


def test_equal_direct_dependency_values_preserve_source_multiplicity(
    tmp_path: Path,
) -> None:
    dependency_digest = package_slice._write_package(
        tmp_path,
        "dep",
        name="dep",
    )
    declaration = ("example", "dep", "1.0.0", dependency_digest, "dep")
    root_digest = package_slice._write_package(
        tmp_path,
        ".",
        dependencies=(declaration, declaration),
    )
    package_facts = _build_package_inspection_fact_set(
        package_slice._plan(tmp_path, ".", root_digest)
    )
    projection = _project_package_requirement_provenance(
        package_facts,
        _capability_facts(package_facts, (None, None)),
    )
    dependencies = projection.packages[projection.root_package_position].dependencies
    assert tuple(item.position for item in dependencies) == (0, 1)
    assert dependencies[0].coordinate == dependencies[1].coordinate
    assert dependencies[0].target_package_position == (
        dependencies[1].target_package_position
    )


def test_root_and_dependency_requirements_preserve_bounded_why_and_key_shape(
    tmp_path: Path,
) -> None:
    dependency = _requirements("consumer", "dependency", _INT_KEY, _WINDOW_KEY)
    root = _requirements("consumer", "root", _TEXT_KEY)
    projection = _projection(tmp_path, dependency=dependency, project=root)

    assert tuple(
        collection.declared_by for collection in projection.requirement_collections
    ) == (
        0,
        1,
    )
    dependency_collection, root_collection = projection.requirement_collections
    assert dependency_collection.requested_by == projection.root_package_position == 1
    assert dependency_collection.package_role is ProjectExplainPackageRole.DEPENDENCY
    assert dependency_collection.requirement_positions == (0, 1)
    assert root_collection.declared_by == root_collection.requested_by == 1
    assert root_collection.package_role is ProjectExplainPackageRole.ROOT
    assert root_collection.requirement_positions == (2,)

    assert tuple(request.position for request in projection.requirements) == (0, 1, 2)
    assert tuple(
        request.occurrence_position for request in projection.requirements
    ) == (
        0,
        1,
        0,
    )
    assert all(
        request.stage is ProjectExplainRequirementStage.REQUEST
        and request.requested_by == projection.root_package_position
        for request in projection.requirements
    )
    first, window, root_request = projection.requirements
    assert first.declared_by == 0
    assert root_request.declared_by == 1
    assert tuple(field.name for field in fields(first.key)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert window.key.domain is CapabilityDomain.WINDOW_FUNCTION
    assert window.key.operation == "row_number"
    assert window.key.dialect == "postgresql"


def test_equal_requirement_values_across_packages_remain_distinct_occurrences(
    tmp_path: Path,
) -> None:
    same_dependency = _requirements("consumer", "same", _INT_KEY)
    same_root = _requirements("consumer", "same", _INT_KEY)
    projection = _projection(
        tmp_path,
        dependency=same_dependency,
        project=same_root,
    )
    assert len(projection.requirements) == 2
    assert projection.requirements[0].key == projection.requirements[1].key
    assert tuple(item.position for item in projection.requirements) == (0, 1)
    assert tuple(item.declared_by for item in projection.requirements) == (0, 1)


def test_undeclared_and_declared_empty_collections_remain_distinct(
    tmp_path: Path,
) -> None:
    declared_empty = _requirements("consumer", "empty")
    projection = _projection(tmp_path, dependency=None, project=declared_empty)
    assert projection.requirements == ()
    assert len(projection.requirement_collections) == 1
    collection = projection.requirement_collections[0]
    assert collection.declared_by == projection.root_package_position
    assert collection.requirement_positions == ()

    package_facts, capability_facts = _simple_authority(tmp_path / "undeclared")
    undeclared = _project_package_requirement_provenance(
        package_facts,
        capability_facts,
    )
    assert undeclared.requirement_collections == ()
    assert undeclared.requirements == ()


def test_non_success_package_inspection_fails_before_projection() -> None:
    error = ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.PROJECT_ROOT,
        "missing",
        None,
    )
    failed = _build_package_inspection_fact_set(package_slice._error_result((error,)))
    assert failed.inspection.outcome is PackageInspectionOutcome.ERROR
    with pytest.raises(ValueError):
        _project_package_requirement_provenance(failed, ())


def test_capability_fact_tuple_count_order_duplicates_and_foreign_authority_fail(
    tmp_path: Path,
) -> None:
    package_facts, capability_facts = _simple_authority(tmp_path / "main")
    with pytest.raises(TypeError):
        _project_package_requirement_provenance(
            package_facts,
            cast(tuple[CapabilityInspectionFactSet, ...], list(capability_facts)),
        )
    with pytest.raises(ValueError):
        _project_package_requirement_provenance(package_facts, capability_facts[:1])
    with pytest.raises(ValueError):
        _project_package_requirement_provenance(
            package_facts,
            tuple(reversed(capability_facts)),
        )
    with pytest.raises(ValueError):
        _project_package_requirement_provenance(
            package_facts,
            (capability_facts[0], capability_facts[0]),
        )

    foreign_packages, foreign_capabilities = _simple_authority(tmp_path / "foreign")
    del foreign_packages
    with pytest.raises(ValueError):
        _project_package_requirement_provenance(
            package_facts,
            (foreign_capabilities[0], capability_facts[1]),
        )


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("role", CapabilityInspectionPackageRole.ROOT),
        ("namespace", "foreign"),
        ("name", "foreign"),
        ("release", "9.9.9"),
        ("content_digest", "f" * 64),
    ),
)
def test_capability_detached_role_coordinate_and_digest_mismatch_fail(
    tmp_path: Path,
    field_name: str,
    replacement: object,
) -> None:
    package_facts, capability_facts = _simple_authority(tmp_path)
    object.__setattr__(
        capability_facts[0].inspection.package,
        field_name,
        replacement,
    )
    with pytest.raises(ValueError):
        _project_package_requirement_provenance(package_facts, capability_facts)


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("target_package_position", 99),
        ("content_digest_pin", "f" * 64),
        (
            "coordinate",
            PackageCoordinate(PackageIdentity("foreign", "dep"), "1.0.0"),
        ),
        ("resolved_project_path", "/host/dep"),
    ),
)
def test_malformed_dependency_target_pin_coordinate_and_path_fail(
    tmp_path: Path,
    field_name: str,
    replacement: object,
) -> None:
    package_facts, capability_facts = _simple_authority(tmp_path)
    root = package_facts.inspection.packages[-1]
    object.__setattr__(root.dependencies[0], field_name, replacement)
    with pytest.raises(ValueError):
        _project_package_requirement_provenance(package_facts, capability_facts)


def test_grafted_requirement_order_fails_closed(tmp_path: Path) -> None:
    collection = _requirements("consumer", "ordered", _INT_KEY, _TEXT_KEY)
    package_facts, capability_facts = _simple_authority(
        tmp_path,
        project=collection,
    )
    root_facts = capability_facts[-1]
    object.__setattr__(
        root_facts.inspection,
        "requirements",
        tuple(reversed(root_facts.inspection.requirements)),
    )
    with pytest.raises(ValueError):
        _project_package_requirement_provenance(package_facts, capability_facts)


def test_projection_root_rejects_invalid_internal_references(tmp_path: Path) -> None:
    collection = _requirements("consumer", "root", _INT_KEY)
    projection = _projection(tmp_path, project=collection)
    with pytest.raises(ValueError):
        replace(projection, root_package_position=0)
    bad_collection = replace(
        projection.requirement_collections[0],
        requirement_positions=(99,),
    )
    with pytest.raises(ValueError):
        replace(projection, requirement_collections=(bad_collection,))
    root = projection.packages[projection.root_package_position]
    bad_dependency = replace(root.dependencies[0], target_package_position=99)
    bad_root = replace(root, dependencies=(bad_dependency,))
    with pytest.raises(ValueError):
        replace(
            projection,
            packages=(projection.packages[0], bad_root),
        )


def _walk(value: object) -> tuple[object, ...]:
    values = [value]
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(cast(Any, value)):
            values.extend(_walk(getattr(value, field.name)))
    elif type(value) is tuple:
        for item in cast(tuple[object, ...], value):
            values.extend(_walk(item))
    return tuple(values)


def test_output_is_fully_detached_relocation_stable_and_private(tmp_path: Path) -> None:
    projection = _projection(
        tmp_path,
        dependency=_requirements("consumer", "dependency", _INT_KEY),
        project=_requirements("consumer", "root", _TEXT_KEY),
    )
    values = _walk(projection)
    assert not any(isinstance(value, Path) for value in values)
    assert str(tmp_path) not in repr(projection)
    forbidden_type_names = {
        "LoadedRootPackage",
        "LoadedDependencyPackage",
        "PackageInspectionFactSet",
        "CapabilityInspectionFactSet",
        "PackageLoadPlan",
        "PackageLoadPlanEntry",
        "PackageDependencyEdge",
        "CapabilityRequirementCollection",
        "CapabilityRequirementOccurrence",
        "PackageCapabilityCheckingMatrix",
        "CapabilityInspection",
    }
    assert forbidden_type_names.isdisjoint(type(value).__name__ for value in values)
    assert all(
        cast(ProjectExplainLogicalPath, path).kind
        in {
            ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
        }
        for path in values
        if type(path).__name__ == "ProjectExplainLogicalPath"
    )


def test_module_is_private_pure_and_has_no_later_slice_surface() -> None:
    assert project_explain_package.__all__ == projection_module.__all__ == ()
    for public_module in (pietto, project_package, metadata_package, semantic_package):
        for name in (
            "ProjectExplainPackageRequirementProjection",
            "ProjectExplainRequirementRequest",
            "ProjectExplainPackage",
        ):
            assert not hasattr(public_module, name)
    source = _read(SOURCE)
    for forbidden in (
        "pathlib",
        "import os",
        "open(",
        ".resolve(",
        ".stat(",
        "socket",
        "requests",
        "json",
        "serialize",
        "render_",
        "argparse",
        "check_package_capability_requirements",
        "build_package_capability_checking_matrix",
        "_build_package_load_plan",
        "ProjectExplainPayload",
        "ProjectExplainTarget",
        "ProjectExplainMatrix",
        "ProjectExplainCatalog",
        "ProjectExplainPortability",
    ):
        assert forbidden not in source


def test_package_smoke_requires_and_imports_installed_projection() -> None:
    source = _read(PACKAGE_SMOKE)
    for required in (
        'f"{prefix}/_project_explain/package_requirement_projection.py"',
        '"installed private project explain package requirement projection import"',
        "import pietto._project_explain.package_requirement_projection",
        'f"{prefix}/_project_explain/compatibility_matrix_projection.py"',
        '"installed private project explain compatibility matrix projection import"',
        "import pietto._project_explain.compatibility_matrix_projection",
    ):
        assert required in source


def test_spec_route_lifecycle_inventory_and_slice4_handoff_are_exact() -> None:
    document = _read(SPEC)
    assert slice1._headings(document) == (
        "Answer And Authority",
        "Exact Private Authorities",
        "No Re-resolution Boundary",
        "Private Python Surface",
        "Closed Vocabularies",
        "Immutable Model Shapes",
        "Package Coordinate And Digest Contract",
        "Package Ordering And Root Position",
        "Package Paths Assets And Dependencies",
        "Requirement Collection Contract",
        "Detached Capability Key",
        "Requirement REQUEST Contract",
        "Bounded Provenance Semantics",
        "Projection Integrity",
        "Canonical Construction",
        "Privacy And Detachment",
        "Retained Later Ownership",
        "Compatibility",
        "Lifecycle And Slice 4 Handoff",
    )
    assert "PHASE58_SLICE3_SELF_OWNED_OPEN = 0" in document
    assert (
        slice1._table_rows(slice1._section(_read(ROADMAP), "Phase 58 route"))[1:]
        == slice1.EXPECTED_ROUTE
    )
    assert slice1._table_rows(_read(STATUS))[1:] == (
        ("Package and CLI", "`0.1.0`"),
        ("Phase 55", "`COMPLETED`"),
        ("Phase 56", "`COMPLETED`"),
        ("Phase 57", "`COMPLETED`"),
        ("Phase 58", "`ACTIVE`"),
        ("Slice 1", "`COMPLETED`"),
        ("Slice 2", "`COMPLETED`"),
        ("Slice 3", "`COMPLETED`"),
        ("Slice 4", "`CURRENT`"),
        ("Slice 5", "`NEXT / UNSTARTED`"),
        ("Next", "`PHASE58_SLICE5_END_TO_END`"),
    )
    normalized_document = " ".join(document.split())
    for required in (
        "Public requirement/target compatibility matrix",
        "explicit evaluated targets",
        "`UNDECLARED`/`BLOCKED`/`CHECKED`",
        "`SATISFIED`/`UNSUPPORTED`/`ABSENT`/`UNKNOWN`/`CONFLICT`",
        "Slice 4 remains `UNSTARTED / NOT AUTHORIZED`",
    ):
        assert required in normalized_document

    production_paths = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "src/pietto/_project_explain").iterdir()
        if path.is_file()
    }
    assert production_paths == {
        "src/pietto/_project_explain/__init__.py",
        "src/pietto/_project_explain/compatibility_matrix_projection.py",
        "src/pietto/_project_explain/model.py",
        "src/pietto/_project_explain/package_requirement_projection.py",
    }
    phase58_paths = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (
            *(REPO_ROOT / "docs/spec").glob("phase58-*"),
            *(REPO_ROOT / "tests").glob("test_phase58_*"),
        )
    }
    assert phase58_paths == {
        "docs/spec/phase58-project-explain-portability-scope-lock-v1.md",
        "docs/spec/phase58-slice2-project-explain-common-model-envelope-v1.md",
        "docs/spec/phase58-slice3-project-explain-package-requirement-provenance-v1.md",
        "docs/spec/phase58-slice4-project-explain-requirement-target-matrix-v1.md",
        "tests/test_phase58_slice1_project_explain_portability_scope_lock.py",
        "tests/test_phase58_slice2_project_explain_common_model_envelope.py",
        "tests/test_phase58_slice3_project_explain_package_requirement_provenance.py",
        "tests/test_phase58_slice4_project_explain_requirement_target_matrix.py",
    }
    assert len(EXPECTED_CHANGED_PATHS) == 26
    assert all((REPO_ROOT / path).exists() for path in EXPECTED_CHANGED_PATHS)
