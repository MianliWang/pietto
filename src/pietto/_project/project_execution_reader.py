"""Unknown-cardinality payload checks, with no change to the finite reader law."""

from __future__ import annotations

from pietto._project import project_arrow_result as arrow
from pietto._project import project_arrow_interop as interop
from pietto._project.project_result_binding import (
    ProducerObservation,
    TextObservation,
    DecimalObservation,
    bind_producer,
)
from pietto._project.project_result_contract import ResultError
from pietto._project.project_sql_emission_rows import field_realization

__all__: tuple[str, ...] = ()

PG_INTS = {20: "pg_int8", 21: "pg_int2", 23: "pg_int4"}


def bind_native_projection(request, description):
    from pietto._project.project_result_binding import _columns

    if request.output is not None:
        return bind_postgres_output(request.output, description)
    columns = _columns(request.contract, request.artifact, request.projection)
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
    return bind_producer(
        request.contract,
        request.artifact,
        tuple(observations),
        projection=request.projection,
    )


def bind_postgres_output(output, description):
    return bind_native_output(output, "postgres_rows", description)


def bind_native_output(output, route, metadata):
    """Check actual protocol types separately from configured scalar requirements.

    Domain bounds, Decimal precision/scale and explicit meanings below come from
    verified original requirements. Missing protocol nullability/typmods stay
    missing in the adapter's raw evidence, including empty native results.
    """
    from pietto._project.project_result_output import verify_output

    columns = verify_output(
        output, output.artifact, output.contract, binding=output.binding
    )
    family = output.artifact.request.family
    if route not in ("postgres_rows", "postgres_adbc", "mysql_rows") or family != (
        "mysql" if route == "mysql_rows" else "postgres"
    ):
        raise ResultError("EXECUTION_METADATA_ROUTE")
    if metadata is None or len(metadata) != len(columns):
        raise ResultError("EXECUTION_METADATA")
    codes = {
        "pg_int2": 21,
        "pg_int4": 23,
        "pg_int8": 20,
        "pg_bool": 16,
        "pg_float8": 701,
        "pg_text": 25,
        "pg_numeric": 1700,
        "pg_timestamp": 1114,
        "pg_uuid": 2950,
        "my_smallint": 2,
        "my_int": 3,
        "my_bigint": 8,
        "my_signed_int": 8,
        "my_bool01": 1,
        "my_signed_bool": 8,
        "my_double": 5,
        "my_varchar": 253,
        "my_utf8mb4_text": 253,
        "my_decimal": 246,
        "my_datetime": 12,
        "my_uuid_bytes": 254,
    }
    arrow_types = {
        "pg_int2": "int16",
        "pg_int4": "int32",
        "pg_int8": "int64",
        "pg_bool": "bool",
        "pg_float8": "double",
        "pg_text": "string",
        "pg_numeric": "extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>",
        "pg_timestamp": "timestamp[us]",
        "pg_uuid": "extension<arrow.opaque[storage_type=binary, type_name=uuid, vendor_name=PostgreSQL]>",
    }
    observations = []
    for column, meta in zip(columns, metadata, strict=True):
        real = column.realization
        storage = real.storage["kind"]
        if route == "postgres_rows":
            if (
                type(meta.name) is not str
                or type(meta.type_code) is not int
                or meta.name != column.label
                or meta.type_code != codes.get(storage)
            ):
                raise ResultError("EXECUTION_METADATA")
            nullable = meta.null_ok
        elif route == "mysql_rows":
            if (
                type(meta) not in (tuple, list)
                or len(meta) != 9
                or type(meta[0]) is not str
                or type(meta[1]) is not int
                or meta[0] != column.label
                or meta[1] != codes.get(storage)
                or type(meta[7]) is not int
                or not 0 <= meta[7] <= 65535
            ):
                raise ResultError("EXECUTION_METADATA")
            if real.tag == "Int" and meta[7] & 32:
                # MySQL ranks expose UNSIGNED BIGINT. A computed result whose
                # independently verified domain is within signed64's nonnegative
                # half is losslessly consumed as Int64. Source storage contracts
                # remain exact; this never widens the semantic value domain.
                if (
                    column.source_field is not None
                    or storage not in ("my_bigint", "my_signed_int")
                    or not 0
                    <= int(real.domain["min"])
                    <= int(real.domain["max"])
                    < 2**63
                ):
                    raise ResultError("EXECUTION_METADATA")
            if real.tag == "Text" and meta[8] != 309:
                raise ResultError("EXECUTION_METADATA")
            if real.tag == "UUID" and meta[8] != 63:
                raise ResultError("EXECUTION_METADATA")
            if meta[6] is not None and (
                type(meta[6]) is not int or meta[6] not in (0, 1)
            ):
                raise ResultError("EXECUTION_METADATA")
            nullable = None if meta[6] is None else meta[6] == 1
        else:
            if (
                type(meta) is not dict
                or type(meta["ordinal"]) is not int
                or type(meta["name"]) is not str
                or type(meta["type"]) is not str
                or meta["ordinal"] != column.ordinal
                or meta["name"] != column.label
                or meta["type"] != arrow_types.get(storage)
            ):
                raise ResultError("EXECUTION_METADATA")
            if real.tag in ("Decimal", "UUID"):
                typename = "numeric" if real.tag == "Decimal" else "uuid"
                if (
                    meta["metadata"].get(b"ADBC:postgresql:typname".hex())
                    != typename.encode().hex()
                ):
                    raise ResultError("EXECUTION_METADATA")
            nullable = meta["nullable"]
        options = {}
        domain, carrier = (
            real.domain["kind"],
            {
                "Int": "int",
                "Bool": "bool" if family == "postgres" else "int01",
                "Float": "float",
                "Text": "str",
                "Decimal": "decimal",
                "Timestamp": "datetime",
                "UUID": "uuid" if family == "postgres" else "bytes16",
            }[real.tag],
        )
        if real.tag == "Int":
            options.update(lower=int(real.domain["min"]), upper=int(real.domain["max"]))
        elif real.tag == "Text":
            options["text"] = TextObservation(
                real.domain["max_characters"],
                real.domain["encoding"],
                real.domain["collation"],
                real.domain["padding"],
                real.storage.get("length"),
            )
        elif real.tag == "Decimal":
            precision, scale = real.domain["precision"], real.domain["scale"]
            if route == "postgres_rows":
                for name, expected in (("precision", precision), ("scale", scale)):
                    observed = getattr(meta, name, None)
                    if observed is not None and (
                        type(observed) is not int or observed != expected
                    ):
                        raise ResultError("EXECUTION_METADATA")
            options["decimal"] = DecimalObservation(precision, scale)
        elif real.tag in ("Timestamp", "UUID"):
            options["meaning"] = column.field.meaning.law
            if real.tag == "Timestamp":
                options["fractional_seconds"] = 6
        elif real.tag == "Float":
            # Verified native window ratios have the original float64 law.
            # Their consumer retains finite binary64 and rejects NaN/Inf.
            domain = "finite_float"
        observations.append(
            ProducerObservation(
                column.ordinal,
                column.label,
                family,
                storage,
                protocol_nullable=nullable,
                domain=domain,
                carrier=carrier,
                **options,
            )
        )
    return bind_producer(
        output.contract, output.artifact, tuple(observations), output=output
    )


def decode_native_rows(output, route, metadata, rows):
    """Closed lossless transport conversions, never inferred from result labels."""
    from decimal import Decimal, InvalidOperation
    import re
    from uuid import UUID

    producer = bind_native_output(output, route, metadata)
    result = []
    for row in rows:
        if len(row) != len(producer.fields):
            raise ResultError("EXECUTION_METADATA")
        values = []
        for value, bound in zip(row, producer.fields, strict=True):
            kind = bound.field.shape.canonical.name
            if value is not None:
                if route == "postgres_adbc" and kind == "Decimal":
                    if (
                        type(value) is not str
                        or len(value) > 256
                        or re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", value) is None
                    ):
                        raise ResultError("EXECUTION_CARRIER")
                    try:
                        value = Decimal(value)
                    except InvalidOperation as exc:
                        raise ResultError("EXECUTION_CARRIER") from exc
                elif route == "postgres_adbc" and kind == "UUID":
                    if type(value) is not bytes or len(value) != 16:
                        raise ResultError("EXECUTION_CARRIER")
                    value = UUID(bytes=value)
                elif route == "mysql_rows" and kind == "Text" and type(value) is bytes:
                    try:
                        value = value.decode("utf-8", errors="strict")
                    except UnicodeDecodeError as exc:
                        raise ResultError("EXECUTION_CARRIER") from exc
            # The original scalar validator owns meaning, precision and range.
            arrow._value(value, bound)
            values.append(value)
        result.append(tuple(values))
    return producer, tuple(result)


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
