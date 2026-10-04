"""S11 job store: specification, identities, publisher fence, history, damage."""

from dataclasses import asdict
import json
import os
import sqlite3

import pytest

from _pietto_phase68_slice11_probe import (
    SENTINEL,
    compiled_template,
    owner_outcome,
    qualified,
    root_of,
    trust,
)
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_compiled_schema import CompiledError
from pietto._project.project_execution_binding_verification import atom
from pietto._project.project_execution_template import (
    BindingError,
    bind_values,
    describe_compiled_binding,
)
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Two-slot templates per tag: WHERE Int plus one seeded typed literal."""
    root = tmp_path_factory.mktemp("s11-templates")
    return {
        seed: compiled_template(root / str(i), seed=seed)
        for i, seed in enumerate(("true", "1", "1.5", '"seed"'))
    }


@pytest.fixture
def workspace(tmp_path):
    if not qualified(tmp_path):
        yield None
        return
    handle = w.create_workspace(str(tmp_path / "workspace"))
    yield handle
    handle.close()


def op():
    return s.new_operation()


def values_for(template, *choices):
    return tuple(
        (slot, choice[slot.tag]) for slot, choice in zip(template.slots, choices)
    )


A = {"Int": 5, "Bool": True, "Float": -0.0, "Text": ""}
B = {"Int": -(2**63), "Bool": False, "Float": 0.0, "Text": SENTINEL + "雪é😀 ? %s $1"}


def job_with_generation(workspace, template, choice=A, route="postgres_rows"):
    job = s.register_job(workspace, template, operation=op()).get("job")
    publisher = s.claim_publisher(workspace, job, operation=op())
    binding = bind_values(template, values_for(template, choice, choice))
    record = s.register_binding(publisher, binding, operation=op()).get("binding")
    generation = s.register_generation(
        publisher, record, binding, route=route, isolation="stable", operation=op()
    ).get("generation")
    return job, publisher, binding, record, generation


def test_live_and_loaded_entries_store_the_same_pinned_bytes_as_distinct_jobs(
    tmp_path, workspace
):
    if workspace is None:
        return
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    live, built = compiled_template(tmp_path / "live")
    loaded = prepare_compiled_template(load_compiled(built.payload, **trust(built)))
    jobs = [
        s.register_job(workspace, t, operation=op()).get("job") for t in (live, loaded)
    ]
    assert len(set(jobs)) == 2
    for job in jobs:
        record = s.job_record(workspace, job)
        assert (record.pin, record.producer, record.compatibility) == (
            built.pin,
            built.producer,
            built.compatibility,
        )
        assert record.bundle_bytes == len(built.payload)
        assert (record.state, record.publisher_epoch, record.revision) == (
            "ACTIVE",
            0,
            1,
        )
        stored = w.read(
            workspace,
            lambda c: c.execute(
                "SELECT bundle FROM job WHERE identity = ?", (job,)
            ).fetchone()[0],
        )
        assert stored == built.payload
        fresh = s.load_job(workspace, job, **trust(built))
        root = root_of(fresh)
        assert root.expected_pin == built.pin and root is not root_of(live)


@pytest.mark.parametrize("seed", ("true", "1", "1.5", '"seed"'))
def test_typed_vectors_round_trip_a_b_a_with_fresh_bindings(built, tmp_path, seed):
    if not qualified(tmp_path):
        return
    template, build = built[seed]
    root = str(tmp_path / "workspace")
    workspace = w.create_workspace(root)
    identity = workspace.identity
    job = s.register_job(workspace, template, operation=op()).get("job")
    publisher = s.claim_publisher(workspace, job, operation=op())
    original = [bind_values(template, values_for(template, x, x)) for x in (A, B, A)]
    records = [
        s.register_binding(publisher, b, operation=op()).get("binding")
        for b in original
    ]
    assert len(set(records)) == 3
    publisher.close()
    workspace.close()
    reopened = w.open_workspace(root, expected_identity=identity)
    try:
        fresh_template = s.load_job(reopened, job, **trust(build))
        rebound = [s.bind_record(reopened, job, fresh_template, r) for r in records]
        for before, after in zip(original, rebound, strict=True):
            assert tuple(atom(v) for v in after.values) == tuple(
                atom(v) for v in before.values
            )
            assert tuple(atom(v) for v in after.arguments) == tuple(
                atom(v) for v in before.arguments
            )
        references = {b.instance_reference for b in original + rebound}
        assert len(references) == 6
        route = "postgres_rows"
        described = [
            json.dumps(
                {
                    k: v
                    for k, v in asdict(
                        describe_compiled_binding(b, route=route)
                    ).items()
                    if k != "binding_reference"
                },
                default=repr,
            )
            for b in rebound
        ]
        assert described[0] == described[2]
        if "Float" in [x.tag for x in template.slots]:
            assert [atom(v) for v in rebound[0].values] != [
                atom(v) for v in rebound[1].values
            ]
        assert verify_store(reopened)["bindings"] == 3
    finally:
        reopened.close()


def test_signed_zero_and_bool_int_are_distinct_vectors(built, workspace):
    if workspace is None:
        return
    template, _ = built["1.5"]
    job = s.register_job(workspace, template, operation=op()).get("job")
    publisher = s.claim_publisher(workspace, job, operation=op())
    negative = bind_values(template, values_for(template, A, A))
    positive = bind_values(
        template, values_for(template, {**A, "Float": 0.0}, {**A, "Float": 0.0})
    )
    vectors = []
    for binding in (negative, positive):
        record = s.register_binding(publisher, binding, operation=op()).get("binding")
        vectors.append(
            w.read(
                workspace,
                lambda c, r=record: c.execute(
                    "SELECT vector FROM binding WHERE identity = ?", (r,)
                ).fetchone()[0],
            )
        )
    assert vectors[0] != vectors[1] and "-0x0.0p+0" in vectors[0]
    int_template, _ = built["1"]
    with pytest.raises(BindingError):
        bind_values(int_template, values_for(int_template, {**A, "Int": True}, A))
    bool_template, _ = built["true"]
    with pytest.raises(BindingError):
        bind_values(bool_template, values_for(bool_template, A, {**A, "Bool": 1}))


def test_illegal_or_foreign_bindings_do_not_mutate_the_job(built, tmp_path, workspace):
    if workspace is None:
        return
    template, _ = built["1"]
    other, _ = built["true"]
    job, publisher, binding, record, generation = job_with_generation(
        workspace, template
    )
    before = s.job_record(workspace, job)
    foreign = bind_values(other, values_for(other, A, A))
    with pytest.raises(JobStoreError, match="BINDING_ROOT"):
        s.register_binding(publisher, foreign, operation=op())
    changed = bind_values(template, values_for(template, B, B))
    with pytest.raises(JobStoreError, match="BINDING_VECTOR"):
        s.register_generation(
            publisher,
            record,
            changed,
            route="postgres_rows",
            isolation="stable",
            operation=op(),
        )
    with pytest.raises(JobStoreError, match="BINDING_VECTOR"):
        s.open_attempt(publisher, generation, changed, operation=op())
    # Route admissibility stays the S10 owner's own value-free category.
    with pytest.raises(BindingError, match="COMPILED_DESCRIPTION_ROUTE"):
        s.register_generation(
            publisher,
            record,
            binding,
            route="mysql_rows",
            isolation="stable",
            operation=op(),
        )
    with pytest.raises(BindingError):
        bind_values(template, values_for(template, {**A, "Int": 2**63}, A))
    after = s.job_record(workspace, job)
    assert after == before
    assert verify_store(workspace)["operations"] == len(before.operations)


def test_fresh_trust_inputs_and_separate_compatibility_dimensions(
    built, workspace, monkeypatch
):
    if workspace is None:
        return
    template, build = built["1"]
    job = s.register_job(workspace, template, operation=op()).get("job")
    good = trust(build)
    for change, category in (
        ({"expected_pin": "0" * 64}, "JOB_TRUST_INPUT"),
        ({"accepted_producer": "other"}, "JOB_TRUST_INPUT"),
        (
            {"accepted_compatibility": build.compatibility[:-1] + ("0" * 64,)},
            "JOB_TRUST_INPUT",
        ),
    ):
        with pytest.raises(JobStoreError, match=category):
            s.load_job(workspace, job, **{**good, **change})
    from pietto._project import project_compiled_loading

    real = project_compiled_loading.supported_compatibility
    monkeypatch.setattr(
        project_compiled_loading,
        "supported_compatibility",
        lambda: real()[:-1] + ("f" * 64,),
    )
    with pytest.raises(JobStoreError, match="JOB_COMPATIBILITY"):
        s.load_job(workspace, job, **good)
    monkeypatch.setattr(project_compiled_loading, "supported_compatibility", real)
    raw = w.read(
        workspace,
        lambda c: c.execute(
            "SELECT bundle FROM job WHERE identity = ?", (job,)
        ).fetchone()[0],
    )
    rewritten = raw.replace(build.producer.encode(), (build.producer + "x").encode(), 1)
    from pietto._project.project_compiled_schema import content_pin

    def store(bundle, pin):
        w.write(
            workspace,
            lambda c: c.execute(
                "UPDATE job SET bundle = ?, pin = ? WHERE identity = ?",
                (bundle, pin, job),
            ),
        )

    # Rewriting bytes alone: the S10 loader rejects the caller's pin.
    store(rewritten, build.pin)
    with pytest.raises(CompiledError, match="COMPILED_CONTENT_PIN"):
        s.load_job(workspace, job, **good)
    # Rewriting the colocated pin too: the stored copy is not a trust anchor.
    store(rewritten, content_pin(rewritten))
    with pytest.raises(JobStoreError, match="JOB_TRUST_INPUT"):
        s.load_job(workspace, job, **good)
    store(raw, build.pin)
    assert root_of(s.load_job(workspace, job, **good)).expected_pin == build.pin


def test_one_publisher_per_job_and_independent_jobs(built, workspace):
    if workspace is None:
        return
    template, _ = built["1"]
    first = s.register_job(workspace, template, operation=op()).get("job")
    second = s.register_job(workspace, template, operation=op()).get("job")
    holder = s.claim_publisher(workspace, first, operation=op())
    before = s.job_record(workspace, first)
    busy = op()
    with pytest.raises(JobStoreError, match="PUBLISHER_BUSY"):
        s.claim_publisher(workspace, first, operation=busy)
    assert s.query_operation(workspace, busy) is None
    assert s.job_record(workspace, first) == before
    other = s.claim_publisher(workspace, second, operation=op())
    assert (holder.epoch, other.epoch) == (1, 1)
    binding = bind_values(template, values_for(template, A, A))
    s.register_binding(other, binding, operation=op())
    holder.close()
    holder.close()
    again = s.claim_publisher(workspace, first, operation=op())
    assert again.epoch == 2 and again.instance != holder.instance
    lock = os.path.join(workspace.root, "locks", first + ".lock")
    assert not os.get_inheritable(again._fd)
    assert os.stat(lock).st_ino == os.fstat(again._fd).st_ino
    with pytest.raises(JobStoreError, match="JOB_UNKNOWN"):
        s.claim_publisher(workspace, w.new_identity("job"), operation=op())
    assert sorted(os.listdir(os.path.join(workspace.root, "locks"))) == sorted(
        [first + ".lock", second + ".lock"]
    )


def test_stale_epoch_is_rejected_at_the_write_boundary(built, workspace):
    if workspace is None:
        return
    template, _ = built["1"]
    job, old, binding, record, generation = job_with_generation(workspace, template)
    # A direct same-user edit removes the lock file; this bypasses OS exclusion,
    # but the durable epoch still fences the database write boundary.
    os.unlink(os.path.join(workspace.root, "locks", job + ".lock"))
    new = s.claim_publisher(workspace, job, operation=op())
    assert new.epoch == old.epoch + 1
    before = s.job_record(workspace, job)
    for call in (
        lambda: s.register_binding(old, binding, operation=op()),
        lambda: s.register_generation(
            old,
            record,
            binding,
            route="postgres_rows",
            isolation="stable",
            operation=op(),
        ),
        lambda: s.open_attempt(old, generation, binding, operation=op()),
        lambda: s.cancel_job(old, operation=op()),
    ):
        with pytest.raises(JobStoreError, match="PUBLISHER_STALE"):
            call()
    assert s.job_record(workspace, job) == before
    attempt = s.open_attempt(new, generation, binding, operation=op())
    with pytest.raises(JobStoreError, match="ATTEMPT_PUBLISHER"):
        s.record_not_executed(old, attempt, operation=op())
    new.revision -= 1
    with pytest.raises(JobStoreError, match="PUBLISHER_REVISION"):
        s.record_not_executed(new, attempt, operation=op())
    new.revision += 1
    forged = s.Publisher(
        workspace, job, new.epoch, w.new_identity("pub"), new.revision, os.dup(new._fd)
    )
    with pytest.raises(JobStoreError, match="PUBLISHER_STALE"):
        s.record_not_executed(
            forged,
            s.AttemptHandle(
                forged,
                attempt.identity,
                generation,
                1,
                "postgres_rows",
                "stable",
                binding,
            ),
            operation=op(),
        )
    forged.close()
    s.record_not_executed(new, attempt, operation=op())
    verify_store(workspace)


def test_handle_lifetime_and_wrong_owner(built, tmp_path, workspace):
    if workspace is None:
        return
    template, _ = built["1"]
    job, publisher, binding, record, generation = job_with_generation(
        workspace, template
    )
    other_job, other, other_binding, _, other_generation = job_with_generation(
        workspace, template
    )
    attempt = s.open_attempt(other, other_generation, other_binding, operation=op())
    with pytest.raises(JobStoreError, match="ATTEMPT_PUBLISHER"):
        s.record_not_executed(publisher, attempt, operation=op())
    with pytest.raises(JobStoreError, match="GENERATION_UNKNOWN"):
        s.open_attempt(publisher, other_generation, binding, operation=op())
    with pytest.raises(JobStoreError, match="BINDING_UNKNOWN"):
        s.bind_record(workspace, other_job, template, record)
    owner = owner_outcome(binding)
    with pytest.raises(JobStoreError, match="ATTEMPT_OWNER"):
        s.record_attempt(other, attempt, owner, operation=op())
    publisher.close()
    with pytest.raises(JobStoreError, match="PUBLISHER_CLOSED"):
        s.cancel_job(publisher, operation=op())
    publisher._pid = -1
    with pytest.raises(JobStoreError, match="PUBLISHER_FOREIGN_PROCESS"):
        s.cancel_job(publisher, operation=op())
    publisher._pid = os.getpid()


def test_operation_identity_replay_conflict_and_query(built, workspace):
    if workspace is None:
        return
    template, _ = built["1"]
    operation = op()
    first = s.register_job(workspace, template, operation=operation)
    replay = s.register_job(workspace, template, operation=operation)
    assert first.observation == "COMMITTED_THIS_CALL"
    assert replay.observation == "PREVIOUSLY_COMMITTED"
    assert (replay.job, replay.sequence, replay.result) == (
        first.job,
        first.sequence,
        first.result,
    )
    queried = s.query_operation(workspace, operation)
    assert queried is not None and queried.observation == "QUERIED"
    assert (queried.job, queried.result) == (first.job, first.result)
    other, _ = built["true"]
    with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
        s.register_job(workspace, other, operation=operation)
    publisher = s.claim_publisher(workspace, first.job, operation=op())
    with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
        s.cancel_job(publisher, operation=operation)
    a = bind_values(template, values_for(template, A, A))
    b = bind_values(template, values_for(template, B, B))
    binding_operation = op()
    s.register_binding(publisher, a, operation=binding_operation)
    with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
        s.register_binding(publisher, b, operation=binding_operation)
    claim = op()
    publisher.close()
    again = s.claim_publisher(workspace, first.job, operation=claim)
    again.close()
    with pytest.raises(JobStoreError, match="PUBLISHER_CLAIM_REPLAYED"):
        s.claim_publisher(workspace, first.job, operation=claim)
    assert s.query_operation(workspace, op()) is None
    for bad in ("op-1", "job-" + "0" * 32, None, "op-" + "G" * 32):
        with pytest.raises(JobStoreError, match="OPERATION_IDENTITY"):
            s.query_operation(workspace, bad)  # type: ignore[arg-type]
    assert len(s.job_record(workspace, first.job).operations) == 4
    verify_store(workspace)


@pytest.mark.parametrize("injection", ["before_commit", "after_commit"])
def test_injected_ambiguous_commit_has_zero_or_one_queryable_effect(
    built, tmp_path, monkeypatch, injection
):
    if not qualified(tmp_path):
        return
    template, _ = built["1"]
    root = str(tmp_path / "workspace")
    workspace = w.create_workspace(root)
    identity = workspace.identity
    real = w.commit

    def injected(connection):
        # Explicit application fault injection, not an observed device failure.
        if injection == "after_commit":
            real(connection)
        raise sqlite3.OperationalError("injected disk I/O error")

    operation = op()
    monkeypatch.setattr(w, "commit", injected)
    with pytest.raises(JobStoreError, match="STORE_COMMIT_UNKNOWN"):
        s.register_job(workspace, template, operation=operation)
    with pytest.raises(JobStoreError, match="WORKSPACE_RETIRED"):
        s.query_operation(workspace, operation)
    workspace.close()
    monkeypatch.setattr(w, "commit", real)
    fresh = w.open_workspace(root, expected_identity=identity)
    try:
        queried = s.query_operation(fresh, operation)
        jobs = w.read(
            fresh, lambda c: c.execute("SELECT count(*) FROM job").fetchone()[0]
        )
        if injection == "before_commit":
            assert queried is None and jobs == 0
        else:
            assert queried is not None and queried.observation == "QUERIED"
            assert jobs == 1
        verify_store(fresh)
    finally:
        fresh.close()


def test_layered_history_keeps_unknown_beside_later_attempts(built, workspace):
    if workspace is None:
        return
    template, _ = built["1"]
    job, first, binding, record, generation = job_with_generation(workspace, template)
    interrupted = s.open_attempt(first, generation, binding, operation=op())
    with pytest.raises(JobStoreError, match="ATTEMPT_OPEN"):
        s.open_attempt(first, generation, binding, operation=op())
    first.close()
    second = s.claim_publisher(workspace, job, operation=op())
    with pytest.raises(JobStoreError, match="ATTEMPT_PUBLISHER"):
        s.record_not_executed(second, interrupted, operation=op())
    s.interrupt_attempt(second, interrupted.identity, operation=op())
    with pytest.raises(JobStoreError, match="ATTEMPT_TERMINAL"):
        s.interrupt_attempt(second, interrupted.identity, operation=op())
    fresh = s.bind_record(workspace, job, template, record)
    owner_attempt = s.open_attempt(second, generation, fresh, operation=op())
    with pytest.raises(JobStoreError, match="ATTEMPT_PUBLISHER"):
        s.interrupt_attempt(second, owner_attempt.identity, operation=op())
    with pytest.raises(JobStoreError, match="ATTEMPT_OWNER"):
        s.record_attempt(second, owner_attempt, owner_outcome(binding), operation=op())
    owner = owner_outcome(fresh, password=SENTINEL + "-password", connect=True)
    recorded = s.record_attempt(second, owner_attempt, owner, operation=op())
    assert recorded.get("kind") == "OUTCOME"
    with pytest.raises(JobStoreError, match="ATTEMPT_TERMINAL"):
        s.interrupt_attempt(second, owner_attempt.identity, operation=op())
    history = s.job_record(workspace, job)
    assert [
        (a.ordinal, a.publisher_epoch, a.terminal, a.terminal_epoch)
        for a in history.attempts
    ] == [
        (1, 1, "INTERRUPTED", 2),
        (2, 2, "OUTCOME", 2),
    ]
    old, new = (dict(a.outcome or ()) for a in history.attempts)
    assert old == s.INTERRUPTED
    assert (
        new["source"],
        new["transaction"],
        new["cleanup"],
        new["local_durable_result"],
    ) == (
        "FAILED",
        "NOT_STARTED",
        "CLOSED",
        "NOT_IMPLEMENTED",
    )
    assert new["remote_source_use_end"] == "REMOTE_QUIESCENCE_UNCONFIRMED"
    assert new["binding_reference"] == fresh.instance_reference
    assert verify_store(workspace)["terminals"] == 2


@pytest.mark.parametrize("route", ["postgres_rows", "postgres_adbc", "mysql_rows"])
def test_every_route_owner_records_its_exact_closed_layers(tmp_path, built, route):
    """Each route closes with its own cleanup vocabulary; an open owner refuses."""
    if not qualified(tmp_path):
        return
    from pietto._project.project_execution import compiled_attempt_outcome

    if route == "mysql_rows":
        template, _ = compiled_template(tmp_path / "mysql", target="mysql")
    else:
        template, _ = built["1"]
    workspace = w.create_workspace(str(tmp_path / "workspace"))
    try:
        job, publisher, binding, _record, generation = job_with_generation(
            workspace, template, route=route
        )
        attempt = s.open_attempt(publisher, generation, binding, operation=op())
        owner = owner_outcome(binding, route=route)
        owner._closed = False
        with pytest.raises(JobStoreError, match="ATTEMPT_OWNER_OPEN"):
            s.record_attempt(publisher, attempt, owner, operation=op())
        owner._closed = True
        s.record_attempt(publisher, attempt, owner, operation=op())
        (stored,) = s.job_record(workspace, job).attempts
        assert {
            k: list(v) if type(v) is tuple else v for k, v in (stored.outcome or ())
        } == json.loads(json.dumps(asdict(compiled_attempt_outcome(owner))))
        verify_store(workspace)
    finally:
        workspace.close()


def test_cancellation_forbids_new_work_but_not_truthful_terminals(built, workspace):
    if workspace is None:
        return
    template, _ = built["1"]
    job, publisher, binding, record, generation = job_with_generation(
        workspace, template
    )
    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    cancelled = s.cancel_job(publisher, operation=op())
    assert dict(cancelled.result) == {
        "revision": cancelled.get("revision"),
        "state": "CANCELLED",
    }
    for call in (
        lambda: s.register_binding(publisher, binding, operation=op()),
        lambda: s.register_generation(
            publisher,
            record,
            binding,
            route="postgres_rows",
            isolation="stable",
            operation=op(),
        ),
        lambda: s.open_attempt(publisher, generation, binding, operation=op()),
        lambda: s.cancel_job(publisher, operation=op()),
    ):
        with pytest.raises(JobStoreError, match="JOB_STATE"):
            call()
    s.record_attempt(publisher, attempt, owner_outcome(binding), operation=op())
    publisher.close()
    later = s.claim_publisher(workspace, job, operation=op())
    with pytest.raises(JobStoreError, match="JOB_STATE"):
        s.open_attempt(later, generation, binding, operation=op())
    record_state = s.job_record(workspace, job)
    assert record_state.state == "CANCELLED" and record_state.publisher_epoch == 2
    verify_store(workspace)


def tamper(root, *statements):
    raw = sqlite3.connect(os.path.join(root, "store.sqlite"), isolation_level=None)
    try:
        raw.execute("PRAGMA foreign_keys = OFF")
        raw.execute("PRAGMA ignore_check_constraints = ON")
        for statement, parameters in statements:
            raw.execute(statement, parameters)
    finally:
        raw.close()


def build_history(workspace, template):
    job, publisher, binding, record, generation = job_with_generation(
        workspace, template
    )
    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    s.record_attempt(publisher, attempt, owner_outcome(binding), operation=op())
    other = s.register_job(workspace, template, operation=op()).get("job")
    publisher.close()
    return job, other, record, generation, attempt.identity


@pytest.mark.parametrize(
    "damage,category",
    [
        ("epoch_without_claim", "JOB_STATE"),
        ("revision", "JOB_STATE"),
        ("state", "JOB_STATE|INTEGRITY"),
        ("generation_job", "INTEGRITY"),
        ("attempt_epoch", "ATTEMPT_HISTORY"),
        ("terminal_only", "TERMINAL_HISTORY"),
        ("missing_history", "OPERATION_SEQUENCE"),
        ("pin", "JOB_BUNDLE"),
        ("vector_reencoded_tag", "BINDING_VECTOR|BINDING_HISTORY"),
        ("description_swapped_slots", "GENERATION_DESCRIPTION|GENERATION_HISTORY"),
        ("duplicate_terminal_kind", "TERMINAL_HISTORY"),
    ],
)
def test_independent_checker_rejects_damage(tmp_path, built, damage, category):
    if not qualified(tmp_path):
        return
    template, _ = built["1"]
    root = str(tmp_path / "workspace")
    workspace = w.create_workspace(root)
    identity = workspace.identity
    job, other, record, generation, attempt = build_history(workspace, template)
    workspace.close()
    statements = {
        "epoch_without_claim": (
            "UPDATE job SET publisher_epoch = publisher_epoch + 1 WHERE identity = ?",
            (job,),
        ),
        "revision": (
            "UPDATE job SET revision = revision + 1 WHERE identity = ?",
            (job,),
        ),
        "state": ("UPDATE job SET state = 'PAUSED' WHERE identity = ?", (job,)),
        "generation_job": (
            "UPDATE generation SET job = ? WHERE identity = ?",
            (other, generation),
        ),
        "attempt_epoch": (
            "UPDATE attempt SET publisher_epoch = 2 WHERE identity = ?",
            (attempt,),
        ),
        "terminal_only": (
            'UPDATE attempt_terminal SET outcome = replace(outcome, \'"transaction":"NOT_STARTED"\', \'"transaction":"COMMIT_ACK"\') WHERE attempt = ?',
            (attempt,),
        ),
        "missing_history": ("DELETE FROM operation WHERE sequence = 3", ()),
        "pin": ("UPDATE job SET pin = ? WHERE identity = ?", ("0" * 64, job)),
        "vector_reencoded_tag": (
            'UPDATE binding SET vector = replace(vector, \'["Int","5"]\', \'["Bool",true]\') WHERE identity = ?',
            (record,),
        ),
        "description_swapped_slots": (
            "UPDATE generation SET description = replace(description, '\"Int\"', '\"Text\"') WHERE identity = ?",
            (generation,),
        ),
        "duplicate_terminal_kind": (
            "UPDATE attempt_terminal SET kind = 'INTERRUPTED' WHERE attempt = ?",
            (attempt,),
        ),
    }
    tamper(root, statements[damage])
    try:
        reopened = w.open_workspace(root, expected_identity=identity)
    except JobStoreError as error:
        assert str(error) == "WORKSPACE_SCHEMA"
        return
    try:
        with pytest.raises(JobStoreError, match="STORE_INVARIANT_(" + category + ")"):
            verify_store(reopened)
    finally:
        reopened.close()


def test_coordinated_reencoding_needs_the_independent_literal_oracle(tmp_path, built):
    """A consistent rewrite of vector AND history passes structural checks; only the
    frozen literal oracle (not the store's decoder) detects the changed value."""
    if not qualified(tmp_path):
        return
    template, _ = built["1"]
    root = str(tmp_path / "workspace")
    workspace = w.create_workspace(root)
    identity = workspace.identity
    job, other, record, generation, attempt = build_history(workspace, template)
    workspace.close()
    tamper(
        root,
        (
            'UPDATE binding SET vector = replace(vector, \'["Int","5"]\', \'["Int","6"]\')',
            (),
        ),
        (
            "UPDATE operation SET request = replace(request, ?, ?)",
            ('[\\"Int\\",\\"5\\"]', '[\\"Int\\",\\"6\\"]'),
        ),
    )
    reopened = w.open_workspace(root, expected_identity=identity)
    try:
        verify_store(reopened)
        rebound = s.bind_record(reopened, job, template, record)
        oracle = tuple(A[slot.tag] for slot in template.slots)
        assert tuple(atom(v) for v in rebound.values) != tuple(atom(v) for v in oracle)
    finally:
        reopened.close()


def test_damaged_stored_vector_is_a_typed_refusal(tmp_path, built):
    if not qualified(tmp_path):
        return
    template, _ = built["1"]
    root = str(tmp_path / "workspace")
    workspace = w.create_workspace(root)
    identity = workspace.identity
    job, other, record, generation, attempt = build_history(workspace, template)
    workspace.close()
    for damaged in ('[["Int","05"],["Int","5"]]', "not-json", '[["Int"]]'):
        tamper(
            root,
            ("UPDATE binding SET vector = ? WHERE identity = ?", (damaged, record)),
        )
        reopened = w.open_workspace(root, expected_identity=identity)
        try:
            with pytest.raises(JobStoreError, match="BINDING_VECTOR"):
                s.bind_record(reopened, job, template, record)
        finally:
            reopened.close()


def test_protected_values_and_credentials_stay_confined(tmp_path, built):
    if not qualified(tmp_path):
        return
    template, _ = built['"seed"']
    root = tmp_path / "workspace"
    workspace = w.create_workspace(str(root))
    seen = []
    job, publisher, binding, record, generation = job_with_generation(
        workspace, template, choice=B
    )
    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    password = SENTINEL + "-credential"
    owner = owner_outcome(binding, password=password, connect=True)
    seen.append(s.record_attempt(publisher, attempt, owner, operation=op()))
    for call in (
        lambda: s.register_binding(
            publisher,
            bind_values(template, values_for(template, B, {**B, "Int": 2**63})),
            operation=op(),
        ),
        lambda: s.load_job(
            workspace,
            job,
            expected_pin="0" * 64,
            accepted_producer="x",
            accepted_compatibility=(),
        ),
    ):
        try:
            call()
        except (JobStoreError, BindingError) as error:
            seen.append(error)
    seen += [
        workspace,
        publisher,
        attempt,
        s.job_record(workspace, job),
        s.query_operation(workspace, seen[0].operation),
    ]
    for item in seen:
        assert SENTINEL not in repr(item) and SENTINEL not in str(item)
    publisher.close()
    workspace.close()
    contents = {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }
    assert set(contents) == {
        "store.sqlite",
        "workspace.json",
        "locks/" + job + ".lock",
    }
    assert SENTINEL.encode() in contents["store.sqlite"]
    assert password.encode() not in contents["store.sqlite"]
    assert all(
        SENTINEL.encode() not in v for k, v in contents.items() if k != "store.sqlite"
    )


def test_record_and_size_bounds_fail_closed(built, workspace, monkeypatch):
    if workspace is None:
        return
    template, _ = built["1"]
    monkeypatch.setattr(s, "LIMITS", {**s.LIMITS, "job": 1})
    s.register_job(workspace, template, operation=op())
    with pytest.raises(JobStoreError, match="STORE_LIMIT"):
        s.register_job(workspace, template, operation=op())
    monkeypatch.setattr(s, "LIMITS", {**s.LIMITS, "job": 3})
    job, publisher, binding, record, generation = job_with_generation(
        workspace, template
    )
    monkeypatch.setattr(s, "MAX_ATTEMPT_ORDINAL", 1)
    first = s.open_attempt(publisher, generation, binding, operation=op())
    s.record_not_executed(publisher, first, operation=op())
    with pytest.raises(JobStoreError, match="STORE_LIMIT"):
        s.open_attempt(publisher, generation, binding, operation=op())
    monkeypatch.setattr(s, "MAX_VECTOR_BYTES", 4)
    with pytest.raises(JobStoreError, match="BINDING_VECTOR"):
        s.register_binding(publisher, binding, operation=op())
    before = s.job_record(workspace, job)
    monkeypatch.setattr(w, "CONTROL_RESERVE", workspace.budget)
    with pytest.raises(JobStoreError, match="WORKSPACE_BUDGET"):
        s.register_job(workspace, template, operation=op())
    assert s.job_record(workspace, job) == before
