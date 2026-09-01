from __future__ import annotations

import io
import json
import tokenize
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_CONFIG_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "config.py"
PROJECT_CHECK_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "check.py"

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


def test_project_check_text_mode_is_parse_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root_with_source(tmp_path)

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""
    assert str(root) not in captured.out


@pytest.mark.parametrize(
    "format_args",
    [
        ["--format", "json"],
        ["--format=json"],
    ],
)
def test_project_check_json_v2_success_reports_inputs_and_counters(
    format_args: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root_with_source(tmp_path)

    assert cli.main(["check", "--project", str(root), *format_args]) == 0

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


@pytest.mark.parametrize(
    ("make_root", "expected_kind", "expected_project", "expected_path"),
    [
        (
            lambda path: path / "missing",
            "project_root",
            {"root": None, "config_path": None},
            None,
        ),
        (
            lambda path: path,
            "config_read",
            {"root": ".", "config_path": "pietto.toml"},
            "pietto.toml",
        ),
    ],
)
def test_project_check_json_v2_errors_are_stdout_only_and_project_relative(
    make_root: Callable[[Path], Path],
    expected_kind: str,
    expected_project: dict[str, object],
    expected_path: str | None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = make_root(tmp_path)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    document = _read_json_document(capsys)
    assert document["schema_version"] == 2
    assert document["command"] == "check"
    assert document["mode"] == "project"
    assert document["ok"] is False
    assert document["project"] == expected_project
    assert document["inputs"] == []
    assert document["diagnostics"] == []
    assert document["result"] == {
        "check": {
            "files_total": 0,
            "files_ok": 0,
            "files_with_errors": 0,
        }
    }
    cli_errors = cast(list[dict[str, object]], document["cli_errors"])
    assert len(cli_errors) == 1
    assert cli_errors[0]["kind"] == expected_kind
    assert cli_errors[0]["path"] == expected_path
    assert str(tmp_path) not in json.dumps(document)


def test_single_file_json_v1_and_artifact_v1_surfaces_remain_separate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    check_source = _write(
        tmp_path,
        "valid.pietto",
        "shape User:\n    email: Text not null\n",
    )
    relation_source = _write(tmp_path, "active_users.pietto", _RELATION_SOURCE)

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
    assert "mode" not in explain_document


def test_project_flag_remains_rejected_by_emit_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path)

    assert cli.main(["emit-sql", "--project", str(root)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: pietto" in captured.err


def test_slice8_does_not_add_deferred_project_capabilities() -> None:
    project_source = _read("src/pietto/_project/discovery.py")
    cli_source = _read("src/pietto/cli.py")
    explain_composition = REPO_ROOT / "src/pietto/_project_explain/composition.py"
    explain_json = REPO_ROOT / "src/pietto/_project_explain/json_v1.py"
    explain_runtime = REPO_ROOT / "src/pietto/_project_explain/runtime_builder.py"
    explain_text = REPO_ROOT / "src/pietto/_project_explain/text.py"
    cli_path = REPO_ROOT / "src/pietto/cli.py"
    source_tree = "\n".join(
        _read(path.relative_to(REPO_ROOT).as_posix())
        for path in sorted((REPO_ROOT / "src" / "pietto").rglob("*.py"))
        if "__pycache__" not in path.parts
    )
    source_tree_without_project_config_or_check = "\n".join(
        _read(path.relative_to(REPO_ROOT).as_posix())
        for path in sorted((REPO_ROOT / "src" / "pietto").rglob("*.py"))
        if (
            "__pycache__" not in path.parts
            and path
            not in {PROJECT_CONFIG_SOURCE, PROJECT_CHECK_SOURCE, explain_runtime}
        )
    )

    for forbidden in (
        "tomllib",
        ".glob(",
        ".rglob(",
        "read_text(",
        "read_bytes(",
        "open(",
    ):
        assert forbidden not in project_source

    assert "load_project_config" not in source_tree_without_project_config_or_check
    assert "compile_project" not in _python_identifier_names(source_tree)
    for forbidden in (
        "configured_source_selection",
        "aggregate_project_metadata",
        "result.explain",
    ):
        assert forbidden not in source_tree
    assert "project_explain" not in "\n".join(
        _read(path.relative_to(REPO_ROOT).as_posix())
        for path in sorted((REPO_ROOT / "src" / "pietto").rglob("*.py"))
        if "__pycache__" not in path.parts
        and path
        not in {
            cli_path,
            explain_composition,
            explain_json,
            explain_runtime,
            explain_text,
        }
    )

    assert '"--project"' not in _configure_parser_source(cli_source, "emit_sql")
    assert '"--project"' in _configure_parser_source(cli_source, "explain")


def test_deferred_compile_project_reader_uses_exact_python_identifiers() -> None:
    for source in (
        "def compile_project():\n    pass\n",
        "compile_project()\n",
        "module.compile_project()\n",
        "from package import compile_project\n",
    ):
        assert "compile_project" in _python_identifier_names(source)

    for source in (
        "def _compile_project_value_fd_index():\n    pass\n",
        "compile_project_value_fd_index()\n",
        "some_compile_project_helper = None\n",
        "# compile_project\nvalue = 'compile_project'\n",
    ):
        assert "compile_project" not in _python_identifier_names(source)


def _python_identifier_names(source: str) -> frozenset[str]:
    return frozenset(
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.NAME
    )


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


def _write(root: Path, relative_path: str, text: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _configure_parser_source(cli_source: str, name: str) -> str:
    start = cli_source.index(f"def _configure_{name}_parser")
    next_function = cli_source.index("\ndef ", start + 1)
    return cli_source[start:next_function]
