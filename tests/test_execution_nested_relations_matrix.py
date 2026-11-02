"""The public-entry matrix of collection-carrying queries, its laws and the
carrier bounds of sibling collections.

These mechanism cells replace exactly one name, the collection predicate,
and each has an unseamed flat control driven in the same window. Real nested
producer/consumer behavior belongs to the installed native campaign. Accesses point
at a loopback listener of the test function; observers forward to the real
workspace opener and sink resolver. Expected words are hand-written.
"""

from __future__ import annotations

from dataclasses import replace
import itertools
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import types

import pytest

import _pietto_execution_api as api
import _pietto_execution_nested_matrix as m
import pietto.execution as execution

pytestmark = pytest.mark.ci_workload("general-runtime")

MYSQL_BODY = "query result:\n    from lhs\n    select:\n        id\n"


def _bundle(query):
    bundle = execution.export_bundle(query)
    return execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )


def _origins(query):
    return {"live": query, "bundle": _bundle(query)}


@pytest.fixture(scope="module")
def postgres(tmp_path_factory):
    return _origins(
        execution.compile_query(
            api.write_example(tmp_path_factory.mktemp("matrix-postgres")),
            module="main.pietto",
            kind="table",
            name="active_items",
            dialect="postgres",
            emission_contract="contract.json",
        )
    )


@pytest.fixture(scope="module")
def mysql(tmp_path_factory):
    project = tmp_path_factory.mktemp("matrix-mysql") / "project"
    return _origins(
        execution.compile_query(
            api.write_join_witness(project, "mysql", MYSQL_BODY),
            module="main.pietto",
            kind="query",
            name="result",
            dialect="mysql",
            emission_contract="contract.json",
        )
    )


def _control(dialect, entry, route, origin):
    """The flat control's word and its workspace and sink observations."""
    if (dialect == "mysql") != (route == "mysql_rows"):
        return ("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE", 0, 0)
    if entry == "execute":
        return ("ADMIT", "ResultHandle", 0, 0)
    if entry == "relay_live":
        return ("PIE-R1001", "REFERENCE_SINK_ROOT", 0, 1)
    if entry != "save" and origin == "bundle":
        return ("PIE-R1004", "PUBLIC_R2_LIVE_QUERY", 0, 0)
    return ("PIE-R1009", "WORKSPACE_OBJECT", 1, 0)


def test_public_entries_are_closed_into_shape_classes():
    assert m.unclassified(execution) == ()
    names = {name: getattr(execution, name) for name in execution.__all__}

    def smuggle(query):
        return query

    def inspect_job(workspace, query):
        return query

    grown = types.SimpleNamespace(
        **names, smuggle=smuggle, __all__=[*execution.__all__, "smuggle"]
    )
    reshaped = types.SimpleNamespace(
        **{**names, "inspect_job": inspect_job}, __all__=execution.__all__
    )
    shrunk = types.SimpleNamespace(
        **names, __all__=[n for n in execution.__all__ if n != "save"]
    )
    assert m.unclassified(grown) == ("smuggle",)
    assert m.unclassified(reshaped) == ("inspect_job",)
    assert m.unclassified(shrunk) == ("save",)


@pytest.mark.parametrize("origin", ("live", "bundle"))
@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_a_collection_query_still_exports_its_bundle(request, dialect, origin):
    query = request.getfixturevalue(dialect)[origin]
    for closure in m.CLOSURES:
        with m.seam(closure):
            assert type(execution.export_bundle(query)) is execution.QueryBundle


@pytest.mark.parametrize("origin", ("live", "bundle"))
@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_every_public_query_entry_meets_its_cell_before_any_effect(
    request, tmp_path, dialect, origin
):
    query = request.getfixturevalue(dialect)[origin]
    cells = [(dialect, e, r, origin) for r in m.ROUTES for e in m.ENTRIES]
    with m.Witness(tmp_path) as witness:
        for _, entry, route, _ in cells:
            for closure in (None, *m.CLOSURES):
                witness.drive(query, entry, route, subject="q", closure=closure)
        facts = witness.settle()
    driven = dict(zip(cells, itertools.batched(facts, 1 + len(m.CLOSURES))))
    assert {
        cell: (*control.word, control.workspaces, control.sinks)
        for cell, (control, *_) in driven.items()
    } == {cell: _control(*cell) for cell in cells}
    wrong = {}
    for cell, (control, *seamed) in driven.items():
        kind, *word = m.EXPECTED[cell]
        words = {control.word} if kind == "T" else {tuple(word)}
        if kind == "T":
            assert all(f.effects == control.effects for f in seamed)
        if [(f.closure, f.word in words) for f in seamed] != [
            (closure, True) for closure in m.CLOSURES
        ]:
            wrong[cell] = [(f.closure, f.word) for f in seamed]
    assert wrong == {}
    quiet = (0, False, False)
    assert [f for f in facts if (f.connects, f.files, f.threads) != quiet] == []
    assert m.laws(facts) == ()


def test_precedence_of_a_missing_premise_and_collection_words(postgres, tmp_path):
    query = postgres["live"]
    with m.Witness(tmp_path) as witness:
        for entry, route in (
            ("execute", "postgres_adbc"),
            ("save", "postgres_adbc"),
            ("save", "postgres_rows"),
        ):
            for closure in (None, frozenset({"collect"})):
                witness.drive(query, entry, route, closure=closure, premise=False)
        facts = witness.settle()
    assert {fact.word for fact in facts} == {("PIE-R1001", "PUBLIC_PREMISE_REQUIRED")}
    assert m.laws(facts, expected={}) == ()
    # A precedence that let the collection word win is reported.
    swapped = [
        replace(f, code=ROUTE[0], detail=ROUTE[1], again=(*ROUTE, 0, 0))
        if f.closure and f.route == "postgres_adbc"
        else f
        for f in facts
    ]
    assert "L7" in m.laws(swapped, expected={})


def test_the_effect_witnesses_see_what_they_witness(postgres, tmp_path, monkeypatch):
    query = postgres["live"]
    with m.Witness(tmp_path) as witness:
        raw = socket.create_connection(("127.0.0.1", witness.port))
        assert witness.accepted() == 1
        raw.close()
        release = threading.Event()
        started = witness.observe(
            lambda: threading.Thread(target=release.wait, daemon=True).start()
        )
        release.set()
        assert started["threads"] and not started["files"]
        made = witness.observe(lambda: (tmp_path / "made").write_text("x"))
        assert made["files"] and made["code"] == "ADMIT"
        # A shared connection is retained without inventing a caller.
        real = m.public_call

        def connecting(query, entry, route, **keywords):
            call = real(query, entry, route, **keywords)
            if entry != "save":
                return call

            def connect():
                socket.create_connection(("127.0.0.1", witness.port)).close()
                return call()

            return connect

        monkeypatch.setattr(m, "public_call", connecting)
        for entry in ("execute", "save", "relay_live"):
            witness.drive(query, entry, "postgres_adbc", closure=frozenset({"collect"}))
        facts = witness.settle()
    assert [fact.connects for fact in facts] == [0, 0, 0]
    assert [fact.shared_connects for fact in facts] == [2, 2, 2]
    assert m.laws(facts) == ("L1",)


def test_shared_window_connections_are_not_dropped(postgres, tmp_path, monkeypatch):
    query = postgres["live"]
    with m.Witness(tmp_path) as witness:
        real = m.public_call
        once, calls = False, 0

        def connecting_once(query, entry, route, **keywords):
            call = real(query, entry, route, **keywords)

            def connect():
                nonlocal once, calls
                calls += 1
                if entry == "save" and not once:
                    once = True
                    (tmp_path / "first-window-effect").write_text("retained")
                    socket.create_connection(("127.0.0.1", witness.port)).close()
                return call()

            return connect

        monkeypatch.setattr(m, "public_call", connecting_once)
        for entry in ("execute", "save", "relay_live"):
            witness.drive(query, entry, "postgres_adbc", closure=frozenset({"collect"}))
        facts = witness.settle()
    assert [fact.connects for fact in facts] == [0, 0, 0]
    assert [fact.shared_connects for fact in facts] == [1, 1, 1]
    assert calls == 6
    assert [fact.files for fact in facts] == [False, True, False]
    assert m.laws(facts) == ("L1",)


def _fact(entry, route, origin, closure, code, detail, workspaces=0, sinks=0, **kw):
    return m.Fact(
        "q",
        "postgres",
        origin,
        entry,
        route,
        closure,
        code,
        detail,
        again=(code, detail, workspaces, sinks),
        workspaces=workspaces,
        sinks=sinks,
        **kw,
    )


def _cell(entry, route, origin, control, word):
    return [_fact(entry, route, origin, m.FLAT, *control)] + [
        _fact(entry, route, origin, closure, *word) for closure in m.CLOSURES
    ]


ROUTE = ("PIE-R1003", "COLLECTION_ROUTE")
ENTRY = ("PIE-R1004", "COLLECTION_ENTRY")
LIVE_QUERY = ("PIE-R1004", "PUBLIC_R2_LIVE_QUERY")
ADMIT = ("ADMIT", "ResultHandle")
OPENED = ("PIE-R1009", "WORKSPACE_OBJECT", 1)
BASELINE = (
    *_cell("execute", "postgres_rows", "live", ADMIT, ADMIT),
    *_cell("execute", "postgres_adbc", "live", ADMIT, ROUTE),
    *_cell("save", "postgres_rows", "live", OPENED, OPENED),
    *_cell("save", "postgres_adbc", "live", OPENED, ROUTE),
    *_cell("recover", "postgres_rows", "bundle", LIVE_QUERY, LIVE_QUERY),
    *_cell(
        "relay_live",
        "postgres_rows",
        "live",
        ("PIE-R1001", "REFERENCE_SINK_ROOT", 0, 1),
        ENTRY,
    ),
)
COLLECT = m.CLOSURES[0]


def _set(entry, route, closure=COLLECT, **changes):
    """BASELINE with one fact changed; its second run follows unless given."""
    facts = []
    for f in BASELINE:
        if (f.entry, f.route, f.closure) == (entry, route, closure):
            f = replace(f, **changes)
            if "again" not in changes:
                f = replace(f, again=(f.code, f.detail, f.workspaces, f.sinks))
        facts.append(f)
    return facts


def _without_controls():
    return [f for f in BASELINE if f.closure]


def _leaves(*words):
    return [
        _fact("save", "postgres_rows", "live", COLLECT, *word, leaf=leaf)
        for leaf, word in zip(("Int", "Float"), words)
    ]


SAVE_FOLLOWS = dict(code="PIE-R1009", detail="WORKSPACE_OBJECT", workspaces=1)
CORRUPTIONS = {
    # Each law reports its own corruption ...
    "L1 connection": (lambda: _set("save", "postgres_adbc", connects=1), "L1", True),
    "L2 admitted beside an admitted control": (
        lambda: _set("execute", "postgres_adbc", code="ADMIT", detail="ResultHandle"),
        "L2",
        True,
    ),
    "L3 unnest differs": (
        lambda: _set(
            "save",
            "postgres_adbc",
            m.CLOSURES[1],
            code="PIE-R1004",
            detail="COLLECTION_ENTRY",
        ),
        "L3",
        True,
    ),
    "L4 permanent internal error": (
        lambda: _set(
            "relay_live", "postgres_rows", code="PIE-R1999", detail="INTERNAL"
        ),
        "L4",
        True,
    ),
    "L4 permanent admitted": (
        lambda: _set("save", "postgres_adbc", code="ADMIT", detail="SaveReply"),
        "L4",
        True,
    ),
    "L5 obsolete collection refusal": (
        lambda: _set(
            "save",
            "postgres_rows",
            code="PIE-R1004",
            detail="COLLECTION_ENTRY",
            workspaces=0,
        ),
        "L5",
        True,
    ),
    "L6 chained": (lambda: _set("save", "postgres_adbc", chained=True), "L6", True),
    "L6 sentinel": (lambda: _set("save", "postgres_adbc", leaked=True), "L6", True),
    "L6 second run differs": (
        lambda: _set("save", "postgres_adbc", again=(*ENTRY, 0, 0)),
        "L6",
        True,
    ),
    "L7 swapped": (
        lambda: _set(
            "recover", "postgres_rows", code="PIE-R1004", detail="PUBLIC_R2_COLLECTION"
        ),
        "L7",
        True,
    ),
    "L8 leaves differ": (lambda: _leaves(ENTRY, ROUTE), "L8", True),
    # ... and none applies when its premise is false.
    "L1 admitted with a connection": (
        lambda: _set("execute", "postgres_rows", connects=1),
        "L1",
        False,
    ),
    "L5 transitional follows its control": (
        lambda: _follow_all("save", "postgres_rows"),
        "L5",
        False,
    ),
    "L2 without a control": (
        lambda: [
            replace(
                f, code="PIE-R1002", detail="OTHER", again=("PIE-R1002", "OTHER", 0, 0)
            )
            if f.entry == "execute" and f.route == "postgres_adbc"
            else f
            for f in _without_controls()
        ],
        "L2",
        False,
    ),
    "L3 leaf word": (
        lambda: _set(
            "save",
            "postgres_adbc",
            m.CLOSURES[1],
            code="PIE-R1004",
            detail="COLLECTION_LEAF",
        ),
        "L3",
        False,
    ),
    "L4 transitional": (lambda: _follow_all("save", "postgres_rows"), "L4", False),
    "L6 admitted detail": (lambda: list(BASELINE), "L6", False),
    "L7 one applicable refusal": (
        lambda: _follow_all("save", "postgres_rows"),
        "L7",
        False,
    ),
    "L8 one leaf": (lambda: _leaves(ENTRY), "L8", False),
    "L8 leaf word": (
        lambda: _leaves(ENTRY, ("PIE-R1004", "COLLECTION_LEAF")),
        "L8",
        False,
    ),
}


def _follow_all(entry, route):
    """Every closure of the cell stops where its flat control stops."""
    facts = []
    for f in BASELINE:
        if f.closure and (f.entry, f.route) == (entry, route):
            f = replace(f, **SAVE_FOLLOWS, again=(*OPENED[:2], 1, 0))
        facts.append(f)
    return facts


def test_the_baseline_facts_keep_every_law():
    assert m.laws(BASELINE) == ()
    assert m.laws(_follow_all("save", "postgres_rows")) == ()


@pytest.mark.parametrize("name", CORRUPTIONS)
def test_each_law_reports_its_corruption_and_only_under_its_premise(name):
    corrupt, law, reported = CORRUPTIONS[name]
    assert (law in m.laws(corrupt())) is reported


def test_importing_the_matrix_helper_loads_no_driver(tmp_path):
    tests = Path(__file__).resolve().parent
    source = Path(execution.__file__).resolve().parents[2]
    code = (
        "import sys; import _pietto_execution_nested_matrix as m; "
        "print(sorted(n for n in sys.modules if n.startswith(m.DRIVERS)))"
    )
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(tests), str(source))))
    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert (done.returncode, done.stdout, done.stderr) == (0, "[]\n", "")
