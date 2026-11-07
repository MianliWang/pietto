from __future__ import annotations

import io
import json
import tokenize
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

import pietto.cli as cli
from pietto._project import model as project_model

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts" / "package_smoke.py"
PROJECT_CONFIG_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "config.py"
PROJECT_CHECK_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "check.py"

_RELATION_SOURCE = (
    "shape User:\n"
    "    id: UUID\n"
    "    email: Text\n"
    "    active: Bool\n"
    'source users: User = postgres.table("users")\n'
    "table active_users:\n"
    "    from users\n"
    "    where active == True\n"
    "    select:\n"
    "        id\n"
    "        email\n"
)

_VALID_RELATION_SOURCE = (
    "shape User:\n"
    "    id: Int\n"
    "    email: Text\n"
    'source users: User = postgres.table("users")\n'
    "table active_users:\n"
    "    from users\n"
    "    select:\n"
    "        id\n"
)

_VALID_PROJECT_SOURCES = {
    "models/a_shape.pietto": "shape Row:\n    id: Int\n",
    "models/b_source.pietto": 'source rows: Row = postgres.table("rows")\n',
    "models/c_table.pietto": (
        "table projected:\n    from rows\n    select:\n        id\n"
    ),
}

_PROJECT_JSON_KEYS = (
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


def test_project_check_valid_root_config_is_text_only_and_pipeline_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root_with_source(tmp_path)
    _forbid_project_output_pipelines(monkeypatch)

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
    _forbid_project_output_pipelines(monkeypatch)

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
        "query q(a: Int):\n    from rows\n    select:\n        id\n"
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
        "    id: UUID",
        "    deleted_at: Timestamp | None",
        "",
        'source users: User = postgres.table("public.users")',
        "",
        "query q:",
        "    from users",
        "    where missing_field is None",
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
        "shape Row:\n    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
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
        "def one(x: Int) -> Bool | None: return x == 1\n"
        "shape Row:\n    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
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
def test_project_check_reports_the_recursion_limit_in_a_long_relationship_predicate(
    condition: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A typed relationship predicate is an ordinary Bool expression: its
    # 3,000 terms nest as written, deeper than the WHERE of b.pietto, and are
    # held to the recursion limit. Only the retired source-bound `on` was read
    # one conjunct at a time, adding no depth.
    root = _project_root(
        tmp_path,
        config_text='schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n',
    )
    header = (
        "shape Row:\n    id: Int\n"
        'source xs: Row = postgres.table("xs")\n'
        'source ys: Row = postgres.table("ys")\n'
    )
    _write(
        root,
        "a.pietto",
        header + f"relationship r(a: Row, b: Row):\n    {condition}\n",
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
        f"a.pietto:1:1 PIE-S2006 error: {_RECURSION_LIMIT}\n",
    )
    (root / "b.pietto").unlink()
    assert cli.main(["check", "--project", str(root)]) == 1
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == (
        "",
        f"a.pietto:1:1 PIE-S2006 error: {_RECURSION_LIMIT}\n",
    )


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


@pytest.mark.parametrize("command", ["check", "explain"])
@pytest.mark.parametrize("output_format", ["text", "json"])
def test_an_empty_project_root_is_a_usage_error_not_the_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    output_format: str,
) -> None:
    monkeypatch.chdir(_project_root(tmp_path / "project"))

    for spelling in (["--project", ""], ["--project="]):
        assert cli.main([command, *spelling, "--format", output_format]) == 2

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err.endswith(
            f"pietto {command}: error: argument --project: Project root must be a"
            " non-empty path.\n"
        )


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
        "shape User:\n    email: Text\n",
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
    _forbid_project_output_pipelines(monkeypatch)


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


def test_project_check_adds_no_deferred_project_capabilities() -> None:
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


def test_project_check_json_parser_diagnostics_do_not_enter_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _sources_root(tmp_path, "*.pietto", "models/*.pietto")
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _write(root, "models/good.pietto", "shape Good:\n    id: Int\n")
    _forbid_project_output_pipelines(monkeypatch)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert document["inputs"] == [
        {
            "path": "bad.pietto",
            "kind": "source",
            "status": "error",
        },
        {
            "path": "models/good.pietto",
            "kind": "source",
            "status": "parsed",
        },
    ]
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 2,
            "files_ok": 1,
            "files_with_errors": 1,
        }
    }
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert diagnostics
    assert diagnostics[0]["code"] == "PIE-P1000"
    assert diagnostics[0]["related_locations"] == []
    location = cast(dict[str, object], diagnostics[0]["location"])
    assert location["path"] == "bad.pietto"
    assert str(root) not in json.dumps(document)


def test_project_check_json_source_read_and_config_errors_stay_cli_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _sources_root(tmp_path / "read-error", "*.pietto")
    _write_bytes(root, "bad.pietto", b"\xff")
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")
    _forbid_project_output_pipelines(monkeypatch)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    read_error_document = _read_json_document(capsys)
    assert read_error_document["inputs"] == [
        {
            "path": "bad.pietto",
            "kind": "source",
            "status": "error",
        },
        {
            "path": "good.pietto",
            "kind": "source",
            "status": "parsed",
        },
    ]
    assert read_error_document["diagnostics"] == []
    assert read_error_document["cli_errors"] == [
        {
            "kind": "source_read",
            "message": "Project source file must be valid UTF-8.",
            "path": "bad.pietto",
        }
    ]
    assert read_error_document["result"] == {
        "check": {
            "files_total": 2,
            "files_ok": 1,
            "files_with_errors": 1,
        }
    }

    schema_root = _project_root(
        tmp_path / "schema-error",
        config_text="schema_version = 1\n\n[sources]\ninclude = []\n",
    )
    assert cli.main(["check", "--project", str(schema_root), "--format", "json"]) == 2

    schema_error_document = _read_json_document(capsys)
    assert schema_error_document["project"] == {
        "root": ".",
        "config_path": "pietto.toml",
    }
    assert schema_error_document["inputs"] == []
    assert schema_error_document["diagnostics"] == []
    assert schema_error_document["result"] == {
        "check": {
            "files_total": 0,
            "files_ok": 0,
            "files_with_errors": 0,
        }
    }
    cli_errors = cast(list[dict[str, object]], schema_error_document["cli_errors"])
    assert len(cli_errors) == 1
    assert cli_errors[0]["kind"] == "config_schema"
    assert cli_errors[0]["path"] == "pietto.toml"
    assert str(tmp_path) not in json.dumps(schema_error_document)


def test_installed_package_smoke_checks_project_text_and_json_success_only() -> None:
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
        '"path": "models/user.pietto"',
        '"kind": "source"',
        '"status": "parsed"',
        '"files_total": 1',
        '"files_ok": 1',
        '"files_with_errors": 0',
        "installed CLI project check text wrote unexpected stderr",
        "installed CLI project check JSON v2 wrote unexpected stderr",
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
            'enum Status:\n    active\nsource rows: Status = postgres.table("rows")\n',
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
    root = _sources_root(tmp_path, "*.pietto")
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


def test_project_relation_check_does_not_enter_output_pipelines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _sources_root(tmp_path, "*.pietto")
    _write(root, "good.pietto", _VALID_RELATION_SOURCE)

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""


def test_project_text_semantic_errors_keep_diagnostic_compatibility(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _sources_root(tmp_path, "*.pietto")
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


def test_project_json_semantic_errors_keep_shape_and_count_the_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _sources_root(tmp_path, "*.pietto")
    _write(
        root,
        "missing_relation.pietto",
        "table projected:\n    from missing_relation\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert tuple(document) == _PROJECT_JSON_KEYS
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
            "files_ok": 0,
            "files_with_errors": 1,
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
    root = _sources_root(tmp_path, "*.pietto")
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _forbid_project_semantic_builder(monkeypatch)

    assert cli.main(_project_args(arguments, root)) == 1

    if json_mode:
        document = _read_json_document(capsys)
        assert tuple(document) == _PROJECT_JSON_KEYS
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
    root = _sources_root(tmp_path, "*.pietto")
    _write_bytes(root, "bad.pietto", b"\xff")
    _forbid_project_semantic_builder(monkeypatch)

    arguments = ["check", "--project", str(root)]
    if json_mode:
        arguments.extend(("--format", "json"))

    assert cli.main(arguments) == 2

    if json_mode:
        document = _read_json_document(capsys)
        assert tuple(document) == _PROJECT_JSON_KEYS
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
        tmp_path / "project",
        config_text="schema_version = 1\n\n[sources]\ninclude = []\n",
    )
    _forbid_project_semantic_builder(monkeypatch)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    document = _read_json_document(capsys)
    assert tuple(document) == _PROJECT_JSON_KEYS
    assert document["inputs"] == []
    assert document["diagnostics"] == []
    cli_errors = cast(list[dict[str, object]], document["cli_errors"])
    assert len(cli_errors) == 1
    assert cli_errors[0]["kind"] == "config_schema"
    assert cli_errors[0]["path"] == "pietto.toml"


def test_valid_project_text_and_json_success_remain_compatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    text_root = _valid_project(tmp_path / "text-project")

    assert cli.main(["check", "--project", str(text_root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 3\n"
    assert captured.err == ""

    json_root = _valid_project(tmp_path / "json-project")

    assert cli.main(["check", "--project", str(json_root), "--format", "json"]) == 0

    document = _read_json_document(capsys)
    assert tuple(document) == _PROJECT_JSON_KEYS
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
        "shape Row:\n    id: Int\n",
    )
    relation_source = _write(tmp_path, "relation.pietto", _VALID_RELATION_SOURCE)

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
    assert "PIE-S2302" not in emit_result.out
    assert emit_result.err == ""

    assert cli.main(["explain", str(relation_source), "--format", "json"]) == 0
    explain_document = _read_json_document(capsys)
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert explain_document["command"] == "explain"
    assert "mode" not in explain_document


@pytest.mark.parametrize("json_mode", (False, True))
def test_project_cycle_check_does_not_enter_single_file_output_pipelines(
    json_mode: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _cycle_project(tmp_path, source_name="cycle_project.pietto")
    arguments = ["check", "--project", root.as_posix()]
    if json_mode:
        arguments.extend(("--format", "json"))

    assert cli.main(arguments) == 1

    if json_mode:
        document = _read_json_document(capsys)
        diagnostics = cast(list[dict[str, object]], document["diagnostics"])
        assert [(item["code"], item["message"]) for item in diagnostics] == [
            ("PIE-S2302", "Relation cycle detected: first -> second -> first")
        ]
        return

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "cycle_project.pietto:6:5 PIE-S2302 error" in captured.err
    assert "Relation cycle detected: first -> second -> first" in captured.err
    assert "Project check OK" not in captured.out
    assert "Files checked" not in captured.out


def test_project_emit_sql_remains_rejected_without_cycle_leakage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _cycle_project(tmp_path, source_name="cycle_project.pietto")

    assert cli.main(["emit-sql", "--project", root.as_posix()]) != 0

    captured = capsys.readouterr()
    combined_output = f"{captured.out}\n{captured.err}"
    assert "SELECT" not in captured.out
    assert "Semantic Metadata Artifact" not in captured.out
    assert "Project check OK" not in captured.out
    assert "PIE-S2302" not in combined_output
    for internal_name in (
        "relation_dependency_graph",
        "ProjectRelationDependencyGraph",
        "ProjectRelationDependencyCycle",
    ):
        assert internal_name not in combined_output


def test_project_json_v2_cycle_output_shape_and_private_facts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _cycle_project(tmp_path, source_name="cycle_json.pietto")

    assert cli.main(["check", "--project", root.as_posix(), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    serialized = json.dumps(document)

    assert tuple(document) == _PROJECT_JSON_KEYS
    assert document["schema_version"] == 2
    assert document["command"] == "check"
    assert document["mode"] == "project"
    assert document["ok"] is False
    assert document["inputs"] == [
        {"path": "cycle_json.pietto", "kind": "source", "status": "parsed"}
    ]
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 0,
            "files_with_errors": 1,
        }
    }
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]
    assert diagnostics[0]["severity"] == "error"
    assert diagnostics[0]["suggestion"] is None
    assert diagnostics[0]["related_locations"] == []
    assert cast(dict[str, object], diagnostics[0]["location"]) == {
        "path": "cycle_json.pietto",
        "line": 6,
        "column": 5,
        "end_line": 6,
        "end_column": 15,
    }
    assert str(root) not in serialized
    _assert_private_cycle_facts_absent(document)


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


def _forbid_project_semantic_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_builder(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project semantic builder must not run")

    monkeypatch.setattr(
        project_model, "build_empty_project_semantic_result", unexpected_builder
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


def _sources_root(
    path: Path,
    *include: str,
    exclude: tuple[str, ...] = (),
) -> Path:
    return _project_root(
        path / "project",
        config_text=(
            "schema_version = 1\n\n"
            "[sources]\n"
            f"include = {_toml_array(include)}\n"
            f"exclude = {_toml_array(exclude)}\n"
        ),
    )


def _project_root_with_source(path: Path) -> Path:
    root = _project_root(
        path,
        config_text=(
            'schema_version = 1\n\n[sources]\ninclude = ["models/*.pietto"]\n'
        ),
    )
    _write(root, "models/user.pietto", "shape User:\n    id: Int\n")
    return root


def _valid_project(path: Path) -> Path:
    root = _sources_root(path, "models/*.pietto")
    for relative_path, source in _VALID_PROJECT_SOURCES.items():
        _write(root, relative_path, source)
    return root


def _cycle_project(path: Path, *, source_name: str) -> Path:
    root = _sources_root(path, "*.pietto")
    _write(
        root,
        source_name,
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
    )
    return root


def _root_with_config_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "pietto.toml").mkdir()
    return path


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


def _python_identifier_names(source: str) -> frozenset[str]:
    return frozenset(
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.NAME
    )


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _configure_parser_source(cli_source: str, name: str) -> str:
    start = cli_source.index(f"def _configure_{name}_parser")
    next_function = cli_source.index("\ndef ", start + 1)
    return cli_source[start:next_function]


def _assert_no_private_semantic_facts(serialized: str) -> None:
    for private_fact in (
        "ProjectSymbol",
        "catalog",
        "type_resolutions",
        "source_shape_resolutions",
        "relation_resolutions",
    ):
        assert private_fact not in serialized


_PRIVATE_CYCLE_FACTS = frozenset(
    {
        "relation_dependency_graph",
        "ProjectRelationDependencyGraph",
        "ProjectRelationDependencyCycle",
        "cycles",
        "nodes",
        "edges",
        "origin",
        "target",
        "dependency_source",
    }
)


def _assert_private_cycle_facts_absent(value: object) -> None:
    """No key of the parsed JSON document, at any depth, is a private fact."""
    if isinstance(value, dict):
        assert _PRIVATE_CYCLE_FACTS.isdisjoint(value), value
        value = list(value.values())
    if isinstance(value, list):
        for child in value:
            _assert_private_cycle_facts_absent(child)
