from __future__ import annotations

import hashlib
from pathlib import Path
import struct

from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,  # noqa: F401
    ProjectRootPackageActivation,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    _build_package_inspection_fact_set,
)
from pietto._project.package_load_plan import (
    PackageLoadPlanResult,
    _build_package_load_plan,
)
from pietto._project.package_loader import LoadedRootPackage, _load_root_package
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root


_SOURCE_A = b"shape Row:\n    id: Int\n"
_SOURCE_B = b"shape Row:\n    value: Text\n"


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
