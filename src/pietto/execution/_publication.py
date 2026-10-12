"""Public complete local publication of one saved generation."""

from __future__ import annotations

from dataclasses import dataclass
import re

from pietto._project import project_job_publication as private
from pietto._project import project_job_capture as capture
from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as job_workspace
from pietto._project.project_compiled_schema import VERSIONS
from pietto.execution._errors import RequestRejected, failure, workspace_failure
from pietto.execution._workspace import OperationReply, WorkspaceRef, _reply

__all__ = ["PublicationReply", "publish_saved_generation"]

_RECORD = re.compile("[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class PublicationReply:
    """The recorded local publication, or the initial-step lost-reply fact."""

    workspace: str
    operation: OperationReply | None
    job: str | None
    generation: str | None
    checkpoint: str | None
    closing: str | None
    extent: int | None
    retention: str | None
    terminal: str


def _required(value, detail):
    if value is None:
        raise RequestRejected(failure("PIE-R1001", detail))


def _checked(
    workspace,
    job,
    generation,
    checkpoint,
    closing,
    purpose,
    route,
    isolation,
    values,
    expected_pin,
    accepted_producer,
    accepted_compatibility,
    seconds,
    operation,
):
    if type(workspace) is not WorkspaceRef:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_WORKSPACE_REFERENCE"))
    for value, detail in (
        (job, "PUBLIC_JOB_REQUIRED"),
        (generation, "PUBLIC_GENERATION_REQUIRED"),
        (checkpoint, "PUBLIC_CHECKPOINT_REQUIRED"),
        (closing, "PUBLIC_CLOSING_REQUIRED"),
        (purpose, "PUBLIC_PURPOSE_REQUIRED"),
        (route, "PUBLIC_ROUTE_REQUIRED"),
        (isolation, "PUBLIC_ISOLATION_REQUIRED"),
        (values, "PUBLIC_VALUES_REQUIRED"),
        (expected_pin, "PUBLIC_TRUST_INPUT_REQUIRED"),
        (accepted_producer, "PUBLIC_TRUST_INPUT_REQUIRED"),
        (accepted_compatibility, "PUBLIC_TRUST_INPUT_REQUIRED"),
        (seconds, "PUBLIC_SECONDS_REQUIRED"),
        (operation, "PUBLIC_OPERATION_REQUIRED"),
    ):
        _required(value, detail)
    if not all(
        type(value) is str
        for value in (
            job,
            generation,
            checkpoint,
            closing,
            purpose,
            route,
            isolation,
            operation,
        )
    ):
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_PUBLICATION_ARGUMENT"))
    if type(values) is not tuple or type(seconds) is not int:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_PUBLICATION_ARGUMENT"))
    for value in (expected_pin, accepted_producer, accepted_compatibility):
        if type(value) is not str or _RECORD.fullmatch(value) is None:
            raise RequestRejected(failure("PIE-R1002", "PUBLIC_TRUST_INPUT_TYPE"))
    if not job_workspace.valid_identity(operation, "op"):
        raise RequestRejected(failure("PIE-R1010", "PUBLIC_OPERATION_IDENTITY"))


def publish_saved_generation(
    workspace: WorkspaceRef,
    *,
    job: str,
    generation: str,
    checkpoint: str,
    closing: str,
    purpose: str,
    route: str,
    isolation: str,
    values: tuple,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: str,
    seconds: int,
    operation: str,
) -> PublicationReply:
    """Publish one fully captured local generation.

    The caller operation records preparation.  Repeating it reports that exact
    step as partial instead of guessing whether the later visibility write ran.
    """
    _checked(
        workspace,
        job,
        generation,
        checkpoint,
        closing,
        purpose,
        route,
        isolation,
        values,
        expected_pin,
        accepted_producer,
        accepted_compatibility,
        seconds,
        operation,
    )
    refusal = None
    try:
        opened = job_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        publisher = None
        try:
            acceptance = private.accept_publication(
                opened,
                job,
                generation,
                checkpoint=checkpoint,
                closing=closing,
                purpose=purpose,
                route=route,
                isolation=isolation,
                values=values,
                expected_pin=expected_pin,
                accepted_producer=accepted_producer,
                accepted_compatibility=(*VERSIONS, accepted_compatibility),
                seconds=seconds,
            )
            previous = store.query_operation(
                opened,
                operation,
                expected_kind="retain_checkpoint",
                expected_request=capture.retain_checkpoint_request(
                    job,
                    generation,
                    checkpoint,
                    {
                        "closing": acceptance.closing,
                        "purpose": "publication-preparation",
                        "subject": acceptance.purpose,
                    },
                ),
            )
            if previous is not None:
                return PublicationReply(
                    workspace.identity,
                    _reply(previous),
                    previous.job,
                    generation,
                    checkpoint,
                    closing,
                    None,
                    None,
                    "REPLY_LOST_OR_PARTIAL",
                )
            publisher = store.claim_publisher(
                opened, job, operation=store.new_operation()
            )
            prepared = private.prepare_publication(
                publisher, acceptance, operation=operation
            )
            recorded = private.publish_generation(
                publisher, prepared, operation=store.new_operation()
            )
            return PublicationReply(
                workspace.identity,
                _reply(store.query_operation(opened, operation)),
                job,
                generation,
                recorded.get("checkpoint"),
                recorded.get("closing"),
                recorded.get("extent"),
                recorded.get("retention"),
                "PUBLISHED",
            )
        finally:
            if publisher is not None:
                publisher.close()
            opened.close()
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)
