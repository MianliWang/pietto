from __future__ import annotations

import subprocess
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-45-project-wide-semantic-model-mvp.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE1_GATE2_PATHS = {
    "docs/plan/phase-45-project-wide-semantic-model-mvp.md",
    "docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md",
    "tests/test_phase45_project_semantic_scope_lock.py",
}

FORBIDDEN_DIFF_PATHS = (
    "src",
    "scripts",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "tests/fixtures",
    "tests/goldens",
    "grammar",
)


def _docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_phase45_identity_and_true_project_model_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _docs()
    for required in (
        "Project-wide Semantic Model Design And MVP",
        "private-first and conservative",
        "builds on Phase 44",
        "upgrades project check from parse-only toward project-wide semantic checking",
        "must preserve single-file behavior",
        "requires a true private project-wide semantic model",
        "must not be reduced to per-file semantic aggregation",
        "a selected-project compile unit",
        "deterministic selected input ordering",
        "parsed AST retention for selected files before project semantic analysis",
        "project-relative diagnostic locations",
        "a private project semantic catalog/model",
        "cross-file symbol collection before reference resolution",
        "one project-wide semantic environment/model",
        "not independent per-file analysis plus merge",
        "treating Phase 45 as only a list of per-file semantic results",
        "independently calling single-file semantic analysis per file and merging",
        "allowing cross-file references without a deterministic project catalog",
    ):
        assert required in docs, required


def test_phase45_namespace_cross_file_and_ambiguity_policy_are_locked() -> None:
    docs = _docs()
    for required in (
        "hybrid namespace policy",
        "The type namespace includes:",
        "`shape`",
        "existing and future type aliases",
        "existing `enum`",
        "future domain types",
        "The relation namespace includes:",
        "`source`",
        "`table`",
        "`query`",
        "The callable namespace includes:",
        "existing `constraint`",
        "existing `derive`",
        "Slice 1 adds no callable behavior",
        "any selected project top-level symbol may be referenced",
        "Source shape bindings must be able to resolve project type namespace symbols",
        "Table and query `from` clauses must be able to resolve project relation namespace symbols",
        "source shape bindings must be able to resolve project type namespace symbols",
        "table and query `from` targets must be able to resolve project relation",
        "same relation namespace name across `source`, `table`, and `query` must fail closed",
        "non-strict warning / strict-mode error policy is deferred",
        "Ambiguous unqualified references must fail closed",
    ):
        assert required in docs, required


def test_phase45_module_import_and_json_policy_are_locked() -> None:
    docs = _docs()
    for required in (
        "flat implicit project package model",
        "Python-like imports, exports, and modules remain a required long-term target",
        "imports/modules/export behavior is not implemented in Phase 45 Slice 1",
        "Imports/modules/export behavior requires readiness before implementation",
        "Project semantic diagnostics should be represented in Project JSON v2 top-level",
        "`diagnostics[]`",
        "existing diagnostic shape where possible",
        "`related_locations: []` is acceptable for the MVP",
        "Semantic diagnostics must use project-relative paths",
        "Config, source-selection, and source-read failures remain in `cli_errors[]`",
        "Parser diagnostics remain in top-level `diagnostics[]`",
        "Semantic diagnostics must not require public diagnostic-surface expansion in Slice 1",
        "`inputs[].status` remains based on read/parse status",
        'readable and parsed input remains `"parsed"` even if semantic diagnostics exist',
        'read/parse failure remains `"error"`',
        'internal `"selected"` stays internal',
        "`result.check.files_total`, `files_ok`, and `files_with_errors` remain",
        "Top-level `ok` must become `false` if any error diagnostic exists",
        "Project text check should exit nonzero on semantic errors",
    ):
        assert required in docs, required


def test_phase45_slice_route_allowlist_validation_and_gate3_are_locked() -> None:
    docs = _docs()
    for required in (
        "1. Candidate / scope lock",
        "2. Parsed project semantic input units",
        "3. Private project semantic model scaffold",
        "4. Project catalog and duplicate detection",
        "5. Cross-file type namespace semantics",
        "6. Cross-file relation namespace semantics",
        "7. Project semantic CLI gate",
        "8. Project JSON v2 semantic diagnostics",
        "9. Compatibility hardening",
        "10. Completion audit and status lock",
        "Phase 45 Slice 1 Gate 2 is limited to:",
        "docs/plan/phase-45-project-wide-semantic-model-mvp.md",
        "docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md",
        "tests/test_phase45_project_semantic_scope_lock.py",
        "No other file is approved in this Gate 2",
        "git diff --check",
        "uv run ruff format --check tests/test_phase45_project_semantic_scope_lock.py",
        "uv run ruff check tests/test_phase45_project_semantic_scope_lock.py",
        "uv run pyright --project pyrightconfig.tests.json",
        "uv run pytest tests/test_phase45_project_semantic_scope_lock.py",
        "Gate 3 must not run local validation",
    ):
        assert required in docs, required

    assert _git_status_paths().issubset(ALLOWED_SLICE1_GATE2_PATHS)


def test_phase45_forbidden_surfaces_and_release_boundaries_are_locked() -> None:
    docs = _docs()
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject

    for required in (
        "project IR",
        "project SQL",
        "`emit-sql --project`",
        "`explain --project`",
        "imports/modules/export behavior",
        "JOIN/relationship query behavior",
        "runtime/database/db introspection",
        "Arrow/PyArrow",
        "LSP/UI",
        "release/tag/publish/upload/signing/attestation",
        "package version change",
        "external plugin adoption",
        "external scripts/hooks/MCP configs",
        "copied external code",
        "Slice 1 changes no production source",
        "no source behavior, no CLI behavior, no JSON behavior, and no semantic implementation",
        "Slice 1 does not add or change `src/**`",
    ):
        assert required in docs, required

    assert _git_diff_name_only(FORBIDDEN_DIFF_PATHS) == ""
    assert _git_status_paths().issubset(ALLOWED_SLICE1_GATE2_PATHS)


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
