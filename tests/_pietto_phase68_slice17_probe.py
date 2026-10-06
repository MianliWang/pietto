"""S17 runtime/collection fixtures and explicit bounded families; import acquires
nothing.

Core tests have no database and no Arrow. Their units run through the real
coordinator, admission, claims, leases, publisher fences, closures and
collector; only labelled steps are replaced: ARROW_FREE_STORAGE_STEP (the S12
synthetic frame through the real `_materialize`, claim and lease), the S13/S15
Arrow-free replay and payload steps, the S16 ARROW_FREE_MEMBER_CHECK, the
SYNTHETIC_CLOSED_OWNER terminal fields and SIMULATED_NATIVE_IO (a never-connected
real compiled owner whose blocking fetch is a Gate woken only by release or by
the owner's own `cancel()`). Real Arrow and native evidence come from the
execution-profile families.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import os
import threading
import time
from typing import Any, cast

import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice13_probe as s13
import _pietto_phase68_slice15_probe as s15
import _pietto_phase68_slice16_probe as s16

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice17-"
op = s12.op
trust = s13.trust
close_owner = s16.close_owner


def store(root, template, values=(1,), **options):
    """A v7 workspace with one job, publisher, binding and generation."""
    from pietto._project import project_job_workspace as w

    return s12.store(root, template, values, format=w.FORMAT_V7, **options)


def another_job(workspace, template, values=(1,)):
    """A second job (own publisher, binding, generation) in the same workspace."""
    from pietto._project import project_job_store as s
    from pietto._project.project_execution_template import bind_values

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
    return job, publisher, binding, record, generation


def generation_of(publisher, record, binding):
    from pietto._project import project_job_store as s

    return s.register_generation(
        publisher,
        record,
        binding,
        route="postgres_rows",
        isolation="stable",
        operation=op(),
    ).get("generation")


class Gate:
    """SIMULATED_NATIVE_IO blocking fetch: released explicitly, or woken by the
    owner's own cancel event (as a native cancel wakes a blocked fetch)."""

    def __init__(self):
        self.entered = threading.Event()
        self.released = threading.Event()


class Plan:
    """What one capture's simulated owner delivers: row counts, (rows, frame
    bytes), Gates (a blocked fetch) or "FAIL" (a lost read)."""

    def __init__(self, *items, cancel_sent=False):
        self.items = list(items)
        self.cancel_sent = cancel_sent
        self.pulled = 0


PLANS: dict[str, Plan] = {}


def _cancelled(session, sent):
    """SYNTHETIC_CLOSED_OWNER after an observed native cancellation."""
    from pietto._project.project_job_workspace import JobStoreError

    close_owner(
        session.owner,
        session._observed,
        source="FAILED",
        transaction="ROLLBACK_ACK",
        delivery="FAILED",
        primary=("read", "QueryCanceled"),
        cancel=(True, sent, True),
    )
    session._terminal = "FAILED"
    raise JobStoreError("SIMULATED_NATIVE_CANCELED")


def arrow_free_stage(session):
    """CaptureSession.stage over ARROW_FREE_STORAGE_STEP frames of the plan of
    its generation; a Gate blocks like a native fetch until released or the
    owner's own cancel event is set. Positions follow the real stage rules."""
    from pietto._project import project_job_capture as c
    from pietto._project.project_job_workspace import JobStoreError

    session._use()
    if session._ended:
        raise JobStoreError("CAPTURE_ENDED")
    if session._terminal is not None:
        return None
    if session._failed:
        raise JobStoreError("CAPTURE_FAILED")
    if len(session._staged) >= c.MAX_STAGED:
        raise JobStoreError("CAPTURE_STAGED_LIMIT")
    plan = PLANS[session.attempt.generation]
    owner = session.owner
    while True:
        if owner._cancel.is_set():
            _cancelled(session, plan.cancel_sent)
        if not plan.items:
            close_owner(owner, session._observed)
            session._terminal = "EOF"
            return None
        item = plan.items[0]
        if isinstance(item, Gate):
            item.entered.set()
            while not item.released.is_set():
                if owner._cancel.is_set():
                    _cancelled(session, plan.cancel_sent)
                time.sleep(0.005)
            plan.items.pop(0)
            continue
        plan.items.pop(0)
        plan.pulled += 1
        if item == "FAIL":
            # A lost read: the owner's own failure terminal (SYNTHETIC_CLOSED).
            close_owner(
                owner,
                session._observed,
                source="FAILED",
                transaction="ROLLBACK_ACK",
                delivery="FAILED",
                primary=("read", "SimulatedReadError"),
            )
            session._terminal = "FAILED"
            raise JobStoreError("SIMULATED_NATIVE_FAILURE")
        rows, size = item if isinstance(item, tuple) else (item, 64)
        try:
            return s12.stage_frame(session, rows, size=size)
        except BaseException:
            session._failed = True
            raise


def synthetic_owner(binding, source):
    """A real compiled, never-connected PostgresExecution (open is a no-op)."""
    owner = s12.pg_owner(binding)
    owner.open = lambda: owner
    return owner


def arrow_free(monkeypatch=None):
    """Install every labelled Arrow-free step and the simulated owner
    (process-wide without a monkeypatch, as in a spawned child)."""
    from pietto._project import project_job_capture as c
    from pietto._project import project_job_runtime as rt

    s15.arrow_free(monkeypatch)
    s16.arrow_free(monkeypatch)
    for target, name, value in (
        (c.CaptureSession, "stage", arrow_free_stage),
        (rt, "_owner", synthetic_owner),
    ):
        if monkeypatch is None:
            setattr(target, name, value)
        else:
            monkeypatch.setattr(target, name, value)


def source():
    from pietto._project import project_execution as ex
    from pietto._project import project_job_runtime as rt

    access = ex.PostgresAccess(
        "127.0.0.1", 9, "phase66", "pietto_query", "pw", "disable"
    )
    return rt.NativeSource(
        "postgres_rows",
        access,
        ("public", "pg_catalog"),
        ex.ExecutionLimits(batch_rows=2, seconds=600),
    )


def unit(x, mode, generation=None, job=None, **fields):
    from pietto._project import project_job_runtime as rt

    base: dict[str, Any] = dict(
        mode=mode,
        root=x.workspace.root,
        workspace=x.workspace.identity,
        job=job or x.job,
        generation=generation or x.generation,
        trust=(x.built.pin, x.built.producer, x.built.compatibility),
        values=(1,),
        seconds=600,
    )
    if mode in ("CAPTURE", "RELAY", "RECOVER"):
        base.update(source=source(), durable=4 * 1024 * 1024, operations=4096)
    base.update(fields)
    return rt.Unit(**base)


def open_runtime(x, **policy):
    from pietto._project import project_job_runtime as rt

    return rt.open_runtime(
        x.workspace.root,
        expected_identity=x.workspace.identity,
        policy=rt.Policy(**policy),
    )


def grant_capture(runtime, x, publisher, generation, binding, sizes, *, end=True):
    """A caller-run capture under a granted admission (ARROW_FREE_STORAGE_STEP)."""
    from pietto._project import project_job_store as s

    admission = runtime.grant(
        publisher.job, unit(x, "CAPTURE", generation, publisher.job)
    )
    session = s12.capture(publisher.use(), publisher, generation, binding)
    session.admission = admission
    staged = [s12.stage_frame(session, rows) for rows in sizes]
    for item in staged:
        session.publish(item, operation=op())
    if end:
        close_owner(session.owner, session.observed)
        session.end(operation=op())
        s.record_attempt(publisher, session.attempt, session.owner, operation=op())
    return session, admission


def rows(workspace, sql, parameters=()):
    return workspace.use().execute(sql, parameters).fetchall()


def files(root):
    """(directory, name) of every chunk/staging name present."""
    return sorted(
        (d, n) for d in ("chunks", "staging") for n in os.listdir(os.path.join(root, d))
    )


def wait_for(predicate, seconds=30.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def setup_namespace(**values):
    return SimpleNamespace(**values)


def json_text(value):
    return json.dumps(value, sort_keys=True)


CHILD_HEADER = r"""
import json, os, signal, sys, time
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[3])
config = json.loads(sys.argv[2])
from types import SimpleNamespace
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c, project_job_chunks as k
from pietto._project import project_job_collection as col
from pietto._project import project_job_runtime as rt
import _pietto_phase68_slice17_probe as probe
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

def attach():
    return w.open_workspace(config["workspace"], expected_identity=config["identity"])

def runtime():
    return rt.open_runtime(config["workspace"], expected_identity=config["identity"],
        policy=rt.Policy())
"""


def child(program, config):
    """A spawned isolated child (fresh interpreter, no inherited handles); the
    caller must reap it."""
    import subprocess
    import sys

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


def child_config(x, **extra):
    return {
        "workspace": x.workspace.root,
        "identity": x.workspace.identity,
        "job": x.job,
        "generation": x.generation,
        "pin": x.built.pin,
        "producer": x.built.producer,
        "compatibility": list(x.built.compatibility),
        **extra,
    }


def outcome(item) -> dict:
    """The recorded outcome of one AttemptRecord (it must have a terminal)."""
    assert item.outcome is not None
    return dict(item.outcome)


# ---------------------------------------------------------------------------
# Execution-profile families (Arrow present). Nothing runs at import.


def arrow_native(gates: dict):
    """SIMULATED_NATIVE_IO for the Arrow profile: the runtime's `_native` builds
    a real compiled never-connected PostgresExecution whose `__next__` is the
    S12 simulated stepper (real ExecutionPayloads checks, Arrow and IPC), with
    the labelled SIMULATED qualification/context; a Gate in a plan blocks like a
    native fetch until released or the owner's own cancel event is set."""
    import pietto._project.project_execution as ex
    from pietto._project import project_job_runtime as rt
    from pietto._project.project_execution_postgres import PostgresExecution

    def gated(owner):
        plan = s12.PLANS[id(owner)]
        while plan.batches and isinstance(plan.batches[0], Gate):
            gate = plan.batches[0]
            gate.entered.set()
            while not gate.released.is_set():
                if owner._cancel.is_set():
                    owner._primary = ex.ExecutionFailure("read", "QueryCanceled")
                    owner._source, owner._delivery = "FAILED", "FAILED"
                    owner._transaction, owner._cleanup = "ROLLBACK_ACK", "CLOSED"
                    owner._cancel_observed, owner._closed = True, True
                    raise RuntimeError("SIMULATED_NATIVE_CANCELED")
                time.sleep(0.005)
            plan.batches.pop(0)
        return s12.simulated_next(owner)

    def native(self, record, context, binding, route):
        owner = s12.pg_owner(binding, batch_rows=4)
        owner.open = lambda: owner
        owner._qualification = s16.SIMULATED_QUALIFICATION
        owner.context = s16.SIMULATED_CONTEXT
        batches, codes = gates[record.unit.generation]
        plan = s12.Plan([b for b in batches if not isinstance(b, Gate)], codes)
        # Gates sit between the S12 batches (the simulated stepper skips them).
        plan.batches = cast(
            Any,
            [b if isinstance(b, Gate) else tuple(tuple(r) for r in b) for b in batches],
        )
        s12.PLANS[id(owner)] = plan
        context["owner"] = owner
        self._bind_owner(record, owner)
        return owner

    PostgresExecution.__next__ = gated  # type: ignore[method-assign]
    rt.Runtime._native = native  # type: ignore[method-assign]


SUITE_HEADER = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, os, hashlib, sqlite3, threading, time, subprocess, signal
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["runtime_cwd"])
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
sys.path.append(config["tests"])
from pietto._project import project_job_capture as c, project_job_store as s
from pietto._project import project_job_workspace as w, project_job_publication as p
from pietto._project import project_job_replay as r, project_job_chunks as k
from pietto._project import project_job_runtime as rt, project_job_collection as col
from pietto._project import project_job_sink as sk
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_execution_template import bind_values
import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice17_probe as probe
def op():
    return s.new_operation()
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

SUITE = r"""
import pyarrow as pa
from pietto._project import project_job_chunks as chunks
base = Path(config["directory"])
template, built = s12.seven_template(base / "build", precision=39)
trust = (built.pin, built.producer, built.compatibility)
plans = {}
probe.arrow_native(plans)
workspace = w.create_workspace(str(base / "ws"), format=w.FORMAT_V7)
W = workspace.root
binding0 = bind_values(template, ())
def job(batches):
    j = s.register_job(workspace, template, operation=op()).get("job")
    publisher = s.claim_publisher(workspace, j, operation=op())
    record = s.register_binding(publisher, binding0, operation=op()).get("binding")
    g = s.register_generation(publisher, record, binding0, route="postgres_rows",
        isolation="stable", operation=op()).get("generation")
    publisher.close()
    plans[g] = (batches, s12.SEVEN_CODES)
    return j, g
def rows(*indexes):
    return [s12.SEVEN_ROWS[i] for i in indexes]
def unit(mode, j, g, **fields):
    base_ = dict(mode=mode, root=W, workspace=workspace.identity, job=j, generation=g,
        trust=trust, values=(), seconds=1800)
    if mode in ("CAPTURE", "RELAY", "RECOVER"):
        base_.update(source=probe.source(), durable=8 * 1024 * 1024)
    base_.update(fields)
    return rt.Unit(**base_)
def wires_of(batch):
    data = pa.record_batch(batch)
    columns = [data.column(i).to_pylist() for i in range(data.num_columns)]
    return [[chunks.coordinate_wire(column[j]) for column in columns]
        for j in range(data.num_rows)]
policy = dict(connections=3, workers=3, queue=8, memory=512 * 1024 * 1024,
    durable=64 * 1024 * 1024, operations=65536, overtakes=4)
runtime = rt.open_runtime(W, expected_identity=workspace.identity, policy=rt.Policy(**policy))
handles = []
observed = {}
# 1. Two distinct jobs overlap through the coordinator (both blocked in a fetch).
gate_a, gate_b = probe.Gate(), probe.Gate()
ja, ga = job([rows(0, 1), gate_a, rows(2, 3), rows(4)])
jb, gb = job([rows(1), gate_b, rows(0)])
ha = runtime.submit(unit("CAPTURE", ja, ga)); handles.append(ha)
hb = runtime.submit(unit("CAPTURE", jb, gb)); handles.append(hb)
assert gate_a.entered.wait(120) and gate_b.entered.wait(120)
observed["overlap"] = {"a": dict(runtime.query(ha).counters), "b": dict(runtime.query(hb).counters),
    "both_blocked_ns": time.monotonic_ns()}
gate_a.released.set(); gate_b.released.set()
observed["capture_terminals"] = [runtime.wait(h, 300).terminal for h in (ha, hb)]
# 2. RELAY against a stalled sink: a fixed high-water while another job runs.
handle = sk.create_sink(str(base / "sink"), namespace="s17.suite", epoch=1,
    retention_seconds=86400)
sink_facts = [handle.root, handle.identity, handle.namespace, handle.epoch, handle.retention]
handle.close()
jc, gc = job([rows(0, 1), rows(2, 3), rows(4)])
lock = sqlite3.connect(sink_facts[0] + "/sink.sqlite", isolation_level=None, timeout=5)
lock.execute("BEGIN IMMEDIATE")
hc = runtime.submit(unit("RELAY", jc, gc, sink=rt.SinkTarget(*sink_facts, 0.2), rows=2,
    batch_rows=2)); handles.append(hc)
state = runtime.wait_activity(hc, "WAITING_FOR_DOWNSTREAM", 300)
high = dict(state.counters)
jd, gd = job([rows(0), rows(1), rows(2)])
hd = runtime.submit(unit("CAPTURE", jd, gd)); handles.append(hd)
other = runtime.wait(hd, 300).terminal
time.sleep(0.5)
still = runtime.query(hc)
observed["relay_high_water"] = {"first": high, "after": dict(still.counters),
    "activity": still.activity, "other_terminal": other,
    "claims": workspace.use().execute("SELECT count(*) FROM chunk_claim WHERE generation = ?",
        (gc,)).fetchone()[0],
    "observations": workspace.use().execute("SELECT count(*) FROM sink_observation").fetchone()[0]}
lock.execute("ROLLBACK"); lock.close()
runtime.resume(hc)
observed["relay_terminal"] = runtime.wait(hc, 300).terminal
reopened = sk.open_sink(sink_facts[0], expected_identity=sink_facts[1])
observed["sink_rows"] = [list(r) for r in reopened.use().execute(
    "SELECT position, payload FROM effect ORDER BY position")]
reopened.close()
# 3. REPLAY of job A's saved result: real Arrow batches, explicit acks only.
snapshot = c.checkpoint_snapshot(workspace, ja, ga)
hr = runtime.submit(unit("REPLAY", ja, ga, checkpoint=snapshot.checkpoint,
    extent=snapshot.frontier, rows=2, batch_rows=2)); handles.append(hr)
acked, replay_wires, replay_extents, before_ack = set(), [], [], []
while runtime.query(hr).terminal is None:
    item = runtime.take(hr, 1)
    if item is None or item.identity in acked:
        time.sleep(0.01)
        continue
    before_ack.append(workspace.use().execute(
        "SELECT count(*) FROM acknowledgement").fetchone()[0])
    replay_wires.extend(wires_of(item.batch))
    replay_extents.append([item.start, item.stop, item.held_bytes])
    acked.add(item.identity)
    runtime.ack(hr, item)
observed["replay"] = {"terminal": runtime.query(hr).terminal, "wires": replay_wires,
    "extents": replay_extents, "acks_before_each": before_ack,
    "counters": dict(runtime.query(hr).counters)}
# 4. PUBLISH job A's complete generation (members read under shared leases).
closing = s.job_record(workspace, ja).attempts[0].identity
hp = runtime.submit(unit("PUBLISH", ja, ga, checkpoint=snapshot.checkpoint,
    closing=closing)); handles.append(hp)
observed["publish_terminal"] = runtime.wait(hp, 300).terminal
# 5. Control under saturation: three admitted units blocked, one queued.
gates = [probe.Gate() for _ in range(3)]
blocked = []
for gate in gates:
    je, ge = job([rows(0), gate, rows(1)])
    blocked.append((runtime.submit(unit("CAPTURE", je, ge)), je, ge))
    handles.append(blocked[-1][0])
assert all(g.entered.wait(120) for g in gates)
jq, gq = job([rows(0)])
hq = runtime.submit(unit("CAPTURE", jq, gq)); handles.append(hq)
time.sleep(0.3)
saturated = runtime.query(hq)
receipt = runtime.cancel(blocked[0][0])
queued = runtime.cancel(hq)
gates[1].released.set(); gates[2].released.set()
cancelled = runtime.wait(blocked[0][0], 300)
waiting = runtime.wait(hq, 300)
observed["control"] = {"saturated": [saturated.state, saturated.limiting],
    "receipt": receipt["signal"], "cancelled": [cancelled.terminal, cancelled.durable_cancel,
    [k for _n, k in cancelled.events]], "queued": [waiting.terminal, waiting.durable_cancel],
    "jobs": [s.job_record(workspace, blocked[0][1]).state, s.job_record(workspace, jq).state],
    "others": [runtime.wait(h, 300).terminal for h, _j, _g in blocked[1:]]}
# A killed producer (an attempt left open, then a takeover interrupts it).
jk, gk = job([rows(0)])
publisher = s.claim_publisher(workspace, jk, operation=op())
killed = s.open_attempt(publisher, gk, binding0, operation=op()).identity
publisher.close()
publisher = s.claim_publisher(workspace, jk, operation=op())
s.interrupt_attempt(publisher, killed, operation=op())
publisher.close()
# 6. Retirement with a surviving consumer root, then real cross-process races.
consumer_snapshot = c.checkpoint_snapshot(workspace, jb, gb)
publisher = s.claim_publisher(workspace, jb, operation=op())
acceptance = r.accept_saved_read(workspace, jb, gb, checkpoint=consumer_snapshot.checkpoint,
    consumer=r.new_consumer(), scope="complete_capture", extent=consumer_snapshot.frontier,
    purpose="s17-suite", route="postgres_rows", values=(), expected_pin=built.pin,
    accepted_producer=built.producer, accepted_compatibility=built.compatibility,
    seconds=3600, batch_rows=4096)
retention = r.register_consumer(publisher, acceptance, operation=op()).get("retention")
col.retire_generation(publisher, gb, operation=op())
with_root = runtime.collect()
reader = subprocess.Popen([sys.executable, "-I", "-B", "-c", probe.ARROW_READER,
    json.dumps({"origin": config["origin"], "library_source": config["library_source"],
    "tests": config["tests"], "workspace": W, "identity": workspace.identity, "job": jb,
    "generation": gb, "pin": built.pin, "producer": built.producer,
    "compatibility": list(built.compatibility), "release": str(base / "release")})],
    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
line = reader.stdout.readline().strip()
reads = [json.loads(line)] if line.startswith("{") else []
c.release_retention(publisher, retention, operation=op())
publisher.close()
busy = runtime.collect()
(base / "release").write_text("")
reader_out, reader_err = reader.communicate(timeout=120)
before_collection = base / "before-collection.sqlite"
with sqlite3.connect(before_collection) as out:
    workspace.use().backup(out)
out.close()
before_files = {n: list(v) for n, v in probe.check_inventory(W).items()}
won = runtime.collect()
decisions = [[gb, time.monotonic_ns()]]
# Collector first in another process (decided, killed before unlink), then a
# reader in this process refuses after the lease is released.
publisher = s.claim_publisher(workspace, jd, operation=op())
col.retire_generation(publisher, gd, operation=op())
publisher.close()
runtime.close()
collector = subprocess.Popen([sys.executable, "-I", "-B", "-c", probe.ARROW_CUT,
    json.dumps({"origin": config["origin"], "library_source": config["library_source"],
    "tests": config["tests"], "workspace": W, "identity": workspace.identity})],
    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
cut_line = collector.stdout.readline().strip()
cut_epoch = int(cut_line.split()[1]) if cut_line.startswith("cut ") else None
outcome = []
def late_reader():
    handle_ = w.open_workspace(W, expected_identity=workspace.identity)
    try:
        output = c.stored_output(handle_, jd, gd, expected_pin=built.pin,
            accepted_producer=built.producer, accepted_compatibility=built.compatibility)
        snap = c.checkpoint_snapshot(handle_, jd, gd)
        with c.SnapshotReader(handle_, snap, output) as reader_:
            reader_.read(0)
        outcome.append("READ")
    except w.JobStoreError as error:
        outcome.append(str(error))
    finally:
        handle_.close()
thread = threading.Thread(target=late_reader)
thread.start()
time.sleep(0.5)
waiting_reader = thread.is_alive()
collector.send_signal(signal.SIGKILL)
collector.communicate(timeout=60)
thread.join(120)
second = rt.open_runtime(W, expected_identity=workspace.identity, policy=rt.Policy(**policy))
resumed = second.collect()
# A decided subject whose unlink fails stays decided, present and unremoved.
publisher = s.claim_publisher(workspace, blocked[0][1], operation=op())
col.retire_generation(publisher, blocked[0][2], operation=op())
publisher.close()
real_unlink = k._unlink
k._unlink = lambda name, fd: (_ for _ in ()).throw(OSError(5, "EIO"))
try:
    second.collect()
except OSError:
    pass
finally:
    k._unlink = real_unlink
second.close()
after_files = {n: list(v) for n, v in probe.check_inventory(W).items()}
after_collection = base / "after-collection.sqlite"
with sqlite3.connect(after_collection) as out:
    workspace.use().backup(out)
out.close()
units = {}
vectors = {row[0]: json.loads(row[4]) for row in workspace.use().execute(
    "SELECT * FROM admission")}
for h in handles:
    q = runtime.query(h)
    units[h] = {"events": [list(e) for e in q.events], "vector": vectors.get(h),
        "job": q.job, "generation": q.generation, "durable_cancel": q.durable_cancel,
        "settlement": q.settlement, "terminal": q.terminal, "failure": q.failure}
# D12 input: one typed value of job A's first member altered with every checksum
# recomputed; decoded here (Arrow profile) for the independent checker.
first = c.checkpoint_snapshot(workspace, ja, ga).members[0]
data = (Path(W) / "chunks" / first.file).read_bytes()
_text, descriptor, frame = chunks.decode_chunk(data)
import _pietto_phase68_slice12_check as k12
table = k12.decode_frame(frame, first.stop - first.start, descriptor["contract"])[1]
column = table.column(4).to_pylist()
column[0] = column[0] + 1
table = table.set_column(4, table.schema.field(4), pa.array(column, table.schema.field(4).type))
sink_ = pa.BufferOutputStream()
with pa.ipc.new_stream(sink_, table.schema) as writer:
    for batch in table.to_batches():
        writer.write_batch(batch)
payload = sink_.getvalue().to_pybytes()
head = k12.FRAME.unpack_from(frame)
reframed = k12.FRAME.pack(head[0], head[1], head[2], len(payload), head[4],
    hashlib.sha256(payload).digest()) + payload
fields = {key: value for key, value in descriptor.items()
    if key not in ("format", "frame_bytes", "frame_sha256")}
_t, damaged_chunk = chunks.encode_chunk(fields, reframed)
_t2, parsed, parsed_frame = k12.parse_chunk(damaged_chunk)
redecoded = k12.decode_frame(parsed_frame, parsed["rows"], parsed["contract"])[1]
damaged_wires = [[chunks.coordinate_wire(redecoded.column(i).to_pylist()[j])
    for i in range(redecoded.num_columns)] for j in range(redecoded.num_rows)]
write({"observed": observed, "units": units, "policy": policy,
    "stores": {"before": str(before_collection), "after": str(after_collection)},
    "files": {"before": before_files, "after": after_files},
    "collections": {"with_root": [list(d) for d in with_root.decided],
        "with_root_blocked": [[g, [list(x) for x in rs]] for g, rs in with_root.blocked],
        "busy": list(busy.busy), "busy_decided": [list(d) for d in busy.decided],
        "won": [list(d) for d in won.decided], "won_removed": [list(x) for x in won.removed],
        "resumed": [list(x) for x in resumed.resumed]},
    "reads": reads, "decisions": decisions, "reader_stderr": reader_err[-2000:],
    "cut": {"epoch": cut_epoch, "waiting_reader": waiting_reader, "outcome": outcome,
        "generation": gd},
    "killed": [killed], "acked": sorted(acked), "replay_wires": replay_wires,
    "damaged_wires": damaged_wires, "jobs": {"a": [ja, ga], "b": [jb, gb], "c": [jc, gc],
    "d": [jd, gd]}, "verify": verify_store(workspace), "workspace": W,
    "identity": workspace.identity})
workspace.close()
"""

ARROW_READER = r"""
import json, os, sys, time
config = json.loads(sys.argv[1])
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
sys.path.append(config["tests"])
from pietto._project import project_job_capture as c, project_job_workspace as w
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
output = c.stored_output(workspace, config["job"], config["generation"],
    expected_pin=config["pin"], accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]))
snapshot = c.checkpoint_snapshot(workspace, config["job"], config["generation"])
reader = c.SnapshotReader(workspace, snapshot, output)
checked = reader.read(0)
sys.stdout.write(json.dumps([config["generation"], time.monotonic_ns(), "READ",
    checked.table.num_rows]) + "\n")
sys.stdout.flush()
deadline = time.monotonic() + 120
while not os.path.exists(config["release"]) and time.monotonic() < deadline:
    time.sleep(0.01)
reader.close()
workspace.close()
"""

ARROW_CUT = r"""
import json, sys, time
config = json.loads(sys.argv[1])
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
sys.path.append(config["tests"])
from pietto._project import project_job_chunks as k, project_job_runtime as rt
opened = rt.open_runtime(config["workspace"], expected_identity=config["identity"])
def stop(*args, **kwargs):
    sys.stdout.write("cut " + str(opened.owner.epoch) + "\n")
    sys.stdout.flush()
    while True:
        time.sleep(60)
k._unlink = stop
opened.collect()
"""


def check_inventory(root):
    from _pietto_phase68_slice17_check import inventory

    return inventory(root)


def suite(directory, ledger, interpreter, *, origin, wheel=None, old_wheel=None):
    """Arrow-profile S17 suite in one registered worker (see SUITE), then the
    independent checker, the coordinated damages and (installed) the archived
    S16 runtime's refusal of v7."""
    import _pietto_phase68_slice15_check as s15check
    import _pietto_phase68_slice16_check as s16check
    import _pietto_phase68_slice17_check as check
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_phase68_slice14_probe import _origin_check
    from _pietto_target_conformance_resources import clean_environment

    directory.mkdir(mode=0o700)
    raw = directory / (PREFIX + "suite-raw.json")
    path = directory / (PREFIX + "suite-config.json")
    s16._write_private(
        path,
        {
            "runtime_cwd": str(directory),
            "library_source": str(ROOT / "src"),
            "tests": str(ROOT / "tests"),
            "origin": origin,
            "directory": str(directory),
            "raw": str(raw),
        },
    )
    started = time.monotonic()
    with (directory / (PREFIX + "suite-worker.log")).open("wb") as log:
        status = worker_process(
            [str(interpreter), "-I", "-B", "-c", SUITE_HEADER + SUITE, str(path)],
            clean_environment(),
            ledger,
            log,
            origin=origin,
            group="s17-suite",
            directory=directory,
            seconds=3600,
        )
    if status:
        raise ValueError("S17_SUITE_WORKER:" + str(status))
    data = json.loads(raw.read_text())
    _origin_check(data, origin, wheel)
    report = {
        "status": "CHECKING",
        "origin": origin,
        "worker_seconds": time.monotonic() - started,
    }
    o = data["observed"]
    check.need(o["capture_terminals"] == ["COMPLETED", "COMPLETED"], "SUITE_OVERLAP")
    check.need(
        o["overlap"]["a"].get("chunks", 0) >= 1
        and o["overlap"]["b"].get("chunks", 0) >= 1,
        "SUITE_OVERLAP",
    )
    high = o["relay_high_water"]
    check.need(
        high["activity"] == "WAITING_FOR_DOWNSTREAM"
        and high["first"] == high["after"]
        and high["other_terminal"] == "COMPLETED"
        and high["claims"] == 1
        and high["observations"] == 0
        and o["relay_terminal"] == "COMPLETED",
        "SUITE_BACKPRESSURE",
    )
    check.need([row[0] for row in o["sink_rows"]] == list(range(5)), "SUITE_SINK_ONCE")
    oracle = s16check.encoded([s12.SEVEN_ROWS[i] for i in (0, 1, 2, 3, 4)])
    replayed = [[s15check.decode_wire(v) for v in row] for row in o["replay"]["wires"]]
    check.need(s16check.encoded(replayed) == oracle, "VALUES")
    check.need(
        o["replay"]["terminal"] == "COMPLETED"
        and o["replay"]["acks_before_each"] == list(range(len(o["replay"]["extents"]))),
        "SUITE_ACK",
    )
    check.need(o["publish_terminal"] == "COMPLETED", "SUITE_PUBLISH")
    control = o["control"]
    check.need(
        control["saturated"] == ["WAITING_FOR_ADMISSION", "connections"]
        and control["cancelled"][:2] == ["CANCELLED", "COMMITTED"]
        and control["queued"] == ["CANCELLED_QUEUED", "COMMITTED"]
        and control["jobs"] == ["CANCELLED", "CANCELLED"]
        and control["others"] == ["COMPLETED", "COMPLETED"],
        "SUITE_CONTROL",
    )
    collections = data["collections"]
    check.need(not collections["with_root"], "SUITE_ROOT")
    check.need(
        collections["busy"] and not collections["busy_decided"], "SUITE_READER_WINS"
    )
    check.need(collections["won"] and collections["won_removed"], "SUITE_COLLECTED")
    cut = data["cut"]
    check.need(
        cut["waiting_reader"]
        and cut["outcome"] == ["CHUNK_COLLECTED"]
        and sorted(b for _c, b in collections["resumed"]) == ["UNLINKED"] * 3,
        "SUITE_COLLECTOR_WINS",
    )
    damaged = [[s15check.decode_wire(v) for v in row] for row in data["damaged_wires"]]
    check.need(
        s16check.encoded(damaged) != oracle[: len(damaged)], "VALUES"
    )  # D12: the altered typed value meets the literal oracle
    after = check.load(data["stores"]["after"])
    evidence = {
        "data": after,
        "units": {h: u for h, u in data["units"].items() if u["vector"] is not None},
        "policy": data["policy"],
        "files": {n: tuple(v) for n, v in data["files"]["after"].items()},
        "killed": data["killed"],
        "acked": set(data["acked"]),
        "reads": [tuple(x[:3]) for x in data["reads"]],
        "decisions": [tuple(x) for x in data["decisions"]],
    }
    facts = check.check_all(evidence)
    damages = {
        kind: check.rejects(kind, evidence)
        for kind in check.DAMAGES
        if kind not in ("D14_promoted_unlink",)
    }
    report.update(
        status="PASS",
        facts=facts,
        damages=damages,
        d12="VALUES",
        verify=data["verify"],
        overlap=o["overlap"],
        high_water=high,
        control=control,
        collections=collections,
        cut=cut,
    )
    if old_wheel is not None:
        report["old_runtime"] = old_runtime(directory, ledger, interpreter, old_wheel)
    s16._write_private(directory / (PREFIX + "suite-report.json"), report)
    return report


def old_runtime(directory, ledger, interpreter, old_wheel):
    """The archived S16 workspace owner (wheel bytes) meets a v7 workspace: it
    must refuse before SQLite with the directory unchanged."""
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_target_conformance_resources import clean_environment
    from pietto._project import project_job_workspace as w

    root = directory / (PREFIX + "v7-workspace")
    workspace = w.create_workspace(str(root), format=w.FORMAT_V7)
    identity = workspace.identity
    workspace.close()
    raw = directory / (PREFIX + "old-runtime-raw.json")
    private = directory / (PREFIX + "old-runtime-input.json")
    s16._write_private(
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
            origin="archived-s16-wheel",
            group="s17-old-runtime",
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
        raise ValueError("S17_OLD_RUNTIME_ACCEPTED_V7")
    return data


# ---------------------------------------------------------------------------
# Native joined histories through the runtime (pinned native profile for
# capture/R2/control, Arrow-only profile for saved use and collection).

NATIVE_HEADER = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, os, time, hashlib, shutil, sqlite3
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
from pietto._project import project_job_runtime as rt, project_job_sink as sk
from pietto._project import project_job_delivery as d
from pietto._project.project_job_store_verification import verify_store
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
def source(route_, page):
    if route_ == "mysql_rows":
        access = ex.MySQLAccess("127.0.0.1", config["port"], "phase66", "pietto_query",
            config["password"], config["ca_path"], "pietto_query@%",
            verify_identity=False, loopback_tls_exception=True)
        schemas = ("phase66",)
    else:
        access = ex.PostgresAccess("127.0.0.1", config["port"], "phase66",
            "pietto_query", config["password"], "disable")
        schemas = ("public", "pg_catalog")
    return rt.NativeSource(route_, access, schemas,
        ex.ExecutionLimits(batch_rows=page, seconds=config["request_seconds"]))
def bundle(item):
    trust_ = dict(expected_pin=item["pin"], accepted_producer=item["producer"],
        accepted_compatibility=tuple(item["compatibility"]))
    template_ = prepare_compiled_template(load_compiled(
        Path(item["bundle"]).read_bytes(), **trust_))
    return template_, tuple(scalar_read(v).value for v in item["values"]), (
        item["pin"], item["producer"], tuple(item["compatibility"]))
def register(workspace, template_, values_, route_):
    binding = bind_values(template_, tuple(zip(template_.slots, values_, strict=True)))
    job = s.register_job(workspace, template_, operation=op()).get("job")
    publisher = s.claim_publisher(workspace, job, operation=op())
    record = s.register_binding(publisher, binding, operation=op()).get("binding")
    generation = s.register_generation(publisher, record, binding, route=route_,
        isolation="stable", operation=op()).get("generation")
    publisher.close()
    return job, generation
def unit(workspace, mode, job, generation, trust_, values_, **fields):
    return rt.Unit(mode=mode, root=workspace.root, workspace=workspace.identity,
        job=job, generation=generation, trust=trust_, values=values_,
        seconds=config["request_seconds"], **fields)
def states(runtime, handles, workspace):
    vectors = {r[0]: json.loads(r[4]) for r in workspace.use().execute(
        "SELECT * FROM admission")}
    out = {}
    for h in handles:
        q = runtime.query(h)
        out[h] = {"events": [list(e) for e in q.events], "vector": vectors.get(h),
            "job": q.job, "generation": q.generation, "durable_cancel": q.durable_cancel,
            "settlement": q.settlement, "terminal": q.terminal, "failure": q.failure,
            "counters": dict(q.counters), "signal": q.cancel[1],
            "runtime": runtime.owner.epoch}
    return out
policy = rt.Policy(workers=3, connections=3, queue=8, durable=128 * 1024 * 1024)
"""

NATIVE_CAPTURE = r"""
main_trust = (config["pin"], config["producer"], tuple(config["compatibility"]))
main_values = tuple(scalar_read(v).value for v in config["values"])
live = None
if config["entry"] == "live":
    sys.path.insert(0, config["build_helpers"])
    from _pietto_phase68_slice10_probe import build_native_reference
    reference = build_native_reference(Path(config["live_project"]),
        config["target"], config["cell"], config["providers"])
    artifact, preparation, query, output, bound = reference
    live = prepare_live_template(artifact, guarded=preparation, refinement=query)
    del artifact, preparation, query, output, bound, reference, build_native_reference
    shutil.rmtree(config["live_project"])
    sys.path.remove(config["build_helpers"])
    for name in tuple(sys.modules):
        if name.startswith(("_pietto_", "test_phase", "s04_", "s03_")):
            del sys.modules[name]
    template = live
else:
    template = prepare_compiled_template(load_compiled(Path(config["bundle"]).read_bytes(),
        expected_pin=config["pin"], accepted_producer=config["producer"],
        accepted_compatibility=tuple(config["compatibility"])))
workspace = w.create_workspace(config["workspace"], format=w.FORMAT_V7)
job, generation = register(workspace, template, main_values, route)
contention = bundle(config["contention"])
c_job, c_generation = register(workspace, contention[0], contention[1],
    config["contention_route"])
distinct = []
for item in config["distinctions"]:
    t_, v_, tr_ = bundle(item)
    j_, g_ = register(workspace, t_, v_, route)
    distinct.append((item["key"], j_, g_, tr_, v_))
handle = sk.create_sink(config["sink"], namespace=config["namespace"], epoch=1,
    retention_seconds=86400)
sink = [handle.root, handle.identity, handle.namespace, handle.epoch, handle.retention]
handle.close()
lock = sqlite3.connect(sink[0] + "/sink.sqlite", isolation_level=None, timeout=5)
lock.execute("BEGIN IMMEDIATE")
runtime = rt.open_runtime(workspace.root, expected_identity=workspace.identity,
    policy=policy)
relay = runtime.submit(unit(workspace, "RELAY", job, generation, main_trust, main_values,
    source=source(route, 2), extraction=True, sink=rt.SinkTarget(*sink, 0.2), rows=2,
    batch_rows=2, durable=16 * 1024 * 1024, template=live))
handles = [relay]
others = [runtime.submit(unit(workspace, "CAPTURE", c_job, c_generation, contention[2],
    contention[1], source=source(config["contention_route"], 2),
    durable=16 * 1024 * 1024))]
for key, j_, g_, tr_, v_ in distinct:
    others.append(runtime.submit(unit(workspace, "CAPTURE", j_, g_, tr_, v_,
        source=source(route, 2), durable=16 * 1024 * 1024)))
handles += others
blocked = runtime.wait_activity(relay, "WAITING_FOR_DOWNSTREAM", 600)
finished = [runtime.wait(h, 900) for h in others]
time.sleep(0.3)
still = runtime.query(relay)
record = s.job_record(workspace, job)
snapshot = c.checkpoint_snapshot(workspace, job, generation)
facts.update(workspace=workspace.root, identity=workspace.identity, job=job,
    generation=generation, attempt=record.attempts[0].identity,
    contention=[c_job, c_generation], distinct=[[k, j, g] for k, j, g, _t, _v in distinct],
    blocked=[blocked.activity, dict(blocked.counters)],
    still=[still.activity, dict(still.counters)],
    others=[[q.terminal, q.failure] for q in finished],
    closings={g_: s.job_record(workspace, j_).attempts[0].identity
        for _k, j_, g_, _t, _v in distinct},
    members=[[m.start, m.stop, m.attempt, m.chunk] for m in snapshot.members],
    checkpoint=snapshot.checkpoint, sink=sink, units=states(runtime, handles, workspace),
    session=getattr(runtime._records[relay].owner, "session_id", None))
barrier("cut")
hold()
"""

NATIVE_RECOVER = r"""
main_trust = (config["pin"], config["producer"], tuple(config["compatibility"]))
main_values = tuple(scalar_read(v).value for v in config["values"])
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
job, generation = config["job"], config["generation"]
runtime = rt.open_runtime(workspace.root, expected_identity=workspace.identity,
    policy=policy)
reconciled = runtime.reconcile()
latest = c.checkpoint_snapshot(workspace, job, generation)
recover = runtime.submit(unit(workspace, "RECOVER", job, generation, main_trust,
    main_values, source=source(route, 3), checkpoint=latest.checkpoint, interrupt=True,
    durable=16 * 1024 * 1024))
# Control under bounded downstream pressure on another job of this route.
pressure = bundle(config["pressure"])
l_job, l_generation = register(workspace, pressure[0], pressure[1], route)
handle = sk.create_sink(config["sink"], namespace=config["namespace"], epoch=1,
    retention_seconds=86400)
sink = [handle.root, handle.identity, handle.namespace, handle.epoch, handle.retention]
handle.close()
lock = sqlite3.connect(sink[0] + "/sink.sqlite", isolation_level=None, timeout=5)
lock.execute("BEGIN IMMEDIATE")
pressed = runtime.submit(unit(workspace, "RELAY", l_job, l_generation, pressure[2],
    pressure[1], source=source(route, 2), sink=rt.SinkTarget(*sink, 0.2), rows=2,
    batch_rows=2, durable=16 * 1024 * 1024))
waiting = runtime.wait_activity(pressed, "WAITING_FOR_DOWNSTREAM", 600)
high = dict(waiting.counters)
conflict = runtime.submit(unit(workspace, "CAPTURE", l_job, l_generation, pressure[2],
    pressure[1], source=source(route, 2), durable=1024 * 1024))
conflicted = runtime.wait(conflict, 600)
requested = time.monotonic_ns()
receipt = runtime.cancel(pressed)
signalled = time.monotonic_ns()
cancelled = runtime.wait(pressed, 600)
ended = time.monotonic_ns()
lock.execute("ROLLBACK")
lock.close()
recovered = runtime.wait(recover, 1800)
record = s.job_record(workspace, job)
after = c.checkpoint_snapshot(workspace, job, generation)
state = x.extraction_state(workspace, job, generation)
pressed_outcome = [a.outcome for a in s.job_record(workspace, l_job).attempts]
facts.update(reconciled=[list(r) for r in reconciled], predecessor=latest.checkpoint,
    recovered=[recovered.terminal, recovered.failure, dict(recovered.counters)],
    original=[record.attempts[0].terminal,
        None if record.attempts[0].outcome is None else dict(record.attempts[0].outcome)],
    closing=record.attempts[-1].identity,
    closing_outcome=None if record.attempts[-1].outcome is None
        else dict(record.attempts[-1].outcome),
    members=[[m.start, m.stop, m.attempt, m.chunk] for m in after.members],
    checkpoint=after.checkpoint, frontier=after.frontier, known=state.known,
    coverage=state.complete_coverage, pressure=[l_job, l_generation],
    high_water=high, conflict=[conflicted.terminal, conflicted.failure],
    cancel={"receipt": receipt["signal"], "terminal": cancelled.terminal,
        "durable": cancelled.durable_cancel, "requested_ns": requested,
        "signalled_ns": signalled, "ended_ns": ended,
        "outcome": [None if o is None else dict(o) for o in pressed_outcome],
        "job_state": s.job_record(workspace, l_job).state},
    units=states(runtime, [recover, pressed, conflict], workspace),
    verify=verify_store(workspace))
runtime.close()
workspace.close()
write_facts()
"""

NATIVE_SAVED = r"""
from pietto._project import project_job_capture as c, project_job_replay as r
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_runtime as rt, project_job_collection as col
from pietto._project import project_job_chunks as chunks
from pietto._project.project_compiled_schema import scalar_read
from pietto._project.project_job_store_verification import verify_store
import sqlite3, threading
def op():
    return s.new_operation()
def unit(workspace, mode, item, generation, job, **fields):
    return rt.Unit(mode=mode, root=workspace.root, workspace=workspace.identity,
        job=job, generation=generation,
        trust=(item["pin"], item["producer"], tuple(item["compatibility"])),
        values=tuple(scalar_read(v).value for v in item["values"]), seconds=3600,
        **fields)
def drain(runtime, handle):
    acked, wires, extents = set(), [], []
    while runtime.query(handle).terminal is None:
        got = runtime.take(handle, 1)
        if got is None or got.identity in acked:
            time.sleep(0.01)
            continue
        data = pa.record_batch(got.batch)
        columns = [data.column(i).to_pylist() for i in range(data.num_columns)]
        wires.extend([chunks.coordinate_wire(column[j]) for column in columns]
            for j in range(data.num_rows))
        extents.append([got.start, got.stop])
        acked.add(got.identity)
        runtime.ack(handle, got)
    return acked, wires, extents
results = []
for item in config["stores"]:
    out = {"key": item["key"]}
    workspace = w.open_workspace(item["workspace"], expected_identity=item["identity"])
    runtime = rt.open_runtime(workspace.root, expected_identity=workspace.identity,
        policy=rt.Policy(workers=3, connections=3))
    try:
        publishes = []
        targets = [(item, item["generation"], item["job"], item["closing"])] + [
            (item["trusts"][g], g, j, item["closings"][g]) for _k, j, g in item["distinct"]]
        for it, g, j, closing in targets:
            snap = c.checkpoint_snapshot(workspace, j, g)
            publishes.append(runtime.submit(unit(workspace, "PUBLISH", it, g, j,
                checkpoint=snap.checkpoint, closing=closing)))
        # Retire the separate unpublished contention generation and collect it
        # while the publications are being prepared.
        c_job, c_generation = item["contention"]
        holder = s.claim_publisher(workspace, c_job, operation=op())
        col.retire_generation(holder, c_generation, operation=op())
        holder.close()
        during = runtime.collect()
        published = [runtime.wait(h, 1800) for h in publishes]
        after = runtime.collect()
        reads = {}
        acked_all = set()
        for it, g, j, _closing in targets:
            snap = c.checkpoint_snapshot(workspace, j, g)
            h = runtime.submit(unit(workspace, "REPLAY", it, g, j,
                checkpoint=snap.checkpoint, extent=snap.frontier, rows=5, batch_rows=5))
            acked, wires, extents = drain(runtime, h)
            acked_all |= acked
            reads[g] = {"terminal": runtime.query(h).terminal, "wires": wires,
                "extents": extents}
            publishes.append(h)
        main = c.checkpoint_snapshot(workspace, item["job"], item["generation"])
        names = set(os.listdir(os.path.join(workspace.root, "chunks")))
        vectors = {row[0]: json.loads(row[4]) for row in workspace.use().execute(
            "SELECT * FROM admission")}
        units = {}
        for h in publishes:
            q = runtime.query(h)
            units[h] = {"events": [list(e) for e in q.events], "vector": vectors.get(h),
                "job": q.job, "generation": q.generation,
                "durable_cancel": q.durable_cancel, "settlement": q.settlement,
                "terminal": q.terminal, "failure": q.failure,
                "runtime": runtime.owner.epoch}
        out.update(published=[[q.terminal, q.failure] for q in published],
            during=[list(d) for d in during.decided], during_busy=list(during.busy),
            after=[list(d) for d in after.decided], removed=[list(x) for x in during.removed + after.removed],
            reads=reads, acked=sorted(acked_all), units=units,
            main_present=all(m.file in names for m in main.members),
            old_present=all(n + ".chunk" in names for n in item["old_members"]),
            verify=verify_store(workspace))
        backup = item["workspace"] + "-final.sqlite"
        with sqlite3.connect(backup) as copy:
            workspace.use().backup(copy)
        copy.close()
        out["backup"] = backup
    except Exception as error:
        out["error"] = type(error).__name__ + ":" + str(error)[:300]
    finally:
        runtime.close()
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

NATIVE_TUNING = r"""
from pietto._project import project_job_chunks as chunks
results = {}
for label, workers in (("baseline", 1), ("tuned", 3)):
    workspace = w.create_workspace(config["workspace"] + "-" + label, format=w.FORMAT_V7)
    jobs = []
    for item in config["items"]:
        t_, v_, tr_ = bundle(item)
        j_, g_ = register(workspace, t_, v_, route)
        jobs.append((item["key"], j_, g_, tr_, v_))
    runtime = rt.open_runtime(workspace.root, expected_identity=workspace.identity,
        policy=rt.Policy(workers=workers, connections=workers,
        durable=128 * 1024 * 1024))
    started = time.monotonic()
    handles = [runtime.submit(unit(workspace, "CAPTURE", j_, g_, tr_, v_,
        source=source(route, 2), durable=16 * 1024 * 1024))
        for _k, j_, g_, tr_, v_ in jobs]
    done = [runtime.wait(h, 1800) for h in handles]
    elapsed = time.monotonic() - started
    values = {}
    for key, j_, g_, tr_, _v in jobs:
        output = c.stored_output(workspace, j_, g_, expected_pin=tr_[0],
            accepted_producer=tr_[1], accepted_compatibility=tr_[2])
        snap = c.checkpoint_snapshot(workspace, j_, g_)
        wires = []
        with c.SnapshotReader(workspace, snap, output) as reader:
            for index in range(len(snap.members)):
                table = reader.read(index).table
                names = table.column_names
                wires.extend([[chunks.coordinate_wire(row[n]) for n in names]
                    for row in table.to_pylist()])
        values[key] = wires
    results[label] = {"elapsed": elapsed, "terminals": [q.terminal for q in done],
        "values": values, "units": states(runtime, handles, workspace),
        "verify": verify_store(workspace)}
    runtime.close()
    workspace.close()
facts["tuning"] = results
write_facts()
"""

# Distinctions per bundle cell (route, origin): ordinary seven-scalar values,
# ordinary and refined empty results and a guarded result, captured through
# the runtime beside the R2 relay and published later from an Arrow-only
# process (the S16 set, now through admitted claims and leases).
DISTINCT = s16.DISTINCT


def native(
    directory,
    ledger,
    capture_interpreter,
    saved_interpreter,
    *,
    target,
    cells,
    wheel=None,
):
    """Per route and (origin, entry) cell: (A) a native R2 relay held at its
    high-water by a stalled sink beside a mixed-route contention capture and
    (bundle) the S16 distinctions, all through one runtime, then SIGKILL; (B) a
    replacement runtime reconciles and RECOVERs with fresh qualification while
    another job's relay is cancelled under bounded downstream pressure and a
    same-job unit meets the real publisher lock; the source is then deleted;
    (C) an Arrow-only, driver-free runtime publishes and replays every result
    while collecting a separate retired generation."""
    import _pietto_phase68_slice10_probe as s10
    import _pietto_phase68_slice13_probe as r13
    import _pietto_phase68_slice14_probe as s14
    from _pietto_phase68_slice6_probe import manager, session_gone
    from _pietto_phase68_slice6_probe import setup as setup_general
    from _pietto_phase68_slice7_cases import manifest as guard_manifest
    from _pietto_phase68_slice7_probe import fill
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
        {"kind": "s17_native_start", "directory": str(directory), "target": target},
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
        s16.guard_sources(resource)
        bag = next(c for c in guard_manifest() if c["name"] == "bag_one")
        fill(
            resource,
            bag["lhs"],
            bag["rhs"],
            wide_text=bag["options"].get("wide_text", False),
        )
        if target == "mysql":
            for table in ("threads", "events_transactions_current"):
                manager(
                    resource,
                    "GRANT SELECT ON performance_schema."
                    + table
                    + " TO 'pietto_query'@'%'",
                )

        def bundle(reference_cell, name):
            reference = s10.build_native_reference(
                directory / (PREFIX + name + "-source"),
                target,
                reference_cell,
                providers,
            )
            if reference is None:
                raise ValueError("S17_NATIVE_REFERENCE:" + name)
            artifact, preparation, query, _output, _binding = reference
            built = build_compiled(artifact, guarded=preparation, refinement=query)
            path = directory / (PREFIX + name + "-bundle.json")
            path.write_bytes(built.payload)
            path.chmod(0o600)
            values = [
                scalar_wire(Scalar(v.tag.value, v.value)) for v in artifact.fixed_values
            ]
            return {
                "bundle": str(path),
                "pin": built.pin,
                "producer": built.producer,
                "compatibility": list(built.compatibility),
                "values": values,
            }

        main = bundle(cell, "reference")
        distinctions = {s16.label(d): bundle(d, s16.label(d)) for d in DISTINCT}
        ordinary = distinctions[s16.label(DISTINCT[0])]
        timings["preparation"] = time.monotonic() - mark
        common = {
            "target": target,
            "cell": cell,
            "providers": providers,
            "build_helpers": str(ROOT / "tests"),
            "library_source": str(ROOT / "src"),
            "port": resource.port,
            "password": resource._passwords[1],
            "ca_path": str(resource.ca_path) if target == "mysql" else None,
            "request_seconds": 900,
            **main,
        }

        def spawn(interpreter, name, program, config, *, cut=False):
            path = directory / (name + "-config.json")
            runtime_cwd = directory / (name + "-runtime")
            runtime_cwd.mkdir(mode=0o700)
            facts = directory / (name + "-facts.json")
            s16._write_private(
                path,
                {
                    **common,
                    **config,
                    "runtime_cwd": str(runtime_cwd),
                    "facts": str(facts),
                },
            )
            with (directory / (name + "-worker.log")).open("w") as log:
                child = s14._spawn(interpreter, program, path, ledger, log, name)
                try:
                    if cut:
                        until(child, "cut", 1800)
                        code, _ = kill(child)
                    else:
                        code = child.wait(timeout=3600)
                finally:
                    if child.poll() is None:
                        kill(child)
                    s14._reaped(ledger, child, child.returncode)
            path.unlink()
            if code != (-9 if cut else 0):
                raise ValueError("S17_NATIVE_WORKER:" + name + ":" + str(code))
            return json.loads(facts.read_text())

        for route in routes:
            other = (
                "postgres_adbc"
                if route == "postgres_rows"
                else "postgres_rows"
                if route == "postgres_adbc"
                else route
            )
            for origin, entry in cells:
                key = route + "-" + origin + "-" + entry
                name = PREFIX + key
                record: dict = {
                    "key": key,
                    "route": route,
                    "origin": origin,
                    "entry": entry,
                }
                report["histories"].append(record)
                items = []
                if entry == "bundle":
                    for d in DISTINCT:
                        items.append(
                            {
                                "key": key + "-" + s16.label(d),
                                **distinctions[s16.label(d)],
                            }
                        )
                mark = time.monotonic()
                captured = spawn(
                    capture_interpreter,
                    name + "-capture",
                    NATIVE_HEADER + NATIVE_CAPTURE,
                    {
                        "route": route,
                        "role": "capture",
                        "origin": origin,
                        "entry": entry,
                        "workspace": str(directory / (name + "-workspace")),
                        "sink": str(directory / (name + "-sink")),
                        "namespace": "s17.native." + key,
                        "live_project": str(directory / (name + "-source")),
                        "contention": ordinary,
                        "contention_route": other,
                        "distinctions": items,
                    },
                    cut=True,
                )
                s14._origin_check(captured, origin, wheel)
                if captured.get("session") is not None:
                    captured["session_gone"] = session_gone(
                        resource, captured["session"]
                    )
                record["capture"] = captured
                timings[key + ":capture"] = time.monotonic() - mark
                mark = time.monotonic()
                recovered = spawn(
                    capture_interpreter,
                    name + "-recover",
                    NATIVE_HEADER + NATIVE_RECOVER,
                    {
                        **{
                            k: captured[k]
                            for k in ("workspace", "identity", "job", "generation")
                        },
                        "route": route,
                        "role": "recover",
                        "origin": origin,
                        "entry": "bundle",
                        "pressure": ordinary,
                        "sink": str(directory / (name + "-pressure-sink")),
                        "namespace": "s17.pressure." + key,
                    },
                )
                s14._origin_check(recovered, origin, wheel)
                record["recover"] = recovered
                timings[key + ":recover"] = time.monotonic() - mark
                stores.append(
                    {
                        "key": key,
                        "origin": origin,
                        "workspace": captured["workspace"],
                        "identity": captured["identity"],
                        "job": captured["job"],
                        "generation": captured["generation"],
                        "closing": recovered["closing"],
                        "old_members": [m[3] for m in captured["members"]],
                        "contention": captured["contention"],
                        "distinct": captured["distinct"],
                        "closings": captured["closings"],
                        # Each distinction keeps its own bundle trust and values.
                        "trusts": {
                            g: distinctions[k[len(key) + 1 :]]
                            for k, _j, g in captured["distinct"]
                        },
                        **main,
                    }
                )
                report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        # Equal-guarantee tuning: the same real captures, serialized (workers=1)
        # and bounded-concurrent (workers=3), through the same runtime.
        mark = time.monotonic()
        report["tuning"] = spawn(
            capture_interpreter,
            PREFIX + "tuning",
            NATIVE_HEADER + NATIVE_TUNING,
            {
                "route": routes[0],
                "role": "tuning",
                "origin": "source",
                "entry": "bundle",
                "workspace": str(directory / (PREFIX + "tuning-workspace")),
                "items": [
                    {"key": s16.label(d), **distinctions[s16.label(d)]}
                    for d in DISTINCT
                ],
            },
        )
        s14._origin_check(report["tuning"], "source", None)
        timings["tuning"] = time.monotonic() - mark
        mark = time.monotonic()
        report["source_cleanup"] = resource.cleanup()
        timings["source_cleanup"] = time.monotonic() - mark
        mark = time.monotonic()
        for origin in sorted({o for o, _e in cells}):
            raw = directory / (PREFIX + "saved-" + origin + ".json")
            path = directory / (PREFIX + "saved-" + origin + "-config.json")
            s16._write_private(
                path,
                {
                    "runtime_cwd": str(directory),
                    "library_source": str(ROOT / "src"),
                    "origin": origin,
                    "raw": str(raw),
                    "stores": [s for s in stores if s["origin"] == origin],
                },
            )
            with (directory / (PREFIX + "saved-" + origin + ".log")).open("wb") as log:
                status = worker_process(
                    [
                        str(saved_interpreter),
                        "-I",
                        "-B",
                        "-c",
                        r13.REPLAY_HEADER + NATIVE_SAVED,
                        str(path),
                    ],
                    clean_environment(),
                    ledger,
                    log,
                    origin=origin,
                    group="s17-native-saved",
                    directory=directory,
                    seconds=3600,
                )
            path.unlink()
            if status:
                raise ValueError("S17_NATIVE_SAVED")
            data = json.loads(raw.read_text())
            s14._origin_check(data, origin, wheel)
            if (
                data["connections"]
                or data["loaded_drivers"]
                or data["installed_drivers"]
            ):
                raise ValueError("S17_NATIVE_SAVED_SOURCE_ACCESS")
            for result in data["results"]:
                for record in report["histories"]:
                    if record["key"] == result["key"]:
                        record["saved"] = result
        timings["saved"] = time.monotonic() - mark
        mark = time.monotonic()
        native_check(directory, target, report)
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
                "kind": "s17_native_terminal",
                "directory": str(directory),
                "status": report["status"],
                "cleanup": report["source_cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


def native_check(directory, target, report):
    """Independent judgement: literal oracles outside every worker, store
    history/publication/values (S16 checker over v7 rows), S17 laws over raw
    rows, files and runtime events, and coordinated damages of each route's
    first history."""
    import _pietto_phase68_slice15_check as s15check
    import _pietto_phase68_slice16_check as s16check
    import _pietto_phase68_slice17_check as check
    from _pietto_phase68_slice6_check import expected
    from _pietto_phase68_slice7_cases import manifest as guard_manifest

    def oracle(cell):
        if cell["group"] == "guarded":
            case = next(c for c in guard_manifest() if c["name"] == cell["case"])
            return s16check.encoded(case["rows"]), False
        return expected(target, cell["case"], cell["variant"], None)

    tuning = report["tuning"]["tuning"]
    baseline, tuned = tuning["baseline"], tuning["tuned"]
    check.need(
        baseline["terminals"] == ["COMPLETED"] * 4
        and tuned["terminals"] == ["COMPLETED"] * 4
        and baseline["values"] == tuned["values"],
        "TUNING_EQUALITY",
    )
    for cell_ in DISTINCT:
        literal_, ordered_ = oracle(cell_)
        decoded = [
            [s15check.decode_wire(v) for v in row]
            for row in tuned["values"][s16.label(cell_)]
        ]
        check.need(
            s16check.same_rows(decoded, literal_, ordered=ordered_), "TUNING_VALUES"
        )
    peaks = {}
    for label_, part in (("baseline", baseline), ("tuned", tuned)):
        workers_ = 1 if label_ == "baseline" else 3
        peaks[label_] = check.check_events(
            part["units"],
            {
                "connections": workers_,
                "workers": workers_,
                "memory": 512 * 1024 * 1024,
                "durable": 128 * 1024 * 1024,
                "operations": 65536,
            },
        )
    check.need(peaks["baseline"]["connections"] == 1, "TUNING_BASELINE")
    report["tuning_summary"] = {
        "baseline_seconds": baseline["elapsed"],
        "tuned_seconds": tuned["elapsed"],
        "peaks": peaks,
    }
    damaged = set()
    for record in report["histories"]:
        captured, recovered, saved = (
            record["capture"],
            record["recover"],
            record["saved"],
        )
        check.need("error" not in saved, "NATIVE_SAVED")
        check.need(
            captured["blocked"][0] == "WAITING_FOR_DOWNSTREAM"
            and captured["still"] == captured["blocked"]
            and all(t == "COMPLETED" for t, _f in captured["others"]),
            "NATIVE_HIGH_WATER",
        )
        check.need(
            recovered["recovered"][0] == "COMPLETED"
            and recovered["original"][0] == "INTERRUPTED"
            and recovered["original"][1]["transaction"] == "UNKNOWN"
            and recovered["coverage"],
            "NATIVE_R2",
        )
        check.need(
            recovered["conflict"][0] == "FAILED"
            and "PUBLISHER_BUSY" in str(recovered["conflict"][1]),
            "NATIVE_SAME_JOB",
        )
        cancel = recovered["cancel"]
        check.need(
            cancel["terminal"] == "CANCELLED"
            and cancel["durable"] == "COMMITTED"
            and cancel["job_state"] == "CANCELLED"
            and cancel["receipt"]["requested"],
            "NATIVE_CANCEL",
        )
        check.need(
            all(t == "COMPLETED" for t, _f in saved["published"])
            and saved["main_present"]
            and saved["old_present"]
            and (saved["during"] or saved["after"]),
            "NATIVE_SAVED_GC",
        )
        literal, ordered = oracle(
            {"group": "refined", "case": "R2_seven", "variant": "39_values"}
        )
        main = saved["reads"][captured["generation"]]
        decoded = [[s15check.decode_wire(v) for v in row] for row in main["wires"]]
        check.need(
            main["terminal"] == "COMPLETED"
            and s16check.same_rows(decoded, literal, ordered=ordered),
            "NATIVE_READ_VALUES",
        )
        for key, _job, generation in captured["distinct"]:
            cell_ = next(d for d in DISTINCT if key.endswith(s16.label(d)))
            literal_, ordered_ = oracle(cell_)
            got = saved["reads"][generation]
            decoded = [[s15check.decode_wire(v) for v in row] for row in got["wires"]]
            check.need(
                got["terminal"] == "COMPLETED"
                and s16check.same_rows(decoded, literal_, ordered=ordered_),
                "NATIVE_DISTINCT_VALUES",
            )
        data = check.load(saved["backup"])
        units = {
            h: u
            for part in (captured["units"], recovered["units"], saved["units"])
            for h, u in part.items()
            if u["vector"] is not None
        }
        evidence = {
            "data": data,
            "units": units,
            "policy": {
                "connections": 3,
                "workers": 3,
                "memory": 512 * 1024 * 1024,
                "durable": 128 * 1024 * 1024,
                "operations": 65536,
            },
            "files": check.inventory(captured["workspace"]),
            "killed": [captured["attempt"]],
            "acked": set(saved["acked"]),
        }
        record["checked"] = check.check_all(evidence)
        if record["route"] not in damaged:
            damaged.add(record["route"])
            record["damages"] = {
                kind: check.rejects(kind, evidence)
                for kind in check.DAMAGES
                if kind
                not in (
                    "D07_stale_snapshot_read",
                    "D10_replacement_object",
                    "D11_credited_not_removed",
                    "D14_promoted_unlink",
                )
            }
    return report
