"""S12 process histories: SIGKILL cuts, fresh readers, holes and the fork boundary.

Children are registered spawned interpreters that open their own workspace and
claim their own publisher; no live handle crosses a process boundary. SIGKILL
cuts are real process deaths at named protocol steps; they are not power-loss
certificates, and device/OS sync honesty stays an external premise.
"""

import json
from pathlib import Path

import pytest

import _pietto_phase68_slice12_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from _pietto_phase68_slice11_probe import finish, kill, until
from pietto._project import project_job_capture as c
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store

op = probe.op
BATCHES = [[[2, None], [5, 50]], [[9, None], [9, -9]], [[7, 1], [8, 2]]]

CUT = r"""
workspace, publisher, attempt, owner = attach()
session = c.begin_capture(publisher, attempt, owner, operation=s.new_operation())
first = probe.stage_frame(session, 2)
session.publish(first, operation=s.new_operation())
barrier("prior")
cut, real_sync, real_commit = config["cut"], k._sync, w.commit
if cut == "K1_partial_write":
    def partial(fd, data):
        os.write(fd, data[: len(data) // 2])
        barrier("cut")
        hold()
    k._write_all = partial
elif cut == "K2_complete_before_file_fsync":
    def sync(fd):
        barrier("cut")
        hold()
    k._sync = sync
elif cut == "K3_file_fsync_before_link":
    def link(*args):
        barrier("cut")
        hold()
    k._link = link
elif cut == "K4_durable_orphan_before_metadata":
    def write(workspace, body):
        barrier("cut")
        hold()
    s.write = write
elif cut == "K5_inserted_before_commit":
    def commit(connection):
        barrier("cut")
        hold()
    w.commit = commit
elif cut == "K6_committed_before_reply":
    def commit(connection):
        real_commit(connection)
        barrier("cut")
        hold()
    w.commit = commit
staged = probe.stage_frame(session, 2)
session.publish(staged, operation=config["operation"])
barrier("cut")
hold()
"""

READER = r"""
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
snapshot = c.checkpoint_snapshot(workspace, config["job"], config["generation"])
workspace.close()
sys.stdout.write(json.dumps({"frontier": snapshot.frontier,
    "committed": snapshot.committed, "holes": snapshot.holes,
    "observed_end": snapshot.observed_end, "ordinal": snapshot.ordinal,
    "layers": dict(snapshot.layers), "pid": os.getpid()}) + "\n")
"""

HOLE = r"""
workspace, publisher, attempt, owner = attach()
session = c.begin_capture(publisher, attempt, owner, operation=s.new_operation())
a, b, d = (probe.stage_frame(session, 2) for _ in range(3))
session.publish(a, operation=s.new_operation())
session.publish(d, operation=s.new_operation())
barrier("hole")
deadline = time.monotonic() + 60
while not os.path.exists(config["go"]):
    if time.monotonic() > deadline:
        raise SystemExit(3)
    time.sleep(0.05)
result = session.publish(b, operation=s.new_operation())
owner.close()
session.end(operation=s.new_operation())
s.record_attempt(publisher, attempt, owner, operation=s.new_operation())
publisher.close()
workspace.close()
barrier("closed " + str(result.get("frontier")))
"""

# The fork happens inside a registered single-threaded child, never in pytest.
FORK = r"""
workspace, publisher, attempt, owner = attach()
session = c.begin_capture(publisher, attempt, owner, operation=s.new_operation())
staged = probe.stage_frame(session, 2)
read, write = os.pipe()
pid = os.fork()
if pid == 0:
    os.close(read)
    observed = []
    for call in (session.stage, lambda: session.publish(staged, operation="op-" + "0" * 32),
            publisher.use, workspace.use):
        try:
            call()
            observed.append("ACCEPTED")
        except w.JobStoreError as error:
            observed.append(str(error))
    os.write(write, json.dumps(observed).encode())
    os._exit(0)
os.close(write)
with os.fdopen(read, "rb") as stream:
    inherited = json.loads(stream.read())
status = os.waitpid(pid, 0)[1]
frontier = session.publish(staged, operation=s.new_operation()).get("frontier")
publisher.close()
workspace.close()
sys.stdout.write(json.dumps({"inherited": inherited, "status": status,
    "frontier": frontier, "file": staged.name}) + "\n")
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(
        tmp_path_factory.mktemp("s12-process") / "small", entry="bundle"
    )


def registered(tmp_path, built):
    """Parent registration only; the child opens, loads and claims for itself."""
    template, compiled = built
    workspace, job, publisher, _binding, record, generation = probe.store(
        tmp_path / "workspace", template, (1,)
    )
    publisher.close()
    config = probe.child_config(
        workspace, job, record, generation, compiled, BATCHES, probe.SMALL_CODES
    )
    workspace.close()
    return config


@pytest.mark.parametrize(
    "cut",
    [
        "K1_partial_write",
        "K2_complete_before_file_fsync",
        "K3_file_fsync_before_link",
        "K4_durable_orphan_before_metadata",
        "K5_inserted_before_commit",
        "K6_committed_before_reply",
        "K7_reply_delivered",
    ],
)
def test_sigkill_cuts_preserve_every_acknowledged_checkpoint(tmp_path, built, cut):
    if not qualified(tmp_path):
        return
    config = registered(tmp_path, built)
    operation = op()
    process = probe.child(CUT, {**config, "cut": cut, "operation": operation})
    try:
        until(process, "prior")
        until(process, "cut")
    finally:
        code, _stderr = kill(process)
    assert code == -9
    workspace = w.open_workspace(
        config["workspace"], expected_identity=config["identity"]
    )
    try:
        snapshot = c.checkpoint_snapshot(workspace, config["job"], config["generation"])
        committed = cut in ("K6_committed_before_reply", "K7_reply_delivered")
        assert snapshot.committed == (((0, 2), (2, 4)) if committed else ((0, 2),))
        assert snapshot.frontier == (4 if committed else 2)
        files = c.classify_files(workspace)
        staging = cut.startswith(("K1", "K2", "K3"))
        orphan = cut.startswith(("K4", "K5"))
        assert len(files["referenced"]) == (2 if committed else 1)
        assert len(files["staging"]) == (1 if staging else 0)
        assert len(files["orphans"]) == (1 if orphan else 0)
        assert files["missing"] == files["foreign"] == ()
        found = s.query_operation(workspace, operation)
        assert (found is not None) is committed
        if found is not None:
            assert found.get("frontier") == 4 and found.get("ordinal") == 2
        verify_store(workspace)
        # The dead publisher's lock is gone; a later epoch closes its attempt.
        publisher = s.claim_publisher(workspace, config["job"], operation=op())
        s.interrupt_attempt(publisher, snapshot.attempt, operation=op())
        layers = dict(
            c.checkpoint_snapshot(workspace, config["job"], config["generation"]).layers
        )
        assert layers["attempt_terminal"] == "INTERRUPTED"
        assert {layers[n] for n in ("source", "transaction", "delivery")} == {"UNKNOWN"}
        publisher.close()
        # Opening never adopted the stray file and never repaired anything.
        assert c.classify_files(workspace) == files
        verify_store(workspace)
    finally:
        workspace.close()


def test_fresh_reader_sees_the_hole_until_the_owner_closes_it(tmp_path, built):
    if not qualified(tmp_path):
        return
    config = registered(tmp_path, built)
    go = tmp_path / "go"
    holder = probe.child(HOLE, {**config, "go": str(go)})
    try:
        until(holder, "hole")
        early = json.loads(finish(probe.child(READER, config)))
        assert early["committed"] == [[0, 2], [4, 6]]
        assert (early["frontier"], early["holes"], early["ordinal"]) == (2, [[2, 4]], 2)
        assert early["observed_end"] is None and early["pid"] != holder.pid
        go.touch()
        until(holder, "closed 6")
        assert holder.wait(timeout=60) == 0
    finally:
        if holder.poll() is None:
            kill(holder)
    late = json.loads(finish(probe.child(READER, config)))
    assert late["committed"] == [[0, 2], [2, 4], [4, 6]]
    assert (late["frontier"], late["holes"], late["observed_end"]) == (6, [], 6)
    assert late["layers"]["attempt_terminal"] == "OUTCOME"
    assert late["layers"]["source"] == "EARLY_CLOSE"
    workspace = w.open_workspace(
        config["workspace"], expected_identity=config["identity"]
    )
    try:
        assert verify_store(workspace)["checkpoints"] == 3
    finally:
        workspace.close()


def test_inherited_session_refuses_in_a_forked_child(tmp_path, built):
    if not qualified(tmp_path):
        return
    config = registered(tmp_path, built)
    observed = json.loads(finish(probe.child(FORK, config)))
    assert observed["inherited"] == [
        "CAPTURE_FOREIGN_PROCESS",
        "CAPTURE_FOREIGN_PROCESS",
        "PUBLISHER_FOREIGN_PROCESS",
        "WORKSPACE_FOREIGN_PROCESS",
    ]
    assert observed["status"] == 0 and observed["frontier"] == 2
    workspace = w.open_workspace(
        config["workspace"], expected_identity=config["identity"]
    )
    try:
        assert Path(config["workspace"], "chunks", observed["file"]).exists()
        verify_store(workspace)
    finally:
        workspace.close()
