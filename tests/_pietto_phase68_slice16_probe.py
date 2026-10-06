"""S16 publication fixtures and explicit bounded families; import acquires nothing.

Ordinary tests have no Arrow and no database. Saved inputs use S12/S13's
labelled ARROW_FREE_STORAGE_STEP (and S14's SYNTHETIC_OPEN_OWNER /
ARROW_FREE_PAGE_STEP for R2). A closing owner is a real compiled owner that
never connects: SYNTHETIC_CLOSED_OWNER sets only the terminal fields a route
sets at its end (with a labelled qualification and transaction context), and
the publication member check is ARROW_FREE_MEMBER_CHECK (bounded bytes, digest,
exact descriptor and the file object across the read; no IPC value decode).
record_attempt, the closing observation, retention, every fence, the
publication transaction, lookups and the independent verifier run for real.
Real checked Arrow members, native closing owners and source-free reads run only
in the execution-profile families.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import os
import sys

import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice13_probe as s13

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice16-"
op = s12.op
SIMULATED_QUALIFICATION = "SIMULATED_QUALIFICATION"
SIMULATED_CONTEXT = ("SIMULATED_CONTEXT",)


def store(root, template, values=(1,), **options):
    """A v6 workspace with one job, publisher, binding and generation."""
    from pietto._project import project_job_workspace as w

    return s12.store(root, template, values, format=w.FORMAT_V6, **options)


def close_owner(
    owner,
    rows,
    *,
    source="EOF",
    transaction="COMMIT_ACK",
    delivery="COMPLETE",
    cleanup="CLOSED",
    primary=None,
    cleanup_errors=(),
    qualified=True,
    opened=True,
    guards=None,
    cancel=(False, False, False),
):
    """SYNTHETIC_CLOSED_OWNER: the terminal fields a route sets at its end."""
    from pietto._project.project_execution import ExecutionFailure

    owner._payloads = SimpleNamespace(rows=rows, batches=1 if rows else 0, bytes=0)
    owner._source, owner._transaction = source, transaction
    owner._delivery, owner._cleanup = delivery, cleanup
    owner._primary = None if primary is None else ExecutionFailure(*primary)
    owner._cleanup_errors = [ExecutionFailure(*item) for item in cleanup_errors]
    owner._qualification = SIMULATED_QUALIFICATION if qualified else None
    owner.context = SIMULATED_CONTEXT if opened else None
    owner.guards = None if guards is None else SimpleNamespace(states=tuple(guards))
    if cancel[0]:
        owner._cancel.set()
    owner._cancel_sent, owner._cancel_observed = cancel[1], cancel[2]
    owner._closed = True
    return owner


def arrow_free_verify(workspace, acceptance, snapshot):
    """ARROW_FREE_MEMBER_CHECK: bounded bytes, digest, exact descriptor and the
    file object across the read; the IPC value decode is not exercised."""
    from pietto._project import project_job_chunks as k
    from pietto._project import project_job_publication as p
    from pietto._project.project_job_workspace import CHUNKS, JobStoreError

    files = []
    directory = workspace.directory(CHUNKS)
    try:
        for member in snapshot.members:
            before = p._object(directory, member)
            data = k.read_chunk_file(
                directory, member.file, member.bytes, member.digest
            )
            text, descriptor, _frame = k.decode_chunk(data)
            if text != member.descriptor or descriptor["attempt"] != member.attempt:
                raise JobStoreError("CHUNK_DESCRIPTOR")
            if p._object(directory, member) != before:
                raise JobStoreError("CHUNK_OBJECT")
            files.append(before)
    finally:
        os.close(directory)
    return tuple(files)


def arrow_free(monkeypatch=None):
    """Install the labelled Arrow-free member check and S13 replay step."""
    from pietto._project import project_job_publication as p

    s13.arrow_free(monkeypatch)
    if monkeypatch is None:
        p._verify = arrow_free_verify
    else:
        monkeypatch.setattr(p, "_verify", arrow_free_verify)


def ordinary(publisher, generation, binding, sizes, *, order=None, end=True, **close):
    """An ordinary capture of ARROW_FREE_STORAGE_STEP chunks; with `end` its
    owner is closed (SYNTHETIC_CLOSED_OWNER over the observed rows), the capture
    end and the attempt outcome (with its v6 closing observation) recorded."""
    from pietto._project import project_job_store as s

    session = s12.capture(publisher.use(), publisher, generation, binding)
    staged = [s12.stage_frame(session, rows) for rows in sizes]
    if not sizes:
        staged = [s12.stage_frame(session, 0, terminal="EOF")]
    for index in range(len(staged)) if order is None else order:
        session.publish(staged[index], operation=op())
    if end:
        close_owner(session.owner, session.observed, **close)
        session.end(operation=op())
        s.record_attempt(publisher, session.attempt, session.owner, operation=op())
    return session


def accept(workspace, job, generation, built, closing, *, values=(1,), **overrides):
    """A fresh publication acceptance for the generation's latest checkpoint."""
    from pietto._project import project_job_capture as c
    from pietto._project import project_job_publication as p

    arguments = {
        "checkpoint": c.checkpoint_snapshot(workspace, job, generation).checkpoint,
        "closing": closing,
        "purpose": "s16-publish",
        "route": "postgres_rows",
        "isolation": "stable",
        "values": values,
        "seconds": 600,
        **s13.trust(built),
    }
    arguments.update(overrides)
    return p.accept_publication(workspace, job, generation, **arguments)


def publish(workspace, job, publisher, generation, built, closing, **overrides):
    """Accept, prepare and publish; returns (prepared, operation, result)."""
    from pietto._project import project_job_publication as p

    acceptance = accept(workspace, job, generation, built, closing, **overrides)
    prepared = p.prepare_publication(publisher, acceptance, operation=op())
    operation = op()
    return (
        prepared,
        operation,
        p.publish_generation(publisher, prepared, operation=operation),
    )


def finish_continuation(session, **close):
    """The continuation owner's normal end (SYNTHETIC_CLOSED_OWNER over every
    re-enumerated row), its stream close, end and attempt outcome."""
    from pietto._project import project_job_store as s

    close_owner(session.owner, session.observed, **close)
    session._terminal = "EOF" if close.get("source", "EOF") == "EOF" else None
    staged = session._close_stream(session.publisher.use())
    if session.ready and not session.reconciled:
        session.reconcile(operation=op())
    for item in staged or ():
        session.publish(item, operation=op())
    ended = session.end(operation=op())
    s.record_attempt(session.publisher, session.attempt, session.owner, operation=op())
    return ended


def rows(workspace, sql, parameters=()):
    return workspace.use().execute(sql, parameters).fetchall()


CHILD_HEADER = r"""
import json, os, signal, sys, time
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[3])
config = json.loads(sys.argv[2])
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c
from pietto._project import project_job_publication as p
import _pietto_phase68_slice16_probe as probe
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

def attach(*, claim=True):
    workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
    publisher = None
    if claim:
        publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
    return workspace, publisher

def acceptance(workspace):
    return p.accept_publication(workspace, config["job"], config["generation"],
        checkpoint=config["checkpoint"], closing=config["closing"], purpose="s16-child",
        route="postgres_rows", isolation="stable", values=tuple(config["values"]),
        expected_pin=config["pin"], accepted_producer=config["producer"],
        accepted_compatibility=tuple(config["compatibility"]), seconds=600)
"""


def child(program, config, *, stdout=None):
    """A spawned isolated child (fresh interpreter, no inherited handles); the
    caller must reap it."""
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
        stdout=subprocess.PIPE if stdout is None else stdout,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/",
    )


def child_config(workspace, job, generation, built, closing, checkpoint, **extra):
    return {
        "workspace": workspace.root,
        "identity": workspace.identity,
        "job": job,
        "generation": generation,
        "closing": closing,
        "checkpoint": checkpoint,
        "pin": built.pin,
        "producer": built.producer,
        "compatibility": list(built.compatibility),
        "values": [1],
        **extra,
    }


# ---------------------------------------------------------------------------
# Execution-profile families (Arrow present). Nothing runs at import.

# name -> (precision, simulated native batches as S12 SEVEN row indexes or
# "LATE", expected publication outcome)
SUITE_CASES = {
    "seven39": (39, [[0, 1], [2, 3], [4]], "PUBLISHED"),
    "seven65": (65, [[0, 1], [2]], "PUBLISHED"),
    "seven7": (39, [[0, 1], [2, 3], [4, 0], [1]], "PUBLISHED"),
    "empty": (39, [], "PUBLISHED"),
    "late": (39, [[0, 1], "LATE"], "PUBLICATION_SOURCE"),
}
# Product-side member checks over real Arrow members, before any visibility.
MEMBER_DAMAGES = {
    "late_digest": "CHUNK_DIGEST",
    "swapped_members": "CHUNK_DESCRIPTOR",
    "out_of_meaning": None,
    "copied_query": "CHUNK_DESCRIPTOR",
    "empty_schema": None,
}

WORKER_HEADER = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, os, hashlib, shutil, sqlite3
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["runtime_cwd"])
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
sys.path.append(config["tests"])
from pietto._project import project_job_capture as c, project_job_store as s
from pietto._project import project_job_workspace as w, project_job_publication as p
from pietto._project import project_job_replay as r, project_job_chunks as k
from pietto._project.project_job_store_verification import verify_store
import _pietto_phase68_slice16_probe as probe
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

CAPTURE = r"""
import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice12_check as k12
import _pietto_phase68_slice16_check as k16
import pyarrow as pa
base = Path(config["directory"])
templates = {q: s12.seven_template(base / ("build-" + str(q)), precision=q)
    for q in (39, 65)}

def closed(name, precision, spec):
    source = s12.SEVEN65_ROWS if precision == 65 else s12.SEVEN_ROWS
    batches = [[s12.LATE_INVALID] if b == "LATE" else [source[i] for i in b]
        for b in spec]
    template, built = templates[precision]
    workspace, job, publisher, binding, record, generation = s12.store(
        base / (name + "-workspace"), template, format=w.FORMAT_V6)
    attempt, owner = s12.attempt_owner(publisher, generation, binding,
        s12.Plan(batches, s12.SEVEN_CODES), None)
    capture = c.begin_capture(publisher, attempt, owner, operation=op())
    failure = None
    try:
        while True:
            staged = capture.stage()
            if staged is None:
                break
            capture.publish(staged, operation=op())
    except Exception as error:
        failure = type(error).__name__ + ":" + str(error)
    # SIMULATED_NATIVE_IO does not observe source qualification or the
    # transaction context; the labelled values stand in for them here only.
    owner._qualification = probe.SIMULATED_QUALIFICATION
    owner.context = probe.SIMULATED_CONTEXT
    capture.end(operation=op())
    s.record_attempt(publisher, attempt, owner, operation=op())
    return workspace, job, publisher, generation, attempt.identity, built, failure

def accept(workspace, job, generation, closing, built):
    checkpoint = c.checkpoint_snapshot(workspace, job, generation).checkpoint
    return p.accept_publication(workspace, job, generation, checkpoint=checkpoint,
        closing=closing, purpose="s16-suite", route="postgres_rows",
        isolation="stable", values=(), expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility, seconds=3600)

def rows(workspace, generation):
    return workspace.use().execute(
        "SELECT identity, file, bytes, digest, descriptor FROM chunk"
        " WHERE generation = ? ORDER BY start", (generation,)).fetchall()

def reframe(frame, table):
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        for batch in table.to_batches():
            writer.write_batch(batch)
    payload = sink.getvalue().to_pybytes()
    head = k12.FRAME.unpack_from(frame)
    return k12.FRAME.pack(head[0], head[1], head[2], len(payload), head[4],
        hashlib.sha256(payload).digest()) + payload

def damage(kind, workspace, generation, other):
    root, store = Path(workspace.root), Path(workspace.root) / "store.sqlite"
    found = rows(workspace, generation)
    if kind == "late_digest":
        path = root / "chunks" / found[-1][1]
        data = bytearray(path.read_bytes())
        data[-1] ^= 1
        path.write_bytes(bytes(data))
    elif kind == "swapped_members":
        a, b = found[0], found[1]
        da = (root / "chunks" / a[1]).read_bytes()
        db = (root / "chunks" / b[1]).read_bytes()
        (root / "chunks" / a[1]).write_bytes(db)
        (root / "chunks" / b[1]).write_bytes(da)
        with sqlite3.connect(store) as raw:
            raw.execute("UPDATE chunk SET bytes = ?, digest = ?, descriptor = ?"
                " WHERE identity = ?", (b[2], b[3], b[4], a[0]))
            raw.execute("UPDATE chunk SET bytes = ?, digest = ?, descriptor = ?"
                " WHERE identity = ?", (a[2], a[3], a[4], b[0]))
        raw.close()
    elif kind in ("out_of_meaning", "empty_schema"):
        last = found[-1]
        _t, descriptor, frame = k12.parse_chunk((root / "chunks" / last[1]).read_bytes())
        rows_ = descriptor["rows"]
        table = k12.decode_frame(frame, rows_, descriptor["contract"])[1]
        if kind == "out_of_meaning":
            column = table.column(0).to_pylist()
            column[-1] = s12.LATE_INVALID[0]
            table = table.set_column(0, table.schema.field(0),
                pa.array(column, table.schema.field(0).type))
        else:
            table = table.rename_columns(["renamed"] + table.column_names[1:])
        k16._rewrite(root, store, last[0], reframe(frame, table))
    elif kind == "copied_query":
        donor = rows(other[0], other[1])[0]
        data = (Path(other[0].root) / "chunks" / donor[1]).read_bytes()
        (root / "chunks" / found[0][1]).write_bytes(data)
        with sqlite3.connect(store) as raw:
            raw.execute("UPDATE chunk SET bytes = ?, digest = ?, descriptor = ?"
                " WHERE identity = ?", (donor[2], donor[3], donor[4], found[0][0]))
        raw.close()

cases = {}
for name, (precision, spec, expect) in config["cases"].items():
    workspace, job, publisher, generation, closing, built, failure = closed(
        name, precision, spec)
    out = {"workspace": str(workspace.root), "identity": workspace.identity,
        "job": job, "generation": generation, "closing": closing,
        "pin": built.pin, "producer": built.producer,
        "compatibility": list(built.compatibility), "failure": failure}
    try:
        prepared = p.prepare_publication(publisher,
            accept(workspace, job, generation, closing, built), operation=op())
        operation = op()
        result = p.publish_generation(publisher, prepared, operation=operation)
        out["published"] = {"operation": operation, "observation": result.observation,
            **dict(result.result)}
    except Exception as error:
        out["refused"] = type(error).__name__ + ":" + str(error)
    found = p.publication(workspace, job, generation)
    out["recorded"] = None if found is None else [found.checkpoint, found.extent,
        found.members, found.closing, found.retention, found.operation]
    out["verify"] = verify_store(workspace)
    publisher.close()
    workspace.close()
    cases[name] = out
damages = {}
donor = closed("donor65", 65, [[0, 1], [2]])
for kind in config["damages"]:
    precision, spec = (39, []) if kind == "empty_schema" else (39, [[0, 1], [2, 3], [4]])
    workspace, job, publisher, generation, closing, built, failure = closed(
        "damage-" + kind, precision, spec)
    damage(kind, workspace, generation, (donor[0], donor[3]))
    try:
        p.prepare_publication(publisher,
            accept(workspace, job, generation, closing, built), operation=op())
        damages[kind] = "ACCEPTED"
    except Exception as error:
        damages[kind] = type(error).__name__ + ":" + str(error)
    released = workspace.use().execute(
        "SELECT count(*) FROM retention_release").fetchone()[0]
    damages[kind] = [damages[kind], released,
        p.publication(workspace, job, generation) is None]
    publisher.close()
    workspace.close()
donor[2].close()
donor[0].close()
write({"cases": cases, "damages": damages})
"""

READ = r"""
from pietto._project import project_job_chunks as chunks
import pyarrow as pa
results = {}
for name, case in config["cases"].items():
    workspace = w.open_workspace(case["workspace"], expected_identity=case["identity"])
    publisher = s.claim_publisher(workspace, case["job"], operation=op())
    found = p.publication(workspace, case["job"], case["generation"])
    acceptance = r.accept_saved_read(workspace, case["job"], case["generation"],
        checkpoint=found.checkpoint, consumer=r.new_consumer(), scope="complete_capture",
        extent=found.extent, purpose="s16-suite-read", route="postgres_rows", values=(),
        expected_pin=case["pin"], accepted_producer=case["producer"],
        accepted_compatibility=tuple(case["compatibility"]), seconds=3600,
        batch_rows=4096)
    r.register_consumer(publisher, acceptance, operation=op())
    replay = r.open_replay(publisher, acceptance, operation=op())
    wires, extents = [], []
    while True:
        got = replay.next(2, operation=op())
        if isinstance(got, r.SavedScopeEnd):
            end = [got.terminal, got.acknowledged, got.extent]
            break
        data = pa.record_batch(got.batch)
        columns = [data.column(i).to_pylist() for i in range(data.num_columns)]
        wires.extend([chunks.coordinate_wire(column[j]) for column in columns]
            for j in range(data.num_rows))
        extents.append([got.start, got.stop])
        replay.acknowledge(got, operation=op())
        got.batch.close()
    replay.close()
    results[name] = {"recorded": [found.checkpoint, found.extent, found.integrity],
        "wires": wires, "extents": extents, "end": end,
        "verify": verify_store(workspace)}
    publisher.close()
    workspace.close()
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
            group="s16-" + name,
            directory=directory,
            seconds=1800,
        )
    if status:
        raise ValueError("S16_WORKER:" + name)
    data = json.loads(raw.read_text())
    _origin_check(data, origin, wheel)
    return data


def old_runtime(directory, ledger, interpreter, old_wheel):
    """The published S15 workspace owner (archived wheel bytes) meets a v6
    workspace: it must refuse before SQLite and leave the directory unchanged."""
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_target_conformance_resources import clean_environment
    from pietto._project import project_job_workspace as w

    root = directory / (PREFIX + "v6-workspace")
    workspace = w.create_workspace(str(root), format=w.FORMAT_V6)
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
            origin="archived-s15-wheel",
            group="s16-old-runtime",
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
        raise ValueError("S16_OLD_RUNTIME_ACCEPTED_V6")
    return data


def literal_rows(precision, spec) -> list[tuple]:
    """The S12 literal fixture rows a suite case delivered (outside workers)."""
    source = s12.SEVEN65_ROWS if precision == 65 else s12.SEVEN_ROWS
    return [source[i] for batch in spec if batch != "LATE" for i in batch]


def suite(directory, ledger, interpreter, *, origin, wheel=None, old_wheel=None):
    """Arrow-profile publication without a source database: simulated native IO
    (real S10 checks, Arrow, IPC and chunks), closing observations, publication
    after a real member check, a fresh-process S13 read of the published
    reference, product-side member damages, independent checks and the
    archived S15 runtime's refusal of v6."""
    import _pietto_phase68_slice15_check as s15check
    import _pietto_phase68_slice16_check as check

    directory.mkdir(mode=0o700)
    common = {
        "runtime_cwd": str(directory),
        "library_source": str(ROOT / "src"),
        "tests": str(ROOT / "tests"),
        "origin": origin,
        "directory": str(directory),
    }
    captured = _run_worker(
        directory,
        ledger,
        interpreter,
        CAPTURE,
        {**common, "cases": SUITE_CASES, "damages": list(MEMBER_DAMAGES)},
        "capture",
        origin,
        wheel,
    )
    published = {n: c for n, c in captured["cases"].items() if "published" in c}
    read = _run_worker(
        directory,
        ledger,
        interpreter,
        READ,
        {**common, "cases": published},
        "read",
        origin,
        wheel,
    )
    report: dict = {"status": "CHECKING", "origin": origin, "cases": {}}
    for name, (precision, spec, expect) in SUITE_CASES.items():
        case = captured["cases"][name]
        stored = directory / (PREFIX + name + "-store-backup.sqlite")
        backup_store(case["workspace"], case["identity"], stored)
        oracle = check.encoded(literal_rows(precision, spec))
        if expect == "PUBLISHED":
            checked = check.check_store(
                stored, case["workspace"], case["generation"], oracle, ordered=True
            )
            got = read["cases"][name]
            decoded = [[s15check.decode_wire(v) for v in row] for row in got["wires"]]
            check.need(check.encoded(decoded) == oracle, "SUITE_READ_VALUES")
            check.need(
                got["end"]
                == ["SAVED_SCOPE_EXHAUSTED", checked["extent"], checked["extent"]]
                and got["recorded"][2] == "RECORDED",
                "SUITE_READ_END",
            )
            report["cases"][name] = {
                "published": case["published"]["observation"],
                "extent": checked["extent"],
                "members": checked["members"],
                "basis": checked["basis"],
                "read_extents": got["extents"],
            }
        else:
            check.need(
                case["refused"].endswith(":" + expect) and case["recorded"] is None,
                "SUITE_REFUSAL",
            )
            history = check.check_history(check.load(stored))
            report["cases"][name] = {
                "refused": expect,
                "failure": case["failure"],
                **history,
            }
    damages = captured["damages"]
    for kind, code in MEMBER_DAMAGES.items():
        refused, released, absent = damages[kind]
        check.need(
            refused != "ACCEPTED"
            and (code is None or refused.endswith(":" + code))
            and released == 1
            and absent,
            "SUITE_MEMBER_DAMAGE",
        )
    report["damages"] = {kind: damages[kind][0] for kind in MEMBER_DAMAGES}
    if old_wheel is not None:
        report["old_runtime"] = old_runtime(directory, ledger, interpreter, old_wheel)
    report["status"] = "PASS"
    _write_private(directory / (PREFIX + "suite-report.json"), report)
    return report


# ---------------------------------------------------------------------------
# Native joined histories (pinned native capture/R2 profile + Arrow-only
# publication profile). Nothing runs at import.

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
from pietto._project import project_job_publication as p
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
def closing_rows(workspace):
    return [list(r) for r in workspace.use().execute(
        "SELECT * FROM closing_observation").fetchall()]
def outcome_of(workspace, job, attempt):
    for item in s.job_record(workspace, job).attempts:
        if item.identity == attempt:
            return [item.terminal, None if item.outcome is None else dict(item.outcome)]
trust = dict(expected_pin=config["pin"], accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]))
values = tuple(scalar_read(v).value for v in config["values"])
window = dict(purpose="s16-native", route=route, values=values, seconds=3600,
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
    workspace = w.create_workspace(config["workspace"], format=w.FORMAT_V6)
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
        epoch=1, retention=handle.retention, purpose="s16-native", seconds=3600)
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
                "observed": capture.observed, "position": session.position}
        if step == "DELIVERED":
            delivered += 1
        if step in ("SOURCE_TERMINAL", "BLOCKED"):
            break
    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    facts.update(workspace=workspace.root, identity=workspace.identity, job=job,
        generation=generation, record=record, attempt=attempt.identity,
        session=owner.session_id, stream=stream, sink=handle.root,
        sink_identity=handle.identity, namespace=handle.namespace,
        steps=steps, first=first, members=members(snapshot),
        checkpoint=snapshot.checkpoint, frontier=snapshot.frontier,
        position=session.position, sink_rows=sink_rows(handle))
    barrier("cut")
    hold()
if role == "distinct":
    results = {}
    for item in config["distinctions"]:
        item_trust = dict(expected_pin=item["pin"], accepted_producer=item["producer"],
            accepted_compatibility=tuple(item["compatibility"]))
        item_values = tuple(scalar_read(v).value for v in item["values"])
        template = prepare_compiled_template(load_compiled(
            Path(item["bundle"]).read_bytes(), **item_trust))
        workspace = w.create_workspace(item["workspace"], format=w.FORMAT_V6)
        binding = bind_values(template, tuple(zip(template.slots, item_values,
            strict=True)))
        job = s.register_job(workspace, template, operation=op()).get("job")
        publisher = s.claim_publisher(workspace, job, operation=op())
        record = s.register_binding(publisher, binding, operation=op()).get("binding")
        generation = s.register_generation(publisher, record, binding, route=route,
            isolation="stable", operation=op()).get("generation")
        attempt = s.open_attempt(publisher, generation, binding, operation=op())
        owner = owner_for(binding)
        owner.open()
        capture = c.begin_capture(publisher, attempt, owner, operation=op())
        failure = None
        try:
            while True:
                staged = capture.stage()
                if staged is None:
                    break
                capture.publish(staged, operation=op())
        except Exception as error:
            failure = type(error).__name__ + ":" + str(error)[:300]
        finally:
            owner.close()
        ended = capture.end(operation=op())
        s.record_attempt(publisher, attempt, owner, operation=op())
        snapshot = c.checkpoint_snapshot(workspace, job, generation)
        results[item["key"]] = {"workspace": workspace.root,
            "identity": workspace.identity, "job": job, "generation": generation,
            "closing": attempt.identity, "checkpoint": snapshot.checkpoint,
            "failure": failure, "end": dict(ended.result),
            "outcome": outcome_of(workspace, job, attempt.identity),
            "closing_rows": closing_rows(workspace), "members": members(snapshot),
            "session": owner.session_id, "verify": verify_store(workspace)}
        publisher.close()
        workspace.close()
    facts["results"] = results
    write_facts()
    raise SystemExit(0)
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
job, generation = config["job"], config["generation"]
publisher = s.claim_publisher(workspace, job, operation=op())
for item in s.job_record(workspace, job).attempts:
    if item.terminal is None:
        s.interrupt_attempt(publisher, item.identity, operation=op())
latest = c.checkpoint_snapshot(workspace, job, generation)
facts.update(predecessor=latest.checkpoint, before=members(latest))
# Before R2 the only closing candidate is the interrupted original: refused.
try:
    p.prepare_publication(publisher, p.accept_publication(workspace, job, generation,
        checkpoint=latest.checkpoint, closing=config["relay_attempt"],
        purpose="s16-native-early", route=route, isolation="stable", values=values,
        seconds=3600, **trust), operation=op())
    facts["before_r2"] = "PREPARED"
except w.JobStoreError as error:
    facts["before_r2"] = str(error)
facts["before_r2_releases"] = workspace.use().execute(
    "SELECT count(*) FROM retention_release").fetchone()[0]
acceptance = x.accept_recovery(workspace, job, generation, checkpoint=latest.checkpoint,
    purpose="s16-native-r2", values=values, seconds=3600, **trust)
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
    coverage=state.complete_coverage, closing=attempt.identity,
    outcome=outcome_of(workspace, job, attempt.identity),
    original=outcome_of(workspace, job, config["relay_attempt"]),
    closing_rows=closing_rows(workspace), verify=verify_store(workspace))
publisher.close()
workspace.close()
write_facts()
"""

PUBLISH = r"""
from pietto._project import project_job_capture as c, project_job_replay as r
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_publication as p, project_job_chunks as chunks
from pietto._project import project_job_delivery as d
from pietto._project.project_compiled_schema import scalar_read
from pietto._project.project_job_store_verification import verify_store
def op():
    return s.new_operation()
def coordinate_damage(item):
    # A private copy whose first refined member loses one coordinate (coherent
    # bytes, digest and descriptor): refused before any visibility.
    root = Path(item["workspace"] + "-coordinate-copy")
    shutil.copytree(item["workspace"], root)
    for name in os.listdir(root):
        if name.endswith(("-wal", "-shm")):
            raise RuntimeError("unexpected live WAL in a closed store")
    store = root / "store.sqlite"
    connection = sqlite3.connect(store)
    chunk, name = connection.execute("SELECT identity, file FROM chunk WHERE"
        " generation = ? AND stop > start ORDER BY start LIMIT 1",
        (item["generation"],)).fetchone()
    connection.close()
    data = (root / "chunks" / name).read_bytes()
    head = struct.unpack(">16sQQ32s", data[:64])
    body = data[64:]
    descriptor = json.loads(body[:head[1]])
    frame = body[head[1]:]
    descriptor["coordinates"][0] = descriptor["coordinates"][0][:-1]
    raw = json.dumps(descriptor, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode()
    body = raw + frame
    data = struct.pack(">16sQQ32s", head[0], len(raw), len(frame),
        hashlib.sha256(body).digest()) + body
    (root / "chunks" / name).write_bytes(data)
    connection = sqlite3.connect(store)
    connection.execute("UPDATE chunk SET bytes = ?, digest = ?, descriptor = ?"
        " WHERE identity = ?", (len(data), hashlib.sha256(data).hexdigest(),
        raw.decode(), chunk))
    connection.commit()
    connection.close()
    copy = w.open_workspace(str(root), expected_identity=item["identity"])
    publisher = s.claim_publisher(copy, item["job"], operation=op())
    try:
        p.prepare_publication(publisher, accept(copy, item, None), operation=op())
        return "PREPARED"
    except Exception as error:
        return type(error).__name__ + ":" + str(error)
    finally:
        publisher.close()
        copy.close()
        shutil.rmtree(root)
def accept(workspace, item, checkpoint):
    vals = tuple(scalar_read(v).value for v in item["values"])
    if checkpoint is None:
        checkpoint = c.checkpoint_snapshot(workspace, item["job"],
            item["generation"]).checkpoint
    return p.accept_publication(workspace, item["job"], item["generation"],
        checkpoint=checkpoint, closing=item["closing"], purpose="s16-native-publish",
        route=item["route"], isolation="stable", values=vals, seconds=3600,
        expected_pin=item["pin"], accepted_producer=item["producer"],
        accepted_compatibility=tuple(item["compatibility"]))
import shutil, sqlite3, struct, time
results = []
for item in config["stores"]:
    out = {"key": item["key"]}
    try:
        if item.get("coordinate_damage"):
            out["coordinate_damage"] = coordinate_damage(item)
        workspace = w.open_workspace(item["workspace"], expected_identity=item["identity"])
        publisher = s.claim_publisher(workspace, item["job"], operation=op())
        try:
            if item.get("older"):
                try:
                    p.prepare_publication(publisher, accept(workspace, item, item["older"]),
                        operation=op())
                    out["older"] = "PREPARED"
                except Exception as error:
                    out["older"] = type(error).__name__ + ":" + str(error)
            stream = None
            if item.get("stream"):
                stream = d.stream_state(workspace, item["stream"])
            mark = time.monotonic()
            prepared = p.prepare_publication(publisher, accept(workspace, item, None),
                operation=op())
            prepared_at = time.monotonic()
            operation = op()
            result = p.publish_generation(publisher, prepared, operation=operation)
            found = p.publication(workspace, item["job"], item["generation"])
            queried = s.query_operation(workspace, operation)
            published_at = time.monotonic()
            out["published"] = {"observation": result.observation,
                "operation": operation, "queried": queried.kind,
                "recorded": [found.checkpoint, found.extent, found.members,
                    found.closing, found.retention, found.integrity]}
            if stream is not None:
                again = d.stream_state(workspace, item["stream"])
                out["stream"] = {"before": [stream.position, list(stream.unresolved),
                    stream.retired], "after": [again.position, list(again.unresolved),
                    again.retired]}
            read_at = time.monotonic()
            vals = tuple(scalar_read(v).value for v in item["values"])
            reading = r.accept_saved_read(workspace, item["job"], item["generation"],
                checkpoint=found.checkpoint, consumer=r.new_consumer(),
                scope="complete_capture", extent=found.extent, purpose="s16-native-read",
                route=item["route"], values=vals, seconds=3600, batch_rows=4096,
                expected_pin=item["pin"], accepted_producer=item["producer"],
                accepted_compatibility=tuple(item["compatibility"]))
            r.register_consumer(publisher, reading, operation=op())
            replay = r.open_replay(publisher, reading, operation=op())
            wires, extents = [], []
            while True:
                got = replay.next(5, operation=op())
                if isinstance(got, r.SavedScopeEnd):
                    end = [got.terminal, got.acknowledged, got.extent]
                    break
                data = pa.record_batch(got.batch)
                columns = [data.column(i).to_pylist() for i in range(data.num_columns)]
                wires.extend([chunks.coordinate_wire(column[j]) for column in columns]
                    for j in range(data.num_rows))
                extents.append([got.start, got.stop])
                replay.acknowledge(got, operation=op())
                got.batch.close()
            replay.close()
            out["read"] = {"wires": wires, "extents": extents, "end": end}
            out["seconds"] = {"prepare": prepared_at - mark,
                "publish": published_at - prepared_at,
                "read": time.monotonic() - read_at}
            out["verify"] = verify_store(workspace)
        finally:
            publisher.close()
            workspace.close()
    except Exception as error:
        out["error"] = type(error).__name__ + ":" + str(error)[:300]
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

# Distinctions per (route, origin): an ordinary seven-scalar result, an
# ordinary and a refined empty result and a guarded result, each captured by a
# real native owner and published later from an Arrow-only process.
DISTINCT = (
    {
        "group": "ordinary",
        "case": "R2_seven",
        "variant": "39_values",
        "excluded": False,
    },
    {"group": "ordinary", "case": "R2_seven", "variant": "39_empty", "excluded": False},
    {"group": "refined", "case": "R2_seven", "variant": "39_empty", "excluded": False},
    {"group": "guarded", "case": "bag_one", "variant": None, "excluded": False},
)


def label(cell) -> str:
    return "-".join(str(cell[k]) for k in ("group", "case", "variant"))


def guard_sources(resource):
    """S07's guard sources beside S06's general setup in the same database: the
    original S07 setup, with its two parts that the general setup already
    created exactly once (the seven-scalar tables and the query login) left out;
    its grants are re-applied so the query role reads the new guard objects."""
    import _pietto_phase68_slice5_probe as s05
    from _pietto_phase68_slice7_probe import setup as setup_guard

    statements = resource.role_statements
    seven = s05.setup_seven
    s05.setup_seven = lambda _resource: None
    resource.role_statements = lambda: tuple(
        (sql, secret)
        for sql, secret in statements()
        if not sql.startswith(("CREATE ROLE", "CREATE USER"))
    )
    try:
        setup_guard(resource)
    finally:
        s05.setup_seven = seven
        resource.role_statements = statements


def native(
    directory,
    ledger,
    capture_interpreter,
    publish_interpreter,
    *,
    target,
    cells,
    wheel=None,
):
    """One joined native history per route and (origin, entry) cell over
    R2_seven 39_values: a refined R2 capture relayed into sink A before the
    source ends (S15 prefix effects); the extractor SIGKILLed; a refused
    publication before R2; S14 recovery in a fresh native process whose real
    owner records the closing observation; per (route, origin) the ordinary,
    empty and guarded distinctions; the source database deleted; then an
    Arrow-only, driver-free process publishes, queries and reads every result."""
    import time

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
        {"kind": "s16_native_start", "directory": str(directory), "target": target},
    )
    report: dict = {
        "status": "STARTED",
        "target": target,
        "histories": [],
        "distinct": [],
    }
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
        guard_sources(resource)
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
                raise ValueError("S16_NATIVE_REFERENCE:" + name)
            artifact, preparation, query, _output, _binding = reference
            built = build_compiled(artifact, guarded=preparation, refinement=query)
            path = directory / (PREFIX + name + "-bundle.json")
            path.write_bytes(built.payload)
            path.chmod(0o600)
            values = [
                scalar_wire(Scalar(v.tag.value, v.value)) for v in artifact.fixed_values
            ]
            return path, built, values

        main, built, main_values = bundle(cell, "reference")
        distinctions = {label(d): bundle(d, label(d)) for d in DISTINCT}
        timings["preparation"] = time.monotonic() - mark
        common = {
            "target": target,
            "cell": cell,
            "providers": providers,
            "build_helpers": str(ROOT / "tests"),
            "library_source": str(ROOT / "src"),
            "bundle": str(main),
            "pin": built.pin,
            "producer": built.producer,
            "compatibility": list(built.compatibility),
            "values": main_values,
            "port": resource.port,
            "password": resource._passwords[1],
            "ca_path": str(resource.ca_path) if target == "mysql" else None,
            "request_seconds": 360,
        }

        def spawn(interpreter, name, program, config, *, cut=False):
            path = directory / (name + "-config.json")
            runtime = directory / (name + "-runtime")
            runtime.mkdir(mode=0o700)
            facts = directory / (name + "-facts.json")
            _write_private(
                path,
                {**common, **config, "runtime_cwd": str(runtime), "facts": str(facts)},
            )
            with (directory / (name + "-worker.log")).open("w") as log:
                child = s14._spawn(interpreter, program, path, ledger, log, name)
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
                raise ValueError("S16_NATIVE_WORKER:" + name + ":" + str(code))
            return json.loads(facts.read_text())

        for route in routes:
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
                mark = time.monotonic()
                relay = spawn(
                    capture_interpreter,
                    name + "-relay",
                    NATIVE,
                    {
                        "route": route,
                        "role": "relay",
                        "origin": origin,
                        "entry": entry,
                        "page_size": 2,
                        "rows": 2,
                        "deliver_steps": 2,
                        "workspace": str(directory / (name + "-workspace")),
                        "sink": str(directory / (name + "-sink")),
                        "namespace": "s16.native." + key,
                        "live_project": str(directory / (name + "-source")),
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
                    name + "-recover",
                    NATIVE,
                    {
                        **store,
                        "route": route,
                        "role": "recover",
                        "origin": origin,
                        "entry": "bundle",
                        "page_size": 3,
                        "relay_attempt": relay["attempt"],
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
                        "closing": recovered["closing"],
                        "older": recovered["predecessor"],
                        "stream": relay["stream"],
                        "values": main_values,
                        "pin": built.pin,
                        "producer": built.producer,
                        "compatibility": list(built.compatibility),
                        "coordinate_damage": entry == "bundle",
                    }
                )
                if entry == "bundle":
                    mark = time.monotonic()
                    items = []
                    for d in DISTINCT:
                        path, item_built, item_values = distinctions[label(d)]
                        items.append(
                            {
                                "key": key + "-" + label(d),
                                "bundle": str(path),
                                "pin": item_built.pin,
                                "producer": item_built.producer,
                                "compatibility": list(item_built.compatibility),
                                "values": item_values,
                                "workspace": str(
                                    directory / (name + "-" + label(d) + "-workspace")
                                ),
                            }
                        )
                    distinct = spawn(
                        capture_interpreter,
                        name + "-distinct",
                        NATIVE,
                        {
                            "route": route,
                            "role": "distinct",
                            "origin": origin,
                            "entry": "bundle",
                            "page_size": 2,
                            "distinctions": items,
                        },
                    )
                    s14._origin_check(distinct, origin, wheel)
                    for d, item in zip(DISTINCT, items, strict=True):
                        result = distinct["results"][item["key"]]
                        report["distinct"].append(
                            {
                                "key": item["key"],
                                "route": route,
                                "origin": origin,
                                "cell": d,
                                "capture": result,
                            }
                        )
                        stores.append(
                            {
                                "key": item["key"],
                                "route": route,
                                "origin": origin,
                                "workspace": result["workspace"],
                                "identity": result["identity"],
                                "job": result["job"],
                                "generation": result["generation"],
                                "closing": result["closing"],
                                "values": item["values"],
                                "pin": item["pin"],
                                "producer": item["producer"],
                                "compatibility": item["compatibility"],
                            }
                        )
                    timings[key + ":distinct"] = time.monotonic() - mark
                report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        mark = time.monotonic()
        report["source_cleanup"] = resource.cleanup()
        timings["source_cleanup"] = time.monotonic() - mark
        # The source database is gone: Arrow-only, driver-free publication.
        mark = time.monotonic()
        for origin in sorted({o for o, _e in cells}):
            raw = directory / (PREFIX + "publish-" + origin + ".json")
            path = directory / (PREFIX + "publish-" + origin + "-config.json")
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
            with (directory / (PREFIX + "publish-" + origin + ".log")).open(
                "wb"
            ) as log:
                status = worker_process(
                    [
                        str(publish_interpreter),
                        "-I",
                        "-B",
                        "-c",
                        r13.REPLAY_HEADER + PUBLISH,
                        str(path),
                    ],
                    clean_environment(),
                    ledger,
                    log,
                    origin=origin,
                    group="s16-native-publish",
                    directory=directory,
                    seconds=1800,
                )
            path.unlink()
            if status:
                raise ValueError("S16_NATIVE_PUBLISH")
            data = json.loads(raw.read_text())
            s14._origin_check(data, origin, wheel)
            if (
                data["connections"]
                or data["loaded_drivers"]
                or data["installed_drivers"]
            ):
                raise ValueError("S16_NATIVE_PUBLISH_SOURCE_ACCESS")
            for result in data["results"]:
                for record in report["histories"] + report["distinct"]:
                    if record["key"] == result["key"]:
                        record["publish"] = result
        timings["publish"] = time.monotonic() - mark
        for phase in ("prepare", "publish", "read"):
            timings["publish:" + phase] = sum(
                record["publish"]["seconds"][phase]
                for record in report["histories"] + report["distinct"]
                if "seconds" in record.get("publish", {})
            )
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
                "kind": "s16_native_terminal",
                "directory": str(directory),
                "status": report["status"],
                "cleanup": report["source_cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


def native_check(directory, target, report):
    """Independent judgement of recorded native histories and distinctions from
    closed stores and chunk bytes (literal oracles outside every worker), plus
    coordinated damages of each route's first history."""
    import _pietto_phase68_slice15_check as s15check
    import _pietto_phase68_slice16_check as check
    from _pietto_phase68_slice6_check import expected
    from _pietto_phase68_slice7_cases import manifest as guard_manifest

    def oracle(cell):
        if cell["group"] == "guarded":
            case = next(c for c in guard_manifest() if c["name"] == cell["case"])
            return check.encoded(case["rows"]), False
        return expected(target, cell["case"], cell["variant"], None)

    damaged = set()
    for record in report["histories"]:
        relay, recover, published = (
            record["relay"],
            record["recover"],
            record["publish"],
        )
        check.need("error" not in published, "NATIVE_PUBLISH")
        check.need(
            recover["before_r2"] == "PUBLICATION_CLOSING_UNOBSERVED"
            and recover["before_r2_releases"] == 1,
            "NATIVE_BEFORE_R2",
        )
        check.need(
            relay["first"] is not None and relay["first"]["terminal"] is None,
            "NATIVE_BEFORE_EOF",
        )
        check.need(
            recover["original"][0] == "INTERRUPTED"
            and recover["original"][1]["transaction"] == "UNKNOWN",
            "NATIVE_OLD_UNKNOWN",
        )
        check.need(
            published["older"].endswith(":PUBLICATION_BASIS")
            and published["published"]["observation"] == "COMMITTED_THIS_CALL"
            and published["published"]["queried"] == "publish_generation",
            "NATIVE_PUBLICATION",
        )
        check.need(
            published.get("coordinate_damage") in (None,)
            or published["coordinate_damage"].endswith(":CHUNK_COORDINATE"),
            "NATIVE_COORDINATE_DAMAGE",
        )
        stream = published["stream"]
        check.need(
            stream["before"] == stream["after"] and stream["before"][0] == 4,
            "NATIVE_SINK_SEPARATE",
        )
        stored = directory / (PREFIX + record["key"] + "-store-backup.sqlite")
        if not stored.exists():
            backup_store(relay["workspace"], relay["identity"], stored)
        literal, ordered = oracle(
            {"group": "refined", "case": "R2_seven", "variant": "39_values"}
        )
        checked = check.check_store(
            stored, relay["workspace"], relay["generation"], literal, ordered=ordered
        )
        decoded = [
            [s15check.decode_wire(v) for v in row] for row in published["read"]["wires"]
        ]
        check.need(
            check.same_rows(decoded, literal, ordered=ordered), "NATIVE_READ_VALUES"
        )
        check.need(
            published["read"]["end"]
            == ["SAVED_SCOPE_EXHAUSTED", checked["extent"], checked["extent"]]
            and checked["basis"] == "CONTINUATION"
            and checked["closing"] == recover["closing"]
            and checked["unknown"] >= 1,
            "NATIVE_READ_END",
        )
        record["checked"] = {
            k: checked[k] for k in ("extent", "members", "basis", "unknown")
        }
        if record["route"] not in damaged:
            damaged.add(record["route"])
            record["damages"] = check.damages(
                stored,
                relay["workspace"],
                relay["generation"],
                literal,
                ordered=ordered,
                scratch=directory / (PREFIX + record["key"] + "-damages"),
            )
    for record in report["distinct"]:
        published, capture = record["publish"], record["capture"]
        check.need(
            "error" not in published and capture["failure"] is None, "NATIVE_DISTINCT"
        )
        stored = directory / (PREFIX + record["key"] + "-store-backup.sqlite")
        if not stored.exists():
            backup_store(capture["workspace"], capture["identity"], stored)
        literal, ordered = oracle(record["cell"])
        checked = check.check_store(
            stored,
            capture["workspace"],
            capture["generation"],
            literal,
            ordered=ordered,
        )
        decoded = [
            [s15check.decode_wire(v) for v in row] for row in published["read"]["wires"]
        ]
        check.need(
            check.same_rows(decoded, literal, ordered=ordered)
            and checked["basis"] == "CAPTURE",
            "NATIVE_DISTINCT_VALUES",
        )
        record["checked"] = {k: checked[k] for k in ("extent", "members", "basis")}
    return report
