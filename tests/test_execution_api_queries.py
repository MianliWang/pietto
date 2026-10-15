"""Query bundles, explicit values and repeated calls of the public execution
alpha, without a database.

export_bundle and load_bundle under the caller's own trust records, exact
value binding to a bind-safe query's slots, repeated calls that share only the
immutable template, and invalidation by a code change, through the real
public layer and private owners. The real-database and installed-consumer
witnesses are tests/_pietto_execution_api_probe.py.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import traceback
from types import SimpleNamespace
from typing import Any

import pytest

import _pietto_execution_api as api
import pietto.execution as execution
from pietto._project import project_arrow_result
from pietto._project import project_compiled_loading as loading
from pietto._project import project_execution as ex
from pietto._project import project_execution_postgres as pg
from pietto._project import project_public_execution as composition
from pietto._project.project_compiled_build import build_compiled
from pietto._project.project_compiled_verification import (
    verify_description,
    verify_export,
)
from pietto._project.project_compiled_schema import (
    FIELDS,
    VERSIONS,
    Address,
    CompiledError,
    Record,
    content_pin,
    decode,
    encode,
)
from pietto._project.project_execution_template import (
    bind_values,
    compatible_compiled_values,
)
from pietto._project.project_sql_emission_cli import POLICIES, emit_project
from pietto.execution import _errors as errors

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "pw-8c41d2-never-shown"
MARKER = "secret-7c1e"
PREMISE = execution.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
RECORD = re.compile("[0-9a-f]{64}")
NAMES = ("expected_pin", "accepted_producer", "accepted_compatibility")
CHANGED = "0" * 64  # the identity a patched code change reports


def compiled(project, policy="bind-safe", kind="table"):
    return execution.compile_query(
        project,
        module="main.pietto",
        kind=kind,
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy=policy,
    )


def variant(directory, where, extra="", kind="table"):
    """The documented project with another condition, an appended clause or
    the other declaration kind."""
    project = api.write_example(directory)
    path = project / "main.pietto"
    text = path.read_text(encoding="utf-8")
    assert text.count("    where id > 1\n") == 1
    text = text.replace("    where id > 1\n", "    where " + where + "\n")
    path.write_text(
        text.replace("table active_items", kind + " active_items") + extra,
        encoding="utf-8",
    )
    return project


def records(bundle):
    return dict(
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )


def load(bundle, payload=None, **changes):
    """load_bundle with `bundle`'s own records, `changes` replacing some."""
    return execution.load_bundle(
        bundle.payload if payload is None else payload, **(records(bundle) | changes)
    )


def project_with(directory, body):
    """The documented project with `body` after its shape and source; returns
    the project and its main.pietto text."""
    project = api.write_example(directory)
    path = project / "main.pietto"
    text = path.read_text(encoding="utf-8").split("table active_items:")[0] + body
    path.write_text(text, encoding="utf-8")
    return project, text


def test_public_compile_and_bundle_accept_a_computed_order_key(tmp_path):
    """A computed ORDER key retains its expression provenance without a use."""
    project, _ = project_with(
        tmp_path / "computed-order",
        "table active_items:\n    from items\n    select:\n        label\n        normalized = upper(label)\n"
        "    order by:\n        upper(label)\n",
    )

    query = compiled(project)
    exported = execution.export_bundle(query)
    loaded = load(exported)

    assert query.origin == "live"
    assert loaded.origin == "bundle"
    assert facts(loaded) == facts(query)


def test_public_compile_and_bundle_accept_a_joined_computed_key(tmp_path):
    """A key computed from both JOIN sides, MIN/MAX over a joined LET value and
    ordering by the key's output cross the public compile and bundle layer."""
    project, _ = project_with(
        tmp_path / "joined-computed-key",
        "table active_items:\n    from items\n    inner join items as r:\n"
        "        from items\n        on items.id == r.id\n    let:\n"
        "        later = items.id > r.id or r.id > 12\n"
        "        level = r.id + items.id * 0\n    group by:\n        later\n"
        "    select:\n        later\n        total = count()\n"
        "        low = min(level)\n        top = max(level)\n"
        "    order by:\n        later\n",
    )

    query = compiled(project)
    loaded = load(execution.export_bundle(query))

    assert query.origin == "live" and loaded.origin == "bundle"
    assert query.slots == ("Int", "Int")
    assert facts(loaded) == facts(query)


def literals(query, text):
    """The source text of each slot's literal, in slot order, found as the
    documentation says: slot i is fixed_values[i] of the bind-safe emission,
    and the `parameter` range of its literal site locates it."""
    document = json.loads(query.emission or b"")
    places = {
        r["subject"]["position"]: r["origins"][0]["sources"][0]["location"]
        for r in document["ranges"]
        if r["kind"] == "parameter"
    }
    lines = text.splitlines()
    found = []
    for slot, value in enumerate(document["fixed_values"]):
        assert value["slot"] == slot
        at = places[value["site"]["position"]]
        found.append(lines[at["line"] - 1][at["column"] - 1 : at["end_column"] - 1])
    return found


def rewritten(payload, kind, field, value):
    """The bundle with `field` of every `kind` record replaced, encoded
    again: a sender who pins changed bytes himself."""
    description = decode(payload)
    at = FIELDS[kind].index(field)
    members = tuple(
        (
            name,
            tuple(
                Record(r.address, (*r.values[:at], value, *r.values[at + 1 :]))
                if r.address.kind == kind
                else r
                for r in records
            ),
        )
        for name, records in description.members
    )
    return encode(dataclasses.replace(description, members=members))


def access(user="reader", password=PASSWORD, port=5432):
    return execution.PostgresAccess("127.0.0.1", port, "app", user, password, "disable")


def run(query, values=None, **changes):
    arguments: dict[str, Any] = dict(
        route="postgres_rows", access=access(), premise=PREMISE, values=values
    )
    arguments.update(changes)
    return execution.execute(query, **arguments)


def refused(call, *arguments, **keywords):
    """(code, detail) of the RequestRejected that `call` raises; it carries no
    attempt and is chained to nothing."""
    with pytest.raises(execution.RequestRejected) as error:
        call(*arguments, **keywords)
    assert error.value.__cause__ is None and error.value.__context__ is None
    assert error.value.attempt is None and error.value.outcome is None
    return error.value.code, error.value.detail


def bound(handle):
    """The SQL text and native arguments an unopened attempt prepared."""
    request = handle._owner.request
    return request.artifact.rendered.sql, request.binding.arguments


def facts(query):
    return (
        query.module,
        query.kind,
        query.name,
        query.dialect,
        query.release,
        query.literal_policy,
        query.slots,
    )


def root_of(query):
    return query._template.artifact.request.verification.completed.root


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    return api.write_example(tmp_path_factory.mktemp("execution-queries"))


@pytest.fixture(scope="module")
def live(example):
    return compiled(example)


@pytest.fixture(scope="module")
def bundle(live):
    return execution.export_bundle(live)


@pytest.fixture(scope="module")
def other(tmp_path_factory):
    """The export of another project: same layout, another condition."""
    return execution.export_bundle(
        compiled(variant(tmp_path_factory.mktemp("other-export"), "id > 2"))
    )


@pytest.fixture
def unconnected(monkeypatch):
    """Nothing may reach the driver or a socket."""

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused or unopened request reached the driver")

    monkeypatch.setattr(pg, "_connect", forbidden)
    monkeypatch.setattr(pg, "drivers", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.fixture
def clean(monkeypatch):
    """No ambient connection input and no PSYCOPG_IMPL, for an attempt that
    opens."""
    for name in tuple(os.environ):
        if name.startswith("PG") or name in (*ex.AMBIENT_TLS, "PSYCOPG_IMPL"):
            monkeypatch.delenv(name)
    return monkeypatch


@pytest.fixture
def code(monkeypatch):
    """The installed code identity, changed or restored as a code change and
    its reversal would change it."""
    real = loading.semantic_build_identity

    def change(identity=CHANGED):
        monkeypatch.setattr(loading, "semantic_build_identity", lambda: identity)

    def restore():
        monkeypatch.setattr(loading, "semantic_build_identity", real)

    return SimpleNamespace(change=change, restore=restore)


def test_export_returns_the_live_query_own_bundle_and_its_records(
    example, live, bundle
):
    """The payload and records are the private build of the same emission;
    the pin names exactly these bytes and the compatibility is the
    installed code. repr() shows the payload's length only."""
    outcome, _ = emit_project(
        example,
        "main.pietto",
        "table",
        "active_items",
        "postgres",
        "contract.json",
        POLICIES["bind-safe"],
    )
    built = build_compiled(outcome.artifact)
    assert (bundle.payload, bundle.pin, bundle.producer) == (
        built.payload,
        built.pin,
        built.producer,
    )
    assert (*VERSIONS, bundle.compatibility) == built.compatibility
    assert built.compatibility == loading.supported_compatibility()
    assert content_pin(bundle.payload) == bundle.pin
    assert all(
        RECORD.fullmatch(r) for r in (bundle.pin, bundle.producer, bundle.compatibility)
    )
    assert repr(bundle) == (
        f"QueryBundle(payload=<{len(bundle.payload)} bytes>, pin={bundle.pin!r},"
        f" producer={bundle.producer!r}, compatibility={bundle.compatibility!r})"
    )
    with pytest.raises(AttributeError):
        bundle.pin = CHANGED  # type: ignore[misc]
    assert refused(execution.export_bundle, None) == (
        "PIE-R1001",
        "PUBLIC_QUERY_REQUIRED",
    )
    for wrong in (bundle, bundle.payload, "SELECT 1"):
        assert refused(execution.export_bundle, wrong) == (
            "PIE-R1002",
            "PUBLIC_QUERY_TYPE",
        )


def test_compiling_the_same_project_gives_the_same_bundle_anywhere(
    example, bundle, tmp_path
):
    again = execution.export_bundle(compiled(example))
    moved = tmp_path / "elsewhere" / "copied-project"
    shutil.copytree(example, moved)
    there = execution.export_bundle(compiled(moved))
    assert again == bundle == there and again is not bundle


def test_a_loaded_bundle_is_the_live_query_template(live, bundle, unconnected):
    """A loaded query has the live query's facts and template: equal SQL
    bytes and native arguments for equal values, and the owner's
    same-template law holds exactly for equal values."""
    loaded = load(bundle)
    assert (live.origin, loaded.origin) == ("live", "bundle")
    expected = (
        "main.pietto",
        "table",
        "active_items",
        "postgres",
        "18.6",
        "bind-safe",
        ("Int",),
    )
    assert facts(loaded) == facts(live) == expected
    # The private facts end with the query's (empty) parameter header.
    assert composition.query_facts(live._template) == (*expected, ())
    assert loaded.parameters == live.parameters == ()
    assert loaded.emission is None
    assert json.loads(live.emission or b"")["status"] == "VERIFIED"
    assert repr(loaded) == repr(live).replace("origin='live'", "origin='bundle'")
    assert repr(loaded).endswith(", literal_policy='bind-safe', origin='bundle')")
    for values in (None, (3,)):
        assert bound(run(live, values)) == bound(run(loaded, values))
    (slot,) = live._template.slots
    (loaded_slot,) = loaded._template.slots
    left = bind_values(live._template, ((slot, 3),))
    same = bind_values(loaded._template, ((loaded_slot, 3),))
    different = bind_values(loaded._template, ((loaded_slot, 4),))
    assert compatible_compiled_values(left, same, route="postgres_rows")
    assert not compatible_compiled_values(left, different, route="postgres_rows")


def test_each_load_is_a_new_query_and_nothing_is_remembered(bundle):
    first, second = load(bundle), load(bundle)
    assert first is not second and first._template is not second._template
    assert root_of(first) is not root_of(second)
    assert root_of(first).scope is not root_of(second).scope
    # An accepted load does not let a later wrong pin through, and a refusal
    # does not stop a later load with the right records.
    assert refused(load, bundle, expected_pin="f" * 64) == (
        "PIE-R1007",
        "COMPILED_CONTENT_PIN",
    )
    assert load(bundle).origin == "bundle"
    assert execution.export_bundle(second) == bundle


def test_load_bundle_takes_every_trust_record_from_the_caller(bundle):
    """Keyword-only records without defaults; None is missing, anything but
    64 lowercase hexadecimal characters is invalid, each argument checked
    given then type in signature order, the payload first."""
    parameters = inspect.signature(execution.load_bundle).parameters
    assert [(n, p.kind.name, p.default is p.empty) for n, p in parameters.items()] == [
        ("payload", "POSITIONAL_OR_KEYWORD", True),
        ("expected_pin", "KEYWORD_ONLY", True),
        ("accepted_producer", "KEYWORD_ONLY", True),
        ("accepted_compatibility", "KEYWORD_ONLY", True),
    ]
    for missing in NAMES:
        given = records(bundle)
        del given[missing]
        with pytest.raises(TypeError, match=missing):
            execution.load_bundle(bundle.payload, **given)
    with pytest.raises(TypeError):
        execution.load_bundle(bundle.payload, *records(bundle).values())  # type: ignore[misc]
    assert refused(
        execution.load_bundle,
        None,
        **dict.fromkeys(NAMES),  # type: ignore[arg-type]
    ) == ("PIE-R1001", "PUBLIC_PAYLOAD_REQUIRED")
    for position in range(len(NAMES)):
        assert refused(load, bundle, **dict.fromkeys(NAMES[position:])) == (
            "PIE-R1001",
            "PUBLIC_TRUST_INPUT_REQUIRED",
        )

    class Hex(str):
        pass

    private = (*VERSIONS, bundle.compatibility)
    for name, record in records(bundle).items():
        assert record.upper() != record
        for value in (
            bundle,
            bundle.payload,
            private,
            record.upper(),
            record[:63],
            record + "0",
            "g" * 64,
            record.encode(),
            Hex(record),
        ):
            assert refused(load, bundle, **{name: value}) == (
                "PIE-R1002",
                "PUBLIC_TRUST_INPUT_TYPE",
            )
    assert refused(
        load, bundle, expected_pin=bundle.pin.upper(), accepted_producer=None
    ) == ("PIE-R1002", "PUBLIC_TRUST_INPUT_TYPE")
    assert refused(load, bundle, bytearray(bundle.payload), expected_pin=None) == (
        "PIE-R1002",
        "PUBLIC_PAYLOAD_TYPE",
    )


def test_the_accepted_compatibility_must_name_the_installed_code_first(
    bundle, code, monkeypatch
):
    """The accepted code is compared with the installed code before the
    bytes are read, so a foreign compatibility is a code-identity refusal
    whatever the bytes."""
    tampered = bundle.payload.replace(b'"1"]', b'"7"]', 1)
    assert tampered != bundle.payload
    assert refused(load, bundle, tampered) == ("PIE-R1007", "COMPILED_CONTENT_PIN")
    for payload in (tampered, b"", b"SELECT 1"):
        assert refused(load, bundle, payload, accepted_compatibility=CHANGED) == (
            "PIE-R1005",
            "PUBLIC_BUNDLE_CODE_IDENTITY",
        )
    code.change()
    assert refused(load, bundle) == ("PIE-R1005", "PUBLIC_BUNDLE_CODE_IDENTITY")

    def unknown():
        raise CompiledError("COMPILED_CODE_ORIGIN")

    monkeypatch.setattr(loading, "semantic_build_identity", unknown)
    assert refused(load, bundle) == ("PIE-R1005", "COMPILED_CODE_ORIGIN")
    code.restore()
    assert load(bundle).origin == "bundle"


def test_bundle_bytes_must_be_exactly_the_pinned_bytes(bundle):
    payload = bundle.payload
    at = payload.index(b"active_items")
    flipped = payload[:at] + b"b" + payload[at + 1 :]
    for changed in (
        flipped,
        payload + b" ",
        payload[:-1],
        payload[: len(payload) // 2],
        payload.replace(b'"1"]', b'"7"]', 1),
    ):
        assert changed != payload
        assert refused(load, bundle, changed) == ("PIE-R1007", "COMPILED_CONTENT_PIN")
    # A change that breaks the bracket nesting is refused as malformed by
    # the bounded reader before the bytes are hashed.
    assert refused(load, bundle, payload + b"]") == ("PIE-R1008", "COMPILED_JSON")
    for size in (b"", b" " * (32 * 1024 * 1024 + 1)):
        assert refused(load, bundle, size) == ("PIE-R1002", "PUBLIC_BUNDLE_SIZE")
    for wrong in (bytearray(payload), payload.decode(), memoryview(payload)):
        assert refused(load, bundle, wrong) == ("PIE-R1002", "PUBLIC_PAYLOAD_TYPE")
    # Pinned bytes whose embedded contract or premise value is empty fail
    # verification (R1008), however their limit word reads; only the payload's
    # own size is an input error.
    for kind, field in (("target", "contract"), ("premise", "value")):
        crafted = rewritten(payload, kind, field, "")
        assert 0 < len(crafted) < len(payload)
        assert refused(load, bundle, crafted, expected_pin=content_pin(crafted)) == (
            "PIE-R1008",
            "COMPILED_BYTE_LIMIT",
        )
    assert load(bundle).origin == "bundle"


def test_a_bundle_never_vouches_for_itself(bundle, other, unconnected):
    """Embedded producer and compatibility are compared, never adopted; SQL
    text is no bundle even under its own pin; and the honest limit: changed
    bytes are accepted under a pin computed from them, so only a pin from the
    caller's own records protects the content."""
    assert other.producer != bundle.producer and other.pin != bundle.pin
    assert other.compatibility == bundle.compatibility
    assert refused(load, bundle, accepted_producer=other.producer) == (
        "PIE-R1008",
        "COMPILED_COMPATIBILITY",
    )
    assert refused(load, bundle, expected_pin=other.pin) == (
        "PIE-R1007",
        "COMPILED_CONTENT_PIN",
    )
    assert refused(load, bundle, other.payload) == (
        "PIE-R1007",
        "COMPILED_CONTENT_PIN",
    )
    sql = b"SELECT * FROM fixture.items"
    assert refused(load, bundle, sql, expected_pin=content_pin(sql)) == (
        "PIE-R1008",
        "COMPILED_JSON",
    )
    tampered = bundle.payload.replace(b'"1"]', b'"7"]', 1)
    forged = load(bundle, tampered, expected_pin=content_pin(tampered))
    assert bound(run(forged))[1] == (7,)
    assert [n for n in dir(execution.QueryBundle) if not n.startswith("_")] == [
        "compatibility",
        "payload",
        "pin",
        "producer",
    ]


def test_bundles_with_a_guard_program_or_refinement_are_not_executable_here(
    tmp_path, bundle, monkeypatch
):
    """Only what compile_query can produce is executable through the public
    entry: a guarded bundle with its own records, and a root whose policy
    names a refinement, are refused."""
    from _pietto_execution_guard_cases import case_preparation, manifest

    case = next(c for c in manifest() if c["name"] == "bag_one")
    guarded = case_preparation(tmp_path / "guarded", "postgres", case)
    built = build_compiled(guarded.artifact, guarded=guarded)
    policy = built.root.records[Address("policy", 0)]
    assert (policy.get("guarded"), policy.get("refinement")) == (True, None)
    assert refused(
        execution.load_bundle,
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility[-1],
    ) == ("PIE-R1004", "PUBLIC_BUNDLE_UNSUPPORTED")
    real = loading.load_compiled

    def refined(*arguments, **keywords):
        root = real(*arguments, **keywords)
        policy = root.records[Address("policy", 0)]
        values = list(policy.values)
        values[2] = Address("refinement", 0)
        changed = dict(root.records)
        changed[policy.address] = Record(policy.address, tuple(values))
        return SimpleNamespace(records=changed)

    monkeypatch.setattr(loading, "load_compiled", refined)
    assert refused(load, bundle) == ("PIE-R1004", "PUBLIC_BUNDLE_UNSUPPORTED")


def test_a_loaded_bundle_that_cannot_become_a_template_has_the_query_codes(
    bundle, code, monkeypatch
):
    """After acceptance, the template stage reports the query's own codes:
    PIE-R1005 when the installed code changed in between and PIE-R1004 for a
    refusal of the accepted structure, never the acceptance stage's R1008."""
    real = composition.bundle_template

    def changed_in_between(root):
        code.change()
        return real(root)

    monkeypatch.setattr(composition, "bundle_template", changed_in_between)
    assert refused(load, bundle) == ("PIE-R1005", "COMPILED_COMPATIBILITY")
    code.restore()

    def refused_structure(root):
        raise CompiledError("COMPILED_INPUT_CHANGED")

    monkeypatch.setattr(composition, "bundle_template", refused_structure)
    assert refused(load, bundle) == ("PIE-R1004", "COMPILED_INPUT_CHANGED")
    # The acceptance stage calls the same word R1008.
    word = CompiledError("COMPILED_INPUT_CHANGED")
    assert errors.bundle_failure(word).code == "PIE-R1008"
    monkeypatch.setattr(composition, "bundle_template", real)
    assert load(bundle).origin == "bundle"


def test_a_stray_distribution_never_changes_what_is_accepted(
    tmp_path, example, live, bundle, monkeypatch, unconnected
):
    """A stray ANTLR runtime *.dist-info on sys.path changes neither the code
    identity nor what a load accepts: one whose RECORD claims the imported
    runtime file leaves two owners, so every compile, load and execute is
    refused; one that claims no imported file changes nothing."""
    import antlr4

    info = tmp_path / "antlr4_python3_runtime-9.9.9.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: antlr4-python3-runtime\nVersion: 9.9.9\n"
    )
    (info / "RECORD").write_text(antlr4.__file__ + ",,\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    for call in (lambda: compiled(example), lambda: load(bundle), lambda: run(live)):
        assert refused(call) == ("PIE-R1005", "COMPILED_CODE_ORIGIN")
    (info / "RECORD").write_text("antlr4/__init__.py,,\n")
    assert execution.export_bundle(compiled(example)) == bundle
    assert load(bundle).origin == "bundle" and run(live).outcome.end == "NOT_STARTED"


def test_a_code_change_invalidates_compiled_and_loaded_queries(
    example, live, bundle, code, unconnected
):
    """Every query compiled or loaded before a code change, and every load
    under the old records, is refused; restoring the code restores them."""
    loaded = load(bundle)
    code.change()
    for query in (live, loaded):
        for values in (None, (3,)):
            assert refused(run, query, values) == (
                "PIE-R1005",
                "COMPILED_COMPATIBILITY",
            )
    assert refused(load, bundle) == ("PIE-R1005", "PUBLIC_BUNDLE_CODE_IDENTITY")
    # The old bytes relabeled with the new code's compatibility.
    assert refused(load, bundle, accepted_compatibility=CHANGED) == (
        "PIE-R1008",
        "COMPILED_COMPATIBILITY",
    )
    renewed = execution.export_bundle(compiled(example))
    assert renewed.compatibility == CHANGED
    assert renewed.producer != bundle.producer and renewed.pin != bundle.pin
    assert load(renewed).origin == "bundle"
    code.restore()
    for query in (live, loaded):
        assert run(query, (3,)).outcome.end == "NOT_STARTED"
    assert load(bundle).origin == "bundle"
    assert refused(load, renewed) == ("PIE-R1005", "PUBLIC_BUNDLE_CODE_IDENTITY")


SOURCE_FREE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
events = []
WATCHED = ("open", "socket.connect", "socket.getaddrinfo", "subprocess.Popen")
sys.addaudithook(
    lambda name, args: events.append([name, str(args[0]) if args else ""])
    if name in WATCHED else None
)
config = json.loads(sys.stdin.readline())
from pathlib import Path
import pietto.ast_nodes as nodes
import pietto.parser_api as parser
from pietto._project import model, project_completed_semantics
from pietto._project import project_execution_template
def forbidden(*args, **kwargs):
    raise AssertionError("source-language entry used")
parser.parse_source = forbidden
model.build_empty_project_semantic_result = forbidden
project_completed_semantics.build_project_completed_semantic_result = forbidden
project_execution_template._syntax_image = forbidden
project_execution_template._specialize = forbidden
for name in ("Script", "QueryDef", "TableDef", "SourceDef", "LiteralExpr", "NameExpr"):
    getattr(nodes, name).__new__ = forbidden
model.ProjectParseCheckResult.__new__ = forbidden
import pietto.execution as pe
from pietto._project import project_execution as private_execution
from pietto._project import project_execution_postgres as postgres
from pietto._project import project_job_store as job_store
from pietto._project import project_job_workspace as workspace
def forbidden(*args, **kwargs):
    raise AssertionError("an unopened bundle had a side effect")
postgres._connect = forbidden
postgres.drivers = forbidden
private_execution.refuse_ambient = forbidden
workspace.create_workspace = forbidden
workspace.open_workspace = forbidden
job_store.register_job = forbidden
job_store.claim_publisher = forbidden
payload = Path(config["payload"]).read_bytes()
start = len(events)
query = pe.load_bundle(payload, **config["records"])
handle = pe.execute(query, route="postgres_rows",
    access=pe.PostgresAccess("127.0.0.1", config["port"], "app", "reader", "pw", "disable"),
    premise=pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog")), values=(3,))
after = events[start:]
mark = len(events)
exported = pe.export_bundle(query)
print(json.dumps({
    "origin": query.origin,
    "export_opens": [p for n, p in events[mark:] if n == "open"],
    "exported": exported.payload == payload,
    "end": handle.outcome.end,
    "arguments": list(handle._owner.request.binding.arguments),
    "project_reads": [p for n, p in after if n == "open"
        and p.endswith((".pietto", "pietto.toml", "contract.json"))],
    "network": [n for n, p in events if n != "open"],
    "loaded": sorted({m.split(".")[0] for m in sys.modules}
        & {"psycopg", "psycopg_binary", "pyarrow"}),
    "helpers": sorted(m for m in sys.modules if m.startswith(("_pietto_", "test_"))),
}))
# Control: the same observation sees a project file that is read.
Path("demo-exec/main.pietto").read_bytes()
print(json.dumps([p for n, p in events if n == "open" and p.endswith(".pietto")]))
"""


def test_loading_and_running_a_bundle_reads_no_project_and_connects_nowhere(
    tmp_path,
):
    """A fresh `-I` process loads and prepares a bundle whose project is gone,
    with the source-language entries forbidden and a decoy project in its
    working directory: it reads no project file, connects nowhere and loads
    no driver, PyArrow or workspace module."""
    project = api.write_example(tmp_path / "build")
    exported = execution.export_bundle(compiled(project))
    shutil.rmtree(project)
    payload = tmp_path / "active_items.bundle"
    payload.write_bytes(exported.payload)
    decoy = tmp_path / "runtime"
    api.write_example(decoy)
    listener = socket.create_server(("127.0.0.1", 0))
    listener.setblocking(False)
    environment = {
        k: v for k, v in os.environ.items() if not k.startswith(("PG", "PYTHON"))
    }
    config = {
        "payload": str(payload),
        "records": records(exported),
        "port": listener.getsockname()[1],
    }
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", SOURCE_FREE, str(ROOT / "src")],
            input=json.dumps(config) + "\n",
            capture_output=True,
            text=True,
            env=environment,
            cwd=decoy,
            timeout=120,
        )
        with pytest.raises(BlockingIOError):
            listener.accept()
    finally:
        listener.close()
    assert result.returncode == 0, result.stderr[-6000:]
    observed, control = result.stdout.splitlines()
    assert json.loads(control) == ["demo-exec/main.pietto"]
    assert json.loads(observed) == {
        "origin": "bundle",
        "export_opens": [],
        "exported": True,
        "end": "NOT_STARTED",
        "arguments": [3],
        "project_reads": [],
        "network": [],
        "loaded": [],
        "helpers": [],
    }


def test_bundles_and_errors_never_show_query_literals_or_credentials(
    tmp_path, unconnected
):
    """The bytes hold the query's literals in clear text; no repr, error,
    error chain or traceback shows a literal, a value or the password."""
    project = variant(
        tmp_path / "marker", f'id > 1 and label != "{MARKER}"', kind="query"
    )
    query = compiled(project, kind="query")
    assert (query.kind, query.slots) == ("query", ("Int", "Text"))
    exported = execution.export_bundle(query)
    assert MARKER.encode() in exported.payload
    loaded = load(exported)
    secret = access(password=PASSWORD)
    uncovered = execution.PostgresDeploymentPremise(schemas=("public", "pg_catalog"))
    calls = (
        lambda: load(exported, exported.payload.replace(MARKER.encode(), b"x")),
        lambda: load(exported, expected_pin=content_pin(MARKER.encode())),
        lambda: run(loaded, (1, MARKER + "\0"), access=secret),
        lambda: run(loaded, (True, MARKER), access=secret),
        lambda: run(loaded, [1, MARKER], access=secret),
        lambda: run(loaded, (1, MARKER), access=secret, premise=uncovered),
        lambda: execution.export_bundle(MARKER),  # type: ignore[arg-type]
        lambda: execution.load_bundle(MARKER.encode(), **records(exported)),
    )
    for call in calls:
        with pytest.raises(execution.RequestRejected) as caught:
            call()
        error = caught.value
        assert error.__cause__ is None and error.__context__ is None
        shown = "".join(traceback.format_exception(error)) + repr(error)
        assert MARKER not in shown and PASSWORD not in shown, shown
    handle = run(loaded, (1, MARKER), access=secret)
    for text in (
        repr(exported),
        str(exported),
        repr(query),
        repr(loaded),
        repr(handle),
    ):
        assert MARKER not in text and PASSWORD not in text


def test_a_bundle_carries_no_access_or_attempt_state(live, bundle, clean):
    """Exports before and after refused, unopened and failed attempts with a
    marker password are byte-identical and hold no password."""
    loaded = load(bundle)
    listener = socket.create_server(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    clean.setattr(project_arrow_result, "pinned", lambda: None)
    for query in (live, loaded):
        run(query, (5,))
        refused(run, query, (True,))
        handle = run(query, (3,), access=access(port=port))
        with pytest.raises(execution.AttemptFailed):
            with handle:
                pass
    for query in (live, loaded):
        after = execution.export_bundle(query)
        assert after == bundle and PASSWORD.encode() not in after.payload


def test_the_premise_bounds_what_a_bundle_reads(bundle, unconnected):
    loaded = load(bundle)
    for schemas in (("public", "pg_catalog"), ("fixture",), ("pg_catalog",)):
        premise = execution.PostgresDeploymentPremise(schemas=schemas)
        assert refused(run, loaded, premise=premise) == (
            "PIE-R1002",
            "POSTGRES_DEPLOYMENT_PREMISE_SCOPE",
        )
    assert run(loaded).outcome.end == "NOT_STARTED"


def test_a_mysql_bundle_loads_and_prepares_its_selected_route(
    tmp_path, unconnected, monkeypatch
):
    from _pietto_execution_postgres_rows_probe import template
    from pietto._project import project_execution_mysql_native as mysql_native

    def forbidden(*arguments, **keywords):
        raise AssertionError("an unopened MySQL bundle reached the driver")

    built = build_compiled(template(tmp_path / "mysql", target="mysql").artifact)
    query = execution.load_bundle(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility[-1],
    )
    assert (query.origin, query.dialect, query.emission) == ("bundle", "mysql", None)
    assert query.slots == ("Int",)
    for route in ("postgres_rows", "postgres_adbc", "unknown"):
        assert refused(run, query, route=route) == (
            "PIE-R1003",
            "PUBLIC_ROUTE_UNAVAILABLE",
        )
    monkeypatch.setattr(mysql_native, "drivers", forbidden)
    values = (2,)
    handle = execution.execute(
        query,
        route="mysql_rows",
        access=execution.MySQLAccess(
            "127.0.0.1",
            3306,
            "phase66",
            "pietto_query",
            PASSWORD,
            "/explicit/ca.pem",
            "pietto_query",
        ),
        premise=execution.MySQLDeploymentPremise(schemas=("phase66",)),
        values=values,
    )
    assert (
        handle.route == "mysql_rows"
        and handle.outcome.end == "NOT_STARTED"
        and handle._owner.request.binding.arguments == values
    )
    assert execution.export_bundle(query).payload == built.payload


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_conditional_parameter_uses_follow_sql_order_through_bundle_load(
    tmp_path, target
):
    from _pietto_execution_postgres_rows_probe import template
    from _pietto_results_product import source

    prepared = template(
        tmp_path / target,
        source(target).replace("renamed = id", "choice = 10 if id == 1 else 20"),
        target=target,
    )
    artifact = prepared.artifact
    assert [value.value for value in artifact.fixed_values] == [10, 1, 20]
    assert [use.original.expression.value for use in artifact.parameter_uses] == [
        1,
        10,
        20,
    ]
    assert [(use.ordinal, use.server_index) for use in artifact.parameter_uses] == [
        (0, 1),
        (1, 2),
        (2, 3),
    ]
    if target == "postgres":
        assert b"= CAST($1 AS pg_catalog.int8)) THEN CAST($2" in artifact.rendered.sql

    built = build_compiled(artifact)
    query = execution.load_bundle(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility[-1],
    )
    if target == "postgres":
        handle = execution.execute(
            query,
            route="postgres_rows",
            access=access(),
            premise=execution.PostgresDeploymentPremise(
                schemas=("public", "pg_catalog")
            ),
        )
    else:
        handle = execution.execute(
            query,
            route="mysql_rows",
            access=execution.MySQLAccess(
                "127.0.0.1",
                3306,
                "phase66",
                "pietto_query",
                PASSWORD,
                "/explicit/ca.pem",
                "pietto_query",
            ),
            premise=execution.MySQLDeploymentPremise(schemas=("phase66",)),
        )
    assert query.origin == "bundle"
    assert handle._owner.request.binding.arguments == (1, 10, 20)


def test_values_replace_the_bind_safe_fixed_values_slot_by_slot(
    live, bundle, unconnected
):
    """The native arguments are exactly the supplied values, the SQL text is
    the template's, and None binds the compiled values."""
    loaded = load(bundle)
    assert live.slots == loaded.slots == ("Int",)
    document = json.loads(live.emission or b"")
    assert [v["value"] for v in document["fixed_values"]] == ["1"]
    for query in (live, loaded):
        sql, arguments = bound(run(query))
        assert arguments == (1,) and "$1" in sql.decode()
        for value in (3, 0, -7, 2**63 - 1, -(2**63)):
            assert bound(run(query, (value,))) == (sql, (value,))


def test_each_value_must_exactly_fit_its_slot(tmp_path, live, unconnected):
    """Nothing is converted: each value has its slot's exact type and range,
    the tuple has one value per slot, and only a tuple is accepted. The
    refusal names the slot, never the value."""

    class Number(int):
        pass

    for value in (True, 3.0, 2**63, -(2**63) - 1, "3", Number(3), None):
        assert refused(run, live, (value,)) == ("PIE-R1006", "BINDING_VALUE:0:Int")
    for values in ((), (1, 2)):
        assert refused(run, live, values) == ("PIE-R1006", "BINDING_SLOTS")

    class Values(tuple):
        pass

    for values in ([3], Values((3,)), {3}, 3, "3"):
        assert refused(run, live, values) == ("PIE-R1002", "PUBLIC_VALUES_TYPE")
    text = compiled(
        variant(tmp_path / "text", f'id > 1 and label != "{MARKER}"', kind="query"),
        kind="query",
    )
    assert text.slots == ("Int", "Text")
    for value in ("nul\0inside", "\ud800", b"x", 1):
        assert refused(run, text, (1, value)) == ("PIE-R1006", "BINDING_VALUE:1:Text")
    assert bound(run(text, (1, "雪é")))[1] == (1, "雪é")


def test_a_preserve_query_has_no_slots(example, unconnected):
    query = compiled(example, "preserve")
    assert query.slots == () and query.literal_policy == "preserve"
    for values in (None, ()):
        sql, arguments = bound(run(query, values))
        assert arguments == () and "$1" not in sql.decode()
    assert refused(run, query, (1,)) == ("PIE-R1006", "BINDING_SLOTS")
    exported = execution.export_bundle(query)
    assert load(exported).slots == ()


def test_a_slot_is_one_literal_and_its_sign_stays_in_the_query(tmp_path, unconnected):
    """In `id > -1` the slot holds 1 and the minus stays SQL structure; a
    LIMIT count is no slot."""
    signed = compiled(variant(tmp_path / "sign", "id > -1"))
    assert signed.slots == ("Int",)
    sql, arguments = bound(run(signed))
    assert arguments == (1,) and "(-CAST($1" in sql.decode()
    assert bound(run(signed, (5,))) == (sql, (5,))
    # A value of the right type that cannot be prepared under the minus.
    assert refused(run, signed, (-(2**63),)) == ("PIE-R1004", "BINDING_INVALID")
    limited = compiled(
        variant(
            tmp_path / "limit", "id > 1", "    order by:\n        id\n    limit 3\n"
        )
    )
    assert limited.slots == ("Int",)
    sql, arguments = bound(run(limited, (3,)))
    assert arguments == (3,) and sql.decode().endswith("LIMIT 3")


def test_each_slot_is_one_literal_in_the_compiler_order(tmp_path, unconnected):
    """The definitions a query reads come first, in the compiler's schedule
    rather than the order the query names them; within one definition, let
    before where before select, each expression left to right; a definition
    or relation let read twice has its literals once. A loaded bundle keeps
    the order."""
    stages, text = project_with(
        tmp_path / "stages",
        "table active_items:\n    from items\n    let:\n        bonus = id + 30\n"
        '    where id > 1 and label != "x"\n    select:\n        id\n'
        "        more = bonus + 7\n",
    )
    contract_path = stages / "contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["sources"][0]["fields"][0]["representation"]["storage"] = {
        "kind": "pg_int4"
    }
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    query = compiled(stages)
    assert query.slots == ("Int", "Int", "Text", "Int")
    assert literals(query, text) == ["30", "1", '"x"', "7"]
    # Inside arithmetic a slot takes only values whose results stay
    # The source's full int4 range is proved; each literal anchors the result
    # in int8. Both bonus = id + v and more = bonus + 7 must fit that carrier.
    largest = 2**63 - 1 - (2**31 - 1) - 7
    assert bound(run(query, (largest, 1, "x", 7)))[1] == (largest, 1, "x", 7)
    assert refused(run, query, (largest + 1, 1, "x", 7)) == (
        "PIE-R1004",
        "BINDING_INVALID",
    )
    reading = (
        "table b:\n    from items\n    where id > 2\n    select:\n        id\n"
        "table a:\n    from items\n    where id > 1\n    select:\n        id\n"
        "query active_items:\n    union all:\n        from a\n        from b\n"
    )
    union, text = project_with(tmp_path / "union", reading)
    query = compiled(union, kind="query")
    assert query.slots == ("Int", "Int") and literals(query, text) == ["2", "1"]
    loaded = load(execution.export_bundle(query))
    assert loaded.slots == query.slots
    assert bound(run(loaded, (10, 20))) == bound(run(query, (10, 20)))
    twice, text = project_with(
        tmp_path / "twice",
        "table a:\n    from items\n    where id > 3\n    select:\n        id\n"
        "query active_items:\n    union all:\n        from a\n        from a\n",
    )
    query = compiled(twice, kind="query")
    assert query.slots == ("Int",) and literals(query, text) == ["3"]
    # Relation lets come before their query, each after the lets it reads,
    # otherwise as written; `base`, read twice, has its literal once.
    lets, text = project_with(
        tmp_path / "lets",
        "query active_items:\n"
        "    let low:\n        from base\n        where id < 50\n"
        "        select:\n            id\n"
        "    let high:\n        from base\n        where id > 10\n"
        "        select:\n            id\n"
        "    let base:\n        from items\n        where id > 3\n"
        "        select:\n            id\n"
        "    union all:\n        from low\n        from high\n",
    )
    query = compiled(lets, kind="query")
    assert query.slots == ("Int",) * 3 and literals(query, text) == ["3", "50", "10"]


def test_repeated_calls_share_only_the_template(live, bundle, unconnected):
    """A/B/A: each call is a new binding, request, owner and attempt with its
    own values and access; only the immutable template is shared."""
    loaded = load(bundle)
    for query in (live, loaded):
        calls = (("a", (1,)), ("b", (3,)), ("a", (1,)))
        handles = [
            run(query, values, access=access(user=user)) for user, values in calls
        ]
        requests = [h._owner.request for h in handles]
        assert len({h.attempt for h in handles}) == 3
        assert len({r.binding.instance_reference for r in requests}) == 3
        assert (
            len({id(r) for r in requests}) == len({id(h._owner) for h in handles}) == 3
        )
        assert all(r.binding.template is query._template for r in requests)
        assert [r.binding.arguments for r in requests] == [(1,), (3,), (1,)]
        assert [r.access.user for r in requests] == ["a", "b", "a"]
        assert all(h.outcome.end == "NOT_STARTED" for h in handles)


def test_a_refused_call_changes_nothing_for_the_next_call(
    live, bundle, code, tmp_path, unconnected
):
    loaded = load(bundle)
    for query in (live, loaded):
        first = bound(run(query, (3,)))
        assert refused(run, query, (True,)) == ("PIE-R1006", "BINDING_VALUE:0:Int")
        assert refused(run, query, (3,), premise=None) == (
            "PIE-R1001",
            "PUBLIC_PREMISE_REQUIRED",
        )
        code.change()
        assert refused(run, query, (3,)) == ("PIE-R1005", "COMPILED_COMPATIBILITY")
        code.restore()
        assert bound(run(query, (3,))) == first
    signed = compiled(variant(tmp_path / "sign", "id > -1"))
    assert refused(run, signed, (-(2**63),)) == ("PIE-R1004", "BINDING_INVALID")
    assert bound(run(signed, (5,)))[1] == (5,)


def test_values_are_checked_in_the_documented_order(live, code, unconnected):
    """`values` type after every presence and type check; binding (R1006)
    before the code identity (R1005); both before the premise, access,
    isolation and limits values."""
    uncovered = execution.PostgresDeploymentPremise(schemas=("public",))
    wide = execution.ExecutionLimits(batch_rows=5000)
    pairs = (
        (dict(isolation=None, values=[3]), "PUBLIC_ISOLATION_REQUIRED"),
        (dict(limits={"seconds": 1}, values=[3]), "PUBLIC_LIMITS_TYPE"),
        (dict(values=[3], premise=uncovered), "PUBLIC_VALUES_TYPE"),
        (dict(values=[3], isolation="read committed"), "PUBLIC_VALUES_TYPE"),
        (dict(values=(True,), premise=uncovered), "BINDING_VALUE:0:Int"),
        (dict(values=(1, 2), access=access(user="")), "BINDING_SLOTS"),
        (dict(values=(True,), limits=wide), "BINDING_VALUE:0:Int"),
    )
    for changes, detail in pairs:
        assert refused(run, live, **changes)[1] == detail, changes
    code.change()
    assert refused(run, live, (True,)) == ("PIE-R1006", "BINDING_VALUE:0:Int")
    assert refused(run, live, (3,), premise=uncovered) == (
        "PIE-R1005",
        "COMPILED_COMPATIBILITY",
    )


def test_a_compiled_query_keeps_the_project_it_was_compiled_from(tmp_path, unconnected):
    """A compiled query is a snapshot: edits after compile_query change
    nothing until the next compile, even with the project gone."""
    project = api.write_example(tmp_path / "snapshot")
    query = compiled(project)
    before = bound(run(query))
    exported = execution.export_bundle(query)
    path = project / "main.pietto"
    path.write_text(
        path.read_text(encoding="utf-8").replace("id > 1", "id > 2"), encoding="utf-8"
    )
    assert bound(run(query)) == before and before[1] == (1,)
    again = compiled(project)
    assert bound(run(again))[1] == (2,)
    renewed = execution.export_bundle(again)
    assert renewed.pin != exported.pin and renewed.producer != exported.producer
    assert execution.export_bundle(query) == exported
    shutil.rmtree(project)
    assert bound(run(query)) == before


LET_TAGS = """
source tags: Item is postgres.table("fixture.tags")

table tagged_items:
    let tagged:
        from tags
        where id > 2
        select:
            tag_id = id
    from items
    inner join tagged as t:
        from items
        on items.id == t.tag_id
    select:
        id = items.id
        label = items.label
"""


def let_example(directory, text=LET_TAGS):
    """The documented project plus a table whose let alone reads `tags`."""
    project = api.write_example(directory)
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + text, encoding="utf-8")
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    tags = json.loads(json.dumps(contract["sources"][0]))
    tags["selector"]["name"] = "tags"
    tags["relation"]["name"] = "tags"
    contract["sources"].append(tags)
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return project


def _with_declaration(description, label, **changes):
    """`description` with fields of the declaration record `label` changed."""
    names = FIELDS["declaration"]

    def changed(record):
        values = dict(zip(names, record.values, strict=True)) | changes
        return Record(record.address, tuple(values[name] for name in names))

    return dataclasses.replace(
        description,
        members=tuple(
            (
                name,
                tuple(
                    changed(r)
                    if r.address.kind == "declaration" and r.values[5] == label
                    else r
                    for r in records
                ),
            )
            for name, records in description.members
        ),
    )


def test_a_compiled_query_carries_each_let_as_its_own_block(tmp_path):
    project = let_example(tmp_path)
    query = execution.compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="tagged_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    description = decode(bundle.payload)
    records = description.records
    declarations = sorted(r.values for r in records if r.address.kind == "declaration")
    # The let shares its declaration's coordinates and is told apart by `let`.
    assert declarations == [
        ("main.pietto", 0, 1, "relation", "source", "items", None),
        ("main.pietto", 0, 3, "relation", "source", "tags", None),
        ("main.pietto", 0, 4, "relation", "query", "tagged", 0),
        ("main.pietto", 0, 4, "relation", "table", "tagged_items", None),
    ]
    assert sorted(r.get("name") for r in records if r.address.kind == "source") == [
        "items",
        "tags",
    ]
    loaded = execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    assert execution.export_bundle(loaded).payload == bundle.payload
    # A `let` position belongs to a query block only.
    for label, changed in (
        ("tagged", -1),
        ("tagged", True),
        ("tagged", "0"),
        ("tags", 0),
    ):
        with pytest.raises(CompiledError, match="DECLARATION"):
            verify_description(_with_declaration(description, label, let=changed))
    # Well-typed forgeries: the selected table posing as a let or a source, and
    # a let naming a position or a parent block the closure does not have.
    for label, changes, category in (
        ("tagged_items", {"let": 0}, "QUERY"),
        ("tagged_items", {"kind": "source"}, "QUERY"),
        ("tagged", {"let": 1}, "DECLARATION"),
        ("tagged", {"position": 3}, "DECLARATION"),
        ("tagged", {"module_position": 1}, "DECLARATION"),
    ):
        with pytest.raises(CompiledError, match=category):
            verify_description(_with_declaration(description, label, **changes))
    # A let is not a module declaration and cannot be selected.
    with pytest.raises(execution.CompileRejected):
        execution.compile_query(
            project,
            module="main.pietto",
            kind="query",
            name="tagged",
            dialect="postgres",
            emission_contract="contract.json",
        )


def test_each_route_prepares_a_let_query_with_its_let_source(tmp_path, unconnected):
    """An unopened attempt of every route binds the let's source like any other."""
    import _pietto_sql_emission as probe

    query = execution.compile_query(
        let_example(tmp_path / "postgres"),
        module="main.pietto",
        kind="table",
        name="tagged_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    for route in ("postgres_rows", "postgres_adbc"):
        handle = run(query, route=route)
        request = handle._owner.request
        assert handle.route == route and handle.outcome.end == "NOT_STARTED"
        assert [s.name for s in request.binding.artifact.request.sources] == [
            "items",
            "tags",
        ]
    item = probe.fixture("mysql", "L_let_relations", "hidden_join")
    root = tmp_path / "mysql"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (root / "main.pietto").write_text(item["source"], encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    mysql_query = execution.compile_query(
        root,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="mysql",
        emission_contract="contract.json",
    )
    handle = execution.execute(
        mysql_query,
        route="mysql_rows",
        access=execution.MySQLAccess(
            "127.0.0.1",
            3306,
            "phase66",
            "pietto_query",
            PASSWORD,
            "/explicit/ca.pem",
            "pietto_query",
        ),
        premise=execution.MySQLDeploymentPremise(schemas=("phase66",)),
    )
    assert handle.route == "mysql_rows" and handle.outcome.end == "NOT_STARTED"
    # The MySQL source closure starts from exactly these roots.
    assert [s.name for s in handle._owner.request.artifact.request.sources] == [
        "phase66 source é",
        "p0",
    ]


REUSED_LETS = {
    # `base` is read by two lets declared before it, both read by the body.
    "diamond": (
        """table result:
    let low:
        from base
        where id < 50
        select:
            id
    let high:
        from base
        where id > 10
        select:
            id
    let base:
        from items
        select:
            id
    union all:
        from low
        from high
""",
        [
            ("base", "items", 0),
            ("low", "base", 0),
            ("high", "base", 0),
            ("result", "low", 0),
            ("result", "high", 1),
        ],
    ),
    "self_join": (
        """table result:
    let a:
        from items
        select:
            id
    from a
    inner join a as b:
        from a
        on a.id == b.id
    select:
        x = a.id
""",
        [("a", "items", 0), ("result", "a", 0), ("result", "a", 1)],
    ),
}


@pytest.mark.parametrize("case", sorted(REUSED_LETS))
def test_a_reused_let_is_one_producer_with_distinct_uses(tmp_path, case):
    text, expected = REUSED_LETS[case]
    project = api.write_example(tmp_path)
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + text, encoding="utf-8")
    query = execution.compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="result",
        dialect="postgres",
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    records = {r.address: r for r in decode(bundle.payload).records}
    labels = [
        r.get("label") for r in records.values() if r.address.kind == "declaration"
    ]
    # One declaration record per let and declaration, never one per read.
    assert sorted(labels) == sorted({label for use in expected for label in use[:2]})

    def owner(address):
        record = records[address]
        field = "declaration" if address.kind == "source" else "owner"
        return records[record.get(field)].get("label")

    crossing = [
        (owner(r.get("consumer")), owner(r.get("producer")), r.get("ordinal"))
        for r in records.values()
        if r.address.kind == "use"
        and owner(r.get("consumer")) != owner(r.get("producer"))
    ]
    assert crossing == expected
    loaded = execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    assert execution.export_bundle(loaded).payload == bundle.payload


VALUES_SEED = """
query seeded:
    values(id: Int not null, label: Text nullable):
        1, "a"
        2, null
"""


def values_example(directory):
    """The documented project plus a pure VALUES query and a source-free contract."""
    project = api.write_example(directory)
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + VALUES_SEED, encoding="utf-8")
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    contract["sources"] = []
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return project


def _with_values(description, change):
    """`description` with its one `values` record's values passed through `change`."""
    return dataclasses.replace(
        description,
        members=tuple(
            (
                name,
                tuple(
                    Record(r.address, change(r.values))
                    if r.address.kind == "values"
                    else r
                    for r in records
                ),
            )
            for name, records in description.members
        ),
    )


def test_a_compiled_values_query_carries_its_typed_rows_inline(tmp_path):
    query = execution.compile_query(
        values_example(tmp_path),
        module="main.pietto",
        kind="query",
        name="seeded",
        dialect="postgres",
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    (values,) = (r for r in records.values() if r.address.kind == "values")
    assert not any(a.kind in ("source", "use") for a in records)
    fields = [records[a].values for a in values.get("fields")]
    assert [f[1:5] for f in fields] == [
        (0, "id", "c0", ("Int", "non_null")),
        (1, "label", "c1", ("Text", "nullable")),
    ]
    assert [
        tuple(None if cell is None else (cell.tag, cell.value) for cell in row)
        for row in values.get("rows")
    ] == [(("Int", 1), ("Text", "a")), (("Int", 2), None)]
    assert values.get("layout") == (None, (), "v0", True, 0)
    loaded = execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    assert execution.export_bundle(loaded).payload == bundle.payload
    emission = query.emission
    assert emission is not None
    live_sql = json.loads(emission)["sql"]
    assert query._template.artifact.rendered.sql.decode() == live_sql
    assert loaded._template.artifact.rendered.sql.decode() == live_sql
    # A forged cell, column type or row width is not a VALUES record.
    for change in (
        lambda v: (v[0], v[1], ((None, v[2][0][1]), v[2][1]), *v[3:]),
        lambda v: (v[0], v[1], ((v[2][0][1], v[2][0][0]), v[2][1]), *v[3:]),
        lambda v: (v[0], v[1], (v[2][0][:1], v[2][1]), *v[3:]),
        lambda v: (v[0], v[1], v[2] * 501, *v[3:]),
    ):
        with pytest.raises(CompiledError, match="VALUES"):
            verify_description(_with_values(description, change))


def test_a_zero_source_values_query_prepares_on_postgres_with_pg_catalog(
    tmp_path, unconnected
):
    query = execution.compile_query(
        values_example(tmp_path),
        module="main.pietto",
        kind="query",
        name="seeded",
        dialect="postgres",
        emission_contract="contract.json",
    )
    handle = run(query, premise=execution.PostgresDeploymentPremise(("pg_catalog",)))
    assert handle.route == "postgres_rows" and handle.outcome.end == "NOT_STARTED"
    assert handle._owner.request.artifact.request.sources == ()
    assert refused(
        run, query, premise=execution.PostgresDeploymentPremise(("fixture",))
    ) == ("PIE-R1002", "POSTGRES_DEPLOYMENT_PREMISE_SCOPE")


def test_a_parameterized_query_over_values_binds_without_io(tmp_path, unconnected):
    """A header parameter reads beside the VALUES columns it never shadows."""
    project = values_example(tmp_path)
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + "query picked(low: Int not null):\n    from seeded\n    where id > low\n"
        "    select:\n        id\n        label\n",
        encoding="utf-8",
    )
    query = execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="picked",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="bind-safe",
    )
    assert query.parameters == (("low", "Int", False),)
    premise = execution.PostgresDeploymentPremise(("pg_catalog",))
    handle = run(query, premise=premise, parameters={"low": 1})
    sql, arguments = bound(handle)
    assert arguments == (1,)
    assert b'WHERE ("s0"."c0" > CAST($1 AS pg_catalog.int8))' in sql
    handle.close()
    assert refused(run, query, premise=premise, parameters={"low": "1"}) == (
        "PIE-R1006",
        "BINDING_PARAMETER:0:Int",
    )


VALUES_BESIDE = """query result:
    let seed:
        values(rid: Int not null, label: Text nullable, flag: Bool nullable, ratio: Float nullable):
            1, "a", true, 0.5
            2, null, null, null
    from lhs
    inner join seed as s:
        from lhs
        on lhs.id == s.rid
    select:
        a = lhs.id
        b = s.label
        c = s.flag
        d = s.ratio
"""
# The header alone: every column's domain is its whole carrier.
VALUES_EMPTY_BESIDE = """query result:
    let seed:
        values(rid: Int not null, label: Text nullable, flag: Bool nullable, ratio: Float nullable)
    from lhs
    left join seed as s:
        from lhs
        on lhs.id == s.rid
    select:
        a = lhs.id
        b = s.label
"""
VALUES_CARRIERS = {
    "postgres": ["pg_int8", "pg_text", "pg_bool", "pg_float8"],
    "mysql": ["my_signed_int", "my_utf8mb4_text", "my_signed_bool", "my_double"],
}


@pytest.mark.parametrize("body", (VALUES_BESIDE, VALUES_EMPTY_BESIDE))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_values_beside_a_physical_source_compiles_loads_and_prepares(
    tmp_path, target, body, unconnected
):
    """Each VALUES column keeps its target's literal carrier through compile,
    export and load, though no contract source field has MySQL's carriers, and
    the target's route prepares the query with the physical source only."""
    query = execution.compile_query(
        api.write_join_witness(tmp_path / target, target, body),
        module="main.pietto",
        kind="query",
        name="result",
        dialect=target,
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    described = {r.address: r for r in decode(bundle.payload).records}
    (values,) = (r for r in described.values() if r.address.kind == "values")
    assert [
        json.loads(described[a].get("physical"))["storage"]["kind"]
        for a in values.get("fields")
    ] == VALUES_CARRIERS[target]
    loaded = load(bundle)
    assert execution.export_bundle(loaded).payload == bundle.payload
    sql = query._template.artifact.rendered.sql
    assert loaded._template.artifact.rendered.sql == sql
    if target == "postgres":
        handle = run(
            loaded,
            premise=execution.PostgresDeploymentPremise(("public", "pg_catalog")),
        )
    else:
        handle = execution.execute(
            loaded,
            route="mysql_rows",
            access=execution.MySQLAccess(
                "127.0.0.1",
                3306,
                "phase66",
                "pietto_query",
                PASSWORD,
                "/explicit/ca.pem",
                "pietto_query",
            ),
            premise=execution.MySQLDeploymentPremise(schemas=("phase66",)),
        )
    assert handle.outcome.end == "NOT_STARTED"
    request = handle._owner.request
    assert request.artifact.rendered.sql == sql
    assert [s.name for s in request.artifact.request.sources] == ["phase66 lhs é"]


def _forged(payload, change):
    """`payload` with every record passed through `change` (None keeps it),
    encoded again: a sender who pins changed bytes himself."""
    description = decode(payload)
    return encode(
        dataclasses.replace(
            description,
            members=tuple(
                (name, tuple(change(r) or r for r in records))
                for name, records in description.members
            ),
        )
    )


def _set(record, name, value):
    at = FIELDS[record.address.kind].index(name)
    return Record(
        record.address, (*record.values[:at], value, *record.values[at + 1 :])
    )


def _at(address, change):
    """`change` for the record at `address` only."""
    return lambda r: change(r) if r.address == address else None


def _physical(record, change):
    from pietto._project.project_sql_emission_contract import canonical

    value = json.loads(record.get("physical"))
    change(value)
    return _set(record, "physical", canonical(value).decode())


def test_load_rederives_each_values_column_from_its_own_cells(tmp_path):
    """A self-pinned VALUES record is refused when a column claims another
    carrier or domain than its cells give, a cell PostgreSQL cannot store, or a
    column, port or layout compile_query never writes."""
    from pietto._project.project_compiled_schema import Scalar

    query = execution.compile_query(
        values_example(tmp_path),
        module="main.pietto",
        kind="query",
        name="seeded",
        dialect="postgres",
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    (values,) = (
        r for r in decode(bundle.payload).records if r.address.kind == "values"
    )
    number, text = values.get("fields")
    port = values.get("outputs")[0]
    (one, a), (two, null) = values.get("rows")
    at = _at
    forgeries = {
        "VALUES_REPRESENTATION": (
            at(number, lambda r: _physical(r, lambda p: p["domain"].update(max="1"))),
            at(number, lambda r: _physical(r, lambda p: p["domain"].update(min="0"))),
            at(number, lambda r: _physical(r, lambda p: p.update(nullable=True))),
            at(
                number,
                lambda r: _physical(r, lambda p: p.update(storage={"kind": "pg_int4"})),
            ),
            at(
                text,
                lambda r: _physical(r, lambda p: p["domain"].update(max_characters=6)),
            ),
            # Same length, so only the NUL that PostgreSQL text cannot hold differs.
            at(
                values.address,
                lambda r: _set(r, "rows", ((one, Scalar("Text", "\0")), (two, null))),
            ),
        ),
        "VALUES_COLUMNS": (
            at(number, lambda r: _set(r, "column", "c1")),
            at(number, lambda r: _set(r, "logical", None)),
            at(port, lambda r: _set(r, "logical", ("Int", "nullable"))),
        ),
        "VALUES_LAYOUT": (
            at(values.address, lambda r: _set(r, "layout", r.get("layout")[:4])),
        ),
    }
    assert a == Scalar("Text", "a") and null is None
    for category, changes in forgeries.items():
        for change in changes:
            forged = _forged(bundle.payload, change)
            assert refused(load, bundle, forged, expected_pin=content_pin(forged)) == (
                "PIE-R1008",
                "COMPILED_" + category,
            )


def test_a_premise_context_naming_a_values_column_is_a_compiled_refusal(tmp_path):
    """A self-pinned expression context that names a VALUES column, scoping the
    physical source's premise, is a classified PIE-R1008 refusal: a VALUES
    column has no source premise. Naming a source field keeps its own scope
    refusal."""
    query = execution.compile_query(
        api.write_join_witness(tmp_path / "pg", "postgres", VALUES_BESIDE),
        module="main.pietto",
        kind="query",
        name="result",
        dialect="postgres",
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    description = decode(bundle.payload)
    records = {r.address: r for _, group in description.members for r in group}
    (values,) = (r for r in records.values() if r.address.kind == "values")
    (premise,) = (
        r
        for r in records.values()
        if r.address.kind == "premise" and r.get("key") == "row_domain_matches"
    )
    (source,) = (r for r in records.values() if r.address.kind == "source")
    context = Address("expression_context", 0)
    for field, category in (
        (values.get("fields")[0], "COMPILED_EXPRESSION_CONTEXT"),
        (source.get("fields")[0], "COMPILED_CONTRACT_PREMISE_SCOPE"),
    ):
        added = Record(
            context, (Address("declaration", 2), "where", 0, "query", 0, (field,))
        )
        members = tuple(
            (
                name,
                tuple(
                    _set(r, "scope", (premise.get("scope"), context))
                    if r.address == premise.address
                    else r
                    for r in group
                )
                + ((added,) if name == "structure" else ()),
            )
            for name, group in description.members
        )
        forged = encode(dataclasses.replace(description, members=members))
        assert refused(load, bundle, forged, expected_pin=content_pin(forged)) == (
            "PIE-R1008",
            category,
        )


def test_export_and_compiled_emission_check_values_records_against_their_unit(
    tmp_path,
):
    """The exporter compares each VALUES record with the emitted unit, and the
    compiled emission compares the unit it rebuilds with the record."""
    from dataclasses import replace

    from pietto._project.project_compiled_schema import Scalar
    from pietto._project.project_compiled_verification import (
        verify_compiled_values_unit,
        verify_export,
    )

    project = values_example(tmp_path)
    outcome, _ = emit_project(
        project,
        "main.pietto",
        "query",
        "seeded",
        "postgres",
        "contract.json",
        POLICIES["preserve"],
    )
    payload = build_compiled(outcome.artifact).payload
    description = decode(payload)
    verify_export(description, outcome.artifact)
    (values,) = (r for r in description.records if r.address.kind == "values")
    (one, _), second = values.get("rows")
    label = values.get("fields")[0]
    for category, change in (
        (
            "EXPORT_VALUES",
            _at(values.address, lambda r: _set(r, "layout", (None, (), "v9", True, 0))),
        ),
        ("EXPORT_VALUES_COLUMN", _at(label, lambda r: _set(r, "label", "other"))),
        (
            "EXPORT_VALUES_ROW",
            _at(
                values.address,
                lambda r: _set(r, "rows", ((one, Scalar("Text", "b")), second)),
            ),
        ),
    ):
        changed = decode(_forged(payload, change))
        with pytest.raises(CompiledError, match=f"^COMPILED_{category}$"):
            verify_export(changed, outcome.artifact)
    artifact = execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="seeded",
        dialect="postgres",
        emission_contract="contract.json",
    )._template.artifact
    request = artifact.request
    (record,) = (
        r
        for r in request.plan.ir.completed.root.records.values()
        if r.address.kind == "values"
    )
    (body,) = artifact.ast.bodies
    verify_compiled_values_unit(body, record, request)
    first = body.columns[0]
    for category, changed in (
        ("VALUES_UNIT", replace(body, rows=body.rows[::-1])),
        (
            "VALUES_COLUMN",
            replace(body, columns=(replace(first, label="x"), *body.columns[1:])),
        ),
    ):
        with pytest.raises(CompiledError, match=f"^COMPILED_{category}$"):
            verify_compiled_values_unit(changed, record, request)


EXISTS_TAGS = """
source tags: Item is postgres.table("fixture.tags")

table flagged_items:
    let tagged:
        from tags
        where id > 2
        select:
            tag_id = id
    from items
    where exists tagged and not exists tags
    select:
        id = items.id
        label = items.label
"""


def _flagged(directory):
    return execution.compile_query(
        let_example(directory, EXISTS_TAGS),
        module="main.pietto",
        kind="table",
        name="flagged_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


def _replaced(description, kind, change):
    return dataclasses.replace(
        description,
        members=tuple(
            (name, tuple(change(r) if r.address.kind == kind else r for r in records))
            for name, records in description.members
        ),
    )


def test_a_compiled_existence_read_carries_its_block_use_and_inner_source(
    tmp_path,
):
    query = _flagged(tmp_path)
    bundle = execution.export_bundle(query)
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    assert tuple(description.compatibility[:4]) == VERSIONS
    reads = [r for r in description.records if r.address.kind == "expression_block_use"]
    # One record per read in the statement's block use order; record n renders
    # the relation alias e<n>, so no alias, clause or occurrence field is stored.
    assert [r.address.position for r in reads] == [0, 1]
    for read in reads:
        operation = records[read.get("operation")]
        assert operation.get("operator") == ("exists", "exists")
        assert operation.get("operands") == ()
        assert operation.get("logical") == ("Bool", "non_null")
        assert read.get("column") is None
        consumer = records[read.get("consumer")]
        assert records[consumer.get("owner")].get("label") == "flagged_items"
    let_unit = records[reads[0].get("producer")]
    assert (
        records[let_unit.get("owner")].get("label"),
        records[let_unit.get("owner")].get("let"),
    ) == ("tagged", 0)
    assert records[reads[1].get("producer")].get("name") == "tags"
    # The source read only through the let or the read is a compiled source.
    assert sorted(
        r.get("name") for r in records.values() if r.address.kind == "source"
    ) == ["items", "tags"]
    loaded = execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    assert execution.export_bundle(loaded).payload == bundle.payload
    sql = loaded._template.artifact.rendered.sql
    assert b'AS "e0"' in sql and b'AS "e1"' in sql

    def changed(index, values):
        target = reads[index].address
        return dataclasses.replace(
            description,
            members=tuple(
                (
                    name,
                    tuple(
                        Record(r.address, values) if r.address == target else r
                        for r in rs
                    ),
                )
                for name, rs in description.members
            ),
        )

    first, second = (r.values for r in reads)
    for forged in (
        # A producer equal to its consumer, a consumer that does not execute
        # the read, a column on an existence read, two records of one read.
        changed(0, (first[0], first[1], first[1], None)),
        changed(0, (first[0], first[2], first[2], None)),
        changed(0, (*first[:3], 0)),
        changed(1, (first[0], *second[1:])),
    ):
        with pytest.raises(CompiledError):
            verify_description(forged)
    # Without its block uses the inner relation is outside the closure.
    with pytest.raises(CompiledError):
        verify_description(
            dataclasses.replace(
                description,
                members=tuple(
                    (
                        name,
                        tuple(
                            r for r in rs if r.address.kind != "expression_block_use"
                        ),
                    )
                    for name, rs in description.members
                ),
            )
        )
    # Valid-looking swaps describe another consistent query; the export
    # verifier re-derives every record from the live statement and refuses them.
    outcome, _ = emit_project(
        let_example(tmp_path / "live", EXISTS_TAGS),
        "main.pietto",
        "table",
        "flagged_items",
        "postgres",
        "contract.json",
        POLICIES["bind-safe"],
    )
    built = build_compiled(outcome.artifact)
    live = decode(built.payload)
    verify_export(live, outcome.artifact)
    live_reads = [r for r in live.records if r.address.kind == "expression_block_use"]
    a, b = (r.values for r in live_reads)

    def swapped(first_values, second_values):
        targets = {
            live_reads[0].address: first_values,
            live_reads[1].address: second_values,
        }
        return dataclasses.replace(
            live,
            members=tuple(
                (
                    name,
                    tuple(
                        Record(r.address, targets[r.address])
                        if r.address in targets
                        else r
                        for r in rs
                    ),
                )
                for name, rs in live.members
            ),
        )

    for forged in (
        swapped((a[0], a[1], b[2], None), (b[0], b[1], a[2], None)),
        swapped((b[0], *a[1:]), (a[0], *b[1:])),
        swapped(b, a),
    ):
        verify_description(forged)
        with pytest.raises(CompiledError):
            verify_export(forged, outcome.artifact)


def test_each_route_prepares_an_existence_read_with_its_inner_source(
    tmp_path, unconnected
):
    query = _flagged(tmp_path)
    for route in ("postgres_rows", "postgres_adbc"):
        handle = run(query, route=route)
        request = handle._owner.request
        assert handle.route == route and handle.outcome.end == "NOT_STARTED"
        assert [s.name for s in request.binding.artifact.request.sources] == [
            "items",
            "tags",
        ]
    import _pietto_sql_emission as probe

    item = probe.join_witness(
        "mysql",
        "query result:\n    let picked:\n        from rhs\n        select:\n"
        "            rid = id\n    from lhs\n    where not exists picked\n"
        "    select:\n        a = lhs.id\n        e = exists rhs\n",
    )
    root = tmp_path / "mysql"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (root / "main.pietto").write_text(item["source"], encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    mysql_query = execution.compile_query(
        root,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="mysql",
        emission_contract="contract.json",
    )
    handle = execution.execute(
        mysql_query,
        route="mysql_rows",
        access=execution.MySQLAccess(
            "127.0.0.1",
            3306,
            "phase66",
            "pietto_query",
            PASSWORD,
            "/explicit/ca.pem",
            "pietto_query",
        ),
        premise=execution.MySQLDeploymentPremise(schemas=("phase66",)),
    )
    assert handle.route == "mysql_rows" and handle.outcome.end == "NOT_STARTED"
    # A source read only inside the read let or the read itself is a MySQL
    # source closure root.
    assert [s.name for s in handle._owner.request.artifact.request.sources] == [
        "phase66 lhs é",
        "phase66 rhs é",
    ]


SCALAR_TAGS = """
source tags: Item is postgres.table("fixture.tags")

table priced_items:
    let top:
        from tags
        where id > 2
        select:
            n = count()
    from items
    where id <= scalar top.n
    select:
        id = items.id
        best = scalar tags.label
"""


def _priced(directory):
    return execution.compile_query(
        let_example(directory, SCALAR_TAGS),
        module="main.pietto",
        kind="table",
        name="priced_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


def test_a_compiled_scalar_read_carries_its_column_and_inner_source(tmp_path):
    query = _priced(tmp_path)
    bundle = execution.export_bundle(query)
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    assert tuple(description.compatibility[:4]) == VERSIONS
    reads = sorted(
        (r for r in records.values() if r.address.kind == "expression_block_use"),
        key=lambda r: r.address.position,
    )
    # The read's own column ordinal is the only scalar-specific record value.
    assert [
        (
            records[r.get("operation")].get("operator"),
            records[r.get("operation")].get("operands"),
            records[r.get("operation")].get("logical"),
            r.get("column"),
        )
        for r in reads
    ] == [
        (("scalar", "scalar"), (), ("Int", "nullable"), 0),
        (("scalar", "scalar"), (), ("Text", "nullable"), 1),
    ]
    owner = records[records[reads[0].get("producer")].get("owner")]
    assert (owner.get("label"), owner.get("let")) == ("top", 0)
    assert records[reads[1].get("producer")].get("name") == "tags"
    assert sorted(
        r.get("name") for r in records.values() if r.address.kind == "source"
    ) == ["items", "tags"]
    loaded = execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    assert execution.export_bundle(loaded).payload == bundle.payload
    source_read = reads[1].address
    at = FIELDS["expression_block_use"].index("column")

    def forged(column):
        return _replaced(
            description,
            "expression_block_use",
            lambda r: (
                Record(r.address, (*r.values[:at], column, *r.values[at + 1 :]))
                if r.address == source_read
                else r
            ),
        )

    # A column past the producer's outputs, none, and an existence operator
    # are refused by the description check itself.
    for column in (2, None):
        with pytest.raises(CompiledError):
            verify_description(forged(column))
    with pytest.raises(CompiledError):
        verify_description(
            _replaced(
                description,
                "operation",
                lambda r: (
                    Record(r.address, (("exists", "exists"), *r.values[1:]))
                    if r.address == reads[1].get("operation")
                    else r
                ),
            )
        )
    # The source's other existing column, under a pin computed from the forged
    # bytes, is refused by the independent semantic re-derivation.
    crafted = encode(forged(0))
    assert refused(load, bundle, crafted, expected_pin=content_pin(crafted)) == (
        "PIE-R1004",
        "COMPILED_OPERATOR_TYPE",
    )


# No FROM, JOIN, set or let reads `tags`: only scalar reads in WHERE and SELECT.
SCALAR_ONLY = """
source tags: Item is postgres.table("fixture.tags")

table scalar_only:
    from items
    where id <= scalar tags.id
    select:
        id = items.id
        best = scalar tags.label
"""


def test_a_source_read_only_through_scalar_reads_compiles_and_loads(
    tmp_path, unconnected
):
    query = execution.compile_query(
        let_example(tmp_path, SCALAR_ONLY),
        module="main.pietto",
        kind="table",
        name="scalar_only",
        dialect="postgres",
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    records = {r.address: r for r in decode(bundle.payload).records}
    (tags,) = (
        r.address
        for r in records.values()
        if r.address.kind == "source" and r.get("name") == "tags"
    )
    assert [
        (
            records[r.get("operation")].get("operator"),
            r.get("producer"),
            r.get("column"),
        )
        for r in records.values()
        if r.address.kind == "expression_block_use"
    ] == [(("scalar", "scalar"), tags, 0), (("scalar", "scalar"), tags, 1)]
    # No stage input uses `tags`; its ports are reached only through the reads.
    assert not any(
        r.address.kind == "use" and r.get("producer") == tags for r in records.values()
    )
    loaded = load(bundle)
    assert execution.export_bundle(loaded).payload == bundle.payload
    handle = run(loaded)
    assert bound(handle) == bound(run(query))
    sources = handle._owner.request.binding.artifact.request.sources
    assert [s.name for s in sources] == ["items", "tags"]


def test_each_route_prepares_a_scalar_read_with_its_inner_source(tmp_path, unconnected):
    import _pietto_sql_emission as probe

    query = _priced(tmp_path / "postgres")
    for route in ("postgres_rows", "postgres_adbc"):
        handle = run(query, route=route)
        request = handle._owner.request
        assert handle.route == route and handle.outcome.end == "NOT_STARTED"
        assert [s.name for s in request.binding.artifact.request.sources] == [
            "items",
            "tags",
        ]
    item = probe.fixture("mysql", "L_relation_scalar", "kept")
    root = tmp_path / "mysql"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (root / "main.pietto").write_text(item["source"], encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    mysql_query = execution.compile_query(
        root,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="mysql",
        emission_contract="contract.json",
    )
    handle = execution.execute(
        mysql_query,
        route="mysql_rows",
        access=execution.MySQLAccess(
            "127.0.0.1",
            3306,
            "phase66",
            "pietto_query",
            PASSWORD,
            "/explicit/ca.pem",
            "pietto_query",
        ),
        premise=execution.MySQLDeploymentPremise(schemas=("phase66",)),
    )
    assert handle.route == "mysql_rows" and handle.outcome.end == "NOT_STARTED"
    assert b"(SELECT `e0`.`c0` FROM `p3` AS `e0`)" in (
        handle._owner.request.artifact.rendered.sql
    )


MEMBERSHIP_TAGS = """
source tags: Item is postgres.table("fixture.tags")

table tag_ids:
    from tags
    select:
        id

table flagged_items:
    let tagged:
        from tags
        where id > 2
        select:
            tag_id = id
    from items
    where id not in tagged
    select:
        id = items.id
        label = items.label
        flag = 3 in tag_ids
"""


def _members(project, policy="preserve"):
    return execution.compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="flagged_items",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy=policy,
    )


def test_a_compiled_membership_read_carries_its_operand_column_and_inner_source(
    tmp_path,
):
    project = let_example(tmp_path, MEMBERSHIP_TAGS)
    query = _members(project)
    bundle = execution.export_bundle(query)
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    reads = [r for r in description.records if r.address.kind == "expression_block_use"]
    operations = [records[r.get("operation")] for r in reads]
    assert [r.address.position for r in reads] == [0, 1]
    assert [o.get("operator") for o in operations] == [
        ("relation_membership", "not_in"),
        ("relation_membership", "in"),
    ]
    assert [o.get("logical") for o in operations] == [("Bool", "nullable")] * 2
    assert [[a.kind for a in o.get("operands")] for o in operations] == [
        ["read"],
        ["literal"],
    ]
    # The read compares with column 0 of its single-column producer.
    assert [r.get("column") for r in reads] == [0, 0]
    producers = [records[records[r.get("producer")].get("owner")] for r in reads]
    assert [(p.get("label"), p.get("let")) for p in producers] == [
        ("tagged", 0),
        ("tag_ids", None),
    ]
    assert sorted(
        r.get("name") for r in records.values() if r.address.kind == "source"
    ) == ["items", "tags"]
    loaded = execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    assert execution.export_bundle(loaded).payload == bundle.payload
    first = reads[0]
    for changed in (
        # No column, another column, a Boolean that equals 0 and a producer
        # equal to its consumer are each refused.
        lambda r: Record(r.address, (*r.values[:3], None)),
        lambda r: Record(r.address, (*r.values[:3], 1)),
        lambda r: Record(r.address, (*r.values[:3], False)),
        lambda r: Record(r.address, (r.values[0], r.values[1], r.values[1], 0)),
    ):
        forged = _replaced(
            description,
            "expression_block_use",
            lambda r: changed(r) if r.address == first.address else r,
        )
        with pytest.raises(CompiledError):
            verify_description(forged)
    # A membership without its left value breaks the operator arity.
    with pytest.raises(CompiledError):
        verify_description(
            _replaced(
                description,
                "operation",
                lambda r: (
                    Record(r.address, (r.values[0], (), *r.values[2:]))
                    if r.address == operations[0].address
                    else r
                ),
            )
        )
    # The other membership operator describes another consistent query; the
    # export verifier re-derives it from the live statement and refuses it.
    flipped = _replaced(
        description,
        "operation",
        lambda r: (
            Record(r.address, (("relation_membership", "in"), *r.values[1:]))
            if r.address == operations[0].address
            else r
        ),
    )
    verify_description(flipped)
    outcome, _ = emit_project(
        project,
        "main.pietto",
        "table",
        "flagged_items",
        "postgres",
        "contract.json",
        POLICIES["preserve"],
    )
    verify_export(description, outcome.artifact)
    with pytest.raises(CompiledError):
        verify_export(flipped, outcome.artifact)


def test_each_route_prepares_a_membership_read_with_its_inner_source(
    tmp_path, unconnected
):
    query = _members(let_example(tmp_path, MEMBERSHIP_TAGS), policy="bind-safe")
    sql = query._template.artifact.rendered.sql.decode()
    assert '"s2"."item_id" NOT IN (SELECT "e0"."c0" FROM "p2" AS "e0")' in sql
    assert (
        '(CAST($2 AS pg_catalog.int8) IN (SELECT "e1"."c0" FROM "p0" AS "e1"))' in sql
    )
    for route in ("postgres_rows", "postgres_adbc"):
        handle = run(query, route=route)
        request = handle._owner.request
        assert handle.route == route and handle.outcome.end == "NOT_STARTED"
        assert [s.name for s in request.binding.artifact.request.sources] == [
            "items",
            "tags",
        ]


def test_compile_query_refuses_a_two_column_membership_read(tmp_path):
    text = MEMBERSHIP_TAGS.replace(
        "        id\n\ntable flagged_items:",
        "        id\n        label\n\ntable flagged_items:",
    )
    assert text != MEMBERSHIP_TAGS
    with pytest.raises(execution.CompileRejected) as error:
        _members(let_example(tmp_path, text))
    document = json.loads(error.value.emission)
    assert error.value.status == document["status"] == "BLOCKED"
    # The width of a module table is known before completion: the semantic
    # check refuses the read at the test.
    assert [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in document["diagnostics"]
    ] == [
        (
            "PIE-S2105",
            "Invalid operands for operator in: expected a relation with one "
            "output column",
            33,
            16,
        )
    ]


@pytest.mark.parametrize("policy", ("preserve", "bind-safe"))
def test_a_null_left_value_takes_the_read_column_type_through_compile_and_load(
    tmp_path, unconnected, policy
):
    text = MEMBERSHIP_TAGS.replace(
        "        flag = 3 in tag_ids\n",
        "        flag = 3 in tag_ids\n        unknown = null not in tag_ids\n",
    )
    assert text != MEMBERSHIP_TAGS
    query = _members(let_example(tmp_path, text), policy)
    sql = query._template.artifact.rendered.sql.decode()
    assert '(NULL NOT IN (SELECT "e2"."c0" FROM "p0" AS "e2")) AS "unknown"' in sql
    bundle = execution.export_bundle(query)
    records = {r.address: r for r in decode(bundle.payload).records}
    (read,) = (
        r
        for r in records.values()
        if r.address.kind == "expression_block_use" and r.address.position == 2
    )
    (operand,) = records[read.get("operation")].get("operands")
    assert operand.kind == "null_literal"
    loaded = load(bundle)
    assert execution.export_bundle(loaded).payload == bundle.payload
    assert bound(run(loaded)) == bound(run(query))


PAIRED_TAGS = """
source tags: Item is postgres.table("fixture.tags")

table tag_ids:
    from tags
    select:
        id

table tag_labels:
    from tags
    select:
        label

table tag_pairs:
    from tags
    select:
        id
        label

table flagged_items:
    from items
    where id not in tag_ids and exists tag_pairs and exists tag_labels
    select:
        id
        label
"""


def test_a_loaded_membership_read_rederives_its_operand_and_column_pair(tmp_path):
    """Pinned bytes whose membership operand or producer no longer pairs with
    one column of its own type are refused before any template exists, as
    compile_query refuses the written pair; a derivation that skipped the
    pairing is refused by the independent semantic verifier."""
    from pietto._project.project_completed_semantics import (
        CompiledCompletedSemanticResult,
        derive_compiled_semantics,
        verify_compiled_semantics,
    )

    bundle = execution.export_bundle(_members(let_example(tmp_path, PAIRED_TAGS)))
    description = decode(bundle.payload)
    by_address = {r.address: r for r in description.records}
    reads = {
        by_address[by_address[r.get("producer")].get("owner")].get("label"): r
        for r in description.records
        if r.address.kind == "expression_block_use"
    }
    membership = reads["tag_ids"]
    operand = by_address[by_address[membership.get("operation")].get("operands")[0]]
    (label,) = (
        p
        for p in by_address[operand.get("use")].get("ports")
        if by_address[p].get("logical")[0] == "Text"
    )

    def forged(kind, changes):
        return _replaced(description, kind, lambda r: changes.get(r.address, r))

    def swapped(other):
        """The membership read and an existence read exchange producers."""
        return forged(
            "expression_block_use",
            {
                membership.address: Record(
                    membership.address,
                    (*membership.values[:2], other.get("producer"), 0),
                ),
                other.address: Record(
                    other.address,
                    (*other.values[:2], membership.get("producer"), None),
                ),
            },
        )

    retyped = forged(
        "read", {operand.address: Record(operand.address, (label, *operand.values[1:]))}
    )
    for changed, expected in (
        # items.id NOT IN tag_ids becomes items.label NOT IN tag_ids.
        (retyped, ("PIE-R1004", "COMPILED_OPERATOR_TYPE")),
        # items.id NOT IN the one Text column of tag_labels.
        (swapped(reads["tag_labels"]), ("PIE-R1004", "COMPILED_OPERATOR_TYPE")),
        # A membership read of the two columns of tag_pairs.
        (swapped(reads["tag_pairs"]), ("PIE-R1008", "COMPILED_EXPRESSION_BLOCK_USE")),
    ):
        payload = encode(changed)
        assert refused(load, bundle, payload, expected_pin=content_pin(payload)) == (
            expected
        )

    # The producer exchange changes no scalar record, so the genuine facts on
    # the forged root form a derivation that skipped only the pairing.
    def loaded(payload):
        return loading.load_compiled(
            payload,
            expected_pin=content_pin(payload),
            accepted_producer=description.producer,
            accepted_compatibility=description.compatibility,
        )

    root = loaded(encode(swapped(reads["tag_labels"])))
    genuine = derive_compiled_semantics(loaded(bundle.payload), ())
    verify_compiled_semantics(genuine)
    with pytest.raises(CompiledError, match="^COMPILED_SEMANTIC_TYPE$"):
        verify_compiled_semantics(
            CompiledCompletedSemanticResult(
                root,
                genuine.values,
                tuple(dataclasses.replace(d, root=root) for d in genuine.declarations),
                tuple(dataclasses.replace(f, root=root) for f in genuine.facts),
                genuine.retention,
            )
        )


CROSS_TAGS = """
source tags: Item is postgres.table("fixture.tags")

table tag_ids:
    from tags
    select:
        id

table tag_count:
    from tags
    select:
        n = count()

table cross_reads:
"""
# The read kinds of the stacked slices together: (body, block use operators
# with their column, in record order).
CROSS_READS = {
    "scalar_in_in": (
        "    from items\n    where scalar tag_count.n in tag_ids\n"
        "    select:\n        id = items.id\n",
        [(("relation_membership", "in"), 0), (("scalar", "scalar"), 0)],
    ),
    "let_bodies": (
        "    let a:\n        from tags\n        select:\n            id\n"
        "    let b:\n        from tags\n        select:\n            n = count()\n"
        "    let c:\n        from tags\n        select:\n            label\n"
        "    let d:\n        from tags\n"
        "        where id in a and exists c and id <= scalar b.n\n"
        "        select:\n            id\n"
        "    from items\n    where id not in d\n    select:\n        id = items.id\n",
        [
            (("relation_membership", "in"), 0),
            (("exists", "exists"), None),
            (("scalar", "scalar"), 0),
            (("relation_membership", "not_in"), 0),
        ],
    ),
    "computed_group_key": (
        "    from items\n    let:\n        big = id > 2\n"
        "    where id in tag_ids and exists tags and id <= scalar tag_count.n\n"
        "    group by:\n        big\n    select:\n        big\n        n = count()\n",
        [
            (("relation_membership", "in"), 0),
            (("exists", "exists"), None),
            (("scalar", "scalar"), 0),
        ],
    ),
    # Typed VALUES lets, one of them with no row, read by all three kinds
    # (the contract's `tags` source is read too).
    "values": (
        "    let seed:\n        values(rid: Int not null):\n            1\n"
        "            2\n"
        "    let top:\n        values(n: Int not null):\n            5\n"
        "    let none:\n        values(rid: Int not null)\n"
        "    from items\n"
        "    where id in seed and not exists none and id <= scalar top.n\n"
        "    select:\n        id = items.id\n        tagged = exists tags\n",
        [
            (("relation_membership", "in"), 0),
            (("exists", "exists"), None),
            (("scalar", "scalar"), 0),
            (("exists", "exists"), None),
        ],
    ),
}


@pytest.mark.parametrize("policy", ("preserve", "bind-safe"))
@pytest.mark.parametrize("shape", tuple(CROSS_READS))
def test_read_kinds_combine_through_compile_bundle_and_load(
    tmp_path, unconnected, shape, policy
):
    body, expected = CROSS_READS[shape]
    query = execution.compile_query(
        let_example(tmp_path, CROSS_TAGS + body),
        module="main.pietto",
        kind="table",
        name="cross_reads",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy=policy,
    )
    bundle = execution.export_bundle(query)
    records = {r.address: r for r in decode(bundle.payload).records}
    assert [
        (records[r.get("operation")].get("operator"), r.get("column"))
        for r in sorted(
            (r for r in records.values() if r.address.kind == "expression_block_use"),
            key=lambda r: r.address.position,
        )
    ] == expected
    loaded = load(bundle)
    assert bound(run(loaded)) == bound(run(query))


# Phase70 S10: a let with capture lines reads the current row of its reader's
# FROM input; it is compiled inline at the existence read that renders it.
CAPTURE_TAGS = """
source tags: Item is postgres.table("fixture.tags")

table matched_items:
    let same_label:
        capture items
        from tags
        where tags.label == items.label and tags.id > items.id
        select:
            tag_id = id
    from items
    where exists same_label and not exists tags
    select:
        id = items.id
        label = items.label
"""


def _matched(directory, dialect="postgres"):
    return execution.compile_query(
        let_example(directory, CAPTURE_TAGS),
        module="main.pietto",
        kind="table",
        name="matched_items",
        dialect=dialect,
        emission_contract="contract.json",
    )


def _records_changed(description, targets):
    return dataclasses.replace(
        description,
        members=tuple(
            (
                name,
                tuple(
                    Record(r.address, targets[r.address]) if r.address in targets else r
                    for r in rs
                    if targets.get(r.address, ()) is not None
                ),
            )
            for name, rs in description.members
        ),
    )


def test_a_compiled_capture_names_the_outer_ports_of_its_read(tmp_path):
    query = _matched(tmp_path)
    bundle = execution.export_bundle(query)
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    assert tuple(description.compatibility[:4]) == VERSIONS == (5, 1, 5, 1)
    (capture,) = [r for r in description.records if r.address.kind == "capture_use"]
    block = records[capture.get("read")]
    assert block.address.kind == "expression_block_use"
    assert block.address.position == 0 and capture.get("ordinal") == 0
    # The reading body's own use carries the captured ports: every field of the
    # captured input, in its field order.
    reader = records[block.get("consumer")]
    (use,) = [
        r
        for r in description.records
        if r.address.kind == "use" and r.get("consumer") == reader.address
    ]
    assert all(port in use.get("ports") for port in capture.get("ports"))
    assert [records[p].get("ordinal") for p in capture.get("ports")] == [0, 1]
    reads = [
        r
        for r in description.records
        if r.address.kind == "read" and r.get("role") == "capture"
    ]
    assert len(reads) == 2 and {r.get("port") for r in reads} == set(
        capture.get("ports")
    )
    assert {r.get("use") for r in reads} == {use.address}
    # The capturing let is an inline unit without a unit position; the read of
    # the capture-free source keeps no capture record.
    inline = records[block.get("producer")]
    assert inline.address.kind == "row" and inline.get("layout")[-1] is None
    assert inline.get("layout")[:2] == (None, ()) and inline.get("layout")[3] is False
    assert sorted(
        r.get("name") for r in records.values() if r.address.kind == "source"
    ) == ["items", "tags"]
    loaded = execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    assert execution.export_bundle(loaded).payload == bundle.payload
    sql = loaded._template.artifact.rendered.sql
    assert sql == query._template.artifact.rendered.sql
    # The capture-free source stays a plain read; the capturing let renders
    # inline over the reading body's alias "s1".
    assert sql == (
        b'WITH "p0" ("c0", "c1") AS (SELECT "s1"."item_id" AS "c0", '
        b'"s1"."item_label" AS "c1" FROM "fixture"."items" AS "s1" '
        b'WHERE (EXISTS (SELECT 1 FROM (SELECT "t1"."c0" AS "c0" FROM '
        b'(SELECT "s0"."item_id" AS "c0", "s0"."item_label" AS "c1" '
        b'FROM "fixture"."tags" AS "s0" WHERE (("s0"."item_label" = '
        b'"s1"."item_label") AND ("s0"."item_id" > "s1"."item_id"))) AS "t1") '
        b'AS "e0") AND (NOT EXISTS (SELECT 1 FROM "fixture"."tags" AS "e1")))) '
        b'SELECT "t3"."c0" AS "id", "t3"."c1" AS "label" FROM "p0" AS "t3"'
    )

    first = capture.values
    port_id, port_label = first[2]
    other = next(
        r.address
        for r in description.records
        if r.address.kind == "port"
        and r.address not in use.get("ports")
        and r.get("owner") == inline.address
    )
    for forged in (
        # Ports outside the reading use, a repeated port, a capture of the
        # capture-free source read, a missing capture record.
        _records_changed(description, {capture.address: (*first[:2], (other,))}),
        _records_changed(
            description, {capture.address: (*first[:2], (port_id, port_id))}
        ),
        _records_changed(
            description,
            {
                capture.address: (
                    Address("expression_block_use", 1),
                    *first[1:],
                )
            },
        ),
        _records_changed(description, {capture.address: None}),
        # An inline unit that claims a unit position.
        _records_changed(
            description,
            {inline.address: (*inline.values[:-1], (*inline.get("layout")[:-1], 0))},
        ),
    ):
        with pytest.raises(CompiledError):
            verify_description(forged)
    # Without the source: line ordinals count from 0, and the ports are the
    # whole captured input row in port order.
    # A layout that is no layout is refused, never an internal error.
    for target, values, word in (
        (capture, (first[0], 7, first[2]), "CAPTURE_ORDINALS"),
        (capture, (*first[:2], (port_label, port_id)), "CAPTURE_PORTS"),
        (capture, (*first[:2], (port_id,)), "CAPTURE_PORTS"),
        (inline, (*inline.values[:-1], 5), "LAYOUT"),
    ):
        forged = _records_changed(description, {target.address: values})
        with pytest.raises(CompiledError, match=word):
            verify_description(forged)
        raw = encode(forged)
        assert refused(
            execution.load_bundle,
            raw,
            expected_pin=content_pin(raw),
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
        ) == ("PIE-R1008", "COMPILED_" + word)
    # Valid-looking alternatives describe another consistent capture; the export
    # verifier re-derives every capture from the live statement and refuses them.
    outcome, _ = emit_project(
        let_example(tmp_path / "live", CAPTURE_TAGS),
        "main.pietto",
        "table",
        "matched_items",
        "postgres",
        "contract.json",
        POLICIES["bind-safe"],
    )
    live = decode(build_compiled(outcome.artifact).payload)
    verify_export(live, outcome.artifact)
    (live_capture,) = [r for r in live.records if r.address.kind == "capture_use"]
    ident, label = live_capture.get("ports")
    captured = sorted(
        (
            r
            for r in live.records
            if r.address.kind == "read" and r.get("role") == "capture"
        ),
        key=lambda r: r.get("port") == ident,
    )
    names = FIELDS["read"]

    def read_values(record, **changes):
        values = dict(zip(names, record.values, strict=True)) | changes
        return tuple(values[name] for name in names)

    for targets, coherent in (
        # Both captured reads swapped to the other field: a coherent description.
        (
            {
                captured[0].address: read_values(captured[0], port=ident),
                captured[1].address: read_values(captured[1], port=label),
            },
            True,
        ),
        # A captured read relabelled as an ordinary read of the same port.
        ({captured[0].address: read_values(captured[0], role="value")}, False),
    ):
        forged = _records_changed(live, targets)
        if coherent:
            verify_description(forged)
        with pytest.raises(CompiledError):
            verify_export(forged, outcome.artifact)


@pytest.mark.parametrize(
    "operator",
    (
        ("relation_membership", "in"),
        ("relation_membership", "not_in"),
        ("scalar", "scalar"),
    ),
)
def test_a_capturing_let_read_other_than_exists_is_refused_on_load(tmp_path, operator):
    # A membership or scalar read of the single-column capturing let is a
    # valid block read elsewhere; only an existence read executes the let.
    bundle = execution.export_bundle(_matched(tmp_path))
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    (capture,) = [r for r in description.records if r.address.kind == "capture_use"]
    block = records[capture.get("read")]
    operation = records[block.get("operation")]
    (use,) = [
        r.address
        for r in description.records
        if r.address.kind == "use" and r.get("consumer") == block.get("consumer")
    ]
    value = next(
        r.address
        for r in description.records
        if r.address.kind == "read" and r.get("use") == use and r.get("role") == "value"
    )
    forged = _records_changed(
        description,
        {
            operation.address: (
                operator,
                () if operator[0] == "scalar" else (value,),
                ("Int" if operator[0] == "scalar" else "Bool", "nullable"),
                None,
            ),
            block.address: (*block.values[:3], 0),
        },
    )
    with pytest.raises(CompiledError, match="CAPTURE_USE"):
        verify_description(forged)
    raw = encode(forged)
    assert refused(load, bundle, raw, expected_pin=content_pin(raw)) == (
        "PIE-R1008",
        "COMPILED_CAPTURE_USE",
    )


JOINED_CAPTURES = (
    "query result:\n    let matched:\n        capture r\n        capture lhs\n"
    "        from rhs\n        where rhs.key == r.key and rhs.id == lhs.id\n"
    "        select:\n            id\n    from lhs\n    left join rhs as r:\n"
    "        from lhs\n        on lhs.id == r.id\n    where exists matched\n"
    "    select:\n        a = lhs.id\n        b = r.key\n"
)


def test_compiled_captures_of_a_joined_row_are_whole_bindings(tmp_path):
    import _pietto_sql_emission as probe

    item = probe.join_witness("postgres", JOINED_CAPTURES)
    (tmp_path / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (tmp_path / "main.pietto").write_text(item["source"], encoding="utf-8")
    (tmp_path / "contract.json").write_text(item["contract"], encoding="utf-8")
    query = execution.compile_query(
        tmp_path,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="postgres",
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    first, second = [r for r in description.records if r.address.kind == "capture_use"]
    (use,) = [
        r
        for r in description.records
        if r.address.kind == "use"
        and r.get("consumer") == records[first.get("read")].get("consumer")
    ]
    # The reading body reads the JOIN row (lhs.id, lhs.key, r.id, r.key):
    # line 0 captures the JOIN target r, line 1 the FROM input lhs. Only r.key
    # and lhs.id are read.
    lhs_id, lhs_key, r_id, r_key = use.get("ports")
    read = first.get("read")
    assert (first.values, second.values) == (
        (read, 0, (r_id, r_key)),
        (read, 1, (lhs_id, lhs_key)),
    )
    for targets, word in (
        ({first.address: (read, 7, (r_id, r_key))}, "CAPTURE_ORDINALS"),
        (
            {
                first.address: (read, 1, (r_id, r_key)),
                second.address: (read, 0, (lhs_id, lhs_key)),
            },
            "CAPTURE_ORDINALS",
        ),
        # An extra unread outer port, a missing unread port, swapped ports.
        ({first.address: (read, 0, (r_id, r_key, lhs_key))}, "CAPTURE_PORTS"),
        ({first.address: (read, 0, (r_key,))}, "CAPTURE_PORTS"),
        ({first.address: (read, 0, (r_key, r_id))}, "CAPTURE_PORTS"),
    ):
        forged = _records_changed(description, targets)
        with pytest.raises(CompiledError, match=word):
            verify_description(forged)
        raw = encode(forged)
        assert refused(load, bundle, raw, expected_pin=content_pin(raw)) == (
            "PIE-R1008",
            "COMPILED_" + word,
        )
    # The two lines exchanging their bindings is a coherent description; only
    # the source says which input each line names.
    swapped = _records_changed(
        description,
        {
            first.address: (read, 0, (lhs_id, lhs_key)),
            second.address: (read, 1, (r_id, r_key)),
        },
    )
    verify_description(swapped)
    outcome, _ = emit_project(
        tmp_path,
        "main.pietto",
        "query",
        "result",
        "postgres",
        "contract.json",
        POLICIES["bind-safe"],
    )
    live = decode(build_compiled(outcome.artifact).payload)
    verify_export(live, outcome.artifact)
    live_first, live_second = [
        r for r in live.records if r.address.kind == "capture_use"
    ]
    with pytest.raises(CompiledError, match="EXPORT_CAPTURE"):
        verify_export(
            _records_changed(
                live,
                {
                    live_first.address: (
                        *live_first.values[:2],
                        live_second.get("ports"),
                    ),
                    live_second.address: (
                        *live_second.values[:2],
                        live_first.get("ports"),
                    ),
                },
            ),
            outcome.artifact,
        )


def _witness(directory, body, dialect="postgres", policy="preserve"):
    import _pietto_sql_emission as probe

    literals = "bind_safe_literals" if policy == "bind-safe" else "preserve_literals"
    item = probe.join_witness(dialect, body, policy=literals)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (directory / "main.pietto").write_text(item["source"], encoding="utf-8")
    (directory / "contract.json").write_text(item["contract"], encoding="utf-8")
    return directory


def _witness_round_trip(project, dialect, policy):
    """emit-sql VERIFIED, then compile, export and load to the same statement."""
    outcome, _ = emit_project(
        project,
        "main.pietto",
        "query",
        "result",
        dialect,
        "contract.json",
        POLICIES[policy],
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None, outcome
    query = execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="result",
        dialect=dialect,
        emission_contract="contract.json",
        literal_policy=policy,
    )
    sql = query._template.artifact.rendered.sql
    assert sql == outcome.artifact.rendered.sql
    bundle = execution.export_bundle(query)
    loaded = load(bundle)
    assert loaded._template.artifact.rendered.sql == sql
    assert execution.export_bundle(loaded).payload == bundle.payload
    return query, bundle


TWO_CAPTURES = (
    "query result:\n    let m1:\n        capture lhs\n        from rhs\n"
    "        where rhs.key == lhs.key\n        select:\n            id\n"
    "    let m2:\n        capture lhs\n        from rhs\n"
    "        where rhs.id == lhs.id\n        select:\n            id\n"
    "    from lhs\n"
)
REVERSED_READS = {
    "where": "    where exists m2 and exists m1\n    select:\n        a = lhs.id\n",
    "where_select": (
        "    where exists m2\n    select:\n        a = lhs.id\n        e = exists m1\n"
    ),
    "select": (
        "    select:\n        a = lhs.id\n        f = exists m2\n        e = exists m1\n"
    ),
}


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", sorted(REVERSED_READS))
def test_capturing_lets_read_out_of_declaration_order_compile_and_load(
    tmp_path, dialect, shape
):
    # The second let is read first: its capture is ordered by the plan, not by
    # the order the reads are discovered in.
    q = '"' if dialect == "postgres" else "`"
    for policy in ("preserve", "bind-safe"):
        body = TWO_CAPTURES + REVERSED_READS[shape]
        project = _witness(tmp_path / policy, body, dialect, policy)
        query, _ = _witness_round_trip(project, dialect, policy)
        sql = query._template.artifact.rendered.sql.decode()
        assert sql.index(f"{q}order.id{q} = ") < sql.index(f"{q}key value{q} = ")


MATCHED = (
    "query result:\n    let matched:\n        capture lhs\n        from rhs\n"
    "        where rhs.id == lhs.id\n        select:\n            id\n"
)
MATCHED_JOIN = (
    "query result:\n    let matched:\n        capture r\n        capture lhs\n"
    "        from rhs\n        where rhs.key == r.key and rhs.id == lhs.id\n"
    "        select:\n            id\n    from lhs\n    left join rhs as r:\n"
    "        from lhs\n        on lhs.id == r.id\n"
)
STAGED_READS = {
    "let_where": MATCHED
    + "    from lhs\n    let:\n        k2 = lhs.id == 1\n"
    + "    where exists matched\n    select:\n        a = lhs.id\n",
    "let_select": MATCHED
    + "    from lhs\n    let:\n        k2 = lhs.id == 1\n"
    + "    select:\n        a = lhs.id\n        e = exists matched\n",
    "join_where_select": MATCHED_JOIN
    + "    where lhs.id > 0\n    select:\n        a = lhs.id\n"
    + "        e = exists matched\n",
    "join_copy_let_where": MATCHED_JOIN
    + "    let:\n        k2 = lhs.id\n    where exists matched\n"
    + "    select:\n        a = lhs.id\n",
    "window_select": MATCHED
    + "    from lhs\n    select:\n        id\n        e = exists matched\n"
    + "        rn = row_number() window:\n            order by:\n"
    + "                id\n",
}


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", sorted(STAGED_READS))
def test_a_capture_read_after_row_stages_compiles_and_loads(tmp_path, dialect, shape):
    # The reading body reads a let, WHERE or window stage of its own
    # declaration: a carried column stays in its binding, a computed or copied
    # one belongs to none.
    for policy in ("preserve", "bind-safe"):
        project = _witness(tmp_path / policy, STAGED_READS[shape], dialect, policy)
        _, bundle = _witness_round_trip(project, dialect, policy)
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    captures = [r for r in description.records if r.address.kind == "capture_use"]
    (use,) = [
        r
        for r in description.records
        if r.address.kind == "use"
        and r.get("consumer") == records[captures[0].get("read")].get("consumer")
    ]
    captured = {p for c in captures for p in c.get("ports")}
    assert len(captured) == 2 * len(captures)
    # Any other port of the reading use in a line's place, a valid port of the
    # same row, describes no binding.
    for capture in captures:
        read, ordinal, ports = capture.values
        for other in [p for p in use.get("ports") if p not in ports]:
            forged = _records_changed(
                description, {capture.address: (read, ordinal, (*ports[:-1], other))}
            )
            with pytest.raises(CompiledError, match="CAPTURE_PORTS"):
                verify_description(forged)
            raw = encode(forged)
            assert refused(load, bundle, raw, expected_pin=content_pin(raw)) == (
                "PIE-R1008",
                "COMPILED_CAPTURE_PORTS",
            )


INNER_ON = "    inner join rhs as r:\n        from lhs\n        on lhs.key == r.key\n"
NARROWED_CAPTURES = {
    "join_target": (
        "query result:\n    let matched:\n        capture r\n        from rhs\n"
        "        where rhs.id == r.key\n        select:\n            id\n"
        "            k = r.key\n    from lhs\n"
        + INNER_ON
        + "    where exists matched\n    select:\n        a = lhs.id\n"
    ),
    "from_input": (
        "query result:\n    let matched:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key\n        select:\n            id\n"
        "            k = lhs.key\n    from lhs\n"
        + INNER_ON
        + "    select:\n        a = lhs.id\n        e = exists matched\n"
    ),
    "lateral": (
        "query result:\n    let m:\n        capture lhs\n        from rhs\n"
        "        where rhs.id == lhs.key\n        select:\n            id\n"
        "            k = lhs.key\n    from lhs\n"
        + INNER_ON
        + "    cross join m as x:\n        from lhs\n    select:\n"
        "        a = lhs.id\n        b = x.k\n"
    ),
}


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", sorted(NARROWED_CAPTURES))
def test_a_captured_field_an_on_condition_narrows_stays_nullable_through_load(
    tmp_path, dialect, shape
):
    # The INNER JOIN ON narrows the read port; the captured field keeps its
    # input field's nullable type, and the loader re-derives that rule.
    for policy in ("preserve", "bind-safe"):
        project = _witness(tmp_path / policy, NARROWED_CAPTURES[shape], dialect, policy)
        _, bundle = _witness_round_trip(project, dialect, policy)
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    captured = {
        r.address
        for r in description.records
        if r.address.kind == "read" and r.get("role") == "capture"
    }
    assert {records[records[a].get("port")].get("logical") for a in captured} == {
        ("Int", "non_null")
    }
    (column,) = [
        r
        for r in description.records
        if r.address.kind == "port" and r.get("source") in captured
    ]
    assert column.get("logical") == ("Int", "nullable")
    forged = _records_changed(
        description, {column.address: (*column.values[:4], ("Int", "non_null"))}
    )
    raw = encode(forged)
    assert refused(load, bundle, raw, expected_pin=content_pin(raw)) == (
        "PIE-R1004",
        "COMPILED_PORT_TYPE",
    )


BOUND_CAPTURES = {
    "let_where_select": (
        "query result:\n    let m1:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key and rhs.id > 11\n        select:\n"
        "            id\n            k = lhs.id > 12\n    from lhs\n"
        "    where exists m1\n    select:\n        a = lhs.id\n"
    ),
    "two_lets_and_outer": (
        "query result:\n    let m1:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key and rhs.id > 11\n        select:\n"
        "            id\n            k = lhs.id > 12\n    let m2:\n"
        "        capture lhs\n        from rhs\n"
        "        where rhs.id < 13 and rhs.id == lhs.id\n        select:\n"
        "            id\n    from lhs\n"
        "    where lhs.id > 14 and exists m1 and lhs.id < 15\n    select:\n"
        "        a = lhs.id > 16\n        e = not exists m2\n        f = lhs.id > 17\n"
    ),
}


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", sorted(BOUND_CAPTURES))
def test_bind_safe_literals_of_a_capturing_let_bind_in_rendered_order(
    tmp_path, dialect, shape
):
    # An inline let's SELECT renders before its WHERE: each native placeholder
    # binds the slot of the literal written at its place in the statement.
    project = _witness(tmp_path / "bind", BOUND_CAPTURES[shape], dialect, "bind-safe")
    query, bundle = _witness_round_trip(project, dialect, "bind-safe")
    inline, _ = _witness_round_trip(
        _witness(tmp_path / "inline", BOUND_CAPTURES[shape], dialect),
        dialect,
        "preserve",
    )
    written = tuple(
        int(value)
        for value in re.findall(
            r"CAST\((\d+) AS", inline._template.artifact.rendered.sql.decode()
        )
    )
    loaded = load(bundle)
    for template in (query._template, loaded._template):
        fixed = tuple(v.value for v in template.artifact.fixed_values)
        assert sorted(fixed) == sorted(written) and fixed != written
        assert bind_values(template, tuple(zip(template.slots, fixed))).arguments == (
            written
        )
        if shape == "let_where_select":
            assert fixed == (11, 12)
            assert bind_values(
                template, tuple(zip(template.slots, (101, 202)))
            ).arguments == (202, 101)
    # Native uses naming the slots in the other order are another binding.
    description = decode(bundle.payload)
    first, second, *_ = [
        r for r in description.records if r.address.kind == "native_use"
    ]
    forged = _records_changed(
        description,
        {
            first.address: (second.get("slot"), *first.values[1:]),
            second.address: (first.get("slot"), *second.values[1:]),
        },
    )
    raw = encode(forged)
    assert refused(load, bundle, raw, expected_pin=content_pin(raw)) == (
        "PIE-R1004",
        "COMPILED_EMISSION_PARAMETER_INVENTORY",
    )


def _aliased(record, alias):
    layout = record.get("layout")
    return {record.address: (*record.values[:-1], (*layout[:2], alias, *layout[3:]))}


def test_a_loaded_inline_let_alias_names_no_relation_of_its_reader(tmp_path):
    # A correlated reference names its reading body's alias: an inline let's
    # unit named like it (or the reverse) would read the let's own row.
    bundle = execution.export_bundle(_matched(tmp_path / "exists"))
    description = decode(bundle.payload)
    units = [r for r in description.records if "layout" in FIELDS[r.address.kind]]
    scan = next(r for r in units if r.get("layout")[-1] is None)
    reader = next(r for r in units if r.get("layout")[-1] == 0)
    assert (scan.get("layout")[2], reader.get("layout")[2]) == ("s0", "s1")
    joined = execution.export_bundle(
        execution.compile_query(
            _witness(tmp_path / "join", JOINED_CAPTURES),
            module="main.pietto",
            kind="query",
            name="result",
            dialect="postgres",
            emission_contract="contract.json",
        )
    )
    joined_description = decode(joined.payload)
    (join,) = [r for r in joined_description.records if r.address.kind == "join"]
    inline = next(
        r.get("layout")[2]
        for r in joined_description.records
        if "layout" in FIELDS[r.address.kind] and r.get("layout")[-1] is None
    )
    assert join.get("layout")[2] == ("m0", "m1")
    joined_records = {r.address: r for r in joined_description.records}
    (block,) = [
        r
        for r in joined_description.records
        if r.address.kind == "expression_block_use"
    ]
    # The let's SELECT reads its WHERE body; both read the reader's row.
    projection = joined_records[block.get("producer")]
    joined_reader = joined_records[block.get("consumer")].get("layout")[2]
    for source, described, targets in (
        (bundle, description, _aliased(scan, "s1")),
        (bundle, description, _aliased(reader, "s0")),
        (bundle, description, _aliased(scan, "e0")),
        (bundle, description, _aliased(reader, ("s1",))),
        (joined, joined_description, _aliased(projection, joined_reader)),
        (joined, joined_description, _aliased(projection, inline)),
        (joined, joined_description, _aliased(join, ("m0", "m0"))),
        (joined, joined_description, _aliased(join, "m0")),
        (joined, joined_description, _aliased(join, ("m0",))),
    ):
        forged = _records_changed(described, targets)
        with pytest.raises(CompiledError, match="ALIASES"):
            verify_description(forged)
        raw = encode(forged)
        assert refused(load, source, raw, expected_pin=content_pin(raw)) == (
            "PIE-R1008",
            "COMPILED_ALIASES",
        )
    # A fresh name, or the name of a relation in another unit's scope,
    # renames one relation of the same statement.
    raw = encode(_records_changed(description, _aliased(scan, "zz")))
    renamed = load(bundle, raw, expected_pin=content_pin(raw))
    assert b'AS "zz"' in renamed._template.artifact.rendered.sql
    raw = encode(_records_changed(joined_description, _aliased(join, ("m0", inline))))
    renamed = load(joined, raw, expected_pin=content_pin(raw))
    assert f'LEFT JOIN "public"."phase66 rhs é" AS "{inline}"'.encode() in (
        renamed._template.artifact.rendered.sql
    )


DEFERRED_CAPTURES = {
    "set_let": (
        "query result:\n    let codes:\n        union all:\n            from lhs\n"
        "            from rhs\n    let m:\n        capture codes\n"
        "        from rhs\n        where rhs.key == codes.key\n        select:\n"
        "            id\n    from codes\n    where exists m\n    select:\n"
        "        a = codes.id\n"
    ),
    "join_table": (
        "table codes:\n    from lhs\n    inner join rhs as r:\n        from lhs\n"
        "        on lhs.id == r.id\n    select:\n        id = lhs.id\n"
        "        key = r.key\nquery result:\n    let m:\n        capture codes\n"
        "        from rhs\n        where rhs.key == codes.key\n        select:\n"
        "            id\n    from codes\n    where exists m\n    select:\n"
        "        a = codes.id\n"
    ),
}


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", sorted(DEFERRED_CAPTURES))
def test_a_capture_of_columns_known_only_after_completion_is_refused(
    tmp_path, dialect, shape
):
    # The semantic check refuses the field read; emission and compilation
    # stop on it instead of rejecting their own input.
    project = _witness(tmp_path, DEFERRED_CAPTURES[shape], dialect)
    lines = (project / "main.pietto").read_text(encoding="utf-8").splitlines()
    expected = [
        (
            "PIE-S2369",
            "Captured field codes.key is not yet available: the columns of codes "
            "are not known before completion.",
            lines.index("        where rhs.key == codes.key") + 1,
            26,
        )
    ]
    outcome, _ = emit_project(
        project,
        "main.pietto",
        "query",
        "result",
        dialect,
        "contract.json",
        POLICIES["preserve"],
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    with pytest.raises(execution.CompileRejected) as error:
        execution.compile_query(
            project,
            module="main.pietto",
            kind="query",
            name="result",
            dialect=dialect,
            emission_contract="contract.json",
        )
    document = json.loads(error.value.emission)
    assert error.value.status == document["status"] == "BLOCKED"
    assert [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in document["diagnostics"]
    ] == expected


def test_each_route_prepares_a_correlated_read_with_its_inner_source(
    tmp_path, unconnected
):
    query = _matched(tmp_path)
    for route in ("postgres_rows", "postgres_adbc"):
        handle = run(query, route=route)
        assert handle.route == route and handle.outcome.end == "NOT_STARTED"
        assert [
            s.name for s in handle._owner.request.binding.artifact.request.sources
        ] == ["items", "tags"]
    import _pietto_sql_emission as probe

    item = probe.join_witness(
        "mysql",
        # Two lets capture the same row input and are read in one predicate.
        "query result:\n    let matched:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key\n        select:\n            id\n"
        "    let other:\n        capture lhs\n        from rhs\n"
        "        where rhs.id == lhs.id\n        select:\n            id\n"
        "    from lhs\n    where exists matched or not exists other\n"
        "    select:\n        a = lhs.id\n",
    )
    root = tmp_path / "mysql"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (root / "main.pietto").write_text(item["source"], encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    mysql_query = execution.compile_query(
        root,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="mysql",
        emission_contract="contract.json",
    )
    reloaded = execution.export_bundle(mysql_query)
    assert (
        execution.export_bundle(
            execution.load_bundle(
                reloaded.payload,
                expected_pin=reloaded.pin,
                accepted_producer=reloaded.producer,
                accepted_compatibility=reloaded.compatibility,
            )
        ).payload
        == reloaded.payload
    )
    handle = execution.execute(
        mysql_query,
        route="mysql_rows",
        access=execution.MySQLAccess(
            "127.0.0.1",
            3306,
            "phase66",
            "pietto_query",
            PASSWORD,
            "/explicit/ca.pem",
            "pietto_query",
        ),
        premise=execution.MySQLDeploymentPremise(schemas=("phase66",)),
    )
    assert handle.route == "mysql_rows" and handle.outcome.end == "NOT_STARTED"
    assert [s.name for s in handle._owner.request.artifact.request.sources] == [
        "phase66 lhs é",
        "phase66 rhs é",
    ]


TWINS = """
table twins:
    let others:
        from items
        select:
            id
            label
    let same_label:
        capture items
        from others
        where others.label == items.label and others.id != items.id
        select:
            id
    from items
    where exists same_label
    select:
        id = items.id
"""


def test_a_self_correlation_reads_its_input_through_another_let(tmp_path):
    # The documented rename: the let reads `items` through `others`, so it may
    # capture `items`; the other declaration of the module still compiles alone.
    project = api.write_example(tmp_path)
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + TWINS, encoding="utf-8")
    kinds = {}
    for name in ("active_items", "twins"):
        query = execution.compile_query(
            project,
            module="main.pietto",
            kind="table",
            name=name,
            dialect="postgres",
            emission_contract="contract.json",
        )
        bundle = execution.export_bundle(query)
        loaded = execution.load_bundle(
            bundle.payload,
            expected_pin=bundle.pin,
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
        )
        assert execution.export_bundle(loaded).payload == bundle.payload
        kinds[name] = [
            r.address.kind
            for r in decode(bundle.payload).records
            if r.address.kind == "capture_use"
        ]
    assert kinds == {"active_items": [], "twins": ["capture_use"]}


# An entry query with header parameters may read a table whose let has capture
# lines (the parameters themselves stay unavailable beside lets): its inline
# literal binds first, then the one parameter PostgreSQL reads twice as $2.
PARAMETER_OVER_CAPTURE = """
source tags: Item is postgres.table("fixture.tags")

table matched_tags:
    let same_label:
        capture items
        from tags
        where tags.label == items.label and tags.id > 5
        select:
            tag_id = id
    from items
    where exists same_label
    select:
        id = items.id
        label = items.label

query picked_items(cut: Int not null):
    from matched_tags
    where id > cut and id != cut
    select:
        id
"""


def test_a_parameter_after_a_capturing_let_binds_in_text_order(tmp_path, unconnected):
    query = execution.compile_query(
        let_example(tmp_path, PARAMETER_OVER_CAPTURE),
        module="main.pietto",
        kind="query",
        name="picked_items",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="bind-safe",
    )
    assert query.parameters == (("cut", "Int", False),)
    sql, arguments = bound(run(query, parameters={"cut": 7}))
    assert arguments == (5, 7)
    assert sql.count(b"$2") == 2
    assert sql.index(b"$1") < sql.index(b'AS "e0"') < sql.index(b"$2")


# Lets are reused and read forward (Phase70 S05): the capturing let reads a let
# written after it, which reads a third let the body also reads.
CAPTURE_CHAIN = """
source tags: Item is postgres.table("fixture.tags")

table chained_items:
    let same_label:
        capture items
        from others
        where others.label == items.label and others.id > 2
        select:
            tag_id = id
    let others:
        from base
        where id > 1
        select:
            id
            label
    let base:
        from tags
        select:
            id
            label
    from items
    where exists same_label and exists base and items.id > 3
    select:
        id = items.id
"""


def test_a_capturing_let_over_a_forward_let_chain_binds_slots_in_text_order(
    tmp_path, unconnected
):
    query = execution.compile_query(
        let_example(tmp_path, CAPTURE_CHAIN),
        module="main.pietto",
        kind="table",
        name="chained_items",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="bind-safe",
    )
    bundle = execution.export_bundle(query)
    loaded = load(bundle)
    assert execution.export_bundle(loaded).payload == bundle.payload
    sql, arguments = bound(run(query))
    # $1 is the forward let's literal, $2 the inline let's, $3 the body's own.
    assert arguments == (1, 2, 3)
    assert sql.index(b"$1") < sql.index(b"EXISTS (SELECT 1 FROM (SELECT ")
    assert sql.index(b"$2") < sql.index(b'AS "e0"') < sql.index(b"$3")
    assert bound(run(loaded, values=(4, 5, 6))) == (sql, (4, 5, 6))


# Phase70 S12: a JOIN reads a let with capture lines LATERAL; the let compiles
# inline at that JOIN's right input, correlated to the JOIN's own left input.
LATERAL_TAGS = """
source tags: Item is postgres.table("fixture.tags")

table lateral_items:
    let later_tags:
        capture items
        from tags
        where tags.label == items.label and tags.id > items.id
        select:
            tag_id = id
    from items
    cross join later_tags as t:
        from items
    select:
        id = items.id
        tag_id = t.tag_id
"""
LATERAL_SQL = (
    b'WITH "p0" ("c0", "c1", "c2") AS (SELECT "m0"."item_id" AS "c0", '
    b'"m0"."item_label" AS "c1", "m1"."c0" AS "c2" FROM "fixture"."items" AS "m0" '
    b'CROSS JOIN LATERAL (SELECT "t1"."c0" AS "c0" FROM (SELECT "s0"."item_id" '
    b'AS "c0", "s0"."item_label" AS "c1" FROM "fixture"."tags" AS "s0" WHERE '
    b'(("s0"."item_label" = "m0"."item_label") AND ("s0"."item_id" > '
    b'"m0"."item_id"))) AS "t1") AS "m1") SELECT "t0"."c0" AS "id", '
    b'"t0"."c2" AS "tag_id" FROM "p0" AS "t0"'
)


def _lateral_items(directory):
    return execution.compile_query(
        let_example(directory, LATERAL_TAGS),
        module="main.pietto",
        kind="table",
        name="lateral_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


def _lateral_records(description, targets):
    """`description` with record values replaced (or the record dropped: None)."""
    return dataclasses.replace(
        description,
        members=tuple(
            (
                name,
                tuple(
                    Record(r.address, targets[r.address]) if r.address in targets else r
                    for r in records
                    if targets.get(r.address, ()) is not None
                ),
            )
            for name, records in description.members
        ),
    )


def test_a_compiled_lateral_capture_names_the_join_left_ports(tmp_path):
    query = _lateral_items(tmp_path)
    bundle = execution.export_bundle(query)
    description = decode(bundle.payload)
    records = {r.address: r for r in description.records}
    (capture,) = [r for r in description.records if r.address.kind == "capture_use"]
    right = records[capture.get("read")]
    join = records[right.get("consumer")]
    assert (right.address.kind, right.get("ordinal"), join.address.kind) == (
        "use",
        1,
        "join",
    )
    (left,) = [
        r
        for r in description.records
        if r.address.kind == "use"
        and r.get("consumer") == join.address
        and r.get("ordinal") == 0
    ]
    # The captured ports are the JOIN's left input ports, in field order.
    assert capture.get("ordinal") == 0
    assert [left.get("ports").index(p) for p in capture.get("ports")] == [0, 1]
    reads = [
        r
        for r in description.records
        if r.address.kind == "read" and r.get("role") == "capture"
    ]
    assert len(reads) == 2 and {r.get("use") for r in reads} == {left.address}
    inline = records[right.get("producer")]
    assert inline.address.kind == "row" and inline.get("layout")[-1] is None
    assert inline.get("layout")[:2] == (None, ()) and inline.get("layout")[3] is False
    assert sorted(
        r.get("name") for r in records.values() if r.address.kind == "source"
    ) == ["items", "tags"]
    loaded = execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    assert execution.export_bundle(loaded).payload == bundle.payload
    assert loaded._template.artifact.rendered.sql == LATERAL_SQL
    assert query._template.artifact.rendered.sql == LATERAL_SQL

    inline_port = next(
        r.address
        for r in description.records
        if r.address.kind == "port" and r.get("owner") == inline.address
    )
    first = capture.values
    for forged in (
        # A port outside the left use, the left use as the read, a missing
        # capture record and an inline unit that claims a unit position.
        _lateral_records(description, {capture.address: (*first[:2], (inline_port,))}),
        _lateral_records(description, {capture.address: (left.address, *first[1:])}),
        _lateral_records(description, {capture.address: None}),
        _lateral_records(
            description,
            {inline.address: (*inline.values[:-1], (*inline.get("layout")[:-1], 0))},
        ),
    ):
        with pytest.raises(CompiledError):
            verify_description(forged)
    # The ports in the other order describe another consistent capture; the
    # export verifier re-derives it from the live statement and refuses it.
    outcome, _ = emit_project(
        let_example(tmp_path / "live", LATERAL_TAGS),
        "main.pietto",
        "table",
        "lateral_items",
        "postgres",
        "contract.json",
        POLICIES["bind-safe"],
    )
    live = decode(build_compiled(outcome.artifact).payload)
    verify_export(live, outcome.artifact)
    (live_capture,) = [r for r in live.records if r.address.kind == "capture_use"]
    ident, label = live_capture.get("ports")
    # The ports in the other order are no row binding of the left input.
    forged = _lateral_records(
        live, {live_capture.address: (*live_capture.values[:2], (label, ident))}
    )
    with pytest.raises(CompiledError, match="CAPTURE_PORTS"):
        verify_description(forged)
    # The two captured reads swapped to each other's field are a coherent
    # description; the export verifier re-derives them from the live statement.
    first_read, second_read = [
        r
        for r in live.records
        if r.address.kind == "read" and r.get("role") == "capture"
    ]
    forged = _lateral_records(
        live,
        {
            first_read.address: (second_read.get("port"), *first_read.values[1:]),
            second_read.address: (first_read.get("port"), *second_read.values[1:]),
        },
    )
    verify_description(forged)
    with pytest.raises(CompiledError):
        verify_export(forged, outcome.artifact)


@pytest.mark.parametrize("top_k", (False, True))
def test_each_route_prepares_a_lateral_join_with_its_inner_source(
    tmp_path, unconnected, top_k
):
    # A let ending in ORDER BY and LIMIT (a top-k per left row) prepares alike.
    order = "        order by:\n            id desc\n        limit 2\n" if top_k else ""
    query = execution.compile_query(
        let_example(
            tmp_path,
            LATERAL_TAGS.replace(
                "            tag_id = id\n", "            tag_id = id\n" + order
            ),
        ),
        module="main.pietto",
        kind="table",
        name="lateral_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    assert (b" LIMIT 2) AS " in query._template.artifact.rendered.sql) is top_k
    for route in ("postgres_rows", "postgres_adbc"):
        handle = run(query, route=route)
        assert handle.route == route and handle.outcome.end == "NOT_STARTED"
        assert [
            s.name for s in handle._owner.request.binding.artifact.request.sources
        ] == ["items", "tags"]
    import _pietto_sql_emission as probe

    item = probe.join_witness(
        "mysql",
        "query result:\n    let m:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key\n        select:\n            id\n"
        + order
        + "    from lhs\n    inner join m as m1:\n        from lhs\n        on true\n"
        "    select:\n        a = lhs.id\n        b = m1.id\n",
    )
    root = tmp_path / "mysql"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (root / "main.pietto").write_text(item["source"], encoding="utf-8")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")
    mysql_query = execution.compile_query(
        root,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="mysql",
        emission_contract="contract.json",
    )
    exported = execution.export_bundle(mysql_query)
    loaded = execution.load_bundle(
        exported.payload,
        expected_pin=exported.pin,
        accepted_producer=exported.producer,
        accepted_compatibility=exported.compatibility,
    )
    assert execution.export_bundle(loaded).payload == exported.payload
    handle = execution.execute(
        mysql_query,
        route="mysql_rows",
        access=execution.MySQLAccess(
            "127.0.0.1",
            3306,
            "phase66",
            "pietto_query",
            PASSWORD,
            "/explicit/ca.pem",
            "pietto_query",
        ),
        premise=execution.MySQLDeploymentPremise(schemas=("phase66",)),
    )
    assert handle.route == "mysql_rows" and handle.outcome.end == "NOT_STARTED"
    assert [s.name for s in handle._owner.request.artifact.request.sources] == [
        "phase66 lhs é",
        "phase66 rhs é",
    ]


# An entry query with header parameters may read a table that joins a let with
# capture lines LATERAL and reads another by exists: the lateral let's literal
# binds first, then the exists let's, then the one parameter read twice as $3.
PARAMETER_OVER_LATERAL = """
source tags: Item is postgres.table("fixture.tags")

table later_tags:
    let later:
        capture items
        from tags
        where tags.id > items.id and tags.id > 6
        select:
            later_id = id
    let same_label:
        capture items
        from tags
        where tags.label == items.label and tags.id > 5
        select:
            tag_id = id
    from items
    cross join later as l:
        from items
    where exists same_label
    select:
        id = items.id
        later_id = l.later_id

query picked_later(cut: Int not null):
    from later_tags
    where id > cut and later_id != cut
    select:
        id
"""


def test_a_parameter_after_a_lateral_let_binds_in_text_order(tmp_path, unconnected):
    query = execution.compile_query(
        let_example(tmp_path, PARAMETER_OVER_LATERAL),
        module="main.pietto",
        kind="query",
        name="picked_later",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="bind-safe",
    )
    assert query.parameters == (("cut", "Int", False),)
    sql, arguments = bound(run(query, parameters={"cut": 7}))
    assert arguments == (6, 5, 7)
    assert sql.count(b"$3") == 2
    assert sql.index(b"$1") < sql.index(b'AS "m1"') < sql.index(b"$2")
    assert sql.index(b"$2") < sql.index(b'AS "e0"') < sql.index(b"$3")


# Lets are reused and read forward (Phase70 S05): the LATERAL right input reads
# a let written after it, which reads a third let the body also reads.
LATERAL_CHAIN = CAPTURE_CHAIN.replace("chained_items", "lateral_chain").replace(
    "    where exists same_label and exists base and items.id > 3\n",
    "    cross join same_label as t:\n        from items\n"
    "    where exists base and items.id > 3\n",
)


def test_a_lateral_let_over_a_forward_let_chain_binds_slots_in_text_order(
    tmp_path, unconnected
):
    query = execution.compile_query(
        let_example(tmp_path, LATERAL_CHAIN),
        module="main.pietto",
        kind="table",
        name="lateral_chain",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="bind-safe",
    )
    bundle = execution.export_bundle(query)
    loaded = load(bundle)
    assert execution.export_bundle(loaded).payload == bundle.payload
    sql, arguments = bound(run(query))
    # $1 is the forward let's literal, $2 the lateral let's, $3 the body's own.
    assert arguments == (1, 2, 3)
    assert sql.index(b"$1") < sql.index(b"CROSS JOIN LATERAL (")
    assert sql.index(b"$2") < sql.index(b'AS "m1"') < sql.index(b"$3")
    assert bound(run(loaded, values=(4, 5, 6))) == (sql, (4, 5, 6))
