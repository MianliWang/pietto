"""S17 v7 boundary, explicit retirement, protection roots and concurrent safe GC.

No database or Arrow: captures use ARROW_FREE_STORAGE_STEP frames through the
real claim, lease and publish path; closing owners are SYNTHETIC_CLOSED_OWNER;
S13/S15/S16 steps use their labelled Arrow-free replacements. Retirement,
fences, roots, leases, tombstones, unlinks, directory synchronization, removals
and the independent verifier run for real. Readers are real SnapshotReaders over
a binding-free StoredOutput (ARROW_FREE_READER: lease, fresh tombstone check and
raw member reads; IPC decoding is execution-profile evidence).
"""

import json
import os
import sqlite3
from typing import Any, cast
import threading
import time

import pytest

import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice13_probe as s13
import _pietto_phase68_slice14_probe as s14
import _pietto_phase68_slice15_probe as s15
import _pietto_phase68_slice16_probe as s16
import _pietto_phase68_slice17_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from pietto._project import project_job_capture as c
from pietto._project import project_job_chunks as k
from pietto._project import project_job_collection as col
from pietto._project import project_job_delivery as d
from pietto._project import project_job_publication as p
from pietto._project import project_job_replay as r
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

op = probe.op


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
    runtime = probe.open_runtime(
        probe.setup_namespace(workspace=workspace), workers=3, connections=3
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
        runtime=runtime,
    )
    yield x
    for opened in {id(runtime): runtime, id(x.runtime): x.runtime}.values():
        opened.close()
    for item in (x.publisher, x.workspace):
        if not item._closed:
            item.close()


def captured(x, sizes=(2, 1, 3), generation=None):
    """A complete capture under a granted admission; returns its generation."""
    generation = generation or x.generation
    session, admission = probe.grant_capture(
        x.runtime, x, x.publisher, generation, x.binding, list(sizes)
    )
    x.runtime.release(admission)
    return session


def collect(x, **quanta):
    return x.runtime.collect(**quanta)


def present(x, session=None, generation=None):
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, generation or x.generation)
    names = set(os.listdir(os.path.join(x.workspace.root, "chunks")))
    return [m.file in names for m in snapshot.members]


def reader(x, snapshot):
    """ARROW_FREE_READER: a real SnapshotReader over a binding-free output."""
    output = c.StoredOutput(
        snapshot.job, snapshot.generation, snapshot.contract, snapshot.scheme, None
    )
    return c.SnapshotReader(x.workspace, snapshot, output)


def history(x):
    return {
        table: probe.rows(x.workspace, f"SELECT count(*) FROM {table}")[0][0]
        for table in (
            "chunk",
            "checkpoint",
            "checkpoint_member",
            "attempt",
            "operation",
        )
    }


# --- v7 boundary --------------------------------------------------------------


def test_v7_is_an_explicit_closed_capability_set(tmp_path, built):
    if not qualified(tmp_path):
        return
    v6, v7 = w.expected_schema(w.FORMAT_V6), w.expected_schema(w.FORMAT_V7)
    added = {row[1] for row in v7} - {row[1] for row in v6}
    assert added == {
        "runtime_owner",
        "admission",
        "admission_settlement",
        "chunk_claim",
        "chunk_claim_admission",
        "generation_retirement",
        "collection",
        "tombstone",
        "removal",
    } | {name for name in added if name.startswith("sqlite_autoindex_")}
    assert {row for row in v6} <= {row for row in v7}
    workspace = w.create_workspace(str(tmp_path / "v7"), format=w.FORMAT_V7)
    try:
        assert w.supports(workspace, "bounded-job-runtime")
        assert w.supports(workspace, "concurrent-gc")
        envelope = json.loads((tmp_path / "v7" / "workspace.json").read_text())
        assert envelope["features"] == [
            "result-chunks",
            "saved-replay",
            "extraction-resume",
            "cooperative-delivery",
            "complete-publication",
            "bounded-job-runtime",
            "concurrent-gc",
        ]
        assert workspace.use().execute("PRAGMA user_version").fetchone() == (7,)
    finally:
        workspace.close()
    w.open_workspace(str(tmp_path / "v7"), expected_identity=workspace.identity).close()
    raw = (tmp_path / "v7" / "workspace.json").read_bytes()
    for bad in (
        raw.replace(b',"concurrent-gc"', b""),
        raw.replace(b',"bounded-job-runtime"', b""),
        raw.replace(b"job-workspace.v7", b"job-workspace.v8"),
        raw.replace(b"job-workspace.v7", b"job-workspace.v6"),
    ):
        with pytest.raises(JobStoreError, match="WORKSPACE_FORMAT"):
            w.read_envelope(bad)
    # v6 and older: S17 refuses before any change; capture needs no admission.
    template, _compiled = built
    old, job, publisher, binding, _record, generation = s16.store(
        tmp_path / "v6", template
    )
    try:
        before = probe.rows(old, "SELECT * FROM operation")
        from pietto._project import project_job_runtime as rt

        with pytest.raises(JobStoreError, match="WORKSPACE_RUNTIME_FORMAT"):
            rt.claim_runtime(old, rt.Policy())
        with pytest.raises(JobStoreError, match="WORKSPACE_COLLECTION_FORMAT"):
            col.retire_generation(publisher, generation, operation=op())
        with pytest.raises(JobStoreError, match="WORKSPACE_COLLECTION_FORMAT"):
            col.protection(old, job)
        assert probe.rows(old, "SELECT * FROM operation") == before
        session = s12.capture(old, publisher, generation, binding)
        session.publish(s12.stage_frame(session, 2), operation=op())
        assert not os.path.exists(os.path.join(old.root, "locks", generation + ".life"))
        assert set(c.classify_files(old)) == {
            "referenced",
            "missing",
            "orphans",
            "staging",
            "foreign",
        }
    finally:
        publisher.close()
        old.close()


def test_v7_capture_without_admission_refuses_before_any_file(setup):
    x = setup
    if x is None:
        return
    session = s12.capture(x.workspace, x.publisher, x.generation, x.binding)
    with pytest.raises(JobStoreError, match="RUNTIME_ADMISSION_REQUIRED"):
        s12.stage_frame(session, 2)
    assert probe.files(x.workspace.root) == []
    assert probe.rows(x.workspace, "SELECT count(*) FROM chunk_claim") == [(0,)]
    # A foreign object in place of an admission is no authority either.
    session.admission = object()
    with pytest.raises(JobStoreError, match="RUNTIME_ADMISSION_REQUIRED"):
        session._claim(x.workspace, "chk-" + "0" * 32, 10)


def test_claims_precede_files_and_bind_publication(setup):
    x = setup
    if x is None:
        return
    admission = x.runtime.grant(x.job, probe.unit(x, "CAPTURE"))
    session = s12.capture(x.workspace, x.publisher, x.generation, x.binding)
    session.admission = admission
    staged = s12.stage_frame(session, 3)
    claim = probe.rows(
        x.workspace, "SELECT chunk, attempt, admission, bytes FROM chunk_claim"
    )
    assert claim == [
        (staged.identity, session.attempt.identity, admission.identity, staged.size)
    ]
    assert probe.files(x.workspace.root) == [("chunks", staged.name)]
    # The claim is bound into the publication transaction (exact object/size).
    forged = c.StagedChunk(
        session,
        staged.identity,
        staged.start,
        staged.stop,
        staged.batches,
        staged.name,
        staged.size + 1,
        staged.digest,
        staged.descriptor,
        staged.device,
        staged.inode,
        staged.changed,
    )
    session._staged[staged.identity] = forged
    with pytest.raises(JobStoreError, match="CHUNK_CLAIM"):
        session.publish(forged, operation=op())
    session._staged[staged.identity] = staged
    session.publish(staged, operation=op())
    fact = x.runtime.release(admission)
    assert fact.settlement == (x.runtime.owner.epoch, "RELEASED", staged.size)
    assert verify_store(x.workspace)["claims"] == 1


def test_allowance_is_exact_per_admission(setup):
    x = setup
    if x is None:
        return
    small = probe.unit(x, "CAPTURE", durable=1000)
    admission = x.runtime.grant(x.job, small)
    session = s12.capture(x.workspace, x.publisher, x.generation, x.binding)
    session.admission = admission
    first = s12.stage_frame(session, 1, size=64)
    assert first.size < 1000
    with pytest.raises(JobStoreError, match="RUNTIME_ALLOWANCE"):
        s12.stage_frame(session, 1, size=2000)
    # Refused before the file exists: no name, no claim, an honest hole.
    assert len(probe.files(x.workspace.root)) == 1
    assert probe.rows(x.workspace, "SELECT count(*) FROM chunk_claim") == [(1,)]
    x.runtime.release(admission)
    with pytest.raises(JobStoreError, match="RUNTIME_ADMISSION_REQUIRED"):
        session._claim(x.workspace, "chk-" + "1" * 32, 10)


# --- retirement --------------------------------------------------------------


def test_retirement_is_explicit_monotone_and_fenced(setup):
    x = setup
    if x is None:
        return
    session = s12.capture(x.workspace, x.publisher, x.generation, x.binding)
    session.admission = x.runtime.grant(x.job, probe.unit(x, "CAPTURE"))
    session.publish(s12.stage_frame(session, 2), operation=op())
    with pytest.raises(JobStoreError, match="ATTEMPT_OPEN"):
        col.retire_generation(x.publisher, x.generation, operation=op())
    probe.close_owner(session.owner, session.observed)
    session.end(operation=op())
    s.record_attempt(x.publisher, session.attempt, session.owner, operation=op())
    x.runtime.release(session.admission)
    before = history(x)
    operation = op()
    first = col.retire_generation(x.publisher, x.generation, operation=operation)
    assert first.observation == "COMMITTED_THIS_CALL"
    again = col.retire_generation(x.publisher, x.generation, operation=operation)
    assert again.observation == "PREVIOUSLY_COMMITTED"
    with pytest.raises(JobStoreError, match="GENERATION_RETIRED"):
        col.retire_generation(x.publisher, x.generation, operation=op())
    # Production, new references and publication of it are refused.
    with pytest.raises(JobStoreError, match="GENERATION_RETIRED"):
        s.open_attempt(x.publisher, x.generation, x.binding, operation=op())
    with pytest.raises(JobStoreError, match="GENERATION_RETIRED"):
        c.retain_checkpoint(
            x.publisher, x.generation, scope={"why": "s17"}, operation=op()
        )
    with pytest.raises(JobStoreError, match="GENERATION_RETIRED"):
        r.register_consumer(
            x.publisher,
            s13.accept(x.workspace, x.job, x.generation, x.built),
            operation=op(),
        )
    with pytest.raises(JobStoreError, match="GENERATION_RETIRED"):
        p.prepare_publication(
            x.publisher,
            s16.accept(
                x.workspace, x.job, x.generation, x.built, session.attempt.identity
            ),
            operation=op(),
        )
    assert history(x) == {**before, "operation": before["operation"] + 1}
    # Cancellation may coexist with retirement but never performs it.
    other = probe.generation_of(x.publisher, x.record, x.binding)
    s.cancel_job(x.publisher, operation=op())
    assert (
        col.retire_generation(x.publisher, other, operation=op()).get("generation")
        == other
    )
    assert verify_store(x.workspace)["retirements"] == 2


def test_publication_and_retirement_are_mutually_ordered(setup):
    x = setup
    if x is None:
        return
    first = captured(x, (2, 2))
    s16.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, first.attempt.identity
    )
    with pytest.raises(JobStoreError, match="GENERATION_PUBLISHED"):
        col.retire_generation(x.publisher, x.generation, operation=op())
    # Retirement first: the later preparation (a new reference) refuses.
    other = probe.generation_of(x.publisher, x.record, x.binding)
    second = captured(x, (1,), other)
    col.retire_generation(x.publisher, other, operation=op())
    with pytest.raises(JobStoreError, match="GENERATION_RETIRED"):
        s16.publish(
            x.workspace, x.job, x.publisher, other, x.built, second.attempt.identity
        )
    # Publication survives cancel, reader close and every collection attempt.
    s.cancel_job(x.publisher, operation=op())
    report = collect(x)
    published = {t[0] for t in probe.rows(x.workspace, "SELECT chunk FROM tombstone")}
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    assert not published & {m.chunk for m in snapshot.members}
    assert all(present(x))
    assert report.decided and report.decided[0][1] == other
    assert p.publication(x.workspace, x.job, x.generation) is not None
    verify_store(x.workspace)


# --- protection roots ------------------------------------------------------------


def test_latest_checkpoint_and_islands_protect_until_retirement(setup):
    x = setup
    if x is None:
        return
    session = s12.capture(x.workspace, x.publisher, x.generation, x.binding)
    admission = x.runtime.grant(x.job, probe.unit(x, "CAPTURE"))
    session.admission = admission
    staged = [s12.stage_frame(session, n) for n in (2, 2, 2)]
    # An island after a hole: [0, 2) and [4, 6) published, [2, 4) never.
    session.publish(staged[0], operation=op())
    session.publish(staged[2], operation=op())
    probe.close_owner(
        session.owner,
        2,
        source="FAILED",
        transaction="ROLLBACK_ACK",
        delivery="FAILED",
        primary=("read", "SIMULATED"),
    )
    session._terminal = "FAILED"
    session.end(operation=op())
    s.record_attempt(x.publisher, session.attempt, session.owner, operation=op())
    x.runtime.release(admission)
    report = collect(x)
    # The never-published staged file is abandoned (terminal attempt); the
    # latest checkpoint's members, including the island, are protected.
    assert [d[2] for d in report.decided] == [1]
    assert {t[0] for t in probe.rows(x.workspace, "SELECT chunk FROM tombstone")} == {
        staged[1].identity
    }
    assert all(present(x))
    (generation,) = col.protection(x.workspace, x.job)
    assert [root[0] for root in generation.roots] == ["LATEST"]
    assert {
        m.chunk for m in c.checkpoint_snapshot(x.workspace, x.job, x.generation).members
    } == set(generation.protected)
    col.retire_generation(x.publisher, x.generation, operation=op())
    report = collect(x)
    assert sorted(t[1] for t in report.removed) == ["UNLINKED", "UNLINKED"]
    assert not any(present(x))
    verify_store(x.workspace)


@pytest.mark.parametrize(
    "root", ["EXPLICIT", "CONSUMER", "PREPARATION", "READER", "ALL"]
)
def test_each_root_protects_alone_and_together(setup, root):
    x = setup
    if x is None:
        return
    first = captured(x, (2, 2))
    roots = []
    if root in ("EXPLICIT", "ALL"):
        held = c.retain_checkpoint(
            x.publisher, x.generation, scope={"why": "s17"}, operation=op()
        )
        roots.append(("release", held.retention))
    if root in ("CONSUMER", "ALL"):
        result = r.register_consumer(
            x.publisher,
            s13.accept(x.workspace, x.job, x.generation, x.built),
            operation=op(),
        )
        roots.append(("release", result.get("retention")))
    if root in ("PREPARATION", "ALL"):
        prepared = p.prepare_publication(
            x.publisher,
            s16.accept(
                x.workspace, x.job, x.generation, x.built, first.attempt.identity
            ),
            operation=op(),
        )
        roots.append(("release", prepared.retention))
    if root in ("READER", "ALL"):
        held_reader = reader(x, c.checkpoint_snapshot(x.workspace, x.job, x.generation))
        roots.append(("close", held_reader))
    col.retire_generation(x.publisher, x.generation, operation=op())
    reasons = {g: rs for g, rs in collect(x).blocked}
    while roots:
        report = collect(x)
        assert not report.decided and all(present(x))
        assert report.busy or reasons
        kind, item = roots.pop(0)
        if kind == "release":
            c.release_retention(x.publisher, item, operation=op())
        else:
            item.close()
    report = collect(x)
    assert report.decided and not any(present(x))
    verify_store(x.workspace)


def test_pending_s15_window_is_protected_until_resolved(setup, tmp_path):
    x = setup
    if x is None:
        return
    captured(x, (2,))
    handle = s15.sink(tmp_path / "sink")
    stream, session = s15.registered(
        x.workspace, x.job, x.publisher, x.generation, x.built, handle
    )
    window = session.window
    handle.close()  # the sink becomes unavailable: the issuance stays unresolved
    item = session.next(2, operation=op())
    assert isinstance(item, d.Issued)
    outcomes = session.send(item)
    assert set(outcomes.values()) <= {"UNKNOWN", "NOT_SENT"}
    col.retire_generation(x.publisher, x.generation, operation=op())
    with pytest.raises(JobStoreError, match="RETENTION_OBLIGATION"):
        c.release_retention(x.publisher, window.retention, operation=op())
    with pytest.raises(JobStoreError, match="STREAM_OBLIGATION_UNRESOLVED"):
        d.retire_stream(x.publisher, stream, operation=op())
    report = collect(x)
    assert not report.decided
    reasons = dict(report.blocked)[x.generation]
    assert ("ROOT", "UNRESOLVED_WINDOW", stream) in reasons
    assert ("ROOT", "WINDOW", window.retention) in reasons
    # Resolution through the sink, then the stream's own retirement.
    reopened = k_sink(handle)
    session.sink = s15.accept_sink(reopened)
    session.reconcile(item)
    session.confirm(item, operation=op())
    d.retire_stream(x.publisher, stream, operation=op())
    assert collect(x).decided
    reopened.close()
    session.close()
    verify_store(x.workspace)


def k_sink(handle):
    from pietto._project.project_job_sink import open_sink

    return open_sink(handle.root, expected_identity=handle.identity)


def test_retired_generation_with_live_consumer_then_released(setup):
    x = setup
    if x is None:
        return
    captured(x, (2, 1))
    acceptance = s13.accept(x.workspace, x.job, x.generation, x.built)
    registered = r.register_consumer(x.publisher, acceptance, operation=op())
    col.retire_generation(x.publisher, x.generation, operation=op())
    # Existing valid fixed-scope use continues under the original rules.
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    extents, end = s13.drain(replay, 2)
    assert extents == [(0, 2), (2, 3)] and end.terminal == r.EXHAUSTED
    replay.close()
    assert not collect(x).decided
    # A new consumer of a retired generation is refused.
    with pytest.raises(JobStoreError, match="GENERATION_RETIRED"):
        r.register_consumer(
            x.publisher,
            s13.accept(x.workspace, x.job, x.generation, x.built),
            operation=op(),
        )
    c.release_retention(x.publisher, registered.get("retention"), operation=op())
    report = collect(x)
    assert report.decided[0][2] == 2
    assert {s for _c, s, _p in col.availability(x.workspace, x.job, x.generation)} == {
        "REMOVED_OBSERVED"
    }
    verify_store(x.workspace)


# --- the mandatory positive and its history ----------------------------------


def test_retired_committed_generation_is_collected_with_history_intact(setup):
    x = setup
    if x is None:
        return
    session = captured(x, (2, 1, 3))
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    sizes = sum(m.bytes for m in snapshot.members)
    before_charge = col.charged(x.workspace)
    before = history(x)
    col.retire_generation(x.publisher, x.generation, operation=op())
    states = col.availability(x.workspace, x.job, x.generation)
    assert {s for _c, s, _p in states} == {"RETIRED_UNPROTECTED"}
    report = collect(x)
    assert len(report.decided) == 1 and report.decided[0][2:] == (3, sizes)
    assert sorted(b for _c, b in report.removed) == ["UNLINKED"] * 3
    assert probe.files(x.workspace.root) == []
    after = col.charged(x.workspace)
    assert after["removed"] == sizes and after["claimed"] == before_charge["claimed"]
    assert after["decided_unremoved"] == 0
    # History stays: chunks, checkpoints, members, attempts and operations.
    assert history(x) == {**before, "operation": before["operation"] + 1}
    again = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    assert again.members == snapshot.members
    files = c.classify_files(x.workspace)
    assert files["missing"] == () and len(files["removed"]) == 3
    assert files["referenced"] == ()
    # Current use refuses explicitly; nothing is resurrected or refetched.
    with pytest.raises(JobStoreError, match="CHUNK_COLLECTED"):
        reader(x, again)
    repeat = collect(x)
    assert not repeat.decided and not repeat.removed and not repeat.resumed
    counts = verify_store(x.workspace)
    assert (counts["collections"], counts["tombstones"], counts["removals"]) == (
        1,
        3,
        3,
    )
    assert session.attempt.identity in {
        row[0]
        for row in probe.rows(x.workspace, "SELECT attempt FROM attempt_terminal")
    }


def test_stale_snapshot_and_reader_orders_in_process(setup):
    x = setup
    if x is None:
        return
    captured(x, (2, 2))
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    col.retire_generation(x.publisher, x.generation, operation=op())
    # Reader first: the collector reports the subject busy and waits for nobody.
    held = reader(x, snapshot)
    data = k.read_chunk_file(
        held._directory,
        snapshot.members[0].file,
        snapshot.members[0].bytes,
        snapshot.members[0].digest,
    )
    report = collect(x)
    assert report.busy == (x.generation,) and not report.decided
    held.close()
    # Collector first: the stale snapshot (taken earlier) is refused at use.
    report = collect(x)
    assert report.decided
    with pytest.raises(JobStoreError, match="CHUNK_COLLECTED"):
        reader(x, snapshot)
    assert data[:16] == k.MAGIC


def test_busy_subject_does_not_block_other_generations(setup):
    x = setup
    if x is None:
        return
    other = probe.generation_of(x.publisher, x.record, x.binding)
    captured(x, (1,))
    captured(x, (1,), other)
    for generation in (x.generation, other):
        col.retire_generation(x.publisher, generation, operation=op())
    lease = k.Lease(x.workspace, x.generation)
    try:
        report = collect(x)
        assert report.busy == (x.generation,)
        assert [d[1] for d in report.decided] == [other]
    finally:
        lease.close()
    assert [d[1] for d in collect(x).decided] == [x.generation]


def test_fully_protected_workspace_reports_honest_reasons(setup):
    x = setup
    if x is None:
        return
    captured(x, (1, 1))
    report = collect(x)
    assert not report.decided and not report.removed
    reasons = dict(report.blocked)[x.generation]
    assert (None, "NOT_RETIRED") in reasons
    assert any(item[:2] == ("ROOT", "LATEST") for item in reasons)


# --- abandoned claims, aliases, foreign and missing objects --------------------


def test_live_stage_is_kept_abandoned_claim_is_collected(setup):
    x = setup
    if x is None:
        return
    admission = x.runtime.grant(x.job, probe.unit(x, "CAPTURE"))
    session = s12.capture(x.workspace, x.publisher, x.generation, x.binding)
    session.admission = admission
    live = s12.stage_frame(session, 2)
    report = collect(x)
    assert not report.decided
    assert (live.identity, "OWNER_LIVE") in dict(report.blocked)[x.generation]
    probe.close_owner(session.owner, 2)
    session.end(operation=op())
    s.record_attempt(x.publisher, session.attempt, session.owner, operation=op())
    x.runtime.release(admission)
    report = collect(x)
    assert [(c_, b) for c_, b in report.removed] == [(live.identity, "UNLINKED")]
    with pytest.raises(JobStoreError, match="ATTEMPT_TERMINAL|CHUNK_COLLECTED"):
        session.publish(live, operation=op())
    tombstone = probe.rows(x.workspace, "SELECT basis FROM tombstone")
    assert tombstone == [("ABANDONED",)]
    verify_store(x.workspace)


def test_aliases_are_removed_together_and_credited_once(setup):
    x = setup
    if x is None:
        return
    admission = x.runtime.grant(x.job, probe.unit(x, "CAPTURE"))
    session = s12.capture(x.workspace, x.publisher, x.generation, x.binding)
    session.admission = admission
    identity = w.new_identity("chk")
    text, data = k.encode_chunk(
        {
            "attempt": session.attempt.identity,
            "batches": 1,
            "binding": session.record,
            "chunk": identity,
            "contract": session.contract,
            "coordinates": None,
            "generation": x.generation,
            "job": x.job,
            "kind": "ORDINARY",
            "rows": 1,
            "start": 0,
            "stop": 1,
            "terminal": None,
            "workspace": x.workspace.identity,
        },
        s12.synthetic_frame(1, contract=bytes.fromhex(session.contract)),
    )
    session._claim(x.workspace, identity, len(data))
    # The exact state of a death after link and before the staging unlink.
    staged = os.path.join(x.workspace.root, "staging", identity + k.STAGED)
    with open(os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as f:
        f.write(data)
    os.link(staged, os.path.join(x.workspace.root, "chunks", identity + k.SUFFIX))
    before = col.charged(x.workspace)
    probe.close_owner(session.owner, 0)
    s.record_attempt(x.publisher, session.attempt, session.owner, operation=op())
    x.runtime.release(admission)
    report = collect(x)
    assert report.removed == ((identity, "UNLINKED"),)
    objects = json.loads(probe.rows(x.workspace, "SELECT objects FROM tombstone")[0][0])
    assert sorted(o[0] for o in objects) == ["chunks", "staging"]
    assert len({(o[2], o[3]) for o in objects}) == 1
    assert probe.files(x.workspace.root) == []
    after = col.charged(x.workspace)
    assert after["removed"] - before["removed"] == len(data)


def test_foreign_replaced_and_missing_objects_are_refused_and_preserved(setup):
    x = setup
    if x is None:
        return
    captured(x, (1, 1))
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    chunks_dir = os.path.join(x.workspace.root, "chunks")
    # An unclaimed name is never a candidate (not even when unreferenced).
    foreign = os.path.join(chunks_dir, "chk-" + "f" * 32 + ".chunk")
    with open(os.open(foreign, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as f:
        f.write(b"x")
    assert c.classify_files(x.workspace)["orphans"] == ("chk-" + "f" * 32 + ".chunk",)
    # A committed file missing without a decision is corruption, also retired.
    first = os.path.join(chunks_dir, snapshot.members[0].file)
    os.unlink(first)
    assert c.classify_files(x.workspace)["missing"] == (snapshot.members[0].file,)
    states = dict(
        (c_, s_) for c_, s_, _p in col.availability(x.workspace, x.job, x.generation)
    )
    assert states[snapshot.members[0].chunk] == "MISSING"
    col.retire_generation(x.publisher, x.generation, operation=op())
    # A replaced object (new inode under the old name) is refused too.
    second = os.path.join(chunks_dir, snapshot.members[1].file)
    data = open(second, "rb").read()
    os.unlink(second)
    with open(os.open(second, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as f:
        f.write(data)
    report = collect(x)
    assert (snapshot.members[0].chunk, "CHUNK_MISSING") in report.refused
    # (the replaced file is a new, untracked object; it is decided with its
    # current identity, never trusted from before)
    assert os.path.exists(foreign)
    verify_store(x.workspace)


def test_decided_object_replaced_before_unlink_is_refused(setup, monkeypatch):
    x = setup
    if x is None:
        return
    captured(x, (1,))
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    col.retire_generation(x.publisher, x.generation, operation=op())
    path = os.path.join(x.workspace.root, "chunks", snapshot.members[0].file)
    real = col._remove

    def swap(workspace, objects):
        data = open(path, "rb").read()
        os.unlink(path)
        with open(
            os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
        ) as f:
            f.write(data)
        return real(workspace, objects)

    monkeypatch.setattr(col, "_remove", swap)
    report = collect(x)
    assert report.decided and not report.removed
    assert report.refused == ((snapshot.members[0].chunk, "COLLECTION_OBJECT"),)
    assert os.path.exists(path)
    monkeypatch.setattr(col, "_remove", real)
    again = collect(x)
    assert again.refused and not again.resumed and os.path.exists(path)
    assert c.classify_files(x.workspace)["collected"] == (snapshot.members[0].file,)


# --- injected cuts, resume and query ----------------------------------------------


def test_injected_cuts_resume_exactly_the_pinned_set(setup, monkeypatch):
    x = setup
    if x is None:
        return
    captured(x, (1, 1))
    col.retire_generation(x.publisher, x.generation, operation=op())
    real_unlink, real_sync = k._unlink, k._sync
    # Decision committed, deletion fails before any unlink.
    monkeypatch.setattr(
        k, "_unlink", lambda name, fd: (_ for _ in ()).throw(OSError(5, "EIO"))
    )
    with pytest.raises(OSError):
        collect(x)
    decided = probe.rows(x.workspace, "SELECT collection FROM tombstone")
    assert len(decided) == 2 and probe.rows(
        x.workspace, "SELECT count(*) FROM removal"
    ) == [(0,)]
    pending = col.collection_state(x.workspace, decided[0][0])
    assert pending is not None and pending[1][0][3] is None
    # Another candidate appears; a resume must not expand the pinned set.
    other = probe.generation_of(x.publisher, x.record, x.binding)
    captured(x, (1,), other)
    monkeypatch.setattr(k, "_unlink", real_unlink)
    # After the unlink, the directory synchronization fails: nothing recorded.
    monkeypatch.setattr(k, "_sync", lambda fd: (_ for _ in ()).throw(OSError(5, "EIO")))
    with pytest.raises(OSError):
        collect(x)
    assert probe.rows(x.workspace, "SELECT count(*) FROM removal") == [(0,)]
    assert len(c.classify_files(x.workspace)["collected_absent"]) == 2
    monkeypatch.setattr(k, "_sync", real_sync)
    report = collect(x)
    # The earlier unlink was not observed as durable by its caller: ABSENT.
    assert sorted(b for _c, b in report.resumed) == ["ABSENT", "ABSENT"]
    assert not report.decided  # `other` is not retired
    state = col.collection_state(x.workspace, decided[0][0])
    assert state is not None
    assert state[0][3] == 2 and {row[3] for row in state[1]} == {"ABSENT"}
    assert col.collection_state(x.workspace, "gcd-" + "0" * 32) is None
    verify_store(x.workspace)


def test_decision_commit_unknown_is_queried_not_repeated(setup, monkeypatch):
    x = setup
    if x is None:
        return
    captured(x, (2,))
    col.retire_generation(x.publisher, x.generation, operation=op())
    real = w.commit
    calls = []

    def lost(connection):
        real(connection)
        if not calls:
            calls.append(1)
            raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(w, "commit", lost)
    with pytest.raises(JobStoreError, match="STORE_COMMIT_UNKNOWN"):
        collect(x)
    monkeypatch.setattr(w, "commit", real)
    # The decision exists (COMMIT happened); the next pass resumes it.
    assert probe.rows(x.workspace, "SELECT count(*) FROM tombstone") == [(1,)]
    report = collect(x)
    assert report.resumed and not report.decided
    verify_store(x.workspace)


# --- S14 old islands and live candidates ------------------------------------------


def test_s14_continuation_inputs_and_candidates_are_protected(tmp_path, monkeypatch):
    if not qualified(tmp_path):
        return
    from pietto._project import project_job_extraction as x_

    template, compiled, values = s14.refined_template(tmp_path / "refined")
    s14.synthetic(monkeypatch)
    probe.arrow_free(monkeypatch)
    workspace, job, publisher, binding, record, generation = s12.store(
        tmp_path / "ws", template, values, format=w.FORMAT_V7
    )
    runtime = probe.open_runtime(probe.setup_namespace(workspace=workspace))
    built = probe.setup_namespace(
        workspace=workspace, job=job, generation=generation, built=compiled
    )
    try:
        admission = runtime.grant(job, probe.unit(built, "CAPTURE"))
        attempt = s.open_attempt(publisher, generation, binding, operation=op())
        session = x_.begin_extraction(
            publisher, attempt, s14.owner(binding), operation=op()
        )
        session.admission = admission
        staged = [s14.stage_refined(session, n) for n in (2, 2, 2)]
        session.publish(staged[0], operation=op())
        session.publish(staged[2], operation=op())  # an island after a hole
        runtime.release(admission)
        # The original dies: a new publisher interrupts it (old UNKNOWN kept).
        publisher.close()
        publisher, acceptance, attempt = s14.recover(
            workspace, job, generation, compiled, values
        )
        report = runtime.collect()
        # Old islands are the latest checkpoint; the dead attempt's unpublished
        # stage is abandoned (terminal INTERRUPTED) and only it is collected.
        assert [b for _c, b in report.removed] == ["UNLINKED"]
        assert {t[0] for t in probe.rows(workspace, "SELECT chunk FROM tombstone")} == {
            staged[1].identity
        }
        second = runtime.grant(job, probe.unit(built, "RECOVER"))
        continuation = x_.begin_continuation(
            publisher,
            acceptance,
            attempt,
            s14.owner(acceptance.binding),
            operation=op(),
        )
        continuation.admission = second
        pending = s14.drive(continuation, [2, 2], publish=False)
        assert pending and not continuation.reconciled
        # Before the barrier: candidates are live claims, islands are roots.
        report = runtime.collect()
        assert not report.decided
        reasons = dict(report.blocked)[generation]
        assert all((item.identity, "OWNER_LIVE") in reasons for item in pending)
        names = set(os.listdir(os.path.join(workspace.root, "chunks")))
        assert {staged[0].name, staged[2].name} <= names
        assert {item.name for item in pending} <= names
        outcome = s.job_record(workspace, job).attempts[0]
        assert outcome.terminal == "INTERRUPTED"
        assert probe.outcome(outcome)["transaction"] == "UNKNOWN"
        continuation.close()
        runtime.release(second)
        verify_store(workspace)
    finally:
        runtime.close()
        publisher.close()
        workspace.close()


# --- product verifier over coordinated row damages ---------------------------------


def damaged(x, statement):
    """A copy of the store with one coordinated row damage (FKs off for the edit)."""
    copy = x.root / ("damage-" + w.new_identity("op")[3:11])
    copy.mkdir(mode=0o700)
    target = copy / "store.sqlite"
    with sqlite3.connect(target) as out:
        x.workspace.use().backup(out)
    out.close()
    connection = sqlite3.connect(target, isolation_level=None)
    connection.execute("PRAGMA foreign_keys = OFF")
    for sql, values in statement:
        connection.execute(sql, values)
    connection.close()
    return target


def verify_copy(x, target):
    """verify_store over the damaged copy through a minimal read-only handle."""
    connection = sqlite3.connect(target, isolation_level=None)
    handle = probe.setup_namespace(
        identity=x.workspace.identity,
        format=x.workspace.format,
        use=lambda: connection,
        _retired=False,
    )
    try:
        from pietto._project import project_job_store_verification as v

        def read(_workspace, body):
            connection.execute("BEGIN")
            try:
                return body(connection)
            finally:
                connection.execute("ROLLBACK")

        original = v.read
        v.read = read
        try:
            return v.verify_store(cast(Any, handle))
        finally:
            v.read = original
    finally:
        connection.close()


@pytest.mark.parametrize(
    "case",
    [
        "unchanged_copy",
        "protected_tombstone",
        "retired_published",
        "chunk_without_claim",
        "settlement_claimed",
        "over_allowance",
        "removal_runtime",
    ],
)
def test_verify_store_rejects_v7_damages(setup, case):
    x = setup
    if x is None:
        return
    first = captured(x, (1, 1))
    s16.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, first.attempt.identity
    )
    other = probe.generation_of(x.publisher, x.record, x.binding)
    captured(x, (1,), other)
    col.retire_generation(x.publisher, other, operation=op())
    collect(x)
    verify_store(x.workspace)
    member = c.checkpoint_snapshot(x.workspace, x.job, x.generation).members[0]
    forged = w.new_identity("gcd")
    statements = {
        "unchanged_copy": ([], None),
        "protected_tombstone": (
            [
                (
                    "INSERT INTO collection(identity, job, generation, runtime, members)"
                    " VALUES (?, ?, ?, 1, 1)",
                    (forged, x.job, x.generation),
                ),
                (
                    "INSERT INTO tombstone(chunk, collection, generation, basis, objects,"
                    " bytes) VALUES (?, ?, ?, 'RETIRED', ?, ?)",
                    (
                        member.chunk,
                        forged,
                        x.generation,
                        json.dumps(
                            [["chunks", member.file, 1, 1, 1, member.bytes]],
                            separators=(",", ":"),
                        ),
                        member.bytes,
                    ),
                ),
            ],
            "STORE_INVARIANT_TOMBSTONE_ROOTS",
        ),
        "retired_published": (
            [
                (
                    "INSERT INTO generation_retirement SELECT ?, job, publisher_epoch,"
                    " publisher_instance FROM generation_retirement LIMIT 1",
                    (x.generation,),
                )
            ],
            "STORE_INVARIANT_RETIREMENT_ROWS",
        ),
        "chunk_without_claim": (
            [("DELETE FROM chunk_claim WHERE chunk = ?", (member.chunk,))],
            "STORE_INVARIANT_CLAIM_HISTORY",
        ),
        "settlement_claimed": (
            [("UPDATE admission_settlement SET claimed = claimed + 1", ())],
            "STORE_INVARIANT_SETTLEMENT_ROWS",
        ),
        "over_allowance": (
            [("UPDATE admission SET durable = 1", ())],
            "STORE_INVARIANT_ADMISSION_ROWS",
        ),
        "removal_runtime": (
            [("UPDATE removal SET runtime = 0", ())],
            "STORE_INVARIANT_INTEGRITY",
        ),
    }
    edits, code = statements[case]
    target = damaged(x, edits)
    if code is None:
        assert verify_copy(x, target)["removals"] == 1
        return
    with pytest.raises(JobStoreError, match=code):
        verify_copy(x, target)


# --- bounded passes, symlinks, storage failure, yielding and root races ----------


def test_bounded_partial_deletion_keeps_each_member_state(setup):
    x = setup
    if x is None:
        return
    captured(x, (1, 1, 1))
    col.retire_generation(x.publisher, x.generation, operation=op())
    first = collect(x, max_members=1)
    assert [d[2] for d in first.decided] == [1] and len(first.removed) == 1
    states = sorted(
        s_ for _c, s_, _p in col.availability(x.workspace, x.job, x.generation)
    )
    assert states == ["REMOVED_OBSERVED", "RETIRED_UNPROTECTED", "RETIRED_UNPROTECTED"]
    second = collect(x, max_members=2)
    assert [d[2] for d in second.decided] == [2]
    assert probe.files(x.workspace.root) == []
    verify_store(x.workspace)


def test_a_symlink_at_a_claimed_name_is_refused_and_kept(setup):
    x = setup
    if x is None:
        return
    admission = x.runtime.grant(x.job, probe.unit(x, "CAPTURE"))
    session = s12.capture(x.workspace, x.publisher, x.generation, x.binding)
    session.admission = admission
    identity = w.new_identity("chk")
    session._claim(x.workspace, identity, 100)
    link = os.path.join(x.workspace.root, "staging", identity + k.STAGED)
    os.symlink("/etc/hostname", link)
    probe.close_owner(session.owner, 0)
    s.record_attempt(x.publisher, session.attempt, session.owner, operation=op())
    x.runtime.release(admission)
    report = collect(x)
    assert report.refused == ((identity, "COLLECTION_OBJECT"),)
    assert os.path.islink(link) and not report.decided
    os.unlink(link)


def test_storage_full_while_recording_removal_is_reconciled(setup, monkeypatch):
    x = setup
    if x is None:
        return
    captured(x, (1,))
    col.retire_generation(x.publisher, x.generation, operation=op())
    real = col._record_removals
    monkeypatch.setattr(
        col,
        "_record_removals",
        lambda *args: (_ for _ in ()).throw(JobStoreError("STORE_FULL")),
    )
    with pytest.raises(JobStoreError, match="STORE_FULL"):
        collect(x)
    assert probe.rows(x.workspace, "SELECT count(*) FROM removal") == [(0,)]
    monkeypatch.setattr(col, "_record_removals", real)
    assert [b for _c, b in collect(x).resumed] == ["ABSENT"]


def test_collection_yields_to_pending_control(setup):
    x = setup
    if x is None:
        return
    captured(x, (1,))
    col.retire_generation(x.publisher, x.generation, operation=op())
    workspace = w.open_workspace(
        x.workspace.root, expected_identity=x.workspace.identity
    )
    try:
        report = col.collect(workspace, x.runtime.owner, yielding=lambda: True)
    finally:
        workspace.close()
    assert report.yielded and not report.decided
    assert collect(x).decided


def test_concurrent_last_root_release_never_crosses_a_root(setup):
    x = setup
    if x is None:
        return
    captured(x, (1, 1))
    held = c.retain_checkpoint(
        x.publisher, x.generation, scope={"why": "race"}, operation=op()
    )
    col.retire_generation(x.publisher, x.generation, operation=op())
    seen = []
    done = threading.Event()

    def collector():
        while not done.is_set():
            report = x.runtime.collect()
            released = probe_rows(x, "SELECT count(*) FROM retention_release")
            seen.append((bool(report.decided), released))
            if report.decided:
                return

    thread = threading.Thread(target=collector)
    thread.start()
    time.sleep(0.2)
    assert held.retention is not None
    c.release_retention(x.publisher, held.retention, operation=op())
    thread.join(60)
    done.set()
    # Every decision observed the release already committed.
    assert seen and seen[-1][0]
    assert all(released == 1 for decided, released in seen if decided)
    verify_store(x.workspace)


def probe_rows(x, sql):
    workspace = w.open_workspace(
        x.workspace.root, expected_identity=x.workspace.identity
    )
    try:
        return workspace.use().execute(sql).fetchone()[0]
    finally:
        workspace.close()


# --- pure models and the independent checker over a real core history -------------


def test_pure_transition_models_hold_their_laws():
    import _pietto_phase68_slice17_check as check

    assert check.admission_model() > 200
    assert check.admission_model(envelope=1, units=2, durable=2, allowance=2) > 20
    assert check.lifetime_model(readers=2) > 30
    assert check.lifetime_model(readers=3) > check.lifetime_model(readers=2)


def backup(x, name):
    target = x.root / (name + ".sqlite")
    with sqlite3.connect(target) as out:
        x.workspace.use().backup(out)
    out.close()
    return target


def units_of(runtime_, handles, data):
    vectors = {r[0]: json.loads(r[4]) for r in data["admission"]}
    units = {}
    for handle in handles:
        state = runtime_.query(handle)
        units[handle] = {
            "events": [list(e) for e in state.events],
            "vector": vectors.get(
                handle,
                dict.fromkeys(
                    ("connections", "workers", "memory", "durable", "operations"), 0
                ),
            ),
            "job": state.job,
            "generation": state.generation,
            "durable_cancel": state.durable_cancel,
            "settlement": state.settlement,
        }
    return units


def test_independent_checker_recomputes_a_core_history_and_names_each_damage(
    setup, monkeypatch
):
    import _pietto_phase68_slice17_check as check

    x = setup
    if x is None:
        return
    x.publisher.close()
    opened = x.runtime
    handles = []
    jobs = {}

    def new_job(name):
        job_, publisher, _binding, _record, generation = probe.another_job(
            x.workspace, x.template
        )
        publisher.close()
        jobs[name] = (job_, generation)
        return job_, generation

    a_job, a_generation = x.job, x.generation
    b_job, b_generation = new_job("B")
    gate = probe.Gate()
    probe.PLANS[a_generation] = probe.Plan(1, 1)
    probe.PLANS[b_generation] = probe.Plan(1, gate, 1)
    handles.append(opened.submit(probe.unit(x, "CAPTURE", b_generation, b_job)))
    assert gate.entered.wait(60)
    handles.append(opened.submit(probe.unit(x, "CAPTURE")))
    assert opened.wait(handles[-1], 60).terminal == "COMPLETED"
    gate.released.set()
    assert opened.wait(handles[0], 60).terminal == "COMPLETED"
    snapshot = c.checkpoint_snapshot(x.workspace, a_job, a_generation)
    replay = opened.submit(
        probe.unit(
            x,
            "REPLAY",
            checkpoint=snapshot.checkpoint,
            extent=snapshot.frontier,
            rows=1,
            batch_rows=1,
        )
    )
    handles.append(replay)
    acked = set()
    while opened.query(replay).terminal is None:
        item = opened.take(replay, 1)
        if item is None or item.identity in acked:
            time.sleep(0.01)
            continue
        acked.add(item.identity)
        opened.ack(replay, item)
    assert opened.wait(replay, 60).terminal == "COMPLETED"
    closing = s.job_record(x.workspace, a_job).attempts[0].identity
    handles.append(
        opened.submit(
            probe.unit(x, "PUBLISH", checkpoint=snapshot.checkpoint, closing=closing)
        )
    )
    assert opened.wait(handles[-1], 60).terminal == "COMPLETED"
    c_job, c_generation = new_job("C")
    cancel_gate = probe.Gate()
    probe.PLANS[c_generation] = probe.Plan(1, cancel_gate)
    handles.append(opened.submit(probe.unit(x, "CAPTURE", c_generation, c_job)))
    assert cancel_gate.entered.wait(60)
    opened.cancel(handles[-1])
    assert opened.wait(handles[-1], 60).durable_cancel == "COMMITTED"
    # A killed producer: an attempt left open, then interrupted by a takeover.
    d_job, d_generation = new_job("D")
    publisher = s.claim_publisher(x.workspace, d_job, operation=op())
    _binding = s.bind_record(
        x.workspace,
        d_job,
        x.template,
        probe.rows(
            x.workspace,
            "SELECT binding FROM generation WHERE identity = ?",
            (d_generation,),
        )[0][0],
    )
    killed = s.open_attempt(publisher, d_generation, _binding, operation=op()).identity
    publisher.close()
    publisher = s.claim_publisher(x.workspace, d_job, operation=op())
    s.interrupt_attempt(publisher, killed, operation=op())
    publisher.close()
    # Reader before the decision, then retirement and collection of B.
    b_snapshot = c.checkpoint_snapshot(x.workspace, b_job, b_generation)
    held = reader(x, b_snapshot)
    reads = [(b_generation, time.monotonic_ns(), "READ")]
    held.close()
    publisher = s.claim_publisher(x.workspace, b_job, operation=op())
    col.retire_generation(publisher, b_generation, operation=op())
    publisher.close()
    assert opened.collect().decided
    decisions = [(b_generation, time.monotonic_ns())]
    # A cut: decided and unlinked, never observed by that incarnation.
    e_job, e_generation = new_job("E")
    probe.PLANS[e_generation] = probe.Plan(1)
    handles.append(opened.submit(probe.unit(x, "CAPTURE", e_generation, e_job)))
    assert opened.wait(handles[-1], 60).terminal == "COMPLETED"
    publisher = s.claim_publisher(x.workspace, e_job, operation=op())
    col.retire_generation(publisher, e_generation, operation=op())
    publisher.close()
    real_sync = k._sync
    monkeypatch.setattr(k, "_sync", lambda fd: (_ for _ in ()).throw(OSError(5, "EIO")))
    with pytest.raises(OSError):
        opened.collect()
    monkeypatch.setattr(k, "_sync", real_sync)
    cut_epoch = opened.owner.epoch
    cut_chunks = [
        r[0]
        for r in probe.rows(
            x.workspace,
            "SELECT chunk FROM tombstone WHERE generation = ?",
            (e_generation,),
        )
    ]
    first_units = units_of(opened, handles, check.load(backup(x, "interim")))
    opened.close()
    second = probe.open_runtime(x, workers=3, connections=3)
    x.runtime = second
    assert second.collect().resumed
    # A decided subject whose unlink failed: still present, not removed.
    f_job, f_generation = new_job("F")
    probe.PLANS[f_generation] = probe.Plan(1)
    f_handle = second.submit(probe.unit(x, "CAPTURE", f_generation, f_job))
    assert second.wait(f_handle, 60).terminal == "COMPLETED"
    publisher = s.claim_publisher(x.workspace, f_job, operation=op())
    col.retire_generation(publisher, f_generation, operation=op())
    publisher.close()
    real_unlink = k._unlink
    monkeypatch.setattr(
        k, "_unlink", lambda name, fd: (_ for _ in ()).throw(OSError(5, "EIO"))
    )
    with pytest.raises(OSError):
        second.collect()
    monkeypatch.setattr(k, "_unlink", real_unlink)
    data = check.load(backup(x, "final"))
    units = {**first_units, **units_of(second, [f_handle], data)}
    for handle in units:
        units[handle]["vector"] = {
            r[0]: json.loads(r[4]) for r in data["admission"]
        }.get(handle, units[handle]["vector"])
    evidence = {
        "data": data,
        "units": units,
        "policy": {
            "connections": 3,
            "workers": 3,
            "memory": 512 * 1024 * 1024,
            "durable": 64 * 1024 * 1024,
            "operations": 65536,
        },
        "files": check.inventory(x.workspace.root),
        "killed": [killed],
        "cut": ("K3_unlinked_before_sync", cut_epoch, cut_chunks),
        "acked": acked,
        "reads": reads,
        "decisions": decisions,
    }
    facts = check.check_all(evidence)
    assert facts["published"] == 1 and facts["retired"] == 3 and facts["removals"] >= 2
    rejected = {kind: check.rejects(kind, evidence) for kind in check.DAMAGES}
    assert len(rejected) == 13 and len(set(rejected.values())) == 12
    verify_store(x.workspace)


def test_protected_generations_never_starve_a_collectable_one(setup):
    x = setup
    if x is None:
        return
    for _ in range(4):
        captured(x, (1,), probe.generation_of(x.publisher, x.record, x.binding))
    target = probe.generation_of(x.publisher, x.record, x.binding)
    captured(x, (1,), target)
    col.retire_generation(x.publisher, target, operation=op())
    report = collect(x, max_generations=1)
    assert [d[1] for d in report.decided] == [target]
