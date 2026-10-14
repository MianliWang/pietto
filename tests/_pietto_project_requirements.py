from __future__ import annotations

from pathlib import Path

from pietto._project.package_loader import _compute_package_content_sha256

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = b"shape Row:\n    id: Int\n"
DOMAIN_VALUES = (
    "logical_type",
    "literal",
    "parameter",
    "scalar_function",
    "unary_operator",
    "binary_operator",
    "comparison",
    "null_test",
    "clause",
    "aggregate",
    "window_function",
    "expression_stage",
    "conversion",
    "dialect_lowering",
    "extension_signature",
)


def _entry(
    domain: str,
    *,
    subject: str | None = None,
    operation: str | None = None,
    operands: tuple[str, ...] = (),
    context: str | None = None,
    dialect: str | None = None,
    extension: str | None = None,
) -> str:
    lines = [f'domain = "{domain}"']
    for field_name, value in (
        ("subject", subject),
        ("operation", operation),
    ):
        if value is not None:
            lines.append(f'{field_name} = "{value}"')
    lines.append("operands = [" + ", ".join(f'"{value}"' for value in operands) + "]")
    for field_name, value in (
        ("context", context),
        ("dialect", dialect),
        ("extension", extension),
    ):
        if value is not None:
            lines.append(f'{field_name} = "{value}"')
    return "\n".join(lines)


def _declaration(
    *entries: str,
    root_body: tuple[str, ...] = (),
) -> str:
    lines = [
        "[capability_requirements]",
        'namespace = "exact.requirements"',
        'name = "runtime"',
        *root_body,
    ]
    for entry in entries:
        lines.extend(("", "[[capability_requirements.entries]]", entry))
    return "\n".join(lines)


def _manifest(
    *,
    schema_version: int = 2,
    name: str = "root",
    declaration: str = "",
    root_extra: tuple[str, ...] = (),
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> bytes:
    lines = [
        f"schema_version = {schema_version}",
        'namespace = "example"',
        f'name = "{name}"',
        'version = "1.0.0"',
        *root_extra,
        "",
        "[[assets]]",
        'kind = "module_source"',
        'path = "main.pietto"',
    ]
    for namespace, dep_name, version, sha256, path in dependencies:
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f'namespace = "{namespace}"',
                f'name = "{dep_name}"',
                f'version = "{version}"',
                f'sha256 = "{sha256}"',
                f'path = "{path}"',
            )
        )
    if declaration:
        lines.extend(("", declaration))
    return ("\n".join(lines) + "\n").encode()


def _write_package(
    project: Path,
    package_path: str,
    *,
    schema_version: int = 2,
    name: str = "root",
    declaration: str = "",
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> str:
    package_root = project / package_path
    package_root.mkdir(parents=True)
    manifest = _manifest(
        schema_version=schema_version,
        name=name,
        declaration=declaration,
        dependencies=dependencies,
    )
    (package_root / "pietto-package.toml").write_bytes(manifest)
    (package_root / "main.pietto").write_bytes(SOURCE)
    return _compute_package_content_sha256(manifest, (("main.pietto", SOURCE),))
