"""The two-database differential's rows, SQL, order promise and comparison.

The campaign of tests/_pietto_harness_generated_forms_differential.py runs only
explicitly, under the engine slots, against owned PostgreSQL and MySQL
containers. These tests open no database and need no Docker: they keep the
registered corpus, the domains of its rows, the SQL that loads them, which
row orders the language promises, and that the comparison reports each kind
of disagreement, holds each result to the generator's oracle and accepts
what the language leaves to the target.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import date
import json
import math
import os
import signal
import sys
import types

import _pietto_harness_generated_forms as forms
import _pietto_harness_generated_forms_differential as diff
import pytest

FIELDS = (
    ("id", "Int", False),
    ("f0", "Text", True),
    ("f1", "Bool", False),
    ("f2", "Float", True),
    ("f3", "Date", False),
)


def case(
    form="row",
    order=(("id", False),),
    limit=None,
    keys=(),
    join=None,
    items=(("id", ("field", "id")),),
):
    return forms.Case(
        seed=-1,
        profile="narrow",
        form=form,
        fields=FIELDS,
        join=join,
        lets=(),
        where=None,
        keys=keys,
        items=items,
        order=order,
        limit=limit,
    )


def seen(rows, schema=(("id", "int64", False),), end="COMPLETE"):
    return {
        "schema": [list(f) for f in schema],
        "rows": rows,
        "end": end,
        "count": len(rows),
    }


def both(pg, my=None):
    return {"postgres": pg, "mysql": pg if my is None else my}


def test_registered_corpus_is_the_same_on_every_python() -> None:
    assert diff.corpus_digest(diff.SEEDS) == diff.CORPUS_SHA256


def test_rows_keep_the_contract_domains() -> None:
    assert all(-1000 <= value <= 1000 for value in diff.POOL["Int"])
    assert all(math.isfinite(value) for value in diff.POOL["Float"])
    assert all(
        len(text) <= 16 and "'" not in text and "\\" not in text
        for text in diff.POOL["Text"]
    )
    for seed in diff.SEEDS:
        current = forms.generate(seed, diff.PROFILE)
        for source in ("t", "u"):
            values = diff.rows(current, source)
            ids = [row[0] for row in values]
            assert len(set(ids)) == len(ids) <= 6
            assert all(type(key) is int and -1000 <= key <= 1000 for key in ids)
            for row in values:
                for value, (_, kind, nullable) in zip(
                    row[1:], current.fields[1:], strict=True
                ):
                    assert value is None and nullable or value in diff.POOL[kind]
                    assert value is None or type(value) is type(diff.POOL[kind][0])


@pytest.mark.parametrize("target", diff.TARGETS)
def test_table_sql_writes_the_contract_storage(target: str) -> None:
    statements = diff.table_sql(case(), target)
    columns = {
        "postgres": 'id BIGINT NOT NULL, f0 TEXT COLLATE "C", f1 BOOLEAN NOT NULL,'
        " f2 DOUBLE PRECISION, f3 DATE NOT NULL",
        "mysql": "id BIGINT NOT NULL, f0 VARCHAR(16) CHARACTER SET utf8mb4"
        " COLLATE utf8mb4_0900_bin, f1 TINYINT NOT NULL, f2 DOUBLE, f3 DATE NOT NULL",
    }[target]
    assert statements[0] == "DROP TABLE IF EXISTS app.t, app.u"
    assert f"CREATE TABLE app.t ({columns})" in statements
    assert f"CREATE TABLE app.u ({columns})" in statements
    inserts = [s for s in statements if s.startswith("INSERT")]
    assert len(inserts) == sum(bool(diff.rows(case(), s)) for s in ("t", "u"))
    granted = statements[-1] == "GRANT SELECT ON app.t, app.u TO pietto_query"
    assert granted is (target == "postgres")


def test_literals_keep_each_value_exactly() -> None:
    for value in diff.POOL["Float"]:
        text = diff._literal(value, "mysql")
        assert "e" in text and float(text) == value  # a MySQL DOUBLE literal
    assert diff._literal(True, "postgres") == "TRUE"
    assert diff._literal(False, "mysql") == "0"
    assert diff._literal(date(2024, 2, 29), "mysql") == "DATE '2024-02-29'"
    assert diff._literal("a ", "postgres") == "'a '"
    assert diff._literal(None, "postgres") == "NULL"


def test_only_a_total_order_of_keys_that_cannot_be_null_is_promised() -> None:
    assert diff.promised(case())
    assert diff.promised(case(order=(("f3", True), ("id", False))))
    assert not diff.promised(case(order=(("f0", False), ("id", False))))
    assert diff.promised(case("aggregate", order=(), keys=()))
    assert diff.promised(case("aggregate", order=(("f1", False),), keys=("f1",)))
    assert not diff.promised(case("aggregate", order=(), keys=("f1",)))
    assert not diff.promised(case("aggregate", order=(("f0", False),), keys=("f0",)))
    joined = replace(case("join", order=(("t.id", False),)), join=("cross", None))
    assert not diff.promised(joined)


def test_comparison_holds_promised_sequences_and_schemas() -> None:
    rows = [[1], [2]]
    assert diff.compare(case(), both(seen(rows))) == []
    assert diff.compare(case(), both(seen(rows), seen(rows[::-1])))
    other = seen(rows, schema=(("id", "int64", True),))
    assert diff.compare(case(), both(seen(rows), other))
    assert diff.compare(case(), both(seen(rows), seen(rows, end="FAILED")))
    assert diff.compare(case(), both(seen(rows), {"error": ["PIE-R2004", "AUTH"]}))


@pytest.mark.parametrize("name,kind,nullable", FIELDS)
def test_comparison_holds_each_column_to_the_oracle(
    name: str, kind: str, nullable: bool
) -> None:
    """Each result's column is the oracle's name, Arrow type and nullability,
    and a column the oracle types non_null holds no NULL, also when both
    targets return the same wrong column, which no comparison of the two
    targets sees."""
    one = case(items=((name, ("field", name)),))
    arrow = diff.ARROW_TYPES[kind]
    assert diff.expected_schema(one) == [[name, arrow, nullable]]
    value = [diff.encode(diff.POOL[kind][1])]
    assert (
        diff.compare(one, both(seen([value], schema=((name, arrow, nullable),)))) == []
    )
    other = "large_string" if kind == "Text" else "string"
    for schema in (
        ((name, other, nullable),),
        ((name, arrow, not nullable),),
        (("x", arrow, nullable),),
    ):
        wrong = seen([value], schema=schema)
        assert diff.compare(one, both(wrong))
        right = seen([value], schema=((name, arrow, nullable),))
        assert diff.compare(one, both(right, wrong))
    null = seen([[None]], schema=((name, arrow, nullable),))
    assert bool(diff.compare(one, both(null))) is not nullable


def test_comparison_leaves_null_places_and_ties_to_the_target() -> None:
    unpromised = case(
        order=(("f0", False), ("id", False)), items=(("f0", ("field", "f0")),)
    )
    nulls = seen([[None], ["a"]], schema=(("f0", "string", True),))
    last = seen([["a"], [None]], schema=(("f0", "string", True),))
    assert diff.compare(unpromised, both(nulls, last)) == []
    assert diff.compare(unpromised, both(nulls, seen([["a"], ["a"]])))


def test_comparison_checks_a_cut_unpromised_order_against_the_whole() -> None:
    cut = case(order=(("f0", False), ("id", False)), limit=1)
    whole = both(seen([[1], [2]]))
    assert diff.compare(cut, both(seen([[1]]), seen([[2]])), whole) == []
    assert diff.compare(cut, both(seen([[1]]), seen([[2]])))  # no complete result
    assert diff.compare(cut, both(seen([[1]]), seen([[3]])), whole)
    assert diff.compare(cut, both(seen([[1]]), seen([[1], [2]])), whole)
    assert diff.compare(cut, both(seen([[1]])), both(seen([[1], [2]]), seen([[1]])))


def test_campaign_runs_only_under_its_engine_slot(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PIETTO_ENGINE_SLOT_POSTGRES_SUFFIX", raising=False)
    with pytest.raises(ValueError, match="engine-slot"):
        diff._resource("postgres", tmp_path / "postgres")
    assert list(tmp_path.iterdir()) == []


def _without_engines(monkeypatch, prepared: list) -> None:
    """The campaign's resource layer replaced: no container, no database."""
    probe = types.ModuleType("_pietto_execution_source_assurance_probe")
    monkeypatch.setattr(probe, "manager", lambda resource, sql: None, raising=False)
    monkeypatch.setitem(sys.modules, probe.__name__, probe)
    monkeypatch.setattr(diff, "_prepare", lambda resource: prepared.append(resource))


def test_campaign_reads_both_slots_before_it_opens_a_container(
    tmp_path, monkeypatch
) -> None:
    """Without MySQL's slot suffix the campaign opens no PostgreSQL
    container either, and still reports and cleans up."""
    monkeypatch.setenv("PIETTO_ENGINE_SLOT_POSTGRES_SUFFIX", "-slot9")
    monkeypatch.delenv("PIETTO_ENGINE_SLOT_MYSQL_SUFFIX", raising=False)
    prepared = []
    _without_engines(monkeypatch, prepared)
    with pytest.raises(ValueError, match="engine-slot mysql"):
        diff.campaign(tmp_path / "campaign", range(1))
    report = json.loads((tmp_path / "campaign" / "report.json").read_text())
    assert prepared == []
    assert report["status"] == "FAILED" and report["cleanup"] == {"postgres": "success"}


@contextmanager
def _guarded_stops():
    """Handlers that record a SIGTERM or SIGHUP the campaign leaves to its
    caller, so that a campaign that does not stop on one fails the test
    instead of ending the test process; the previous ones come back."""
    reached, stops = [], (signal.SIGTERM, signal.SIGHUP)

    def guard(signum, frame):
        reached.append(signal.Signals(signum).name)

    previous = {stop: signal.signal(stop, guard) for stop in stops}
    try:
        yield reached, guard
    finally:
        for stop, handler in previous.items():
            signal.signal(stop, handler)


@pytest.mark.parametrize("stop", ("SIGTERM", "SIGHUP"))
def test_a_terminated_campaign_cleans_up_and_reports(
    tmp_path, monkeypatch, stop
) -> None:
    """A SIGTERM or SIGHUP, as when the campaign's session ends, stops it as
    an interrupt does: both resources are cleaned up, and a FAILED report
    keeps the seeds observed before it; the previous handler is put back."""
    cleaned, seen = [], []

    class Resource:
        def __init__(self, target):
            self.target = target

        def cleanup(self):
            cleaned.append(self.target)
            return {"status": "success"}

    def observe(case, root, endpoints):
        seen.append(case.seed)
        if len(seen) == 2:
            os.kill(os.getpid(), getattr(signal, stop))
        return {target: {"error": ["fake"]} for target in diff.TARGETS}

    _without_engines(monkeypatch, [])
    monkeypatch.setattr(diff, "_resource", lambda target, directory: Resource(target))
    monkeypatch.setattr(diff, "_observe", observe)
    with _guarded_stops() as (reached, guard):
        with pytest.raises(KeyboardInterrupt, match=stop):
            diff.campaign(tmp_path / "campaign", range(3))
        assert signal.getsignal(getattr(signal, stop)) is guard
    report = json.loads((tmp_path / "campaign" / "report.json").read_text())
    assert reached == []
    assert cleaned == list(diff.TARGETS)
    assert report["status"] == "FAILED" and report["failure"][0] == "KeyboardInterrupt"
    assert [c["seed"] for c in report["cases"]] == report["disagreements"] == [0]


def test_a_stop_during_the_cleanup_is_ignored(tmp_path, monkeypatch) -> None:
    """A SIGTERM and a SIGHUP that arrive while the campaign cleans up stop
    nothing: both resources are cleaned up, the report is written, and the
    previous handlers come back."""
    cleaned = []

    class Resource:
        def __init__(self, target):
            self.target = target

        def cleanup(self):
            if not cleaned:
                os.kill(os.getpid(), signal.SIGTERM)
                os.kill(os.getpid(), signal.SIGHUP)
            cleaned.append(self.target)
            return {"status": "success"}

    def observe(case, root, endpoints):
        return {target: {"error": ["fake"]} for target in diff.TARGETS}

    _without_engines(monkeypatch, [])
    monkeypatch.setattr(diff, "_resource", lambda target, directory: Resource(target))
    monkeypatch.setattr(diff, "_observe", observe)
    with _guarded_stops() as (reached, guard):
        try:
            diff.campaign(tmp_path / "campaign", range(2))
        except KeyboardInterrupt as error:
            pytest.fail(f"a stop during the cleanup interrupted it: {error}")
        assert signal.getsignal(signal.SIGTERM) is guard
        assert signal.getsignal(signal.SIGHUP) is guard
    report = json.loads((tmp_path / "campaign" / "report.json").read_text())
    assert reached == []
    assert cleaned == list(diff.TARGETS)
    assert report["cleanup"] == {target: "success" for target in diff.TARGETS}
    assert report["status"] == "COMPLETE" and report["disagreements"] == [0, 1]


def test_registered_corpus_reaches_each_comparison() -> None:
    """Coverage is an observation, not a proof: the registered seeds reach
    every form under each comparison, empty sources and NULL order keys."""
    reached = set()
    for seed in diff.SEEDS:
        current = forms.generate(seed, diff.PROFILE)
        promised = diff.promised(current)
        reached.add((current.form, promised, current.limit is not None))
        reached.add(("empty", not diff.rows(current, "t")))
        nullable = any(
            forms.typed(current, ("field", key))[1] != forms.NON_NULL
            for key, _ in current.order
        )
        reached.add(("null order key", nullable))
    required = {(form, False, limited) for form in forms.FORMS for limited in (0, 1)}
    required |= {
        (form, True, limited) for form in ("row", "aggregate") for limited in (0, 1)
    }
    required |= {("empty", True), ("null order key", True)}
    assert not required - reached, required - reached
