"""Tiny real Arrow readiness experiment; import is inert and Arrow stays optional."""

from __future__ import annotations

import argparse
import array
from datetime import datetime
from decimal import Decimal
import gc
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "pietto.arrow-readiness.v1"
VERSION = "25.0.1"
CASES = (
    "types",
    "carriers",
    "adaptation",
    "strings",
    "capsules",
    "alias",
    "finite",
    "ipc",
    "device",
)
LIMITS = {"rows_per_case": 32, "admitted_buffer_bytes": 8 * 1024 * 1024}


class SchemaExporter:
    def __init__(self, value):
        self.value = value

    def __arrow_c_schema__(self):
        return self.value.__arrow_c_schema__()


class ArrayExporter:
    def __init__(self, value):
        self.value = value

    def __arrow_c_array__(self, requested_schema=None):
        return self.value.__arrow_c_array__(requested_schema)


class StreamExporter:
    def __init__(self, value):
        self.value = value

    def __arrow_c_stream__(self, requested_schema=None):
        return self.value.__arrow_c_stream__(requested_schema)


def probe(pa: Any) -> dict[str, dict[str, Any]]:
    assert pa.__version__ == VERSION
    admitted = 0

    def checked(values, kind):
        nonlocal admitted
        assert len(values) <= LIMITS["rows_per_case"]
        result = pa.array(values, type=kind)
        assert result.type == kind and len(result) == len(values)
        admitted += sum(b.size for b in result.buffers() if b is not None)
        assert admitted <= LIMITS["admitted_buffer_bytes"]
        return result

    result: dict[str, dict[str, Any]] = {}

    def record(name, **observations):
        assert name not in result and observations
        result[name] = {"passed": True, "observations": observations}

    arrays = []
    for bits in (16, 32, 64):
        values = [-(2 ** (bits - 1)), 2 ** (bits - 1) - 1, None]
        item = checked(values, getattr(pa, "int" + str(bits))())
        assert item.to_pylist() == values and item.null_count == 1
        arrays.append(str(item.type))
    assert checked([True, False, None], pa.bool_()).to_pylist() == [True, False, None]
    floating = checked([0.0, -0.0, 1.25, None], pa.float64())
    assert [math.copysign(1, floating[i].as_py()) for i in (0, 1)] == [1, -1]
    assert floating[2].as_py() == 1.25 and floating[3].as_py() is None
    assert checked(["雪", "e\u0301", None], pa.string()).to_pylist() == [
        "雪",
        "e\u0301",
        None,
    ]
    decimal_values = [Decimal("1234567.89"), Decimal("-0.01"), None]
    assert checked(decimal_values, pa.decimal128(9, 2)).to_pylist() == decimal_values
    wide = Decimal("1" * 62 + ".123")
    assert checked([wide, None], pa.decimal256(65, 3)).to_pylist() == [wide, None]
    instant = datetime(2026, 1, 2, 3, 4, 5, 123456)
    timestamp = checked([instant, None], pa.timestamp("us"))
    assert (
        timestamp.type.unit == "us"
        and timestamp.type.tz is None
        and timestamp.to_pylist() == [instant, None]
    )
    identifier = uuid.UUID("12345678-1234-5678-1234-567812345678")
    binary = checked([identifier.bytes, None], pa.binary(16))
    extension = checked([identifier.bytes, None], pa.uuid())
    assert binary.type.byte_width == 16 and binary.to_pylist() == [
        identifier.bytes,
        None,
    ]
    assert extension.to_pylist() == [identifier, None]
    record(
        "types",
        integer_types=arrays,
        bool_and_nulls=True,
        finite_float64_signed_zero=True,
        unicode_exact=True,
        decimal128=[9, 2],
        decimal256=[65, 3],
        timestamp_unit="us",
        timestamp_timezone=None,
        uuid_candidates=[str(extension.type), str(binary.type)],
        upstream_meaning_proven=False,
    )

    empty = checked([], pa.int32())
    nulls = checked([None, None], pa.int32())
    duplicate = pa.record_batch(
        [checked([1], pa.int16()), checked([2], pa.int32())], names=["x", "x"]
    )
    assert len(empty) == 0 and empty.type == pa.int32() and nulls.null_count == 2
    assert (
        duplicate.schema.names == ["x", "x"]
        and duplicate.column(0)[0].as_py() == 1
        and duplicate.column(1)[0].as_py() == 2
    )
    metadata = pa.schema(
        [pa.field("n", pa.int64(), nullable=False)],
        metadata={b"pietto": b"redundant-only"},
    )
    bare = metadata.remove_metadata()
    assert metadata.equals(bare) and not metadata.equals(bare, check_metadata=True)
    try:
        raw = pa.RecordBatch.from_arrays([checked([None], pa.int64())], schema=bare)
        raw.validate(full=True)
        nullable_false_accepts_null = raw.column(0).null_count == 1
    except (pa.ArrowInvalid, pa.ArrowTypeError):
        nullable_false_accepts_null = False
    record(
        "carriers",
        zero_rows=True,
        typed_all_null=True,
        duplicate_labels_positional=True,
        schema_equal_without_metadata=True,
        schema_equal_with_metadata=False,
        nullable_false_accepts_actual_null=nullable_false_accepts_null,
        pietto_must_check_actual_nulls=True,
        source_duplicate_labels="PIE-S2305 remains unchanged",
    )

    original = checked([-32768, 32767, None], pa.int16())
    widened = original.cast(pa.int64(), safe=True)
    assert widened.type == pa.int64() and widened.to_pylist() == original.to_pylist()
    refusal = False
    try:
        checked([40000], pa.int64()).cast(pa.int16(), safe=True)
    except pa.ArrowInvalid:
        refusal = True
    assert refusal
    record(
        "adaptation",
        original_type=str(original.type),
        safe_widening=str(widened.type),
        narrowing_refused=refusal,
        product_adapter_implemented=False,
    )

    text = checked(["first", "雪", None], pa.string())
    large = checked(["first", "雪", None], pa.large_string())
    sliced = text.slice(1, 2)
    assert sliced.offset == 1 and sliced.to_pylist() == ["雪", None]
    assert large.to_pylist() == text.to_pylist() and large.type != text.type
    batch = pa.record_batch([sliced], names=["value"]).replace_schema_metadata(
        {b"note": b"transport"}
    )
    assert batch.schema.metadata == {b"note": b"transport"}
    assert batch.replace_schema_metadata(None).schema.metadata is None
    record(
        "strings",
        string_type=str(text.type),
        large_string_type=str(large.type),
        slice_offset=sliced.offset,
        metadata_retained_and_removed=True,
        default="string",
        large_string="explicit binding only",
    )

    schema_exporter = SchemaExporter(batch.schema)
    schema_imported = pa.schema(schema_exporter)
    array_exporter = ArrayExporter(text)
    array_imported = pa.array(array_exporter)
    reader = pa.RecordBatchReader.from_batches(batch.schema, [batch])
    stream_exporter = StreamExporter(reader)
    imported_reader = pa.RecordBatchReader.from_stream(stream_exporter)
    retained = imported_reader.read_next_batch()
    imported_reader.close()
    del (
        schema_exporter,
        array_exporter,
        stream_exporter,
        reader,
        imported_reader,
        batch,
        text,
    )
    gc.collect()
    assert schema_imported.names == ["value"] and schema_imported.metadata == {
        b"note": b"transport"
    }
    assert array_imported.to_pylist() == ["first", "雪", None]
    assert retained.column(0).to_pylist() == ["雪", None]
    uuid_c = pa.array(ArrayExporter(extension))
    uuid_c_preserved = uuid_c.type == extension.type and uuid_c.to_pylist() == [
        identifier,
        None,
    ]
    assert pa.array(ArrayExporter(binary)).to_pylist() == binary.to_pylist()
    record(
        "capsules",
        schema_protocol=True,
        array_protocol=True,
        stream_protocol=True,
        retained_after_exporter_and_reader_release=True,
        uuid_extension_preserved=uuid_c_preserved,
        binary16_preserved=True,
        independent_c_implementation=False,
    )

    backing = array.array("q", [1, 2, 3])
    borrowed = pa.Array.from_buffers(pa.int64(), 3, [None, pa.py_buffer(backing)])
    owned = checked(list(backing), pa.int64())
    assert borrowed.to_pylist() == owned.to_pylist() == [1, 2, 3]
    backing[0] = 9
    assert borrowed.to_pylist() == [9, 2, 3] and owned.to_pylist() == [1, 2, 3]
    del backing
    gc.collect()
    assert borrowed.to_pylist() == [9, 2, 3]
    record(
        "alias",
        external_mutation_visible=True,
        owned_copy_isolated=True,
        backing_lifetime_retained=True,
        borrowed_obligation="retain owner and prohibit external mutation",
        whole_system_zero_copy=False,
    )

    schema = pa.schema([("n", pa.int64())])

    def batches(chunks):
        return [
            pa.record_batch([checked(chunk, pa.int64())], schema=schema)
            for chunk in chunks
        ]

    reader = pa.RecordBatchReader.from_batches(
        schema, batches([[], [1, 1], [None, 2, 3]])
    )
    first = reader.read_next_batch()
    assert first.num_rows == 0
    ordered = []
    for item in reader:
        ordered.extend(item.column(0).to_pylist())
    rechunked = pa.RecordBatchReader.from_batches(
        schema, batches([[1], [1, None], [], [2, 3]])
    )
    again = [v for item in rechunked for v in item.column(0).to_pylist()]
    assert ordered == again == [1, 1, None, 2, 3]
    reader.close()
    rechunked.close()
    record(
        "finite",
        empty_batch_is_eof=False,
        rechunk_order_and_multiplicity=True,
        values=ordered,
        normal_finite_finalization=True,
        executor_success_proven=False,
    )

    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, schema) as writer:
        for item in batches([[1, 2], [3]]):
            writer.write_batch(item)
    encoded = sink.getvalue().to_pybytes()
    assert len(encoded) < LIMITS["admitted_buffer_bytes"]
    assert pa.ipc.open_stream(encoded).read_all().column(0).to_pylist() == [1, 2, 3]
    cursor = pa.BufferReader(encoded)
    pa.ipc.read_message(cursor)  # schema
    pa.ipc.read_message(cursor)  # first complete batch
    boundary = cursor.tell()
    shortened = pa.ipc.open_stream(encoded[:boundary]).read_all().column(0).to_pylist()
    assert shortened == [1, 2]
    mid_refused = False
    try:
        pa.ipc.open_stream(encoded[: boundary - 4]).read_all()
    except (pa.ArrowInvalid, OSError):
        mid_refused = True
    assert mid_refused
    uuid_batch = pa.record_batch([extension, binary], names=["extension", "binary"])
    uuid_sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(uuid_sink, uuid_batch.schema) as writer:
        writer.write_batch(uuid_batch)
    restored = pa.ipc.open_stream(uuid_sink.getvalue()).read_next_batch()
    uuid_ipc_preserved = restored.column(0).type == extension.type and restored.column(
        0
    ).to_pylist() == [identifier, None]
    assert restored.column(1).to_pylist() == binary.to_pylist()
    record(
        "ipc",
        roundtrip=True,
        mid_message_refused=mid_refused,
        boundary_truncation_accepted=True,
        boundary_rows=len(shortened),
        complete_rows=3,
        explicit_result_completeness_required=True,
        uuid_extension_preserved=uuid_ipc_preserved,
        binary16_preserved=True,
    )
    result["types"]["observations"]["uuid_choice"] = (
        "canonical-extension"
        if uuid_c_preserved and uuid_ipc_preserved
        else "explicit-binary16-logical-binding"
    )

    cpu = checked([1], pa.int64())
    assert cpu.is_cpu and all(b is None or b.is_cpu for b in cpu.buffers())
    record(
        "device",
        observed_cpu=True,
        c_array_api=hasattr(cpu, "__arrow_c_array__"),
        c_device_array_api=hasattr(cpu, "__arrow_c_device_array__"),
        device_class_available=hasattr(pa, "Device"),
        gpu_executed=False,
        future_non_cpu="explicit boundary; synthetic refusal is policy-only",
    )
    assert set(result) == set(CASES)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--run-id", default=os.environ.get("GITHUB_RUN_ID", "arrow-local")
    )
    parser.add_argument(
        "--run-attempt",
        type=int,
        default=int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
    )
    args = parser.parse_args(argv)
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    assert sys.version_info[:2] in ((3, 12), (3, 13))
    assert not args.report.exists()
    pa = importlib.import_module("pyarrow")
    context = {
        "checkout": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "python_version": platform.python_version(),
    }
    report = {
        "format": FORMAT,
        "context": context,
        "pyarrow": pa.__version__,
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "requirements_sha256": hashlib.sha256(
            (ROOT / "ci/phase67-arrow-compatibility-requirements.txt").read_bytes()
        ).hexdigest(),
        "cases": probe(pa),
        "limits": LIMITS,
        "exit_code": 0,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "pyarrow": pa.__version__,
                "python": context["python_version"],
                "cases": list(report["cases"]),
                "report": str(args.report),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
