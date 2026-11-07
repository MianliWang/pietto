from __future__ import annotations

import json
from pathlib import Path

import pytest

import pietto.cli as cli

# The source without a shape is the only mode-dependent diagnostic here.
BODY = (
    "shape User:\n"
    "    id: Int\n"
    'source users: User = postgres.table("users")\n'
    'source raw = postgres.table("raw")\n'
    "table all_users:\n"
    "    from users\n"
    "    select:\n"
    "        id\n"
)
MESSAGE = "Source raw has no bound shape; row schema is unknown"
SQL = 'SELECT\n    "id" AS "id"\nFROM "users"'
USAGE = (
    "usage: pietto {command} [-h] [--project PROJECT] [--format {{text,json}}]"
    " [--check-mode {{loose,checked,strict}}] [--set NAME=VALUE] [path]\n"
    "pietto {command}: error: --check-mode and --project are mutually exclusive\n"
)


def _write(tmp_path: Path, header: str = "") -> Path:
    path = tmp_path / "users.pietto"
    path.write_text(header + BODY, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("options", "severity"),
    [
        ((), "warning"),
        (("--check-mode", "loose"), None),
        (("--check-mode", "checked"), "warning"),
        (("--check-mode=strict",), "error"),
    ],
)
def test_check_mode_defaults_to_checked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    options: tuple[str, ...],
    severity: str | None,
) -> None:
    path = _write(tmp_path)

    code = cli.main(["check", str(path), *options])

    captured = capsys.readouterr()
    assert code == (1 if severity == "error" else 0)
    assert captured.out == ("" if severity == "error" else f"OK: {path}\n")
    assert captured.err == (
        "" if severity is None else f"{path}:4:1 PIE-S2303 {severity}: {MESSAGE}\n"
    )


@pytest.mark.parametrize(
    ("mode", "severities", "code"),
    [("loose", [], 0), ("checked", ["warning"], 0), ("strict", ["error"], 1)],
)
def test_check_and_emit_json_keep_their_shapes_in_every_mode(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    mode: str,
    severities: list[str],
    code: int,
) -> None:
    path = _write(tmp_path)

    assert (
        cli.main(["check", str(path), "--format", "json", "--check-mode", mode]) == code
    )
    captured = capsys.readouterr()
    checked = json.loads(captured.out)
    assert captured.err == ""
    assert list(checked) == [
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "cli_errors",
    ]
    assert [item["severity"] for item in checked["diagnostics"]] == severities
    assert checked["ok"] is (code == 0)

    emit = ["emit-sql", str(path), "--dialect", "postgres", "--format", "json"]
    assert cli.main([*emit, "--check-mode", mode]) == code
    captured = capsys.readouterr()
    emitted = json.loads(captured.out)
    assert captured.err == ""
    assert list(emitted) == [
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    ]
    assert [item["severity"] for item in emitted["diagnostics"]] == severities
    assert [item["sql"] for item in emitted["artifacts"]] == ([] if code else [SQL])


def test_emit_sql_and_explain_text_follow_the_selected_mode(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path)
    error = f"{path}:4:1 PIE-S2303 error: {MESSAGE}\n"

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0
    assert capsys.readouterr().out == f"-- all_users\n{SQL};\n"
    assert (
        cli.main(
            ["emit-sql", str(path), "--dialect", "postgres", "--check-mode", "strict"]
        )
        == 1
    )
    assert capsys.readouterr() == ("", error)
    assert cli.main(["explain", str(path), "--check-mode", "strict"]) == 1
    assert capsys.readouterr() == ("", error)
    assert cli.main(["explain", str(path), "--check-mode", "loose"]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("Semantic Metadata Artifact v1\n")
    assert captured.err == ""

    assert (
        cli.main(["explain", str(path), "--format", "json", "--check-mode", "strict"])
        == 1
    )
    failed = json.loads(capsys.readouterr().out)
    assert failed["ok"] is False and "metadata" not in failed
    assert failed["error"]["stage"] == "semantic"
    assert (
        cli.main(["explain", str(path), "--format", "json", "--check-mode", "loose"])
        == 0
    )
    explained = json.loads(capsys.readouterr().out)
    assert explained["ok"] is True and explained["diagnostics"] == []


HEADER = "pietto 0.9\nmode strict\ndialect mysql\nencoding utf8\n"


@pytest.mark.parametrize("command", ["check", "explain"])
@pytest.mark.parametrize("mode", ["loose", "strict"])
def test_each_header_line_is_refused_in_a_single_file_and_a_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: str, mode: str
) -> None:
    path = _write(tmp_path, HEADER)
    refused = [("PIE-P1000", "error", line) for line in (1, 2, 3, 4)]

    argv = [command, str(path), "--format", "json", "--check-mode", mode]
    assert cli.main(argv) == 1
    document = json.loads(capsys.readouterr().out)
    assert document["ok"] is False
    assert [
        (item["code"], item["severity"], item["location"]["line"])
        for item in document["diagnostics"]
    ] == refused
    if command == "explain":
        return
    # A project refuses the same lines, before any semantic rule.
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 1
    project = json.loads(capsys.readouterr().out)
    assert [
        (item["code"], item["severity"], item["location"]["line"])
        for item in project["diagnostics"]
    ] == refused
    (tmp_path / "contract.json").write_text("{}")
    emit = ["emit-sql", "--project", str(tmp_path), "--module", "users.pietto"]
    emit += ["--kind", "table", "--name", "all_users", "--dialect", "postgres"]
    emit += ["--emission-contract", "contract.json", "--format", "json"]
    assert cli.main(emit) == 1
    emitted = json.loads(capsys.readouterr().out)
    assert (emitted["status"], emitted["artifact"]) == ("BLOCKED", None)
    assert [
        (item["code"], item["severity"], item["location"]["line"])
        for item in emitted["diagnostics"]
    ] == refused


@pytest.mark.parametrize(
    "command",
    [["check"], ["emit-sql", "--dialect", "postgres"], ["explain"]],
)
@pytest.mark.parametrize(
    ("header", "hint"),
    [
        (
            "mode strict",
            "in a single file pass `--check-mode strict` instead; "
            "a project never applied it.",
        ),
        ("dialect mysql", "it has no effect; `emit-sql` takes `--dialect mysql`."),
    ],
)
def test_a_header_line_is_refused_in_text_output_whatever_the_check_mode(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    command: list[str],
    header: str,
    hint: str,
) -> None:
    path = _write(tmp_path, header + "\n")
    error = (
        f"{path}:1:1 PIE-P1000 error: This spelling is not accepted by the modern "
        f"syntax. Delete the header line `{header}`; {hint}\n"
    )

    for options in ((), ("--check-mode", "loose")):
        assert cli.main([*command, str(path), *options]) == 1
        assert capsys.readouterr() == ("", error)


@pytest.mark.parametrize(
    "arguments",
    [
        ("check", "{path}"),
        ("emit-sql", "{path}", "--dialect", "postgres"),
        ("explain", "{path}"),
        ("explain", "{path}", "--format", "json"),
    ],
)
def test_invalid_check_mode_is_a_text_usage_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
) -> None:
    path = _write(tmp_path)
    argv = [item.format(path=path) for item in arguments]

    assert cli.main([*argv, "--check-mode", "lenient"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error: argument --check-mode: invalid choice: 'lenient'" in captured.err


@pytest.mark.parametrize(
    "arguments",
    [
        ("check", "{path}", "--format", "json"),
        ("emit-sql", "{path}", "--dialect", "postgres", "--format", "json"),
    ],
)
def test_invalid_check_mode_is_a_json_usage_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
) -> None:
    path = _write(tmp_path)
    argv = [item.format(path=path) for item in arguments]

    assert cli.main([*argv, "--check-mode", "lenient"]) == 2

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert captured.err == ""
    assert document["ok"] is False and document["diagnostics"] == []
    assert [error["kind"] for error in document["cli_errors"]] == ["usage"]
    assert "invalid choice: 'lenient'" in document["cli_errors"][0]["message"]


@pytest.mark.parametrize(
    ("command", "options"),
    [
        ("check", ()),
        ("check", ("--format", "json")),
        ("explain", ()),
        ("explain", ("--format", "json")),
    ],
)
def test_check_mode_with_project_is_a_usage_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    command: str,
    options: tuple[str, ...],
) -> None:
    argv = [command, "--project", str(tmp_path), *options, "--check-mode", "strict"]

    assert cli.main(argv) == 2

    assert capsys.readouterr() == ("", USAGE.format(command=command))


@pytest.mark.parametrize("presentation", ["text", "json"])
def test_project_emit_sql_rejects_check_mode(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    presentation: str,
) -> None:
    argv = [
        "emit-sql",
        "--project",
        str(tmp_path),
        "--module",
        "main.pietto",
        "--kind",
        "table",
        "--name",
        "all_users",
        "--dialect",
        "postgres",
        "--emission-contract",
        "contract.json",
        "--format",
        presentation,
        "--check-mode=strict",
    ]

    assert cli.main(argv) == 2

    captured = capsys.readouterr()
    message = "unrecognized arguments: --check-mode=strict"
    if presentation == "text":
        assert captured.out == ""
        assert captured.err.endswith(f"pietto emit-sql: error: {message}\n")
    else:
        document = json.loads(captured.out)
        assert captured.err == ""
        assert document["status"] == "INPUT_REJECTED"
        assert document["cli_errors"] == [
            {"kind": "usage", "message": message, "path": None}
        ]


# Every gated relation-block form; the gate stops analysis before any mode rule.
RELATION_BLOCKS = (
    "query q(a: Int):\n"
    "    let l:\n"
    "        capture users\n"
    "        from generate_series(1, 2, 1) as n\n"
    "        select:\n"
    "            n\n"
    "    let inner:\n"
    "        values(id: Int)\n"
    "    from users\n"
    "    where scalar l.n in l and exists inner\n"
    "    select:\n"
    "        id\n"
    "    qualify:\n"
    "        id not in l\n"
)
RELATION_BLOCK_CODES = [
    "PIE-S2346",
    "PIE-S2345",
    "PIE-S2351",
    "PIE-S2352",
    "PIE-S2345",
    "PIE-S2347",
    "PIE-S2348",
    "PIE-S2350",
    "PIE-S2349",
    "PIE-S2350",
]


@pytest.mark.parametrize(
    "options", [(), ("--check-mode", "loose")], ids=["header", "loose"]
)
def test_relation_block_forms_stop_check_explain_and_emit_in_every_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], options: tuple[str, ...]
) -> None:
    path = tmp_path / "blocks.pietto"
    path.write_text(BODY + RELATION_BLOCKS, encoding="utf-8")

    assert cli.main(["check", str(path), "--format", "json", *options]) == 1
    document = json.loads(capsys.readouterr().out)
    assert [d["code"] for d in document["diagnostics"]] == RELATION_BLOCK_CODES
    assert cli.main(["explain", str(path), "--format", "json", *options]) == 1
    explained = json.loads(capsys.readouterr().out)
    assert explained["ok"] is False
    assert [d["code"] for d in explained["diagnostics"]] == RELATION_BLOCK_CODES
    assert cli.main(["emit-sql", str(path), "--dialect", "postgres", *options]) == 1
    captured = capsys.readouterr()
    assert "SELECT" not in captured.out and RELATION_BLOCK_CODES[0] in captured.err
    assert "Traceback" not in captured.err
