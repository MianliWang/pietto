"""Public source-free saved-result replay over one fixed checkpoint."""

from __future__ import annotations

from dataclasses import dataclass

from pietto._project import project_job_capture as capture
from pietto._project import project_job_replay as replay
from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as private_workspace
from pietto._project.project_compiled_schema import VERSIONS
from pietto.execution._errors import RequestRejected, failure, workspace_failure
from pietto.execution._handle import ResultBatch, _batch
from pietto.execution._saved import _parameters
from pietto.execution._workspace import OperationReply, WorkspaceRef, _reply

__all__ = [
    "SavedBatch",
    "SavedRead",
    "SavedReadEnd",
    "new_consumer_identity",
    "open_saved_read",
    "release_saved_read",
]


def new_consumer_identity() -> str:
    """Allocate a caller-held identity for one saved-result reader."""
    return replay.new_consumer()


def _compatibility(value):
    if type(value) is not str or not value:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_COMPATIBILITY"))
    return (*VERSIONS, value)


def _require(
    workspace,
    job,
    generation,
    checkpoint,
    consumer,
    register,
    opening,
    *,
    parameters=None,
    distinct=True,
):
    if type(workspace) is not WorkspaceRef:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_WORKSPACE_REFERENCE"))
    for value, detail in (
        (job, "PUBLIC_JOB"),
        (generation, "PUBLIC_GENERATION"),
        (checkpoint, "PUBLIC_CHECKPOINT"),
        (consumer, "PUBLIC_CONSUMER"),
        (opening, "PUBLIC_OPERATION"),
    ):
        if type(value) is not str:
            raise RequestRejected(failure("PIE-R1002", detail))
    if not private_workspace.valid_identity(consumer, "csm"):
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_CONSUMER"))
    if register is not None and type(register) is not str:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_REGISTER_OPERATION"))
    if not private_workspace.valid_identity(opening, "op") or (
        register is not None and not private_workspace.valid_identity(register, "op")
    ):
        raise RequestRejected(failure("PIE-R1010", "PUBLIC_OPERATION_IDENTITY"))
    if distinct and register is not None and register == opening:
        raise RequestRejected(failure("PIE-R1010", "PUBLIC_OPERATION_DISTINCT"))
    return _parameters(parameters)


def _accept(
    opened,
    job,
    generation,
    *,
    checkpoint,
    consumer,
    scope,
    extent,
    purpose,
    route,
    values,
    parameters,
    expected_pin,
    accepted_producer,
    accepted_compatibility,
    seconds,
    batch_rows,
):
    return replay.accept_saved_read(
        opened,
        job,
        generation,
        checkpoint=checkpoint,
        consumer=consumer,
        scope=scope,
        extent=extent,
        purpose=purpose,
        route=route,
        values=values,
        parameters=parameters,
        expected_pin=expected_pin,
        accepted_producer=accepted_producer,
        accepted_compatibility=_compatibility(accepted_compatibility),
        seconds=seconds,
        batch_rows=batch_rows,
    )


@dataclass(frozen=True, slots=True)
class SavedBatch:
    """One issued saved extent and its existing caller-owned ResultBatch."""

    delivery: str
    generation: str
    start: int
    stop: int
    batch: ResultBatch
    _delivery: object


@dataclass(frozen=True, slots=True)
class SavedReadEnd:
    """Fixed saved-scope exhaustion; it is neither source EOF nor an ACK."""

    terminal: str
    generation: str
    checkpoint: str
    extent: int
    acknowledged: int


class SavedRead:
    """One opaque saved-result reader. Only ``ack`` advances its frontier."""

    __slots__ = ("_workspace", "_publisher", "_replay", "_closed")

    def __init__(self, workspace, publisher, session):
        self._workspace, self._publisher, self._replay = workspace, publisher, session
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *arguments):
        self.close()
        return False

    def next(self, rows: int, *, operation: str) -> SavedBatch | SavedReadEnd:
        try:
            item = self._replay.next(rows, operation=operation)
            if type(item) is replay.SavedScopeEnd:
                return SavedReadEnd(
                    item.terminal,
                    item.generation,
                    item.checkpoint,
                    item.extent,
                    item.acknowledged,
                )
            return SavedBatch(
                item.identity,
                item.generation,
                item.start,
                item.stop,
                _batch(item.batch),
                item,
            )
        except Exception as caught:
            raise RequestRejected(workspace_failure(caught)) from None

    def ack(self, batch: SavedBatch, *, operation: str) -> OperationReply:
        if type(batch) is not SavedBatch:
            raise RequestRejected(failure("PIE-R1002", "PUBLIC_SAVED_BATCH"))
        try:
            return _reply(
                self._replay.acknowledge(batch._delivery, operation=operation)
            )
        except Exception as caught:
            raise RequestRejected(workspace_failure(caught)) from None

    def close(self) -> None:
        if self._closed:
            return
        refusal = None
        try:
            self._replay.close()
            self._publisher.close()
            self._workspace.close()
        except Exception as caught:
            refusal = workspace_failure(caught)
        else:
            self._closed = True
            return
        assert refusal is not None
        raise RequestRejected(refusal)


def open_saved_read(
    workspace: WorkspaceRef,
    *,
    job: str,
    generation: str,
    checkpoint: str,
    consumer: str,
    register_operation: str | None = None,
    open_operation: str,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: str,
    values: tuple,
    scope: str = "complete_capture",
    extent: int,
    purpose: str,
    route: str,
    batch_rows: int,
    seconds: int,
    parameters: dict[str, object] | None = None,
) -> SavedRead:
    """Open one source-free R1 reader with caller-held durable operations.

    ``values`` and ``parameters`` restate the saved generation's binding:
    each must equal the saved value with the same type (BINDING_VECTOR); a
    binding that names parameters requires ``parameters``."""
    named = _require(
        workspace,
        job,
        generation,
        checkpoint,
        consumer,
        register_operation,
        open_operation,
        parameters=parameters,
    )
    opened = publisher = None
    refusal = None
    try:
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        # Fresh code/trust and fixed-snapshot checks run before the publisher claim.
        acceptance = _accept(
            opened,
            job,
            generation,
            checkpoint=checkpoint,
            consumer=consumer,
            scope=scope,
            extent=extent,
            purpose=purpose,
            route=route,
            values=values,
            parameters=named,
            expected_pin=expected_pin,
            accepted_producer=accepted_producer,
            accepted_compatibility=accepted_compatibility,
            seconds=seconds,
            batch_rows=batch_rows,
        )
        publisher = store.claim_publisher(opened, job, operation=store.new_operation())
        if register_operation is not None:
            replay.register_consumer(
                publisher, acceptance, operation=register_operation
            )
        session = replay.open_replay(publisher, acceptance, operation=open_operation)
        return SavedRead(opened, publisher, session)
    except Exception as caught:
        if publisher is not None:
            publisher.close()
        if opened is not None:
            opened.close()
        if type(caught) is RequestRejected:
            raise
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)


def release_saved_read(
    workspace: WorkspaceRef,
    *,
    job: str,
    generation: str,
    checkpoint: str,
    consumer: str,
    operation: str,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: str,
    values: tuple,
    scope: str = "complete_capture",
    extent: int,
    purpose: str,
    route: str,
    batch_rows: int,
    seconds: int,
    parameters: dict[str, object] | None = None,
) -> OperationReply:
    """Release one registered reader retention after fresh trust acceptance;
    ``values`` and ``parameters`` restate the saved binding as for
    open_saved_read()."""
    named = _require(
        workspace,
        job,
        generation,
        checkpoint,
        consumer,
        operation,
        operation,
        parameters=parameters,
        distinct=False,
    )
    opened = publisher = None
    refusal = None
    try:
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        acceptance = _accept(
            opened,
            job,
            generation,
            checkpoint=checkpoint,
            consumer=consumer,
            scope=scope,
            extent=extent,
            purpose=purpose,
            route=route,
            values=values,
            parameters=named,
            expected_pin=expected_pin,
            accepted_producer=accepted_producer,
            accepted_compatibility=accepted_compatibility,
            seconds=seconds,
            batch_rows=batch_rows,
        )
        state = replay.consumer_state(opened, consumer)
        if (state.job, state.generation, state.checkpoint) != (
            job,
            generation,
            acceptance.checkpoint,
        ):
            raise private_workspace.JobStoreError("ACCEPTANCE_SUBJECT")
        publisher = store.claim_publisher(opened, job, operation=store.new_operation())
        return _reply(
            capture.release_retention(publisher, state.retention, operation=operation)
        )
    except Exception as caught:
        if type(caught) is RequestRejected:
            raise
        refusal = workspace_failure(caught)
    finally:
        if publisher is not None:
            publisher.close()
        if opened is not None:
            opened.close()
    assert refusal is not None
    raise RequestRejected(refusal)
