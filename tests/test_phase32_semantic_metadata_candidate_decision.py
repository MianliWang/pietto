from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from pietto import cli_json

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-32-semantic-explain-and-metadata-output.md"
SPEC_PATH = REPO_ROOT / "docs/spec/semantic-metadata-artifact-candidate-decision-v1.md"
README_PATH = REPO_ROOT / "README.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
CLI_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/cli-json-v1.md"

STATUS_DOCS = (README_PATH, AGENTS_PATH, PIETTO_SPEC_PATH)
STALE_PHASE32_NOT_STARTED = "Phase 32 remains post-v0.2 and has not started"


def test_phase32_slice1_artifacts_and_handoff_are_locked() -> None:
    combined = _phase32_docs()
    project = cast(dict[str, Any], _pyproject()["project"])

    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert project["version"] == "0.1.0"

    for required in (
        "Phase 32 Slice 1 is complete as Candidate Decision, Roadmap Alignment, "
        "And v0.2 Handoff Audit work only",
        "trusted baseline HEAD is `a2677114269f98c24c250376b3626a7f0178038c`",
        "Phase 31 complete",
        "Pietto v0.2 single-file stable complete",
        "Phase 32 has started",
        "Phase 32 as a whole is not complete",
        "package version remains `0.1.0`",
        "Slice 1 performs no package version bump, release tag, package release, "
        "publishing, upload, signing, or attestation operation",
    ):
        assert required in combined, required

    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in (
            "Phase 31 complete",
            "Pietto v0.2 single-file stable complete",
            "Phase 32 has started",
            "Phase 32 Slice 1 Candidate Decision, Roadmap Alignment, And v0.2 "
            "Handoff Audit is complete as docs/spec/static-audit/status-only work",
            "Phase 32 as a whole is not complete",
            "Package version remains `0.1.0`",
        ):
            assert required in status, f"{path}: missing {required!r}"
        assert STALE_PHASE32_NOT_STARTED not in status, (
            f"{path}: stale current-status phrase {STALE_PHASE32_NOT_STARTED!r}"
        )


def test_phase32_selected_direction_and_roadmap_are_locked() -> None:
    combined = _phase32_docs()

    for required in _roadmap_contracts():
        assert required in combined, f"{PLAN_PATH} or {SPEC_PATH}: missing {required!r}"

    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in _roadmap_contracts():
            assert required in status, f"{path}: missing {required!r}"
        assert STALE_PHASE32_NOT_STARTED not in status, (
            f"{path}: stale current-status phrase {STALE_PHASE32_NOT_STARTED!r}"
        )


def test_semantic_metadata_artifact_v1_identity_is_separate_from_json_versions() -> (
    None
):
    combined = _phase32_docs()
    cli_json_v1 = _normalized(CLI_JSON_SPEC_PATH)

    for required in (
        "Semantic Metadata Artifact v1",
        "separate version domain",
        "existing single-file CLI JSON v1",
        "future project-level JSON v2",
        "Semantic Metadata Artifact v1 is not a mutation of CLI JSON v1",
        "Slice 1 does not define exact JSON property names",
    ):
        assert required in combined, required

    assert "JSON schema version 1 remains exclusively single-file" in cli_json_v1
    assert (
        "planned future project-mode interface uses the separate JSON schema version 2"
        in (cli_json_v1)
    )


def test_explain_cli_direction_is_locked_without_json_v1_mutation() -> None:
    combined = _phase32_docs()

    for required in (
        "pietto explain <file> [--format text|json]",
        "The default format is text",
        "JSON is the future normative machine-readable Semantic Metadata Artifact v1",
        "Text is a human-readable renderer derived from the same normalized artifact",
        "`--dialect` for `explain`",
        "`--output` for `explain`",
        "a project flag",
        "database or runtime options",
    ):
        assert required in combined, required

    check_result = cli_json.check_result_to_json_dict(path="input.pietto")
    emit_result = cli_json.emit_sql_result_to_json_dict(
        path="input.pietto",
        dialect="postgres",
    )

    assert tuple(check_result) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "cli_errors",
    )
    assert check_result["schema_version"] == 1
    assert check_result["command"] == "check"
    assert tuple(emit_result) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    )
    assert emit_result["schema_version"] == 1
    assert emit_result["command"] == "emit-sql"


def test_fail_closed_success_and_failure_policy_is_locked() -> None:
    combined = _phase32_docs()

    for required in (
        "parse -> semantic analysis -> existing IR construction -> normalized "
        "metadata artifact",
        "Explain must not invoke SQL lowering",
        "database connections",
        "SQL execution",
        "runtime behavior",
        "Metadata is emitted only after parse, semantic analysis, and IR "
        "construction all succeed",
        "returns diagnostics or error information only",
        "must not expose partial definitions, partial relations, partial schemas, "
        "partial projections, partial aggregates, or partial lineage",
        "Exact JSON envelope field names belong to Slice 2",
    ):
        assert required in combined, required


def test_path_ordering_and_basic_lineage_boundaries_are_locked() -> None:
    combined = _phase32_docs()

    for required in (
        "existing user-supplied string / `str(path)` posture",
        "does not canonicalize paths by default",
        "does not define multi-file ordering",
        "preserves deterministic source/IR order",
        "direct source relation and field provenance for direct field projections",
        "normalized direct field leaves used by currently supported bounded "
        "expressions",
        "normalized direct field leaves used by currently supported aggregate "
        "arguments",
        "must not expose raw `SymbolId`, raw `FieldId`, AST node identity, raw IR "
        "nodes",
        "relationship traversal, JOIN lineage, multi-file lineage, graph lineage",
    ):
        assert required in combined, required


def test_relationship_dialect_deferred_security_and_public_api_boundaries_are_locked() -> (
    None
):
    combined = _phase32_docs()

    for required in (
        "Relationship metadata is not part of Semantic Metadata Artifact v1",
        "Cardinality, direction, optionality, grain, fanout, traversal, and JOIN "
        "remain Phase 34 work",
        "Artifact v1 has no SQL dialect field",
        "Artifact v1 has no global per-program `deferred` field",
        "unsupported behavior remains represented by compiler diagnostics",
        "must not expose connector literal internals, connector configuration "
        "values, credential-like values, secrets, or raw connector implementation "
        "structures",
        "Phase 32 MVP does not add a new public Python API",
    ):
        assert required in combined, required


def test_tooling_release_and_forbidden_surfaces_are_locked() -> None:
    combined = _phase32_docs()
    project = cast(dict[str, Any], _pyproject()["project"])

    assert project["version"] == "0.1.0"

    for required in (
        "Pyright remains the blocking source of truth",
        "does not add `ty`",
        "does not place `ty` in `scripts/validate.py`",
        "does not add a global coverage threshold",
        "does not make generated ANTLR files a coverage target",
        "does not add Hypothesis",
        "does not add deptry/import-linter",
        "does not add mutation testing",
        "does not add nightly jobs",
        "does not add automatic PyPI publication",
        "Slice 1 does not implement `pietto explain`",
        "source behavior, grammar changes, generated changes, semantic changes, "
        "IR changes, SQL changes, diagnostic changes",
    ):
        assert required in combined, required


def test_current_status_docs_record_phase32_slice1_without_rewriting_history() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)

        for required in (
            "Phase 31 complete",
            "Pietto v0.2 single-file stable complete",
            "Phase 32 has started",
            "Phase 32 Slice 1 Candidate Decision, Roadmap Alignment, And v0.2 "
            "Handoff Audit is complete as docs/spec/static-audit/status-only work",
            "Phase 32 as a whole is not complete",
            "Package version remains `0.1.0`",
            "Phase 32 Slice 1 performed no package version bump, tag, release, "
            "publish, upload, signing, or attestation",
            "No `pietto explain` CLI behavior was implemented in Slice 1",
            "Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 "
            "deferred candidate without an assigned phase number",
        ):
            assert required in status, f"{path}: missing {required!r}"

        assert STALE_PHASE32_NOT_STARTED not in status, (
            f"{path}: stale current-status phrase {STALE_PHASE32_NOT_STARTED!r}"
        )


def test_hash_lock_update_plan_is_documented_without_digest_weakening() -> None:
    combined = _phase32_docs()

    for required in (
        "exact digest-only hash-lock updates where status documents changed",
        "file | locked path | old digest | new digest | reason",
        "preserve the existing hash algorithm",
        "preserve path lists",
        "preserve path counts",
        "preserve ordering",
        "preserve helper functions",
        "preserve all unrelated digest values",
    ):
        assert required in combined, required


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _phase32_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def _pyproject() -> dict[str, object]:
    return tomllib.loads(_read(PYPROJECT_PATH))


def _roadmap_contracts() -> tuple[str, ...]:
    return (
        "Phase 32: Semantic Explain And Metadata Output MVP",
        "Phase 33: JSON v2 And Project / Multi-file MVP",
        "Phase 34: Relationship Grain And Narrow JOIN MVP",
        "Phase 35: Developer Experience And Delivery Pipeline MVP",
        "Phase 36: Post-v0.2 Core Type System Expansion MVP",
        "Phase 37: Post-v0.2 Aggregate Surface Expansion MVP",
        "Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 "
        "deferred candidate without an assigned phase number",
    )
