"""Narrow producer connection and actual production submit seam, offline controls."""

from dataclasses import replace
from typing import Any, cast

import pytest

import test_phase68_slice3_execution as old
from test_phase68_slice4_binding import template, bind
from pietto._project import project_execution as execution
from pietto._project import project_execution_postgres as pg
from pietto._project.project_result_contract import ResultError
from pietto._project.project_execution_template import BindingError


def access():
    return execution.PostgresAccess(
        "127.0.0.1", 5432, "test", "pietto_query", "private", "disable"
    )


def test_bound_arguments_at_submit_and_fresh_attempts(tmp_path, monkeypatch):
    t = template(tmp_path)
    a, b = bind(t, 2), bind(t, 3)
    attempts = []
    for binding in (a, b, a):
        request = execution.prepare_bound_execution(binding, access())
        conn = old.Connection()
        old.install(monkeypatch, conn)
        with pg.PostgresExecution(request) as stream:
            assert [row for batch in stream for row in cast(Any, batch)] == conn.rows
        assert conn.closed and stream.control_joined
        assert [op for op in conn.operations if op[2] is True] == [
            (binding.artifact.rendered.sql.decode(), binding.arguments, True)
        ]
        assert stream.outcome.source == "EOF"
        attempts.append(stream.outcome.attempt)
    assert len(set(attempts)) == 3


def test_legacy_predicate_still_requires_new_authority(tmp_path):
    t = template(tmp_path)
    with pytest.raises(ResultError, match="PRODUCER_UNSUPPORTED"):
        execution.prepare_execution(t.artifact, access())


def test_request_and_projection_grafts(tmp_path):
    t = template(tmp_path)
    a, b = bind(t, 2), bind(t, 3)
    request = execution.prepare_bound_execution(a, access())
    for damaged in (
        replace(request, binding=b),
        replace(request, artifact=b.artifact),
        replace(request, binding=None),
        replace(request, projection=replace(request.projection, artifact=b.artifact)),
    ):
        with pytest.raises((ValueError, BindingError)):
            execution.verify_execution_request(damaged)


def test_row_order_limit_and_complete_correspondence(tmp_path, monkeypatch):
    import _pietto_phase67_result_product_probe as product
    from pietto._project.project_execution_projection import verify_projection

    source = (
        product.source("postgres").replace(
            "    select:", "    where id > 1\n    select:"
        )
        + "    order by:\n        id desc\n    limit 2\n"
    )
    accepted = bind(template(tmp_path, source), 2)
    request = execution.prepare_bound_execution(accepted, access())
    assert (
        b" WHERE " in accepted.artifact.rendered.sql
        and b" ORDER BY " in accepted.artifact.rendered.sql
        and b" LIMIT 2" in accepted.artifact.rendered.sql
    )
    conn = old.Connection()
    conn.rows = []
    old.install(monkeypatch, conn)
    with pg.PostgresExecution(request) as stream:
        assert list(stream) == []
    assert stream.outcome.rows == 0 and stream.outcome.source == "EOF"
    projection = request.projection
    for columns in (
        projection.columns[::-1],
        projection.columns[:1],
        (
            replace(
                projection.columns[0], source_field=projection.columns[1].source_field
            ),
            projection.columns[1],
        ),
    ):
        with pytest.raises(ValueError):
            verify_projection(replace(projection, columns=columns), accepted.artifact)


def test_computed_and_distinct_outputs_stay_later(tmp_path):
    import _pietto_phase67_result_product_probe as product

    for i, source in enumerate(
        (
            product.source("postgres").replace("renamed = id", "renamed = id + 1"),
            product.source("postgres").replace(
                "    select:", "    where id > 1\n    select distinct:"
            ),
        )
    ):
        t = template(tmp_path / str(i), source, lower=0, upper=10)
        accepted = bind(t, 2)
        with pytest.raises((ResultError, ValueError)):
            execution.prepare_bound_execution(accepted, access())


def test_invalid_binding_never_connects(tmp_path, monkeypatch):
    from pietto._project import project_execution_binding_verification as checking

    a = bind(template(tmp_path), 2)
    damaged = replace(a, values=(3,), arguments=(3,))
    damaged = replace(damaged, _state=checking.binding_state(damaged))
    calls = []
    monkeypatch.setattr(pg, "_connect", lambda request: calls.append(request))
    with pytest.raises(BindingError):
        pg.PostgresExecution(execution.prepare_bound_execution(damaged, access()))
    assert calls == []


def test_hidden_order_and_foreign_source_are_not_direct_outputs(tmp_path):
    import _pietto_phase67_result_product_probe as product

    source = (
        product.source("postgres")
        .replace("    select:", "    where id > 1\n    select:")
        .replace("        other\n", "")
        + "    order by:\n        other\n"
    )
    accepted = bind(template(tmp_path, source), 2)
    request = execution.prepare_bound_execution(accepted, access())
    projection = request.projection
    hidden = accepted.artifact.request.sources[0].fields[1]
    from pietto._project.project_execution_projection import verify_projection

    assert len(projection.columns) == 1
    # Hidden ORDER input remains part of the verified SQL, not an output.
    for columns in (
        (
            *projection.columns,
            replace(projection.columns[0], ordinal=1, source_field=hidden),
        ),
        (replace(projection.columns[0], source_field=hidden),),
    ):
        with pytest.raises(ResultError):
            verify_projection(replace(projection, columns=columns), accepted.artifact)


def test_record_checker_rejects_independent_damage(tmp_path):
    """Synthetic receipt tests the checker only; the native lab owns live proof."""
    from copy import deepcopy
    import hashlib
    import json
    from pathlib import Path
    import sys
    from dataclasses import asdict
    import _pietto_phase68_slice4_probe as lab
    from pietto._project.project_sql_emission import (
        serialize_project_sql_emission,
        EmissionOutcome,
    )

    a = bind(template(tmp_path), 1)
    names = (
        "project_execution_template",
        "project_execution_binding_verification",
        "project_execution_projection",
        "project_execution_postgres",
        "project_execution_reader",
    )
    origins = {}
    for name in names:
        name = "pietto._project." + name
        filename = sys.modules[name].__file__
        assert filename is not None
        path = Path(filename).resolve()
        origins[name] = dict(
            path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()
        )
    row = dict(
        case="A",
        values=[lab.s01.scalar(1)],
        public=json.loads(
            serialize_project_sql_emission(EmissionOutcome("VERIFIED", (), a.artifact))
        ),
        sql=lab.SQL,
        submissions=[dict(sql=lab.SQL, arguments=[lab.s01.scalar(1)], prepare=True)],
        rows=[[lab.s01.scalar(v) for v in row] for row in lab.ROWS if row[0] > 1],
        schemas=[[["renamed", "int64", False], ["other", "int64", True]]] * 3,
        bound_schema=[["renamed", "int64", False], ["other", "int64", True]],
        metadata=[["renamed", 20, None], ["other", 20, None]],
        context=["pietto_query", "repeatable read", "on", "UTF8", "pg_catalog"],
        outcome=asdict(
            execution.ExecutionOutcome(
                "synthetic-attempt",
                "EOF",
                "COMMIT_ACK",
                "COMPLETE",
                "CLOSED",
                5,
                3,
                86,
                None,
                (),
                False,
                False,
                False,
            )
        ),
        session=123,
        control_joined=True,
        cancel=None,
        caught=None,
    )
    # JSON process boundary turns tuples into lists, as in the real receipt.
    data = json.loads(
        json.dumps(
            dict(
                origin="source",
                prefix=sys.prefix,
                results=[row],
                origins=origins,
                invalid="BINDING_VALUE:0:Int",
            )
        )
    )
    lab.check_observation(data, "source", ("A",), Path(sys.prefix))

    def damage(record, kind):
        r = record["results"][0]
        if kind == "value":
            r["values"][0]["value"] = "5"
        elif kind == "use":
            r["public"]["parameter_uses"][0]["server_index"] = 2
        elif kind == "sql":
            r["submissions"][0]["sql"] += " WHERE FALSE"
        elif kind == "metadata":
            r["metadata"][0][1] = 23
        elif kind == "rows":
            r["rows"].pop()
        elif kind == "schema":
            r["bound_schema"][0][2] = True
        elif kind == "context":
            r["context"][0] = "foreign"
        elif kind == "origin":
            next(iter(record["origins"].values()))["sha256"] = "0" * 64
        elif kind == "terminal":
            r["outcome"]["transaction"] = "UNKNOWN"

    for kind in (
        "value",
        "use",
        "sql",
        "metadata",
        "rows",
        "schema",
        "context",
        "origin",
        "terminal",
    ):
        corrupted = deepcopy(data)
        damage(corrupted, kind)
        with pytest.raises(ValueError):
            lab.check_observation(corrupted, "source", ("A",), Path(sys.prefix))

    for case, source, phase, kind in (
        ("cancel", "FAILED", "read", "ExecutionError"),
        ("consumer_error", "EARLY_CLOSE", "consumer", "ValueError"),
    ):
        controlled = deepcopy(data)
        r = controlled["results"][0]
        r.update(
            case=case,
            rows=r["rows"][:2],
            schemas=r["schemas"][:1],
            caught=kind,
            cancel=dict(requested=True, sent=True, observed=False, late=False)
            if case == "cancel"
            else None,
        )
        r["outcome"].update(
            source=source,
            transaction="ROLLBACK_ACK",
            delivery="FAILED",
            rows=2,
            batches=1,
            primary=dict(phase=phase, kind=kind, sqlstate=None),
            cancel_requested=case == "cancel",
            cancel_sent=case == "cancel",
        )
        lab.check_observation(controlled, "source", (case,), Path(sys.prefix))
        for field, value in (
            ("source", "UNKNOWN"),
            ("delivery", "EARLY_CLOSE"),
            ("cancel_observed", True),
            ("primary", None),
            ("batches", 2),
        ):
            damaged = deepcopy(controlled)
            damaged["results"][0]["outcome"][field] = value
            with pytest.raises(ValueError):
                lab.check_observation(damaged, "source", (case,), Path(sys.prefix))


def test_binding_does_not_reuse_target_or_role_authority(tmp_path, monkeypatch):
    mysql = bind(template(tmp_path / "mysql", target="mysql"), 2)
    with pytest.raises(execution.ExecutionError, match="EXECUTION_TARGET"):
        execution.prepare_bound_execution(mysql, access())
    accepted = bind(template(tmp_path / "postgres"), 2)
    request = execution.prepare_bound_execution(
        accepted, replace(access(), user="foreign_role")
    )
    connection = old.Connection()
    old.install(monkeypatch, connection)
    stream = pg.PostgresExecution(request)
    with pytest.raises(execution.ExecutionError, match="EXECUTION_CONTEXT"):
        with stream:
            list(stream)
    assert connection.closed and stream.control_joined
    assert not any(op[2] is True for op in connection.operations)


@pytest.mark.parametrize("control", ("cancel", "deadline"))
def test_cancel_during_binding_reverification_prevents_submission(
    tmp_path, monkeypatch, control
):
    accepted = bind(template(tmp_path), 2)
    request = execution.prepare_bound_execution(accepted, access())
    connection = old.Connection()
    old.install(monkeypatch, connection)
    stream = pg.PostgresExecution(request)
    original = pg.execution_arguments

    def cancel_during_check(request):
        arguments = original(request)
        if control == "cancel":
            stream.cancel()
        else:
            assert stream._started is not None
            stream._started -= request.limits.seconds + 1
        return arguments

    monkeypatch.setattr(pg, "execution_arguments", cancel_during_check)
    expected = execution.ExecutionError if control == "cancel" else TimeoutError
    with pytest.raises(expected):
        with stream:
            next(stream)
    assert not any(op[2] is True for op in connection.operations)
    assert connection.closed and stream.control_joined
