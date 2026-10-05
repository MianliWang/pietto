"""S12 capture fixtures and explicit bounded native bridge; import acquires nothing.

Ordinary tests have no database. `simulate` swaps only the owner's native fetch
step (SIMULATED_NATIVE_IO): the real S10 compiled request, owner class, native
metadata ABI check, ExecutionPayloads and every scalar/Arrow check still run.
Native capture evidence comes only from the bridge.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice12-"
# Actual PostgreSQL type OIDs of the seven-scalar fixture's nine result columns.
SEVEN_CODES = (1114, 1114, 2950, 2950, 23, 16, 701, 25, 1700)
SEVEN_ROWS = (
    (
        datetime(2024, 1, 2, 3, 4, 5, 6),
        None,
        UUID("00112233-4455-6677-8899-aabbccddeeff"),
        None,
        -100,
        True,
        -0.0,
        "héllo☃",
        Decimal("12345678901234567890123456789012345.6789"),
    ),
    (
        datetime(2024, 1, 2, 3, 4, 5, 6),
        None,
        UUID("00112233-4455-6677-8899-aabbccddeeff"),
        None,
        -100,
        True,
        -0.0,
        "héllo☃",
        Decimal("12345678901234567890123456789012345.6789"),
    ),
    (None,) * 9,
    (
        datetime(1970, 1, 1),
        datetime(9999, 12, 31, 23, 59, 59, 499999),
        UUID(int=0),
        UUID(int=2**128 - 1),
        100,
        False,
        5e-324,
        "",
        Decimal("-0.0001"),
    ),
    (
        datetime(2000, 2, 29, 12),
        None,
        UUID(int=1),
        None,
        0,
        None,
        0.0,
        "12345678",
        Decimal("0.0000"),
    ),
)
SEVEN65_ROWS = (
    (
        datetime(1000, 1, 1),
        None,
        UUID(int=2**127),
        None,
        1,
        True,
        1.7976931348623157e308,
        "\u96ea",
        Decimal("99999999999999999999999999999999999." + "9" * 30),
    ),
    (
        datetime(2024, 2, 29, 23, 59, 59, 499999),
        None,
        UUID(int=5),
        None,
        -1,
        False,
        -5e-324,
        "x",
        Decimal("-0." + "0" * 29 + "1"),
    ),
    (None,) * 9,
)
# The first value past the Timestamp meaning upper bound; checked late.
LATE_INVALID = (datetime(9999, 12, 31, 23, 59, 59, 500000),) + SEVEN_ROWS[0][1:]
SMALL_CODES = (20, 20)
FAIL = "SIMULATED_LATE_FAILURE"


def seven_template(directory, *, entry="bundle", precision=39):
    """The S05 seven-scalar artifact as a current compiled S10 template."""
    from _pietto_phase68_slice5_cases import seven_artifact
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
        prepare_live_template,
    )

    artifact = seven_artifact(Path(directory), "postgres", precision=precision)
    built = build_compiled(artifact)
    if entry == "live":
        return prepare_live_template(artifact), built
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    return prepare_compiled_template(root), built


def description(codes, labels):
    from types import SimpleNamespace

    return tuple(
        SimpleNamespace(name=label, type_code=code, null_ok=None)
        for label, code in zip(labels, codes, strict=True)
    )


class Plan:
    """Native batches to deliver; FAIL raises after them like a lost read."""

    def __init__(self, batches, codes, *, terminal="EOF"):
        self.batches = [
            b if b == FAIL else tuple(tuple(row) for row in b) for b in batches
        ]
        self.codes = codes
        self.terminal = terminal
        self.metadata = None


def simulated_next(owner):
    """SIMULATED_NATIVE_IO stepper for PostgresExecution; terminal fields are real."""
    from pietto._project.project_execution import ExecutionFailure
    from pietto._project.project_execution_reader import ExecutionPayloads
    from pietto._project.project_result_contract import ResultError

    plan = PLANS[id(owner)]
    if owner._closed:
        raise StopIteration
    phase = "read"
    try:
        if owner._payloads is None:
            labels = tuple(f.label for f in owner.request.contract.shape.fields)
            owner._payloads = ExecutionPayloads(
                owner.request, description(plan.codes, labels)
            )
            owner._source, owner._delivery, owner._transaction = (
                "READING",
                "OPEN",
                "OPEN",
            )
        if not plan.batches:
            owner._source, owner._delivery = "EOF", "COMPLETE"
            owner._transaction = "COMMIT_ACK"
            owner._cleanup, owner._closed = "CLOSED", True
            raise StopIteration
        rows = plan.batches.pop(0)
        if rows == FAIL:
            raise ResultError("EXECUTION_CARRIER")
        phase = "check"
        return owner._payloads.accept(rows)
    except StopIteration:
        raise
    except BaseException as error:
        owner._primary = ExecutionFailure(phase, type(error).__name__)
        owner._source = "INCOMPLETE" if phase == "check" else "FAILED"
        owner._delivery, owner._transaction = "FAILED", "ROLLBACK_ACK"
        owner._cleanup, owner._closed = "CLOSED", True
        raise


PLANS: dict[int, Plan] = {}


def simulate(monkeypatch, owner, plan):
    from pietto._project.project_execution_postgres import PostgresExecution

    PLANS[id(owner)] = plan
    if monkeypatch is None:
        PostgresExecution.__next__ = simulated_next  # type: ignore[method-assign]
    else:
        monkeypatch.setattr(PostgresExecution, "__next__", simulated_next)
    return owner


def pg_owner(binding, *, batch_rows=2):
    """A real compiled PostgresExecution; never connected in ordinary tests."""
    from pietto._project import project_execution as ex
    from pietto._project.project_execution_postgres import PostgresExecution

    access = ex.PostgresAccess(
        "127.0.0.1", 9, "phase66", "pietto_query", "pw", "disable"
    )
    request = ex.prepare_compiled_execution(
        binding,
        access,
        route="postgres_rows",
        limits=ex.ExecutionLimits(batch_rows=batch_rows, seconds=5),
        postgres_deployment=ex.PostgresDeploymentPremise(
            access,
            binding.artifact.request.sources,
            ("public", "pg_catalog"),
            "postgres_rows",
        ),
    )
    return PostgresExecution(request)


def op():
    from pietto._project import project_job_store as s

    return s.new_operation()


def store(root, template, values=(), *, format=None, **options):
    """A v2 (default) workspace with one job, publisher, binding and generation."""
    from pietto._project import project_job_store as s
    from pietto._project import project_job_workspace as w
    from pietto._project.project_execution_template import bind_values

    workspace = w.create_workspace(
        str(root), format=w.FORMAT_V2 if format is None else format, **options
    )
    job = s.register_job(workspace, template, operation=op()).get("job")
    publisher = s.claim_publisher(workspace, job, operation=op())
    binding = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    record = s.register_binding(publisher, binding, operation=op()).get("binding")
    generation = s.register_generation(
        publisher,
        record,
        binding,
        route="postgres_rows",
        isolation="stable",
        operation=op(),
    ).get("generation")
    return workspace, job, publisher, binding, record, generation


def attempt_owner(publisher, generation, binding, plan, monkeypatch):
    from pietto._project import project_job_store as s

    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    owner = simulate(monkeypatch, pg_owner(binding), plan)
    return attempt, owner


def read_all(workspace, job, generation, built, *, checkpoint=None):
    """Fresh-trust stored output plus a VERIFIED read of every member."""
    from pietto._project import project_job_capture as c

    output = c.stored_output(
        workspace,
        job,
        generation,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    snapshot = c.checkpoint_snapshot(workspace, job, generation, checkpoint=checkpoint)
    with c.SnapshotReader(workspace, snapshot, output) as reader:
        chunks = [reader.read(i) for i in range(len(snapshot.members))]
        summary = reader.verify()
    return snapshot, chunks, summary


def values(chunks):
    return [
        tuple(row[name] for name in chunk.table.column_names)
        for chunk in chunks
        for row in chunk.table.to_pylist()
    ]


CHILD_HEADER = r"""
import json, os, signal, sys, time
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[3])
config = json.loads(sys.argv[2])
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c, project_job_chunks as k
import _pietto_phase68_slice12_probe as probe

def barrier(name):
    sys.stdout.write(name + "\n")
    sys.stdout.flush()

def hold():
    while True:
        time.sleep(60)

def attach():
    workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
    template = s.load_job(workspace, config["job"], expected_pin=config["pin"],
        accepted_producer=config["producer"],
        accepted_compatibility=tuple(config["compatibility"]))
    binding = s.bind_record(workspace, config["job"], template, config["record"])
    publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
    attempt = s.open_attempt(publisher, config["generation"], binding,
        operation=s.new_operation())
    plan = probe.Plan(config["batches"], tuple(config["codes"]))
    owner = probe.simulate(None, probe.pg_owner(binding), plan)
    return workspace, publisher, attempt, owner
"""


def child(program, config):
    """A registered, isolated spawned child; the caller must reap it."""
    import subprocess

    return subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            CHILD_HEADER + program,
            str(ROOT / "src"),
            json.dumps(config),
            str(ROOT / "tests"),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/",
    )


def child_config(workspace, job, record, generation, built, batches, codes):
    return {
        "workspace": workspace.root,
        "identity": workspace.identity,
        "job": job,
        "record": record,
        "generation": generation,
        "pin": built.pin,
        "producer": built.producer,
        "compatibility": list(built.compatibility),
        "batches": [b if b == FAIL else [list(r) for r in b] for b in batches],
        "codes": list(codes),
    }


def tree(root) -> dict[str, Any]:
    """Names, kinds and sizes under a workspace (no content)."""
    result = {}
    for directory, names, files in os.walk(root):
        for name in names + files:
            path = os.path.join(directory, name)
            state = os.lstat(path)
            result[os.path.relpath(path, root)] = (state.st_mode >> 12, state.st_size)
    return result


def synthetic_frame(rows, *, size=64, contract=bytes(32)):
    """An independently framed IPC envelope with opaque payload (no Arrow)."""
    from _pietto_phase67_result_product_probe import ipc_envelope

    return ipc_envelope(b"\x5a" * size, rows, 1 if rows else 0, contract)


def stage_frame(session, rows, *, size=64, terminal=None):
    """ARROW_FREE_STORAGE_STEP: what a checked batch of `rows` would materialize.

    Storage-mechanics tests only; positions advance exactly as the checked
    producer step assigns them. Real captures always go through `stage()`.
    """
    workspace = session.publisher.use()
    start, batches = session._observed, 1 if rows else 0
    session._observed += rows
    session._batches += batches
    return session._materialize(
        workspace,
        synthetic_frame(rows, size=size, contract=bytes.fromhex(session.contract)),
        start,
        rows,
        batches,
        None,
        terminal,
    )


def capture(workspace, publisher, generation, binding):
    """A real never-connected owner bound to a new attempt and capture session."""
    from pietto._project import project_job_capture as c
    from pietto._project import project_job_store as s

    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    owner = pg_owner(binding)
    return c.begin_capture(publisher, attempt, owner, operation=op())


# ---------------------------------------------------------------------------
# Execution-profile families (Arrow and drivers present). Nothing runs at import.

LOOP = (
    "                for batch in owner:\n"
    "                    with batch:\n"
    "                        data = pa.record_batch(batch)\n"
    "                        schemas.append([[f.name, str(f.type), f.nullable]"
    " for f in data.schema])\n"
    "                        rows.extend([[scalar(data.column(i)[j].as_py()) for i in"
    " range(data.num_columns)] for j in range(data.num_rows)])\n"
)

CAPTURE = r"""
from pietto._project import project_job_capture as c
current = {}
def publish(session, item):
    result = session.publish(item, operation=s.new_operation())
    snapshot = c.checkpoint_snapshot(workspace, config["job"], attempt.generation)
    return {"chunk": item.identity, "start": item.start, "stop": item.stop,
        "ordinal": result.get("ordinal"), "frontier": result.get("frontier"),
        "members": result.get("members"), "snapshot_frontier": snapshot.frontier,
        "committed": snapshot.committed, "holes": snapshot.holes}
def capture_case(owner):
    session = c.begin_capture(publisher, attempt, owner, operation=s.new_operation())
    current.clear()
    current.update(session=session, staged=[], published=[], control=None)
    while True:
        item = session.stage()
        if item is None:
            break
        current["staged"].append([item.start, item.stop, item.batches])
        if case != "A":
            current["published"].append(publish(session, item))
        if case == "A_late" and len(current["staged"]) == 1:
            current["control"] = owner.cancel()
    staged = list(session.staged)
    order = [0, *range(2, len(staged)), 1] if len(staged) >= 3 else range(len(staged))
    for index in order:
        current["published"].append(publish(session, staged[index]))
"""

EPILOGUE = r"""
        session = current["session"]
        ended = session.end(operation=s.new_operation())
        recorded = s.record_attempt(publisher, attempt, owner, operation=s.new_operation())
        snapshot = c.checkpoint_snapshot(workspace, config["job"], generation)
        result["store"] = {"job": config["job"], "binding_record": record,
            "generation": generation, "attempt": attempt.identity,
            "ordinal": attempt.ordinal, "publisher_epoch": publisher.epoch,
            "operation": recorded.operation, "sequence": recorded.sequence,
            "pid": os.getpid()}
        result["capture"] = {"staged": current["staged"],
            "published": current["published"], "control": current["control"],
            "terminal": session.terminal, "observed": session.observed,
            "end": dict(ended.result), "frontier": snapshot.frontier,
            "committed": snapshot.committed, "holes": snapshot.holes,
            "observed_end": snapshot.observed_end,
            "session_source": snapshot.session_source,
            "layers": dict(snapshot.layers), "checkpoint": snapshot.checkpoint,
            "ordinal": snapshot.ordinal, "contract": snapshot.contract}
        results.append(result)
        retain_raw({"results":results,"forbidden_calls":forbidden_calls})
        if failure is not None and case != "A_late":
            raise RuntimeError("native bridge attempt failed; raw preserved")
publisher.close()
workspace.close()
"""

READ = r"""
from pietto._project import project_job_workspace as w, project_job_capture as c
workspace = w.open_workspace(config["workspace"], expected_identity=config["workspace_identity"])
reads = []
for route, plan in config["plan"]:
    for case, number, record, generation in plan:
        started = time.monotonic()
        output = c.stored_output(workspace, config["job"], generation,
            expected_pin=config["pin"], accepted_producer=config["producer"],
            accepted_compatibility=tuple(config["compatibility"]))
        snapshot = c.checkpoint_snapshot(workspace, config["job"], generation)
        with c.SnapshotReader(workspace, snapshot, output) as reader:
            chunks = [reader.read(i) for i in range(len(snapshot.members))]
            summary = reader.verify()
        tables = [x.table for x in chunks]
        reads.append({"route": route, "case": case, "generation": generation,
            "rows": [[scalar(t.column(i)[j].as_py()) for i in range(t.num_columns)]
                for t in tables for j in range(t.num_rows)],
            "schemas": [[[f.name, str(f.type), f.nullable] for f in t.schema] for t in tables],
            "extents": [[x.start, x.stop, x.terminal] for x in chunks],
            "summary": summary, "frontier": snapshot.frontier,
            "committed": snapshot.committed, "recorded": snapshot.integrity,
            "seconds": time.monotonic() - started})
workspace.close()
"""

CORE_ONLY = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
from pietto._project import project_job_capture as c, project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
workspace = w.open_workspace(config["workspace"], expected_identity=config["workspace_identity"])
snapshots = {}
for generation in config["generations"]:
    snapshot = c.checkpoint_snapshot(workspace, config["job"], generation)
    snapshots[generation] = [snapshot.frontier, snapshot.integrity, len(snapshot.members)]
summary = verify_store(workspace)
protected = sorted(c.protected_chunks(workspace, config["job"]))
files = c.classify_files(workspace)
workspace.close()
optional = sorted(n for n in sys.modules if n.split(".")[0] in
    ("pyarrow", "psycopg", "adbc_driver_manager", "adbc_driver_postgresql", "mysql"))
package = Path(sys.modules["pietto"].__file__).resolve().parent
Path(config["raw"]).write_text(json.dumps({"summary": summary, "optional": optional,
    "snapshots": snapshots, "protected": len(protected),
    "files": {k: len(v) for k, v in files.items()}, "package": str(package),
    "prefix": sys.prefix}))
"""

OLD_RUNTIME = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import importlib.util, json, os, zipfile
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
with zipfile.ZipFile(config["wheel"]) as archive:
    source = archive.read("pietto/_project/project_job_workspace.py")
spec = importlib.util.spec_from_loader("s11_published_workspace", loader=None)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
exec(compile(source, "s11-wheel/project_job_workspace.py", "exec"), module.__dict__)
def tree(root):
    return sorted((os.path.relpath(os.path.join(d, n), root),
        os.lstat(os.path.join(d, n)).st_size, os.lstat(os.path.join(d, n)).st_mtime_ns)
        for d, names, files in os.walk(root) for n in names + files)
before = tree(config["workspace"])
try:
    module.open_workspace(config["workspace"], expected_identity=config["workspace_identity"])
    outcome = "ACCEPTED"
except module.JobStoreError as error:
    outcome = str(error)
Path(config["raw"]).write_text(json.dumps({"outcome": outcome,
    "unchanged": tree(config["workspace"]) == before,
    "s11_format": module.FORMAT}))
"""


def _replace(text, old, new):
    assert text.count(old) == 1, old[:60]
    return text.replace(old, new)


def worker_programs():
    """S12 register/execute/read around S10's verbatim native body (exact anchors)."""
    from _pietto_phase68_slice10_probe import WORKER
    from _pietto_phase68_slice11_probe import EXECUTE_EPILOGUE
    from _pietto_phase68_slice11_probe import worker_programs as original

    register, execute = original()
    register = _replace(
        register,
        'workspace = w.create_workspace(config["workspace"])\n',
        'workspace = w.create_workspace(config["workspace"], format=w.FORMAT_V2)\n',
    )
    execute = _replace(execute, LOOP, "                capture_case(owner)\n")
    execute = _replace(
        execute,
        "results = []\nfor route, plan",
        CAPTURE + "results = []\nfor route, plan",
    )
    execute = _replace(execute, EXECUTE_EPILOGUE, EPILOGUE)

    def at(anchor):
        assert WORKER.count(anchor) == 1, anchor
        return WORKER.index(anchor)

    read = (
        WORKER[: at("live_template = None\n")]
        + WORKER[at("forbidden_calls = []\n") : at("load_started = time.monotonic()\n")]
        + READ
        + "retain_raw({'reads': reads, 'forbidden_calls': forbidden_calls})\n"
        + WORKER[at("origins = {}\n") :].replace('"results":results,', '"reads":reads,')
    )
    return register, execute, read


def bridge(
    directory,
    ledger,
    interpreter,
    *,
    target,
    cells,
    wheel=None,
    core=None,
    old_wheel=None,
):
    """Bounded native S12 bridge: register, capture, fresh reader, checks, damages."""
    import hashlib
    import inspect
    import shutil
    import sqlite3
    import time
    import zipfile

    from _pietto_phase68_slice4_probe import ROWS, s01, template
    from _pietto_phase68_slice6_probe import manager
    from _pietto_phase68_slice8_probe import event, worker_process
    from _pietto_phase68_slice10_check import check_small_pg, check_small_pg_damage
    from _pietto_phase68_slice12_check import check_bridge_store, check_bridge_damage
    from _pietto_target_conformance_resources import Resources, clean_environment
    from pietto._project import project_job_workspace as w
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_job_store_verification import verify_store

    cells = tuple(cells)
    if (
        not cells
        or len(set(cells)) != len(cells)
        or any(
            o not in ("source", "installed") or e not in ("live", "bundle")
            for o, e in cells
        )
        or (any(o == "installed" for o, _e in cells) and wheel is None)
    ):
        raise ValueError("S12_BRIDGE_CELLS")
    directory.mkdir(mode=0o700)
    event(
        ledger,
        {
            "kind": "s12_bridge_start",
            "directory": str(directory),
            "target": target,
            "cells": [list(c) for c in cells],
        },
        targeted_storage_or_native_family_starts=1,
    )
    state = json.loads(ledger.read_text())
    state["owned_resources"].append(
        {"kind": "native_bridge_directory", "path": str(directory), "target": target}
    )
    ledger.write_text(json.dumps(state, indent=2) + "\n")
    project = directory / (PREFIX + "build-only")
    artifact = template(project, target=target).artifact
    expected_sql = artifact.rendered.sql.decode()
    built = build_compiled(artifact)
    bundle = directory / (PREFIX + "bundle.json")
    with bundle.open("xb") as stream:
        stream.write(built.payload)
    bundle.chmod(0o600)
    shutil.rmtree(project)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources(target, pins["targets"][target], directory)
    state = json.loads(ledger.read_text())
    state["owned_resources"].append(
        {
            "kind": "database_resource",
            "target": target,
            "name": resource.name,
            "network_name": resource.network_name,
            "directory": str(directory),
            "journal": str(directory / "resources.jsonl"),
        }
    )
    ledger.write_text(json.dumps(state, indent=2) + "\n")
    routes = ["mysql_rows"] if target == "mysql" else ["postgres_rows", "postgres_adbc"]
    values = [["A", 1], ["B", 5], ["A_again", 1], ["empty", 2**63 - 1], ["A_late", 1]]
    register_program, execute_program, read_program = worker_programs()
    prefix = (
        "import struct\nfrom decimal import Decimal\nfrom datetime import datetime\n"
        "from uuid import UUID\n" + inspect.getsource(s01.scalar) + "\n"
    )
    private = directory / (PREFIX + "private-input.json")
    report: dict[str, Any] = {
        "status": "STARTED",
        "target": target,
        "routes": routes,
        "cells": [],
        "sql": expected_sql,
        "pin": built.pin,
    }
    start = time.monotonic()

    def run(program, config, name, group, origin):
        descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(config, stream)
        try:
            with (directory / (PREFIX + name + ".log")).open("wb") as log:
                return worker_process(
                    [
                        str(interpreter if origin != "core" else core),
                        "-I",
                        "-B",
                        "-c",
                        program,
                        str(private),
                    ],
                    clean_environment(),
                    ledger,
                    log,
                    origin=origin,
                    group=group,
                    directory=directory,
                    seconds=900,
                )
        finally:
            private.unlink(missing_ok=True)

    def installed_bytes(origins):
        assert wheel is not None
        with zipfile.ZipFile(wheel) as archive:
            for name, item in origins.items():
                member = "/".join(name.split(".")) + (
                    "/__init__.py"
                    if Path(item["path"]).name == "__init__.py"
                    else ".py"
                )
                if hashlib.sha256(archive.read(member)).hexdigest() != item["sha256"]:
                    raise ValueError("S12_INSTALLED_MEMBER_BYTES")

    try:
        report["runtime"] = s01.runtime_identity()
        if (
            report["runtime"]["versions"]
            != s01.helper("_pietto_phase68_executor_cases").PINS
        ):
            raise ValueError("S12_RUNTIME_PINS")
        if wheel is not None:
            report["wheel"] = str(wheel)
            report["wheel_sha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()
        report["storage_profile"] = repr(w.storage_profile(str(directory)))
        event(
            ledger,
            {
                "kind": "s12_database_start",
                "directory": str(directory),
                "name": resource.name,
            },
            source_db_lifecycle_starts=1,
        )
        resource.acquire()
        if target == "mysql":
            manager(resource, "USE phase66")
        quote = '"' if target == "postgres" else "`"
        manager(
            resource,
            f"CREATE TABLE {quote}rows{quote}(id BIGINT NOT NULL,other BIGINT)",
        )
        for row in ROWS:
            manager(
                resource,
                f"INSERT INTO {quote}rows{quote} VALUES "
                + ("($1,$2)" if target == "postgres" else "(?,?)"),
                row,
            )
        for sql, _secret in resource.role_statements():
            manager(resource, sql)
        if target == "mysql":
            for table in ("threads", "events_transactions_current"):
                manager(
                    resource,
                    "GRANT SELECT ON performance_schema."
                    + table
                    + " TO 'pietto_query'@'%'",
                )
            manager(resource, "GRANT SHOW VIEW ON phase66.* TO 'pietto_query'@'%'")
        password = resource._passwords[1]
        for origin, entry in cells:
            name = origin + "-" + entry
            workspace = directory / (PREFIX + name + "-workspace")
            registration_path = directory / (PREFIX + name + "-registration.json")
            raw = directory / (PREFIX + name + "-native-raw.json")
            read_raw = directory / (PREFIX + name + "-read-raw.json")
            runtime_cwd = directory / (PREFIX + name + "-runtime")
            runtime_cwd.mkdir(mode=0o700)
            common = {
                "runtime_cwd": str(runtime_cwd),
                "origin": origin,
                "entry": entry,
                "target": target,
                "library_source": str(ROOT / "src"),
                "workspace": str(workspace),
            }
            code = run(
                prefix + register_program,
                {
                    **common,
                    "build_helpers": str(ROOT / "tests"),
                    "live_project": str(
                        directory / (PREFIX + name + "-live-build-only")
                    ),
                    "bundle": str(bundle),
                    "pin": built.pin,
                    "producer": built.producer,
                    "compatibility": built.compatibility,
                    "routes": routes,
                    "values": values,
                    "raw": str(registration_path),
                },
                name + "-register",
                "s12-register-" + name,
                origin,
            )
            cell: dict[str, Any] = {
                "origin": origin,
                "entry": entry,
                "register_exit": code,
            }
            report["cells"].append(cell)
            if code:
                raise ValueError("S12_REGISTER_WORKER_FAILED")
            registration = json.loads(registration_path.read_text())
            accepted = (
                (built.pin, built.producer, list(built.compatibility))
                if entry == "bundle"
                else (
                    registration["pin"],
                    registration["producer"],
                    registration["compatibility"],
                )
            )
            if accepted != (
                registration["pin"],
                registration["producer"],
                registration["compatibility"],
            ):
                raise ValueError("S12_TRUST_HANDOFF")
            trusted = {
                **common,
                "removed_query_project": str(project),
                "workspace_identity": registration["workspace_identity"],
                "job": registration["job"],
                "pin": accepted[0],
                "producer": accepted[1],
                "compatibility": accepted[2],
                "plan": registration["plan"],
            }
            code = run(
                prefix + execute_program,
                {
                    **trusted,
                    "port": resource.port,
                    "password": password,
                    "ca_path": str(resource.ca_path) if target == "mysql" else None,
                    "request_seconds": 20,
                    "raw": str(raw),
                },
                name + "-execute",
                "s12-execute-" + name,
                origin,
            )
            cell["execute_exit"] = code
            cell["raw"] = str(raw) if raw.exists() else None
            if code:
                raise ValueError("S12_EXECUTE_WORKER_FAILED")
            # A fresh source-free process: fresh trust, no source and no access.
            code = run(
                prefix + read_program,
                {**trusted, "raw": str(read_raw)},
                name + "-read",
                "s12-read-" + name,
                origin,
            )
            cell["read_exit"] = code
            if code:
                raise ValueError("S12_READ_WORKER_FAILED")
            data = json.loads(raw.read_text())
            reads = json.loads(read_raw.read_text())
            if origin == "installed":
                for item in (data, reads, registration):
                    installed_bytes(item["origins"])
            origin_root = (
                ROOT / "src/pietto" if origin == "source" else interpreter.parent.parent
            )
            by_cell = {(r["route"], r["case"]): r for r in reads["reads"]}
            merged = {**data, "results": []}
            for result in data["results"]:
                if result["case"] == "A_late":
                    continue
                read = by_cell[(result["route"], result["case"])]
                merged["results"].append(
                    {**result, "rows": read["rows"], "schemas": read["schemas"]}
                )
            check_small_pg(
                merged,
                tuple(ROWS),
                origin_root,
                expected_sql,
                origin=origin,
                entry=entry,
                target=target,
            )
            check_small_pg_damage(
                merged,
                tuple(ROWS),
                origin_root,
                expected_sql,
                origin=origin,
                entry=entry,
                target=target,
            )
            opened = w.open_workspace(
                str(workspace), expected_identity=registration["workspace_identity"]
            )
            backup = directory / (PREFIX + name + "-store-backup.sqlite")
            try:
                cell["verify_store"] = verify_store(opened)
                descriptor = os.open(
                    backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                os.close(descriptor)
                copy = sqlite3.connect(backup)
                try:
                    opened.use().backup(copy)
                finally:
                    copy.close()
            finally:
                opened.close()
            cell["store"] = check_bridge_store(
                backup, workspace, registration, data, reads, tuple(ROWS), target=target
            )
            cell["store_damage_rejected"] = check_bridge_damage(
                backup,
                workspace,
                registration,
                data,
                reads,
                tuple(ROWS),
                target=target,
                scratch=directory / (PREFIX + name + "-damage"),
            )
            if origin == "installed" and core is not None:
                core_raw = directory / (PREFIX + name + "-core-only.json")
                code = run(
                    CORE_ONLY,
                    {
                        "workspace": str(workspace),
                        "workspace_identity": registration["workspace_identity"],
                        "job": registration["job"],
                        "generations": [
                            g[3] for _r, group in registration["plan"] for g in group
                        ],
                        "raw": str(core_raw),
                    },
                    name + "-core-only",
                    "s12-core-only-" + name,
                    "core",
                )
                if code:
                    raise ValueError("S12_CORE_ONLY_WORKER_FAILED")
                observed = json.loads(core_raw.read_text())
                expected_package = (
                    Path(core).parent.parent / "lib/python3.13/site-packages/pietto"
                ).resolve()
                if (
                    observed["optional"]
                    or observed["package"] != str(expected_package)
                    or observed["summary"]["chunks"] != cell["store"]["chunks"]
                    or observed["files"]["orphans"]
                    or observed["files"]["missing"]
                ):
                    raise ValueError("S12_CORE_ONLY")
                cell["core_only"] = observed
            if old_wheel is not None and "old_runtime" not in report:
                old_raw = directory / (PREFIX + name + "-old-runtime.json")
                code = run(
                    OLD_RUNTIME,
                    {
                        "workspace": str(workspace),
                        "wheel": str(old_wheel),
                        "workspace_identity": registration["workspace_identity"],
                        "raw": str(old_raw),
                    },
                    name + "-old-runtime",
                    "s12-old-runtime-" + name,
                    "old-runtime",
                )
                observed = json.loads(old_raw.read_text())
                if code or observed != {
                    "outcome": "WORKSPACE_FORMAT",
                    "unchanged": True,
                    "s11_format": "pietto.job-workspace.v1",
                }:
                    raise ValueError("S12_OLD_RUNTIME")
                report["old_runtime"] = {
                    **observed,
                    "wheel_sha256": hashlib.sha256(old_wheel.read_bytes()).hexdigest(),
                }
            cell["status"] = "PASS"
        report["status"] = "PASS"
    except BaseException as error:
        report["status"] = "FAILED"
        report["error_kind"] = type(error).__name__
        report["error"] = str(error)[:2000].replace(
            getattr(resource, "_passwords", ("", ""))[1] or "\0", "<redacted>"
        )
        raise
    finally:
        report["cleanup"] = resource.cleanup()
        private.unlink(missing_ok=True)
        report["seconds"] = time.monotonic() - start
        (directory / (PREFIX + "bridge.json")).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
        event(
            ledger,
            {
                "kind": "s12_bridge_terminal",
                "status": report["status"],
                "directory": str(directory),
                "seconds": report["seconds"],
            },
        )
    return report


ARROW_SUITE = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import hashlib, json, os, time
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["runtime_cwd"])
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
sys.path.insert(0, config["tests"])
import _pietto_phase68_slice12_probe as probe
from pietto._project import project_job_capture as c, project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
base = Path(config["directory"])
templates = {p: probe.seven_template(base / ("build-" + str(p)), precision=p) for p in (39, 65)}
cases = {}
for name, precision, batches in (
    ("seven39", 39, [probe.SEVEN_ROWS[:2], probe.SEVEN_ROWS[2:4], probe.SEVEN_ROWS[4:]]),
    ("seven65", 65, [probe.SEVEN65_ROWS[:2], probe.SEVEN65_ROWS[2:]]),
    ("empty", 39, []),
    ("late", 39, [probe.SEVEN_ROWS[:2], [probe.LATE_INVALID]]),
    ("full_last", 39, [probe.SEVEN_ROWS[:2], probe.SEVEN_ROWS[2:4]]),
):
    template, built = templates[precision]
    root = base / (name + "-workspace")
    workspace, job, publisher, binding, record, generation = probe.store(root, template)
    attempt, owner = probe.attempt_owner(
        publisher, generation, binding, probe.Plan(batches, probe.SEVEN_CODES), None)
    session = c.begin_capture(publisher, attempt, owner, operation=s.new_operation())
    staged, published, failure, calls = [], [], None, 0
    try:
        while True:
            calls += 1
            item = session.stage()
            if item is None:
                break
            staged.append(item)
            if name == "late":
                published.append(dict(session.publish(item, operation=s.new_operation()).result))
    except Exception as error:
        failure = type(error).__name__ + ":" + str(error)
    if name != "late":
        order = [0, 2, 1] if name == "seven39" else range(len(staged))
        for index in order:
            published.append(dict(session.publish(staged[index], operation=s.new_operation()).result))
    ended = session.end(operation=s.new_operation())
    s.record_attempt(publisher, attempt, owner, operation=s.new_operation())
    snapshot, chunks, summary = probe.read_all(workspace, job, generation, built)
    values = [[scalar(v) for v in row] for row in probe.values(chunks)]
    controls = {}
    for label, call in (
        ("wrong_trust", lambda: c.stored_output(workspace, job, generation,
            expected_pin="0" * 64, accepted_producer=built.producer,
            accepted_compatibility=built.compatibility)),
        ("foreign_output", lambda: c.SnapshotReader(workspace, snapshot,
            cases_output["seven39"]) if name == "seven65" else None),
    ):
        try:
            controls[label] = None if call() is None else "ACCEPTED"
        except Exception as error:
            controls[label] = str(error)
    if name == "seven39":
        cases_output = {"seven39": c.stored_output(workspace, job, generation,
            expected_pin=built.pin, accepted_producer=built.producer,
            accepted_compatibility=built.compatibility)}
    cases[name] = {"workspace": str(root), "identity": workspace.identity, "job": job,
        "generation": generation, "staged": [[x.start, x.stop, x.batches] for x in staged],
        "published": published, "failure": failure, "calls": calls,
        "terminal": session.terminal, "observed": session.observed,
        "end": dict(ended.result), "summary": summary, "values": values,
        "schemas": [[[f.name, str(f.type), f.nullable] for f in x.table.schema] for x in chunks],
        "extents": [[x.start, x.stop, x.terminal] for x in chunks],
        "layers": dict(snapshot.layers), "holes": snapshot.holes,
        "frontier": snapshot.frontier, "contract": snapshot.contract,
        "controls": controls, "verify": verify_store(workspace)}
    publisher.close()
    workspace.close()
# Production reader refusals on closed copies of a committed workspace.
import shutil, sqlite3
from pietto._project import project_job_chunks as k
source_case = cases["full_last"]
_template, built = templates[39]
damages = {}
for kind in ("missing", "truncated", "byte", "coordinated"):
    root = base / ("damage-" + kind)
    shutil.copytree(source_case["workspace"], root)
    names = sorted(os.listdir(root / "chunks"))
    connection = sqlite3.connect(root / "store.sqlite")
    member = connection.execute("SELECT identity, file FROM chunk ORDER BY start").fetchall()[0]
    path = root / "chunks" / member[1]
    if kind == "missing":
        path.unlink()
    elif kind == "truncated":
        path.write_bytes(path.read_bytes()[:-1])
    elif kind == "byte":
        data = bytearray(path.read_bytes())
        data[len(data) // 2] ^= 1
        path.write_bytes(bytes(data))
    else:
        _text, descriptor, frame = k.decode_chunk(path.read_bytes())
        descriptor = {n: v for n, v in descriptor.items()
            if n not in ("format", "frame_bytes", "frame_sha256")}
        descriptor["generation"] = w.new_identity("gen")
        text, data = k.encode_chunk(descriptor, frame)
        path.write_bytes(data)
        connection.execute("UPDATE chunk SET bytes = ?, digest = ?, descriptor = ?"
            " WHERE identity = ?", (len(data), hashlib.sha256(data).hexdigest(), text, member[0]))
        connection.commit()
    connection.close()
    copy = w.open_workspace(str(root), expected_identity=source_case["identity"])
    try:
        output = c.stored_output(copy, source_case["job"], source_case["generation"],
            expected_pin=built.pin, accepted_producer=built.producer,
            accepted_compatibility=built.compatibility)
        snapshot = c.checkpoint_snapshot(copy, source_case["job"], source_case["generation"])
        with c.SnapshotReader(copy, snapshot, output) as reader:
            try:
                reader.verify()
                damages[kind] = "ACCEPTED"
            except Exception as error:
                damages[kind] = str(error)
    finally:
        copy.close()
    shutil.rmtree(root)
origins = {}
for name, module in tuple(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
        path = Path(filename).resolve()
        origins[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
Path(config["raw"]).write_text(json.dumps({"cases": cases, "damages": damages,
    "origins": origins, "prefix": sys.prefix}, ensure_ascii=False))
"""


def arrow_suite(directory, ledger, interpreter, *, cells, wheel=None):
    """Execution-profile capture: real ExecutionPayloads/Arrow/IPC, simulated fetch."""
    import hashlib
    import inspect
    import sqlite3
    import zipfile

    from _pietto_phase68_slice4_probe import s01
    from _pietto_phase68_slice8_probe import event, worker_process
    from _pietto_phase68_slice12_check import check_suite
    from _pietto_target_conformance_resources import clean_environment
    from pietto._project import project_job_workspace as w

    directory.mkdir(mode=0o700)
    event(
        ledger,
        {"kind": "s12_suite_start", "directory": str(directory), "cells": list(cells)},
        targeted_storage_or_native_family_starts=1,
    )
    prefix = (
        "import struct\nfrom decimal import Decimal\nfrom datetime import datetime\n"
        "from uuid import UUID\n" + inspect.getsource(s01.scalar) + "\n"
    )
    report: dict[str, Any] = {"status": "STARTED", "cells": {}}
    try:
        for origin in cells:
            base = directory / (PREFIX + origin)
            base.mkdir(mode=0o700)
            runtime = directory / (PREFIX + origin + "-runtime")
            runtime.mkdir(mode=0o700)
            raw = directory / (PREFIX + origin + "-suite-raw.json")
            private = directory / (PREFIX + origin + "-input.json")
            private.write_text(
                json.dumps(
                    {
                        "origin": origin,
                        "runtime_cwd": str(runtime),
                        "library_source": str(ROOT / "src"),
                        "tests": str(ROOT / "tests"),
                        "directory": str(base),
                        "raw": str(raw),
                    }
                )
            )
            program = ARROW_SUITE.replace(
                "import _pietto_phase68_slice12_probe as probe\n",
                "import _pietto_phase68_slice12_probe as probe\n" + prefix,
                1,
            )
            with (directory / (PREFIX + origin + "-suite.log")).open("wb") as log:
                code = worker_process(
                    [str(interpreter), "-I", "-B", "-c", program, str(private)],
                    clean_environment(),
                    ledger,
                    log,
                    origin=origin,
                    group="s12-suite-" + origin,
                    directory=directory,
                    seconds=900,
                )
            if code:
                raise ValueError("S12_SUITE_WORKER_FAILED")
            data = json.loads(raw.read_text())
            if origin == "installed":
                assert wheel is not None
                if any(
                    not item["path"].startswith(data["prefix"] + "/")
                    for item in data["origins"].values()
                ):
                    raise ValueError("S12_INSTALLED_ORIGIN")
                with zipfile.ZipFile(wheel) as archive:
                    for name, item in data["origins"].items():
                        member = "/".join(name.split(".")) + (
                            "/__init__.py"
                            if Path(item["path"]).name == "__init__.py"
                            else ".py"
                        )
                        if (
                            hashlib.sha256(archive.read(member)).hexdigest()
                            != item["sha256"]
                        ):
                            raise ValueError("S12_INSTALLED_MEMBER_BYTES")
            elif any(
                not item["path"].startswith(str(ROOT / "src"))
                for item in data["origins"].values()
            ):
                raise ValueError("S12_SOURCE_ORIGIN")
            backups = {}
            for name, case in data["cases"].items():
                opened = w.open_workspace(
                    case["workspace"], expected_identity=case["identity"]
                )
                backup = directory / (PREFIX + origin + "-" + name + "-backup.sqlite")
                try:
                    os.close(
                        os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    )
                    copy = sqlite3.connect(backup)
                    try:
                        opened.use().backup(copy)
                    finally:
                        copy.close()
                finally:
                    opened.close()
                backups[name] = str(backup)
            report["cells"][origin] = check_suite(data, backups)
        report["status"] = "PASS"
    except BaseException as error:
        report.update(
            status="FAILED", error_kind=type(error).__name__, error=str(error)[:2000]
        )
        raise
    finally:
        (directory / (PREFIX + "suite.json")).write_text(
            json.dumps(report, indent=2) + "\n"
        )
        event(
            ledger,
            {
                "kind": "s12_suite_terminal",
                "status": report["status"],
                "directory": str(directory),
            },
        )
    return report


REPRESENTATIVE_SETUP = r"""
from pietto._project import project_job_store as s12s, project_job_workspace as s12w
from pietto._project import project_job_capture as s12c
S12_ROOT = template.artifact.request.verification.completed.root
S12_WORKSPACE = s12w.create_workspace(config["raw"][: -len("-raw.json")] + "-workspace",
    format=s12w.FORMAT_V2)
S12_JOB = s12s.register_job(S12_WORKSPACE, template, operation=s12s.new_operation()).get("job")
S12_PUBLISHER = s12s.claim_publisher(S12_WORKSPACE, S12_JOB, operation=s12s.new_operation())
S12 = {}
def S12_CAPTURE(owner):
    S12["owner"] = owner
    session = S12["session"] = s12c.begin_capture(S12_PUBLISHER, S12["attempt"], owner,
        operation=s12s.new_operation())
    output = s12c.stored_output(S12_WORKSPACE, S12_JOB, S12["generation"],
        expected_pin=S12_ROOT.expected_pin, accepted_producer=S12_ROOT.accepted_producer,
        accepted_compatibility=S12_ROOT.accepted_compatibility)
    S12["extents"] = []
    while True:
        staged = session.stage()
        if staged is None:
            return
        session.publish(staged, operation=s12s.new_operation())
        snapshot = s12c.checkpoint_snapshot(S12_WORKSPACE, S12_JOB, S12["generation"])
        with s12c.SnapshotReader(S12_WORKSPACE, snapshot, output) as reader:
            checked = reader.read(len(snapshot.members) - 1)
        S12["extents"].append([checked.start, checked.stop, checked.terminal,
            snapshot.frontier, None if checked.coordinates is None else len(checked.coordinates)])
        yield from checked.table.to_batches()
"""

REPRESENTATIVE_ATTEMPT = r"""
    S12["record"] = s12s.register_binding(S12_PUBLISHER, bound, operation=s12s.new_operation()).get("binding")
    S12["generation"] = s12s.register_generation(S12_PUBLISHER, S12["record"], bound,
        route=route, isolation=options.get("isolation", "stable"),
        operation=s12s.new_operation()).get("generation")
    S12["attempt"] = s12s.open_attempt(S12_PUBLISHER, S12["generation"], bound,
        operation=s12s.new_operation())
"""

REPRESENTATIVE_RECORD = r"""
    S12_END = S12["session"].end(operation=s12s.new_operation())
    s12s.record_attempt(S12_PUBLISHER, S12["attempt"], S12["owner"], operation=s12s.new_operation())
    S12_SNAPSHOT = s12c.checkpoint_snapshot(S12_WORKSPACE, S12_JOB, S12["generation"])
    record["s12"] = {"generation": S12["generation"], "attempt": S12["attempt"].identity,
        "extents": S12["extents"], "frontier": S12_SNAPSHOT.frontier,
        "committed": S12_SNAPSHOT.committed, "holes": S12_SNAPSHOT.holes,
        "observed_end": S12_SNAPSHOT.observed_end,
        "session_source": S12_SNAPSHOT.session_source,
        "layers": dict(S12_SNAPSHOT.layers), "kind": S12_SNAPSHOT.kind,
        "terminal": S12["session"].terminal, "workspace": S12_WORKSPACE.root,
        "identity": S12_WORKSPACE.identity, "job": S12_JOB}
"""


def capture_case_program(original=None):
    """S10's case worker with its owner loop anchored to capture + stored readback."""
    if original is None:
        from _pietto_phase68_slice10_probe import case_worker_program as original

    text = original()
    text = _replace(
        text,
        "        with owner:\n            for batch in owner:\n                with batch:\n"
        "                    array = pa.record_batch(batch)\n",
        "        with owner:\n            for array in S12_CAPTURE(owner):\n"
        "                if True:\n",
    )
    anchor = 'values=tuple(scalar_read(v).value for v in config["values"])\n'
    text = _replace(text, anchor, REPRESENTATIVE_SETUP + anchor)
    anchor = "    request=ex.prepare_compiled_execution("
    text = _replace(text, anchor, REPRESENTATIVE_ATTEMPT.lstrip("\n") + anchor)
    anchor = "    record=collect_owned(request)\n"
    text = _replace(text, anchor, anchor + REPRESENTATIVE_RECORD.lstrip("\n"))
    return _replace(
        text,
        "origins={}\n",
        "S12_PUBLISHER.close()\nS12_WORKSPACE.close()\norigins={}\n",
    )


def representatives(
    directory, ledger, interpreter, *, target, group, selected, cells, wheel=None
):
    """S10 matrix acquisition with capture; S10 checks the read-back values."""
    import sqlite3

    import _pietto_phase68_slice10_probe as s10
    from _pietto_phase68_slice8_probe import event
    from _pietto_phase68_slice12_check import check_representative_store
    from pietto._project import project_job_workspace as w
    from pietto._project.project_job_store_verification import verify_store

    event(
        ledger,
        {
            "kind": "s12_representatives_start",
            "directory": str(directory),
            "target": target,
            "group": group,
            "selected": [list(x) for x in selected],
        },
        targeted_storage_or_native_family_starts=1,
    )
    original = s10.case_worker_program
    s10.case_worker_program = lambda: capture_case_program(original)
    try:
        report = s10.acquire_matrix_group(
            directory,
            ledger,
            interpreter,
            target=target,
            group=group,
            cells=cells,
            wheel=wheel,
            selected=set(selected),
        )
    finally:
        s10.case_worker_program = original
    checked = []
    for item in report["records"]:
        if "raw" not in item:
            continue
        data = json.loads(Path(item["raw"]).read_text())
        for record in data["results"]:
            facts = record["s12"]
            opened = w.open_workspace(
                facts["workspace"], expected_identity=facts["identity"]
            )
            backup = Path(
                item["raw"][: -len("-raw.json")]
                + "-"
                + record["route"]
                + "-backup.sqlite"
            )
            try:
                summary = verify_store(opened)
                os.close(os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
                copy = sqlite3.connect(backup)
                try:
                    opened.use().backup(copy)
                finally:
                    copy.close()
            finally:
                opened.close()
            checked.append(
                {
                    "cell": item["cell"],
                    "origin": item["origin"],
                    "entry": item["entry"],
                    "route": record["route"],
                    "verify_store": summary,
                    "store": check_representative_store(backup, facts, record),
                }
            )
    report["s12"] = checked
    (directory / (PREFIX + "representatives.json")).write_text(
        json.dumps(checked, indent=2) + "\n"
    )
    event(
        ledger,
        {
            "kind": "s12_representatives_terminal",
            "directory": str(directory),
            "checked": len(checked),
        },
    )
    return report
