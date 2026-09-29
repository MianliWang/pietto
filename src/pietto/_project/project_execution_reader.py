"""Unknown-cardinality payload checks, with no change to the finite reader law."""

from __future__ import annotations

from pietto._project import project_arrow_result as arrow
from pietto._project import project_arrow_interop as interop
from pietto._project.project_result_binding import ProducerObservation, bind_producer
from pietto._project.project_result_contract import ResultError
from pietto._project.project_sql_emission_rows import field_realization

__all__: tuple[str, ...] = ()

PG_INTS = {20: "pg_int8", 21: "pg_int2", 23: "pg_int4"}


def bind_native_projection(request, description):
    from pietto._project.project_result_binding import _columns

    columns = _columns(request.contract, request.artifact)
    if description is None or len(description) != len(columns):
        raise ResultError("EXECUTION_METADATA")
    observations = []
    for ordinal, (column, meta) in enumerate(zip(columns, description, strict=True)):
        real = field_realization(column.source_field)
        storage = PG_INTS.get(meta.type_code)
        if (
            real is None
            or storage is None
            or meta.name != column.label
            or storage != real.storage["kind"]
        ):
            raise ResultError("EXECUTION_METADATA")
        observations.append(
            ProducerObservation(
                ordinal,
                meta.name,
                "postgres",
                storage,
                int(real.domain["min"]),
                int(real.domain["max"]),
                protocol_nullable=meta.null_ok,
            )
        )
    return bind_producer(request.contract, request.artifact, tuple(observations))


class ExecutionPayloads:
    """Each returned batch is owned/checked; EOF must come from the adapter."""

    def __init__(self, request, description):
        self.request = request
        self.producer = bind_native_projection(request, description)
        self.binding = arrow.bind_arrow(self.producer)
        self.rows = self.batches = self.bytes = 0

    def accept(self, rows):
        limits = self.request.limits
        if self.rows + len(rows) > limits.max_rows:
            raise ResultError("EXECUTION_RESOURCE_LIMIT")
        managed = interop.build_managed_batch(
            self.binding,
            rows,
            limits=arrow.BatchLimits(rows=limits.batch_rows, bytes=limits.batch_bytes),
        )
        charge = max(managed.usage)
        if self.bytes + charge > limits.max_bytes:
            managed.close()
            raise ResultError("EXECUTION_RESOURCE_LIMIT")
        self.rows += len(rows)
        self.batches += 1
        self.bytes += charge
        return managed
