from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-33-json-v2-and-project-multifile.md"
SPEC_PATH = REPO_ROOT / "docs/spec/project-json-v2-result-envelope-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_IMPLEMENTATION_PATHS = (
    "src/pietto/project.py",
    "src/pietto/project",
    "src/pietto/json_v2.py",
    "src/pietto/json_v2",
    "src/pietto/_project.py",
    "src/pietto/_json_v2.py",
    "src/pietto/database.py",
    "src/pietto/runtime.py",
    "src/pietto/schema_introspection.py",
)


def test_slice2_contract_artifacts_and_plan_status_are_present() -> None:
    spec = _normalized(SPEC_PATH)
    plan = _normalized(PLAN_PATH)
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    assert SPEC_PATH.is_file()
    assert project["version"] == "0.1.0"

    for required in (
        "Phase 33 Slice 2 JSON v2 Project Result Envelope Contract is complete "
        "as docs/spec/static-audit/status-only work",
        "docs/spec/project-json-v2-result-envelope-v1.md",
        "tests/test_phase33_json_v2_project_envelope_contract.py",
        "Slice 2 adds no source implementation, no JSON v2 serializer, no "
        "project discovery runtime, no project CLI",
    ):
        assert required in plan, required

    for required in (
        "This document defines the Phase 33 Slice 2 contract",
        "The envelope is not implemented",
        "Slice 2 is docs/spec/static-audit/status-only work",
    ):
        assert required in spec, required


def test_envelope_identity_and_success_shape_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "schema_version, command, mode, ok, project, inputs, diagnostics, "
        "cli_errors, result",
        "schema_version: 2",
        'command: "check"',
        'mode: "project"',
        "ok: boolean",
        "The envelope uses `result`, not `payload`",
        '"schema_version": 2',
        '"command": "check"',
        '"mode": "project"',
        '"ok": true',
        '"diagnostics": []',
        '"cli_errors": []',
        '"files_with_errors": 0',
    ):
        assert required in spec, required


def test_failure_policy_and_nullable_project_identity_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "When a project check fails, `ok` is `false`",
        "at least one of `diagnostics` or `cli_errors` is non-empty",
        "When failure is attributable to project input files, "
        "`files_with_errors` is greater than `0`",
        '"ok": false',
        '"root": null',
        '"config_path": null',
        "root/config/path errors: exit `2`, stop before parse",
        "source-read errors: exit `2`, report as `cli_errors`",
        "parser errors: exit `1`, aggregate/report diagnostics",
        "semantic errors: exit `1`, block project IR",
        "IR errors: exit `1`, block SQL",
        "no partial SQL output",
        "no partial metadata output by default",
        "JSON `ok` remains separate from the process exit code",
    ):
        assert required in spec, required

    for required in (
        "| `root` | string or null |",
        "| `config_path` | string or null |",
    ):
        assert required in _read(SPEC_PATH), required


def test_project_identity_and_input_contract_are_narrow() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Slice 2 does not authorize `project.name`, `project.display_name`",
        "| `path` | string | Normalized project-relative path |",
        '| `kind` | string | Initially `"source"` |',
        '| `status` | string | Initially `"parsed"` or `"error"` |',
        "Project input ordering is deterministic",
        "containment and duplicate physical identity checks",
        "Diagnostics remain top-level only in Slice 2",
        "`inputs[].diagnostics` is not part of the Slice 2 envelope",
    ):
        assert required in spec, required


def test_diagnostics_cli_errors_and_related_locations_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`diagnostics` contains compiler diagnostics",
        "`cli_errors` contains handled project, CLI, configuration, path, "
        "source-read, resource, and input errors",
        "JSON v2 diagnostics preserve the existing CLI JSON v1 diagnostic fields",
        "code, severity, message, location, suggestion",
        "required v2-only `related_locations` field",
        "`related_locations` is always present and may be empty",
        "Root, config, path, source-read, and resource failures are `cli_errors`",
        "Parser and semantic compiler failures are `diagnostics`",
        "These values are v2-only and do not change CLI JSON v1 CLI error kinds",
    ):
        assert required in spec, required


def test_result_check_counters_and_forbidden_fields_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "result.check.files_total",
        "result.check.files_ok",
        "result.check.files_with_errors",
        "`files_total` counts selected project input files",
        "`files_ok` counts inputs without source-read or parser errors",
        "`files_with_errors` counts inputs with source-read or parser errors",
        "top-level path",
        "artifact",
        "metadata",
        "dialect",
        "artifacts",
        "output",
        "SQL text",
        "Semantic Metadata Artifact v1 aggregation",
        "package release metadata",
    ):
        assert required in spec, required


def test_compatibility_boundaries_and_deferrals_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`pietto check --format json` remains single-file CLI JSON v1",
        "`pietto emit-sql --format json` remains single-file CLI JSON v1",
        "`pietto explain --format json` remains Semantic Metadata Artifact v1",
        "single-file `check` behavior remains unchanged",
        "single-file `emit-sql` behavior remains unchanged",
        "single-file `explain` behavior remains unchanged",
        "Project JSON v2 must not mutate CLI JSON v1",
        "Project JSON v2 must not mutate Semantic Metadata Artifact v1",
        "Project JSON v2 must not inherit Artifact v1 fields implicitly",
    ):
        assert required in spec, required

    for required in (
        "JSON v2 serializer implementation",
        "project discovery runtime",
        "project CLI or `--project` parser behavior",
        "multi-file compilation",
        "metadata aggregation",
        "SQL artifact generation",
        "dependency graph",
        "semantic graph",
        "relationship graph",
        "ERD",
        "AI metadata export",
        "runtime results",
        "database introspection results",
        "schema introspection",
        "database pull",
        "relationship/JOIN behavior",
        "Phase 34 work",
        "Phase 35 work",
        "Phase 36 work",
        "Phase 37 work",
    ):
        assert required in spec, required


def test_roadmap_and_forbidden_implementation_paths_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 33: JSON v2 And Project / Multi-file MVP",
        "Phase 34: Relationship Grain And Narrow JOIN MVP",
        "Phase 35: Developer Experience And Delivery Pipeline MVP",
        "Phase 36: Post-v0.2 Core Type System Expansion MVP",
        "Phase 37: Post-v0.2 Aggregate Surface Expansion MVP",
        "Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 "
        "deferred candidate without an assigned phase number",
        "Phase 34, Phase 35, Phase 36, and Phase 37 are not started",
    ):
        assert required in spec, required

    for relative_path in FORBIDDEN_IMPLEMENTATION_PATHS:
        assert not (REPO_ROOT / relative_path).exists(), relative_path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())
