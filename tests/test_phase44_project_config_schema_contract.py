from __future__ import annotations

import subprocess
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md"
)
SPEC_PATH = REPO_ROOT / "docs/spec/phase44-project-config-schema-contract-v1.md"
PHASE55_SLICE2_SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase55-slice2-explicit-package-activation-compatibility-and-immutable-package-carrier-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_GATE2_PATHS = {
    "docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md",
    "docs/spec/phase44-project-source-selection-scope-lock-v1.md",
    "docs/spec/phase44-project-config-schema-contract-v1.md",
    "docs/spec/project-json-v2-result-envelope-v1.md",
    "docs/spec/project-cli-json-v2.md",
    "src/pietto/_project/json_v2.py",
    "src/pietto/cli.py",
    "scripts/package_smoke.py",
    "tests/test_phase44_completion_audit.py",
    "tests/test_phase44_project_cli_package_compatibility.py",
    "tests/test_phase44_project_json_v2_inputs_counters.py",
    "tests/test_phase44_project_parse_only_check.py",
    "tests/test_phase44_project_config_schema_contract.py",
    "tests/test_phase44_project_source_selection_scope_lock.py",
    "tests/test_phase33_project_check_cli.py",
    "tests/test_phase33_json_v2_project_envelope_contract.py",
    "tests/test_phase33_project_root_config_path_discovery_contract.py",
    "tests/test_phase33_project_json_v2_serializer.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase33_cli_package_compatibility_hardening.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase8_completion_audit.py",
    "tests/test_phase9_completion_audit.py",
    "tests/test_phase10_completion_audit.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_planning_audit.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase12_planning_audit.py",
    "tests/test_phase12_order_limit_contract.py",
    "tests/test_phase13_completion_audit.py",
    "tests/test_phase13_planning_audit.py",
    "tests/test_phase14_candidate_decision_audit.py",
    "tests/test_phase14_completion_audit.py",
    "tests/test_phase14_planning_audit.py",
    "tests/test_phase14_relationship_metadata_completion_audit.py",
    "tests/test_phase15_completion_audit.py",
    "tests/test_phase15_semantic_completion_audit.py",
    "tests/test_phase16_completion_audit.py",
    "tests/test_phase16_current_syntax_surface_audit.py",
    "tests/test_phase16_language_direction_audit.py",
    "tests/test_phase16_safety_deferral_sql_portability.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
    "tests/test_phase25_completion_audit.py",
    "tests/test_phase26_completion_audit.py",
    "tests/test_phase27_completion_audit.py",
    "tests/test_phase28_completion_audit.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_completion_audit.py",
    "tests/test_phase32_completion_audit.py",
}

FORBIDDEN_DIFF_PATHS = (
    "src/pietto/_project/discovery.py",
    "grammar",
    "tests/fixtures",
    "pyproject.toml",
    "uv.lock",
    ".github",
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
)


def test_slice2_artifacts_and_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    combined = _phase44_slice2_text()
    for required in (
        "Phase 44 Slice 2 is Project Config Schema Contract",
        "docs/spec/static-audit work only and implements no behavior change",
        "the narrow active `pietto.toml` schema contract",
        "does not implement a config loader, source selection, glob expansion",
        "source reading, parser aggregation, Project JSON v2 input reporting",
        "Phase 44 Slice 3 is Private Project Config Loader MVP",
        "implements only a private `pietto.toml` loader and schema validator",
        "does not wire the loader into CLI behavior, Project JSON v2 output",
        "Phase 44 Slice 4 is Deterministic Source Selection MVP",
        "implements only private deterministic source selection",
        "does not wire source selection into CLI behavior, Project JSON v2 output",
        "Package version remains `0.1.0`",
    ):
        assert required in combined, required


def test_active_schema_version_and_sources_contract_are_minimal() -> None:
    combined = _phase44_slice2_text()

    for required in (
        "schema_version = 1",
        "[sources]",
        'include = ["models/**/*.pietto"]',
        "exclude = []",
        "`schema_version = 1` is required",
        "`[sources]` is required",
        "`sources.include` is required, must be an array of strings, and must be non-empty",
        "`sources.exclude` is optional",
        "a missing `sources.exclude` means the empty list `[]`",
        "there is no implicit include default",
        "a missing `sources.include` is a schema error",
    ):
        assert required in combined, required

    for forbidden in (
        "`sources.exclude` is required",
        "missing `sources.include` means",
    ):
        assert forbidden not in combined, forbidden


def test_phase55_slice2_extends_without_rewriting_the_phase44_schema_contract() -> None:
    """Schema-v3 is a later exclusive mode; Phase 44's v1 contract stays literal."""

    assert PHASE55_SLICE2_SPEC_PATH.is_file()
    phase44 = _phase44_slice2_text()
    phase55 = _normalized(PHASE55_SLICE2_SPEC_PATH)

    for required in (
        "`schema_version = 1` is required",
        "`[sources]` is required",
        "there is no implicit include default",
    ):
        assert required in phase44, required
    for required in (
        "Schema v1 yields `LEGACY_FLAT`",
        "schema v2 yields `EXPLICIT_MODULES`",
        "`schema_version = 3` plus exactly one `[package]` root table",
        "Schema v1 and v2 allow exactly `schema_version` and `[sources]`",
        "Schema v3 allows exactly `schema_version` and `[package]`",
    ):
        assert required in phase55, required


def test_pattern_path_and_wildcard_rules_are_unambiguous() -> None:
    combined = _phase44_slice2_text()

    for required in (
        "Configured source patterns use normalized project-relative text",
        "`/` is the only separator",
        "paths and patterns are relative to the explicit project root",
        "absolute POSIX paths are rejected",
        "Windows drive paths and UNC paths are rejected",
        "`.` and `..` path segments are rejected",
        "empty path segments from repeated `/` are rejected",
        "leading `/` and trailing `/` are rejected",
        "backslashes and NUL are rejected",
        "no environment-variable expansion, tilde expansion",
        "shell interpretation",
        "`**` may appear only as a complete path segment",
        "`*` may appear inside a normal path segment",
        "`?` may appear inside a normal path segment",
        "*.pietto",
        "models/**/*.pietto",
        "character classes such as `[a-z]`",
        "brace expansion such as `{src,test}`",
        "extglob or shell-specific forms",
        "negated glob syntax",
    ):
        assert required in combined, required


def test_slice2_reporting_and_slice6_json_boundary_are_locked() -> None:
    combined = _phase44_slice2_text()

    for required in (
        "Future runtime config, path, glob, resource, and source-read failures are project",
        "not new `PIE-*` compiler diagnostics",
        "Slice 3 reports config and configured-pattern failures only through the private",
        "project error model",
        "`config_read`",
        "`config_parse`",
        "`config_schema`",
        "`project_path`",
        "`project_glob`",
        "`project_resource`",
        "`source_read`",
        "does not change current root/config-only Project JSON v2 output",
        "Slice 3 implements a private config loader only",
        "Slice 4 implements private deterministic source selection only",
        "It does not own source reading, parser aggregation, CLI behavior, or Project JSON v2 output",
        "Slice 5 implements source read plus parse-only text-mode project check only",
        "Slice 6 implements Project JSON v2 `inputs[]` and project check counters",
        "keeps internal `selected` out of JSON",
        "keeps pre-parse root/config/source-selection failures at empty `inputs` plus",
        "zero counters",
        "does not implement CLI JSON v1 changes",
        "Slice 7 implements CLI/package compatibility hardening through docs, tests, and",
        "static audits only",
        "does not change this config schema contract",
        "Slice 8 implements completion audit and status lock through docs/spec/static",
        "does not claim Gate 3 natural CI success inside this contract",
    ):
        assert required in combined, required


def test_slice2_allowlist_validation_and_stop_conditions_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 44 Slice 2 Gate 2 is limited to:",
        "docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md",
        "docs/spec/phase44-project-config-schema-contract-v1.md",
        "tests/test_phase44_project_config_schema_contract.py",
        "No other file is approved in this Gate 2",
        "git diff --check",
        "uv run pytest tests/test_phase44_project_source_selection_scope_lock.py",
        "uv run pytest tests/test_phase44_project_config_schema_contract.py",
        "Stop and return to Repair Gate 1 if:",
        "any needed change falls outside the Slice 2 allowlist",
        "implementation of config loader, source selection, glob expansion",
        "source reading, parser aggregation",
        "JSON v1, Project JSON v2, or Semantic Metadata Artifact v1 output behavior",
        "Phase 44 Slice 3 Gate 2 is limited to:",
        "src/pietto/_project/config.py",
        "src/pietto/_project/model.py",
        "tests/test_phase44_project_config_loader.py",
        "tests/test_phase44_project_source_selection_scope_lock.py",
        "tests/test_phase33_completion_audit.py",
        "uv run ruff format --check src/pietto/_project",
        "uv run pyright --project pyrightconfig.json",
        "uv run pyright --project pyrightconfig.tests.json",
        "Phase 44 Slice 4 Gate 2 is limited to:",
        "docs/spec/phase44-project-source-selection-scope-lock-v1.md",
        "src/pietto/_project/source_selection.py",
        "tests/test_phase44_project_source_selection.py",
        "tests/test_phase9_completion_audit.py",
        "tests/test_phase33_cli_package_compatibility_hardening.py",
        "source selection does not call `Path.glob`, `Path.rglob`, or `os.walk`",
        "Phase 44 Slice 7 Gate 2 is limited to:",
        "tests/test_phase44_project_cli_package_compatibility.py",
        "No other file is approved in this Gate 2",
        "uv run pytest tests/test_phase44_project_cli_package_compatibility.py",
        "uv run python scripts/package_smoke.py",
        "Phase 44 Slice 8 Gate 2 is limited to:",
        "tests/test_phase44_completion_audit.py",
        "tests/test_phase44_project_json_v2_inputs_counters.py",
        "Slice 8 must not change `src/**`",
        "`scripts/**`, `README.md`, `AGENTS.md`, `docs/spec/pietto-v0.9.md`",
        "uv run ruff format --check tests/test_phase44_completion_audit.py",
        "uv run pytest tests/test_phase44_completion_audit.py",
    ):
        assert required in plan, required


def test_forbidden_implementation_surfaces_are_not_modified() -> None:
    assert (
        _git_diff_name_only(FORBIDDEN_DIFF_PATHS) == ""
    ) or _phase54_active_gate2_is_active()
    assert (
        _git_status_paths().issubset(ALLOWED_GATE2_PATHS)
    ) or _phase54_active_gate2_is_active()


def test_package_version_release_and_public_output_boundaries_remain_locked() -> None:
    pyproject = _read(PYPROJECT_PATH)
    combined = _phase44_slice2_text()
    lowered = combined.lower()

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert "Package version remains `0.1.0`" in combined

    for forbidden in (
        "tag created",
        "release created",
        "package release occurred",
        "published package",
        "uploaded package",
        "signing completed",
        "attestation completed",
    ):
        assert forbidden not in lowered, forbidden

    for required in (
        "CLI JSON v1 mutation",
        "Project JSON v2 serializer changes",
        "Semantic Metadata Artifact v1 mutation",
        "`src/pietto/**` changes",
        "grammar or generated parser changes",
        "fixtures or goldens",
        "package, dependency, workflow, or lockfile changes",
        "tag, release, publish, upload, signing, or attestation",
    ):
        assert required in combined, required


def _phase44_slice2_text() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def _git_diff_name_only(paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def _git_status_paths() -> set[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return paths
