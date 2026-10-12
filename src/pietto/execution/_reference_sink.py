"""Public factory for a local reference-sink descriptor."""

from __future__ import annotations

from dataclasses import dataclass
import os

from pietto._project import project_job_sink as private_sink
from pietto.execution._errors import RequestRejected, failure, sink_failure


@dataclass(frozen=True, slots=True)
class ReferenceSinkDescriptor:
    """Caller-owned values; this descriptor holds no open sink resource."""

    root: str
    identity: str
    namespace: str
    epoch: int
    retention: str
    budget_bytes: int
    busy_seconds: float


def create_reference_sink(
    root,
    *,
    namespace,
    epoch,
    retention_seconds,
    budget_bytes=private_sink.DEFAULT_BUDGET,
    busy_seconds=5.0,
) -> ReferenceSinkDescriptor:
    """Create and read back one qualified local sink without retaining a handle."""
    if root is None:
        raise RequestRejected(failure("PIE-R1001", "REFERENCE_SINK_ROOT"))
    if not isinstance(root, (str, os.PathLike)):
        raise RequestRejected(failure("PIE-R1002", "REFERENCE_SINK_ROOT"))
    if type(busy_seconds) not in (int, float):
        raise RequestRejected(failure("PIE-R1002", "REFERENCE_SINK_BUSY"))
    refusal = None
    try:
        sink = private_sink.create_sink(
            os.fspath(root),
            namespace=namespace,
            epoch=epoch,
            retention_seconds=retention_seconds,
            budget_bytes=budget_bytes,
            busy_seconds=float(busy_seconds),
        )
        try:
            description = sink.describe()
            return ReferenceSinkDescriptor(
                sink.root,
                description.identity,
                description.namespace,
                description.epoch,
                sink.retention,
                sink.budget,
                float(busy_seconds),
            )
        finally:
            sink.close()
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = sink_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)
