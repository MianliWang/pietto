"""Read-only public observations of a saved job's recorded metadata."""

from __future__ import annotations

from dataclasses import dataclass

from pietto._project import project_job_capture as capture
from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as private_workspace
from pietto.execution._errors import RequestRejected, failure, workspace_failure
from pietto.execution._workspace import WorkspaceRef

__all__ = ["GenerationObservation", "JobObservation", "inspect_job"]


@dataclass(frozen=True, slots=True)
class GenerationObservation:
    """RECORDED metadata for one generation; it is not execution authority."""

    identity: str
    route: str
    isolation: str
    checkpoint: str | None
    frontier: int
    committed: tuple[tuple[int, int], ...]
    holes: tuple[tuple[int, int], ...]
    observed_end: int | None
    closings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class JobObservation:
    """One immutable recorded job view, in durable creation order."""

    job: str
    revision: int
    generations: tuple[GenerationObservation, ...]


def _snapshot(workspace, job, generation):
    try:
        return capture.checkpoint_snapshot(workspace, job, generation)
    except private_workspace.JobStoreError as caught:
        if str(caught) != "CAPTURE_UNKNOWN":
            raise
    return None


def _observe(workspace, job):
    before = store.job_record(workspace, job)
    closings = {
        generation.identity: tuple(
            attempt.identity
            for attempt in before.attempts
            if attempt.generation == generation.identity
            and attempt.terminal is not None
        )
        for generation in before.generations
    }
    generations = []
    for generation in before.generations:
        snapshot = _snapshot(workspace, job, generation.identity)
        if snapshot is None:
            checkpoint, frontier, committed, holes, observed_end = None, 0, (), (), None
        else:
            checkpoint = snapshot.checkpoint
            frontier = snapshot.frontier
            committed = snapshot.committed
            holes = snapshot.holes
            observed_end = snapshot.observed_end
        generations.append(
            GenerationObservation(
                generation.identity,
                generation.route,
                generation.isolation,
                checkpoint,
                frontier,
                committed,
                holes,
                observed_end,
                closings[generation.identity],
            )
        )
    after = store.job_record(workspace, job)
    if after.revision != before.revision:
        raise private_workspace.JobStoreError("JOB_REVISION")
    return JobObservation(job, before.revision, tuple(generations))


def inspect_job(workspace: WorkspaceRef, *, job: str) -> JobObservation:
    """Return recorded job metadata without opening a source or writing state.

    A result neither verifies stored members nor grants access, source, trust,
    publication, retention or recovery authority.  A concurrent job update is
    refused rather than retried or merged into an invented observation.
    """
    if type(workspace) is not WorkspaceRef:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_WORKSPACE_REFERENCE"))
    if job is None:
        raise RequestRejected(failure("PIE-R1001", "PUBLIC_JOB_REQUIRED"))
    if type(job) is not str:
        raise RequestRejected(failure("PIE-R1002", "PUBLIC_JOB_TYPE"))
    refusal = None
    try:
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            return _observe(opened, job)
        finally:
            opened.close()
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)
