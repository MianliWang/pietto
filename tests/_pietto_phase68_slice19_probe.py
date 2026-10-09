"""S19 whole-matrix, joint-history, equal-guarantee and CI-shaped consumer
families; import acquires nothing.

Each family composes the original owners (S10 case worker and literal/native
checkers, S14 R2 capture/recovery, S15 relay/adoption, S16 publication, S17
runtime/collection, S18 installation/compatibility) in registered fresh
interpreters (`-I -B`, clean environment, unrelated working directory):

- matrix: one owned database per interleaved part of the whole declared matrix
  of a target or per claimant of its shared queue (each declaration claimed
  once). General and guarded fixtures are prepared once; one reference
  bundle per declared case serves every route and (origin, entry) cell; each
  route runs in its own selected installation. An ordinary or guarded cell is
  one checked attempt; an admitted R2 cell is an abandoned R2 capture and a
  new-process recovery whose full re-enumeration is also the matrix record.
  After the source database is removed one fresh Arrow-only process per origin
  reads every recovered store.
- storage/tuning/consumer/controls: see their docstrings; the joint family is
  the unchanged S18 `native()` (called directly by the script).

Producers write raw facts only; `_pietto_phase68_slice19_check` and the
original layer checkers judge them.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any

from _pietto_phase68_slice14_probe import _write_private

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice19-"
CELLS = (
    ("source", "live"),
    ("source", "bundle"),
    ("installed", "live"),
    ("installed", "bundle"),
)
ROUTES = {"postgres": ("postgres_rows", "postgres_adbc"), "mysql": ("mysql_rows",)}
REQUEST_SECONDS = 360


def _owned_database(directory, ledger, target, kind):
    """A disposable owned source database, registered in the family ledger."""
    from _pietto_phase68_slice8_probe import event
    from _pietto_target_conformance_resources import Resources

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
        {"kind": kind + "_start", "directory": str(directory), "target": target},
        source_db_lifecycle_starts=1,
    )
    return resource


def fixtures(resource):
    """General (S06) and guarded (S07 via S16) sources in one database, with the
    MySQL performance-schema grants both query roles need; returns the general
    and guard providers."""
    import _pietto_phase68_slice10_probe as s10
    import _pietto_phase68_slice16_probe as s16
    from _pietto_phase68_slice6_probe import manager, setup as setup_general

    if resource.target == "mysql":
        manager(resource, "USE phase66")
    general = setup_general(resource)
    s16.guard_sources(resource)
    guard = s10.guard_providers(resource)
    if resource.target == "mysql":
        for user in ("pietto_query", "pietto_subset"):
            for table in ("threads", "events_transactions_current"):
                manager(
                    resource,
                    "GRANT SELECT ON performance_schema."
                    + table
                    + " TO '"
                    + user
                    + "'@'%'",
                )
    return general, guard


def _exclusion(directory, target, cell, case, providers):
    """The original owner's own refusal of a target-excluded declaration."""
    import _pietto_phase68_slice10_probe as s10
    from _pietto_phase68_slice7_cases import case_preparation

    key = [target, cell["group"], cell["case"], cell["variant"]]
    build = directory / (PREFIX + "excluded-" + "-".join(map(str, key[1:])))
    if case is not None:
        try:
            case_preparation(build, target, case)
        except ValueError as error:
            return {
                "excluded": key,
                "owner": "case_preparation",
                "observed": type(error).__name__,
            }
        raise ValueError("S19_LOST_GUARD_TARGET_EXCLUSION")
    if s10.build_native_reference(build, target, cell, providers) is not None:
        raise ValueError("S19_LOST_ORIGINAL_TARGET_EXCLUSION")
    return {"excluded": key, "owner": "original", "observed": "NONE"}


def _r2_config(directory, label, config, options, workspace, role, page, **extra):
    """One S14 R2 worker configuration (capture page 2 / recovery page 3)."""
    name = label + ("" if role == "capture" else "-recover")
    runtime = directory / (name + "-runtime")
    runtime.mkdir(mode=0o700)
    return {
        **config,
        "runtime_cwd": str(runtime),
        "live_project": str(directory / (name + "-source")),
        "options": {**options, "page_size": page},
        "raw": str(directory / (name + "-raw.json")),
        "s14": {"role": role, "workspace": str(workspace), "pages": 3, **extra},
    }


def _latest_checkpoint(root, facts):
    """The generation's latest checkpoint, read through its own owner."""
    from pietto._project import project_job_capture as c
    from pietto._project import project_job_workspace as w

    opened = w.open_workspace(str(root), expected_identity=facts["identity"])
    try:
        return c.checkpoint_snapshot(
            opened, facts["job"], facts["generation"]
        ).checkpoint
    finally:
        opened.close()


def queue_work(declarations, admitted, *, joint):
    """A queue claimant's walk over the whole declared matrix, as (manifest
    index, declaration): the R2-admitted class (the long cells) first, each
    class in manifest order. The joint part walks only that class, so its joint
    history starts when the class is exhausted, not after the queue drains."""
    keyed = [
        (index, cell, (cell["group"], cell["case"], cell["variant"]) in admitted)
        for index, cell in enumerate(declarations)
    ]
    keyed.sort(key=lambda item: not item[2])
    return [(index, cell) for index, cell, r2 in keyed if r2 or not joint]


def claim(queue, target, index) -> bool:
    """Whether this part takes declaration `index` of `target` off the shared
    queue: the first exclusive creation of its claim file wins. A claim is
    dispatch, not completion; only checked records count."""
    try:
        os.close(
            os.open(
                queue / ("%s-%d.claim" % (target, index)),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        )
    except FileExistsError:
        return False
    return True


def matrix(
    directory,
    ledger,
    *,
    target,
    interpreters,
    saved_interpreter,
    wheel,
    part=(0, 1),
    cells=CELLS,
    selected=None,
    drift=False,
    joint=False,
    queue=None,
):
    """One owned database for the interleaved part `part` of the whole declared
    matrix of `target` (see the module docstring), or, with a shared `queue`
    directory, for every declaration this part claims there (`queue_work`);
    `drift` adds the guarded fresh-guard violation item on installed:bundle per
    route and `joint` runs `joint_extensions` (J01, J02, J09) in the same live
    database last."""
    import _pietto_phase68_slice10_probe as s10
    import _pietto_phase68_slice14_probe as s14
    from _pietto_phase68_slice6_probe import session_gone
    from _pietto_phase68_slice7_cases import manifest as guard_manifest
    from _pietto_phase68_slice7_probe import fill
    from _pietto_phase68_slice8_probe import event, worker_process
    from _pietto_phase68_slice10_check import check_matrix_origin, check_matrix_record
    from _pietto_phase68_slice14_check import (
        check_capture,
        check_r1,
        check_recovery,
        check_refused_recovery,
    )
    from _pietto_target_conformance_resources import clean_environment
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_schema import Scalar, scalar_wire

    directory.mkdir(mode=0o700)
    guards = {c["name"]: c for c in guard_manifest()}
    admitted = {(c["group"], c["case"], c["variant"]) for c in s14.r2_families(target)}
    declarations = [
        c
        for c in s10.native_manifest(target)
        if selected is None or (c["group"], c["case"], c["variant"]) in selected
    ]
    if queue is None:
        declarations = declarations[part[0] :: part[1]]
    if not declarations:
        raise ValueError("S19_EMPTY_MATRIX_PART")
    resource = _owned_database(directory, ledger, target, "s19_matrix")
    report: dict[str, Any] = {
        "status": "STARTED",
        "target": target,
        "part": list(part),
        "cells": [list(c) for c in cells],
        "denominator": declarations if queue is None else [],
        "records": [],
        "timings": {},
    }
    report_path = directory / (PREFIX + "matrix.json")
    private = directory / (PREFIX + "private-input.json")
    programs = {"MATRIX": s10.case_worker_program(), "R2": s14.r2_case_program()}
    stores: dict[str, list] = {"source": [], "installed": []}
    expected: dict[str, dict] = {"source": {}, "installed": {}}
    started = time.monotonic()

    def run(label, config, kind):
        interpreter = interpreters[config["routes"][0]]
        public = {k: v for k, v in config.items() if k not in ("password", "ca_path")}
        _write_private(directory / (label + "-handoff.json"), public)
        _write_private(private, config)
        mark = time.monotonic()
        try:
            with (directory / (label + "-worker.log")).open("wb") as log:
                status = worker_process(
                    [str(interpreter), "-I", "-B", "-c", programs[kind], str(private)],
                    clean_environment(),
                    ledger,
                    log,
                    origin=config["origin"],
                    group="s19-matrix-" + kind,
                    directory=directory,
                    seconds=2 * REQUEST_SECONDS + 240,
                )
        finally:
            private.unlink(missing_ok=True)
        if status:
            raise ValueError("S19_MATRIX_WORKER:" + label + ":" + str(status))
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
        # The parent's observations stay separate from the child raw (never rewritten).
        Path(str(raw)[: -len("-raw.json")] + "-sessions.json").write_text(
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
        return data, {
            "raw": str(raw),
            "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "seconds": time.monotonic() - mark,
            "attempts": [r["outcome"]["attempt"] for r in data["results"]],
        }

    try:
        mark = time.monotonic()
        resource.acquire()
        general, guard = fixtures(resource)
        report["timings"]["fixtures"] = time.monotonic() - mark
        order = (
            enumerate(declarations)
            if queue is None
            else queue_work(declarations, admitted, joint=joint)
        )
        work = [(index, cell, False) for index, cell in order]
        if drift:
            pages = next(
                c
                for c in s10.native_manifest(target)
                if c["group"] == "guarded" and c["case"] == "refined_pages"
            )
            work.append((len(declarations), pages, True))
        violation = guards["refined_violation_outside_page"]
        for index, cell, drifted in work:
            if queue is not None and not drifted:
                if not claim(queue, target, index):
                    continue
                report["denominator"].append(cell)
            key = (cell["group"], cell["case"], cell["variant"])
            case = guards.get(cell["case"]) if cell["group"] == "guarded" else None
            providers = guard if case is not None else general
            if cell["excluded"]:
                report["records"].append(
                    _exclusion(directory, target, cell, case, providers)
                )
                continue
            mark = time.monotonic()
            build = directory / (PREFIX + str(index) + "-reference-source")
            reference = s10.build_native_reference(build, target, cell, providers)
            if reference is None:
                raise ValueError("S19_MISSING_ORIGINAL_REFERENCE")
            artifact, preparation, query, _output, _binding = reference
            built = build_compiled(artifact, guarded=preparation, refinement=query)
            bundle = directory / (PREFIX + str(index) + "-bundle.json")
            bundle.write_bytes(built.payload)
            bundle.chmod(0o600)
            shutil.rmtree(build)
            report["timings"]["reference:" + str(index)] = time.monotonic() - mark
            options = {} if case is None else dict(case["options"])
            obligation = "R2" if key in admitted else "MATRIX"
            if drifted and obligation != "R2":
                raise ValueError("S19_DRIFT_NOT_R2")
            base = {
                "target": target,
                "cell": cell,
                "providers": providers,
                "build_helpers": str(ROOT / "tests"),
                "library_source": str(ROOT / "src"),
                "removed_query_project": str(build),
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
                "request_seconds": REQUEST_SECONDS,
            }
            combos = [("installed", "bundle")] if drifted else list(cells)
            for route in ROUTES[target]:
                for origin, entry in combos:
                    if case is not None:
                        fill(
                            resource,
                            case["lhs"],
                            case["rhs"],
                            wide_text=options.get("wide_text", False),
                        )
                    label = "%s%d-%s-%s-%s%s" % (
                        PREFIX,
                        index,
                        route,
                        origin,
                        entry,
                        "-drift" if drifted else "",
                    )
                    item: dict[str, Any] = {
                        "cell": [target, route, *key, entry, origin, obligation]
                    }
                    if drifted:
                        item = {"drift": item["cell"]}
                    config = {
                        **base,
                        "origin": origin,
                        "entry": entry,
                        "routes": [route],
                        "options": options,
                    }
                    if obligation == "MATRIX":
                        runtime = directory / (label + "-runtime")
                        runtime.mkdir(mode=0o700)
                        data, facts = run(
                            label,
                            {
                                **config,
                                "runtime_cwd": str(runtime),
                                "live_project": str(directory / (label + "-source")),
                                "raw": str(directory / (label + "-raw.json")),
                            },
                            "MATRIX",
                        )
                        check_matrix_record(
                            data["results"][0], cell, reference, case=case
                        )
                        item["attempt"] = facts
                    else:
                        workspace = directory / (label + "-workspace")
                        data, item["capture"] = run(
                            label,
                            _r2_config(
                                directory,
                                label,
                                config,
                                options,
                                workspace,
                                "capture",
                                2,
                            ),
                            "R2",
                        )
                        check_capture(data["results"][0], cell, case)
                        captured = data["results"][0]["s14"]
                        if captured is None:
                            item["basis"] = "NO_R2_BASIS"
                        else:
                            if drifted:
                                fill(resource, violation["lhs"], violation["rhs"])
                            r2 = _r2_config(
                                directory,
                                label,
                                config,
                                options,
                                workspace,
                                "recover",
                                3,
                                identity=captured["identity"],
                                routes={
                                    route: {
                                        "job": captured["job"],
                                        "generation": captured["generation"],
                                    }
                                },
                            )
                            data, item["recover"] = run(label + "-recover", r2, "R2")
                            record = data["results"][0]
                            if drifted:
                                check_refused_recovery(record, captured)
                                after = _latest_checkpoint(workspace, captured)
                                item["after_refusal"] = [captured["checkpoint"], after]
                                if after != captured["checkpoint"]:
                                    raise ValueError("S19_REFUSAL_CHANGED_CHECKPOINT")
                            else:
                                check_matrix_record(record, cell, reference, case=case)
                                check_recovery(record, captured)
                                backup = directory / (label + "-backup.sqlite")
                                s14._backup(
                                    str(workspace), captured["identity"], backup
                                )
                                item["backup"] = str(backup)
                                store_key = label[len(PREFIX) :]
                                stores[origin].append(
                                    {
                                        "key": store_key,
                                        "workspace": captured["workspace"],
                                        "identity": captured["identity"],
                                        "job": captured["job"],
                                        "generation": captured["generation"],
                                        "route": route,
                                        "pin": built.pin,
                                        "producer": built.producer,
                                        "compatibility": built.compatibility,
                                        "values": base["values"],
                                    }
                                )
                                expected[origin][store_key] = {
                                    "rows": record["rows"],
                                    "generation": captured["generation"],
                                    "attempts": sorted(
                                        {m[2] for m in record["s14"]["members"]}
                                    ),
                                    "checkpoint": record["s14"]["checkpoint"],
                                }
                    item["checked"] = True
                    report["records"].append(item)
                    report_path.write_text(json.dumps(report, indent=2) + "\n")
                    print(
                        target,
                        *(item["cell"] if "cell" in item else item["drift"]),
                        "checked",
                        flush=True,
                    )
        if joint:
            mark = time.monotonic()
            report["joint"] = joint_extensions(
                directory,
                ledger,
                target=target,
                resource=resource,
                providers=general,
                interpreters=interpreters,
                saved=saved_interpreter,
                wheel=wheel,
            )
            report["timings"]["joint"] = time.monotonic() - mark
        mark = time.monotonic()
        report["source_cleanup"] = resource.cleanup()
        report["timings"]["source_cleanup"] = time.monotonic() - mark
        report["r1"] = {}
        for origin in ("source", "installed"):
            if not stores[origin]:
                continue
            mark = time.monotonic()
            data = s14.r1_offline(
                directory,
                ledger,
                saved_interpreter,
                stores[origin],
                origin=origin,
                wheel=wheel,
            )
            check_r1(data, expected[origin])
            report["r1"][origin] = {
                "stores": len(stores[origin]),
                "loaded_drivers": data["loaded_drivers"],
                "installed_drivers": data["installed_drivers"],
                "connections": data["connections"],
                "seconds": time.monotonic() - mark,
            }
        report["status"] = "CHECKED"
    except BaseException as error:
        report.update(
            status="FAILED",
            error_kind=type(error).__name__,
            error=resource.without_secrets(str(error)),
        )
        raise
    finally:
        private.unlink(missing_ok=True)
        if "source_cleanup" not in report:
            report["source_cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - started
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        event(
            ledger,
            {
                "kind": "s19_matrix_terminal",
                "directory": str(directory),
                "status": report["status"],
                "cleanup": report["source_cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


# ---------------------------------------------------------------------------
# Joint native histories in a matrix part's live database before it is removed:
# J01/J09 (S14 holes, repeated recovery, damaged saved members, drift and
# revision) and J02 (a sink commit whose reply is lost before local
# confirmation, before the source ends) per route in its installed bundle. The
# 12-cell joined floor is the unchanged S18 native() family.

J02_HOOK = r"""
    if config.get("cut_confirm"):
        real_confirm = d.StreamSession.confirm
        confirms = []
        def cut_confirm(self, issued, *, operation):
            confirms.append([issued.start, issued.stop])
            if len(confirms) == config["cut_confirm"]:
                cut_snapshot = c.checkpoint_snapshot(workspace, job, generation)
                facts.update(workspace=workspace.root, identity=workspace.identity,
                    job=job, generation=generation, attempt=attempt.identity,
                    session=owner.session_id, stream=stream, sink=handle.root,
                    sink_identity=handle.identity, namespace=handle.namespace,
                    lost=[issued.start, issued.stop], confirms=confirms,
                    sink_rows=sink_rows(handle), position=self.position,
                    members=members(cut_snapshot), checkpoint=cut_snapshot.checkpoint,
                    frontier=cut_snapshot.frontier, observed=capture.observed,
                    terminal=capture.terminal)
                barrier("cut")
                hold()
            return real_confirm(self, issued, operation=operation)
        d.StreamSession.confirm = cut_confirm
"""

J02_ADOPT = r"""
from pietto._project import project_job_capture as c, project_job_store as s
from pietto._project import project_job_workspace as w, project_job_delivery as d
from pietto._project import project_job_sink as k
from pietto._project.project_compiled_schema import scalar_read
from pietto._project.project_job_store_verification import verify_store
def op():
    return s.new_operation()
def effects(handle):
    return [list(row) for row in handle.use().execute("SELECT position, digest,"
        " commit_identity, sequence, payload FROM effect ORDER BY position")]
results = {}
for item in config["stores"]:
    workspace = w.open_workspace(item["workspace"], expected_identity=item["identity"])
    publisher = s.claim_publisher(workspace, item["job"], operation=op())
    handle = k.open_sink(item["sink"], expected_identity=item["sink_identity"])
    try:
        values = tuple(scalar_read(v).value for v in item["values"])
        window = dict(purpose="s19-j02", route=item["route"], values=values,
            seconds=3600, batch_rows=4096, expected_pin=item["pin"],
            accepted_producer=item["producer"],
            accepted_compatibility=tuple(item["compatibility"]))
        before = effects(handle)
        sink = d.accept_sink(handle, instance=handle.identity, namespace=handle.namespace,
            epoch=handle.epoch, retention=handle.retention, purpose="s19-j02", seconds=3600)
        # Fresh read permission naming the window adopted before the cut.
        cut = d.accept_window(workspace, item["job"], item["generation"],
            checkpoint=item["cut_checkpoint"], **window)
        session = d.open_stream(publisher, item["stream"], sink, window=cut,
            operation=op())
        reopened = session.position
        first = session.next(config["rows"], operation=op())
        first_statuses = session.send(first)
        session.confirm(first, operation=op())
        latest = c.checkpoint_snapshot(workspace, item["job"], item["generation"])
        adopted = session.adopt(d.accept_window(workspace, item["job"],
            item["generation"], checkpoint=latest.checkpoint, **window), operation=op())
        issued = []
        while True:
            got = session.next(config["rows"], operation=op())
            if isinstance(got, d.Waiting):
                waiting = [got.terminal, got.position, got.observed_end,
                    got.complete_coverage]
                break
            statuses = session.send(got)
            session.confirm(got, operation=op())
            issued.append([got.start, got.stop,
                [statuses[p] for p in range(got.start, got.stop)]])
        session.close()
        # The same effect key with another occurrence's payload must conflict.
        layout = handle.use().execute(
            "SELECT layout FROM effect WHERE position = 0").fetchone()[0]
        donor = handle.use().execute(
            "SELECT payload FROM effect WHERE position = 1").fetchone()[0]
        reply = handle.submit(k.SinkEffect(sink=handle.identity,
            namespace=handle.namespace, epoch=handle.epoch, retention=handle.retention,
            workspace=workspace.identity, generation=item["generation"], position=0,
            layout=layout, payload=donor))
        state = d.stream_state(workspace, item["stream"])
        results[item["key"]] = {"before": before, "reopened": reopened,
            "first": [first.start, first.stop, sorted(first.prior),
                {str(p): v for p, v in first_statuses.items()}],
            "adopted": dict(adopted.result), "issued": issued, "waiting": waiting,
            "conflict": reply.status, "final": effects(handle),
            "position": state.position, "windows": [list(x) for x in state.windows],
            "checkpoint": latest.checkpoint, "frontier": latest.frontier,
            "members": [[m.start, m.stop, m.attempt, m.chunk] for m in latest.members],
            "verify": verify_store(workspace)}
    finally:
        handle.close()
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
retain_raw({"results": results, "connections": connections,
    "installed_drivers": installed_drivers, "loaded_drivers": loaded,
    "origins": origins, "prefix": sys.prefix})
"""

J01_HISTORIES = (
    "B_holes",
    "B_damage_value",
    "B_damage_coordinate",
    "C_reply_lost",
    "D_second_crash",
    "G_source_drift",
    "H_version_replaced",
)


def j02_relay_program():
    """S15's native relay/recovery program with a cut at the `cut_confirm`-th
    local confirmation: the sink has committed, the reply is never confirmed."""
    import _pietto_phase68_slice12_probe as s12
    import _pietto_phase68_slice15_probe as s15

    anchor = "    steps, first, delivered = [], None, 0\n"
    return s12._replace(s15.NATIVE, anchor, J02_HOOK.lstrip("\n") + anchor)


def _j02(directory, ledger, *, route, resource, common, interpreter, saved, wheel):
    """Relay before EOF, cut after the second sink commit, S14 recovery in a new
    process, then a fresh driver-free adopter resends the lost window by the
    same identity, adopts the recovered checkpoint and delivers the rest."""
    import _pietto_phase68_slice13_probe as s13
    import _pietto_phase68_slice14_probe as s14
    import _pietto_phase68_slice15_probe as s15
    from _pietto_phase68_slice6_probe import session_gone
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_phase68_slice11_probe import kill, until
    from _pietto_target_conformance_resources import clean_environment

    label = PREFIX + "j02-" + route

    def spawn(name, program, config, *, cut=False):
        path = directory / (name + "-config.json")
        runtime = directory / (name + "-runtime")
        runtime.mkdir(mode=0o700)
        facts = directory / (name + "-facts.json")
        _write_private(
            path, {**common, **config, "runtime_cwd": str(runtime), "facts": str(facts)}
        )
        with (directory / (name + "-worker.log")).open("w") as log:
            child = s14._spawn(interpreter, program, path, ledger, log, name)
            try:
                if cut:
                    until(child, "cut", 900)
                    code, _ = kill(child)
                else:
                    code = child.wait(timeout=1800)
            finally:
                if child.poll() is None:
                    kill(child)
                s14._reaped(ledger, child, child.returncode)
        path.unlink()
        if code != (-9 if cut else 0):
            raise ValueError("S19_J02_WORKER:" + name + ":" + str(code))
        data = json.loads(facts.read_text())
        s14._origin_check(data, "installed", wheel)
        data["returncode"], data["reaped"] = code, True
        data["session_gone"] = session_gone(resource, data["session"])
        return data

    relay = spawn(
        label + "-relay",
        j02_relay_program(),
        {
            "route": route,
            "role": "relay",
            "origin": "installed",
            "entry": "bundle",
            "page_size": 2,
            "rows": 2,
            "deliver_steps": 64,
            "cut_confirm": 2,
            "workspace": str(directory / (label + "-workspace")),
            "sink": str(directory / (label + "-sink")),
            "namespace": "s19.j02." + route,
            "live_project": str(directory / (label + "-unused-source")),
        },
        cut=True,
    )
    store = {k: relay[k] for k in ("workspace", "identity", "job", "generation")}
    recovered = spawn(
        label + "-recover",
        s15.NATIVE,
        {
            **store,
            "route": route,
            "role": "recover",
            "origin": "installed",
            "entry": "bundle",
            "page_size": 3,
        },
    )
    raw = directory / (label + "-adopt-raw.json")
    path = directory / (label + "-adopt-config.json")
    runtime = directory / (label + "-adopt-runtime")
    runtime.mkdir(mode=0o700)
    _write_private(
        path,
        {
            "runtime_cwd": str(runtime),
            "library_source": str(ROOT / "src"),
            "origin": "installed",
            "raw": str(raw),
            "rows": 3,
            "stores": [
                {
                    **store,
                    "key": route,
                    "route": route,
                    "values": common["values"],
                    "pin": common["pin"],
                    "producer": common["producer"],
                    "compatibility": common["compatibility"],
                    "sink": relay["sink"],
                    "sink_identity": relay["sink_identity"],
                    "stream": relay["stream"],
                    "cut_checkpoint": relay["checkpoint"],
                }
            ],
        },
    )
    with (directory / (label + "-adopt.log")).open("wb") as log:
        status = worker_process(
            [str(saved), "-I", "-B", "-c", s13.REPLAY_HEADER + J02_ADOPT, str(path)],
            clean_environment(),
            ledger,
            log,
            origin="installed",
            group="s19-j02-adopt",
            directory=directory,
            seconds=1800,
        )
    path.unlink()
    if status:
        raise ValueError("S19_J02_ADOPT:" + route + ":" + str(status))
    adopt = json.loads(raw.read_text())
    s14._origin_check(adopt, "installed", wheel)
    backup = directory / (label + "-backup.sqlite")
    s14._backup(store["workspace"], store["identity"], backup)
    return {
        "relay": relay,
        "recover": recovered,
        "adopt": adopt["results"][route],
        "adopt_process": {
            k: adopt[k] for k in ("connections", "installed_drivers", "loaded_drivers")
        },
        "backup": str(backup),
    }


def joint_extensions(
    directory,
    ledger,
    *,
    target,
    resource,
    providers,
    interpreters,
    saved,
    wheel,
):
    """In a live owned database before it is removed: per route in its installed
    bundle, the S14 J01_HISTORIES (holes, repeated recovery and damaged-member
    refusals; J09 drift and revision) and J02 over R2_seven 39_values."""
    import _pietto_phase68_slice10_probe as s10
    import _pietto_phase68_slice14_probe as s14
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_schema import Scalar, scalar_wire

    cell = {
        "group": "refined",
        "case": "R2_seven",
        "variant": "39_values",
        "excluded": False,
    }
    reference = s10.build_native_reference(
        directory / (PREFIX + "joint-reference-source"), target, cell, providers
    )
    if reference is None:
        raise ValueError("S19_JOINT_REFERENCE")
    artifact, preparation, query, _output, _binding = reference
    built = build_compiled(artifact, guarded=preparation, refinement=query)
    bundle = directory / (PREFIX + "joint-bundle.json")
    bundle.write_bytes(built.payload)
    bundle.chmod(0o600)
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
        "bundle": str(bundle),
        "pin": built.pin,
        "producer": built.producer,
        "compatibility": list(built.compatibility),
        "values": [
            scalar_wire(Scalar(v.tag.value, v.value)) for v in artifact.fixed_values
        ],
    }
    found: dict[str, Any] = {"j01": {}, "j02": {}}
    for route in ROUTES[target]:
        j01 = s14.r2_histories(
            directory / (PREFIX + "j01-" + route),
            ledger,
            interpreters[route],
            target=target,
            origin="installed",
            wheel=wheel,
            only=list(J01_HISTORIES),
            shared=(resource, providers),
            routes=[route],
        )
        found["j01"][route] = {
            "status": j01["status"],
            "histories": j01["histories"],
        }
        found["j02"][route] = _j02(
            directory,
            ledger,
            route=route,
            resource=resource,
            common=common,
            interpreter=interpreters[route],
            saved=saved,
            wheel=wheel,
        )
    return found


# ---------------------------------------------------------------------------
# Storage joint history (no source database): one connected v7 workspace with
# real checked Arrow chunks (SIMULATED_NATIVE_IO owners, real IPC, chunk files,
# SQLite, publication, sink, runtime and collector), driven through registered
# child interpreters that are SIGKILLed at named protocol steps. The original
# S16/S17 child programs are reused verbatim (read from their test modules);
# only the Arrow-free substitution of those tests is absent here.

STORAGE_HEADER = r"""
import json, os, signal, sys, time, hashlib, sqlite3, threading
from pathlib import Path
config = json.loads(sys.argv[1])
os.chdir(config["cwd"])
if config["origin"] == "source":
    sys.path.insert(0, config["library_source"])
sys.path.append(config["tests"])
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c, project_job_chunks as k
from pietto._project import project_job_publication as p
from pietto._project import project_job_collection as col
from pietto._project import project_job_runtime as rt
from pietto._project import project_job_replay as r
def barrier(name):
    sys.stdout.write(name + "\n")
    sys.stdout.flush()
def hold():
    while True:
        time.sleep(60)
def emit(value):
    found = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
            path = Path(filename).resolve()
            found[name] = {"path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    Path(config["raw"]).write_text(json.dumps({**value, "origins": found,
        "prefix": sys.prefix}, default=str))
    sys.stdout.write(json.dumps(value, default=str) + "\n")
    sys.stdout.flush()
def runtime():
    return rt.open_runtime(config["workspace"], expected_identity=config["identity"],
        policy=rt.Policy())
"""

ATTACH16 = r"""
def attach(*, claim=True):
    workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
    publisher = None
    if claim:
        publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
    return workspace, publisher
def acceptance(workspace):
    return p.accept_publication(workspace, config["job"], config["generation"],
        checkpoint=config["checkpoint"], closing=config["closing"], purpose="s19-storage",
        route="postgres_rows", isolation="stable", values=tuple(config["values"]),
        expected_pin=config["pin"], accepted_producer=config["producer"],
        accepted_compatibility=tuple(config["compatibility"]), seconds=600)
"""

ATTACH17 = r"""
def attach():
    return w.open_workspace(config["workspace"], expected_identity=config["identity"])
"""

STORAGE_SETUP = r"""
import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice16_probe as s16
import _pietto_phase68_slice17_probe as probe17
from pietto._project import project_job_delivery as d, project_job_sink as sk
from pietto._project.project_execution_template import bind_values
base = Path(config["directory"])
template, built = s12.seven_template(base / "build", precision=39)
trust = (built.pin, built.producer, built.compatibility)
plans = {}
probe17.arrow_native(plans)
workspace = w.create_workspace(config["workspace"], format=w.FORMAT_V7)
W = workspace.root
binding0 = bind_values(template, ())
def op():
    return s.new_operation()
def rows(*indexes):
    return [s12.SEVEN_ROWS[i] for i in indexes]
def job():
    j = s.register_job(workspace, template, operation=op()).get("job")
    publisher = s.claim_publisher(workspace, j, operation=op())
    record = s.register_binding(publisher, binding0, operation=op()).get("binding")
    g = s.register_generation(publisher, record, binding0, route="postgres_rows",
        isolation="stable", operation=op()).get("generation")
    return j, g, publisher
def members(snapshot):
    return [[m.start, m.stop, m.attempt, m.chunk] for m in snapshot.members]
def direct(name, batches, close=None):
    # A caller-run checked capture (SIMULATED_NATIVE_IO, real Arrow/IPC/chunks);
    # `close` overrides the owner's terminal fields (SYNTHETIC_CLOSED_OWNER).
    j, g, publisher = job()
    attempt, owner = s12.attempt_owner(publisher, g, binding0,
        s12.Plan(batches, s12.SEVEN_CODES), None)
    capture = c.begin_capture(publisher, attempt, owner, operation=op())
    # v7: every chunk claim belongs to an admission (a caller-run granted unit).
    capture.admission = runtime_.grant(j, unit("CAPTURE", j, g))
    checkpoints = []
    while True:
        staged = capture.stage()
        if staged is None:
            break
        result = capture.publish(staged, operation=op())
        checkpoints.append([result.get("checkpoint"), result.get("frontier")])
    owner._qualification = s16.SIMULATED_QUALIFICATION
    owner.context = s16.SIMULATED_CONTEXT
    if close:
        s16.close_owner(owner, capture.observed, **close)
    capture.end(operation=op())
    s.record_attempt(publisher, attempt, owner, operation=op())
    runtime_.release(capture.admission)
    snapshot = c.checkpoint_snapshot(workspace, j, g)
    out = {"job": j, "generation": g, "closing": attempt.identity,
        "checkpoint": snapshot.checkpoint, "frontier": snapshot.frontier,
        "checkpoints": checkpoints, "members": members(snapshot),
        "close": close or {}}
    return out, publisher
def unit(mode, j, g, **fields):
    base_ = dict(mode=mode, root=W, workspace=workspace.identity, job=j, generation=g,
        trust=trust, values=(), seconds=1800)
    if mode in ("CAPTURE", "RELAY", "RECOVER"):
        base_.update(source=probe17.source(), durable=8 * 1024 * 1024)
    base_.update(fields)
    return rt.Unit(**base_)
runtime_ = rt.open_runtime(W, expected_identity=workspace.identity, policy=rt.Policy())
captured = {}
a, holder = direct("A", [rows(0, 1), rows(2, 3), rows(4, 0), rows(1, 2)])
holder.close()
captured["A"] = a
# J10: one durable prefix per generation, different remote closing outcomes.
VARIANTS = {"E_ack": None, "E_unknown": {"transaction": "UNKNOWN"},
    "E_source": {"source": "FAILED", "transaction": "ROLLBACK_ACK", "delivery": "FAILED",
        "primary": ("read", "SimulatedReadError")},
    "E_cleanup": {"cleanup_errors": [("close", "SimulatedCloseError")]}}
handle = sk.create_sink(config["sink"], namespace="s19.storage", epoch=1,
    retention_seconds=86400)
sink_ = d.accept_sink(handle, instance=handle.identity, namespace=handle.namespace,
    epoch=1, retention=handle.retention, purpose="s19-storage", seconds=3600)
for name, close in VARIANTS.items():
    item, publisher = direct(name, [rows(0, 1), rows(2, 3)], close)
    # Provisional effects of every committed occurrence before any publication.
    window = d.accept_window(workspace, item["job"], item["generation"],
        checkpoint=item["checkpoint"], purpose="s19-storage", route="postgres_rows",
        values=(), expected_pin=built.pin, accepted_producer=built.producer,
        accepted_compatibility=built.compatibility, seconds=3600, batch_rows=4096)
    stream = d.register_stream(publisher, window, sink_, operation=op()).get("stream")
    session = d.open_stream(publisher, stream, sink_, operation=op())
    session.adopt(window, operation=op())
    delivered = []
    while True:
        got = session.next(2, operation=op())
        if isinstance(got, d.Waiting):
            break
        statuses = session.send(got)
        session.confirm(got, operation=op())
        delivered.append([got.start, got.stop, sorted(statuses.values())])
    session.close()
    try:
        acceptance_ = p.accept_publication(workspace, item["job"], item["generation"],
            checkpoint=item["checkpoint"], closing=item["closing"], purpose="s19-j10",
            route="postgres_rows", isolation="stable", values=(),
            expected_pin=built.pin, accepted_producer=built.producer,
            accepted_compatibility=built.compatibility, seconds=600)
        prepared = p.prepare_publication(publisher, acceptance_, operation=op())
        result = p.publish_generation(publisher, prepared, operation=op())
        item["publication"] = ["PUBLISHED", result.observation]
    except w.JobStoreError as error:
        item["publication"] = ["REFUSED", str(error)]
    item.update(stream=stream, delivered=delivered)
    publisher.close()
    captured[name] = item
handle.close()
for name in ["B1", "B2", "N", "R"] + ["G%d" % i for i in range(1, 8)]:
    item, publisher = direct(name, [rows(0, 1), rows(2)])
    publisher.close()
    captured[name] = item
runtime_.close()
emit({"workspace": W, "identity": workspace.identity, "sink": handle.root,
    "sink_identity": handle.identity, "pin": built.pin, "producer": built.producer,
    "compatibility": list(built.compatibility), "captured": captured})
workspace.close()
"""

J03_FIRST = r"""
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
accepted = r.accept_saved_read(workspace, config["job"], config["generation"],
    checkpoint=config["checkpoint"], consumer=r.new_consumer(), scope="committed_prefix",
    extent=config["extent"], purpose="s19-j03", route="postgres_rows", values=(),
    expected_pin=config["pin"], accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]), seconds=3600, batch_rows=2)
retention = r.register_consumer(publisher, accepted, operation=s.new_operation()).get(
    "retention")
session = r.open_replay(publisher, accepted, operation=s.new_operation())
first = session.next(2, operation=s.new_operation())
session.acknowledge(first, operation=s.new_operation())
second = session.next(2, operation=s.new_operation())
Path(config["cut_facts"]).write_text(json.dumps({"consumer": accepted.consumer,
    "retention": retention, "acked": [first.start, first.stop],
    "issued": [second.start, second.stop],
    "occurrences": [list(o) for o in second.occurrences]}))
barrier("cut")
hold()
"""

J03_SECOND = r"""
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
before = r.consumer_state(workspace, config["consumer"])
accepted = r.accept_saved_read(workspace, config["job"], config["generation"],
    checkpoint=config["checkpoint"], consumer=config["consumer"], scope="committed_prefix",
    extent=config["extent"], purpose="s19-j03", route="postgres_rows", values=(),
    expected_pin=config["pin"], accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]), seconds=3600, batch_rows=3)
session = r.open_replay(publisher, accepted, operation=s.new_operation())
deliveries = []
while True:
    got = session.next(3, operation=s.new_operation())
    if isinstance(got, r.SavedScopeEnd):
        end = [got.terminal, got.acknowledged, got.extent]
        break
    deliveries.append([got.start, got.stop, [list(o) for o in got.occurrences]])
    session.acknowledge(got, operation=s.new_operation())
    got.batch.close()
session.close()
state = r.consumer_state(workspace, config["consumer"])
emit({"before": [list(x) for x in before.acknowledged], "deliveries": deliveries,
    "end": end, "acknowledged": [list(x) for x in state.acknowledged],
    "checkpoint": state.checkpoint, "extent": state.extent})
"""

CONSUMER_STATE = r"""
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
state = r.consumer_state(workspace, config["consumer"])
found = p.publication(workspace, config["job"], config["generation"])
query = s.query_operation(workspace, config["operation"]) if config.get("operation") else None
protected = sorted(c.protected_chunks(workspace, config["job"]))
emit({"acknowledged": [list(x) for x in state.acknowledged], "checkpoint": state.checkpoint,
    "extent": state.extent, "publication": None if found is None else [found.checkpoint,
    found.extent, found.members, found.closing, found.retention, found.operation],
    "query": None if query is None else [query.kind, query.observation, dict(query.result)],
    "protected": protected})
"""

COLLECT = r"""
workspace = attach()
for job, generation in config.get("retire", ()):
    holder = s.claim_publisher(workspace, job, operation=s.new_operation())
    col.retire_generation(holder, generation, operation=s.new_operation())
    holder.close()
before = col.charged(workspace)
opened = runtime()
report = opened.collect()
after = col.charged(workspace)
opened.close()
emit({"decided": [list(x) for x in report.decided], "removed": [list(x) for x in report.removed],
    "resumed": [list(x) for x in report.resumed], "busy": list(report.busy),
    "blocked": [[g, [list(x) for x in rs]] for g, rs in report.blocked],
    "refused": [list(x) for x in report.refused], "charged": [before, after]})
"""

LATE_READ = r"""
workspace = attach()
try:
    output = c.stored_output(workspace, config["job"], config["generation"],
        expected_pin=config["pin"], accepted_producer=config["producer"],
        accepted_compatibility=tuple(config["compatibility"]))
    snapshot = c.checkpoint_snapshot(workspace, config["job"], config["generation"])
    with c.SnapshotReader(workspace, snapshot, output) as reader:
        reader.read(0)
    outcome = "READ"
except w.JobStoreError as error:
    outcome = str(error)
emit({"outcome": outcome, "ns": time.monotonic_ns()})
"""

J08_PRESSURE = r"""
import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice17_probe as probe17
from pietto._project import project_job_sink as sk
from pietto._project.project_execution_template import bind_values
base = Path(config["directory"])
template, built = s12.seven_template(base / "build-j08", precision=39)
trust = (built.pin, built.producer, built.compatibility)
plans = {}
probe17.arrow_native(plans)
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
binding0 = bind_values(template, ())
def rows(*indexes):
    return [s12.SEVEN_ROWS[i] for i in indexes]
def job(batches):
    j = s.register_job(workspace, template, operation=s.new_operation()).get("job")
    publisher = s.claim_publisher(workspace, j, operation=s.new_operation())
    record = s.register_binding(publisher, binding0, operation=s.new_operation()).get(
        "binding")
    g = s.register_generation(publisher, record, binding0, route="postgres_rows",
        isolation="stable", operation=s.new_operation()).get("generation")
    publisher.close()
    plans[g] = (batches, s12.SEVEN_CODES)
    return j, g
def unit(mode, j, g, **fields):
    base_ = dict(mode=mode, root=workspace.root, workspace=workspace.identity, job=j,
        generation=g, trust=trust, values=(), seconds=1800, source=probe17.source(),
        durable=8 * 1024 * 1024)
    base_.update(fields)
    return rt.Unit(**base_)
opened = rt.open_runtime(workspace.root, expected_identity=workspace.identity,
    policy=rt.Policy(connections=2, workers=2, queue=8))
handle = sk.create_sink(config["sink"], namespace="s19.j08", epoch=1,
    retention_seconds=86400)
target = [handle.root, handle.identity, handle.namespace, handle.epoch, handle.retention]
handle.close()
lock = sqlite3.connect(target[0] + "/sink.sqlite", isolation_level=None, timeout=5)
lock.execute("BEGIN IMMEDIATE")
gate = probe17.Gate()
slow_job = job([rows(0, 1), rows(2, 3), rows(4)])
fast_job = job([rows(0), gate, rows(1)])
waiting_job = job([rows(0)])
slow = opened.submit(unit("RELAY", *slow_job, sink=rt.SinkTarget(*target, 0.2), rows=2,
    batch_rows=2))
fast = opened.submit(unit("CAPTURE", *fast_job))
stalled = opened.wait_activity(slow, "WAITING_FOR_DOWNSTREAM", 300)
assert gate.entered.wait(120)
queued = opened.submit(unit("CAPTURE", *waiting_job))
# The control thread classifies the queued unit; observe that state itself.
limit = time.monotonic() + 120
saturated = opened.query(queued)
while saturated.state != "WAITING_FOR_ADMISSION" and time.monotonic() < limit:
    time.sleep(0.01)
    saturated = opened.query(queued)
receipt = opened.cancel(queued)
cancelled = opened.wait(queued, 300)
gate.released.set()
progressed = opened.wait(fast, 300)
# A deadline stops a blocked fetch without a durable cancel (control serviced).
late_gate = probe17.Gate()
deadline_job = job([late_gate, rows(0)])
deadline = opened.submit(unit("CAPTURE", *deadline_job, seconds=20))
assert late_gate.entered.wait(120)
stopped = opened.wait(deadline, 300)
attempts = workspace.use().execute("SELECT count(*) FROM attempt").fetchone()[0]
open_admissions = workspace.use().execute("SELECT count(*) FROM admission a WHERE NOT"
    " EXISTS (SELECT 1 FROM admission_settlement x WHERE x.admission = a.identity)"
    ).fetchone()[0]
Path(config["cut_facts"]).write_text(json.dumps({"slow": [slow, *slow_job],
    "fast": [fast, *fast_job], "queued": [queued, *waiting_job],
    "stalled": [stalled.activity, dict(stalled.counters)],
    "saturated": [saturated.state, saturated.limiting], "receipt": receipt["signal"],
    "cancelled": [cancelled.terminal, cancelled.durable_cancel],
    "progressed": [progressed.terminal, progressed.failure],
    "deadline": [deadline, stopped.terminal, stopped.durable_cancel,
        [e for _n, e in stopped.events]], "attempts": attempts,
    "open_admissions": open_admissions, "epoch": opened.owner.epoch}))
barrier("cut")
hold()
"""

J08_RECONCILE = r"""
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
attempts = workspace.use().execute("SELECT count(*) FROM attempt").fetchone()[0]
opened = runtime()
first = opened.reconcile()
second = opened.reconcile()
after = workspace.use().execute("SELECT count(*) FROM attempt").fetchone()[0]
settlements = [list(x) for x in workspace.use().execute(
    "SELECT * FROM admission_settlement ORDER BY admission")]
opened.close()
emit({"first": [list(x) for x in first], "second": [list(x) for x in second],
    "attempts_before": attempts, "attempts_after": after, "settlements": settlements,
    "epoch": opened.owner.epoch})
"""

J09_REFUSALS = r"""
workspace = w.open_workspace(config["workspace"], expected_identity=config["identity"])
publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
trust = dict(expected_pin=config["pin"], accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]))
out = {}
accepted = r.accept_saved_read(workspace, config["job"], config["generation"],
    checkpoint=config["checkpoint"], consumer=r.new_consumer(), scope="complete_capture",
    extent=config["extent"], purpose="s19-j09", route="postgres_rows", values=(),
    seconds=1, batch_rows=4096, **trust)
time.sleep(1.5)
try:
    r.register_consumer(publisher, accepted, operation=s.new_operation())
    out["expired"] = "REGISTERED"
    r.open_replay(publisher, accepted, operation=s.new_operation())
    out["expired"] = "ACCEPTED"
except w.JobStoreError as error:
    out["expired"] = out.get("expired", "") + ":" + str(error)
try:
    r.accept_saved_read(workspace, config["job"], config["generation"],
        checkpoint=config["checkpoint"], consumer=r.new_consumer(),
        scope="complete_capture", extent=config["extent"], purpose="s19-j09",
        route="postgres_rows", values=(), seconds=60, batch_rows=4096,
        **{**trust, "accepted_compatibility": ("0" * 64,)})
    out["compiled"] = "ACCEPTED"
except Exception as error:
    out["compiled"] = type(error).__name__ + ":" + str(error)
publisher.close()
emit(out)
"""


def _source_program(module: str, name: str) -> str:
    """A child program constant from an original test module, read from its
    source text (no pytest import in the harness interpreter)."""
    import ast

    tree = ast.parse((ROOT / "tests" / (module + ".py")).read_text())
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            return ast.literal_eval(node.value)
    raise ValueError("S19_PROGRAM:" + module + ":" + name)


def _child(directory, ledger, interpreter, program, config, name):
    """A registered child with barrier/emit lines on stdout; the caller reaps."""
    import subprocess

    from _pietto_phase68_slice8_probe import event
    from _pietto_target_conformance_resources import clean_environment

    cwd = directory / (name + "-cwd")
    cwd.mkdir(mode=0o700)
    value = {
        "cwd": str(cwd),
        "library_source": str(ROOT / "src"),
        "tests": str(ROOT / "tests"),
        "raw": str(directory / (name + "-raw.json")),
        **config,
    }
    log = (directory / (name + "-stderr.log")).open("w")
    child = subprocess.Popen(
        [str(interpreter), "-I", "-B", "-c", program, json.dumps(value)],
        env=clean_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=log,
        text=True,
    )
    log.close()
    event(ledger, {"kind": "registered_worker", "pid": child.pid, "group": name})
    return child


def _finish(child, name, directory, seconds=900):
    """Normal completion within `seconds`; a failure carries the stderr tail."""
    import subprocess

    from _pietto_phase68_slice11_probe import kill

    try:
        stdout, _ = child.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        kill(child)
        raise
    if child.returncode:
        tail = (directory / (name + "-stderr.log")).read_text()[-4000:]
        raise ValueError("S19_CHILD:" + name + ":" + str(child.returncode) + ":" + tail)
    return stdout


def _reaped(ledger, child, name):
    from _pietto_phase68_slice8_probe import event

    event(
        ledger,
        {
            "kind": "worker_reaped",
            "pid": child.pid,
            "returncode": child.returncode,
            "group": name,
        },
    )


def storage(directory, ledger, interpreter, *, origin, capture_interpreter, wheel=None):
    """The connected storage history of the module comment for one origin. Every
    step runs in the clean Arrow-only installation `interpreter` (no drivers)
    except J08, whose coordinator units meet S18's selected-route preflight and
    therefore run in the postgres_rows installation `capture_interpreter` with
    SIMULATED_NATIVE_IO owners that never connect."""
    import _pietto_phase68_slice14_probe as s14
    from _pietto_phase68_slice11_probe import kill, until
    from pietto._project.project_job_store import new_operation

    directory.mkdir(mode=0o700)
    started = time.monotonic()
    ws = directory / (PREFIX + "storage-workspace")

    report: dict[str, Any] = {"status": "STARTED", "origin": origin, "steps": []}
    report_path = directory / (PREFIX + "storage.json")
    h16 = "test_phase68_slice16_process_histories"
    h17 = "test_phase68_slice17_process_histories"
    head16 = STORAGE_HEADER + ATTACH16
    head17 = STORAGE_HEADER + ATTACH17

    def step(
        name, program, config, *, cut=None, evidence="REAL_COMPONENT", python=None
    ):
        child = _child(
            directory, ledger, python or interpreter, program, config, PREFIX + name
        )
        record: dict[str, Any] = {
            "step": name,
            "evidence": evidence,
            "config": {
                k: config[k] for k in ("cut", "operation", "prepare") if k in config
            },
        }
        mark = time.monotonic()
        try:
            if cut is not None:
                until(child, cut, 600)
                code, _ = kill(child)
                record.update(evidence="SIGKILL", returncode=code, reaped=True)
                if code != -9:
                    raise ValueError("S19_STORAGE_CUT:" + name + ":" + str(code))
            else:
                stdout = _finish(child, PREFIX + name, directory)
                record["emitted"] = json.loads(stdout.strip().splitlines()[-1])
                record["returncode"] = child.returncode
        finally:
            if child.poll() is None:
                kill(child)
            _reaped(ledger, child, PREFIX + name)
        record["seconds"] = time.monotonic() - mark
        raw = directory / (PREFIX + name + "-raw.json")
        if raw.exists():
            data = json.loads(raw.read_text())
            s14._origin_check(data, origin, wheel)
            record["origins_checked"] = len(data["origins"])
        report["steps"].append(record)
        report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        return record

    try:
        setup = step(
            "setup",
            STORAGE_HEADER + STORAGE_SETUP,
            {
                "origin": origin,
                "directory": str(directory),
                "workspace": str(ws),
                "sink": str(directory / (PREFIX + "storage-sink")),
            },
        )["emitted"]
        report["setup"] = setup
        cap = setup["captured"]
        common = {
            "origin": origin,
            "workspace": setup["workspace"],
            "identity": setup["identity"],
            "pin": setup["pin"],
            "producer": setup["producer"],
            "compatibility": setup["compatibility"],
            "values": [],
        }

        def gen(name, **extra):
            item = cap[name]
            return {
                **common,
                "job": item["job"],
                "generation": item["generation"],
                "checkpoint": item["checkpoint"],
                "closing": item["closing"],
                **extra,
            }

        # J03: fixed committed prefix [0, 4) of A's second checkpoint.
        ck2 = next(ck for ck, frontier in cap["A"]["checkpoints"] if frontier == 4)
        cut_facts = directory / (PREFIX + "j03-cut.json")
        step(
            "j03-first",
            STORAGE_HEADER + J03_FIRST,
            gen("A", checkpoint=ck2, extent=4, cut_facts=str(cut_facts)),
            cut="cut",
        )
        report["j03_cut"] = json.loads(cut_facts.read_text())
        consumer = report["j03_cut"]["consumer"]
        step(
            "j03-second",
            STORAGE_HEADER + J03_SECOND,
            gen("A", checkpoint=ck2, extent=4, consumer=consumer),
        )
        # J04: pre-commit and post-commit/reply cuts of A's publication, each
        # followed by a fresh-process query; then a notification loss on N.
        cut16 = _source_program(h16, "CUT")
        for cut_name, query_name in (
            ("P3_inserted_before_commit", "j04-query-precommit"),
            ("P4_committed_before_response", "j04-query-postcommit"),
        ):
            operation = new_operation()
            step(
                "j04-" + cut_name,
                head16 + cut16,
                gen("A", cut=cut_name, prepare=new_operation(), operation=operation),
                cut="cut",
            )
            step(
                query_name,
                STORAGE_HEADER + CONSUMER_STATE,
                gen("A", consumer=consumer, operation=operation),
            )
        go = directory / (PREFIX + "j04-notify-go")
        outcome = directory / (PREFIX + "j04-notify-outcome.json")
        notify = _child(
            directory,
            ledger,
            interpreter,
            head16 + _source_program(h16, "NOTIFY"),
            gen("N", operation=new_operation(), go=str(go), outcome=str(outcome)),
            PREFIX + "j04-notify",
        )
        try:
            until(notify, "returned", 600)
            assert notify.stdout is not None
            notify.stdout.close()
            go.write_text("")
            notify.wait(timeout=60)
        finally:
            if notify.poll() is None:
                kill(notify)
            _reaped(ledger, notify, PREFIX + "j04-notify")
        report["j04_notify"] = json.loads(outcome.read_text())
        step(
            "j04-query-notify",
            STORAGE_HEADER + CONSUMER_STATE,
            gen("N", consumer=consumer),
        )
        # J05: cancel-first (a live holder makes a second writer meet the real
        # PUBLISHER_BUSY, then dies) and publish-first, across processes.
        held = directory / (PREFIX + "j05-held.json")
        holder = _child(
            directory,
            ledger,
            interpreter,
            head16 + _source_program(h16, "HOLDER"),
            gen("B1", held=str(held)),
            PREFIX + "j05-holder",
        )
        try:
            until(holder, "prepared", 600)
            step("j05-busy", head16 + _source_program(h16, "CLAIM"), gen("B1"))
        finally:
            code, _ = kill(holder)
            _reaped(ledger, holder, PREFIX + "j05-holder")
        report["j05_holder"] = {"returncode": code, **json.loads(held.read_text())}
        step(
            "j05-cancel", head16 + _source_program(h16, "CLAIM"), gen("B1", cancel=True)
        )
        step("j05-resume", head16 + _source_program(h16, "RESUME"), gen("B1"))
        step(
            "j05-publish",
            head16 + _source_program(h16, "PUBLISH"),
            gen("B2", operation=new_operation()),
        )
        step(
            "j05-cancel-after",
            head16 + _source_program(h16, "CLAIM"),
            gen("B2", cancel=True),
        )
        # J07 first (S17's K1 cut stops at the first commit once any tombstone
        # exists): the five collection cuts on G1..G5, each SIGKILLed, then a
        # replacement collection and a repeat that must find nothing.
        cut17 = _source_program(h17, "CUT")
        for index, cut_name in enumerate(
            (
                "K1_decision_uncommitted",
                "K2_committed_before_unlink",
                "K3_unlinked_before_sync",
                "K4_synced_before_observation",
                "K5_observed_before_reply",
            ),
            start=1,
        ):
            name = "G%d" % index
            step(
                "j07-" + cut_name,
                head17 + "for job, generation in config['retire']:\n"
                "    holder = s.claim_publisher(attach(), job, operation=s.new_operation())\n"
                "    col.retire_generation(holder, generation, operation=s.new_operation())\n"
                "    holder.close()\n" + cut17,
                gen(
                    name,
                    cut=cut_name,
                    retire=[[cap[name]["job"], cap[name]["generation"]]],
                ),
                cut="cut",
            )
            step("j07-resume-" + name, head17 + COLLECT, gen(name))
            step("j07-repeat-" + name, head17 + COLLECT, gen(name))
        # J06: reader-first, then collection-decision-first, with consumer,
        # window, preparation and publication roots present in the workspace.
        release = directory / (PREFIX + "j06-release")
        reader = _child(
            directory,
            ledger,
            interpreter,
            head17 + _source_program(h17, "READER"),
            gen("G6", release=str(release)),
            PREFIX + "j06-reader",
        )
        try:
            until(reader, "reading", 600)
            step(
                "j06-collect-busy",
                head17 + COLLECT,
                gen("G6", retire=[[cap["G6"]["job"], cap["G6"]["generation"]]]),
            )
            release.write_text("")
            until(reader, "released", 600)
            reader.wait(timeout=60)
        finally:
            if reader.poll() is None:
                kill(reader)
            _reaped(ledger, reader, PREFIX + "j06-reader")
        step("j06-collect-won", head17 + COLLECT, gen("G6"))
        collector = _child(
            directory,
            ledger,
            interpreter,
            head17 + "for job, generation in config['retire']:\n"
            "    holder = s.claim_publisher(attach(), job, operation=s.new_operation())\n"
            "    col.retire_generation(holder, generation, operation=s.new_operation())\n"
            "    holder.close()\n" + cut17,
            gen(
                "G7",
                cut="K2_committed_before_unlink",
                retire=[[cap["G7"]["job"], cap["G7"]["generation"]]],
            ),
            PREFIX + "j06-collector",
        )
        try:
            until(collector, "cut", 600)
            late = _child(
                directory,
                ledger,
                interpreter,
                head17 + LATE_READ,
                gen("G7"),
                PREFIX + "j06-late-reader",
            )
            code, _ = kill(collector)
        finally:
            if collector.poll() is None:
                kill(collector)
            _reaped(ledger, collector, PREFIX + "j06-collector")
        stdout = _finish(late, PREFIX + "j06-late-reader", directory)
        _reaped(ledger, late, PREFIX + "j06-late-reader")
        report["j06_decision_first"] = {
            "collector": code,
            "late": json.loads(stdout.strip().splitlines()[-1]),
        }
        step("j06-collect-resume", head17 + COLLECT, gen("G7"))
        # J08: exhausted connections, a stalled sink, independent progress, a
        # serviced cancel, then the coordinator SIGKILLed and reconciled once.
        j08_facts = directory / (PREFIX + "j08-cut.json")
        step(
            "j08-pressure",
            STORAGE_HEADER + J08_PRESSURE,
            {
                **common,
                "directory": str(directory),
                "sink": str(directory / (PREFIX + "j08-sink")),
                "cut_facts": str(j08_facts),
            },
            cut="cut",
            python=capture_interpreter,
        )
        report["j08_cut"] = json.loads(j08_facts.read_text())
        step("j08-reconcile", STORAGE_HEADER + J08_RECONCILE, common)
        # J09: an expired saved-read acceptance and a foreign compatibility.
        step(
            "j09-refusals",
            STORAGE_HEADER + J09_REFUSALS,
            gen("R", extent=cap["R"]["frontier"]),
        )
        # Final static backups (supported backup API) for the independent checker.
        backup = directory / (PREFIX + "storage-final.sqlite")
        s14._backup(setup["workspace"], setup["identity"], backup)
        sink_backup = directory / (PREFIX + "storage-sink-final.sqlite")
        _backup_sink(setup["sink"], setup["sink_identity"], sink_backup)
        report.update(
            backup=str(backup), sink_backup=str(sink_backup), status="ACQUIRED"
        )
    except BaseException as error:
        report.update(
            status="FAILED", error_kind=type(error).__name__, error=str(error)[:500]
        )
        raise
    finally:
        report["seconds"] = time.monotonic() - started
        report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


def _backup_sink(root, identity, target):
    """Supported SQLite backup of a closed reference sink."""
    import sqlite3

    from pietto._project import project_job_sink as k

    opened = k.open_sink(root, expected_identity=identity)
    try:
        os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        copy = sqlite3.connect(target)
        try:
            opened.use().backup(copy)
        finally:
            copy.close()
    finally:
        opened.close()


# ---------------------------------------------------------------------------
# Compatibility: the current runtime against the two archived roles S19 may
# materialize, from their original archived wheel bytes: S16 (true old-runtime
# refusal of v7) and B19/S18 (immediate predecessor). The S18 programs run
# unchanged; the expected B19 outcome follows from recomputed code identities.

S18_EVIDENCE = (
    Path.home() / ".local/state/pietto/evidence/pietto-phase68-slice18-20261006T221828Z"
)
B19_WHEEL = (
    S18_EVIDENCE / "pietto-phase68-slice18-dist-final/pietto-0.1.0-py3-none-any.whl"
)
B19_SHA256 = "cf81718b12dfcc9161719063b7f171d65299eb662507cdf37467d64a75543979"
S16_SHA256 = "035fa6057afce966045c8003855a7cf2eaeae2c472ed2b6d865251867a0c5a7a"


def compat(
    directory, ledger, *, wheel, current, house, constraints, interpreter, cache
):
    """Format matrix (current vs archived B19), envelopes before SQLite, a
    recognized schema damage, archived S16 refusal of v7, B19 code compatibility
    and a fresh current acceptance."""
    import _pietto_phase68_slice13_probe as s13
    import _pietto_phase68_slice18_probe as s18
    import _pietto_phase68_slice19_check as check
    from pietto._project.project_compiled_loading import supported_compatibility

    directory.mkdir(mode=0o700)
    started = time.monotonic()
    log = directory / (PREFIX + "compat-commands.log")
    archived = {}
    for label, path, digest in (
        ("s16", s18.S16_WHEEL, S16_SHA256),
        ("b19", B19_WHEEL, B19_SHA256),
    ):
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("S19_ARCHIVED_WHEEL:" + label)
        prefix = directory / (PREFIX + "archived-" + label)
        commands = s18.materialize(
            prefix, interpreter, path, (), house, constraints, cache, log
        )
        if commands["install"]["returncode"]:
            raise ValueError("S19_ARCHIVED_INSTALL:" + label)
        archived[label] = {"prefix": prefix, "wheel": path, "commands": commands}

    def run(python, program, name, config=None):
        return s18._worker(
            directory,
            ledger,
            python,
            s18.HEADER + program,
            {"tests": str(ROOT / "tests"), **(config or {})},
            PREFIX + name,
            origin="installed",
        )

    current_python = Path(current) / "bin/python"
    b19_python = archived["b19"]["prefix"] / "bin/python"
    matrices = {
        "current": run(current_python, s18.MATRIX, "matrix-current"),
        "b19": run(b19_python, s18.MATRIX, "matrix-b19"),
    }
    envelopes = run(current_python, s18.ENVELOPES, "envelopes")
    old16 = run(
        archived["s16"]["prefix"] / "bin/python",
        s18.OLD16,
        "archived-s16-refusal",
        {
            "subject": envelopes["archived_subject"],
            "identity": envelopes["archived_identity"],
        },
    )
    produced = run(b19_python, s18.PRODUCE, "b19-producer")
    consumed = run(current_python, s18.CONSUME, "current-consumer", {"old": produced})
    for data, origin_wheel in (
        (matrices["current"], wheel),
        (envelopes, wheel),
        (consumed, wheel),
        (matrices["b19"], B19_WHEEL),
        (produced, B19_WHEEL),
        (old16, s18.S16_WHEEL),
    ):
        s13.installed_members(data, origin_wheel)
    (antlr,) = sorted(Path(house).glob("antlr4_python3_runtime-*.whl"))
    evidence = {
        "formats": {k: v["matrix"] for k, v in matrices.items()},
        "envelopes": envelopes["envelopes"],
        "schema": envelopes["schema"],
        "s16": {k: old16[k] for k in ("outcome", "unchanged", "format")},
        "code": {
            "b19_identity": produced["identity"],
            "current_identity": consumed["identity"],
            "source_identity": supported_compatibility()[-1],
            "b19_self": produced["self_load"],
            "b19_binding": produced["self_binding"],
            "load": consumed["load"],
            "open": consumed["open"],
            "binding_b19": consumed["binding_s17"],
            "binding_current": consumed["binding_current"],
            "fresh": consumed["fresh"],
        },
        "b19_wheel": B19_WHEEL.read_bytes(),
        "current_wheel": Path(wheel).read_bytes(),
        "antlr_wheel": antlr.read_bytes(),
    }
    raw = {k: v for k, v in evidence.items() if not k.endswith("_wheel")}
    raw["archived"] = {
        label: {
            "prefix": str(a["prefix"]),
            "wheel": str(a["wheel"]),
            "install": a["commands"]["install"],
            "check": a["commands"]["check"],
        }
        for label, a in archived.items()
    }
    s18._write(directory / (PREFIX + "compat-raw.json"), raw)
    report: dict = {"verdict": check.check_compat(evidence)}
    report["damages"] = check.compat_damages(evidence)
    report["seconds"] = time.monotonic() - started
    s18._write(directory / (PREFIX + "compat-report.json"), report)
    return report


# ---------------------------------------------------------------------------
# Equal-guarantee comparison: the same jobs under a serial and a bounded
# concurrent policy of the delivered runtime, everything else equal.

TUNING = r"""
from pietto._project import project_job_chunks as chunks
from pietto._project import project_job_sink as sk
results = {}
for label, workers in config["policies"]:
    workspace = w.create_workspace(config["workspace"] + "-" + label, format=w.FORMAT_V7)
    jobs = []
    for item in config["items"]:
        t_, v_, tr_ = bundle(item)
        j_, g_ = register(workspace, t_, v_, route)
        jobs.append((item, j_, g_, tr_, v_))
    runtime = rt.open_runtime(workspace.root, expected_identity=workspace.identity,
        policy=rt.Policy(workers=workers, connections=workers, durable=128 * 1024 * 1024))
    handle = sk.create_sink(config["sink"] + "-" + label, namespace="s19.tuning." + label,
        epoch=1, retention_seconds=86400)
    target = [handle.root, handle.identity, handle.namespace, handle.epoch, handle.retention]
    handle.close()
    lock = sqlite3.connect(target[0] + "/sink.sqlite", isolation_level=None, timeout=5)
    lock.execute("BEGIN IMMEDIATE")
    started = time.monotonic()
    handles = []
    for item, j_, g_, tr_, v_ in jobs:
        if item["kind"] == "relay":
            handles.append(runtime.submit(unit(workspace, "RELAY", j_, g_, tr_, v_,
                source=source(route, item["page"]), sink=rt.SinkTarget(*target, 0.2),
                rows=item["page"], batch_rows=item["page"], durable=16 * 1024 * 1024)))
        else:
            handles.append(runtime.submit(unit(workspace, "CAPTURE", j_, g_, tr_, v_,
                source=source(route, item["page"]), durable=16 * 1024 * 1024)))
    keys = [item["key"] for item, *_x in jobs]
    receipt = runtime.cancel(handles[keys.index("cancelled")])
    # Backpressure: the sink stays busy until the relay is observed parked on it,
    # then for the stall; the lock is released and the unit given its relief.
    slow = handles[keys.index("slow")]
    # Identified native connections open at one instant (registered and not yet
    # closed), sampled from submission until the relay is seen parked on the
    # pushing-back sink (the largest such set): one worker never holds two, a
    # bounded concurrent policy does. A single sample at the park instant raced
    # the other jobs' completion once they ran faster.
    open_sessions, deadline = [], time.monotonic() + 600
    while True:
        blocked = runtime.wait_activity(slow, "WAITING_FOR_DOWNSTREAM", 0.05)
        with runtime._cond:
            current = sorted({str(r_.owner.session_id) for r_ in runtime._records.values()
                if r_.owner is not None and r_.terminal is None
                and r_.owner.session_id is not None and not r_.owner._closed})
        if len(current) > len(open_sessions):
            open_sessions = current
        if (blocked.activity == "WAITING_FOR_DOWNSTREAM" or blocked.terminal is not None
                or time.monotonic() > deadline):
            break
    time.sleep(config["stall_seconds"])
    lock.execute("ROLLBACK")
    lock.close()
    runtime.resume(slow)
    done = [runtime.wait(h, 1800) for h in handles]
    elapsed = time.monotonic() - started
    values = {}
    for item, j_, g_, tr_, _v in jobs:
        if item["kind"] == "cancelled":
            continue
        output = c.stored_output(workspace, j_, g_, expected_pin=tr_[0],
            accepted_producer=tr_[1], accepted_compatibility=tr_[2])
        snap = c.checkpoint_snapshot(workspace, j_, g_)
        wires = []
        with c.SnapshotReader(workspace, snap, output) as reader:
            for index in range(len(snap.members)):
                table = reader.read(index).table
                columns = [table.column(i).to_pylist() for i in range(table.num_columns)]
                wires.extend([[chunks.coordinate_wire(column[j]) for column in columns]
                    for j in range(table.num_rows)])
        values[item["key"]] = wires
    con = workspace.use()
    results[label] = {"elapsed": elapsed, "workers": workers,
        "terminals": {item["key"]: [q.terminal, q.failure, q.durable_cancel]
            for (item, *_x), q in zip(jobs, done)},
        "values": values, "units": states(runtime, handles, workspace),
        "open_sessions": open_sessions, "cancel": receipt, "blocked": blocked.activity,
        "chunks": con.execute("SELECT count(*) FROM chunk").fetchone()[0],
        "operations": con.execute("SELECT count(*) FROM operation").fetchone()[0],
        "admissions": con.execute("SELECT count(*) FROM admission").fetchone()[0],
        "verify": verify_store(workspace)}
    runtime.close()
    workspace.close()
facts["tuning"] = results
write_facts()
"""


def tuning(directory, ledger, *, target, interpreters, wheel, routes=None):
    """Per route (all of the target's, or the named subset) one pair (serial
    workers=1 vs concurrent workers=3) over the same small, larger multi-page,
    slow-sink relay and cancelled jobs in fresh workspaces; values, terminals and
    runtime laws are compared, the largest set of identified native sessions open
    at one instant before the sink is seen pushing back is recorded, and elapsed
    time is only reported. Run in an
    exclusive measurement window. A route's policy order alternates by its
    position in the target's route list."""
    import _pietto_phase68_slice10_probe as s10
    import _pietto_phase68_slice14_probe as s14
    import _pietto_phase68_slice17_probe as s17
    from _pietto_phase68_slice8_probe import event
    from _pietto_phase68_slice11_probe import kill
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_schema import Scalar, scalar_wire

    directory.mkdir(mode=0o700)
    resource = _owned_database(directory, ledger, target, "s19_tuning")
    report: dict[str, Any] = {"status": "STARTED", "target": target, "pairs": {}}
    report_path = directory / (PREFIX + "tuning.json")
    started = time.monotonic()
    try:
        resource.acquire()
        general, _guard = fixtures(resource)
        cell = {
            "group": "refined",
            "case": "R2_seven",
            "variant": "39_values",
            "excluded": False,
        }
        reference = s10.build_native_reference(
            directory / (PREFIX + "reference-source"), target, cell, general
        )
        if reference is None:
            raise ValueError("S19_TUNING_REFERENCE")
        artifact, preparation, query, _output, _binding = reference
        built = build_compiled(artifact, guarded=preparation, refinement=query)
        bundle = directory / (PREFIX + "bundle.json")
        bundle.write_bytes(built.payload)
        bundle.chmod(0o600)
        main = {
            "bundle": str(bundle),
            "pin": built.pin,
            "producer": built.producer,
            "compatibility": list(built.compatibility),
            "values": [
                scalar_wire(Scalar(v.tag.value, v.value)) for v in artifact.fixed_values
            ],
        }
        items = [
            {"key": "small", "kind": "capture", "page": 6, **main},
            {"key": "larger", "kind": "capture", "page": 1, **main},
            {"key": "slow", "kind": "relay", "page": 2, **main},
            {"key": "cancelled", "kind": "cancelled", "page": 2, **main},
        ]
        for route in routes or ROUTES[target]:
            policies = [["serial", 1], ["concurrent", 3]]
            if ROUTES[target].index(route) % 2:
                policies.reverse()
            name = PREFIX + "tuning-" + route
            path = directory / (name + "-config.json")
            runtime = directory / (name + "-runtime")
            runtime.mkdir(mode=0o700)
            facts = directory / (name + "-facts.json")
            _write_private(
                path,
                {
                    **main,
                    "target": target,
                    "route": route,
                    "role": "tuning",
                    "origin": "installed",
                    "library_source": str(ROOT / "src"),
                    "port": resource.port,
                    "password": resource._passwords[1],
                    "ca_path": str(resource.ca_path) if target == "mysql" else None,
                    "request_seconds": 900,
                    "items": items,
                    "policies": policies,
                    "stall_seconds": 1.0,
                    "workspace": str(directory / (name + "-workspace")),
                    "sink": str(directory / (name + "-sink")),
                    "runtime_cwd": str(runtime),
                    "facts": str(facts),
                },
            )
            mark = time.monotonic()
            with (directory / (name + "-worker.log")).open("w") as log:
                child = s14._spawn(
                    interpreters[route],
                    s17.NATIVE_HEADER + TUNING,
                    path,
                    ledger,
                    log,
                    name,
                )
                try:
                    code = child.wait(timeout=3600)
                finally:
                    if child.poll() is None:
                        kill(child)
                    s14._reaped(ledger, child, child.returncode)
            path.unlink()
            if code:
                raise ValueError("S19_TUNING_WORKER:" + route + ":" + str(code))
            data = json.loads(facts.read_text())
            s14._origin_check(data, "installed", wheel)
            report["pairs"][route] = {
                "order": [p[0] for p in policies],
                "worker_seconds": time.monotonic() - mark,
                "tuning": data["tuning"],
            }
            report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        report["status"] = "ACQUIRED"
    except BaseException as error:
        report.update(
            status="FAILED",
            error_kind=type(error).__name__,
            error=resource.without_secrets(str(error)),
        )
        raise
    finally:
        report["source_cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - started
        report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        event(
            ledger,
            {
                "kind": "s19_tuning_terminal",
                "status": report["status"],
                "cleanup": report["source_cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


# ---------------------------------------------------------------------------
# CI-shaped installed consumers, run locally with explicit LOCAL labels: the
# Compiler/Package job's Arrow readiness and installed result-product consumers
# and the aggregate's real-consumer prepare/replay/verify over this head's
# archived native receipts with their ORIGINAL identity (local HEAD equals that
# identity only before the next commit; nothing is rewritten). The receipts are
# the latest published head's verified natural-CI artifacts.

RECEIPT_RUN = (
    Path.home()
    / ".local/state/pietto/evidence/pietto-post-phase68-performance-20261008T060017Z"
    / "pietto-post-phase68-performance-ci-37823793256-attempt1"
)
RECEIPTS = RECEIPT_RUN / "pietto-post-phase68-performance-artifacts"
RECEIPT_IDENTITY = ("381376fba59868cfed70fc09a21c4cd6a8be4309", "37823793256", 1)


def consumer(directory, ledger, *, label, uv_cache=None):
    """Each step is the CI command shape; the checkers are the CI checkers."""
    import subprocess

    from _pietto_phase68_slice8_probe import event

    directory.mkdir(mode=0o700)
    audit = json.loads(
        (RECEIPT_RUN / "pietto-post-phase68-performance-audit.json").read_text()
    )
    receipts = directory / (PREFIX + "receipts")
    receipts.mkdir(mode=0o700)
    copied = {}
    for target in ("postgres", "mysql"):
        name = "phase66-%s-%s-%d.json" % (
            target,
            RECEIPT_IDENTITY[1],
            RECEIPT_IDENTITY[2],
        )
        data = (RECEIPTS / name).read_bytes()
        copied[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        (receipts / name).write_bytes(data)
        (receipts / name).chmod(0o400)
    environment = {
        **{k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG")},
        "UV_PYTHON": "3.13.13",
        "UV_NO_SYNC": "1",
        "UV_LOCKED": "1",
        "GITHUB_RUN_ID": label,
        "GITHUB_RUN_ATTEMPT": "1",
    }
    if uv_cache is not None:
        environment["UV_CACHE_DIR"] = str(uv_cache)
    arrow = directory / (PREFIX + "arrow-ready")
    dist = directory / (PREFIX + "result-dist")
    extra = directory / (PREFIX + "consumer-extra")
    extra_dist = directory / (PREFIX + "consumer-dist")
    reports = directory / (PREFIX + "reports")
    reports.mkdir(mode=0o700)
    readiness = reports / ("arrow-readiness-%s-1-3.13.json" % label)
    product = reports / ("result-product-%s-1-3.13.json" % label)
    integration = reports / ("phase67-consumer-integration-%s.json" % label)
    replay_identity = [
        "--expected-commit",
        RECEIPT_IDENTITY[0],
        "--run-id",
        RECEIPT_IDENTITY[1],
        "--run-attempt",
        str(RECEIPT_IDENTITY[2]),
    ]
    steps = [
        (
            "package_smoke",
            [
                "uv",
                "run",
                "python",
                "scripts/package_smoke.py",
                "--dist-dir",
                str(dist),
                "--extra-env",
                str(arrow),
            ],
        ),
        (
            "arrow_readiness",
            [
                str(arrow / "bin/python"),
                "-I",
                "tests/_pietto_phase67_arrow_compatibility_probe.py",
                "--report",
                str(readiness),
            ],
        ),
        (
            "check_arrow",
            [
                "uv",
                "run",
                "python",
                "scripts/ci_validation.py",
                "check-arrow",
                "--python",
                "3.13",
                "--report",
                str(readiness),
            ],
        ),
        (
            "result_product",
            [
                str(arrow / "bin/python"),
                "-I",
                "tests/_pietto_phase67_result_product_probe.py",
                "--repository",
                str(ROOT),
                "--report",
                str(product),
            ],
        ),
        (
            "check_product",
            [
                "uv",
                "run",
                "python",
                "scripts/ci_validation.py",
                "check-product",
                "--python",
                "3.13",
                "--report",
                str(product),
            ],
        ),
        (
            "consumer_prepare",
            [
                "uv",
                "run",
                "python",
                "tests/_pietto_phase67_real_consumer_probe.py",
                "prepare",
                "--repository",
                str(ROOT),
                "--environment",
                str(extra),
                "--dist-dir",
                str(extra_dist),
            ],
        ),
        (
            "consumer_replay",
            [
                str(extra / "bin/python"),
                "-I",
                "tests/_pietto_phase67_real_consumer_probe.py",
                "replay",
                "--repository",
                str(ROOT),
                "--receipts",
                str(receipts),
                "--wheel",
                str(extra_dist / "pietto-0.1.0-py3-none-any.whl"),
                "--report",
                str(integration),
                *replay_identity,
            ],
        ),
        (
            "consumer_verify",
            [
                "uv",
                "run",
                "python",
                "tests/_pietto_phase67_real_consumer_probe.py",
                "verify",
                "--repository",
                str(ROOT),
                "--receipts",
                str(receipts),
                "--wheel",
                str(extra_dist / "pietto-0.1.0-py3-none-any.whl"),
                "--report",
                str(integration),
                *replay_identity,
                "--python",
                "3.13",
            ],
        ),
    ]
    report: dict[str, Any] = {
        "provenance": "LOCAL",
        "label": label,
        "receipts": copied,
        "receipt_audit": {k: audit[k] for k in audit if k in ("verdict", "status")},
        "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "steps": [],
    }
    for name, argv in steps:
        mark = time.monotonic()
        with (directory / (PREFIX + name + ".log")).open("wb") as log:
            result = subprocess.run(
                argv,
                cwd=ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600,
                check=False,
            )
        report["steps"].append(
            {
                "step": name,
                "returncode": result.returncode,
                "seconds": time.monotonic() - mark,
            }
        )
        event(
            ledger,
            {
                "kind": "s19_consumer_step",
                "step": name,
                "returncode": result.returncode,
            },
        )
        (directory / (PREFIX + "consumer.json")).write_text(
            json.dumps(report, indent=2) + "\n"
        )
        if result.returncode:
            raise ValueError("S19_CONSUMER_STEP:" + name + ":" + str(result.returncode))
    report["wheels"] = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted([*dist.glob("*.whl"), *extra_dist.glob("*.whl")])
    }
    report["reports"] = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(reports.iterdir())
    }
    (directory / (PREFIX + "consumer.json")).write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return report


# ---------------------------------------------------------------------------
# Adapter controls: the original per-adapter control families run unchanged
# on the current candidate, each in its own owned database and its own family
# process (their injections stay inside that isolated process): S03 PG rows
# product cases (blocked cancel/deadline, early close, late cancel, cleanup and
# source failures), S09 PG ADBC controls, S08 MySQL controls. Their original
# checkers judge the records. Each family's own environment contract is the
# S01 executor premise (every pinned driver; S09 records its runtime identity
# over all of them), i.e. the union recipe; route-specific isolation is the
# matrix's and S18's installation evidence.


def _family_ledger(path, *, budgets=False):
    """A sub-ledger with the counters the original families charge (S03 uses
    its own `budgets` shape); the S19 master ledger is charged before launch."""
    names = ("source_db_lifecycle_starts", "targeted_live_family_starts")
    value: dict[str, Any] = (
        {"budgets": {n: {"used": 0, "limit": 1} for n in names}, "events": []}
        if budgets
        else {
            "limits": {n: 1 for n in names},
            "used": {n: 0 for n in names},
            "used_detail": {},
            "events": [],
            "owned_resources": [],
        }
    )
    path.write_text(json.dumps(value, indent=2) + "\n")


def controls(directory, ledger, *, target, tree, union, wheel, families=None):
    """Run the original control families of `target` (or the named subset of
    s03/s09/s08) in the executor-premise union recipe, then their checkers."""
    import subprocess

    from _pietto_phase68_slice8_probe import event
    from _pietto_target_conformance_resources import clean_environment

    directory.mkdir(mode=0o700)
    report: dict[str, Any] = {"target": target, "tree": tree, "families": {}}

    def run(name, argv):
        mark = time.monotonic()
        with (directory / (PREFIX + name + ".log")).open("wb") as log:
            result = subprocess.run(
                argv,
                cwd=ROOT,
                env=clean_environment(),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=7200,
                check=False,
            )
        event(
            ledger,
            {
                "kind": "s19_control_family",
                "family": name,
                "returncode": result.returncode,
            },
        )
        report["families"][name] = {
            "returncode": result.returncode,
            "seconds": time.monotonic() - mark,
        }
        if result.returncode:
            raise ValueError(
                "S19_CONTROL_FAMILY:" + name + ":" + str(result.returncode)
            )

    def wanted(name):
        return families is None or name in families

    if target == "postgres" and wanted("s03"):
        s03 = directory / "s03"
        s03.mkdir(mode=0o700)
        _family_ledger(s03 / "ledger.json", budgets=True)
        # The S01-pinned premise environment is the union recipe.
        run(
            "s03-product",
            [
                str(union),
                "-B",
                str(ROOT / "scripts/phase68_slice3_probe.py"),
                "product",
                "--directory",
                str(s03 / "run"),
                "--ledger",
                str(s03 / "ledger.json"),
                "--tree",
                tree,
                "--target",
                "postgres",
            ],
        )
        from _pietto_phase68_slice3_cases import verify_product

        found = json.loads(
            (s03 / "run" / "pietto-phase68-slice03-report.json").read_text()
        )
        report["s03"] = verify_product(found)
    if target == "postgres" and wanted("s09"):
        s09 = directory / "s09"
        s09.mkdir(mode=0o700)
        _family_ledger(s09 / "ledger.json")
        (s09 / "pietto-phase68-slice09-acceptance-manifest.json").write_text(
            json.dumps({"ordinary": [], "refined": [], "guarded": []})
        )
        (s09 / "pietto-phase68-slice09-native-env").symlink_to(
            Path(union).parent.parent
        )
        run(
            "s09-controls",
            [
                str(union),
                "-B",
                str(ROOT / "scripts/phase68_slice9_probe.py"),
                "--mode",
                "preflight",
                "--origin",
                "source",
                "--directory",
                str(s09 / "run"),
                "--ledger",
                str(s09 / "ledger.json"),
                "--tree",
                tree,
                "--wheel",
                str(wheel),
                "--groups",
                "controls",
            ],
        )
        from _pietto_phase68_slice9_check import check_controls, check_source_controls

        worker = json.loads(
            (
                s09
                / "run"
                / "pietto-phase68-slice09-controls-source"
                / "pietto-phase68-slice09-worker.json"
            ).read_text()
        )
        check_controls(worker["controls"])
        check_source_controls(worker["source_controls"])
        report["s09"] = {"controls": [c["control"] for c in worker["controls"]]}
    if target == "mysql" and wanted("s08"):
        s08 = directory / "s08"
        s08.mkdir(mode=0o700)
        _family_ledger(s08 / "ledger.json")
        run(
            "s08-controls",
            [
                str(union),
                "-B",
                str(ROOT / "scripts/phase68_slice8_probe.py"),
                "--mode",
                "controls",
                "--origin",
                "source",
                "--directory",
                str(s08 / "run"),
                "--ledger",
                str(s08 / "ledger.json"),
                "--tree",
                tree,
            ],
        )
        from _pietto_phase68_slice8_check import check_controls as check08

        found = json.loads(
            (s08 / "run" / "pietto-phase68-slice08-controls.json").read_text()
        )
        kinds = [r["kind"] for r in found["controls"]]
        check08(found["controls"], kinds)
        report["s08"] = {"controls": kinds, "result": found.get("result")}
    (directory / (PREFIX + "controls.json")).write_text(
        json.dumps(report, indent=2, default=str) + "\n"
    )
    return report
