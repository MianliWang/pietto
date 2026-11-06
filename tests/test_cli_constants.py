"""The `--set NAME=VALUE` contract of `check`, `emit-sql` and `explain`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pietto import cli

SOURCE = """shape Order:
    id: Int
    created: Date
    amount: Float

source orders: Order = {dialect}.table("orders")

cutoff: Date = "2024-01-31"

lo: Float = 1.5

query recent:
    from orders
    where created >= cutoff and amount > lo
    select:
        id
"""
CHECK_USAGE = (
    "usage: pietto check [-h] [--project PROJECT] [--format {text,json}]"
    " [--check-mode {loose,checked,strict}] [--set NAME=VALUE] [path]\n"
    "pietto check: error: "
)
EXPLAIN_USAGE = CHECK_USAGE.replace("pietto check", "pietto explain")
EMIT_USAGE = (
    "usage: pietto emit-sql [-h] --dialect {postgres,mysql} [--output OUTPUT]"
    " [--format {text,json}] [--check-mode {loose,checked,strict}]"
    " [--set NAME=VALUE] path\npietto emit-sql: error: "
)


def _file(tmp_path: Path, dialect: str = "postgres", **values: str) -> Path:
    source = SOURCE.format(dialect=dialect)
    for old, new in values.items():
        source = source.replace(old, new)
    path = tmp_path / f"{dialect}-{len(values)}.pietto"
    path.write_text(source, encoding="utf-8")
    return path


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_mysql_refuses_each_relation_that_reads_a_constant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A relation that reads a constant, through a `def` or a relationship or
    by reading such a relation is refused; the others still emit."""
    path = _file(tmp_path, "mysql")
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\nquery everything:\n    from orders\n    select:\n        id\n"
        + "\nquery later:\n    from recent\n    select:\n        id\n"
        + "\ndef above(x: Float) -> Bool: return x > lo\n"
        + "\nquery by_def:\n    from orders\n    where above(amount)\n"
        + "    select:\n        id\n"
        + "\nshape Tag:\n    id: Int\n    weight: Float\n"
        + '\nsource tags: Tag = mysql.table("tags")\n'
        + "\nrelationship heavy(o: Order, t: Tag): o.id == t.id and t.weight > lo\n"
        + "\nquery by_relationship:\n    from orders\n"
        + "    inner join tags on heavy(orders, tags)\n"
        + "    select:\n        oid = orders.id\n",
        encoding="utf-8",
    )
    reason = "MySQL has no top-level constants yet; emit with --dialect postgres"
    refused = [("recent", 12), ("later", 23), ("by_def", 30), ("by_relationship", 44)]

    for settings in ((), ("--set", "lo=0.5")):
        code, out, err = _run(
            capsys, "emit-sql", "--dialect", "mysql", *settings, str(path)
        )
        assert (code, err) == (
            1,
            "".join(
                f"{path}:{line}:1 PIE-B1000 error: MySQL SQL emission is not "
                f"implemented for RelationIR: {name}. {reason}\n"
                for name, line in refused
            ),
        )
        assert "everything" in out and "recent" not in out
    code, document, err = _run(
        capsys, "emit-sql", "--dialect", "mysql", "--format", "json", str(path)
    )
    result = json.loads(document)
    assert (code, err) == (1, "")
    assert [item["name"] for item in result["artifacts"]] == ["everything"]
    assert [(item["code"], item["message"]) for item in result["diagnostics"]] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: {name}. {reason}",
        )
        for name, _ in refused
    ]


@pytest.mark.parametrize("dialect", ["postgres"])
def test_set_emits_the_bytes_of_the_value_written_in_the_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], dialect: str
) -> None:
    source = _file(tmp_path, dialect)
    written = _file(
        tmp_path, dialect, **{'"2024-01-31"': '"2024-02-29"', "= 1.5": "= -2.25"}
    )
    settings = ("--set", "cutoff=2024-02-29", "--set=lo=-2.25")

    code, overridden, err = _run(
        capsys, "emit-sql", "--dialect", dialect, *settings, str(source)
    )
    assert (code, err) == (0, "")
    assert _run(capsys, "emit-sql", "--dialect", dialect, str(written)) == (
        0,
        overridden,
        "",
    )
    assert "DATE '2024-02-29'" in overridden and "(-2.25)" in overridden
    code, document, err = _run(
        capsys,
        "emit-sql",
        "--dialect",
        dialect,
        "--format",
        "json",
        *settings,
        str(source),
    )
    assert (code, err) == (0, "")
    assert json.loads(document)["artifacts"][0]["sql"] + ";\n" in overridden


def test_check_and_explain_read_the_set_value(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _file(tmp_path)

    assert _run(capsys, "check", "--set", "lo=0.5", str(path)) == (
        0,
        f"OK: {path}\n",
        "",
    )
    code, out, _ = _run(
        capsys, "check", "--format", "json", "--set", "lo=0.5", str(path)
    )
    assert (code, json.loads(out)["ok"]) == (0, True)
    code, out, err = _run(capsys, "explain", "--set", "cutoff=2024-03-01", str(path))
    assert (code, err) == (0, "") and "recent (query)" in out


@pytest.mark.parametrize(
    ("written", "setting", "code"),
    [
        ({"= 1.5": "= 1"}, "lo=0.5", "PIE-S2391"),
        ({'"2024-01-31"': 'date("2024-01-31")'}, "cutoff=2024-02-29", "PIE-S2391"),
    ],
)
def test_set_never_hides_an_invalid_initializer(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    written: dict[str, str],
    setting: str,
    code: str,
) -> None:
    """`--set` changes a value for one run, never whether the file is valid:
    an initializer that is no literal of its type keeps its own error."""
    path = _file(tmp_path, **written)

    for argv in (("check",), ("explain",), ("emit-sql", "--dialect", "postgres")):
        plain = _run(capsys, *argv, str(path))
        assert plain[0] == 1 and f" {code} error: " in plain[1] + plain[2]
        assert _run(capsys, *argv, "--set", setting, str(path)) == plain


@pytest.mark.parametrize(
    ("argv", "usage", "message"),
    [
        (
            ("check", "--set", "lo=1.0", "--set", "lo=2.0", "{path}"),
            CHECK_USAGE,
            "--set lo is given more than once",
        ),
        (
            ("check", "--set", "missing=1", "{path}"),
            CHECK_USAGE,
            "--set missing: no top-level constant missing is declared",
        ),
        (
            ("explain", "--set", "cutoff=2024-02-30", "{path}"),
            EXPLAIN_USAGE,
            "--set cutoff: constant cutoff has type Date; write YYYY-MM-DD from "
            "1000-01-01 to 9999-12-31",
        ),
        (
            ("explain", "--set", "lo=1.0", "--set", "lo=1.0", "{path}"),
            EXPLAIN_USAGE,
            "--set lo is given more than once",
        ),
        (
            ("emit-sql", "--dialect", "postgres", "--set", "lo=2", "{path}"),
            EMIT_USAGE,
            "--set lo: constant lo has type Float; write a number with a decimal point "
            "such as 1.5 or -1.5",
        ),
        (
            (
                "emit-sql",
                "--dialect",
                "mysql",
                "--set",
                "a=1",
                "--set",
                "a=2",
                "{path}",
            ),
            EMIT_USAGE,
            "--set a is given more than once",
        ),
        (
            ("check", "--project", "{root}", "--set", "lo=1.0"),
            CHECK_USAGE,
            "--set and --project are mutually exclusive",
        ),
        (
            ("explain", "--project", "{root}", "--set", "lo=1.0"),
            EXPLAIN_USAGE,
            "--set and --project are mutually exclusive",
        ),
    ],
    ids=[
        "check_repeated",
        "check_undeclared",
        "explain_invalid_date",
        "explain_repeated",
        "emit_invalid_float",
        "emit_repeated",
        "check_project",
        "explain_project",
    ],
)
def test_text_usage_errors_exit_two_with_their_exact_text(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    argv: tuple[str, ...],
    usage: str,
    message: str,
) -> None:
    path = _file(tmp_path)
    filled = [item.format(path=path, root=tmp_path) for item in argv]

    assert _run(capsys, *filled) == (2, "", usage + message + "\n")


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (
            ("check", "--format", "json", "--set", "x=1", "--set", "x=1"),
            "--set x is given more than once",
        ),
        (
            ("check", "--format", "json", "--set", "flag=yes"),
            "--set flag: no top-level constant flag is declared",
        ),
        (
            ("emit-sql", "--dialect", "postgres", "--format", "json", "--set", "lo=x"),
            "--set lo: constant lo has type Float; write a number with a decimal point "
            "such as 1.5 or -1.5",
        ),
        (
            ("check", "--format", "json", "--set", "novalue"),
            "argument --set: expected NAME=VALUE",
        ),
    ],
    ids=["check_repeated", "check_undeclared", "emit_invalid", "malformed"],
)
def test_json_usage_errors_are_cli_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    argv: tuple[str, ...],
    message: str,
) -> None:
    path = _file(tmp_path)
    code, out, err = _run(capsys, *argv, str(path))

    assert (code, err) == (2, "")
    document = json.loads(out)
    (error,) = document["cli_errors"]
    assert (error["kind"], error["message"]) == ("usage", message)
    # A usage error after the arguments parse names the input path.
    assert document["path"] == (None if "novalue" in argv else str(path))


def test_migrate_and_project_emission_refuse_set(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _file(tmp_path)

    code, out, err = _run(capsys, "migrate", str(path), "--set", "lo=1.0")
    assert (code, out) == (2, "")
    assert err.endswith("pietto: error: unrecognized arguments: --set lo=1.0\n")
    code, out, err = _run(
        capsys, "emit-sql", "--project", str(tmp_path), "--set", "lo=1.0"
    )
    assert (code, err) == (2, "")
    (error,) = json.loads(out)["cli_errors"]
    assert error["message"] == "--set and --project are mutually exclusive"
    code, out, err = _run(
        capsys, "emit-sql", "--project", str(tmp_path), "--format", "text", "--set=a=b"
    )
    assert (code, out) == (2, "")
    assert err.endswith(
        "pietto emit-sql: error: --set and --project are mutually exclusive\n"
    )
