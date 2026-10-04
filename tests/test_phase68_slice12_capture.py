"""S12 capture protocol: lineage, fence, holes, idempotency, retention, damage.

Storage mechanics here use the Arrow-free storage step (synthetic frames with
producer-assigned positions); real checked Arrow captures and VERIFIED reads run
in the execution-profile probe and the native bridge.
"""

import json
import os
import sqlite3

import pytest

import _pietto_phase68_slice12_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from pietto._project import project_job_capture as c
from pietto._project import project_job_chunks as k
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

op = probe.op


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(
        tmp_path_factory.mktemp("s12-capture") / "small", entry="bundle"
    )


@pytest.fixture
def setup(tmp_path, built):
    if not qualified(tmp_path):
        yield None
        return
    template, _ = built
    workspace, job, publisher, binding, record, generation = probe.store(
        tmp_path / "workspace", template, (1,)
    )
    yield workspace, job, publisher, binding, record, generation
    publisher.close()
    if not workspace._closed:
        workspace.close()


def finish(publisher, session):
    """Close the never-connected owner and record its exact closed layers."""
    session.owner.close()
    return s.record_attempt(publisher, session.attempt, session.owner, operation=op())


def test_required_hole_history_and_immutable_checkpoints(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    first, second, third = (probe.stage_frame(session, 2) for _ in range(3))
    assert [(x.start, x.stop) for x in (first, second, third)] == [
        (0, 2),
        (2, 4),
        (4, 6),
    ]
    one = session.publish(first, operation=op())
    three = session.publish(third, operation=op())
    assert (three.get("ordinal"), three.get("frontier"), three.get("members")) == (
        2,
        2,
        2,
    )
    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    assert snapshot.committed == ((0, 2), (4, 6))
    assert (snapshot.frontier, snapshot.holes) == (2, ((2, 4),))
    assert snapshot.integrity == "RECORDED" and snapshot.observed_end is None
    two = session.publish(second, operation=op())
    assert (two.get("ordinal"), two.get("frontier"), two.get("members")) == (3, 6, 3)
    for result, frontier, committed in (
        (one, 2, ((0, 2),)),
        (three, 2, ((0, 2), (4, 6))),
        (two, 6, ((0, 2), (2, 4), (4, 6))),
    ):
        old = c.checkpoint_snapshot(
            workspace, job, generation, checkpoint=result.get("checkpoint")
        )
        assert (old.frontier, old.committed) == (frontier, committed)
    session.owner.close()
    session.end(operation=op())
    final = c.checkpoint_snapshot(workspace, job, generation)
    assert (final.observed_end, final.holes, final.ordinal) == (6, (), 3)
    assert dict(final.layers) == {
        "attempt_terminal": None,
        "source": "UNKNOWN",
        "transaction": "UNKNOWN",
        "delivery": "UNKNOWN",
        "cancel": "UNKNOWN",
        "cleanup": "UNKNOWN",
        "remote_source_use_end": "UNKNOWN",
        "publication": "NOT_IMPLEMENTED_BY_S12",
        "consumer_ack": "NOT_IMPLEMENTED_BY_S12",
    }
    assert final.session_source == "EARLY_CLOSE"
    summary = verify_store(workspace)
    assert (summary["captures"], summary["chunks"], summary["checkpoints"]) == (1, 3, 3)
    files = c.classify_files(workspace)
    assert len(files["referenced"]) == 3
    assert files["orphans"] == files["staging"] == files["missing"] == ()


def test_schema_only_chunk_stands_alone_and_extents_never_overlap(setup, built):
    if setup is None:
        return
    workspace, job, publisher, binding, record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    empty = probe.stage_frame(session, 0, terminal="EOF")
    assert (empty.start, empty.stop, empty.batches) == (0, 0, 0)
    result = session.publish(empty, operation=op())
    assert (result.get("frontier"), result.get("members")) == (0, 1)
    late = probe.stage_frame(session, 2)
    with pytest.raises(JobStoreError, match="CAPTURE_OVERLAP"):
        session.publish(late, operation=op())
    # A second generation: data first, then a crafted overlapping extent.
    finish(publisher, session)
    other = s.register_generation(
        publisher,
        record,
        binding,
        route="postgres_rows",
        isolation="stable",
        operation=op(),
    ).get("generation")
    second = probe.capture(workspace, publisher, other, binding)
    a, b = probe.stage_frame(second, 2), probe.stage_frame(second, 2)
    second.publish(a, operation=op())
    before = c.checkpoint_snapshot(workspace, job, other)
    crafted = c.StagedChunk(
        second, w.new_identity("chk"), 1, 3, 1, b.name, b.size, b.digest,
        b.descriptor, b.device, b.inode, b.changed,
    )  # fmt: skip
    second._staged[crafted.identity] = crafted
    with pytest.raises(JobStoreError, match="CAPTURE_OVERLAP"):
        second.publish(crafted, operation=op())
    with pytest.raises(JobStoreError, match="CAPTURE_STAGED_FOREIGN"):
        second.publish(a, operation=op())
    with pytest.raises(JobStoreError, match="CAPTURE_STAGED_FOREIGN"):
        session.publish(b, operation=op())
    assert c.checkpoint_snapshot(workspace, job, other) == before
    second.owner.close()
    second.end(operation=op())
    del second._staged[crafted.identity]
    beyond = c.StagedChunk(
        second, w.new_identity("chk"), 4, 6, 1, b.name, b.size, b.digest,
        b.descriptor, b.device, b.inode, b.changed,
    )  # fmt: skip
    second._staged[beyond.identity] = beyond
    with pytest.raises(JobStoreError, match="CAPTURE_EXTENT"):
        second.publish(beyond, operation=op())
    del second._staged[beyond.identity]
    assert second.publish(b, operation=op()).get("frontier") == 4
    assert verify_store(workspace)["chunks"] == 3


def test_one_original_capture_attempt_per_generation(setup, built):
    if setup is None:
        return
    workspace, job, publisher, binding, record, generation = setup
    template, _ = built
    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    owner = probe.pg_owner(binding)
    wrong = probe.pg_owner(
        s.bind_record(workspace, job, template, record)
    )  # same vector, different live binding
    with pytest.raises(JobStoreError, match="ATTEMPT_OWNER"):
        c.begin_capture(publisher, attempt, wrong, operation=op())
    closed = probe.pg_owner(binding)
    closed.close()
    with pytest.raises(JobStoreError, match="CAPTURE_OWNER_STATE"):
        c.begin_capture(publisher, attempt, closed, operation=op())
    impostor = s.Publisher(
        workspace, job, publisher.epoch, publisher.instance, publisher.revision, -1
    )
    fake = s.AttemptHandle(
        impostor, attempt.identity, generation, 1, "postgres_rows", "stable", binding
    )
    with pytest.raises(JobStoreError, match="ATTEMPT_PUBLISHER"):
        c.begin_capture(publisher, fake, owner, operation=op())
    session = c.begin_capture(publisher, attempt, owner, operation=op())
    probe.stage_frame(session, 2)
    finish(publisher, session)
    staged = session.staged[0]
    with pytest.raises(JobStoreError, match="ATTEMPT_TERMINAL"):
        session.publish(staged, operation=op())
    later = s.open_attempt(publisher, generation, binding, operation=op())
    later_owner = probe.pg_owner(binding)
    with pytest.raises(JobStoreError, match="CAPTURE_EXISTS"):
        c.begin_capture(publisher, later, later_owner, operation=op())
    later_owner.close()
    s.record_attempt(publisher, later, later_owner, operation=op())
    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    assert (snapshot.attempt, snapshot.members) == (attempt.identity, ())
    assert dict(snapshot.layers)["attempt_terminal"] == "OUTCOME"
    assert c.classify_files(workspace)["orphans"] == (staged.name,)
    verify_store(workspace)


def test_cancellation_and_publisher_change_refuse_new_progress(setup, tmp_path):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    first, paused = probe.stage_frame(session, 2), probe.stage_frame(session, 2)
    session.publish(first, operation=op())
    # Ownership changes while `paused` is durable but unpublished.
    session.owner.close()
    os.close(publisher._fd)
    other_handle = w.open_workspace(
        workspace.root, expected_identity=workspace.identity
    )
    try:
        other = s.claim_publisher(other_handle, job, operation=op())
        with pytest.raises(JobStoreError, match="PUBLISHER_STALE"):
            session.publish(paused, operation=op())
        with pytest.raises(JobStoreError, match="PUBLISHER_STALE"):
            session.end(operation=op())
        snapshot = c.checkpoint_snapshot(other_handle, job, generation)
        assert (snapshot.frontier, len(snapshot.members)) == (2, 1)
        assert c.classify_files(other_handle)["orphans"] == (paused.name,)
        s.interrupt_attempt(other, session.attempt.identity, operation=op())
        assert (
            dict(c.checkpoint_snapshot(other_handle, job, generation).layers)["source"]
            == "UNKNOWN"
        )
        s.cancel_job(other, operation=op())
        with pytest.raises(JobStoreError, match="JOB_STATE"):
            s.register_generation(
                other,
                s.job_record(other_handle, job).bindings[0],
                binding,
                route="postgres_rows",
                isolation="stable",
                operation=op(),
            )
        # Retention and release remain truthful control operations.
        held = c.retain_checkpoint(
            other, generation, scope={"purpose": "audit"}, operation=op()
        )
        c.release_retention(other, str(held.retention), operation=op())
        verify_store(other_handle)
        other.close()
    finally:
        publisher._closed = True
        other_handle.close()


def test_cancelled_job_refuses_publication_before_metadata(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    staged = probe.stage_frame(session, 2)
    s.cancel_job(publisher, operation=op())
    with pytest.raises(JobStoreError, match="JOB_STATE"):
        session.publish(staged, operation=op())
    assert c.checkpoint_snapshot(workspace, job, generation).members == ()
    session.owner.close()
    assert session.end(operation=op()).get("observed") == 2
    assert c.checkpoint_snapshot(workspace, job, generation).holes == ((0, 2),)


def test_final_object_identity_is_rechecked_at_publication(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    replaced, removed = probe.stage_frame(session, 2), probe.stage_frame(session, 2)
    root = os.path.join(workspace.root, "chunks")
    data = open(os.path.join(root, replaced.name), "rb").read()
    os.unlink(os.path.join(root, replaced.name))
    with open(os.path.join(root, replaced.name), "xb") as stream:
        stream.write(data)
    os.chmod(os.path.join(root, replaced.name), 0o600)
    with pytest.raises(JobStoreError, match="CHUNK_OBJECT"):
        session.publish(replaced, operation=op())
    os.unlink(os.path.join(root, removed.name))
    with pytest.raises(JobStoreError, match="CHUNK_MISSING"):
        session.publish(removed, operation=op())
    assert c.checkpoint_snapshot(workspace, job, generation).members == ()
    assert verify_store(workspace)["chunks"] == 0


@pytest.mark.parametrize("injection", ["before_commit", "after_commit"])
def test_ambiguous_commit_has_zero_or_one_queryable_effect(
    setup, monkeypatch, injection
):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    staged = probe.stage_frame(session, 2)
    real = w.commit

    def commit(connection):
        if injection == "after_commit":
            real(connection)
        raise sqlite3.OperationalError("injected lost reply")

    monkeypatch.setattr(w, "commit", commit)
    operation = op()
    with pytest.raises(JobStoreError, match="STORE_COMMIT_UNKNOWN"):
        session.publish(staged, operation=operation)
    monkeypatch.undo()
    with pytest.raises(JobStoreError, match="WORKSPACE_RETIRED"):
        session.publish(staged, operation=operation)
    fresh = w.open_workspace(workspace.root, expected_identity=workspace.identity)
    try:
        found = s.query_operation(fresh, operation)
        snapshot = c.checkpoint_snapshot(fresh, job, generation)
        if injection == "before_commit":
            assert found is None and snapshot.members == ()
            assert c.classify_files(fresh)["orphans"] == (staged.name,)
        else:
            assert found is not None and found.observation == "QUERIED"
            assert (
                found.kind == "publish_chunk" and found.get("chunk") == staged.identity
            )
            assert [m.chunk for m in snapshot.members] == [staged.identity]
            assert snapshot.checkpoint == found.get("checkpoint")
        verify_store(fresh)
    finally:
        fresh.close()


def test_operation_identity_replays_and_conflicts_exactly(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    first, second = probe.stage_frame(session, 2), probe.stage_frame(session, 2)
    operation = op()
    session.publish(first, operation=operation)
    revision = publisher.revision
    with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
        session.publish(second, operation=operation)
    assert publisher.revision == revision
    assert [
        m.chunk for m in c.checkpoint_snapshot(workspace, job, generation).members
    ] == [first.identity]
    retain = op()
    held = c.retain_checkpoint(
        publisher, generation, scope={"purpose": "read"}, operation=retain
    )
    again = c.retain_checkpoint(
        publisher, generation, scope={"purpose": "read"}, operation=retain
    )
    assert again.retention == held.retention and again.members == held.members
    with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
        c.retain_checkpoint(
            publisher, generation, scope={"purpose": "other"}, operation=retain
        )
    finish(publisher, session)
    replay = op()
    attempt = s.open_attempt(
        publisher, _other_generation(publisher, binding), binding, operation=op()
    )
    c.begin_capture(publisher, attempt, probe.pg_owner(binding), operation=replay)
    with pytest.raises(JobStoreError, match="CAPTURE_REPLAYED"):
        c.begin_capture(publisher, attempt, probe.pg_owner(binding), operation=replay)


def _other_generation(publisher, binding):
    record = s.job_record(publisher.workspace, publisher.job).bindings[0]
    return s.register_generation(
        publisher,
        record,
        binding,
        route="postgres_rows",
        isolation="stable",
        operation=op(),
    ).get("generation")


def test_retention_references_protected_set_and_release(setup, tmp_path, built):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    with pytest.raises(JobStoreError, match="CHECKPOINT_UNKNOWN"):
        c.retain_checkpoint(publisher, generation, scope={"p": "x"}, operation=op())
    a = probe.stage_frame(session, 2)
    session.publish(a, operation=op())
    held = c.retain_checkpoint(
        publisher, generation, scope={"purpose": "read", "minimum": 1}, operation=op()
    )
    assert held.retention is not None and [m.chunk for m in held.members] == [
        a.identity
    ]
    b = probe.stage_frame(session, 2)
    session.publish(b, operation=op())
    assert c.protected_chunks(workspace, job) == {a.identity, b.identity}
    for bad in ({}, {"p": 1.5}, {1: "x"}, "read", {"p": "x" * 5000}):
        with pytest.raises(JobStoreError, match="RETENTION_SCOPE"):
            c.retain_checkpoint(publisher, generation, scope=bad, operation=op())  # type: ignore[arg-type]
    c.release_retention(publisher, str(held.retention), operation=op())
    with pytest.raises(JobStoreError, match="RETENTION_RELEASED"):
        c.release_retention(publisher, str(held.retention), operation=op())
    with pytest.raises(JobStoreError, match="RETENTION_UNKNOWN"):
        c.release_retention(publisher, w.new_identity("ret"), operation=op())
    # Latest members remain protected; nothing was deleted by any release.
    assert c.protected_chunks(workspace, job) == {a.identity, b.identity}
    assert len(c.classify_files(workspace)["referenced"]) == 2
    old = c.retain_checkpoint(
        publisher,
        generation,
        scope={"purpose": "crash"},
        operation=op(),
        checkpoint=held.checkpoint,
    )
    # A foreign job cannot release it, a later publisher of this job can.
    template, _ = built
    foreign_job = s.register_job(workspace, template, operation=op()).get("job")
    foreign = s.claim_publisher(workspace, foreign_job, operation=op())
    with pytest.raises(JobStoreError, match="RETENTION_UNKNOWN"):
        c.release_retention(foreign, str(old.retention), operation=op())
    foreign.close()
    publisher.close()
    later = s.claim_publisher(workspace, job, operation=op())
    try:
        assert c.protected_chunks(workspace, job) == {a.identity, b.identity}
        c.release_retention(later, str(old.retention), operation=op())
        verify_store(workspace)
    finally:
        later.close()


def test_recorded_metadata_damage_refuses_without_erasing_history(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    for _ in range(2):
        session.publish(probe.stage_frame(session, 2), operation=op())
    workspace.close()
    database = os.path.join(workspace.root, "store.sqlite")
    raw = sqlite3.connect(database, isolation_level=None)
    try:
        raw.execute("PRAGMA foreign_keys = OFF")
        raw.execute(
            "UPDATE checkpoint SET frontier = 4 WHERE identity = ?",
            (_first_checkpoint(raw, generation),),
        )
    finally:
        raw.close()
    reopened = w.open_workspace(workspace.root, expected_identity=workspace.identity)
    try:
        with pytest.raises(JobStoreError, match="CHECKPOINT_MEMBERS"):
            c.checkpoint_snapshot(
                reopened,
                job,
                generation,
                checkpoint=_first_checkpoint(reopened.use(), generation),
            )
        assert c.checkpoint_snapshot(reopened, job, generation).frontier == 4
        with pytest.raises(JobStoreError, match="STORE_INVARIANT_CHECKPOINT_HISTORY"):
            verify_store(reopened)
        assert len(s.job_record(reopened, job).operations) >= 6
    finally:
        reopened.close()


def _first_checkpoint(connection, generation):
    return connection.execute(
        "SELECT identity FROM checkpoint WHERE generation = ? AND ordinal = 1",
        (generation,),
    ).fetchone()[0]


@pytest.mark.parametrize(
    "damage,category",
    [
        ("descriptor", "CHUNK_HISTORY"),
        ("member", "CHECKPOINT_HISTORY"),
        ("epoch", "CHUNK_HISTORY"),
        ("end", "END_HISTORY"),
        ("retention", "RETENTION_HISTORY"),
    ],
)
def test_independent_history_replay_rejects_row_damage(setup, damage, category):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    a, b = probe.stage_frame(session, 2), probe.stage_frame(session, 2)
    session.publish(a, operation=op())
    session.publish(b, operation=op())
    session.owner.close()
    session.end(operation=op())
    held = c.retain_checkpoint(publisher, generation, scope={"p": "x"}, operation=op())
    verify_store(workspace)
    connection = workspace.use()
    connection.execute("PRAGMA foreign_keys = OFF")
    if damage == "descriptor":
        descriptor = json.loads(b.descriptor)
        descriptor["start"] = 3
        connection.execute(
            "UPDATE chunk SET descriptor = ? WHERE identity = ?",
            (k.canonical(descriptor), b.identity),
        )
    elif damage == "member":
        connection.execute(
            "DELETE FROM checkpoint_member WHERE chunk = ? AND checkpoint = ?",
            (a.identity, held.checkpoint),
        )
    elif damage == "epoch":
        connection.execute(
            "UPDATE chunk SET publisher_epoch = 9 WHERE identity = ?", (a.identity,)
        )
    elif damage == "end":
        connection.execute("UPDATE capture_end SET observed = 3")
    else:
        connection.execute(
            "UPDATE retention SET checkpoint = ? WHERE identity = ?",
            (_first_checkpoint(connection, generation), held.retention),
        )
    connection.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(JobStoreError, match="STORE_INVARIANT_" + category):
        verify_store(workspace)


def test_data_admission_keeps_the_control_reserve(tmp_path, built):
    if not qualified(tmp_path):
        return
    template, _ = built
    workspace = w.create_workspace(
        str(tmp_path / "small"), budget_bytes=w.MIN_BUDGET, format=w.FORMAT_V2
    )
    try:
        job = s.register_job(workspace, template, operation=op()).get("job")
        publisher = s.claim_publisher(workspace, job, operation=op())
        from pietto._project.project_execution_template import bind_values

        binding = bind_values(template, ((template.slots[0], 1),))
        record = s.register_binding(publisher, binding, operation=op()).get("binding")
        generation = s.register_generation(
            publisher,
            record,
            binding,
            route="postgres_rows",
            isolation="stable",
            operation=op(),
        ).get("generation")
        session = probe.capture(workspace, publisher, generation, binding)
        session.publish(probe.stage_frame(session, 2), operation=op())
        room = w.MIN_BUDGET - w.accounted_bytes(workspace) - w.CONTROL_RESERVE
        with pytest.raises(JobStoreError, match="WORKSPACE_BUDGET"):
            probe.stage_frame(session, 2, size=room // 3 + 1)
        assert c.classify_files(workspace)["staging"] == ()
        session.owner.close()
        assert session.end(operation=op()).observation == "COMMITTED_THIS_CALL"
        held = c.retain_checkpoint(
            publisher, generation, scope={"p": "x"}, operation=op()
        )
        c.release_retention(publisher, str(held.retention), operation=op())
        publisher.close()
    finally:
        workspace.close()


def test_handles_and_sessions_are_process_and_owner_bound(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, _record, generation = setup
    session = probe.capture(workspace, publisher, generation, binding)
    assert repr(session) == f"CaptureSession(generation={generation!r})"
    with pytest.raises(JobStoreError, match="CAPTURE_OWNER_OPEN"):
        session.end(operation=op())
    # Early local close is a real owner terminal, not EOF: no schema chunk.
    session.owner.close()
    assert session.stage() is None and session.terminal == "EARLY_CLOSE"
    assert session.stage() is None
    staged = probe.stage_frame(session, 2)
    assert "digest" not in repr(staged) and "descriptor" not in repr(staged)
    session._pid = -1
    for call in (session.stage, lambda: session.publish(staged, operation=op())):
        with pytest.raises(JobStoreError, match="CAPTURE_FOREIGN_PROCESS"):
            call()
    session._pid = os.getpid()
    session.end(operation=op())
    for call in (session.stage, lambda: session.end(operation=op())):
        with pytest.raises(JobStoreError, match="CAPTURE_ENDED"):
            call()
    # After the end, an already staged in-extent chunk may still close a hole.
    assert session.publish(staged, operation=op()).get("frontier") == 2
    s.record_attempt(publisher, session.attempt, session.owner, operation=op())
    layers = dict(c.checkpoint_snapshot(workspace, job, generation).layers)
    assert (layers["attempt_terminal"], layers["source"]) == ("OUTCOME", "EARLY_CLOSE")
    assert layers["transaction"] == "NOT_STARTED" and layers["cancel"] == (
        False,
        False,
        False,
    )
