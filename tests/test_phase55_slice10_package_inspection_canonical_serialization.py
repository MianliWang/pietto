from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import inspect
import os
from pathlib import Path
import struct
import subprocess
import sys

import pytest

import pietto
import pietto._project as project_package
import pietto._project.package_inspection as package_inspection
from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)
from pietto._project.package_inspection import (
    PackageInspection,
    PackageInspectionAsset,
    PackageInspectionDependency,
    PackageInspectionDiagnostic,
    PackageInspectionError,
    PackageInspectionFactSet,
    PackageInspectionFormat,
    PackageInspectionOutcome,
    PackageInspectionPackage,
    PackageInspectionPackageRole,
    PackageInspectionRejection,
    PackageInspectionRejectionOccurrence,
    _build_package_inspection_fact_set,
)
from pietto._project.package_load_plan import (
    PackageLoadPlanBlockerKind,
    PackageLoadPlanResult,
    _build_package_load_plan,
)
from pietto._project.package_loader import LoadedRootPackage, _load_root_package
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root
from pietto._project.package_rejection import PackageConflictReason


_SOURCE_A = b"shape Row:\n    id: Int\n"
_SOURCE_B = b"shape Row:\n    value: Text\n"


def test_success_projection_preserves_exact_plan_asset_and_dependency_order(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    leaf_digest = _write_package(
        project,
        "deps/leaf",
        name="leaf",
        version="2.0.0",
        assets=(("models/main.pietto", _SOURCE_A),),
    )
    middle_digest = _write_package(
        project,
        "deps/middle",
        name="middle",
        assets=(("models/main.pietto", _SOURCE_A),),
        dependencies=(("example", "leaf", "2.0.0", leaf_digest, "../leaf"),),
    )
    declaration = (
        "example",
        "middle",
        "1.0.0",
        middle_digest,
        "../../deps/middle",
    )
    root_digest = _write_package(
        project,
        "packages/root",
        assets=(
            ("z/main.pietto", _SOURCE_A),
            ("a/main.pietto", _SOURCE_B),
        ),
        dependencies=(declaration, declaration),
    )

    result = _plan(project, "packages/root", root_digest)
    facts = _build_package_inspection_fact_set(result)
    inspection = facts.inspection

    assert inspection.format is PackageInspectionFormat.PACKAGE_INSPECTION_V1
    assert inspection.outcome is PackageInspectionOutcome.SUCCESS
    assert inspection.plan_result is result
    assert inspection.package_count == 3
    assert tuple(package.project_path for package in inspection.packages) == (
        "deps/leaf",
        "deps/middle",
        "packages/root",
    )
    assert tuple(package.position for package in inspection.packages) == (0, 1, 2)
    assert inspection.packages[-1].role is PackageInspectionPackageRole.ROOT
    assert all(
        package.role is PackageInspectionPackageRole.DEPENDENCY
        for package in inspection.packages[:-1]
    )
    assert inspection.root_coordinate is inspection.packages[-1].coordinate
    assert tuple(asset.path for asset in inspection.packages[-1].assets) == (
        "z/main.pietto",
        "a/main.pietto",
    )
    assert tuple(asset.position for asset in inspection.packages[-1].assets) == (0, 1)
    root_dependencies = inspection.packages[-1].dependencies
    assert tuple(item.position for item in root_dependencies) == (0, 1)
    assert tuple(item.authored_path for item in root_dependencies) == (
        "../../deps/middle",
        "../../deps/middle",
    )
    assert tuple(item.resolved_project_path for item in root_dependencies) == (
        "deps/middle",
        "deps/middle",
    )
    assert tuple(item.target_package_position for item in root_dependencies) == (1, 1)
    assert root_dependencies[0].edge.package is root_dependencies[1].edge.package
    assert root_dependencies[0].edge.occurrence is not (
        root_dependencies[1].edge.occurrence
    )
    assert inspection.packages[0].coordinate.exact_version == "2.0.0"
    assert inspection.packages[0].content_digest == leaf_digest
    assert inspection.packages[1].dependencies[0].content_digest_pin == leaf_digest
    assert tuple(
        package.entry.package.modules[0].identity.path
        for package in inspection.packages
    ) == ("models/main.pietto", "models/main.pietto", "z/main.pietto")
    assert facts.authority.plan_result is result
    assert facts.authority.rejection_product.plan_result is result
    assert facts.inspection is facts.authority.inspection
    assert facts.canonical_bytes is facts.authority.canonical_bytes


def test_zero_dependency_root_and_exact_error_vector(tmp_path: Path) -> None:
    zero_project = tmp_path / "zero"
    zero_digest = _write_package(zero_project, "root")
    zero = _build_package_inspection_fact_set(
        _plan(zero_project, "root", zero_digest)
    ).inspection
    assert zero.outcome is PackageInspectionOutcome.SUCCESS
    assert zero.package_count == 1
    assert zero.packages[0].role is PackageInspectionPackageRole.ROOT
    assert zero.packages[0].dependencies == ()

    error_project = tmp_path / "error"
    error_digest = _write_package(
        error_project,
        "root",
        dependencies=(("example", "outside", "1.0.0", "a" * 64, "../../outside"),),
    )
    error_result = _plan(error_project, "root", error_digest)
    facts = _build_package_inspection_fact_set(error_result)
    expected = (
        b"inspection\tformat=e:pietto.package-inspection.v1"
        b"\toutcome=e:error\tpackages=i:0\terrors=i:1"
        b"\tdiagnostics=i:0\trejections=i:0\n"
        b"error\terror=i:0\tkind=e:project_path"
        b"\tmessage=s:Package dependency path escapes the pinned project root."
        b"\tpath=s:../../outside\n"
    )
    assert facts.canonical_bytes == expected
    assert facts.inspection.errors[0].error is error_result.errors[0]


def test_repeated_relocated_and_separate_process_construction_is_canonical(
    tmp_path: Path,
) -> None:
    results: list[PackageInspectionFactSet] = []
    for directory in ("one", "two"):
        project = tmp_path / directory
        dep_digest = _write_package(project, "dep", name="dep")
        root_digest = _write_package(
            project,
            "root",
            dependencies=(("example", "dep", "1.0.0", dep_digest, "../dep"),),
        )
        plan_result = _plan(project, "root", root_digest)
        first = _build_package_inspection_fact_set(plan_result)
        second = _build_package_inspection_fact_set(plan_result)
        assert first.inspection == second.inspection
        assert first.canonical_bytes == second.canonical_bytes
        results.append(first)

    assert results[0].inspection == results[1].inspection
    assert results[0].canonical_bytes == results[1].canonical_bytes
    first_plan = results[0].inspection.plan_result.plan
    second_plan = results[1].inspection.plan_result.plan
    assert first_plan is not None and second_plan is not None
    assert (
        first_plan.root_package.located_root.canonical_path
        != second_plan.root_package.located_root.canonical_path
    )

    error = ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.PROJECT_PATH,
        "Package dependency path escapes the pinned project root.",
        "../../outside",
    )
    expected = _build_package_inspection_fact_set(
        _error_result((error,))
    ).canonical_bytes
    script = (
        "import sys\n"
        "from pietto._project.model import ProjectDiscoveryError, ProjectDiscoveryErrorKind\n"
        "from pietto._project.package_inspection import _build_package_inspection_fact_set\n"
        "from pietto._project.package_load_plan import PackageLoadPlanResult\n"
        "result = object.__new__(PackageLoadPlanResult)\n"
        "object.__setattr__(result, 'plan', None)\n"
        "object.__setattr__(result, 'errors', (ProjectDiscoveryError(\n"
        "    ProjectDiscoveryErrorKind.PROJECT_PATH,\n"
        "    'Package dependency path escapes the pinned project root.',\n"
        "    '../../outside',\n"
        "),))\n"
        "object.__setattr__(result, 'blockers', ())\n"
        "object.__setattr__(result, 'diagnostics', ())\n"
        "sys.stdout.buffer.write(_build_package_inspection_fact_set(result).canonical_bytes)\n"
    )
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = "4294967295"
    environment["PYTHONPATH"] = str(Path(pietto.__file__).resolve().parents[1])
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        env=environment,
    )
    assert completed.stdout == expected


def test_canonical_bytes_change_with_each_retained_authority_fact(
    tmp_path: Path,
) -> None:
    baseline = _simple_inspection(tmp_path / "baseline")
    renamed = _simple_inspection(tmp_path / "renamed", root_name="renamed")
    changed_digest = _simple_inspection(
        tmp_path / "digest",
        root_assets=(("a.pietto", _SOURCE_B), ("b.pietto", _SOURCE_B)),
    )
    changed_pin = _simple_inspection(
        tmp_path / "pin",
        dependency_source=_SOURCE_B,
    )
    changed_authored = _simple_inspection(
        tmp_path / "authored",
        authored_path=".././dep",
    )
    changed_resolved = _simple_inspection(
        tmp_path / "resolved",
        root_path="nested/root",
        dependency_path="nested/dep",
    )
    changed_asset_order = _simple_inspection(
        tmp_path / "asset-order",
        root_assets=(("b.pietto", _SOURCE_B), ("a.pietto", _SOURCE_A)),
    )

    variants = (
        renamed,
        changed_digest,
        changed_pin,
        changed_authored,
        changed_resolved,
        changed_asset_order,
    )
    assert all(item.canonical_bytes != baseline.canonical_bytes for item in variants)
    assert renamed.inspection.root_coordinate != baseline.inspection.root_coordinate
    assert changed_digest.inspection.packages[-1].content_digest != (
        baseline.inspection.packages[-1].content_digest
    )
    assert changed_pin.inspection.packages[-1].dependencies[0].content_digest_pin != (
        baseline.inspection.packages[-1].dependencies[0].content_digest_pin
    )
    assert changed_authored.inspection.packages[-1].dependencies[0].authored_path == (
        ".././dep"
    )
    assert (
        changed_authored.inspection.packages[-1].dependencies[0].resolved_project_path
        == baseline.inspection.packages[-1].dependencies[0].resolved_project_path
    )
    assert (
        changed_resolved.inspection.packages[-1].dependencies[0].resolved_project_path
        == "nested/dep"
    )
    assert tuple(
        asset.path for asset in changed_asset_order.inspection.packages[-1].assets
    ) == (
        "b.pietto",
        "a.pietto",
    )

    forward = _two_dependency_inspection(tmp_path / "forward", reverse=False)
    backward = _two_dependency_inspection(tmp_path / "backward", reverse=True)
    assert tuple(
        dependency.coordinate.identity.name
        for dependency in forward.inspection.packages[-1].dependencies
    ) == ("one", "two")
    assert tuple(
        dependency.coordinate.identity.name
        for dependency in backward.inspection.packages[-1].dependencies
    ) == ("two", "one")
    assert forward.canonical_bytes != backward.canonical_bytes


def test_rejections_and_project_errors_preserve_complete_ordered_evidence(
    tmp_path: Path,
) -> None:
    cycle_project = tmp_path / "cycle"
    child_digest = _write_package(
        cycle_project,
        "deps/child",
        name="child",
        dependencies=(("example", "root", "1.0.0", "a" * 64, "../../root"),),
    )
    root_digest = _write_package(
        cycle_project,
        "root",
        dependencies=(("example", "child", "1.0.0", child_digest, "../deps/child"),),
    )
    cycle_result = _plan(cycle_project, "root", root_digest)
    cycle = _build_package_inspection_fact_set(cycle_result).inspection
    assert cycle.outcome is PackageInspectionOutcome.REJECTED
    assert cycle.packages == () and cycle.root_coordinate is None
    assert cycle.rejections[0].kind is PackageLoadPlanBlockerKind.CYCLE
    assert tuple(
        occurrence.coordinate.identity.name
        for occurrence in cycle.rejections[0].occurrences
    ) == ("child", "root")
    assert cycle.rejections[0].diagnostic.blocker is cycle_result.blockers[0]

    conflict_project = tmp_path / "conflict"
    one_digest = _write_package(
        conflict_project,
        "deps/one",
        name="same",
        version="1.0.0",
    )
    two_digest = _write_package(
        conflict_project,
        "deps/two",
        name="same",
        version="2.0.0",
    )
    conflict_root = _write_package(
        conflict_project,
        "root",
        dependencies=(
            ("example", "same", "1.0.0", one_digest, "../deps/one"),
            ("example", "same", "2.0.0", two_digest, "../deps/two"),
        ),
    )
    conflict = _build_package_inspection_fact_set(
        _plan(conflict_project, "root", conflict_root)
    ).inspection.rejections[0]
    assert conflict.kind is PackageLoadPlanBlockerKind.CONFLICT
    assert conflict.conflict_reasons == (
        PackageConflictReason.IDENTITY_DIFFERENT_PHYSICAL_ROOT,
        PackageConflictReason.INCOMPATIBLE_CONTENT_DIGEST_PIN,
    )
    assert len(conflict.occurrences) == 2

    diamond_project = tmp_path / "diamond"
    leaf_digest = _write_package(diamond_project, "deps/leaf", name="leaf")
    left_digest = _write_package(
        diamond_project,
        "deps/left",
        name="left",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    right_digest = _write_package(
        diamond_project,
        "deps/right",
        name="right",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    diamond_root = _write_package(
        diamond_project,
        "root",
        dependencies=(
            ("example", "left", "1.0.0", left_digest, "../deps/left"),
            ("example", "right", "1.0.0", right_digest, "../deps/right"),
        ),
    )
    diamond = _build_package_inspection_fact_set(
        _plan(diamond_project, "root", diamond_root)
    ).inspection.rejections[0]
    assert diamond.kind is PackageLoadPlanBlockerKind.DIAMOND
    assert tuple(
        occurrence.declaring_coordinate.identity.name
        for occurrence in diamond.occurrences
    ) == ("left", "right")
    assert diamond.conflict_reasons == ()
    assert "no-winner" in diamond.message

    errors = (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            "first",
            "pietto-package.toml",
        ),
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.PROJECT_PATH,
            "second",
            "../authored",
        ),
    )
    projected = _build_package_inspection_fact_set(_error_result(errors)).inspection
    assert tuple(error.error for error in projected.errors) == errors
    assert tuple(error.message for error in projected.errors) == ("first", "second")
    assert tuple(error.position for error in projected.errors) == (0, 1)


def test_parser_error_diagnostics_are_projected_without_partial_graph(
    tmp_path: Path,
) -> None:
    project = tmp_path / "parser-error"
    dependency_digest = _write_package(
        project,
        "dep",
        name="dep",
        assets=(("bad.pietto", b"shape Broken:\n  bad\n"),),
    )
    root_digest = _write_package(
        project,
        "root",
        dependencies=(("example", "dep", "1.0.0", dependency_digest, "../dep"),),
    )
    result = _plan(project, "root", root_digest)
    inspection = _build_package_inspection_fact_set(result).inspection

    assert result.plan is None and result.diagnostics
    assert inspection.outcome is PackageInspectionOutcome.ERROR
    assert inspection.packages == () and inspection.rejections == ()
    assert tuple(item.diagnostic for item in inspection.diagnostics) == (
        result.diagnostics
    )
    assert inspection.diagnostics[0].path == "bad.pietto"
    assert str(tmp_path) not in inspection.diagnostics[0].message


def test_contradictory_and_grafted_products_fail_closed(tmp_path: Path) -> None:
    facts: list[PackageInspectionFactSet] = []
    for name in ("one", "two"):
        project = tmp_path / name
        digest = _write_package(project, "root")
        facts.append(_build_package_inspection_fact_set(_plan(project, "root", digest)))
    first, foreign = facts
    assert first.inspection == foreign.inspection
    assert first.inspection is not foreign.inspection
    assert first.canonical_bytes == foreign.canonical_bytes

    with pytest.raises(ValueError, match="exact derived inspection"):
        replace(first, inspection=foreign.inspection)
    with pytest.raises(ValueError, match="exact derived canonical bytes"):
        replace(first, canonical_bytes=bytes(bytearray(first.canonical_bytes)))
    with pytest.raises(ValueError, match="exact derived inspection"):
        replace(first, authority=foreign.authority)
    with pytest.raises(FrozenInstanceError):
        first.inspection = foreign.inspection  # pyright: ignore[reportAttributeAccessIssue]

    successful = first.inspection.plan_result
    contradictory = object.__new__(PackageLoadPlanResult)
    object.__setattr__(contradictory, "plan", successful.plan)
    object.__setattr__(
        contradictory,
        "errors",
        (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                "contradictory",
            ),
        ),
    )
    object.__setattr__(contradictory, "blockers", ())
    object.__setattr__(contradictory, "diagnostics", ())
    with pytest.raises(ValueError, match="forbid failure evidence"):
        _build_package_inspection_fact_set(contradictory)
    with pytest.raises(ValueError, match="require exact failure evidence"):
        _build_package_inspection_fact_set(_error_result(()))


def test_builder_is_pure_private_and_payload_has_no_host_or_raw_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "private"
    dependency_digest = _write_package(project, "dep", name="dep")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(("example", "dep", "1.0.0", dependency_digest, "../dep"),),
    )
    result = _plan(project, "root", root_digest)

    def refuse(*arguments: object, **keywords: object) -> object:
        del arguments, keywords
        raise AssertionError("package inspection must not perform input or output")

    monkeypatch.setattr("builtins.open", refuse)
    monkeypatch.setattr(Path, "open", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    monkeypatch.setattr(Path, "read_bytes", refuse)
    monkeypatch.setattr(os, "open", refuse)
    monkeypatch.setattr(os, "listdir", refuse)
    facts = _build_package_inspection_fact_set(result)
    decoded = facts.canonical_bytes.decode("utf-8")

    assert str(tmp_path) not in decoded
    assert str(tmp_path.resolve()) not in decoded
    assert _SOURCE_A.decode().strip() not in decoded
    assert "canonical_path" not in decoded
    assert "inode" not in decoded
    assert "device" not in decoded
    assert "object at" not in decoded
    assert "0x" not in decoded
    assert decoded.startswith("inspection\tformat=e:pietto.package-inspection.v1\t")
    assert decoded.endswith("\n") and not decoded.endswith("\n\n")

    source = inspect.getsource(package_inspection)
    for forbidden in (
        "open(",
        "pathlib",
        "requests",
        "urllib",
        "http://",
        "https://",
        "getcwd",
        "environ",
        "listdir",
        "_build_package_load_plan(",
    ):
        assert forbidden not in source

    assert package_inspection.__all__ == ()
    for name in (
        "PackageInspection",
        "PackageInspectionFactSet",
        "PackageInspectionPackage",
        "_build_package_inspection_fact_set",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)


def test_all_new_carriers_are_immutable_slotted_and_canonical_only() -> None:
    for carrier in (
        PackageInspectionAsset,
        PackageInspectionDependency,
        PackageInspectionPackage,
        PackageInspectionError,
        PackageInspectionDiagnostic,
        PackageInspectionRejectionOccurrence,
        PackageInspectionRejection,
        PackageInspection,
    ):
        assert hasattr(carrier, "__slots__")
        with pytest.raises(TypeError):
            carrier()  # type: ignore[call-arg]


def _simple_inspection(
    project: Path,
    *,
    root_name: str = "root",
    root_path: str = "root",
    dependency_path: str = "dep",
    dependency_source: bytes = _SOURCE_A,
    authored_path: str = "../dep",
    root_assets: tuple[tuple[str, bytes], ...] = (
        ("a.pietto", _SOURCE_A),
        ("b.pietto", _SOURCE_B),
    ),
) -> PackageInspectionFactSet:
    dependency_digest = _write_package(
        project,
        dependency_path,
        name="dep",
        assets=(("main.pietto", dependency_source),),
    )
    root_digest = _write_package(
        project,
        root_path,
        name=root_name,
        assets=root_assets,
        dependencies=(("example", "dep", "1.0.0", dependency_digest, authored_path),),
    )
    return _build_package_inspection_fact_set(
        _plan(project, root_path, root_digest, name=root_name)
    )


def _two_dependency_inspection(
    project: Path,
    *,
    reverse: bool,
) -> PackageInspectionFactSet:
    one_digest = _write_package(project, "one", name="one")
    two_digest = _write_package(project, "two", name="two")
    dependencies = (
        ("example", "one", "1.0.0", one_digest, "../one"),
        ("example", "two", "1.0.0", two_digest, "../two"),
    )
    if reverse:
        dependencies = tuple(reversed(dependencies))
    root_digest = _write_package(project, "root", dependencies=dependencies)
    return _build_package_inspection_fact_set(_plan(project, "root", root_digest))


def _error_result(
    errors: tuple[ProjectDiscoveryError, ...],
) -> PackageLoadPlanResult:
    result = object.__new__(PackageLoadPlanResult)
    object.__setattr__(result, "plan", None)
    object.__setattr__(result, "errors", errors)
    object.__setattr__(result, "blockers", ())
    object.__setattr__(result, "diagnostics", ())
    return result


def _write_package(
    project: Path,
    package_path: str,
    *,
    namespace: str = "example",
    name: str = "root",
    version: str = "1.0.0",
    assets: tuple[tuple[str, bytes], ...] = (("main.pietto", _SOURCE_A),),
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> str:
    package_root = project / package_path
    package_root.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(
        namespace=namespace,
        name=name,
        version=version,
        assets=tuple(path for path, _ in assets),
        dependencies=dependencies,
    )
    (package_root / "pietto-package.toml").write_bytes(manifest)
    for logical_path, content in assets:
        path = package_root.joinpath(*logical_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return _digest(manifest, assets)


def _plan(
    project: Path,
    package_path: str,
    digest: str,
    *,
    namespace: str = "example",
    name: str = "root",
    version: str = "1.0.0",
) -> PackageLoadPlanResult:
    pinned_root = _pin_project_root(project)
    assert type(pinned_root) is ProjectPinnedRoot
    activation = ProjectRootPackageActivation(
        path=package_path,
        namespace=namespace,
        name=name,
        version=version,
        sha256=digest,
    )
    located = _locate_root_package(pinned_root, activation)
    assert located.ok and type(located.located_root) is LocatedRootPackage
    loaded = _load_root_package(located.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    return _build_package_load_plan(loaded.loaded_package)


def _manifest(
    *,
    namespace: str,
    name: str,
    version: str,
    assets: tuple[str, ...],
    dependencies: tuple[tuple[str, str, str, str, str], ...],
) -> bytes:
    lines = [
        "schema_version = 1",
        f'namespace = "{namespace}"',
        f'name = "{name}"',
        f'version = "{version}"',
    ]
    for path in assets:
        lines.extend(
            (
                "",
                "[[assets]]",
                'kind = "module_source"',
                f'path = "{path}"',
            )
        )
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


def _digest(
    manifest: bytes,
    assets: tuple[tuple[str, bytes], ...],
) -> str:
    stream = bytearray(b"pietto-package-content-v1\0")
    for path, content in (("pietto-package.toml", manifest), *assets):
        path_bytes = path.encode()
        stream.extend(struct.pack(">Q", len(path_bytes)))
        stream.extend(path_bytes)
        stream.extend(struct.pack(">Q", len(content)))
        stream.extend(content)
    return hashlib.sha256(stream).hexdigest()
