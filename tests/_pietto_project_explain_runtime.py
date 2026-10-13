from __future__ import annotations

from pathlib import Path


from pietto._project.config import load_project_config
from pietto._project.package_loader import (
    LoadedRootPackage,
    _compute_package_content_sha256,
    _load_root_package,
)
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = b"shape Row:\n    id: Int\n"
EXTENSION_REQUIREMENT = '''[[capability_requirements.entries]]
domain = "extension_signature"
operation = "vector-native-type"
operands = []
dialect = "postgresql"
extension = "vector"'''
EXTENSION_SELECTOR = '''[[extension_signature_selectors]]
requirement_position = 0
family = "native_type"
physical_name = "vector"'''
LOGICAL_REQUIREMENT = """[[capability_requirements.entries]]
domain = "logical_type"
subject = "Int"
operands = []"""


def _manifest(
    schema_version: int,
    *,
    namespace: str = "example",
    name: str = "root",
    requirements: tuple[str, ...] | None = None,
    selectors: tuple[str, ...] = (),
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> bytes:
    lines = [
        f"schema_version = {schema_version}",
        f'namespace = "{namespace}"',
        f'name = "{name}"',
        'version = "1.0.0"',
        "",
        "[[assets]]",
        'kind = "module_source"',
        'path = "main.pietto"',
    ]
    for dep_namespace, dep_name, release, digest, path in dependencies:
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f'namespace = "{dep_namespace}"',
                f'name = "{dep_name}"',
                f'version = "{release}"',
                f'sha256 = "{digest}"',
                f'path = "{path}"',
            )
        )
    if requirements is not None:
        lines.extend(
            (
                "",
                "[capability_requirements]",
                'namespace = "requirements"',
                'name = "runtime"',
            )
        )
        for requirement in requirements:
            lines.extend(("", requirement))
    for selector in selectors:
        lines.extend(("", selector))
    return ("\n".join(lines) + "\n").encode()


def _project_config(
    package_path: str,
    digest: str,
    *,
    targets: bool,
    vector_overlay: bool = True,
) -> str:
    lines = [
        "schema_version = 4",
        "",
        "[package]",
        f'path = "{package_path}"',
        'namespace = "example"',
        'name = "root"',
        'version = "1.0.0"',
        f'sha256 = "{digest}"',
        "",
        "[capability_environment]",
    ]
    if not targets:
        return "\n".join(lines) + "\n"
    lines.extend(
        (
            "",
            "[[capability_environment.profiles]]",
            'namespace = "profiles"',
            'name = "base"',
            'release = "r1"',
            'kind = "base"',
            'database_family = "PostgreSQL"',
            'database_release = "18"',
        )
    )
    if vector_overlay:
        lines.extend(
            (
                "",
                "[[capability_environment.profiles]]",
                'namespace = "profiles"',
                'name = "vector"',
                'release = "r1"',
                'kind = "overlay"',
                'database_family = "PostgreSQL"',
                'database_release = "18"',
                'extension_identity = "vector"',
                'extension_release = "0.8.6"',
                'base_namespace = "profiles"',
                'base_name = "base"',
                'base_release = "r1"',
                "",
                "[[capability_environment.profiles.facts]]",
                'support = "supported"',
                'domain = "extension_signature"',
                'operation = "vector-native-type"',
                "operands = []",
                'dialect = "postgresql"',
                'extension = "vector"',
            )
        )
    lines.extend(
        (
            "",
            "[[capability_environment.targets]]",
            'database_family = "PostgreSQL"',
            'database_release = "18"',
            'base_profile_namespace = "profiles"',
            'base_profile_name = "base"',
            'base_profile_release = "r1"',
        )
    )
    if vector_overlay:
        lines.extend(
            (
                "",
                "[[capability_environment.targets.overlays]]",
                'namespace = "profiles"',
                'name = "vector"',
                'release = "r1"',
            )
        )
    return "\n".join(lines) + "\n"


def _write_package(path: Path, manifest: bytes, source: bytes = SOURCE) -> str:
    path.mkdir(parents=True)
    (path / "pietto-package.toml").write_bytes(manifest)
    (path / "main.pietto").write_bytes(source)
    return _compute_package_content_sha256(manifest, (("main.pietto", source),))


def _write_project(
    tmp_path: Path,
    manifest: bytes,
    *,
    targets: bool,
    vector_overlay: bool = True,
    source: bytes = SOURCE,
    name: str = "project",
) -> Path:
    root = tmp_path / name
    package_path = root / "package"
    digest = _write_package(package_path, manifest, source)
    root.mkdir(exist_ok=True)
    (root / "pietto.toml").write_text(
        _project_config(
            "package",
            digest,
            targets=targets,
            vector_overlay=vector_overlay,
        ),
        encoding="utf-8",
    )
    return root


def _loaded_root(root: Path) -> LoadedRootPackage:
    config_result = load_project_config(root)
    assert config_result.ok and config_result.config is not None
    assert config_result.pinned_root is not None
    activation = config_result.config.root_package
    assert activation is not None
    located = _locate_root_package(config_result.pinned_root, activation)
    assert located.ok and type(located.located_root) is LocatedRootPackage
    loaded = _load_root_package(located.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    return loaded.loaded_package


def _schema3_extension_manifest() -> bytes:
    return _manifest(
        3,
        requirements=(EXTENSION_REQUIREMENT,),
        selectors=(EXTENSION_SELECTOR,),
    )
