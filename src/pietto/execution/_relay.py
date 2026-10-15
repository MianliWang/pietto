"""Public one-shot live relay to an explicitly named local reference sink."""

from __future__ import annotations

from dataclasses import dataclass
import os

from pietto._project import project_job_runtime as runtime
from pietto._project import project_job_sink as private_sink
from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as private_workspace
from pietto._project import project_public_jobs as jobs
from pietto.execution._errors import (
    RequestRejected,
    failure,
    sink_failure,
    workspace_failure,
)
from pietto.execution._saved import _checked_request
from pietto.execution._workspace import WorkspaceRef, _reply, operation_result

__all__ = ["RelayCloseHandle", "RelayReply", "relay_live"]


class RelayCloseHandle:
    """One pending relay's retained coordinator; it is never a saved reader."""

    __slots__ = ("_pending", "_closed")

    def __init__(self, pending):
        self._pending, self._closed = pending, False

    @property
    def closed(self):
        return self._closed

    def close(self):
        if self._closed:
            return
        refusal = None
        try:
            self._pending.close()
        except Exception as caught:
            refusal = workspace_failure(caught)
        else:
            self._closed = True
            return
        assert refusal is not None
        raise RequestRejected(refusal)

    def __reduce_ex__(self, protocol):
        raise TypeError("RelayCloseHandle cannot be pickled or copied")


@dataclass(frozen=True, slots=True)
class RelayReply:
    """The current observation of one fresh live relay submission."""

    workspace: str
    operation: object | None
    job: str | None
    generation: str | None
    admission: str | None
    terminal: str | None
    settlement: str | None
    cleanup: RelayCloseHandle | None = None


def _refuse(detail):
    raise RequestRejected(failure("PIE-R1002", detail))


def _sink_target(
    root,
    expected_identity,
    namespace,
    epoch,
    retention,
    budget_bytes,
    busy_seconds,
):
    if root is None:
        raise RequestRejected(failure("PIE-R1001", "REFERENCE_SINK_ROOT"))
    if not isinstance(root, (str, os.PathLike)):
        _refuse("REFERENCE_SINK_ROOT")
    if expected_identity is None:
        raise RequestRejected(failure("PIE-R1001", "REFERENCE_SINK_IDENTITY"))
    if type(expected_identity) is not str:
        _refuse("REFERENCE_SINK_IDENTITY")
    if namespace is None:
        raise RequestRejected(failure("PIE-R1001", "REFERENCE_SINK_NAMESPACE"))
    if type(namespace) is not str:
        _refuse("REFERENCE_SINK_NAMESPACE")
    if epoch is None:
        raise RequestRejected(failure("PIE-R1001", "REFERENCE_SINK_EPOCH"))
    if type(epoch) is not int:
        _refuse("REFERENCE_SINK_EPOCH")
    if retention is None:
        raise RequestRejected(failure("PIE-R1001", "REFERENCE_SINK_RETENTION"))
    if type(retention) is not str:
        _refuse("REFERENCE_SINK_RETENTION")
    if budget_bytes is None:
        raise RequestRejected(failure("PIE-R1001", "REFERENCE_SINK_BUDGET"))
    if type(budget_bytes) is not int:
        _refuse("REFERENCE_SINK_BUDGET")
    if type(busy_seconds) not in (int, float):
        _refuse("REFERENCE_SINK_BUSY")
    path, busy = os.fspath(root), float(busy_seconds)
    refusal = None
    try:
        opened = private_sink.open_sink(
            path, expected_identity=expected_identity, busy_seconds=busy
        )
        try:
            description = opened.describe()
            if description.namespace != namespace:
                _refuse("REFERENCE_SINK_NAMESPACE")
            if description.epoch != epoch:
                _refuse("REFERENCE_SINK_EPOCH")
            if opened.retention != retention:
                _refuse("REFERENCE_SINK_RETENTION")
            if opened.budget != budget_bytes:
                _refuse("REFERENCE_SINK_BUDGET")
        finally:
            opened.close()
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = sink_failure(caught)
    else:
        return runtime.SinkTarget(
            path,
            expected_identity,
            namespace,
            epoch,
            retention,
            busy,
            budget_bytes,
        )
    assert refusal is not None
    raise RequestRejected(refusal)


def relay_live(
    workspace: WorkspaceRef,
    query,
    *,
    operation: str,
    route: str,
    access,
    premise,
    sink_root,
    expected_sink_identity: str,
    sink_namespace: str,
    sink_epoch: int,
    sink_retention: str,
    sink_budget_bytes: int,
    sink_busy_seconds: float = 5.0,
    limits=None,
    isolation: str = "stable",
    values: tuple | None = None,
    parameters: dict[str, object] | None = None,
) -> RelayReply:
    """Start one fresh live capture/relay; prior saved results are not inputs.

    ``parameters`` binds a query's declared parameters by name."""
    if limits is None:
        from pietto.execution._access import ExecutionLimits

        limits = ExecutionLimits()
    (
        binding,
        supplied,
        private_access,
        private_limits,
        schemas,
        named,
    ) = _checked_request(
        workspace,
        query,
        operation,
        route,
        access,
        premise,
        limits,
        isolation,
        values,
        None,
        parameters=parameters,
    )
    sink = _sink_target(
        sink_root,
        expected_sink_identity,
        sink_namespace,
        sink_epoch,
        sink_retention,
        sink_budget_bytes,
        sink_busy_seconds,
    )
    refusal = None
    try:
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            previous = store.query_operation(
                opened,
                operation,
                expected_kind="register_job",
                expected_request=store.register_job_request(query._template),
            )
            if previous is not None:
                return RelayReply(
                    workspace.identity,
                    _reply(previous),
                    previous.job,
                    None,
                    None,
                    "REPLY_LOST_OR_PARTIAL",
                    None,
                )
            registered, job, generation = jobs.register_generation(
                opened, query._template, binding, route, isolation, operation, None
            )
            if registered.observation != "COMMITTED_THIS_CALL":
                return RelayReply(
                    workspace.identity,
                    _reply(registered),
                    job,
                    None,
                    None,
                    "REPLY_LOST_OR_PARTIAL",
                    None,
                )
            root = query._template.artifact.request.verification.completed.root
            trust = (
                root.expected_pin,
                root.accepted_producer,
                root.accepted_compatibility,
            )
        finally:
            opened.close()
        state, pending = jobs.relay(
            workspace,
            job=job,
            generation=generation,
            template=query._template,
            route=route,
            access=private_access,
            schemas=schemas,
            limits=private_limits,
            isolation=isolation,
            values=supplied,
            parameters=named,
            trust=trust,
            sink=sink,
            purpose="public-live-relay",
            rows=private_limits.batch_rows,
            batch_rows=private_limits.batch_rows,
        )
        return RelayReply(
            workspace.identity,
            operation_result(workspace, operation),
            job,
            generation,
            state.handle,
            state.terminal,
            state.settlement,
            None if pending is None else RelayCloseHandle(pending),
        )
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)
