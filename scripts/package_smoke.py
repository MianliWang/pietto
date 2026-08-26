"""Build, inspect, install, and smoke test Pietto release artifacts."""

from __future__ import annotations

import configparser
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CHECK_INPUT = Path("examples/basic/types.pietto")
POSTGRES_INPUT = Path("tests/fixtures/postgres/compatibility_ordering_metadata.pietto")
POSTGRES_GOLDEN = Path(
    "tests/fixtures/golden/emit_sql_compatibility_ordering_metadata.sql"
)
MYSQL_INPUT = Path("tests/fixtures/mysql/compatibility_ordering_metadata.pietto")
MYSQL_GOLDEN = Path(
    "tests/fixtures/golden/emit_mysql_compatibility_ordering_metadata.json"
)

GENERATED_FILES = frozenset(
    {
        "Pietto.interp",
        "Pietto.tokens",
        "PiettoLexer.interp",
        "PiettoLexer.py",
        "PiettoLexer.tokens",
        "PiettoParser.py",
        "PiettoVisitor.py",
        "__init__.py",
    }
)


@dataclass(frozen=True)
class ProjectContract:
    """Packaging values declared by the current project metadata."""

    name: str
    version: str
    requires_python: str
    dependencies: tuple[str, ...]
    console_entry: str
    readme: str | None


class SmokeFailure(Exception):
    """A packaging smoke failure with a process-compatible exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _project_contract() -> ProjectContract:
    try:
        document = tomllib.loads(
            (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        project = document["project"]
        scripts = project["scripts"]
        return ProjectContract(
            name=project["name"],
            version=project["version"],
            requires_python=project["requires-python"],
            dependencies=tuple(project.get("dependencies", ())),
            console_entry=scripts["pietto"],
            readme=project.get("readme"),
        )
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise SmokeFailure(f"cannot read packaging contract: {error}") from error


def _run_command(
    stage: str,
    command: tuple[str, ...],
    *,
    cwd: Path,
    capture_output: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    print(f"[package-smoke] {stage}: {shlex.join(command)}", flush=True)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=capture_output,
            env=env,
        )
    except OSError as error:
        raise SmokeFailure(f"{stage} could not start: {error}") from error

    if result.returncode == 0:
        return result

    if capture_output:
        if result.stdout:
            print(result.stdout.decode("utf-8", errors="replace"), end="")
        if result.stderr:
            print(
                result.stderr.decode("utf-8", errors="replace"),
                end="",
                file=sys.stderr,
            )
    raise SmokeFailure(
        f"{stage} failed with exit code {result.returncode}",
        result.returncode,
    )


def _find_artifacts(dist_dir: Path) -> tuple[Path, Path]:
    sdists = tuple(sorted(dist_dir.glob("*.tar.gz")))
    wheels = tuple(sorted(dist_dir.glob("*.whl")))
    if len(sdists) != 1 or len(wheels) != 1:
        raise SmokeFailure(
            "build must produce exactly one sdist and one wheel; "
            f"found {len(sdists)} sdist and {len(wheels)} wheel files"
        )
    return sdists[0], wheels[0]


def _required_runtime_files(prefix: str) -> frozenset[str]:
    required = {
        f"{prefix}/__init__.py",
        f"{prefix}/cli.py",
        f"{prefix}/parser_api.py",
        f"{prefix}/_project_explain/__init__.py",
        f"{prefix}/_project_explain/compatibility_matrix_projection.py",
        f"{prefix}/_project_explain/composition.py",
        f"{prefix}/_project_explain/extension_catalog_evidence_projection.py",
        f"{prefix}/_project_explain/json_v1.py",
        f"{prefix}/_project_explain/model.py",
        f"{prefix}/_project_explain/package_requirement_projection.py",
        f"{prefix}/_project_explain/portability_projection.py",
        f"{prefix}/_project_explain/runtime_builder.py",
        f"{prefix}/_project_explain/text.py",
        f"{prefix}/_project/package_capability_requirements.py",
        f"{prefix}/_project/package_extension_signature_selectors.py",
        f"{prefix}/_project/package_graph.py",
        f"{prefix}/_project/project_capability_environment.py",
        f"{prefix}/_project/extension_catalog_availability.py",
        f"{prefix}/_project/extension_catalog_inspection.py",
        f"{prefix}/_project/extension_catalog_inspection_pure_boundary.py",
        f"{prefix}/_project/extension_signature_provider.py",
        f"{prefix}/semantic/__init__.py",
        f"{prefix}/semantic/extension_catalog.py",
        f"{prefix}/semantic/extension_catalog_pure_boundary.py",
        f"{prefix}/semantic/extension_catalog_pg_trgm.py",
        f"{prefix}/semantic/extension_catalog_pgvector.py",
        f"{prefix}/semantic/extension_signature_requirements.py",
        f"{prefix}/ir/__init__.py",
        f"{prefix}/sql/postgres.py",
        f"{prefix}/sql/mysql.py",
    }
    required.update(f"{prefix}/generated/{name}" for name in GENERATED_FILES)
    return frozenset(required)


def _missing_files(inventory: set[str], required: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(required - inventory))


def _validate_core_metadata(metadata_bytes: bytes, contract: ProjectContract) -> None:
    metadata = BytesParser(policy=policy.default).parsebytes(metadata_bytes)
    expected = {
        "Name": contract.name,
        "Version": contract.version,
        "Requires-Python": contract.requires_python,
    }
    for field, value in expected.items():
        if metadata.get(field) != value:
            raise SmokeFailure(
                f"artifact metadata {field} is {metadata.get(field)!r}, "
                f"expected {value!r}"
            )

    declared_dependencies = tuple(metadata.get_all("Requires-Dist", ()))
    for dependency in contract.dependencies:
        if dependency not in declared_dependencies:
            raise SmokeFailure(
                f"artifact metadata is missing runtime dependency {dependency!r}"
            )

    if contract.readme is not None:
        if metadata.get("Description-Content-Type") != "text/markdown":
            raise SmokeFailure("artifact metadata is missing Markdown README metadata")
        payload = metadata.get_payload()
        if not isinstance(payload, str) or "# Pietto" not in payload:
            raise SmokeFailure("artifact metadata is missing the declared README body")


def _inspect_wheel(wheel: Path, contract: ProjectContract) -> None:
    dist_info = f"{contract.name.replace('-', '_')}-{contract.version}.dist-info"
    metadata_path = f"{dist_info}/METADATA"
    entry_points_path = f"{dist_info}/entry_points.txt"

    try:
        with zipfile.ZipFile(wheel) as archive:
            inventory = set(archive.namelist())
            required = _required_runtime_files(contract.name) | frozenset(
                {metadata_path, entry_points_path, f"{dist_info}/WHEEL"}
            )
            missing = _missing_files(inventory, required)
            if missing:
                raise SmokeFailure(
                    f"wheel is missing required files: {', '.join(missing)}"
                )
            metadata_bytes = archive.read(metadata_path)
            entry_points_text = archive.read(entry_points_path).decode("utf-8")
    except (OSError, UnicodeError, zipfile.BadZipFile, KeyError) as error:
        raise SmokeFailure(f"cannot inspect wheel {wheel.name}: {error}") from error

    _validate_core_metadata(metadata_bytes, contract)
    parser = configparser.ConfigParser()
    try:
        parser.read_string(entry_points_text)
    except configparser.Error as error:
        raise SmokeFailure(f"invalid console entry point metadata: {error}") from error
    if parser.get("console_scripts", "pietto", fallback=None) != contract.console_entry:
        raise SmokeFailure(
            "wheel console entry point does not match "
            f"pietto = {contract.console_entry}"
        )


def _read_tar_member(archive: tarfile.TarFile, name: str) -> bytes:
    member = archive.extractfile(name)
    if member is None:
        raise SmokeFailure(f"sdist member is not a regular file: {name}")
    return member.read()


def _inspect_sdist(sdist: Path, contract: ProjectContract) -> None:
    prefix = f"{contract.name}-{contract.version}"
    metadata_path = f"{prefix}/PKG-INFO"
    required = _required_runtime_files(f"{prefix}/src/{contract.name}") | frozenset(
        {
            metadata_path,
            f"{prefix}/pyproject.toml",
        }
    )
    if contract.readme is not None:
        required |= frozenset({f"{prefix}/{contract.readme}"})

    try:
        with tarfile.open(sdist, mode="r:gz") as archive:
            inventory = set(archive.getnames())
            missing = _missing_files(inventory, required)
            if missing:
                raise SmokeFailure(
                    f"sdist is missing required files: {', '.join(missing)}"
                )
            metadata_bytes = _read_tar_member(archive, metadata_path)
    except (OSError, tarfile.TarError, KeyError) as error:
        raise SmokeFailure(f"cannot inspect sdist {sdist.name}: {error}") from error

    _validate_core_metadata(metadata_bytes, contract)


def _venv_python(venv_dir: Path) -> Path:
    executable = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    return venv_dir / executable


def _venv_cli(venv_dir: Path) -> Path:
    executable = Path("Scripts/pietto.exe") if os.name == "nt" else Path("bin/pietto")
    return venv_dir / executable


def _clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _copy_smoke_inputs(scratch_dir: Path) -> None:
    for relative_path in (CHECK_INPUT, POSTGRES_INPUT, MYSQL_INPUT):
        destination = scratch_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative_path, destination)


def _run_installed_cli(
    cli_path: Path,
    arguments: tuple[str, ...],
    *,
    scratch_dir: Path,
    stage: str,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[bytes]:
    return _run_command(
        stage,
        (str(cli_path), *arguments),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )


def _smoke_installed_cli(
    venv_dir: Path,
    scratch_dir: Path,
    contract: ProjectContract,
) -> None:
    try:
        scratch_dir.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        raise SmokeFailure("installed CLI scratch directory must be outside repository")

    cli_path = _venv_cli(venv_dir)
    if not cli_path.is_file():
        raise SmokeFailure(f"installed console script is missing: {cli_path}")

    _copy_smoke_inputs(scratch_dir)
    environment = _clean_environment()

    _run_command(
        "installed private Phase 59 package graph import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.package_graph",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain JSON v1 import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.json_v1",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain composition import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.composition",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain portability projection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.portability_projection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain extension catalog evidence projection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.extension_catalog_evidence_projection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain compatibility matrix projection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.compatibility_matrix_projection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain package requirement projection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.package_requirement_projection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain model import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            (
                "import pietto._project_explain.model as project_explain_model; "
                "assert project_explain_model.PROJECT_EXPLAIN_ARTIFACT_NAME "
                "== 'Project Explain Artifact v1'; "
                "assert project_explain_model.ProjectExplainFormat."
                "PROJECT_EXPLAIN_V1.value == 'pietto.project-explain.v1'"
            ),
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto.semantic.extension_catalog",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog availability import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.extension_catalog_availability",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog inspection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.extension_catalog_inspection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog inspection pure evaluation",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            (
                "from pietto._project.extension_catalog_inspection_pure_boundary "
                "import ExtensionCatalogInspectionPureDocument, "
                "ExtensionCatalogInspectionPureStatus, "
                "evaluate_extension_catalog_inspection_document, "
                "extension_catalog_inspection_pure_enumeration as e, "
                "extension_catalog_inspection_pure_text as s, "
                "extension_catalog_inspection_pure_tuple as t; "
                "assert evaluate_extension_catalog_inspection_document("
                "ExtensionCatalogInspectionPureDocument(root=t("
                "s('extension_catalog_inspection'), "
                "e('ExtensionCatalogInspectionFormat', "
                "'pietto.extension-catalog-inspection.v1'), "
                "s('consumer'), s('installed'), t(), t()))).status "
                "is ExtensionCatalogInspectionPureStatus.OK"
            ),
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog pure evaluation",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            (
                "from pietto.semantic.extension_catalog_pure_boundary "
                "import ExtensionCatalogPureDocument, ExtensionCatalogPureStatus, "
                "evaluate_extension_catalog_document; "
                "assert evaluate_extension_catalog_document("
                "ExtensionCatalogPureDocument(root=None)).status "
                "is ExtensionCatalogPureStatus.MISSING_ROOT"
            ),
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private pgvector extension catalog import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto.semantic.extension_catalog_pgvector",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private pg_trgm extension catalog import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto.semantic.extension_catalog_pg_trgm",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension signature provider import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.extension_signature_provider",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension signature requirements import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto.semantic.extension_signature_requirements",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private package capability requirements import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.package_capability_requirements",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project capability environment import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.project_capability_environment",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private package extension signature selectors import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.package_extension_signature_selectors",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain runtime builder import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.runtime_builder",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain text import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.text",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )

    version = _run_installed_cli(
        cli_path,
        ("--version",),
        scratch_dir=scratch_dir,
        stage="installed CLI version",
        environment=environment,
    )
    expected_version = f"pietto {contract.version}\n".encode()
    if version.stdout != expected_version or version.stderr:
        raise SmokeFailure("installed CLI --version output is unexpected")

    help_result = _run_installed_cli(
        cli_path,
        ("--help",),
        scratch_dir=scratch_dir,
        stage="installed CLI help",
        environment=environment,
    )
    for marker in (b"usage: pietto", b"check", b"emit-sql", b"explain"):
        if marker not in help_result.stdout:
            raise SmokeFailure(f"installed CLI --help is missing {marker!r}")
    if help_result.stderr:
        raise SmokeFailure("installed CLI --help wrote unexpected stderr")

    _run_installed_cli(
        cli_path,
        ("check", CHECK_INPUT.as_posix()),
        scratch_dir=scratch_dir,
        stage="installed CLI check",
        environment=environment,
    )

    project_root = scratch_dir / "project-check"
    project_root.mkdir()
    project_models = project_root / "models"
    project_models.mkdir()
    (project_root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models/*.pietto"]\n',
        encoding="utf-8",
    )
    (project_models / "user.pietto").write_text(
        "shape User:\n    id: Int\n",
        encoding="utf-8",
    )

    project_check_text = _run_installed_cli(
        cli_path,
        ("check", "--project", project_root.as_posix()),
        scratch_dir=scratch_dir,
        stage="installed CLI project check text",
        environment=environment,
    )
    if project_check_text.stdout != b"Project check OK: .\nFiles checked: 1\n":
        raise SmokeFailure("installed CLI project check text output is unexpected")
    if project_check_text.stderr:
        raise SmokeFailure("installed CLI project check text wrote unexpected stderr")

    project_check_json = _run_installed_cli(
        cli_path,
        ("check", "--project", project_root.as_posix(), "--format", "json"),
        scratch_dir=scratch_dir,
        stage="installed CLI project check JSON v2",
        environment=environment,
    )
    try:
        project_check_document = json.loads(project_check_json.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"cannot decode project check JSON v2: {error}") from error
    if project_check_document != {
        "schema_version": 2,
        "command": "check",
        "mode": "project",
        "ok": True,
        "project": {
            "root": ".",
            "config_path": "pietto.toml",
        },
        "inputs": [
            {
                "path": "models/user.pietto",
                "kind": "source",
                "status": "parsed",
            }
        ],
        "diagnostics": [],
        "cli_errors": [],
        "result": {
            "check": {
                "files_total": 1,
                "files_ok": 1,
                "files_with_errors": 0,
            }
        },
    }:
        raise SmokeFailure("installed CLI project check JSON v2 envelope is unexpected")
    if project_check_json.stderr:
        raise SmokeFailure(
            "installed CLI project check JSON v2 wrote unexpected stderr"
        )

    project_explain_root = scratch_dir / "project-explain"
    project_explain_package = project_explain_root / "package"
    project_explain_package.mkdir(parents=True)
    project_explain_manifest = (
        b'schema_version = 1\nnamespace = "example"\nname = "root"\n'
        b'version = "1.0.0"\n\n[[assets]]\nkind = "module_source"\n'
        b'path = "main.pietto"\n'
    )
    project_explain_source = b"shape Row:\n    id: Int not null\n"
    (project_explain_package / "pietto-package.toml").write_bytes(
        project_explain_manifest
    )
    (project_explain_package / "main.pietto").write_bytes(project_explain_source)
    digest_result = _run_command(
        "installed project explain package digest",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "from pietto._project.package_loader import "
            "_compute_package_content_sha256 as compute; "
            f"print(compute({project_explain_manifest!r}, "
            f"(('main.pietto', {project_explain_source!r}),)))",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    project_explain_digest = digest_result.stdout.decode("ascii").strip()
    (project_explain_root / "pietto.toml").write_text(
        'schema_version = 4\n\n[package]\npath = "package"\n'
        'namespace = "example"\nname = "root"\nversion = "1.0.0"\n'
        f'sha256 = "{project_explain_digest}"\n\n[capability_environment]\n',
        encoding="utf-8",
    )
    project_explain_text = _run_installed_cli(
        cli_path,
        ("explain", "--project", project_explain_root.as_posix()),
        scratch_dir=scratch_dir,
        stage="installed CLI project explain text",
        environment=environment,
    )
    for marker in (
        b"Project Explain Artifact v1\n",
        b"Targets (0)\n    none\n",
        b"project: indeterminate reason=no-evaluated-targets requirements=0\n",
    ):
        if marker not in project_explain_text.stdout:
            raise SmokeFailure(
                f"installed CLI project explain text is missing {marker!r}"
            )
    if project_explain_text.stderr:
        raise SmokeFailure("installed CLI project explain text wrote unexpected stderr")

    project_explain_json = _run_installed_cli(
        cli_path,
        (
            "explain",
            "--project",
            project_explain_root.as_posix(),
            "--format",
            "json",
        ),
        scratch_dir=scratch_dir,
        stage="installed CLI project explain JSON v1",
        environment=environment,
    )
    try:
        project_explain_document = json.loads(project_explain_json.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"cannot decode Project Explain JSON v1: {error}") from error
    if tuple(project_explain_document) != (
        "format",
        "ok",
        "diagnostics",
        "payload",
    ):
        raise SmokeFailure("installed Project Explain JSON field order is unexpected")
    payload = project_explain_document.get("payload")
    if (
        project_explain_document.get("format") != "pietto.project-explain.v1"
        or project_explain_document.get("ok") is not True
        or not isinstance(payload, dict)
        or payload.get("compatibility", {}).get("targets") != []
        or {"outcome", "exit_code"} & project_explain_document.keys()
    ):
        raise SmokeFailure("installed Project Explain JSON v1 envelope is unexpected")
    if (
        project_explain_json.stderr
        or not project_explain_json.stdout.endswith(b"\n")
        or project_explain_json.stdout.endswith(b"\n\n")
    ):
        raise SmokeFailure("installed Project Explain JSON stream is unexpected")

    explain_text = _run_installed_cli(
        cli_path,
        ("explain", CHECK_INPUT.as_posix()),
        scratch_dir=scratch_dir,
        stage="installed CLI explain text",
        environment=environment,
    )
    if b"Semantic Metadata Artifact v1\n" not in explain_text.stdout:
        raise SmokeFailure(
            "installed CLI explain text output is missing artifact header"
        )
    if explain_text.stderr:
        raise SmokeFailure("installed CLI explain text wrote unexpected stderr")

    explain_json = _run_installed_cli(
        cli_path,
        ("explain", CHECK_INPUT.as_posix(), "--format", "json"),
        scratch_dir=scratch_dir,
        stage="installed CLI explain JSON",
        environment=environment,
    )
    try:
        explain_document = json.loads(explain_json.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(
            f"cannot decode explain Artifact v1 JSON: {error}"
        ) from error
    if explain_document.get("artifact") != "Semantic Metadata Artifact v1":
        raise SmokeFailure("installed CLI explain JSON artifact identity is unexpected")
    if explain_document.get("command") != "explain":
        raise SmokeFailure("installed CLI explain JSON command is unexpected")
    if explain_document.get("schema_version") != 1:
        raise SmokeFailure("installed CLI explain JSON schema_version is unexpected")
    if explain_document.get("ok") is not True:
        raise SmokeFailure("installed CLI explain JSON ok field is unexpected")
    if "metadata" not in explain_document or "error" in explain_document:
        raise SmokeFailure("installed CLI explain JSON envelope is unexpected")
    if explain_json.stderr:
        raise SmokeFailure("installed CLI explain JSON wrote unexpected stderr")

    postgres = _run_installed_cli(
        cli_path,
        (
            "emit-sql",
            POSTGRES_INPUT.as_posix(),
            "--dialect",
            "postgres",
        ),
        scratch_dir=scratch_dir,
        stage="installed PostgreSQL text",
        environment=environment,
    )
    expected_postgres = (REPO_ROOT / POSTGRES_GOLDEN).read_bytes()
    if postgres.stdout != expected_postgres or postgres.stderr:
        raise SmokeFailure(
            "installed PostgreSQL text output differs from reviewed golden bytes"
        )

    mysql = _run_installed_cli(
        cli_path,
        (
            "emit-sql",
            MYSQL_INPUT.as_posix(),
            "--dialect",
            "mysql",
            "--format",
            "json",
        ),
        scratch_dir=scratch_dir,
        stage="installed MySQL JSON v1",
        environment=environment,
    )
    try:
        actual_mysql = json.loads(mysql.stdout)
        expected_mysql = json.loads((REPO_ROOT / MYSQL_GOLDEN).read_bytes())
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(
            f"cannot decode MySQL JSON v1 smoke output: {error}"
        ) from error
    if actual_mysql != expected_mysql or mysql.stderr:
        raise SmokeFailure(
            "installed MySQL JSON v1 output differs structurally from reviewed golden"
        )

    print(f"[package-smoke] installed CLI version: {version.stdout.decode().strip()}")
    print(
        "[package-smoke] installed CLI verified: --help, check, project check, "
        "single-file and project explain, PostgreSQL byte-exact text, "
        "MySQL JSON v1 structure",
        flush=True,
    )


def main() -> int:
    """Run the independent packaging and installed-CLI smoke validation."""

    try:
        contract = _project_contract()
        with tempfile.TemporaryDirectory(prefix="pietto-package-smoke-") as temporary:
            temporary_root = Path(temporary)
            dist_dir = temporary_root / "dist"
            venv_dir = temporary_root / "venv"
            scratch_dir = temporary_root / "scratch"
            dist_dir.mkdir()
            scratch_dir.mkdir()

            _run_command(
                "build sdist and wheel",
                (
                    "uv",
                    "build",
                    "--sdist",
                    "--wheel",
                    "--out-dir",
                    str(dist_dir),
                ),
                cwd=REPO_ROOT,
            )
            sdist, wheel = _find_artifacts(dist_dir)
            print(f"[package-smoke] built sdist: {sdist.name}")
            print(f"[package-smoke] built wheel: {wheel.name}")

            _inspect_sdist(sdist, contract)
            _inspect_wheel(wheel, contract)
            print("[package-smoke] artifact inventory and metadata verified")

            _run_command(
                "create clean virtual environment",
                (sys.executable, "-m", "venv", str(venv_dir)),
                cwd=temporary_root,
            )
            venv_python = _venv_python(venv_dir)
            _run_command(
                "install wheel",
                (
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(venv_python),
                    str(wheel),
                ),
                cwd=temporary_root,
                env=_clean_environment(),
            )
            _smoke_installed_cli(venv_dir, scratch_dir, contract)
    except SmokeFailure as error:
        print(f"[package-smoke] error: {error}", file=sys.stderr)
        return error.exit_code

    print("[package-smoke] packaging and installed CLI smoke passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
