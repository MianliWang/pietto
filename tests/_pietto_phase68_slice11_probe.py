"""S11 job-store fixtures and explicit bounded native bridge; import acquires nothing."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice11-"
SENTINEL = "S11-SENTINEL-6b1f0c4e"
STORAGE_CLASS_VARIABLE = "PIETTO_STORAGE_CLASS"
STORAGE_CLASSES = ("hosted-refusal", "qualified", "report")
# This session's --pietto-storage-class value, set by tests/conftest.py.
STORAGE_CLASS_OPTION = None


def compiled_template(directory, *, seed=None, target="postgres", entry="live"):
    """A current S10 template; a seed adds one typed slot beside the WHERE Int slot."""
    import _pietto_phase67_result_product_probe as original
    from _pietto_phase68_slice4_probe import template
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
        prepare_live_template,
    )

    source = None
    if seed is not None:
        source = (
            original.source(target)
            .replace("renamed = id", "renamed = " + seed)
            .replace("    select:", "    where id > 1\n    select:")
        )
    live = template(Path(directory), source, target=target)
    built = build_compiled(live.artifact)
    if entry == "live":
        return prepare_live_template(live.artifact), built
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    return prepare_compiled_template(root), built


def storage_class(environ=None, option=None):
    """The declared storage class; a declaration wins, and without one hosted
    CI keeps the refusal branch while any other run reports not-run positives.
    A class never grants qualification: the observed profile still decides."""
    environ = os.environ if environ is None else environ
    declared = environ.get(STORAGE_CLASS_VARIABLE)
    if option is not None and declared is not None and declared != option:
        raise ValueError("PIETTO_STORAGE_CLASS_CONFLICT")
    value = option if option is not None else declared
    if value is None:
        return "hosted-refusal" if environ.get("GITHUB_ACTIONS") == "true" else "report"
    if value not in STORAGE_CLASSES:
        raise ValueError("PIETTO_STORAGE_CLASS_UNKNOWN")
    return value


def qualified(path):
    """True on the allowlisted profile. Otherwise assert the explicit refusal,
    then act by the storage class: hosted-refusal returns False, qualified
    fails and report skips as a counted not-run storage positive."""
    from pietto._project import project_job_workspace as w

    declared = storage_class(option=STORAGE_CLASS_OPTION)
    try:
        w.storage_profile(str(path))
    except w.JobStoreError as error:
        assert str(error) in (
            "WORKSPACE_PROFILE_PLATFORM",
            "WORKSPACE_PROFILE_SQLITE",
            "WORKSPACE_PROFILE_FILESYSTEM",
        )
        refused = Path(path) / "refused-workspace"
        try:
            w.create_workspace(str(refused))
        except w.JobStoreError as again:
            assert str(again) == str(error)
        else:
            raise AssertionError("unqualified profile created a workspace")
        assert not refused.exists()
        if declared == "hosted-refusal":
            return False
        import pytest

        if declared == "qualified":
            pytest.fail("PIETTO_STORAGE_REQUIRED " + str(error), pytrace=False)
        pytest.skip("PIETTO_NOT_RUN storage-positive " + str(error))
    return True


def root_of(template):
    """The compiled root of a template (untyped S10 carrier access for tests)."""
    return template.artifact.request.verification.completed.root


def trust(built) -> dict[str, Any]:
    return dict(
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )


def owner_outcome(binding, *, route="postgres_rows", password="pw", connect=False):
    """A real closed S10 owner without a database: never-started or refused."""
    from pietto._project import project_execution as ex
    from pietto._project.project_execution_mysql import MySQLExecution
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution

    sources = binding.artifact.request.sources
    if route == "mysql_rows":
        access = ex.MySQLAccess(
            "127.0.0.1",
            9,
            "phase66",
            "pietto_query",
            password,
            "/dev/null",
            "pietto_query@%",
            verify_identity=False,
            loopback_tls_exception=True,
        )
        options: dict[str, Any] = {
            "mysql_deployment": ex.MySQLDeploymentPremise(access, sources, ("phase66",))
        }
    else:
        access = ex.PostgresAccess(
            "127.0.0.1", 9, "phase66", "pietto_query", password, "disable"
        )
        options: dict[str, Any] = {
            "postgres_deployment": ex.PostgresDeploymentPremise(
                access, sources, ("public", "pg_catalog"), route
            )
        }
    request = ex.prepare_compiled_execution(
        binding, access, route=route, limits=ex.ExecutionLimits(seconds=2), **options
    )
    owner = {
        "postgres_rows": PostgresExecution,
        "postgres_adbc": PostgresADBCExecution,
        "mysql_rows": MySQLExecution,
    }[route](request)
    if connect:
        try:
            with owner:
                for _batch in owner:
                    pass
        except Exception:
            pass
    owner.close()
    return owner


CHILD_HEADER = r"""
import json, os, signal, sys, time
sys.path.insert(0, sys.argv[1])
config = json.loads(sys.argv[2])
from pietto._project import project_job_store as s, project_job_workspace as w

def barrier(name):
    sys.stdout.write(name + "\n")
    sys.stdout.flush()

def hold():
    while True:
        time.sleep(60)
"""


def child(program, config):
    """A registered, isolated child; the caller must reap it."""
    return subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            CHILD_HEADER + program,
            str(ROOT / "src"),
            json.dumps(config),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=config.get("cwd", "/"),
    )


def until(process, expected, seconds=60):
    """Read barrier lines until the expected one; any other end is a failure."""
    import selectors

    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        import time

        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if not selector.select(timeout=max(0.0, deadline - time.monotonic())):
                break
            line = process.stdout.readline()
            if not line:
                break
            if line.strip() == expected:
                return
        raise AssertionError("child barrier missing: " + expected)
    finally:
        selector.close()


def kill(process):
    """SIGKILL and reap; a descendant holding a pipe cannot block the reader."""
    if process.poll() is None:
        process.send_signal(signal.SIGKILL)
    try:
        _stdout, stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        process.wait(timeout=30)
        stderr = None
    return process.returncode, stderr


def finish(process, seconds=120):
    """Normal completion; a timeout kills and reaps before failing."""
    try:
        stdout, stderr = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        kill(process)
        raise
    assert process.returncode == 0, stderr[-6000:]
    return stdout


def worker_programs():
    """S11 workers around S10's verbatim native observation body (anchors exact)."""
    from _pietto_phase68_slice10_probe import WORKER

    def at(anchor):
        assert WORKER.count(anchor) == 1, anchor
        return WORKER.index(anchor)

    live = "live_template = None\n"
    hooks = "forbidden_calls = []\n"
    loaded = "load_started = time.monotonic()\n"
    bound = "        bind_seconds = time.monotonic() - bind_started\n"
    append = "        results.append(result)\n"
    tail = "origins = {}\n"
    header = WORKER[: at(live)]
    register = header + WORKER[at(live) : at(hooks)] + REGISTER
    execute = (
        header
        + WORKER[at(hooks) : at(loaded)]
        + EXECUTE_PRELUDE
        + WORKER[at(bound) + len(bound) : at(append)]
        + EXECUTE_EPILOGUE
        + WORKER[at(tail) :]
    )
    return register, execute


REGISTER = r"""
from pietto._project import project_job_store as s, project_job_workspace as w
if config["entry"] == "bundle":
    template = prepare_compiled_template(load_compiled(
        Path(config["bundle"]).read_bytes(), expected_pin=config["pin"],
        accepted_producer=config["producer"],
        accepted_compatibility=tuple(config["compatibility"])))
else:
    template = live_template
root = template.artifact.request.verification.completed.root
workspace = w.create_workspace(config["workspace"])
job = s.register_job(workspace, template, operation=s.new_operation()).get("job")
publisher = s.claim_publisher(workspace, job, operation=s.new_operation())
plan, references = [], []
for route in config["routes"]:
    group = []
    for case, number in config["values"]:
        bound = bind_values(template, tuple((slot, number) for slot in template.slots))
        record = s.register_binding(publisher, bound, operation=s.new_operation()).get("binding")
        generation = s.register_generation(publisher, record, bound, route=route,
            isolation="stable", operation=s.new_operation()).get("generation")
        group.append([case, number, record, generation])
        references.append(bound.instance_reference)
    plan.append([route, group])
publisher.close()
identity = workspace.identity
workspace.close()
origins = {}
for name, module in tuple(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
        path = Path(filename).resolve()
        origins[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
retain_raw({"workspace_identity": identity, "job": job, "pin": root.expected_pin,
    "producer": root.accepted_producer, "compatibility": list(root.accepted_compatibility),
    "plan": plan, "binding_references": references, "pid": os.getpid(),
    "entry": config["entry"], "origin": config["origin"], "origins": origins,
    "prefix": sys.prefix})
"""

EXECUTE_PRELUDE = r"""
from pietto._project import project_job_store as s, project_job_workspace as w
load_started = time.monotonic()
workspace = w.open_workspace(config["workspace"], expected_identity=config["workspace_identity"])
template = s.load_job(workspace, config["job"], expected_pin=config["pin"],
    accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]))
load_seconds = time.monotonic() - load_started
publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
results = []
for route, plan in config["plan"]:
    for case, number, record, generation in plan:
        bind_started = time.monotonic()
        bound = s.bind_record(workspace, config["job"], template, record)
        bind_seconds = time.monotonic() - bind_started
        attempt = s.open_attempt(publisher, generation, bound, operation=s.new_operation())
"""

EXECUTE_EPILOGUE = r"""
        recorded = s.record_attempt(publisher, attempt, owner, operation=s.new_operation())
        result["store"] = {"job": config["job"], "binding_record": record,
            "generation": generation, "attempt": attempt.identity,
            "ordinal": attempt.ordinal, "publisher_epoch": publisher.epoch,
            "operation": recorded.operation, "sequence": recorded.sequence,
            "pid": os.getpid()}
        results.append(result)
        retain_raw({"results":results,"forbidden_calls":forbidden_calls})
        if failure is not None:
            raise RuntimeError("native bridge attempt failed; raw preserved")
publisher.close()
workspace.close()
"""

CORE_ONLY = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
workspace = w.open_workspace(config["workspace"], expected_identity=config["workspace_identity"])
template = s.load_job(workspace, config["job"], expected_pin=config["pin"],
    accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"]))
binding = s.bind_record(workspace, config["job"], template, config["record"])
publisher = s.claim_publisher(workspace, config["job"], operation=s.new_operation())
attempt = s.open_attempt(publisher, config["generation"], binding, operation=s.new_operation())
s.record_not_executed(publisher, attempt, operation=s.new_operation())
publisher.close()
summary = verify_store(workspace)
workspace.close()
optional = sorted(n for n in sys.modules if n.split(".")[0] in
    ("pyarrow", "psycopg", "adbc_driver_manager", "adbc_driver_postgresql", "mysql"))
package = Path(sys.modules["pietto"].__file__).resolve().parent
outside = sorted(n for n, m in sys.modules.items() if n.startswith("pietto")
    and getattr(m, "__file__", None)
    and not Path(m.__file__).resolve().is_relative_to(package))
Path(config["raw"]).write_text(json.dumps({"summary": summary, "optional": optional,
    "package": str(package), "outside": outside, "prefix": sys.prefix,
    "values": list(binding.values)}))
"""


def bridge(directory, ledger, interpreter, *, target, cells, wheel=None, core=None):
    """Bounded native S11 bridge: register, exit, source-free reload and attempts."""
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
    from _pietto_phase68_slice11_check import (
        check_store_bridge,
        check_store_bridge_damage,
    )
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
        raise ValueError("S11_BRIDGE_CELLS")
    directory.mkdir(mode=0o700)
    event(
        ledger,
        {
            "kind": "s11_bridge_start",
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
    values = [["A", 1], ["B", 5], ["A_again", 1], ["empty", 2**63 - 1]]
    register_program, execute_program = worker_programs()
    prefix = (
        "import struct\nfrom decimal import Decimal\nfrom datetime import datetime\n"
        "from uuid import UUID\n" + inspect.getsource(s01.scalar) + "\n"
    )
    private = directory / (PREFIX + "private-input.json")
    report = {
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
                    raise ValueError("S11_INSTALLED_MEMBER_BYTES")

    try:
        report["runtime"] = s01.runtime_identity()
        if (
            report["runtime"]["versions"]
            != s01.helper("_pietto_phase68_executor_cases").PINS
        ):
            raise ValueError("S11_RUNTIME_PINS")
        if wheel is not None:
            report["wheel"] = str(wheel)
            report["wheel_sha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()
        event(
            ledger,
            {
                "kind": "s11_database_start",
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
                "s11-register-" + name,
                origin,
            )
            cell = {"origin": origin, "entry": entry, "register_exit": code}
            report["cells"].append(cell)
            if code:
                raise ValueError("S11_REGISTER_WORKER_FAILED")
            registration = json.loads(registration_path.read_text())
            # Explicit caller acceptance: bundle trust is the controller's own
            # build handoff; live trust is the live build's reported root.
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
                raise ValueError("S11_TRUST_HANDOFF")
            code = run(
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
                "s11-execute-" + name,
                origin,
            )
            cell["execute_exit"] = code
            cell["raw"] = str(raw) if raw.exists() else None
            if code:
                raise ValueError("S11_EXECUTE_WORKER_FAILED")
            data = json.loads(raw.read_text())
            if origin == "installed":
                installed_bytes(data["origins"])
                installed_bytes(registration["origins"])
            origin_root = (
                ROOT / "src/pietto" if origin == "source" else interpreter.parent.parent
            )
            check_small_pg(
                data,
                tuple(ROWS),
                origin_root,
                expected_sql,
                origin=origin,
                entry=entry,
                target=target,
            )
            check_small_pg_damage(
                data,
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
            check_store_bridge(
                data, registration, backup, workspace, target=target, password=password
            )
            cell["store_damage_rejected"] = check_store_bridge_damage(
                data,
                registration,
                backup,
                workspace,
                target=target,
                password=password,
                scratch=directory,
            )
            if origin == "installed" and core is not None:
                core_raw = directory / (PREFIX + name + "-core-only.json")
                ((_route, group),) = registration["plan"][:1]
                _case, _number, record, generation = group[0]
                code = run(
                    CORE_ONLY,
                    {
                        "workspace": str(workspace),
                        "workspace_identity": registration["workspace_identity"],
                        "job": registration["job"],
                        "pin": accepted[0],
                        "producer": accepted[1],
                        "compatibility": accepted[2],
                        "record": record,
                        "generation": generation,
                        "raw": str(core_raw),
                    },
                    name + "-core-only",
                    "s11-core-only-" + name,
                    "core",
                )
                if code:
                    raise ValueError("S11_CORE_ONLY_WORKER_FAILED")
                observed = json.loads(core_raw.read_text())
                expected_package = (
                    Path(core).parent.parent / "lib/python3.13/site-packages/pietto"
                ).resolve()
                if (
                    observed["optional"]
                    or observed["outside"]
                    or observed["values"] != [1]
                    or observed["package"] != str(expected_package)
                    or observed["summary"]["attempts"]
                    != sum(len(g) for _r, g in registration["plan"]) + 1
                ):
                    raise ValueError("S11_CORE_ONLY")
                cell["core_only"] = observed
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
                "kind": "s11_bridge_terminal",
                "status": report["status"],
                "directory": str(directory),
                "seconds": report["seconds"],
            },
        )
    return report
