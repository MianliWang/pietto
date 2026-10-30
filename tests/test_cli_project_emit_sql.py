"""Installed Project emit-SQL: explicit contract input, public output, legacy compatibility.

Every positive document below is produced by the public command over an
ordinary authored project and is compared byte-for-byte with the installed
API pipeline's artifact for the same source, contract and policy; the data-only
public decoder is the only reader of command output. Real-filesystem checks
(symlinks, hard links, FIFOs, oversize files, atomic replacement) run against
real files; injected I/O faults are labelled as stubs. Installed-console and
native-target evidence live in the package smoke and the target facility.
"""

from __future__ import annotations

import contextlib
import errno
import io
import json
import os
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from _pietto_project_path_trust import (
    CLOUD_FILE_TAG,
    JUNCTION_TAG,
    later_descriptor_ctime,
    mutate_before_fallback_open,
    report_reparse_point,
)
import _pietto_sql_emission as probe
from pietto import _output_file as output_file
from pietto import cli
from pietto._project import path_trust
from pietto._project import project_sql_emission_cli as emission_cli
from pietto._project.path_trust import (
    ProjectIdentityUnavailableError,
    ProjectRootChangedError,
)
from pietto._project.project_sql_emission import (
    EmissionOutcome,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_contract import MAX_INPUT_BYTES

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("postgres", "mysql")
SENTINEL = "SECRET_SENTINEL_9f3a"
LEGACY_INPUT = (
    REPO_ROOT / "tests/fixtures/postgres/compatibility_ordering_metadata.pietto"
)
LEGACY_GOLDEN = (
    REPO_ROOT / "tests/fixtures/golden/emit_sql_compatibility_ordering_metadata.sql"
)
MYSQL_LEGACY_INPUT = (
    REPO_ROOT / "tests/fixtures/mysql/compatibility_ordering_metadata.pietto"
)


def run(argv: list[str]) -> tuple[int, bytes, str]:
    out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", newline="")
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    out.flush()
    return code, out.buffer.getvalue(), err.getvalue()


def project(
    tmp_path: Path,
    target: str,
    case: str = "G_emission_table_bag",
    variant: str = "bag",
    name: str = "project",
) -> tuple[Path, dict[str, Any]]:
    item = probe.fixture(target, case, variant)
    root = tmp_path / name
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG)
    for file, content in probe.source_files(item["source"]).items():
        (root / file).write_text(content, encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    return root, item


def argv(root: Path | str, target: str, kind: str = "table", **extra: str) -> list[str]:
    result = [
        "emit-sql",
        "--project",
        str(root),
        "--module",
        "main.pietto",
        "--kind",
        kind,
        "--name",
        "result",
        "--dialect",
        target,
        "--emission-contract",
        "contract.json",
    ]
    if "emission_contract" in extra:
        result[12] = extra.pop("emission_contract")
    for key, value in extra.items():
        result += ["--" + key.replace("_", "-"), value]
    return result


def api_bytes(tmp_path: Path, item: dict[str, Any], policy: str | None = None) -> bytes:
    """The installed API pipeline's artifact for the same input (the oracle)."""
    _, outcome = probe.build_case(
        tmp_path / "api", item["source"], item["contract"], policy or item["policy"]
    )
    return serialize_project_sql_emission(outcome)


def failure(out: bytes) -> dict[str, Any]:
    document = probe.decode_public(out)
    assert document["status"] != "VERIFIED" and document["artifact"] is None
    for key in ("sql", "fixed_values", "parameter_uses", "columns", "ranges"):
        assert key not in document
    return document


def kinds(out: bytes) -> list[tuple[str, str | None]]:
    return [(e["kind"], e["path"]) for e in failure(out)["cli_errors"]]


def open_descriptors() -> int:
    return len(os.listdir("/proc/self/fd")) if os.path.isdir("/proc/self/fd") else 0


# --- dispatch, defaults and legacy precedence -----------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_project_default_json_preserve_is_the_installed_api_artifact(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target)
    code, out, err = run(argv(root, target))
    assert (code, err) == (0, "")
    assert out == api_bytes(tmp_path, item)
    assert out.endswith(b"\n") and out.count(b"\n") == 1
    document = probe.decode_public(out)
    assert document["status"] == "VERIFIED"
    assert document["request"]["literal_policy"] == "preserve_literals"
    assert document["request"]["owner"] == {
        "module": "main.pietto",
        "kind": "table",
        "name": "result",
    }
    assert document["target"] == {
        "family": target,
        "release": "18.6" if target == "postgres" else "8.4.12",
        "environment": json.loads(item["contract"])["environment"],
    }
    # Explicit spellings, option order and `--` select the same document.
    for spelling in (
        ["emit-sql", f"--project={root}", "--emission-contract=contract.json"]
        + argv(root, target)[3:11],
        argv(root, target)[:1]
        + argv(root, target)[3:]
        + argv(root, target)[1:3]
        + ["--"],
        argv(root, target, format="json", literal_policy="preserve"),
    ):
        assert run(spelling) == (0, out, "")


def test_legacy_single_file_forms_are_unchanged(tmp_path: Path) -> None:
    code, out, err = run(["emit-sql", str(LEGACY_INPUT), "--dialect", "postgres"])
    assert (code, err) == (0, "") and out == LEGACY_GOLDEN.read_bytes()
    code, out, err = run(
        ["emit-sql", str(MYSQL_LEGACY_INPUT), "--dialect", "mysql", "--format", "json"]
    )
    document = json.loads(out)
    assert code == 0 and document["schema_version"] == 1
    assert document["command"] == "emit-sql" and document["ok"] is True
    assert set(document) == {
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    }
    output = tmp_path / "legacy.sql"
    code, out, err = run(
        [
            "emit-sql",
            str(LEGACY_INPUT),
            "--dialect",
            "postgres",
            "--output",
            str(output),
        ]
    )
    assert (code, out, err) == (0, b"", "")
    assert output.read_bytes() == LEGACY_GOLDEN.read_bytes()
    # A positional value that merely contains an option-like string is legacy.
    code, out, err = run(["emit-sql", "--dialect", "postgres", "--", "--project"])
    assert code == 2 and out == b"" and err.startswith("--project: error:")
    code, out, err = run(
        ["emit-sql", str(LEGACY_INPUT), "--dialect", "postgres", "--module", "x"]
    )
    assert code == 2 and out == b"" and "unrecognized arguments" in err
    code, out, err = run(["emit-sql", "missing.pietto", "--dialect", "sqlite"])
    assert code == 2 and out == b""
    assert run(["emit-sql", "--help"])[0] == 0
    assert b"project mode: pietto emit-sql --project" in run(["emit-sql", "--help"])[1]
    assert run([])[0] == 0 and run(["--version"])[0] == 0
    assert run(["check", str(LEGACY_INPUT)])[0] == 0
    assert run(["explain", str(LEGACY_INPUT), "--format", "json"])[0] == 0


@pytest.mark.parametrize(
    ("arguments", "fragment"),
    (
        ([], "required: --module, --kind, --name, --dialect, --emission-contract"),
        (["--module", "m", "--kind", "table", "--name", "r"], "required: --dialect"),
        (["--kind", "view"], "invalid choice"),
        (["--literal-policy", "rebind"], "invalid choice"),
        (["--format", "yaml"], "invalid choice"),
        (["--dialect", "sqlite"], "invalid choice"),
        (["--module", "a", "--module", "b"], "given more than once"),
        (["--format", "json", "--format", "json"], "given more than once"),
        (["--output", "a", "--output", "a"], "given more than once"),
        (["--dialect", "postgres", "--dialect", "postgres"], "given more than once"),
        (["--emission-contract"], "expected one argument"),
        (["--verbose"], "unrecognized arguments"),
        (["file.pietto"], "path and --project are mutually exclusive"),
        (["--", "file.pietto"], "path and --project are mutually exclusive"),
        (["--proj", "x"], "unrecognized arguments"),
    ),
)
def test_project_usage_errors_are_the_new_failure_family_without_side_effects(
    tmp_path: Path, arguments: list[str], fragment: str
) -> None:
    root = tmp_path / "absent"
    output = tmp_path / "never.json"
    code, out, err = run(
        ["emit-sql", "--project", str(root), "--output", str(output), *arguments]
    )
    assert (code, err) == (2, "")
    document = failure(out)
    assert document["status"] == "INPUT_REJECTED" and document["blockers"] == []
    assert [e["kind"] for e in document["cli_errors"]] == ["usage"]
    assert fragment in document["cli_errors"][0]["message"]
    assert not root.exists() and not output.exists()
    assert str(tmp_path) not in out.decode()


def test_text_usage_error_uses_stderr_banner_and_help_opens_nothing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "absent"
    code, out, err = run(["emit-sql", "--project", str(root), "--format", "text"])
    assert (code, out) == (2, b"")
    assert err.startswith("usage: pietto emit-sql --project PATH")
    assert "pietto emit-sql: error: the following arguments are required" in err
    # An ambiguous text request (repeated --format) falls back to the JSON document.
    code, out, err = run(
        ["emit-sql", "--project", str(root), "--format", "text", "--format", "text"]
    )
    assert code == 2 and err == "" and kinds(out) == [("usage", None)]
    code, out, err = run(["emit-sql", "--project", str(root), "--help"])
    assert (code, err) == (0, "") and out.startswith(
        b"usage: pietto emit-sql --project PATH"
    )
    assert not root.exists()


# --- explicit project boundary ---------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_explicit_project_requires_configured_explicit_modules(
    tmp_path: Path, target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, item = project(tmp_path, target)
    # Relative root from an unrelated working directory; no ancestor discovery.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    expected = api_bytes(tmp_path, item)
    assert run(argv(Path("..") / "project", target)) == (0, expected, "")
    nested = root / "nested"
    nested.mkdir()
    assert kinds(run(argv(nested, target))[1]) == [("config_read", "pietto.toml")]
    assert kinds(run(argv(tmp_path / "missing", target))[1]) == [("project_root", None)]
    assert kinds(run(argv(root / "pietto.toml", target))[1]) == [("project_root", None)]
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "pietto.toml").write_text(
        'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (legacy / "main.pietto").write_text((root / "main.pietto").read_text())
    (legacy / "contract.json").write_text(item["contract"])
    assert kinds(run(argv(legacy, target))[1]) == [("config_schema", "pietto.toml")]
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "pietto.toml").write_text("schema_version = [\n")
    code, out, err = run(argv(broken, target))
    assert code == 2 and err == "" and [k for k, _ in kinds(out)] == ["config_parse"]
    # Environment variables never select a project or a target.
    monkeypatch.setenv("PIETTO_PROJECT", str(root))
    assert kinds(run(argv(tmp_path / "missing", target))[1]) == [("project_root", None)]


@pytest.mark.parametrize(
    ("query", "error"),
    [
        (
            "query q:\n    from result\n    let r = nowhere\n"
            "    inner join r on True\n    select:\n        x = 1\n",
            ("PIE-S2301", "Unknown relation: nowhere"),
        ),
        (
            "query q(n: Int):\n    from result\n    select:\n        x = 1\n"
            "    limit n\n",
            ("PIE-S2355", "Query parameters are not available in this position."),
        ),
    ],
)
@pytest.mark.parametrize("target", TARGETS)
def test_a_naming_error_never_masks_a_module_error_in_emission(
    tmp_path: Path, target: str, query: str, error: tuple[str, str]
) -> None:
    root, _ = project(tmp_path, target)
    (root / "other.pietto").write_text(
        'from "missing.pietto" import (\n    shape Row)\n' + query,
        encoding="utf-8",
    )
    code, out, err = run(argv(root, target))
    document = failure(out)
    assert (code, err, document["status"]) == (1, "", "BLOCKED")
    assert [
        (item["code"], item["message"], item["location"]["path"])
        for item in document["diagnostics"]
    ] == [
        (
            "PIE-S2701",
            'Unresolved module import target: "missing.pietto"',
            "other.pietto",
        ),
        (*error, "other.pietto"),
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_a_selected_file_name_that_is_not_utf8_rejects_emission(
    tmp_path: Path, target: str
) -> None:
    root, _ = project(tmp_path, target)
    try:
        Path(os.fsdecode(os.fsencode(root) + b"/\xff.pietto")).write_bytes(b"")
    except (OSError, UnicodeError):
        pytest.skip("this file system refuses a file name that is not UTF-8")
    # Check reads the file, but an emission document, which is UTF-8 and names
    # every selected source, cannot: a document says so, never a traceback.
    assert cli.main(["check", "--project", str(root)]) == 0
    code, out, err = run(argv(root, target))
    document = failure(out)
    rejected = [
        {
            "kind": "project_path",
            "message": "Project source path must be valid UTF-8 to emit SQL:"
            ' "\\udcff.pietto"; rename it.',
            "path": None,
        }
    ]
    assert (code, err, document["status"], document["cli_errors"]) == (
        2,
        "",
        "INPUT_REJECTED",
        rejected,
    )
    # A diagnostic located in that file cannot be carried either: the error
    # names the file in its place.
    unnamed = Path(os.fsdecode(os.fsencode(root) + b"/\xff.pietto"))
    unnamed.write_text("query bad:\n    from\n")
    code, out, err = run(argv(root, target))
    document = failure(out)
    assert (code, document["cli_errors"], document["diagnostics"]) == (
        2,
        rejected,
        [],
    )
    # An input error about that file keeps its kind and message, path null.
    unnamed.write_bytes(b"\xff")
    assert kinds(run(argv(root, target))[1]) == [
        ("source_read", None),
        ("project_path", None),
    ]
    # A project refused for another reason reports it as before: a refusal
    # of the selected owner (its blocker, its selector, its contract or the
    # target family), a parse or semantic error located elsewhere with exit 1
    # and its diagnostics, or its own input error.
    unnamed.write_bytes(b"")
    main = root / "main.pietto"

    def changed(position: int, value: str, kind: str = "table") -> list[str]:
        arguments = argv(root, target, kind)
        arguments[position] = value
        return arguments

    main.write_text(
        main.read_text() + "\nquery counted:\n    from rows\n    select:\n"
        "        n = count(ratio)\n"
    )
    code, out, err = run(changed(8, "counted", "query"))
    document = failure(out)
    assert (code, document["status"], document["cli_errors"]) == (1, "BLOCKED", [])
    assert [item["subject"]["detail"] for item in document["blockers"]] == [
        "count_argument_outside_reviewed_int_domain"
    ]
    assert kinds(run(changed(8, "nosuch"))[1]) == [("emission_selector", None)]
    (root / "empty.json").write_text("{}")
    assert [kind for kind, _ in kinds(run(changed(12, "empty.json"))[1])] == [
        "emission_contract_schema"
    ]
    other = "mysql" if target == "postgres" else "postgres"
    assert kinds(run(changed(10, other))[1]) == [
        ("emission_contract_schema", "target/family")
    ]
    # A selector listing names the file escaped, as project_path does.
    assert failure(run(changed(4, "nosuch.pietto"))[1])["cli_errors"] == [
        {
            "kind": "emission_selector",
            "message": "No project module matches --module; project modules:"
            " main.pietto, \\udcff.pietto.",
            "path": None,
        }
    ]
    main.write_text(main.read_text().partition("\nquery counted:")[0])
    main.write_text(
        main.read_text() + "\nquery bad:\n    from nosuch\n    select:\n        id\n"
    )
    code, out, err = run(argv(root, target))
    document = failure(out)
    assert (code, document["status"], document["cli_errors"]) == (1, "BLOCKED", [])
    assert [item["code"] for item in document["diagnostics"]] == ["PIE-S2301"]
    (root / "pietto.toml").write_text(
        'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n'
    )
    assert kinds(run(argv(root, target))[1]) == [("config_schema", "pietto.toml")]


def test_a_diagnostic_naming_a_path_that_is_not_utf8_shows_it_escaped(
    tmp_path: Path,
) -> None:
    root, _ = project(tmp_path, "postgres")
    try:
        directory = Path(os.fsdecode(os.fsencode(root) + b"/m\xff"))
        directory.mkdir()
    except (OSError, UnicodeError):
        pytest.skip("this file system refuses a file name that is not UTF-8")
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["**/*.pietto"]\n'
    )
    (directory / "a.pietto").write_text(
        "shape A:\n    id: Int\n"
        'source items: A = postgres.table("items")\n'
        "def twice(x: Int) -> Int:\n    return x * 2\n"
        "export (\n    shape A,\n    source items)\n"
    )

    def diagnostics(source: str) -> list[tuple[str, str, str]]:
        (root / "b.pietto").write_text(source)
        code, out, err = run(argv(root, "postgres"))
        document = failure(out)
        assert (code, err, document["status"], document["cli_errors"]) == (
            1,
            "",
            "BLOCKED",
            [],
        )
        return [
            (item["code"], item["message"], item["location"]["path"])
            for item in document["diagnostics"]
        ]

    # No Pietto string spells that path, so neither b.pietto's PIE-S2701 nor
    # an import hint suggests it. A def hint names it, escaped as
    # project_path names it, and the error located in b.pietto is kept.
    assert diagnostics('from "a.pietto" import (\n    shape A)\n') == [
        ("PIE-S2701", 'Unresolved module import target: "a.pietto"', "b.pietto")
    ]
    assert diagnostics(
        "shape B:\n    id: Int\n"
        'source bs: B = postgres.table("b")\n'
        "query q:\n    from items\n    select:\n        id\n"
        "query p:\n    from bs\n    select:\n        doubled = twice(id)\n"
    ) == [
        ("PIE-S2301", "Unknown relation: items", "b.pietto"),
        (
            "PIE-S2103",
            "Unknown function: twice; twice is a def of m\\udcff/a.pietto, which"
            " a module cannot import: declare it in this module",
            "b.pietto",
        ),
    ]
    # A source directory that is not valid UTF-8 and cannot be read is named
    # beside its own error, whose path is then null.
    (root / "b.pietto").unlink()
    (directory / "a.pietto").unlink()
    directory.chmod(0)
    try:
        if os.access(directory, os.R_OK):
            pytest.skip("this process reads a directory without permission")
        assert kinds(run(argv(root, "postgres"))[1]) == [
            ("project_glob", None),
            ("project_path", None),
        ]
        assert failure(run(argv(root, "postgres"))[1])["cli_errors"][1]["message"] == (
            'Project source path must be valid UTF-8 to emit SQL: "m\\udcff";'
            " rename it."
        )
    finally:
        directory.chmod(0o700)


def test_an_unopened_contract_path_that_is_not_utf8_is_named_by_null(
    tmp_path: Path,
) -> None:
    root, _ = project(tmp_path, "postgres")
    # The document is UTF-8 text, where that path has none.
    contract = os.fsdecode(b"c\xff.json")
    for text in ("json", "text"):
        code, out, err = run(
            argv(root, "postgres", emission_contract=contract, format=text)
        )
        assert code == 2
    assert kinds(run(argv(root, "postgres", emission_contract=contract))[1]) == [
        ("emission_contract_read", None)
    ]
    assert err == (
        "pietto.sql-emission.v1 INPUT_REJECTED\nerror emission_contract_read:"
        " Emission contract file could not be opened inside the project root.\n"
    )


@pytest.mark.parametrize("target", TARGETS)
def test_owner_selection_is_exact_and_never_first_match(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target, "N_imported_chain", "bag")
    expected = api_bytes(tmp_path, item)
    assert run(argv(root, target, kind="query")) == (0, expected, "")
    selector = [("emission_selector", None)]
    assert kinds(run(argv(root, target, kind="table"))[1]) == selector
    for module, kind, name in (
        ("main.pietto", "table", "Alias"),  # an import facade is not an owner
        ("b.pietto", "table", "Public"),
        ("b.pietto", "table", "first"),
        ("a.pietto", "query", "first"),
        ("missing.pietto", "table", "first"),
        ("main.pietto", "query", "absent"),
        ("main.pietto", "query", ""),
    ):
        arguments = argv(root, target, kind=kind)
        arguments[4], arguments[8] = module, name
        assert kinds(run(arguments)[1]) == selector, (module, kind, name)
    # The exact defining occurrence in another module is its own owner.
    arguments = argv(root, target, kind="table")
    arguments[4], arguments[8] = "a.pietto", "first"
    code, out, err = run(arguments)
    document = probe.decode_public(out)
    assert code == 0 and document["request"]["owner"] == {
        "module": "a.pietto",
        "kind": "table",
        "name": "first",
    }
    # The same spelling in a different module is a different owner: the contract
    # binds only main.pietto's source, so other.pietto's result lacks realization.
    root, item = project(tmp_path, target, name="twin")
    (root / "other.pietto").write_text(
        (root / "main.pietto").read_text(), encoding="utf-8"
    )
    code, out, err = run(argv(root, target))
    assert (
        code == 0
        and probe.decode_public(out)["request"]["owner"]["module"] == "main.pietto"
    )
    arguments = argv(root, target)
    arguments[4] = "other.pietto"
    code, out, err = run(arguments)
    document = failure(out)
    assert code == 1 and document["status"] == "BLOCKED"
    assert [b["code"] for b in document["blockers"]] == ["PIE-B1001"]


@pytest.mark.parametrize("target", TARGETS)
def test_relation_lets_emit_with_their_declaration_and_are_never_selected(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target, "L_let_relations", "chain")
    expected = api_bytes(tmp_path, item)
    assert item["policy"] == "bind_safe_literals"
    arguments = argv(root, target, kind="query", literal_policy="bind-safe")
    assert run(arguments) == (0, expected, "")
    document = probe.decode_public(expected)
    assert document["request"]["owner"] == {
        "module": "main.pietto",
        "kind": "query",
        "name": "result",
    }
    # A let is a block of its declaration: its name is no owner, in any kind.
    for kind, name in (("query", "first"), ("query", "second"), ("table", "first")):
        arguments = argv(root, target, kind=kind)
        arguments[8] = name
        assert kinds(run(arguments)[1]) == [("emission_selector", None)], name


@pytest.mark.parametrize("target", TARGETS)
def test_existence_reads_emit_through_the_project_command(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target, "L_relation_exists", "kept")
    expected = api_bytes(tmp_path, item)
    arguments = argv(root, target, kind="query", literal_policy="bind-safe")
    assert run(arguments) == (0, expected, "")
    document = probe.decode_public(expected)
    # Each read is its own EXISTS subquery over a complete named producer.
    assert document["sql"].count("EXISTS (SELECT 1 FROM ") == 2


@pytest.mark.parametrize("target", TARGETS)
def test_a_correlated_existence_read_emits_through_the_project_command(
    tmp_path: Path, target: str
) -> None:
    # Phase70 S10: the let with a capture line is the derived relation of its
    # own read, correlated to the reading body's FROM row.
    item = probe.join_witness(
        target,
        "query result:\n    let matched:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key and rhs.id > 0\n        select:\n"
        "            id\n    from lhs\n    where exists matched\n    select:\n"
        "        a = lhs.id\n",
        policy="bind_safe_literals",
    )
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG)
    for file, content in probe.source_files(item["source"]).items():
        (root / file).write_text(content, encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    expected = api_bytes(tmp_path, item)
    arguments = argv(root, target, kind="query", literal_policy="bind-safe")
    assert run(arguments) == (0, expected, "")
    document = json.loads(expected)
    quote = '"' if target == "postgres" else "`"
    outer = f"{quote}s1{quote}.{quote}key value{quote}"
    assert document["status"] == "VERIFIED" and len(document["parameter_uses"]) == 1
    assert document["sql"].count("EXISTS (SELECT 1 FROM (SELECT ") == 1
    assert document["sql"].count(outer) == 2


@pytest.mark.parametrize("target", TARGETS)
def test_a_lateral_join_emits_through_the_project_command(
    tmp_path: Path, target: str
) -> None:
    # Phase70 S12: the let with a capture line is the JOIN's LATERAL derived
    # relation, correlated to the JOIN's left input alias.
    item = probe.join_witness(
        target,
        "query result:\n    let m:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key and rhs.id > 0\n        select:\n"
        "            id\n    from lhs\n    let m1 = m\n    cross join m1\n"
        "    select:\n        a = lhs.id\n        b = m1.id\n",
        policy="bind_safe_literals",
    )
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG)
    for file, content in probe.source_files(item["source"]).items():
        (root / file).write_text(content, encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    expected = api_bytes(tmp_path, item)
    arguments = argv(root, target, kind="query", literal_policy="bind-safe")
    assert run(arguments) == (0, expected, "")
    document = json.loads(expected)
    quote = '"' if target == "postgres" else "`"
    outer = f"= {quote}m0{quote}.{quote}key value{quote})"
    assert document["status"] == "VERIFIED" and len(document["parameter_uses"]) == 1
    assert document["sql"].count(" CROSS JOIN LATERAL (SELECT ") == 1
    assert document["sql"].count(outer) == 1


@pytest.mark.parametrize("target", TARGETS)
def test_correlated_scalar_and_in_reads_emit_through_the_project_command(
    tmp_path: Path, target: str
) -> None:
    # Phase70 S14: a NOT IN and a scalar read of two lets with capture lines;
    # each let is the derived relation of its own read.
    item = probe.join_witness(
        target,
        "query result:\n    let matched:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key and rhs.id > 0\n        select:\n"
        "            id\n    let keyed:\n        capture lhs\n        from rhs\n"
        "        where rhs.id == lhs.id\n        select:\n            key\n"
        "    from lhs\n    where lhs.id not in matched\n    select:\n"
        "        a = lhs.id\n        k = scalar keyed.key\n",
        policy="bind_safe_literals",
    )
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG)
    for file, content in probe.source_files(item["source"]).items():
        (root / file).write_text(content, encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    expected = api_bytes(tmp_path, item)
    arguments = argv(root, target, kind="query", literal_policy="bind-safe")
    assert run(arguments) == (0, expected, "")
    document = json.loads(expected)
    q = '"' if target == "postgres" else "`"
    assert document["status"] == "VERIFIED" and len(document["parameter_uses"]) == 1
    assert (
        document["sql"].count(f" NOT IN (SELECT {q}e0{q}.{q}c0{q} FROM (SELECT ") == 1
    )
    assert document["sql"].count(f"(SELECT {q}e1{q}.{q}c0{q} FROM (SELECT ") == 1
    assert [(c["label"], c["nullable"]) for c in document["columns"]] == [
        ("a", False),
        ("k", True),
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_a_correlated_order_and_limit_read_emits_only_for_postgres(
    tmp_path: Path, target: str
) -> None:
    # Owner decision 2026-10-15 (D70.05): a scalar read of a let ending in
    # ORDER BY and LIMIT wraps the let's result body in its own derived table
    # on PostgreSQL; the MySQL command refuses it with one PIE-B1003 blocker.
    item = probe.join_witness(
        target,
        "query result:\n    let last:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key\n        select:\n            id\n"
        "        order by:\n            id desc\n        limit 1\n"
        "    from lhs\n    select:\n        a = lhs.id\n        k = scalar last.id\n",
        policy="bind_safe_literals",
    )
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG)
    for file, content in probe.source_files(item["source"]).items():
        (root / file).write_text(content, encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    expected = api_bytes(tmp_path, item)
    code, out, err = run(argv(root, target, kind="query", literal_policy="bind-safe"))
    assert (out, err) == (expected, "")
    if target == "postgres":
        document = json.loads(out)
        assert (code, document["status"]) == (0, "VERIFIED")
        assert document["sql"].count(' ORDER BY "t0"."c1" DESC LIMIT 1) AS "e0")') == 1
        return
    document = failure(out)
    assert (code, document["status"], document["cli_errors"]) == (1, "BLOCKED", [])
    lines = (root / "main.pietto").read_text(encoding="utf-8").splitlines()
    line = lines.index("        k = scalar last.id") + 1
    assert document["diagnostics"] == []
    assert [
        (
            b["code"],
            b["subject"]["detail"],
            b["location"]["line"],
            b["location"]["column"],
        )
        for b in document["blockers"]
    ] == [
        (
            "PIE-B1003",
            "mysql_correlated_order_or_limit_read_not_admitted",
            line,
            13,
        )
    ]


# --- contract read boundary ------------------------------------------------------


@pytest.mark.parametrize("fallback", (False, True))
@pytest.mark.parametrize("target", TARGETS)
def test_contract_read_is_contained_bounded_and_closes_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str, fallback: bool
) -> None:
    monkeypatch.setattr(
        path_trust, "_supports_directory_relative_open", lambda: not fallback
    )
    root, item = project(tmp_path, target)
    expected = api_bytes(tmp_path, item)
    outside = tmp_path / "outside.json"
    outside.write_text(item["contract"])
    (root / "sub").mkdir()
    (root / "sub" / "contract.json").write_text(item["contract"])
    os.symlink(outside, root / "link.json")
    os.symlink(root / "sub", root / "linkdir")
    (tmp_path / "escape").mkdir()
    (tmp_path / "escape" / "contract.json").write_text(item["contract"])
    os.symlink(tmp_path / "escape", root / "escape")
    (root / "hard.json").hardlink_to(outside)
    os.mkfifo(root / "fifo.json")
    (root / "dir.json").mkdir()
    read = "emission_contract_read"
    before = open_descriptors()
    for contract, path in (
        (str(outside), None),
        ("../outside.json", None),
        ("./contract.json", None),
        ("sub/../contract.json", None),
        ("sub//contract.json", None),
        ("contract.json/", None),
        ("", None),
        ("link.json", "link.json"),
        ("linkdir/contract.json", "linkdir/contract.json"),
        ("escape/contract.json", "escape/contract.json"),
        ("fifo.json", "fifo.json"),
        ("dir.json", "dir.json"),
        ("absent.json", "absent.json"),
        ("sub", "sub"),
    ):
        code, out, err = run(argv(root, target, emission_contract=contract))
        assert (code, err) == (2, ""), contract
        assert kinds(out) == [(read, path)], contract
        assert str(root) not in out.decode() and str(outside) not in out.decode()
        if contract in {"linkdir/contract.json", "escape/contract.json"}:
            assert failure(out)["cli_errors"][0]["message"] == (
                "Emission contract file could not be opened inside the project root."
            )
    assert open_descriptors() == before
    # A hard link to a regular file inside the root is a regular file.
    assert run(argv(root, target, emission_contract="hard.json")) == (0, expected, "")
    assert run(argv(root, target, emission_contract="sub/contract.json")) == (
        0,
        expected,
        "",
    )
    # The 1 MiB ceiling is inclusive and enforced while reading.
    padded = item["contract"].encode()
    exact = padded + b" " * (MAX_INPUT_BYTES - len(padded))
    (root / "exact.json").write_bytes(exact)
    (root / "over.json").write_bytes(exact + b" ")
    code, out, err = run(argv(root, target, emission_contract="exact.json"))
    assert code == 0 and probe.decode_public(out)["status"] == "VERIFIED"
    code, out, err = run(argv(root, target, emission_contract="over.json"))
    assert kinds(out) == [(read, "over.json")]
    assert str(MAX_INPUT_BYTES) in failure(out)["cli_errors"][0]["message"]
    assert open_descriptors() == before


@pytest.mark.parametrize(
    ("reparse_tag", "admitted"),
    ((JUNCTION_TAG, False), (CLOUD_FILE_TAG, True)),
    ids=("junction", "cloud-file"),
)
def test_contract_parent_name_surrogate_is_not_traversed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reparse_tag: int, admitted: bool
) -> None:
    """Simulated Windows: a junction parent is refused; other reparse tags are not links."""
    root, item = project(tmp_path, "postgres")
    (root / "sub").mkdir()
    (root / "sub" / "contract.json").write_text(item["contract"])
    monkeypatch.setattr(path_trust, "_supports_directory_relative_open", lambda: False)
    report_reparse_point(monkeypatch, (root / "sub").resolve(), reparse_tag)

    code, out, err = run(argv(root, "postgres", emission_contract="sub/contract.json"))

    if admitted:
        assert (code, err) == (0, "")
        assert probe.decode_public(out)["status"] == "VERIFIED"
        return
    assert (code, err) == (2, "") and kinds(out) == [
        ("emission_contract_read", "sub/contract.json")
    ]
    assert failure(out)["cli_errors"][0]["message"] == (
        "Emission contract file could not be opened inside the project root."
    )


def test_contract_identity_controls_are_mapped_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stubbed: the trusted-open primitives are made to report the controls."""
    root, _ = project(tmp_path, "postgres")
    real = emission_cli._fstat_state
    states: list[Any] = []

    def drifting(descriptor: int) -> Any:
        state = real(descriptor)
        states.append(state)
        if len(states) == 2:
            return type(state)(
                physical_identity=state.physical_identity,
                file_type=state.file_type,
                size=state.size + 1,
                mtime_ns=state.mtime_ns,
                ctime_ns=state.ctime_ns,
            )
        return state

    monkeypatch.setattr(emission_cli, "_fstat_state", drifting)
    document = failure(run(argv(root, "postgres"))[1])
    assert (
        document["cli_errors"][0]["message"]
        == "Emission contract file changed while being read."
    )
    monkeypatch.setattr(emission_cli, "_fstat_state", real)
    for error, message in (
        (
            ProjectRootChangedError("x"),
            "Project root identity changed while reading the emission contract.",
        ),
        (
            ProjectIdentityUnavailableError("x"),
            "Project filesystem identity is unavailable.",
        ),
        (
            PermissionError(errno.EACCES, SENTINEL),
            "Emission contract file could not be opened inside the project root.",
        ),
    ):

        def failing(*args: Any, error: Exception = error) -> int:
            raise error

        monkeypatch.setattr(emission_cli, "_open_pinned_file", failing)
        code, out, err = run(argv(root, "postgres"))
        assert (code, err) == (2, "") and kinds(out) == [
            ("emission_contract_read", "contract.json")
        ]
        assert failure(out)["cli_errors"][0]["message"] == message
        assert SENTINEL not in out.decode()


@pytest.mark.parametrize("mutation", ("none", "replace", "size", "mtime"))
def test_fallback_contract_open_race_is_reported_as_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """Real files: the contract changes between the fallback's inspection and open."""
    root, _ = project(tmp_path, "postgres")
    fired = mutate_before_fallback_open(monkeypatch, root / "contract.json", mutation)
    code, out, err = run(argv(root, "postgres"))

    assert fired == [True]
    if mutation == "none":
        assert (code, err) == (0, "")
        assert probe.decode_public(out)["status"] == "VERIFIED"
        return
    assert (code, err) == (2, "") and kinds(out) == [
        ("emission_contract_read", "contract.json")
    ]
    assert (
        failure(out)["cli_errors"][0]["message"]
        == "Emission contract file changed while being read."
    )


def test_descriptor_ctime_split_is_tolerated_only_where_ctime_is_not_comparable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulated Windows CPython: os.fstat reports a later st_ctime than os.lstat."""
    root, _ = project(tmp_path, "postgres")
    contract = os.stat(root / "contract.json")
    monkeypatch.setattr(path_trust, "_supports_directory_relative_open", lambda: False)
    later_descriptor_ctime(monkeypatch)
    monkeypatch.setattr(path_trust, "_CTIME_IS_COMPARABLE", False)
    code, out, err = run(argv(root, "postgres"))
    assert (code, err) == (0, "")
    assert probe.decode_public(out)["status"] == "VERIFIED"

    monkeypatch.setattr(path_trust, "_CTIME_IS_COMPARABLE", True)
    later_descriptor_ctime(monkeypatch, only=(contract.st_dev, contract.st_ino))
    code, out, err = run(argv(root, "postgres"))
    assert (code, err) == (2, "") and kinds(out) == [
        ("emission_contract_read", "contract.json")
    ]
    assert (
        failure(out)["cli_errors"][0]["message"]
        == "Emission contract file changed while being read."
    )


# --- strict input and compiler outcomes -------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_strict_contract_input_and_target_agreement(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target)
    contract = json.loads(item["contract"])
    schema = "emission_contract_schema"

    def with_bytes(data: bytes) -> tuple[int, bytes, str]:
        (root / "variant.json").write_bytes(data)
        return run(argv(root, target, emission_contract="variant.json"))

    def encoded(value: Any) -> bytes:
        return json.dumps(value, ensure_ascii=False).encode("utf-8")

    for data in (
        b"\xef\xbb\xbf" + item["contract"].encode(),
        item["contract"].encode()[:-1] + b'"',
        item["contract"].encode() + b" {}",
        b'{"format": 1, "format": "pietto.emission-contract.v1", "target": {}, "sources": [], "environment": []}',
        item["contract"].encode().replace(b'"scan"', '"scán"'.encode("latin-1")),
        encoded({**contract, "extra": 1}),
        encoded({k: v for k, v in contract.items() if k != "environment"}),
        encoded({**contract, "target": {"family": target, "release": " 18.6"}}),
    ):
        code, out, err = with_bytes(data)
        assert (code, err) == (2, ""), data[:40]
        assert {k for k, _ in kinds(out)} == {schema}, data[:40]
    # Bool-as-ordinal and a malformed unused description are rejected even when
    # the selected closure is otherwise complete.
    bad_ordinal = json.loads(item["contract"])
    bad_ordinal["sources"][0]["fields"][0]["ordinal"] = True
    assert kinds(with_bytes(encoded(bad_ordinal))[1]) == [
        ("emission_selector", "sources/0/fields/0/ordinal")
    ]
    unused = json.loads(item["contract"])
    unused["sources"].append(
        {
            **unused["sources"][0],
            "selector": {"module": "main.pietto", "kind": "source", "name": "ghost"},
        }
    )
    assert kinds(with_bytes(encoded(unused))[1]) == [
        ("emission_selector", "sources/1/selector")
    ]
    # A well-formed release outside the allowlist is BLOCKED, never negotiated.
    unsupported = {**contract, "target": {"family": target, "release": "17.0"}}
    code, out, err = with_bytes(encoded(unsupported))
    document = failure(out)
    assert (code, document["status"], document["cli_errors"]) == (1, "BLOCKED", [])
    assert [b["code"] for b in document["blockers"]] == ["PIE-B1003"]
    # CLI/file target families must agree; neither wins.
    other = "mysql" if target == "postgres" else "postgres"
    arguments = argv(root, target)
    arguments[10] = other
    assert kinds(run(arguments)[1]) == [(schema, "target/family")]
    # A same-scope declaration conflict is a premise conflict, not a repair.
    conflict = json.loads(item["contract"])
    conflict["environment"].append(
        {"key": "client_encoding", "scope": "statement", "value": "LATIN1"}
    )
    code, out, err = with_bytes(encoded(conflict))
    document = failure(out)
    assert code == 1 and {b["code"] for b in document["blockers"]} == {"PIE-B1005"}
    assert document["cli_errors"] == [] and err == ""


@pytest.mark.parametrize("target", TARGETS)
def test_compiler_outcomes_keep_complete_diagnostics_without_candidate_sql(
    tmp_path: Path, target: str
) -> None:
    for case, variant, kind, code in (
        ("K_emission_rejected", "duplicate_selector", "query", 2),
        ("K_emission_rejected", "stale_selector", "query", 2),
        ("L_emission_blocked", "missing_source", "query", 1),
        ("L_emission_blocked", "timestamp_meaning", "query", 0),
        ("L_emission_blocked", "uuid_meaning", "query", 0),
        ("L_emission_blocked", "decimal_mismatch", "query", 1),
        ("V_result_blocked", "hidden_strict_fd", "query", 1),
        ("S_set_boundaries", "limit_zero_operand", "query", 0),
        ("M_named_chain", "table_bag", "table", 0),
        ("S_set_forms", "union_all", "query", 0),
        ("O_result_order", "ordinary_desc", "query", 0),
        ("Z_aggregate_joined", "inner_fanout", "query", 0),
        ("A_window_frame", "rows", "query", 0),
    ):
        root, item = project(tmp_path, target, case, variant, name=f"{case}-{variant}")
        expected = api_bytes(root.parent / f"{case}-{variant}-api", item)
        arguments = argv(root, target, kind=kind)
        if item["policy"] == "bind_safe_literals":
            arguments += ["--literal-policy", "bind-safe"]
        actual, out, err = run(arguments)
        assert (actual, out, err) == (code, expected, ""), (case, variant)
        document = probe.decode_public(out)
        assert document["status"] == (
            "VERIFIED" if code == 0 else probe.expected_status(case, variant, target)
        )
        if document["status"] == "VERIFIED":
            assert (
                document["columns"] and document["requirements"] and document["ranges"]
            )
            assert "blockers" not in document and "cli_errors" not in document
    # MySQL keeps FULL as a typed non-support while PostgreSQL admits it.
    root, item = project(tmp_path, target, "V_join_full", "restricted", name="full")
    code, out, err = run(argv(root, target, kind="query"))
    assert out == api_bytes(root.parent / "full-api", item)
    assert code == (0 if target == "postgres" else 1)
    # A whole-project parse or semantic ERROR blocks emission with every
    # diagnostic in order and no cli_errors. A cross-family comparison is such
    # an ERROR rather than an emission blocker, also for a sibling declaration.
    for name, body, prefix in (
        ("parse", "table result:\n    from rows\n    select\n        id\n", "PIE-P"),
        (
            "semantic",
            "table result:\n    from rows\n    select:\n        missing\n",
            "PIE-S",
        ),
        (
            "comparison",
            'table result:\n    from rows\n    where id == "x"\n    select:\n        id\n',
            "PIE-S2105",
        ),
        (
            "sibling_comparison",
            "table result:\n    from rows\n    select:\n        id\n"
            'query other:\n    from rows\n    where id == "x"\n    select:\n        id\n',
            "PIE-S2105",
        ),
        # A declaration error blocks emission as it fails a check.
        (
            "sibling_declaration",
            "table result:\n    from rows\n    select:\n        id\n"
            "constraint other(x: Int) -> Int:\n    return x > 0\n",
            "PIE-S2401",
        ),
        # A sibling's header beside a table-function let stays unadmitted.
        (
            "unadmitted_sibling_header_beside_table_function",
            "table result:\n    from rows\n    select:\n        id\n"
            "query other(k: Int):\n    let l:\n"
            "        from generate_series(1, 3, 1) as n\n"
            "        select:\n            n\n    from l\n    select:\n        n\n",
            "PIE-S2346",
        ),
    ):
        root, item = project(tmp_path, target, name=name)
        source = (root / "main.pietto").read_text().split("table result:", 1)[0]
        (root / "main.pietto").write_text(source + body)
        code, out, err = run(argv(root, target))
        document = failure(out)
        assert (code, document["status"], document["cli_errors"]) == (1, "BLOCKED", [])
        assert document["diagnostics"] and all(
            d["code"].startswith(prefix) and d["severity"] == "error"
            for d in document["diagnostics"]
        )
        if prefix in ("PIE-S2105", "PIE-S2346", "PIE-S2401"):
            assert len(document["diagnostics"]) == 1
        assert probe.decode_public(out)["blockers"] == []
        code, out, err = run(argv(root, target, format="text"))
        assert (code, out) == (1, b"")
        assert err.startswith("pietto.sql-emission.v1 BLOCKED\n") and prefix in err


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("stage", ["semantics", "def", "planning"])
def test_the_recursion_limit_blocks_emission_with_one_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str, stage: str
) -> None:
    # A WHERE of 3,000 conditions used to raise RecursionError out of emit-sql;
    # planning or emitting a shallower one may exhaust the limit first, and
    # is reported over the selected module even beside a module that nests
    # deeper but is neither planned nor emitted. Def calls count as inlined.
    root, _ = project(tmp_path, target)
    source = (root / "main.pietto").read_text().split("table result:", 1)[0]
    if stage == "semantics":
        condition = " and ".join(["id == 1"] * 3000)
    elif stage == "def":
        source = "def one(x: Int) -> Bool | None: return x == 1\n" + source
        condition = " and ".join(["one(id)"] * 3000)
    else:
        condition = "id == 1"
        (root / "a.pietto").write_text(
            source
            + "table other:\n    from rows\n"
            + f"    where {' and '.join(['id == 1'] * 50)}\n"
            + "    select:\n        id\n"
        )

        def exhausted(*args: object, **kwargs: object) -> object:
            del args, kwargs
            raise RecursionError

        monkeypatch.setattr(emission_cli, "build_project_sql_plan", exhausted)
    (root / "main.pietto").write_text(
        source
        + f"table result:\n    from rows\n    where {condition}\n"
        + "    select:\n        id\n"
    )

    code, out, err = run(argv(root, target))

    document = failure(out)
    assert (code, err, document["status"], document["cli_errors"]) == (
        1,
        "",
        "BLOCKED",
        [],
    )
    assert probe.decode_public(out)["blockers"] == []
    assert document["diagnostics"] == [
        {
            "code": "PIE-S2006",
            "severity": "error",
            "message": "Semantic analysis recursion limit exceeded while "
            "processing source.",
            "location": {
                "path": "main.pietto",
                "line": 1,
                "column": 1,
                "end_line": 13 if stage == "def" else 12,
                "end_column": 11,
            },
            "suggestion": None,
        }
    ]
    code, out, err = run(argv(root, target, format="text"))
    assert (code, out, err) == (
        1,
        b"",
        "pietto.sql-emission.v1 BLOCKED\nmain.pietto:1:1 PIE-S2006 error: "
        "Semantic analysis recursion limit exceeded while processing source.\n",
    )


@pytest.mark.parametrize("target", TARGETS)
def test_c03_fixed_values_preserve_and_bind_safe(tmp_path: Path, target: str) -> None:
    documents = {}
    for variant, policy in (
        ("table_preserve", "preserve"),
        ("table_bind", "bind-safe"),
    ):
        root, item = project(tmp_path, target, "R_fixed_direct", variant, name=variant)
        expected = api_bytes(root.parent / f"{variant}-api", item)
        code, out, err = run(argv(root, target, literal_policy=policy))
        assert (code, out, err) == (0, expected, "")
        documents[policy] = probe.decode_public(out)
    preserve, bind = documents["preserve"], documents["bind-safe"]
    assert preserve["parameter_uses"] == [] and bind["parameter_uses"]
    values = [(v["tag"], v["value"]) for v in bind["fixed_values"]]
    assert ("Int", "9007199254740993") in values
    assert ("Bool", True) in values and ("Bool", False) in values
    # Equal values keep their own positional slots; nothing is deduplicated.
    assert values.count(("Int", "17")) == 2 and values.count(("Int", "2")) == 2
    # The authored sign is unary SQL structure, never folded into the value:
    # +0.0 and -0.0 both transport the positive-zero binary64 payload.
    assert values.count(("Float", (0.0).hex())) == 2
    assert ("Float", (-0.0).hex()) not in values
    assert ("Float", (1.5).hex()) in values and ("Float", (-1.5).hex()) not in values
    assert bind["sql"].count("(-") == 3 and bind["sql"].count("(+") == 2
    assert preserve["sql"].count("(-") == 3 and preserve["sql"].count("(+") == 2
    assert ("Text", "雪e\u0301😀") in values and ("Text", "? %s $1") in values
    assert all(type(value) is str for tag, value in values if tag != "Bool")
    sql = bind["sql"].encode("utf-8")
    for use in bind["parameter_uses"]:
        token = sql[use["range"]["start"] : use["range"]["end"]].decode("utf-8")
        assert token == (
            "$" + str(use["server_index"]) if target == "postgres" else "?"
        )
    if target == "mysql":
        assert [u["server_index"] for u in bind["parameter_uses"]] == list(
            range(1, len(bind["parameter_uses"]) + 1)
        )
    assert (
        "9007199254740993" in preserve["sql"] and "9007199254740993" not in bind["sql"]
    )
    # The large Int is exact in the decoded native arguments, never a float.
    assert 9007199254740993 in probe.decoded_arguments(bind)
    # Text presentation carries the same tagged records and the complete SQL.
    root, item = project(tmp_path, target, "R_fixed_direct", "table_bind", name="text")
    code, out, err = run(argv(root, target, literal_policy="bind-safe", format="text"))
    text = out.decode("utf-8")
    assert (code, err) == (0, "") and text.startswith(
        "pietto.sql-emission.v1 VERIFIED\n"
    )
    assert "\nsql:\n" + bind["sql"] + "\nend sql\n" in text
    assert f"fixed_values ({len(bind['fixed_values'])}):\n" in text
    assert f"parameter_uses ({len(bind['parameter_uses'])}):\n" in text
    for record in bind["fixed_values"]:
        assert (
            "  "
            + json.dumps(
                record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            + "\n"
            in text
        )
    assert "literal_policy: bind_safe_literals\n" in text
    assert (
        "contract: "
        + json.dumps(
            json.loads(item["contract"]),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        in text
    )
    assert f"columns ({len(bind['columns'])}):\n" in text
    assert f"requirements ({len(bind['requirements'])}):\n" in text
    assert f"ranges ({len(bind['ranges'])}):\n" in text
    assert text.endswith("diagnostics (0):\n")


# --- channels, privacy and files -------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="needs control characters in names")
def test_verified_text_escapes_controls_in_paths_and_canonical_records(
    tmp_path: Path,
) -> None:
    root, item = project(tmp_path, "postgres")
    # ESC, DEL, C1 CSI and RIGHT-TO-LEFT OVERRIDE in the module file name.
    module = "m\x1b[31m\x7f\u009b\u202e.pietto"
    (root / "main.pietto").rename(root / module)
    (root / "contract.json").write_text(
        item["contract"].replace('"main.pietto"', json.dumps(module))
    )
    arguments = argv(root, "postgres")
    arguments[arguments.index("main.pietto")] = module

    code, out, err = run(arguments + ["--format", "text"])
    text = out.decode("utf-8")
    assert (code, err) == (0, "")
    assert not any(control in text for control in "\x1b\x7f\u009b\u202e")
    lines = text.splitlines()
    assert "owner: m\\x1b[31m\\x7f\\u009b\\u202e.pietto table result" in lines
    # Every canonical record line still decodes to the JSON document's values.
    document = probe.decode_public(run(arguments)[1])
    request = document["request"]
    start = lines.index(f"sources ({len(request['sources'])}):") + 1
    sources = lines[start : start + len(request["sources"])]
    assert [json.loads(line) for line in sources] == request["sources"]
    contract = next(line for line in lines if line.startswith("contract: "))
    assert json.loads(contract.removeprefix("contract: ")) == request["contract"]
    assert [source["module"] for source in request["sources"]] == [module]
    assert "\\u001b[31m\\u007f\\u009b\\u202e.pietto" in sources[0]


@pytest.mark.parametrize("target", TARGETS)
def test_failure_messages_never_echo_roots_or_raw_input(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target, name=SENTINEL)
    (root / "contract.json").write_text('{"format": "' + SENTINEL + '"')
    code, out, err = run(argv(root, target))
    assert code == 2 and SENTINEL not in out.decode() and err == ""
    code, out, err = run(argv(root, target, format="text"))
    assert (code, out) == (2, b"") and SENTINEL not in err
    assert err.startswith(
        "pietto.sql-emission.v1 INPUT_REJECTED\nerror emission_contract_schema:"
    )
    code, out, err = run(argv(tmp_path / ("nope-" + SENTINEL), target))
    assert code == 2 and SENTINEL not in out.decode()
    # Control characters in a source diagnostic are escaped in text presentation.
    (root / "contract.json").write_text(item["contract"])
    (root / "main.pietto").write_text(
        (root / "main.pietto").read_text() + "table \x1b[31mbad:\n"
    )
    code, out, err = run(argv(root, target, format="text"))
    assert code == 1 and "\x1b" not in err and "\\x1b" in err
    # So are C1 controls (CSI here) and bidi controls (RIGHT-TO-LEFT OVERRIDE).
    source = (root / "main.pietto").read_text()
    for control in ("\u009b", "\u202e"):
        (root / "main.pietto").write_text(source.replace("\x1b[31m", control))
        code, out, err = run(argv(root, target, format="text"))
        assert code == 1 and control not in err
        assert f"Unexpected '\\u{ord(control):04x}'" in err


@pytest.mark.parametrize("target", TARGETS)
def test_output_file_is_the_exact_artifact_and_replacement_is_atomic(
    tmp_path: Path, target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, item = project(tmp_path, target)
    expected = api_bytes(tmp_path, item)
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    # Ordinary cwd-relative output interpretation, not project containment.
    code, out, err = run(argv(root, target, output="out/artifact.json"))
    assert code == 2 and kinds(out) == [("output_path", None)]
    (elsewhere / "out").mkdir()
    code, out, err = run(argv(root, target, output="out/artifact.json"))
    assert (code, out, err) == (0, expected, "")
    assert (elsewhere / "out" / "artifact.json").read_bytes() == expected
    assert (
        probe.decode_public((elsewhere / "out" / "artifact.json").read_bytes())[
            "status"
        ]
        == "VERIFIED"
    )
    assert sorted(p.name for p in (elsewhere / "out").iterdir()) == ["artifact.json"]
    # Existing destination is replaced; text stdout with the JSON file.
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"stale")
    code, out, err = run(argv(root, target, format="text", output=str(existing)))
    assert (code, err) == (0, "") and out.startswith(
        b"pietto.sql-emission.v1 VERIFIED\n"
    )
    assert existing.read_bytes() == expected
    assert not tuple(tmp_path.glob("*.tmp"))
    # Only VERIFIED publishes: a failure leaves an existing destination unchanged.
    existing.write_bytes(b"stale")
    arguments = argv(root, target, kind="query", output=str(existing))
    assert run(arguments)[0] == 2 and existing.read_bytes() == b"stale"
    absent = tmp_path / "absent.json"
    arguments = argv(root, target, kind="query", output=str(absent))
    assert run(arguments)[0] == 2 and not absent.exists()
    # Unsuitable destinations are rejected before compilation or mutation.
    (tmp_path / "dir.json").mkdir()
    os.symlink(existing, tmp_path / "link.json")
    for destination in (
        tmp_path / "dir.json",
        tmp_path / "link.json",
        tmp_path / "missing" / "x.json",
    ):
        code, out, err = run(argv(root, target, output=str(destination)))
        assert code == 2 and kinds(out) == [("output_path", None)]
    assert existing.read_bytes() == b"stale"


@pytest.mark.skipif(
    sys.platform == "win32", reason="needs POSIX directory permissions and names"
)
@pytest.mark.parametrize("presentation", ["json", "text"])
@pytest.mark.parametrize(
    "case", ["unsearchable-parent", "link-loop-parent", "name-too-long"]
)
def test_an_uninspectable_destination_is_an_output_write_error(
    tmp_path: Path, case: str, presentation: str
) -> None:
    root, _ = project(tmp_path, "postgres")
    locked = tmp_path / "locked"
    if case == "unsearchable-parent":
        if os.geteuid() == 0:
            pytest.skip("needs POSIX directory permissions that bind the user")
        locked.mkdir()
        locked.chmod(0)
        destination = locked / "artifact.json"
    elif case == "link-loop-parent":
        os.symlink(tmp_path / "loop-b", tmp_path / "loop-a")
        os.symlink(tmp_path / "loop-a", tmp_path / "loop-b")
        destination = tmp_path / "loop-a" / "artifact.json"
    else:
        longest = os.pathconf(tmp_path, "PC_NAME_MAX")
        destination = tmp_path / f"{'a' * (longest + 1 - len('.json'))}.json"
    arguments = argv(root, "postgres", output=str(destination))
    if presentation == "text":
        arguments += ["--format", "text"]
    try:
        code, out, err = run(arguments)
    finally:
        if locked.exists():
            locked.chmod(0o700)
    if presentation == "json":
        assert (code, err) == (2, "")
        assert [(e["kind"], e["message"]) for e in failure(out)["cli_errors"]] == [
            ("output_write", "Output file could not be written.")
        ]
    else:
        assert (code, out) == (2, b"")
        assert err.startswith(
            "pietto.sql-emission.v1 INPUT_REJECTED\n"
            "error output_write: Output file could not be written.\n"
        )
    assert not tuple(tmp_path.rglob("*.tmp"))


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows limits the whole path, not one name"
)
def test_output_file_accepts_the_longest_file_name_the_os_accepts(
    tmp_path: Path,
) -> None:
    root, item = project(tmp_path, "postgres")
    expected = api_bytes(tmp_path, item)
    longest = os.pathconf(tmp_path, "PC_NAME_MAX")
    output = tmp_path / f"{'a' * (longest - len('.json'))}.json"
    assert run(argv(root, "postgres", output=str(output))) == (0, expected, "")
    assert output.read_bytes() == expected
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX permission bits")
def test_output_file_mode_follows_the_umask_and_a_replaced_file_keeps_its_bits(
    tmp_path: Path,
) -> None:
    if sys.platform == "linux":
        # A default ACL a shared base directory passes on would override the
        # umask and mask the group bits of every new file.
        for name in ("system.posix_acl_default", "system.posix_acl_access"):
            try:
                os.removexattr(tmp_path, name)
            except OSError as error:
                if error.errno not in {errno.ENODATA, errno.ENOTSUP, errno.EOPNOTSUPP}:
                    raise
    root, item = project(tmp_path, "postgres")
    expected = api_bytes(tmp_path, item)
    # A new file gets 0o666 less the umask; a replaced file keeps its own bits,
    # neither narrowed by the umask nor widened to it (only its owner bits
    # elsewhere than on Linux).
    cases = ((0o022, None, 0o644), (0o077, None, 0o600))
    cases += ((0o077, 0o664, 0o664 if sys.platform == "linux" else 0o600),)
    cases += ((0o022, 0o600, 0o600),)
    for umask, existing, mode in cases:
        output = tmp_path / f"artifact-{umask:03o}-{existing}.json"
        if existing is not None:
            output.write_bytes(b"stale")
            output.chmod(existing)
        previous = os.umask(umask)
        try:
            result = run(argv(root, "postgres", output=str(output)))
        finally:
            os.umask(previous)
        assert result == (0, expected, "")
        assert output.read_bytes() == expected
        assert stat.S_IMODE(output.stat().st_mode) == mode, (umask, existing)
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX owners")
@pytest.mark.parametrize("presentation", ["json", "text"])
def test_another_users_destination_is_refused_as_an_output_write_error(
    tmp_path: Path, presentation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = project(tmp_path, "postgres")
    output = tmp_path / "artifact.json"
    output.write_bytes(b"stale")
    before = output.stat()
    # The command runs as a user who is neither the file's owner nor root.
    monkeypatch.setattr(os, "geteuid", lambda: before.st_uid + 1)
    arguments = argv(root, "postgres", output=str(output))
    if presentation == "text":
        arguments += ["--format", "text"]
    code, out, err = run(arguments)
    if presentation == "json":
        assert (code, err) == (2, "")
        assert out == (
            b'{"artifact":null,"blockers":[],"cli_errors":[{"kind":"output_write",'
            b'"message":"Output file belongs to another user.","path":null}],'
            b'"diagnostics":[],"format":"pietto.sql-emission.v1",'
            b'"status":"INPUT_REJECTED"}\n'
        )
    else:
        assert (code, out, err) == (
            2,
            b"",
            "pietto.sql-emission.v1 INPUT_REJECTED\n"
            "error output_write: Output file belongs to another user.\n",
        )
    assert output.read_bytes() == b"stale"
    after = output.stat()
    assert (after.st_mode, after.st_ino) == (before.st_mode, before.st_ino)
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("presentation", ["json", "text"])
def test_a_destination_whose_state_cannot_be_read_is_never_replaced(
    tmp_path: Path, presentation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = project(tmp_path, "postgres")
    output = tmp_path / "artifact.json"
    output.write_bytes(b"stale")
    before = output.stat()
    real_stat = os.stat

    def stat_failing_for_output(
        target: Any, *arguments: Any, **keywords: Any
    ) -> os.stat_result:
        # Only a missing entry shows a destination absent; this one is there.
        if str(target) == str(output):
            raise OSError(errno.EIO, "state could not be read")
        return real_stat(target, *arguments, **keywords)

    monkeypatch.setattr(os, "stat", stat_failing_for_output)
    arguments = argv(root, "postgres", output=str(output))
    if presentation == "text":
        arguments += ["--format", "text"]
    code, out, err = run(arguments)
    if presentation == "json":
        assert (code, err) == (2, "")
        assert out == (
            b'{"artifact":null,"blockers":[],"cli_errors":[{"kind":"output_write",'
            b'"message":"Output file could not be written.","path":null}],'
            b'"diagnostics":[],"format":"pietto.sql-emission.v1",'
            b'"status":"INPUT_REJECTED"}\n'
        )
    else:
        assert (code, out, err) == (
            2,
            b"",
            "pietto.sql-emission.v1 INPUT_REJECTED\n"
            "error output_write: Output file could not be written.\n",
        )
    assert output.read_bytes() == b"stale"
    after = real_stat(output)
    assert (after.st_mode, after.st_ino) == (before.st_mode, before.st_ino)
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("presentation", ["json", "text"])
def test_a_read_only_destination_is_refused_as_an_output_write_error(
    tmp_path: Path, presentation: str
) -> None:
    root, _ = project(tmp_path, "postgres")
    output = tmp_path / "artifact.json"
    output.write_bytes(b"stale")
    output.chmod(0o444)
    if os.access(output, os.W_OK):
        pytest.skip("this user may write a read-only file")
    before = output.stat()
    arguments = argv(root, "postgres", output=str(output))
    if presentation == "text":
        arguments += ["--format", "text"]
    code, out, err = run(arguments)
    if presentation == "json":
        assert (code, err) == (2, "")
        assert out == (
            b'{"artifact":null,"blockers":[],"cli_errors":[{"kind":"output_write",'
            b'"message":"Output file is read-only.","path":null}],"diagnostics":[],'
            b'"format":"pietto.sql-emission.v1","status":"INPUT_REJECTED"}\n'
        )
        assert failure(out)["status"] == "INPUT_REJECTED"
    else:
        assert (code, out, err) == (
            2,
            b"",
            "pietto.sql-emission.v1 INPUT_REJECTED\n"
            "error output_write: Output file is read-only.\n",
        )
    assert output.read_bytes() == b"stale"
    after = output.stat()
    assert (after.st_mode, after.st_ino) == (before.st_mode, before.st_ino)
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("target", TARGETS)
def test_protected_inputs_and_their_aliases_are_never_replaced(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target, "N_imported_chain", "bag")
    (root / "unrelated.pietto").write_text(
        "shape Extra:\n    id: Int\n", encoding="utf-8"
    )
    os.symlink(root, tmp_path / "alias")
    (tmp_path / "hard-main.pietto").hardlink_to(root / "main.pietto")
    (tmp_path / "hard-contract.json").hardlink_to(root / "contract.json")
    (tmp_path / "hard-config.toml").hardlink_to(root / "pietto.toml")
    protected = [
        root / "pietto.toml",
        root / "main.pietto",
        root / "a.pietto",
        root / "b.pietto",
        root / "unrelated.pietto",
        root / "contract.json",
        tmp_path / "hard-main.pietto",
        tmp_path / "hard-contract.json",
        tmp_path / "hard-config.toml",
        tmp_path / "alias" / "pietto.toml",
        tmp_path / "alias" / "a.pietto",
        tmp_path / "alias" / "contract.json",
        tmp_path / "project" / ".." / "project" / "b.pietto",
        Path(os.path.relpath(root / "main.pietto")),
    ]
    facts = {path: (path.read_bytes(), os.stat(path).st_ino) for path in protected}
    for destination in protected:
        code, out, err = run(argv(root, target, kind="query", output=str(destination)))
        assert (code, err) == (2, ""), destination
        assert kinds(out) == [("output_path", None)], destination
        assert (
            "differ from the project configuration"
            in failure(out)["cli_errors"][0]["message"]
        )
    assert {
        path: (path.read_bytes(), os.stat(path).st_ino) for path in protected
    } == facts
    # A different file with the same spelling elsewhere is not protected.
    other = tmp_path / "other"
    other.mkdir()
    code, out, err = run(
        argv(root, target, kind="query", output=str(other / "main.pietto"))
    )
    assert code == 0 and (other / "main.pietto").read_bytes() == out


def test_injected_file_faults_preserve_destinations_and_report_honestly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stubbed I/O faults: creation, write, replacement and cleanup failures."""
    root, item = project(tmp_path, "postgres")
    expected = api_bytes(tmp_path, item)
    existing = tmp_path / "existing.json"
    absent = tmp_path / "absent.json"

    def check(destination: Path, before: bytes | None, messages: list[str]) -> None:
        code, out, err = run(argv(root, "postgres", output=str(destination)))
        assert (code, err) == (2, "")
        document = failure(out)
        assert [e["kind"] for e in document["cli_errors"]] == ["output_write"] * len(
            messages
        )
        assert [e["message"] for e in document["cli_errors"]] == messages
        assert (
            destination.read_bytes() if before is not None else not destination.exists()
        ) == (before if before is not None else True)
        assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]

    real_open_replacement = emission_cli.open_replacement

    def failing_creation(output: Path) -> Any:
        raise OSError(errno.ENOSPC, SENTINEL)

    written = "Output file could not be written."
    cleanup = "Temporary output file could not be removed."
    existing.write_bytes(b"stale")
    monkeypatch.setattr(emission_cli, "open_replacement", failing_creation)
    check(existing, b"stale", [written])
    check(absent, None, [written])

    class FailingWrite:
        def __init__(self, handle: Any) -> None:
            self.handle = handle

        def __enter__(self) -> "FailingWrite":
            return self

        def __exit__(self, *exc: Any) -> None:
            self.handle.close()

        def write(self, data: bytes) -> int:
            raise OSError(errno.EIO, SENTINEL)

    def failing_write(output: Path) -> tuple[FailingWrite, Path]:
        handle, temporary = real_open_replacement(output)
        return FailingWrite(handle), temporary

    monkeypatch.setattr(emission_cli, "open_replacement", failing_write)
    check(existing, b"stale", [written])
    monkeypatch.setattr(emission_cli, "open_replacement", real_open_replacement)

    def failing_replace(source: Any, destination: Any) -> None:
        raise OSError(errno.EXDEV, SENTINEL)

    real_replace = os.replace
    monkeypatch.setattr(emission_cli.os, "replace", failing_replace)
    check(existing, b"stale", [written])
    check(absent, None, [written])
    real_unlink = Path.unlink

    def failing_unlink(self: Path, missing_ok: bool = False) -> None:
        raise OSError(errno.EPERM, SENTINEL)

    monkeypatch.setattr(Path, "unlink", failing_unlink)
    code, out, err = run(argv(root, "postgres", output=str(existing)))
    assert code == 2 and [e["message"] for e in failure(out)["cli_errors"]] == [
        written,
        cleanup,
    ]
    assert existing.read_bytes() == b"stale" and SENTINEL not in out.decode()
    monkeypatch.setattr(Path, "unlink", real_unlink)
    leftovers = tuple(tmp_path.glob("*.tmp"))
    assert len(leftovers) == 1  # the temporary file whose removal failed
    leftovers[0].unlink()
    monkeypatch.setattr(emission_cli.os, "replace", real_replace)
    assert run(argv(root, "postgres", output=str(existing))) == (0, expected, "")
    assert existing.read_bytes() == expected


def test_a_refused_temporary_file_open_leaves_nothing_to_remove(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stubbed fault: an audit hook refuses the open of the temporary file.

    Python audits an open before the file is created, so even a removal the
    file system would refuse has nothing left to remove or report.
    """
    root, _ = project(tmp_path, "postgres")
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"stale")

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError(errno.EACCES, SENTINEL)

    monkeypatch.setattr(output_file, "open", refuse, raising=False)
    monkeypatch.setattr(os, "unlink", refuse)
    monkeypatch.setattr(Path, "unlink", refuse)
    code, out, err = run(argv(root, "postgres", output=str(existing)))

    assert (code, err) == (2, "")
    assert [(e["kind"], e["message"]) for e in failure(out)["cli_errors"]] == [
        ("output_write", "Output file could not be written.")
    ]
    assert existing.read_bytes() == b"stale" and SENTINEL not in out.decode()
    assert not tuple(tmp_path.glob("*.tmp"))


def test_stdout_failure_is_not_success_and_never_rolls_back_a_replaced_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stubbed stream fault: the write/flush of the presentation fails."""
    root, item = project(tmp_path, "postgres")
    expected = api_bytes(tmp_path, item)
    destination = tmp_path / "artifact.json"

    class BrokenBuffer:
        def write(self, data: bytes) -> int:
            raise OSError(errno.EPIPE, "broken pipe")

    class BrokenStdout:
        buffer = BrokenBuffer()

        def write(self, text: str) -> int:
            raise OSError(errno.EPIPE, "broken pipe")

        def flush(self) -> None:
            return None

    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", BrokenStdout())
    with contextlib.redirect_stderr(err):
        code = cli.main(argv(root, "postgres", output=str(destination)))
    assert code == 2 and destination.read_bytes() == expected
    assert err.getvalue() == (
        "pietto emit-sql: error: standard output could not be written;"
        " the replaced artifact file is kept\n"
    )
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code = cli.main(argv(root, "postgres"))
    assert code == 2 and err.getvalue() == (
        "pietto emit-sql: error: standard output could not be written\n"
    )

    # A closed descriptor 1 leaves sys.stdout None, and a stream may fail only
    # in every flush: each is the same failure, reported exactly once.
    class FullStdout(io.StringIO):
        def flush(self) -> None:
            raise OSError(errno.ENOSPC, "no space")

    for stdout in (None, FullStdout()):
        monkeypatch.setattr(sys, "stdout", stdout)
        for arguments in (argv(root, "postgres"), argv(root, "postgres") + ["--help"]):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = cli.main(arguments)
            assert code == 2 and err.getvalue() == (
                "pietto emit-sql: error: standard output could not be written\n"
            )
    # A stream without a binary buffer still receives the exact UTF-8 text.
    plain = io.StringIO()
    monkeypatch.setattr(sys, "stdout", plain)
    assert cli.main(argv(root, "postgres")) == 0
    assert plain.getvalue().encode("utf-8") == expected


def test_invalid_runtime_outcome_cannot_publish_a_success_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Injected: a VERIFIED-labelled outcome without its artifact reaches the serializer."""
    root, _ = project(tmp_path, "postgres")
    destination = tmp_path / "artifact.json"
    monkeypatch.setattr(
        emission_cli,
        "realize_project_sql",
        lambda prepared: EmissionOutcome(
            "VERIFIED", prepared.verification.completed.diagnostics, None
        ),
    )
    code, out, err = run(argv(root, "postgres", output=str(destination)))
    document = failure(out)
    assert (code, err, document["status"]) == (1, "", "BLOCKED")
    assert [(b["code"], b["reason"]) for b in document["blockers"]] == [
        ("PIE-B1008", "ARTIFACT_INTEGRITY")
    ]
    assert not destination.exists()


@pytest.mark.parametrize("target", TARGETS)
def test_independent_decoder_refuses_corrupted_console_output(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target, "R_fixed_direct", "table_bind")
    code, out, err = run(argv(root, target, literal_policy="bind-safe"))
    document = json.loads(out)

    def corrupted(**changes: Any) -> bytes:
        value = json.loads(out)
        for key, change in changes.items():
            value[key] = change(value[key])
        return json.dumps(value, ensure_ascii=False).encode("utf-8")

    for data in (
        corrupted(sql=lambda s: s.replace("SELECT", "DELETE", 1)),
        corrupted(sql=lambda s: s + " "),
        corrupted(fixed_values=lambda v: []),
        corrupted(fixed_values=lambda v: v[:-1]),
        corrupted(parameter_uses=lambda v: v[1:]),
        corrupted(parameter_uses=lambda v: [{**v[0], "server_index": 99}, *v[1:]]),
        corrupted(ranges=lambda v: [{**v[0], "end": v[0]["end"] + 1}, *v[1:]]),
        corrupted(columns=lambda v: []),
        json.dumps({**json.loads(out), "extra": 1}).encode(),
        b'{"format": "pietto.sql-emission.v1", "status": "INPUT_REJECTED", "artifact": null, "blockers": [], "diagnostics": [], "cli_errors": [{"kind": "surprise", "message": "m", "path": null}]}',
    ):
        with pytest.raises(ValueError):
            probe.decode_public(data)
    assert probe.decode_public(out)["sql"] == document["sql"]


def test_real_subprocess_streams_and_exit_codes(tmp_path: Path) -> None:
    """A genuine child process from an unrelated working directory."""
    root, item = project(tmp_path, "postgres")
    expected = api_bytes(tmp_path, item)
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()
    command = [
        sys.executable,
        "-c",
        "from pietto.cli import main; raise SystemExit(main())",
    ]
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "PYTHONIOENCODING": "ascii",
    }
    result = subprocess.run(
        command + argv(root, "postgres", output="artifact.json"),
        cwd=elsewhere,
        env=env,
        capture_output=True,
        check=False,
    )
    assert (result.returncode, result.stderr) == (0, b"")
    assert (
        result.stdout == expected
        and (elsewhere / "artifact.json").read_bytes() == expected
    )
    result = subprocess.run(
        command + argv(root, "postgres", format="text"),
        cwd=elsewhere,
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0 and result.stderr == b""
    assert result.stdout.decode("utf-8").startswith("pietto.sql-emission.v1 VERIFIED\n")
    assert json.loads(expected)["sql"].encode("utf-8") in result.stdout
    result = subprocess.run(
        command + argv(root, "postgres", kind="query", format="text"),
        cwd=elsewhere,
        env=env,
        capture_output=True,
        check=False,
    )
    assert (result.returncode, result.stdout) == (2, b"")
    assert result.stderr.startswith(b"pietto.sql-emission.v1 INPUT_REJECTED\n")
    result = subprocess.run(
        command + argv(root, "postgres", kind="query"),
        cwd=elsewhere,
        env=env,
        capture_output=True,
        check=False,
    )
    assert (result.returncode, result.stderr) == (2, b"")
    assert kinds(result.stdout) == [("emission_selector", None)]


def test_readme_example_is_copyable_verified_and_shared_with_the_package_smoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The documented project, contract and commands run exactly as written."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Project SQL emission", 1)[1].split("\n## ", 1)[0]
    blocks = dict(
        (language, body)
        for language, body in re.findall(r"```(\w+)\n(.*?)```", section, re.S)
        if language != "bash"
    )
    commands = re.findall(r"```bash\n(.*?)```", section, re.S)
    assert set(blocks) == {"text", "toml", "pietto", "json"} and len(commands) == 2
    smoke = (REPO_ROOT / "scripts/package_smoke.py").read_text(encoding="utf-8")
    assert blocks["pietto"] in smoke and blocks["json"] in smoke
    root = tmp_path / "demo-emit"
    root.mkdir()
    (root / "pietto.toml").write_text(blocks["toml"], encoding="utf-8")
    (root / "main.pietto").write_text(blocks["pietto"], encoding="utf-8")
    (root / "contract.json").write_text(blocks["json"], encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    first, second = (
        shlex.split(command.replace("\\\n", " "))[1:] for command in commands
    )
    assert all(c[0] == "emit-sql" for c in (first, second))
    code, out, err = run(first)
    assert (code, err) == (0, "")
    document = probe.decode_public(out)
    assert document["status"] == "VERIFIED" and document["sql"].startswith("SELECT ")
    assert document["request"]["owner"] == {
        "module": "main.pietto",
        "kind": "table",
        "name": "active_items",
    }
    code, text, err = run(second)
    assert (code, err) == (0, "") and text.startswith(
        b"pietto.sql-emission.v1 VERIFIED\n"
    )
    assert (tmp_path / "active_items.sql-emission.json").read_bytes() == out


# --- precise refusal reasons, places and remedies --------------------------------

REASONS_SOURCE = """shape Item:
    id: Int
    label: Text
    qty: Int
    price: Float
    amount: Decimal(10, 2)
    item_key = unique(id)

source items: Item = postgres.table("fixture.items")

query aggregates:
    from items
    group by qty
    select:
        qty
        a = count(label)
        b = count_distinct(price)
        c = max(amount)
        d = min(price)

query float_group:
    from items
    group by price
    select:
        price
        n = count()

query renamed:
    from items
    select:
        item = label
    order by item

query arithmetic:
    from items
    select:
        d = qty + 1

query plain:
    from items
    select:
        id
"""


def _reasons_contract(**changes: Any) -> dict[str, Any]:
    int_range = {"kind": "int_range", "min": "0", "max": "100"}
    representations = {
        "id": {"storage": {"kind": "pg_int8"}, "domain": int_range},
        "label": {
            "storage": {"kind": "pg_text"},
            "domain": {
                "kind": "text",
                "max_characters": 64,
                "encoding": "UTF8",
                "collation": "C",
                "padding": "NO PAD",
            },
        },
        "qty": {"storage": {"kind": "pg_int8"}, "domain": int_range},
        "price": {
            "storage": {"kind": "pg_float8"},
            "domain": {"kind": "finite_float", "format": "binary64"},
        },
        "amount": {
            "storage": {"kind": "pg_numeric", "precision": 10, "scale": 2},
            "domain": {"kind": "decimal", "precision": 10, "scale": 2},
        },
    }
    contract: dict[str, Any] = {
        "format": "pietto.emission-contract.v1",
        "target": {"family": "postgres", "release": "18.6"},
        "sources": [
            {
                "selector": {
                    "module": "main.pietto",
                    "kind": "source",
                    "name": "items",
                },
                "relation": {"namespace": "fixture", "name": "items"},
                "scan": "relation_rows",
                "fields": [
                    {
                        "ordinal": ordinal,
                        "name": name,
                        "column": name,
                        "representation": {**value, "nullable": False},
                    }
                    for ordinal, (name, value) in enumerate(representations.items())
                ],
                "premises": [
                    {"key": "row_domain_matches", "scope": "source", "value": True},
                    {"key": "read_only_object", "scope": "source", "value": True},
                ],
            }
        ],
        "environment": [
            {"key": "client_encoding", "scope": "statement", "value": "UTF8"},
            {
                "key": "operator_environment",
                "scope": "statement",
                "value": "builtin_only",
            },
            {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"},
        ],
    }
    contract.update(changes)
    return contract


def _reasons_project(tmp_path: Path, contract: dict[str, Any]) -> Path:
    root = tmp_path / "reasons"
    root.mkdir(exist_ok=True)
    (root / "pietto.toml").write_text(probe.CONFIG)
    (root / "main.pietto").write_text(REASONS_SOURCE, encoding="utf-8")
    (root / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return root


def _reasons(tmp_path: Path, name: str, contract: dict[str, Any]) -> tuple[int, str]:
    arguments = argv(_reasons_project(tmp_path, contract), "postgres", kind="query")
    arguments[8] = name
    code, out, err = run([*arguments, "--format", "text"])
    assert out == b""
    return code, err


def test_blockers_name_their_own_reason_place_and_remedy(tmp_path: Path) -> None:
    contract = _reasons_contract()
    # Every refused aggregate at its own item, in select order, with the
    # reviewed-domain reason; only sum and avg have a proof to supply.
    assert _reasons(tmp_path, "aggregates", contract) == (
        1,
        "pietto.sql-emission.v1 BLOCKED\n"
        "blocker PIE-B1003 UNSUPPORTED_RULE:"
        " count_argument_outside_reviewed_int_domain (main.pietto:16:9)\n"
        "blocker PIE-B1003 UNSUPPORTED_RULE:"
        " count_distinct_argument_outside_reviewed_int_domain (main.pietto:17:9)\n"
        "blocker PIE-B1003 UNSUPPORTED_RULE:"
        " max_argument_outside_reviewed_int_domain (main.pietto:18:9)\n"
        "blocker PIE-B1003 UNSUPPORTED_RULE:"
        " min_argument_outside_reviewed_int_domain (main.pietto:19:9)\n",
    )
    # A refused group key is at its GROUP BY item.
    assert _reasons(tmp_path, "float_group", contract) == (
        1,
        "pietto.sql-emission.v1 BLOCKED\n"
        "blocker PIE-B1003 UNSUPPORTED_RULE:"
        " group_key_type_outside_reviewed_comparison_domain (main.pietto:23:14)\n",
    )
    # A plan-stage refusal is at its clause, not the whole declaration.
    assert _reasons(tmp_path, "renamed", contract) == (
        1,
        "pietto.sql-emission.v1 BLOCKED\n"
        "blocker PIE-B1003 UNSUPPORTED_RULE: order (main.pietto:32:5)\n"
        "  hint: without GROUP BY, a key must be an input field, a restated"
        " selected expression or a selected let name, of a type that orders\n",
    )
    assert _reasons(tmp_path, "arithmetic", contract) == (
        1,
        "pietto.sql-emission.v1 BLOCKED\n"
        "blocker PIE-B1002 REPRESENTATION: arithmetic_outside_physical_range"
        " (main.pietto:37:9)\n"
        "  hint: an Int field ranges over its whole storage type; its declared"
        " int_range does not narrow that, so the result must fit the storage"
        " type\n",
    )
    # The field's storage, not the family's widest, bounds the result: the
    # hint names none.
    assert emission_cli._blocker_hint(
        "arithmetic_outside_physical_range", "mysql"
    ) == emission_cli._blocker_hint("arithmetic_outside_physical_range", "postgres")
    # Premise and target refusals name the reviewed value to write.
    assert _reasons(
        tmp_path,
        "plain",
        _reasons_contract(
            target={"family": "postgres", "release": "17.0"}, environment=[]
        ),
    ) == (
        1,
        "pietto.sql-emission.v1 BLOCKED\n"
        "blocker PIE-B1003 UNSUPPORTED_RULE: target_release_not_reviewed\n"
        '  hint: the reviewed postgres release is "18.6"\n'
        "blocker PIE-B1004 MISSING_EVIDENCE: client_encoding_declaration_missing\n"
        '  hint: add {"key":"client_encoding","scope":"statement","value":"UTF8"}'
        ' to "environment"\n',
    )
    # A source mapping that leaves a field out is at the source declaration,
    # related to the missing shape field.
    dropped = _reasons_contract()
    del dropped["sources"][0]["fields"][4]
    code, err = _reasons(tmp_path, "plain", dropped)
    assert (code, err) == (
        1,
        "pietto.sql-emission.v1 BLOCKED\n"
        "blocker PIE-B1001 SOURCE_REALIZATION:"
        " complete_ordered_source_schema_required (main.pietto:9:1)\n"
        "  related: main.pietto:6:5\n"
        '  hint: map every field of the source\'s shape once in "fields", in shape'
        " order; related lists the fields left out or out of order\n",
    )
    arguments = argv(tmp_path / "reasons", "postgres", kind="query")
    arguments[8] = "plain"
    blocker = failure(run(arguments)[1])["blockers"][0]
    assert (blocker["location"], blocker["related"]) == (
        {
            "path": "main.pietto",
            "line": 9,
            "column": 1,
            "end_line": 9,
            "end_column": 53,
        },
        [
            {
                "path": "main.pietto",
                "line": 6,
                "column": 5,
                "end_line": 6,
                "end_column": 27,
            }
        ],
    )
    # A JOIN that reads the left-out field is refused at the same source.
    (tmp_path / "reasons" / "main.pietto").write_text(
        REASONS_SOURCE + "\nquery joined:\n    from items\n    let other = items\n"
        "    inner join other on items.id == other.id\n    select:\n"
        "        a = items.id\n",
        encoding="utf-8",
    )
    arguments[8] = "joined"
    assert [
        (blocker["subject"]["detail"], blocker["location"]["line"])
        for blocker in failure(run(arguments)[1])["blockers"]
    ] == [
        ("join_input_source_field_not_bound", 9),
        ("complete_ordered_source_schema_required", 9),
    ]


def test_selection_and_contract_errors_name_their_fault(tmp_path: Path) -> None:
    root = _reasons_project(tmp_path, _reasons_contract())

    def message(*replacements: tuple[int, str], contract: str = "contract.json") -> str:
        arguments = argv(root, "postgres", kind="query", emission_contract=contract)
        arguments[8] = "plain"
        for position, value in replacements:
            arguments[position] = value
        code, out, err = run(arguments)
        document = failure(out)
        assert (code, err, len(document["cli_errors"])) == (2, "", 1)
        error = document["cli_errors"][0]
        return f"{error['kind']} {error['path']}: {error['message']}"

    assert message((4, "models\\main.pietto")) == (
        "emission_selector None: No project module matches --module; project"
        " modules: main.pietto. --module uses / as the separator."
    )
    assert message((6, "table")) == (
        "emission_selector None: main.pietto declares no table named by --name;"
        " its tables: none."
    )
    assert message((8, "absent")) == (
        "emission_selector None: main.pietto declares no query named by --name;"
        " its queries: aggregates, arithmetic, float_group, plain, renamed."
    )

    def contract_message(data: bytes) -> str:
        (root / "variant.json").write_bytes(data)
        return message(contract="variant.json")

    contract = _reasons_contract()
    assert contract_message(b"\xef\xbb\xbf" + json.dumps(contract).encode()) == (
        "emission_contract_schema None: Emission contract starts with a UTF-8"
        " byte-order mark; save it as UTF-8 without BOM."
    )
    # The reason is the json module's; this one reads the same on 3.12 and 3.13.
    assert contract_message(b'{"format": 1') == (
        "emission_contract_schema None: Invalid JSON emission input: Expecting"
        " ',' delimiter (line 1, column 13)."
    )
    # Valid UTF-8 JSON whose number overflows, or whose integer is longer
    # than Python reads, names that fault.
    assert contract_message(b'{"format": 1e400}') == (
        "emission_contract_schema None: Emission contract numbers must be finite."
    )
    assert contract_message(b'{"format": ' + b"1" * 5000 + b"}") == (
        "emission_contract_schema None: Invalid JSON emission input: Exceeds the"
        " limit (4300 digits) for integer string conversion: value has 5000"
        " digits."
    )
    # Valid UTF-8 whose escape stands for an unpaired surrogate.
    assert contract_message(b'{"format": "\\ud800"}') == (
        "emission_contract_schema None: Emission contract strings must not hold"
        " a lone surrogate escape (\\uD800-\\uDFFF)."
    )
    assert contract_message(b'{"format": "\xff"}') == (
        "emission_contract_schema None: Emission contract must be valid UTF-8."
    )
    assert contract_message(json.dumps({**contract, "note": 1}).encode()) == (
        "emission_contract_schema None: Invalid emission contract object: 1"
        " unexpected key; expected exactly the keys: format, target, sources,"
        " environment."
    )
    source = contract["sources"][0]
    missing = {
        **contract,
        "sources": [{k: v for k, v in source.items() if k != "scan"}],
    }
    assert contract_message(json.dumps(missing).encode()) == (
        "emission_contract_schema sources/0/scan: Invalid emission contract"
        " object: missing key scan; expected exactly the keys: selector, relation,"
        " scan, fields, premises."
    )
    renamed = json.loads(json.dumps(contract))
    renamed["sources"][0]["fields"][0]["name"] = "ident"
    assert contract_message(json.dumps(renamed).encode()) == (
        "emission_selector sources/0/fields/0/name: Field ordinal 0 must be named id."
    )
    elsewhere = json.loads(json.dumps(contract))
    elsewhere["sources"][0]["selector"]["name"] = "ghost"
    assert contract_message(json.dumps(elsewhere).encode()) == (
        "emission_selector sources/0/selector: main.pietto declares no source of"
        " the selector's name; its sources: items."
    )
    # An empty selector key or another kind names that key and what it takes.
    for key, value, expected in (
        (
            "module",
            "",
            "Source selector module must be a non-empty string; modules with"
            " sources: main.pietto.",
        ),
        ("name", "", "Source selector name must be a non-empty string."),
        ("kind", "table", 'Source selector kind must be "source".'),
    ):
        broken = json.loads(json.dumps(contract))
        broken["sources"][0]["selector"][key] = value
        assert contract_message(json.dumps(broken).encode()) == (
            f"emission_selector sources/0/selector/{key}: {expected}"
        )


def test_wrong_schema_and_empty_root_name_the_next_step(tmp_path: Path) -> None:
    root = _reasons_project(tmp_path, _reasons_contract())
    (root / "pietto.toml").write_text(
        'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n'
    )
    code, out, err = run(argv(root, "postgres", kind="query"))
    assert (code, err) == (2, "") and failure(out)["cli_errors"] == [
        {
            "kind": "config_schema",
            "message": "emit-sql --project needs schema_version = 2 (explicit"
            " modules); this project uses schema_version 1. Set schema_version = 2"
            " and declare the names a file uses from another file with import and"
            " export.",
            "path": "pietto.toml",
        }
    ]
    # An integer too long for tomllib is a configuration error, not a root
    # that could not be pinned.
    (root / "pietto.toml").write_text(f"schema_version = 2\nx = {'9' * 5000}\n")
    code, out, err = run(argv(root, "postgres", kind="query"))
    assert (code, err) == (2, "") and failure(out)["cli_errors"] == [
        {
            "kind": "config_parse",
            "message": "Project configuration TOML is invalid: Exceeds the limit"
            " (4300 digits) for integer string conversion: value has 5000 digits.",
            "path": "pietto.toml",
        }
    ]
    for project_argument in ("--project=", "--project"):
        arguments = argv("", "postgres", kind="query")
        if project_argument == "--project=":
            arguments[1:3] = ["--project="]
        code, out, err = run(arguments)
        assert (code, err) == (2, "") and failure(out)["cli_errors"] == [
            {
                "kind": "usage",
                "message": "argument --project: Project root must be a non-empty path.",
                "path": None,
            }
        ]
