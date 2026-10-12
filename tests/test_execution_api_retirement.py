"""Public retirement stays fenced to one caller-owned v7 generation."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

import _pietto_jobs_public_cases as public_cases
import pietto.execution as execution
from pietto._project import project_job_collection as collection
from pietto._project import project_job_runtime as runtime
from pietto._project import project_job_workspace as private_workspace


def workspace_ref():
    value = object.__new__(execution.WorkspaceRef)
    object.__setattr__(value, "root", "/not-opened")
    object.__setattr__(value, "identity", "ws-" + "0" * 32)
    return value


@pytest.mark.parametrize(
    "changes,code,detail",
    (
        ({"job": None}, "PIE-R1001", "PUBLIC_JOB_REQUIRED"),
        ({"generation": None}, "PIE-R1001", "PUBLIC_GENERATION_REQUIRED"),
        ({"operation": None}, "PIE-R1001", "PUBLIC_OPERATION_REQUIRED"),
        ({"job": 1}, "PIE-R1002", "PUBLIC_JOB_TYPE"),
        ({"generation": "gen-invalid"}, "PIE-R1002", "PUBLIC_GENERATION_TYPE"),
        ({"operation": "op-invalid"}, "PIE-R1002", "PUBLIC_OPERATION_TYPE"),
    ),
)
def test_retirement_refuses_invalid_input_before_workspace_open(
    monkeypatch, changes, code, detail
):
    monkeypatch.setattr(
        private_workspace,
        "open_workspace",
        lambda *args, **kwargs: pytest.fail("invalid retirement opened workspace"),
    )
    arguments = {
        "job": "job-" + "1" * 32,
        "generation": "gen-" + "2" * 32,
        "operation": "op-" + "3" * 32,
    }
    arguments.update(changes)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.retire_generation(workspace_ref(), **arguments)
    assert (refused.value.code, refused.value.detail) == (code, detail)


def test_retirement_is_the_only_new_public_control_export():
    assert "retire_generation" in execution.__all__
    assert not {"collect", "open_runtime", "reconcile", "Runtime"} & set(
        execution.__all__
    )


def test_retirement_removes_only_the_callers_unpublished_latest_root(tmp_path):
    case = public_cases.unstarted_saved_generation(tmp_path)
    if case is None:
        return
    try:
        reply = execution.retire_generation(
            case.reference,
            job=case.job,
            generation=case.generation,
            operation=execution.new_operation(),
        )
        assert (
            reply.kind == "retire_generation"
            and dict(reply.result)["generation"] == case.generation
        )
        state = collection.protection(case.workspace, case.job)
        assert len(state) == 1
        assert state[0].retired and not state[0].published
        assert not state[0].roots and not state[0].decided and not state[0].removed
    finally:
        case.close()


def test_incompatible_job_refuses_before_opening_a_runtime(tmp_path, monkeypatch):
    case = public_cases.unstarted_saved_generation(tmp_path)
    if case is None:
        return
    try:
        private_workspace.write(
            case.workspace,
            lambda connection: connection.execute(
                "UPDATE job SET compatibility = ? WHERE identity = ?", ("[]", case.job)
            ),
        )
        monkeypatch.setattr(
            runtime,
            "open_runtime",
            lambda *args, **kwargs: pytest.fail(
                "incompatible retirement opened runtime"
            ),
        )
        with pytest.raises(execution.RequestRejected) as refused:
            execution.retire_generation(
                case.reference,
                job=case.job,
                generation=case.generation,
                operation=execution.new_operation(),
            )
        assert (refused.value.code, refused.value.detail) == (
            "PIE-R1009",
            "JOB_COMPATIBILITY",
        )
    finally:
        case.close()


def test_other_process_runtime_is_a_typed_busy_refusal(tmp_path):
    case = public_cases.unstarted_saved_generation(tmp_path)
    if case is None:
        return
    code = """
import json, sys
from pietto._project import project_job_runtime as runtime
from pietto._project import project_public_jobs as jobs
config = json.loads(sys.stdin.readline())
ref = type('Ref', (), config)()
budget, available = jobs.runtime_capacity(ref)
opened = runtime.open_runtime(config['root'], expected_identity=config['identity'],
    policy=jobs.policy_for(budget, available))
print('ready', flush=True)
sys.stdin.readline()
opened.close()
"""
    child = subprocess.Popen(
        [sys.executable, "-I", "-B", "-c", code],
        cwd=tmp_path,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdin is not None and child.stdout is not None
        child.stdin.write(
            json.dumps(
                {"root": case.workspace.root, "identity": case.workspace.identity}
            )
            + "\n"
        )
        child.stdin.flush()
        assert child.stdout.readline().strip() == "ready"
        with pytest.raises(execution.RequestRejected) as refused:
            execution.retire_generation(
                case.reference,
                job=case.job,
                generation=case.generation,
                operation=execution.new_operation(),
            )
        assert (refused.value.code, refused.value.detail) == (
            "PIE-R1009",
            "RUNTIME_BUSY",
        )
    finally:
        if child.stdin is not None:
            child.stdin.write("close\n")
            child.stdin.close()
        child.wait(timeout=30)
        case.close()
