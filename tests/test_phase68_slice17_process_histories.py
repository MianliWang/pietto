"""S17 process histories: one coordinator per workspace across processes, reader
versus collector in separate processes (both orders), real SIGKILL at the five
collection cuts, coordinator death with replacement and reconciliation, and a
lease prolonged by an inherited descriptor.

Children are spawned interpreters that open their own workspace and runtime;
no live handle crosses a process boundary (the inherited-descriptor case forks
on purpose, with no threads and no SQLite use in the fork). Captures use the
labelled ARROW_FREE_STORAGE_STEP; readers are ARROW_FREE_READER SnapshotReaders.
SIGKILL cuts are real process deaths at named protocol steps, not power-loss
certificates.
"""

import json
import os
import signal
import threading
import time

import pytest

import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice17_probe as probe
from _pietto_phase68_slice11_probe import (
    compiled_template,
    finish,
    kill,
    qualified,
    until,
)
from pietto._project import project_job_capture as c
from pietto._project import project_job_collection as col
from pietto._project import project_job_runtime as rt
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

op = probe.op

READER = r"""
workspace = attach()
snapshot = c.checkpoint_snapshot(workspace, config["job"], config["generation"])
output = c.StoredOutput(config["job"], config["generation"], snapshot.contract,
    snapshot.scheme, None)
reader = c.SnapshotReader(workspace, snapshot, output)
barrier("reading")
deadline = time.monotonic() + 120
while not os.path.exists(config["release"]) and time.monotonic() < deadline:
    time.sleep(0.01)
reader.close()
barrier("released")
"""

CUT = r"""
cut = config["cut"]
real_commit, real_record = w.commit, col._record_removals
def stop(*args, **kwargs):
    barrier("cut")
    hold()
if cut == "K1_decision_uncommitted":
    def commit(connection):
        if connection.execute("SELECT count(*) FROM tombstone").fetchone()[0]:
            stop()
        real_commit(connection)
    w.commit = commit
elif cut == "K2_committed_before_unlink":
    k._unlink = stop
elif cut == "K3_unlinked_before_sync":
    k._sync = stop
elif cut == "K4_synced_before_observation":
    col._record_removals = stop
elif cut == "K5_observed_before_reply":
    def record(workspace, owner, removed):
        def commit(connection):
            real_commit(connection)
            stop()
        w.commit = commit
        real_record(workspace, owner, removed)
    col._record_removals = record
opened = runtime()
opened.collect()
barrier("returned")
hold()
"""

HOLD = r"""
opened = runtime()
barrier("held")
emit({"epoch": opened.owner.epoch})
hold()
"""

COORDINATOR = r"""
opened = runtime()
gate = probe.Gate()
probe.PLANS[config["generation"]] = probe.Plan(2, gate)
unit = rt.Unit(mode="CAPTURE", root=config["workspace"], workspace=config["identity"],
    job=config["job"], generation=config["generation"],
    trust=(config["pin"], config["producer"], tuple(config["compatibility"])),
    source=probe.source(), durable=4 * 1024 * 1024)
handle = opened.submit(unit)
if not gate.entered.wait(60):
    raise SystemExit(3)
barrier("cut")
emit({"admission": handle})
hold()
"""

INHERITED = r"""
workspace = attach()
lease = k.Lease(workspace, config["generation"])
parent = os.getpid()
pid = os.fork()
if pid == 0:
    while os.getppid() == parent:
        time.sleep(0.05)
    os._exit(0)
lease.close()
barrier("forked")
emit({"grandchild": pid})
os.waitpid(pid, 0)
barrier("reaped")
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(tmp_path_factory.mktemp("s17p") / "small", entry="bundle")


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
    x = probe.setup_namespace(
        workspace=workspace,
        job=job,
        publisher=publisher,
        binding=binding,
        record=record,
        generation=generation,
        built=compiled,
        template=template,
        root=tmp_path,
        children=[],
    )
    yield x
    for process in x.children:
        if process.poll() is None:
            kill(process)
    for item in (x.publisher, x.workspace):
        if not item._closed:
            item.close()


def spawn(x, program, **extra):
    process = probe.child(program, probe.child_config(x, **extra))
    x.children.append(process)
    return process


def emitted(process) -> dict:
    return json.loads(process.stdout.readline())


def retired_capture(x, sizes=(1, 2)):
    """A complete, retired, unprotected generation (runtime closed after)."""
    opened = probe.open_runtime(x)
    try:
        session, admission = probe.grant_capture(
            opened, x, x.publisher, x.generation, x.binding, list(sizes)
        )
        opened.release(admission)
    finally:
        opened.close()
    col.retire_generation(x.publisher, x.generation, operation=op())
    return c.checkpoint_snapshot(x.workspace, x.job, x.generation)


def collect(x):
    opened = probe.open_runtime(x)
    try:
        return opened.collect()
    finally:
        opened.close()


def present(x, snapshot):
    names = set(os.listdir(os.path.join(x.workspace.root, "chunks")))
    return [m.file in names for m in snapshot.members]


def test_one_coordinator_across_processes_and_replacement(setup):
    x = setup
    if x is None:
        return
    holder = spawn(x, HOLD)
    until(holder, "held")
    first = emitted(holder)
    with pytest.raises(JobStoreError, match="RUNTIME_BUSY"):
        probe.open_runtime(x)
    code, _stderr = kill(holder)
    assert code == -signal.SIGKILL
    replacement = probe.open_runtime(x)
    try:
        assert replacement.owner.epoch == first["epoch"] + 1
    finally:
        replacement.close()


def test_reader_in_another_process_wins_then_collector(setup):
    x = setup
    if x is None:
        return
    snapshot = retired_capture(x)
    flag = x.root / "release"
    reader = spawn(x, READER, release=str(flag))
    until(reader, "reading")
    report = collect(x)
    assert report.busy == (x.generation,) and not report.decided
    assert all(present(x, snapshot))
    flag.write_text("")
    until(reader, "released")
    finish(reader)
    report = collect(x)
    assert report.decided and not any(present(x, snapshot))
    verify_store(x.workspace)


def test_collector_in_another_process_wins_then_reader_refuses(setup):
    x = setup
    if x is None:
        return
    snapshot = retired_capture(x)
    collector = spawn(x, CUT, cut="K2_committed_before_unlink")
    until(collector, "cut")
    outcome = []

    def read():
        # This thread's own handle (SQLite connections never cross threads).
        workspace = w.open_workspace(
            x.workspace.root, expected_identity=x.workspace.identity
        )
        output = c.StoredOutput(
            x.job, x.generation, snapshot.contract, snapshot.scheme, None
        )
        try:
            c.SnapshotReader(workspace, snapshot, output).close()
            outcome.append("READ")
        except JobStoreError as error:
            outcome.append(str(error))
        finally:
            workspace.close()

    thread = threading.Thread(target=read)
    thread.start()
    time.sleep(0.5)
    assert thread.is_alive() and not outcome  # bounded wait on the exclusive lease
    kill(collector)
    thread.join(60)
    assert outcome == ["CHUNK_COLLECTED"]
    assert all(present(x, snapshot))  # decided, not yet removed
    report = collect(x)
    assert sorted(b for _c, b in report.resumed) == ["UNLINKED", "UNLINKED"]


@pytest.mark.parametrize(
    "cut",
    [
        "K1_decision_uncommitted",
        "K2_committed_before_unlink",
        "K3_unlinked_before_sync",
        "K4_synced_before_observation",
        "K5_observed_before_reply",
    ],
)
def test_sigkill_at_each_collection_cut_reconciles_once(setup, cut):
    x = setup
    if x is None:
        return
    snapshot = retired_capture(x)
    collector = spawn(x, CUT, cut=cut)
    until(collector, "cut")
    code, _stderr = kill(collector)
    assert code == -signal.SIGKILL
    tombstones = probe.rows(x.workspace, "SELECT chunk, collection FROM tombstone")
    removals = probe.rows(x.workspace, "SELECT chunk, basis FROM removal")
    alive = present(x, snapshot)
    expected = {
        "K1_decision_uncommitted": (0, 0, [True, True]),
        "K2_committed_before_unlink": (2, 0, [True, True]),
        "K3_unlinked_before_sync": (2, 0, [False, False]),
        "K4_synced_before_observation": (2, 0, [False, False]),
        "K5_observed_before_reply": (2, 2, [False, False]),
    }[cut]
    assert (len(tombstones), len(removals), alive) == expected
    if tombstones:
        state = col.collection_state(x.workspace, tombstones[0][1])
        assert state is not None
        assert state[0][3] == 2 and len(state[1]) == 2
    report = collect(x)
    if cut == "K1_decision_uncommitted":
        assert (
            report.decided and sorted(b for _c, b in report.removed) == ["UNLINKED"] * 2
        )
    elif cut == "K2_committed_before_unlink":
        assert sorted(b for _c, b in report.resumed) == ["UNLINKED"] * 2
    elif cut in ("K3_unlinked_before_sync", "K4_synced_before_observation"):
        # The dead collector's unlink was never observed durable by it.
        assert sorted(b for _c, b in report.resumed) == ["ABSENT"] * 2
    else:
        assert not report.resumed and not report.decided
        assert sorted(b for _c, b in removals) == ["UNLINKED"] * 2
    assert not any(present(x, snapshot))
    again = collect(x)
    assert not again.decided and not again.resumed and not again.removed
    counts = verify_store(x.workspace)
    assert (counts["tombstones"], counts["removals"]) == (2, 2)


def test_coordinator_death_replacement_reconciles_without_restart(setup):
    x = setup
    if x is None:
        return
    x.publisher.close()
    coordinator = spawn(x, COORDINATOR)
    until(coordinator, "cut")
    admission = emitted(coordinator)["admission"]
    kill(coordinator)
    record = s.job_record(x.workspace, x.job)
    assert [a.terminal for a in record.attempts] == [None]
    replacement = probe.open_runtime(x)
    try:
        assert replacement.owner.epoch == 2
        claimed = probe.rows(
            x.workspace, "SELECT coalesce(sum(bytes), 0) FROM chunk_claim"
        )[0][0]
        assert replacement.reconcile() == ((admission, claimed),)
        fact = rt.admission_fact(x.workspace, admission)
        assert fact is not None and fact.settlement == (2, "RECONCILED", claimed)
        # Nothing restarted: the attempt stays open until a publisher acts.
        assert [a.terminal for a in s.job_record(x.workspace, x.job).attempts] == [None]
        publisher = s.claim_publisher(x.workspace, x.job, operation=op())
        try:
            s.interrupt_attempt(publisher, record.attempts[0].identity, operation=op())
            outcome = probe.outcome(s.job_record(x.workspace, x.job).attempts[0])
            assert (
                outcome["transaction"] == "UNKNOWN" and outcome["source"] == "UNKNOWN"
            )
            col.retire_generation(publisher, x.generation, operation=op())
        finally:
            publisher.close()
        report = replacement.collect()
        assert report.decided[0][2] == 1
    finally:
        replacement.close()
    verify_store(x.workspace)


def test_an_inherited_descriptor_keeps_the_subject_busy(setup):
    x = setup
    if x is None:
        return
    retired_capture(x)
    holder = spawn(x, INHERITED)
    until(holder, "forked")
    grandchild = emitted(holder)["grandchild"]
    report = collect(x)
    assert report.busy == (x.generation,) and not report.decided
    os.kill(grandchild, signal.SIGKILL)
    until(holder, "reaped")
    finish(holder)
    assert collect(x).decided
    verify_store(x.workspace)


def test_live_publisher_stage_survives_a_concurrent_collector(setup):
    x = setup
    if x is None:
        return
    opened = probe.open_runtime(x)
    try:
        admission = opened.grant(x.job, probe.unit(x, "CAPTURE"))
        session = s12.capture(x.workspace, x.publisher, x.generation, x.binding)
        session.admission = admission
        staged = s12.stage_frame(session, 2)
        report = opened.collect()
        assert (staged.identity, "OWNER_LIVE") in dict(report.blocked)[x.generation]
        session.publish(staged, operation=op())
        opened.release(admission)
    finally:
        opened.close()
    assert os.path.exists(os.path.join(x.workspace.root, "chunks", staged.name))
