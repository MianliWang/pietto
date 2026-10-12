"""Narrow public retirement of one caller-owned unpublished generation."""

from __future__ import annotations

from pietto._project import project_job_collection as collection
from pietto._project import project_job_runtime as runtime
from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as private
from pietto._project import project_public_jobs as jobs
from pietto._project.project_compiled_loading import supported_compatibility
from pietto.execution._errors import RequestRejected, failure, workspace_failure
from pietto.execution._workspace import OperationReply, WorkspaceRef, _reply

__all__ = ["retire_generation"]


def retire_generation(
    workspace: WorkspaceRef, *, job: str, generation: str, operation: str
) -> OperationReply:
    """Retire one caller-owned unpublished generation.

    This removes only its implicit latest-checkpoint root. It never collects
    files, releases another retention, exposes a coordinator or retries a
    caller operation. A recorded incompatible job is refused before opening a
    coordinator; a replacement coordinator may still reconcile old admissions
    only through the private runtime's existing narrow allowance.
    """
    if type(workspace) is not WorkspaceRef:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_WORKSPACE_REFERENCE"))
    for value, prefix, missing, invalid in (
        (job, "job", "PUBLIC_JOB_REQUIRED", "PUBLIC_JOB_TYPE"),
        (generation, "gen", "PUBLIC_GENERATION_REQUIRED", "PUBLIC_GENERATION_TYPE"),
        (operation, "op", "PUBLIC_OPERATION_REQUIRED", "PUBLIC_OPERATION_TYPE"),
    ):
        if value is None:
            raise RequestRejected(failure("PIE-R1001", missing))
        if type(value) is not str or not private.valid_identity(value, prefix):
            raise RequestRejected(failure("PIE-R1002", invalid))
    refusal = None
    try:
        opened = private.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            record = store.job_record(opened, job)
            if record.compatibility != supported_compatibility():
                raise private.JobStoreError("JOB_COMPATIBILITY")
            if generation not in {item.identity for item in record.generations}:
                raise private.JobStoreError("GENERATION_UNKNOWN")
        finally:
            opened.close()
        budget, available_operations = jobs.runtime_capacity(workspace)
        policy = jobs.policy_for(budget, available_operations)
        coordinator = runtime.open_runtime(
            workspace.root, expected_identity=workspace.identity, policy=policy
        )
        try:
            while coordinator.reconcile():
                pass
            opened = private.open_workspace(
                workspace.root, expected_identity=workspace.identity
            )
            try:
                publisher = store.claim_publisher(
                    opened, job, operation=store.new_operation()
                )
                try:
                    return _reply(
                        collection.retire_generation(
                            publisher, generation, operation=operation
                        )
                    )
                finally:
                    publisher.close()
            finally:
                opened.close()
        finally:
            report = coordinator.close()
            if report["unjoined"]:
                raise private.JobStoreError("RUNTIME_CLOSE_UNJOINED")
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)
