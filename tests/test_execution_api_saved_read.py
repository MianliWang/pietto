"""Public R1 boundary refusals before any saved-result control or source path."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

import pietto.execution as execution
from pietto._project import project_job_workspace as private_workspace
from _pietto_jobs_public_cases import completed_saved_result


def _workspace():
    value = object.__new__(execution.WorkspaceRef)
    object.__setattr__(value, "root", "/not-opened")
    object.__setattr__(value, "identity", "ws-" + "0" * 32)
    return value


def _common(case) -> dict[str, Any]:
    pin, producer, compatibility = case.trust
    return dict(
        workspace=case.reference,
        job=case.job,
        generation=case.generation,
        checkpoint=case.snapshot.checkpoint,
        expected_pin=pin,
        accepted_producer=producer,
        accepted_compatibility=compatibility[-1],
        values=case.user_values,
        extent=case.snapshot.frontier,
        purpose="public-r1",
        route="postgres_rows",
        batch_rows=2,
        seconds=60,
    )


def test_r1_rejects_reused_operations_before_workspace_or_driver_access(monkeypatch):
    def forbidden(*arguments, **keywords):
        raise AssertionError("an invalid R1 request opened private workspace state")

    monkeypatch.setattr(private_workspace, "open_workspace", forbidden)
    before = {
        name for name in sys.modules if name.split(".")[0] in {"psycopg", "pyarrow"}
    }
    consumer = execution.new_consumer_identity()
    operation = execution.new_operation()
    with pytest.raises(execution.RequestRejected) as refused:
        execution.open_saved_read(
            _workspace(),
            job="job-" + "0" * 32,
            generation="gen-" + "0" * 32,
            checkpoint="ckp-" + "0" * 32,
            consumer=consumer,
            register_operation=operation,
            open_operation=operation,
            expected_pin="0" * 64,
            accepted_producer="pietto",
            accepted_compatibility="identity",
            values=(),
            extent=0,
            purpose="saved-read",
            route="postgres_rows",
            batch_rows=1,
            seconds=1,
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1010",
        "PUBLIC_OPERATION_DISTINCT",
    )
    assert before == {
        name for name in sys.modules if name.split(".")[0] in {"psycopg", "pyarrow"}
    }


def test_r1_rejects_non_string_register_operation_before_workspace_open(monkeypatch):
    monkeypatch.setattr(
        private_workspace,
        "open_workspace",
        lambda *arguments, **keywords: pytest.fail("opened private workspace"),
    )
    with pytest.raises(execution.RequestRejected) as refused:
        execution.open_saved_read(
            _workspace(),
            job="job-" + "0" * 32,
            generation="gen-" + "0" * 32,
            checkpoint="ckp-" + "0" * 32,
            consumer=execution.new_consumer_identity(),
            register_operation=object(),  # type: ignore[arg-type]
            open_operation=execution.new_operation(),
            expected_pin="0" * 64,
            accepted_producer="pietto",
            accepted_compatibility="identity",
            values=(),
            extent=0,
            purpose="saved-read",
            route="postgres_rows",
            batch_rows=1,
            seconds=1,
        )
    assert refused.value.detail == "PUBLIC_REGISTER_OPERATION"


def test_saved_read_surface_keeps_workspace_and_operations_opaque():
    assert {
        "SavedBatch",
        "SavedRead",
        "SavedReadEnd",
        "new_consumer_identity",
        "open_saved_read",
        "release_saved_read",
    } <= set(execution.__all__)
    consumer = execution.new_consumer_identity()
    assert consumer.startswith("csm-") and "workspace" not in repr(_workspace())


def test_saved_read_close_projects_a_failure_and_allows_retry():
    class Closer:
        def __init__(self, secret=None):
            self.calls, self.secret = 0, secret

        def close(self):
            self.calls += 1
            if self.calls == 1 and self.secret is not None:
                raise RuntimeError(self.secret)

    replay = Closer("saved-read-close-secret")
    publisher, workspace = Closer(), Closer()
    reader = execution.SavedRead(workspace, publisher, replay)
    with pytest.raises(execution.RequestRejected) as refused:
        reader.close()
    assert (
        "saved-read-close-secret" not in str(refused.value)
        and refused.value.__cause__ is None
        and refused.value.__context__ is None
        and (replay.calls, publisher.calls, workspace.calls) == (1, 0, 0)
    )
    reader.close()
    reader.close()
    assert (replay.calls, publisher.calls, workspace.calls) == (2, 1, 1)


def test_r1_defers_arrow_binding_until_the_first_batch(tmp_path, monkeypatch):
    case = completed_saved_result(tmp_path, monkeypatch)
    assert case is not None
    try:
        from pietto._project import project_arrow_result as arrow
        from pietto._project.project_result_contract import ResultError

        def missing():
            raise ResultError("ARROW_DEPENDENCY_MISSING")

        monkeypatch.setattr(arrow, "_arrow", missing)
        opened = execution.open_saved_read(
            **_common(case),
            consumer=execution.new_consumer_identity(),
            register_operation=execution.new_operation(),
            open_operation=execution.new_operation(),
        )
        try:
            with pytest.raises(execution.RequestRejected) as refused:
                opened.next(1, operation=execution.new_operation())
            assert refused.value.code == "PIE-R1009"
        finally:
            opened.close()
    finally:
        case.close()


def test_r1_real_checkpoint_requires_ack_and_reissues_unacknowledged_extent(
    tmp_path, monkeypatch
):
    case = completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        return
    common = _common(case)
    consumer = execution.new_consumer_identity()
    first = execution.open_saved_read(
        **common,
        consumer=consumer,
        register_operation=execution.new_operation(),
        open_operation=execution.new_operation(),
    )
    try:
        offered = first.next(2, operation=execution.new_operation())
        assert isinstance(offered, execution.SavedBatch)
        assert (offered.start, offered.stop, offered.batch.num_rows) == (0, 2, 2)
    finally:
        first.close()
    resumed = execution.open_saved_read(
        **common,
        consumer=consumer,
        register_operation=None,
        open_operation=execution.new_operation(),
    )
    try:
        repeated = resumed.next(2, operation=execution.new_operation())
        assert isinstance(repeated, execution.SavedBatch)
        assert (repeated.start, repeated.stop) == (offered.start, offered.stop)
        assert repeated.delivery != offered.delivery
        resumed.ack(repeated, operation=execution.new_operation())
        tail = resumed.next(2, operation=execution.new_operation())
        assert isinstance(tail, execution.SavedBatch)
        assert (tail.start, tail.stop, tail.batch.num_rows) == (2, 3, 1)
        resumed.ack(tail, operation=execution.new_operation())
        end = resumed.next(1, operation=execution.new_operation())
        assert isinstance(end, execution.SavedReadEnd)
        assert (end.terminal, end.acknowledged, end.extent) == (
            "SAVED_SCOPE_EXHAUSTED",
            3,
            3,
        )
    finally:
        resumed.close()
        case.close()


@pytest.mark.parametrize(
    "override",
    (
        {"expected_pin": "0" * 64},
        {"accepted_producer": "pietto-other"},
        {"accepted_compatibility": "other"},
        {"values": (True,)},
    ),
)
def test_r1_fresh_acceptance_projects_wrong_trust_or_values(
    tmp_path, monkeypatch, override
):
    case = completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        return
    try:
        with pytest.raises(execution.RequestRejected) as refused:
            execution.open_saved_read(
                **(_common(case) | override),
                consumer=execution.new_consumer_identity(),
                register_operation=execution.new_operation(),
                open_operation=execution.new_operation(),
            )
        assert refused.value.code == "PIE-R1009"
    finally:
        case.close()


def test_r1_never_registers_or_reopens_a_released_consumer(tmp_path, monkeypatch):
    case = completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        return
    common, consumer = _common(case), execution.new_consumer_identity()
    try:
        with pytest.raises(execution.RequestRejected) as refused:
            execution.open_saved_read(
                **common,
                consumer=consumer,
                register_operation=None,
                open_operation=execution.new_operation(),
            )
        assert (refused.value.code, refused.value.detail) == (
            "PIE-R1009",
            "CONSUMER_UNKNOWN",
        )
        opened = execution.open_saved_read(
            **common,
            consumer=consumer,
            register_operation=execution.new_operation(),
            open_operation=execution.new_operation(),
        )
        opened.close()
        released = execution.release_saved_read(
            **common, consumer=consumer, operation=execution.new_operation()
        )
        assert released.kind == "release_retention"
        with pytest.raises(execution.RequestRejected) as refused:
            execution.open_saved_read(
                **common,
                consumer=consumer,
                register_operation=None,
                open_operation=execution.new_operation(),
            )
        assert (refused.value.code, refused.value.detail) == (
            "PIE-R1009",
            "CONSUMER_RELEASED",
        )
    finally:
        case.close()


def test_r1_projects_conflicting_operation_and_missing_saved_chunk(
    tmp_path, monkeypatch
):
    case = completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        return
    opened = None
    try:
        opened = execution.open_saved_read(
            **_common(case),
            consumer=execution.new_consumer_identity(),
            register_operation=execution.new_operation(),
            open_operation=execution.new_operation(),
        )
        operation = execution.new_operation()
        offered = opened.next(2, operation=operation)
        assert isinstance(offered, execution.SavedBatch)
        with pytest.raises(execution.RequestRejected) as refused:
            opened.ack(offered, operation=operation)
        assert (refused.value.code, refused.value.detail) == (
            "PIE-R1010",
            "OPERATION_CONFLICT",
        )
        offered.batch.close()
        opened.ack(offered, operation=execution.new_operation())
        Path(case.workspace.root, "chunks", case.snapshot.members[1].file).unlink()
        with pytest.raises(execution.RequestRejected) as refused:
            opened.next(2, operation=execution.new_operation())
        assert (refused.value.code, refused.value.detail) == (
            "PIE-R1009",
            "CHUNK_MISSING",
        )
    finally:
        if opened is not None:
            opened.close()
        case.close()
