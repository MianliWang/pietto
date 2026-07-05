from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "docs/spec/project-explain-metadata-aggregation-boundary-v1.md"
PLAN_PATH = REPO_ROOT / "docs/plan/phase-33-json-v2-and-project-multifile.md"
README_PATH = REPO_ROOT / "README.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"

STATUS_DOCS = (README_PATH, AGENTS_PATH, PIETTO_SPEC_PATH)

_RELATION_SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
    "table active_users:\n"
    "    from users\n"
    "    where active == true\n"
    "    select:\n"
    "        id\n"
    "        email\n"
)


def test_slice7_contract_is_static_boundary_only() -> None:
    spec = _normalized(SPEC_PATH)
    plan = _normalized(PLAN_PATH)

    assert SPEC_PATH.is_file()
    for required in (
        "Phase 33 Slice 7 contract",
        "Slice 7 is contract-only",
        "no source implementation",
        "no CLI parser change",
        "no project explain runtime",
        "no source selection",
        "no TOML schema parser",
        "no glob expansion",
        "no source reading or parsing",
        "no multi-file semantic analysis",
        "no metadata aggregation",
        "pietto check --project ROOT",
        "pietto check --project ROOT --format json",
        "That behavior validates only the explicit project root and direct "
        "`pietto.toml` presence",
    ):
        assert required in spec, required

    for required in (
        "Phase 33 Slice 7 Project Explain/Metadata Aggregation Contract is complete",
        "Slice 7 adds only project explain/metadata aggregation boundary contract",
        "Phase 33 Slice 8 CLI, Package Smoke, Docs, And Compatibility Hardening is complete",
        "Phase 33 Slice 9 Completion Audit And Status Lock is complete",
        "Phase 33 JSON v2 And Project / Multi-file MVP is complete",
    ):
        assert required in plan, required


def test_project_explain_and_emit_sql_project_modes_remain_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path)

    for command in ("explain", "emit-sql"):
        assert cli.main([command, "--project", str(root)]) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "usage: pietto" in captured.err


def test_project_check_json_v2_remains_root_config_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, config_text="not valid = [")

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    document = _read_json_document(capsys)
    assert document["schema_version"] == 2
    assert document["command"] == "check"
    assert document["mode"] == "project"
    assert document["ok"] is False
    assert document["project"] == {"root": ".", "config_path": "pietto.toml"}
    assert document["inputs"] == []
    assert document["diagnostics"] == []
    cli_errors = cast(list[dict[str, object]], document["cli_errors"])
    assert len(cli_errors) == 1
    assert cli_errors[0]["kind"] == "config_parse"
    assert "Project configuration TOML is invalid" in cast(
        str, cli_errors[0]["message"]
    )
    assert cli_errors[0]["path"] == "pietto.toml"
    assert document["result"] == {
        "check": {
            "files_total": 0,
            "files_ok": 0,
            "files_with_errors": 0,
        }
    }
    for forbidden in ("artifact", "metadata", "path"):
        assert forbidden not in document


def test_artifact_v1_remains_single_file_and_json_v1_compatible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write(tmp_path, "active_users.pietto", _RELATION_SOURCE)

    assert cli.main(["explain", str(source_path), "--format", "json"]) == 0

    document = _read_json_document(capsys)
    assert document["artifact"] == "Semantic Metadata Artifact v1"
    assert document["schema_version"] == 1
    assert document["command"] == "explain"
    assert document["path"] == str(source_path)
    assert "metadata" in document
    assert "mode" not in document
    assert "project" not in document
    assert "inputs" not in document
    assert "result" not in document


def test_contract_locks_future_json_v2_extension_boundaries() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`pietto check --project ROOT --format json`",
        "top-level `artifact`",
        "top-level `metadata`",
        "If project explain JSON is approved later",
        'command: "explain"',
        'mode: "project"',
        "result.explain",
        "Future project explain metadata belongs under command-specific "
        "`result.explain`",
        "not under top-level `metadata` and not under `result.check`",
    ):
        assert required in spec, required


def test_contract_records_project_metadata_prerequisites() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "configured source selection from pietto.toml",
        "TOML schema parsing and validation",
        "glob expansion and deterministic ordered source inputs",
        "source reading and parser aggregation",
        "project-wide semantic gating",
        "per-file metadata build after successful parse, semantic analysis, and IR",
        "project JSON v2 input states beyond []",
        "project resource budgets",
        "Metadata aggregation must not emit partial project metadata after blocking "
        "failures",
    ):
        assert required in spec, required


def test_no_project_metadata_aggregation_source_surface_was_added() -> None:
    source_paths = tuple(
        path
        for path in (REPO_ROOT / "src").rglob("*.py")
        if "__pycache__" not in path.parts
    )
    joined_paths = "\n".join(
        path.relative_to(REPO_ROOT).as_posix() for path in source_paths
    )
    joined_text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for forbidden in (
        "project_explain",
        "explain_project",
        "metadata_aggregation",
        "project_metadata",
    ):
        assert forbidden not in joined_paths
        assert forbidden not in joined_text

    cli_text = (REPO_ROOT / "src" / "pietto" / "cli.py").read_text(encoding="utf-8")
    explain_parser_start = cli_text.index("def _configure_explain_parser")
    explain_parser_end = cli_text.index("def _build_check_json_parser")
    explain_parser = cli_text[explain_parser_start:explain_parser_end]
    assert "--project" not in explain_parser


def test_status_docs_record_slice7_completion_and_roadmap_lock() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in (
            "Phase 33 Slice 7 Project Explain/Metadata Aggregation Contract is complete",
            "project explain / metadata aggregation boundary contract",
            "Phase 33 did not implement source selection, TOML schema parsing",
            "project emit-sql, project explain, metadata aggregation",
            "Phase 33 Slice 8 CLI, Package Smoke, Docs, And Compatibility Hardening is complete",
            "Phase 33 Slice 9 Completion Audit And Status Lock is complete",
            "Phase 33 JSON v2 And Project / Multi-file MVP is complete",
            "Phase 34 Relationship Grain And Narrow JOIN readiness foundation is "
            "complete as docs/spec/static-audit/status-only work",
            "Phase 35 Developer Experience And Delivery Pipeline MVP is complete",
            "Phase 35 Slice 1 remains complete at "
            "`cd6a727989f3ba47ea9e7dcd7c04b6a2a7cb1071`",
            "Phase 34: Relationship Grain And Narrow JOIN MVP",
            "Phase 35: Developer Experience And Delivery Pipeline MVP",
            "Phase 36: Post-v0.2 Core Type System Expansion MVP",
            "Phase 37: Post-v0.2 Aggregate Surface Expansion MVP",
            "Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 "
            "deferred candidate without an assigned phase number",
        ):
            assert required in status, f"{path}: missing {required!r}"
        assert "Phase 34 has not started" not in status, path

        for stale in (
            "Phase 33 Slice 7 has not started",
            "Phase 33 Slice 8 has not started",
            "Phase 33 Slice 9 has not started",
            "Phase 33 as a whole is not complete",
            "Phase 34: Semantic Graph / ERD / AI Metadata Export MVP",
            "Semantic Graph / ERD / AI Metadata Export: Phase",
        ):
            assert stale not in status, f"{path}: stale {stale!r}"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _project_root(path: Path, *, config_text: str = "") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "pietto.toml").write_text(config_text, encoding="utf-8")
    return path


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _read_json_document(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))
