"""S15 provisional delivery and the cooperative reference sink: v5 boundary,
sink identity and typed effects, windows, keys, local frontier, lost replies,
authority, injected faults, protection, the S13 bridge, the relay step and
independent history replay.

Saved inputs use S12's ARROW_FREE_STORAGE_STEP, reads S13's
ARROW_FREE_REPLAY_STEP and rows the labelled ARROW_FREE_PAYLOAD_STEP; the sink's
own transactions, windows, issuance, confirmations, fences and every SQLite
transaction run for real. Real checked Arrow rows, seven scalars and refined
coordinates run in the Arrow-only delivery profile
(`scripts/phase68_slice15_probe.py`). Pure laws run on every host.
"""

import copy
import dataclasses
import json
import os
import pickle
import sqlite3
from types import SimpleNamespace
from typing import Any

import pytest

import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice13_probe as s13
import _pietto_phase68_slice15_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from pietto._project import project_job_capture as c
from pietto._project import project_job_delivery as d
from pietto._project import project_job_replay as r
from pietto._project import project_job_sink as k
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

op = probe.op


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(
        tmp_path_factory.mktemp("s15-delivery") / "small", entry="bundle"
    )


@pytest.fixture
def setup(tmp_path, built, monkeypatch):
    if not qualified(tmp_path):
        yield None
        return
    probe.arrow_free(monkeypatch)
    monkeypatch.setattr(probe, "SALT", {})
    template, compiled = built
    workspace, job, publisher, binding, record, generation = probe.store(
        tmp_path / "workspace", template
    )
    handle = probe.sink(tmp_path / "sink")
    from pietto._project.project_execution import compiled_output

    output, refinement, _program = compiled_output(binding)
    x = SimpleNamespace(
        root=tmp_path,
        layout=d.layout(output, refinement),
        workspace=workspace,
        job=job,
        publisher=publisher,
        binding=binding,
        record=record,
        generation=generation,
        built=compiled,
        template=template,
        sink=handle,
    )
    yield x
    for item in (x.sink, x.publisher, x.workspace):
        try:
            item.close()
        except JobStoreError:
            pass


def window(x, checkpoint=None, **overrides):
    if checkpoint is None:
        checkpoint = probe.latest(x.workspace, x.job, x.generation)
    return probe.accept_window(
        x.workspace, x.job, x.generation, x.built, checkpoint, **overrides
    )


def stream_of(x, sizes=(2, 2), **options):
    probe.capture(x.workspace, x.publisher, x.generation, x.binding, sizes, **options)
    return probe.registered(
        x.workspace, x.job, x.publisher, x.generation, x.built, x.sink
    )


def reopen(x, stream, *, read=True):
    checkpoint = d.stream_state(x.workspace, stream).windows[-1][1]
    return d.open_stream(
        x.publisher,
        stream,
        probe.accept_sink(x.sink),
        window=window(x, checkpoint) if read else None,
        operation=op(),
    )


def issue(session, rows) -> d.Issued:
    item = session.next(rows, operation=op())
    assert isinstance(item, d.Issued)
    return item


def effect(x, position, payload=None, **overrides):
    layout = x.layout
    fields: dict[str, Any] = {
        "sink": x.sink.identity,
        "namespace": x.sink.namespace,
        "epoch": x.sink.epoch,
        "retention": x.sink.retention,
        "workspace": x.workspace.identity,
        "generation": x.generation,
        "position": position,
        "layout": layout,
        "payload": probe.synthetic_row(position) if payload is None else payload,
    }
    fields.update(overrides)
    return k.SinkEffect(**fields)


# ---------------------------------------------------------------------------
# Format and identity boundaries


def test_effect_keys_and_frontier_are_pure_laws():
    from pietto._project.project_job_capture import frontier

    # The derived frontier is the maximal contiguous observed prefix.
    for observed, expected in (
        ([], 0),
        ([0, 2], 1),
        ([1, 2], 0),
        ([0, 1, 2], 3),
        ([0, 1, 3, 4], 2),
    ):
        assert frontier([(p, p + 1) for p in observed]) == expected
    assert d._ranges([5, 0, 1, 3, 4]) == ((0, 2), (3, 6))
    base: dict[str, Any] = dict(
        sink=w.new_identity("snk"),
        namespace="n",
        epoch=1,
        retention="r",
        workspace=w.new_identity("ws"),
        generation=w.new_identity("gen"),
        layout="l",
        payload="p",
    )
    # Equal payloads at two positions are two keys; the key never names a batch.
    one, two = k.SinkEffect(position=1, **base), k.SinkEffect(position=2, **base)
    assert one.key != two.key and one.key[:5] == two.key[:5]
    assert one.key == k.SinkEffect(position=1, **base).key
    assert k.effect_digest("a", "b") != k.effect_digest("ab", "")
    for kind in ("stm", "sts", "sti", "snk", "skc"):
        assert w.valid_identity(w.new_identity(kind), kind)
        assert not w.valid_identity(w.new_identity(kind), "dlv")


def test_v5_is_explicit_and_older_formats_refuse_delivery_unchanged(tmp_path, built):
    if not qualified(tmp_path):
        return
    template, compiled = built
    v4, v5 = w.expected_schema(w.FORMAT_V4), w.expected_schema(w.FORMAT_V5)
    added = {row[1] for row in v5} - {row[1] for row in v4}
    assert {n for n in added if not n.startswith("sqlite_autoindex_")} == {
        "stream",
        "stream_window",
        "stream_session",
        "stream_issuance",
        "sink_observation",
        "stream_retirement",
    }
    assert set(v4) < set(v5)
    workspace = w.create_workspace(str(tmp_path / "v5"), format=w.FORMAT_V5)
    try:
        assert json.loads((tmp_path / "v5" / "workspace.json").read_bytes()) == {
            "budget": w.DEFAULT_BUDGET,
            "database": "store.sqlite",
            "features": [
                "result-chunks",
                "saved-replay",
                "extraction-resume",
                "cooperative-delivery",
            ],
            "format": "pietto.job-workspace.v5",
            "identity": workspace.identity,
        }
        assert workspace.use().execute("PRAGMA user_version").fetchone() == (5,)
        assert all(
            w.supports(workspace, f)
            for f in (
                "result-chunks",
                "saved-replay",
                "extraction-resume",
                "cooperative-delivery",
            )
        )
    finally:
        workspace.close()
    w.open_workspace(str(tmp_path / "v5"), expected_identity=workspace.identity).close()
    for format, version in (
        (w.FORMAT, 1),
        (w.FORMAT_V2, 2),
        (w.FORMAT_V3, 3),
        (w.FORMAT_V4, 4),
    ):
        root = tmp_path / ("v" + str(version))
        workspace, job, publisher, _binding, _record, generation = s12.store(
            root, template, (1,), format=format
        )
        absent: Any = None
        try:
            schema = w.expected_schema(format)
            assert not w.supports(workspace, "cooperative-delivery")
            for call in (
                lambda: d.stream_state(workspace, w.new_identity("stm")),
                lambda: d.find_stream(
                    workspace, job, generation, sink="x", namespace="n", epoch=1
                ),
                lambda: d.open_stream(
                    publisher, w.new_identity("stm"), absent, operation=op()
                ),
                lambda: d.register_stream(publisher, absent, absent, operation=op()),
                lambda: d.retire_stream(
                    publisher, w.new_identity("stm"), operation=op()
                ),
                lambda: probe.accept_window(workspace, job, generation, compiled, None),
            ):
                with pytest.raises(JobStoreError, match="WORKSPACE_DELIVERY_FORMAT"):
                    call()
            connection = workspace.use()
            assert connection.execute("PRAGMA user_version").fetchone()[0] == version
            assert (
                tuple(
                    connection.execute(
                        "SELECT type, name, tbl_name, sql FROM sqlite_schema"
                        " ORDER BY type, name"
                    )
                )
                == schema
            )
            verify_store(workspace)
        finally:
            publisher.close()
            workspace.close()


def test_a_runtime_without_v5_refuses_it_before_sqlite(tmp_path, monkeypatch):
    if not qualified(tmp_path):
        return
    root = tmp_path / "v5"
    workspace = w.create_workspace(str(root), format=w.FORMAT_V5)
    workspace.close()
    before = s12.tree(root)
    monkeypatch.setattr(
        w, "VERSIONS", {key: v for key, v in w.VERSIONS.items() if key != w.FORMAT_V5}
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("SQLite opened before the envelope was accepted")

    monkeypatch.setattr(w, "_connect", forbidden)
    with pytest.raises(JobStoreError, match="WORKSPACE_FORMAT"):
        w.open_workspace(str(root), expected_identity=workspace.identity)
    assert s12.tree(root) == before
    monkeypatch.undo()
    for bad in ("pietto.job-workspace.v7", "pietto.job-workspace.v5 "):
        with pytest.raises(JobStoreError, match="WORKSPACE_FORMAT"):
            w.create_workspace(str(tmp_path / "other"), format=bad)
    assert not (tmp_path / "other").exists()


def test_sink_identity_envelope_and_schema_are_closed(tmp_path, monkeypatch):
    if not qualified(tmp_path):
        return
    handle = probe.sink(tmp_path / "sink", namespace="orders.v1", epoch=3, seconds=60)
    description = handle.describe()
    retention = json.loads(handle.retention)
    assert (description.identity, description.namespace, description.epoch) == (
        handle.identity,
        "orders.v1",
        3,
    )
    assert retention["seconds"] == 60 and retention["format"] == k.RETENTION
    assert description.retained_until == retention["retained_until"]
    envelope = json.loads((tmp_path / "sink" / "sink.json").read_bytes())
    assert envelope == {
        "budget": w.DEFAULT_BUDGET,
        "database": "sink.sqlite",
        "epoch": 3,
        "format": "pietto.reference-sink.v1",
        "identity": handle.identity,
        "namespace": "orders.v1",
        "retention": retention,
    }
    connection = handle.use()
    assert connection.execute("PRAGMA application_id").fetchone()[0] == k.APPLICATION_ID
    assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
    assert connection.getlimit(sqlite3.SQLITE_LIMIT_ATTACHED) == 0
    foreign = probe.sink(tmp_path / "other", namespace="orders.v1", epoch=3)
    foreign.close()
    with pytest.raises(JobStoreError, match="SINK_EXISTS"):
        probe.sink(tmp_path / "sink")
    handle.close()
    handle.close()
    with pytest.raises(JobStoreError, match="SINK_CLOSED"):
        handle.describe()
    with pytest.raises(JobStoreError, match="SINK_IDENTITY"):
        k.open_sink(str(tmp_path / "sink"), expected_identity=foreign.identity)
    with pytest.raises(JobStoreError, match="SINK_IDENTITY"):
        k.open_sink(str(tmp_path / "sink"), expected_identity="ws-" + "0" * 32)
    reopened = k.open_sink(str(tmp_path / "sink"), expected_identity=handle.identity)
    reopened._pid = -1
    with pytest.raises(JobStoreError, match="SINK_FOREIGN_PROCESS"):
        reopened.describe()
    reopened._pid = os.getpid()
    reopened.close()
    # Unknown or modified envelopes never reach SQLite and change nothing.
    before = s12.tree(tmp_path / "sink")
    path = tmp_path / "sink" / "sink.json"
    original = path.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("SQLite opened before the envelope was accepted")

    with monkeypatch.context() as patch:
        patch.setattr(k, "_connect", forbidden)
        for document in (
            {**envelope, "format": "pietto.reference-sink.v2"},
            {**envelope, "epoch": 0},
            {**envelope, "namespace": "bad name"},
            {**envelope, "retention": {**retention, "seconds": 0}},
            {**envelope, "extra": 1},
        ):
            path.chmod(0o600)
            path.write_bytes(
                (
                    json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
                ).encode()
            )
            with pytest.raises(JobStoreError, match="SINK_FORMAT"):
                k.open_sink(str(tmp_path / "sink"), expected_identity=handle.identity)
    path.write_bytes(original)
    assert s12.tree(tmp_path / "sink") == before
    # A sink is not a job workspace and a workspace is not a sink.
    with pytest.raises(JobStoreError, match="WORKSPACE_INCOMPLETE"):
        w.open_workspace(str(tmp_path / "sink"), expected_identity=w.new_identity("ws"))
    workspace = w.create_workspace(str(tmp_path / "workspace"), format=w.FORMAT_V5)
    workspace.close()
    with pytest.raises(JobStoreError, match="SINK_INCOMPLETE"):
        k.open_sink(str(tmp_path / "workspace"), expected_identity=handle.identity)
    # An existing directory without a complete envelope is never initialized.
    (tmp_path / "empty").mkdir(mode=0o700)
    with pytest.raises(JobStoreError, match="SINK_INCOMPLETE"):
        k.open_sink(str(tmp_path / "empty"), expected_identity=handle.identity)
    with pytest.raises(JobStoreError, match="SINK_EXISTS"):
        probe.sink(tmp_path / "empty")
    assert os.listdir(tmp_path / "empty") == []
    (tmp_path / "sink" / "stray").write_bytes(b"")
    (tmp_path / "sink" / "stray").chmod(0o600)
    with pytest.raises(JobStoreError, match="SINK_OBJECT"):
        k.open_sink(str(tmp_path / "sink"), expected_identity=handle.identity)
    (tmp_path / "sink" / "stray").unlink()
    for bad in (
        {"namespace": "", "epoch": 1, "retention_seconds": 1},
        {"namespace": "a b", "epoch": 1, "retention_seconds": 1},
        {"namespace": "n", "epoch": 0, "retention_seconds": 1},
        {"namespace": "n", "epoch": True, "retention_seconds": 1},
        {"namespace": "n", "epoch": 1, "retention_seconds": 0},
        {
            "namespace": "n",
            "epoch": 1,
            "retention_seconds": k.MAX_RETENTION_SECONDS + 1,
        },
    ):
        with pytest.raises(JobStoreError, match="SINK_CONTRACT"):
            k.create_sink(str(tmp_path / "bad"), **bad)  # type: ignore[arg-type]
    assert not (tmp_path / "bad").exists()
    # A database whose identity row was replaced is refused at open.
    raw = sqlite3.connect(tmp_path / "sink" / "sink.sqlite")
    raw.execute("UPDATE sink SET epoch = 4")
    raw.commit()
    raw.close()
    with pytest.raises(JobStoreError, match="SINK_SCHEMA"):
        k.open_sink(str(tmp_path / "sink"), expected_identity=handle.identity)


def test_unqualified_profiles_refuse_sink_and_workspace_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(w, "QUALIFIED_SQLITE", frozenset())
    for create in (
        lambda: probe.sink(tmp_path / "sink"),
        lambda: w.create_workspace(str(tmp_path / "ws"), format=w.FORMAT_V5),
    ):
        with pytest.raises(JobStoreError, match="WORKSPACE_PROFILE"):
            create()
    assert not (tmp_path / "sink").exists() and not (tmp_path / "ws").exists()


# ---------------------------------------------------------------------------
# Reference sink effect laws


def test_sink_commits_once_and_reports_duplicates_and_conflicts(setup):
    if setup is None:
        return
    x = setup
    probe.capture(x.workspace, x.publisher, x.generation, x.binding, (2,))
    first = x.sink.submit(effect(x, 0))
    assert (first.status, first.kind, first.sequence) == ("COMMITTED", "submit", 1)
    assert w.valid_identity(first.commit, "skc")
    assert first.digest == k.effect_digest(effect(x, 0).layout, effect(x, 0).payload)
    again = x.sink.submit(effect(x, 0))
    assert again.status == "DUPLICATE"
    assert (again.commit, again.sequence, again.digest) == (
        first.commit,
        first.sequence,
        first.digest,
    )
    changed = x.sink.submit(effect(x, 0, probe.synthetic_row(0, 1)))
    assert changed.status == "CONFLICT" and changed.commit == first.commit
    # Equal values at two positions are two materialized effects.
    same = probe.synthetic_row(7)
    one, two = x.sink.submit(effect(x, 1, same)), x.sink.submit(effect(x, 2, same))
    assert (one.status, two.status) == ("COMMITTED", "COMMITTED")
    assert one.commit != two.commit and one.digest == two.digest
    rows = probe.effects(x.sink)
    assert [row[0] for row in rows] == [0, 1, 2] and len({row[2] for row in rows}) == 3
    stored = (
        x.sink.use()
        .execute("SELECT payload FROM effect WHERE position = 0")
        .fetchone()[0]
    )
    assert stored == probe.synthetic_row(0)  # never overwritten
    for payload, status in (
        (probe.synthetic_row(0), "PRESENT_MATCHING"),
        (probe.synthetic_row(0, 1), "PRESENT_CONFLICT"),
    ):
        found = x.sink.query(effect(x, 0, payload))
        assert (found.kind, found.status, found.commit) == (
            "query",
            status,
            first.commit,
        )
    assert x.sink.query(effect(x, 9)).status == "ACTIVE_NOT_FOUND"
    # Another instance, namespace, epoch or retention contract is not this one.
    for overrides in (
        {"sink": w.new_identity("snk")},
        {"namespace": "other"},
        {"epoch": 2},
        {"retention": k.retention_descriptor(1, 2)},
    ):
        assert x.sink.submit(effect(x, 5, **overrides)).status == "UNAVAILABLE"
        assert (
            x.sink.query(effect(x, 0, **overrides)).status == "UNAVAILABLE_OR_UNKNOWN"
        )
    assert [row[0] for row in probe.effects(x.sink)] == [0, 1, 2]
    for bad in (
        {"workspace": "ws-1"},
        {"generation": w.new_identity("job")},
        {"position": -1},
        {"position": True},
    ):
        with pytest.raises(JobStoreError, match="SINK_REQUEST"):
            x.sink.submit(dataclasses.replace(effect(x, 0), **bad))


def test_sink_checks_exact_typed_rows_before_any_effect(setup):
    if setup is None:
        return
    x = setup
    probe.capture(x.workspace, x.publisher, x.generation, x.binding, (1,))
    small = window(x, None).layout
    fields = [
        [0, "b", "builtin", "Bool", "nullable", None],
        [1, "f", "builtin", "Float", "non_null", None],
        [2, "d", "builtin", "Decimal", "nullable", None],
        [3, "t", "builtin", "Timestamp", "nullable", ["timestamp", "x"]],
        [4, "u", "builtin", "UUID", "nullable", ["uuid", "big_endian", 16]],
        [5, "s", "builtin", "Text", "nullable", None],
    ]
    typed = d._json(
        {
            "contract": "0" * 64,
            "fields": fields,
            "format": k.LAYOUT,
            "multiplicity": ["bag"],
            "scheme": None,
        }
    )
    good = [
        ["bool", True],
        ["float", (-0.0).hex()],
        ["decimal", 0, [1, 2, 0], -2],
        ["datetime", "2024-01-02T03:04:05.000006", 0],
        ["uuid", "00" * 16],
        ["str", "héllo☃"],
    ]

    def row(values, coordinates=None):
        return d._json({"coordinates": coordinates, "values": values})

    k.check_effect(typed, row(good))
    k.check_effect(typed, row([["NoneType", None], *good[1:]]))
    # True and 1, -0.0 and 0.0 are distinct rows, never one value.
    assert row(good) != row([["bool", True], ["float", (0.0).hex()], *good[2:]])
    for values in (
        [["int", 1], *good[1:]],  # Int is not Bool
        [good[0], ["NoneType", None], *good[2:]],  # NULL in a non-null field
        [good[0], ["float", "zz"], *good[2:]],  # not a closed wire
        good[:5],  # arity
        [*good[:4], ["bytes", "00" * 16], good[5]],  # UUID is not bytes
    ):
        with pytest.raises(JobStoreError, match="SINK_EFFECT"):
            k.check_effect(typed, row(values))
    for layout, payload in (
        (typed, row(good) + " "),  # not canonical
        (typed, json.dumps({"values": good, "coordinates": None})),
        (typed, row(good, [["int", 1]])),  # coordinates without a scheme
        (typed.replace(k.LAYOUT, "other"), row(good)),
        (small, row(good)),
        (typed, "x" * (k.MAX_EFFECT_BYTES + 1)),
    ):
        with pytest.raises(JobStoreError, match="SINK_EFFECT"):
            k.check_effect(layout, payload)
    with pytest.raises(JobStoreError, match="SINK_EFFECT"):
        x.sink.submit(effect(x, 0, row(good)))
    assert probe.effects(x.sink) == []


def test_retention_contract_is_fixed_and_expiry_is_not_absence(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    probe.capture(x.workspace, x.publisher, x.generation, x.binding, (2,))
    assert x.sink.submit(effect(x, 0)).status == "COMMITTED"
    clock = {"now": float(x.sink.retained_until)}
    monkeypatch.setattr(k, "_wall", lambda: clock["now"])
    monkeypatch.setattr(d, "_wall", lambda: clock["now"])
    assert x.sink.submit(effect(x, 1)).status == "RETENTION_EXPIRED"
    # Expired is not absence: a present effect is not reported as not found.
    for position in (0, 1):
        assert x.sink.query(effect(x, position)).status == "RETENTION_EXPIRED"
    with pytest.raises(JobStoreError, match="RETENTION_EXPIRED"):
        probe.accept_sink(x.sink)
    # Physical records remain without restoring the guarantee.
    assert [row[0] for row in probe.effects(x.sink)] == [0]
    clock["now"] -= 1
    acceptance = probe.accept_sink(x.sink, seconds=600)
    clock["now"] += 1
    with pytest.raises(JobStoreError, match="RETENTION_EXPIRED"):
        d._accepted(acceptance, d.SinkAcceptance)


# ---------------------------------------------------------------------------
# Windows, disclosure and effect identity


def test_windows_extend_only_by_confirmed_verified_checkpoints(setup):
    if setup is None:
        return
    x = setup
    session, results = probe.capture(
        x.workspace, x.publisher, x.generation, x.binding, (2,), eof=False
    )
    stream, delivery = probe.registered(
        x.workspace, x.job, x.publisher, x.generation, x.built, x.sink
    )
    assert delivery.window.start == 0 and delivery.window.stop == 2
    first = results[0].get("checkpoint")
    staged = [s12.stage_frame(session, 2), s12.stage_frame(session, 2)]
    later = [session.publish(item, operation=op()) for item in staged]
    newest = later[-1].get("checkpoint")
    # [2, 6) needs [0, 2) confirmed first.
    with pytest.raises(JobStoreError, match="STREAM_WINDOW_UNCONFIRMED"):
        delivery.adopt(window(x, newest), operation=op())
    extents, waiting = probe.deliver(delivery, 3)
    assert extents == [(0, 2, ("COMMITTED", "COMMITTED"))]
    assert (waiting.position, waiting.window, waiting.checkpoint) == (2, 1, first)
    assert waiting.complete_coverage is False and waiting.observed_end is None
    for checkpoint, code in (
        (first, "STREAM_WINDOW_CURRENT"),
        (w.new_identity("ckp"), "CHECKPOINT_UNKNOWN"),
    ):
        with pytest.raises(JobStoreError, match=code):
            delivery.adopt(window(x, checkpoint), operation=op())
    middle = later[0].get("checkpoint")
    adopted = delivery.adopt(window(x, middle), operation=op())
    assert (adopted.get("start"), adopted.get("stop"), adopted.get("ordinal")) == (
        2,
        4,
        2,
    )
    # A regression to an older checkpoint is never an extension.
    extents, _ = probe.deliver(delivery, 3)
    assert extents == [(2, 4, ("COMMITTED", "COMMITTED"))]
    with pytest.raises(JobStoreError, match="STREAM_WINDOW_EXTENSION"):
        delivery.adopt(window(x, first), operation=op())
    operation = op()
    grown = delivery.adopt(window(x, newest), operation=operation)
    assert (grown.get("start"), grown.get("stop"), grown.get("ordinal")) == (4, 6, 3)
    # Idempotent adoption returns the historical fact, not new permission.
    again = delivery.adopt(window(x, newest), operation=operation)
    assert again.observation == "PREVIOUSLY_COMMITTED" and again.result == grown.result
    extents, waiting = probe.deliver(delivery, 4)
    assert extents == [(4, 6, ("COMMITTED", "COMMITTED"))] and waiting.position == 6
    state = d.stream_state(x.workspace, stream)
    assert [(wd[0], wd[3], wd[4]) for wd in state.windows] == [
        (1, 0, 2),
        (2, 2, 4),
        (3, 4, 6),
    ]
    assert (
        state.position == 6 and state.observed == ((0, 6),) and state.unresolved == ()
    )
    protected = c.protected_chunks(x.workspace, x.job)
    for item in state.windows:
        snapshot = c.checkpoint_snapshot(
            x.workspace, x.job, x.generation, checkpoint=item[1]
        )
        assert {m.chunk for m in snapshot.members} <= protected
    assert [row[0] for row in probe.effects(x.sink)] == list(range(6))
    verify_store(x.workspace)


def test_graft_from_another_generation_is_refused(setup):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (2,))
    job = s.register_job(x.workspace, x.template, operation=op()).get("job")
    publisher = s.claim_publisher(x.workspace, job, operation=op())
    try:
        record = s.register_binding(publisher, x.binding, operation=op()).get("binding")
        other = s.register_generation(
            publisher,
            record,
            x.binding,
            route="postgres_rows",
            isolation="stable",
            operation=op(),
        ).get("generation")
        probe.capture(x.workspace, publisher, other, x.binding, (2, 2))
    finally:
        publisher.close()
    foreign = probe.latest(x.workspace, job, other)
    probe.deliver(delivery, 2)
    with pytest.raises(JobStoreError, match="CHECKPOINT_UNKNOWN"):
        window(x, foreign)
    graft = probe.accept_window(x.workspace, job, other, x.built, foreign)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_SUBJECT"):
        delivery.adopt(graft, operation=op())
    with pytest.raises(JobStoreError, match="ACCEPTANCE_SUBJECT"):
        d.open_stream(
            x.publisher, stream, probe.accept_sink(x.sink), window=graft, operation=op()
        )
    assert len(d.stream_state(x.workspace, stream).windows) == 1


def test_islands_beyond_a_hole_are_never_disclosed(setup):
    if setup is None:
        return
    x = setup
    session, results = probe.capture(
        x.workspace,
        x.publisher,
        x.generation,
        x.binding,
        (2, 2, 2),
        order=(0, 2),
        eof=False,
    )
    assert [p.get("frontier") for p in results] == [2, 2]
    _stream, delivery = probe.registered(
        x.workspace, x.job, x.publisher, x.generation, x.built, x.sink
    )
    assert (delivery.window.start, delivery.window.stop) == (0, 2)
    extents, waiting = probe.deliver(delivery, 4)
    assert extents == [(0, 2, ("COMMITTED", "COMMITTED"))]
    assert waiting.holes == ((2, 4),) and waiting.position == 2
    assert [row[0] for row in probe.effects(x.sink)] == [0, 1]
    filled = session.publish(session.staged[0], operation=op())
    assert filled.get("frontier") == 6
    delivery.adopt(window(x, filled.get("checkpoint")), operation=op())
    extents, waiting = probe.deliver(delivery, 4)
    assert extents == [(2, 6, ("COMMITTED",) * 4)] and waiting.holes == ()
    verify_store(x.workspace)


def test_empty_schema_differs_from_a_hole_at_zero(tmp_path, built, monkeypatch):
    if not qualified(tmp_path):
        return
    probe.arrow_free(monkeypatch)
    template, compiled = built
    waits = {}
    for name, sizes, order, eof in (
        ("empty", (), None, True),
        ("hole", (2, 2), (1,), False),
    ):
        workspace, job, publisher, binding, _record, generation = probe.store(
            tmp_path / name, template
        )
        handle = probe.sink(tmp_path / (name + "-sink"))
        try:
            probe.capture(
                workspace, publisher, generation, binding, sizes, order=order, eof=eof
            )
            _stream, delivery = probe.registered(
                workspace, job, publisher, generation, compiled, handle
            )
            waits[name] = delivery.next(1, operation=op())
            assert probe.effects(handle) == []
            verify_store(workspace)
        finally:
            handle.close()
            publisher.close()
            workspace.close()
    empty, hole = waits["empty"], waits["hole"]
    assert empty.terminal == hole.terminal == d.WAITING
    assert empty.schema[0] == "ARROW_FREE_SCHEMA_MEMBER" and hole.schema is None
    assert (
        empty.position,
        empty.holes,
        empty.observed_end,
        empty.complete_coverage,
    ) == (
        0,
        (),
        0,
        True,
    )
    assert (hole.position, hole.holes, hole.complete_coverage) == (0, ((0, 2),), False)


def test_fixed_s13_consumers_keep_their_checkpoint_and_extent(setup):
    if setup is None:
        return
    x = setup
    session, results = probe.capture(
        x.workspace, x.publisher, x.generation, x.binding, (2,), eof=False
    )
    acceptance = s13.accept(
        x.workspace, x.job, x.generation, x.built, scope="committed_prefix", extent=2
    )
    r.register_consumer(x.publisher, acceptance, operation=op())
    _stream, delivery = probe.registered(
        x.workspace, x.job, x.publisher, x.generation, x.built, x.sink
    )
    probe.deliver(delivery, 2)
    grown = session.publish(s12.stage_frame(session, 2), operation=op())
    delivery.adopt(window(x, grown.get("checkpoint")), operation=op())
    probe.deliver(delivery, 2)
    state = r.consumer_state(x.workspace, acceptance.consumer)
    assert (state.checkpoint, state.extent, state.position) == (
        results[0].get("checkpoint"),
        2,
        0,
    )
    extents, end = s13.drain(r.open_replay(x.publisher, acceptance, operation=op()), 4)
    assert extents == [(0, 2)] and end.extent == 2


def test_keys_survive_sessions_and_batch_sizes_without_double_effects(setup):
    if setup is None:
        return
    x = setup
    stream, first = stream_of(x, (3, 3, 1))
    one = issue(first, 1)
    first.send(one)
    first.confirm(one, operation=op())
    two = issue(first, 2)
    first.send(two)  # sink effects 1 and 2 committed, never confirmed locally
    keys = {e.position: e.key for e in two.effects}
    second = reopen(x, stream)
    assert second.position == 1 and second.ordinal == 2
    three = issue(second, 3)
    assert (three.start, three.stop, three.prior) == (1, 4, frozenset({1, 2}))
    assert all(keys[e.position] == e.key for e in three.effects if e.position in keys)
    statuses = second.send(three)
    # Prior occurrences are reconciled by query, the new one is submitted.
    assert statuses == {1: "PRESENT_MATCHING", 2: "PRESENT_MATCHING", 3: "COMMITTED"}
    second.confirm(three, operation=op())
    extents, waiting = probe.deliver(second, 2)
    assert extents == [(4, 6, ("COMMITTED", "COMMITTED")), (6, 7, ("COMMITTED",))]
    rows = probe.effects(x.sink)
    assert [row[0] for row in rows] == list(range(7))
    assert [row[3] for row in rows] == list(range(1, 8))  # one commit per occurrence
    connection = x.workspace.use()
    assert connection.execute(
        "SELECT position, basis FROM sink_observation ORDER BY position"
    ).fetchall() == [
        (0, "REPLY"),
        (1, "QUERY"),
        (2, "QUERY"),
        (3, "REPLY"),
        (4, "REPLY"),
        (5, "REPLY"),
        (6, "REPLY"),
    ]
    state = d.stream_state(x.workspace, stream)
    assert (state.position, state.unresolved) == (7, ())
    assert verify_store(x.workspace)["sink_observations"] == 7


def lost_after_commit(monkeypatch, positions, *, absent=()):
    """Injected lost reply: the effect is committed, the reply never arrives.
    `absent` positions fail before any effect (nothing committed)."""
    real = k.Sink.submit

    def submit(self, item):
        if item.position in absent:
            raise JobStoreError("INJECTED_UNAVAILABLE")
        reply = real(self, item)
        if item.position in positions:
            raise JobStoreError("INJECTED_LOST_REPLY")
        return reply

    monkeypatch.setattr(k.Sink, "submit", submit)
    return real


def test_frontier_counts_only_contiguous_local_confirmations(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (3,))
    real = lost_after_commit(monkeypatch, {1})
    item = issue(delivery, 3)
    assert delivery.send(item) == {0: "COMMITTED", 1: "UNKNOWN", 2: "COMMITTED"}
    assert item.outcome(1) == ("UNKNOWN", "INJECTED_LOST_REPLY")
    result = delivery.confirm(item, operation=op())
    # Sink effects 0, 1 and 2 exist; local confirmations 0 and 2 give frontier 1.
    assert [row[0] for row in probe.effects(x.sink)] == [0, 1, 2]
    assert (result.get("confirmed"), result.get("position")) == (2, 1)
    assert d.stream_state(x.workspace, stream).observed == ((0, 1), (2, 3))
    with pytest.raises(JobStoreError, match="DELIVERY_PENDING"):
        delivery.next(1, operation=op())
    with pytest.raises(JobStoreError, match="STREAM_NOTHING_TO_CONFIRM"):
        delivery.confirm(item, operation=op())
    monkeypatch.setattr(k.Sink, "submit", real)
    assert delivery.reconcile(item)[1] == "PRESENT_MATCHING"
    filled = delivery.confirm(item, operation=op())
    assert (filled.get("confirmed"), filled.get("position")) == (1, 3)
    assert delivery.pending is None and item.resolved
    # The lost reply is never recorded as received: the hole was filled by a
    # later query observation.
    outcome = item.outcome(1)
    assert outcome is not None and outcome[0] == "PRESENT_MATCHING"
    basis = (
        x.workspace.use()
        .execute(
            "SELECT position, basis, status FROM sink_observation ORDER BY position"
        )
        .fetchall()
    )
    assert basis == [
        (0, "REPLY", "COMMITTED"),
        (1, "QUERY", "PRESENT_MATCHING"),
        (2, "REPLY", "COMMITTED"),
    ]
    verify_store(x.workspace)


def test_partial_batch_ambiguity_completes_with_another_batch_size(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    stream, first = stream_of(x, (2, 2))
    real = lost_after_commit(monkeypatch, {1}, absent={2})
    item = issue(first, 4)
    assert first.send(item) == {
        0: "COMMITTED",
        1: "UNKNOWN",
        2: "UNKNOWN",
        3: "COMMITTED",
    }
    first.confirm(item, operation=op())
    assert first.position == 1
    monkeypatch.setattr(k.Sink, "submit", real)
    second = reopen(x, stream)
    again = issue(second, 2)
    assert (again.start, again.stop, again.prior) == (1, 3, frozenset({1, 2}))
    # 1 is found committed; 2 is absent in the exact incarnation, so it is
    # resubmitted once with the same key and payload.
    assert second.send(again) == {1: "PRESENT_MATCHING", 2: "COMMITTED"}
    assert second.confirm(again, operation=op()).get("position") == 4
    assert isinstance(second.next(2, operation=op()), d.Waiting)
    rows = probe.effects(x.sink)
    assert [(row[0], row[3]) for row in rows] == [(0, 1), (1, 2), (2, 4), (3, 3)]
    assert d.stream_state(x.workspace, stream).unresolved == ()
    verify_store(x.workspace)


def test_lost_reply_stays_unknown_and_reconciliation_is_bounded(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (2,))
    real = k.commit

    def lost(connection):
        real(connection)
        raise sqlite3.OperationalError("injected lost reply")

    monkeypatch.setattr(k, "commit", lost)
    item = issue(delivery, 2)
    assert delivery.send(item) == {0: "UNKNOWN", 1: "UNKNOWN"}
    assert item.outcome(0) == ("UNKNOWN", "SINK_COMMIT_UNKNOWN")
    assert item.outcome(1) == ("UNKNOWN", "SINK_RETIRED")  # the handle was retired
    monkeypatch.setattr(k, "commit", real)
    calls = []
    query = k.Sink.query

    def counted(self, item):
        calls.append(("query", item.position))
        return query(self, item)

    monkeypatch.setattr(k.Sink, "query", counted)
    # Still unavailable: one query per occurrence per explicit call, no retry.
    assert delivery.reconcile(item) == {0: "UNKNOWN", 1: "UNKNOWN"}
    assert calls == [("query", 0), ("query", 1)]
    assert d.stream_state(x.workspace, stream).position == 0
    # A fresh sink handle and acceptance: a new session queries and resubmits.
    x.sink.close()
    x.sink = k.open_sink(x.sink.root, expected_identity=x.sink.identity)
    fresh = reopen(x, stream)
    recovered = issue(fresh, 2)
    assert recovered.prior == frozenset({0, 1})
    assert fresh.send(recovered) == {0: "PRESENT_MATCHING", 1: "COMMITTED"}
    fresh.confirm(recovered, operation=op())
    outcome = item.outcome(0)
    assert fresh.position == 2 and outcome is not None and outcome[0] == "UNKNOWN"
    assert [row[0] for row in probe.effects(x.sink)] == [0, 1]
    verify_store(x.workspace)


def test_conflicting_sink_effects_are_never_confirmed(setup):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (3,))
    assert x.sink.submit(effect(x, 1, probe.synthetic_row(1, 5))).status == "COMMITTED"
    item = issue(delivery, 3)
    assert delivery.send(item) == {0: "COMMITTED", 1: "CONFLICT", 2: "COMMITTED"}
    delivery.confirm(item, operation=op())
    assert delivery.position == 1 and delivery.pending is item
    assert delivery.reconcile(item) == {0: "COMMITTED", 1: "CONFLICT", 2: "COMMITTED"}
    with pytest.raises(JobStoreError, match="DELIVERY_PENDING"):
        delivery.next(1, operation=op())
    with pytest.raises(JobStoreError, match="STREAM_OBLIGATION_UNRESOLVED"):
        d.retire_stream(x.publisher, stream, operation=op())
    state = d.stream_state(x.workspace, stream)
    assert (state.position, state.unresolved, state.retired) == (1, ((1, 2),), False)
    stored = (
        x.sink.use()
        .execute("SELECT payload FROM effect WHERE position = 1")
        .fetchone()[0]
    )
    assert stored == probe.synthetic_row(1, 5)


# ---------------------------------------------------------------------------
# Authority


def test_acceptances_reject_every_wrong_correspondence(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    probe.capture(x.workspace, x.publisher, x.generation, x.binding, (2,))
    for overrides, code in (
        ({"instance": w.new_identity("snk")}, "SINK_DESTINATION"),
        ({"namespace": "other"}, "SINK_DESTINATION"),
        ({"epoch": 2}, "SINK_DESTINATION"),
        ({"retention": k.retention_descriptor(1, 2)}, "SINK_DESTINATION"),
        ({"purpose": ""}, "ACCEPTANCE_PURPOSE"),
        ({"seconds": 0}, "ACCEPTANCE_BOUND"),
        ({"seconds": d.MAX_ACCEPTANCE_SECONDS + 1}, "ACCEPTANCE_BOUND"),
    ):
        with pytest.raises(JobStoreError, match=code):
            probe.accept_sink(x.sink, **overrides)
    with pytest.raises(JobStoreError, match="SINK_UNKNOWN"):
        d.accept_sink(object(), **probe.expected(x.sink), purpose="p", seconds=1)  # type: ignore[arg-type]
    for overrides, code in (
        ({"expected_pin": "0" * 64}, "JOB_TRUST_INPUT"),
        ({"accepted_producer": "pietto-other"}, "JOB_TRUST_INPUT"),
        ({"route": "postgres_adbc"}, "ACCEPTANCE_ROUTE"),
        ({"values": (2,)}, "BINDING_VECTOR"),
        ({"values": (True,)}, "BINDING_VECTOR"),
        ({"batch_rows": 0}, "ACCEPTANCE_BOUND"),
        ({"purpose": "line\n"}, "ACCEPTANCE_PURPOSE"),
        ({"checkpoint": "ckp-1"}, "CHECKPOINT_UNKNOWN"),
    ):
        with pytest.raises(JobStoreError, match=code):
            window(x, **overrides)
    read, sink = window(x), probe.accept_sink(x.sink)
    for item in (read, sink):
        for call in (lambda: copy.copy(item), lambda: pickle.dumps(item)):
            with pytest.raises(JobStoreError, match="ACCEPTANCE_COPY"):
                call()
    forged = object.__new__(d.SinkAcceptance)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_UNKNOWN"):
        d.register_stream(x.publisher, read, forged, operation=op())
    foreign = probe.accept_sink(x.sink)
    object.__setattr__(foreign, "_pid", -1)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_FOREIGN_PROCESS"):
        d.register_stream(x.publisher, read, foreign, operation=op())
    other_job = s.register_job(x.workspace, x.template, operation=op()).get("job")
    other = s.claim_publisher(x.workspace, other_job, operation=op())
    try:
        with pytest.raises(JobStoreError, match="ACCEPTANCE_SUBJECT"):
            d.register_stream(other, read, sink, operation=op())
    finally:
        other.close()
    stream = d.register_stream(x.publisher, read, sink, operation=op()).get("stream")
    with pytest.raises(JobStoreError, match="STREAM_EXISTS"):
        d.register_stream(x.publisher, window(x), sink, operation=op())
    assert (
        d.find_stream(
            x.workspace,
            x.job,
            x.generation,
            sink=x.sink.identity,
            namespace=x.sink.namespace,
            epoch=x.sink.epoch,
        )
        == stream
    )
    # A replacement sink at the same place (same namespace and epoch) is
    # another incarnation: it cannot reopen the old registration.
    root = x.sink.root
    x.sink.close()
    os.rename(root, root + ".old")
    x.sink = probe.sink(root)
    replaced = probe.accept_sink(x.sink)
    with pytest.raises(JobStoreError, match="SINK_DESTINATION"):
        d.open_stream(x.publisher, stream, replaced, operation=op())
    # A deliberately different epoch is a different contract (new stream).
    newer = probe.sink(x.root / "newer", epoch=2)
    try:
        assert (
            d.register_stream(
                x.publisher, window(x), probe.accept_sink(newer), operation=op()
            ).get("stream")
            != stream
        )
    finally:
        newer.close()
    verify_store(x.workspace)


def test_validity_is_bounded_by_clocks_and_sink_retention(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    clock = {"wall": float(x.sink.retained_until - 100), "mono": 50.0}
    monkeypatch.setattr(d, "_wall", lambda: clock["wall"])
    monkeypatch.setattr(d, "_monotonic", lambda: clock["mono"])
    monkeypatch.setattr(k, "_wall", lambda: clock["wall"])
    stream, delivery = stream_of(x, (2, 2))
    item = issue(delivery, 2)
    # The sink contract ends before the session's own 600 s: nothing is sent.
    clock["wall"] += 100
    assert delivery.send(item) == {0: "NOT_SENT"}
    assert item.outcome(0) == ("NOT_SENT", "RETENTION_EXPIRED")
    assert probe.effects(x.sink) == []
    clock["wall"] -= 50
    # A wall-clock rollback cannot lengthen a session: the monotonic bound holds.
    clock["mono"] += 601
    with pytest.raises(JobStoreError, match="ACCEPTANCE_EXPIRED"):
        d._accepted(delivery.window_acceptance, d.WindowAcceptance)
    clock["mono"] = 0.0
    clock["wall"] += 601
    with pytest.raises(JobStoreError, match="ACCEPTANCE_EXPIRED"):
        d._accepted(delivery.sink, d.SinkAcceptance)
    assert d.stream_state(x.workspace, stream).unresolved == ((0, 2),)


def test_stale_sessions_publishers_and_foreign_items_cannot_progress(setup):
    if setup is None:
        return
    x = setup
    stream, old = stream_of(x, (2, 2))
    item = issue(old, 2)
    old.send(item)
    newer = reopen(x, stream)
    for call in (
        lambda: old.confirm(item, operation=op()),
        lambda: old.adopt(window(x), operation=op()),
    ):
        with pytest.raises(JobStoreError, match="STREAM_SESSION_STALE"):
            call()
    with pytest.raises(JobStoreError, match="DELIVERY_PENDING"):
        old.next(1, operation=op())
    for call in (
        lambda: newer.confirm(item, operation=op()),
        lambda: newer.send(item),
        lambda: newer.reconcile(item),
        lambda: newer.acknowledge(item, operation=op()),
    ):
        with pytest.raises(JobStoreError, match="ISSUANCE_FOREIGN"):
            call()
    # Old replies cannot be grafted: a new issuance compares its own digests.
    mine = issue(newer, 2)
    assert mine.prior == frozenset({0, 1})
    operation = op()
    assert newer.send(mine) == {0: "PRESENT_MATCHING", 1: "PRESENT_MATCHING"}
    newer.confirm(mine, operation=operation)
    later = issue(newer, 2)
    newer.send(later)
    with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
        newer.confirm(later, operation=operation)
    os.close(x.publisher._fd)  # the lock is lost while the handle still exists
    handle = w.open_workspace(x.workspace.root, expected_identity=x.workspace.identity)
    try:
        claimed = s.claim_publisher(handle, x.job, operation=op())
        with pytest.raises(JobStoreError, match="PUBLISHER_STALE"):
            newer.confirm(later, operation=op())
        state = d.stream_state(handle, stream)
        assert (state.position, state.unresolved) == (2, ((2, 4),))
        claimed.close()
    finally:
        x.publisher._closed = True
        handle.close()


@pytest.mark.parametrize("event", ["cancel", "release", "expire"])
@pytest.mark.parametrize(
    "phase", ["before_issue", "decode_issue", "issue_send", "send_confirm"]
)
def test_authority_changes_refuse_new_sends_and_receipts(
    setup, monkeypatch, event, phase
):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (2, 2))
    code = {
        "cancel": "JOB_STATE",
        "release": "STREAM_RELEASED",
        "expire": "ACCEPTANCE_EXPIRED",
    }[event]

    def trigger():
        if event == "cancel":
            s.cancel_job(x.publisher, operation=op())
        elif event == "release":
            c.release_retention(x.publisher, delivery.window.retention, operation=op())
        else:
            monkeypatch.setattr(d, "_monotonic", lambda: float("inf"))

    if phase == "before_issue":
        trigger()
        with pytest.raises(JobStoreError, match=code):
            delivery.next(2, operation=op())
    elif phase == "decode_issue":
        step = r._rebatch

        def decoded(source, start, stop):
            value = step(source, start, stop)
            trigger()
            return value

        monkeypatch.setattr(r, "_rebatch", decoded)
        with pytest.raises(JobStoreError, match=code):
            delivery.next(2, operation=op())
    elif phase == "issue_send":
        item = issue(delivery, 2)
        trigger()
        assert delivery.send(item) == {0: "NOT_SENT"}
        assert item.outcome(0) == ("NOT_SENT", code)
    else:
        item = issue(delivery, 2)
        assert delivery.send(item) == {0: "COMMITTED", 1: "COMMITTED"}
        trigger()
        with pytest.raises(JobStoreError, match=code):
            delivery.confirm(item, operation=op())
        # The external effects stay; no compensation, no local progress.
        assert [row[0] for row in probe.effects(x.sink)] == [0, 1]
    state = d.stream_state(x.workspace, stream)
    assert state.position == 0 and state.observed == ()
    assert len(state.issuances) == (
        0 if phase in ("before_issue", "decode_issue") else 1
    )
    # Historical queries still observe without granting a send or a receipt.
    found = x.sink.query(effect(x, 0))
    assert found.status == (
        "PRESENT_MATCHING" if phase == "send_confirm" else "ACTIVE_NOT_FOUND"
    )
    assert c.classify_files(x.workspace)["missing"] == ()
    verify_store(x.workspace)


# ---------------------------------------------------------------------------
# Injected local and sink faults


@pytest.mark.parametrize("call", ["issue", "confirm", "adopt"])
@pytest.mark.parametrize("injection", ["before_commit", "after_commit"])
def test_ambiguous_local_commits_leave_zero_or_one_queryable_effect(
    setup, monkeypatch, call, injection
):
    if setup is None:
        return
    x = setup
    session, _results = probe.capture(
        x.workspace, x.publisher, x.generation, x.binding, (2,), eof=False
    )
    stream, delivery = probe.registered(
        x.workspace, x.job, x.publisher, x.generation, x.built, x.sink
    )
    item = grown = None
    if call == "confirm":
        item = issue(delivery, 2)
        delivery.send(item)
    if call == "adopt":
        probe.deliver(delivery, 2)
        published = session.publish(s12.stage_frame(session, 2), operation=op())
        grown = window(x, published.get("checkpoint"))
    real = w.commit

    def commit(connection):
        if injection == "after_commit":
            real(connection)
        raise sqlite3.OperationalError("injected lost reply")

    operation = op()
    monkeypatch.setattr(w, "commit", commit)
    with pytest.raises(JobStoreError, match="STORE_COMMIT_UNKNOWN"):
        if call == "issue":
            delivery.next(2, operation=operation)
        elif call == "confirm":
            assert item is not None
            delivery.confirm(item, operation=operation)
        else:
            delivery.adopt(grown, operation=operation)  # type: ignore[arg-type]
    monkeypatch.setattr(w, "commit", real)
    with pytest.raises(JobStoreError, match="WORKSPACE_RETIRED"):
        d.stream_state(x.workspace, stream)
    x.publisher.close()
    fresh = w.open_workspace(x.workspace.root, expected_identity=x.workspace.identity)
    try:
        committed = injection == "after_commit"
        assert (s.query_operation(fresh, operation) is not None) is committed
        state = d.stream_state(fresh, stream)
        if call == "issue":
            assert len(state.issuances) == int(committed) and state.position == 0
            assert probe.effects(x.sink) == []  # never sent guessed work
        elif call == "confirm":
            assert state.position == (2 if committed else 0)
            assert [row[0] for row in probe.effects(x.sink)] == [0, 1]
        else:
            assert len(state.windows) == 1 + int(committed) and state.position == 2
        verify_store(fresh)
    finally:
        fresh.close()


def test_sink_busy_full_budget_and_close_failures_keep_state(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (2, 2))
    item = issue(delivery, 4)
    blocker = sqlite3.connect(os.path.join(x.sink.root, "sink.sqlite"), timeout=0)
    x.sink._connection.execute("PRAGMA busy_timeout = 100")
    try:
        blocker.execute("BEGIN IMMEDIATE")
        assert delivery.send(item) == {p: "UNKNOWN" for p in range(4)}
        assert item.outcome(0) == ("UNKNOWN", "STORE_BUSY")
    finally:
        blocker.rollback()
        blocker.close()

    def over_budget(self, payload):
        raise JobStoreError("SINK_BUDGET")

    with monkeypatch.context() as patch:
        patch.setattr(k.Sink, "_admit", over_budget)
        assert delivery.reconcile(item) == {p: "UNKNOWN" for p in range(4)}
        assert item.outcome(3) == ("UNKNOWN", "SINK_BUDGET")
    real = x.sink._connection

    class Full:
        def execute(self, sql, *args):
            if sql.startswith("INSERT INTO effect"):
                error = sqlite3.OperationalError("injected full")
                error.sqlite_errorname = "SQLITE_FULL"  # type: ignore[attr-defined]
                raise error
            return real.execute(sql, *args)

        def close(self):
            real.close()

    x.sink._connection = Full()  # type: ignore[assignment]
    assert delivery.reconcile(item)[0] == "UNKNOWN"
    assert item.outcome(0) == ("UNKNOWN", "STORE_FULL")
    x.sink._connection = real
    assert delivery.reconcile(item) == {p: "COMMITTED" for p in range(4)}
    delivery.confirm(item, operation=op())
    # Local data admission keeps the control reserve; retirement still works.
    with monkeypatch.context() as patch:
        patch.setattr(w, "accounted_bytes", lambda ws: ws.budget - w.CONTROL_RESERVE)
        with pytest.raises(JobStoreError, match="WORKSPACE_BUDGET"):
            reopen(x, stream)
        d.retire_stream(x.publisher, stream, operation=op())
    assert d.stream_state(x.workspace, stream).retired

    class Closing:
        def close(self):
            raise sqlite3.OperationalError("injected close")

    x.sink._connection = Closing()  # type: ignore[assignment]
    with pytest.raises(JobStoreError, match="SINK_CLOSE"):
        x.sink.close()
    real.close()
    again = k.open_sink(x.sink.root, expected_identity=x.sink.identity)
    assert [row[0] for row in probe.effects(again)] == [0, 1, 2, 3]
    x.sink = again
    verify_store(x.workspace)


# ---------------------------------------------------------------------------
# Protection and retirement


def test_protection_holds_until_explicit_retirement_and_deletes_nothing(setup):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (2, 2))
    delivery.next(2, operation=op())  # issued, never sent
    files = c.classify_files(x.workspace)
    with pytest.raises(JobStoreError, match="STREAM_OBLIGATION_UNRESOLVED"):
        d.retire_stream(x.publisher, stream, operation=op())
    delivery.close()  # a local close releases nothing
    state = d.stream_state(x.workspace, stream)
    assert state.unresolved == ((0, 2),) and not any(wd[5] for wd in state.windows)
    newer = reopen(x, stream)
    again = issue(newer, 4)
    assert again.prior == frozenset({0, 1})
    newer.send(again)
    newer.confirm(again, operation=op())
    operation = op()
    retired = d.retire_stream(x.publisher, stream, operation=operation)
    assert retired.get("released") == 1 and retired.get("position") == 4
    assert d.retire_stream(x.publisher, stream, operation=operation).observation == (
        "PREVIOUSLY_COMMITTED"
    )
    with pytest.raises(JobStoreError, match="STREAM_RETIRED"):
        d.retire_stream(x.publisher, stream, operation=op())
    state = d.stream_state(x.workspace, stream)
    assert state.retired and all(wd[5] for wd in state.windows)
    for call in (
        lambda: reopen(x, stream),
        lambda: newer.adopt(window(x), operation=op()),
        lambda: newer._live(),
    ):
        with pytest.raises(JobStoreError, match="STREAM_RETIRED"):
            call()
    # Release changes metadata only; every referenced file stays.
    after = c.classify_files(x.workspace)
    assert after["referenced"] == files["referenced"] and after["missing"] == ()
    verify_store(x.workspace)


# ---------------------------------------------------------------------------
# S13 bridge


def test_s13_delivery_is_acknowledged_only_after_sink_confirmation(setup):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (2, 2, 2))
    acceptance = s13.accept(x.workspace, x.job, x.generation, x.built)
    r.register_consumer(x.publisher, acceptance, operation=op())
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    offered = s13.issue(replay, 3)
    item = delivery.bridge(offered, operation=op())
    assert (item.start, item.stop, item.delivery, item.window) == (
        0,
        3,
        offered.identity,
        None,
    )
    with pytest.raises(JobStoreError, match="STREAM_UNCONFIRMED"):
        delivery.acknowledge(item, operation=op())
    assert delivery.send(item) == {p: "COMMITTED" for p in range(3)}
    delivery.confirm(item, operation=op())
    acknowledged = delivery.acknowledge(item, operation=op())
    assert acknowledged.get("position") == 3
    assert r.consumer_state(x.workspace, acceptance.consumer).position == 3
    # A crash between confirmation and acknowledgement redelivers [3, 6) once
    # confirmed: the sink key prevents a second effect.
    second = s13.issue(replay, 3)
    bridged = delivery.bridge(second, operation=op())
    delivery.send(bridged)
    delivery.confirm(bridged, operation=op())
    replay.close()
    again = r.open_replay(x.publisher, acceptance, operation=op())
    redelivered = s13.issue(again, 3)
    assert redelivered.occurrences == second.occurrences
    fresh = reopen(x, stream, read=False)
    resent = fresh.bridge(redelivered, operation=op())
    assert resent.confirmed == frozenset({3, 4, 5}) and resent.resolved
    assert fresh.send(resent) == {}
    fresh.acknowledge(resent, operation=op())
    assert r.consumer_state(x.workspace, acceptance.consumer).position == 6
    assert [row[0] for row in probe.effects(x.sink)] == list(range(6))
    with pytest.raises(JobStoreError, match="DELIVERY_FOREIGN"):
        fresh.bridge(redelivered, operation=op())
    verify_store(x.workspace)


def test_an_unrelated_r1_cursor_proves_no_sink_effect(setup):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (2, 2))
    acceptance = s13.accept(x.workspace, x.job, x.generation, x.built)
    r.register_consumer(x.publisher, acceptance, operation=op())
    s13.drain(r.open_replay(x.publisher, acceptance, operation=op()), 4)
    assert r.consumer_state(x.workspace, acceptance.consumer).position == 4
    state = d.stream_state(x.workspace, stream)
    assert (state.position, state.observed) == (0, ())
    assert probe.effects(x.sink) == []
    extents, waiting = probe.deliver(delivery, 4)
    assert extents == [(0, 4, ("COMMITTED",) * 4)] and waiting.position == 4


# ---------------------------------------------------------------------------
# Provisional relay: committed chunks reach the sink before the source ends


def test_relay_delivers_before_the_source_ends_and_blocks_on_unknown(
    setup, monkeypatch
):
    if setup is None:
        return
    x = setup
    attempt = s.open_attempt(x.publisher, x.generation, x.binding, operation=op())
    capture = c.begin_capture(
        x.publisher, attempt, s12.pg_owner(x.binding), operation=op()
    )
    plan = [2, 2, 1]
    pulls = []

    def staged(session):
        # ARROW_FREE_STORAGE_STEP stand-in for one checked owner batch.
        pulls.append(len(plan))
        if not plan:
            session._terminal = "EOF"
            return None
        return s12.stage_frame(session, plan.pop(0))

    monkeypatch.setattr(c.CaptureSession, "stage", staged)
    stream = d.register_stream(
        x.publisher, window(x, None), probe.accept_sink(x.sink), operation=op()
    ).get("stream")
    session = d.open_stream(
        x.publisher, stream, probe.accept_sink(x.sink), operation=op()
    )
    trust = dict(
        purpose="s15-deliver",
        route="postgres_rows",
        values=(1,),
        seconds=600,
        batch_rows=4096,
        **s13.trust(x.built),
    )
    steps = [d.relay(session, capture, rows=4, **trust) for _ in range(2)]
    assert steps == ["COMMITTED_CHUNK", "DELIVERED"]
    # Effects for [0, 2) are committed while the source has not ended.
    assert capture.terminal is None and [row[0] for row in probe.effects(x.sink)] == [
        0,
        1,
    ]
    assert len(pulls) == 1
    real = lost_after_commit(monkeypatch, {2})
    assert d.relay(session, capture, rows=4, **trust) == "COMMITTED_CHUNK"
    assert d.relay(session, capture, rows=4, **trust) == "BLOCKED"
    # Blocked: further relay steps pull no source batch.
    for _ in range(3):
        assert d.relay(session, capture, rows=4, **trust) == "BLOCKED"
    assert len(pulls) == 2 and session.position == 2
    monkeypatch.setattr(k.Sink, "submit", real)
    pending = session.pending
    assert pending is not None and session.reconcile(pending)[2] == "PRESENT_MATCHING"
    session.confirm(pending, operation=op())
    results = []
    while True:
        step = d.relay(session, capture, rows=4, **trust)
        results.append(step)
        if step in ("SOURCE_TERMINAL", "BLOCKED"):
            break
    assert results == ["COMMITTED_CHUNK", "DELIVERED", "SOURCE_TERMINAL"]
    assert capture.terminal == "EOF" and session.position == 5
    assert [row[0] for row in probe.effects(x.sink)] == list(range(5))
    with pytest.raises(JobStoreError, match="STREAM_CAPTURE"):
        d.relay(session, object(), rows=1, **trust)  # type: ignore[arg-type]
    verify_store(x.workspace)


def test_relay_never_pulls_past_an_unread_adopted_window(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    attempt = s.open_attempt(x.publisher, x.generation, x.binding, operation=op())
    capture = c.begin_capture(
        x.publisher, attempt, s12.pg_owner(x.binding), operation=op()
    )
    first = capture.publish(s12.stage_frame(capture, 2), operation=op())
    pulls = []
    monkeypatch.setattr(c.CaptureSession, "stage", lambda session: pulls.append(1))
    stream = d.register_stream(
        x.publisher, window(x), probe.accept_sink(x.sink), operation=op()
    ).get("stream")
    session = d.open_stream(
        x.publisher, stream, probe.accept_sink(x.sink), operation=op()
    )
    session.adopt(window(x, first.get("checkpoint")), operation=op())
    # A session without read permission for the adopted window cannot deliver
    # it, so it must not pull more of the source either.
    bare = d.open_stream(x.publisher, stream, probe.accept_sink(x.sink), operation=op())
    trust = dict(
        purpose="s15-deliver",
        route="postgres_rows",
        values=(1,),
        seconds=600,
        batch_rows=4096,
        **s13.trust(x.built),
    )
    with pytest.raises(JobStoreError, match="STREAM_READ_REQUIRED"):
        d.relay(bare, capture, rows=2, **trust)
    assert pulls == [] and probe.effects(x.sink) == []
    assert d.stream_state(x.workspace, stream).position == 0


# ---------------------------------------------------------------------------
# Independent history replay


@pytest.mark.parametrize(
    "damage,category",
    [
        ("window_stop", "WINDOW_HISTORY"),
        ("window_checkpoint", "WINDOW_HISTORY"),
        ("session_position", "STREAM_SESSION_HISTORY"),
        ("issuance_range", "STREAM_ISSUANCE_HISTORY"),
        ("issuance_digest", "STREAM_ISSUANCE_HISTORY"),
        ("observation_commit", "OBSERVATION_HISTORY"),
        ("observation_forged", "DELIVERY_ROWS"),
        ("observation_deleted", "OBSERVATION_HISTORY"),
        ("retirement_forged", "DELIVERY_ROWS"),
        ("stream_epoch", "STREAM_HISTORY"),
    ],
)
def test_independent_history_replay_rejects_delivery_damage(setup, damage, category):
    if setup is None:
        return
    x = setup
    stream, delivery = stream_of(x, (2, 2, 2))
    item = issue(delivery, 2)
    delivery.send(item)
    delivery.confirm(item, operation=op())
    delivery.next(2, operation=op())  # issued, never confirmed
    verify_store(x.workspace)
    connection = x.workspace.use()
    connection.execute("PRAGMA foreign_keys = OFF")
    if damage == "window_stop":
        connection.execute("UPDATE stream_window SET stop = 4")
    elif damage == "window_checkpoint":
        older = connection.execute(
            "SELECT identity FROM checkpoint ORDER BY ordinal LIMIT 1"
        ).fetchone()[0]
        connection.execute("UPDATE stream_window SET checkpoint = ?", (older,))
    elif damage == "session_position":
        connection.execute("UPDATE stream_session SET position = 1")
    elif damage == "issuance_range":
        connection.execute("UPDATE stream_issuance SET stop = 3 WHERE start = 0")
    elif damage == "issuance_digest":
        connection.execute("UPDATE stream_issuance SET digest = ?", ("0" * 64,))
    elif damage == "observation_commit":
        connection.execute(
            "UPDATE sink_observation SET commit_identity = ? WHERE position = 1",
            (w.new_identity("skc"),),
        )
    elif damage == "observation_forged":
        connection.execute(
            "INSERT INTO sink_observation SELECT stream, 2, issuance, session, basis,"
            " status, ?, 9, digest, publisher_epoch FROM sink_observation"
            " WHERE position = 1",
            (w.new_identity("skc"),),
        )
    elif damage == "observation_deleted":
        connection.execute("DELETE FROM sink_observation WHERE position = 0")
    elif damage == "retirement_forged":
        connection.execute(
            "INSERT INTO stream_retirement VALUES (?, 2, ?, ?)",
            (stream, x.publisher.epoch, x.publisher.instance),
        )
    else:
        connection.execute("UPDATE stream SET epoch = 2")
    connection.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(JobStoreError, match="STORE_INVARIANT_" + category):
        verify_store(x.workspace)
