"""S14 process histories: real SIGKILL cuts around the R2 protocol steps.

Children are registered spawned interpreters that open their own workspace,
claim their own publisher, interrupt older open attempts and take their own fresh
recovery acceptance; no live handle or candidate file list crosses a process
boundary as authority. Steps use the labelled synthetic replacements of the
probe (no Arrow, no database). SIGKILL cuts are process deaths at named protocol
steps, not power-loss certificates.
"""

import json

import pytest

import _pietto_phase68_slice14_probe as probe
from _pietto_phase68_slice11_probe import kill, qualified, until
from pietto._project import project_job_capture as c
from pietto._project import project_job_extraction as x
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store

op = probe.op

INITIAL = r"""
workspace, binding = attach()
publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
attempt = s.open_attempt(publisher, config["generation"], binding,
    operation=s.new_operation())
session = x.begin_extraction(publisher, attempt, probe.owner(binding),
    operation=s.new_operation())
if config["cut"] != "K1_after_basis":
    staged = [probe.stage_refined(session, n) for n in (2, 2, 2)]
    for index in (0, 2):
        session.publish(staged[index], operation=s.new_operation())
barrier("cut")
hold()
"""

RECOVERY = r"""
from pathlib import Path
workspace, binding = attach()
cut, real_commit = config["cut"], w.commit
def stop_after(connection):
    real_commit(connection)
    barrier("cut")
    hold()
publisher, acceptance, attempt = probe.recover(workspace, config["job"],
    config["generation"], built(), tuple(config["values"]))
session = x.begin_continuation(publisher, acceptance, attempt,
    probe.owner(acceptance.binding, batch_rows=3), operation=s.new_operation())
first = probe.page(session, 3)
Path(config["facts"]).write_text(json.dumps({"attempt": attempt.identity,
    "candidates": [i.name for i in first]}))
if cut == "K2_candidates":
    barrier("cut")
    hold()
second = probe.page(session, 3)
session.reconcile(operation=s.new_operation())
if cut == "K3_after_barrier":
    barrier("cut")
    hold()
if cut == "K4_publish_reply_lost":
    w.commit = stop_after
    session.publish(first[0], operation=config["operation"])
for item in (*first, *second):
    session.publish(item, operation=s.new_operation())
probe.drive(session, [1])
if cut == "K5_second_crash":
    barrier("cut")
    hold()
probe.finish_stream(session)
w.commit = stop_after
session.end(operation=config["operation"])
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return probe.refined_template(tmp_path_factory.mktemp("s14-process") / "bound")


@pytest.fixture(autouse=True)
def synthetic(monkeypatch):
    probe.synthetic(monkeypatch)


def stored(tmp_path, built):
    template, compiled, values = built
    workspace, job, publisher, binding, record, generation = probe.store(
        tmp_path / "workspace", template, values
    )
    config = probe.child_config(
        workspace,
        job,
        record,
        generation,
        compiled,
        values,
        facts=str(tmp_path / "facts.json"),
    )
    publisher.close()
    workspace.close()
    return config, compiled, values


def cut(program, config, name, operation=None):
    process = probe.child(program, {**config, "cut": name, "operation": operation})
    try:
        until(process, "cut")
    finally:
        code, _stderr = kill(process)
    assert code == -9


def complete(config, compiled, values, sizes):
    """A later process: takeover, fresh acceptance, reconcile, publish, end."""
    workspace = w.open_workspace(
        config["workspace"], expected_identity=config["identity"]
    )
    publisher, acceptance, attempt = probe.recover(
        workspace, config["job"], config["generation"], compiled, values
    )
    session = x.begin_continuation(
        publisher,
        acceptance,
        attempt,
        probe.owner(acceptance.binding),
        operation=op(),
    )
    probe.drive(session, sizes)
    probe.finish_stream(session)
    ended = session.end(operation=op())
    s.record_attempt(publisher, attempt, session.owner, operation=op())
    publisher.close()
    return workspace, acceptance, ended


@pytest.mark.parametrize(
    "name",
    [
        "K1_after_basis",
        "K2_candidates",
        "K3_after_barrier",
        "K4_publish_reply_lost",
        "K5_second_crash",
        "K6_end_reply_lost",
    ],
)
def test_sigkill_cuts_recover_from_the_actual_committed_membership(
    tmp_path, built, name
):
    if not qualified(tmp_path):
        return
    config, compiled, values = stored(tmp_path, built)
    cut(INITIAL, config, "K1_after_basis" if name == "K1_after_basis" else "initial")
    operation = op()
    if name != "K1_after_basis":
        cut(RECOVERY, config, name, operation)
    facts = (
        json.loads((tmp_path / "facts.json").read_text())
        if name != "K1_after_basis"
        else {}
    )
    workspace = w.open_workspace(
        config["workspace"], expected_identity=config["identity"]
    )
    try:
        queried = s.query_operation(workspace, operation)
        before = c.checkpoint_snapshot(workspace, config["job"], config["generation"])
        if name == "K4_publish_reply_lost":
            # The SAME operation is queried: one committed effect, reply unknown.
            assert queried is not None and queried.kind == "publish_chunk"
            assert queried.get("checkpoint") == before.checkpoint
            assert before.committed == ((0, 2), (2, 3), (4, 6))
        elif name == "K6_end_reply_lost":
            assert queried is not None and queried.kind == "end_continuation"
            assert queried.get("checkpoint") == before.checkpoint
        else:
            assert queried is None
        if name == "K6_end_reply_lost":
            state = x.extraction_state(workspace, config["job"], config["generation"])
            assert state.complete_coverage and state.known == 7
            verify_store(workspace)
            return
    finally:
        workspace.close()
    workspace, acceptance, ended = complete(config, compiled, values, [2, 2, 2, 1])
    try:
        assert acceptance.checkpoint == before.checkpoint
        state = x.extraction_state(workspace, config["job"], config["generation"])
        assert state.complete_coverage and state.known == ended.get("observed") == 7
        snapshot = c.checkpoint_snapshot(workspace, config["job"], config["generation"])
        assert snapshot.committed[0] == (0, 2) and snapshot.frontier == 7
        files = c.classify_files(workspace)
        # Earlier candidate files stay unreferenced; nothing adopts them.
        if name == "K2_candidates":
            assert set(facts["candidates"]) <= set(files["orphans"])
        assert not files["missing"]
        record = s.job_record(workspace, config["job"])
        interrupted = [a for a in record.attempts if a.terminal == "INTERRUPTED"]
        assert interrupted and all(
            dict(a.outcome or ())["transaction"] == "UNKNOWN" for a in interrupted
        )
        verify_store(workspace)
    finally:
        workspace.close()
