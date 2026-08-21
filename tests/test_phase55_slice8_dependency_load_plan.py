from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import inspect
from pathlib import Path
import struct

import pytest

import pietto
import pietto._project as project_package
import pietto._project.package_load_plan as package_load_plan
from pietto._project.model import (
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)
from pietto._project.package_load_plan import (
    DependencyLocatorKind,
    LoadedDependencyPackage,
    LocatedDependencyPackage,
    PackageDependencyEdge,
    PackageDependencyOccurrence,
    PackageDependencyValidationResult,
    PackageLoadPlan,
    PackageLoadPlanBlocker,
    PackageLoadPlanBlockerKind,
    PackageLoadPlanEntry,
    PackageLoadPlanResult,
    _build_package_load_plan,
    _validate_dependency_occurrences,
)
from pietto._project.package_loader import (
    LoadedRootPackage,
    _LoadedPackageContent,
    _PackageContentLoadResult,
    _PackageFileContent,
    _PackageModuleContent,
    _load_root_package,
)
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.package_manifest import PackageIdentity
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root


_SOURCE = b"shape Row:\n    id: Int\n"


def test_exact_dependency_validation_preserves_order_multiplicity_and_spelling(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    dep_digest = _write_package(project, "deps/a", namespace="Exact.NS", name="Name")
    dependencies = (
        ("Exact.NS", "Name", "1.2.3", dep_digest, "../deps/a"),
        ("Exact.NS", "Name", "1.2.3", dep_digest, "../deps/a"),
    )
    root_digest = _write_package(project, "root", dependencies=dependencies)
    root = _load_root(project, "root", root_digest)

    result = _validate_dependency_occurrences(root)

    assert result.ok
    assert tuple(occurrence.position for occurrence in result.occurrences) == (0, 1)
    assert tuple(occurrence.declaration for occurrence in result.occurrences) == (
        root.catalog.root_package.manifest.dependencies
    )
    assert (
        result.occurrences[0].declaration
        is (root.catalog.root_package.manifest.dependencies[0])
    )
    assert result.occurrences[0].coordinate.identity == PackageIdentity(
        "Exact.NS", "Name"
    )
    assert result.occurrences[0].coordinate.exact_version == "1.2.3"
    assert result.occurrences[0].content_digest_pin == dep_digest
    assert result.occurrences[0].locator_kind is DependencyLocatorKind.LOCAL_DIRECTORY
    assert result.occurrences[0].resolved_project_path == "deps/a"


@pytest.mark.parametrize(
    ("version", "sha256", "message"),
    (
        ("1.0", "a" * 64, "strict SemVer"),
        ("1.0.0", "A" * 64, "lowercase hexadecimal"),
    ),
)
def test_invalid_exact_version_and_digest_fail_semantic_validation(
    tmp_path: Path,
    version: str,
    sha256: str,
    message: str,
) -> None:
    project = tmp_path / message.replace(" ", "-")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(("ns", "dep", version, sha256, "../dep"),),
    )
    root = _load_root(project, "root", root_digest)

    result = _validate_dependency_occurrences(root)

    assert not result.ok and result.occurrences == ()
    assert message in result.errors[0].message
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA


def test_paths_normalize_from_declaring_package_and_escape_fails(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    root_digest = _write_package(
        project,
        "packages/root",
        dependencies=(
            ("ns", "shared", "1.0.0", "a" * 64, "../shared"),
            ("ns", "vendor", "1.0.0", "b" * 64, "./vendor/a"),
        ),
    )
    root = _load_root(project, "packages/root", root_digest)

    result = _validate_dependency_occurrences(root)

    assert result.ok
    assert tuple(item.resolved_project_path for item in result.occurrences) == (
        "packages/shared",
        "packages/root/vendor/a",
    )

    escape_digest = _write_package(
        project,
        "escape",
        dependencies=(("ns", "bad", "1.0.0", "c" * 64, "../../outside"),),
    )
    escape = _load_root(project, "escape", escape_digest)
    rejected = _validate_dependency_occurrences(escape)
    assert not rejected.ok
    assert rejected.errors[0].kind is ProjectDiscoveryErrorKind.PROJECT_PATH
    assert rejected.errors[0].path == "../../outside"


def test_nominal_identity_is_host_relocation_independent(tmp_path: Path) -> None:
    roots: list[LoadedRootPackage] = []
    for name in ("one", "two"):
        project = tmp_path / name
        root_digest = _write_package(
            project,
            "packages/root",
            dependencies=(("Exact", "Dep", "2.0.0", "d" * 64, "../dep"),),
        )
        roots.append(_load_root(project, "packages/root", root_digest))

    first = _validate_dependency_occurrences(roots[0]).occurrences[0]
    second = _validate_dependency_occurrences(roots[1]).occurrences[0]
    assert first.coordinate == second.coordinate
    assert first.content_digest_pin == second.content_digest_pin
    assert roots[0].located_root.canonical_path != roots[1].located_root.canonical_path


def test_zero_one_multiple_and_multihop_packages_emit_declaration_order_postorder(
    tmp_path: Path,
) -> None:
    zero_project = tmp_path / "zero"
    zero_digest = _write_package(zero_project, "root")
    zero = _build_package_load_plan(_load_root(zero_project, "root", zero_digest))
    assert zero.ok and zero.plan is not None
    assert _entry_paths(zero.plan) == ("root",)

    one_project = tmp_path / "one"
    dep_digest = _write_package(one_project, "deps/a", name="a")
    root_digest = _write_package(
        one_project,
        "root",
        dependencies=(("example", "a", "1.0.0", dep_digest, "../deps/a"),),
    )
    one = _build_package_load_plan(_load_root(one_project, "root", root_digest))
    assert one.ok and one.plan is not None
    assert _entry_paths(one.plan) == ("deps/a", "root")

    multi_project = tmp_path / "multi"
    z_digest = _write_package(multi_project, "deps/z", name="z")
    a_digest = _write_package(multi_project, "deps/a", name="a")
    root_digest = _write_package(
        multi_project,
        "root",
        dependencies=(
            ("example", "z", "1.0.0", z_digest, "../deps/z"),
            ("example", "a", "1.0.0", a_digest, "../deps/a"),
        ),
    )
    multiple = _build_package_load_plan(_load_root(multi_project, "root", root_digest))
    assert multiple.ok and multiple.plan is not None
    assert _entry_paths(multiple.plan) == ("deps/z", "deps/a", "root")
    assert tuple(
        edge.occurrence.position for edge in multiple.plan.entries[-1].dependencies
    ) == (0, 1)

    hop_project = tmp_path / "hop"
    leaf_digest = _write_package(hop_project, "deps/leaf", name="leaf")
    middle_digest = _write_package(
        hop_project,
        "deps/middle",
        name="middle",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    root_digest = _write_package(
        hop_project,
        "root",
        dependencies=(("example", "middle", "1.0.0", middle_digest, "../deps/middle"),),
    )
    multihop = _build_package_load_plan(_load_root(hop_project, "root", root_digest))
    assert multihop.ok and multihop.plan is not None
    assert _entry_paths(multihop.plan) == ("deps/leaf", "deps/middle", "root")


@pytest.mark.parametrize("field", ("namespace", "version", "sha256"))
def test_dependency_must_match_loaded_identity_version_and_digest(
    tmp_path: Path,
    field: str,
) -> None:
    project = tmp_path / field
    dep_digest = _write_package(project, "dep", namespace="actual", name="dep")
    namespace = "wrong" if field == "namespace" else "actual"
    version = "2.0.0" if field == "version" else "1.0.0"
    sha256 = "0" * 64 if field == "sha256" else dep_digest
    root_digest = _write_package(
        project,
        "root",
        dependencies=((namespace, "dep", version, sha256, "../dep"),),
    )
    root = _load_root(project, "root", root_digest)

    result = _build_package_load_plan(root)

    assert not result.ok and result.plan is None
    assert result.errors or result.blockers


@pytest.mark.parametrize("shape", ("missing", "symlink"))
def test_missing_or_symlink_dependency_package_fails_closed(
    tmp_path: Path,
    shape: str,
) -> None:
    project = tmp_path / shape
    project.mkdir()
    dependency_path = "missing"
    if shape == "symlink":
        outside = tmp_path / "outside"
        outside.mkdir()
        (project / "linked").symlink_to(outside, target_is_directory=True)
        dependency_path = "linked"
    root_digest = _write_package(
        project,
        "root",
        dependencies=(("example", "dep", "1.0.0", "a" * 64, f"../{dependency_path}"),),
    )
    root = _load_root(project, "root", root_digest)

    result = _build_package_load_plan(root)

    assert not result.ok and result.plan is None
    assert result.errors
    assert all(
        error.path is None or str(tmp_path) not in error.path for error in result.errors
    )


def test_exact_duplicate_occurrences_remain_two_edges_without_two_nodes(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    dep_digest = _write_package(project, "dep", name="dep")
    declaration = ("example", "dep", "1.0.0", dep_digest, "../dep")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(declaration, declaration),
    )
    result = _build_package_load_plan(_load_root(project, "root", root_digest))

    assert result.ok and result.plan is not None
    assert _entry_paths(result.plan) == ("dep", "root")
    root_entry = result.plan.entries[-1]
    assert len(root_entry.dependencies) == 2
    assert root_entry.dependencies[0].occurrence is not (
        root_entry.dependencies[1].occurrence
    )
    assert root_entry.dependencies[0].package is root_entry.dependencies[1].package


def test_cycle_terminates_with_private_occurrence_evidence(tmp_path: Path) -> None:
    project = tmp_path / "project"
    provisional_root_pin = "a" * 64
    child_digest = _write_package(
        project,
        "deps/child",
        name="child",
        dependencies=(
            ("example", "root", "1.0.0", provisional_root_pin, "../../root"),
        ),
    )
    root_digest = _write_package(
        project,
        "root",
        name="root",
        dependencies=(("example", "child", "1.0.0", child_digest, "../deps/child"),),
    )
    result = _build_package_load_plan(_load_root(project, "root", root_digest))

    assert not result.ok and result.plan is None and result.errors == ()
    assert result.blockers[0].kind is PackageLoadPlanBlockerKind.CYCLE
    assert (
        result.blockers[0].location.occurrence is (result.blockers[0].occurrences[-1])
    )
    assert tuple(item.declaration.name for item in result.blockers[0].occurrences) == (
        "child",
        "root",
    )


def test_identity_conflict_never_selects_one_physical_package(tmp_path: Path) -> None:
    project = tmp_path / "project"
    first_digest = _write_package(project, "deps/one", name="same", version="1.0.0")
    second_digest = _write_package(project, "deps/two", name="same", version="2.0.0")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(
            ("example", "same", "1.0.0", first_digest, "../deps/one"),
            ("example", "same", "2.0.0", second_digest, "../deps/two"),
        ),
    )
    result = _build_package_load_plan(_load_root(project, "root", root_digest))

    assert not result.ok and result.plan is None
    assert result.blockers[0].kind is PackageLoadPlanBlockerKind.CONFLICT
    assert len(result.blockers[0].occurrences) == 2
    assert result.blockers[0].location.occurrence is result.blockers[0].occurrences[-1]


def test_diamond_is_retained_as_private_blocker_without_winner(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    leaf_digest = _write_package(project, "deps/leaf", name="leaf")
    left_digest = _write_package(
        project,
        "deps/left",
        name="left",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    right_digest = _write_package(
        project,
        "deps/right",
        name="right",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    root_digest = _write_package(
        project,
        "root",
        dependencies=(
            ("example", "left", "1.0.0", left_digest, "../deps/left"),
            ("example", "right", "1.0.0", right_digest, "../deps/right"),
        ),
    )
    result = _build_package_load_plan(_load_root(project, "root", root_digest))

    assert not result.ok and result.plan is None
    assert result.blockers[0].kind is PackageLoadPlanBlockerKind.DIAMOND
    assert len(result.blockers[0].occurrences) == 2
    assert result.blockers[0].location.occurrence is result.blockers[0].occurrences[-1]


def test_packages_remain_separate_compilation_islands_with_equal_module_paths(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    dep_digest = _write_package(
        project, "dep", name="dep", module_path="models/main.pietto"
    )
    root_digest = _write_package(
        project,
        "root",
        module_path="models/main.pietto",
        dependencies=(("example", "dep", "1.0.0", dep_digest, "../dep"),),
    )
    result = _build_package_load_plan(_load_root(project, "root", root_digest))

    assert result.ok and result.plan is not None
    dependency, root = (entry.package for entry in result.plan.entries)
    assert dependency is not root
    assert dependency.modules[0].identity.path == root.modules[0].identity.path
    assert dependency.modules[0] is not root.modules[0]


def test_iterative_dfs_source_and_repeat_runs_are_deterministic(tmp_path: Path) -> None:
    project = tmp_path / "project"
    next_digest = _write_package(project, "deps/39", name="p39")
    for index in reversed(range(39)):
        next_digest = _write_package(
            project,
            f"deps/{index}",
            name=f"p{index}",
            dependencies=(
                ("example", f"p{index + 1}", "1.0.0", next_digest, f"../{index + 1}"),
            ),
        )
    root_digest = _write_package(
        project,
        "root",
        dependencies=(("example", "p0", "1.0.0", next_digest, "../deps/0"),),
    )
    root = _load_root(project, "root", root_digest)

    first = _build_package_load_plan(root)
    second = _build_package_load_plan(root)

    assert first.ok and second.ok and first.plan is not None and second.plan is not None
    assert _entry_paths(first.plan) == _entry_paths(second.plan)
    assert len(first.plan.entries) == 41
    source = inspect.getsource(_build_package_load_plan)
    assert source.count("_build_package_load_plan(") == 1


def test_plan_boundary_is_private_canonical_and_has_no_forbidden_products(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    root_digest = _write_package(project, "root")
    root = _load_root(project, "root", root_digest)
    result = _build_package_load_plan(root)
    assert result.ok and result.plan is not None

    for carrier in (
        PackageDependencyOccurrence,
        PackageDependencyEdge,
        PackageDependencyValidationResult,
        LocatedDependencyPackage,
        LoadedDependencyPackage,
        PackageLoadPlanEntry,
        PackageLoadPlan,
        PackageLoadPlanBlocker,
        PackageLoadPlanResult,
        _PackageFileContent,
        _PackageModuleContent,
        _LoadedPackageContent,
        _PackageContentLoadResult,
    ):
        assert hasattr(carrier, "__slots__")
        with pytest.raises(TypeError):
            carrier()  # type: ignore[call-arg]
    with pytest.raises(FrozenInstanceError):
        result.plan.entries = ()  # pyright: ignore[reportAttributeAccessIssue]

    assert package_load_plan.__all__ == ()
    for name in (
        "PackageDependencyOccurrence",
        "LoadedDependencyPackage",
        "PackageLoadPlan",
        "PackageLoadPlanResult",
        "_build_package_load_plan",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)

    source = inspect.getsource(package_load_plan)
    for forbidden in (
        "requests",
        "urllib",
        "http://",
        "https://",
        "ProjectSemanticModel",
        "ProjectLogicalModule",
        "ProjectModuleGraph",
        "subprocess",
    ):
        assert forbidden not in source


def _write_package(
    project: Path,
    package_path: str,
    *,
    namespace: str = "example",
    name: str = "root",
    version: str = "1.0.0",
    module_path: str = "main.pietto",
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> str:
    package_root = project / package_path
    package_root.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(
        namespace=namespace,
        name=name,
        version=version,
        module_path=module_path,
        dependencies=dependencies,
    )
    (package_root / "pietto-package.toml").write_bytes(manifest)
    module = package_root / module_path
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_bytes(_SOURCE)
    return _digest(manifest, ((module_path, _SOURCE),))


def _load_root(project: Path, package_path: str, digest: str) -> LoadedRootPackage:
    pinned_root = _pin_project_root(project)
    assert type(pinned_root) is ProjectPinnedRoot
    activation = ProjectRootPackageActivation(
        path=package_path,
        namespace="example",
        name="root",
        version="1.0.0",
        sha256=digest,
    )
    located = _locate_root_package(pinned_root, activation)
    assert located.ok and type(located.located_root) is LocatedRootPackage
    loaded = _load_root_package(located.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    assert loaded.loaded_package.content_digest == digest
    return loaded.loaded_package


def _manifest(
    *,
    namespace: str,
    name: str,
    version: str,
    module_path: str,
    dependencies: tuple[tuple[str, str, str, str, str], ...],
) -> bytes:
    lines = [
        "schema_version = 1",
        f'namespace = "{namespace}"',
        f'name = "{name}"',
        f'version = "{version}"',
        "",
        "[[assets]]",
        'kind = "module_source"',
        f'path = "{module_path}"',
    ]
    for dep_namespace, dep_name, dep_version, sha256, path in dependencies:
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f'namespace = "{dep_namespace}"',
                f'name = "{dep_name}"',
                f'version = "{dep_version}"',
                f'sha256 = "{sha256}"',
                f'path = "{path}"',
            )
        )
    return ("\n".join(lines) + "\n").encode()


def _digest(manifest: bytes, assets: tuple[tuple[str, bytes], ...]) -> str:
    stream = bytearray(b"pietto-package-content-v1\0")
    for path, content in (("pietto-package.toml", manifest), *assets):
        path_bytes = path.encode()
        stream.extend(struct.pack(">Q", len(path_bytes)))
        stream.extend(path_bytes)
        stream.extend(struct.pack(">Q", len(content)))
        stream.extend(content)
    return hashlib.sha256(stream).hexdigest()


def _entry_paths(plan: PackageLoadPlan) -> tuple[str, ...]:
    return tuple(
        package_load_plan._package_project_path(entry.package) for entry in plan.entries
    )
