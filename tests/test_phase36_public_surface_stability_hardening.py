from __future__ import annotations

import subprocess
import tomllib
from dataclasses import fields
from pathlib import Path
from typing import cast

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    _non_slice3_repair_diff_paths,
)

from pietto import cli_json
from pietto._metadata import model as metadata_model
from pietto._metadata.model import SemanticMetadataType
from pietto._project import json_v2 as project_json_v2
from pietto.errors import Diagnostic, Severity, SourceLocation

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/public-surface-stability-hardening-v1.md"

CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"
PROJECT_JSON_V2_PATH = REPO_ROOT / "src/pietto/_project/json_v2.py"
METADATA_MODEL_PATH = REPO_ROOT / "src/pietto/_metadata/model.py"
METADATA_BUILDER_PATH = REPO_ROOT / "src/pietto/_metadata/builder.py"
METADATA_SERIALIZER_PATH = REPO_ROOT / "src/pietto/_metadata/serializer.py"
METADATA_TEXT_PATH = REPO_ROOT / "src/pietto/_metadata/text.py"
CHECK_GENERATED_PATH = REPO_ROOT / "scripts/check_generated.py"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
CI_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/_metadata",
    "src/pietto/_project",
    "tests/fixtures",
    "pyproject.toml",
    "uv.lock",
    ".github",
    "scripts",
    "examples",
)

PHASE36_CANDIDATE_PUBLIC_FIELD_FRAGMENTS = (
    "precision_scale",
    "decimal_precision",
    "decimal_scale",
    "uuid_native",
    "native_uuid",
    "enum_sql",
    "enum_metadata",
    "datetime_precision",
    "timezone",
    "time_zone",
    "duration",
    "interval",
    "bytes_encoding",
    "json_schema",
    "json_path",
    "domain_constraints",
    "validation_rules",
    "operator_matrix",
    "native_db_metadata",
    "native_database_metadata",
    "currency",
    "money",
)


def _slice10_docs() -> str:
    return f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"


def test_slice10_selects_option_b_and_no_behavior_change() -> None:
    docs = _slice10_docs()

    for required in (
        "Phase 36 Slice 10 selects Option B: tests-only hardening",
        "Public Surface Stability Hardening",
        "locks public surface stability after Phase 36 Slices 3 through 9",
        "Slice 10 makes no behavior change",
        "No behavior change",
        "No schema/output change",
        "No package/workflow/release change",
        "Future public surface changes require separately approved Gate 1 and Gate 2",
    ):
        assert required in docs, required


def test_documented_public_surface_inventory_is_complete() -> None:
    docs = _slice10_docs()

    for required in (
        "CLI text output",
        "CLI JSON v1",
        "Project JSON v2",
        "Semantic Metadata Artifact v1 JSON and text output",
        "PostgreSQL SQL output",
        "private MySQL SQL and JSON output",
        "diagnostic envelope shape",
        "fixture and golden inventory",
        "generated parser inventory",
        "package metadata, package version, and package-smoke policy",
        "validation scripts and CI workflow role",
        "release, publish/upload, signing, and attestation non-authorization",
    ):
        assert required in docs, required


def test_cli_json_v1_schema_and_envelopes_are_source_backed() -> None:
    source = _read(CLI_JSON_PATH)

    assert cli_json._SCHEMA_VERSION == 1
    assert "_SCHEMA_VERSION = 1" in source
    assert "_SCHEMA_VERSION = 2" not in source

    for required in (
        '"schema_version": _SCHEMA_VERSION',
        '"command": "check"',
        '"command": "emit-sql"',
        '"ok": _result_is_ok(diagnostics, cli_errors)',
        '"path": _path_text(path)',
        '"diagnostics"',
        '"cli_errors"',
        '"dialect": dialect',
        '"artifacts"',
        '"output": _output_to_json_dict(output)',
    ):
        assert required in source, required

    diagnostic = cli_json.diagnostic_to_json_dict(
        _diagnostic(code="PIE-S2314", message="Unsupported aggregate argument type.")
    )
    assert tuple(diagnostic) == (
        "code",
        "severity",
        "message",
        "location",
        "suggestion",
    )
    assert diagnostic["code"] == "PIE-S2314"


def test_project_json_v2_schema_and_envelope_are_source_backed() -> None:
    source = _read(PROJECT_JSON_V2_PATH)

    assert project_json_v2._PROJECT_JSON_V2_VERSION == 2
    for required in (
        "_PROJECT_JSON_V2_VERSION = 2",
        '_COMMAND = "check"',
        '_MODE = "project"',
        '"schema_version": _PROJECT_JSON_V2_VERSION',
        '"command": _COMMAND',
        '"mode": _MODE',
        '"ok": result.ok',
        '"project": _project_to_json_dict(result)',
        '_JSON_INPUT_KIND = "source"',
        '_JSON_INPUT_STATUSES = frozenset({"parsed", "error"})',
        '"inputs": inputs',
        '"diagnostics": diagnostics',
        '"cli_errors": [_cli_error_to_json_dict(error) for error in result.errors]',
        '"result"',
        '"files_total": len(inputs)',
        '"files_ok": files_ok',
        '"files_with_errors": files_with_errors',
        "ProjectParseCheckResult",
        "_inputs_to_json_list",
        "_diagnostics_to_json_list",
        "_check_counters",
    ):
        assert required in source, required

    for forbidden in ("artifact", "metadata", "dialect", "artifacts", "output"):
        assert f'"{forbidden}"' not in source, forbidden


def test_semantic_metadata_artifact_v1_schema_and_type_fields_are_locked() -> None:
    model_source = _read(METADATA_MODEL_PATH)
    serializer_source = _read(METADATA_SERIALIZER_PATH)
    text_source = _read(METADATA_TEXT_PATH)

    assert metadata_model.SEMANTIC_METADATA_ARTIFACT_NAME == (
        "Semantic Metadata Artifact v1"
    )
    assert metadata_model.SEMANTIC_METADATA_SCHEMA_VERSION == 1
    assert metadata_model.SEMANTIC_METADATA_COMMAND == "explain"
    assert [field.name for field in fields(SemanticMetadataType)] == [
        "status",
        "name",
        "kind",
        "canonical_name",
        "canonical_kind",
        "nullability",
        "support_posture",
    ]

    for required in (
        '"artifact": artifact.artifact',
        '"schema_version": artifact.schema_version',
        '"command": artifact.command',
        '"ok": artifact.ok',
        '"path": artifact.path',
        '"diagnostics"',
        '"metadata": _payload_to_json_dict(artifact.metadata)',
        '"error"',
        '"stage": stage',
        '"message": message',
    ):
        assert required in serializer_source, required

    for required in (
        "Semantic Metadata Artifact v1",
        "schema_version: {artifact.schema_version}",
        "command: {artifact.command}",
        "summary:",
        "definitions:",
        "sources:",
        "relations:",
        "types:",
        "support={type_ref.support_posture}",
    ):
        assert required in model_source or required in text_source, required


def test_phase36_candidate_specific_public_fields_are_not_added() -> None:
    combined_public_sources = "\n".join(
        _read(path).lower()
        for path in (
            CLI_JSON_PATH,
            PROJECT_JSON_V2_PATH,
            METADATA_MODEL_PATH,
            METADATA_SERIALIZER_PATH,
            METADATA_TEXT_PATH,
        )
    )

    for fragment in PHASE36_CANDIDATE_PUBLIC_FIELD_FRAGMENTS:
        assert fragment not in combined_public_sources, fragment


def test_support_posture_vocabulary_is_documented_and_source_backed() -> None:
    docs = _slice10_docs()
    builder_source = _read(METADATA_BUILDER_PATH)
    schema_type_test = _read(
        REPO_ROOT / "tests/test_phase32_metadata_schema_type_nullability.py"
    )

    for posture in (
        "current",
        "limited_frozen",
        "metadata_only",
        "deferred_builtin",
        "unknown",
    ):
        assert f"`{posture}`" in docs, posture
        assert posture in builder_source or posture in schema_type_test, posture

    assert '_LIMITED_FROZEN_BUILTINS = frozenset({"UUID"})' in builder_source
    assert '_DEFERRED_BUILTINS = frozenset({"Bytes", "Json"})' in builder_source


def test_slice5_diagnostic_migration_is_not_schema_expansion() -> None:
    docs = _slice10_docs()
    cli_json_source = _read(CLI_JSON_PATH)
    serializer_source = _read(METADATA_SERIALIZER_PATH)

    for required in (
        "`count(Enum field)` now fails closed with diagnostic `PIE-S2314`",
        "not a JSON schema, diagnostic envelope, or public output shape change",
        "Slice 5 changed the unsafe Enum aggregate path",
        "does not change CLI JSON v1, Project JSON v2, or Semantic Metadata "
        "Artifact v1 diagnostic envelope shape",
    ):
        assert required in docs, required

    assert "PIE-S2314" not in cli_json_source
    assert "PIE-S2314" not in serializer_source
    assert "PIE-B1000" not in cli_json_source
    assert "PIE-B1000" not in serializer_source


def test_golden_and_generated_inventories_remain_locked() -> None:
    check_goldens = _read(CHECK_GOLDENS_PATH)
    check_generated = _read(CHECK_GENERATED_PATH)
    tracked_generated = _tracked_files("src/pietto/generated")

    for required in (
        "SQL_FIXTURES = frozenset(",
        "JSON_FIXTURES = frozenset(",
        "CLASSIFIED_FIXTURES = SQL_FIXTURES | JSON_FIXTURES",
        "no missing or orphan fixtures",
    ):
        assert required in check_goldens, required

    assert 'f"{len(SQL_FIXTURES)} SQL byte-exact' in check_goldens
    assert 'f"{len(JSON_FIXTURES)} JSON structural' in check_goldens

    assert tracked_generated == (
        "src/pietto/generated/Pietto.interp",
        "src/pietto/generated/Pietto.tokens",
        "src/pietto/generated/PiettoLexer.interp",
        "src/pietto/generated/PiettoLexer.py",
        "src/pietto/generated/PiettoLexer.tokens",
        "src/pietto/generated/PiettoParser.py",
        "src/pietto/generated/PiettoVisitor.py",
        "src/pietto/generated/__init__.py",
    )
    for required in (
        "Verify ANTLR provenance and exact generated-file reproducibility.",
        "ANTLR_JAR",
        "CHECKSUM_FILE",
        "GENERATED_DIR",
        "_compare_generated_files",
        "byte-for-byte",
    ):
        assert required in check_generated, required


def test_package_version_smoke_scripts_and_workflow_boundaries_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    package_smoke = _read(PACKAGE_SMOKE_PATH)
    validate_py = _read(VALIDATE_PATH)
    workflow = _read(CI_WORKFLOW_PATH)

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)

    for required in (
        "Build, inspect, install, and smoke test Pietto release artifacts.",
        '"build sdist and wheel"',
        '"install wheel"',
        "installed CLI version",
        "installed CLI help",
        "installed CLI check",
        "installed CLI project check JSON v2",
        "installed CLI explain JSON",
        "installed PostgreSQL text",
        "installed MySQL JSON v1",
        "packaging and installed CLI smoke passed",
    ):
        assert required in package_smoke, required

    for required in (
        '("lockfile", ("uv", "lock", "--check"))',
        '("format", ("uv", "run", "ruff", "format", "--check", "."))',
        '("lint", ("uv", "run", "ruff", "check", "."))',
        '("production typing", ("uv", "run", "pyright"))',
        '"test typing"',
        '("tests", ("uv", "run", "pytest"))',
    ):
        assert required in validate_py, required

    for required in (
        "permissions:\n  contents: read",
        "run: uv run python scripts/validate.py",
        "run: uv run python scripts/check_generated.py",
        "run: uv run python scripts/check_goldens.py",
        "run: uv run python scripts/package_smoke.py",
    ):
        assert required in workflow, required

    combined_release_surface = "\n".join(
        (_read(PACKAGE_SMOKE_PATH), _read(VALIDATE_PATH), _read(CI_WORKFLOW_PATH))
    ).lower()
    for forbidden in (
        "twine",
        "pypi-token",
        "trusted publishing",
        "sigstore",
        "attestation",
        "id-token:",
        "contents: write",
    ):
        assert forbidden not in combined_release_surface, forbidden


def test_status_docs_are_deferred_until_slice11_and_housekeeping_is_recorded() -> None:
    docs = _slice10_docs()

    for required in (
        "`README.md`, `AGENTS.md`, and `docs/spec/pietto-v0.9.md` remain deferred to Slice 11",
        "Slice 10 does not perform global status housekeeping",
        "Slice 11 status housekeeping",
        "Phase 36 Slice 11 selects Option B",
        "updates `README.md`, `AGENTS.md`, and `docs/spec/pietto-v0.9.md`",
        "does not claim Phase 36 final completion",
    ):
        assert required in docs, required


def test_package_smoke_network_policy_is_documented() -> None:
    docs = _slice10_docs()

    for required in (
        "Sandbox DNS/PyPI failures in `scripts/package_smoke.py` are environment-only",
        "dependency fetch, name resolution, or package index access failure",
        "record the raw failure",
        "must not patch repository files",
    ):
        assert required in docs, required


def test_forbidden_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert _non_slice3_repair_diff_paths(diff_output) == set()


def _tracked_files(relative_path: str) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "ls-files", relative_path],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return tuple(result.stdout.splitlines())


def _diagnostic(*, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=cast(SourceLocation, None),
    )
