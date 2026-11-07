"""Public project SQL compile entry: compile_sql / compile_all_sql.

Each document is compared with the stdout bytes and exit code of
``pietto emit-sql --project ... --format json`` run through ``cli.main`` with
independently spelled argv (and once in a real child process) by the same
interpreter. Faults injected with monkeypatch are labelled as stubs.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import _pietto_sql_emission as probe
from pietto import cli, execution
from pietto._project import project_public_execution
from pietto._project import project_sql_emission_cli as emission_cli
from pietto.compiler import SqlEmission, compile_all_sql, compile_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("postgres", "mysql")
POLICIES = {"preserve_literals": "preserve", "bind_safe_literals": "bind-safe"}
EXITS = {"VERIFIED": 0, "BLOCKED": 1, "INPUT_REJECTED": 2}


def run(argv: list[str]) -> tuple[int, bytes, str]:
    out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", newline="")
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(["emit-sql", *argv])
    out.flush()
    return code, out.buffer.getvalue(), err.getvalue()


def project(
    tmp_path: Path,
    target: str,
    case: str = "G_emission_table_bag",
    variant: str = "bag",
    extra: str = "",
) -> tuple[Path, str]:
    item = probe.fixture(target, case, variant)
    root = tmp_path / f"{target}-{case}-{variant}"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG)
    for file, content in probe.source_files(item["source"]).items():
        (root / file).write_text(content + extra, encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    return root, POLICIES[item["policy"]]


def single(target: str, **change: str) -> dict[str, str]:
    arguments = {
        "module": "main.pietto",
        "kind": "table",
        "name": "result",
        "dialect": target,
        "emission_contract": "contract.json",
    }
    return {**arguments, **change}


def space_argv(root: Path | str, values: dict[str, str], *, batch: bool) -> list[str]:
    argv = ["--project", str(root), *(["--all"] if batch else [])]
    for key, value in values.items():
        argv += ["--" + key.replace("_", "-"), value]
    return [*argv, "--format", "json"]


def same(emission: SqlEmission, argv: list[str]) -> dict[str, Any]:
    """The emission is the command's stdout, status and exit code."""
    code, out, err = run(argv)
    assert (emission.document, err) == (out, "")
    assert type(emission.document) is bytes and emission.document.endswith(b"\n")
    document = json.loads(emission.document)
    assert emission.status == document["status"] and code == EXITS[emission.status]
    return document


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "case,variant,kind,status,form",
    (
        ("G_emission_table_bag", "bag", "table", "VERIFIED", "v1"),
        ("Q_query_parameters", "preserve", "query", "VERIFIED", "v2"),
        ("L_emission_blocked", "bool_domain", "query", "BLOCKED", "v1"),
        ("K_emission_rejected", "duplicate_selector", "query", "INPUT_REJECTED", "v1"),
    ),
)
def test_single_emission_is_the_command_document(
    tmp_path: Path, target, case, variant, kind, status, form
) -> None:
    root, policy = project(tmp_path, target, case, variant)
    values = single(target, kind=kind, literal_policy=policy)
    emission = compile_sql(root, **values)
    document = same(emission, space_argv(root, values, batch=False))
    assert (emission.status, document["format"]) == (
        status,
        f"pietto.sql-emission.{form}",
    )
    # The guide reads the statement as the document's top-level "sql".
    assert ("sql" in document) == (status == "VERIFIED")


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", ("preserve", "bind-safe"))
def test_both_literal_policies_and_a_path_object_root(
    tmp_path: Path, target: str, policy: str
) -> None:
    root, _ = project(tmp_path, target)
    values = single(target, literal_policy=policy)
    emission = compile_sql(Path(root), **values)
    assert same(emission, space_argv(root, values, batch=False))["status"] == "VERIFIED"
    if policy == "preserve":
        default = single(target)
        assert compile_sql(str(root), **default) == emission
        assert same(emission, space_argv(root, default, batch=False))


@pytest.mark.parametrize(
    "change,kind",
    (
        ({"emission_contract": "missing.json"}, None),
        ({"dialect": "oracle"}, "usage"),
        ({"kind": "view"}, "usage"),
        ({"literal_policy": "bind_safe"}, "usage"),
        ({"dialect": "oracle", "kind": "view"}, "usage"),
        ({"name": "missing"}, "emission_selector"),
        ({"module": "other.pietto"}, "emission_selector"),
        ({"kind": "query"}, "emission_selector"),
        ({"project": ""}, "usage"),
        ({"project": "absent"}, None),
    ),
)
def test_rejected_values_are_returned_documents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change, kind
) -> None:
    root, _ = project(tmp_path, "postgres")
    monkeypatch.chdir(tmp_path)
    change = dict(change)
    target = change.pop("project", root)
    values = single("postgres", **change)
    emission = compile_sql(target, **values)
    document = same(emission, space_argv(target, values, batch=False))
    assert emission.status == "INPUT_REJECTED" and document["cli_errors"]
    if kind is not None:
        assert document["cli_errors"][0]["kind"] == kind


@pytest.mark.parametrize("value", ("--all", "-h", "--help", "--", "-", "--name=x", ""))
def test_option_like_values_stay_values(tmp_path: Path, value: str) -> None:
    root, _ = project(tmp_path, "postgres")
    emission = compile_sql(root, **single("postgres", name=value))
    code, out, err = run(
        [f"--project={root}", "--module=main.pietto", "--kind=table"]
        + [f"--name={value}", "--dialect=postgres"]
        + ["--emission-contract=contract.json", "--literal-policy=preserve"]
        + ["--format=json"]
    )
    assert (emission.document, code, err) == (out, 2, "")
    document = json.loads(out)
    assert document["format"] == "pietto.sql-emission.v1"
    assert document["cli_errors"][0]["kind"] == "emission_selector"
    batch = compile_all_sql(
        root, dialect="postgres", emission_contract="contract.json", name=value
    )
    assert json.loads(batch.document)["format"] == "pietto.sql-emission.batch.v1"
    assert batch.status == "INPUT_REJECTED"


class _Disguised(str):
    """A str subclass whose formatting and str() spell another value."""

    def __format__(self, spec: str) -> str:
        return "result"

    def __str__(self) -> str:
        return "result"


def test_a_str_subclass_is_passed_as_its_string_value(tmp_path: Path) -> None:
    root, _ = project(tmp_path, "postgres")
    values = single("postgres", name=_Disguised("nope"))
    emission = compile_sql(_Disguised(str(root)), **values)
    expected = space_argv(root, single("postgres", name="nope"), batch=False)
    assert same(emission, expected)["cli_errors"][0]["kind"] == "emission_selector"


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "selectors",
    ({}, {"kind": "query"}, {"module": "main.pietto", "name": "result"}),
)
def test_batch_is_the_command_batch_in_authority_order(
    tmp_path: Path, target: str, selectors: dict[str, str]
) -> None:
    root, _ = project(
        tmp_path,
        target,
        extra="\nquery selected:\n    from rows\n    select:\n        selected_id = id\n",
    )
    values = {**selectors, "dialect": target, "emission_contract": "contract.json"}
    emission = compile_all_sql(root, **values)
    document = same(emission, space_argv(root, values, batch=True))
    owners = [item["owner"] for item in document["items"]]
    expected = [("table", "result"), ("query", "selected")]
    assert owners == [
        {"module": "main.pietto", "kind": kind, "name": name}
        for kind, name in expected
        if all(selectors.get(k, v) == v for k, v in (("kind", kind), ("name", name)))
    ]
    assert emission.status == "VERIFIED"


def test_batch_keeps_every_outcome_and_rejects_an_empty_match(tmp_path: Path) -> None:
    root, _ = project(
        tmp_path,
        "postgres",
        extra="\nquery blocked:\n    from result\n    select:\n        record_id\n",
    )
    values = {"dialect": "postgres", "emission_contract": "contract.json"}
    emission = compile_all_sql(root, **values)
    document = same(emission, space_argv(root, values, batch=True))
    assert emission.status == "BLOCKED"
    assert [item["document"]["status"] for item in document["items"]] == [
        "VERIFIED",
        "BLOCKED",
    ]
    values["name"] = "missing"
    emission = compile_all_sql(root, **values)
    document = same(emission, space_argv(root, values, batch=True))
    assert emission.status == "INPUT_REJECTED" and document["items"] == []
    assert document["failure"]["cli_errors"][0]["kind"] == "emission_selector"
    values = {"dialect": "oracle", "emission_contract": "contract.json"}
    emission = compile_all_sql(root, **values)
    document = same(emission, space_argv(root, values, batch=True))
    assert document["failure"]["cli_errors"][0]["kind"] == "usage"


def test_batch_output_limit_is_a_returned_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = project(tmp_path, "postgres")
    values = {"dialect": "postgres", "emission_contract": "contract.json"}
    baseline = compile_all_sql(root, **values)
    monkeypatch.setattr(emission_cli, "MAX_BATCH_BYTES", len(baseline.document) - 1)
    emission = compile_all_sql(root, **values)
    document = same(emission, space_argv(root, values, batch=True))
    assert emission.status == "INPUT_REJECTED" and document["items"] == []
    assert document["failure"]["cli_errors"][0]["kind"] == "batch_output_limit"


class _BytesPath:
    def __fspath__(self) -> bytes:
        return b"root"


@pytest.mark.parametrize(
    "call,change",
    (
        (compile_sql, {"project": b"root"}),
        (compile_sql, {"project": _BytesPath()}),
        (compile_sql, {"project": None}),
        (compile_sql, {"module": None}),
        (compile_sql, {"kind": b"table"}),
        (compile_sql, {"name": 7}),
        (compile_sql, {"emission_contract": Path("contract.json")}),
        (compile_sql, {"literal_policy": None}),
        (compile_all_sql, {"dialect": None}),
        (compile_all_sql, {"name": 7}),
        (compile_all_sql, {"module": Path("main.pietto")}),
    ),
)
def test_wrong_python_types_raise_before_the_project_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, call, change
) -> None:
    root, _ = project(tmp_path, "postgres")

    def forbidden(arguments):
        raise AssertionError("a type error reads nothing")

    monkeypatch.setattr("pietto.compiler.run_project_emit_sql", forbidden)
    values: dict[str, Any] = {
        "project": root,
        "dialect": "postgres",
        "emission_contract": "contract.json",
    }
    if call is compile_sql:
        values.update(module="main.pietto", kind="table", name="result")
    values.update(change)
    with pytest.raises(TypeError):
        call(values.pop("project"), **values)
    with pytest.raises(TypeError):
        compile_sql(root, dialect="postgres", emission_contract="contract.json")  # type: ignore[call-arg]


def test_internal_errors_propagate_and_unencodable_output_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stubs: the realization stage raises UnicodeEncodeError with no unnamed
    path, for which the command prints no document; the parse raises an
    unexpected error, which is never disguised as a status."""
    root, _ = project(tmp_path, "postgres")
    values = single("postgres")

    def unencodable(prepared):
        raise UnicodeEncodeError("utf-8", "\udcff", 0, 1, "surrogates not allowed")

    monkeypatch.setattr(emission_cli, "realize_project_sql", unencodable)
    with pytest.raises(UnicodeEncodeError):
        compile_sql(root, **values)
    assert run(space_argv(root, values, batch=False)) == (
        2,
        b"",
        "pietto: error: terminal output could not be encoded\n",
    )

    def broken(path):
        raise RuntimeError("internal")

    monkeypatch.setattr(emission_cli, "check_project_parse_only", broken)
    with pytest.raises(RuntimeError, match="internal"):
        compile_sql(root, **values)


def test_a_verified_emission_needs_no_execution_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stub: template preparation overflows, so compile_query refuses with
    PIE-R1004, while compile_sql still returns the VERIFIED command bytes."""
    root, _ = project(tmp_path, "postgres")
    values = single("postgres")

    def overflow(outcome):
        raise RecursionError

    monkeypatch.setattr(project_public_execution, "live_template", overflow)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.compile_query(root, **values)
    assert refused.value.code == "PIE-R1004"
    emission = compile_sql(root, **values)
    assert same(emission, space_argv(root, values, batch=False))
    assert emission.status == "VERIFIED"


def test_calls_are_independent_and_write_nothing(tmp_path: Path) -> None:
    root, _ = project(tmp_path, "postgres")
    values = single("postgres")

    def snapshot() -> dict[Path, bytes]:
        return {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    before = snapshot()
    first = compile_sql(root, **values)
    main = root / "main.pietto"
    source = main.read_text(encoding="utf-8")
    main.write_text(source.replace("record_id = id", "record_id = missing"))
    broken = compile_sql(root, **values)
    assert broken.status != "VERIFIED"
    main.write_text(source, encoding="utf-8")
    assert compile_sql(root, **values) == first
    assert compile_all_sql(root, dialect="postgres", emission_contract="contract.json")
    assert snapshot() == before


def test_a_real_child_process_prints_the_same_bytes(tmp_path: Path) -> None:
    root, _ = project(tmp_path, "mysql")
    values = single("mysql")
    emission = compile_sql(root, **values)
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pietto.cli import main; raise SystemExit(main())",
            "emit-sql",
            *space_argv(root, values, batch=False),
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        check=False,
    )
    assert (child.returncode, child.stdout, child.stderr) == (
        0,
        emission.document,
        b"",
    )
