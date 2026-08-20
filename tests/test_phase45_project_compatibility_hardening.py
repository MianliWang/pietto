from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"

PROJECT_JSON_TOP_LEVEL_KEYS = (
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

VALID_PROJECT_SOURCES = {
    "models/a_shape.pietto": "shape Row:\n    id: Int\n",
    "models/b_source.pietto": 'source rows: Row is postgres.table("rows")\n',
    "models/c_table.pietto": (
        "table projected:\n    from rows\n    select:\n        id\n"
    ),
}

VALID_RELATION_SOURCE = (
    "shape User:\n"
    "    id: Int not null\n"
    "    email: Text not null\n"
    'source users: User is postgres.table("users")\n'
    "table active_users:\n"
    "    from users\n"
    "    select:\n"
    "        id\n"
)


def test_project_text_semantic_errors_keep_diagnostic_compatibility(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "missing_relation.pietto",
        "table projected:\n    from missing_relation\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "missing_relation.pietto:2:5 PIE-S2301 error" in captured.err
    assert "Unknown relation: missing_relation" in captured.err
    assert "Project check OK" not in captured.out
    assert "Files checked" not in captured.out
    assert str(root) not in captured.err


def test_project_json_semantic_errors_keep_shape_and_read_parse_counters(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "missing_relation.pietto",
        "table projected:\n    from missing_relation\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["schema_version"] == 2
    assert document["command"] == "check"
    assert document["mode"] == "project"
    assert document["ok"] is False
    assert document["inputs"] == [
        {
            "path": "missing_relation.pietto",
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
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]
    assert diagnostics[0]["severity"] == "error"
    assert diagnostics[0]["related_locations"] == []
    assert cast(dict[str, object], diagnostics[0]["location"])["path"] == (
        "missing_relation.pietto"
    )
    serialized = json.dumps(document)
    assert str(root) not in serialized
    _assert_no_private_semantic_facts(serialized)


@pytest.mark.parametrize(
    ("arguments", "json_mode"),
    (
        (("check", "--project", "{root}"), False),
        (("check", "--project", "{root}", "--format", "json"), True),
    ),
)
def test_parser_errors_short_circuit_project_semantic_building(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
    json_mode: bool,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _forbid_project_semantic_builder(monkeypatch)

    assert cli.main(_project_args(arguments, root)) == 1

    if json_mode:
        document = _read_json_document(capsys)
        assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
        assert document["inputs"] == [
            {
                "path": "bad.pietto",
                "kind": "source",
                "status": "error",
            }
        ]
        assert document["cli_errors"] == []
        diagnostics = cast(list[dict[str, object]], document["diagnostics"])
        assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-P1000"]
    else:
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "bad.pietto:" in captured.err
        assert "PIE-P1000" in captured.err


@pytest.mark.parametrize("json_mode", (False, True))
def test_source_read_errors_short_circuit_project_semantic_building(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    json_mode: bool,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write_bytes(root, "bad.pietto", b"\xff")
    _forbid_project_semantic_builder(monkeypatch)

    arguments = ["check", "--project", str(root)]
    if json_mode:
        arguments.extend(("--format", "json"))

    assert cli.main(arguments) == 2

    if json_mode:
        document = _read_json_document(capsys)
        assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
        assert document["diagnostics"] == []
        assert document["inputs"] == [
            {
                "path": "bad.pietto",
                "kind": "source",
                "status": "error",
            }
        ]
        assert document["cli_errors"] == [
            {
                "kind": "source_read",
                "message": "Project source file must be valid UTF-8.",
                "path": "bad.pietto",
            }
        ]
    else:
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Project source file must be valid UTF-8." in captured.err
        assert "Project check OK" not in captured.out


def test_config_errors_short_circuit_json_project_semantic_building(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(
        tmp_path,
        config_text="schema_version = 1\n\n[sources]\ninclude = []\n",
    )
    _forbid_project_semantic_builder(monkeypatch)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    document = _read_json_document(capsys)
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["inputs"] == []
    assert document["diagnostics"] == []
    cli_errors = cast(list[dict[str, object]], document["cli_errors"])
    assert len(cli_errors) == 1
    assert cli_errors[0]["kind"] == "config_schema"
    assert cli_errors[0]["path"] == "pietto.toml"


def test_valid_project_text_and_json_success_remain_compatible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    text_root = _valid_project(tmp_path / "text-project")

    assert cli.main(["check", "--project", str(text_root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 3\n"
    assert captured.err == ""

    json_root = _valid_project(tmp_path / "json-project")

    assert cli.main(["check", "--project", str(json_root), "--format", "json"]) == 0

    document = _read_json_document(capsys)
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is True
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    assert document["inputs"] == [
        {
            "path": "models/a_shape.pietto",
            "kind": "source",
            "status": "parsed",
        },
        {
            "path": "models/b_source.pietto",
            "kind": "source",
            "status": "parsed",
        },
        {
            "path": "models/c_table.pietto",
            "kind": "source",
            "status": "parsed",
        },
    ]
    assert document["result"] == {
        "check": {
            "files_total": 3,
            "files_ok": 3,
            "files_with_errors": 0,
        }
    }


def test_single_file_surfaces_do_not_use_project_semantic_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_semantic_builder(monkeypatch)
    check_source = _write(
        tmp_path,
        "shape_only.pietto",
        "shape Row:\n    id: Int not null\n",
    )
    relation_source = _write(tmp_path, "relation.pietto", VALID_RELATION_SOURCE)

    assert cli.main(["check", str(check_source)]) == 0
    text_check = capsys.readouterr()
    assert text_check.out == f"OK: {check_source}\n"
    assert text_check.err == ""

    assert cli.main(["check", str(check_source), "--format", "json"]) == 0
    check_document = _read_json_document(capsys)
    assert check_document["schema_version"] == 1
    assert check_document["command"] == "check"
    assert "mode" not in check_document

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


@pytest.mark.parametrize("command", ("emit-sql", "explain"))
def test_project_emit_sql_and_explain_remain_rejected(
    command: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _valid_project(tmp_path / "project")

    assert cli.main([command, "--project", str(root)]) != 0

    captured = capsys.readouterr()
    assert "SELECT" not in captured.out
    assert "Semantic Metadata Artifact" not in captured.out
    assert "Project check OK" not in captured.out


def test_package_smoke_remains_success_read_parse_smoke_only() -> None:
    source = PACKAGE_SMOKE_PATH.read_text(encoding="utf-8")

    for required in (
        '"installed CLI project check text"',
        '"installed CLI project check JSON v2"',
        '("check", "--project", project_root.as_posix())',
        '("check", "--project", project_root.as_posix(), "--format", "json")',
        "Project check OK: .",
        "Files checked: 1",
        '"schema_version": 2',
        '"mode": "project"',
        '"status": "parsed"',
        '"files_total": 1',
        '"files_ok": 1',
        '"files_with_errors": 0',
    ):
        assert required in source, required

    for semantic_error_marker in (
        "PIE-S2001",
        "PIE-S2002",
        "PIE-S2301",
        "PIE-S2303",
        "Unknown relation",
        "Unknown type",
        "Duplicate symbol",
        "Source shape must refer to a shape",
    ):
        assert semantic_error_marker not in source


def _read_json_document(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _project_root(
    path: Path,
    *,
    include: tuple[str, ...] = ("*.pietto",),
    exclude: tuple[str, ...] = (),
    config_text: str | None = None,
) -> Path:
    root = path / "project"
    root.mkdir(parents=True)
    if config_text is None:
        config_text = (
            "schema_version = 1\n\n"
            "[sources]\n"
            f"include = {_toml_array(include)}\n"
            f"exclude = {_toml_array(exclude)}\n"
        )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _valid_project(path: Path) -> Path:
    root = _project_root(path, include=("models/*.pietto",))
    for relative_path, source in VALID_PROJECT_SOURCES.items():
        _write(root, relative_path, source)
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


def _project_args(arguments: tuple[str, ...], root: Path) -> list[str]:
    return [
        root.as_posix() if argument == "{root}" else argument for argument in arguments
    ]


def _forbid_project_semantic_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_builder(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project semantic builder must not run")

    monkeypatch.setattr(cli, "build_empty_project_semantic_result", unexpected_builder)


def _assert_no_private_semantic_facts(serialized: str) -> None:
    for private_fact in (
        "ProjectSymbol",
        "catalog",
        "type_resolutions",
        "source_shape_resolutions",
        "relation_resolutions",
    ):
        assert private_fact not in serialized
