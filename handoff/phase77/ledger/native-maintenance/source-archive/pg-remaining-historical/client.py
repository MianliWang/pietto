"""One R3 public-route and raw-driver observation through the R3 relay.

Password arrives only on standard input. The script records data and terminal
facts; its judge, not this client, decides the frozen acceptance matrix.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import importlib.metadata
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import threading
import time


HERE = Path(__file__).resolve().parent


def _value(value):
    if isinstance(value, datetime):
        return {"kind": "datetime", "value": value.isoformat(timespec="microseconds")}
    if isinstance(value, list):
        return {"kind": "list", "items": [_value(item) for item in value]}
    return {"kind": type(value).__name__, "value": str(value)}


def _identity():
    import pietto

    names = (
        "pietto",
        "pyarrow",
        "psycopg",
        "psycopg-binary",
        "adbc-driver-postgresql",
        "adbc-driver-manager",
    )
    result = {
        name: {
            "version": importlib.metadata.version(name),
            "origin": str(importlib.metadata.distribution(name).locate_file("")),
        }
        for name in names
    }
    distribution = importlib.metadata.distribution("pietto")
    result["pietto"]["direct_url"] = distribution.read_text("direct_url.json")
    result["pietto"]["module"] = str(Path(pietto.__file__).resolve())
    result["pietto"]["record"] = str(
        distribution.locate_file("pietto-0.1.10.dist-info/RECORD")
    )
    return result


def _error(error):
    return {
        "type": type(error).__name__,
        "code": getattr(error, "code", None),
        "detail": getattr(error, "detail", None),
        "text": str(error),
    }


def _query(project, name, contract):
    from pietto.execution import compile_query

    return compile_query(
        str(project),
        module="main.pietto",
        kind="table",
        name=name,
        dialect="postgres",
        emission_contract=contract,
    )


def _access(port, password, ca_file):
    from pietto.execution import PostgresAccess

    return PostgresAccess(
        "127.0.0.1", port, "app", "pietto_reader", password, "require", str(ca_file)
    )


def _premise():
    from pietto.execution import PostgresDeploymentPremise

    return PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))


def _public_rows(query, access):
    import pyarrow as pa
    from pietto.execution import ExecutionLimits, execute

    result = {}
    handle = execute(
        query,
        route="postgres_rows",
        access=access,
        premise=_premise(),
        limits=ExecutionLimits(batch_rows=1, max_rows=4),
    )
    batches, batch_rows, rows = [], [], []
    try:
        for batch in handle:
            with batch:
                converted = pa.record_batch(batch)
                batches.append([str(field.type) for field in converted.schema])
                batch_rows.append(batch.num_rows)
                rows.extend(converted.to_pylist())
    except BaseException as error:
        result["bounded_error"] = _error(error)
    finally:
        handle.close()
    result["bounded"] = {"batches": batches, "batch_rows": batch_rows, "rows": rows, "outcome": asdict(handle.outcome)}

    limited = execute(
        query,
        route="postgres_rows",
        access=access,
        premise=_premise(),
        limits=ExecutionLimits(batch_rows=1, max_rows=3),
    )
    delivered = 0
    try:
        for batch in limited:
            with batch:
                delivered += batch.num_rows
    except BaseException as error:
        result["limit_error"] = _error(error)
    finally:
        limited.close()
    result["limit"] = {"delivered": delivered, "outcome": asdict(limited.outcome)}

    early = execute(
        query,
        route="postgres_rows",
        access=access,
        premise=_premise(),
        limits=ExecutionLimits(batch_rows=1, max_rows=4),
    )
    first = next(early)
    with first:
        result["early_first_rows"] = first.num_rows
        result["early_first"] = pa.record_batch(first).to_pylist()
    early.close()
    result["early"] = asdict(early.outcome)

    cancelled = execute(
        query,
        route="postgres_rows",
        access=access,
        premise=_premise(),
        limits=ExecutionLimits(batch_rows=1, max_rows=4),
    )
    first = next(cancelled)
    with first:
        result["cancel_first_rows"] = first.num_rows
        result["cancel_first"] = pa.record_batch(first).to_pylist()
    answer = {}

    def cancel():
        answer["reply"] = cancelled.cancel()

    control = threading.Thread(target=cancel, name="p77-maint-public-cancel")
    control.start()
    control.join(10)
    result["cancel_control_joined"] = not control.is_alive()
    try:
        next(cancelled)
    except StopIteration:
        result["cancel_next"] = "eof"
    except BaseException as error:
        result["cancel_error"] = _error(error)
    finally:
        cancelled.close()
    result["cancel"] = {"reply": answer.get("reply"), "outcome": asdict(cancelled.outcome)}
    return result


def _timestamp(query, access):
    import pyarrow as pa
    from pietto.execution import execute

    handle = execute(query, route="postgres_rows", access=access, premise=_premise())
    values, schema = [], None
    try:
        for batch in handle:
            with batch:
                converted = pa.record_batch(batch)
                schema = [str(field.type) for field in converted.schema]
                values.extend(_value(row["occurred_at"]) for row in converted.to_pylist())
    finally:
        handle.close()
    return {"schema": schema, "values": values, "outcome": asdict(handle.outcome)}


def _adbc(query, access):
    import pyarrow as pa
    from pietto.execution import ExecutionLimits, execute

    handle = execute(
        query,
        route="postgres_adbc",
        access=access,
        premise=_premise(),
        limits=ExecutionLimits(batch_rows=1, max_rows=4),
    )
    first = next(handle)
    converted = pa.record_batch(first)
    before = {"schema": [str(field.type) for field in converted.schema], "rows": converted.to_pylist()}
    first.close()
    after = {"schema": [str(field.type) for field in converted.schema], "rows": converted.to_pylist()}
    remainder = []
    try:
        for batch in handle:
            with batch:
                remainder.extend(pa.record_batch(batch).to_pylist())
    finally:
        handle.close()
    return {"before_close": before, "after_close": after, "public_batch_closed": first.closed, "handle_closed": handle.closed, "remainder": remainder, "outcome": asdict(handle.outcome)}


def _raw_driver(port, password, ca_file):
    child = subprocess.Popen(
        [sys.executable, "-I", str(HERE / "raw_driver_child.py"), str(port), str(ca_file)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    assert child.stdin and child.stdout and child.stderr
    child.stdin.write((password + "\n").encode())
    child.stdin.close()
    selector = selectors.DefaultSelector()
    for stream in (child.stdout, child.stderr):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ)
    output = {child.stdout: bytearray(), child.stderr: bytearray()}
    overflow = timeout = False
    deadline = time.monotonic() + 20
    try:
        while selector.get_map():
            if time.monotonic() >= deadline:
                timeout = True
                child.kill()
            for key, _ in selector.select(max(0, min(0.2, deadline - time.monotonic()))):
                data = os.read(key.fd, 4097)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                if len(output[key.fileobj]) + len(data) > 4096:
                    overflow = True
                    child.kill()
                    selector.unregister(key.fileobj)
                else:
                    output[key.fileobj].extend(data)
        child.wait(timeout=5)
    finally:
        selector.close()
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
    stdout = bytes(output[child.stdout]).decode("utf-8", "replace")
    stderr = bytes(output[child.stderr]).decode("utf-8", "replace")
    result = {"returncode": child.returncode, "stdout": stdout, "stderr": stderr, "stdout_bytes": len(stdout.encode()), "stderr_bytes": len(stderr.encode()), "capture_overflow": overflow, "timed_out": timeout}
    try:
        result["record"] = json.loads(stdout)
    except (TypeError, json.JSONDecodeError):
        result["record"] = None
    return result


def main(port_text):
    password = sys.stdin.readline().rstrip("\n")
    port = int(port_text)
    ca = HERE / "tls" / "ca.pem"
    active = _query(HERE / "in" / "ordered-exec", "active_items", "contract.json")
    timestamp = _query(HERE / "in" / "timestamp-exec", "timestamp_rows", "contract.json")
    access = _access(port, password, ca)
    record = {"identity": _identity(), "active_sql": json.loads(active.emission)["sql"], "timestamp_sql": json.loads(timestamp.emission)["sql"]}
    try:
        record["rows"] = _public_rows(active, access)
        record["timestamp"] = _timestamp(timestamp, access)
        record["adbc"] = _adbc(active, access)
        record["raw_driver"] = _raw_driver(port, password, ca)
    except BaseException as error:
        record["fatal"] = {"type": type(error).__name__, "text": str(error)}
    print(json.dumps(record, sort_keys=True, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:2])
