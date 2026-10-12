"""Explicit live-only same-source R2 entrypoints."""

from __future__ import annotations

from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as private_workspace
from pietto._project import project_job_extraction as extraction
from pietto._project import project_public_jobs as jobs
from pietto._project import project_public_r2_proposal as proposal
from pietto._project.project_execution_template import bind_values
from pietto.execution._errors import (
    RequestRejected,
    failure,
    request_failure,
    workspace_failure,
)
from pietto.execution._saved import SaveCloseHandle, SaveReply, _checked_request
from pietto.execution._workspace import WorkspaceRef, _reply, operation_result

__all__ = ["R2SourceInput", "recover", "save_recoverable"]

R2SourceInput = proposal.R2SourceInput
R2SourceInput.__module__ = __name__


def _request(call):
    """Project a pre-workspace refusal without retaining private context."""
    refusal = None
    try:
        return call()
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = request_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)


def _recovery_trust(query, expected_pin, accepted_producer, accepted_compatibility):
    """Rejoin caller-held public records to the live query before store reads."""
    root = query._template.artifact.request.verification.completed.root
    if (
        type(expected_pin) is not str
        or type(accepted_producer) is not str
        or type(accepted_compatibility) is not str
        or (expected_pin, accepted_producer, accepted_compatibility)
        != (root.expected_pin, root.accepted_producer, root.accepted_compatibility[-1])
    ):
        raise RequestRejected(failure("PIE-R1008", "PUBLIC_R2_TRUST"))
    return root.expected_pin, root.accepted_producer, root.accepted_compatibility


def _generation(workspace, template, binding, route, isolation, operation, job):
    if job is None:
        record = store.register_job(workspace, template, operation=operation)
        job = record.job
    else:
        record = None
    publisher = store.claim_publisher(workspace, job, operation=store.new_operation())
    try:
        bound = store.register_binding(
            publisher,
            binding,
            operation=operation if record is None else store.new_operation(),
        )
        generation = store.register_generation(
            publisher,
            bound.get("binding"),
            binding,
            route=route,
            isolation=isolation,
            operation=store.new_operation(),
        )
        return record or bound, job, generation.get("generation")
    finally:
        publisher.close()


def save_recoverable(
    workspace: WorkspaceRef,
    query,
    *,
    source_requirements: tuple[R2SourceInput, ...],
    operation: str,
    route: str,
    access,
    premise,
    limits,
    isolation: str = "stable",
    values: tuple | None = None,
    job: str | None = None,
) -> SaveReply:
    """Create an R2 generation by recording explicit retention before progress."""
    binding, supplied, private_access, private_limits, schemas = _checked_request(
        workspace,
        query,
        operation,
        route,
        access,
        premise,
        limits,
        isolation,
        values,
        job,
        allow_guard_sql=True,
    )
    prepared = _request(
        lambda: proposal.prepare_live_refinement(query, binding, source_requirements)
    )
    try:
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            expected_kind = "register_job" if job is None else "register_binding"
            expected_request = (
                store.register_job_request(query._template)
                if job is None
                else store.register_binding_request(job, binding)
            )
            previous = store.query_operation(
                opened,
                operation,
                expected_kind=expected_kind,
                expected_request=expected_request,
            )
            if previous is not None:
                return SaveReply(
                    workspace.identity,
                    _reply(previous),
                    previous.job,
                    None,
                    None,
                    "REPLY_LOST_OR_PARTIAL",
                    None,
                )
            template = query._template
            if job is not None:
                root = template.artifact.request.verification.completed.root
                template = store.load_job(
                    opened,
                    job,
                    expected_pin=root.expected_pin,
                    accepted_producer=root.accepted_producer,
                    accepted_compatibility=root.accepted_compatibility,
                )
                binding = bind_values(
                    template,
                    tuple(zip(template.slots, supplied))
                    if len(supplied) == len(template.slots)
                    else supplied,
                )
            recorded, actual_job, generation = _generation(
                opened, template, binding, route, isolation, operation, job
            )
            if recorded.observation != "COMMITTED_THIS_CALL":
                return SaveReply(
                    workspace.identity,
                    _reply(recorded),
                    actual_job,
                    None,
                    None,
                    "REPLY_LOST_OR_PARTIAL",
                    None,
                )
        finally:
            opened.close()
        state, pending = jobs.capture_recoverable(
            workspace,
            job=actual_job,
            generation=generation,
            template=template,
            route=route,
            access=private_access,
            schemas=schemas,
            limits=private_limits,
            isolation=isolation,
            values=supplied,
            source_requirements=source_requirements,
            live_r2=prepared,
        )
        return SaveReply(
            workspace.identity,
            operation_result(workspace, operation),
            actual_job,
            generation,
            state.handle,
            state.terminal or "FAILED_REMOTE_UNOBSERVED",
            state.settlement,
            None if pending is None else SaveCloseHandle(pending),
        )
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)


def recover(
    workspace: WorkspaceRef,
    *,
    job: str,
    generation: str,
    checkpoint: str | None,
    query,
    source_requirements: tuple[R2SourceInput, ...],
    operation: str,
    route: str,
    access,
    premise,
    limits,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: str,
    purpose: str,
    seconds: int,
    isolation: str = "stable",
    values: tuple | None = None,
) -> SaveReply:
    """Make one new R2 attempt; an existing operation never reruns its source."""
    if (
        type(purpose) is not str
        or not purpose
        or not purpose.isprintable()
        or len(purpose.encode("utf-8")) > extraction.MAX_PURPOSE_BYTES
    ):
        raise RequestRejected(failure("PIE-R1002", "ACCEPTANCE_PURPOSE"))
    if (
        type(seconds) is not int
        or not 1 <= seconds <= extraction.MAX_ACCEPTANCE_SECONDS
    ):
        raise RequestRejected(failure("PIE-R1002", "ACCEPTANCE_BOUND"))
    binding, supplied, private_access, private_limits, schemas = _checked_request(
        workspace,
        query,
        operation,
        route,
        access,
        premise,
        limits,
        isolation,
        values,
        job,
        allow_guard_sql=True,
    )
    prepared = _request(
        lambda: proposal.prepare_live_refinement(query, binding, source_requirements)
    )
    trust = _request(
        lambda: _recovery_trust(
            query, expected_pin, accepted_producer, accepted_compatibility
        )
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
                expected_kind="begin_continuation",
                expected_request=extraction.continuation_replay_request(
                    opened,
                    job,
                    generation,
                    checkpoint=checkpoint,
                    values=supplied,
                    expected_pin=trust[0],
                    accepted_producer=trust[1],
                    accepted_compatibility=trust[2],
                    source_requirements=source_requirements,
                    live_r2=prepared,
                ),
            )
            if previous is not None:
                return SaveReply(
                    workspace.identity,
                    _reply(previous),
                    previous.job,
                    generation,
                    None,
                    "REPLY_LOST_OR_PARTIAL",
                    None,
                )
            extraction.accept_recovery(
                opened,
                job,
                generation,
                checkpoint=checkpoint,
                purpose=purpose,
                values=supplied,
                expected_pin=trust[0],
                accepted_producer=trust[1],
                accepted_compatibility=trust[2],
                seconds=seconds,
                source_requirements=source_requirements,
                live_r2=prepared,
            )
        finally:
            opened.close()
        state, pending = jobs.recover_recoverable(
            workspace,
            job=job,
            generation=generation,
            checkpoint=checkpoint,
            template=query._template,
            route=route,
            access=private_access,
            schemas=schemas,
            limits=private_limits,
            isolation=isolation,
            values=supplied,
            trust=trust,
            purpose=purpose,
            seconds=seconds,
            source_requirements=source_requirements,
            live_r2=prepared,
            operation=operation,
        )
        return SaveReply(
            workspace.identity,
            operation_result(workspace, operation),
            job,
            generation,
            state.handle,
            state.terminal or "FAILED_REMOTE_UNOBSERVED",
            state.settlement,
            None if pending is None else SaveCloseHandle(pending),
        )
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)
