from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-33-json-v2-and-project-multifile.md"
SPEC_PATH = REPO_ROOT / "docs/spec/project-root-config-path-discovery-v1.md"
ENVELOPE_SPEC_PATH = REPO_ROOT / "docs/spec/project-json-v2-result-envelope-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_IMPLEMENTATION_PATHS = (
    "src/pietto/project.py",
    "src/pietto/project",
    "src/pietto/config.py",
    "src/pietto/project_config.py",
    "src/pietto/project_discovery.py",
    "src/pietto/json_v2.py",
    "src/pietto/_project.py",
    "src/pietto/_json_v2.py",
    "src/pietto/database.py",
    "src/pietto/runtime.py",
    "src/pietto/schema_introspection.py",
)


def test_slice3_contract_artifacts_and_plan_status_are_present() -> None:
    spec = _normalized(SPEC_PATH)
    plan = _normalized(PLAN_PATH)
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    assert SPEC_PATH.is_file()
    assert project["version"] == "0.1.0"

    for required in (
        "Phase 33 Slice 3 Project Root, Config, Path, And Discovery Contract "
        "Reconciliation is complete as docs/spec/static-audit/status-only work",
        "docs/spec/project-root-config-path-discovery-v1.md",
        "tests/test_phase33_project_root_config_path_discovery_contract.py",
        "Slice 3 adds no source implementation, no CLI behavior, no project "
        "CLI, no `--project` parser behavior",
    ):
        assert required in plan, required

    for required in (
        "This document reconciles the Phase 33 Slice 3 contract",
        "The contract is not implemented",
        "Slice 3 is docs/spec/static-audit/status-only work",
    ):
        assert required in spec, required


def test_explicit_invocation_and_configless_modes_are_rejected() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Future project mode starts only through",
        "--project ROOT",
        "explicit `--project ROOT`",
        "required `pietto.toml`",
        "no implicit parent search",
        "no configless project mode",
        "no hidden global config",
        "no environment configuration",
        "no auto-discovery",
        "no positional directory project inference",
        "Slice 3 does not implement `--project`",
    ):
        assert required in spec, required


def test_project_root_and_config_failure_boundaries_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`ROOT` must be explicit",
        "`ROOT` must resolve to a directory",
        "`ROOT` must be normalized deterministically",
        "`ROOT` must be normalized/canonicalized deterministically only for "
        "containment and file identity checks",
        "failure to resolve or access `ROOT` is a `project_root` cli_error",
        "project root failures use exit `2`",
        "project root failures stop before parse",
        'The JSON v2 root identity remains logical `"."`',
        "Canonical absolute project roots must not leak into JSON v2 by default",
        "`project.root` and `project.config_path` may be `null`",
        "`schema_version` is required",
        "unsupported config versions fail closed",
        "invalid TOML syntax is a `config_parse` CLI error",
        "schema-invalid config is a `config_schema` CLI error",
        "config read, parse, and schema failures use exit `2`",
        "config read, parse, and schema failures stop before parse",
        "Config read/parse/schema failures are `cli_errors`, exit `2`, and "
        "stop before parse",
        "Slice 3 does not implement TOML parsing, config loading",
        "TOML loader",
    ):
        assert required in spec, required


def test_source_discovery_and_path_policy_are_deterministic() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "configured source selection only",
        "Historical `[sources].include` and `[sources].exclude` names are "
        "referenced only as the planned configuration shape",
        "deterministic file discovery/reporting",
        "normalized project-relative paths",
        "root-contained source selection",
        "`/` separators in reported paths",
        "stable sorting by normalized project-relative path",
        "containment checks before reading source bytes",
        "duplicate physical identity rejection",
        "no hidden traversal outside root",
        "no filesystem enumeration order dependency",
        "no hash-map order dependency",
        "no inode order dependency",
        "no locale order dependency",
        "no modification-time order dependency",
        "An empty final source set is a project input error",
    ):
        assert required in spec, required

    for required in (
        "JSON v2 input paths are not absolute paths",
        "JSON v2 input paths do not contain `..` escape segments",
        "JSON v2 input paths do not leak platform-specific separators",
        "JSON v2 input paths do not leak canonical absolute roots by default",
        "symlink and canonicalization policy must reject duplicate physical identity",
        "filesystem enumeration order must not affect output order",
    ):
        assert required in spec, required


def test_failure_policy_and_json_v2_envelope_compatibility_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    envelope = _normalized(ENVELOPE_SPEC_PATH)

    for required in (
        "root/config/path errors are `cli_errors`, exit `2`, and stop before parse",
        "source-read errors are `cli_errors`, exit `2` for affected input",
        "parser errors are compiler diagnostics, exit `1`, and block project "
        "semantic analysis",
        "semantic errors are compiler diagnostics, exit `1`, and block project IR",
        "IR errors are diagnostics or internal failure reporting as separately "
        "contracted, exit `1`, and block SQL",
        "no partial SQL output",
        "no partial metadata output by default",
        "Root, config, path, source-read, and project resource failures belong "
        "in `cli_errors`",
        "Parser and semantic compiler failures belong in `diagnostics`",
        "v2-only `related_locations` field",
        "machine-readable JSON v2 failure envelope",
    ):
        assert required in spec, required

    for required in (
        "schema_version, command, mode, ok, project, inputs, diagnostics, "
        "cli_errors, result",
        "result.check.files_total",
        "result.check.files_ok",
        "result.check.files_with_errors",
    ):
        assert required in envelope, required


def test_single_file_surfaces_and_artifact_v1_remain_unchanged() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`pietto check --format json` remains single-file CLI JSON v1",
        "`pietto emit-sql --format json` remains single-file CLI JSON v1",
        "`pietto explain --format json` remains Semantic Metadata Artifact v1",
        "Single-file CLI JSON v1 remains unchanged",
        "Semantic Metadata Artifact v1 remains unchanged",
        "single-file `check` behavior remains unchanged",
        "single-file `emit-sql` behavior remains unchanged",
        "single-file `explain` behavior remains unchanged",
        "The Slice 2 Project JSON v2 result envelope remains unchanged",
        "it does not mutate the envelope top-level fields",
        "diagnostic fields, CLI error separation, or compatibility boundaries",
    ):
        assert required in spec, required


def test_deferrals_roadmap_and_forbidden_implementation_paths_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "project discovery runtime",
        "TOML parser implementation",
        "config loader implementation",
        "project loader implementation",
        "project CLI implementation",
        "`--project` parser behavior",
        "JSON v2 serializer implementation",
        "multi-file semantic analysis",
        "imports/includes/modules",
        "cross-file references",
        "dependency graph",
        "SQL artifacts",
        "metadata aggregation",
        "relationship/JOIN behavior",
        "runtime behavior",
        "database behavior",
        "schema introspection",
        "database pull",
        "Semantic Graph / ERD / AI Metadata Export",
        "Phase 34 work",
        "Phase 35 work",
        "Phase 36 work",
        "Phase 37 work",
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
