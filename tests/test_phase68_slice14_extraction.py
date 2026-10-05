"""S14 R2 storage protocol: v4, initial basis, barrier, continuation and R1 handoff.

No database or Arrow: owners are real compiled refined owners that never connect,
with the labelled SYNTHETIC_OPEN_OWNER, ARROW_FREE_MEMBER_CHECK and
ARROW_FREE_PAGE_STEP replacements (see the probe). The pure segment model is
exhaustive; the real reconciliation step, fences, barrier, publication, end and
the independent verifier run for real. Checked Arrow pages, native requalification
and source-offline R1 are execution-profile evidence only.
"""

import json
import os
import pickle
import sqlite3
from itertools import product

import pytest

import _pietto_phase68_slice13_probe as s13
import _pietto_phase68_slice14_probe as probe
from _pietto_phase68_slice11_probe import qualified
from pietto._project import project_job_capture as c
from pietto._project import project_job_extraction as x
from pietto._project import project_job_replay as r
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

op = probe.op


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return probe.refined_template(tmp_path_factory.mktemp("s14") / "bound")


@pytest.fixture
def setup(tmp_path, built, monkeypatch):
    if not qualified(tmp_path):
        yield None
        return
    probe.synthetic(monkeypatch)
    s13.arrow_free(monkeypatch)
    template, compiled, values = built
    workspace, job, publisher, binding, record, generation = probe.store(
        tmp_path / "workspace", template, values
    )
    yield workspace, job, publisher, binding, generation, compiled, values
    for item in (publisher, workspace):
        if not item._closed:
            item.close()


def members(workspace, job, generation, checkpoint=None):
    snapshot = c.checkpoint_snapshot(workspace, job, generation, checkpoint=checkpoint)
    return snapshot, [(m.start, m.stop, m.attempt) for m in snapshot.members]


def test_v4_is_an_explicit_closed_capability_set(tmp_path):
    if not qualified(tmp_path):
        return
    v3, v4 = w.expected_schema(w.FORMAT_V3), w.expected_schema(w.FORMAT_V4)
    added = {row[1] for row in v4} - {row[1] for row in v3}
    assert {"extraction", "continuation", "reconciliation", "continuation_end"} <= added
    assert not {row[1] for row in v3} - {row[1] for row in v4}
    workspace = w.create_workspace(str(tmp_path / "v4"), format=w.FORMAT_V4)
    try:
        assert [
            w.supports(workspace, f) for f in ("result-chunks", "saved-replay")
        ] == [
            True,
            True,
        ]
        assert w.supports(workspace, "extraction-resume")
        envelope = json.loads((tmp_path / "v4" / "workspace.json").read_text())
        assert envelope["features"] == [
            "result-chunks",
            "saved-replay",
            "extraction-resume",
        ]
        assert workspace.use().execute("PRAGMA user_version").fetchone() == (4,)
    finally:
        workspace.close()
    reopened = w.open_workspace(
        str(tmp_path / "v4"), expected_identity=workspace.identity
    )
    reopened.close()
    old = w.create_workspace(str(tmp_path / "v3"), format=w.FORMAT_V3)
    try:
        assert not w.supports(old, "extraction-resume")
        with pytest.raises(JobStoreError, match="WORKSPACE_EXTRACTION_FORMAT"):
            x.extraction_state(old, "job-" + "0" * 32, "gen-" + "0" * 32)
    finally:
        old.close()


def test_segments_partition_every_small_layout():
    """Exhaustive model: member layouts over [0, 6) and every page [a, b)."""
    from types import SimpleNamespace

    checked = 0
    for cuts in product((False, True), repeat=5):
        bounds = [0] + [i + 1 for i, cut in enumerate(cuts) if cut] + [6]
        blocks = list(zip(bounds, bounds[1:]))
        for chosen in product((False, True), repeat=len(blocks)):
            saved = [
                SimpleNamespace(start=a, stop=b)
                for (a, b), keep in zip(blocks, chosen)
                if keep
            ]
            covered = {p for m in saved for p in range(m.start, m.stop)}
            for a in range(0, 8):
                for b in range(a + 1, 9):
                    parts = x.segments(saved, a, b)
                    assert parts[0][1] == a and parts[-1][2] == b
                    assert all(p[2] == q[1] for p, q in zip(parts, parts[1:]))
                    for kind, start, stop, index in parts:
                        assert start < stop
                        inside = set(range(start, stop)) <= covered
                        assert (kind == "old") == inside
                        if kind == "old":
                            m = saved[index]
                            assert m.start <= start and stop <= m.stop
                        else:
                            assert not set(range(start, stop)) & covered
                    checked += 1
    assert checked > 10000
    schema = [SimpleNamespace(start=0, stop=0)]
    assert x.segments(schema, 0, 3) == (("new", 0, 3, None),)


def test_initial_basis_is_registered_with_the_first_capture(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    session, _ = probe.extract(publisher, generation, binding, [2])
    record = s.job_record(workspace, job)
    begun = [o for o in record.operations if o.kind == "begin_extraction"]
    assert len(begun) == 1 and not [
        o for o in record.operations if o.kind == "begin_capture"
    ]
    row = (
        workspace.use()
        .execute("SELECT attempt, specification, qualification FROM extraction")
        .fetchone()
    )
    assert row[0] == session.attempt.identity and row[2] == probe.SYNTHETIC
    spec = json.loads(row[1])
    assert spec["version"] == "pietto.extraction-spec.v1"
    assert (spec["kind"], spec["route"], spec["isolation"]) == (
        "REFINED",
        "postgres_rows",
        "stable",
    )
    assert spec["contract"] == session.contract and spec["sources"]
    assert all(len(source) == 11 for source in spec["sources"])
    assert json.loads(spec["scheme"])["choice"] == "structural_occurrence_ascending"
    # One original capture per generation; a second begin cannot certify anything.
    with pytest.raises(JobStoreError, match="ATTEMPT_OPEN"):
        s.open_attempt(publisher, generation, binding, operation=op())
    assert verify_store(workspace)["extractions"] == 1


def test_ordinary_capture_on_v4_has_no_continuation_rights(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    session = c.begin_capture(publisher, attempt, probe.owner(binding), operation=op())
    session.publish(probe.stage_refined(session, 2), operation=op())
    fresh = probe.takeover(workspace, job, publisher)
    with pytest.raises(JobStoreError, match="EXTRACTION_UNKNOWN"):
        probe.accept(workspace, job, generation, compiled, values)
    # R1 of the ordinary saved prefix still works on v4.
    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    acceptance = s13.accept(
        workspace,
        job,
        generation,
        compiled,
        scope="committed_prefix",
        values=values,
    )
    r.register_consumer(fresh, acceptance, operation=op())
    replay = r.open_replay(fresh, acceptance, operation=op())
    extents, end = s13.drain(replay, 1)
    assert extents == [(0, 1), (1, 2)] and end.extent == snapshot.frontier == 2
    verify_store(workspace)


def test_history_b_barrier_fills_hole_under_new_identity(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    original, _ = probe.extract(publisher, generation, binding, [2, 2, 2], order=[0, 2])
    old, old_members = members(workspace, job, generation)
    assert [(a, b) for a, b, _ in old_members] == [(0, 2), (4, 6)]
    assert (old.frontier, old.holes) == (2, ((2, 4),))
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    assert (acceptance.frontier, acceptance.reach, acceptance.rows) == (2, 6, 4)
    session = x.begin_continuation(
        fresh,
        acceptance,
        attempt,
        probe.owner(acceptance.binding, batch_rows=3),
        operation=op(),
    )
    first = probe.page(session, 3)
    assert [(i.start, i.stop) for i in first] == [(2, 3)] and not session.ready
    # Candidates are durable files, never members or deliverable progress.
    with pytest.raises(JobStoreError, match="RECONCILIATION_REQUIRED"):
        session.publish(first[0], operation=op())
    assert first[0].name in c.classify_files(workspace)["orphans"]
    second = probe.page(session, 3)
    assert [(i.start, i.stop) for i in second] == [(3, 4)]
    assert session.ready and session.matched == 4
    assert probe.COMPARED[attempt.identity] == [(0, 0, 2), (1, 4, 6)]
    with pytest.raises(JobStoreError, match="RECONCILIATION_PENDING"):
        session.stage()
    session.reconcile(operation=op())
    for item in (*first, *second):
        session.publish(item, operation=op())
    suffix = probe.drive(session, [3])
    assert suffix == [] and session.observed == 9
    assert probe.finish_stream(session) == ()
    ended = session.end(operation=op())
    s.record_attempt(fresh, attempt, session.owner, operation=op())
    latest, latest_members = members(workspace, job, generation)
    assert (latest.frontier, latest.holes, latest.observed_end) == (9, (), 9)
    assert ended.get("checkpoint") == latest.checkpoint != old.checkpoint
    producers = {b: a for _s, b, a in latest_members}
    assert producers[2] == producers[6] == original.attempt.identity
    assert {producers[3], producers[4], producers[9]} == {attempt.identity}
    # The frozen predecessor is unchanged: same members, frontier and identity.
    again, again_members = members(workspace, job, generation, old.checkpoint)
    assert again_members == old_members and again.frontier == 2
    state = x.extraction_state(workspace, job, generation)
    assert state.complete_coverage and state.known == 9
    assert state.continuations[0][:6] == (attempt.identity, old.checkpoint, 2, 6, 2, 4)
    layers = dict(latest.layers)
    assert layers["source"] == "UNKNOWN" and layers["attempt_terminal"] == "INTERRUPTED"
    assert layers["continuations"][0][:2] == (attempt.identity, "OUTCOME")
    assert verify_store(workspace)["continuation_ends"] == 1


def test_late_island_mismatch_leaves_every_checkpoint_unchanged(setup, monkeypatch):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2, 2, 2], order=[0, 2])
    before = workspace.use().execute("SELECT * FROM checkpoint").fetchall()

    def mismatch_last(session, index, a, b, fresh, wires):
        if index == 1:
            raise JobStoreError("RECONCILIATION_MISMATCH")

    monkeypatch.setattr(x.ContinuationSession, "_compare", mismatch_last)
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    session = x.begin_continuation(
        fresh,
        acceptance,
        attempt,
        probe.owner(acceptance.binding, batch_rows=3),
        operation=op(),
    )
    candidate = probe.page(session, 3)
    with pytest.raises(JobStoreError, match="RECONCILIATION_MISMATCH"):
        probe.page(session, 3)
    assert not session.ready
    with pytest.raises(JobStoreError, match="RECONCILIATION_INCOMPLETE"):
        session.reconcile(operation=op())
    with pytest.raises(JobStoreError, match="CAPTURE_FAILED"):
        session.stage()
    assert workspace.use().execute("SELECT * FROM checkpoint").fetchall() == before
    files = c.classify_files(workspace)
    assert candidate[0].name in files["orphans"] and not files["missing"]
    verify_store(workspace)


def test_history_a_resume_with_new_page_size_and_no_saved_hole(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2])
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    session = x.begin_continuation(
        fresh,
        acceptance,
        attempt,
        probe.owner(acceptance.binding, batch_rows=3),
        operation=op(),
    )
    assert probe.drive(session, [3, 1]) == []
    probe.finish_stream(session)
    session.end(operation=op())
    _, found = members(workspace, job, generation)
    assert [(a, b) for a, b, _ in found] == [(0, 2), (2, 3), (3, 4)]
    verify_store(workspace)


def test_no_saved_checkpoint_opens_the_barrier_at_position_zero(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    session, _ = probe.extract(publisher, generation, binding, [2], order=[])
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    assert acceptance.checkpoint is None and (
        acceptance.frontier,
        acceptance.reach,
    ) == (0, 0)
    continuation = x.begin_continuation(
        fresh, acceptance, attempt, probe.owner(acceptance.binding), operation=op()
    )
    assert continuation.ready
    with pytest.raises(JobStoreError, match="RECONCILIATION_PENDING"):
        continuation.stage()
    probe.drive(continuation, [2, 1])
    probe.finish_stream(continuation)
    continuation.end(operation=op())
    _, found = members(workspace, job, generation)
    assert {a for _s, _e, a in found} == {attempt.identity}
    assert session._staged  # the original attempt's file was never adopted
    verify_store(workspace)


def test_premature_end_and_early_barrier_are_refused(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2, 2])
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    session = x.begin_continuation(
        fresh, acceptance, attempt, probe.owner(acceptance.binding), operation=op()
    )
    with pytest.raises(JobStoreError, match="RECONCILIATION_INCOMPLETE"):
        session.reconcile(operation=op())
    probe.page(session, 2)
    with pytest.raises(JobStoreError, match="RECONCILIATION_PREMATURE_END"):
        probe.finish_stream(session)
    with pytest.raises(JobStoreError, match="RECONCILIATION_INCOMPLETE"):
        session.end(operation=op())
    count = workspace.use().execute("SELECT count(*) FROM continuation_end")
    assert count.fetchone() == (0,)
    verify_store(workspace)


def test_known_extent_and_candidate_bounds(setup, monkeypatch):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2, 2], order=[0], eof=True)
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    assert acceptance.known == 4
    session = x.begin_continuation(
        fresh, acceptance, attempt, probe.owner(acceptance.binding), operation=op()
    )
    probe.page(session, 2)
    with pytest.raises(JobStoreError, match="RECONCILIATION_EXTENT"):
        probe.page(session, 3)
    monkeypatch.setattr(x, "MAX_CANDIDATES", 0)
    fresh2, acceptance2, attempt2 = probe.recover(
        workspace, job, generation, compiled, values, previous=fresh
    )
    limited = x.begin_continuation(
        fresh2, acceptance2, attempt2, probe.owner(acceptance2.binding), operation=op()
    )
    with pytest.raises(JobStoreError, match="RECONCILIATION_CANDIDATE_LIMIT"):
        limited.stage()


def test_recovery_authority_is_fresh_and_exact(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2, 2])
    head = c.checkpoint_snapshot(workspace, job, generation)
    first = (
        workspace.use()
        .execute("SELECT identity FROM checkpoint ORDER BY ordinal LIMIT 1")
        .fetchone()[0]
    )
    fresh = probe.takeover(workspace, job, publisher)
    for overrides, code in (
        ({"checkpoint": first}, "CONTINUATION_PREDECESSOR"),
        ({"checkpoint": None}, "CONTINUATION_PREDECESSOR"),
        ({"values": tuple(v + 1 for v in values)}, "BINDING_VECTOR"),
        ({"expected_pin": "0" * 64}, "JOB_TRUST_INPUT"),
        ({"purpose": ""}, "ACCEPTANCE_PURPOSE"),
        ({"seconds": 0}, "ACCEPTANCE_BOUND"),
    ):
        stated = overrides.pop("values", values)
        with pytest.raises(JobStoreError, match=code):
            probe.accept(workspace, job, generation, compiled, stated, **overrides)
    acceptance = probe.accept(workspace, job, generation, compiled, values)
    assert acceptance.checkpoint == head.checkpoint
    with pytest.raises(JobStoreError, match="ACCEPTANCE_COPY"):
        pickle.dumps(acceptance)
    attempt = s.open_attempt(fresh, generation, acceptance.binding, operation=op())
    changed = probe.owner(acceptance.binding)
    probe.DESCRIPTIONS[changed] = '["CHANGED_FRESH_DESCRIPTION"]'
    with pytest.raises(JobStoreError, match="EXTRACTION_QUALIFICATION_CHANGED"):
        x.begin_continuation(fresh, acceptance, attempt, changed, operation=op())
    with pytest.raises(JobStoreError, match="ATTEMPT_OWNER"):
        x.begin_continuation(
            fresh, acceptance, attempt, probe.owner(binding), operation=op()
        )
    # Ownership changes: the old lock is released, a new publisher claims.
    os.close(fresh._fd)
    other_handle = w.open_workspace(
        workspace.root, expected_identity=workspace.identity
    )
    try:
        other = s.claim_publisher(other_handle, job, operation=op())
        with pytest.raises(JobStoreError, match="PUBLISHER_STALE"):
            x.begin_continuation(
                fresh,
                acceptance,
                attempt,
                probe.owner(acceptance.binding),
                operation=op(),
            )
        other.close()
    finally:
        fresh._closed = True
        other_handle.close()
    verify_store(workspace)


def test_commit_ambiguity_is_queried_never_repeated(setup, monkeypatch):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2])
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    session = x.begin_continuation(
        fresh, acceptance, attempt, probe.owner(acceptance.binding), operation=op()
    )
    staged = probe.page(session, 3)
    session.reconcile(operation=op())
    real = w.commit
    lost = op()

    def commit_then_lose(connection):
        real(connection)
        raise sqlite3.OperationalError("reply lost")

    monkeypatch.setattr(w, "commit", commit_then_lose)
    with pytest.raises(JobStoreError, match="STORE_COMMIT_UNKNOWN"):
        session.publish(staged[0], operation=lost)
    monkeypatch.setattr(w, "commit", real)
    reopened = w.open_workspace(workspace.root, expected_identity=workspace.identity)
    try:
        queried = s.query_operation(reopened, lost)
        assert queried is not None and queried.kind == "publish_chunk"
        snapshot = c.checkpoint_snapshot(reopened, job, generation)
        assert queried.get("checkpoint") == snapshot.checkpoint
        assert snapshot.committed == ((0, 2), (2, 3))
        verify_store(reopened)
    finally:
        reopened.close()


def test_end_records_coverage_only_when_gap_free(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2])
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    session = x.begin_continuation(
        fresh, acceptance, attempt, probe.owner(acceptance.binding), operation=op()
    )
    probe.drive(session, [2, 2], publish=False)
    probe.finish_stream(session)
    with pytest.raises(JobStoreError, match="CONTINUATION_COVERAGE"):
        session.end(operation=op())
    assert workspace.use().execute(
        "SELECT count(*) FROM continuation_end"
    ).fetchone() == (0,)
    verify_store(workspace)


def test_verifier_and_reader_reject_grafted_and_damaged_history(setup, tmp_path):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2, 2], order=[0])
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    session = x.begin_continuation(
        fresh, acceptance, attempt, probe.owner(acceptance.binding), operation=op()
    )
    probe.drive(session, [2, 2, 1])
    probe.finish_stream(session)
    session.end(operation=op())
    verify_store(workspace)
    fresh.close()
    workspace.close()
    database = tmp_path / "workspace" / "store.sqlite"
    edits = {
        "reconciliation": "DELETE FROM reconciliation",
        "frontier": "UPDATE continuation SET frontier = 0, rows = rows",
        "producer": "UPDATE chunk SET attempt = (SELECT attempt FROM extraction)"
        " WHERE attempt IN (SELECT attempt FROM continuation)",
        "specification": "UPDATE extraction SET qualification = '[]'",
    }
    for name, edit in edits.items():
        copy = tmp_path / ("damage-" + name)
        copy.mkdir(mode=0o700)
        for item in (tmp_path / "workspace").iterdir():
            if item.is_dir():
                (copy / item.name).mkdir(mode=0o700)
                for inner in item.iterdir():
                    (copy / item.name / inner.name).write_bytes(inner.read_bytes())
                    (copy / item.name / inner.name).chmod(0o600)
            else:
                (copy / item.name).write_bytes(item.read_bytes())
                (copy / item.name).chmod(0o600)
        connection = sqlite3.connect(copy / "store.sqlite")
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(edit)
        connection.commit()
        connection.close()
        damaged = w.open_workspace(str(copy), expected_identity=workspace.identity)
        try:
            with pytest.raises(JobStoreError, match="STORE_INVARIANT"):
                verify_store(damaged)
        finally:
            damaged.close()
    assert database.exists()


def test_r1_consumers_keep_their_checkpoint_and_read_the_recovered_result(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2, 2], order=[0])
    old = c.checkpoint_snapshot(workspace, job, generation)
    early = s13.accept(
        workspace, job, generation, compiled, scope="committed_prefix", values=values
    )
    reader = probe.takeover(workspace, job, publisher)
    r.register_consumer(reader, early, operation=op())
    replay = r.open_replay(reader, early, operation=op())
    first = s13.issue(replay, 1)
    replay.acknowledge(first, operation=op())
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=reader
    )
    session = x.begin_continuation(
        fresh, acceptance, attempt, probe.owner(acceptance.binding), operation=op()
    )
    probe.drive(session, [2, 2, 1])
    probe.finish_stream(session)
    session.end(operation=op())
    state = r.consumer_state(workspace, early.consumer)
    assert (state.checkpoint, state.extent, state.position) == (old.checkpoint, 2, 1)
    latest = c.checkpoint_snapshot(workspace, job, generation)
    late = s13.accept(workspace, job, generation, compiled, values=values)
    assert (late.checkpoint, late.extent, late.scope) == (
        latest.checkpoint,
        5,
        "complete_capture",
    )
    r.register_consumer(fresh, late, operation=op())
    extents, end = s13.drain(r.open_replay(fresh, late, operation=op()), 2)
    assert extents == [(0, 2), (2, 4), (4, 5)] and end.extent == 5
    assert dict(end.layers)["continuations"][0][0] == attempt.identity
    resumed = s13.accept(
        workspace,
        job,
        generation,
        compiled,
        checkpoint=old.checkpoint,
        consumer=early.consumer,
        scope="committed_prefix",
        extent=2,
        values=values,
    )
    again = r.open_replay(fresh, resumed, operation=op())
    assert again.position == 1
    assert s13.issue(again, 2).occurrences == ((generation, 1),)
    verify_store(workspace)


@pytest.mark.parametrize(
    "target,cell",
    [(t, c) for t in ("postgres", "mysql") for c in probe.r2_families(t)],
    ids=lambda v: v if isinstance(v, str) else f"{v['case']}:{v['variant']}",
)
def test_every_admitted_r2_family_reconstructs_its_specification(
    tmp_path, target, cell
):
    """Pure coverage: live and loaded roots give one exact extraction
    specification per route (choice, coordinates, ordered source-use vector)."""
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution import compiled_output
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )

    reference = probe.fixture_reference(tmp_path, target, cell)
    if cell["excluded"]:
        assert reference is None
        return
    assert reference is not None
    artifact, preparation, query, output, binding = reference
    assert query is not None
    built = build_compiled(artifact, guarded=preparation, refinement=query)
    loaded = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    live = prepare_live_template(artifact, guarded=preparation, refinement=query)
    values = tuple(v.value for v in artifact.fixed_values)
    route = "mysql_rows" if target == "mysql" else "postgres_rows"
    texts = []
    for template in (live, loaded):
        bound = bind_values(template, tuple(zip(template.slots, values, strict=True)))
        out, refinement, _program = compiled_output(bound)
        texts.append(x.specification(refinement, out, route, "stable"))
        assert x.specification(refinement, out, route, "serializable") != texts[-1]
        if target == "postgres":
            assert (
                x.specification(refinement, out, "postgres_adbc", "stable") != texts[-1]
            )
    assert texts[0] == texts[1]
    spec = json.loads(texts[0])
    assert [s[:2] for s in spec["sources"]] == [
        [s.source.namespace, s.source.name] for s in query.sources
    ]
    assert json.loads(spec["scheme"])["choice"] == query.policy.choice


def test_cancellation_expiry_replay_and_conflict_stop_progress(setup, monkeypatch):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2])
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    owner = probe.owner(acceptance.binding)
    session = x.begin_continuation(fresh, acceptance, attempt, owner, operation=op())
    staged = probe.page(session, 3)
    assert session.ready
    owner._cancel.set()
    with pytest.raises(JobStoreError, match="CONTINUATION_CANCELED"):
        session.reconcile(operation=op())
    owner._cancel.clear()
    barrier = op()
    session.reconcile(operation=barrier)
    with pytest.raises(JobStoreError, match="RECONCILIATION_RECORDED"):
        session.reconcile(operation=op())
    # The same operation with a different request is a conflict, never a replay.
    session._reconciled = False
    session._observed += 1
    with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
        session.reconcile(operation=barrier)
    session._observed -= 1
    session._reconciled = True
    # An acceptance past its monotonic deadline stops the next write.
    monkeypatch.setattr(x, "_monotonic", lambda: acceptance._deadline + 1)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_EXPIRED"):
        session.publish(staged[0], operation=op())
    count = workspace.use().execute(
        "SELECT count(*) FROM chunk WHERE attempt = ?", (attempt.identity,)
    )
    assert count.fetchone() == (0,)
    # A non-EOF end is still recorded as an honest provisional observation.
    probe.finish_stream(session, source="EARLY_CLOSE")
    ended = session.end(operation=op())
    assert ended.get("checkpoint") is None
    verify_store(workspace)


def test_corrupt_or_missing_saved_bytes_are_refused_before_any_source(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2, 2])
    fresh = probe.takeover(workspace, job, publisher)
    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    chunks = workspace.root + "/chunks/"
    first, second = (chunks + m.file for m in snapshot.members)
    with open(first, "r+b") as stream:
        stream.seek(-1, 2)
        last = stream.read(1)
        stream.seek(-1, 2)
        stream.write(bytes([last[0] ^ 1]))
    with pytest.raises(JobStoreError, match="CHUNK_DIGEST"):
        probe.accept(workspace, job, generation, compiled, values)
    os.rename(second, second + ".moved")
    with pytest.raises(JobStoreError, match="CHUNK_DIGEST|CHUNK_MISSING"):
        probe.accept(workspace, job, generation, compiled, values)
    # Nothing was refetched or rewritten: the membership is unchanged.
    again = c.checkpoint_snapshot(workspace, job, generation)
    assert (again.checkpoint, again.members) == (snapshot.checkpoint, snapshot.members)
    fresh.close()


def test_sessions_and_acceptances_never_cross_a_process(setup):
    if setup is None:
        return
    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(publisher, generation, binding, [2])
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    session = x.begin_continuation(
        fresh, acceptance, attempt, probe.owner(acceptance.binding), operation=op()
    )
    session._pid = -1
    with pytest.raises(JobStoreError, match="CAPTURE_FOREIGN_PROCESS"):
        session.stage()
    object.__setattr__(acceptance, "_pid", -1)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_FOREIGN_PROCESS"):
        x.begin_continuation(
            fresh, acceptance, attempt, probe.owner(acceptance.binding), operation=op()
        )


@pytest.mark.parametrize("saved", (True, False))
def test_empty_refined_result_keeps_a_schema_member_with_empty_coordinates(
    setup, monkeypatch, saved
):
    """An empty refined result: the saved (or newly staged) [0, 0) EOF member
    carries an empty coordinate list; a saved one is matched only by a fresh
    empty result with the same schema (SYNTHETIC schema step, labelled)."""
    if setup is None:
        return
    from types import SimpleNamespace

    workspace, job, publisher, binding, generation, compiled, values = setup
    probe.extract(
        publisher, generation, binding, [], order=[0] if saved else [], eof=saved
    )
    descriptors = [
        json.loads(r[0])
        for r in workspace.use().execute("SELECT descriptor FROM chunk").fetchall()
    ]
    assert all(d["coordinates"] == [] for d in descriptors)
    fresh, acceptance, attempt = probe.recover(
        workspace, job, generation, compiled, values, previous=publisher
    )
    assert acceptance.known == (0 if saved else None)
    owner = probe.owner(acceptance.binding)
    schema = SimpleNamespace(equals=lambda other, check_metadata: other == "SCHEMA")
    monkeypatch.setattr(
        owner, "_payloads", SimpleNamespace(binding=SimpleNamespace(schema="SCHEMA"))
    )
    monkeypatch.setattr(
        x.ContinuationSession,
        "_chunk",
        lambda self, index: SimpleNamespace(table=SimpleNamespace(schema=schema)),
    )
    session = x.begin_continuation(fresh, acceptance, attempt, owner, operation=op())
    assert session.ready is (not saved)
    if not saved:
        session.reconcile(operation=op())
    staged = probe.finish_stream(session)
    assert staged is not None and len(staged) == (0 if saved else 1)
    if saved:
        session.reconcile(operation=op())
    for item in staged or ():
        session.publish(item, operation=op())
    ended = session.end(operation=op())
    latest = c.checkpoint_snapshot(workspace, job, generation)
    assert (latest.frontier, latest.observed_end, latest.holes) == (0, 0, ())
    assert ended.get("checkpoint") == latest.checkpoint
    assert [(m.start, m.stop) for m in latest.members] == [(0, 0)]
    verify_store(workspace)
