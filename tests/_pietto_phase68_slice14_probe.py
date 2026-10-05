"""S14 R2 fixtures and explicit bounded families; import acquires nothing.

Ordinary tests have no Arrow and no database. Their owners are real compiled S10
refined PostgreSQL owners that never connect. SYNTHETIC_OPEN_OWNER replaces only
the opened-owner gate and its native source description, ARROW_FREE_MEMBER_CHECK
replaces only the saved members' Arrow value check (bounded bytes, digest and
descriptor still run), and ARROW_FREE_PAGE_STEP feeds the REAL reconciliation step
synthetic page slices whose saved-value comparison is skipped. Every SQLite
transaction, fence, barrier, publication and verifier still runs for real. Real
checked Arrow pages, native qualification and source-offline R1 run only in the
execution-profile families.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import sys
import weakref

import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice13_probe as s13

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice14-"
op = s12.op
# SYNTHETIC_OPEN_OWNER descriptions per never-connected owner; a test changes
# one to model a changed fresh qualification.
DESCRIPTIONS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
SYNTHETIC = '["SYNTHETIC_OPEN_OWNER"]'
# Saved extents the skipped comparison would have checked, per attempt identity.
COMPARED: dict[str, list] = {}


def refined_template(directory, *, entry="bundle", target="postgres"):
    """S06 R2_bound with fixture source requirements as a current S10 template."""
    from _pietto_phase68_slice6_cases import original
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_execution_source import RetainedSourceRequirement
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
        prepare_live_template,
    )
    from pietto._project.project_refinement import TieRefinement, prepare_refinement

    artifact = original(Path(directory), target, "R2_bound", "range")
    assert artifact is not None
    # S06's fixture declarations (labels only; no native admission here).
    requirements = tuple(
        RetainedSourceRequirement(
            s,
            "explicit-fixture-provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "explicit fixture view definition",
            ("key0",),
            "pietto_query",
            "Fixture declaration only; fresh native admission is separate.",
        )
        for s in artifact.request.sources
    )
    refinement = prepare_refinement(artifact, requirements, policy=TieRefinement())
    built = build_compiled(artifact, refinement=refinement)
    values = tuple(v.value for v in artifact.fixed_values)
    if entry == "live":
        return prepare_live_template(artifact, refinement=refinement), built, values
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    return prepare_compiled_template(root), built, values


def fixture_reference(directory, target, cell):
    """S10's build-only reference with fixture provider declarations (no database).

    The provider declarations are labels for the compiled requirement vector
    only; native admission of them is execution-profile evidence.
    """
    import _pietto_phase68_slice10_probe as s10
    from _pietto_phase68_slice6_cases import original
    from _pietto_phase68_slice7_cases import case_preparation, manifest

    directory = Path(directory)
    if cell["group"] == "guarded":
        case = next(c for c in manifest() if c["name"] == cell["case"])
        first = case_preparation(directory / "sources", target, case).artifact
    else:
        first = original(directory / "sources", target, cell["case"], cell["variant"])
    if first is None:
        return None
    relations = sorted({(s.namespace, s.name) for s in first.request.sources})
    providers = [
        dict(
            namespace=n,
            name=m,
            provider="fixture-" + str(i),
            version="v1",
            revision="r1",
            registry="registry",
            definition="fixture view definition",
            tokens=["key0"],
        )
        for i, (n, m) in enumerate(relations)
    ]
    return s10.build_native_reference(directory / "reference", target, cell, providers)


def r2_families(target):
    """Every admitted R2 family: S10's refined group and S07's refined guarded cases."""
    import _pietto_phase68_slice10_probe as s10
    from _pietto_phase68_slice7_cases import manifest

    refined = {c["name"] for c in manifest() if c["options"].get("refined")}
    return [
        c
        for c in s10.native_manifest(target)
        if c["group"] == "refined" or (c["group"] == "guarded" and c["case"] in refined)
    ]


def store(root, template, values, **options):
    """A v4 workspace with one job, publisher, binding and generation."""
    from pietto._project import project_job_workspace as w

    return s12.store(root, template, values, format=w.FORMAT_V4, **options)


def synthetic_describe(owner):
    return DESCRIPTIONS.get(owner, SYNTHETIC)


def arrow_free_members(workspace, snapshot, output, refinement, route):
    """ARROW_FREE_MEMBER_CHECK: bounded bytes, digest and exact descriptor."""
    from pietto._project import project_job_chunks as k
    from pietto._project.project_job_workspace import CHUNKS, JobStoreError

    directory = workspace.directory(CHUNKS)
    try:
        for member in snapshot.members:
            data = k.read_chunk_file(
                directory, member.file, member.bytes, member.digest
            )
            text, descriptor, _frame = k.decode_chunk(data)
            if text != member.descriptor or descriptor["attempt"] != member.attempt:
                raise JobStoreError("CHUNK_DESCRIPTOR")
    finally:
        os.close(directory)


def synthetic_frame_step(session, array, rows):
    return s12.synthetic_frame(rows, contract=bytes.fromhex(session.contract))


def skipped_compare(session, index, a, b, fresh, wires):
    """ARROW_FREE_PAGE_STEP: the saved-value comparison is not exercised here."""
    COMPARED.setdefault(session.attempt.identity, []).append((index, a, b))


def synthetic(monkeypatch=None):
    """Install the labelled synthetic steps (process-wide without monkeypatch)."""
    from pietto._project import project_job_capture as c
    from pietto._project import project_job_extraction as x

    patches = (
        (x, "_fresh", lambda owner: None),
        (x, "describe", synthetic_describe),
        (x, "_verify_saved", arrow_free_members),
        (c.CaptureSession, "_encode", synthetic_frame_step),
        (x.ContinuationSession, "_compare", skipped_compare),
    )
    for target, name, value in patches:
        if monkeypatch is None:
            setattr(target, name, value)
        else:
            monkeypatch.setattr(target, name, value)


def owner(binding, *, batch_rows=2):
    """A real compiled refined PostgresExecution that never connects."""
    return s12.pg_owner(binding, batch_rows=batch_rows)


def wires(start, rows):
    return [[["int", start + i]] for i in range(rows)]


def stage_refined(session, rows, *, terminal=None):
    """ARROW_FREE_STORAGE_STEP of an original REFINED capture with coordinates."""
    workspace = session.publisher.use()
    start, batches = session._observed, 1 if rows else 0
    session._observed += rows
    session._batches += batches
    return session._materialize(
        workspace,
        s12.synthetic_frame(rows, contract=bytes.fromhex(session.contract)),
        start,
        rows,
        batches,
        wires(start, rows),
        terminal,
    )


def extract(publisher, generation, binding, sizes, *, order=None, eof=False):
    """An initial R2 capture of synthetic pages, published in `order`.

    Without `eof` the attempt stays open (a crashed original); with it the
    owner's EOF is recorded and the attempt terminal is recorded.
    """
    from pietto._project import project_job_extraction as x
    from pietto._project import project_job_store as s

    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    session = x.begin_extraction(publisher, attempt, owner(binding), operation=op())
    staged = [stage_refined(session, rows) for rows in sizes]
    if not sizes and eof:
        staged = [stage_refined(session, 0, terminal="EOF")]
    results = [
        session.publish(staged[i], operation=op())
        for i in (range(len(staged)) if order is None else order)
    ]
    if eof:
        session.owner.close()
        session._terminal = "EOF"
        session.end(operation=op())
        s.record_attempt(publisher, attempt, session.owner, operation=op())
    return session, results


def trust(built):
    return s13.trust(built)


def takeover(workspace, job, previous=None):
    """A new process's publisher: the previous holder's lock is gone (closed
    here, as process death would), and every open attempt is interrupted."""
    from pietto._project import project_job_store as s

    if previous is not None:
        previous.close()
    publisher = s.claim_publisher(workspace, job, operation=op())
    for item in s.job_record(workspace, job).attempts:
        if item.terminal is None:
            s.interrupt_attempt(publisher, item.identity, operation=op())
    return publisher


def accept(workspace, job, generation, built, values, **overrides):
    from pietto._project import project_job_capture as c
    from pietto._project import project_job_extraction as x

    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    arguments: dict[str, Any] = {
        "checkpoint": snapshot.checkpoint,
        "purpose": "s14-recover",
        "values": values,
        "seconds": 600,
        **trust(built),
    }
    arguments.update(overrides)
    return x.accept_recovery(workspace, job, generation, **arguments)


def recover(workspace, job, generation, built, values, *, previous=None, **overrides):
    """Takeover, a fresh acceptance and a new attempt with its fresh binding."""
    from pietto._project import project_job_store as s

    publisher = takeover(workspace, job, previous)
    acceptance = accept(workspace, job, generation, built, values, **overrides)
    attempt = s.open_attempt(publisher, generation, acceptance.binding, operation=op())
    return publisher, acceptance, attempt


class Slices:
    """ARROW_FREE_PAGE_STEP carrier: what a checked page's slices would be."""

    def slice(self, offset, length):
        return ("SLICE", offset, length)


def page(session, rows):
    """The REAL `_step` over a synthetic checked page of `rows` (labelled)."""
    start = session.observed
    return session._step(session.publisher.use(), Slices(), rows, wires(start, rows))


def finish_stream(session, *, source="EOF"):
    """The owner's terminal as the real stream would report it, then `_close_stream`."""
    session.owner.close()
    session._terminal = source
    return session._close_stream(session.publisher.use())


def drive(session, sizes, *, publish=True):
    """Pages of `sizes`; reconcile as soon as ready and publish what is staged."""
    pending = []
    for rows in sizes:
        if session.ready and not session.reconciled:
            session.reconcile(operation=op())
        pending.extend(page(session, rows))
        if publish and session.reconciled:
            for item in pending:
                session.publish(item, operation=op())
            pending.clear()
    if session.ready and not session.reconciled:
        session.reconcile(operation=op())
    if publish and session.reconciled:
        for item in list(session.staged):
            session.publish(item, operation=op())
    return pending


CHILD_HEADER = r"""
import json, os, signal, sys, time
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[3])
config = json.loads(sys.argv[2])
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c, project_job_extraction as x
import _pietto_phase68_slice14_probe as probe
probe.synthetic()

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
    return workspace, binding

def built():
    from types import SimpleNamespace
    return SimpleNamespace(pin=config["pin"], producer=config["producer"],
        compatibility=tuple(config["compatibility"]))
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


def child_config(workspace, job, record, generation, built, values, **extra):
    return {
        "workspace": workspace.root,
        "identity": workspace.identity,
        "job": job,
        "record": record,
        "generation": generation,
        "pin": built.pin,
        "producer": built.producer,
        "compatibility": list(built.compatibility),
        "values": list(values),
        **extra,
    }


# ---------------------------------------------------------------------------
# Execution-profile families (Arrow and drivers present). Nothing runs at import.

INTERRUPTED = "S14_EXTRACTION_ABANDONED_WITHOUT_TERMINAL"

R2_SETUP = r"""
from pietto._project import project_job_store as s14s, project_job_workspace as s14w
from pietto._project import project_job_capture as s14c, project_job_extraction as s14x
from pietto._project import project_job_replay as s14r
from pietto._project.project_job_store_verification import verify_store as s14verify
import pyarrow as s14pa
S14_CONFIG = config["s14"]
S14_ROLE = S14_CONFIG["role"]
if S14_ROLE == "capture":
    S14_WORKSPACE = s14w.create_workspace(S14_CONFIG["workspace"], format=s14w.FORMAT_V4)
else:
    S14_WORKSPACE = s14w.open_workspace(S14_CONFIG["workspace"],
        expected_identity=S14_CONFIG["identity"])
S14 = {"publishers": []}
class S14Abandoned(Exception):
    pass
def s14_op():
    return s14s.new_operation()
def s14_members(snapshot):
    return [[m.start, m.stop, m.attempt, m.chunk] for m in snapshot.members]
def S14_CAPTURE(owner):
    session = s14x.begin_extraction(S14["publisher"], S14["attempt"], owner,
        operation=s14_op())
    staged, published = [], []
    for _ in range(S14_CONFIG["pages"]):
        item = session.stage()
        if item is None:
            break
        staged.append(item)
    plan = [0, 2] if len(staged) >= 3 else [0] if staged else []
    for index in plan:
        result = session.publish(staged[index], operation=s14_op())
        published.append([staged[index].identity, result.get("checkpoint"),
            result.get("frontier")])
    snapshot = s14c.checkpoint_snapshot(S14_WORKSPACE, S14["job"], S14["generation"])
    S14["facts"] = {"workspace": S14_WORKSPACE.root, "identity": S14_WORKSPACE.identity,
        "job": S14["job"], "generation": S14["generation"], "record": S14["record"],
        "attempt": S14["attempt"].identity,
        "staged": [[x.start, x.stop, x.batches, x.identity] for x in staged],
        "published": published, "terminal": session.terminal,
        "observed": session.observed, "members": s14_members(snapshot),
        "frontier": snapshot.frontier, "checkpoint": snapshot.checkpoint}
    raise S14Abandoned(INTERRUPTED)
def S14_RECOVER(owner):
    session = s14x.begin_continuation(S14["publisher"], S14["acceptance"],
        S14["attempt"], owner, operation=s14_op())
    published, pages, extents = [], [], []
    def publish(items):
        for item in items:
            result = session.publish(item, operation=s14_op())
            published.append([item.start, item.stop, item.identity,
                result.get("checkpoint"), result.get("frontier")])
    try:
        while True:
            if session.ready and not session.reconciled:
                reconciled = session.reconcile(operation=s14_op())
                publish(list(session.staged))
            before = session.observed
            items = session.stage()
            if items is None:
                break
            if session.observed > before:
                extents.append((before, session.observed))
            pages.append([session.observed, session.matched, [[x.start, x.stop] for x in items]])
            if session.reconciled:
                publish(items)
        if session.ready and not session.reconciled:
            reconciled = session.reconcile(operation=s14_op())
            publish(list(session.staged))
        ended = session.end(operation=s14_op())
    finally:
        session.close()
    s14s.record_attempt(S14["publisher"], S14["attempt"], owner, operation=s14_op())
    snapshot = s14c.checkpoint_snapshot(S14_WORKSPACE, S14["job"], S14["generation"])
    state = s14x.extraction_state(S14_WORKSPACE, S14["job"], S14["generation"])
    a = S14["acceptance"]
    S14["facts"] = {"job": S14["job"], "generation": S14["generation"],
        "attempt": S14["attempt"].identity, "predecessor": a.checkpoint,
        "frozen": [a.frontier, a.reach, a.rows, a.known,
            s14_members(a._snapshot)],
        "reconciled": dict(reconciled.result), "materialized": session.materialized,
        "matched": session.matched, "observed": session.observed, "pages": pages,
        "published": published, "end": dict(ended.result),
        "members": s14_members(snapshot), "checkpoint": snapshot.checkpoint,
        "frontier": snapshot.frontier, "holes": snapshot.holes,
        "observed_end": snapshot.observed_end, "layers": [list(x) for x in snapshot.layers],
        "state": [state.known, state.complete_coverage, list(state.continuations)],
        "verify_store": s14verify(S14_WORKSPACE)}
    output = s14c.stored_output(S14_WORKSPACE, S14["job"], S14["generation"],
        expected_pin=config["pin"], accepted_producer=config["producer"],
        accepted_compatibility=tuple(config["compatibility"]))
    # The saved multi-attempt result, rebatched to the fresh pages' extents.
    with s14c.SnapshotReader(S14_WORKSPACE, snapshot, output) as reader:
        held = None
        for start, stop in extents:
            parts = []
            for index, offset, rows in s14r.plan(snapshot.members, start, stop):
                if held is None or held[0] != index:
                    held = (index, reader.read(index).table)
                parts.append(held[1].slice(offset, rows))
            yield s14pa.concat_tables(parts).combine_chunks().to_batches()[0]
def S14_LOOP(owner):
    return S14_CAPTURE(owner) if S14_ROLE == "capture" else S14_RECOVER(owner)
"""

R2_ATTEMPT = r"""
    if S14_ROLE == "capture":
        S14["job"] = s14s.register_job(S14_WORKSPACE, template,
            operation=s14_op()).get("job")
        S14["publisher"] = s14s.claim_publisher(S14_WORKSPACE, S14["job"],
            operation=s14_op())
        S14["record"] = s14s.register_binding(S14["publisher"], bound,
            operation=s14_op()).get("binding")
        S14["generation"] = s14s.register_generation(S14["publisher"], S14["record"],
            bound, route=route, isolation=options.get("isolation", "stable"),
            operation=s14_op()).get("generation")
        S14["attempt"] = s14s.open_attempt(S14["publisher"], S14["generation"], bound,
            operation=s14_op())
    else:
        facts = S14_CONFIG["routes"][route]
        S14["job"], S14["generation"] = facts["job"], facts["generation"]
        S14["publisher"] = s14s.claim_publisher(S14_WORKSPACE, S14["job"],
            operation=s14_op())
        for item in s14s.job_record(S14_WORKSPACE, S14["job"]).attempts:
            if item.terminal is None:
                s14s.interrupt_attempt(S14["publisher"], item.identity,
                    operation=s14_op())
        latest = s14c.checkpoint_snapshot(S14_WORKSPACE, S14["job"], S14["generation"])
        S14["acceptance"] = s14x.accept_recovery(S14_WORKSPACE, S14["job"],
            S14["generation"], checkpoint=latest.checkpoint, purpose="s14-matrix",
            values=values, expected_pin=config["pin"],
            accepted_producer=config["producer"],
            accepted_compatibility=tuple(config["compatibility"]), seconds=3600)
        # The fresh binding and a fresh managed premise over ITS sources.
        bound = S14["acceptance"].binding
        if route == "mysql_rows":
            premise = {"mysql_deployment": ex.MySQLDeploymentPremise(a,
                bound.artifact.request.sources, ("phase66",))}
        else:
            premise = {"postgres_deployment": ex.PostgresDeploymentPremise(a,
                bound.artifact.request.sources, ("public", "pg_catalog"), route)}
        S14["attempt"] = s14s.open_attempt(S14["publisher"], S14["generation"], bound,
            operation=s14_op())
    S14["publishers"].append(S14["publisher"])
"""

R2_RECORD = r"""
    record["s14"] = S14.pop("facts", None)
"""


def r2_case_program(original=None):
    """S10's isolated case worker with its owner loop anchored to R2 capture or
    fresh-process recovery; S10's native observer and source-free boundary stay."""
    if original is None:
        from _pietto_phase68_slice10_probe import case_worker_program as original

    text = original()
    text = s12._replace(
        text,
        "        with owner:\n            for batch in owner:\n                with batch:\n"
        "                    array = pa.record_batch(batch)\n",
        "        with owner:\n            for array in S14_LOOP(owner):\n"
        "                if True:\n",
    )
    anchor = 'values=tuple(scalar_read(v).value for v in config["values"])\n'
    text = s12._replace(
        text,
        anchor,
        anchor + R2_SETUP.lstrip("\n").replace("INTERRUPTED", repr(INTERRUPTED)),
    )
    anchor = "    request=ex.prepare_compiled_execution("
    text = s12._replace(text, anchor, R2_ATTEMPT.lstrip("\n") + anchor)
    anchor = "    record=collect_owned(request)\n"
    text = s12._replace(text, anchor, anchor + R2_RECORD.lstrip("\n"))
    return s12._replace(
        text,
        "origins={}\n",
        "for publisher in S14['publishers']:\n    publisher.close()\n"
        "S14_WORKSPACE.close()\norigins={}\n",
    )


def _write_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, ensure_ascii=False)


def _backup(workspace_root, identity, target):
    """Supported SQLite backup of a closed workspace (never a lone main-file copy)."""
    import sqlite3

    from pietto._project import project_job_workspace as w

    opened = w.open_workspace(workspace_root, expected_identity=identity)
    try:
        os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        copy = sqlite3.connect(target)
        try:
            opened.use().backup(copy)
        finally:
            copy.close()
    finally:
        opened.close()


def acquire_r2_group(
    directory,
    ledger,
    interpreter,
    *,
    target,
    group,
    cells,
    wheel=None,
    selected=None,
    request_seconds=180,
    part=(0, 1),
    extra_cells=(),
    extra_selected=frozenset(),
    drift_cells=(),
    histories=None,
):
    """One owned database; per admitted R2 cell and (origin, entry): an isolated
    S10 subject R2-captures at most three pages of size 2 and abandons the
    attempt without a terminal; a NEW isolated subject recovers it from the
    store with fresh trust/access/premise and page size 3. S10's raw checker
    and the S06/S07 oracles run here, outside every worker."""
    import hashlib
    import shutil
    import time

    import _pietto_phase68_slice10_probe as s10
    from _pietto_phase68_slice6_probe import setup as setup_general, manager
    from _pietto_phase68_slice6_probe import session_gone
    from _pietto_phase68_slice7_probe import setup as setup_guard, fill
    from _pietto_phase68_slice7_cases import manifest as guard_manifest
    from _pietto_phase68_slice8_probe import event, worker_process
    from _pietto_phase68_slice10_check import check_matrix_record, check_matrix_origin
    from _pietto_phase68_slice14_check import (
        check_capture,
        check_recovery,
        check_refused_recovery,
    )
    from _pietto_target_conformance_resources import Resources, clean_environment
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_schema import Scalar, scalar_wire

    directory.mkdir(mode=0o700)
    guarded = {c["name"]: c for c in guard_manifest()}
    declarations = [
        c
        for c in s10.native_manifest(target)
        if (c["group"] == "guarded") == (group == "guarded")
        and (c["group"] != "guarded" or guarded[c["case"]]["options"].get("refined"))
        and c["group"] in ("refined", "guarded")
        and (selected is None or (c["group"], c["case"], c["variant"]) in selected)
    ]
    # A fixed interleaved part of the frozen denominator (parallel lifecycles).
    declarations = declarations[part[0] :: part[1]]
    if not declarations:
        raise ValueError("S14_EMPTY_R2_GROUP")
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
        {
            "kind": "s14_r2_group_start",
            "directory": str(directory),
            "target": target,
            "group": group,
            "denominator": declarations,
            "cells": cells,
        },
        source_db_lifecycle_starts=1,
    )
    report: dict[str, Any] = {
        "status": "STARTED",
        "target": target,
        "group": group,
        "denominator": declarations,
        "cells": cells,
        "records": [],
    }
    report_path = directory / (PREFIX + "r2-group.json")
    private = directory / (PREFIX + "private-input.json")
    started = time.monotonic()
    program = r2_case_program()
    routes = ["mysql_rows"] if target == "mysql" else ["postgres_rows", "postgres_adbc"]

    def run(label, config, cell):
        public = {k: v for k, v in config.items() if k not in ("password", "ca_path")}
        _write_private(directory / (label + "-handoff.json"), public)
        _write_private(private, config)
        try:
            with (directory / (label + "-worker.log")).open("wb") as log:
                status = worker_process(
                    [str(interpreter), "-I", "-B", "-c", program, str(private)],
                    clean_environment(),
                    ledger,
                    log,
                    origin=config["origin"],
                    group="s14-" + group + "-" + config["s14"]["role"],
                    directory=directory,
                    seconds=2 * request_seconds + 240,
                )
        finally:
            private.unlink(missing_ok=True)
        if status:
            raise ValueError("S14_ISOLATED_NATIVE_WORKER_FAILED:" + label)
        raw = Path(config["raw"])
        data = json.loads(raw.read_text())
        check_matrix_origin(data, config, interpreter, wheel)
        for record in data["results"]:
            record["session_gone"] = (
                None
                if record["session"] is None
                else session_gone(resource, record["session"])
            )
            record["sessions_gone"] = {
                str(s): session_gone(resource, s) for s in record.get("sessions", ())
            }
        terminal = directory / (label + "-sessions.json")
        terminal.write_text(
            json.dumps(
                [
                    {
                        "attempt": r["outcome"]["attempt"],
                        "session_gone": r["session_gone"],
                        "sessions_gone": r["sessions_gone"],
                    }
                    for r in data["results"]
                ],
                indent=2,
            )
            + "\n"
        )
        return data, hashlib.sha256(raw.read_bytes()).hexdigest()

    try:
        resource.acquire()
        if target == "mysql":
            manager(resource, "USE phase66")
        providers = (
            (setup_guard(resource), s10.guard_providers(resource))[1]
            if group == "guarded"
            else setup_general(resource)
        )
        if target == "mysql":
            for user in (
                ("pietto_query", "pietto_subset")
                if group == "guarded"
                else ("pietto_query",)
            ):
                for table in ("threads", "events_transactions_current"):
                    manager(
                        resource,
                        "GRANT SELECT ON performance_schema."
                        + table
                        + " TO '"
                        + user
                        + "'@'%'",
                    )
        # Main combinations for every cell, the extra entry/origin combinations
        # for the discriminating set, then (guarded only) a fresh-guard drift item.
        work = [
            (
                index,
                cell,
                [*cells]
                + (
                    [*extra_cells]
                    if (cell["group"], cell["case"], cell["variant"]) in extra_selected
                    else []
                ),
                False,
            )
            for index, cell in enumerate(declarations)
        ]
        if drift_cells:
            pages = next(
                c
                for c in s10.native_manifest(target)
                if c["group"] == "guarded" and c["case"] == "refined_pages"
            )
            work.append((len(declarations), pages, [*drift_cells], True))
        violation = guarded["refined_violation_outside_page"]
        for index, cell, combos, drifted in work:
            build_directory = directory / (PREFIX + str(index) + "-reference-source")
            if cell["excluded"] and cell["group"] == "guarded":
                report["records"].append(
                    {"cell": cell, "status": "ORIGINAL_TARGET_EXCLUSION"}
                )
                continue
            reference = s10.build_native_reference(
                build_directory, target, cell, providers
            )
            if cell["excluded"]:
                if reference is not None:
                    raise ValueError("S14_LOST_ORIGINAL_TARGET_EXCLUSION")
                report["records"].append(
                    {"cell": cell, "status": "ORIGINAL_TARGET_EXCLUSION"}
                )
                continue
            if reference is None or reference[2] is None:
                raise ValueError("S14_R2_CELL_NOT_REFINED")
            artifact, preparation, query, output, binding = reference
            built = build_compiled(artifact, guarded=preparation, refinement=query)
            bundle = directory / (PREFIX + str(index) + "-bundle.json")
            bundle.write_bytes(built.payload)
            bundle.chmod(0o600)
            shutil.rmtree(build_directory)
            case = guarded.get(cell["case"]) if cell["group"] == "guarded" else None
            options = {} if case is None else dict(case["options"])
            for origin, entry in combos:
                if origin == "installed" and wheel is None:
                    raise ValueError("S14_INSTALLED_WHEEL_REQUIRED")
                if case is not None:
                    fill(
                        resource,
                        case["lhs"],
                        case["rhs"],
                        wide_text=options.get("wide_text", False),
                    )
                label = (
                    PREFIX
                    + str(index)
                    + "-"
                    + origin
                    + "-"
                    + entry
                    + ("-drift" if drifted else "")
                )
                workspace = directory / (label + "-workspace")
                config = {
                    "origin": origin,
                    "entry": entry,
                    "target": target,
                    "cell": cell,
                    "providers": providers,
                    "build_helpers": str(ROOT / "tests"),
                    "library_source": str(ROOT / "src"),
                    "removed_query_project": str(build_directory),
                    "bundle": str(bundle),
                    "pin": built.pin,
                    "producer": built.producer,
                    "compatibility": built.compatibility,
                    "values": [
                        scalar_wire(Scalar(v.tag.value, v.value))
                        for v in artifact.fixed_values
                    ],
                    "port": resource.port,
                    "password": resource._passwords[1],
                    "ca_path": str(resource.ca_path) if target == "mysql" else None,
                    "request_seconds": request_seconds,
                    "routes": routes,
                }
                item: dict[str, Any] = {"cell": cell, "origin": origin, "entry": entry}
                report["records"].append(item)
                for role, page_size in (("capture", 2), ("recover", 3)):
                    name = label + ("" if role == "capture" else "-recover")
                    runtime = directory / (name + "-runtime")
                    runtime.mkdir(mode=0o700)
                    role_config = {
                        **config,
                        "runtime_cwd": str(runtime),
                        "live_project": str(directory / (name + "-source")),
                        "options": {**options, "page_size": page_size},
                        "raw": str(directory / (name + "-raw.json")),
                        "s14": {"role": role, "workspace": str(workspace), "pages": 3},
                    }
                    if role == "recover":
                        if drifted:
                            # A guard violation outside the saved page appears.
                            fill(resource, violation["lhs"], violation["rhs"])
                            item["drift"] = {
                                "lhs": violation["lhs"],
                                "rhs": violation["rhs"],
                            }
                        facts = {
                            r["route"]: r["s14"] for r in item["capture"]["results"]
                        }
                        if any(f is None for f in facts.values()):
                            # No R2 basis was registered (e.g. the attempt failed
                            # before its first capture): nothing may continue.
                            item["recover"] = "NO_R2_BASIS"
                            break
                        role_config["s14"].update(
                            identity=next(iter(facts.values()))["identity"],
                            routes={
                                route: {"job": f["job"], "generation": f["generation"]}
                                for route, f in facts.items()
                            },
                        )
                    data, digest = run(name, role_config, cell)
                    item[role] = {"raw": role_config["raw"], "sha256": digest}
                    item[role]["results"] = [
                        {"route": r["route"], "s14": r["s14"]} for r in data["results"]
                    ]
                    for record in data["results"]:
                        if role == "capture":
                            check_capture(record, cell, case)
                        elif drifted:
                            capture = next(
                                r
                                for r in item["capture"]["results"]
                                if r["route"] == record["route"]
                            )
                            check_refused_recovery(record, capture["s14"])
                        else:
                            check_matrix_record(record, cell, reference, case=case)
                            capture = next(
                                r
                                for r in item["capture"]["results"]
                                if r["route"] == record["route"]
                            )
                            check_recovery(record, capture["s14"])
                    report_path.write_text(json.dumps(report, indent=2) + "\n")
                if drifted and item.get("recover") != "NO_R2_BASIS":
                    from pietto._project import project_job_capture as c
                    from pietto._project import project_job_workspace as w

                    first = item["capture"]["results"][0]["s14"]
                    opened = w.open_workspace(
                        str(workspace), expected_identity=first["identity"]
                    )
                    try:
                        item["after_refusal"] = {
                            r["route"]: [
                                r["s14"]["checkpoint"],
                                c.checkpoint_snapshot(
                                    opened, r["s14"]["job"], r["s14"]["generation"]
                                ).checkpoint,
                            ]
                            for r in item["capture"]["results"]
                        }
                    finally:
                        opened.close()
                    if any(a != b for a, b in item["after_refusal"].values()):
                        raise ValueError("S14_REFUSAL_CHANGED_CHECKPOINT")
                if item.get("recover") != "NO_R2_BASIS":
                    backup = directory / (label + "-backup.sqlite")
                    _backup(
                        str(workspace),
                        item["capture"]["results"][0]["s14"]["identity"],
                        backup,
                    )
                    item["backup"] = str(backup)
                item["checked"] = True
                report_path.write_text(json.dumps(report, indent=2) + "\n")
                print(
                    target,
                    group,
                    index,
                    cell["case"],
                    cell["variant"],
                    origin,
                    entry,
                    "checked",
                    flush=True,
                )
        if histories is not None:
            # The same live database, after every matrix item is checked.
            report["histories"] = r2_histories(
                directory / "histories",
                ledger,
                interpreter,
                target=target,
                origin=histories,
                wheel=wheel,
                shared=(resource, providers),
            )["status"]
        report["status"] = "PASS"
    except BaseException as error:
        report.update(
            status="FAILED",
            error_kind=type(error).__name__,
            error=resource.without_secrets(str(error)),
        )
        raise
    finally:
        private.unlink(missing_ok=True)
        report["cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - started
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        event(
            ledger,
            {
                "kind": "s14_r2_group_terminal",
                "directory": str(directory),
                "status": report["status"],
                "cleanup": report["cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


HISTORY = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, os, time
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["runtime_cwd"])
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_schema import scalar_read
from pietto._project.project_execution_template import prepare_compiled_template, bind_values
from pietto._project import project_execution as ex
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c, project_job_extraction as x
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_execution_postgres import PostgresExecution
from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
from pietto._project.project_execution_mysql import MySQLExecution
OWNERS = {"postgres_rows": PostgresExecution, "postgres_adbc": PostgresADBCExecution,
    "mysql_rows": MySQLExecution}
route, role, cut = config["route"], config["role"], config.get("cut")
facts = {"role": role, "route": route, "cut": cut, "pid": os.getpid()}
def write_facts():
    import hashlib
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
        limits=ex.ExecutionLimits(batch_rows=config["page_size"], seconds=900), **premise)
    return OWNERS[route](request)
def members(snapshot):
    return [[m.start, m.stop, m.attempt, m.chunk] for m in snapshot.members]
trust = dict(expected_pin=config["pin"], accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]))
values = tuple(scalar_read(v).value for v in config["values"])
if role == "capture":
    workspace = w.create_workspace(config["workspace"], format=w.FORMAT_V4)
    root = load_compiled(Path(config["bundle"]).read_bytes(), **trust)
    template = prepare_compiled_template(root)
    binding = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    job = s.register_job(workspace, template, operation=op()).get("job")
    publisher = s.claim_publisher(workspace, job, operation=op())
    record = s.register_binding(publisher, binding, operation=op()).get("binding")
    generation = s.register_generation(publisher, record, binding, route=route,
        isolation="stable", operation=op()).get("generation")
    attempt = s.open_attempt(publisher, generation, binding, operation=op())
    owner = owner_for(binding)
    owner.open()
    session = x.begin_extraction(publisher, attempt, owner, operation=op())
    staged = []
    for _ in range(config["pages"]):
        item = session.stage()
        if item is None:
            break
        staged.append(item)
    for index in config["publish"]:
        session.publish(staged[index], operation=op())
    snapshot = c.checkpoint_snapshot(workspace, job, generation)
    facts.update(workspace=workspace.root, identity=workspace.identity, job=job,
        generation=generation, attempt=attempt.identity, session=owner.session_id,
        staged=[[i.start, i.stop, i.identity] for i in staged], members=members(snapshot),
        checkpoint=snapshot.checkpoint, frontier=snapshot.frontier)
    barrier("cut")
    hold()
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
job, generation = config["job"], config["generation"]
publisher = s.claim_publisher(workspace, job, operation=op())
for item in s.job_record(workspace, job).attempts:
    if item.terminal is None:
        s.interrupt_attempt(publisher, item.identity, operation=op())
latest = c.checkpoint_snapshot(workspace, job, generation)
facts["predecessor"] = latest.checkpoint
facts["before"] = members(latest)
owner = session = None
try:
    acceptance = x.accept_recovery(workspace, job, generation,
        checkpoint=latest.checkpoint, purpose="s14-history", values=values,
        seconds=600, **trust)
    attempt = s.open_attempt(publisher, generation, acceptance.binding, operation=op())
    facts["attempt"] = attempt.identity
    owner = owner_for(acceptance.binding)
    if cut == "precancel":
        facts["cancel"] = owner.cancel()
    owner.open()
    facts["session"] = owner.session_id
    session = x.begin_continuation(publisher, acceptance, attempt, owner, operation=op())
    facts["continued"] = True
    real_commit = w.commit
    def stop_after(connection):
        real_commit(connection)
        barrier("cut")
        hold()
    published = []
    def publish(items):
        for item in items:
            if cut == "reply" and not published:
                w.commit = stop_after
                facts["lost"] = [item.start, item.stop, item.identity]
                session.publish(item, operation=config["operation"])
            published.append(session.publish(item, operation=op()).get("checkpoint"))
            if cut == "extend" and item.start >= acceptance.reach:
                facts["extended"] = members(c.checkpoint_snapshot(workspace, job, generation))
                barrier("cut")
                hold()
    pages = 0
    while True:
        if session.ready and not session.reconciled:
            session.reconcile(operation=op())
            if cut == "barrier":
                barrier("cut")
                hold()
            publish(list(session.staged))
        items = session.stage()
        if items is None:
            break
        pages += 1
        if cut == "cancel" and pages == 1:
            facts["cancel"] = owner.cancel()
        if session.reconciled:
            publish(items)
    if session.ready and not session.reconciled:
        session.reconcile(operation=op())
        publish(list(session.staged))
    if cut == "end_reply":
        w.commit = stop_after
        session.end(operation=config["operation"])
    ended = session.end(operation=op())
    s.record_attempt(publisher, attempt, owner, operation=op())
    after = c.checkpoint_snapshot(workspace, job, generation)
    state = x.extraction_state(workspace, job, generation)
    facts.update(status="COMPLETE", end=dict(ended.result), members=members(after),
        checkpoint=after.checkpoint, frontier=after.frontier, holes=after.holes,
        materialized=session.materialized, matched=session.matched,
        observed=session.observed, known=state.known, coverage=state.complete_coverage,
        layers=[list(l) for l in after.layers], verify=verify_store(workspace))
    output = c.stored_output(workspace, job, generation, **trust)
    rows = []
    with c.SnapshotReader(workspace, after, output) as reader:
        for index in range(len(after.members)):
            table = reader.read(index).table
            rows.extend([[scalar(table.column(i)[j].as_py()) for i in
                range(table.num_columns)] for j in range(table.num_rows)])
    facts["rows"] = rows
except Exception as error:
    facts.update(status="REFUSED", error=type(error).__name__ + ":" + str(error)[:200])
    if session is not None:
        facts.update(matched=session.matched, observed=session.observed,
            ready=session.ready, reconciled=session.reconciled,
            materialized=session.materialized)
finally:
    if session is not None:
        session.close()
    if owner is not None:
        owner.close()
        facts["outcome"] = [owner.outcome.source, owner.outcome.transaction]
        if facts.get("status") == "REFUSED":
            # A refused attempt still records its own closed owner's layers.
            try:
                s.record_attempt(publisher, attempt, owner, operation=op())
                facts["recorded"] = True
            except Exception as error:
                facts["recorded"] = type(error).__name__ + ":" + str(error)[:120]
after = c.checkpoint_snapshot(workspace, job, generation)
facts.update(final_members=members(after), final_checkpoint=after.checkpoint,
    files=c.classify_files(workspace))
publisher.close()
workspace.close()
write_facts()
"""


def history_program():
    """The history worker with the shared typed scalar encoder of S01."""
    import inspect

    from _pietto_phase68_slice4_probe import s01

    head, gate = HISTORY.split("from pietto._project.project_compiled_loading", 1)
    prefix = (
        "import struct\nfrom decimal import Decimal\nfrom datetime import datetime\n"
        "from uuid import UUID\n" + inspect.getsource(s01.scalar) + "\n"
    )
    return head + prefix + "from pietto._project.project_compiled_loading" + gate


def _origin_check(data, origin, wheel):
    """Every imported pietto module is the source file or the wheel member."""
    import hashlib

    if origin == "installed":
        s13.installed_members(data, wheel)
        return
    for item in data["origins"].values():
        path = Path(item["path"])
        if not path.is_relative_to(ROOT / "src") or (
            hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
        ):
            raise ValueError("S14_SOURCE_ORIGIN")


def _spawn(interpreter, program, config_path, ledger, log, label):
    import subprocess

    from _pietto_phase68_slice8_probe import event
    from _pietto_target_conformance_resources import clean_environment

    child = subprocess.Popen(
        [str(interpreter), "-I", "-B", "-c", program, str(config_path)],
        env=clean_environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=log,
        text=True,
    )
    event(ledger, {"kind": "registered_worker", "pid": child.pid, "group": label})
    assert child.stdin is not None
    child.stdin.write("1")
    child.stdin.close()
    return child


def _reaped(ledger, child, code):
    from _pietto_phase68_slice8_probe import event

    event(ledger, {"kind": "worker_reaped", "pid": child.pid, "returncode": code})


# History name -> capture (page size, pages, published indexes) and the
# recovery steps: (page size, cut) per fresh process; None is a normal run.
HISTORIES = {
    "A_prefix_suffix": ((2, 1, [0]), [(3, None)]),
    "B_holes": ((2, 3, [0, 2]), [(3, None)]),
    "B_damage_value": ((2, 3, [0, 2]), [(3, None)]),
    "B_damage_coordinate": ((2, 3, [0, 2]), [(3, None)]),
    "C_reply_lost": ((2, 3, [0, 2]), [(3, "reply"), (2, None)]),
    "D_second_crash": ((2, 1, [0]), [(2, "extend"), (1, None)]),
    "E_end_reply_lost": ((2, 1, [0]), [(3, "end_reply")]),
    "F_barrier_crash": ((2, 3, [0, 2]), [(3, "barrier"), (1, None)]),
    "G_source_drift": ((2, 1, [0]), [(3, None), (3, None)]),
    "H_version_replaced": ((2, 1, [0]), [(3, None), (3, None)]),
    "I_cancel": ((2, 1, [0]), [(3, "cancel"), (3, None)]),
    "L_cancel_before_qualification": ((2, 1, [0]), [(3, "precancel"), (2, None)]),
}


def _damage(
    workspace_root, identity, job, generation, pin, producer, compatibility, kind
):
    """Coordinated damage of the LAST saved member: bytes, digest, descriptor and
    chunk row stay mutually consistent, so only reconciliation can see it."""
    import hashlib
    import sqlite3

    from pietto._project import project_job_capture as c
    from pietto._project import project_job_chunks as k
    from pietto._project import project_job_workspace as w
    from pietto._project.project_arrow_result import _arrow
    from pietto._project.project_result_ipc import IPCLimits, encode_ipc, open_ipc

    opened = w.open_workspace(workspace_root, expected_identity=identity)
    try:
        snapshot = c.checkpoint_snapshot(opened, job, generation)
        output = c.stored_output(
            opened,
            job,
            generation,
            expected_pin=pin,
            accepted_producer=producer,
            accepted_compatibility=compatibility,
        )
        member = snapshot.members[-1]
        directory = opened.directory(w.CHUNKS)
        try:
            data = k.read_chunk_file(
                directory, member.file, member.bytes, member.digest
            )
        finally:
            os.close(directory)
    finally:
        opened.close()
    _text, descriptor, frame = k.decode_chunk(data)
    rows = member.stop - member.start
    if kind == "coordinate":
        key = descriptor["coordinates"][0]
        last = k.read_coordinate(key[-1])
        if type(last) is not int:
            raise ValueError("S14_DAMAGE_COORDINATE_KIND")
        key[-1] = k.coordinate_wire(last + 1000)
    else:
        session = open_ipc(
            output.binding,
            frame,
            expected_rows=rows,
            ipc_limits=IPCLimits(k.MAX_FRAME_BYTES),
        )
        with session:
            table = _arrow().RecordBatchReader.from_stream(session).read_all()
        pa = _arrow()
        columns = []
        for index, column in enumerate(table.columns):
            values = column.to_pylist()
            if pa.types.is_integer(column.type) and values[0] is not None:
                values[0] = values[0] + 1
                column = pa.array(values, type=column.type)
            columns.append(column)
        changed = pa.table(columns, schema=table.schema)
        frame = encode_ipc(
            output.binding,
            pa.RecordBatchReader.from_batches(table.schema, changed.to_batches()),
            expected_rows=rows,
            ipc_limits=IPCLimits(k.MAX_FRAME_BYTES),
        )
    fields = {
        n: descriptor[n] for n in k.FIELDS - {"format", "frame_bytes", "frame_sha256"}
    }
    text, raw = k.encode_chunk(fields, frame)
    path = Path(workspace_root) / w.CHUNKS / member.file
    temporary = path.with_name(member.file + ".damage")
    temporary.write_bytes(raw)
    temporary.chmod(0o600)
    os.replace(temporary, path)
    connection = sqlite3.connect(Path(workspace_root) / w.DATABASE)
    try:
        connection.execute(
            "UPDATE chunk SET bytes = ?, digest = ?, descriptor = ? WHERE identity = ?",
            (len(raw), hashlib.sha256(raw).hexdigest(), text, member.chunk),
        )
        connection.commit()
    finally:
        connection.close()
    return {"member": [member.start, member.stop, member.chunk], "kind": kind}


def r2_histories(
    directory,
    ledger,
    interpreter,
    *,
    target,
    origin="source",
    wheel=None,
    only=None,
    shared=None,
):
    """Real per-route SIGKILL histories over R2_seven 39_values: original attempt
    death, holes, coordinated late-island damage, reply loss, repeated crashes,
    barrier crash, source drift, version replacement and cancellations. `shared`
    = (resource, providers) of a finished matrix group's live database."""
    import time

    import _pietto_phase68_slice10_probe as s10
    from _pietto_phase68_slice6_probe import setup as setup_general, manager, quoted
    from _pietto_phase68_slice6_probe import session_gone
    from _pietto_phase68_slice8_probe import event
    from _pietto_phase68_slice11_probe import kill, until
    from _pietto_phase68_slice14_check import check_history
    from _pietto_target_conformance_resources import Resources
    from pietto._project import project_job_store as s
    from pietto._project import project_job_workspace as w
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_schema import Scalar, scalar_wire

    directory.mkdir(mode=0o700)
    start_event = {
        "kind": "s14_histories_start",
        "directory": str(directory),
        "target": target,
        "origin": origin,
    }
    providers: Any = None
    if shared is None:
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
        event(ledger, start_event, source_db_lifecycle_starts=1)
    else:
        resource, providers = shared
        event(ledger, {**start_event, "shared_database": resource.name})
    report: dict[str, Any] = {
        "status": "STARTED",
        "target": target,
        "origin": origin,
        "histories": [],
    }
    report_path = directory / (PREFIX + "histories.json")
    started = time.monotonic()
    routes = ["mysql_rows"] if target == "mysql" else ["postgres_rows", "postgres_adbc"]
    namespace = "public" if target == "postgres" else "phase66"
    try:
        if shared is None:
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
        cell = {
            "group": "refined",
            "case": "R2_seven",
            "variant": "39_values",
            "excluded": False,
        }
        build = directory / (PREFIX + "reference-source")
        reference = s10.build_native_reference(build, target, cell, providers)
        if reference is None:
            raise ValueError("S14_HISTORY_REFERENCE")
        artifact, preparation, query, output, binding = reference
        built = build_compiled(artifact, guarded=preparation, refinement=query)
        bundle = directory / (PREFIX + "bundle.json")
        bundle.write_bytes(built.payload)
        bundle.chmod(0o600)
        provider = next(p for p in providers if p["name"] == "p68seven39_values")
        from _pietto_phase68_slice6_check import expected

        literal, ordered = expected(target, "R2_seven", "39_values", output.columns)
        oracle = {"rows": literal, "ordered": ordered}
        program = history_program()
        base = quoted(namespace, target) + "." + quoted(provider["backing"], target)
        registry = (
            quoted(namespace, target) + "." + quoted(provider["registry"], target)
        )
        common = {
            "origin": origin,
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
        }

        def mutate(change, restore=False):
            if target == "postgres":
                manager(
                    resource, f"ALTER TABLE {base} DISABLE TRIGGER p68_r2_immutable"
                )
            index = provider["backing"].rsplit("_", 1)[1]
            if target == "mysql":
                manager(
                    resource,
                    f"DROP TRIGGER {quoted(namespace, target)}."
                    f"{quoted('p68_r2_' + index + '_update', target)}",
                )
            manager(
                resource,
                f"UPDATE {base} SET {quoted('number', target)} = "
                f"{quoted('number', target)} {'-' if restore else '+'} 1"
                " WHERE p68_raw_id = 1",
            )
            if target == "postgres":
                manager(resource, f"ALTER TABLE {base} ENABLE TRIGGER p68_r2_immutable")
            else:
                manager(
                    resource,
                    f"CREATE TRIGGER {quoted(namespace, target)}."
                    f"{quoted('p68_r2_' + index + '_update', target)} BEFORE UPDATE ON "
                    f"{base} FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT="
                    "'immutable owned source'",
                )
            return change

        def run(label, config, *, cut=None):
            path = directory / (label + "-config.json")
            _write_private(path, {**common, **config})
            runtime = directory / (label + "-runtime")
            runtime.mkdir(mode=0o700)
            facts = directory / (label + "-facts.json")
            with (directory / (label + "-worker.log")).open("w") as log:
                child = _spawn(interpreter, program, path, ledger, log, label)
                try:
                    if cut:
                        until(child, "cut", 180)
                        code, _ = kill(child)
                    else:
                        code = child.wait(timeout=300)
                finally:
                    if child.poll() is None:
                        kill(child)
                    _reaped(ledger, child, child.returncode)
            path.unlink()
            if code != (-9 if cut else 0):
                raise ValueError("S14_HISTORY_WORKER:" + label + ":" + str(code))
            data = json.loads(facts.read_text())
            _origin_check(data, origin, wheel)
            return data

        for route in routes:
            for name, (capture, steps) in HISTORIES.items():
                if only is not None and name not in only:
                    continue
                label = PREFIX + route + "-" + name
                size, pages, publish = capture
                base_config = {"route": route, "runtime_cwd": None}
                record: dict[str, Any] = {"route": route, "history": name, "steps": []}
                report["histories"].append(record)
                first = run(
                    label + "-capture",
                    {
                        **base_config,
                        "role": "capture",
                        "page_size": size,
                        "pages": pages,
                        "publish": publish,
                        "workspace": str(directory / (label + "-workspace")),
                        "runtime_cwd": str(directory / (label + "-capture-runtime")),
                        "facts": str(directory / (label + "-capture-facts.json")),
                    },
                    cut="capture",
                )
                first["session_gone"] = session_gone(resource, first["session"])
                record["capture"] = first
                store = {
                    k: first[k] for k in ("workspace", "identity", "job", "generation")
                }
                if name.startswith("B_damage"):
                    record["damage"] = _damage(
                        first["workspace"],
                        first["identity"],
                        first["job"],
                        first["generation"],
                        built.pin,
                        built.producer,
                        tuple(built.compatibility),
                        name.rsplit("_", 1)[1],
                    )
                for number, (page_size, cut) in enumerate(steps):
                    if name == "G_source_drift" and number == 0:
                        record["drift"] = mutate("number+1 at raw id 1")
                    if name == "G_source_drift" and number == 1:
                        mutate("restored", restore=True)
                    if name == "H_version_replaced":
                        manager(
                            resource,
                            f"UPDATE {registry} SET revision = "
                            f"'{'r2' if number == 0 else 'r1'}'",
                        )
                    operation = s.new_operation()
                    step = run(
                        label + "-recover" + str(number),
                        {
                            **base_config,
                            **store,
                            "role": "recover",
                            "page_size": page_size,
                            "cut": cut,
                            "operation": operation,
                            "runtime_cwd": str(
                                directory
                                / (label + "-recover" + str(number) + "-runtime")
                            ),
                            "facts": str(
                                directory
                                / (label + "-recover" + str(number) + "-facts.json")
                            ),
                        },
                        cut=cut if cut not in (None, "cancel", "precancel") else None,
                    )
                    if step.get("session") is not None:
                        step["session_gone"] = session_gone(resource, step["session"])
                    if cut in ("reply", "end_reply"):
                        from pietto._project import project_job_extraction as x

                        opened = w.open_workspace(
                            store["workspace"], expected_identity=store["identity"]
                        )
                        try:
                            queried = s.query_operation(opened, operation)
                            step["queried"] = (
                                None
                                if queried is None
                                else [
                                    queried.kind,
                                    queried.observation,
                                    dict(queried.result),
                                ]
                            )
                            state = x.extraction_state(
                                opened, store["job"], store["generation"]
                            )
                            step["state"] = [
                                state.checkpoint,
                                state.known,
                                state.complete_coverage,
                                state.committed,
                            ]
                        finally:
                            opened.close()
                    record["steps"].append(step)
                    report_path.write_text(
                        json.dumps(report, indent=2, default=str) + "\n"
                    )
                check_history(record, route, oracle)
                record["checked"] = True
                report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
                print(target, route, name, "checked", flush=True)
        report["status"] = "PASS"
    except BaseException as error:
        report.update(
            status="FAILED",
            error_kind=type(error).__name__,
            error=resource.without_secrets(str(error)),
        )
        raise
    finally:
        report["cleanup"] = (
            resource.cleanup()
            if shared is None
            else {"status": "SHARED_WITH_MATRIX_GROUP", "database": resource.name}
        )
        report["seconds"] = time.monotonic() - started
        report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        event(
            ledger,
            {
                "kind": "s14_histories_terminal",
                "directory": str(directory),
                "status": report["status"],
                "cleanup": report["cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


R1 = r"""
from pietto._project import project_job_capture as c, project_job_replay as r
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_chunks as k
from pietto._project.project_compiled_schema import scalar_read
results = []
for item in config["stores"]:
    workspace = w.open_workspace(item["workspace"], expected_identity=item["identity"])
    publisher = s.claim_publisher(workspace, item["job"], operation=s.new_operation())
    try:
        snapshot = c.checkpoint_snapshot(workspace, item["job"], item["generation"])
        acceptance = r.accept_saved_read(workspace, item["job"], item["generation"],
            checkpoint=snapshot.checkpoint, consumer=r.new_consumer(),
            scope="complete_capture", extent=snapshot.frontier,
            purpose="s14-r1-source-offline", route=item["route"],
            values=tuple(scalar_read(v).value for v in item["values"]),
            expected_pin=item["pin"], accepted_producer=item["producer"],
            accepted_compatibility=tuple(item["compatibility"]), seconds=3600,
            batch_rows=4096)
        r.register_consumer(publisher, acceptance, operation=s.new_operation())
        replay = r.open_replay(publisher, acceptance, operation=s.new_operation())
        rows, occurrences, coordinates = [], [], []
        while True:
            got = replay.next(4096, operation=s.new_operation())
            if not isinstance(got, r.Delivery):
                end = got
                break
            data = pa.record_batch(got.batch)
            rows.extend([[scalar(data.column(i)[j].as_py()) for i in
                range(data.num_columns)] for j in range(data.num_rows)])
            occurrences.extend([list(o) for o in got.occurrences])
            coordinates.extend([[k.coordinate_wire(v) for v in key]
                for key in got.coordinates or ()])
            got.batch.close()
            replay.acknowledge(got, operation=s.new_operation())
        replay.close()
        results.append({"key": item["key"], "checkpoint": snapshot.checkpoint,
            "rows": rows, "occurrences": occurrences, "coordinates": coordinates,
            "attempts": sorted({m.attempt for m in snapshot.members}),
            "end": [end.terminal, end.scope, end.extent, end.observed_end,
                [list(h) for h in end.holes]],
            "layers": [list(x) for x in end.layers]})
    except Exception as error:
        results.append({"key": item["key"],
            "error": type(error).__name__ + ":" + str(error)[:200]})
    finally:
        publisher.close()
        workspace.close()
loaded = sorted(n for n in sys.modules if n.split(".")[0] in DRIVERS)
origins = {}
for name, module in tuple(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
        path = Path(filename).resolve()
        origins[name] = {"path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
retain_raw({"results": results, "forbidden_calls": forbidden_calls,
    "connections": connections, "installed_drivers": installed_drivers,
    "loaded_drivers": loaded, "origins": origins, "prefix": sys.prefix})
"""


def r1_program():
    """S13's Arrow-only header (socket refusal, driver inventory), the S10
    source-free boundary and the S14 recovered-result reader."""
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
    return s13.REPLAY_HEADER + prefix + boundary + R1


def r1_offline(directory, ledger, interpreter, stores, *, origin, wheel=None):
    """One fresh Arrow-only process reads every recovered store with no source."""
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_target_conformance_resources import clean_environment

    runtime = directory / (PREFIX + "r1-" + origin + "-runtime")
    runtime.mkdir(mode=0o700)
    raw = directory / (PREFIX + "r1-" + origin + "-raw.json")
    private = directory / (PREFIX + "r1-" + origin + "-input.json")
    _write_private(
        private,
        {
            "origin": origin,
            "library_source": str(ROOT / "src"),
            "removed_query_project": str(directory / "never-a-query-project"),
            "stores": stores,
            "runtime_cwd": str(runtime),
            "raw": str(raw),
        },
    )
    with (directory / (PREFIX + "r1-" + origin + ".log")).open("wb") as log:
        status = worker_process(
            [str(interpreter), "-I", "-B", "-c", r1_program(), str(private)],
            clean_environment(),
            ledger,
            log,
            origin=origin,
            group="s14-r1-" + origin,
            directory=directory,
            seconds=1800,
        )
    private.unlink(missing_ok=True)
    if status:
        raise ValueError("S14_R1_OFFLINE_WORKER")
    data = json.loads(raw.read_text())
    if origin == "installed":
        s13.installed_members(data, wheel)
    return data


def matrix_r1(report, directory, ledger, interpreter, *, wheel=None):
    """After the group's database is gone: every recovered store, per origin, in
    one fresh Arrow-only process; compared with the oracle-checked recovery."""
    from _pietto_phase68_slice14_check import check_r1

    checked = {}
    for origin in sorted(
        {item["origin"] for item in report["records"] if "origin" in item}
    ):
        stores, expected = [], {}
        for index, item in enumerate(report["records"]):
            if (
                item.get("origin") != origin
                or "recover" not in item
                or item["recover"] == "NO_R2_BASIS"
                or "drift" in item
            ):
                continue
            capture = {r["route"]: r["s14"] for r in item["capture"]["results"]}
            handoff = json.loads(
                Path(
                    item["capture"]["raw"][: -len("-raw.json")] + "-handoff.json"
                ).read_text()
            )
            trust = {
                k: handoff[k] for k in ("pin", "producer", "compatibility", "values")
            }
            raw = json.loads(Path(item["recover"]["raw"]).read_text())
            for record in raw["results"]:
                key = "%d:%s:%s" % (index, item["entry"], record["route"])
                facts = capture[record["route"]]
                stores.append(
                    {
                        "key": key,
                        "workspace": facts["workspace"],
                        "identity": facts["identity"],
                        "job": facts["job"],
                        "generation": facts["generation"],
                        "route": record["route"],
                        **trust,
                    }
                )
                expected[key] = {
                    "rows": record["rows"],
                    "generation": facts["generation"],
                    "attempts": sorted({m[2] for m in record["s14"]["members"]}),
                    "checkpoint": record["s14"]["checkpoint"],
                }
        if stores:
            data = r1_offline(
                directory, ledger, interpreter, stores, origin=origin, wheel=wheel
            )
            check_r1(data, expected)
            checked[origin] = len(stores)
    report["r1"] = checked
    return checked


def old_runtime(directory, ledger, interpreter, old_wheel):
    """The published S13 workspace owner (archived wheel bytes) meets a v4
    workspace: it must refuse before SQLite and leave the directory unchanged."""
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_target_conformance_resources import clean_environment
    from pietto._project import project_job_workspace as w

    directory.mkdir(mode=0o700)
    root = directory / (PREFIX + "v4-workspace")
    workspace = w.create_workspace(str(root), format=w.FORMAT_V4)
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
            origin="archived-s13-wheel",
            group="s14-old-runtime",
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
        raise ValueError("S14_OLD_RUNTIME_ACCEPTED_V4")
    return data


def checker_damage(matrix_directory, histories_directory):
    """Independent-checker discrimination over REAL raw: every damaged copy keeps
    superficial shape but changes one law-bearing fact and must be rejected."""
    import copy

    from _pietto_phase68_slice14_check import (
        check_capture,
        check_history,
        check_recovery,
    )

    report = json.loads((matrix_directory / (PREFIX + "r2-group.json")).read_text())
    item = next(i for i in report["records"] if i.get("checked"))
    capture_raw = json.loads(Path(item["capture"]["raw"]).read_text())
    recover_raw = json.loads(Path(item["recover"]["raw"]).read_text())
    capture = capture_raw["results"][0]
    recovery = next(r for r in recover_raw["results"] if r["route"] == capture["route"])
    check_capture(capture, item["cell"], None)
    check_recovery(recovery, capture["s14"])
    outcomes = {}

    def damaged(name, base, change, check):
        value = copy.deepcopy(base)
        change(value)
        try:
            check(value)
        except AssertionError as error:
            outcomes[name] = str(error)
            return
        raise ValueError("S14_CHECKER_FALSE_PASS:" + name)

    def relabel(r):
        kept = next(m for m in r["s14"]["members"] if m[2] != r["s14"]["attempt"])
        kept[2] = r["s14"]["attempt"]

    def gap(r):
        new = [m for m in r["s14"]["members"] if m[2] == r["s14"]["attempt"]]
        r["s14"]["members"].remove(new[0])

    def frozen(r):
        r["s14"]["frozen"][0] += 1

    def barrier(r):
        r["s14"]["reconciled"]["position"] = r["s14"]["frozen"][1] - 1

    def prior(r):
        for pair in r["s14"]["layers"]:
            if pair[0] == "attempt_terminal":
                pair[1] = "OUTCOME"

    def eof(r):
        r["s14"]["end"]["observed"] += 1

    for name, change in (
        ("producing_attempt", relabel),
        ("hole", gap),
        ("frontier", frozen),
        ("barrier", barrier),
        ("prior_unknown", prior),
        ("eof", eof),
    ):
        damaged(name, recovery, change, lambda v: check_recovery(v, capture["s14"]))

    def plan(c):
        c["s14"]["published"][0][0] = "chk-" + "0" * 32

    damaged(
        "capture_plan", capture, plan, lambda v: check_capture(v, item["cell"], None)
    )
    histories = json.loads(
        (histories_directory / (PREFIX + "histories.json")).read_text()
    )
    record = next(
        h
        for h in histories["histories"]
        if h.get("checked") and h["history"] == "B_holes"
    )
    oracle_rows = record["steps"][-1]["rows"]
    oracle = {"rows": oracle_rows, "ordered": False}
    check_history(record, record["route"], oracle)

    def payload(h):
        row = h["steps"][-1]["rows"][3]
        cell = next(v for v in row if v["kind"] == "int")
        cell["value"] = str(int(cell["value"]) + 1)

    def hole_closed(h):
        h["capture"]["members"].append(
            [2, 4, h["capture"]["attempt"], "chk-" + "1" * 32]
        )

    damaged(
        "history_payload_bit",
        record,
        payload,
        lambda v: check_history(v, v["route"], oracle),
    )
    damaged(
        "history_saved_membership",
        record,
        hole_closed,
        lambda v: check_history(v, v["route"], oracle),
    )
    return outcomes


def empty_refined_check(directory):
    """Real Arrow/IPC (no database): a REFINED schema-only EOF member written by
    the capture writer is read by SnapshotReader, accepted by verify_store and
    by a recovery acceptance's full member check. Only the opened-owner gate and
    its native description are synthetic (SYNTHETIC_OPEN_OWNER)."""
    from pietto._project import project_job_capture as c
    from pietto._project import project_job_extraction as x
    from pietto._project import project_job_store as s
    from pietto._project.project_execution import compiled_output
    from pietto._project.project_job_store_verification import verify_store

    directory = Path(directory)
    template, built, values = refined_template(directory / "bound")
    workspace, job, publisher, binding, record, generation = store(
        directory / "workspace", template, values
    )
    real = (x._fresh, x.describe)
    x._fresh, x.describe = (lambda owner: None), synthetic_describe
    try:
        attempt = s.open_attempt(publisher, generation, binding, operation=op())
        session = x.begin_extraction(publisher, attempt, owner(binding), operation=op())
        output, refinement, _program = compiled_output(binding)
        session._binding = c.arrow_output(
            job, generation, output, refinement, "postgres_rows"
        ).binding
        staged = session._materialize(
            workspace, session._encode(None, 0), 0, 0, 0, [], "EOF"
        )
        session.publish(staged, operation=op())
        snapshot = c.checkpoint_snapshot(workspace, job, generation)
        stored = c.stored_output(workspace, job, generation, **trust(built))
        with c.SnapshotReader(workspace, snapshot, stored) as reader:
            checked = reader.read(0)
        summary = verify_store(workspace)
        fresh = takeover(workspace, job, publisher)
        acceptance = accept(workspace, job, generation, built, values)
        result = {
            "rows": checked.table.num_rows,
            "coordinates": list(checked.coordinates or ()),
            "terminal": checked.terminal,
            "known": acceptance.known,
            "verify": summary,
        }
        fresh.close()
    finally:
        x._fresh, x.describe = real
        workspace.close()
    if (
        result["rows"]
        or result["coordinates"]
        or result["terminal"] != "EOF"
        or result["known"] != 0
    ):
        raise ValueError("S14_EMPTY_REFINED_MEMBER")
    return result
