from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from _static_audit_helpers import normalized_text as _normalized

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-45-project-wide-semantic-model-mvp.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md"

_VALID_RELATION_SOURCE = (
    "shape User:\n"
    "    id: Int not null\n"
    "    email: Text not null\n"
    'source users: User is postgres.table("users")\n'
    "table active_users:\n"
    "    from users\n"
    "    select:\n"
    "        id\n"
)


@pytest.mark.parametrize(
    ("source_name", "source_text", "expected_code", "expected_message"),
    (
        (
            "duplicate_b.pietto",
            "shape Row:\n    id: Int\nshape Row:\n    id: Int\n",
            "PIE-S2001",
            "Duplicate symbol name in type namespace: Row",
        ),
        (
            "unknown_type.pietto",
            "shape Broken:\n    id: MissingType\n",
            "PIE-S2002",
            "Unknown type: MissingType",
        ),
        (
            "bad_shape.pietto",
            'enum Status:\n    active\nsource rows: Status is postgres.table("rows")\n',
            "PIE-S2303",
            "Source shape must refer to a shape: Status",
        ),
        (
            "missing_relation.pietto",
            "table projected:\n    from missing_relation\n    select:\n        id\n",
            "PIE-S2301",
            "Unknown relation: missing_relation",
        ),
    ),
)
def test_project_text_check_fails_on_private_semantic_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    source_name: str,
    source_text: str,
    expected_code: str,
    expected_message: str,
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, source_name, source_text)

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert expected_code in captured.err
    assert expected_message in captured.err
    assert f"{source_name}:" in captured.err
    assert str(root) not in captured.err
    assert "Project check OK" not in captured.out
    assert "Files checked" not in captured.out


def test_project_text_check_succeeds_for_valid_cross_file_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(root, "models/a_shape.pietto", "shape Row:\n    id: Int\n")
    _write(
        root,
        "models/b_source.pietto",
        'source rows: Row is postgres.table("rows")\n',
    )
    _write(
        root,
        "models/c_table.pietto",
        "table projected:\n    from rows\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 3\n"
    assert captured.err == ""


def test_parser_errors_short_circuit_project_semantic_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")

    def unexpected_builder(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project semantic builder must not run after parse errors")

    monkeypatch.setattr(cli, "build_empty_project_semantic_result", unexpected_builder)

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "bad.pietto:" in captured.err
    assert "PIE-P1000" in captured.err


def test_project_json_mode_reports_semantic_diagnostics_after_slice8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "private_relation_error.pietto",
        "table projected:\n    from missing_relation\n    select:\n        id\n",
    )

    _forbid_project_output_pipelines(monkeypatch)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert tuple(document) == (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
    assert document["ok"] is False
    assert document["inputs"] == [
        {
            "path": "private_relation_error.pietto",
            "kind": "source",
            "status": "parsed",
        }
    ]
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 1,
            "files_with_errors": 0,
        }
    }
    serialized = json.dumps(document)
    assert "PIE-S2301" in serialized
    assert "relation_resolutions" not in serialized
    assert "catalog" not in serialized


def test_project_semantic_cli_gate_does_not_enter_output_pipelines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", _VALID_RELATION_SOURCE)

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""


def test_single_file_cli_surfaces_remain_separate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    check_source = _write(
        tmp_path, "shape_only.pietto", "shape Row:\n    id: Int not null\n"
    )
    relation_source = _write(tmp_path, "relation.pietto", _VALID_RELATION_SOURCE)

    assert cli.main(["check", str(check_source)]) == 0
    check_result = capsys.readouterr()
    assert check_result.out == f"OK: {check_source}\n"
    assert check_result.err == ""

    assert cli.main(["emit-sql", str(relation_source), "--dialect", "postgres"]) == 0
    emit_result = capsys.readouterr()
    assert "SELECT" in emit_result.out
    assert emit_result.err == ""

    assert cli.main(["explain", str(relation_source), "--format", "json"]) == 0
    explain_document = _read_json_document(capsys)
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert explain_document["command"] == "explain"
    assert "mode" not in explain_document


def test_slice7_docs_lock_text_only_project_semantic_cli_gate() -> None:
    docs = " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))

    for required in (
        "Slice 7 adds a text-only project semantic CLI gate",
        "`pietto check --project ROOT` text mode runs private project semantic checks after parse success",
        "Text mode renders project semantic diagnostics",
        "Text mode returns `1` on project semantic errors",
        "Text mode does not print success output when semantic errors exist",
        "Parse/project errors short-circuit semantic checks",
        "Valid cross-file projects still print the existing success output",
        "Slice 8 adds Project JSON v2 semantic diagnostics",
        "JSON mode computes the private project semantic result after parse success",
        "No Project JSON v2 shape, counter, input-status, or semantic `ok` behavior changes in Slice 7",
        "no IR, SQL, project `emit-sql`, or project `explain` path",
        "no import from `pietto.semantic`",
        "no single-file behavior change",
    ):
        assert required in docs, required


def _forbid_project_output_pipelines(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project check must not enter compiler output pipelines")

    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
    monkeypatch.setattr(cli.mysql_backend, "emit_mysql_sql", unexpected_call)
    monkeypatch.setattr(cli, "build_semantic_metadata_artifact", unexpected_call)
    monkeypatch.setattr(cli, "semantic_metadata_artifact_to_json_dict", unexpected_call)
    monkeypatch.setattr(cli, "render_semantic_metadata_text", unexpected_call)


def _read_json_document(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    config_text = (
        "schema_version = 1\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path
