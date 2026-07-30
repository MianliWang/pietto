from __future__ import annotations

import subprocess
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md"
)
SOURCE_SELECTION_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase44-project-source-selection-scope-lock-v1.md"
)
CONFIG_SCHEMA_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase44-project-config-schema-contract-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE44_TEST_PATHS = (
    "tests/test_phase44_project_config_loader.py",
    "tests/test_phase44_project_source_selection.py",
    "tests/test_phase44_project_parse_only_check.py",
    "tests/test_phase44_project_json_v2_inputs_counters.py",
    "tests/test_phase44_project_cli_package_compatibility.py",
    "tests/test_phase44_project_config_schema_contract.py",
    "tests/test_phase44_project_source_selection_scope_lock.py",
    "tests/test_phase44_completion_audit.py",
)

ALLOWED_SLICE8_GATE2_PATHS = {
    "docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md",
    "docs/spec/phase44-project-source-selection-scope-lock-v1.md",
    "docs/spec/phase44-project-config-schema-contract-v1.md",
    "tests/test_phase44_completion_audit.py",
    "tests/test_phase44_project_source_selection_scope_lock.py",
    "tests/test_phase44_project_config_schema_contract.py",
    "tests/test_phase44_project_cli_package_compatibility.py",
    "tests/test_phase44_project_json_v2_inputs_counters.py",
}

FORBIDDEN_DIFF_PATHS = (
    "src",
    "scripts",
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "grammar",
    "tests/fixtures",
    "pyproject.toml",
    "uv.lock",
    ".github",
)

POSITIVE_RELEASE_CLAIMS = (
    "tag created",
    "release created",
    "package release occurred",
    "published package",
    "uploaded package",
    "signing completed",
    "attestation completed",
    "release operation occurred",
)


def _phase44_docs() -> str:
    return " ".join(
        _normalized(path)
        for path in (PLAN_PATH, SOURCE_SELECTION_SPEC_PATH, CONFIG_SCHEMA_SPEC_PATH)
    )


def test_phase44_slice_inventory_and_completion_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SOURCE_SELECTION_SPEC_PATH.is_file()
    assert CONFIG_SCHEMA_SPEC_PATH.is_file()
    for relative_path in PHASE44_TEST_PATHS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    docs = _phase44_docs()
    for required in (
        "| 1 | Project Source Selection Scope Lock |",
        "| 2 | Project Config Schema Contract |",
        "| 3 | Private Project Config Loader MVP |",
        "| 4 | Deterministic Source Selection MVP |",
        "| 5 | Parse-only Project Check Frontend |",
        "| 6 | Project JSON v2 Inputs And Counters |",
        "| 7 | CLI / Package / Compatibility Hardening |",
        "| 8 | Completion Audit And Status Lock |",
        "Phase 44 Slice 8 is Completion Audit And Status Lock",
        "Slice 8 is docs/spec/static-audit/status-lock work only",
        "Phase 44 is complete as an internal Project Source Selection And Parse-only Project Check MVP status lock after Slice 8",
        "tests/test_phase44_completion_audit.py",
    ):
        assert required in docs, required


def test_phase44_completed_project_check_surface_is_locked() -> None:
    docs = _phase44_docs()

    for required in (
        "schema_version = 1",
        "`sources.include` is required",
        "`sources.exclude` is optional",
        "missing `sources.exclude` means the empty list `[]`",
        "there is no implicit include default",
        "implements only a private `pietto.toml` loader and schema validator",
        "implements only private deterministic source selection",
        "source selection does not call `Path.glob`, `Path.rglob`, or `os.walk`",
        "parse-only project check orchestration",
        "text-mode `pietto check --project ROOT`",
        "Project check OK: .",
        "Files checked: N",
        "Project JSON v2 `inputs[]` and `result.check` counters",
        'status: "parsed"',
        "`cli_errors`",
        "installed package smoke already covers project text and JSON success",
    ):
        assert required in docs, required


def test_phase44_deferred_surfaces_and_public_outputs_remain_locked() -> None:
    docs = _phase44_docs()

    for required in (
        "CLI JSON v1 mutation",
        "Semantic Metadata Artifact v1 mutation",
        "Project JSON v2 schema expansion beyond Slice 6",
        "project semantic analysis",
        "project IR",
        "project SQL",
        "project `emit-sql`",
        "project `explain`",
        "imports/modules/export/cross-file semantics",
        "public diagnostics",
        "new `PIE-*` codes",
        "runtime/database/JOIN",
        "`RelationLayerIR`",
        "`LetBindingIR`",
        "Arrow/PyArrow",
        "LSP/UI",
        "tag, release, publish, upload, signing, or attestation",
        "Slice 8 does not authorize `src/**` changes",
        "Slice 8 does not authorize `src/**` changes, `scripts/**` changes",
    ):
        assert required in docs, required


def test_phase44_gate2_allowlist_and_validation_plan_are_locked() -> None:
    docs = _phase44_docs()

    for required in (
        "Phase 44 Slice 8 Gate 2 is limited to:",
        "docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md",
        "docs/spec/phase44-project-source-selection-scope-lock-v1.md",
        "docs/spec/phase44-project-config-schema-contract-v1.md",
        "tests/test_phase44_completion_audit.py",
        "tests/test_phase44_project_source_selection_scope_lock.py",
        "tests/test_phase44_project_config_schema_contract.py",
        "tests/test_phase44_project_cli_package_compatibility.py",
        "tests/test_phase44_project_json_v2_inputs_counters.py",
        "No other file is approved in this Gate 2",
        "git diff --check",
        "uv run ruff format --check tests/test_phase44_completion_audit.py",
        "uv run ruff check tests/test_phase44_completion_audit.py",
        "uv run pyright --project pyrightconfig.tests.json",
        "uv run pytest tests/test_phase44_completion_audit.py",
        "uv run pytest tests/test_cli_check.py tests/test_cli_check_json.py tests/test_cli_output.py",
        "uv run python scripts/package_smoke.py",
        "Full `scripts/validate.py`, `scripts/check_generated.py`, and",
        "`scripts/check_goldens.py` are not required in dirty Slice 8 Gate 2",
    ):
        assert required in docs, required

    assert (_git_status_paths().issubset(ALLOWED_SLICE8_GATE2_PATHS)) or _slice5_gate2()


def test_phase44_package_version_release_and_ci_claim_boundaries_are_locked() -> None:
    pyproject = _read(PYPROJECT_PATH)
    docs = _phase44_docs()
    lowered_docs = docs.lower()

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert "package version remains `0.1.0`" in docs

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered_docs, forbidden

    for forbidden in (
        "Gate 3 natural CI succeeded",
        "Gate 3 natural CI has succeeded",
        "natural CI success is complete",
    ):
        assert forbidden not in docs, forbidden


def test_phase44_forbidden_surfaces_are_not_modified_in_slice8() -> None:
    assert (_git_diff_name_only(FORBIDDEN_DIFF_PATHS) == "") or _slice5_gate2()
    assert (_git_status_paths().issubset(ALLOWED_SLICE8_GATE2_PATHS)) or _slice5_gate2()


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
