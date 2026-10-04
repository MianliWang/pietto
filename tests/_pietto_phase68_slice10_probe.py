"""Bounded S10 native acquisition; source-free workers receive no query builder."""

from pathlib import Path
import inspect
import hashlib
import zipfile
import json
import os
import shutil
import importlib
import time
from typing import Any

# Pure observation owners reused by the live lab and copied verbatim into the
# isolated subject program; no source-building helper enters the bundle runtime.
from _pietto_phase68_slice6_probe import observation_data, page_data
from _pietto_phase68_slice7_probe import encoded, native_record
from _pietto_phase68_slice8_probe import Calls as MySQLCalls
from _pietto_phase68_slice9_probe import Calls as ADBCCalls, native_data

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice10-"

# Only stdlib, actual Pietto product code and explicit native/Arrow dependencies
# are imported in this subject. The original scalar encoder is inserted verbatim
# by the observer; no source-building helper is shipped with it.
WORKER = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, importlib, hashlib, time, os
from pathlib import Path
from dataclasses import asdict
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
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_execution_template import prepare_compiled_template, prepare_live_template, bind_values
from pietto._project import project_execution as ex
from pietto._project.project_execution_postgres import PostgresExecution
from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
from pietto._project.project_execution_mysql import MySQLExecution
from pietto._project import model, trusted_source
import pietto.ast_nodes as nodes

live_template = None
if config["entry"] == "live":
    import shutil
    sys.path.insert(0, config["build_helpers"])
    from _pietto_phase68_slice4_probe import template as original_template
    source_template = original_template(Path(config["live_project"]), target=config["target"])
    live_template = prepare_live_template(source_template.artifact)
    del source_template, original_template
    shutil.rmtree(config["live_project"])
    sys.path.remove(config["build_helpers"])
    for name in tuple(sys.modules):
        if name.startswith(("_pietto_", "test_phase", "s04_", "s03_")):
            del sys.modules[name]
forbidden_calls = []
def forbidden(*args, **kwargs):
    forbidden_calls.append("source_elaboration")
    raise AssertionError("source-language entry reached by source-free execution")
blocked = []
for module_name, names in (
    ("pietto.parser_api", ("parse_source",)),
    ("pietto._project.model", ("build_empty_project_semantic_result",)),
    ("pietto._project.project_completed_semantics", ("build_project_completed_semantic_result",)),
    ("pietto._project.project_execution_template", ("_syntax_image", "_specialize")),
    ("pietto._project.discovery", ("discover_project_inputs",)),
    ("pietto._project.config", ("load_project_config", "_read_project_config_bytes")),
    ("pietto._project.trusted_source", ("_load_trusted_source",)),
    ("pietto._project.package_loader", ("_load_root_package", "_load_package_content", "_read_trusted_package_file_at")),
    ("pietto._project.module_catalog", ("_build_project_module_catalog_set",)),
    ("pietto._project.module_attribution", ("_build_project_module_attribution_fact_set", "_derive_project_module_attribution_fact_collections")),
):
    module = importlib.import_module(module_name)
    blocked.extend(getattr(module, name) for name in names)
for module in tuple(sys.modules.values()):
    if not getattr(module, "__name__", "").startswith("pietto"):
        continue
    for name, value in tuple(vars(module).items()):
        if any(value is function for function in blocked):
            setattr(module, name, forbidden)
for value in tuple(vars(nodes).values()):
    if type(value) is type and (issubclass(value, nodes.Node) or value is nodes.Span):
        value.__new__ = forbidden
model.ProjectParseCheckResult.__new__ = forbidden
trusted_source.ProjectTrustedSourceSnapshot.__new__ = forbidden
assert not Path(config["removed_query_project"]).exists()
assert not any(name.startswith("_pietto_") or name.startswith("test_phase") for name in sys.modules)
load_started = time.monotonic()
if config["entry"] == "bundle":
    root = load_compiled(Path(config["bundle"]).read_bytes(), expected_pin=config["pin"],
        accepted_producer=config["producer"], accepted_compatibility=tuple(config["compatibility"]))
    template = prepare_compiled_template(root)
else:
    template = live_template
load_seconds = time.monotonic() - load_started
results = []
for route in config["routes"]:
    for case, number in config["values"]:
        bind_started = time.monotonic()
        bound = bind_values(template, tuple((slot, number) for slot in template.slots))
        bind_seconds = time.monotonic() - bind_started
        if route == "mysql_rows":
            access = ex.MySQLAccess("127.0.0.1", config["port"], "phase66", "pietto_query", config["password"], config["ca_path"], "pietto_query@%", verify_identity=False, loopback_tls_exception=True)
            premise_args = {"mysql_deployment": ex.MySQLDeploymentPremise(access, bound.artifact.request.sources, ("phase66",))}
        else:
            access = ex.PostgresAccess("127.0.0.1", config["port"], "phase66", "pietto_query", config["password"], "disable")
            premise_args = {"postgres_deployment": ex.PostgresDeploymentPremise(access, bound.artifact.request.sources, ("public", "pg_catalog"), route)}
        request = ex.prepare_compiled_execution(bound, access, route=route, **premise_args,
            limits=ex.ExecutionLimits(batch_rows=2, seconds=config["request_seconds"]))
        owner = {"postgres_rows":PostgresExecution,"postgres_adbc":PostgresADBCExecution,"mysql_rows":MySQLExecution}[route](request)
        submissions, rows, schemas = [], [], []
        if route == "postgres_rows":
            import psycopg
            original_execute = psycopg.RawCursor.execute
            def observed_execute(cursor, query, params=None, **options):
                if cursor is owner._cursor:
                    submissions.append({"sql":query.decode() if type(query) is bytes else query,"arguments":[scalar(v) for v in (params or ())]})
                return original_execute(cursor, query, params, **options)
            psycopg.RawCursor.execute = observed_execute
        elif route == "mysql_rows":
            from mysql.connector.connection import MySQLConnection
            original_execute = MySQLConnection.cmd_stmt_execute
            original_prepare = MySQLConnection.cmd_stmt_prepare
            preparations = {}
            def observed_prepare(connection, statement, **options):
                reply = original_prepare(connection, statement, **options)
                if connection is owner._owned_connection:
                    preparations[reply["statement_id"]] = (bytes(statement).decode(),reply)
                return reply
            def observed_execute(connection, statement_id, data=(), parameters=(), flags=0, **options):
                if connection is owner._owned_connection:
                    sql, preparation = preparations[statement_id]
                    submissions.append({"sql":sql,"arguments":[scalar(v) for v in data],"prepared":preparation,"flags":flags})
                return original_execute(connection, statement_id, data=data, parameters=parameters, flags=flags, **options)
            MySQLConnection.cmd_stmt_prepare = observed_prepare
            MySQLConnection.cmd_stmt_execute = observed_execute
        else:
            from pietto._project.project_execution_postgres_adbc_native import NativeStatement
            original_execute = NativeStatement._execute
            def observed_execute(statement, maximum):
                if statement.owner is owner and statement.purpose in ("query", "guard", "page"):
                    submissions.append({"sql":statement.sql.decode(),"arguments":[scalar(v) for v in statement.arguments],"copy":statement.copy,"purpose":statement.purpose})
                return original_execute(statement, maximum)
            NativeStatement._execute = observed_execute
        failure = None
        start = time.monotonic()
        try:
            with owner:
                for batch in owner:
                    with batch:
                        data = pa.record_batch(batch)
                        schemas.append([[f.name, str(f.type), f.nullable] for f in data.schema])
                        rows.extend([[scalar(data.column(i)[j].as_py()) for i in range(data.num_columns)] for j in range(data.num_rows)])
        except BaseException as error:
            failure = {"kind": type(error).__name__, "message":str(error).replace(config["password"], "<redacted>"), "sqlstate": getattr(error, "sqlstate", None)}
        finally:
            if route == "postgres_rows":
                psycopg.RawCursor.execute = original_execute
            elif route == "mysql_rows":
                MySQLConnection.cmd_stmt_execute = original_execute
                MySQLConnection.cmd_stmt_prepare = original_prepare
            else:
                NativeStatement._execute = original_execute
            owner.close()
        qualification = owner._qualification
        qualified = None if qualification is None else {
            "roots":[[s.namespace,s.name] for s in owner.request.artifact.request.sources],"context":qualification.context,
            "objects":[asdict(obj) for obj in qualification.objects],
            "edges":qualification.edges,"security":qualification.security,
        } if route == "mysql_rows" else {
            "roots": qualification.roots, "paths": qualification.paths,
            "context": qualification.context,
            "replies": [{"kind": r.kind, "arguments": [scalar(v) for v in r.arguments],
                "rows": [[scalar(v) for v in row] for row in r.rows],
                "native_sql": r.native.sql.decode(), "native_arguments": [scalar(v) for v in r.native.arguments],
                "native_rows": [[scalar(v) for v in row] for row in r.native.rows],
                "native_terminal": r.native.terminal,
                "native_metadata": r.native.metadata if route == "postgres_rows" else None,
                "native_status": r.native.status.decode() if route == "postgres_rows" else None,
            } for r in qualification.replies],
        }
        result = {"session":owner.session_id, "case":case, "route":route, "entry":config["entry"], "origin":config["origin"],
            "binding":bound.instance_reference, "values":[scalar(v) for v in bound.values],
            "sql":bound.artifact.rendered.sql.decode(), "submissions":submissions,
            "rows":rows, "schemas":schemas,
            "bound_schema":None if owner._payloads is None else [[f.name,str(f.type),f.nullable] for f in owner._payloads.binding.schema],
            "native_metadata":owner.actual_metadata, "qualification":qualified,
            "outcome":asdict(owner.outcome), "layers":asdict(ex.compiled_attempt_outcome(owner)),
            "failure":failure, "control_joined":owner.control_joined,
            "context":owner._profile_context if route == "postgres_rows" else owner.context,
            "control_events":owner.control_events, "guard_events":owner.guard_events,
            "timings":{"load":load_seconds,"bind":bind_seconds,"attempt":time.monotonic()-start}}
        if route == "mysql_rows":
            result["epoch"] = owner._epoch
            result["initial_epoch"] = owner._initial_epoch
            result["statements"] = [{"sql":s.sql.decode(),"arguments":[scalar(v) for v in s.arguments],"purpose":s.purpose,"prepared":s.prepared,"metadata":s.metadata,"metadata_eof":s.metadata_eof,"terminal":s.terminal,"closed":s.closed,"close_send":s.close_send} for s in owner._statements]
        results.append(result)
        retain_raw({"results":results,"forbidden_calls":forbidden_calls})
        if failure is not None:
            raise RuntimeError("native pilot attempt failed; raw preserved")
origins = {}
for name,module in tuple(sys.modules.items()):
    filename=getattr(module,"__file__",None)
    if (name=="pietto" or name.startswith("pietto.")) and type(filename) is str:
        path=Path(filename).resolve(); origins[name]={"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
retain_raw({"results":results,"forbidden_calls":forbidden_calls,"origins":origins,"prefix":sys.prefix})
"""


def pilot(
    directory,
    ledger,
    interpreter,
    *,
    origin="source",
    entry="bundle",
    cells=None,
    wheel=None,
    target="postgres",
):
    """Small bound native pilot; not a complete S10 campaign."""
    from _pietto_phase68_slice4_probe import template, ROWS, s01
    from _pietto_phase68_slice6_probe import manager
    from _pietto_phase68_slice8_probe import event, worker_process
    from _pietto_target_conformance_resources import Resources, clean_environment
    from pietto._project.project_compiled_build import build_compiled
    from _pietto_phase68_slice10_check import check_small_pg, check_small_pg_damage

    cells = ((origin, entry),) if cells is None else tuple(cells)
    if (
        not cells
        or len(cells) > 4
        or len(set(cells)) != len(cells)
        or any(
            o not in ("source", "installed") or e not in ("live", "bundle")
            for o, e in cells
        )
    ):
        raise ValueError("S10_PILOT_CELLS")
    directory.mkdir(mode=0o700)
    event(
        ledger,
        {"kind": "s10_small_pg_pilot_start", "directory": str(directory)},
        targeted_live_family_starts=1,
    )
    state = json.loads(ledger.read_text())
    state["owned_resources"].append(
        {"kind": "native_pilot_directory", "path": str(directory), "target": target}
    )
    ledger.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    project = directory / (PREFIX + "build-only")
    artifact = template(project, target=target).artifact
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
    ledger.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    private = directory / (PREFIX + "private-input.json")
    report = {
        "status": "STARTED",
        "requested_cells": cells,
        "cells": [],
        "routes": ["mysql_rows"]
        if target == "mysql"
        else ["postgres_rows", "postgres_adbc"],
    }
    start = time.monotonic()
    try:
        report["runtime"] = s01.runtime_identity()
        if (
            report["runtime"]["versions"]
            != s01.helper("_pietto_phase68_executor_cases").PINS
        ):
            raise ValueError("S10_RUNTIME_PINS")
        if any(o == "installed" for o, e in cells) and wheel is None:
            raise ValueError("S10_INSTALLED_WHEEL_REQUIRED")
        if wheel is not None:
            report["wheel"] = str(wheel)
            report["wheel_sha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()
        event(
            ledger,
            {
                "kind": "s10_database_start",
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
                f"INSERT INTO {quote}rows{quote} VALUES ({'$1,$2' if target == 'postgres' else '?,?'})",
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
        for origin, entry in cells:
            raw = directory / (PREFIX + origin + "-" + entry + "-native-raw.json")
            runtime_cwd = directory / (PREFIX + origin + "-" + entry + "-runtime")
            runtime_cwd.mkdir(mode=0o700)
            config = {
                "runtime_cwd": str(runtime_cwd),
                "origin": origin,
                "entry": entry,
                "target": target,
                "ca_path": str(resource.ca_path) if target == "mysql" else None,
                "build_helpers": str(ROOT / "tests"),
                "live_project": str(
                    directory / (PREFIX + origin + "-" + entry + "-live-build-only")
                ),
                "library_source": str(ROOT / "src"),
                "removed_query_project": str(project),
                "bundle": str(bundle),
                "pin": built.pin,
                "producer": built.producer,
                "compatibility": built.compatibility,
                "port": resource.port,
                "password": resource._passwords[1],
                "request_seconds": 20,
                "routes": report["routes"],
                "values": [["A", 1], ["B", 5], ["A_again", 1], ["empty", 2**63 - 1]],
                "raw": str(raw),
            }
            descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                json.dump(config, stream)
            program = (
                "import struct\nfrom decimal import Decimal\nfrom datetime import datetime\nfrom uuid import UUID\n"
                + inspect.getsource(s01.scalar)
                + "\n"
                + WORKER
            )
            with (directory / (PREFIX + origin + "-" + entry + "-worker.log")).open(
                "wb"
            ) as log:
                result = worker_process(
                    [str(interpreter), "-I", "-B", "-c", program, str(private)],
                    clean_environment(),
                    ledger,
                    log,
                    origin=origin,
                    group="s10-pg-bound-pilot-" + entry,
                    directory=directory,
                    seconds=600,
                )
            report["cells"].append(
                {
                    "origin": origin,
                    "entry": entry,
                    "worker_exit": result,
                    "raw": str(raw) if raw.exists() else None,
                }
            )
            private.unlink(missing_ok=True)
            if result:
                raise ValueError("S10_PILOT_WORKER_FAILED")
            data = json.loads(raw.read_text())
            if origin == "installed":
                assert wheel is not None
                with zipfile.ZipFile(wheel) as archive:
                    for name, item in data["origins"].items():
                        relative = "/".join(name.split("."))
                        member = relative + (
                            "/__init__.py"
                            if Path(item["path"]).name == "__init__.py"
                            else ".py"
                        )
                        if (
                            hashlib.sha256(archive.read(member)).hexdigest()
                            != item["sha256"]
                        ):
                            raise ValueError("S10_INSTALLED_MEMBER_BYTES")
            origin_root = (
                ROOT / "src/pietto" if origin == "source" else interpreter.parent.parent
            )
            check_small_pg(
                data,
                tuple(ROWS),
                origin_root,
                artifact.rendered.sql.decode(),
                origin=origin,
                entry=entry,
                target=target,
            )
            check_small_pg_damage(
                data,
                tuple(ROWS),
                origin_root,
                artifact.rendered.sql.decode(),
                origin=origin,
                entry=entry,
                target=target,
            )
        report["status"] = "PASS"
    except BaseException as error:
        report["status"] = "FAILED"
        report["error_kind"] = type(error).__name__
        raise
    finally:
        report["cleanup"] = resource.cleanup()
        private.unlink(missing_ok=True)
        report["seconds"] = time.monotonic() - start
        (directory / (PREFIX + "pilot.json")).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
        event(ledger, {"kind": "s10_small_pg_pilot_terminal", **report})
    return report


def collect_pg_live(resource, artifact, *, query=None, preparation=None, seconds=120):
    """Observe the real Psycopg owner; source fixture acquisition stays external."""
    psycopg = importlib.import_module("psycopg")
    pa = importlib.import_module("pyarrow")
    from dataclasses import asdict
    from _pietto_phase68_slice4_probe import s01
    from _pietto_phase68_slice6_probe import session_gone
    from pietto._project import project_execution as ex
    from pietto._project.project_execution_template import (
        prepare_live_template,
        bind_values,
    )
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_sql_emission import (
        EmissionOutcome,
        serialize_project_sql_emission,
    )

    template = prepare_live_template(artifact, guarded=preparation, refinement=query)
    values = tuple(v.value for v in artifact.fixed_values)
    binding = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    access = ex.PostgresAccess(
        "127.0.0.1",
        resource.port,
        "phase66",
        "pietto_query",
        resource._passwords[1],
        "disable",
    )
    premise = ex.PostgresDeploymentPremise(
        access,
        binding.artifact.request.sources,
        ("public", "pg_catalog"),
        "postgres_rows",
    )
    request = ex.prepare_compiled_execution(
        binding,
        access,
        route="postgres_rows",
        postgres_deployment=premise,
        limits=ex.ExecutionLimits(batch_rows=2, seconds=seconds),
    )
    owner = PostgresExecution(request)
    record = {
        "entry": "live",
        "origin": "source",
        "route": "postgres_rows",
        "attempt": owner.attempt,
        "rows": [],
        "schemas": [],
        "failure": None,
        "statements": [],
        "request_seconds": seconds,
        "public": None
        if preparation is not None
        else json.loads(
            serialize_project_sql_emission(EmissionOutcome("VERIFIED", (), artifact))
        ),
    }
    original_execute = psycopg.RawCursor.execute

    def observe(cursor, sql, params=None, **options):
        item = None
        if cursor.connection is owner._owned_connection:
            item = {
                "sql": sql.decode() if type(sql) is bytes else sql,
                "arguments": [s01.scalar(v) for v in (params or ())],
                "terminal": "PENDING",
            }
            record["statements"].append(item)
        try:
            result = original_execute(cursor, sql, params, **options)
            if item is not None:
                item.update(
                    terminal="NORMAL",
                    status=None
                    if cursor.pgresult is None
                    else cursor.pgresult.command_status.decode(),
                    metadata=None
                    if cursor.description is None
                    else [[c.name, c.type_code] for c in cursor.description],
                )
            return result
        except BaseException as error:
            if item is not None:
                item.update(
                    terminal="ERROR",
                    error_kind=type(error).__name__,
                    sqlstate=getattr(error, "sqlstate", None),
                )
            raise

    started = time.monotonic()
    psycopg.RawCursor.execute = observe
    try:
        with owner:
            for batch in owner:
                with batch:
                    array = pa.record_batch(batch)
                    record["schemas"].append(
                        [[f.name, str(f.type), f.nullable] for f in array.schema]
                    )
                    record["rows"].extend(
                        [
                            [
                                s01.scalar(array.column(i)[j].as_py())
                                for i in range(array.num_columns)
                            ]
                            for j in range(array.num_rows)
                        ]
                    )
    except BaseException as error:
        record["failure"] = {
            "kind": type(error).__name__,
            "message": resource.without_secrets(str(error)),
            "sqlstate": getattr(error, "sqlstate", None),
        }
    finally:
        owner.close()
        psycopg.RawCursor.execute = original_execute
    record.update(
        outcome=asdict(owner.outcome),
        layers=asdict(ex.compiled_attempt_outcome(owner)),
        control_joined=owner.control_joined,
        context=owner._profile_context,
        control_events=owner.control_events,
        guard_events=owner.guard_events,
        bound_schema=None
        if owner._payloads is None
        else [
            [f.name, str(f.type), f.nullable] for f in owner._payloads.binding.schema
        ],
        session_gone=None
        if owner.session_id is None
        else session_gone(resource, owner.session_id),
        seconds=time.monotonic() - started,
    )
    q = owner._qualification
    record["qualification"] = (
        None
        if q is None
        else {
            "roots": q.roots,
            "paths": q.paths,
            "context": q.context,
            "replies": [
                {
                    "kind": r.kind,
                    "arguments": r.arguments,
                    "rows": r.rows,
                    "sql": r.native.sql.decode(),
                    "metadata": r.native.metadata,
                    "native_rows": r.native.rows,
                    "terminal": r.native.terminal,
                }
                for r in q.replies
            ],
        }
    )
    if owner.source_admissions is not None:
        record["admission"] = observation_data(owner.source_admissions)
    return record


def source_profile_pilot(directory, ledger):
    """Reuse all original finite PG source fixtures on the actual new rows owner."""
    import _pietto_phase68_slice9_probe as original
    import _pietto_target_conformance_cases as fixtures
    from _pietto_phase68_slice6_probe import manager
    from _pietto_phase68_slice8_probe import event
    from _pietto_target_conformance_resources import Resources
    from _pietto_phase68_slice10_check import check_pg_source_controls

    directory.mkdir(mode=0o700)
    event(
        ledger,
        {"kind": "s10_pg_source_pilot_start", "directory": str(directory)},
        targeted_live_family_starts=1,
    )
    state = json.loads(ledger.read_text())
    state["owned_resources"].append(
        {"kind": "native_pilot_directory", "path": str(directory), "target": "postgres"}
    )
    ledger.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources("postgres", pins["targets"]["postgres"], directory)
    state = json.loads(ledger.read_text())
    state["owned_resources"].append(
        {
            "kind": "database_resource",
            "target": "postgres",
            "name": resource.name,
            "network_name": resource.network_name,
            "directory": str(directory),
            "journal": str(directory / "resources.jsonl"),
        }
    )
    ledger.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    path = directory / (PREFIX + "source-controls.json")
    report: dict[str, Any] = {
        "status": "STARTED",
        "origin": "source",
        "entry": "live",
        "route": "postgres_rows",
    }
    old_attempt, old_prefix = original.attempt, original.PREFIX
    start = time.monotonic()
    try:
        event(
            ledger,
            {
                "kind": "s10_database_start",
                "directory": str(directory),
                "name": resource.name,
            },
            source_db_lifecycle_starts=1,
        )
        resource.acquire()
        for sql, args in fixtures.emission_setup("postgres"):
            manager(resource, sql, args)
        for sql, _secret in resource.role_statements():
            manager(resource, sql)
        original.attempt = collect_pg_live
        original.PREFIX = PREFIX
        original.source_records(resource, directory, report, path)
        check_pg_source_controls(report["source_controls"])
        report["status"] = "PASS"
    except BaseException as error:
        report["status"] = "FAILED"
        report["error_kind"] = type(error).__name__
        raise
    finally:
        original.attempt, original.PREFIX = old_attempt, old_prefix
        report["cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - start
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        event(
            ledger,
            {
                "kind": "s10_pg_source_pilot_terminal",
                "status": report["status"],
                "path": str(path),
                "cleanup": report["cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


def collect_owned(request, *, control=None):
    """Only real native owners and passive records; safe to ship without source builders."""
    import importlib
    import sys
    import time
    from dataclasses import asdict
    from pietto._project import project_execution as ex
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
    from pietto._project.project_execution_mysql import MySQLExecution
    from pietto._project.project_refinement_enumeration import Enumeration

    base = getattr(request, "execution", request)
    route = base.route
    owner: Any = {
        "postgres_rows": PostgresExecution,
        "postgres_adbc": PostgresADBCExecution,
        "mysql_rows": MySQLExecution,
    }[route](request)
    pa = importlib.import_module("pyarrow")
    result: dict[str, Any] = {
        "route": route,
        "rows": [],
        "schemas": [],
        "pages": [],
        "failure": None,
        "statements": [],
        "interventions": [],
        "request_seconds": base.limits.seconds,
    }
    original_profile, original_trace = sys.getprofile(), sys.gettrace()
    originals: dict[str, Any] = {}
    cursors: dict[Any, Any] = {}
    cursor_records: dict[Any, Any] = {}
    observer: Any = None
    psycopg: Any = None
    if route == "postgres_rows":
        psycopg = importlib.import_module("psycopg")
        for method in ("execute", "fetchone", "fetchmany", "fetchall", "close"):
            originals[method] = getattr(psycopg.RawCursor, method)

        def execute(cursor, query, params=None, **options):
            item = None
            if cursor.connection is owner._owned_connection:
                item = {
                    "sql": query.decode() if type(query) is bytes else query,
                    "arguments": encoded((params or (),))[0],
                    "fetches": [],
                    "closed": False,
                    "purpose": "page"
                    if owner.enumeration is not None
                    and owner.enumeration._pending is not None
                    and query == owner.enumeration._pending.native.sql.decode()
                    else "guard"
                    if owner.guards is not None
                    and owner.guards.native is not None
                    and query == owner.guards.native.sql.decode()
                    else "query"
                    if query == owner.request.artifact.rendered.sql.decode()
                    else "control",
                }
                if cursor not in cursor_records:
                    cursor_records[cursor] = {
                        "ordinal": len(cursor_records),
                        "session": owner.session_id,
                        "closed": False,
                        "statements": [],
                    }
                cursor_record = cursor_records[cursor]
                item.update(
                    ordinal=len(result["statements"]), cursor=cursor_record["ordinal"]
                )
                cursor_record["statements"].append(item["ordinal"])
                cursors[cursor] = item
                result["statements"].append(item)
            try:
                reply = originals["execute"](cursor, query, params, **options)
                if item is not None:
                    item.update(
                        metadata=[]
                        if cursor.description is None
                        else [list(c) for c in cursor.description],
                        native_status=int(cursor.pgresult.status),
                        command_status=cursor.pgresult.command_status.decode(),
                        native_rows=cursor.pgresult.ntuples,
                        execute_returned=True,
                    )
                return reply
            except BaseException as error:
                if item is not None:
                    item["error"] = {
                        "kind": type(error).__name__,
                        "sqlstate": getattr(error, "sqlstate", None),
                    }
                raise

        def fetch(method):
            def observed(cursor, *args, **kwargs):
                reply = originals[method](cursor, *args, **kwargs)
                item = cursors.get(cursor)
                if item is not None:
                    rows = (
                        ([] if reply is None else [reply])
                        if method == "fetchone"
                        else reply
                    )
                    item["fetches"].append(
                        {
                            "method": method,
                            "rows": encoded(rows),
                            "empty": not rows,
                            "normal": True,
                        }
                    )
                return reply

            return observed

        def close(cursor):
            answer = originals["close"](cursor)
            if cursor in cursor_records:
                cursor_records[cursor]["closed"] = True
                for index in cursor_records[cursor]["statements"]:
                    result["statements"][index]["closed"] = True
            return answer

        psycopg.RawCursor.execute = execute
        for method in ("fetchone", "fetchmany", "fetchall"):
            setattr(psycopg.RawCursor, method, fetch(method))
        psycopg.RawCursor.close = close
    else:
        observer = (ADBCCalls if route == "postgres_adbc" else MySQLCalls)(owner)
    # The original event readers are active only around actual native methods.
    # Expensive pure semantic verification remains timed by the real owner but
    # is outside passive driver tracing; no native call or return is replaced.
    native_wrappers = []

    def observed_method(original):
        def observed(*args, **kwargs):
            obj = args[0]
            matches = (
                obj is owner
                or getattr(obj, "owner", None) is owner
                or any(obj is c for c in getattr(owner, "_connections", ()))
            )
            if not matches:
                return original(*args, **kwargs)
            previous = sys.getprofile()
            trace = sys.gettrace()
            sys.setprofile(observer.observe)
            try:
                return original(*args, **kwargs)
            finally:
                sys.setprofile(previous)
                sys.settrace(trace)

        return observed

    def wrap_native(cls, methods):
        for name in methods:
            original = getattr(cls, name)
            native_wrappers.append((cls, name, original))
            setattr(cls, name, observed_method(original))

    if route == "postgres_adbc":
        from pietto._project.project_execution_postgres_adbc_native import (
            NativeStatement,
        )

        wrap_native(NativeStatement, ("_execute", "fetch", "close"))
        wrap_native(PostgresADBCExecution, ("_refresh",))
        verify = PostgresADBCExecution._verify_submission

        def untapped_verification(self, statement):
            previous, trace = sys.getprofile(), sys.gettrace()
            sys.setprofile(original_profile)
            sys.settrace(original_trace)
            try:
                return verify(self, statement)
            finally:
                sys.setprofile(previous)
                sys.settrace(trace)

        native_wrappers.append((PostgresADBCExecution, "_verify_submission", verify))
        setattr(PostgresADBCExecution, "_verify_submission", untapped_verification)
    elif route == "mysql_rows":
        connection_type = importlib.import_module(
            "mysql.connector.connection"
        ).MySQLConnection
        wrap_native(
            connection_type,
            (
                "cmd_stmt_prepare",
                "cmd_stmt_execute",
                "get_rows",
                "cmd_query",
                "cmd_stmt_close",
            ),
        )

    original_commit = Enumeration.commit_page

    def committed(self, checked, **options):
        enumeration = self
        reply = original_commit(enumeration, checked, **options)
        if enumeration is owner.enumeration:
            fact = page_data(checked.request, enumeration.query)
            fact.update(
                sql=checked.request.native.sql.decode(),
                arguments=encoded((checked.request.native.arguments,))[0],
                accepted_progress=enumeration.progress,
            )
            result["pages"].append(fact)
            if route == "postgres_adbc":
                observer.pages.append(
                    {
                        "page": page_data(checked.request, enumeration.query),
                        "progress": enumeration.progress,
                    }
                )
        return reply

    Enumeration.commit_page = committed
    original_finish = owner._finish
    injected_finalizer = False

    def finish(commit):
        nonlocal injected_finalizer
        if (
            commit
            and not injected_finalizer
            and control in ("finalize_error", "finalize_graft")
        ):
            injected_finalizer = True
            if control == "finalize_graft":
                with owner._owned_connection.cursor() as cursor:
                    cursor.execute("COMMIT")
                    cursor.execute(
                        "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY"
                        if route == "mysql_rows"
                        else "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"
                    )
                result["interventions"].append(
                    {"kind": "actual_transaction_replaced_after_data_eof"}
                )
            owner._primary = ex.ExecutionFailure(
                "injected_before_finalization", "ValueError"
            )
            owner._delivery = "FAILED"
            result["interventions"].append(
                {"kind": "injected_primary_before_finalizer", "source": owner._source}
            )
            return original_finish(False)
        return original_finish(commit)

    if control in ("finalize_error", "finalize_graft"):
        owner._finish = finish
    started = time.monotonic()
    retained = []
    try:
        if control == "pre_cancel":
            owner.cancel()
        with owner:
            for batch in owner:
                with batch:
                    array = pa.record_batch(batch)
                    retained.append(array)
                    result["schemas"].append(
                        [[f.name, str(f.type), f.nullable] for f in array.schema]
                    )
                    result["rows"].extend(
                        encoded(
                            tuple(
                                tuple(
                                    array.column(i)[j].as_py()
                                    for i in range(array.num_columns)
                                )
                                for j in range(array.num_rows)
                            )
                        )
                    )
                if control in (
                    "consumer_error",
                    "transaction_graft",
                    "cancel_after_batch",
                ):
                    if control == "transaction_graft":
                        if route != "postgres_rows":
                            raise ValueError("S10 control route")
                        with owner._owned_connection.cursor() as cursor:
                            cursor.execute("COMMIT")
                            cursor.execute(
                                "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"
                            )
                        result["interventions"].append(
                            {"kind": "actual_transaction_replaced_before_primary_error"}
                        )
                    elif control == "cancel_after_batch":
                        result["interventions"].append(
                            {"kind": "cancel_return", "value": owner.cancel()}
                        )
                    raise ValueError("injected consumer failure")
            if control == "delivery_after_eof":
                raise ValueError(
                    "injected delivery failure after actual EOF and finalization"
                )
    except BaseException as error:
        result["failure"] = {
            "kind": type(error).__name__,
            "category": str(error).replace(base.access.password, "<redacted>"),
            "message": str(error).replace(base.access.password, "<redacted>"),
            "sqlstate": getattr(error, "sqlstate", None),
        }
    finally:
        owner.close()
        Enumeration.commit_page = original_commit
        if route == "postgres_rows":
            for method, original in originals.items():
                setattr(psycopg.RawCursor, method, original)
        else:
            for cls, method, original in reversed(native_wrappers):
                setattr(cls, method, original)
            sys.setprofile(original_profile)
            sys.settrace(original_trace)
    result.update(
        outcome=asdict(owner.outcome),
        layers=asdict(ex.compiled_attempt_outcome(owner)),
        session=owner.session_id,
        context=owner._profile_context if route == "postgres_rows" else owner.context,
        control_events=owner.control_events,
        control_joined=owner.control_joined,
        guard_states=None if owner.guards is None else owner.guards.states,
        guard_events=owner.guard_events,
        seconds=time.monotonic() - started,
        progress=None if owner.enumeration is None else owner.enumeration.progress,
        bound_schema=None
        if owner._payloads is None
        else [
            [f.name, str(f.type), f.nullable] for f in owner._payloads.binding.schema
        ],
        post_close_rows=encoded(
            tuple(
                tuple(a.column(i)[j].as_py() for i in range(a.num_columns))
                for a in retained
                for j in range(a.num_rows)
            )
        ),
    )
    if owner.guards is not None and owner.guards.native is not None:
        result["guard_native"] = native_record(owner.guards.native)
    if owner.source_admissions is not None:
        result["admission"] = observation_data(owner.source_admissions)
    if route == "postgres_rows":
        result["cursors"] = list(cursor_records.values())
    if route == "mysql_rows":
        result.update(
            assurance=owner.assurance,
            deployment_schemas=("phase66",),
            batch_rows=base.limits.batch_rows,
            metadata=owner.actual_metadata,
            events=observer.events,
            epoch=owner._epoch,
            initial_epoch=owner._initial_epoch,
            environment=owner.environment,
            role=base.access.account,
            sessions=[
                c.connection_id
                for c in owner._connections
                if c.connection_id is not None
            ],
        )
        result["statements"] = [
            dict(
                sql=s.sql.hex(),
                arguments=encoded((s.arguments,))[0],
                purpose=s.purpose,
                terminal=s.terminal,
                prepared=s.prepared,
                metadata=s.metadata,
                metadata_eof=s.metadata_eof,
                closed=s.closed,
                executed=s.executed,
                close_send=s.close_send,
            )
            for s in owner._statements
        ]
        result["sources"] = [asdict(s) for s in owner._sources]
        result["source_edges"] = (
            None if owner._qualification is None else owner._qualification.edges
        )
        result["security"] = (
            None if owner._qualification is None else owner._qualification.security
        )
    elif route == "postgres_adbc":
        result["statements"] = observer.statements
        result["copy_checkpoints"] = observer.copy_checkpoints
        result["flat_pages"] = result["pages"]
        result["pages"] = observer.pages
    if route != "mysql_rows":
        result["environment"] = (
            base.artifact.request.release,
            "repeatable read" if base.isolation == "stable" else "serializable",
            True,
            "UTF8",
        )
        result["role"] = base.access.user
        result["native_context"] = (
            None
            if owner._context_native is None
            else native_data(owner._context_native)
        )
        q = owner._qualification
        result["qualification"] = (
            None
            if q is None
            else {
                "roots": q.roots,
                "paths": q.paths,
                "context": q.context,
                "replies": [
                    {
                        "kind": r.kind,
                        "arguments": r.arguments,
                        "rows": r.rows,
                        "native": native_data(r.native),
                    }
                    for r in q.replies
                ],
                "basis": q.definition_stability,
                "compliance": q.premise_compliance,
                "native_lifetime": q.native_lifetime_protection,
            }
        )
    result["premise"] = {
        "route": route,
        "basis": "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE",
        "schemas": ["phase66"] if route == "mysql_rows" else ["public", "pg_catalog"],
        "roots": [[s.namespace, s.name] for s in base.artifact.request.sources],
        "access": {"database": base.access.database, "user": base.access.user},
    }
    return result


def representative_pilot(
    directory, ledger, *, target="postgres", cells=None, seconds=180
):
    """A few original guarded/refined mechanisms on the intended raw observer."""
    from _pietto_phase68_slice7_cases import manifest, case_preparation
    from _pietto_phase68_slice7_probe import setup, fill, refinement
    from _pietto_phase68_slice6_probe import manager, session_gone
    from _pietto_phase68_slice8_probe import event
    from _pietto_target_conformance_resources import Resources
    from pietto._project.project_guard_preparation import prepare_guarded_output
    from pietto._project.project_guard_program import prepare_program
    from pietto._project.project_execution_template import (
        prepare_live_template,
        bind_values,
    )
    from pietto._project import project_execution as ex
    from _pietto_phase68_slice10_check import check_representative

    names = (
        "bag_one",
        "bag_two_equal_null",
        "source_text_wide",
        "bound_four",
        "refined_tied_subject",
        "bound_four_refined",
    )
    routes = (
        ("mysql_rows",) if target == "mysql" else ("postgres_rows", "postgres_adbc")
    )
    selected = (
        tuple((route, name) for name in names for route in routes)
        if cells is None
        else tuple(cells)
    )
    if (
        not selected
        or len(set(selected)) != len(selected)
        or any(route not in routes or name not in names for route, name in selected)
    ):
        raise ValueError("S10_REPRESENTATIVE_CELLS")
    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources(target, pins["targets"][target], directory)
    event(
        ledger,
        {
            "kind": "s10_representative_pilot_start",
            "directory": str(directory),
            "target": target,
            "names": names,
            "selected": selected,
        },
        targeted_live_family_starts=1,
        source_db_lifecycle_starts=1,
    )
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
    report: dict[str, Any] = {
        "status": "STARTED",
        "records": [],
        "names": names,
        "target": target,
        "entry": "live",
        "origin": "source",
    }
    path = directory / (PREFIX + "representative.json")
    started = time.monotonic()
    try:
        resource.acquire()
        if target == "mysql":
            manager(resource, "USE phase66")
        setup(resource)
        if target == "mysql":
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
        for name in names:
            if not any(n == name for _, n in selected):
                continue
            case = next(c for c in manifest() if c["name"] == name)
            options = case["options"]
            fill(
                resource,
                case["lhs"],
                case["rhs"],
                wide_text=options.get("wide_text", False),
            )
            preparation = case_preparation(directory / (PREFIX + name), target, case)
            output = prepare_guarded_output(preparation)
            query = (
                refinement(resource, preparation, output)
                if options.get("refined")
                else None
            )
            program = prepare_program(preparation, refinement=query)
            template = prepare_live_template(
                preparation.artifact, guarded=preparation, refinement=query
            )
            for route in routes:
                if (route, name) not in selected:
                    continue
                binding = bind_values(
                    template,
                    tuple(
                        zip(
                            template.slots,
                            (v.value for v in preparation.artifact.fixed_values),
                            strict=True,
                        )
                    ),
                )
                premise: dict[str, Any]
                if target == "mysql":
                    a = ex.MySQLAccess(
                        "127.0.0.1",
                        resource.port,
                        "phase66",
                        "pietto_query",
                        resource._passwords[1],
                        str(resource.ca_path),
                        "pietto_query@%",
                        verify_identity=False,
                        loopback_tls_exception=True,
                    )
                    premise = {
                        "mysql_deployment": ex.MySQLDeploymentPremise(
                            a, binding.artifact.request.sources, ("phase66",)
                        )
                    }
                else:
                    a = ex.PostgresAccess(
                        "127.0.0.1",
                        resource.port,
                        "phase66",
                        "pietto_query",
                        resource._passwords[1],
                        "disable",
                    )
                    premise = {
                        "postgres_deployment": ex.PostgresDeploymentPremise(
                            a,
                            binding.artifact.request.sources,
                            ("public", "pg_catalog"),
                            route,
                        )
                    }
                request = ex.prepare_compiled_execution(
                    binding,
                    a,
                    route=route,
                    limits=ex.ExecutionLimits(batch_rows=2, seconds=seconds),
                    **premise,
                )
                raw = collect_owned(request)
                raw.update(case=name, entry="live", origin="source")
                raw["session_gone"] = (
                    None
                    if raw["session"] is None
                    else session_gone(resource, raw["session"])
                )
                raw["sessions_gone"] = {
                    str(s): session_gone(resource, s) for s in raw.get("sessions", ())
                }
                report["records"].append(raw)
                path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
                check_representative(json.loads(json.dumps(raw)), case, program)
                print(
                    target, route, name, "checked", round(raw["seconds"], 3), flush=True
                )
        report["status"] = "PASS"
    except BaseException as error:
        report.update(
            status="FAILED",
            error_kind=type(error).__name__,
            error=resource.without_secrets(str(error)),
        )
        raise
    finally:
        report["cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - started
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        event(
            ledger,
            {
                "kind": "s10_representative_pilot_terminal",
                "status": report["status"],
                "directory": str(directory),
                "seconds": report["seconds"],
                "cleanup": report["cleanup"],
            },
        )
    return report


def native_manifest(target):
    """Current original denominators; target exclusions stay explicit."""
    from _pietto_phase68_slice5_cases import CASES as ordinary
    from _pietto_phase68_slice6_cases import CASES as refined
    from _pietto_phase68_slice7_cases import manifest

    exclusions = (
        {("V_join_full", "null_keys"), ("A_window_groups", "exclude")}
        if target == "mysql"
        else set()
    )
    result = []
    for group, cases in (
        (
            "ordinary",
            (
                *ordinary,
                *(
                    ("R2_seven", f"{p}_{state}")
                    for p in (39, 65)
                    for state in ("values", "empty", "null")
                ),
            ),
        ),
        ("refined", (*refined, *(("R2_bound", v) for v in ("A", "B", "A_again")))),
    ):
        for case, variant in cases:
            result.append(
                {
                    "group": group,
                    "case": case,
                    "variant": variant,
                    "excluded": (case, variant) in exclusions,
                }
            )
    if target == "postgres":
        result.extend(
            {
                "group": "ordinary",
                "case": "G_scan_row_domains",
                "variant": variant,
                "excluded": False,
            }
            for variant in ("inherited_parent", "view_rows")
        )
    for case in manifest():
        result.append(
            {
                "group": "guarded",
                "case": case["name"],
                "variant": None,
                "excluded": target == "mysql"
                and case["options"].get("postgres_only", False),
            }
        )
    return result


def build_native_reference(directory, target, cell, providers):
    """Build-only acquisition through original source/case/requirement owners."""
    from _pietto_phase68_slice6_cases import original, source_requirements
    from _pietto_phase68_slice7_cases import manifest, case_preparation
    from pietto._project.project_guard_preparation import (
        prepare_guarded_output,
        prepare_guarded_template,
    )
    from pietto._project.project_execution_template import prepare_template, bind_values
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_refinement import prepare_refinement, TieRefinement

    preparation: Any = None
    query: Any = None
    binding: Any = None
    artifact: Any = None
    output: Any = None
    options = {}
    if cell["group"] == "guarded":
        case = next(c for c in manifest() if c["name"] == cell["case"])
        options = case["options"]
        preparation = case_preparation(directory, target, case)
        if "binding_values" in options:
            template = prepare_guarded_template(preparation)
            binding = bind_values(
                template,
                tuple(zip(template.slots, options["binding_values"], strict=True)),
            )
            preparation = binding.guarded
        artifact = preparation.artifact
        output = prepare_guarded_output(preparation, binding=binding)
    else:
        artifact = original(directory, target, cell["case"], cell["variant"])
        if artifact is None:
            if not cell["excluded"]:
                raise ValueError("S10_UNEXPECTED_ORIGINAL_EXCLUSION")
            return None
        if cell["case"] == "R2_bound":
            template = prepare_template(artifact)
            values = (1, 2) if cell["variant"] == "B" else (0, 1)
            binding = bind_values(
                template, tuple(zip(template.slots, values, strict=True))
            )
            artifact = binding.artifact
        output = prepare_output(artifact, binding=binding)
    if cell["group"] == "refined" or options.get("refined"):
        role = options.get("role", "pietto_query") + ("@%" if target == "mysql" else "")
        query = prepare_refinement(
            artifact,
            source_requirements(artifact, providers, role),
            policy=TieRefinement(),
            output=output,
            binding=binding,
        )
    return artifact, preparation, query, output, binding


def guard_providers(resource):
    """Same native definitions and provider coordinates as original S07 setup."""
    from _pietto_phase68_slice6_probe import manager, quoted

    result = []
    namespace = "public" if resource.target == "postgres" else "phase66"
    for side in ("lhs", "rhs"):
        name = "phase66 " + side + " é"
        relation = (
            quoted(namespace, resource.target) + "." + quoted(name, resource.target)
        )
        if resource.target == "postgres":
            manager(resource, "SET search_path=pg_catalog")
            definition = manager(
                resource,
                "SELECT pg_catalog.pg_get_viewdef($1::regclass,true)",
                (relation,),
            )[0][0]
        else:
            definition = manager(resource, "SHOW CREATE VIEW " + relation)[0][1]
        result.append(
            {
                "namespace": namespace,
                "name": name,
                "provider": "p68-guard-" + side,
                "version": "v1",
                "revision": "r1",
                "registry": "p68_guard_registry_" + side,
                "definition": definition,
                "tokens": ["token"],
            }
        )
    return result


CASE_WORKER = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import json, importlib, hashlib, time, os, shutil
from pathlib import Path
config=json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["runtime_cwd"])
if config["origin"] == "source":
    sys.path.insert(0,config["library_source"])
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_schema import scalar_read
from pietto._project.project_execution_template import prepare_live_template,prepare_compiled_template,bind_values
from pietto._project import project_execution as ex, model, trusted_source
import pietto.ast_nodes as nodes
if config["entry"] == "live":
    sys.path.insert(0,config["build_helpers"])
    from _pietto_phase68_slice10_probe import build_native_reference
    reference=build_native_reference(Path(config["live_project"]),config["target"],config["cell"],config["providers"])
    artifact,preparation,query,output,binding=reference
    template=prepare_live_template(artifact,guarded=preparation,refinement=query)
    del artifact,preparation,query,output,binding,reference,build_native_reference
    shutil.rmtree(config["live_project"])
    sys.path.remove(config["build_helpers"])
    for name in tuple(sys.modules):
        if name.startswith(("_pietto_","test_phase","s04_","s03_")):
            del sys.modules[name]
# S10_FORBIDDEN_BOUNDARY
if config["entry"] == "bundle":
    root=load_compiled(Path(config["bundle"]).read_bytes(),expected_pin=config["pin"],accepted_producer=config["producer"],accepted_compatibility=tuple(config["compatibility"]))
    template=prepare_compiled_template(root)
values=tuple(scalar_read(v).value for v in config["values"])
results=[]
for route in config["routes"]:
    started=time.monotonic()
    bound=bind_values(template,tuple(zip(template.slots,values,strict=True)))
    options=config["options"]
    user=options.get("role","pietto_query")
    if route == "mysql_rows":
        a=ex.MySQLAccess("127.0.0.1",config["port"],"phase66",user,config["password"],config["ca_path"],user+"@%",verify_identity=False,loopback_tls_exception=True)
        premise={"mysql_deployment":ex.MySQLDeploymentPremise(a,bound.artifact.request.sources,("phase66",))}
    else:
        a=ex.PostgresAccess("127.0.0.1",config["port"],"phase66",user,config["password"],"disable")
        premise={"postgres_deployment":ex.PostgresDeploymentPremise(a,bound.artifact.request.sources,("public","pg_catalog"),route)}
    request=ex.prepare_compiled_execution(bound,a,route=route,limits=ex.ExecutionLimits(batch_rows=options.get("page_size",2),seconds=config["request_seconds"]),isolation=options.get("isolation","stable"),allow_guard_sql=options.get("allow",True),**premise)
    record=collect_owned(request)
    record.update(case=config["cell"]["case"],variant=config["cell"]["variant"],entry=config["entry"],origin=config["origin"],binding_reference=bound.instance_reference,preparation_and_attempt_seconds=time.monotonic()-started)
    results.append(record)
    encoded_record=json.dumps({"results":results,"forbidden_calls":forbidden_calls},ensure_ascii=False).encode()
    if len(encoded_record)>64*1024*1024:
        raise ValueError("S10 bounded raw observation exceeded")
    Path(config["raw"]).write_bytes(encoded_record)
origins={}
for name,module in tuple(sys.modules.items()):
    filename=getattr(module,"__file__",None)
    if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
        path=Path(filename).resolve();origins[name]={"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
Path(config["raw"]).write_text(json.dumps({"results":results,"forbidden_calls":forbidden_calls,"origins":origins,"prefix":sys.prefix},ensure_ascii=False))
"""


def case_worker_program():
    """Ship only native observers, data serializers and source-free subject code."""
    from _pietto_phase68_slice6_probe import use_data
    from _pietto_phase68_slice4_probe import s01

    header = "import sys, importlib, importlib.metadata, linecache, struct\nfrom pathlib import Path\nfrom typing import Any\nfrom decimal import Decimal\nfrom datetime import datetime\nfrom uuid import UUID\nfrom types import SimpleNamespace\n"
    helpers = inspect.getsource(s01.scalar) + "\ns01=SimpleNamespace(scalar=scalar)\n"
    for function in (
        encoded,
        use_data,
        page_data,
        observation_data,
        native_record,
        native_data,
    ):
        helpers += "\n" + inspect.getsource(function)
    for cls, name in ((ADBCCalls, "ADBCCalls"), (MySQLCalls, "MySQLCalls")):
        code = inspect.getsource(cls).replace("class Calls:", "class " + name + ":", 1)
        code = code.replace(
            "            from _pietto_phase68_slice6_probe import page_data\n", ""
        )
        helpers += "\n" + code
    helpers += "\n" + inspect.getsource(collect_owned)
    boundary = (
        "forbidden_calls = []"
        + WORKER.split("forbidden_calls = []", 1)[1].split(
            "load_started = time.monotonic()", 1
        )[0]
    )
    return header + helpers + CASE_WORKER.replace("# S10_FORBIDDEN_BOUNDARY", boundary)


def acquire_matrix_group(
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
    controls=False,
):
    """One owned database, original fixtures, fresh registered isolated subjects."""
    from _pietto_phase68_slice6_probe import (
        setup as setup_general,
        manager,
        session_gone,
    )
    from _pietto_phase68_slice7_probe import setup as setup_guard, fill
    from _pietto_phase68_slice7_cases import manifest as guard_manifest
    from _pietto_phase68_slice8_probe import event, worker_process
    from _pietto_target_conformance_resources import Resources, clean_environment
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_schema import Scalar, scalar_wire
    from _pietto_phase68_slice10_check import check_matrix_record, check_matrix_origin

    directory.mkdir(mode=0o700)
    declarations = [
        c
        for c in native_manifest(target)
        if (c["group"] == "guarded") == (group == "guarded")
        and (selected is None or (c["group"], c["case"], c["variant"]) in selected)
    ]
    if not declarations:
        raise ValueError("S10_EMPTY_MATRIX_GROUP")
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
    event(
        ledger,
        {
            "kind": "s10_matrix_group_start",
            "directory": str(directory),
            "target": target,
            "group": group,
            "denominator": declarations,
            "cells": cells,
            "request_seconds": request_seconds,
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
    report_path = directory / (PREFIX + "matrix-group.json")
    private = directory / (PREFIX + "private-input.json")
    started = time.monotonic()
    try:
        resource.acquire()
        if target == "mysql":
            manager(resource, "USE phase66")
        if group == "guarded":
            setup_guard(resource)
            providers = guard_providers(resource)
        else:
            providers = setup_general(resource)
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
        program = case_worker_program()
        for index, cell in enumerate(declarations):
            build_directory = directory / (PREFIX + str(index) + "-reference-source")
            if cell["excluded"] and cell["group"] == "guarded":
                # Original explicit PostgreSQL-only source selection is the exclusion owner.
                report["records"].append(
                    {"cell": cell, "status": "ORIGINAL_TARGET_EXCLUSION"}
                )
                continue
            reference = build_native_reference(build_directory, target, cell, providers)
            if cell["excluded"]:
                if reference is not None:
                    raise ValueError("S10_LOST_ORIGINAL_TARGET_EXCLUSION")
                report["records"].append(
                    {"cell": cell, "status": "ORIGINAL_TARGET_EXCLUSION"}
                )
                continue
            if reference is None:
                raise ValueError("S10_MISSING_ORIGINAL_REFERENCE")
            artifact, preparation, query, output, binding = reference
            if (
                controls
                and cell["group"] == "ordinary"
                and cell["case"] == "G_emission_table_bag"
            ):
                report["controls"] = str(
                    collect_control_family(resource, directory, reference, cell)
                )
                controls = False
            built = build_compiled(artifact, guarded=preparation, refinement=query)
            bundle = directory / (PREFIX + str(index) + "-bundle.json")
            bundle.write_bytes(built.payload)
            bundle.chmod(0o600)
            shutil.rmtree(build_directory)
            case = (
                None
                if cell["group"] != "guarded"
                else next(c for c in guard_manifest() if c["name"] == cell["case"])
            )
            options = {} if case is None else case["options"]
            for origin, entry in cells:
                if origin == "installed" and wheel is None:
                    raise ValueError("S10_INSTALLED_WHEEL_REQUIRED")
                if case is not None:
                    fill(
                        resource,
                        case["lhs"],
                        case["rhs"],
                        wide_text=options.get("wide_text", False),
                    )
                label = PREFIX + str(index) + "-" + origin + "-" + entry
                runtime = directory / (label + "-runtime")
                runtime.mkdir(mode=0o700)
                raw = directory / (label + "-raw.json")
                config = {
                    "runtime_cwd": str(runtime),
                    "origin": origin,
                    "entry": entry,
                    "target": target,
                    "cell": cell,
                    "options": options,
                    "providers": providers,
                    "build_helpers": str(ROOT / "tests"),
                    "live_project": str(directory / (label + "-source")),
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
                    "routes": ["mysql_rows"]
                    if target == "mysql"
                    else ["postgres_rows", "postgres_adbc"],
                    "raw": str(raw),
                }
                handoff = directory / (label + "-handoff.json")
                public_input = {
                    k: v for k, v in config.items() if k not in ("password", "ca_path")
                }
                fd = os.open(handoff, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as stream:
                    json.dump(public_input, stream, ensure_ascii=False)
                descriptor = os.open(
                    private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                with os.fdopen(descriptor, "w") as stream:
                    json.dump(config, stream)
                with (directory / (label + "-worker.log")).open("wb") as log:
                    status = worker_process(
                        [str(interpreter), "-I", "-B", "-c", program, str(private)],
                        clean_environment(),
                        ledger,
                        log,
                        origin=origin,
                        group="s10-" + group + "-" + entry,
                        directory=directory,
                        seconds=2 * request_seconds + 240,
                    )
                private.unlink(missing_ok=True)
                item = {
                    "cell": cell,
                    "origin": origin,
                    "entry": entry,
                    "raw": str(raw),
                    "worker_exit": status,
                    "handoff": str(handoff),
                    "checked": False,
                }
                report["records"].append(item)
                report_path.write_text(json.dumps(report, indent=2) + "\n")
                if status:
                    raise ValueError("S10_ISOLATED_NATIVE_WORKER_FAILED")
                data = json.loads(raw.read_text())
                check_matrix_origin(data, config, interpreter, wheel)
                histories = []
                for record in data["results"]:
                    record["session_gone"] = (
                        None
                        if record["session"] is None
                        else session_gone(resource, record["session"])
                    )
                    record["sessions_gone"] = {
                        str(s): session_gone(resource, s)
                        for s in record.get("sessions", ())
                    }
                    histories.append(
                        {
                            "attempt": record["outcome"]["attempt"],
                            "session_gone": record["session_gone"],
                            "sessions_gone": record["sessions_gone"],
                        }
                    )
                # Preserve parent observations separately; never rewrite child raw.
                terminal = directory / (label + "-sessions.json")
                terminal.write_text(json.dumps(histories, indent=2) + "\n")
                item["sessions"] = str(terminal)
                for record in data["results"]:
                    check_matrix_record(record, cell, reference, case=case)
                item["raw_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
                item["sessions_sha256"] = hashlib.sha256(
                    terminal.read_bytes()
                ).hexdigest()
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
                "kind": "s10_matrix_group_terminal",
                "directory": str(directory),
                "status": report["status"],
                "cleanup": report["cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


def collect_control_family(resource, directory, reference, cell):
    from _pietto_phase68_slice6_probe import session_gone
    from pietto._project.project_execution_template import (
        prepare_live_template,
        bind_values,
    )
    from pietto._project import project_execution as ex
    from _pietto_phase68_slice10_check import check_control_family

    artifact = reference[0]
    template = prepare_live_template(artifact)
    route = "mysql_rows" if resource.target == "mysql" else "postgres_rows"
    records = []
    controls = (
        "pre_cancel",
        "short_deadline",
        "finalize_error",
        "finalize_graft",
        "delivery_after_eof",
        "cancel_after_batch",
        "fresh_success",
    )
    path = directory / (PREFIX + "actual-controls.json")
    for control in controls:
        binding = bind_values(
            template,
            tuple(
                zip(
                    template.slots,
                    (v.value for v in artifact.fixed_values),
                    strict=True,
                )
            ),
        )
        premise: dict[str, Any]
        if route == "mysql_rows":
            a = ex.MySQLAccess(
                "127.0.0.1",
                resource.port,
                "phase66",
                "pietto_query",
                resource._passwords[1],
                str(resource.ca_path),
                "pietto_query@%",
                verify_identity=False,
                loopback_tls_exception=True,
            )
            premise = {
                "mysql_deployment": ex.MySQLDeploymentPremise(
                    a, binding.artifact.request.sources, ("phase66",)
                )
            }
        else:
            a = ex.PostgresAccess(
                "127.0.0.1",
                resource.port,
                "phase66",
                "pietto_query",
                resource._passwords[1],
                "disable",
            )
            premise = {
                "postgres_deployment": ex.PostgresDeploymentPremise(
                    a, binding.artifact.request.sources, ("public", "pg_catalog"), route
                )
            }
        request = ex.prepare_compiled_execution(
            binding,
            a,
            route=route,
            limits=ex.ExecutionLimits(
                batch_rows=2, seconds=0.001 if control == "short_deadline" else 30
            ),
            **premise,
        )
        record = collect_owned(request, control=control)
        record.update(
            control=control,
            entry="live",
            origin="source",
            case=cell["case"],
            variant=cell["variant"],
        )
        record["session_gone"] = (
            None
            if record["session"] is None
            else session_gone(resource, record["session"])
        )
        record["sessions_gone"] = {
            str(s): session_gone(resource, s) for s in record.get("sessions", ())
        }
        records.append(record)
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
        print(
            resource.target,
            "control",
            control,
            record["outcome"]["transaction"],
            flush=True,
        )
    check_control_family(json.loads(json.dumps(records)), reference, cell)
    return path


def campaign_inputs():
    """Actual source/reference/observer closure consumed across the readiness boundary."""
    import subprocess

    paths = set(
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "--",
                "src",
                "tests",
                "scripts",
                "pyproject.toml",
                "uv.lock",
                "ci/phase68-executor-premise-requirements.txt",
            ],
            cwd=ROOT,
            text=True,
        ).splitlines()
    )
    paths.update(
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "--others",
                "--exclude-standard",
                "--",
                "src",
                "tests",
                "scripts",
            ],
            cwd=ROOT,
            text=True,
        ).splitlines()
    )
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in sorted(paths)
        if (ROOT / name).is_file()
    }


def complete_campaign(directory, ledger, interpreter, wheel, readiness):
    """Only an exact current GREEN permits the complete declared four-cell matrix."""
    from _pietto_phase68_slice8_probe import event

    event(
        ledger,
        {
            "kind": "s10_complete_campaign_start",
            "directory": str(directory),
            "readiness": str(readiness),
        },
        complete_s10_live_campaign_starts=1,
    )
    report: dict[str, Any] = {
        "status": "STARTED",
        "readiness": str(readiness),
        "wheel": str(wheel),
        "groups": [],
    }
    path = directory / (PREFIX + "complete-campaign.json")
    started = time.monotonic()
    owned_directory = False
    try:
        directory.mkdir(mode=0o700)
        owned_directory = True
        state = json.loads(readiness.read_text())
        if (
            state["state"] != "GREEN_FOR_CURRENT_INPUTS"
            or state["inputs"] != campaign_inputs()
            or state["wheel_sha256"] != hashlib.sha256(wheel.read_bytes()).hexdigest()
        ):
            raise ValueError("S10_CURRENT_READINESS_REQUIRED")
        for target in ("postgres", "mysql"):
            for group in ("general", "guarded"):
                result = acquire_matrix_group(
                    directory / (PREFIX + target + "-" + group),
                    ledger,
                    interpreter,
                    target=target,
                    group=group,
                    cells=(
                        ("source", "live"),
                        ("source", "bundle"),
                        ("installed", "live"),
                        ("installed", "bundle"),
                    ),
                    wheel=wheel,
                    request_seconds=state["request_seconds"],
                )
                report["groups"].append(result)
                path.write_text(json.dumps(report, indent=2) + "\n")
        from _pietto_phase68_slice10_check import check_complete_campaign

        report["coverage"] = check_complete_campaign(report, state["denominator"])
        report["status"] = "PASS"
    except BaseException as error:
        report.update(
            status="FAILED",
            error_kind=type(error).__name__,
            failure_classification="UNRESOLVED_REQUIRES_CAUSAL_CLASSIFICATION_BEFORE_ANY_FULL_RESTART",
        )
        raise
    finally:
        report["seconds"] = time.monotonic() - started
        if owned_directory:
            path.write_text(json.dumps(report, indent=2) + "\n")
        event(
            ledger,
            {
                "kind": "s10_complete_campaign_terminal",
                "status": report["status"],
                "directory": str(directory),
                "seconds": report["seconds"],
            },
        )
    return report
