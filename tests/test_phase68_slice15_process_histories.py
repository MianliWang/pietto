"""S15 process histories: real SIGKILL cuts around issuance, the sink's own
commit, the reply, the local receipt and the S13 acknowledgement; query after
loss; concurrent duplicate and conflicting submissions in two processes.

Children are registered spawned interpreters that open their own workspace and
sink, claim their own publisher and take their own fresh acceptances; no live
handle crosses a process boundary. Saved inputs use S12's Arrow-free storage
step, reads S13's ARROW_FREE_REPLAY_STEP and rows ARROW_FREE_PAYLOAD_STEP. The
sink effects are real SQLite rows in the sink's own database. SIGKILL cuts are
real process deaths at named protocol steps, not power-loss certificates.
"""

import json
import time

import pytest

import _pietto_phase68_slice13_probe as s13
import _pietto_phase68_slice15_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from _pietto_phase68_slice11_probe import finish, kill, until
from pietto._project import project_job_delivery as d
from pietto._project import project_job_replay as r
from pietto._project import project_job_sink as k
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store

op = probe.op

CUT = r"""
workspace, publisher, handle, sink, read = attach()
cut, real_commit, sink_commit = config["cut"], w.commit, k.commit
def stop_before(connection):
    barrier("cut")
    hold()
def stop_after(connection):
    real_commit(connection)
    barrier("cut")
    hold()
def sink_before(connection):
    barrier("cut")
    hold()
def sink_after(connection):
    sink_commit(connection)
    barrier("cut")
    hold()
session = d.open_stream(publisher, config["stream"], sink, window=read,
    operation=s.new_operation())
receipt = cut in ("K7_receipt_before_commit", "K8_receipt_after_commit")
issue = s.new_operation() if receipt else config["operation"]
if cut in ("K1_issue_before_commit", "K2_issue_after_commit"):
    w.commit = stop_before if cut == "K1_issue_before_commit" else stop_after
item = session.next(2, operation=issue)
if cut == "K3_issued_before_send":
    barrier("cut")
    hold()
if cut in ("K4_sink_before_commit", "K5_sink_after_commit"):
    k.commit = sink_before if cut == "K4_sink_before_commit" else sink_after
session.send(item)
if cut == "K6_reply_before_receipt":
    barrier("cut")
    hold()
w.commit = stop_before if cut == "K7_receipt_before_commit" else stop_after
session.confirm(item, operation=config["operation"])
"""

BRIDGE_CUT = r"""
workspace, publisher, handle, sink, read = attach(window=False)
acceptance = r.accept_saved_read(workspace, config["job"], config["generation"],
    checkpoint=config["checkpoint"], consumer=config["consumer"],
    scope="complete_capture", extent=config["extent"], purpose="s13-read",
    route="postgres_rows", values=tuple(config["values"]), expected_pin=config["pin"],
    accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]), seconds=600, batch_rows=4096)
session = d.open_stream(publisher, config["stream"], sink, operation=s.new_operation())
replay = r.open_replay(publisher, acceptance, operation=s.new_operation())
item = session.bridge(replay.next(2, operation=s.new_operation()),
    operation=s.new_operation())
session.send(item)
session.confirm(item, operation=config["operation"])
barrier("cut")
hold()
"""

RESUME = r"""
workspace, publisher, handle, sink, read = attach()
session = d.open_stream(publisher, config["stream"], sink, window=read,
    operation=s.new_operation())
start = session.position
extents, waiting = probe.deliver(session, config["rows"])
emit({"start": start, "extents": [list(e[:2]) + [list(e[2])] for e in extents],
    "position": waiting.position, "pid": os.getpid()})
"""

RESUME_BRIDGE = r"""
workspace, publisher, handle, sink, read = attach(window=False)
acceptance = r.accept_saved_read(workspace, config["job"], config["generation"],
    checkpoint=config["checkpoint"], consumer=config["consumer"],
    scope="complete_capture", extent=config["extent"], purpose="s13-read",
    route="postgres_rows", values=tuple(config["values"]), expected_pin=config["pin"],
    accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]), seconds=600, batch_rows=4096)
session = d.open_stream(publisher, config["stream"], sink, operation=s.new_operation())
replay = r.open_replay(publisher, acceptance, operation=s.new_operation())
steps = []
while True:
    item = replay.next(2, operation=s.new_operation())
    if isinstance(item, r.SavedScopeEnd):
        break
    issued = session.bridge(item, operation=s.new_operation())
    statuses = session.send(issued)
    if statuses:
        session.confirm(issued, operation=s.new_operation())
    session.acknowledge(issued, operation=s.new_operation())
    steps.append([issued.start, issued.stop, sorted(statuses.values())])
emit({"steps": steps, "acknowledged": item.acknowledged, "pid": os.getpid()})
"""

SUBMIT = r"""
handle = k.open_sink(config["sink"], expected_identity=config["sink_identity"])
item = k.SinkEffect(handle.identity, handle.namespace, handle.epoch, handle.retention,
    config["identity"], config["generation"], config["position"], config["layout"],
    config["payload"])
if config.get("hold"):
    real = k.commit
    def held(connection):
        barrier("holding")
        while not os.path.exists(config["go"]):
            time.sleep(0.01)
        real(connection)
    k.commit = held
else:
    barrier("submitting")
reply = handle.submit(item)
emit({"status": reply.status, "commit": reply.commit, "sequence": reply.sequence,
    "pid": os.getpid()})
"""

CUTS = (
    "K1_issue_before_commit",
    "K2_issue_after_commit",
    "K3_issued_before_send",
    "K4_sink_before_commit",
    "K5_sink_after_commit",
    "K6_reply_before_receipt",
    "K7_receipt_before_commit",
    "K8_receipt_after_commit",
)


@pytest.fixture(autouse=True)
def arrow_free(monkeypatch):
    probe.arrow_free(monkeypatch)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(
        tmp_path_factory.mktemp("s15-process") / "small", entry="bundle"
    )


def saved(tmp_path, built, sizes, *, consumer=False):
    """Parent capture, stream registration and first window; children attach."""
    template, compiled = built
    workspace, job, publisher, binding, _record, generation = probe.store(
        tmp_path / "workspace", template
    )
    probe.capture(workspace, publisher, generation, binding, sizes)
    handle = probe.sink(tmp_path / "sink")
    stream, session = probe.registered(
        workspace, job, publisher, generation, compiled, handle
    )
    extra = {"stream": stream}
    if consumer:
        acceptance = s13.accept(workspace, job, generation, compiled)
        r.register_consumer(publisher, acceptance, operation=op())
        extra.update(
            consumer=acceptance.consumer,
            checkpoint=acceptance.checkpoint,
            extent=acceptance.extent,
        )
    config = probe.child_config(workspace, job, generation, compiled, handle, **extra)
    config["layout"] = session.facts.layout
    session.close()
    handle.close()
    publisher.close()
    workspace.close()
    return config


def last(stdout):
    return json.loads(stdout.strip().splitlines()[-1])


def observed(config):
    """Fresh handles: durable operation/stream facts and the sink's real rows."""
    workspace = w.open_workspace(
        config["workspace"], expected_identity=config["identity"]
    )
    handle = k.open_sink(config["sink"], expected_identity=config["sink_identity"])
    try:
        found = s.query_operation(workspace, config["operation"])
        state = d.stream_state(workspace, config["stream"])
        verify_store(workspace)
        return found, state, probe.effects(handle)
    finally:
        handle.close()
        workspace.close()


def run(program, config, seconds=120):
    return last(finish(probe.child(program, config), seconds))


@pytest.mark.parametrize("cut", CUTS)
def test_sigkill_cuts_leave_zero_or_one_effect_and_resume(tmp_path, built, cut):
    if not qualified(tmp_path):
        return
    config = saved(tmp_path, built, (2, 2))
    config.update(cut=cut, operation=s.new_operation(), rows=2)
    process = probe.child(CUT, config)
    try:
        until(process, "cut")
    finally:
        code, _stderr = kill(process)
    assert code == -9
    found, state, effects = observed(config)
    issued = {
        "K1_issue_before_commit": 0,
    }.get(cut, 1)
    committed_effects = {
        "K1_issue_before_commit": [],
        "K2_issue_after_commit": [],
        "K3_issued_before_send": [],
        "K4_sink_before_commit": [],
        "K5_sink_after_commit": [0],
    }.get(cut, [0, 1])
    confirmed = [(0, 2)] if cut == "K8_receipt_after_commit" else []
    assert len(state.issuances) == issued
    assert [row[0] for row in effects] == committed_effects
    assert list(state.observed) == confirmed
    # The caller's operation is queryable exactly when its COMMIT happened.
    expected = cut in (
        "K2_issue_after_commit",
        "K3_issued_before_send",
        "K4_sink_before_commit",
        "K5_sink_after_commit",
        "K6_reply_before_receipt",
        "K8_receipt_after_commit",
    )
    assert (found is not None) is expected
    if found is not None:
        assert found.kind == (
            "confirm_sink" if cut == "K8_receipt_after_commit" else "issue_stream"
        )
    result = run(RESUME, config)
    start = 2 if cut == "K8_receipt_after_commit" else 0
    assert result["start"] == start and result["position"] == 4
    # Prior unknown sends are reconciled by query; absent ones are resubmitted
    # once with the same key and payload; nothing is rekeyed.
    resumed = {
        "K5_sink_after_commit": ["COMMITTED", "PRESENT_MATCHING"],
        "K6_reply_before_receipt": ["PRESENT_MATCHING", "PRESENT_MATCHING"],
        "K7_receipt_before_commit": ["PRESENT_MATCHING", "PRESENT_MATCHING"],
    }.get(cut, ["COMMITTED", "COMMITTED"])
    assert result["extents"][0] == [start, start + 2, resumed]
    found, state, effects = observed(config)
    assert [row[0] for row in effects] == [0, 1, 2, 3]
    assert len({row[2] for row in effects}) == 4  # one commit per occurrence
    assert (state.position, state.observed, state.unresolved) == (4, ((0, 4),), ())


def test_sigkill_after_sink_confirmation_before_s13_acknowledgement(tmp_path, built):
    if not qualified(tmp_path):
        return
    config = saved(tmp_path, built, (2, 2), consumer=True)
    config["operation"] = s.new_operation()
    process = probe.child(BRIDGE_CUT, config)
    try:
        until(process, "cut")
    finally:
        code, _stderr = kill(process)
    assert code == -9
    found, state, effects = observed(config)
    assert found is not None and found.kind == "confirm_sink"
    assert state.observed == ((0, 2),) and [row[0] for row in effects] == [0, 1]
    workspace = w.open_workspace(
        config["workspace"], expected_identity=config["identity"]
    )
    try:
        # The S13 acknowledgement alone is never sink proof, and here it is absent.
        assert r.consumer_state(workspace, config["consumer"]).position == 0
    finally:
        workspace.close()
    result = run(RESUME_BRIDGE, config)
    # [0, 2) is redelivered; its occurrences are already confirmed, so nothing
    # is sent again before the original acknowledgement.
    assert result["steps"] == [[0, 2, []], [2, 4, ["COMMITTED", "COMMITTED"]]]
    assert result["acknowledged"] == 4
    found, state, effects = observed(config)
    assert [row[0] for row in effects] == [0, 1, 2, 3]
    assert state.position == 4


@pytest.mark.parametrize("variant", ["duplicate", "conflict"])
def test_two_processes_submitting_one_key_insert_it_once(tmp_path, built, variant):
    if not qualified(tmp_path):
        return
    config = saved(tmp_path, built, (2,))
    go = str(tmp_path / "go")
    first = probe.child(
        SUBMIT,
        {
            **config,
            "position": 0,
            "payload": probe.synthetic_row(0),
            "hold": True,
            "go": go,
        },
    )
    second = None
    try:
        until(first, "holding")
        payload = probe.synthetic_row(0, 0 if variant == "duplicate" else 1)
        second = probe.child(
            SUBMIT, {**config, "position": 0, "payload": payload, "hold": False}
        )
        until(second, "submitting")
        time.sleep(0.5)  # the second writer now waits on the sink's write lock
        with open(go, "w"):
            pass
        one, two = last(finish(first)), last(finish(second))
    finally:
        for process in (first, second):
            if process is not None and process.poll() is None:
                kill(process)
    assert one["status"] == "COMMITTED" and one["pid"] != two["pid"]
    # The late original and the resubmission converge through the key; a
    # different row for the same key is an explicit conflict, never a write.
    assert two["status"] == ("DUPLICATE" if variant == "duplicate" else "CONFLICT")
    assert (two["commit"], two["sequence"]) == (one["commit"], one["sequence"])
    handle = k.open_sink(config["sink"], expected_identity=config["sink_identity"])
    try:
        rows = probe.effects(handle)
        assert len(rows) == 1 and rows[0][2] == one["commit"]
        stored = handle.use().execute("SELECT payload FROM effect").fetchone()[0]
        assert stored == probe.synthetic_row(0)
    finally:
        handle.close()
