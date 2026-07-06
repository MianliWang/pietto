from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-45-project-wide-semantic-model-mvp.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PROJECT_MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PROJECT_JSON_V2_PATH = REPO_ROOT / "src/pietto/_project/json_v2.py"
CLI_PATH = REPO_ROOT / "src/pietto/cli.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"

PHASE45_TEST_PATHS = (
    "tests/test_phase45_project_semantic_scope_lock.py",
    "tests/test_phase45_project_semantic_input_units.py",
    "tests/test_phase45_project_semantic_model_scaffold.py",
    "tests/test_phase45_project_type_namespace_semantics.py",
    "tests/test_phase45_project_relation_namespace_semantics.py",
    "tests/test_phase45_project_semantic_cli_gate.py",
    "tests/test_phase45_project_json_v2_semantic_diagnostics.py",
    "tests/test_phase45_project_compatibility_hardening.py",
    "tests/test_phase45_completion_audit.py",
)

PRIVATE_FACT_MARKERS = (
    "ProjectSymbol",
    "catalog",
    "type_resolutions",
    "source_shape_resolutions",
    "relation_resolutions",
)


def _phase45_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_phase45_identity_route_and_completion_status_are_locked() -> None:
    docs = _phase45_docs()

    for required in (
        "Project-wide Semantic Model Design And MVP",
        "Phase 45 Slice 10 is `Completion audit and status lock`",
        "Slice 10 is docs/tests/static-audit/status-lock only",
        "Phase 45 is complete after Slice 10",
        "Gate 3 commit, push, and natural CI proof remain separate",
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
    ):
        assert required in docs, required


def test_phase45_required_test_artifacts_exist() -> None:
    for relative_path in PHASE45_TEST_PATHS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_phase45_delivered_boundaries_are_documented_and_locked() -> None:
    docs = _phase45_docs()

    for required in (
        "parsed project semantic input units",
        "private project semantic model scaffold",
        "project catalog and duplicate detection",
        "cross-file type namespace semantics",
        "cross-file relation namespace semantics",
        "project text semantic CLI gate",
        "Project JSON v2 semantic diagnostics",
        "compatibility hardening",
        "completion audit and status lock",
        "requires a true private project-wide semantic model",
        "one project-wide semantic environment/model",
    ):
        assert required in docs, required


def test_private_project_semantic_model_boundary_remains_private() -> None:
    assert PROJECT_MODEL_PATH.is_file()
    model_source = _read(PROJECT_MODEL_PATH)
    json_v2_source = _read(PROJECT_JSON_V2_PATH)
    docs = _phase45_docs()

    for required in (
        "class ProjectSemanticCatalog",
        "class ProjectSemanticModel",
        "class ProjectSemanticResult",
        "class ProjectSymbol",
        "type_resolutions",
        "source_shape_resolutions",
        "relation_resolutions",
        "def build_empty_project_semantic_result",
    ):
        assert required in model_source, required

    for forbidden in PRIVATE_FACT_MARKERS:
        assert forbidden not in json_v2_source, forbidden

    for required in (
        "Private project semantic facts remain private and un-serialized",
        "Project JSON v2 does not expose the private catalog",
        "`ProjectSymbol`",
        "`type_resolutions`",
        "`source_shape_resolutions`",
        "`relation_resolutions`",
    ):
        assert required in docs, required


def test_project_json_v2_completion_boundary_is_locked() -> None:
    docs = _phase45_docs()
    json_v2_source = _read(PROJECT_JSON_V2_PATH)

    for required in (
        "Semantic diagnostics remain top-level `diagnostics[]`",
        "`cli_errors[]` remains project/config/source-selection/source-read only",
        "`inputs[]` and `result.check` remain read/parse based",
        "no semantic input statuses or semantic file counters are introduced",
        "No new Project JSON v2 fields",
    ):
        assert required in docs, required

    for required in (
        "semantic_diagnostics",
        '"ok": result.ok and not _has_error_diagnostics(semantic_diagnostics)',
        "diagnostics.extend(semantic_diagnostics)",
        '"cli_errors": [_cli_error_to_json_dict(error) for error in result.errors]',
        '"inputs": inputs',
        '"check": counters',
        "def _check_counters",
        '"files_total": len(inputs)',
        '"files_ok": files_ok',
        '"files_with_errors": files_with_errors',
    ):
        assert required in json_v2_source, required


def test_cli_project_and_single_file_boundaries_are_locked() -> None:
    docs = _phase45_docs()
    cli_source = _read(CLI_PATH)

    for required in (
        "`pietto check --project ROOT` text mode runs private project semantic checks after parse success",
        "JSON mode computes the private project semantic result after parse success",
        "Parse/project errors short-circuit semantic checks",
        "Valid project text checks keep the existing `Project check OK: .`",
        "Single-file `check`, CLI JSON v1, `emit-sql`, and `explain` remain separate and unchanged",
        "Project `emit-sql` and project `explain` remain unsupported or absent",
    ):
        assert required in docs, required

    for required in (
        "build_empty_project_semantic_result(parse_result)",
        "project_check_result_to_json_dict(",
        "semantic_diagnostics=semantic_result.diagnostics",
        "Project check OK: .",
        "Files checked:",
        "def _run_check",
        "def _run_emit_sql",
        "def _run_explain",
    ):
        assert required in cli_source, required


def test_forbidden_project_surfaces_remain_locked() -> None:
    docs = _phase45_docs()
    model_source = _read(PROJECT_MODEL_PATH)

    for required in (
        "No project IR, project SQL, project `emit-sql`, or project `explain` path exists after Phase 45 completion",
        "Project runtime/database execution",
        "DB introspection",
        "Arrow/PyArrow",
        "LSP/UI",
        "imports/modules/export behavior",
        "JOIN/relationship query behavior",
        "relation cycle detection",
        "row schema propagation",
        "projection/body semantic validation",
    ):
        assert required in docs, required

    for forbidden in (
        "from pietto import semantic",
        "import pietto.semantic",
        "emit_postgres_sql",
        "emit_mysql_sql",
        "build_ir",
        "ScriptIR",
        "RelationIR",
    ):
        assert forbidden not in model_source, forbidden


def test_parser_package_release_and_dependabot_boundaries_are_locked() -> None:
    docs = _phase45_docs()
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject

    for required in (
        "Slice 10 changes no parser public API",
        "grammar",
        "generated parser artifact",
        "package version",
        "workflow",
        "dependency file",
        "package metadata",
        "tag, release, publish, upload, signing, attestation",
        "Dependabot policy maintenance is separate from Phase 45 completion",
        "Slice 10 requires no `.github/dependabot.yml`, `pyproject.toml`, `uv.lock`, or workflow edit",
    ):
        assert required in docs, required

    for forbidden in (
        "tag created",
        "release created",
        "package release occurred",
        "published package",
        "uploaded package",
        "signing completed",
        "attestation completed",
    ):
        assert forbidden not in docs.lower(), forbidden


def test_package_smoke_policy_remains_success_read_parse_only() -> None:
    docs = _phase45_docs()
    package_smoke_source = _read(PACKAGE_SMOKE_PATH)

    for required in (
        "Package smoke policy remains success/read-parse smoke only for project mode",
        "Semantic-error Project JSON compatibility remains focused in-process test coverage, not package-smoke expansion",
    ):
        assert required in docs, required

    for required in (
        '("check", "--project", project_root.as_posix())',
        '("check", "--project", project_root.as_posix(), "--format", "json")',
    ):
        assert required in package_smoke_source, required

    for semantic_error_marker in (
        "PIE-S2001",
        "PIE-S2002",
        "PIE-S2301",
        "PIE-S2303",
        "semantic-error",
        "ProjectSymbol",
        "type_resolutions",
        "source_shape_resolutions",
        "relation_resolutions",
    ):
        assert semantic_error_marker not in package_smoke_source
