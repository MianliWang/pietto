"""S16 process histories: real SIGKILL cuts around preparation, validation, the
publication transaction and its reply; notification loss after a successful
return; independent snapshots; both publish/cancel orderings across processes.

Children are spawned interpreters that open their own workspace, claim their
own publisher and take their own fresh acceptances; no live handle crosses a
process boundary. Saved inputs use the labelled Arrow-free storage step and the
closing owner is SYNTHETIC_CLOSED_OWNER (see the probe); the member check is
ARROW_FREE_MEMBER_CHECK. SIGKILL cuts are real process deaths at named
protocol steps, not power-loss certificates.
"""

import json

import pytest

import _pietto_phase68_slice16_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from _pietto_phase68_slice11_probe import finish, kill, until
from pietto._project import project_job_capture as c
from pietto._project import project_job_publication as p
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store

op = probe.op

CUT = r"""
workspace, publisher = attach()
cut, real_commit = config["cut"], w.commit
def stop(*args, **kwargs):
    barrier("cut")
    hold()
def stop_after(connection):
    real_commit(connection)
    barrier("cut")
    hold()
if cut == "P1_preparation_protected":
    p._verify = stop
prepared = p.prepare_publication(publisher, acceptance(workspace),
    operation=config["prepare"])
if cut == "P2_validated_not_published":
    stop()
if cut == "P3_inserted_before_commit":
    w.commit = stop
if cut == "P4_committed_before_response":
    w.commit = stop_after
p.publish_generation(publisher, prepared, operation=config["operation"])
barrier("returned")
hold()
"""

RESUME = r"""
workspace, publisher = attach()
try:
    prepared = p.prepare_publication(publisher, acceptance(workspace),
        operation=s.new_operation())
    result = p.publish_generation(publisher, prepared, operation=s.new_operation())
    emit({"observation": result.observation})
except w.JobStoreError as error:
    emit({"refused": str(error)})
"""

NOTIFY = r"""
workspace, publisher = attach()
prepared = p.prepare_publication(publisher, acceptance(workspace),
    operation=s.new_operation())
result = p.publish_generation(publisher, prepared, operation=config["operation"])
barrier("returned")
while not os.path.exists(config["go"]):
    time.sleep(0.05)
outcome = {"observation": result.observation}
try:
    sys.stdout.write("NOTIFY " + config["operation"] + "\n")
    sys.stdout.flush()
    outcome["notification"] = "WRITTEN"
except BrokenPipeError:
    outcome["notification"] = "BrokenPipeError"
with open(config["outcome"], "x") as stream:
    json.dump(outcome, stream)
os._exit(0)
"""

READER = r"""
workspace, _none = attach(claim=False)
connection = workspace.use()
connection.execute("BEGIN")
before = connection.execute("SELECT count(*) FROM publication").fetchone()[0]
barrier("snapshot")
while not os.path.exists(config["go"]):
    time.sleep(0.05)
held = connection.execute("SELECT count(*) FROM publication").fetchone()[0]
connection.execute("COMMIT")
found = p.publication(workspace, config["job"], config["generation"])
protected = sorted(c.protected_chunks(workspace, config["job"]))
emit({"before": before, "held": held, "fresh": None if found is None else
    [found.checkpoint, found.extent, found.members, found.retention, found.operation],
    "protected": protected})
"""

HOLDER = r"""
workspace, publisher = attach()
prepared = p.prepare_publication(publisher, acceptance(workspace),
    operation=s.new_operation())
with open(config["held"], "x") as stream:
    json.dump({"retention": prepared.retention, "epoch": publisher.epoch}, stream)
barrier("prepared")
hold()
"""

CLAIM = r"""
workspace, _none = attach(claim=False)
try:
    publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
except w.JobStoreError as error:
    emit({"claim": str(error)})
else:
    if config.get("cancel"):
        s.cancel_job(publisher, operation=s.new_operation())
    emit({"claim": "CLAIMED", "epoch": publisher.epoch})
"""

PUBLISH = r"""
workspace, publisher = attach()
prepared = p.prepare_publication(publisher, acceptance(workspace),
    operation=s.new_operation())
result = p.publish_generation(publisher, prepared, operation=config["operation"])
emit({"observation": result.observation, "retention": prepared.retention})
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(
        tmp_path_factory.mktemp("s16-process") / "small", entry="bundle"
    )


def ready(tmp_path, built):
    """A v6 store whose generation is complete and closed (not yet published);
    the parent then releases its own publisher and handle."""
    template, compiled = built
    workspace, job, publisher, binding, record, generation = probe.store(
        tmp_path / "workspace", template
    )
    session = probe.ordinary(publisher, generation, binding, [2, 2, 1])
    checkpoint = c.checkpoint_snapshot(workspace, job, generation).checkpoint
    config = probe.child_config(
        workspace, job, generation, compiled, session.attempt.identity, checkpoint
    )
    publisher.close()
    workspace.close()
    return config


def fresh(config):
    return w.open_workspace(config["workspace"], expected_identity=config["identity"])


def last(stdout):
    return json.loads(stdout.strip().splitlines()[-1])


CUTS = (
    "P1_preparation_protected",
    "P2_validated_not_published",
    "P3_inserted_before_commit",
    "P4_committed_before_response",
)


@pytest.mark.parametrize("cut", CUTS)
def test_sigkill_cuts_leave_zero_or_one_complete_publication(tmp_path, built, cut):
    if not qualified(tmp_path):
        return
    config = ready(tmp_path, built)
    config.update(cut=cut, prepare=op(), operation=op())
    process = probe.child(CUT, config)
    try:
        until(process, "cut")
    finally:
        code, _stderr = kill(process)
    assert code == -9
    workspace = fresh(config)
    try:
        found = p.publication(workspace, config["job"], config["generation"])
        queried = s.query_operation(workspace, config["operation"])
        committed = cut == "P4_committed_before_response"
        # Zero or one complete record: never a partial reference, never an ACK.
        assert (found is not None) is committed and (queried is not None) is committed
        preparation = s.query_operation(workspace, config["prepare"])
        assert preparation is not None and preparation.kind == "retain_checkpoint"
        retention = preparation.get("retention")
        assert not probe.rows(
            workspace,
            "SELECT 1 FROM retention_release WHERE retention = ?",
            (retention,),
        )
        if committed:
            assert found is not None and found.retention == retention
            assert queried is not None and queried.kind == "publish_generation"
        verify_store(workspace)
    finally:
        workspace.close()
    # A fresh process (fresh acceptance) completes the publication only once.
    result = last(finish(probe.child(RESUME, config)))
    workspace = fresh(config)
    try:
        listed = p.publications(workspace, config["job"])
        assert len(listed) == 1
        if cut == "P4_committed_before_response":
            assert result == {"refused": "GENERATION_PUBLISHED"}
            assert listed[0].operation == config["operation"]
        else:
            assert result == {"observation": "COMMITTED_THIS_CALL"}
        verify_store(workspace)
    finally:
        workspace.close()


def test_notification_loss_after_return_is_outside_the_commit(tmp_path, built):
    if not qualified(tmp_path):
        return
    config = ready(tmp_path, built)
    config.update(
        operation=op(),
        go=str(tmp_path / "go"),
        outcome=str(tmp_path / "outcome.json"),
    )
    process = probe.child(NOTIFY, config)
    try:
        until(process, "returned")
        # The caller-facing channel is gone before the message is written.
        assert process.stdout is not None
        process.stdout.close()
        open(config["go"], "x").close()
        process.wait(timeout=120)
    finally:
        if process.poll() is None:
            kill(process)
    assert process.returncode == 0
    outcome = json.loads(open(config["outcome"]).read())
    assert outcome == {
        "observation": "COMMITTED_THIS_CALL",
        "notification": "BrokenPipeError",
    }
    workspace = fresh(config)
    try:
        # One original publication and operation; no source query was rerun.
        (found,) = p.publications(workspace, config["job"])
        assert found.operation == config["operation"]
        queried = s.query_operation(workspace, config["operation"])
        assert queried is not None and queried.get("generation") == config["generation"]
        verify_store(workspace)
    finally:
        workspace.close()


def test_old_snapshot_sees_nothing_and_a_fresh_one_sees_everything(
    tmp_path, built, monkeypatch
):
    if not qualified(tmp_path):
        return
    probe.arrow_free(monkeypatch)
    config = ready(tmp_path, built)
    config.update(go=str(tmp_path / "go"))
    workspace = fresh(config)
    publisher = s.claim_publisher(workspace, config["job"], operation=op())
    reader = probe.child(READER, config)
    try:
        acceptance = p.accept_publication(
            workspace,
            config["job"],
            config["generation"],
            checkpoint=config["checkpoint"],
            closing=config["closing"],
            purpose="s16-parent",
            route="postgres_rows",
            isolation="stable",
            values=(1,),
            seconds=600,
            expected_pin=config["pin"],
            accepted_producer=config["producer"],
            accepted_compatibility=tuple(config["compatibility"]),
        )
        prepared = p.prepare_publication(publisher, acceptance, operation=op())
        until(reader, "snapshot")
        operation = op()
        p.publish_generation(publisher, prepared, operation=operation)
        open(config["go"], "x").close()
        seen = last(finish(reader))
    finally:
        if reader.poll() is None:
            kill(reader)
        publisher.close()
    try:
        found = p.publication(workspace, config["job"], config["generation"])
        assert found is not None
        # The held snapshot keeps its older view; a fresh one sees the whole record.
        assert (seen["before"], seen["held"]) == (0, 0)
        assert seen["fresh"] == [
            found.checkpoint,
            found.extent,
            found.members,
            found.retention,
            operation,
        ]
        members = {
            m.chunk
            for m in c.checkpoint_snapshot(
                workspace, config["job"], config["generation"]
            ).members
        }
        assert members <= set(seen["protected"])
    finally:
        workspace.close()


def test_cancel_before_publish_across_processes(tmp_path, built):
    if not qualified(tmp_path):
        return
    config = ready(tmp_path, built)
    config.update(held=str(tmp_path / "held.json"))
    holder = probe.child(HOLDER, config)
    try:
        until(holder, "prepared")
        held = json.loads(open(config["held"]).read())
        # A second writer gets the real rejection while the first holds the job.
        busy = last(finish(probe.child(CLAIM, config)))
        assert busy == {"claim": "PUBLISHER_BUSY"}
    finally:
        code, _stderr = kill(holder)
    assert code == -9
    # The holder died after preparing; a new publisher cancels first.
    cancelled = last(finish(probe.child(CLAIM, {**config, "cancel": True})))
    assert cancelled["claim"] == "CLAIMED" and cancelled["epoch"] == held["epoch"] + 1
    refused = last(finish(probe.child(RESUME, config)))
    assert refused == {"refused": "JOB_STATE"}
    workspace = fresh(config)
    try:
        assert p.publication(workspace, config["job"], config["generation"]) is None
        assert s.job_record(workspace, config["job"]).state == "CANCELLED"
        # The dead holder's preparation stays protected (never guessed released).
        assert not probe.rows(
            workspace,
            "SELECT 1 FROM retention_release WHERE retention = ?",
            (held["retention"],),
        )
        verify_store(workspace)
    finally:
        workspace.close()


def test_publish_before_cancel_across_processes(tmp_path, built):
    if not qualified(tmp_path):
        return
    config = ready(tmp_path, built)
    config.update(operation=op())
    published = last(finish(probe.child(PUBLISH, config)))
    assert published["observation"] == "COMMITTED_THIS_CALL"
    cancelled = last(finish(probe.child(CLAIM, {**config, "cancel": True})))
    assert cancelled["claim"] == "CLAIMED"
    workspace = fresh(config)
    try:
        found = p.publication(workspace, config["job"], config["generation"])
        assert found is not None and found.operation == config["operation"]
        assert found.retention == published["retention"]
        assert s.job_record(workspace, config["job"]).state == "CANCELLED"
        publisher = s.claim_publisher(workspace, config["job"], operation=op())
        try:
            with pytest.raises(w.JobStoreError, match="RETENTION_PUBLISHED"):
                c.release_retention(publisher, found.retention, operation=op())
        finally:
            publisher.close()
        assert {
            m.chunk
            for m in c.checkpoint_snapshot(
                workspace, config["job"], config["generation"]
            ).members
        } <= c.protected_chunks(workspace, config["job"])
        verify_store(workspace)
    finally:
        workspace.close()
