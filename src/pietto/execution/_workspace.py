"""Opaque public references to v7 saved-result workspaces."""

from __future__ import annotations

from dataclasses import dataclass
import os

from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as private
from pietto.execution._errors import RequestRejected, failure, workspace_failure

__all__ = [
    "OperationReply",
    "WorkspaceRef",
    "create_workspace",
    "new_operation",
    "open_workspace",
    "operation_result",
]


@dataclass(frozen=True, slots=True)
class WorkspaceRef:
    """A v7 workspace name and identity, never its SQLite connection."""

    root: str
    identity: str

    def __reduce_ex__(self, protocol):
        raise TypeError("WorkspaceRef cannot be pickled or copied")


@dataclass(frozen=True, slots=True)
class OperationReply:
    """One recorded private step, or the durable result of an earlier call."""

    operation: str
    kind: str
    job: str
    sequence: int
    result: tuple[tuple[str, object], ...]
    observation: str


def _root(root):
    if root is None:
        raise RequestRejected(failure("PIE-R1001", "PUBLIC_WORKSPACE_ROOT"))
    if not isinstance(root, (str, os.PathLike)):
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_WORKSPACE_ROOT"))
    return os.fspath(root)


def _reply(value):
    return OperationReply(
        value.operation,
        value.kind,
        value.job,
        value.sequence,
        value.result,
        value.observation,
    )


def create_workspace(
    root: str | os.PathLike[str], *, budget_bytes: int
) -> WorkspaceRef:
    """Create exactly one v7 workspace at ``root``.

    The returned reference owns no open file descriptor.  There is no format
    selector, migration, scheduler or deletion operation on this API.
    """
    path = _root(root)
    if budget_bytes is None:
        raise RequestRejected(failure("PIE-R1001", "PUBLIC_WORKSPACE_BUDGET"))
    if type(budget_bytes) is not int:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_WORKSPACE_BUDGET"))
    refusal = None
    try:
        workspace = private.create_workspace(
            path, budget_bytes=budget_bytes, format=private.FORMAT_V7
        )
        try:
            return WorkspaceRef(workspace.root, workspace.identity)
        finally:
            workspace.close()
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)


def open_workspace(
    root: str | os.PathLike[str], *, expected_identity: str
) -> WorkspaceRef:
    """Verify and name an existing v7 workspace without opening a coordinator."""
    path = _root(root)
    if expected_identity is None:
        raise RequestRejected(failure("PIE-R1001", "PUBLIC_WORKSPACE_IDENTITY"))
    if type(expected_identity) is not str:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_WORKSPACE_IDENTITY"))
    refusal = None
    try:
        workspace = private.open_workspace(path, expected_identity=expected_identity)
        try:
            if workspace.format != private.FORMAT_V7:
                raise private.JobStoreError("WORKSPACE_FORMAT")
            return WorkspaceRef(workspace.root, workspace.identity)
        finally:
            workspace.close()
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)


def new_operation() -> str:
    """Return one caller-held identity for the next durable save step."""
    return store.new_operation()


def operation_result(workspace: WorkspaceRef, operation: str) -> OperationReply | None:
    """Read one recorded step.  It never retries or advances a save flow."""
    if type(workspace) is not WorkspaceRef:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_WORKSPACE_REFERENCE"))
    if operation is None:
        raise RequestRejected(failure("PIE-R1001", "PUBLIC_OPERATION_REQUIRED"))
    if type(operation) is not str:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_OPERATION_TYPE"))
    refusal = None
    try:
        opened = private.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            value = store.query_operation(opened, operation)
            return None if value is None else _reply(value)
        finally:
            opened.close()
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)
