from __future__ import annotations

from pathlib import Path


from pietto._project.model import ProjectRootPackageActivation
from pietto._project.package_loader import (
    LoadedRootPackage,
    _compute_package_content_sha256,
    _load_root_package,
)
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.package_manifest import (
    _normalize_package_manifest,
)
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = b"shape Row:\n    id: Int\n"


def _requirement(
    domain: str = "extension_signature",
    *,
    operation: str = "distance",
    dialect: str | None = "postgresql",
    extension: str | None = "vector",
) -> str:
    lines = [
        "[[capability_requirements.entries]]",
        f'domain = "{domain}"',
        f'operation = "{operation}"',
        'operands = ["left", "right"]',
    ]
    if dialect is not None:
        lines.append(f'dialect = "{dialect}"')
    if extension is not None:
        lines.append(f'extension = "{extension}"')
    return "\n".join(lines)


def _type(kind: str, physical_name: str) -> tuple[str, str]:
    return kind, physical_name


def _selector(
    position: int,
    family: str,
    *,
    physical_name: str = "vector",
    sql_name: str = "distance",
    arity: str = "binary",
    input_types: tuple[tuple[str, str], ...] = (),
    operand_types: tuple[tuple[str, str], ...] = (),
    source_type: tuple[str, str] = ("postgres_builtin", "text"),
    target_type: tuple[str, str] = ("extension_native", "vector"),
) -> str:
    lines = [
        "[[extension_signature_selectors]]",
        f"requirement_position = {position}",
        f'family = "{family}"',
    ]
    if family == "native_type":
        lines.append(f'physical_name = "{physical_name}"')
    elif family in {"scalar_function", "aggregate"}:
        lines.append(f'sql_name = "{sql_name}"')
        for kind, name in input_types:
            lines.extend(
                (
                    "",
                    "[[extension_signature_selectors.input_types]]",
                    f'kind = "{kind}"',
                    f'physical_name = "{name}"',
                )
            )
    elif family == "operator":
        lines.extend((f'operator_name = "{sql_name}"', f'arity = "{arity}"'))
        for kind, name in operand_types:
            lines.extend(
                (
                    "",
                    "[[extension_signature_selectors.operand_types]]",
                    f'kind = "{kind}"',
                    f'physical_name = "{name}"',
                )
            )
    elif family == "cast":
        lines.extend(
            (
                "",
                "[extension_signature_selectors.source_type]",
                f'kind = "{source_type[0]}"',
                f'physical_name = "{source_type[1]}"',
                "",
                "[extension_signature_selectors.target_type]",
                f'kind = "{target_type[0]}"',
                f'physical_name = "{target_type[1]}"',
            )
        )
    return "\n".join(lines)


def _manifest(
    *,
    schema_version: int = 3,
    requirements: tuple[str, ...] | None = None,
    selectors: tuple[str, ...] = (),
) -> bytes:
    lines = [
        f"schema_version = {schema_version}",
        'namespace = "example"',
        'name = "root"',
        'version = "1.0.0"',
        "",
        "[[assets]]",
        'kind = "module_source"',
        'path = "main.pietto"',
    ]
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


def _normalize(manifest: bytes):
    return _normalize_package_manifest(
        ProjectRootPackageActivation(".", "example", "root", "1.0.0", "a" * 64),
        manifest,
    )


def _write_package(root: Path, name: str, manifest: bytes) -> tuple[Path, str]:
    package_root = root / name
    package_root.mkdir(parents=True)
    (package_root / "pietto-package.toml").write_bytes(manifest)
    (package_root / "main.pietto").write_bytes(SOURCE)
    return package_root, _compute_package_content_sha256(
        manifest,
        (("main.pietto", SOURCE),),
    )


def _load(root: Path, package_path: str, digest: str) -> LoadedRootPackage:
    pinned = _pin_project_root(root)
    assert type(pinned) is ProjectPinnedRoot
    located = _locate_root_package(
        pinned,
        ProjectRootPackageActivation(
            package_path,
            "example",
            "root",
            "1.0.0",
            digest,
        ),
    )
    assert located.ok and type(located.located_root) is LocatedRootPackage
    loaded = _load_root_package(located.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    return loaded.loaded_package
