"""S13 process histories: real SIGKILL cursor cuts, query-after-loss and contention.

Children are registered spawned interpreters that open their own workspace,
claim their own publisher and take their own fresh acceptance; no live handle
crosses a process boundary. Saved inputs use S12's Arrow-free storage step and
the replay data step is ARROW_FREE_REPLAY_STEP. SIGKILL cuts are real process
deaths at named protocol steps, not power-loss certificates.
"""

import json

import pytest

import _pietto_phase68_slice13_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from _pietto_phase68_slice11_probe import finish, kill, until
from pietto._project import project_job_replay as r
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

op = probe.op

CUT = r"""
workspace, publisher, acceptance = attach()
cut, real_commit = config["cut"], w.commit
def stop_before(connection):
    barrier("cut")
    hold()
def stop_after(connection):
    real_commit(connection)
    barrier("cut")
    hold()
if cut.startswith("C1"):
    w.commit = stop_before if cut == "C1a_register_before_commit" else stop_after
    r.register_consumer(publisher, acceptance, operation=config["operation"])
r.register_consumer(publisher, acceptance, operation=s.new_operation())
replay = r.open_replay(publisher, acceptance, operation=s.new_operation())
if cut == "C2_session_without_offer":
    barrier("cut")
    hold()
if cut == "C3_issued_before_seen":
    w.commit = stop_after
issue = config["operation"] if cut in ("C3_issued_before_seen",
    "C4_handed_off_before_ack", "C7_acknowledged_before_end") else s.new_operation()
item = replay.next(2, operation=issue)
if cut == "C4_handed_off_before_ack":
    barrier("cut")
    hold()
if cut == "C7_acknowledged_before_end":
    replay.acknowledge(item, operation=s.new_operation())
    replay.acknowledge(replay.next(2, operation=s.new_operation()),
        operation=s.new_operation())
    barrier("cut")
    hold()
w.commit = stop_before if cut == "C5_ack_before_commit" else stop_after
replay.acknowledge(item, operation=config["operation"])
"""

SESSION_A = r"""
workspace, publisher, acceptance = attach()
replay = r.open_replay(publisher, acceptance, operation=s.new_operation())
replay.acknowledge(replay.next(2, operation=s.new_operation()),
    operation=s.new_operation())
offered = replay.next(2, operation=s.new_operation())
barrier("offered")
hold()
"""

LOST_REPLY = r"""
workspace, publisher, acceptance = attach()
replay = r.open_replay(publisher, acceptance, operation=s.new_operation())
replay.acknowledge(replay.next(2, operation=s.new_operation()),
    operation=s.new_operation())
item = replay.next(2, operation=s.new_operation())
real_commit = w.commit
def stop_after(connection):
    real_commit(connection)
    barrier("cut")
    hold()
w.commit = stop_after
replay.acknowledge(item, operation=config["operation"])
"""

RESUME = r"""
workspace, publisher, acceptance = attach()
replay = r.open_replay(publisher, acceptance, operation=s.new_operation())
start = replay.position
extents, end = probe.drain(replay, config["rows"])
replay.close()
publisher.close()
workspace.close()
emit({"start": start, "extents": extents, "end": [end.terminal, end.acknowledged,
    list(end.verified)], "pid": os.getpid()})
"""

HOLDER = r"""
workspace, publisher, acceptance = attach()
replay = r.open_replay(publisher, acceptance, operation=s.new_operation())
item = replay.next(2, operation=s.new_operation())
barrier("holding")
hold()
"""


@pytest.fixture(autouse=True)
def arrow_free(monkeypatch):
    probe.arrow_free(monkeypatch)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(
        tmp_path_factory.mktemp("s13-process") / "small", entry="bundle"
    )


def saved(tmp_path, built, sizes, *, register=True):
    """Parent capture (and registration); children open, accept and claim."""
    template, compiled = built
    workspace, job, publisher, binding, _record, generation = probe.store(
        tmp_path / "workspace", template
    )
    probe.capture(workspace, publisher, generation, binding, sizes)
    acceptance = probe.accept(workspace, job, generation, compiled)
    if register:
        r.register_consumer(publisher, acceptance, operation=op())
    config = probe.child_config(
        workspace,
        job,
        generation,
        compiled,
        {
            "consumer": acceptance.consumer,
            "checkpoint": acceptance.checkpoint,
            "extent": acceptance.extent,
            "scope": acceptance.scope,
        },
    )
    publisher.close()
    workspace.close()
    return config


def last(stdout):
    return json.loads(stdout.strip().splitlines()[-1])


def reopen(config):
    return w.open_workspace(config["workspace"], expected_identity=config["identity"])


def resumed(workspace, config, compiled, *, register=False):
    """A fresh acceptance and publisher in this process; drain to the end."""
    publisher = s.claim_publisher(workspace, config["job"], operation=op())
    try:
        acceptance = probe.accept(
            workspace,
            config["job"],
            config["generation"],
            compiled,
            consumer=config["consumer"],
        )
        if register:
            r.register_consumer(publisher, acceptance, operation=op())
        replay = r.open_replay(publisher, acceptance, operation=op())
        start = replay.position
        extents, end = probe.drain(replay, 2)
        replay.close()
        return start, extents, end
    finally:
        publisher.close()


@pytest.mark.parametrize(
    "cut",
    [
        "C1a_register_before_commit",
        "C1b_register_before_reply",
        "C2_session_without_offer",
        "C3_issued_before_seen",
        "C4_handed_off_before_ack",
        "C5_ack_before_commit",
        "C6_ack_before_reply",
        "C7_acknowledged_before_end",
    ],
)
def test_sigkill_cursor_cuts_recover_the_durable_position(tmp_path, built, cut):
    if not qualified(tmp_path):
        return
    config = saved(tmp_path, built, (2, 2), register=False)
    operation = op()
    process = probe.child(CUT, {**config, "cut": cut, "operation": operation})
    try:
        until(process, "cut")
    finally:
        code, _stderr = kill(process)
    assert code == -9
    workspace = reopen(config)
    try:
        found = s.query_operation(workspace, operation)
        if cut == "C1a_register_before_commit":
            assert found is None
            with pytest.raises(JobStoreError, match="CONSUMER_UNKNOWN"):
                r.consumer_state(workspace, config["consumer"])
            assert verify_store(workspace)["retentions"] == 0
            start, extents, end = resumed(workspace, config, built[1], register=True)
            assert (start, extents, end.acknowledged) == (0, [(0, 2), (2, 4)], 4)
            return
        state = r.consumer_state(workspace, config["consumer"])
        expected = {
            "C1b_register_before_reply": ("register_consumer", 0, 0, ()),
            "C2_session_without_offer": (None, 0, 1, ()),
            "C3_issued_before_seen": ("issue_delivery", 0, 1, ((0, 2, False),)),
            "C4_handed_off_before_ack": ("issue_delivery", 0, 1, ((0, 2, False),)),
            "C5_ack_before_commit": (None, 0, 1, ((0, 2, False),)),
            "C6_ack_before_reply": ("acknowledge_delivery", 2, 1, ((0, 2, True),)),
            "C7_acknowledged_before_end": (
                "issue_delivery",
                4,
                1,
                ((0, 2, True), (2, 4, True)),
            ),
        }[cut]
        assert (None if found is None else found.kind) == expected[0]
        assert (state.position, len(state.sessions)) == expected[1:3]
        assert tuple(i[2:] for i in state.issued) == expected[3]
        verify_store(workspace)
        # The dead publisher's lock is gone; a fresh process-local acceptance resumes.
        start, extents, end = resumed(workspace, config, built[1])
        assert start == state.position
        assert end.acknowledged == 4 and end.verified == (start, 4)
        assert extents == [(p, p + 2) for p in range(start, 4, 2)]
        after = r.consumer_state(workspace, config["consumer"])
        assert after.acknowledged == ((0, 2), (2, 4))
        assert len(after.sessions) == len(state.sessions) + 1
        verify_store(workspace)
    finally:
        workspace.close()


def test_required_example_after_a_real_death_resumes_at_two(tmp_path, built):
    if not qualified(tmp_path):
        return
    config = saved(tmp_path, built, (2, 2, 2, 1))
    assert config["extent"] == 7
    first = probe.child(SESSION_A, config)
    try:
        until(first, "offered")
    finally:
        code, _stderr = kill(first)
    assert code == -9
    resumed_b = last(finish(probe.child(RESUME, {**config, "rows": 3})))
    assert resumed_b["start"] == 2
    assert resumed_b["extents"] == [[2, 5], [5, 7]]
    assert resumed_b["end"] == ["SAVED_SCOPE_EXHAUSTED", 7, [2, 7]]
    workspace = reopen(config)
    try:
        state = r.consumer_state(workspace, config["consumer"])
        assert state.acknowledged == ((0, 2), (2, 5), (5, 7))
        assert [i[2:] for i in state.issued] == [
            (0, 2, True),
            (2, 4, False),
            (2, 5, True),
            (5, 7, True),
        ]
        assert [ss[1:] for ss in state.sessions] == [(1, 0), (2, 2)]
        summary = verify_store(workspace)
        assert (summary["sessions"], summary["acknowledgements"]) == (2, 3)
    finally:
        workspace.close()


def test_acknowledgement_committed_before_its_reply_is_found_by_query(tmp_path, built):
    if not qualified(tmp_path):
        return
    config = saved(tmp_path, built, (2, 2, 2, 1))
    operation = op()
    process = probe.child(LOST_REPLY, {**config, "operation": operation})
    try:
        until(process, "cut")
    finally:
        code, _stderr = kill(process)
    assert code == -9
    workspace = reopen(config)
    try:
        found = s.query_operation(workspace, operation)
        assert found is not None and found.observation == "QUERIED"
        assert (found.kind, found.get("position")) == ("acknowledge_delivery", 4)
        assert r.consumer_state(workspace, config["consumer"]).position == 4
    finally:
        workspace.close()
    after = last(finish(probe.child(RESUME, {**config, "rows": 3})))
    assert (after["start"], after["extents"]) == (4, [[4, 7]])
    workspace = reopen(config)
    try:
        assert r.consumer_state(workspace, config["consumer"]).acknowledged == (
            (0, 2),
            (2, 4),
            (4, 7),
        )
        verify_store(workspace)
    finally:
        workspace.close()


def test_a_live_holder_excludes_other_processes_until_it_dies(tmp_path, built):
    if not qualified(tmp_path):
        return
    config = saved(tmp_path, built, (2, 2))
    holder = probe.child(HOLDER, config)
    try:
        until(holder, "holding")
        workspace = reopen(config)
        try:
            with pytest.raises(JobStoreError, match="PUBLISHER_BUSY"):
                s.claim_publisher(workspace, config["job"], operation=op())
            # Observations stay available to other processes meanwhile.
            state = r.consumer_state(workspace, config["consumer"])
            assert [i[2:] for i in state.issued] == [(0, 2, False)]
        finally:
            workspace.close()
    finally:
        code, _stderr = kill(holder)
    assert code == -9
    after = last(finish(probe.child(RESUME, {**config, "rows": 2})))
    assert (after["start"], after["extents"]) == (0, [[0, 2], [2, 4]])
    workspace = reopen(config)
    try:
        state = r.consumer_state(workspace, config["consumer"])
        assert [ss[1] for ss in state.sessions] == [1, 2]
        assert [i[2:] for i in state.issued] == [
            (0, 2, False),
            (0, 2, True),
            (2, 4, True),
        ]
        verify_store(workspace)
    finally:
        workspace.close()
