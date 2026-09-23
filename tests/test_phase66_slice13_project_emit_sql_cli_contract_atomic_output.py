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
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto import cli
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


# --- contract read boundary ------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_contract_read_is_contained_bounded_and_closes_descriptors(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target)
    expected = api_bytes(tmp_path, item)
    outside = tmp_path / "outside.json"
    outside.write_text(item["contract"])
    (root / "sub").mkdir()
    (root / "sub" / "contract.json").write_text(item["contract"])
    os.symlink(outside, root / "link.json")
    os.symlink(root / "sub", root / "linkdir")
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
        ("fifo.json", "fifo.json"),
        ("dir.json", "dir.json"),
        ("absent.json", "absent.json"),
        ("sub", "sub"),
    ):
        code, out, err = run(argv(root, target, emission_contract=contract))
        assert (code, err) == (2, ""), contract
        assert kinds(out) == [(read, path)], contract
        assert str(root) not in out.decode() and str(outside) not in out.decode()
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
        ("L_emission_blocked", "timestamp_meaning", "query", 1),
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
        assert document["status"] == probe.expected_status(case, variant, target)
        if document["status"] == "VERIFIED":
            assert (
                document["columns"] and document["requirements"] and document["ranges"]
            )
    # MySQL keeps FULL as a typed non-support while PostgreSQL admits it.
    root, item = project(tmp_path, target, "V_join_full", "restricted", name="full")
    code, out, err = run(argv(root, target, kind="query"))
    assert out == api_bytes(root.parent / "full-api", item)
    assert code == (0 if target == "postgres" else 1)
    # A whole-project parse or semantic ERROR blocks emission with every
    # diagnostic in order and no cli_errors.
    for name, body, prefix in (
        ("parse", "table result:\n    from rows\n    select\n        id\n", "PIE-P"),
        (
            "semantic",
            "table result:\n    from rows\n    select:\n        missing\n",
            "PIE-S",
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
        assert probe.decode_public(out)["blockers"] == []
        code, out, err = run(argv(root, target, format="text"))
        assert (code, out) == (1, b"")
        assert err.startswith("pietto.sql-emission.v1 BLOCKED\n") and prefix in err


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
    assert (
        sorted(p.name for p in tmp_path.iterdir() if p.name.startswith(".existing"))
        == []
    )
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


@pytest.mark.parametrize("target", TARGETS)
def test_protected_inputs_and_their_aliases_are_never_replaced(
    tmp_path: Path, target: str
) -> None:
    root, item = project(tmp_path, target, "N_imported_chain", "bag")
    (root / "unrelated.pietto").write_text(
        "shape Extra:\n    id: Int not null\n", encoding="utf-8"
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

    real_temporary = emission_cli.tempfile.NamedTemporaryFile

    def failing_temporary(*args: Any, **kwargs: Any) -> Any:
        raise OSError(errno.ENOSPC, SENTINEL)

    written = "Output file could not be written."
    cleanup = "Temporary output file could not be removed."
    existing.write_bytes(b"stale")
    monkeypatch.setattr(emission_cli.tempfile, "NamedTemporaryFile", failing_temporary)
    check(existing, b"stale", [written])
    check(absent, None, [written])

    class FailingWrite:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.handle = real_temporary(*args, **kwargs)
            self.name = self.handle.name

        def __enter__(self) -> "FailingWrite":
            self.handle.__enter__()
            return self

        def __exit__(self, *exc: Any) -> None:
            self.handle.__exit__(*exc)

        def write(self, data: bytes) -> int:
            raise OSError(errno.EIO, SENTINEL)

    monkeypatch.setattr(emission_cli.tempfile, "NamedTemporaryFile", FailingWrite)
    check(existing, b"stale", [written])
    monkeypatch.setattr(emission_cli.tempfile, "NamedTemporaryFile", real_temporary)

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
    for leftover in tmp_path.glob(".existing.json.*.tmp"):
        leftover.unlink()
    monkeypatch.setattr(emission_cli.os, "replace", real_replace)
    assert run(argv(root, "postgres", output=str(existing))) == (0, expected, "")
    assert existing.read_bytes() == expected


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
        shlex.split(command.replace("\\\n", " "))[3:] for command in commands
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
