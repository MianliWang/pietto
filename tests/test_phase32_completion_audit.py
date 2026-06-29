from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-32-semantic-explain-and-metadata-output.md"
README_PATH = REPO_ROOT / "README.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"

STATUS_DOCS = (README_PATH, AGENTS_PATH, PIETTO_SPEC_PATH)

PHASE32_SLICE_STATUS = (
    "Phase 32 Slice 1 is complete as Candidate Decision, Roadmap Alignment, "
    "And v0.2 Handoff Audit work only",
    "Phase 32 Slice 2 is complete as Semantic Metadata Artifact v1 Contract work only",
    "Phase 32 Slice 3 is complete as Private Metadata Model And Builder MVP work only",
    "Phase 32 Slice 4 is complete as Definition, Schema, Type, And "
    "Nullability Metadata work only",
    "Phase 32 Slice 5 is complete as Query Posture, Aggregate, And Basic "
    "Lineage Metadata work only",
    "Phase 32 Slice 6 is complete as JSON Serializer And Fail-closed Error "
    "Envelope work only",
    "Phase 32 Slice 7 is complete as Explain CLI Text/JSON Integration, "
    "Docs, Examples, And Package Smoke Readiness work only",
    "Phase 32 Slice 8 is complete as Completion Audit And Status Lock work only",
)

PLAN_FINAL_STATUS_TEXT = (
    "Phase 32 Slice 8 Completion Audit And Status Lock is complete",
    "Phase 32 Semantic Explain And Metadata Output MVP is complete",
    "Slice 8 completes completion audit and status lock only",
    "`pietto explain <file> [--format text|json]` is available",
    "Semantic Metadata Artifact v1 JSON is available through `pietto explain "
    "--format json`",
    "package version remains `0.1.0`",
    "no package release/tag/publish/upload/signing/attestation occurred",
    "no JSON v2/project/multi-file behavior was started",
    "no relationship/JOIN/graph/runtime/database/schema-introspection behavior "
    "was started",
    "Phase 33 has not started",
)

PHASE34_COMPLETION_STATEMENT = (
    "Phase 34 Relationship Grain And Narrow JOIN readiness foundation is "
    "complete as docs/spec/static-audit/status-only work"
)
PHASE35_ACTIVE_STATEMENT = (
    "Phase 35 is active as Developer Experience And Delivery Pipeline MVP"
)
PHASE35_SLICE1_LOCK = (
    "Phase 35 Slice 1 is complete at `cd6a727989f3ba47ea9e7dcd7c04b6a2a7cb1071`"
)

CURRENT_STATUS_DOC_TEXT = (
    "Phase 32 Slice 8 Completion Audit And Status Lock is complete",
    "Phase 32 Semantic Explain And Metadata Output MVP is complete",
    "Slice 8 completes completion audit and status lock only",
    "`pietto explain <file> [--format text|json]` is available",
    "Semantic Metadata Artifact v1 JSON is available through `pietto explain "
    "--format json`",
    "package version remains `0.1.0`",
    "no package release/tag/publish/upload/signing/attestation occurred",
    "no JSON v2/project/multi-file implementation behavior was added",
    "no relationship/JOIN/graph/runtime/database/schema-introspection behavior "
    "was started",
    "Phase 33 Slice 1, Slice 2, and Slice 3 remain complete, pushed, and CI green",
    "Phase 33 Slice 4 Private Project Discovery Model MVP is complete",
    "Phase 33 Slice 5 Project Check CLI MVP is complete",
    "Phase 33 Slice 6 JSON v2 Serializer MVP is complete",
    "Phase 33 Slice 7 Project Explain/Metadata Aggregation Contract is complete",
    "Phase 33 Slice 8 CLI, Package Smoke, Docs, And Compatibility Hardening is complete",
    "Phase 33 Slice 9 Completion Audit And Status Lock is complete",
    "Phase 33 JSON v2 And Project / Multi-file MVP is complete",
    "Phase 33 delivered a conservative project-mode foundation",
    "private `_project` model/discovery source",
    "text-mode `pietto check --project ROOT` root/config validation",
    "project JSON v2 for `pietto check --project ROOT --format json`",
    "project explain / metadata aggregation boundary contract",
    "package smoke / compatibility hardening",
    "Phase 33 did not implement source selection, TOML schema parsing, glob "
    "expansion, project source reading/parsing, multi-file semantic analysis",
    "project IR/SQL, project emit-sql, project explain, metadata aggregation",
    "relationship/JOIN, runtime/database/schema introspection, db pull, "
    "graph/ERD/AI metadata export",
    PHASE34_COMPLETION_STATEMENT,
    "The original behavior MVP remains future implementation deferred",
    PHASE35_ACTIVE_STATEMENT,
    PHASE35_SLICE1_LOCK,
    "Safe Simplification remains a scoped discipline and future-slice discipline",
    "Package version remains `0.1.0`",
    "No tag/release/publish/upload/signing/attestation occurred",
)

ROADMAP_STATUS = (
    "Phase 33: JSON v2 And Project / Multi-file MVP",
    "Phase 34: Relationship Grain And Narrow JOIN MVP",
    "Phase 35: Developer Experience And Delivery Pipeline MVP",
    "Phase 36: Post-v0.2 Core Type System Expansion MVP",
    "Phase 37: Post-v0.2 Aggregate Surface Expansion MVP",
    "Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 "
    "deferred candidate without an assigned phase number",
)

ARTIFACT_IMPLEMENTATION_FILES = (
    "docs/spec/semantic-metadata-artifact-v1.md",
    "src/pietto/_metadata/model.py",
    "src/pietto/_metadata/builder.py",
    "src/pietto/_metadata/serializer.py",
    "src/pietto/_metadata/text.py",
)

PHASE32_TEST_FILES = (
    "tests/test_phase32_semantic_metadata_candidate_decision.py",
    "tests/test_phase32_semantic_metadata_artifact_contract.py",
    "tests/test_phase32_private_metadata_builder.py",
    "tests/test_phase32_metadata_schema_type_nullability.py",
    "tests/test_phase32_metadata_query_aggregate_lineage.py",
    "tests/test_phase32_metadata_json_serializer.py",
    "tests/test_phase32_explain_cli.py",
)

CLI_JSON_V1_TEST_FILES = (
    "tests/test_cli_check_json.py",
    "tests/test_cli_emit_sql_json.py",
    "tests/test_cli_json.py",
)

FORBIDDEN_PHASE33_PATHS = (
    "src/pietto/project.py",
    "src/pietto/project",
    "src/pietto/json_v2.py",
    "src/pietto/json_v2",
    "src/pietto/_json_v2.py",
    "src/pietto/_project.py",
    "src/pietto/database.py",
    "src/pietto/runtime.py",
    "src/pietto/schema_introspection.py",
)


def test_phase32_plan_records_all_slices_and_phase_completion() -> None:
    plan = _normalized(PLAN_PATH)

    for required in PHASE32_SLICE_STATUS:
        assert required in plan, required
    for required in PLAN_FINAL_STATUS_TEXT:
        assert required in plan, required

    assert "Phase 32 has started. Phase 32 as a whole is not complete." not in plan


def test_status_docs_record_phase32_completion_and_release_boundary() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in CURRENT_STATUS_DOC_TEXT:
            assert required in status, f"{path}: missing {required!r}"
        assert "Phase 33 has not started" not in status, path
        assert "Phase 33 Slice 4 has not started" not in status, path
        assert "Phase 33 Slice 5 has not started" not in status, path
        assert "Phase 33 Slice 6 has not started" not in status, path
        assert "Phase 33 Slice 7 has not started" not in status, path
        assert "Phase 33 Slice 8 has not started" not in status, path
        assert "Phase 33 Slice 9 has not started" not in status, path
        assert "Phase 33 as a whole is not complete" not in status, path
        assert "Phase 34 has not started" not in status, path


def test_artifact_implementation_and_phase32_tests_remain_present() -> None:
    for relative_path in (
        *ARTIFACT_IMPLEMENTATION_FILES,
        *PHASE32_TEST_FILES,
        *CLI_JSON_V1_TEST_FILES,
    ):
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_package_smoke_includes_explain_and_project_check_coverage() -> None:
    smoke = _read(PACKAGE_SMOKE_PATH)

    for required in (
        '("check", "--project", project_root.as_posix())',
        '("check", "--project", project_root.as_posix(), "--format", "json")',
        "Project check OK: .",
        "Files checked: 0",
        '"schema_version": 2',
        '"mode": "project"',
        '"inputs": []',
        '"files_total": 0',
        "installed CLI project check text",
        "installed CLI project check JSON v2",
        '("explain", CHECK_INPUT.as_posix())',
        '("explain", CHECK_INPUT.as_posix(), "--format", "json")',
        "Semantic Metadata Artifact v1",
        "installed CLI explain text",
        "installed CLI explain JSON",
        "metadata",
    ):
        assert required in smoke, required


def test_deferred_roadmap_names_and_graph_deferral_are_locked() -> None:
    combined = " ".join(
        _normalized(path)
        for path in (PLAN_PATH, README_PATH, AGENTS_PATH, PIETTO_SPEC_PATH)
    )

    for required in ROADMAP_STATUS:
        assert required in combined, required

    for stale in (
        "Phase 36: Core Type System Expansion II",
        "Phase 37: Aggregate Expansion II",
        "core type system expansion II: Phase 36",
        "aggregate expansion II: Phase 37",
    ):
        assert stale not in combined, stale

    assert "Semantic Graph / ERD / AI Metadata Export: Phase" not in combined


def test_package_version_remains_010() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    assert project["version"] == "0.1.0"


def test_phase33_and_forbidden_runtime_surfaces_were_not_started() -> None:
    for relative_path in FORBIDDEN_PHASE33_PATHS:
        assert not (REPO_ROOT / relative_path).exists(), relative_path

    src_paths = tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "src" / "pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    forbidden_name_fragments = (
        "json_v2",
        "project_loader",
        "multi_file",
        "schema_introspection",
        "graph_runtime",
    )
    approved_slice6_files = {
        "src/pietto/_project/json_v2.py",
    }

    for relative_path in src_paths:
        for fragment in forbidden_name_fragments:
            if fragment == "json_v2" and relative_path in approved_slice6_files:
                continue
            assert fragment not in relative_path, relative_path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())
