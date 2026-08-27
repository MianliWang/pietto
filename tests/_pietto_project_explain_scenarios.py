"""Mechanical real-input and CLI helpers for Project Explain assurance tests."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys

from pietto._project.package_loader import _compute_package_content_sha256


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
ROOT_SELECTOR = '''[[extension_signature_selectors]]
requirement_position = 0
family = "native_type"
physical_name = "halfvec"'''
UNSUPPORTED_REQUIREMENT = """[[capability_requirements.entries]]
domain = "logical_type"
subject = "UnsupportedType"
operands = []"""
ABSENT_REQUIREMENT = '''[[capability_requirements.entries]]
domain = "logical_type"
subject = "AbsentType"
operation = "catalog_membership"
operands = []
context = "builtin_registry"'''
CONFLICT_REQUIREMENT = """[[capability_requirements.entries]]
domain = "logical_type"
subject = "ConflictType"
operands = []"""

_CLI_PAIR_CODE = r"""
import base64
import io
import json
import sys
from pietto.cli import main

class Capture:
    encoding = "utf-8"

    def __init__(self):
        self.buffer = io.BytesIO()

    def write(self, value):
        self.buffer.write(value.encode(self.encoding))
        return len(value)

    def flush(self):
        pass

    def isatty(self):
        return False

def run(arguments):
    stdout = Capture()
    stderr = Capture()
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    try:
        sys.stdout = stdout
        sys.stderr = stderr
        try:
            returncode = main(arguments)
        except SystemExit as error:
            returncode = error.code
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
    assert type(returncode) is int
    return [
        returncode,
        base64.b64encode(stdout.buffer.getvalue()).decode("ascii"),
        base64.b64encode(stderr.buffer.getvalue()).decode("ascii"),
    ]

commands = json.loads(sys.argv[1])
assert type(commands) is list and len(commands) == 2
sys.stdout.write(json.dumps([run(command) for command in commands], separators=(",", ":")))
"""


def _run_cli_pair(
    first: tuple[str, ...],
    second: tuple[str, ...],
    cwd: Path,
) -> tuple[subprocess.CompletedProcess[bytes], subprocess.CompletedProcess[bytes]]:
    commands = (first, second)
    completed = subprocess.run(
        (
            sys.executable,
            "-c",
            _CLI_PAIR_CODE,
            json.dumps(commands, separators=(",", ":")),
        ),
        check=True,
        capture_output=True,
        cwd=cwd,
        env=os.environ.copy(),
    )
    assert completed.stderr == b""
    payload = json.loads(completed.stdout)
    assert type(payload) is list and len(payload) == len(commands)
    results = []
    for arguments, item in zip(commands, payload, strict=True):
        assert (
            type(item) is list
            and len(item) == 3
            and type(item[0]) is int
            and type(item[1]) is str
            and type(item[2]) is str
        )
        results.append(
            subprocess.CompletedProcess(
                arguments,
                item[0],
                base64.b64decode(item[1]),
                base64.b64decode(item[2]),
            )
        )
    return results[0], results[1]


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


def _write_package(path: Path, manifest: bytes, source: bytes = SOURCE) -> str:
    path.mkdir(parents=True)
    (path / "pietto-package.toml").write_bytes(manifest)
    (path / "main.pietto").write_bytes(source)
    return _compute_package_content_sha256(manifest, (("main.pietto", source),))


def _fact(
    support: str,
    domain: str,
    *,
    subject: str | None = None,
    operation: str | None = None,
    context: str | None = None,
    dialect: str | None = None,
    extension: str | None = None,
) -> str:
    lines = [
        "[[capability_environment.profiles.facts]]",
        f'support = "{support}"',
        f'domain = "{domain}"',
    ]
    for key, value in (
        ("subject", subject),
        ("operation", operation),
        ("context", context),
        ("dialect", dialect),
        ("extension", extension),
    ):
        if value is not None:
            lines.append(f'{key} = "{value}"')
    lines.append("operands = []")
    return "\n".join(lines)


def _profile(
    name: str,
    database_release: str,
    *,
    kind: str = "base",
    facts: tuple[str, ...] = (),
    extension_identity: str = "vector",
    extension_release: str = "0.8.6",
    base_name: str = "base",
) -> str:
    lines = [
        "[[capability_environment.profiles]]",
        'namespace = "profiles"',
        f'name = "{name}"',
        'release = "r1"',
        f'kind = "{kind}"',
        'database_family = "PostgreSQL"',
        f'database_release = "{database_release}"',
    ]
    if kind == "overlay":
        lines.extend(
            (
                f'extension_identity = "{extension_identity}"',
                f'extension_release = "{extension_release}"',
                'base_namespace = "profiles"',
                f'base_name = "{base_name}"',
                'base_release = "r1"',
            )
        )
    for fact in facts:
        lines.extend(("", fact))
    return "\n".join(lines)


def _target(base_name: str, database_release: str, overlay_name: str | None) -> str:
    lines = [
        "[[capability_environment.targets]]",
        'database_family = "PostgreSQL"',
        f'database_release = "{database_release}"',
        'base_profile_namespace = "profiles"',
        f'base_profile_name = "{base_name}"',
        'base_profile_release = "r1"',
    ]
    if overlay_name is not None:
        lines.extend(
            (
                "",
                "[[capability_environment.targets.overlays]]",
                'namespace = "profiles"',
                f'name = "{overlay_name}"',
                'release = "r1"',
            )
        )
    return "\n".join(lines)


def _project_config(
    package_path: str,
    digest: str,
    *,
    profiles: tuple[str, ...] = (),
    targets: tuple[str, ...] = (),
    environment_entries: tuple[str, ...] = (),
) -> str:
    return "\n".join(
        (
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
            *environment_entries,
            *(part for section in (*profiles, *targets) for part in ("", section)),
            "",
        )
    )


def _write_single_project(
    workspace: Path,
    manifest: bytes,
    *,
    profiles: tuple[str, ...] = (),
    targets: tuple[str, ...] = (),
    environment_entries: tuple[str, ...] = (),
    name: str,
) -> Path:
    root = workspace / name
    digest = _write_package(root / "package", manifest)
    (root / "pietto.toml").write_text(
        _project_config(
            "package",
            digest,
            profiles=profiles,
            targets=targets,
            environment_entries=environment_entries,
        ),
        encoding="utf-8",
    )
    return root


def _multi_package_multi_target_project(workspace: Path, name: str) -> Path:
    root = workspace / name
    dependency_manifest = _manifest(
        3,
        namespace="example",
        name="dependency",
        requirements=(EXTENSION_REQUIREMENT,),
        selectors=(EXTENSION_SELECTOR,),
    )
    dependency_digest = _write_package(root / "dependency", dependency_manifest)
    root_manifest = _manifest(
        3,
        requirements=(
            EXTENSION_REQUIREMENT,
            UNSUPPORTED_REQUIREMENT,
            ABSENT_REQUIREMENT,
            CONFLICT_REQUIREMENT,
        ),
        selectors=(ROOT_SELECTOR,),
        dependencies=(
            ("example", "dependency", "1.0.0", dependency_digest, "../dependency"),
        ),
    )
    root_digest = _write_package(root / "root", root_manifest)
    extension_fact = _fact(
        "supported",
        "extension_signature",
        operation="vector-native-type",
        dialect="postgresql",
        extension="vector",
    )
    absent_fact = _fact(
        "supported",
        "logical_type",
        subject="AbsentType",
        operation="catalog_membership",
        context="builtin_registry",
    )
    profiles = (
        _profile(
            "base18",
            "18",
            facts=(
                _fact(
                    "explicitly_unsupported",
                    "logical_type",
                    subject="UnsupportedType",
                ),
                absent_fact,
                _fact("supported", "logical_type", subject="ConflictType"),
                _fact(
                    "explicitly_unsupported",
                    "logical_type",
                    subject="ConflictType",
                ),
            ),
        ),
        _profile(
            "vector18",
            "18",
            kind="overlay",
            facts=(extension_fact,),
            base_name="base18",
        ),
        _profile("base17", "17", facts=(absent_fact,)),
        _profile(
            "vector17",
            "17",
            kind="overlay",
            facts=(extension_fact,),
            base_name="base17",
        ),
    )
    targets = (
        _target("base18", "18", "vector18"),
        _target("base17", "17", "vector17"),
    )
    (root / "pietto.toml").write_text(
        _project_config("root", root_digest, profiles=profiles, targets=targets),
        encoding="utf-8",
    )
    return root
