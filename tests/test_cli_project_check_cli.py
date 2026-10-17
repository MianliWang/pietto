from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

import pietto.cli as cli

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


def test_project_check_valid_root_config_is_text_only_and_pipeline_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root_with_source(tmp_path)
    _forbid_project_compiler_pipeline(monkeypatch)

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""
    assert str(root) not in captured.out


def test_project_check_explicit_text_format_matches_default(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root_with_source(tmp_path)

    assert cli.main(["check", "--project", str(root), "--format", "text"]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("root_name", "make_root", "expected_kind"),
    [
        ("missing", lambda path: path / "missing", "project_root"),
        ("file-root", lambda path: _write(path, "file-root", ""), "project_root"),
        ("missing-config", lambda path: path, "config_read"),
        (
            "directory-config",
            lambda path: _root_with_config_directory(path),
            "config_read",
        ),
    ],
)
def test_project_check_root_and_config_errors_are_project_relative(
    root_name: str,
    make_root: Callable[[Path], Path],
    expected_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del root_name
    root = make_root(tmp_path)
    _forbid_project_pipeline(monkeypatch)

    assert cli.main(["check", "--project", str(root)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"project error: {expected_kind}:" in captured.err
    assert str(tmp_path) not in captured.err
    if expected_kind == "config_read":
        assert "(path: pietto.toml)" in captured.err


@pytest.mark.parametrize(
    "format_args",
    [
        ["--format", "json"],
        ["--format=json"],
    ],
)
def test_project_check_json_success_emits_json_v2_stdout_only(
    format_args: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root_with_source(tmp_path)
    _forbid_project_compiler_pipeline(monkeypatch)

    assert cli.main(["check", "--project", str(root), *format_args]) == 0

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
    ("root_name", "make_root", "expected_kind", "expected_path", "expected_project"),
    [
        (
            "missing",
            lambda path: path / "missing",
            "project_root",
            None,
            {"root": None, "config_path": None},
        ),
        (
            "file-root",
            lambda path: _write(path, "file-root", ""),
            "project_root",
            None,
            {"root": None, "config_path": None},
        ),
        (
            "missing-config",
            lambda path: path,
            "config_read",
            "pietto.toml",
            {"root": ".", "config_path": "pietto.toml"},
        ),
        (
            "directory-config",
            lambda path: _root_with_config_directory(path),
            "config_read",
            "pietto.toml",
            {"root": ".", "config_path": "pietto.toml"},
        ),
    ],
)
def test_project_check_json_root_and_config_errors_are_json_v2(
    root_name: str,
    make_root: Callable[[Path], Path],
    expected_kind: str,
    expected_path: str | None,
    expected_project: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del root_name
    root = make_root(tmp_path)
    _forbid_project_pipeline(monkeypatch)

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
    assert isinstance(cli_errors[0]["message"], str)
    assert cli_errors[0]["message"]
    assert cli_errors[0]["path"] == expected_path
    assert str(tmp_path) not in json.dumps(document)


@pytest.mark.parametrize("schema", [1, 2], ids=["legacy_flat", "explicit_modules"])
def test_project_check_json_reports_gate_diagnostics_beside_parse_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], schema: int
) -> None:
    root = _project_root(
        tmp_path / "project",
        config_text=f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n',
    )
    _write(root, "a.pietto", "table broken\n")
    _write(
        root,
        "b.pietto",
        "query q(a: Int not null):\n    from rows\n    select:\n        id\n"
        "query r:\n    from rows\n    where exists t and id == scalar t.c\n"
        "    select:\n        id\n"
        "type Age = Int:\n    ensure self > scalar t.c\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert document["ok"] is False
    diagnostics = cast(list[dict[str, Any]], document["diagnostics"])
    paths = [item["location"]["path"] for item in diagnostics]
    assert paths == sorted(paths) and set(paths) == {"a.pietto", "b.pietto"}
    assert {item["code"] for item in diagnostics[: paths.count("a.pietto")]} == {
        "PIE-P1000"
    }
    # An explicit-module project admits a SELECT-body query header and the
    # relation reads inside a relation body; a read in a type rule stays gated.
    assert [
        (item["code"], item["location"]["line"], item["location"]["column"])
        for item in diagnostics
        if item["location"]["path"] == "b.pietto"
    ] == [("PIE-S2346", 1, 9), ("PIE-S2349", 7, 11), ("PIE-S2348", 7, 30)] * (
        schema == 1
    ) + [("PIE-S2348", 11, 19)]


def test_project_check_counts_lf_crlf_and_lone_cr_as_one_line_end_per_module(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project_root(
        tmp_path / "project",
        config_text='schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
    )
    lines = [
        "shape User:",
        "    id: UUID not null",
        "    deleted_at: Timestamp nullable",
        "",
        'source users: User is postgres.table("public.users")',
        "",
        "query q:",
        "    from users",
        "    where missing_field is null",
        "    select:",
        "        id",
    ]
    endings = {
        "a": ("\n",),
        "b": ("\r\n",),
        "c": ("\r",),
        "d": ("\r", "\r\n", "\n"),
    }
    for name, ends in endings.items():
        (root / f"{name}.pietto").write_bytes(
            "".join(
                line + ends[index % len(ends)] for index, line in enumerate(lines)
            ).encode("utf-8")
        )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    document = _read_json_document(capsys)
    assert [
        (item["code"], item["location"], item["related_locations"])
        for item in cast(list[dict[str, Any]], document["diagnostics"])
    ] == [
        (
            "PIE-S2102",
            {
                "path": f"{name}.pietto",
                "line": 9,
                "column": 11,
                "end_line": 9,
                "end_column": 24,
            },
            [],
        )
        for name in endings
    ]

    assert cli.main(["check", "--project", str(root)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "".join(
        f"{name}.pietto:9:11 PIE-S2102 error: Unknown field: missing_field\n"
        for name in endings
    )


_RECURSION_LIMIT = "Semantic analysis recursion limit exceeded while processing source."


@pytest.mark.parametrize("schema", [1, 2], ids=["legacy_flat", "explicit_modules"])
def test_project_check_reports_the_recursion_limit_at_the_most_nested_module(
    schema: int,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A WHERE of 3,000 conditions used to raise RecursionError out of the check.
    root = _project_root(
        tmp_path,
        config_text=f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n',
    )
    _write(root, "a.pietto", _RELATION_SOURCE)
    _write(
        root,
        "b.pietto",
        "shape Row:\n    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "table deep:\n    from rows\n"
        f"    where {' and '.join(['id == 1'] * 3000)}\n"
        "    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"b.pietto:1:1 PIE-S2006 error: {_RECURSION_LIMIT}\n"
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    document = _read_json_document(capsys)
    assert (document["ok"], document["diagnostics"]) == (
        False,
        [
            {
                "code": "PIE-S2006",
                "severity": "error",
                "message": _RECURSION_LIMIT,
                "location": {
                    "path": "b.pietto",
                    "line": 1,
                    "column": 1,
                    "end_line": 8,
                    "end_column": 11,
                },
                "suggestion": None,
                "related_locations": [],
            }
        ],
    )


def test_project_check_reports_the_recursion_limit_through_def_calls(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Every def call is inlined before the module is checked, so a WHERE of
    # 3,000 calls nests as its expansion does and is contained the same way.
    root = _project_root(
        tmp_path,
        config_text='schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n',
    )
    _write(
        root,
        "b.pietto",
        "def one(x: Int not null) -> Bool nullable: return x == 1\n"
        "shape Row:\n    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "table deep:\n    from rows\n"
        f"    where {' and '.join(['one(id)'] * 3000)}\n"
        "    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == (
        "",
        f"b.pietto:1:1 PIE-S2006 error: {_RECURSION_LIMIT}\n",
    )


@pytest.mark.parametrize(
    "condition",
    [
        " and ".join(["a.id == b.id"] * 3000),
        " or ".join(["a.id == b.id"] * 3000),
        "a.id == " + " + ".join(["b.id"] * 3000),
    ],
    ids=["and_equalities", "or_chain", "deep_operand"],
)
def test_project_check_reports_the_recursion_limit_past_a_long_relationship_on(
    condition: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # a.pietto alone checks: each conjunct of its 3,000-term `on` is read one
    # at a time and only at its top, so the `on` adds no depth and the
    # shallower WHERE of b.pietto, which exceeds the limit, is reported.
    root = _project_root(
        tmp_path,
        config_text='schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n',
    )
    header = (
        "shape Row:\n    id: Int not null\n"
        'source xs: Row is postgres.table("xs")\n'
        'source ys: Row is postgres.table("ys")\n'
    )
    _write(
        root,
        "a.pietto",
        header + "relationship r:\n    endpoint a: xs\n    endpoint b: ys\n"
        f"    on {condition}\n",
    )
    _write(
        root,
        "b.pietto",
        header + "table deep:\n    from xs\n"
        f"    where {' and '.join(['id == 1'] * 1000)}\n"
        "    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == (
        "",
        f"b.pietto:1:1 PIE-S2006 error: {_RECURSION_LIMIT}\n",
    )
    (root / "b.pietto").unlink()
    assert cli.main(["check", "--project", str(root)]) == 0
    assert capsys.readouterr().err == ""


def test_project_check_rejects_path_and_project_together(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write(tmp_path, "input.pietto", "")
    root = _project_root(tmp_path / "project")

    assert cli.main(["check", str(source_path), "--project", str(root)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "path and --project are mutually exclusive" in captured.err


def test_project_check_still_requires_single_file_or_project(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["check"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "the following arguments are required: path" in captured.err


def test_project_flag_is_not_accepted_by_emit_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Slice13 introduced `emit-sql --project`; an incomplete invocation is now
    # the closed pietto.sql-emission.v1 usage rejection, not an argparse banner.
    root = _project_root(tmp_path)

    assert cli.main(["emit-sql", "--project", str(root)]) == 2

    document = _read_json_document(capsys)

    assert set(document) == {
        "format",
        "status",
        "artifact",
        "blockers",
        "diagnostics",
        "cli_errors",
    }
    assert document["format"] == "pietto.sql-emission.v1"
    assert document["status"] == "INPUT_REJECTED"
    assert document["artifact"] is None
    assert document["blockers"] == [] and document["diagnostics"] == []
    cli_errors = document["cli_errors"]
    assert isinstance(cli_errors, list) and len(cli_errors) == 1
    assert cli_errors[0]["kind"] == "usage" and cli_errors[0]["path"] is None
    assert "the following arguments are required" in cli_errors[0]["message"]
    assert str(root) not in json.dumps(document)
    # The missing arguments are discovered without opening any project root.
    assert cli.main(["emit-sql", "--project", str(tmp_path / "absent")]) == 2
    assert (
        capsys.readouterr().out
        == json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        + "\n"
    )


def test_single_file_check_text_and_json_v1_remain_available(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write(
        tmp_path,
        "valid.pietto",
        "shape User:\n    email: Text not null\n",
    )

    assert cli.main(["check", str(source_path)]) == 0
    text_result = capsys.readouterr()
    assert text_result.out == f"OK: {source_path}\n"
    assert text_result.err == ""

    assert cli.main(["check", str(source_path), "--format", "json"]) == 0
    json_result = capsys.readouterr()
    document = json.loads(json_result.out)
    assert json_result.err == ""
    assert document["schema_version"] == 1
    assert document["command"] == "check"
    assert document["path"] == str(source_path)
    assert "mode" not in document


def test_single_file_emit_sql_json_v1_and_explain_artifact_v1_remain_available(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write(tmp_path, "active_users.pietto", _RELATION_SOURCE)

    assert (
        cli.main(
            [
                "emit-sql",
                str(source_path),
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
    assert "artifacts" in emit_document
    assert "mode" not in emit_document

    assert cli.main(["explain", str(source_path), "--format", "json"]) == 0
    explain_document = _read_json_document(capsys)
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert explain_document["command"] == "explain"
    assert "metadata" in explain_document
    assert "mode" not in explain_document


def _forbid_project_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project check must not enter the compiler pipeline")

    monkeypatch.setattr(cli.parser_api, "parse_file", unexpected_call)
    _forbid_project_compiler_pipeline(monkeypatch)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--proj", "{root}", "--form", "json"],
        ["--p={root}", "--fo=json"],
        ["--proj", "{root}", "--format", "json"],
    ],
)
def test_project_check_accepts_argparse_abbreviations_with_json(
    arguments: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root_with_source(tmp_path)

    assert cli.main(["check", *(item.format(root=root) for item in arguments)]) == 0

    document = _read_json_document(capsys)
    assert (document["schema_version"], document["mode"], document["ok"]) == (
        2,
        "project",
        True,
    )


def _forbid_project_compiler_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project check must not enter the compiler pipeline")

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


def _root_with_config_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "pietto.toml").mkdir()
    return path


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path
