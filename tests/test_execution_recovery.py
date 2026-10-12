"""Offline checks for the public ordinary R2 entry."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from typing import Any, cast

from pietto._project import project_job_extraction as extraction
from pietto._project import project_job_store as store
from pietto._project import project_public_jobs as jobs
from pietto._project.project_job_workspace import JobStoreError, Workspace
from pietto.execution import RequestRejected, WorkspaceRef
from pietto.execution import _r2 as public_r2


def test_saved_output_rebuilds_recorded_r2_shape_over_guarded_output(monkeypatch):
    from pietto._project import project_execution as private_execution
    from pietto._project import project_job_capture as capture

    binding, output, program, refinement = object(), object(), object(), object()
    observed = []
    monkeypatch.setattr(capture, "supports", lambda workspace, feature: True)
    monkeypatch.setattr(
        private_execution, "compiled_output", lambda actual: (output, None, program)
    )
    monkeypatch.setattr(capture, "read", lambda *args: ("recorded", "stable"))
    monkeypatch.setattr(
        capture,
        "_recorded_refinement",
        lambda actual_binding, actual_output, route, isolation, text: (
            observed.append((actual_binding, actual_output, route, isolation, text))
            or refinement
        ),
    )
    monkeypatch.setattr(
        capture,
        "arrow_output",
        lambda job, generation, actual_output, actual_refinement, route: (
            job,
            generation,
            actual_output,
            actual_refinement,
            route,
        ),
    )

    assert capture.verified_stored_output(
        cast(Workspace, object()), "job", "generation", binding, "postgres_rows"
    ) == ("job", "generation", output, refinement, "postgres_rows")
    assert observed == [(binding, output, "postgres_rows", "stable", "recorded")]


def test_r2_entry_refuses_an_ordinary_owner_before_capture_progress():
    class Owner:
        refined_request = None
        enumeration = None
        _payloads = None
        _closed = False

    with pytest.raises(JobStoreError, match="EXTRACTION_OWNER_STATE"):
        extraction._fresh(Owner())


@pytest.mark.parametrize(
    ("purpose", "seconds", "reason"),
    (
        ("", 60, "ACCEPTANCE_PURPOSE"),
        ("recovery", 0, "ACCEPTANCE_BOUND"),
    ),
)
def test_recovery_acceptance_refuses_invalid_caller_declaration_before_source(
    monkeypatch, purpose, seconds, reason
):
    monkeypatch.setattr(extraction, "_extracting", lambda workspace: None)
    monkeypatch.setattr(
        extraction,
        "stored_binding",
        lambda *args, **kwargs: pytest.fail("invalid acceptance opened a saved source"),
    )
    with pytest.raises(JobStoreError, match=reason):
        extraction.accept_recovery(
            cast(Any, object()),
            "job-" + "0" * 32,
            "gen-" + "0" * 32,
            checkpoint=None,
            purpose=purpose,
            values=(),
            expected_pin="0" * 64,
            accepted_producer="0" * 64,
            accepted_compatibility=(),
            seconds=seconds,
        )


@pytest.mark.parametrize(
    ("purpose", "seconds", "detail"),
    (
        ("", 60, "ACCEPTANCE_PURPOSE"),
        ("unprintable\n", 60, "ACCEPTANCE_PURPOSE"),
        ("x" * 257, 60, "ACCEPTANCE_PURPOSE"),
        ("recovery", 0, "ACCEPTANCE_BOUND"),
        ("recovery", True, "ACCEPTANCE_BOUND"),
        ("recovery", 86401, "ACCEPTANCE_BOUND"),
    ),
)
def test_public_recovery_rejects_invalid_bounds_before_workspace(
    monkeypatch, purpose, seconds, detail
):
    monkeypatch.setattr(
        public_r2.private_workspace,
        "open_workspace",
        lambda *args, **kwargs: pytest.fail("invalid input opened a workspace"),
    )
    with pytest.raises(RequestRejected) as refused:
        public_r2.recover(
            WorkspaceRef("/not-opened", "ws-" + "0" * 32),
            job="job-" + "1" * 32,
            generation="gen-" + "2" * 32,
            checkpoint=None,
            query=None,
            source_requirements=(),
            operation="op-" + "3" * 32,
            route="postgres_rows",
            access=None,
            premise=None,
            limits=None,
            expected_pin="0" * 64,
            accepted_producer="0" * 64,
            accepted_compatibility="0" * 64,
            purpose=purpose,
            seconds=seconds,
        )
    assert refused.value.code == "PIE-R1002"
    assert refused.value.detail == detail
    assert refused.value.__cause__ is None
    assert refused.value.__context__ is None


def test_public_recovery_refuses_preflight_before_runtime(monkeypatch):
    workspace = WorkspaceRef("/not-opened", "ws-" + "0" * 32)
    opened = SimpleNamespace(close=lambda: None)
    called = []
    monkeypatch.setattr(
        public_r2, "_checked_request", lambda *args, **kwargs: (None,) * 5
    )
    monkeypatch.setattr(
        public_r2.proposal, "prepare_live_refinement", lambda *args: None
    )
    monkeypatch.setattr(
        public_r2, "_recovery_trust", lambda *args: ("pin", "producer", ())
    )
    monkeypatch.setattr(
        public_r2.private_workspace, "open_workspace", lambda *args, **kwargs: opened
    )
    monkeypatch.setattr(
        public_r2.extraction,
        "continuation_replay_request",
        lambda *args, **kwargs: {"job": args[1]},
    )
    monkeypatch.setattr(
        public_r2.store, "query_operation", lambda *args, **kwargs: None
    )

    def refuse(*args, **kwargs):
        called.append((args, kwargs))
        raise JobStoreError("JOB_UNKNOWN")

    monkeypatch.setattr(public_r2.extraction, "accept_recovery", refuse)
    monkeypatch.setattr(
        public_r2.jobs,
        "recover_recoverable",
        lambda *args, **kwargs: pytest.fail("preflight failure opened runtime"),
    )
    with pytest.raises(RequestRejected) as refused:
        public_r2.recover(
            workspace,
            job="job-" + "1" * 32,
            generation="gen-" + "2" * 32,
            checkpoint=None,
            query=object(),
            source_requirements=(),
            operation="op-" + "3" * 32,
            route="postgres_rows",
            access=object(),
            premise=object(),
            limits=object(),
            expected_pin="pin",
            accepted_producer="producer",
            accepted_compatibility="compatibility",
            purpose="recovery",
            seconds=60,
        )
    assert (
        refused.value.code == "PIE-R1009"
        and refused.value.__cause__ is None
        and refused.value.__context__ is None
        and len(called) == 1
    )


def test_public_recovery_replays_before_current_predecessor_acceptance(monkeypatch):
    workspace = WorkspaceRef("/not-opened", "ws-" + "0" * 32)
    opened = SimpleNamespace(close=lambda: None)
    operation = "op-" + "3" * 32
    expected = {
        "job": "job-" + "1" * 32,
        "generation": "gen-" + "2" * 32,
        "predecessor": "ckp-" + "4" * 32,
        "frontier": 2,
        "reach": 2,
        "members": 1,
        "rows": 2,
        "qualification": "qualified",
    }
    previous = store.OperationResult(
        operation, "begin_continuation", expected["job"], 7, (), "QUERIED"
    )
    monkeypatch.setattr(
        public_r2,
        "_checked_request",
        lambda *args, **kwargs: (None, (), None, None, ()),
    )
    monkeypatch.setattr(
        public_r2.proposal, "prepare_live_refinement", lambda *args: object()
    )
    monkeypatch.setattr(
        public_r2, "_recovery_trust", lambda *args: ("pin", "producer", ())
    )
    monkeypatch.setattr(
        public_r2.private_workspace, "open_workspace", lambda *args, **kwargs: opened
    )
    monkeypatch.setattr(
        public_r2.extraction,
        "continuation_replay_request",
        lambda *args, **kwargs: expected,
    )

    def query(_workspace, actual_operation, *, expected_kind, expected_request):
        assert (actual_operation, expected_kind, expected_request) == (
            operation,
            "begin_continuation",
            expected,
        )
        return previous

    monkeypatch.setattr(public_r2.store, "query_operation", query)
    monkeypatch.setattr(
        public_r2.extraction,
        "accept_recovery",
        lambda *args, **kwargs: pytest.fail("replay accepted a current predecessor"),
    )
    monkeypatch.setattr(
        public_r2.jobs,
        "recover_recoverable",
        lambda *args, **kwargs: pytest.fail("replay opened a recovery runtime"),
    )
    reply = public_r2.recover(
        workspace,
        job=expected["job"],
        generation=expected["generation"],
        checkpoint=expected["predecessor"],
        query=object(),
        source_requirements=(),
        operation=operation,
        route="postgres_rows",
        access=object(),
        premise=object(),
        limits=object(),
        expected_pin="pin",
        accepted_producer="producer",
        accepted_compatibility="compatibility",
        purpose="recovery",
        seconds=60,
    )
    assert reply.terminal == "REPLY_LOST_OR_PARTIAL"
    assert reply.operation is not None and reply.operation.sequence == 7


@pytest.mark.parametrize(
    "function", (jobs.capture_recoverable, jobs.recover_recoverable)
)
def test_recoverable_pending_close_reuses_the_s08_single_retry(monkeypatch, function):
    class Opened:
        def __init__(self):
            self.resumes = self.closes = 0

        def reconcile(self):
            return ()

        def submit(self, unit):
            return "admission"

        def wait(self, handle, timeout):
            return SimpleNamespace(
                terminal="COMPLETED" if self.resumes else None,
                activity=None if self.resumes else "WAITING_FOR_CLEANUP",
            )

        def resume(self, handle):
            self.resumes += 1

        def close(self):
            self.closes += 1
            return {"unjoined": False}

    opened = Opened()
    monkeypatch.setattr(
        jobs,
        "runtime_capacity",
        lambda workspace: (jobs.workspace.CONTROL_RESERVE + 2, 1),
    )
    monkeypatch.setattr(jobs.runtime, "open_runtime", lambda *args, **kwargs: opened)
    values = dict(
        job="job-" + "0" * 32,
        generation="gen-" + "0" * 32,
        template=object(),
        route="postgres_rows",
        access=object(),
        schemas=(),
        limits=SimpleNamespace(seconds=1),
        isolation="stable",
        values=(),
    )
    if function is jobs.capture_recoverable:
        values["source_requirements"] = ()
    else:
        values.update(
            checkpoint=None,
            trust=("pin", "producer", ()),
            purpose="recovery",
            seconds=1,
            source_requirements=(),
            operation="op-" + "0" * 32,
        )
    state, pending = function(
        SimpleNamespace(root="/root", identity="ws-" + "0" * 32), **values
    )
    assert state.activity == "WAITING_FOR_CLEANUP" and pending is not None
    pending.close()
    pending.close()
    assert (opened.resumes, opened.closes) == (1, 1)


def test_pending_close_refuses_an_unresolved_single_retry():
    class Opened:
        def __init__(self):
            self.resumes = self.closes = 0

        def resume(self, handle):
            self.resumes += 1

        def wait(self, handle, timeout):
            return SimpleNamespace(terminal=None)

        def close(self):
            self.closes += 1
            return {"unjoined": False}

    opened = Opened()
    with pytest.raises(JobStoreError, match="RUNTIME_CLOSE_UNJOINED"):
        jobs.PendingClose(opened, "admission").close()
    assert (opened.resumes, opened.closes) == (1, 0)
