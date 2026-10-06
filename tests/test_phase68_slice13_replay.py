"""S13 R1 replay protocol: v3 boundary, fresh acceptance, fixed scope, issuance,
explicit acknowledgement, fences, expiry, faults and independent history replay.

Saved inputs use S12's Arrow-free storage step and the replay data step is the
labelled ARROW_FREE_REPLAY_STEP; real checked Arrow replay, seven scalars,
refined coordinates and chunk damage run in the Arrow-only replay profile
(`scripts/phase68_slice13_probe.py`). Pure interval laws run on every host.
"""

import copy
import dataclasses
import json
import os
import pickle
import sqlite3
from types import SimpleNamespace

import pytest

import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice13_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from pietto._project import project_job_capture as c
from pietto._project import project_job_replay as r
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

op = probe.op


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(
        tmp_path_factory.mktemp("s13-replay") / "small", entry="bundle"
    )


@pytest.fixture
def setup(tmp_path, built, monkeypatch):
    if not qualified(tmp_path):
        yield None
        return
    probe.arrow_free(monkeypatch)
    template, compiled = built
    workspace, job, publisher, binding, record, generation = probe.store(
        tmp_path / "workspace", template
    )
    yield SimpleNamespace(
        workspace=workspace,
        job=job,
        publisher=publisher,
        binding=binding,
        record=record,
        generation=generation,
        built=compiled,
        template=template,
    )
    publisher.close()
    workspace.close()


def accept(x, **overrides):
    return probe.accept(x.workspace, x.job, x.generation, x.built, **overrides)


def registered(x, sizes=(2, 2), **overrides):
    probe.capture(x.workspace, x.publisher, x.generation, x.binding, sizes)
    acceptance = accept(x, **overrides)
    result = r.register_consumer(x.publisher, acceptance, operation=op())
    return acceptance, result


def test_plan_covers_every_extent_of_a_contiguous_prefix_exactly():
    members = [SimpleNamespace(start=a, stop=b) for a, b in ((0, 2), (2, 4), (4, 5))]
    for start in range(5):
        for stop in range(start + 1, 6):
            slices = r.plan(members, start, stop)
            assert [
                members[i].start + offset + k
                for i, offset, rows in slices
                for k in range(rows)
            ] == list(range(start, stop))
            assert all(
                rows > 0 and offset + rows <= members[i].stop - members[i].start
                for i, offset, rows in slices
            )
            assert [i for i, _o, _n in slices] == sorted({i for i, _o, _n in slices})
    assert r.plan(members, 3, 5) == ((1, 1, 1), (2, 0, 1))
    assert r.plan(members, 1, 2) == ((0, 1, 1),)
    hole = [SimpleNamespace(start=0, stop=2), SimpleNamespace(start=4, stop=6)]
    assert r.plan(hole, 0, 2) == ((0, 0, 2),)
    for start, stop in ((1, 5), (2, 3)):
        with pytest.raises(JobStoreError, match="CHECKPOINT_MEMBERS"):
            r.plan(hole, start, stop)
    with pytest.raises(JobStoreError, match="CHECKPOINT_MEMBERS"):
        r.plan(members, 4, 6)
    assert r.plan([SimpleNamespace(start=0, stop=0)], 0, 0) == ()
    assert all(
        w.valid_identity(w.new_identity(kind), kind) for kind in ("csm", "rps", "dlv")
    )
    assert w.valid_identity(r.new_consumer(), "csm")
    assert not w.valid_identity(r.new_consumer(), "rps")


def test_v3_is_explicit_and_v1_v2_refuse_replay_unchanged(tmp_path, built):
    if not qualified(tmp_path):
        return
    template, compiled = built
    v3 = w.create_workspace(str(tmp_path / "v3"), format=w.FORMAT_V3)
    try:
        assert json.loads((tmp_path / "v3" / "workspace.json").read_bytes()) == {
            "budget": w.DEFAULT_BUDGET,
            "database": "store.sqlite",
            "features": ["result-chunks", "saved-replay"],
            "format": "pietto.job-workspace.v3",
            "identity": v3.identity,
        }
        connection = v3.use()
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert tuple(
            connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
            )
        ) == w.expected_schema(w.FORMAT_V3)
        assert set(w.expected_schema(w.FORMAT_V2)) < set(w.expected_schema(w.FORMAT_V3))
        assert w.supports(v3, "result-chunks") and w.supports(v3, "saved-replay")
    finally:
        v3.close()
    assert sorted(os.listdir(tmp_path / "v3")) == [
        "chunks",
        "locks",
        "staging",
        "store.sqlite",
        "workspace.json",
    ]
    for format, version in ((w.FORMAT, 1), (w.FORMAT_V2, 2)):
        root = tmp_path / ("v" + str(version))
        workspace, job, publisher, _binding, _record, generation = s12.store(
            root, template, (1,), format=format
        )
        try:
            schema = w.expected_schema(format)
            assert not w.supports(workspace, "saved-replay")
            for call in (
                lambda: r.consumer_state(workspace, r.new_consumer()),
                lambda: r.register_consumer(publisher, None, operation=op()),  # type: ignore[arg-type]
                lambda: r.open_replay(publisher, None, operation=op()),  # type: ignore[arg-type]
                lambda: r.accept_saved_read(
                    workspace,
                    job,
                    generation,
                    checkpoint=w.new_identity("ckp"),
                    consumer=r.new_consumer(),
                    scope="committed_prefix",
                    extent=0,
                    purpose="p",
                    route="postgres_rows",
                    values=(1,),
                    seconds=60,
                    batch_rows=1,
                    **probe.trust(compiled),
                ),
            ):
                with pytest.raises(JobStoreError, match="WORKSPACE_REPLAY_FORMAT"):
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
        assert "consumer" not in str(s12.tree(root))


def test_a_runtime_without_v3_refuses_it_before_sqlite(tmp_path, monkeypatch):
    if not qualified(tmp_path):
        return
    root = tmp_path / "v3"
    workspace = w.create_workspace(str(root), format=w.FORMAT_V3)
    workspace.close()
    before = s12.tree(root)
    monkeypatch.setattr(
        w, "VERSIONS", {k: v for k, v in w.VERSIONS.items() if k != w.FORMAT_V3}
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("SQLite opened before the envelope was accepted")

    monkeypatch.setattr(w, "_connect", forbidden)
    with pytest.raises(JobStoreError, match="WORKSPACE_FORMAT"):
        w.open_workspace(str(root), expected_identity=workspace.identity)
    assert s12.tree(root) == before
    monkeypatch.undo()
    for bad in ("pietto.job-workspace.v6", "pietto.job-workspace.v3 "):
        with pytest.raises(JobStoreError, match="WORKSPACE_FORMAT"):
            w.create_workspace(str(tmp_path / "other"), format=bad)
    assert not (tmp_path / "other").exists()


def test_required_example_resumes_at_the_acknowledged_frontier(setup):
    if setup is None:
        return
    x = setup
    acceptance, result = registered(x, (2, 2, 2, 1))
    assert (acceptance.extent, result.get("extent")) == (7, 7)
    first = r.open_replay(x.publisher, acceptance, operation=op())
    one = probe.issue(first, 2)
    assert (one.start, one.stop) == (0, 2)
    assert one.occurrences == ((x.generation, 0), (x.generation, 1))
    first.acknowledge(one, operation=op())
    offered = probe.issue(first, 2)
    assert (offered.start, offered.stop, first.position) == (2, 4, 2)
    # Session A never acknowledges [2, 4); B starts at the committed frontier.
    second = r.open_replay(x.publisher, acceptance, operation=op())
    assert (second.position, second.ordinal, second.start) == (2, 2, 2)
    with pytest.raises(JobStoreError, match="REPLAY_SESSION_STALE"):
        first.acknowledge(offered, operation=op())
    with pytest.raises(JobStoreError, match="DELIVERY_FOREIGN"):
        second.acknowledge(offered, operation=op())
    extents, end = probe.drain(second, 3)
    assert extents == [(2, 5), (5, 7)]
    assert (end.terminal, end.acknowledged, end.extent, end.verified) == (
        "SAVED_SCOPE_EXHAUSTED",
        7,
        7,
        (2, 7),
    )
    assert (end.scope, end.observed_end, end.holes, end.schema) == (
        "complete_capture",
        7,
        (),
        None,
    )
    # Historical remote layers stay UNKNOWN after local success.
    layers = dict(end.layers)
    assert layers["attempt_terminal"] is None
    assert {layers[n] for n in ("source", "transaction", "delivery")} == {"UNKNOWN"}
    state = r.consumer_state(x.workspace, acceptance.consumer)
    assert (state.position, state.acknowledged) == (7, ((0, 2), (2, 5), (5, 7)))
    assert [i[2:] for i in state.issued] == [
        (0, 2, True),
        (2, 4, False),
        (2, 5, True),
        (5, 7, True),
    ]
    assert [ss[1:] for ss in state.sessions] == [(1, 0), (2, 2)]
    assert len({i[0] for i in state.issued}) == 4
    third = r.open_replay(x.publisher, acceptance, operation=op())
    late = probe.end(third)
    assert (late.acknowledged, late.verified) == (7, (7, 7))
    summary = verify_store(x.workspace)
    assert (
        summary["consumers"],
        summary["sessions"],
        summary["issuances"],
        summary["acknowledgements"],
    ) == (1, 3, 4, 3)


def test_reading_yielding_the_end_and_close_never_acknowledge(setup):
    if setup is None:
        return
    x = setup
    acceptance, _ = registered(x)
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    whole = probe.issue(replay, 4)
    assert (whole.start, whole.stop) == (0, 4)
    with pytest.raises(JobStoreError, match="DELIVERY_PENDING"):
        replay.next(1, operation=op())
    assert replay.position == 0 and whole.batch.closed is False
    replay.close()
    replay.close()
    with pytest.raises(JobStoreError, match="REPLAY_CLOSED"):
        replay.next(1, operation=op())
    state = r.consumer_state(x.workspace, acceptance.consumer)
    assert (state.position, [i[2:] for i in state.issued]) == (0, [(0, 4, False)])
    again = r.open_replay(x.publisher, acceptance, operation=op())
    redelivered = probe.issue(again, 4)
    assert redelivered.occurrences == whole.occurrences
    assert redelivered.identity != whole.identity
    assert (redelivered.session, redelivered.operation) != (
        whole.session,
        whole.operation,
    )
    for bad in (0, 4097, True, 2.0):
        with pytest.raises(JobStoreError, match="DELIVERY_PENDING"):
            again.next(bad, operation=op())  # type: ignore[arg-type]
    again.acknowledge(redelivered, operation=op())
    for bad in (0, 4097, True):
        assert type(again.next(bad, operation=op())) is r.SavedScopeEnd
    assert r.consumer_state(x.workspace, acceptance.consumer).position == 4


def test_row_bounds_are_checked_before_reading(setup):
    if setup is None:
        return
    x = setup
    acceptance, _ = registered(x, batch_rows=3)
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    for bad in (0, 4, True, 2.0, None):
        with pytest.raises(JobStoreError, match="REPLAY_ROWS"):
            replay.next(bad, operation=op())  # type: ignore[arg-type]
    assert r.consumer_state(x.workspace, acceptance.consumer).issued == ()


def test_acknowledgement_replays_only_its_fact_and_rejects_others(setup):
    if setup is None:
        return
    x = setup
    acceptance, _ = registered(x, (2, 2, 2))
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    first = probe.issue(replay, 2)
    operation = op()
    committed = replay.acknowledge(first, operation=operation)
    again = replay.acknowledge(first, operation=operation)
    assert committed.observation == "COMMITTED_THIS_CALL"
    assert again.observation == "PREVIOUSLY_COMMITTED"
    assert (again.sequence, again.result) == (committed.sequence, committed.result)
    with pytest.raises(JobStoreError, match="DELIVERY_ACKNOWLEDGED"):
        replay.acknowledge(first, operation=op())
    second = probe.issue(replay, 2)
    revision = x.publisher.revision
    with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
        replay.acknowledge(second, operation=operation)
    with pytest.raises(JobStoreError, match="CONSUMER_PROGRESS"):
        replay.acknowledge(dataclasses.replace(second, stop=6), operation=op())
    with pytest.raises(JobStoreError, match="CONSUMER_PROGRESS"):
        replay.acknowledge(dataclasses.replace(second, start=3), operation=op())
    with pytest.raises(JobStoreError, match="DELIVERY_FOREIGN"):
        replay.acknowledge(dataclasses.replace(second, replay=object()), operation=op())
    with pytest.raises(JobStoreError, match="DELIVERY_FOREIGN"):
        replay.acknowledge(
            dataclasses.replace(second, identity=w.new_identity("dlv")),
            operation=op(),
        )
    assert x.publisher.revision == revision
    replay.acknowledge(second, operation=op())
    assert replay.position == 4
    verify_store(x.workspace)


def test_scope_modes_pin_the_exact_checkpoint(setup):
    if setup is None:
        return
    x = setup
    _session, results = probe.capture(
        x.workspace, x.publisher, x.generation, x.binding, (2, 2, 2), order=(0, 2, 1)
    )
    held = results[1].get("checkpoint")
    assert [p.get("frontier") for p in results] == [2, 2, 6]
    with pytest.raises(JobStoreError, match="CONSUMER_SCOPE"):
        accept(x, checkpoint=held, extent=2)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_EXTENT"):
        accept(x, checkpoint=held, scope="committed_prefix", extent=6)
    prefix = accept(x, checkpoint=held, scope="committed_prefix", extent=2)
    r.register_consumer(x.publisher, prefix, operation=op())
    replay = r.open_replay(x.publisher, prefix, operation=op())
    extents, end = probe.drain(replay, 3)
    assert extents == [(0, 2)]
    assert (end.extent, end.scope, end.holes, end.observed_end) == (
        2,
        "committed_prefix",
        ((2, 4),),
        6,
    )
    whole = accept(x)
    assert (whole.checkpoint, whole.extent) == (results[2].get("checkpoint"), 6)
    r.register_consumer(x.publisher, whole, operation=op())
    extents, end = probe.drain(r.open_replay(x.publisher, whole, operation=op()), 4)
    assert extents == [(0, 4), (4, 6)] and end.holes == ()
    assert r.consumer_state(x.workspace, prefix.consumer).checkpoint == held


def test_complete_capture_needs_recorded_eof_and_known_end(setup):
    if setup is None:
        return
    x = setup
    session, _results = probe.capture(
        x.workspace, x.publisher, x.generation, x.binding, (2,), eof=False
    )
    with pytest.raises(JobStoreError, match="CONSUMER_SCOPE"):
        accept(x, extent=2)
    prefix = accept(x, scope="committed_prefix", extent=2)
    r.register_consumer(x.publisher, prefix, operation=op())
    session.owner.close()
    session.end(operation=op())  # the real early close is not EOF
    with pytest.raises(JobStoreError, match="CONSUMER_SCOPE"):
        accept(x, extent=2)
    extents, end = probe.drain(r.open_replay(x.publisher, prefix, operation=op()), 2)
    assert extents == [(0, 2)] and end.observed_end == 2


def test_empty_schema_differs_from_a_hole_at_zero(tmp_path, built, monkeypatch):
    if not qualified(tmp_path):
        return
    probe.arrow_free(monkeypatch)
    template, compiled = built
    ends = {}
    for name, sizes, order, eof in (
        ("empty", (), None, True),
        ("hole", (2, 2), (1,), False),
    ):
        workspace, job, publisher, binding, _record, generation = probe.store(
            tmp_path / name, template
        )
        try:
            probe.capture(
                workspace, publisher, generation, binding, sizes, order=order, eof=eof
            )
            scope = "complete_capture" if name == "empty" else "committed_prefix"
            if name == "hole":
                with pytest.raises(JobStoreError, match="CONSUMER_SCOPE"):
                    probe.accept(workspace, job, generation, compiled, extent=0)
            acceptance = probe.accept(
                workspace, job, generation, compiled, scope=scope, extent=0
            )
            r.register_consumer(publisher, acceptance, operation=op())
            replay = r.open_replay(publisher, acceptance, operation=op())
            ends[name] = probe.end(replay)
            assert r.consumer_state(workspace, acceptance.consumer).issued == ()
            verify_store(workspace)
        finally:
            publisher.close()
            workspace.close()
    empty, hole = ends["empty"], ends["hole"]
    assert empty.schema[0] == "ARROW_FREE_SCHEMA_MEMBER" and hole.schema is None
    assert (empty.extent, empty.holes, empty.observed_end, empty.verified) == (
        0,
        (),
        0,
        (0, 0),
    )
    assert (hole.extent, hole.holes, hole.observed_end, hole.scope) == (
        0,
        ((0, 2),),
        None,
        "committed_prefix",
    )


def test_fresh_acceptance_rejects_every_wrong_correspondence(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    probe.capture(x.workspace, x.publisher, x.generation, x.binding, (2,))
    for overrides, code in (
        ({"expected_pin": "0" * 64}, "JOB_TRUST_INPUT"),
        ({"accepted_producer": "pietto-other"}, "JOB_TRUST_INPUT"),
        ({"accepted_compatibility": ("x",)}, "JOB_TRUST_INPUT"),
        ({"route": "postgres_adbc"}, "ACCEPTANCE_ROUTE"),
        ({"values": (2,)}, "BINDING_VECTOR"),
        ({"values": (True,)}, "BINDING_VECTOR"),
        ({"values": (1.0,)}, "BINDING_VECTOR"),
        ({"values": ()}, "BINDING_VECTOR"),
        ({"values": None}, "BINDING_VECTOR"),
        ({"seconds": 0}, "ACCEPTANCE_BOUND"),
        ({"seconds": r.MAX_ACCEPTANCE_SECONDS + 1}, "ACCEPTANCE_BOUND"),
        ({"batch_rows": 4097}, "ACCEPTANCE_BOUND"),
        ({"batch_rows": True}, "ACCEPTANCE_BOUND"),
        ({"purpose": ""}, "ACCEPTANCE_PURPOSE"),
        ({"purpose": "line\n"}, "ACCEPTANCE_PURPOSE"),
        ({"purpose": "x" * 257}, "ACCEPTANCE_PURPOSE"),
        ({"consumer": "csm-1"}, "CONSUMER_IDENTITY"),
        ({"scope": "latest"}, "CONSUMER_SCOPE"),
        ({"extent": -1}, "CONSUMER_SCOPE"),
        ({"checkpoint": w.new_identity("ckp")}, "CHECKPOINT_UNKNOWN"),
        ({"extent": 1}, "ACCEPTANCE_EXTENT"),
    ):
        with pytest.raises(JobStoreError, match=code):
            accept(x, **overrides)
    from pietto._project import project_compiled_loading as loading

    with monkeypatch.context() as patch:
        patch.setattr(loading, "supported_compatibility", lambda: ("changed",))
        with pytest.raises(JobStoreError, match="JOB_COMPATIBILITY"):
            accept(x)
    acceptance = accept(x)
    for call in (lambda: copy.copy(acceptance), lambda: pickle.dumps(acceptance)):
        with pytest.raises(JobStoreError, match="ACCEPTANCE_COPY"):
            call()
    forged = object.__new__(r.SavedReadAcceptance)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_UNKNOWN"):
        r.register_consumer(x.publisher, forged, operation=op())
    foreign = accept(x)
    object.__setattr__(foreign, "_pid", -1)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_FOREIGN_PROCESS"):
        r.register_consumer(x.publisher, foreign, operation=op())
    other_job = s.register_job(x.workspace, x.template, operation=op()).get("job")
    other = s.claim_publisher(x.workspace, other_job, operation=op())
    try:
        with pytest.raises(JobStoreError, match="ACCEPTANCE_SUBJECT"):
            r.register_consumer(other, acceptance, operation=op())
    finally:
        other.close()
    r.register_consumer(x.publisher, acceptance, operation=op())
    stranger = accept(x)
    with pytest.raises(JobStoreError, match="CONSUMER_UNKNOWN"):
        r.open_replay(x.publisher, stranger, operation=op())
    for overrides in ({"purpose": "audit"}, {"scope": "committed_prefix"}):
        changed = accept(x, consumer=acceptance.consumer, **overrides)
        with pytest.raises(JobStoreError, match="ACCEPTANCE_SUBJECT"):
            r.open_replay(x.publisher, changed, operation=op())
    state = r.consumer_state(x.workspace, acceptance.consumer)
    assert (state.sessions, state.issued, state.position) == ((), (), 0)
    assert verify_store(x.workspace)["consumers"] == 1


def test_validity_is_bounded_by_wall_and_monotonic_clocks(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    clock = {"wall": 2_000_000_000.0, "mono": 50.0}
    monkeypatch.setattr(r, "_wall", lambda: clock["wall"])
    monkeypatch.setattr(r, "_monotonic", lambda: clock["mono"])
    probe.capture(x.workspace, x.publisher, x.generation, x.binding, (2, 2))
    acceptance = accept(x, seconds=60)
    for bad in (int(clock["wall"]), 1, -5, True, 2.0e9):
        with pytest.raises(JobStoreError, match="CONSUMER_EXPIRED"):
            r.register_consumer(x.publisher, acceptance, operation=op(), not_after=bad)  # type: ignore[arg-type]
    limit = int(clock["wall"]) + 3600
    r.register_consumer(x.publisher, acceptance, operation=op(), not_after=limit)
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    item = probe.issue(replay, 2)
    # A wall-clock rollback cannot lengthen the accepted session.
    clock["wall"] -= 10_000
    clock["mono"] += 61
    with pytest.raises(JobStoreError, match="ACCEPTANCE_EXPIRED"):
        replay.acknowledge(item, operation=op())
    with pytest.raises(JobStoreError, match="ACCEPTANCE_EXPIRED"):
        r.open_replay(x.publisher, acceptance, operation=op())
    fresh = accept(x, consumer=acceptance.consumer, seconds=60)
    # A forward wall jump also ends it although little real time passed.
    clock["wall"] += 61
    clock["mono"] += 1
    with pytest.raises(JobStoreError, match="ACCEPTANCE_EXPIRED"):
        r.open_replay(x.publisher, fresh, operation=op())
    clock["wall"] = float(limit)
    late = accept(x, consumer=acceptance.consumer)
    with pytest.raises(JobStoreError, match="CONSUMER_EXPIRED"):
        r.open_replay(x.publisher, late, operation=op())
    state = r.consumer_state(x.workspace, acceptance.consumer)
    assert (state.position, state.not_after) == (0, limit)
    assert [i[2:] for i in state.issued] == [(0, 2, False)]


@pytest.mark.parametrize("event", ["cancel", "release", "expire"])
@pytest.mark.parametrize("phase", ["before_open", "decode_offer", "offer_ack"])
def test_authority_changes_refuse_new_reads_and_progress(
    setup, monkeypatch, event, phase
):
    if setup is None:
        return
    x = setup
    acceptance, result = registered(x)
    code = {
        "cancel": "JOB_STATE",
        "release": "CONSUMER_RELEASED",
        "expire": "ACCEPTANCE_EXPIRED",
    }[event]

    def trigger():
        if event == "cancel":
            s.cancel_job(x.publisher, operation=op())
        elif event == "release":
            c.release_retention(x.publisher, result.get("retention"), operation=op())
        else:
            monkeypatch.setattr(r, "_monotonic", lambda: float("inf"))

    referenced = c.classify_files(x.workspace)["referenced"]
    if phase == "before_open":
        trigger()
        with pytest.raises(JobStoreError, match=code):
            r.open_replay(x.publisher, acceptance, operation=op())
    elif phase == "decode_offer":
        replay = r.open_replay(x.publisher, acceptance, operation=op())
        step = r._rebatch
        rows = []

        def decoded(replay, start, stop):
            value = step(replay, start, stop)
            rows.append(value[0])
            trigger()
            return value

        monkeypatch.setattr(r, "_rebatch", decoded)
        with pytest.raises(JobStoreError, match=code):
            replay.next(2, operation=op())
        assert rows[0].closed is True  # never handed to the caller
    else:
        replay = r.open_replay(x.publisher, acceptance, operation=op())
        item = probe.issue(replay, 2)
        trigger()
        with pytest.raises(JobStoreError, match=code):
            replay.acknowledge(item, operation=op())
        # Data already handed to the caller cannot be revoked from its memory.
        assert item.batch.closed is False
    state = r.consumer_state(x.workspace, acceptance.consumer)
    assert state.position == 0 and state.acknowledged == ()
    assert len(state.issued) == (1 if phase == "offer_ack" else 0)
    assert state.released is (event == "release")
    # Control and observations stay truthful; nothing is collected or deleted.
    if event != "release":
        c.release_retention(x.publisher, result.get("retention"), operation=op())
    assert c.classify_files(x.workspace)["referenced"] == referenced
    verify_store(x.workspace)


def test_stale_publisher_and_superseded_session_cannot_advance(setup):
    if setup is None:
        return
    x = setup
    acceptance, _ = registered(x, (2, 2, 2))
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    item = probe.issue(replay, 2)
    newer = r.open_replay(x.publisher, acceptance, operation=op())
    with pytest.raises(JobStoreError, match="REPLAY_SESSION_STALE"):
        replay.acknowledge(item, operation=op())
    os.close(x.publisher._fd)  # the lock is lost while the handle still exists
    handle = w.open_workspace(x.workspace.root, expected_identity=x.workspace.identity)
    try:
        other = s.claim_publisher(handle, x.job, operation=op())
        for call in (
            lambda: newer.next(2, operation=op()),
            lambda: r.open_replay(x.publisher, acceptance, operation=op()),
        ):
            with pytest.raises(JobStoreError, match="PUBLISHER_STALE"):
                call()
        fresh = probe.accept(
            handle,
            x.job,
            x.generation,
            x.built,
            consumer=acceptance.consumer,
        )
        latest = r.open_replay(other, fresh, operation=op())
        assert (latest.position, latest.ordinal) == (0, 3)
        extents, end = probe.drain(latest, 4)
        assert extents == [(0, 4), (4, 6)] and end.acknowledged == 6
        verify_store(handle)
        other.close()
    finally:
        x.publisher._closed = True
        handle.close()


class _Connection:
    """Explicit labelled fault injection around one real connection."""

    def __init__(self, real, fail):
        self.real, self.fail = real, fail

    def execute(self, sql, *args):
        if sql == self.fail:
            raise sqlite3.OperationalError("injected " + sql)
        return self.real.execute(sql, *args)

    def close(self):
        self.real.close()
        if self.fail == "close":
            raise sqlite3.OperationalError("injected close")


@pytest.mark.parametrize("call", ["issue", "acknowledge"])
@pytest.mark.parametrize("injection", ["before_commit", "after_commit"])
def test_ambiguous_commit_leaves_zero_or_one_queryable_effect(
    setup, monkeypatch, call, injection
):
    if setup is None:
        return
    x = setup
    acceptance, _ = registered(x)
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    item = probe.issue(replay, 2) if call == "acknowledge" else None
    seen = []
    step = r._rebatch
    monkeypatch.setattr(r, "_rebatch", lambda *a: seen.append(step(*a)) or seen[-1])
    real = w.commit

    def commit(connection):
        if injection == "after_commit":
            real(connection)
        raise sqlite3.OperationalError("injected lost reply")

    monkeypatch.setattr(w, "commit", commit)
    operation = op()
    with pytest.raises(JobStoreError, match="STORE_COMMIT_UNKNOWN"):
        if item is None:
            replay.next(2, operation=operation)
        else:
            replay.acknowledge(item, operation=operation)
    monkeypatch.setattr(w, "commit", real)
    if item is None:
        assert seen[-1][0].closed is True  # an uncertain issuance exposes nothing
    with pytest.raises(JobStoreError, match="WORKSPACE_RETIRED"):
        if item is None:
            replay.next(2, operation=op())
        else:
            replay.acknowledge(item, operation=op())
    x.publisher.close()
    fresh = w.open_workspace(x.workspace.root, expected_identity=x.workspace.identity)
    try:
        committed = injection == "after_commit"
        found = s.query_operation(fresh, operation)
        assert (found is not None) is committed
        state = r.consumer_state(fresh, acceptance.consumer)
        if item is None:
            assert len(state.issued) == int(committed) and state.position == 0
        else:
            assert state.position == (2 if committed else 0)
            assert found is None or found.get("position") == 2
        publisher = s.claim_publisher(fresh, x.job, operation=op())
        resumed = r.open_replay(
            publisher,
            probe.accept(
                fresh, x.job, x.generation, x.built, consumer=acceptance.consumer
            ),
            operation=op(),
        )
        assert resumed.position == state.position
        extents, end = probe.drain(resumed, 2)
        assert end.acknowledged == 4 and extents[0][0] == state.position
        verify_store(fresh)
        publisher.close()
    finally:
        fresh.close()


def test_busy_capacity_cleanup_and_close_failures_keep_state(
    tmp_path, built, monkeypatch
):
    if not qualified(tmp_path):
        return
    probe.arrow_free(monkeypatch)
    template, compiled = built
    workspace, job, publisher, binding, _record, generation = probe.store(
        tmp_path / "workspace", template, busy_seconds=0.2
    )
    try:
        probe.capture(workspace, publisher, generation, binding, (2, 2))
        acceptance = probe.accept(workspace, job, generation, compiled)
        result = r.register_consumer(publisher, acceptance, operation=op())
        replay = r.open_replay(publisher, acceptance, operation=op())
        blocker = sqlite3.connect(os.path.join(workspace.root, "store.sqlite"))
        try:
            blocker.execute("BEGIN IMMEDIATE")
            with pytest.raises(JobStoreError, match="STORE_BUSY"):
                replay.next(2, operation=op())
        finally:
            blocker.rollback()
            blocker.close()
        # Injected capacity: data admission keeps the control reserve.
        with monkeypatch.context() as patch:
            patch.setattr(
                w, "accounted_bytes", lambda ws: ws.budget - w.CONTROL_RESERVE
            )
            with pytest.raises(JobStoreError, match="WORKSPACE_BUDGET"):
                replay.next(2, operation=op())
            held = c.retain_checkpoint(
                publisher, generation, scope={"purpose": "control"}, operation=op()
            )
        assert r.consumer_state(workspace, acceptance.consumer).issued == ()
        item = probe.issue(replay, 2)
        real = workspace._connection
        workspace._connection = _Connection(real, "ROLLBACK")  # type: ignore[assignment]
        monkeypatch.setattr(
            r, "_reached", lambda *a: (_ for _ in ()).throw(ValueError("primary"))
        )
        with pytest.raises(ValueError, match="primary") as raised:
            replay.acknowledge(item, operation=op())
        assert raised.value.__notes__ == ["rollback failed; workspace retired"]
        monkeypatch.undo()
        publisher.close()
        workspace.close()
        again = w.open_workspace(workspace.root, expected_identity=workspace.identity)
        state = r.consumer_state(again, acceptance.consumer)
        assert state.position == 0 and [i[2:] for i in state.issued] == [(0, 2, False)]
        later = s.claim_publisher(again, job, operation=op())
        c.release_retention(later, str(held.retention), operation=op())
        later.close()
        verify_store(again)
        again._connection = _Connection(again._connection, "close")  # type: ignore[assignment]
        with pytest.raises(JobStoreError, match="STORE_CLOSE"):
            again.close()
        final = w.open_workspace(workspace.root, expected_identity=workspace.identity)
        try:
            assert r.consumer_state(final, acceptance.consumer).released is False
            assert result.get("retention") != held.retention
        finally:
            final.close()
    finally:
        publisher.close()
        if not workspace._closed:
            workspace.close()


def test_decode_failure_issues_nothing_and_keeps_the_session(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    acceptance, _ = registered(x)
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    step = r._rebatch

    def damaged(replay, start, stop):
        raise JobStoreError("CHUNK_DIGEST")

    monkeypatch.setattr(r, "_rebatch", damaged)
    with pytest.raises(JobStoreError, match="CHUNK_DIGEST"):
        replay.next(2, operation=op())
    assert replay.position == 0
    assert r.consumer_state(x.workspace, acceptance.consumer).issued == ()
    monkeypatch.setattr(r, "_rebatch", step)
    extents, end = probe.drain(replay, 2)
    assert extents == [(0, 2), (2, 4)] and end.verified == (0, 4)


def test_registration_is_atomic_replayable_and_protects_the_checkpoint(
    setup, monkeypatch
):
    if setup is None:
        return
    x = setup
    probe.capture(x.workspace, x.publisher, x.generation, x.binding, (2, 2))
    acceptance = accept(x)
    retentions = verify_store(x.workspace)["retentions"]
    with monkeypatch.context() as patch:
        patch.setattr(
            r, "_covered", lambda *a: (_ for _ in ()).throw(JobStoreError("INJECTED"))
        )
        with pytest.raises(JobStoreError, match="INJECTED"):
            r.register_consumer(x.publisher, acceptance, operation=op())
    assert verify_store(x.workspace)["retentions"] == retentions
    operation = op()
    first = r.register_consumer(x.publisher, acceptance, operation=operation)
    again = r.register_consumer(x.publisher, acceptance, operation=operation)
    assert again.observation == "PREVIOUSLY_COMMITTED"
    assert again.result == first.result
    with pytest.raises(JobStoreError, match="CONSUMER_EXISTS"):
        r.register_consumer(x.publisher, acceptance, operation=op())
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    assert {m.chunk for m in snapshot.members} <= c.protected_chunks(x.workspace, x.job)
    state = r.consumer_state(x.workspace, acceptance.consumer)
    assert (state.retention, state.extent, state.position) == (
        first.get("retention"),
        4,
        0,
    )
    assert (state.binding, state.purpose, state.scope) == (
        snapshot.binding,
        "s13-read",
        "complete_capture",
    )
    s.cancel_job(x.publisher, operation=op())
    with pytest.raises(JobStoreError, match="JOB_STATE"):
        r.register_consumer(x.publisher, accept(x), operation=op())
    assert verify_store(x.workspace)["retentions"] == retentions + 1


@pytest.mark.parametrize(
    "damage,category",
    [
        ("session_ordinal", "SESSION_HISTORY"),
        ("session_position", "SESSION_HISTORY"),
        ("issuance_epoch", "ISSUANCE_HISTORY"),
        ("consumer_extent", "CONSUMER_HISTORY"),
        ("consumer_scope", "CONSUMER_HISTORY"),
        ("forged_ack", "REPLAY_ROWS"),
        ("deleted_ack", "ACK_HISTORY"),
        ("gap", "INTEGRITY"),
    ],
)
def test_independent_history_replay_rejects_cursor_damage(setup, damage, category):
    if setup is None:
        return
    x = setup
    acceptance, _ = registered(x, (2, 2, 2))
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    first = probe.issue(replay, 2)
    replay.acknowledge(first, operation=op())
    replay.next(2, operation=op())  # issued, never acknowledged
    verify_store(x.workspace)
    consumer = acceptance.consumer
    connection = x.workspace.use()
    connection.execute("PRAGMA foreign_keys = OFF")
    pending = connection.execute(
        "SELECT identity, session FROM issuance WHERE start = 2"
    ).fetchone()
    if damage == "session_ordinal":
        connection.execute("UPDATE replay_session SET ordinal = 5")
    elif damage == "session_position":
        connection.execute("UPDATE replay_session SET position = 1")
    elif damage == "issuance_epoch":
        connection.execute("UPDATE issuance SET publisher_epoch = 9")
    elif damage == "consumer_extent":
        connection.execute("UPDATE consumer SET extent = 4")
    elif damage == "consumer_scope":
        connection.execute("UPDATE consumer SET scope = 'committed_prefix'")
    elif damage == "forged_ack":
        connection.execute(
            "INSERT INTO acknowledgement VALUES (?, ?, ?, 2, 4, 2, ?)",
            (pending[0], consumer, pending[1], x.publisher.epoch),
        )
    elif damage == "deleted_ack":
        connection.execute("DELETE FROM acknowledgement")
    else:
        connection.execute(
            "INSERT INTO issuance VALUES (?, ?, ?, 9, 4, 6, ?)",
            (w.new_identity("dlv"), consumer, pending[1], x.publisher.epoch),
        )
        connection.execute(
            "INSERT INTO acknowledgement SELECT identity, consumer, session, 4, 6, 4,"
            " publisher_epoch FROM issuance WHERE ordinal = 9"
        )
    connection.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(JobStoreError, match="STORE_INVARIANT_" + category):
        verify_store(x.workspace)
    if damage == "gap":
        # The product's own derivation refuses a cursor gap as well.
        for call in (
            lambda: r.consumer_state(x.workspace, consumer),
            lambda: r.open_replay(x.publisher, acceptance, operation=op()),
        ):
            with pytest.raises(JobStoreError, match="CONSUMER_PROGRESS"):
                call()
