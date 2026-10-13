"""Installed-consumer and real PostgreSQL 18.6 witnesses of the public
execution alpha; importing acquires nothing.

Run explicitly where the premises hold (Validation Runner Acceptance R4 row 7
for both families; row 4, Docker with the pinned image, for `postgres`):

    python tests/_pietto_execution_api_probe.py consumer --directory NEW \\
        --wheel WHEEL --interpreter CPYTHON [--house DIR] [--cache DIR]
    python tests/_pietto_execution_api_probe.py postgres --directory NEW \\
        --wheel WHEEL --interpreter CPYTHON [--house DIR] [--cache DIR]
    python tests/_pietto_execution_api_probe.py check --report REPORT

Each family materializes fresh prefixes of the exact wheel from the verified
wheelhouse of the lock's artifacts (the S18 recipe; `--house` reuses an
existing one), runs the documented examples and the case workers there as
fresh `-I -B` interpreters with a clean environment (no forced
`PSYCOPG_IMPL`), the configuration and passwords on standard input and an
unrelated working directory, writes raw facts to `report.json` and exits
non-zero when the independent checker `_pietto_execution_api_check` rejects
them. The `postgres` fixture follows the documented server setup: the
documented relation, reader role and `\\password` exchange, TLS on, and the
documented `hostssl`/`host` pg_hba.conf lines (database and client address
replaced, since Docker's gateway rather than 127.0.0.1 reaches the server).
Query bundles are exported, loaded, refused and re-run under a changed copy
of the code in `consumer`, and in `postgres` one bundle whose project is
deleted is loaded once and run step by step while the reader's privilege is
revoked and granted again. Ordinary pytest never runs a family; it runs the
consumer cases against the checkout and the checker.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "pietto.execution-api-witness.v1"
AMBIENT = (
    "PGHOST",
    "PGPASSWORD",
    "PGSERVICE",
    "SSLKEYLOGFILE",
    "OPENSSL_CONF",
    "OPENSSL_MODULES",
)
ROWS = ((0, "zero"), (1, "one"), (2, "two"), (2, "two"), (3, "three"), (5, "five"))
WIDE_ROWS = ((2, "two"), (1000, "out of domain"))
# Roles of the PostgreSQL fixture and the pg_hba.conf method each one meets.
ROLES = {
    "pietto_reader": "scram-sha-256",
    "pietto_trust": "trust",
    "pietto_cleartext": "password",
    "pietto_md5": "md5",
}


def hba():
    """pg_hba.conf of the fixture, first match wins: the refused methods, the
    documented reader lines with the database and the client address
    replaced, then the fixture's own manager."""
    from _pietto_execution_api import setup_blocks

    reader: list[str] = []
    for line in setup_blocks()["conf"].splitlines():
        if line.strip() and not line.startswith("#"):
            kind, _database, user, _address, method = line.split()
            documented = " ".join((kind, "phase66", user, "all", method))
            if documented not in reader:
                reader.append(documented)
    return (
        "local all all trust",
        "host all pietto_trust all trust",
        "host all pietto_cleartext all password",
        "host all pietto_md5 all md5",
        *reader,
        "host all pietto_manager all scram-sha-256",
    )


WORKER = r"""
import gc, json, os, sys, threading, time, warnings
from pathlib import Path
config = json.loads(sys.stdin.readline())
for entry in reversed(config.get("path", ())):
    sys.path.insert(0, entry)
case = config["case"]
result = {"case": case}
def records(bundle):
    return dict(expected_pin=bundle.pin, accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility)
if case == "identity":
    from importlib.metadata import version
    from pietto._project.project_compiled_loading import semantic_build_identity
    import pietto.execution as pe
    exported = pe.export_bundle(pe.compile_query(config["project"],
        module="main.pietto", kind="table", name="active_items", dialect="postgres",
        emission_contract="contract.json", literal_policy="bind-safe"))
    bundled = pe.load_bundle(exported.payload, **records(exported))
    result.update(identity=semantic_build_identity(),
        metadata=version("antlr4-python3-runtime"),
        records=[exported.pin, exported.producer, exported.compatibility],
        origin=bundled.origin)
    print(json.dumps(result))
    raise SystemExit(0)
DRIVERS = {"psycopg", "psycopg_binary", "pyarrow"}
def loaded():
    return sorted({m.split(".")[0] for m in sys.modules} & DRIVERS)
import pietto.execution as pe
result["after_import"] = loaded()
password = config["password"]
def facts(outcome):
    p = outcome.primary
    return {"end": outcome.end, "source": outcome.source,
        "transaction": outcome.transaction, "delivery": outcome.delivery,
        "cleanup": outcome.cleanup, "remote": outcome.remote_source_use_end,
        "rows": outcome.rows, "batches": outcome.batches,
        "cancel": [outcome.cancel_requested, outcome.cancel_sent, outcome.cancel_observed],
        "primary": None if p is None else [p.code, p.detail, p.phase, p.sqlstate, p.cause],
        "cleanup_failures": [[f.code, f.phase, f.cause] for f in outcome.cleanup_failures]}
def effects():
    roots = {"cwd": os.getcwd(), "home": os.environ.get("HOME", ""),
        "tmp": os.environ.get("TMPDIR", "")}
    return {"threads": sorted(t.name for t in threading.enumerate()),
        "jobs": sorted(m for m in sys.modules if m.startswith("pietto._project.project_job")),
        "files": {name: sorted(str(p.relative_to(root)) for p in Path(root).rglob("*"))
            for name, root in roots.items() if root}}
def refusal(error):
    return {"code": error.code, "detail": error.detail, "cause": error.failure.cause,
        "sqlstate": error.failure.sqlstate, "shown": password in str(error),
        "chained": error.__cause__ is not None or error.__context__ is not None,
        "outcome": None if error.outcome is None else facts(error.outcome)}
def rejected(call):
    try:
        call()
    except pe.RequestRejected as error:
        return [error.code, error.detail, password in str(error) + repr(error),
            error.__cause__ is not None or error.__context__ is not None]
    return None
query = pe.compile_query(config["project"], module="main.pietto", kind="table",
    name="active_items", dialect="postgres", emission_contract="contract.json",
    literal_policy=config.get("policy", "preserve"))
if config.get("load_bundle"):
    exported = pe.export_bundle(query)
    query = pe.load_bundle(exported.payload, **records(exported))
result["origin"] = query.origin
access = pe.PostgresAccess(config.get("host", "127.0.0.1"), config["port"],
    config.get("database", "phase66"), config.get("user", "pietto_reader"),
    password, config.get("sslmode", "require"))
premise = pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
limits = pe.ExecutionLimits(**config.get("limits", {}))
def attempt(**changes):
    arguments = dict(route="postgres_rows", access=access, premise=premise,
        limits=limits)
    if "values" in config:
        arguments["values"] = tuple(config["values"])
    arguments.update(changes)
    return pe.execute(query, **arguments)
handle = attempt()
result["unopened"] = [loaded(), handle.outcome.end, password in repr(handle)]
if case == "schema_refused":
    try:
        handle.__arrow_c_schema__()
    except pe.HandleMisuse as error:
        result["schema"] = refusal(error)
elif case == "cancelled":
    result["cancel_return"] = handle.cancel() is None
    try:
        with handle:
            pass
    except pe.AttemptFailed as error:
        result.update(refusal(error))
elif case == "requests":
    refusals = {}
    for name, changes in (("premise_none", {"premise": None}),
            ("route_unknown", {"route": "postgres_unknown"}),
            ("socket_host", {"access": pe.PostgresAccess("/var/run/postgresql",
                5432, "phase66", "pietto_reader", password)})):
        try:
            attempt(**changes)
            refusals[name] = None
        except pe.RequestRejected as error:
            refusals[name] = [error.code, error.detail, password in str(error)]
    try:
        pe.execute("SELECT * FROM fixture.items", route="postgres_rows",
            access=access, premise=premise)
        refusals["sql_text"] = None
    except pe.RequestRejected as error:
        refusals["sql_text"] = [error.code, error.detail, False]
    result["refusals"] = refusals
elif case == "refused":
    try:
        with handle:
            result["opened"] = True
    except pe.AttemptFailed as error:
        result.update(refusal(error))
    result["after_open"] = loaded()
    psycopg = sys.modules.get("psycopg")
    result["psycopg_file"] = getattr(psycopg, "__file__", None)
elif case == "rows":
    import pyarrow as pa

    rows = []
    result["before"] = effects()
    result["schema"] = [[field.name, str(field.type), field.nullable] for field in pa.schema(handle)]
    result["schema_preopen"] = {
        "closed": handle.closed,
        "end": handle.outcome.end,
        "loaded": loaded(),
    }
    with handle:
        for batch in handle:
            with batch:
                rows.extend(pa.record_batch(batch).to_pylist())
    result.update(rows=sorted([r["id"], r["label"]] for r in rows),
        outcome=facts(handle.outcome), after=effects())
elif case == "early_stop":
    result["before"] = effects()
    with handle:
        first = next(handle)
        result["first_rows"] = first.num_rows
        first.close()
    result.update(outcome=facts(handle.outcome), after=effects())
elif case == "interrupt":
    try:
        with handle:
            raise KeyboardInterrupt
    except KeyboardInterrupt:
        result["reraised"] = True
    result["outcome"] = facts(handle.outcome)
elif case == "buffer":
    import pyarrow as pa

    with handle:
        batch = next(handle)
        with batch:
            result["first_row"] = pa.record_batch(batch).to_pylist()
        result["delivered_rows"] = batch.num_rows
        result["native_buffered_rows"] = handle._owner.native_buffered_rows
        try:
            next(handle)
        except StopIteration:
            result["second"] = "EOF"
        except pe.AttemptFailed as error:
            result.update(second="REFUSED", failure=refusal(error))
    result["outcome"] = facts(handle.outcome)
elif case == "failure":
    started = time.monotonic()
    try:
        with handle:
            result["opened"] = time.monotonic() - started
            for batch in handle:
                batch.close()
        result["completed"] = True
    except pe.AttemptFailed as error:
        result.update(refusal(error))
    result["seconds"] = time.monotonic() - started
elif case == "dropped":
    handle.__enter__()
    next(handle).close()
    attempt_id = handle.attempt
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        del handle
        gc.collect()
    result["warnings"] = [[w.message.code, w.message.outcome.end,
        w.message.outcome.attempt == attempt_id] for w in caught
        if isinstance(w.message, pe.UnclosedHandleWarning)]
    result["dropped_at"] = time.monotonic()
elif case == "bundles":
    import hashlib
    from pietto._project.project_compiled_schema import content_pin
    first, second = pe.export_bundle(query), pe.export_bundle(query)
    bundled = pe.load_bundle(first.payload, **records(first))
    again = pe.export_bundle(bundled)
    handles = [pe.execute(bundled, route="postgres_rows", access=access,
        premise=premise, values=(3,)) for _ in range(2)]
    other = pe.export_bundle(pe.compile_query(config["other"], module="main.pietto",
        kind="table", name="active_items", dialect="postgres",
        emission_contract="contract.json", literal_policy="bind-safe"))
    tampered = first.payload.replace(b'"1"]', b'"7"]', 1)
    sql = b"SELECT * FROM fixture.items"
    def loading(payload, **changes):
        return lambda: pe.load_bundle(payload, **{**records(first), **changes})
    def running(values):
        return lambda: pe.execute(bundled, route="postgres_rows", access=access,
            premise=premise, values=values)
    refusals = {name: rejected(call) for name, call in (
        ("tampered", loading(tampered)),
        ("truncated", loading(first.payload[:-1])),
        ("sql_self_pinned", loading(sql, expected_pin=content_pin(sql))),
        ("mixed_records", loading(first.payload, accepted_producer=other.producer)),
        ("foreign_compatibility", loading(first.payload,
            accepted_compatibility="0" * 64)),
        ("pin_none", loading(first.payload, expected_pin=None)),
        ("bundle_as_pin", loading(first.payload, expected_pin=first)),
        ("upper_pin", loading(first.payload, expected_pin=first.pin.upper())),
        ("payload_text", loading(first.payload.decode())),
        ("payload_bytearray", loading(bytearray(first.payload))),
        ("payload_empty", loading(b"")),
        ("export_bytes", lambda: pe.export_bundle(first.payload)),
        ("value_bool", running((True,))),
        ("value_count", running((3, 4))),
        ("values_list", running([3])))}
    after = pe.export_bundle(bundled)
    result.update(records=[first.pin, first.producer, first.compatibility],
        payload_sha256=hashlib.sha256(first.payload).hexdigest(),
        equal=[first == second, first == again, first == after],
        loaded={"origin": bundled.origin, "module": bundled.module,
            "kind": bundled.kind, "name": bundled.name, "dialect": bundled.dialect,
            "release": bundled.release, "literal_policy": bundled.literal_policy,
            "slots": list(bundled.slots), "emission": bundled.emission},
        attempts=[h.attempt for h in handles], ends=[h.outcome.end for h in handles],
        password_in_payload=password.encode() in after.payload,
        refusals=refusals, after=loaded())
elif case == "export":
    exported = pe.export_bundle(query)
    Path(config["bundle_path"]).write_bytes(exported.payload)
    result["records"] = records(exported)
elif case == "code_export":
    import shutil
    import pietto
    exported = pe.export_bundle(query)
    Path(config["bundle_path"]).write_bytes(exported.payload)
    copy = Path(config["changed"]) / "pietto"
    shutil.copytree(Path(pietto.__file__).parent, copy,
        ignore=shutil.ignore_patterns("__pycache__"))
    with open(copy / "__init__.py", "a", encoding="utf-8") as stream:
        stream.write("# changed by the code_change witness\n")
    result.update(records=records(exported), imported=pietto.__file__)
elif case == "code_run":
    import pietto
    result["imported"] = pietto.__file__
    # Only ever edit the copy: refuse before touching any file otherwise.
    if not Path(pietto.__file__).resolve().is_relative_to(
            Path(config["path"][0]).resolve()):
        raise SystemExit("CODE_RUN_NOT_THE_COPY")
    old, accepted = Path(config["bundle_path"]).read_bytes(), config["records"]
    own = pe.export_bundle(query)
    bundled = pe.load_bundle(own.payload, **records(own))
    refusals = {
        "old_records": rejected(lambda: pe.load_bundle(old, **accepted)),
        "relabeled": rejected(lambda: pe.load_bundle(old,
            **{**accepted, "accepted_compatibility": own.compatibility}))}
    with open(pietto.__file__, "a", encoding="utf-8") as stream:
        stream.write("# changed again by the code_change witness\n")
    refusals.update(execute_live=rejected(attempt),
        execute_loaded=rejected(lambda: pe.execute(bundled, route="postgres_rows",
            access=access, premise=premise)),
        records_after_change=rejected(lambda: pe.load_bundle(own.payload,
            **records(own))))
    result.update(refusals=refusals, own_load=bundled.origin,
        compatibility_changed=own.compatibility != accepted["accepted_compatibility"])
print(json.dumps(result), flush=True)
"""

MYSQL_WORKER = r"""
import json, os, sys
from pathlib import Path
config = json.loads(sys.stdin.readline())
for entry in reversed(config.get("path", ())):
    sys.path.insert(0, entry)
from _pietto_execution_rows_cases import build
from pietto._project.project_execution_template import prepare_live_template
from pietto.execution._query import _query
import pietto.execution as pe
result = {"case": config["case"]}
drivers = {"mysql", "psycopg", "pyarrow"}
def loaded():
    return sorted({m.split(".")[0] for m in sys.modules} & drivers)
def refused(call):
    try:
        call()
    except pe.ExecutionError as error:
        return [error.code, error.detail, error.__cause__ is not None or error.__context__ is not None]
    return None
outcome = build(Path(config["work"]), "mysql", "G_emission_table_bag", "bag")
if outcome.status != "VERIFIED" or outcome.artifact is None:
    raise SystemExit("MYSQL_TEMPLATE")
query = _query(prepare_live_template(outcome.artifact), "live", b"")
access = pe.MySQLAccess("127.0.0.1", config["port"], "phase66", "pietto_query",
    config["password"], "/explicit/ca.pem", "pietto_query@%")
premise = pe.MySQLDeploymentPremise(schemas=("phase66",))
def attempt():
    return pe.execute(query, route="mysql_rows", access=access, premise=premise)
result["before"] = loaded()
try:
    handle = attempt()
except pe.ExecutionError as error:
    result["request"] = [error.code, error.detail, error.__cause__ is not None or error.__context__ is not None]
else:
    result["unopened"] = [loaded(), handle.outcome.end, config["password"] in repr(handle)]
    result["open"] = refused(lambda: handle.__enter__())
result["after"] = loaded()
print(json.dumps(result), flush=True)
"""

ADBC_WORKER = r"""
import json, sys
config = json.loads(sys.stdin.readline())
for entry in reversed(config.get("path", ())):
    sys.path.insert(0, entry)
import pietto.execution as pe
result = {"case": config["case"]}
drivers = {"adbc_driver_manager", "adbc_driver_postgresql", "psycopg", "pyarrow"}
def loaded():
    return sorted({m.split(".")[0] for m in sys.modules} & drivers)
def refusal(error):
    return [error.code, error.detail, error.__cause__ is not None or error.__context__ is not None]
query = pe.compile_query(config["project"], module="main.pietto", kind="table",
    name="active_items", dialect="postgres", emission_contract="contract.json")
access = pe.PostgresAccess("127.0.0.1", config["port"], "phase66", "pietto_reader",
    config["password"], "require")
premise = pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
def attempt():
    return pe.execute(query, route="postgres_adbc", access=access, premise=premise)
result["before"] = loaded()
try:
    handle = attempt()
except pe.ExecutionError as error:
    result["request"] = refusal(error)
else:
    result["unopened"] = [loaded(), handle.outcome.end, config["password"] in repr(handle)]
    try:
        handle.__enter__()
    except pe.ExecutionError as error:
        result["open"] = refusal(error)
result["after"] = loaded()
print(json.dumps(result), flush=True)
"""

CANCEL = r"""
import json, sys, threading
config = json.loads(sys.stdin.readline())
import pietto.execution as pe
query = pe.compile_query(config["project"], module="main.pietto", kind="table",
    name="active_items", dialect="postgres", emission_contract="contract.json")
access = pe.PostgresAccess("127.0.0.1", config["port"], "phase66", "pietto_reader",
    config["password"], "require")
premise = pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
handle = pe.execute(query, route="postgres_rows", access=access, premise=premise,
    limits=pe.ExecutionLimits(seconds=20))
done = threading.Event()
result = {}
def facts(outcome):
    p = outcome.primary
    return {"end": outcome.end, "source": outcome.source,
        "transaction": outcome.transaction, "delivery": outcome.delivery,
        "cleanup": outcome.cleanup, "remote": outcome.remote_source_use_end,
        "rows": outcome.rows, "batches": outcome.batches,
        "cancel": [outcome.cancel_requested, outcome.cancel_sent, outcome.cancel_observed],
        "primary": None if p is None else [p.code, p.detail, p.phase, p.sqlstate, p.cause],
        "cleanup_failures": [[f.code, f.phase, f.cause] for f in outcome.cleanup_failures]}
def consume():
    try:
        with handle:
            next(handle)
    except pe.AttemptFailed as error:
        result.update(code=error.code, detail=error.detail,
            chained=error.__cause__ is not None or error.__context__ is not None,
            shown=config["password"] in str(error))
    finally:
        done.set()
thread = threading.Thread(target=consume, name="pietto-manual-cancel-consumer")
thread.start()
print(json.dumps({"ready": handle.attempt}), flush=True)
if sys.stdin.readline() != "cancel\n":
    raise SystemExit("CANCEL_GATE")
result["cancel_return"] = handle.cancel() is None
thread.join(30)
if thread.is_alive():
    raise SystemExit("CANCEL_THREAD")
result["outcome"] = facts(handle.outcome)
print(json.dumps(result), flush=True)
"""

# One worker loads the exported bundle once, then runs each step on that same
# loaded query when the harness sends `go`.
STEPS = r"""
import json, os, sys, threading
from pathlib import Path
config = json.loads(sys.stdin.readline())
import pietto.execution as pe
query = pe.load_bundle(Path(config["payload"]).read_bytes(), **config["records"])
print(json.dumps({"loaded": {"origin": query.origin, "module": query.module,
    "kind": query.kind, "name": query.name, "dialect": query.dialect,
    "release": query.release, "literal_policy": query.literal_policy,
    "slots": list(query.slots), "emission": query.emission},
    "source_present": os.path.exists(config["source"])}), flush=True)
import pyarrow as pa
passwords = config["passwords"]
premise = pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
def facts(outcome):
    p = outcome.primary
    return {"end": outcome.end, "transaction": outcome.transaction,
        "primary": None if p is None else [p.code, p.detail, p.phase, p.sqlstate]}
for step in config["steps"]:
    if sys.stdin.readline() != "go\n":
        raise SystemExit("STEP_GATE")
    record = {"step": step["name"], "attempt": None}
    access = pe.PostgresAccess("127.0.0.1", config["port"], "phase66", step["user"],
        passwords[step["user"]], "require")
    try:
        handle = pe.execute(query, route="postgres_rows", access=access,
            premise=premise, values=(step["value"],))
        record["attempt"] = handle.attempt
        rows = []
        with handle:
            for batch in handle:
                with batch:
                    rows.extend(pa.record_batch(batch).to_pylist())
        record["rows"] = sorted([r["id"], r["label"]] for r in rows)
    except pe.ExecutionError as error:
        record.update(code=error.code, detail=error.detail,
            sqlstate=error.failure.sqlstate,
            shown=any(p in str(error) + repr(error) for p in passwords.values()),
            chained=error.__cause__ is not None or error.__context__ is not None)
    if record["attempt"] is not None:
        record["outcome"] = facts(handle.outcome)
    print(json.dumps(record), flush=True)
roots = {"cwd": os.getcwd(), "home": os.environ.get("HOME", ""),
    "tmp": os.environ.get("TMPDIR", "")}
print(json.dumps({"threads": sorted(t.name for t in threading.enumerate()),
    "jobs": sorted(m for m in sys.modules if m.startswith("pietto._project.project_job")),
    "files": {name: sorted(str(p.relative_to(root)) for p in Path(root).rglob("*"))
        for name, root in roots.items() if root}}), flush=True)
"""
# Steps of the loaded bundle: values, a refused role, the reader's privilege
# revoked and granted again by the manager before the step, a refused value.
BUNDLE_STEPS = (
    {"name": "first", "user": "pietto_reader", "value": 1},
    {"name": "other_role", "user": "pietto_md5", "value": 1},
    {"name": "revoked", "user": "pietto_reader", "value": 1},
    {"name": "granted", "user": "pietto_reader", "value": 3},
    {"name": "refused_value", "user": "pietto_reader", "value": True},
    {"name": "again", "user": "pietto_reader", "value": 1},
)
PRIVILEGE = {
    "revoked": "REVOKE SELECT ON fixture.items FROM pietto_reader",
    "granted": "GRANT SELECT ON fixture.items TO pietto_reader",
}

SHADOW = """
import pathlib
pathlib.Path(__file__).with_name("imported").write_text("yes")
class pq:
    __impl__ = "binary"
def connect(**fields):
    pathlib.Path(__file__).with_name("connected").write_text("yes")
    raise RuntimeError("shadow")
"""
FAKE_METADATA = "Metadata-Version: 2.1\nName: antlr4-python3-runtime\nVersion: 9.9.9\n"


def environment(extra=None):
    """A worker environment without ambient interpreter, project or connection
    inputs; `extra` sets exactly the variables a case examines."""
    from _pietto_target_conformance_resources import clean_environment

    env = {
        key: value
        for key, value in clean_environment().items()
        if key not in {"VIRTUAL_ENV", "PSYCOPG_IMPL"}
        and not key.startswith(("PYTHON", "UV_", "KRB5"))
    }
    env["PYTHONNOUSERSITE"] = "1"
    env.update(extra or {})
    return env


def run(python, arguments, *, cwd, stdin="", extra=None, isolated=True, seconds=120):
    flags = ("-I", "-B") if isolated else ("-E", "-s", "-B")
    started = time.monotonic()
    completed = subprocess.run(
        [str(python), *flags, *arguments],
        cwd=cwd,
        env=environment(extra),
        input=stdin,
        capture_output=True,
        text=True,
        timeout=seconds,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout[-65536:],
        "stderr": completed.stderr[-16384:],
        "seconds": time.monotonic() - started,
    }


def case(python, cwd, config, **options):
    """One fresh worker; its last stdout line is the case's JSON result."""
    record = run(
        python, ["-c", WORKER], cwd=cwd, stdin=json.dumps(config) + "\n", **options
    )
    lines = record["stdout"].strip().splitlines()
    record["result"] = (
        json.loads(lines[-1]) if record["returncode"] == 0 and lines else None
    )
    record.pop("stdout")
    return record


def mysql_case(python, cwd, config, **options):
    """One fresh installed MySQL route worker with the same clean environment."""
    record = run(
        python,
        ["-c", MYSQL_WORKER],
        cwd=cwd,
        stdin=json.dumps(config) + "\n",
        **options,
    )
    try:
        record["result"] = json.loads(record["stdout"].splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        record["result"] = None
    return record


def adbc_case(python, cwd, config, **options):
    record = run(
        python,
        ["-c", ADBC_WORKER],
        cwd=cwd,
        stdin=json.dumps(config) + "\n",
        **options,
    )
    try:
        record["result"] = json.loads(record["stdout"].splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        record["result"] = None
    return record


@contextmanager
def sentinel():
    """A loopback port that only records whether anything connected."""
    listener = socket.create_server(("127.0.0.1", 0))
    listener.setblocking(False)
    state = {"port": listener.getsockname()[1]}

    def connected():
        try:
            listener.accept()[0].close()
        except BlockingIOError:
            return False
        return True

    state["connected"] = connected
    try:
        yield state
    finally:
        listener.close()


def consumer_cases(python, work, *, path=()):
    """The installed-consumer laws that need no database: imports and an
    unopened execute load nothing and connect nowhere; request refusals;
    refused environment before the driver (and before PyArrow can open the
    key log); a shadowing psycopg copy; a psycopg_c copy that calls itself
    binary, refused before psycopg is imported; the ANTLR label, the export records
    and a load under a stray dist-info in the working directory; query
    bundles, their records and refusals and explicit values; a code change
    between an export and a load. `path` puts a checkout first."""
    from _pietto_execution_api import write_example, write_psycopg_c

    work.mkdir(parents=True)
    project = write_example(work)
    other = write_example(work / "other")
    source = (other / "main.pietto").read_text(encoding="utf-8")
    (other / "main.pietto").write_text(
        source.replace("where id > 1", "where id > 2"), encoding="utf-8"
    )
    password = secrets.token_hex(12)
    base = {"project": str(project), "password": password, "path": list(path)}
    facts = {}
    with sentinel() as listener:
        facts["imports"] = case(
            python,
            work,
            {**base, "case": "requests", "port": listener["port"]},
            extra={"PGHOST": "127.0.0.1", "PGPORT": str(listener["port"])},
        )
        facts["imports"]["connected"] = listener["connected"]()
    ambient = {}
    for name in AMBIENT:
        values = {
            "SSLKEYLOGFILE": str(work / "keylog"),
            "OPENSSL_CONF": str(work / "empty.cnf"),
            "OPENSSL_MODULES": str(work),
        }
        (work / "empty.cnf").write_text("")
        with sentinel() as listener:
            record = case(
                python,
                work,
                {**base, "case": "refused", "port": listener["port"]},
                extra={name: values.get(name, "value-never-read")},
            )
            record["connected"] = listener["connected"]()
        record["keylog_created"] = (work / "keylog").exists()
        ambient[name] = record
    facts["ambient"] = ambient
    shadow = work / "shadow" / "psycopg"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text(SHADOW)
    with sentinel() as listener:
        record = case(
            python,
            work,
            {
                **base,
                "case": "refused",
                "port": listener["port"],
                "path": [*path, str(shadow.parent)],
            },
        )
        record["connected"] = listener["connected"]()
    record["shadow"] = str(shadow / "__init__.py")
    record["shadow_imported"] = (shadow / "imported").exists()
    record["shadow_connected"] = (shadow / "connected").exists()
    facts["shadow"] = record
    copy = write_psycopg_c(work / "copy")
    with sentinel() as listener:
        record = case(
            python,
            work,
            {
                **base,
                "case": "refused",
                "port": listener["port"],
                "path": [*path, str(copy.parent)],
            },
        )
        record["connected"] = listener["connected"]()
    record["copy_imported"] = (copy / "imported").exists()
    record["copy_received"] = (copy / "received").exists()
    facts["psycopg_c"] = record
    stray = work / "stray"
    info = stray / "antlr4_python3_runtime-9.9.9.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(FAKE_METADATA)
    (info / "RECORD").write_text("antlr4/__init__.py,,\n")
    facts["identity"] = {
        where: case(
            python,
            cwd,
            {**base, "case": "identity", "port": 0},
            isolated=False,
        )
        for where, cwd in (("clean", work), ("stray", stray))
    }
    with sentinel() as listener:
        facts["bundles"] = case(
            python,
            work,
            {
                **base,
                "case": "bundles",
                "policy": "bind-safe",
                "other": str(other),
                "port": listener["port"],
            },
        )
        facts["bundles"]["connected"] = listener["connected"]()
        facts["code_change"] = code_change(python, work, base, listener["port"])
        facts["code_change"]["connected"] = listener["connected"]()
    return facts


def code_change(python, work, base, port):
    """Worker 1 exports with the code it imports and copies that `pietto`
    package, one comment line appended; worker 2 imports the copy first,
    exports and loads under it, and changes it once more. A copy, never the
    installed or checkout files."""
    root = work / "code-change"
    root.mkdir()
    shared = {
        **base,
        "policy": "bind-safe",
        "bundle_path": str(root / "old.bundle"),
        "port": port,
    }
    exported = case(
        python,
        work,
        {**shared, "case": "code_export", "changed": str(root / "changed")},
    )
    accepted = (exported.get("result") or {}).get("records")
    changed = case(
        python,
        work,
        {
            **shared,
            "case": "code_run",
            "records": accepted,
            "path": [str(root / "changed")],
        },
    )
    return {
        "export": exported,
        "run": changed,
        "copy": str(root / "changed" / "pietto" / "__init__.py"),
    }


def context(wheel):
    return {
        "probe": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "wheel": Path(wheel).name,
        "wheel_sha256": hashlib.sha256(Path(wheel).read_bytes()).hexdigest(),
        "docs": hashlib.sha256((ROOT / "docs/execution.md").read_bytes()).hexdigest(),
    }


def prefixes(directory, recipes, *, wheel, interpreter, house_root, cache):
    """Fresh prefixes of the exact wheel, one normal resolver command each."""
    import _pietto_execution_installation_probe as s18

    house, constraints, entries = s18.wheelhouse(house_root)
    cache = cache or directory / "uv-cache"
    log = directory / "install.log"
    pythons: dict[str, Path] = {}
    records: dict[str, Any] = {"wheelhouse": [e["file"] for e in entries]}
    for recipe, extras in recipes.items():
        prefix = directory / ("prefix-" + recipe)
        records[recipe] = s18.materialize(
            prefix, interpreter, wheel, extras, house, constraints, cache, log
        )
        pythons[recipe] = prefix / "bin/python"
        described = run(pythons[recipe], ["-c", DESCRIBE], cwd=directory)
        records[recipe]["python"] = (
            json.loads(described["stdout"]) if described["returncode"] == 0 else None
        )
    return pythons, records


DESCRIBE = (
    "import json, platform; print(json.dumps([platform.python_implementation(),"
    " platform.python_version(), platform.system(), platform.machine()]))"
)


def consumer(directory, *, wheel, interpreter, house_root=None, cache=None):
    directory.mkdir(mode=0o700)
    started = time.monotonic()
    pythons, install = prefixes(
        directory,
        {"core": (), "execute-postgres": ("execute-postgres",)},
        wheel=wheel,
        interpreter=interpreter,
        house_root=house_root or directory,
        cache=cache,
    )
    report = {
        "format": FORMAT,
        "family": "consumer",
        "context": context(wheel),
        "install": install,
    }
    from _pietto_execution_api import write_example

    core = directory / "core"
    core.mkdir()
    project = write_example(core)
    with sentinel() as listener:
        report["core"] = case(
            pythons["core"],
            core,
            {
                "case": "refused",
                "project": str(project),
                "password": secrets.token_hex(12),
                "port": listener["port"],
            },
        )
        report["core"]["connected"] = listener["connected"]()
    with sentinel() as listener:
        report["core_schema"] = case(
            pythons["core"],
            core,
            {
                "case": "schema_refused",
                "project": str(project),
                "password": secrets.token_hex(12),
                "port": listener["port"],
            },
        )
        report["core_schema"]["connected"] = listener["connected"]()
    with sentinel() as listener:
        report["core_cancel"] = case(
            pythons["core"],
            core,
            {
                "case": "cancelled",
                "project": str(project),
                "password": secrets.token_hex(12),
                "port": listener["port"],
            },
        )
        report["core_cancel"]["connected"] = listener["connected"]()
    # The same refusal for a query loaded from its bundle in the core prefix.
    with sentinel() as listener:
        report["core_bundle"] = case(
            pythons["core"],
            core,
            {
                "case": "refused",
                "project": str(project),
                "password": secrets.token_hex(12),
                "port": listener["port"],
                "policy": "bind-safe",
                "load_bundle": True,
            },
        )
        report["core_bundle"]["connected"] = listener["connected"]()
    report["cases"] = consumer_cases(pythons["execute-postgres"], directory / "cases")
    report["seconds"] = time.monotonic() - started
    return finish(directory, report)


def mysql(directory, *, wheel, interpreter, house_root=None, cache=None):
    """Installed MySQL dependency/origin/ambient witness, without a service.

    The separate native family owns the exact MySQL service acceptance. This
    consumer family proves the selected installed prefix reaches only the
    MySQL route's declared dependency boundary.
    """
    directory.mkdir(mode=0o700)
    pythons, install = prefixes(
        directory,
        {"core": (), "execute-mysql": ("execute-mysql",)},
        wheel=wheel,
        interpreter=interpreter,
        house_root=house_root or directory,
        cache=cache,
    )
    base = {
        "path": [str(ROOT / "tests")],
        "work": str(directory / "work"),
        "port": 9,
        "password": secrets.token_hex(12),
    }
    report = {
        "format": FORMAT,
        "family": "mysql",
        "context": context(wheel),
        "install": install,
    }
    report["core"] = mysql_case(pythons["core"], directory, {**base, "case": "core"})
    ambient = {}
    for name in ("SSLKEYLOGFILE", "OPENSSL_CONF", "OPENSSL_MODULES"):
        ambient[name] = mysql_case(
            pythons["execute-mysql"],
            directory,
            {**base, "case": "ambient"},
            extra={name: "value-never-read"},
        )
    shadow = directory / "shadow" / "mysql"
    (shadow / "connector").mkdir(parents=True)
    (shadow / "__init__.py").write_text("", encoding="utf-8")
    (shadow / "connector" / "__init__.py").write_text("", encoding="utf-8")
    (shadow / "connector" / "connection.py").write_text("", encoding="utf-8")
    report["ambient"] = ambient
    report["shadow"] = mysql_case(
        pythons["execute-mysql"],
        directory,
        {**base, "case": "shadow", "path": [str(ROOT / "tests"), str(shadow.parent)]},
    )
    return finish(directory, report)


def postgres_adbc(directory, *, wheel, interpreter, house_root=None, cache=None):
    """Installed ADBC dependency/origin/ambient witness, without a service.

    The separate exact-wheel PostgreSQL ADBC family owns SCRAM and result
    acceptance; this family proves the public route's selected prefix cannot
    use another route's driver before that service witness runs.
    """
    from _pietto_execution_api import write_example

    directory.mkdir(mode=0o700)
    pythons, install = prefixes(
        directory,
        {"core": (), "execute-postgres-adbc": ("execute-postgres-adbc",)},
        wheel=wheel,
        interpreter=interpreter,
        house_root=house_root or directory,
        cache=cache,
    )
    project = write_example(directory / "project")
    base = {
        "path": [str(ROOT / "tests")],
        "project": str(project),
        "port": 9,
        "password": secrets.token_hex(12),
    }
    report = {
        "format": FORMAT,
        "family": "postgres_adbc",
        "context": context(wheel),
        "install": install,
    }
    report["core"] = adbc_case(pythons["core"], directory, {**base, "case": "core"})
    ambient = {}
    for name in ("SSLKEYLOGFILE", "OPENSSL_CONF", "OPENSSL_MODULES"):
        ambient[name] = adbc_case(
            pythons["execute-postgres-adbc"],
            directory,
            {**base, "case": "ambient"},
            extra={name: "value-never-read"},
        )
    shadow = directory / "shadow" / "adbc_driver_postgresql"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text("", encoding="utf-8")
    report["ambient"] = ambient
    report["shadow"] = adbc_case(
        pythons["execute-postgres-adbc"],
        directory,
        {
            **base,
            "case": "shadow",
            "path": [str(ROOT / "tests"), str(shadow.parent)],
        },
    )
    return finish(directory, report)


def statements(passwords):
    """The fixture: the documented relation and reader role (database `app`
    replaced), an out-of-domain relation, the reader without a server-side
    statement limit, and one role per refused authentication method (md5
    hashed as md5). The reader's password is set as `\\password` sets it."""
    from _pietto_execution_api import example_blocks, setup_blocks
    from _pietto_execution_api import statements as documented

    wide = ",".join(f"({i},'{label}')" for i, label in WIDE_ROWS)
    role = documented(setup_blocks()["sql"])
    database = [s for s in role if " DATABASE app " in s]
    assert len(database) == 1, role
    return (
        *documented(example_blocks()["sql"]),
        'CREATE TABLE fixture.items_wide (item_id int8 NOT NULL, item_label text COLLATE "C" NOT NULL)',
        "INSERT INTO fixture.items_wide VALUES " + wide,
        *(s.replace(" DATABASE app ", " DATABASE phase66 ") for s in role),
        "GRANT SELECT ON fixture.items_wide TO pietto_reader",
        # Only Pietto's own statement limit applies to the reader's sessions.
        "ALTER ROLE pietto_reader SET statement_timeout = 0",
        "CREATE ROLE pietto_trust LOGIN",
        f"CREATE ROLE pietto_cleartext LOGIN PASSWORD '{passwords['pietto_cleartext']}'",
        "SET password_encryption = 'md5'",
        f"CREATE ROLE pietto_md5 LOGIN PASSWORD '{passwords['pietto_md5']}'",
        "RESET password_encryption",
    )


def set_password(manager, role, password):
    """The documented psql commands: each SET, then what `\\password` sends:
    libpq computes the verifier under the session's password_encryption and
    only the verifier reaches the server, in one ALTER USER statement."""
    from psycopg import sql

    from _pietto_execution_api import setup_blocks

    *settings, command = setup_blocks()["psql"].splitlines()
    assert command == "\\password " + role, command
    assert settings and all(
        line.startswith("SET ") and line.endswith(";") for line in settings
    ), settings
    assert settings[-1] == "SET password_encryption = 'scram-sha-256';", settings
    for line in settings:
        with manager.cursor() as cursor:
            cursor.execute(line.rstrip(";"))
    verifier = manager.pgconn.encrypt_password(password.encode(), role.encode())
    statement = sql.SQL("ALTER USER {} PASSWORD {}").format(
        sql.Identifier(role), sql.Literal(verifier.decode())
    )
    with manager.cursor() as cursor:
        cursor.execute(statement)


def rows(connection, sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return [list(row) for row in cursor.fetchall()]


def prepare_server(resources, passwords):
    """Create the fixture as documented, turn TLS on (the S09 self-signed
    fixture certificate), replace pg_hba.conf and record what the server
    reports about them (no password or hash)."""
    from _pietto_execution_adbc_probe import enable_fixture_tls

    manager = resources.manager
    for sql in statements(passwords):
        with manager.cursor() as cursor:
            cursor.execute(sql)
    set_password(manager, "pietto_reader", passwords["pietto_reader"])
    enable_fixture_tls(resources)
    (hba_file,) = rows(manager, "SHOW hba_file")[0]
    lines = ",".join(f"({n},'{line}')" for n, line in enumerate(hba()))
    with manager.cursor() as cursor:
        cursor.execute(
            f"COPY (SELECT line FROM (VALUES {lines}) AS v(n, line) ORDER BY n)"
            f" TO '{hba_file}'"
        )
        cursor.execute("SELECT pg_reload_conf()")
    time.sleep(2)
    return {
        "version": rows(manager, "SELECT current_setting('server_version_num')")[0][0],
        "ssl": rows(manager, "SHOW ssl")[0][0],
        "password_encryption": rows(manager, "SHOW password_encryption")[0][0],
        "reader_settings": rows(
            manager, "SELECT rolconfig FROM pg_roles WHERE rolname = 'pietto_reader'"
        )[0][0],
        "hba": rows(
            manager,
            "SELECT type, user_name, auth_method, error FROM pg_hba_file_rules"
            " ORDER BY rule_number",
        ),
        "hashes": rows(
            manager,
            "SELECT rolname::text, rolpassword LIKE 'SCRAM-SHA-256$%',"
            " rolpassword LIKE 'md5%' FROM pg_authid"
            " WHERE rolname LIKE 'pietto\\_%' AND rolname <> 'pietto_manager'"
            " ORDER BY rolname",
        ),
    }


def sessions(manager, user):
    return rows(
        manager,
        "SELECT count(*) FROM pg_stat_activity WHERE usename = '"
        + user
        + "' AND pid <> pg_backend_pid()",
    )[0][0]


def dropped(python, cwd, config, manager):
    """A worker that drops its open handle: the session while the worker
    still runs (and its TLS as the server sees it), the exit delay the
    deadline timer causes, and the session once the process is gone."""
    process = subprocess.Popen(
        [str(python), "-I", "-B", "-c", WORKER],
        cwd=cwd,
        env=environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    watchdog = threading.Timer(120, process.kill)
    watchdog.start()
    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(json.dumps(config) + "\n")
        process.stdin.close()
        line = process.stdout.readline()
        during = sessions(manager, config["user"])
        tls = rows(
            manager,
            "SELECT s.ssl, s.version FROM pg_stat_activity a JOIN pg_stat_ssl s"
            " ON s.pid = a.pid WHERE a.usename = '"
            + config["user"]
            + "' AND a.pid <> pg_backend_pid()",
        )
        process.wait()
        ended = time.monotonic()
    finally:
        watchdog.cancel()
    after = None
    for _ in range(20):
        after = sessions(manager, config["user"])
        if after == 0:
            break
        time.sleep(0.5)
    result = json.loads(line) if line.strip() else None
    return {
        "returncode": process.returncode,
        "result": result,
        "during": during,
        "tls": tls,
        "exit_delay": None if result is None else ended - result["dropped_at"],
        "after": after,
    }


def manual_cancel(python, cwd, config, manager, quiet):
    """One blocked public statement, then a controller's public cancel call.
    The manager observes PostgreSQL's lock wait before it releases the child."""
    process = subprocess.Popen(
        [str(python), "-I", "-B", "-c", CANCEL],
        cwd=cwd,
        env=environment(quiet),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    watchdog = threading.Timer(120, process.kill)
    watchdog.start()
    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(json.dumps(config) + "\n")
        process.stdin.flush()
        ready = json.loads(process.stdout.readline())
        if set(ready) != {"ready"} or type(ready["ready"]) is not str:
            raise ValueError("CANCEL_READY")
        blocked = None
        for _ in range(50):
            with manager.cursor() as cursor:
                cursor.execute("SELECT pg_stat_clear_snapshot()")
            found = rows(
                manager,
                "SELECT state, wait_event_type FROM pg_stat_activity WHERE usename = 'pietto_reader'"
                " AND pid <> pg_backend_pid()",
            )
            if found == [["active", "Lock"]]:
                blocked = found
                break
            time.sleep(0.1)
        process.stdin.write("cancel\n")
        process.stdin.flush()
        result_line = process.stdout.readline()
        process.stdin.close()
        _stdout, stderr = process.communicate()
        return {
            "returncode": process.returncode,
            "blocked": blocked,
            "result": json.loads(result_line) if result_line.strip() else None,
            "stderr": stderr[-16384:],
        }
    finally:
        watchdog.cancel()


def postgres(directory, *, wheel, interpreter, house_root=None, cache=None):
    import _pietto_target_conformance_resources as resources_module
    from _pietto_execution_api import write_example

    directory.mkdir(mode=0o700)
    started = time.monotonic()
    pythons, install = prefixes(
        directory,
        {"execute-postgres": ("execute-postgres",)},
        wheel=wheel,
        interpreter=interpreter,
        house_root=house_root or directory,
        cache=cache,
    )
    python = pythons["execute-postgres"]
    report = {
        "format": FORMAT,
        "family": "postgres",
        "context": context(wheel),
        "install": install,
    }
    work = directory / "work"
    work.mkdir()
    project = write_example(work)
    ordered = write_example(work / "ordered")
    path = ordered / "main.pietto"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "        label\n", "        label\n    order by:\n        id\n"
        ),
        encoding="utf-8",
    )
    limited = write_example(work / "limited")
    path = limited / "main.pietto"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "        label\n", "        label\n    order by:\n        id\n    limit 1\n"
        ),
        encoding="utf-8",
    )
    wide = write_example(work / "wide", relation="items_wide")
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    (directory / "resources").mkdir()
    resources = resources_module.Resources(
        "postgres", pins["targets"]["postgres"], directory / "resources"
    )
    passwords = {role: secrets.token_hex(16) for role in ROLES}
    quiet = {}
    for name in ("home", "tmp"):
        (directory / name).mkdir(mode=0o700)
        quiet["HOME" if name == "home" else "TMPDIR"] = str(directory / name)
    try:
        resources.acquire()
        manager = resources.manager
        report["server"] = prepare_server(resources, passwords)
        report["image"] = resources.runtime_image_id
        port = resources.port
        base = {"project": str(project), "port": port, "user": "pietto_reader"}
        reader = {**base, "password": passwords["pietto_reader"]}
        secret = passwords["pietto_reader"]
        # As written (TLS, channel binding), then the loopback exception.
        report["example"] = example(python, work, port, secret)
        report["example_loopback"] = example(python, work, port, secret, "disable")
        report["bind_safe"] = case(
            python, work, {**reader, "case": "rows", "policy": "bind-safe"}, extra=quiet
        )
        report["schema_empty"] = case(
            python,
            work,
            {**reader, "case": "rows", "policy": "bind-safe", "values": [100]},
            extra=quiet,
        )
        report["early_stop"] = case(
            python,
            work,
            {**reader, "case": "early_stop", "limits": {"batch_rows": 1}},
            extra=quiet,
        )
        report["interrupt"] = case(
            python, work, {**reader, "case": "interrupt"}, extra=quiet
        )
        report["native_unlimited"] = case(
            python,
            work,
            {
                **reader,
                "case": "buffer",
                "project": str(ordered),
                "limits": {"batch_rows": 1, "max_rows": 1},
            },
            extra=quiet,
        )
        report["native_limited"] = case(
            python,
            work,
            {
                **reader,
                "case": "buffer",
                "project": str(limited),
                "limits": {"batch_rows": 1, "max_rows": 1},
            },
            extra=quiet,
        )
        report["result_check"] = case(
            python, work, {**reader, "case": "failure", "project": str(wide)}
        )
        report["authentication"] = {
            role: case(
                python,
                work,
                {**base, "case": "failure", "user": role, "password": passwords[role]},
            )
            for role in ROLES
            if role != "pietto_reader"
        }
        with manager.cursor() as cursor:
            cursor.execute("BEGIN")
            cursor.execute("LOCK TABLE fixture.items IN ACCESS EXCLUSIVE MODE")
        try:
            # The deadline is far beyond 10 s and the role has no server-side
            # limit, so only Pietto's own statement limit can end it.
            report["statement_timeout"] = case(
                python,
                work,
                {**reader, "case": "failure", "limits": {"seconds": 60}},
                seconds=120,
            )
        finally:
            with manager.cursor() as cursor:
                cursor.execute("ROLLBACK")
        with manager.cursor() as cursor:
            cursor.execute("BEGIN")
            cursor.execute("LOCK TABLE fixture.items IN ACCESS EXCLUSIVE MODE")
        try:
            report["manual_cancel"] = manual_cancel(
                python, work, reader, manager, quiet
            )
        finally:
            with manager.cursor() as cursor:
                cursor.execute("ROLLBACK")
        report["dropped"] = dropped(
            python,
            work,
            {**reader, "case": "dropped", "limits": {"seconds": 4}},
            manager,
        )
        # A bundle exported from a fresh copy that is then deleted, loaded
        # once in an empty working directory and run step by step.
        exported = work / "bundle"
        source = write_example(exported / "copy")
        report["bundle_export"] = case(
            python,
            exported,
            {
                **reader,
                "project": str(source),
                "case": "export",
                "policy": "bind-safe",
                "bundle_path": str(exported / "active_items.bundle"),
            },
        )
        shutil.rmtree(source.parent)
        steps = work / "steps"
        steps.mkdir()
        report["bundle_steps"] = stepped(
            python,
            steps,
            {
                "payload": str(exported / "active_items.bundle"),
                "records": (report["bundle_export"].get("result") or {}).get("records"),
                "source": str(source),
                "port": port,
                "passwords": {
                    role: passwords[role] for role in ("pietto_reader", "pietto_md5")
                },
                "steps": BUNDLE_STEPS,
            },
            manager,
            quiet,
        )
        report["bundle_example"] = example(
            python, work, port, secret, script="bundle_query.py"
        )
        report["consume_example"] = example(
            python, work, port, secret, script="consume_query.py"
        )
    finally:
        report["cleanup"] = resources.cleanup()
    report["seconds"] = time.monotonic() - started
    return finish(directory, report)


def example(python, cwd, port, password, *sslmode, script="run_query.py"):
    """A documented script, run from the directory that holds the project."""
    record = run(
        python,
        [script, "127.0.0.1", str(port), "phase66", "pietto_reader", *sslmode],
        cwd=cwd,
        stdin=password + "\n",
    )
    record["shown"] = password in record["stdout"]
    return record


def stepped(python, cwd, config, manager, quiet):
    """The bundle steps worker: one `go` line per step, the manager's
    privilege change before the steps that name one, and the reader's
    privilege granted again whatever happens."""
    process = subprocess.Popen(
        [str(python), "-I", "-B", "-c", STEPS],
        cwd=cwd,
        env=environment(quiet),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    watchdog = threading.Timer(300, process.kill)
    watchdog.start()
    lines: list[str] = []
    try:
        assert process.stdin is not None and process.stdout is not None
        try:
            process.stdin.write(json.dumps(config) + "\n")
            process.stdin.flush()
            lines.append(process.stdout.readline())
            for step in config["steps"]:
                if step["name"] in PRIVILEGE:
                    with manager.cursor() as cursor:
                        cursor.execute(PRIVILEGE[step["name"]])
                process.stdin.write("go\n")
                process.stdin.flush()
                lines.append(process.stdout.readline())
        except BrokenPipeError:
            pass  # the worker ended early; its stderr says why
        rest, stderr = process.communicate()
        lines.extend(rest.splitlines())
    finally:
        watchdog.cancel()
        with manager.cursor() as cursor:
            cursor.execute(PRIVILEGE["granted"])
    return {
        "returncode": process.returncode,
        "records": [json.loads(line) for line in lines if line.strip()],
        "stderr": stderr[-16384:],
    }


def finish(directory, report):
    import _pietto_execution_api_check as check

    path = directory / "report.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return check.check(json.loads(path.read_text(encoding="utf-8")))


ADBC_NATIVE_WORKER = r"""
import importlib, json, os, sys, threading, time
from importlib.metadata import distribution, version
config = json.loads(sys.stdin.readline())
TRACK = {"adbc_driver_manager", "adbc_driver_postgresql", "pyarrow"}
def loaded():
    return sorted({name.split(".")[0] for name in sys.modules} & TRACK)
def facts(outcome):
    primary = outcome.primary
    return {"end": outcome.end, "source": outcome.source,
        "transaction": outcome.transaction, "delivery": outcome.delivery,
        "cleanup": outcome.cleanup, "remote": outcome.remote_source_use_end,
        "rows": outcome.rows, "batches": outcome.batches,
        "cancel": [outcome.cancel_requested, outcome.cancel_sent, outcome.cancel_observed],
        "primary": None if primary is None else [primary.code, primary.detail,
            primary.phase, primary.sqlstate, primary.cause],
        "cleanup_failures": [[item.code, item.phase, item.cause]
            for item in outcome.cleanup_failures]}
def compile(project, policy="bind-safe"):
    return pe.compile_query(project, module="main.pietto", kind="table",
        name="active_items", dialect="postgres", emission_contract="contract.json",
        literal_policy=policy)
def access(sslmode="require"):
    return pe.PostgresAccess("127.0.0.1", config["port"], "phase66",
        config.get("user", "pietto_reader"), password, sslmode)
def attempt(query, *, values=None, limits=None, sslmode="require"):
    arguments = {}
    if values is not None:
        arguments["values"] = values
    return pe.execute(query, route="postgres_adbc", access=access(sslmode),
        premise=premise, limits=pe.ExecutionLimits(**(limits or {})), **arguments)
def rows(query, *, values=(), limits=None):
    import pyarrow as pa
    handle = attempt(query, values=values, limits=limits)
    schema = [[field.name, str(field.type), field.nullable] for field in pa.schema(handle)]
    data = []
    with handle:
        for batch in handle:
            with batch:
                data.extend(pa.record_batch(batch).to_pylist())
    return {"route": handle.route, "sslmode": "require", "schema": schema,
        "rows": [[item["id"], item["label"]] for item in data],
        "outcome": facts(handle.outcome)}
def library():
    module = importlib.import_module("adbc_driver_postgresql")
    manager = importlib.import_module("adbc_driver_manager")
    root = os.path.realpath(sys.prefix)
    package = os.path.dirname(os.path.realpath(module.__file__))
    path = os.path.join(package, "libadbc_driver_postgresql.so")
    files = {str(item) for item in distribution("adbc-driver-postgresql").files or ()}
    return {"prefix": root, "postgresql_version": version("adbc-driver-postgresql"),
        "manager_version": version("adbc-driver-manager"),
        "module": os.path.realpath(module.__file__),
        "manager_module": os.path.realpath(manager.__file__), "library": path,
        "library_record": "adbc_driver_postgresql/libadbc_driver_postgresql.so" in files,
        "module_record": "adbc_driver_postgresql/__init__.py" in files,
        "module_in_prefix": os.path.commonpath([root, os.path.realpath(module.__file__)]) == root,
        "library_in_prefix": os.path.commonpath([root, path]) == root,
        "library_exists": os.path.isfile(path)}
import pietto.execution as pe
password = config["password"]
premise = pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
result = {"after_import": loaded()}
if config["case"] == "ambient":
    query = compile(config["project"])
    try:
        handle = attempt(query)
    except pe.RequestRejected as error:
        result.update(code=error.code, detail=error.detail,
            shown=password in str(error) + repr(error),
            chained=error.__cause__ is not None or error.__context__ is not None)
    else:
        result["unopened"] = [loaded(), handle.outcome.end, password in repr(handle)]
        try:
            with handle:
                pass
        except pe.AttemptFailed as error:
            result.update(code=error.code, detail=error.detail,
                shown=password in str(error) + repr(error),
                chained=error.__cause__ is not None or error.__context__ is not None,
                outcome=facts(error.outcome))
    result["after_open"] = loaded()
elif config["case"] == "auth":
    query = compile(config["project"])
    handle = attempt(query, sslmode="disable")
    result["unopened"] = [loaded(), handle.outcome.end, password in repr(handle)]
    try:
        with handle:
            pass
    except pe.AttemptFailed as error:
        result.update(code=error.code, detail=error.detail,
            shown=password in str(error) + repr(error),
            chained=error.__cause__ is not None or error.__context__ is not None,
            outcome=facts(error.outcome))
    result["after_open"] = loaded()
elif config["case"] == "native":
    qualification = []
    import pietto._project.project_execution_postgres_adbc as native
    original = native.qualify_sources
    def observed(owner):
        qualification.append(owner.request.route)
        return original(owner)
    native.qualify_sources = observed
    try:
        live = compile(config["project"])
        bundle = pe.export_bundle(live)
        loaded_query = pe.load_bundle(bundle.payload, expected_pin=bundle.pin,
            accepted_producer=bundle.producer, accepted_compatibility=bundle.compatibility)
        live_rows = rows(live, values=(1,))
        bundle_rows = rows(loaded_query, values=(1,))
        live_rows["origin"] = live.origin
        bundle_rows["origin"] = loaded_query.origin
        result.update(live=live_rows, bundle=bundle_rows,
            empty=rows(compile(config["empty"]), values=(100,)),
            bounded=rows(compile(config["limited"]), values=(1,)),
            qualification=qualification,
            driver=library())
        handle = attempt(live, values=(1,), limits={"batch_rows": 1})
        import pyarrow as pa
        with handle:
            batch = next(handle)
            with batch:
                result["early_rows"] = pa.record_batch(batch).to_pylist()
        result["early"] = facts(handle.outcome)
        handle = attempt(live, values=(1,))
        cancelled = {"cancel_return": handle.cancel() is None}
        try:
            with handle:
                pass
        except pe.AttemptFailed as error:
            cancelled.update(code=error.code, detail=error.detail,
                shown=password in str(error) + repr(error),
                chained=error.__cause__ is not None or error.__context__ is not None,
                outcome=facts(error.outcome))
        cancelled["closed"] = handle.closed
        result["cancelled"] = cancelled
    finally:
        native.qualify_sources = original
elif config["case"] in ("active_cancel", "active_server_timeout"):
    live = compile(config["project"])
    handle = attempt(live, values=(1,))
    seen = []
    opened = threading.Event()
    go = threading.Event()
    def consume():
        try:
            handle.__enter__()
            opened.set()
            print(json.dumps({"ready": handle.attempt, "purpose": "query"}), flush=True)
            if not go.wait(30):
                raise RuntimeError("ADBC_CANCEL_GO")
            next(handle)
        except BaseException as error:
            seen.append(error)
    worker = threading.Thread(target=consume, name="pietto-adbc-active-consumer")
    worker.start()
    if sys.stdin.readline() != "go\n":
        raise SystemExit("ADBC_CANCEL_GO")
    go.set()
    active = None
    for _ in range(100):
        candidate = getattr(handle._owner, "_active", None)
        if (
            candidate is not None
            and getattr(candidate, "purpose", None) == "query"
            and getattr(candidate, "native", None) is not None
        ):
            active = candidate
            break
        time.sleep(0.01)
    if active is None:
        raise SystemExit("ADBC_ACTIVE_NATIVE_STATEMENT")
    active_record = {"type": type(active).__name__, "purpose": getattr(active, "purpose", None), "native": getattr(active, "native", None) is not None}
    print(json.dumps({"active": active_record}), flush=True)
    if config["case"] == "active_cancel":
        if sys.stdin.readline() != "cancel\n":
            raise SystemExit("ADBC_CANCEL_CONTROL")
        result["cancel_return"] = handle.cancel() is None
    worker.join(30)
    if worker.is_alive():
        raise SystemExit("ADBC_CANCEL_JOIN")
    settled = facts(handle.outcome)
    result.update(active=active_record, closed=handle.closed, outcome=settled,
        raised=None if not seen else type(seen[0]).__name__,
        late_cancel_return=handle.cancel() is None,
        outcome_after_late=facts(handle.outcome))
print(json.dumps(result), flush=True)
"""


def adbc_native_case(python, cwd, config, **options):
    """One fresh ADBC worker.  Its raw facts never reuse a rows-route child."""
    record = run(
        python,
        ["-c", ADBC_NATIVE_WORKER],
        cwd=cwd,
        stdin=json.dumps(config) + "\n",
        **options,
    )
    lines = record["stdout"].strip().splitlines()
    record["result"] = (
        json.loads(lines[-1]) if record["returncode"] == 0 and lines else None
    )
    record.pop("stdout")
    return record


def adbc_active_cancel(python, cwd, config, manager, quiet, *, deadline=False):
    """Observe a real active lock wait before the public ADBC cancel call."""
    process = subprocess.Popen(
        [str(python), "-I", "-B", "-c", ADBC_NATIVE_WORKER],
        cwd=cwd,
        env=environment(quiet),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    watchdog = threading.Timer(120, process.kill)
    watchdog.start()

    def failed(stage, raw, blocked=None, active=None):
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        stdout, stderr = process.communicate()
        return {
            "returncode": process.returncode,
            "blocked": blocked,
            "active": active,
            "result": None,
            "protocol_failure": stage,
            "rawstdout": raw + stdout,
            "stderr": stderr[-16384:],
        }

    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(
            json.dumps(
                {
                    **config,
                    "case": "active_server_timeout" if deadline else "active_cancel",
                    "limits": {"seconds": 5} if deadline else {},
                }
            )
            + "\n"
        )
        process.stdin.flush()
        raw_ready = process.stdout.readline()
        try:
            ready = json.loads(raw_ready)
        except json.JSONDecodeError:
            return failed("READY_JSON", raw_ready)
        if set(ready) != {"ready", "purpose"} or ready["purpose"] != "query":
            return failed("READY_SHAPE", raw_ready)
        with manager.cursor() as cursor:
            cursor.execute("BEGIN")
            cursor.execute("LOCK TABLE fixture.items IN ACCESS EXCLUSIVE MODE")
            process.stdin.write("go\n")
            process.stdin.flush()
            raw_active = process.stdout.readline()
            try:
                active = json.loads(raw_active)
            except json.JSONDecodeError:
                return failed("ACTIVE_JSON", raw_ready + raw_active, active=None)
            if set(active) != {"active"}:
                return failed("ACTIVE_SHAPE", raw_ready + raw_active, active=active)
            if active["active"] != {
                "type": "NativeStatement",
                "purpose": "query",
                "native": True,
            }:
                return failed(
                    "ACTIVE_NATIVE_STATEMENT",
                    raw_ready + raw_active,
                    active=active,
                )
            blocked = None
            for _ in range(50):
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                found = rows(
                    manager,
                    "SELECT state, wait_event_type FROM pg_stat_activity WHERE usename = 'pietto_reader' AND pid <> pg_backend_pid()",
                )
                if found == [["active", "Lock"]]:
                    blocked = found
                    break
                time.sleep(0.1)
            if not deadline:
                process.stdin.write("cancel\n")
                process.stdin.flush()
            line = process.stdout.readline()
            cursor.execute("ROLLBACK")
        process.stdin.close()
        _stdout, stderr = process.communicate()
        return {
            "returncode": process.returncode,
            "blocked": blocked,
            "attempt": ready["ready"],
            "purpose": ready["purpose"],
            "active": active["active"],
            "result": json.loads(line) if line.strip() else None,
            "stderr": stderr[-16384:],
        }
    finally:
        watchdog.cancel()


def postgres_adbc_native(directory, *, wheel, interpreter, house_root=None, cache=None):
    """A distinct installed ADBC witness against the PostgreSQL 18.6 fixture.

    The ordinary ``postgres_adbc`` consumer family remains service-free.  This
    one proves the selected candidate wheel can perform the public TCP SCRAM
    route; its negative protocol observations use the existing one-shot stub.
    """
    import _pietto_target_conformance_resources as resources_module
    from _pietto_execution_api import PostgresStub, write_example

    directory.mkdir(mode=0o700)
    started = time.monotonic()
    pythons, install = prefixes(
        directory,
        {"execute-postgres-adbc": ("execute-postgres-adbc",)},
        wheel=wheel,
        interpreter=interpreter,
        house_root=house_root or directory,
        cache=cache,
    )
    python = pythons["execute-postgres-adbc"]
    report = {
        "format": FORMAT,
        "family": "postgres_adbc_native",
        "context": context(wheel),
        "install": install,
    }
    work = directory / "work"
    work.mkdir()
    project = write_example(work / "ordered")
    path = project / "main.pietto"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "        label\n", "        label\n    order by:\n        id\n"
        ),
        encoding="utf-8",
    )
    empty = write_example(work / "empty")
    limited = write_example(work / "limited")
    path = limited / "main.pietto"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "        label\n", "        label\n    order by:\n        id\n    limit 1\n"
        ),
        encoding="utf-8",
    )
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    (directory / "resources").mkdir()
    resources = resources_module.Resources(
        "postgres", pins["targets"]["postgres"], directory / "resources"
    )
    passwords = {role: secrets.token_hex(16) for role in ROLES}
    quiet = {}
    for name in ("home", "tmp"):
        (directory / name).mkdir(mode=0o700)
        quiet["HOME" if name == "home" else "TMPDIR"] = str(directory / name)
    try:
        resources.acquire()
        report["server"] = prepare_server(resources, passwords)
        report["image"] = resources.runtime_image_id
        base = {
            "project": str(project),
            "empty": str(empty),
            "limited": str(limited),
            "port": resources.port,
            "password": passwords["pietto_reader"],
        }
        report["native"] = adbc_native_case(
            python, work, {**base, "case": "native"}, extra=quiet
        )
        report["active_cancel"] = adbc_active_cancel(
            python, work, base, resources.manager, quiet
        )
        report["active_server_timeout"] = adbc_active_cancel(
            python, work, base, resources.manager, quiet, deadline=True
        )
        report["authentication"] = {}
        for method in ("trust", "password", "md5", "gss", "sspi"):
            with PostgresStub(auth=method) as stub:
                record = adbc_native_case(
                    python,
                    work,
                    {**base, "case": "auth", "port": stub.port},
                    extra=quiet,
                )
            record["stub"] = {
                "events": stub.events,
                "replied": stub.replied,
                "startup": [
                    stub.startup.get(b"user", b"").decode(),
                    stub.startup.get(b"database", b"").decode(),
                ],
            }
            report["authentication"][method] = record
        report["ambient"] = {}
        for name in ("SSLKEYLOGFILE", "OPENSSL_CONF", "OPENSSL_MODULES"):
            keylog = work / ("keylog-" + name)
            value = {
                "SSLKEYLOGFILE": str(keylog),
                "OPENSSL_CONF": str(work / "empty.cnf"),
                "OPENSSL_MODULES": str(work),
            }[name]
            (work / "empty.cnf").write_text("", encoding="utf-8")
            with sentinel() as listener:
                record = adbc_native_case(
                    python,
                    work,
                    {**base, "case": "ambient", "port": listener["port"]},
                    extra={**quiet, name: value},
                )
                record["connected"] = listener["connected"]()
            record["keylog_created"] = keylog.exists()
            report["ambient"][name] = record
    finally:
        report["cleanup"] = resources.cleanup()
    report["seconds"] = time.monotonic() - started
    return finish(directory, report)


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "family",
        choices=(
            "consumer",
            "mysql",
            "postgres",
            "postgres_adbc",
            "postgres_adbc_native",
            "check",
        ),
    )
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--interpreter", type=Path)
    parser.add_argument("--house", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "src")]
    if args.family == "check":
        import _pietto_execution_api_check as check

        verdict = check.check(json.loads(args.report.read_text()))
    else:
        if None in (args.directory, args.wheel, args.interpreter):
            parser.error("--directory, --wheel and --interpreter are required")
        run_family = {
            "consumer": consumer,
            "mysql": mysql,
            "postgres": postgres,
            "postgres_adbc": postgres_adbc,
            "postgres_adbc_native": postgres_adbc_native,
        }[args.family]
        verdict = run_family(
            args.directory,
            wheel=args.wheel,
            interpreter=args.interpreter,
            house_root=args.house,
            cache=args.cache,
        )
    print(json.dumps(verdict, sort_keys=True))


if __name__ == "__main__":
    main()
