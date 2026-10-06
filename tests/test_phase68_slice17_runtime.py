"""S17 bounded multi-job runtime: ownership, admission, backpressure and control.

No database or Arrow. Units run through the real coordinator, control thread,
worker threads, durable admissions and settlements, per-job publishers, claims,
leases, closures and the independent verifier. Labelled replacements (see the
probe): ARROW_FREE_STORAGE_STEP captures, SIMULATED_NATIVE_IO owners (a real
compiled never-connected owner whose blocking fetch is a Gate woken only by
release or by that owner's own `cancel()`), SYNTHETIC_CLOSED_OWNER terminals,
the S13/S15 Arrow-free replay/payload steps and ARROW_FREE_MEMBER_CHECK.
"""

import sqlite3
import threading
import time

import pytest

import _pietto_phase68_slice15_probe as s15
import _pietto_phase68_slice17_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from pietto._project import project_job_capture as c
from pietto._project import project_job_runtime as rt
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

op = probe.op
TIMEOUT = 60.0


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(tmp_path_factory.mktemp("s17") / "small", entry="bundle")


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
    publisher.close()
    x = probe.setup_namespace(
        workspace=workspace,
        job=job,
        binding=binding,
        record=record,
        generation=generation,
        built=compiled,
        template=template,
        root=tmp_path,
        runtimes=[],
    )
    yield x
    for runtime in x.runtimes:
        runtime.close(timeout=30)
    workspace.close()


def runtime(x, **policy):
    opened = probe.open_runtime(x, **policy)
    x.runtimes.append(opened)
    return opened


def job(x):
    """Another job (own publisher closed) with one generation."""
    other, publisher, binding, record, generation = probe.another_job(
        x.workspace, x.template
    )
    publisher.close()
    return other, generation


def events(state, kind):
    return [t for t, k in state.events if k == kind]


def terminal(runtime_, handle):
    state = runtime_.wait(handle, TIMEOUT)
    assert state.terminal is not None, state
    return state


# --- ownership -----------------------------------------------------------------


def test_one_coordinating_incarnation_per_workspace(setup):
    x = setup
    if x is None:
        return
    first = runtime(x)
    with pytest.raises(JobStoreError, match="RUNTIME_BUSY"):
        probe.open_runtime(x)
    assert first.close()["unjoined"] == []
    second = runtime(x)
    assert (first.owner.epoch, second.owner.epoch) == (1, 2)
    rows = probe.rows(x.workspace, "SELECT epoch, instance, policy FROM runtime_owner")
    assert [r[0] for r in rows] == [1, 2] and rows[0][1] != rows[1][1]
    with pytest.raises(JobStoreError, match="RUNTIME_OWNER_COPY"):
        import pickle

        pickle.dumps(second.owner)


def test_policy_and_unit_bounds_refuse_explicitly(setup):
    x = setup
    if x is None:
        return
    for bad in (dict(workers=0), dict(connections=9), dict(memory=1), dict(queue=65)):
        with pytest.raises(JobStoreError, match="RUNTIME_POLICY"):
            probe.open_runtime(x, **bad)
    opened = runtime(x, queue=1, connections=1, workers=1)
    with pytest.raises(JobStoreError, match="RUNTIME_UNIT_BOUND"):
        opened.submit(probe.unit(x, "CAPTURE", durable=1 << 40))
    with pytest.raises(JobStoreError, match="RUNTIME_UNIT_BOUND"):
        opened.submit(probe.unit(x, "REPLAY", durable=1))
    gate = probe.Gate()
    probe.PLANS[x.generation] = probe.Plan(gate)
    first = opened.submit(probe.unit(x, "CAPTURE"))
    assert gate.entered.wait(TIMEOUT)
    other, generation = job(x)
    probe.PLANS[generation] = probe.Plan(1)
    opened.submit(probe.unit(x, "CAPTURE", generation, other))
    with pytest.raises(JobStoreError, match="RUNTIME_QUEUE_FULL"):
        opened.submit(probe.unit(x, "CAPTURE", generation, other))
    gate.released.set()
    assert terminal(opened, first).terminal == "COMPLETED"


# --- overlap, isolation, same-job conflict -------------------------------------


def test_distinct_jobs_overlap_and_same_job_conflicts(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x, workers=3, connections=3)
    other, generation = job(x)
    gates = probe.Gate(), probe.Gate()
    probe.PLANS[x.generation] = probe.Plan(2, gates[0], 2, 2)
    probe.PLANS[generation] = probe.Plan(1, gates[1], 1)
    a = opened.submit(probe.unit(x, "CAPTURE"))
    b = opened.submit(probe.unit(x, "CAPTURE", generation, other))
    assert gates[0].entered.wait(TIMEOUT) and gates[1].entered.wait(TIMEOUT)
    # Both jobs hold real progress at once: each published its first chunk.
    assert opened.query(a).counters and opened.query(b).counters
    # A second unit of job A meets the real per-job publisher lock.
    conflict = opened.submit(probe.unit(x, "CAPTURE"))
    state = terminal(opened, conflict)
    assert state.terminal == "FAILED" and "PUBLISHER_BUSY" in str(state.failure)
    assert state.settlement == "RELEASED"
    for gate in gates:
        gate.released.set()
    first, second = terminal(opened, a), terminal(opened, b)
    assert (first.terminal, second.terminal) == ("COMPLETED", "COMPLETED")
    assert dict(first.counters)["rows"] == 6 and dict(second.counters)["rows"] == 2
    # Overlap: B's first chunk landed before A finished and vice versa.
    a_done, b_done = (
        events(first, "TERMINAL:COMPLETED")[0],
        events(second, "TERMINAL:COMPLETED")[0],
    )
    a_step, b_step = events(first, "STEPPING")[0], events(second, "STEPPING")[0]
    assert a_step < b_done and b_step < a_done
    counts = verify_store(x.workspace)
    assert (counts["admissions"], counts["settlements"]) == (3, 3)
    assert counts["claims"] == 5


def test_failed_startup_is_isolated_and_settled(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x)
    other, generation = job(x)
    probe.PLANS[generation] = probe.Plan(1, 1)
    bad = probe.unit(
        x, "CAPTURE", trust=("0" * 64, x.built.producer, x.built.compatibility)
    )
    failed = opened.submit(bad)
    good = opened.submit(probe.unit(x, "CAPTURE", generation, other))
    state = terminal(opened, failed)
    assert state.terminal == "FAILED" and "JOB_TRUST_INPUT" in str(state.failure)
    assert state.settlement == "RELEASED"
    assert terminal(opened, good).terminal == "COMPLETED"
    record = s.job_record(x.workspace, x.job)
    assert record.attempts == () and record.state == "ACTIVE"
    verify_store(x.workspace)


# --- admission races, rollback, settlement and ambiguity --------------------------


def race(x, opened, unit_of):
    """Two threads take the last unit of one resource at the same instant."""
    other, _generation = job(x)
    barrier = threading.Barrier(2)
    results = []

    def take(job_):
        barrier.wait()
        try:
            results.append(opened.grant(job_, unit_of(job_)))
        except JobStoreError as error:
            results.append(str(error))

    threads = [threading.Thread(target=take, args=(j,)) for j in (x.job, other)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(TIMEOUT)
    won = [r for r in results if isinstance(r, rt.Admission)]
    for admission in won:
        opened.release(admission)
    return won, [r for r in results if isinstance(r, str)]


def test_last_connection_race_has_one_winner(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x, connections=1)
    won, lost = race(x, opened, lambda j: probe.unit(x, "CAPTURE", job=j))
    assert len(won) == 1 and lost == ["RUNTIME_CAPACITY:connections"]


def test_last_durable_credit_race_is_atomic_in_sqlite(setup):
    x = setup
    if x is None:
        return
    # In-memory bounds admit both; only the durable check can refuse one: two
    # reservations that each fit a stale observation never both commit.
    opened = runtime(x, connections=2, durable=x.workspace.budget - w.CONTROL_RESERVE)
    spare = (
        x.workspace.budget - w.metadata_bytes(x.workspace) - w.CONTROL_RESERVE - 65536
    )
    half = spare // 2 + 1
    won, lost = race(x, opened, lambda j: probe.unit(x, "CAPTURE", job=j, durable=half))
    assert len(won) == 1 and lost == ["WORKSPACE_BUDGET"]
    assert opened._used == rt.Vector(0, 0, 0, 0, 0)


def test_partial_failure_rolls_back_the_whole_vector(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x, connections=1)
    with pytest.raises(JobStoreError, match="JOB_UNKNOWN"):
        opened.grant("job-" + "0" * 32, probe.unit(x, "CAPTURE"))
    assert opened._used == rt.Vector(0, 0, 0, 0, 0)
    granted = opened.grant(x.job, probe.unit(x, "CAPTURE"))
    first = opened.release(granted)
    again = rt.settle(x.workspace, opened.owner, granted.identity)
    assert first == again and first.settlement == (opened.owner.epoch, "RELEASED", 0)
    assert probe.rows(x.workspace, "SELECT count(*) FROM admission_settlement") == [
        (1,)
    ]
    assert opened._used == rt.Vector(0, 0, 0, 0, 0)


@pytest.mark.parametrize("committed", [True, False])
def test_admission_commit_ambiguity_is_queried_before_work(
    setup, monkeypatch, committed
):
    x = setup
    if x is None:
        return
    probe.PLANS[x.generation] = probe.Plan(1)
    real = w.commit
    state = {"armed": True}

    def lost(connection):
        if (
            state["armed"]
            and connection.execute("SELECT count(*) FROM admission").fetchone()[0]
            and threading.current_thread().name == "pietto-runtime-control"
        ):
            state["armed"] = False
            if committed:
                real(connection)
            raise sqlite3.OperationalError("disk I/O error")
        real(connection)

    monkeypatch.setattr(w, "commit", lost)
    opened = runtime(x)
    handle = opened.submit(probe.unit(x, "CAPTURE"))
    final = terminal(opened, handle)
    assert "ADMISSION_UNKNOWN" in [k for _t, k in final.events]
    if committed:
        assert final.terminal == "COMPLETED" and final.settlement == "RELEASED"
    else:
        assert (final.terminal, final.failure) == ("REFUSED", "ADMISSION_ABSENT")
        assert probe.rows(x.workspace, "SELECT count(*) FROM admission") == [(0,)]
        assert s.job_record(x.workspace, x.job).attempts == ()
    assert opened._used == rt.Vector(0, 0, 0, 0, 0)


def test_operation_headroom_is_kept_for_control(setup, monkeypatch):
    x = setup
    if x is None:
        return
    publisher = s.claim_publisher(x.workspace, x.job, operation=op())
    try:
        count = probe.rows(x.workspace, "SELECT count(*) FROM operation")[0][0]
        monkeypatch.setattr(s, "LIMITS", {**s.LIMITS, "operation": count + 3})
        monkeypatch.setattr(s, "CONTROL_OPERATIONS", 2)
        s.register_generation(
            publisher,
            x.record,
            x.binding,
            route="postgres_rows",
            isolation="stable",
            operation=op(),
        )
        with pytest.raises(JobStoreError, match="STORE_LIMIT"):
            s.register_generation(
                publisher,
                x.record,
                x.binding,
                route="postgres_rows",
                isolation="stable",
                operation=op(),
            )
        # Control still has its reserved rows.
        s.cancel_job(publisher, operation=op())
        from pietto._project import project_job_collection as col

        col.retire_generation(publisher, x.generation, operation=op())
    finally:
        publisher.close()


# --- backpressure ------------------------------------------------------------------


def sink_target(handle, busy=0.2):
    return rt.SinkTarget(
        handle.root,
        handle.identity,
        handle.namespace,
        handle.epoch,
        handle.retention,
        busy,
    )


def test_relay_stops_at_a_fixed_high_water_while_others_progress(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x, workers=3, connections=3)
    handle = s15.sink(x.root / "sink")
    handle.close()
    probe.PLANS[x.generation] = probe.Plan(2, 2, 2, 2)
    lock = sqlite3.connect(
        handle.root + "/sink.sqlite", isolation_level=None, timeout=5
    )
    lock.execute(
        "BEGIN IMMEDIATE"
    )  # the sink is busy: every submit waits, then UNKNOWN
    relay = opened.submit(probe.unit(x, "RELAY", sink=sink_target(handle), rows=2))
    state = opened.wait_activity(relay, "WAITING_FOR_DOWNSTREAM", TIMEOUT)
    assert state.activity == "WAITING_FOR_DOWNSTREAM"
    high = dict(state.counters)
    pulled = probe.PLANS[x.generation].pulled
    # Another job progresses to completion while the relay is stalled.
    other, generation = job(x)
    probe.PLANS[generation] = probe.Plan(1, 1, 1)
    progress = opened.submit(probe.unit(x, "CAPTURE", generation, other))
    assert terminal(opened, progress).terminal == "COMPLETED"
    time.sleep(0.5)
    still = opened.query(relay)
    assert still.activity == "WAITING_FOR_DOWNSTREAM"
    assert probe.PLANS[x.generation].pulled == pulled == 1
    assert dict(still.counters)["observed_peak"] == high["observed_peak"] == 2
    staged = probe.rows(
        x.workspace,
        "SELECT count(*) FROM chunk_claim WHERE generation = ?",
        (x.generation,),
    )
    assert staged == [(1,)]
    # No acknowledgement and no local sink confirmation was invented.
    assert probe.rows(x.workspace, "SELECT count(*) FROM sink_observation") == [(0,)]
    assert probe.rows(x.workspace, "SELECT count(*) FROM acknowledgement") == [(0,)]
    lock.execute("ROLLBACK")
    lock.close()
    opened.resume(relay)
    done = terminal(opened, relay)
    assert done.terminal == "COMPLETED", done
    positions = probe.rows(
        x.workspace, "SELECT position, issuance FROM sink_observation ORDER BY position"
    )
    assert [p for p, _i in positions] == list(range(8))
    reopened = k_open(handle)
    assert [row[0] for row in s15.effects(reopened)] == list(range(8))
    reopened.close()
    verify_store(x.workspace)


def k_open(handle):
    from pietto._project.project_job_sink import open_sink

    return open_sink(handle.root, expected_identity=handle.identity)


def test_replay_waits_for_an_explicit_ack_only(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x)
    probe.PLANS[x.generation] = probe.Plan(2, 1)
    assert (
        terminal(opened, opened.submit(probe.unit(x, "CAPTURE"))).terminal
        == "COMPLETED"
    )
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    replay = opened.submit(
        probe.unit(
            x,
            "REPLAY",
            checkpoint=snapshot.checkpoint,
            extent=snapshot.frontier,
            rows=2,
            batch_rows=2,
        )
    )
    first = opened.take(replay, TIMEOUT)
    assert first is not None and (first.start, first.stop) == (0, 2)
    assert opened.wait_activity(replay, "WAITING_FOR_DOWNSTREAM", TIMEOUT).activity
    # Taking again is not an acknowledgement; nothing durable moved.
    assert opened.take(replay, 0.1) is first
    time.sleep(0.2)
    assert probe.rows(x.workspace, "SELECT count(*) FROM acknowledgement") == [(0,)]
    assert probe.rows(x.workspace, "SELECT count(*) FROM issuance") == [(1,)]
    with pytest.raises(JobStoreError, match="DELIVERY_FOREIGN"):
        opened.ack(replay, object())
    opened.ack(replay, first)
    second = None
    for _ in range(100):
        second = opened.take(replay, TIMEOUT)
        if second is not None and second is not first:
            break
        time.sleep(0.01)
    assert second is not None and (second.start, second.stop) == (2, 3)
    assert second.occurrences == ((x.generation, 2),)
    opened.ack(replay, second)
    done = terminal(opened, replay)
    assert done.terminal == "COMPLETED" and dict(done.counters)["acknowledged"] == 3
    assert probe.rows(
        x.workspace, "SELECT start, stop FROM acknowledgement ORDER BY start"
    ) == [
        (0, 2),
        (2, 3),
    ]
    verify_store(x.workspace)


# --- control under saturation ---------------------------------------------------------


def test_cancel_admitted_blocked_and_waiting_units_under_saturation(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x, workers=1, connections=1)
    gate = probe.Gate()
    probe.PLANS[x.generation] = probe.Plan(2, gate, 2)
    blocked = opened.submit(probe.unit(x, "CAPTURE"))
    assert gate.entered.wait(TIMEOUT)
    other, generation = job(x)
    probe.PLANS[generation] = probe.Plan(1)
    waiting = opened.submit(probe.unit(x, "CAPTURE", generation, other))
    assert opened.wait_activity(waiting, "never", 0.3).state == "WAITING_FOR_ADMISSION"
    assert opened.query(waiting).limiting in ("workers", "connections")
    started = time.monotonic_ns()
    receipt = opened.cancel(blocked)
    assert receipt["requested"] and receipt["signal"]["requested"]
    assert receipt["signal"]["sent"] is False  # never connected: nothing to send
    final = terminal(opened, blocked)
    assert final.terminal == "CANCELLED" and final.durable_cancel == "COMMITTED"
    order = [k for _t, k in final.events]
    assert order.index("CANCEL_REQUESTED") < order.index("CANCEL_SIGNALLED")
    assert order.index("CANCEL_SIGNALLED") < order.index("DURABLE_CANCEL:COMMITTED")
    assert events(final, "CANCEL_REQUESTED")[0] >= started
    record = s.job_record(x.workspace, x.job)
    assert record.state == "CANCELLED"
    outcome = probe.outcome(record.attempts[0])
    assert outcome["cancel"] == (True, False, True) and outcome["source"] == "FAILED"
    # The waiting unit is admitted after the cancelled one ends; cancel it while
    # still queued in a second saturated round.
    assert terminal(opened, waiting).terminal == "COMPLETED"
    third_gate = probe.Gate()
    _job, third_generation = job(x)
    probe.PLANS[third_generation] = probe.Plan(third_gate)
    holder = opened.submit(probe.unit(x, "CAPTURE", third_generation, _job))
    assert third_gate.entered.wait(TIMEOUT)
    fourth, fourth_generation = job(x)
    queued = opened.submit(probe.unit(x, "CAPTURE", fourth_generation, fourth))
    opened.cancel(queued)
    final = terminal(opened, queued)
    assert (final.terminal, final.durable_cancel) == ("CANCELLED_QUEUED", "COMMITTED")
    assert s.job_record(x.workspace, fourth).state == "CANCELLED"
    assert s.job_record(x.workspace, fourth).attempts == ()
    third_gate.released.set()
    assert terminal(opened, holder).terminal == "COMPLETED"
    verify_store(x.workspace)


def test_cancel_while_waiting_downstream_keeps_unresolved_obligations(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x)
    handle = s15.sink(x.root / "sink")
    handle.close()
    probe.PLANS[x.generation] = probe.Plan(2, 2)
    lock = sqlite3.connect(
        handle.root + "/sink.sqlite", isolation_level=None, timeout=5
    )
    lock.execute("BEGIN IMMEDIATE")
    relay = opened.submit(probe.unit(x, "RELAY", sink=sink_target(handle), rows=2))
    assert opened.wait_activity(relay, "WAITING_FOR_DOWNSTREAM", TIMEOUT).activity
    opened.cancel(relay)
    final = terminal(opened, relay)
    lock.execute("ROLLBACK")
    lock.close()
    assert final.terminal == "CANCELLED" and final.durable_cancel == "COMMITTED"
    assert s.job_record(x.workspace, x.job).state == "CANCELLED"
    stream = probe.rows(x.workspace, "SELECT identity FROM stream")[0][0]
    from pietto._project import project_job_delivery as d

    assert d.stream_state(x.workspace, stream).unresolved == ((0, 2),)
    verify_store(x.workspace)


def test_deadline_stops_without_a_durable_cancel(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x)
    gate = probe.Gate()
    probe.PLANS[x.generation] = probe.Plan(1, gate)
    handle = opened.submit(probe.unit(x, "CAPTURE", seconds=1))
    final = terminal(opened, handle)
    assert final.terminal == "STOPPED" and final.durable_cancel == "NOT_REQUESTED"
    assert "DEADLINE" in [k for _t, k in final.events]
    record = s.job_record(x.workspace, x.job)
    assert record.state == "ACTIVE" and record.attempts[0].terminal == "OUTCOME"


# --- fairness, close and replacement ------------------------------------------------


def test_bounded_overtaking_is_reproducible(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x, connections=1, workers=8, overtakes=2, queue=8)
    gate = probe.Gate()
    probe.PLANS[x.generation] = probe.Plan(gate)
    holder = opened.submit(probe.unit(x, "CAPTURE"))
    assert gate.entered.wait(TIMEOUT)
    head_job, head_generation = job(x)
    probe.PLANS[head_generation] = probe.Plan(1)
    head = opened.submit(probe.unit(x, "CAPTURE", head_generation, head_job))
    later = []
    for _ in range(4):
        other, generation = job(x)
        later.append(
            opened.submit(
                probe.unit(
                    x,
                    "PUBLISH",
                    generation,
                    other,
                    checkpoint="ckp-" + "0" * 32,
                    closing="att-" + "0" * 32,
                )
            )
        )
    time.sleep(0.5)
    states = [opened.query(h) for h in later]
    passed = [s_ for s_ in states if s_.state != "WAITING_FOR_ADMISSION"]
    waiting = [s_ for s_ in states if s_.state == "WAITING_FOR_ADMISSION"]
    assert len(passed) == 2 and len(waiting) == 2
    assert {s_.limiting for s_ in waiting} == {"OVERTAKING_BOUND"}
    assert opened.query(head).limiting == "connections"
    gate.released.set()
    assert terminal(opened, holder).terminal == "COMPLETED"
    assert terminal(opened, head).terminal == "COMPLETED"
    for handle in later:
        assert terminal(opened, handle).terminal == "FAILED"  # no such checkpoint


def test_close_is_finite_and_a_replacement_reconciles(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x)
    gate = probe.Gate()
    probe.PLANS[x.generation] = probe.Plan(1, gate)
    running = opened.submit(probe.unit(x, "CAPTURE"))
    assert gate.entered.wait(TIMEOUT)
    granted = opened.grant(x.job, probe.unit(x, "PUBLISH"))
    report = opened.close(timeout=30)
    assert report["unjoined"] == []
    assert report["units"][running].terminal == "STOPPED"
    record = s.job_record(x.workspace, x.job)
    assert record.state == "ACTIVE" and record.attempts[0].terminal == "OUTCOME"
    replacement = runtime(x)
    assert replacement.owner.epoch == 2
    rows = replacement.reconcile()
    assert [r[0] for r in rows] == [granted.identity]
    fact = rt.admission_fact(x.workspace, granted.identity)
    assert fact is not None and fact.settlement == (2, "RECONCILED", 0)
    with pytest.raises(JobStoreError, match="RUNTIME_STALE"):
        rt.fence(x.workspace.use(), opened.owner)
    verify_store(x.workspace)


# --- storage pressure, failures and cancel races -----------------------------------


def test_storage_pressure_waits_and_explicit_collection_frees_capacity(
    tmp_path, built, monkeypatch
):
    if not qualified(tmp_path):
        return
    from pietto._project import project_job_collection as col

    probe.arrow_free(monkeypatch)
    template, compiled = built
    budget = 8 * 1024 * 1024
    workspace, job_, publisher, binding, record, generation = probe.store(
        tmp_path / "small", template, budget_bytes=budget
    )
    publisher.close()
    x = probe.setup_namespace(
        workspace=workspace,
        job=job_,
        generation=generation,
        built=compiled,
        template=template,
        runtimes=[],
    )
    try:
        opened = runtime(x, durable=budget - w.CONTROL_RESERVE)
        probe.PLANS[generation] = probe.Plan(*[(1, 512 * 1024)] * 4)
        first = opened.submit(probe.unit(x, "CAPTURE", durable=3 * 1024 * 1024))
        assert terminal(opened, first).terminal == "COMPLETED"
        claimed = col.charged(workspace)["claimed"]
        assert claimed > 2 * 1024 * 1024
        other, second_generation = job(x)
        probe.PLANS[second_generation] = probe.Plan(1)
        room = budget - w.CONTROL_RESERVE - w.metadata_bytes(workspace)
        wanted = room - claimed + 256 * 1024
        waiting = opened.submit(
            probe.unit(x, "CAPTURE", second_generation, other, durable=wanted)
        )
        state = opened.wait_activity(waiting, "never", 1.0)
        assert (state.state, state.limiting) == (
            "WAITING_FOR_ADMISSION",
            "WORKSPACE_BUDGET",
        )
        # Pressure never deletes or retires anything by itself.
        assert col.charged(workspace)["removed"] == 0
        holder = s.claim_publisher(workspace, job_, operation=op())
        col.retire_generation(holder, generation, operation=op())
        holder.close()
        report = opened.collect()
        assert report.decided and col.charged(workspace)["removed"] == claimed
        assert terminal(opened, waiting).terminal == "COMPLETED"
        verify_store(workspace)
    finally:
        for item in x.runtimes:
            item.close(timeout=30)
        workspace.close()


def test_a_failing_worker_does_not_disturb_another(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x)
    other, generation = job(x)
    gate = probe.Gate()
    probe.PLANS[x.generation] = probe.Plan(1, "FAIL")
    probe.PLANS[generation] = probe.Plan(1, gate, 1)
    good = opened.submit(probe.unit(x, "CAPTURE", generation, other))
    assert gate.entered.wait(TIMEOUT)
    bad = opened.submit(probe.unit(x, "CAPTURE"))
    state = terminal(opened, bad)
    assert state.terminal == "FAILED" and "SIMULATED_NATIVE_FAILURE" in str(
        state.failure
    )
    assert opened.query(good).terminal is None
    gate.released.set()
    assert terminal(opened, good).terminal == "COMPLETED"
    failed = probe.outcome(s.job_record(x.workspace, x.job).attempts[0])
    assert failed["source"] == "FAILED" and failed["transaction"] == "ROLLBACK_ACK"
    assert s.job_record(x.workspace, other).state == "ACTIVE"
    verify_store(x.workspace)


def test_cancel_racing_admission_returns_every_credit(setup):
    x = setup
    if x is None:
        return
    opened = runtime(x, workers=2, connections=2, queue=8)
    handles = []
    for _ in range(6):
        other, generation = job(x)
        probe.PLANS[generation] = probe.Plan(1)
        handle = opened.submit(probe.unit(x, "CAPTURE", generation, other))
        opened.cancel(handle)
        handles.append((handle, other))
    for handle, other in handles:
        state = terminal(opened, handle)
        assert state.terminal in ("CANCELLED_QUEUED", "CANCELLED"), state
        assert state.durable_cancel == "COMMITTED"
        assert s.job_record(x.workspace, other).state == "CANCELLED"
    assert opened._used == rt.Vector(0, 0, 0, 0, 0)
    open_admissions = probe.rows(
        x.workspace,
        "SELECT count(*) FROM admission a WHERE NOT EXISTS"
        " (SELECT 1 FROM admission_settlement s WHERE s.admission = a.identity)",
    )
    assert open_admissions == [(0,)]
    verify_store(x.workspace)
