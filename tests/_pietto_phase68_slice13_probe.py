"""S13 replay fixtures and explicit bounded families; import acquires nothing.

Ordinary tests have no Arrow. Their saved inputs use S12's labelled Arrow-free
storage step, and `arrow_free` swaps only the replay data step
(ARROW_FREE_REPLAY_STEP): acceptance, registration, sessions, issuance,
acknowledgement, fences and every SQLite transaction still run for real. Real
checked Arrow replay runs only in the Arrow-only replay profile.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import sys

import _pietto_phase68_slice12_probe as s12
from pietto._project.project_job_replay import Delivery, SavedScopeEnd

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice13-"
op = s12.op


def store(root, template, values=(1,), **options):
    """A v3 workspace with one job, publisher, binding and generation."""
    from pietto._project import project_job_workspace as w

    return s12.store(root, template, values, format=w.FORMAT_V3, **options)


def capture(workspace, publisher, generation, binding, sizes, *, order=None, eof=True):
    """ARROW_FREE_STORAGE_STEP chunks of `sizes` rows, published in `order`.

    `eof` records the source EOF a real owner would report; the attempt itself
    stays open, so its remote layers stay UNKNOWN.
    """
    session = s12.capture(workspace, publisher, generation, binding)
    staged = [s12.stage_frame(session, rows, terminal=None) for rows in sizes]
    if not sizes and eof:
        staged = [s12.stage_frame(session, 0, terminal="EOF")]
    results = [
        session.publish(staged[i], operation=op())
        for i in (range(len(staged)) if order is None else order)
    ]
    if eof:
        session.owner.close()
        session._terminal = "EOF"
        session.end(operation=op())
    return session, results


def trust(built):
    return {
        "expected_pin": built.pin,
        "accepted_producer": built.producer,
        "accepted_compatibility": built.compatibility,
    }


def accept(workspace, job, generation, built, **overrides):
    from pietto._project import project_job_capture as c
    from pietto._project import project_job_replay as r

    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    arguments = {
        "checkpoint": snapshot.checkpoint,
        "consumer": r.new_consumer(),
        "scope": "complete_capture",
        "extent": snapshot.frontier,
        "purpose": "s13-read",
        "route": "postgres_rows",
        "values": (1,),
        "seconds": 600,
        "batch_rows": 4096,
        **trust(built),
    }
    arguments.update(overrides)
    return r.accept_saved_read(workspace, job, generation, **arguments)


class Rows:
    """ARROW_FREE_REPLAY_STEP payload: the checked extent a real batch carries."""

    def __init__(self, start, stop):
        self.start, self.stop, self.closed = start, stop, False

    def close(self):
        self.closed = True


def arrow_free_step(replay, start, stop):
    from pietto._project import project_job_replay as r

    if start == stop:
        member = replay.snapshot.members[0]
        return None, None, 0, ("ARROW_FREE_SCHEMA_MEMBER", member.chunk)
    r.plan(replay.snapshot.members, start, stop)
    return Rows(start, stop), None, 0, None


def arrow_free(monkeypatch=None):
    from pietto._project import project_job_replay as r

    if monkeypatch is None:
        r._rebatch = arrow_free_step
    else:
        monkeypatch.setattr(r, "_rebatch", arrow_free_step)


def issue(replay, rows) -> Delivery:
    """The next item, which must be an issued delivery."""
    item = replay.next(rows, operation=op())
    assert isinstance(item, Delivery)
    return item


def end(replay, rows=1) -> SavedScopeEnd:
    """The next item, which must be the saved-scope end."""
    item = replay.next(rows, operation=op())
    assert isinstance(item, SavedScopeEnd)
    return item


def drain(replay, rows) -> tuple[list[tuple[int, int]], SavedScopeEnd]:
    """Issue and acknowledge until the saved scope ends; returns extents and end."""
    extents = []
    while True:
        item = replay.next(rows, operation=op())
        if isinstance(item, SavedScopeEnd):
            return extents, item
        extents.append((item.start, item.stop))
        replay.acknowledge(item, operation=op())


CHILD_HEADER = r"""
import json, os, signal, sys, time
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[3])
config = json.loads(sys.argv[2])
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c, project_job_replay as r
import _pietto_phase68_slice13_probe as probe
probe.arrow_free()

def barrier(name):
    sys.stdout.write(name + "\n")
    sys.stdout.flush()

def hold():
    while True:
        time.sleep(60)

def attach():
    workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
    publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
    acceptance = r.accept_saved_read(workspace, config["job"], config["generation"],
        checkpoint=config["checkpoint"], consumer=config["consumer"],
        scope=config["scope"], extent=config["extent"], purpose="s13-read",
        route="postgres_rows", values=tuple(config["values"]),
        expected_pin=config["pin"], accepted_producer=config["producer"],
        accepted_compatibility=tuple(config["compatibility"]), seconds=600,
        batch_rows=4096)
    return workspace, publisher, acceptance

def emit(value):
    sys.stdout.write(json.dumps(value) + "\n")
    sys.stdout.flush()
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


def child_config(workspace, job, generation, built, acceptance_facts):
    return {
        "workspace": workspace.root,
        "identity": workspace.identity,
        "job": job,
        "generation": generation,
        "pin": built.pin,
        "producer": built.producer,
        "compatibility": list(built.compatibility),
        "values": [1],
        **acceptance_facts,
    }


# ---------------------------------------------------------------------------
# Execution-profile families (Arrow present). Nothing runs at import.

# name -> (precision, batches as row indexes or "LATE", publish order, route)
CASES = {
    "seven39": (39, [[0, 1], [2, 3], [4]], [0, 2, 1]),
    "seven65": (65, [[0, 1], [2]], [0, 1]),
    "seven7": (39, [[0, 1], [2, 3], [4, 0], [1]], [0, 1, 2, 3]),
    "empty": (39, [], [0]),
    "late": (39, [[0, 1], "LATE"], None),
    "hole0": (39, [[0, 1], [2, 3]], [1, 0]),
}

SUITE_CAPTURE = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, os
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["runtime_cwd"])
sys.path.insert(0, config["library_source"])
sys.path.insert(0, config["tests"])
import _pietto_phase68_slice12_probe as s12
from pietto._project import project_job_capture as c, project_job_store as s
from pietto._project import project_job_workspace as w
base = Path(config["directory"])
templates = {p: s12.seven_template(base / ("build-" + str(p)), precision=p) for p in (39, 65)}
cases = {}
for name, (precision, spec, order) in config["cases"].items():
    source = s12.SEVEN65_ROWS if precision == 65 else s12.SEVEN_ROWS
    batches = [[s12.LATE_INVALID] if b == "LATE" else [source[i] for i in b] for b in spec]
    template, built = templates[precision]
    root = base / (name + "-workspace")
    workspace, job, publisher, binding, record, generation = s12.store(
        root, template, format=w.FORMAT_V3)
    attempt, owner = s12.attempt_owner(
        publisher, generation, binding, s12.Plan(batches, s12.SEVEN_CODES), None)
    session = c.begin_capture(publisher, attempt, owner, operation=s.new_operation())
    staged, checkpoints, failure = [], {}, None
    def publish(item):
        result = session.publish(item, operation=s.new_operation())
        checkpoints[str(result.get("ordinal"))] = [result.get("checkpoint"),
            result.get("frontier")]
    try:
        while True:
            item = session.stage()
            if item is None:
                break
            staged.append(item)
            if order is None:
                publish(item)
    except Exception as error:
        failure = type(error).__name__ + ":" + str(error)
    for index in order or ():
        publish(staged[index])
    ended = session.end(operation=s.new_operation())
    s.record_attempt(publisher, attempt, owner, operation=s.new_operation())
    cases[name] = {"workspace": str(root), "identity": workspace.identity, "job": job,
        "generation": generation, "record": record, "checkpoints": checkpoints,
        "staged": [[x.start, x.stop] for x in staged], "failure": failure,
        "end": dict(ended.result), "pin": built.pin, "producer": built.producer,
        "compatibility": list(built.compatibility), "values": [],
        "route": "postgres_rows", "precision": precision}
    publisher.close()
    workspace.close()
Path(config["raw"]).write_text(json.dumps({"cases": cases}, ensure_ascii=False))
"""

REPLAY_HEADER = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, importlib, importlib.util, hashlib, time, os, socket
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["runtime_cwd"])
def retain_raw(value):
    raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if len(raw) > 64 * 1024 * 1024:
        raise ValueError("bounded raw observation exceeded")
    Path(config["raw"]).write_bytes(raw)
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
import pyarrow as pa
from pietto._project import model, trusted_source
import pietto.ast_nodes as nodes
connections = []
def refused(*args, **kwargs):
    connections.append("socket_connect")
    raise OSError("R1 replay never opens a network connection")
socket.socket.connect = refused
socket.socket.connect_ex = refused
socket.create_connection = refused
DRIVERS = ("psycopg", "adbc_driver_manager", "adbc_driver_postgresql", "mysql")
installed_drivers = sorted(n for n in DRIVERS if importlib.util.find_spec(n) is not None)
"""

REPLAY = r"""
from pietto._project import project_job_capture as c, project_job_replay as r
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_chunks as k
from pietto._project.project_job_store_verification import verify_store
cases = config["cases"]
results = []

def opened(case):
    return w.open_workspace(case["workspace"], expected_identity=case["identity"])

def accepted(workspace, case, **overrides):
    ordinal = overrides.pop("ordinal", None)
    checkpoint = None if ordinal is None else case["checkpoints"][str(ordinal)][0]
    snapshot = c.checkpoint_snapshot(workspace, case["job"], case["generation"],
        checkpoint=checkpoint)
    if "value_wires" in case:
        from pietto._project.project_compiled_schema import scalar_read
        values = tuple(scalar_read(v).value for v in case["value_wires"])
    else:
        values = tuple(case["values"])
    arguments = dict(checkpoint=snapshot.checkpoint, consumer=r.new_consumer(),
        scope="complete_capture", extent=snapshot.frontier, purpose="s13-suite",
        route=case["route"], values=values,
        expected_pin=case["pin"], accepted_producer=case["producer"],
        accepted_compatibility=tuple(case["compatibility"]), seconds=3600,
        batch_rows=4096)
    arguments.update(overrides)
    return r.accept_saved_read(workspace, case["job"], case["generation"], **arguments)

def described(schema):
    return None if schema is None else [[f.name, str(f.type), f.nullable] for f in schema]

def recorded(item):
    if isinstance(item, r.Delivery):
        data = pa.record_batch(item.batch)
        out = {"start": item.start, "stop": item.stop, "delivery": item.identity,
            "session": item.session, "operation": item.operation,
            "occurrences": [list(o) for o in item.occurrences],
            "values": [[scalar(data.column(i)[j].as_py()) for i in range(data.num_columns)]
                for j in range(data.num_rows)],
            "schema": described(data.schema), "held": item.held_bytes,
            "coordinates": None if item.coordinates is None else
                [[k.coordinate_wire(v) for v in key] for key in item.coordinates]}
        item.batch.close()
        return out
    return {"terminal": item.terminal, "scope": item.scope, "extent": item.extent,
        "acknowledged": item.acknowledged, "verified": list(item.verified),
        "schema": described(item.schema), "observed_end": item.observed_end,
        "holes": [list(h) for h in item.holes], "layers": dict(item.layers)}

def drain(replay, rows, acknowledgements=None, items=None):
    items = [] if items is None else items
    while True:
        item = replay.next(rows, operation=s.new_operation())
        items.append(recorded(item))
        if not isinstance(item, r.Delivery) or acknowledgements == 0:
            return items
        replay.acknowledge(item, operation=s.new_operation())
        items[-1]["acknowledged"] = True
        if acknowledgements is not None:
            acknowledgements -= 1

def state(workspace, consumer):
    found = r.consumer_state(workspace, consumer)
    return {"position": found.position, "acknowledged": [list(a) for a in found.acknowledged],
        "sessions": [list(x) for x in found.sessions], "issued": [list(i) for i in found.issued],
        "extent": found.extent, "scope": found.scope, "checkpoint": found.checkpoint}

def error(call):
    try:
        call()
    except Exception as failure:
        return str(failure)
    return "ACCEPTED"

def run(history):
    case = cases[history["case"]]
    kind = history["kind"]
    workspace = opened(case)
    publisher = s.claim_publisher(workspace, case["job"], operation=s.new_operation())
    out = {"history": history["name"], "kind": kind, "case": history["case"]}
    try:
        options = dict(history.get("accept", {}))
        if kind == "refuse":
            out["refusals"] = {}
            for label, overrides, stage in history["attempts"]:
                def attempt(overrides=overrides, stage=stage):
                    a = accepted(workspace, case, **overrides)
                    if stage == "open":
                        good = accepted(workspace, case)
                        r.register_consumer(publisher, good, operation=s.new_operation())
                        changed = accepted(workspace, case, consumer=good.consumer,
                            **overrides)
                        r.open_replay(publisher, changed, operation=s.new_operation())
                out["refusals"][label] = error(attempt)
            return out
        if kind == "resume":
            options["consumer"] = history["consumer"]
            if "operation" in history:
                found = s.query_operation(workspace, history["operation"])
                out["query"] = None if found is None else [found.kind,
                    found.observation, dict(found.result)]
            out["before"] = state(workspace, history["consumer"])
        elif "consumer" in history:
            options["consumer"] = history["consumer"]
        a = accepted(workspace, case, **options)
        out["consumer"], out["checkpoint"], out["extent"] = a.consumer, a.checkpoint, a.extent
        if kind != "resume":
            r.register_consumer(publisher, a, operation=s.new_operation())
        replay = r.open_replay(publisher, a, operation=s.new_operation())
        out["start"] = replay.position
        if kind in ("drain", "resume"):
            out["items"] = drain(replay, history["rows"])
        elif kind == "corrupt":
            out["items"] = []
            try:
                drain(replay, history["rows"], items=out["items"])
            except Exception as failure:
                out["error"] = str(failure)
        elif kind == "two_sessions":
            out["items"] = drain(replay, history["rows"][0], history["acks"])
            replay.close()
            second = r.open_replay(publisher, a, operation=s.new_operation())
            out["second_start"] = second.position
            out["second"] = drain(second, history["rows"][1])
        elif kind == "late_authority":
            real = r._rebatch
            batches = []
            def trigger():
                if history["event"] == "cancel":
                    s.cancel_job(publisher, operation=s.new_operation())
                else:
                    r._monotonic = lambda: float("inf")
            if history["phase"] == "decode_offer":
                def decoded(replay, start, stop):
                    value = real(replay, start, stop)
                    batches.append(value[0])
                    trigger()
                    return value
                r._rebatch = decoded
                out["error"] = error(lambda: replay.next(2, operation=s.new_operation()))
                out["closed"] = batches[0]._closed
                r._rebatch = real
            else:
                item = replay.next(2, operation=s.new_operation())
                trigger()
                out["error"] = error(lambda: replay.acknowledge(item,
                    operation=s.new_operation()))
                out["handed"] = recorded(item)
        elif kind in ("hold_offered", "hold_ack_commit"):
            items = drain(replay, 2, history["acks"])
            out["items"] = items
            results.append(out)
            if kind == "hold_offered":
                retain_raw({"results": results, "connections": connections})
                sys.stdout.write("offered\n")
                sys.stdout.flush()
                while True:
                    time.sleep(60)
            real_commit = w.commit
            def stop_after(connection):
                real_commit(connection)
                retain_raw({"results": results, "connections": connections})
                sys.stdout.write("cut\n")
                sys.stdout.flush()
                while True:
                    time.sleep(60)
            w.commit = stop_after
            pending = replay._pending
            replay.acknowledge(pending, operation=history["operation"])
        if kind == "verify":
            output = c.stored_output(workspace, case["job"], case["generation"],
                expected_pin=case["pin"], accepted_producer=case["producer"],
                accepted_compatibility=tuple(case["compatibility"]))
            snapshot = c.checkpoint_snapshot(workspace, case["job"], case["generation"])
            with c.SnapshotReader(workspace, snapshot, output) as reader:
                out["verified"] = reader.verify()
        replay.close()
        out["after"] = state(workspace, a.consumer)
        # Coordinated row rewrites of a damaged copy must fail independent replay.
        out["verify_store"] = error(lambda: out.update(store=verify_store(workspace)))
        return out
    finally:
        r._monotonic = time.monotonic
        publisher.close()
        workspace.close()

for history in config["histories"]:
    results.append(run(history))
loaded = sorted(n for n in sys.modules if n.split(".")[0] in DRIVERS)
origins = {}
for name, module in tuple(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
        path = Path(filename).resolve()
        origins[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
retain_raw({"results": results, "forbidden_calls": forbidden_calls,
    "connections": connections, "installed_drivers": installed_drivers,
    "loaded_drivers": loaded, "origins": origins, "prefix": sys.prefix})
"""


def replay_program():
    """Header, S10's verbatim source-free boundary, the S13 replay body."""
    import inspect

    from _pietto_phase68_slice4_probe import s01
    from _pietto_phase68_slice10_probe import WORKER

    def at(anchor):
        assert WORKER.count(anchor) == 1, anchor
        return WORKER.index(anchor)

    prefix = (
        "import struct\nfrom decimal import Decimal\nfrom datetime import datetime\n"
        "from uuid import UUID\n" + inspect.getsource(s01.scalar) + "\n"
    )
    boundary = WORKER[
        at("forbidden_calls = []\n") : at("load_started = time.monotonic()\n")
    ]
    return REPLAY_HEADER + prefix + boundary + REPLAY


def damage(root, case, kind, member):
    """Orchestrator-side damage of one committed member of a CLOSED copy."""
    import hashlib
    import sqlite3
    import struct
    from datetime import datetime
    import importlib

    from pietto._project import project_job_chunks as k
    from pietto._project import project_job_workspace as w

    pa: Any = importlib.import_module("pyarrow")
    database = sqlite3.connect(Path(root) / "store.sqlite")
    try:
        rows = database.execute(
            "SELECT identity, file FROM chunk WHERE generation = ? ORDER BY start",
            (case["generation"],),
        ).fetchall()
        identity, name = rows[member]
        path = Path(root) / "chunks" / name
        if kind == "missing":
            path.unlink()
        elif kind == "truncated":
            path.write_bytes(path.read_bytes()[:-1])
        elif kind == "byte":
            data = bytearray(path.read_bytes())
            data[len(data) // 2] ^= 1
            path.write_bytes(bytes(data))
        elif kind == "swapped":
            other = Path(root) / "chunks" / rows[member + 1][1]
            first, second = path.read_bytes(), other.read_bytes()
            path.write_bytes(second)
            other.write_bytes(first)
        else:
            _text, descriptor, frame = k.decode_chunk(path.read_bytes())
            fields = {
                n: v
                for n, v in descriptor.items()
                if n not in ("format", "frame_bytes", "frame_sha256")
            }
            if kind == "coordinated":
                fields["generation"] = w.new_identity("gen")
            else:
                header = struct.Struct(">12sQQQ32s32s")
                magic, extent, batches, _size, contract, _digest = header.unpack_from(
                    frame
                )
                table = pa.ipc.open_stream(frame[header.size :]).read_all()
                column, value = (
                    (0, datetime(9999, 12, 31, 23, 59, 59, 500000))
                    if kind == "domain"
                    else (4, -99)
                )
                cells = table.column(column).to_pylist()
                cells[1 if kind == "domain" else 0] = value
                table = table.set_column(
                    column,
                    table.schema.field(column),
                    pa.array(cells, type=table.schema.field(column).type),
                )
                sink = pa.BufferOutputStream()
                with pa.ipc.new_stream(sink, table.schema) as writer:
                    writer.write_table(table)
                payload = sink.getvalue().to_pybytes()
                frame = (
                    header.pack(
                        magic,
                        extent,
                        batches,
                        len(payload),
                        contract,
                        hashlib.sha256(payload).digest(),
                    )
                    + payload
                )
            text, data = k.encode_chunk(fields, frame)
            path.write_bytes(data)
            database.execute(
                "UPDATE chunk SET bytes = ?, digest = ?, descriptor = ? WHERE identity = ?",
                (len(data), hashlib.sha256(data).hexdigest(), text, identity),
            )
            database.commit()
    finally:
        database.close()


def held_worker(argv, env, ledger, log, barrier, *, group, directory, seconds=600):
    """A registered worker killed at its barrier (real SIGKILL) and reaped."""
    import selectors
    import signal
    import subprocess
    import time

    from _pietto_phase68_slice8_probe import event

    started = time.monotonic()
    child = subprocess.Popen(
        argv, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log
    )
    try:
        event(
            ledger,
            dict(
                kind="registered_worker",
                pid=child.pid,
                group=group,
                directory=str(directory),
            ),
        )
        assert child.stdin is not None and child.stdout is not None
        child.stdin.write(b"1")
        child.stdin.close()
        selector = selectors.DefaultSelector()
        selector.register(child.stdout, selectors.EVENT_READ)
        deadline, line = time.monotonic() + seconds, b""
        try:
            while time.monotonic() < deadline and line.strip() != barrier.encode():
                if not selector.select(timeout=max(0.0, deadline - time.monotonic())):
                    break
                line = child.stdout.readline()
                if not line:
                    break
        finally:
            selector.close()
        if line.strip() != barrier.encode():
            raise ValueError("S13_HELD_WORKER_BARRIER:" + group)
        child.send_signal(signal.SIGKILL)
        return child.wait(timeout=30)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=30)
        if child.stdout is not None:
            child.stdout.close()
        event(
            ledger,
            dict(
                kind="worker_reaped",
                pid=child.pid,
                returncode=child.returncode,
                seconds=time.monotonic() - started,
            ),
        )


def backup(workspace, path):
    """A static copy through the supported SQLite backup API (closed store)."""
    import sqlite3

    from pietto._project import project_job_workspace as w

    opened = w.open_workspace(
        workspace["workspace"], expected_identity=workspace["identity"]
    )
    try:
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        copy = sqlite3.connect(path)
        try:
            opened.use().backup(copy)
        finally:
            copy.close()
    finally:
        opened.close()


DAMAGES = (
    ("damage-missing", "missing", 1),
    ("damage-truncated", "truncated", 1),
    ("damage-byte", "byte", 1),
    ("damage-swapped", "swapped", 1),
    ("damage-coordinated", "coordinated", 1),
    ("damage-domain", "domain", 1),
    ("damage-semantic", "semantic", 0),
)


def suite_histories():
    """One main worker's histories; cancellation runs on dedicated copies."""
    # Sizes 1, 2, 3 and whole: offsets inside members, joins across members.
    histories = [
        {"name": f"{case}-b{rows}", "kind": "drain", "case": case, "rows": rows}
        for case, sizes in (
            ("seven39", (1, 3)),
            ("seven65", (2, 4096)),
            ("seven7", (1, 2, 3)),
        )
        for rows in sizes
    ]
    return histories + [
        {
            "name": "seven39-mid-chunk",
            "kind": "two_sessions",
            "case": "seven39",
            "rows": [3, 2],
            "acks": 1,
        },
        {
            "name": "seven39-pinned-hole",
            "kind": "drain",
            "case": "seven39",
            "rows": 3,
            "accept": {"ordinal": 2, "scope": "committed_prefix", "extent": 2},
        },
        {"name": "empty", "kind": "drain", "case": "empty", "rows": 1},
        {
            "name": "hole0",
            "kind": "drain",
            "case": "hole0",
            "rows": 1,
            "accept": {"ordinal": 1, "scope": "committed_prefix", "extent": 0},
        },
        {
            "name": "late",
            "kind": "drain",
            "case": "late",
            "rows": 2,
            "accept": {"scope": "committed_prefix", "extent": 2},
        },
        {
            "name": "refuse",
            "kind": "refuse",
            "case": "seven39",
            "attempts": [
                ["complete_on_hole", {"ordinal": 2, "extent": 2}, "accept"],
                [
                    "beyond_frontier",
                    {"ordinal": 2, "scope": "committed_prefix", "extent": 5},
                    "accept",
                ],
                ["wrong_pin", {"expected_pin": "0" * 64}, "accept"],
                ["wrong_producer", {"accepted_producer": "pietto-x"}, "accept"],
                ["wrong_route", {"route": "postgres_adbc"}, "accept"],
                ["wrong_value", {"values": [1]}, "accept"],
                ["purpose_change", {"purpose": "other"}, "open"],
            ],
        },
        {
            "name": "late-complete",
            "kind": "refuse",
            "case": "late",
            "attempts": [["complete", {"extent": 2}, "accept"]],
        },
        {"name": "verify", "kind": "verify", "case": "seven39"},
        *(
            {"name": label, "kind": "corrupt", "case": label, "rows": 1}
            for label, _kind, _member in DAMAGES
        ),
        {
            "name": "expire-decode",
            "kind": "late_authority",
            "case": "seven65",
            "event": "expire",
            "phase": "decode_offer",
        },
        {
            "name": "expire-ack",
            "kind": "late_authority",
            "case": "seven65",
            "event": "expire",
            "phase": "offer_ack",
        },
        {
            "name": "cancel-decode",
            "kind": "late_authority",
            "case": "cancel-decode",
            "event": "cancel",
            "phase": "decode_offer",
        },
        {
            "name": "cancel-ack",
            "kind": "late_authority",
            "case": "cancel-ack",
            "event": "cancel",
            "phase": "offer_ack",
        },
    ]


def _worker(directory, ledger, interpreter, program, config, name, origin):
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_target_conformance_resources import clean_environment

    private = directory / (PREFIX + name + "-input.json")
    descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(config, stream)
    argv = [str(interpreter), "-I", "-B", "-c", program, str(private)]
    with (directory / (PREFIX + name + ".log")).open("wb") as log:
        if "barrier" in config:
            return held_worker(
                argv,
                clean_environment(),
                ledger,
                log,
                config["barrier"],
                group="s13-" + name,
                directory=directory,
            )
        return worker_process(
            argv,
            clean_environment(),
            ledger,
            log,
            origin=origin,
            group="s13-" + name,
            directory=directory,
            seconds=900,
        )


def installed_members(data, wheel):
    """Every imported pietto module is the wheel member byte for byte."""
    import hashlib
    import zipfile

    with zipfile.ZipFile(wheel) as archive:
        for name, item in data["origins"].items():
            if not item["path"].startswith(data["prefix"] + "/"):
                raise ValueError("S13_INSTALLED_ORIGIN")
            member = "/".join(name.split(".")) + (
                "/__init__.py" if Path(item["path"]).name == "__init__.py" else ".py"
            )
            if hashlib.sha256(archive.read(member)).hexdigest() != item["sha256"]:
                raise ValueError("S13_INSTALLED_MEMBER_BYTES")


def old_runtime(directory, ledger, interpreter, workspace, wheel):
    """The archived S12 wheel's workspace owner refuses v3 before SQLite."""
    import hashlib

    raw = directory / (PREFIX + "old-runtime.json")
    code = _worker(
        directory,
        ledger,
        interpreter,
        s12.OLD_RUNTIME,
        {
            "workspace": workspace["workspace"],
            "workspace_identity": workspace["identity"],
            "wheel": str(wheel),
            "raw": str(raw),
        },
        "old-runtime",
        "old-runtime",
    )
    observed = json.loads(raw.read_text())
    if code or observed != {
        "outcome": "WORKSPACE_FORMAT",
        "unchanged": True,
        "s11_format": "pietto.job-workspace.v1",
    }:
        raise ValueError("S13_OLD_RUNTIME")
    return {**observed, "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}


def cell_cases(capture, cell, *, copy):
    """Each origin cell replays its own copies; damage and cancel copies are separate."""
    import shutil

    cases = {}
    for name, case in capture["cases"].items():
        if copy:
            shutil.copytree(case["workspace"], cell / (name + "-workspace"))
        cases[name] = {**case, "workspace": str(cell / (name + "-workspace"))}
    for label, source in (
        *((label, "seven39") for label, _k, _m in DAMAGES),
        ("cancel-decode", "seven65"),
        ("cancel-ack", "seven65"),
    ):
        if copy:
            shutil.copytree(capture["cases"][source]["workspace"], cell / label)
        cases[label] = {**capture["cases"][source], "workspace": str(cell / label)}
    if copy:
        for label, kind, member in DAMAGES:
            damage(cell / label, cases[label], kind, member)
    return cases


def recheck(directory, origin):
    """Checker-only reconsumption of one cell's unchanged raw, stores and chunks."""
    from _pietto_phase68_slice13_check import check_suite, pilot

    capture = json.loads((directory / (PREFIX + "capture-raw.json")).read_text())
    cell = directory / (PREFIX + origin)
    cases = cell_cases(capture, cell, copy=False)
    data = {
        name: json.loads((cell / (PREFIX + name + "-raw.json")).read_text())
        for name in ("main", "required-a", "required-b", "lost-reply", "lost-resume")
    }
    consumers = {
        "required": data["required-a"]["results"][0]["consumer"],
        "lost": data["lost-reply"]["results"][0]["consumer"],
    }
    backups = {name: cell / (PREFIX + name + "-backup.sqlite") for name in cases}
    scratch, index = cell / (PREFIX + "pilot"), 2
    while scratch.exists():
        scratch, index = cell / (PREFIX + "pilot-" + str(index)), index + 1
    return {
        "summary": check_suite(capture, data, backups, cases, consumers),
        "pilot": pilot(capture, data, backups, cases, consumers, scratch),
    }


def suite(
    directory,
    ledger,
    capture_interpreter,
    replay_interpreter,
    *,
    cells,
    wheel=None,
    old_wheel=None,
):
    """Capture once (native-capture profile), replay per origin (Arrow-only)."""
    import time

    from _pietto_phase68_slice8_probe import event
    from _pietto_phase68_slice13_check import check_suite, pilot

    from pietto._project import project_job_workspace as w

    directory.mkdir(mode=0o700)
    event(
        ledger,
        {"kind": "s13_suite_start", "directory": str(directory), "cells": list(cells)},
        targeted_storage_or_native_family_starts=1,
    )
    report: dict = {"status": "STARTED", "cells": {}}
    started = time.monotonic()
    try:
        runtime = directory / (PREFIX + "capture-runtime")
        runtime.mkdir(mode=0o700)
        capture_raw = directory / (PREFIX + "capture-raw.json")
        base = directory / (PREFIX + "capture")
        base.mkdir(mode=0o700)
        code = _worker(
            directory,
            ledger,
            capture_interpreter,
            SUITE_CAPTURE,
            {
                "runtime_cwd": str(runtime),
                "library_source": str(ROOT / "src"),
                "tests": str(ROOT / "tests"),
                "directory": str(base),
                "cases": CASES,
                "raw": str(capture_raw),
            },
            "capture",
            "source",
        )
        if code:
            raise ValueError("S13_CAPTURE_WORKER_FAILED")
        capture = json.loads(capture_raw.read_text())
        report["storage_profile"] = repr(w.storage_profile(str(directory)))
        if old_wheel is not None:
            report["old_runtime"] = old_runtime(
                directory,
                ledger,
                replay_interpreter,
                capture["cases"]["seven39"],
                old_wheel,
            )
        program = replay_program()
        for origin in cells:
            cell = directory / (PREFIX + origin)
            cell.mkdir(mode=0o700)
            cases = cell_cases(capture, cell, copy=True)
            consumers = {name: w.new_identity("csm") for name in ("required", "lost")}
            lost_operation = w.new_identity("op")
            common = {
                "origin": origin,
                "library_source": str(ROOT / "src"),
                "removed_query_project": str(cell / "never-a-query-project"),
                "cases": cases,
            }
            runs = (
                ("main", {"histories": suite_histories()}),
                (
                    "required-a",
                    {
                        "histories": [
                            {
                                "name": "required-a",
                                "kind": "hold_offered",
                                "case": "seven7",
                                "consumer": consumers["required"],
                                "acks": 1,
                            }
                        ],
                        "barrier": "offered",
                    },
                ),
                (
                    "required-b",
                    {
                        "histories": [
                            {
                                "name": "required-b",
                                "kind": "resume",
                                "case": "seven7",
                                "consumer": consumers["required"],
                                "rows": 3,
                            }
                        ]
                    },
                ),
                (
                    "lost-reply",
                    {
                        "histories": [
                            {
                                "name": "lost-reply",
                                "kind": "hold_ack_commit",
                                "case": "seven7",
                                "consumer": consumers["lost"],
                                "acks": 1,
                                "operation": lost_operation,
                            }
                        ],
                        "barrier": "cut",
                    },
                ),
                (
                    "lost-resume",
                    {
                        "histories": [
                            {
                                "name": "lost-resume",
                                "kind": "resume",
                                "case": "seven7",
                                "consumer": consumers["lost"],
                                "rows": 3,
                                "operation": lost_operation,
                            }
                        ]
                    },
                ),
            )
            data = {}
            for name, extra in runs:
                worker_cwd = cell / (name + "-runtime")
                worker_cwd.mkdir(mode=0o700)
                raw = cell / (PREFIX + name + "-raw.json")
                code = _worker(
                    cell,
                    ledger,
                    replay_interpreter,
                    program,
                    {
                        **common,
                        **extra,
                        "runtime_cwd": str(worker_cwd),
                        "raw": str(raw),
                    },
                    origin + "-" + name,
                    origin,
                )
                expected = -9 if "barrier" in extra else 0
                if code != expected:
                    raise ValueError("S13_REPLAY_WORKER:" + name + ":" + str(code))
                data[name] = json.loads(raw.read_text())
            if origin == "installed":
                if wheel is None:
                    raise ValueError("S13_INSTALLED_WHEEL")
                for name in ("main", "required-b", "lost-resume"):
                    installed_members(data[name], wheel)
            elif any(
                not item["path"].startswith(str(ROOT / "src"))
                for item in data["main"]["origins"].values()
            ):
                raise ValueError("S13_SOURCE_ORIGIN")
            backups = {}
            for name, case in cases.items():
                backups[name] = cell / (PREFIX + name + "-backup.sqlite")
                backup(case, backups[name])
            report["cells"][origin] = {
                "summary": check_suite(capture, data, backups, cases, consumers),
                "pilot": pilot(
                    capture, data, backups, cases, consumers, cell / (PREFIX + "pilot")
                ),
            }
        report["status"] = "PASS"
    except BaseException as error:
        report.update(
            status="FAILED", error_kind=type(error).__name__, error=str(error)[:2000]
        )
        raise
    finally:
        report["seconds"] = time.monotonic() - started
        (directory / (PREFIX + "suite.json")).write_text(
            json.dumps(report, indent=2, default=str) + "\n"
        )
        event(
            ledger,
            {
                "kind": "s13_suite_terminal",
                "status": report["status"],
                "directory": str(directory),
            },
        )
    return report


def native_histories(cases, *, base=True):
    """Per generation: complete drains, a pinned hole, a prefix and a session switch."""
    histories = []
    for key, case in cases.items():
        name = case["case"]
        if not base:
            histories += [
                {"name": key + "-b1", "kind": "drain", "case": key, "rows": 1},
                {"name": key + "-b3", "kind": "drain", "case": key, "rows": 3},
                {
                    "name": key + "-sessions",
                    "kind": "two_sessions",
                    "case": key,
                    "rows": [1, 2],
                    "acks": 1,
                },
            ]
        elif name == "A_late":
            histories.append(
                {
                    "name": key,
                    "kind": "drain",
                    "case": key,
                    "rows": 1,
                    "accept": {"scope": "committed_prefix"},
                }
            )
        else:
            histories.append(
                {
                    "name": key,
                    "kind": "drain",
                    "case": key,
                    "rows": 3 if name != "A_again" else 2,
                }
            )
            if name == "A":
                histories += [
                    {
                        "name": key + "-pinned",
                        "kind": "drain",
                        "case": key,
                        "rows": 3,
                        "accept": {
                            "ordinal": 2,
                            "scope": "committed_prefix",
                            "extent": case["checkpoints"]["2"][1],
                        },
                    },
                    {
                        "name": key + "-sessions",
                        "kind": "two_sessions",
                        "case": key,
                        "rows": [3, 2],
                        "acks": 1,
                    },
                ]
    return histories


def checkpoints(workspace):
    """Committed checkpoint identities per generation, read from a closed store."""
    import sqlite3

    found: dict = {}
    database = sqlite3.connect(
        "file:" + str(Path(workspace) / "store.sqlite") + "?mode=ro", uri=True
    )
    try:
        for generation, ordinal, identity, reached in database.execute(
            "SELECT generation, ordinal, identity, frontier FROM checkpoint"
        ):
            found.setdefault(generation, {})[str(ordinal)] = [identity, reached]
    finally:
        database.close()
    return found


def source_gone(port):
    """The registered source is unreachable once its resource is cleaned up."""
    import socket

    try:
        socket.create_connection(("127.0.0.1", port), timeout=3).close()
    except OSError as error:
        return type(error).__name__
    return "REACHABLE"


def bridge(
    directory,
    ledger,
    capture_interpreter,
    replay_interpreter,
    *,
    target,
    cells,
    wheel=None,
    old_wheel=None,
):
    """Native capture with the source up; the source DB is then stopped and every
    cell recovers solely from protected saved data in a fresh Arrow-only process."""
    import inspect
    import shutil
    import time

    from _pietto_phase68_slice4_probe import ROWS, s01, template
    from _pietto_phase68_slice6_probe import manager
    from _pietto_phase68_slice8_probe import event
    from _pietto_phase68_slice10_check import check_small_pg
    from _pietto_phase68_slice13_check import check_native
    from _pietto_target_conformance_resources import Resources

    from pietto._project.project_compiled_build import build_compiled

    cells = tuple(cells)
    if (
        not cells
        or len(set(cells)) != len(cells)
        or (any(o == "installed" for o, _e in cells) and wheel is None)
    ):
        raise ValueError("S13_BRIDGE_CELLS")
    directory.mkdir(mode=0o700)
    event(
        ledger,
        {
            "kind": "s13_bridge_start",
            "directory": str(directory),
            "target": target,
            "cells": [list(c) for c in cells],
        },
        targeted_storage_or_native_family_starts=1,
    )
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
    register_program, execute_program, _read = s12.worker_programs()
    register_program = s12._replace(
        register_program, "format=w.FORMAT_V2)", "format=w.FORMAT_V3)"
    )
    prefix = (
        "import struct\nfrom decimal import Decimal\nfrom datetime import datetime\n"
        "from uuid import UUID\n" + inspect.getsource(s01.scalar) + "\n"
    )
    report: dict = {
        "status": "STARTED",
        "target": target,
        "cells": [],
        "pin": built.pin,
    }
    started = time.monotonic()
    captured = []
    try:
        report["runtime"] = s01.runtime_identity()
        if (
            report["runtime"]["versions"]
            != s01.helper("_pietto_phase68_executor_cases").PINS
        ):
            raise ValueError("S13_RUNTIME_PINS")
        try:
            event(
                ledger,
                {
                    "kind": "s13_database_start",
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
                runtime = directory / (PREFIX + name + "-runtime")
                runtime.mkdir(mode=0o700)
                common = {
                    "runtime_cwd": str(runtime),
                    "origin": origin,
                    "entry": entry,
                    "target": target,
                    "library_source": str(ROOT / "src"),
                    "workspace": str(workspace),
                }
                registration_path = directory / (PREFIX + name + "-registration.json")
                code = _worker(
                    directory,
                    ledger,
                    capture_interpreter,
                    prefix + register_program,
                    {
                        **common,
                        "build_helpers": str(ROOT / "tests"),
                        "live_project": str(
                            directory / (PREFIX + name + "-live-build")
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
                    origin,
                )
                if code:
                    raise ValueError("S13_REGISTER_WORKER_FAILED")
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
                    raise ValueError("S13_TRUST_HANDOFF")
                raw = directory / (PREFIX + name + "-native-raw.json")
                code = _worker(
                    directory,
                    ledger,
                    capture_interpreter,
                    prefix + execute_program,
                    {
                        **common,
                        "removed_query_project": str(project),
                        "workspace_identity": registration["workspace_identity"],
                        "job": registration["job"],
                        "pin": accepted[0],
                        "producer": accepted[1],
                        "compatibility": accepted[2],
                        "plan": registration["plan"],
                        "port": resource.port,
                        "password": password,
                        "ca_path": str(resource.ca_path) if target == "mysql" else None,
                        "request_seconds": 20,
                        "raw": str(raw),
                    },
                    name + "-execute",
                    origin,
                )
                if code:
                    raise ValueError("S13_EXECUTE_WORKER_FAILED")
                captured.append(
                    (origin, entry, name, workspace, registration, accepted, raw)
                )
        finally:
            # The source is stopped and removed before any replay starts.
            report["cleanup"] = resource.cleanup()
        report["source_after_cleanup"] = source_gone(resource.port)
        if report["source_after_cleanup"] == "REACHABLE":
            raise ValueError("S13_SOURCE_STILL_REACHABLE")
        if old_wheel is not None:
            first = captured[0]
            report["old_runtime"] = old_runtime(
                directory,
                ledger,
                replay_interpreter,
                {
                    "workspace": str(first[3]),
                    "identity": first[4]["workspace_identity"],
                },
                old_wheel,
            )
        program = replay_program()
        for origin, entry, name, workspace, registration, accepted, raw in captured:
            found = checkpoints(workspace)
            cases, plan = {}, {}
            for route, group in registration["plan"]:
                for case, number, _record, generation in group:
                    key = route + ":" + case
                    plan[key] = (route, case)
                    cases[key] = {
                        "case": case,
                        "store": name,
                        "workspace": str(workspace),
                        "identity": registration["workspace_identity"],
                        "job": registration["job"],
                        "generation": generation,
                        "checkpoints": found.get(generation, {}),
                        "pin": accepted[0],
                        "producer": accepted[1],
                        "compatibility": accepted[2],
                        "values": [number],
                        "route": route,
                    }
            histories = native_histories(cases)
            runtime = directory / (PREFIX + name + "-replay-runtime")
            runtime.mkdir(mode=0o700)
            replay_raw = directory / (PREFIX + name + "-replay-raw.json")
            code = _worker(
                directory,
                ledger,
                replay_interpreter,
                program,
                {
                    "origin": origin,
                    "library_source": str(ROOT / "src"),
                    "removed_query_project": str(project),
                    "cases": cases,
                    "histories": histories,
                    "runtime_cwd": str(runtime),
                    "raw": str(replay_raw),
                },
                name + "-replay",
                origin,
            )
            if code:
                raise ValueError("S13_REPLAY_WORKER_FAILED")
            replay = json.loads(replay_raw.read_text())
            if origin == "installed":
                installed_members(replay, wheel)
            elif any(
                not item["path"].startswith(str(ROOT / "src"))
                for item in replay["origins"].values()
            ):
                raise ValueError("S13_SOURCE_ORIGIN")
            backup_path = directory / (PREFIX + name + "-backup.sqlite")
            backup(
                {
                    "workspace": str(workspace),
                    "identity": registration["workspace_identity"],
                },
                backup_path,
            )
            cell = {
                "origin": origin,
                "entry": entry,
                "native": check_native(
                    {"replay": replay},
                    {name: backup_path},
                    cases,
                    histories,
                    {name: len(cases)},
                ),
            }
            # The original S10 literal consumer reads the rows recovered by R1.
            data = json.loads(raw.read_text())
            by_case = {h["history"]: h for h in replay["results"]}
            merged = {**data, "results": []}
            for result in data["results"]:
                if result["case"] == "A_late":
                    continue
                history = by_case[result["route"] + ":" + result["case"]]
                items = [i for i in history["items"] if "delivery" in i]
                merged["results"].append(
                    {
                        **result,
                        "rows": [v for i in items for v in i["values"]],
                        "schemas": [i["schema"] for i in items],
                    }
                )
            origin_root = (
                ROOT / "src/pietto"
                if origin == "source"
                else Path(capture_interpreter).parent.parent
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
            cell["s10_literal_consumer"] = "PASS"
            cell["status"] = "PASS"
            report["cells"].append(cell)
        report["status"] = "PASS"
    except BaseException as error:
        report["status"] = "FAILED"
        report["error_kind"] = type(error).__name__
        report["error"] = str(error)[:2000].replace(
            getattr(resource, "_passwords", ("", ""))[1] or "\0", "<redacted>"
        )
        raise
    finally:
        report["seconds"] = time.monotonic() - started
        (directory / (PREFIX + "bridge.json")).write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        event(
            ledger,
            {
                "kind": "s13_bridge_terminal",
                "status": report["status"],
                "directory": str(directory),
                "seconds": report["seconds"],
            },
        )
    return report


def representatives(
    directory,
    ledger,
    capture_interpreter,
    replay_interpreter,
    *,
    target,
    selected,
    cells,
    wheel=None,
):
    """S10 matrix capture (refined) with the S12 anchors on v3; after the group's
    database is gone, refined coordinates are recovered in fresh Arrow-only workers."""
    import time

    import _pietto_phase68_slice10_probe as s10
    from _pietto_phase68_slice8_probe import event
    from _pietto_phase68_slice13_check import check_native

    original = s10.case_worker_program

    def program():
        return s12._replace(
            s12.capture_case_program(original),
            "format=s12w.FORMAT_V2)",
            "format=s12w.FORMAT_V3)",
        )

    event(
        ledger,
        {
            "kind": "s13_representatives_start",
            "directory": str(directory),
            "target": target,
            "selected": [list(x) for x in selected],
        },
        targeted_storage_or_native_family_starts=1,
    )
    started = time.monotonic()
    s10.case_worker_program = program
    try:
        matrix = s10.acquire_matrix_group(
            directory,
            ledger,
            capture_interpreter,
            target=target,
            group="ordinary",
            cells=cells,
            wheel=wheel,
            selected=set(tuple(x) for x in selected),
        )
    finally:
        s10.case_worker_program = original
    report: dict = {
        "status": "STARTED",
        "matrix_cleanup": matrix["cleanup"],
        "checked": [],
    }
    try:
        replay_code = replay_program()
        for index, item in enumerate(r for r in matrix["records"] if "raw" in r):
            data = json.loads(Path(item["raw"]).read_text())
            handoff = json.loads(Path(item["handoff"]).read_text())
            cases = {}
            for record in data["results"]:
                facts = record["s12"]
                key = record["route"]
                cases[key] = {
                    "case": item["cell"]["case"],
                    "store": "representative",
                    "workspace": facts["workspace"],
                    "identity": facts["identity"],
                    "job": facts["job"],
                    "generation": facts["generation"],
                    "checkpoints": checkpoints(facts["workspace"])[facts["generation"]],
                    "pin": handoff["pin"],
                    "producer": handoff["producer"],
                    "compatibility": handoff["compatibility"],
                    "value_wires": handoff["values"],
                    "route": record["route"],
                    "kind": facts["kind"],
                }
            if any(c["kind"] != "REFINED" for c in cases.values()):
                raise ValueError("S13_REPRESENTATIVE_NOT_REFINED")
            histories = native_histories(cases, base=False)
            runtime = directory / (PREFIX + str(index) + "-replay-runtime")
            runtime.mkdir(mode=0o700)
            raw = directory / (PREFIX + str(index) + "-replay-raw.json")
            code = _worker(
                directory,
                ledger,
                replay_interpreter,
                replay_code,
                {
                    "origin": item["origin"],
                    "library_source": str(ROOT / "src"),
                    "removed_query_project": str(directory / "never-a-query-project"),
                    "cases": cases,
                    "histories": histories,
                    "runtime_cwd": str(runtime),
                    "raw": str(raw),
                },
                str(index) + "-replay",
                item["origin"],
            )
            if code:
                raise ValueError("S13_REPRESENTATIVE_REPLAY_FAILED")
            replay = json.loads(raw.read_text())
            if item["origin"] == "installed":
                installed_members(replay, wheel)
            store = directory / (PREFIX + str(index) + "-backup.sqlite")
            any_case = next(iter(cases.values()))
            backup(any_case, store)
            report["checked"].append(
                {
                    "cell": item["cell"],
                    "origin": item["origin"],
                    "entry": item["entry"],
                    "native": check_native(
                        {"replay": replay},
                        {"representative": store},
                        cases,
                        histories,
                        {"representative": len(cases)},
                        refined=True,
                    ),
                }
            )
        report["status"] = "PASS"
    except BaseException as error:
        report.update(
            status="FAILED", error_kind=type(error).__name__, error=str(error)[:2000]
        )
        raise
    finally:
        report["seconds"] = time.monotonic() - started
        (directory / (PREFIX + "representatives.json")).write_text(
            json.dumps(report, indent=2, default=str) + "\n"
        )
        event(
            ledger,
            {
                "kind": "s13_representatives_terminal",
                "status": report["status"],
                "directory": str(directory),
            },
        )
    return report
