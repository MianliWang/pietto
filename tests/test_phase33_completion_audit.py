from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import cast

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-33-json-v2-and-project-multifile.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
PROJECT_CONFIG_SOURCE_PATH = REPO_ROOT / "src/pietto/_project/config.py"
PROJECT_CHECK_SOURCE_PATH = REPO_ROOT / "src/pietto/_project/check.py"

STATUS_DOCS = (AGENTS_PATH, PIETTO_SPEC_PATH)

PHASE33_ARTIFACTS = (
    "docs/spec/phase-33-json-v2-project-multifile-boundary-v1.md",
    "docs/spec/project-json-v2-result-envelope-v1.md",
    "docs/spec/project-root-config-path-discovery-v1.md",
    "docs/spec/project-explain-metadata-aggregation-boundary-v1.md",
    "src/pietto/_project/__init__.py",
    "src/pietto/_project/model.py",
    "src/pietto/_project/discovery.py",
    "src/pietto/_project/json_v2.py",
    "tests/test_phase33_candidate_decision.py",
    "tests/test_phase33_json_v2_project_envelope_contract.py",
    "tests/test_phase33_project_root_config_path_discovery_contract.py",
    "tests/test_phase33_private_project_discovery_model.py",
    "tests/test_phase33_project_check_cli.py",
    "tests/test_phase33_project_json_v2_serializer.py",
    "tests/test_phase33_project_explain_metadata_contract.py",
    "tests/test_phase33_cli_package_compatibility_hardening.py",
    "scripts/package_smoke.py",
)

PHASE33_SLICE_STATUS = (
    "Phase 33 Slice 1 Candidate Decision, Scope, Boundary, And Phase 32 "
    "Handoff Audit is complete",
    "Phase 33 Slice 2 JSON v2 Project Result Envelope Contract is complete",
    "Phase 33 Slice 3 Project Root, Config, Path, And Discovery Contract "
    "Reconciliation is complete",
    "Phase 33 Slice 4 Private Project Discovery Model MVP is complete",
    "Phase 33 Slice 5 Project Check CLI MVP is complete",
    "Phase 33 Slice 6 JSON v2 Serializer MVP is complete",
    "Phase 33 Slice 7 Project Explain/Metadata Aggregation Contract is complete",
    "Phase 33 Slice 8 CLI, Package Smoke, Docs, And Compatibility Hardening is complete",
    "Phase 33 Slice 9 Completion Audit And Status Lock is complete",
)

PHASE33_COMPLETION_STATUS = (
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
    "Phase 34 has not started",
    "Package version remains `0.1.0`",
    "No tag/release/publish/upload/signing/attestation occurred",
)

PHASE34_COMPLETION_STATEMENT = (
    "Phase 34 Relationship Grain And Narrow JOIN readiness foundation is "
    "complete as docs/spec/static-audit/status-only work"
)
PHASE35_COMPLETION_STATEMENT = (
    "Phase 35 Developer Experience And Delivery Pipeline MVP is complete"
)
PHASE35_SLICE1_LOCK = (
    "Phase 35 Slice 1 remains complete at `cd6a727989f3ba47ea9e7dcd7c04b6a2a7cb1071`"
)
CURRENT_STATUS_DOC_TEXT = (
    *PHASE33_COMPLETION_STATUS[:-3],
    PHASE34_COMPLETION_STATEMENT,
    "The original behavior MVP remains future implementation deferred",
    PHASE35_COMPLETION_STATEMENT,
    PHASE35_SLICE1_LOCK,
    "Safe Simplification remains a scoped discipline",
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

LOCKED_PHASE33_SURFACES = {
    "project_private": (
        "src/pietto/_project",
        33,
        "db84f12bf9bf619e9b364bb29017789adcffa9ea5c0d73149aa4ff6a7c0af0ed",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "310c07a1a5c9ae53f878b143b9d5dc3b092bfdfa072728ee4cae168e361907ec",
    ),
    "package_smoke": (
        "scripts/package_smoke.py",
        1,
        "9df83ad4944b2fffa46e4a5d5608f0868e7c556feb739703f0862fec452a3aa1",
    ),
    "phase33_plan": (
        "docs/plan/phase-33-json-v2-and-project-multifile.md",
        1,
        "832c753c939668ab60dc28b8db69ea7cba0d5d342b06d9393af261ed2a57df01",
    ),
    "readme": (
        "README.md",
        1,
        "e596420f109516076de0af8b1a54652ec985e4e48213f6641bd73e50360ef0ab",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "4691169dd8550dea14ecdb987c6761ecf497e9c10a8a8028b0711ad4cc2150e9",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "1f72dbb5ea404ee3520fd3cce7ab405b1b222784ef9b4ec581e4d1e42697ecfc",
    ),
}

RELATION_SOURCE = (
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


def test_phase33_artifacts_and_slice_status_are_complete() -> None:
    plan = _normalized(PLAN_PATH)

    for relative_path in PHASE33_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path
    for required in PHASE33_SLICE_STATUS:
        assert required in plan, required
    for required in PHASE33_COMPLETION_STATUS:
        assert required in plan, required

    assert "Phase 33 as a whole is not complete" not in plan
    assert "Phase 33 Slice 9 has not started" not in plan


def test_status_docs_record_phase33_completion_and_phase34_boundary() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in (
            *PHASE33_SLICE_STATUS[3:],
            *CURRENT_STATUS_DOC_TEXT,
            *ROADMAP_STATUS,
        ):
            assert required in status, f"{path}: missing {required!r}"

        for stale in (
            "Phase 33 as a whole is not complete",
            "Phase 33 Slice 9 has not started",
            "Phase 34 has not started",
            "Phase 34: Semantic Graph / ERD / AI Metadata Export MVP",
            "Semantic Graph / ERD / AI Metadata Export: Phase",
        ):
            assert stale not in status, f"{path}: stale {stale!r}"


def test_project_check_text_and_json_v2_are_parse_only_for_project_check(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root_with_source(tmp_path)

    assert cli.main(["check", "--project", str(root)]) == 0
    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""
    assert str(root) not in captured.out

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 0
    document = _read_json_document(capsys)
    assert document == {
        "schema_version": 2,
        "command": "check",
        "mode": "project",
        "ok": True,
        "project": {
            "root": ".",
            "config_path": "pietto.toml",
        },
        "inputs": [
            {
                "path": "models/user.pietto",
                "kind": "source",
                "status": "parsed",
            }
        ],
        "diagnostics": [],
        "cli_errors": [],
        "result": {
            "check": {
                "files_total": 1,
                "files_ok": 1,
                "files_with_errors": 0,
            }
        },
    }
    assert str(root) not in json.dumps(document)


def test_single_file_json_v1_and_artifact_v1_remain_separate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    check_source = _write(tmp_path, "valid.pietto", "shape User:\n    id: Int\n")
    relation_source = _write(tmp_path, "active_users.pietto", RELATION_SOURCE)

    assert cli.main(["check", str(check_source), "--format", "json"]) == 0
    check_document = _read_json_document(capsys)
    assert check_document["schema_version"] == 1
    assert check_document["command"] == "check"
    assert "mode" not in check_document

    assert (
        cli.main(
            [
                "emit-sql",
                str(relation_source),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )
    emit_document = _read_json_document(capsys)
    assert emit_document["schema_version"] == 1
    assert emit_document["command"] == "emit-sql"
    assert "mode" not in emit_document

    assert cli.main(["explain", str(relation_source), "--format", "json"]) == 0
    explain_document = _read_json_document(capsys)
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert explain_document["command"] == "explain"
    assert "metadata" in explain_document
    assert "mode" not in explain_document


@pytest.mark.parametrize("command", ["emit-sql", "explain"])
def test_project_flags_remain_rejected_outside_check(
    command: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path)

    assert cli.main([command, "--project", str(root)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: pietto" in captured.err


def test_package_smoke_keeps_installed_project_check_coverage() -> None:
    smoke = _read(PACKAGE_SMOKE_PATH)

    for required in (
        '("check", "--project", project_root.as_posix())',
        '("check", "--project", project_root.as_posix(), "--format", "json")',
        "Project check OK: .",
        "Files checked: 1",
        '"schema_version": 2',
        '"mode": "project"',
        '"path": "models/user.pietto"',
        '"status": "parsed"',
        '"files_total": 1',
        '"files_ok": 1',
        "installed CLI project check text",
        "installed CLI project check JSON v2",
    ):
        assert required in smoke, required


def test_deferred_project_runtime_surfaces_remain_absent() -> None:
    project_sources = {
        path: path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src" / "pietto" / "_project").glob("*.py"))
    }
    project_source = "\n".join(project_sources.values())
    project_source_without_config = "\n".join(
        source
        for path, source in project_sources.items()
        if path != PROJECT_CONFIG_SOURCE_PATH
    )
    project_source_without_config_or_check = "\n".join(
        source
        for path, source in project_sources.items()
        if path
        not in {
            PROJECT_CONFIG_SOURCE_PATH,
            PROJECT_CHECK_SOURCE_PATH,
            REPO_ROOT / "src/pietto/_project/path_trust.py",
            REPO_ROOT / "src/pietto/_project/trusted_source.py",
        }
    )
    source_tree = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src" / "pietto").rglob("*.py"))
        if "__pycache__" not in path.parts
    )
    source_tree_without_config_or_check = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src" / "pietto").rglob("*.py"))
        if (
            "__pycache__" not in path.parts
            and path not in {PROJECT_CONFIG_SOURCE_PATH, PROJECT_CHECK_SOURCE_PATH}
        )
    )
    cli_source = _read(REPO_ROOT / "src" / "pietto" / "cli.py")

    for forbidden in (
        ".glob(",
        ".rglob(",
    ):
        assert forbidden not in project_source

    for forbidden in (
        "tomllib",
        "read_text(",
        "read_bytes(",
    ):
        assert forbidden not in project_source_without_config

    assert "open(" not in project_source_without_config_or_check

    for forbidden in (
        "configured_source_selection",
        "compile_project",
        "project_explain",
        "explain_project",
        "aggregate_project_metadata",
        "metadata_aggregation",
        "schema_introspection",
        "db_pull",
    ):
        assert forbidden not in source_tree

    assert "load_project_config" not in source_tree_without_config_or_check
    assert '"--project"' not in _configure_parser_source(cli_source, "emit_sql")
    assert '"--project"' not in _configure_parser_source(cli_source, "explain")


def test_package_version_release_and_later_phase_boundaries_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    combined_status = " ".join(_normalized(path) for path in STATUS_DOCS)

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    for required in ROADMAP_STATUS:
        assert required in combined_status, required
    assert "Phase 34 has not started" not in combined_status
    assert PHASE34_COMPLETION_STATEMENT in combined_status
    assert PHASE35_COMPLETION_STATEMENT in combined_status
    assert PHASE35_SLICE1_LOCK in combined_status
    assert (
        "Phase 34: Semantic Graph / ERD / AI Metadata Export MVP" not in combined_status
    )


def test_phase33_locked_surfaces_are_unchanged() -> None:
    for label, (
        relative_path,
        expected_count,
        expected_hash,
    ) in LOCKED_PHASE33_SURFACES.items():
        paths = _paths(REPO_ROOT / relative_path)
        assert len(paths) == expected_count, label
        assert _digest(paths) == expected_hash, label


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _read_json_document(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _project_root(path: Path, *, config_text: str = "") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "pietto.toml").write_text(config_text, encoding="utf-8")
    return path


def _project_root_with_source(path: Path) -> Path:
    root = _project_root(
        path,
        config_text=(
            'schema_version = 1\n\n[sources]\ninclude = ["models/*.pietto"]\n'
        ),
    )
    _write(root, "models/user.pietto", "shape User:\n    id: Int\n")
    return root


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _configure_parser_source(cli_source: str, parser_name: str) -> str:
    start = cli_source.index(f"def _configure_{parser_name}_parser")
    end = cli_source.index("\n\ndef ", start + 1)
    return cli_source[start:end]


def _paths(path: Path) -> tuple[Path, ...]:
    if path.is_file():
        return (path,)
    return tuple(
        sorted(
            child
            for child in path.rglob("*")
            if (
                child.is_file()
                and "__pycache__" not in child.parts
                and child.suffix != ".pyc"
            )
        )
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
