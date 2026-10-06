"""S15 delivery fixtures and explicit bounded families; import acquires nothing.

Ordinary tests have no Arrow. Saved inputs use S12's labelled Arrow-free storage
step, the read step is S13's ARROW_FREE_REPLAY_STEP and the row step is
ARROW_FREE_PAYLOAD_STEP: one deterministic exact typed row per occurrence of
the small two-Int output. Windows, issuance, the reference sink's own
transactions and replies, confirmations, fences and every SQLite transaction
still run for real. Real checked Arrow rows run only in the Arrow-only delivery
profile.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
import sys

import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice13_probe as s13

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice15-"
op = s12.op
# position -> salt: a test may change one occurrence's synthetic row.
SALT: dict[int, int] = {}


def store(root, template, values=(1,), **options):
    """A v5 workspace with one job, publisher, binding and generation."""
    from pietto._project import project_job_workspace as w

    return s12.store(root, template, values, format=w.FORMAT_V5, **options)


def capture(workspace, publisher, generation, binding, sizes, **options):
    """ARROW_FREE_STORAGE_STEP chunks (S13 helper, unchanged)."""
    return s13.capture(workspace, publisher, generation, binding, sizes, **options)


def sink(root, *, namespace="s15.reference", epoch=1, seconds=86400, **options):
    from pietto._project import project_job_sink as k

    return k.create_sink(
        str(root),
        namespace=namespace,
        epoch=epoch,
        retention_seconds=seconds,
        **options,
    )


def expected(handle) -> dict:
    """Independent caller expectations, as a cooperating operator states them."""
    return {
        "instance": handle.identity,
        "namespace": handle.namespace,
        "epoch": handle.epoch,
        "retention": handle.retention,
    }


def accept_sink(handle, **overrides):
    from pietto._project import project_job_delivery as d

    arguments = {**expected(handle), "purpose": "s15-sink", "seconds": 600}
    arguments.update(overrides)
    return d.accept_sink(handle, **arguments)


def accept_window(workspace, job, generation, built, checkpoint, **overrides):
    from pietto._project import project_job_delivery as d

    arguments = {
        "checkpoint": checkpoint,
        "purpose": "s15-deliver",
        "route": "postgres_rows",
        "values": (1,),
        "seconds": 600,
        "batch_rows": 4096,
        **s13.trust(built),
    }
    arguments.update(overrides)
    return d.accept_window(workspace, job, generation, **arguments)


def latest(workspace, job, generation):
    from pietto._project import project_job_capture as c

    return c.checkpoint_snapshot(workspace, job, generation).checkpoint


def synthetic_row(position: int, salt: int = 0) -> str:
    """ARROW_FREE_PAYLOAD_STEP row of the small output (renamed Int, other Int?)."""
    from pietto._project.project_job_store import _json

    return _json(
        {
            "coordinates": None,
            "values": [["int", position * 10 + salt], ["NoneType", None]],
        }
    )


def arrow_free_payloads(batch, coordinates):
    return tuple(
        synthetic_row(p, SALT.get(p, 0)) for p in range(batch.start, batch.stop)
    )


def arrow_free(monkeypatch=None):
    from pietto._project import project_job_delivery as d

    s13.arrow_free(monkeypatch)
    if monkeypatch is None:
        d._payloads = arrow_free_payloads
    else:
        monkeypatch.setattr(d, "_payloads", arrow_free_payloads)


def registered(workspace, job, publisher, generation, built, handle):
    """Register a stream, open a session and adopt the latest window."""
    from pietto._project import project_job_delivery as d

    window = accept_window(
        workspace, job, generation, built, latest(workspace, job, generation)
    )
    sink_acceptance = accept_sink(handle)
    stream = d.register_stream(publisher, window, sink_acceptance, operation=op()).get(
        "stream"
    )
    session = d.open_stream(publisher, stream, sink_acceptance, operation=op())
    session.adopt(window, operation=op())
    return stream, session


def deliver(session, rows):
    """Issue, send and confirm until the adopted windows are drained."""
    from pietto._project import project_job_delivery as d

    extents = []
    while True:
        item = session.next(rows, operation=op())
        if isinstance(item, d.Waiting):
            return extents, item
        statuses = session.send(item)
        session.confirm(item, operation=op())
        extents.append((item.start, item.stop, tuple(sorted(statuses.values()))))


def effects(handle):
    """Raw sink rows (position, digest, commit, sequence) of an open sink."""
    connection = handle.use()
    return [
        tuple(row)
        for row in connection.execute(
            "SELECT position, digest, commit_identity, sequence FROM effect"
            " ORDER BY workspace, generation, position"
        )
    ]


CHILD_HEADER = r"""
import json, os, signal, sys, time
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[3])
config = json.loads(sys.argv[2])
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c, project_job_replay as r
from pietto._project import project_job_delivery as d, project_job_sink as k
import _pietto_phase68_slice15_probe as probe
probe.arrow_free()

def barrier(name):
    sys.stdout.write(name + "\n")
    sys.stdout.flush()

def hold():
    while True:
        time.sleep(60)

def emit(value):
    sys.stdout.write(json.dumps(value) + "\n")
    sys.stdout.flush()

def attach(*, window=True):
    workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
    publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
    handle = k.open_sink(config["sink"], expected_identity=config["sink_identity"])
    sink = d.accept_sink(handle, instance=handle.identity, namespace=config["namespace"],
        epoch=config["epoch"], retention=config["retention"], purpose="s15-sink",
        seconds=600)
    read = None
    if window:
        checkpoint = c.checkpoint_snapshot(workspace, config["job"],
            config["generation"]).checkpoint
        read = d.accept_window(workspace, config["job"], config["generation"],
            checkpoint=checkpoint, purpose="s15-deliver", route="postgres_rows",
            values=tuple(config["values"]), expected_pin=config["pin"],
            accepted_producer=config["producer"],
            accepted_compatibility=tuple(config["compatibility"]), seconds=600,
            batch_rows=4096)
    return workspace, publisher, handle, sink, read
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


def child_config(workspace, job, generation, built, handle, **extra):
    return {
        "workspace": workspace.root,
        "identity": workspace.identity,
        "job": job,
        "generation": generation,
        "pin": built.pin,
        "producer": built.producer,
        "compatibility": list(built.compatibility),
        "values": [1],
        "sink": handle.root,
        "sink_identity": handle.identity,
        "namespace": handle.namespace,
        "epoch": handle.epoch,
        "retention": handle.retention,
        **extra,
    }


# ---------------------------------------------------------------------------
# Execution-profile families (Arrow present). Nothing runs at import.

# name -> (precision, simulated native batches as S12 SEVEN row indexes or "LATE")
SUITE_CASES = {
    "seven39": (39, [[0, 1], [2, 3], [4]]),
    "seven65": (65, [[0, 1], [2]]),
    "seven7": (39, [[0, 1], [2, 3], [4, 0], [1]]),
    "empty": (39, []),
    "late": (39, [[0, 1], "LATE"]),
}
BATCHES = (1, 2, 3, 4096)

WORKER_HEADER = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, os, hashlib
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["runtime_cwd"])
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
sys.path.append(config["tests"])
from pietto._project import project_job_capture as c, project_job_store as s
from pietto._project import project_job_workspace as w, project_job_delivery as d
from pietto._project import project_job_sink as k, project_job_replay as r
from pietto._project.project_job_store_verification import verify_store
def op():
    return s.new_operation()
def sink_rows(handle):
    return [list(row) for row in handle.use().execute(
        "SELECT position, digest, commit_identity, sequence FROM effect ORDER BY position")]
def accept_sink(handle, purpose):
    return d.accept_sink(handle, instance=handle.identity, namespace=handle.namespace,
        epoch=handle.epoch, retention=handle.retention, purpose=purpose, seconds=3600)
def write(value):
    found = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
            path = Path(filename).resolve()
            found[name] = {"path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    value.update(origins=found, prefix=sys.prefix)
    raw = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
    if len(raw) > 64 * 1024 * 1024:
        raise ValueError("bounded raw observation exceeded")
    Path(config["raw"]).write_bytes(raw)
"""

RELAY = r"""
import _pietto_phase68_slice12_probe as s12
base = Path(config["directory"])
templates = {p: s12.seven_template(base / ("build-" + str(p)), precision=p)
    for p in (39, 65)}
cases = {}
for name, (precision, spec) in config["cases"].items():
    source = s12.SEVEN65_ROWS if precision == 65 else s12.SEVEN_ROWS
    batches = [[s12.LATE_INVALID] if b == "LATE" else [source[i] for i in b]
        for b in spec]
    template, built = templates[precision]
    workspace, job, publisher, binding, record, generation = s12.store(
        base / (name + "-workspace"), template, format=w.FORMAT_V5)
    attempt, owner = s12.attempt_owner(publisher, generation, binding,
        s12.Plan(batches, s12.SEVEN_CODES), None)
    capture = c.begin_capture(publisher, attempt, owner, operation=op())
    handle = k.create_sink(str(base / (name + "-relay-sink")),
        namespace="s15.relay." + name, epoch=1, retention_seconds=86400)
    trust = dict(expected_pin=built.pin, accepted_producer=built.producer,
        accepted_compatibility=built.compatibility)
    window = dict(purpose="s15-suite", route="postgres_rows", values=(),
        seconds=3600, batch_rows=4096, **trust)
    sink = accept_sink(handle, "s15-suite")
    stream = d.register_stream(publisher, d.accept_window(workspace, job, generation,
        checkpoint=None, **window), sink, operation=op()).get("stream")
    session = d.open_stream(publisher, stream, sink, operation=op())
    steps, first, failure = [], None, None
    try:
        while True:
            step = d.relay(session, capture, rows=2, **window)
            count = len(sink_rows(handle))
            steps.append([step, owner._source, capture.terminal, count, session.position])
            if first is None and count:
                first = {"source": owner._source, "terminal": capture.terminal,
                    "closed": owner._closed, "observed": capture.observed,
                    "sink_rows": sink_rows(handle)}
            if step in ("SOURCE_TERMINAL", "BLOCKED"):
                break
    except Exception as error:
        failure = type(error).__name__ + ":" + str(error)
    ended = capture.end(operation=op())
    s.record_attempt(publisher, attempt, owner, operation=op())
    state = d.stream_state(workspace, stream)
    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    cases[name] = {"workspace": str(workspace.root), "identity": workspace.identity,
        "job": job, "generation": generation, "record": record, "stream": stream,
        "sink": handle.root, "sink_identity": handle.identity,
        "namespace": handle.namespace, "retention": handle.retention,
        "pin": built.pin, "producer": built.producer,
        "compatibility": list(built.compatibility), "precision": precision,
        "steps": steps, "first": first, "failure": failure, "end": dict(ended.result),
        "position": state.position, "unresolved": [list(x) for x in state.unresolved],
        "windows": [list(x) for x in state.windows], "checkpoint": snapshot.checkpoint,
        "frontier": snapshot.frontier, "observed_end": snapshot.observed_end,
        "source": snapshot.session_source, "sink_rows": sink_rows(handle),
        "verify": verify_store(workspace)}
    session.close()
    handle.close()
    publisher.close()
    workspace.close()
write({"cases": cases})
"""

DELIVER = r"""
base = Path(config["directory"])
results = {}
def schema(item):
    return None if item is None else [[f.name, str(f.type), f.nullable] for f in item]
for name, case in config["cases"].items():
    workspace = w.open_workspace(case["workspace"], expected_identity=case["identity"])
    publisher = s.claim_publisher(workspace, case["job"], operation=op())
    trust = dict(expected_pin=case["pin"], accepted_producer=case["producer"],
        accepted_compatibility=tuple(case["compatibility"]))
    latest = c.checkpoint_snapshot(workspace, case["job"], case["generation"])
    def window(purpose, checkpoint=latest.checkpoint):
        return d.accept_window(workspace, case["job"], case["generation"],
            checkpoint=checkpoint, purpose=purpose, route="postgres_rows", values=(),
            seconds=3600, batch_rows=4096, **trust)
    out = {"batches": {}}
    for rows in config["batches"]:
        handle = k.create_sink(str(base / (name + "-batch" + str(rows) + "-sink")),
            namespace="s15.batch" + str(rows) + "." + name, epoch=1,
            retention_seconds=86400)
        sink, read = accept_sink(handle, "s15-batches"), window("s15-batches")
        stream = d.register_stream(publisher, read, sink, operation=op()).get("stream")
        session = d.open_stream(publisher, stream, sink, operation=op())
        session.adopt(read, operation=op())
        issued = []
        while True:
            item = session.next(rows, operation=op())
            if isinstance(item, d.Waiting):
                waiting = {"terminal": item.terminal, "position": item.position,
                    "observed_end": item.observed_end,
                    "holes": [list(h) for h in item.holes],
                    "complete": item.complete_coverage, "schema": schema(item.schema)}
                break
            statuses = session.send(item)
            session.confirm(item, operation=op())
            issued.append([item.start, item.stop, [statuses[p] for p in
                range(item.start, item.stop)]])
        out["batches"][str(rows)] = {"sink": handle.root,
            "sink_identity": handle.identity, "stream": stream, "issued": issued,
            "waiting": waiting, "sink_rows": sink_rows(handle)}
        session.close()
        handle.close()
    # The fixed S13 consumer, bridged into its own sink; each Delivery is
    # acknowledged only after all of its occurrences are confirmed.
    scope = ("complete_capture" if case["source"] == "EOF"
        and case["observed_end"] == latest.frontier else "committed_prefix")
    acceptance = r.accept_saved_read(workspace, case["job"], case["generation"],
        checkpoint=latest.checkpoint, consumer=r.new_consumer(), scope=scope,
        extent=latest.frontier, purpose="s15-bridge", route="postgres_rows", values=(),
        seconds=3600, batch_rows=4096, **trust)
    r.register_consumer(publisher, acceptance, operation=op())
    handle = k.create_sink(str(base / (name + "-bridge-sink")),
        namespace="s15.bridge." + name, epoch=1, retention_seconds=86400)
    sink = accept_sink(handle, "s15-bridge")
    stream = d.register_stream(publisher, window("s15-bridge"), sink,
        operation=op()).get("stream")
    session = d.open_stream(publisher, stream, sink, operation=op())
    replay = r.open_replay(publisher, acceptance, operation=op())
    steps = []
    while True:
        item = replay.next(2, operation=op())
        if isinstance(item, r.SavedScopeEnd):
            end = [item.terminal, item.acknowledged, item.extent]
            break
        issued = session.bridge(item, operation=op())
        statuses = session.send(issued)
        session.confirm(issued, operation=op())
        session.acknowledge(issued, operation=op())
        steps.append([issued.start, issued.stop, sorted(statuses.values())])
        item.batch.close()
    out["bridge"] = {"sink": handle.root, "sink_identity": handle.identity,
        "stream": stream, "steps": steps, "end": end, "sink_rows": sink_rows(handle),
        "consumer": r.consumer_state(workspace, acceptance.consumer).position}
    session.close()
    replay.close()
    handle.close()
    # The relay destination keeps its one registration; a new session finds
    # every committed occurrence already confirmed there.
    relay = k.open_sink(case["sink"], expected_identity=case["sink_identity"])
    relay_sink = accept_sink(relay, "s15-relay-again")
    try:
        d.register_stream(publisher, window("s15-again"), relay_sink, operation=op())
        out["refusal"] = "ACCEPTED"
    except Exception as error:
        out["refusal"] = str(error)
    again = d.open_stream(publisher, case["stream"], relay_sink,
        window=window("s15-again"), operation=op())
    redelivered = again.next(4096, operation=op())
    out["redelivered"] = redelivered.position if isinstance(redelivered, d.Waiting) else -1
    again.close()
    relay.close()
    out["verify"] = verify_store(workspace)
    publisher.close()
    workspace.close()
    results[name] = out
write({"cases": results})
"""


def _write_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, ensure_ascii=False)


def backup_store(root, identity, target):
    """Supported SQLite backup of a closed workspace (never a lone main-file copy)."""
    import sqlite3

    from pietto._project import project_job_workspace as w

    opened = w.open_workspace(str(root), expected_identity=identity)
    try:
        os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        with sqlite3.connect(target) as copy:
            opened.use().backup(copy)
        copy.close()
    finally:
        opened.close()


def backup_sink(root, identity, target):
    """A WAL-consistent backup of a closed sink through fresh owner access."""
    import sqlite3

    from pietto._project import project_job_sink as k

    opened = k.open_sink(str(root), expected_identity=identity)
    try:
        os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        with sqlite3.connect(target) as copy:
            opened.use().backup(copy)
        copy.close()
    finally:
        opened.close()


def _run_worker(directory, ledger, interpreter, program, config, name, origin, wheel):
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_phase68_slice14_probe import _origin_check
    from _pietto_target_conformance_resources import clean_environment

    raw = directory / (PREFIX + name + ".json")
    path = directory / (PREFIX + name + "-config.json")
    _write_private(path, {**config, "raw": str(raw)})
    with (directory / (PREFIX + name + ".log")).open("wb") as log:
        status = worker_process(
            [str(interpreter), "-I", "-B", "-c", WORKER_HEADER + program, str(path)],
            clean_environment(),
            ledger,
            log,
            origin=origin,
            group="s15-" + name,
            directory=directory,
            seconds=1800,
        )
    if status:
        raise ValueError("S15_WORKER:" + name)
    data = json.loads(raw.read_text())
    _origin_check(data, origin, wheel)
    return data


def old_runtime(directory, ledger, interpreter, old_wheel):
    """The published S14 workspace owner (archived wheel bytes) meets a v5
    workspace: it must refuse before SQLite and leave the directory unchanged."""
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_target_conformance_resources import clean_environment
    from pietto._project import project_job_workspace as w

    root = directory / (PREFIX + "v5-workspace")
    workspace = w.create_workspace(str(root), format=w.FORMAT_V5)
    identity = workspace.identity
    workspace.close()
    raw = directory / (PREFIX + "old-runtime-raw.json")
    private = directory / (PREFIX + "old-runtime-input.json")
    _write_private(
        private,
        {
            "wheel": str(old_wheel),
            "workspace": str(root),
            "workspace_identity": identity,
            "raw": str(raw),
        },
    )
    with (directory / (PREFIX + "old-runtime.log")).open("wb") as log:
        status = worker_process(
            [str(interpreter), "-I", "-B", "-c", s12.OLD_RUNTIME, str(private)],
            clean_environment(),
            ledger,
            log,
            origin="archived-s14-wheel",
            group="s15-old-runtime",
            directory=directory,
            seconds=120,
        )
    private.unlink(missing_ok=True)
    data = json.loads(raw.read_text())
    if status or data != {
        "outcome": "WORKSPACE_FORMAT",
        "unchanged": True,
        "s11_format": "pietto.job-workspace.v1",
    }:
        raise ValueError("S15_OLD_RUNTIME_ACCEPTED_V5")
    return data


def suite(directory, ledger, interpreter, *, origin, wheel=None, old_wheel=None):
    """Arrow-profile delivery without a source database: simulated native IO
    (real S10 checks, Arrow, IPC, chunks and sinks), provisional relay before
    the source ends, fresh-process batches 1/2/3/whole, the S13 bridge, the
    destination refusal, independent checks and real-record damages."""
    import _pietto_phase68_slice15_check as check

    directory.mkdir(mode=0o700)
    common = {
        "runtime_cwd": str(directory),
        "library_source": str(ROOT / "src"),
        "tests": str(ROOT / "tests"),
        "origin": origin,
        "directory": str(directory),
    }
    relay = _run_worker(
        directory,
        ledger,
        interpreter,
        RELAY,
        {**common, "cases": SUITE_CASES},
        "relay",
        origin,
        wheel,
    )
    deliver = _run_worker(
        directory,
        ledger,
        interpreter,
        DELIVER,
        {**common, "cases": relay["cases"], "batches": list(BATCHES)},
        "deliver",
        origin,
        wheel,
    )
    backups: dict = {}
    for name, case in relay["cases"].items():
        stored = directory / (PREFIX + name + "-store-backup.sqlite")
        backup_store(case["workspace"], case["identity"], stored)
        sinks = {"relay": (case["sink"], case["sink_identity"])}
        out = deliver["cases"][name]
        for rows, item in out["batches"].items():
            sinks["batch" + rows] = (item["sink"], item["sink_identity"])
        sinks["bridge"] = (out["bridge"]["sink"], out["bridge"]["sink_identity"])
        copies = {}
        for label, (root, identity) in sinks.items():
            target = directory / (PREFIX + name + "-" + label + "-sink-backup.sqlite")
            backup_sink(root, identity, target)
            copies[label] = target
        backups[name] = {"store": stored, "sinks": copies}
    report: dict = {"status": "CHECKING", "origin": origin}
    report["cases"] = check.check_suite(SUITE_CASES, relay, deliver, backups)
    scratch = directory / (PREFIX + "damages")
    scratch.mkdir(mode=0o700)
    report["damages"] = check.damages(
        "seven39",
        SUITE_CASES["seven39"],
        relay["cases"]["seven39"],
        deliver["cases"]["seven39"],
        backups["seven39"],
        scratch,
    )
    if old_wheel is not None:
        report["old_runtime"] = old_runtime(directory, ledger, interpreter, old_wheel)
    report["status"] = "PASS"
    _write_private(directory / (PREFIX + "suite-report.json"), report)
    return report


# ---------------------------------------------------------------------------
# Native joined histories (pinned native capture/R2 profile + Arrow-only
# delivery profile). Nothing runs at import.

NATIVE = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, os, time, hashlib, shutil
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["runtime_cwd"])
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_schema import scalar_read
from pietto._project.project_execution_template import (prepare_compiled_template,
    prepare_live_template, bind_values)
from pietto._project import project_execution as ex
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c, project_job_extraction as x
from pietto._project import project_job_delivery as d, project_job_sink as k
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_execution_postgres import PostgresExecution
from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
from pietto._project.project_execution_mysql import MySQLExecution
OWNERS = {"postgres_rows": PostgresExecution, "postgres_adbc": PostgresADBCExecution,
    "mysql_rows": MySQLExecution}
route, role = config["route"], config["role"]
facts = {"role": role, "route": route, "pid": os.getpid()}
def write_facts():
    origins = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
            path = Path(filename).resolve()
            origins[name] = {"path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    facts.update(origins=origins, prefix=sys.prefix)
    Path(config["facts"]).write_text(json.dumps(facts, default=str))
def barrier(name):
    write_facts()
    sys.stdout.write(name + "\n")
    sys.stdout.flush()
def hold():
    while True:
        time.sleep(60)
def op():
    return s.new_operation()
def owner_for(binding):
    if route == "mysql_rows":
        a = ex.MySQLAccess("127.0.0.1", config["port"], "phase66", "pietto_query",
            config["password"], config["ca_path"], "pietto_query@%",
            verify_identity=False, loopback_tls_exception=True)
        premise = {"mysql_deployment": ex.MySQLDeploymentPremise(a,
            binding.artifact.request.sources, ("phase66",))}
    else:
        a = ex.PostgresAccess("127.0.0.1", config["port"], "phase66", "pietto_query",
            config["password"], "disable")
        premise = {"postgres_deployment": ex.PostgresDeploymentPremise(a,
            binding.artifact.request.sources, ("public", "pg_catalog"), route)}
    request = ex.prepare_compiled_execution(binding, a, route=route,
        limits=ex.ExecutionLimits(batch_rows=config["page_size"],
        seconds=config["request_seconds"]), **premise)
    return OWNERS[route](request)
def members(snapshot):
    return [[m.start, m.stop, m.attempt, m.chunk] for m in snapshot.members]
def sink_rows(handle):
    return [list(r) for r in handle.use().execute(
        "SELECT position, digest, commit_identity, sequence FROM effect ORDER BY position")]
trust = dict(expected_pin=config["pin"], accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]))
values = tuple(scalar_read(v).value for v in config["values"])
window = dict(purpose="s15-native", route=route, values=values, seconds=3600,
    batch_rows=4096, **trust)
if role == "relay":
    if config["entry"] == "live":
        sys.path.insert(0, config["build_helpers"])
        from _pietto_phase68_slice10_probe import build_native_reference
        reference = build_native_reference(Path(config["live_project"]),
            config["target"], config["cell"], config["providers"])
        artifact, preparation, query, output, bound = reference
        template = prepare_live_template(artifact, guarded=preparation, refinement=query)
        del artifact, preparation, query, output, bound, reference, build_native_reference
        shutil.rmtree(config["live_project"])
        sys.path.remove(config["build_helpers"])
        for name in tuple(sys.modules):
            if name.startswith(("_pietto_", "test_phase", "s04_", "s03_")):
                del sys.modules[name]
    else:
        template = prepare_compiled_template(load_compiled(
            Path(config["bundle"]).read_bytes(), **trust))
    workspace = w.create_workspace(config["workspace"], format=w.FORMAT_V5)
    binding = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    job = s.register_job(workspace, template, operation=op()).get("job")
    publisher = s.claim_publisher(workspace, job, operation=op())
    record = s.register_binding(publisher, binding, operation=op()).get("binding")
    generation = s.register_generation(publisher, record, binding, route=route,
        isolation="stable", operation=op()).get("generation")
    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    owner = owner_for(binding)
    owner.open()
    capture = x.begin_extraction(publisher, attempt, owner, operation=op())
    handle = k.create_sink(config["sink"], namespace=config["namespace"], epoch=1,
        retention_seconds=86400)
    sink = d.accept_sink(handle, instance=handle.identity, namespace=handle.namespace,
        epoch=1, retention=handle.retention, purpose="s15-native", seconds=3600)
    stream = d.register_stream(publisher, d.accept_window(workspace, job, generation,
        checkpoint=None, **window), sink, operation=op()).get("stream")
    session = d.open_stream(publisher, stream, sink, operation=op())
    steps, first, delivered = [], None, 0
    while delivered < config["deliver_steps"]:
        step = d.relay(session, capture, rows=config["rows"], **window)
        count = len(sink_rows(handle))
        steps.append([step, capture.terminal, count, session.position, capture.observed,
            owner._closed])
        if first is None and count:
            first = {"terminal": capture.terminal, "closed": owner._closed,
                "observed": capture.observed, "position": session.position,
                "rows": sink_rows(handle)}
        if step == "DELIVERED":
            delivered += 1
        if step in ("SOURCE_TERMINAL", "BLOCKED"):
            break
    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    facts.update(workspace=workspace.root, identity=workspace.identity, job=job,
        generation=generation, record=record, attempt=attempt.identity,
        session=owner.session_id, stream=stream, sink=handle.root,
        sink_identity=handle.identity, namespace=handle.namespace,
        retention=handle.retention, steps=steps, first=first,
        members=members(snapshot), checkpoint=snapshot.checkpoint,
        frontier=snapshot.frontier, position=session.position,
        sink_rows=sink_rows(handle))
    barrier("cut")
    hold()
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
job, generation = config["job"], config["generation"]
publisher = s.claim_publisher(workspace, job, operation=op())
for item in s.job_record(workspace, job).attempts:
    if item.terminal is None:
        s.interrupt_attempt(publisher, item.identity, operation=op())
latest = c.checkpoint_snapshot(workspace, job, generation)
facts.update(predecessor=latest.checkpoint, before=members(latest))
acceptance = x.accept_recovery(workspace, job, generation, checkpoint=latest.checkpoint,
    purpose="s15-native-r2", values=values, seconds=3600, **trust)
attempt = s.open_attempt(publisher, generation, acceptance.binding, operation=op())
owner = owner_for(acceptance.binding)
owner.open()
facts.update(attempt=attempt.identity, session=owner.session_id)
session = x.begin_continuation(publisher, acceptance, attempt, owner, operation=op())
try:
    while True:
        if session.ready and not session.reconciled:
            session.reconcile(operation=op())
            for item in list(session.staged):
                session.publish(item, operation=op())
        items = session.stage()
        if items is None:
            break
        if session.reconciled:
            for item in items:
                session.publish(item, operation=op())
    if session.ready and not session.reconciled:
        session.reconcile(operation=op())
        for item in list(session.staged):
            session.publish(item, operation=op())
    owner.close()
    ended = session.end(operation=op())
finally:
    session.close()
    owner.close()
s.record_attempt(publisher, attempt, owner, operation=op())
after = c.checkpoint_snapshot(workspace, job, generation)
state = x.extraction_state(workspace, job, generation)
facts.update(status="COMPLETE", end=dict(ended.result), members=members(after),
    checkpoint=after.checkpoint, frontier=after.frontier, holes=after.holes,
    matched=session.matched, observed=session.observed, known=state.known,
    coverage=state.complete_coverage, verify=verify_store(workspace))
publisher.close()
workspace.close()
write_facts()
"""

ADOPT = r"""
results = {}
for item in config["stores"]:
    workspace = w.open_workspace(item["workspace"], expected_identity=item["identity"])
    publisher = s.claim_publisher(workspace, item["job"], operation=op())
    handle = k.open_sink(item["sink"], expected_identity=item["sink_identity"])
    try:
        from pietto._project.project_compiled_schema import scalar_read
        values = tuple(scalar_read(v).value for v in item["values"])
        latest = c.checkpoint_snapshot(workspace, item["job"], item["generation"])
        sink = accept_sink(handle, "s15-native-adopt")
        stream = d.find_stream(workspace, item["job"], item["generation"],
            sink=handle.identity, namespace=handle.namespace, epoch=handle.epoch)
        session = d.open_stream(publisher, stream, sink, operation=op())
        start = session.position
        read = d.accept_window(workspace, item["job"], item["generation"],
            checkpoint=latest.checkpoint, purpose="s15-native-adopt",
            route=item["route"], values=values, seconds=3600, batch_rows=4096,
            expected_pin=item["pin"], accepted_producer=item["producer"],
            accepted_compatibility=tuple(item["compatibility"]))
        adopted = session.adopt(read, operation=op())
        issued = []
        while True:
            got = session.next(config["rows"], operation=op())
            if isinstance(got, d.Waiting):
                waiting = [got.terminal, got.position, got.observed_end,
                    got.complete_coverage]
                break
            statuses = session.send(got)
            session.confirm(got, operation=op())
            issued.append([got.start, got.stop, [statuses[p] for p in
                range(got.start, got.stop)]])
        session.close()
        state = d.stream_state(workspace, stream)
        results[item["key"]] = {"stream": stream, "start": start,
            "adopted": dict(adopted.result), "issued": issued, "waiting": waiting,
            "windows": [list(x) for x in state.windows], "position": state.position,
            "sink_rows": sink_rows(handle), "verify": verify_store(workspace)}
    finally:
        handle.close()
        publisher.close()
        workspace.close()
write({"results": results})
"""

BRIDGE = r"""
from pietto._project import project_job_capture as c, project_job_replay as r
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_delivery as d, project_job_sink as k
from pietto._project.project_compiled_schema import scalar_read
from pietto._project.project_job_store_verification import verify_store
def op():
    return s.new_operation()
def sink_rows(handle):
    return [list(r) for r in handle.use().execute(
        "SELECT position, digest, commit_identity, sequence FROM effect ORDER BY position")]
def accept_sink(handle):
    return d.accept_sink(handle, instance=handle.identity, namespace=handle.namespace,
        epoch=handle.epoch, retention=handle.retention, purpose="s15-r1-bridge",
        seconds=3600)
results = []
for item in config["stores"]:
    workspace = w.open_workspace(item["workspace"], expected_identity=item["identity"])
    publisher = s.claim_publisher(workspace, item["job"], operation=op())
    out = {"key": item["key"]}
    try:
        values = tuple(scalar_read(v).value for v in item["values"])
        trust = dict(expected_pin=item["pin"], accepted_producer=item["producer"],
            accepted_compatibility=tuple(item["compatibility"]))
        snapshot = c.checkpoint_snapshot(workspace, item["job"], item["generation"])
        def bridged(handle, stream, rows):
            acceptance = r.accept_saved_read(workspace, item["job"], item["generation"],
                checkpoint=snapshot.checkpoint, consumer=r.new_consumer(),
                scope="complete_capture", extent=snapshot.frontier,
                purpose="s15-r1-bridge", route=item["route"], values=values,
                seconds=3600, batch_rows=4096, **trust)
            r.register_consumer(publisher, acceptance, operation=op())
            session = d.open_stream(publisher, stream, accept_sink(handle), operation=op())
            replay = r.open_replay(publisher, acceptance, operation=op())
            steps = []
            while True:
                got = replay.next(rows, operation=op())
                if isinstance(got, r.SavedScopeEnd):
                    end = [got.terminal, got.acknowledged, got.extent]
                    break
                issued = session.bridge(got, operation=op())
                statuses = session.send(issued)
                if statuses:
                    session.confirm(issued, operation=op())
                session.acknowledge(issued, operation=op())
                steps.append([issued.start, issued.stop, sorted(statuses.values()),
                    [list(o) for o in got.occurrences]])
                got.batch.close()
            replay.close()
            session.close()
            return {"steps": steps, "end": end, "rows": sink_rows(handle)}
        # A second destination: every saved occurrence becomes one new effect.
        fresh = k.create_sink(item["bridge_sink"], namespace=item["bridge_namespace"],
            epoch=1, retention_seconds=86400)
        read = d.accept_window(workspace, item["job"], item["generation"],
            checkpoint=snapshot.checkpoint, purpose="s15-r1-bridge", route=item["route"],
            values=values, seconds=3600, batch_rows=4096, **trust)
        stream = d.register_stream(publisher, read, accept_sink(fresh),
            operation=op()).get("stream")
        out["fresh"] = {"sink": fresh.root, "sink_identity": fresh.identity,
            "stream": stream, **bridged(fresh, stream, 1)}
        fresh.close()
        # The first destination already confirmed everything: nothing is sent.
        first = k.open_sink(item["sink"], expected_identity=item["sink_identity"])
        out["again"] = bridged(first, item["stream"], 5)
        first.close()
        out["verify"] = verify_store(workspace)
    except Exception as error:
        out["error"] = type(error).__name__ + ":" + str(error)[:300]
    finally:
        publisher.close()
        workspace.close()
    results.append(out)
loaded = sorted(n for n in sys.modules if n.split(".")[0] in DRIVERS)
origins = {}
for name, module in tuple(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
        path = Path(filename).resolve()
        origins[name] = {"path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
retain_raw({"results": results, "connections": connections,
    "installed_drivers": installed_drivers, "loaded_drivers": loaded,
    "origins": origins, "prefix": sys.prefix})
"""


def native(
    directory,
    ledger,
    capture_interpreter,
    delivery_interpreter,
    *,
    target,
    cells,
    wheel=None,
):
    """One joined native history per route and (origin, entry) cell over R2_seven
    39_values: a refined R2 capture relayed into sink A before the source ends;
    the extractor SIGKILLed; S14 recovery in a fresh native process; the next
    window adopted into sink A by a fresh Arrow-only process without repeating
    effects; the source database deleted; a driver-free Arrow-only R1 bridge into
    a new sink B and again into sink A (already confirmed, nothing sent)."""
    import time

    import _pietto_phase68_slice10_probe as s10
    import _pietto_phase68_slice13_probe as r13
    import _pietto_phase68_slice14_probe as s14
    from _pietto_phase68_slice6_probe import session_gone, setup as setup_general
    from _pietto_phase68_slice6_probe import manager
    from _pietto_phase68_slice8_probe import event, worker_process
    from _pietto_phase68_slice11_probe import kill, until
    from _pietto_target_conformance_resources import Resources, clean_environment
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_schema import Scalar, scalar_wire

    directory.mkdir(mode=0o700)
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
        }
    )
    ledger.write_text(json.dumps(state, indent=2) + "\n")
    event(
        ledger,
        {"kind": "s15_native_start", "directory": str(directory), "target": target},
    )
    report: dict = {"status": "STARTED", "target": target, "histories": []}
    report_path = directory / (PREFIX + "native.json")
    started = time.monotonic()
    timings: dict = {}
    routes = ["mysql_rows"] if target == "mysql" else ["postgres_rows", "postgres_adbc"]
    cell = {
        "group": "refined",
        "case": "R2_seven",
        "variant": "39_values",
        "excluded": False,
    }
    stores = []
    try:
        mark = time.monotonic()
        resource.acquire()
        if target == "mysql":
            manager(resource, "USE phase66")
        providers = setup_general(resource)
        if target == "mysql":
            for table in ("threads", "events_transactions_current"):
                manager(
                    resource,
                    "GRANT SELECT ON performance_schema."
                    + table
                    + " TO 'pietto_query'@'%'",
                )
        reference = s10.build_native_reference(
            directory / (PREFIX + "reference-source"), target, cell, providers
        )
        if reference is None:
            raise ValueError("S15_NATIVE_REFERENCE")
        artifact, preparation, query, output, binding = reference
        built = build_compiled(artifact, guarded=preparation, refinement=query)
        bundle = directory / (PREFIX + "bundle.json")
        bundle.write_bytes(built.payload)
        bundle.chmod(0o600)
        timings["preparation"] = time.monotonic() - mark
        common = {
            "target": target,
            "cell": cell,
            "providers": providers,
            "build_helpers": str(ROOT / "tests"),
            "library_source": str(ROOT / "src"),
            "bundle": str(bundle),
            "pin": built.pin,
            "producer": built.producer,
            "compatibility": list(built.compatibility),
            "values": [
                scalar_wire(Scalar(v.tag.value, v.value)) for v in artifact.fixed_values
            ],
            "port": resource.port,
            "password": resource._passwords[1],
            "ca_path": str(resource.ca_path) if target == "mysql" else None,
            "request_seconds": 360,
        }

        def spawn(interpreter, label, program, config, *, cut=False):
            path = directory / (label + "-config.json")
            runtime = directory / (label + "-runtime")
            runtime.mkdir(mode=0o700)
            facts = directory / (label + "-facts.json")
            _write_private(
                path,
                {**common, **config, "runtime_cwd": str(runtime), "facts": str(facts)},
            )
            with (directory / (label + "-worker.log")).open("w") as log:
                child = s14._spawn(interpreter, program, path, ledger, log, label)
                try:
                    if cut:
                        until(child, "cut", 600)
                        code, _ = kill(child)
                    else:
                        code = child.wait(timeout=1800)
                finally:
                    if child.poll() is None:
                        kill(child)
                    s14._reaped(ledger, child, child.returncode)
            path.unlink()
            if code != (-9 if cut else 0):
                raise ValueError("S15_NATIVE_WORKER:" + label + ":" + str(code))
            return json.loads(facts.read_text())

        for route in routes:
            for origin, entry in cells:
                key = route + "-" + origin + "-" + entry
                label = PREFIX + key
                record: dict = {
                    "key": key,
                    "route": route,
                    "origin": origin,
                    "entry": entry,
                }
                report["histories"].append(record)
                mark = time.monotonic()
                relay = spawn(
                    capture_interpreter,
                    label + "-relay",
                    NATIVE,
                    {
                        "route": route,
                        "role": "relay",
                        "origin": origin,
                        "entry": entry,
                        "page_size": 2,
                        "rows": 2,
                        "deliver_steps": 2,
                        "workspace": str(directory / (label + "-workspace")),
                        "sink": str(directory / (label + "-sink-a")),
                        "namespace": "s15.native.a." + key,
                        "live_project": str(directory / (label + "-source")),
                    },
                    cut=True,
                )
                s14._origin_check(relay, origin, wheel)
                relay["session_gone"] = session_gone(resource, relay["session"])
                record["relay"] = relay
                timings[key + ":relay"] = time.monotonic() - mark
                mark = time.monotonic()
                store = {
                    k: relay[k] for k in ("workspace", "identity", "job", "generation")
                }
                recovered = spawn(
                    capture_interpreter,
                    label + "-recover",
                    NATIVE,
                    {
                        **store,
                        "route": route,
                        "role": "recover",
                        "origin": origin,
                        "entry": "bundle",
                        "page_size": 3,
                    },
                )
                s14._origin_check(recovered, origin, wheel)
                recovered["session_gone"] = session_gone(resource, recovered["session"])
                record["recover"] = recovered
                timings[key + ":r2"] = time.monotonic() - mark
                stores.append(
                    {
                        **store,
                        "key": key,
                        "route": route,
                        "origin": origin,
                        "values": common["values"],
                        "pin": built.pin,
                        "producer": built.producer,
                        "compatibility": list(built.compatibility),
                        "sink": relay["sink"],
                        "sink_identity": relay["sink_identity"],
                        "stream": relay["stream"],
                        "bridge_sink": str(directory / (label + "-sink-b")),
                        "bridge_namespace": "s15.native.b." + key,
                    }
                )
                report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        # A fresh Arrow-only process adopts each recovered checkpoint into sink A.
        mark = time.monotonic()
        for origin in sorted({o for o, _e in cells}):
            adopt = _run_worker(
                directory,
                ledger,
                delivery_interpreter,
                ADOPT,
                {
                    "runtime_cwd": str(directory),
                    "library_source": str(ROOT / "src"),
                    "tests": str(ROOT / "tests"),
                    "origin": origin,
                    "directory": str(directory),
                    "rows": 3,
                    "stores": [s for s in stores if s["origin"] == origin],
                },
                "adopt-" + origin,
                origin,
                wheel,
            )
            for record in report["histories"]:
                if record["key"] in adopt["results"]:
                    record["adopt"] = adopt["results"][record["key"]]
        timings["adopt"] = time.monotonic() - mark
        mark = time.monotonic()
        report["source_cleanup"] = resource.cleanup()
        timings["source_cleanup"] = time.monotonic() - mark
        # The source database is gone: driver-free Arrow-only R1 into sinks.
        mark = time.monotonic()
        for origin in sorted({o for o, _e in cells}):
            raw = directory / (PREFIX + "bridge-" + origin + ".json")
            path = directory / (PREFIX + "bridge-" + origin + "-config.json")
            _write_private(
                path,
                {
                    "runtime_cwd": str(directory),
                    "library_source": str(ROOT / "src"),
                    "origin": origin,
                    "raw": str(raw),
                    "stores": [s for s in stores if s["origin"] == origin],
                },
            )
            with (directory / (PREFIX + "bridge-" + origin + ".log")).open("wb") as log:
                status = worker_process(
                    [
                        str(delivery_interpreter),
                        "-I",
                        "-B",
                        "-c",
                        r13.REPLAY_HEADER + BRIDGE,
                        str(path),
                    ],
                    clean_environment(),
                    ledger,
                    log,
                    origin=origin,
                    group="s15-native-bridge",
                    directory=directory,
                    seconds=1800,
                )
            path.unlink()
            if status:
                raise ValueError("S15_NATIVE_BRIDGE")
            data = json.loads(raw.read_text())
            s14._origin_check(data, origin, wheel)
            if (
                data["connections"]
                or data["loaded_drivers"]
                or data["installed_drivers"]
            ):
                raise ValueError("S15_NATIVE_BRIDGE_SOURCE_ACCESS")
            for result in data["results"]:
                for record in report["histories"]:
                    if record["key"] == result["key"]:
                        record["bridge"] = result
        timings["bridge"] = time.monotonic() - mark
        mark = time.monotonic()
        native_check(directory, target, report["histories"])
        timings["audit"] = time.monotonic() - mark
        report["status"] = "PASS"
    except BaseException as error:
        report.update(
            status="FAILED",
            error_kind=type(error).__name__,
            error=resource.without_secrets(str(error)),
        )
        raise
    finally:
        if "source_cleanup" not in report:
            report["source_cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - started
        report["timings"] = timings
        report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        event(
            ledger,
            {
                "kind": "s15_native_terminal",
                "directory": str(directory),
                "status": report["status"],
                "cleanup": report["source_cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


def native_check(directory, target, histories):
    """Independent judgement of recorded native histories from closed stores,
    sinks and chunk bytes; missing static backups are taken once through fresh
    owner access. Database-free: the literal oracle needs no source."""
    import _pietto_phase68_slice15_check as check
    from _pietto_phase68_slice6_check import expected

    literal, ordered = expected(target, "R2_seven", "39_values", None)
    oracle = {"rows": literal, "ordered": ordered}
    for record in histories:
        relay, fresh = record["relay"], record["bridge"]["fresh"]
        store = {
            "workspace": relay["workspace"],
            "identity": relay["identity"],
            "generation": relay["generation"],
            "stream": relay["stream"],
        }
        stored = directory / (PREFIX + record["key"] + "-store-backup.sqlite")
        if not stored.exists():
            backup_store(relay["workspace"], relay["identity"], stored)
        sinks = {}
        for label, root, identity in (
            ("a", relay["sink"], relay["sink_identity"]),
            ("b", fresh["sink"], fresh["sink_identity"]),
        ):
            path = directory / (
                PREFIX + record["key"] + "-sink-" + label + "-backup.sqlite"
            )
            if not path.exists():
                backup_sink(root, identity, path)
            sinks[label] = path
        record["checked"] = check.check_native(record, store, stored, sinks, oracle)
    return histories
