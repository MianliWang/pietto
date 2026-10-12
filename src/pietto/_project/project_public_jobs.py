"""Narrow composition for one ordinary public saved-result capture."""

from __future__ import annotations

import math
from typing import Any

from pietto._project import project_job_runtime as runtime
from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as workspace

__all__: tuple[str, ...] = ()

_DATA_OPERATIONS = 65536 - store.CONTROL_OPERATIONS


def policy_for(budget, operations):
    """One bounded single-unit coordinator policy derived from fresh facts."""
    durable = min(64 * runtime.MIB, (budget - workspace.CONTROL_RESERVE) // 2)
    return runtime.Policy(
        connections=1,
        workers=1,
        queue=1,
        durable=durable,
        operations=operations,
    )


def runtime_capacity(workspace_ref):
    """Fresh v7 budget and data-operation allowance for one public unit."""
    verified = workspace.open_workspace(
        workspace_ref.root, expected_identity=workspace_ref.identity
    )
    try:
        budget = verified.budget
        operations = workspace.read(
            verified,
            lambda connection: connection.execute(
                "SELECT count(*) FROM operation"
            ).fetchone()[0],
        )
    finally:
        verified.close()
    available = min(
        _DATA_OPERATIONS - operations,
        store.LIMITS["operation"] - store.CONTROL_OPERATIONS - operations,
    )
    if available <= 0:
        raise workspace.JobStoreError("RUNTIME_UNIT_BOUND")
    return budget, available


def register_generation(
    workspace_ref, template, binding, route, isolation, operation, job
):
    """Persist the caller's first operation, then the remaining immutable setup."""
    if job is None:
        registered = store.register_job(workspace_ref, template, operation=operation)
        job = registered.job
    else:
        registered = None
    publisher = store.claim_publisher(
        workspace_ref, job, operation=store.new_operation()
    )
    try:
        record = store.register_binding(
            publisher,
            binding,
            operation=operation if registered is None else store.new_operation(),
        )
        generation = store.register_generation(
            publisher,
            record.get("binding"),
            binding,
            route=route,
            isolation=isolation,
            operation=store.new_operation(),
        )
        return registered or record, job, generation.get("generation")
    finally:
        publisher.close()


class PendingClose:
    """The private retained runtime of one public operation awaiting relief."""

    __slots__ = ("runtime", "handle")

    def __init__(self, opened: Any, handle: str):
        self.runtime, self.handle = opened, handle

    def close(self):
        opened = self.runtime
        if opened is None:
            return None
        opened.resume(self.handle)
        state = opened.wait(self.handle, 1.0)
        if state.terminal is None:
            raise workspace.JobStoreError("RUNTIME_CLOSE_UNJOINED")
        report = opened.close()
        if report["unjoined"]:
            raise workspace.JobStoreError("RUNTIME_CLOSE_UNJOINED")
        self.runtime = None
        return state


def capture(
    workspace_ref,
    *,
    job,
    generation,
    template,
    route,
    access,
    schemas,
    limits,
    isolation,
    values,
):
    """Run the one private CAPTURE unit to its recorded terminal state."""
    budget, available_operations = runtime_capacity(workspace_ref)
    pending = False
    policy = policy_for(budget, available_operations)
    opened = runtime.open_runtime(
        workspace_ref.root, expected_identity=workspace_ref.identity, policy=policy
    )
    try:
        while opened.reconcile():
            pass
        source = runtime.NativeSource(route, access, schemas, limits, isolation)
        unit = runtime.Unit(
            "CAPTURE",
            workspace_ref.root,
            workspace_ref.identity,
            job,
            generation,
            trust=(),
            seconds=max(1, math.ceil(limits.seconds)),
            values=values,
            source=source,
            durable=policy.durable,
            operations=policy.operations,
            template=template,
        )
        handle = opened.submit(unit)
        while True:
            state = opened.wait(handle, 1.0)
            if state.terminal is not None:
                return state, None
            if state.activity == "WAITING_FOR_CLEANUP":
                pending = True
                return state, PendingClose(opened, handle)
    finally:
        if not pending:
            report = opened.close()
            if report["unjoined"]:
                raise workspace.JobStoreError("RUNTIME_CLOSE_UNJOINED")
