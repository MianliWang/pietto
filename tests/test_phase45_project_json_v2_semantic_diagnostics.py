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

_VALID_PROJECT_SOURCE = (
    "shape Row:\n"
    "    id: Int\n"
    'source rows: Row is postgres.table("rows")\n'
    "table projected:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
)


@pytest.mark.parametrize(
    ("source_name", "source_text", "expected_code", "expected_message"),
    (
        (
            "duplicate.pietto",
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
def test_project_json_v2_reports_semantic_diagnostics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    source_name: str,
    source_text: str,
    expected_code: str,
    expected_message: str,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, source_name, source_text)

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
            "path": source_name,
            "kind": "source",
            "status": "parsed",
        }
    ]
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 1,
            "files_with_errors": 0,
        }
    }
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        (expected_code, expected_message)
    ]
    assert diagnostics[0]["severity"] == "error"
    assert diagnostics[0]["suggestion"] is None
    assert diagnostics[0]["related_locations"] == []
    location = cast(dict[str, object], diagnostics[0]["location"])
    assert location["path"] == source_name
    serialized = json.dumps(document)
    assert str(root) not in serialized
    for private_fact in (
        "ProjectSymbol",
        "catalog",
        "type_resolutions",
        "source_shape_resolutions",
        "relation_resolutions",
    ):
        assert private_fact not in serialized


def test_project_json_v2_does_not_compute_semantics_after_parser_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")

    def unexpected_builder(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project JSON semantics must not run after parse errors")

    monkeypatch.setattr(cli, "build_empty_project_semantic_result", unexpected_builder)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert document["cli_errors"] == []
    assert document["inputs"] == [
        {
            "path": "bad.pietto",
            "kind": "source",
            "status": "error",
        }
    ]
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-P1000"]


def test_project_json_v2_does_not_compute_semantics_after_project_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write_bytes(root, "bad.pietto", b"\xff")

    def unexpected_builder(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project JSON semantics must not run after project errors")

    monkeypatch.setattr(cli, "build_empty_project_semantic_result", unexpected_builder)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert document["diagnostics"] == []
    assert document["cli_errors"] == [
        {
            "kind": "source_read",
            "message": "Project source file must be valid UTF-8.",
            "path": "bad.pietto",
        }
    ]


def test_valid_cross_file_project_json_v2_remains_success_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
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

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 0

    document = _read_json_document(capsys)
    assert document["ok"] is True
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 3,
            "files_ok": 3,
            "files_with_errors": 0,
        }
    }


def test_project_text_check_still_reports_semantic_diagnostics_after_slice8(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "private_relation_error.pietto",
        "table projected:\n    from missing_relation\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "private_relation_error.pietto:2:5 PIE-S2301 error" in captured.err
    assert "Unknown relation: missing_relation" in captured.err


def test_project_json_v2_semantic_diagnostics_docs_are_locked() -> None:
    docs = " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))

    for required in (
        "Slice 8 adds Project JSON v2 semantic diagnostics",
        "JSON mode computes the private project semantic result after parse success",
        "Semantic diagnostics are appended to top-level `diagnostics[]`",
        "Top-level `ok` becomes false on semantic error diagnostics",
        "`inputs[].status` remains read/parse based",
        "`result.check` counters remain read/parse based",
        "`cli_errors[]` remains project/config/source-selection/source-read only",
        "No new Project JSON v2 fields",
        "No private semantic facts are serialized",
        "Parse/project errors short-circuit semantic checks",
        "Text mode from Slice 7 remains unchanged",
        "no IR, SQL, project `emit-sql`, or project `explain` path",
        "no import from `pietto.semantic`",
        "no single-file JSON behavior change",
    ):
        assert required in docs, required


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


def _write_bytes(root: Path, relative_path: str, content: bytes) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path
