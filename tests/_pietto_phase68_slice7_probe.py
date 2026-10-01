"""Explicit, bounded S07 native acquisition; importing never opens a database."""

from dataclasses import asdict
from pathlib import Path
import hashlib
import importlib
from typing import Any
import json
import os
import subprocess
import sys
import time
import threading
import traceback

from _pietto_phase68_slice6_probe import (
    manager,
    quoted,
    s01,
    bridge_admission,
    adbc_page,
    metadata_description,
    page_data,
    observation_data,
    session_gone,
)
from _pietto_phase68_slice7_cases import planned
from _pietto_target_conformance_resources import Resources

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice07-"


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def ledger(path, event, **charges):
    value = json.loads(path.read_text())
    for name, amount in charges.items():
        value["used"][name] += amount
        if value["used"][name] > value["ceilings"][name]:
            raise ValueError("S07 action ceiling: " + name)
    value["events"].append(event)
    write(path, value)


def setup(resource):
    target = resource.target
    namespace = "public" if target == "postgres" else "phase66"
    for side in ("lhs", "rhs"):
        base = quoted(namespace, target) + "." + quoted("p68_guard_" + side, target)
        view = (
            quoted(namespace, target) + "." + quoted("phase66 " + side + " é", target)
        )
        registry = (
            quoted(namespace, target)
            + "."
            + quoted("p68_guard_registry_" + side, target)
        )
        manager(
            resource,
            "CREATE TABLE "
            + base
            + " ("
            + quoted("order.id", target)
            + " BIGINT NOT NULL,"
            + quoted("key value", target)
            + " BIGINT, token BIGINT NOT NULL PRIMARY KEY, source_version VARCHAR(32) NOT NULL DEFAULT 'v1')",
        )
        manager(
            resource,
            "CREATE TABLE "
            + registry
            + " (provider VARCHAR(64),version_tag VARCHAR(32),active INTEGER,revision VARCHAR(32))",
        )
        manager(
            resource,
            "INSERT INTO "
            + registry
            + " VALUES ('p68-guard-"
            + side
            + "','v1',1,'r1')",
        )
        role = "CURRENT_USER" if target == "postgres" else "CURRENT_USER()"
        restricted = "pietto_subset" if target == "postgres" else "pietto_subset@%"
        manager(
            resource,
            (
                "CREATE VIEW "
                if target == "postgres"
                else "CREATE SQL SECURITY INVOKER VIEW "
            )
            + view
            + (" WITH (security_invoker=true)" if target == "postgres" else "")
            + " AS SELECT b.* FROM "
            + base
            + " AS b WHERE b.source_version=(SELECT version_tag FROM "
            + registry
            + ") AND ("
            + role
            + "<>'"
            + restricted
            + "' OR b."
            + quoted("order.id", target)
            + "<>1)",
        )
    for side in ("lhs", "rhs"):
        text_type = (
            'TEXT COLLATE "C"'
            if target == "postgres"
            else "VARCHAR(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin"
        )
        manager(
            resource,
            "CREATE TABLE "
            + quoted(namespace, target)
            + "."
            + quoted("p68_guard_wide_" + side, target)
            + " ("
            + quoted("order.id", target)
            + " BIGINT NOT NULL,"
            + quoted("key value", target)
            + " "
            + text_type
            + ",token BIGINT NOT NULL PRIMARY KEY)",
        )
    from _pietto_phase68_slice5_probe import setup_seven

    setup_seven(resource)
    for sql, _secret in resource.role_statements():
        manager(resource, sql)
    if target == "postgres":
        manager(
            resource,
            "CREATE ROLE pietto_subset LOGIN PASSWORD '"
            + resource._passwords[1]
            + "' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS",
        )
        manager(resource, "GRANT CONNECT ON DATABASE phase66 TO pietto_subset")
        manager(resource, "GRANT USAGE ON SCHEMA public TO pietto_subset")
        manager(
            resource, "GRANT SELECT ON ALL TABLES IN SCHEMA public TO pietto_subset"
        )
        manager(resource, "GRANT pietto_subset TO pietto_query")
    else:
        manager(
            resource,
            "CREATE USER 'pietto_subset'@'%' IDENTIFIED BY '"
            + resource._passwords[1]
            + "'",
        )
        manager(resource, "GRANT SELECT,SHOW VIEW ON phase66.* TO 'pietto_subset'@'%'")
        manager(resource, "GRANT SHOW VIEW ON phase66.* TO 'pietto_query'@'%'")


def fill(resource, lhs, rhs, *, wide_text=False):
    target = resource.target
    namespace = "public" if target == "postgres" else "phase66"
    for side, rows in (("lhs", lhs), ("rhs", rhs)):
        name = (
            quoted(namespace, target)
            + "."
            + quoted(("p68_guard_wide_" if wide_text else "p68_guard_") + side, target)
        )
        manager(
            resource,
            "UPDATE "
            + quoted(namespace, target)
            + "."
            + quoted("p68_guard_registry_" + side, target)
            + " SET version_tag='v1',revision='r1'",
        )
        manager(resource, "DELETE FROM " + name)
        for token, row in enumerate(rows):
            args = "$1,$2,$3" if target == "postgres" else "?,?,?"
            manager(
                resource,
                "INSERT INTO "
                + name
                + " ("
                + quoted("order.id", target)
                + ","
                + quoted("key value", target)
                + ",token) VALUES ("
                + args
                + ")",
                (*row, token),
            )


def refinement(resource, preparation, output, *, versions=None, role="pietto_query"):
    from pietto._project.project_execution_source import RetainedSourceRequirement
    from pietto._project.project_refinement import TieRefinement, prepare_refinement

    target = resource.target
    requirements = []
    for source in preparation.artifact.request.sources:
        name = quoted(source.namespace, target) + "." + quoted(source.name, target)
        if target == "postgres":
            manager(resource, "SET search_path=pg_catalog")
            definition = manager(
                resource, "SELECT pg_catalog.pg_get_viewdef($1::regclass,true)", (name,)
            )[0][0]
        else:
            definition = manager(resource, "SHOW CREATE VIEW " + name)[0][1]
        side = "lhs" if source.name == "phase66 lhs é" else "rhs"
        requirements.append(
            RetainedSourceRequirement(
                source,
                "p68-guard-" + side,
                (versions or {}).get(side, ("v1", "r1"))[0],
                (versions or {}).get(side, ("v1", "r1"))[1],
                source.namespace,
                "p68_guard_registry_" + side,
                definition,
                ("token",),
                role if target == "postgres" else role + "@%",
                "Owned fixture is unchanged throughout this retained-source attempt.",
            )
        )
    return prepare_refinement(
        preparation.artifact, tuple(requirements), policy=TieRefinement(), output=output
    )


def origins():
    result = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
            result[name] = dict(
                path=filename,
                sha256=hashlib.sha256(Path(filename).read_bytes()).hexdigest(),
            )
    return result


def encoded(rows):
    return [[s01.scalar(v) for v in row] for row in rows]


def native_record(native) -> dict[str, Any]:
    program = native.statement.program
    slots = program.preparation.artifact.request.plan.literal_slots
    uses = []
    for use in native.uses:
        item = dict(domain=use.domain, index=use.index, value=s01.scalar(use.value))
        if use.domain == "original":
            (position,) = tuple(i for i, slot in enumerate(slots) if slot is use.owner)
            item.update(slot=position, original_use=use.original.ordinal)
        else:
            (position,) = tuple(
                i
                for i, control in enumerate(native.statement.controls)
                if control is use.owner
            )
            item["control"] = position
        uses.append(item)
    return dict(
        sql=native.sql.decode(),
        arguments=[s01.scalar(v) for v in native.arguments],
        kind=native.statement.kind,
        subjects=[
            [s.request_position, s.boundary_position] for s in native.statement.subjects
        ],
        uses=uses,
    )


def pg_attempt(
    resource,
    preparation,
    *,
    refined=None,
    allow=True,
    binding=None,
    page_size=2,
    isolation="stable",
    role="pietto_query",
    control=None,
):
    psycopg = importlib.import_module("psycopg")
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_execution_postgres as pg
    from pietto._project.project_execution import PostgresAccess, ExecutionLimits
    from pietto._project.project_guard_runtime import prepare_guarded_execution

    records, cursors, interventions = [], [], []
    injected = set()
    guard_entered, stop_control = threading.Event(), threading.Event()

    class Observed(psycopg.RawCursor):
        def __init__(self, connection, *args, **kwargs):
            super().__init__(connection, *args, **kwargs)
            self.cursor_record: dict[str, Any] = dict(
                ordinal=len(cursors),
                session=connection.info.backend_pid,
                statements=[],
                closed=False,
            )
            cursors.append(self.cursor_record)

        def execute(self, query, params=None, **options):
            self.observation: dict[str, Any] = dict(
                ordinal=len(records),
                cursor=self.cursor_record["ordinal"],
                sql=query,
                arguments=[] if params is None else [s01.scalar(v) for v in params],
                prepare=options.get("prepare"),
                api="psycopg.RawCursor.execute",
                fetches=[],
                closed=False,
            )
            records.append(self.observation)
            self.cursor_record["statements"].append(self.observation["ordinal"])
            if not hasattr(self, "owned_observations"):
                self.owned_observations = []
            self.owned_observations.append(self.observation)
            try:
                if (
                    control in ("cancel_guard", "deadline_guard")
                    and stream.guards is not None
                    and stream.guards.native is not None
                    and query == stream.guards.native.sql.decode()
                ):
                    guard_entered.set()
                result = super().execute(query, params, **options)
                self.observation.update(
                    execute_returned=True,
                    native_status=int(self.pgresult.status),
                    native_rows=self.pgresult.ntuples,
                    metadata=[]
                    if self.description is None
                    else [list(x) for x in self.description],
                )
                if (
                    control == "commit_loss"
                    and query == "COMMIT"
                    and "commit_loss" not in injected
                ):
                    injected.add("commit_loss")
                    interventions.append(
                        dict(
                            kind="injected_commit_response_loss",
                            native_execute_returned=True,
                        )
                    )
                    raise OSError("injected commit response loss")
                return result
            except BaseException as error:
                self.observation["error"] = dict(
                    kind=type(error).__name__, sqlstate=getattr(error, "sqlstate", None)
                )
                raise

        def fetchone(self):
            row = super().fetchone()
            self.observation["fetches"].append(
                dict(
                    method="fetchone",
                    rows=[] if row is None else encoded((row,)),
                    empty=row is None,
                )
            )
            return row

        def fetchmany(self, size=0):
            rows = super().fetchmany(size)
            self.observation["fetches"].append(
                dict(method="fetchmany", rows=encoded(rows), empty=not rows)
            )
            return rows

        def fetchall(self):
            rows = super().fetchall()
            self.observation["fetches"].append(
                dict(method="fetchall", rows=encoded(rows), normal=True)
            )
            return rows

        def close(self):
            super().close()
            self.cursor_record["closed"] = True
            for observation in getattr(self, "owned_observations", ()):
                observation["closed"] = True
            if (
                control == "cleanup_error"
                and "cleanup_error" not in injected
                and stream.guards is not None
                and stream.guards.native is not None
                and getattr(self, "observation", {}).get("sql")
                == stream.guards.native.sql.decode()
            ):
                injected.add("cleanup_error")
                interventions.append(
                    dict(kind="injected_cursor_close_error", native_close_returned=True)
                )
                raise OSError("injected cursor close error")

    connect = pg._connect

    def observed(request):
        connection = connect(request)
        connection.cursor_factory = Observed
        return connection

    request = prepare_guarded_execution(
        preparation,
        PostgresAccess(
            "127.0.0.1",
            resource.port,
            "phase66",
            role,
            resource._passwords[1],
            "disable",
        ),
        limits=ExecutionLimits(
            batch_rows=page_size, seconds=3 if control == "deadline_guard" else 90
        ),
        refinement=refined,
        binding=binding,
        isolation=isolation,
        allow_guard_sql=allow,
    )
    stream = pg.PostgresExecution(request)
    pg._connect = observed
    result: dict[str, Any] = dict(
        rows=[],
        statements=records,
        cursors=cursors,
        attempt=stream.attempt,
        route="postgres_rows",
        mode="refined" if refined else "ordinary",
        pages=[],
        interventions=interventions,
    )
    original_verify = pg.verify_guarded_execution
    original_header = pg.GuardRun.accept_header
    original_guard = pg.GuardRun.accept_guard_result

    def after_guard():
        if "after_guard" in injected:
            return
        injected.add("after_guard")
        if stream.guards is None:
            raise ValueError("guard callback without guard owner")
        interventions.append(dict(kind="guard_fulfilled", states=stream.guards.states))
        if control == "writer_version":
            interventions.append(
                dict(
                    kind="writer_begin",
                    boundary="after_guard_before_page"
                    if refined
                    else "after_shared_native_before_public",
                )
            )
            publish_version(resource)
            interventions.append(
                dict(kind="writer_commit", version="v2", old_rows_retained=True)
            )
        elif control == "ddl_block":
            manager(resource, "SET lock_timeout='1000ms'")
            try:
                manager(
                    resource,
                    'ALTER VIEW public."phase66 rhs é" SET (security_barrier=true)',
                )
            except Exception as error:
                interventions.append(
                    dict(
                        kind="actual_ddl_block",
                        sqlstate=getattr(error, "sqlstate", None),
                    )
                )
                if getattr(error, "sqlstate", None) != "55P03":
                    raise
            else:
                raise ValueError(
                    "owned view DDL unexpectedly crossed active transaction"
                )
            finally:
                manager(resource, "SET lock_timeout='0'")
        elif control == "cancel_after_guard":
            stream.cancel()
            interventions.append(dict(kind="cancel_after_guard"))
        elif control in ("transaction_graft", "role_graft"):
            with stream._connection.cursor() as cursor:
                if control == "transaction_graft":
                    cursor.execute("COMMIT")
                    cursor.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
                else:
                    cursor.execute("SET ROLE pietto_subset")
            interventions.append(dict(kind="actual_" + control))

    def header(self, owner, metadata, row):
        if control == "incomplete_guard_read":
            interventions.append(
                dict(
                    kind="injected_missing_header",
                    native_header_observed=row is not None,
                )
            )
            row = None
        result = original_header(self, owner, metadata, row)
        if control:
            after_guard()
        return result

    def guard(self, owner, metadata, rows, *, terminal):
        result = original_guard(self, owner, metadata, rows, terminal=terminal)
        if control:
            after_guard()
        return result

    def verify(request):
        result = original_verify(request)
        if (
            stream._connection is not None
            and control in ("cancel_verify", "deadline_verify")
            and "verify" not in injected
        ):
            injected.add("verify")
            if control == "cancel_verify":
                stream.cancel()
            else:
                stream._started = time.monotonic() - stream.request.limits.seconds - 1
            interventions.append(
                dict(kind="injected_" + control, after_expensive_verification=True)
            )
        return result

    pg.verify_guarded_execution = verify
    pg.GuardRun.accept_header = header
    pg.GuardRun.accept_guard_result = guard
    if control == "pre_cancel":
        stream.cancel()
        interventions.append(dict(kind="pre_cancel"))

    controller = None
    if control in ("cancel_guard", "deadline_guard"):

        def watch_guard():
            end = time.monotonic() + 15
            while not guard_entered.wait(0.02):
                if stop_control.is_set() or time.monotonic() >= end:
                    return
            while not stop_control.is_set() and time.monotonic() < end:
                rows = manager(
                    resource,
                    "SELECT state,wait_event_type,wait_event FROM pg_catalog.pg_stat_activity WHERE pid=$1",
                    (stream.session_id,),
                )
                if rows and rows[0] == ("active", "Timeout", "PgSleep"):
                    interventions.append(
                        dict(
                            kind="actual_blocked_guard",
                            session=stream.session_id,
                            observation=list(rows[0]),
                        )
                    )
                    if control == "cancel_guard":
                        stream.cancel()
                        interventions.append(dict(kind="native_cancel_requested"))
                    return
                stop_control.wait(0.02)
            interventions.append(dict(kind="blocked_guard_not_observed"))

        controller = threading.Thread(
            target=watch_guard, name="p68-s07-owned-guard-control"
        )
        interventions.append(dict(kind="thread_registered", name=controller.name))
        controller.start()

    def capture_page():
        page = stream.last_page
        if page is not None and all(
            p["ordinal"] != page.ordinal for p in result["pages"]
        ):
            if stream.enumeration is None:
                raise ValueError("missing captured enumerator")
            item = page_data(page, refined)
            item.update(
                sql=page.native.sql.decode(),
                arguments=[s01.scalar(v) for v in page.native.arguments],
                accepted_progress=stream.enumeration.progress,
            )
            result["pages"].append(item)

    try:
        with stream:
            for batch in stream:
                if refined is not None:
                    capture_page()
                with batch:
                    array = pa.record_batch(batch)
                    result["rows"] += encoded(
                        tuple(
                            tuple(
                                array.column(i)[j].as_py()
                                for i in range(array.num_columns)
                            )
                            for j in range(array.num_rows)
                        )
                    )
                if control == "consumer_error":
                    interventions.append(dict(kind="injected_consumer_error"))
                    raise ValueError("injected consumer error")
    except BaseException as error:
        result["failure"] = dict(
            kind=type(error).__name__,
            category=str(error),
            sqlstate=getattr(error, "sqlstate", None),
        )
    finally:
        stop_control.set()
        if controller is not None:
            controller.join(5)
            if controller.is_alive():
                raise RuntimeError("owned guard controller did not join")
            interventions.append(dict(kind="thread_joined", name=controller.name))
        pg.verify_guarded_execution = original_verify
        pg.GuardRun.accept_header = original_header
        pg.GuardRun.accept_guard_result = original_guard
        if refined is not None:
            capture_page()
        stream.close()
        pg._connect = connect
        result.update(
            outcome=asdict(stream.outcome),
            session=stream.session_id,
            guard_states=[] if stream.guards is None else stream.guards.states,
            guard_events=stream.guard_events,
            controls=stream.control_events,
            control_joined=stream._timer is None or not stream._timer.is_alive(),
            progress=None
            if stream.enumeration is None
            else stream.enumeration.progress,
        )
        result["session_close_observations"] = (
            []
            if stream.session_id is None
            else session_gone(resource, stream.session_id)
        )
        result["session_gone"] = (
            stream.session_id is None or result["session_close_observations"][-1] == 0
        )
        if stream.guards is not None and stream.guards.native is not None:
            result["guard_native"] = native_record(stream.guards.native)
        if stream.source_admissions is not None:
            result["admission"] = observation_data(stream.source_admissions)
        if stream.context is not None:
            result["role"] = stream.context[0]
            result["environment"] = (
                preparation.artifact.request.release,
                stream.context[1],
                True,
                "UTF8",
            )
        result["guard_object_created"] = stream.guards is not None
        result["guard_bytes"] = stream._guard_bytes
        result["deadline_expired"] = stream.deadline_expired
    return result


def bridge_attempt(
    resource,
    preparation,
    route,
    *,
    refined=None,
    allow=True,
    binding=None,
    page_size=2,
    isolation="stable",
    role="pietto_query",
    control=None,
):
    pa = importlib.import_module("pyarrow")
    from pietto._project.project_guard_program import prepare_program
    from pietto._project.project_guard_context import ObservedGuardOwner
    from pietto._project.project_guard_runtime import ObservedGuardRequest
    from pietto._project.project_execution import ExecutionLimits
    from pietto._project.project_execution_reader import decode_native_rows
    from pietto._project.project_arrow_result import bind_arrow
    from pietto._project.project_arrow_interop import build_managed_batch

    program = prepare_program(preparation, refinement=refined, binding=binding)
    operations = []

    class ObservedDriver(s01.Driver):
        def query(self, sql, parameters=(), **options):
            operation = dict(
                ordinal=len(operations),
                kind="query",
                sql=sql,
                arguments=[s01.scalar(v) for v in parameters],
                state="registered",
            )
            operations.append(operation)
            raw, rows = super().query(sql, parameters, **options)
            raw["operation"] = operation["ordinal"]
            operation.update(
                state="terminal",
                terminal=raw["source_terminal"],
                closed=raw["statement_cleanup"] == "close_returned",
            )
            return raw, rows

        def control(self, sql):
            operation = dict(
                ordinal=len(operations), kind="control", sql=sql, state="registered"
            )
            operations.append(operation)
            try:
                result = super().control(sql)
                operation.update(state="terminal", returned=True)
                return result
            except BaseException as error:
                operation.update(
                    state="terminal", returned=False, error=type(error).__name__
                )
                raise

    driver = ObservedDriver(
        dict(
            target=resource.target,
            route=route,
            password=resource._passwords[1],
            port=resource.port,
            ca=str(resource.ca_path),
            user=role,
        )
    )
    result: dict[str, Any] = dict(
        rows=[],
        statements=[],
        controls=driver.controls,
        operations=operations,
        route=route,
        mode="refined" if refined else "ordinary",
        guard_states=tuple("NOT_STARTED" for _ in program.subjects),
    )
    owner = None
    from pietto._project import project_guard_runtime as guard_runtime

    original_check = guard_runtime.verify_native_guard
    result["interventions"] = []
    try:
        if refined is not None:
            admissions, source_queries = bridge_admission(driver, refined)
            environment, session, role = (
                admissions.environment,
                admissions.session_id,
                admissions.role,
            )
            result["statements"].extend(source_queries)
            result["admission"] = observation_data(admissions)
        else:
            admissions = None
            strength = "REPEATABLE READ" if isolation == "stable" else "SERIALIZABLE"
            driver.control(
                "SET search_path=pg_catalog"
                if resource.target == "postgres"
                else "SET SESSION TRANSACTION ISOLATION LEVEL " + strength
            )
            driver.control(
                "BEGIN ISOLATION LEVEL " + strength + " READ ONLY"
                if resource.target == "postgres"
                else "START TRANSACTION READ ONLY"
            )
            sql = (
                "SELECT current_setting('server_version_num'),current_setting('transaction_isolation'),current_setting('transaction_read_only'),current_setting('client_encoding'),current_user,pg_backend_pid()"
                if resource.target == "postgres"
                else "SELECT VERSION(),@@transaction_isolation,@@character_set_connection,CURRENT_USER(),CONNECTION_ID()"
            )
            raw, rows = driver.query(sql, use_copy=False)
            result["statements"].append(raw)
            if resource.target == "postgres":
                version, observed_isolation, readonly, encoding, role, session = rows[0]
                version = int(version)
                environment = (
                    f"{version // 10000}.{version % 10000}",
                    observed_isolation,
                    readonly == "on",
                    encoding,
                )
            else:
                version, observed_isolation, encoding, role, session = rows[0]
                environment = (
                    version,
                    observed_isolation.lower().replace("-", " "),
                    bool(raw["native"]["terminal"]["packet"]["status_flag"] & 8192),
                    encoding,
                )
        from pietto._project.project_guard_context import (
            guard_source_schema_sql,
            verify_guard_source_columns,
        )

        result.update(session=session, environment=environment, role=role)
        sources = []
        for source in preparation.artifact.request.sources:
            relation = (
                quoted(source.namespace, resource.target)
                + "."
                + quoted(source.name, resource.target)
            )
            if resource.target == "postgres":
                raw, rows = driver.query(
                    "SELECT c.oid::bigint,c.relkind::text,c.relrowsecurity,pg_catalog.pg_get_userbyid(c.relowner) FROM pg_catalog.pg_class AS c JOIN pg_catalog.pg_namespace AS n ON n.oid=c.relnamespace WHERE n.nspname=$1 AND c.relname=$2",
                    (source.namespace, source.name),
                    use_copy=False,
                )
            else:
                raw, rows = driver.query(
                    "SELECT TABLE_TYPE,ENGINE FROM information_schema.tables WHERE TABLE_SCHEMA=? AND TABLE_NAME=?",
                    (source.namespace, source.name),
                    use_copy=False,
                )
            result["statements"].append(raw)
            if raw.get("error") or raw["statement_cleanup"] != "close_returned":
                raise ValueError("GUARD_SOURCE_NATIVE_CONTEXT")
            sources.append((source, tuple(tuple(row) for row in rows)))
            names = program.source_reads[source.position]
            sql = guard_source_schema_sql(source, names, family=resource.target)
            metadata = ()
            if sql is not None:
                raw, rows = driver.query(sql)
                result["statements"].append(raw)
                if raw.get("error") or rows:
                    raise ValueError("GUARD_SOURCE_SCHEMA_ROWS")
                metadata = metadata_description(raw, route)
            collations = ()
            if resource.target == "postgres":
                raw, rows = driver.query(
                    "SELECT a.attname,c.collname FROM pg_catalog.pg_attribute AS a JOIN pg_catalog.pg_collation AS c ON c.oid=a.attcollation WHERE a.attrelid=$1::regclass AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",
                    (relation,),
                    use_copy=False,
                )
                result["statements"].append(raw)
                if raw.get("error"):
                    raise ValueError("GUARD_SOURCE_COLLATIONS")
                collations = tuple(tuple(row) for row in rows)
            verify_guard_source_columns(
                source, names, metadata, collations, route=route
            )
        owner = ObservedGuardOwner(
            ObservedGuardRequest(
                program,
                ExecutionLimits(batch_rows=page_size, seconds=90),
                isolation="repeatable read"
                if isolation == "stable"
                else "serializable",
                allow_guard_sql=allow,
            ),
            route=route,
            session_id=session,
            role=role,
            environment=environment,
            sources=tuple(sources),
            admissions=admissions,
        )
        result.update(session=session, environment=environment, role=role)
        native = owner.guards.prepare_submission(owner)
        result["guard_native"] = native_record(native)
        raw, rows = driver.query(native.sql.decode(), native.arguments)
        result["statements"].append(raw)
        if raw.get("error"):
            raise ValueError("GUARD_NATIVE_FAILURE:" + str(raw["error"]))
        metadata = raw["arrow_schema"] if route == "postgres_adbc" else raw["metadata"]
        if control in ("cancel_verify", "deadline_verify"):

            def interrupted(native):
                original_check(native)
                if owner is None:
                    raise ValueError("missing observed guard owner")
                if control == "cancel_verify":
                    owner._cancel.set()
                else:
                    owner.deadline = time.monotonic() - 1
                result["interventions"].append(
                    dict(
                        kind="injected_" + control,
                        after_expensive_verification=True,
                        native_rowset_observed=True,
                    )
                )

            guard_runtime.verify_native_guard = interrupted
        if native.statement.kind == "guard":
            owner.guards.accept_guard_result(
                owner,
                tuple(metadata),
                tuple(tuple(row) for row in rows),
                terminal="NORMAL"
                if raw["source_terminal"]
                in ("native_rowset_eof", "arrow_StopIteration")
                and raw["statement_cleanup"] == "close_returned"
                else "INCOMPLETE",
            )
            from pietto._project.project_refinement_enumeration import Enumeration

            enumeration = Enumeration(
                refined, admissions, limits=owner.request.limits, _guards=owner.guards
            )
            result["pages"] = []
            while not enumeration.progress[2]:
                page = enumeration.request_page()
                owner._remaining()
                if owner._cancel.is_set():
                    raise ValueError("EXECUTION_CANCELED")
                if route == "postgres_adbc":
                    operation = dict(
                        ordinal=len(operations),
                        kind="query",
                        sql=page.native.sql.decode(),
                        arguments=[s01.scalar(v) for v in page.native.arguments],
                        state="registered",
                    )
                    operations.append(operation)
                    page_raw, page_rows = adbc_page(driver, page, refined)
                    page_raw["operation"] = operation["ordinal"]
                    operation.update(
                        state="terminal",
                        terminal=page_raw["source_terminal"],
                        closed=page_raw["statement_cleanup"] == "close_returned",
                    )
                else:
                    page_raw, page_rows = driver.query(
                        page.native.sql.decode(), page.native.arguments
                    )
                result["statements"].append(page_raw)
                terminal = (
                    "NORMAL"
                    if not page_raw.get("error")
                    and page_raw["source_terminal"] in ("NORMAL", "native_rowset_eof")
                    and page_raw["statement_cleanup"] == "close_returned"
                    else "UNKNOWN"
                )
                checked = enumeration.check_page(
                    page,
                    metadata_description(page_raw, route),
                    tuple(tuple(row) for row in page_rows),
                    terminal=terminal,
                )
                binding = bind_arrow(checked.producer)
                if checked.rows:
                    with build_managed_batch(binding, checked.rows) as batch:
                        array = pa.record_batch(batch)
                        result["rows"] += encoded(
                            tuple(
                                tuple(
                                    array.column(i)[j].as_py()
                                    for i in range(array.num_columns)
                                )
                                for j in range(array.num_rows)
                            )
                        )
                enumeration.commit_page(
                    checked, cancel_event=owner._cancel, deadline=owner.deadline
                )
                item = page_data(page, refined)
                item.update(
                    sql=page.native.sql.decode(),
                    arguments=[s01.scalar(v) for v in page.native.arguments],
                    accepted_progress=enumeration.progress,
                    terminal=terminal,
                )
                result["pages"].append(item)
            result["progress"] = enumeration.progress
        else:
            if control == "incomplete_guard_read":
                result["interventions"].append(
                    dict(kind="injected_missing_header", native_rowset_observed=True)
                )
            public_metadata = owner.guards.accept_header(
                owner,
                tuple(metadata),
                None
                if native.statement.kind == "data" or control == "incomplete_guard_read"
                else rows[0],
            )
            public = owner.guards.public_rows(
                owner,
                tuple(
                    tuple(row)
                    for row in (rows if native.statement.kind == "data" else rows[1:])
                ),
            )
            producer, decoded = decode_native_rows(
                program.output, route, public_metadata, public
            )
            binding = bind_arrow(producer)
            with build_managed_batch(binding, decoded) as batch:
                array = pa.record_batch(batch)
                result["rows"] = encoded(
                    tuple(
                        tuple(
                            array.column(i)[j].as_py() for i in range(array.num_columns)
                        )
                        for j in range(array.num_rows)
                    )
                )
        driver.control("COMMIT")
        result["transaction"] = "COMMIT_ACK"
    except BaseException as error:
        result["failure"] = dict(
            kind=type(error).__name__,
            category=str(error),
            traceback=traceback.format_exc(),
        )
        try:
            driver.control("ROLLBACK")
            result["transaction"] = "ROLLBACK_ACK"
        except BaseException as cleanup:
            result["rollback_error"] = type(cleanup).__name__
    finally:
        guard_runtime.verify_native_guard = original_check
        if owner is not None:
            owner.close()
            result["guard_states"] = owner.guards.states
        driver.close()
        result["closed"] = True
        result["statement_count"] = len(result["statements"])
        session = result.get("session")
        result["session_close_observations"] = (
            [] if session is None else session_gone(resource, session)
        )
        result["session_gone"] = (
            session is None or result["session_close_observations"][-1] == 0
        )
    return result


def small_family(directory, ledger_path, target, route, tree):
    """A declared targeted family, never a complete campaign or readiness PASS."""
    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources(target, pins["targets"][target], directory)
    ledger(
        ledger_path,
        dict(
            kind="targeted_live_start",
            family="ordinary/refined guard basic transport",
            route=route,
            target=target,
            tree=tree,
            resource=resource.name,
            directory=str(directory),
        ),
        targeted_live_family_starts=1,
        source_db_lifecycle_starts=1,
    )
    report = dict(
        tree=tree,
        target=target,
        route=route,
        attempts=[],
        runtime=s01.runtime_identity(),
    )
    tick = time.monotonic()
    try:
        resource.acquire()
        setup(resource)
        from pietto._project.project_guard_preparation import (
            prepare_guarded,
            prepare_guarded_output,
        )

        preparation = prepare_guarded(*planned(directory / (PREFIX + "input"), target))
        for mode in ("success", "violation", "empty"):
            fill(
                resource,
                ((1, None), (1, 7), (2, None)),
                ((1, None), (1, None))
                if mode == "violation"
                else ()
                if mode == "empty"
                else ((1, None),),
            )
            item = (
                pg_attempt(resource, preparation)
                if route == "postgres_rows"
                else bridge_attempt(resource, preparation, route)
            )
            item["case"] = mode
            report["attempts"].append(item)
            write(directory / (PREFIX + "observations.json"), report)
            assert item["rows"] == (
                [] if mode != "success" else encoded(((1, None), (1, None)))
            ), "native case failed; inspect retained observation"
            assert (
                (item.get("failure", {}).get("category") == "SINGLE_MATCH_VIOLATED")
                if mode == "violation"
                else "failure" not in item
            ), "native case failed; inspect retained observation"
        fill(resource, ((1, None), (1, 7), (2, None)), ((1, None),))
        q = refinement(resource, preparation, prepare_guarded_output(preparation))
        item = (
            pg_attempt(resource, preparation, refined=q)
            if route == "postgres_rows"
            else bridge_attempt(resource, preparation, route, refined=q)
        )
        item["case"] = "refined_success"
        report["attempts"].append(item)
        write(directory / (PREFIX + "observations.json"), report)
        assert "failure" not in item and item["rows"] == encoded(
            ((1, None), (1, None))
        ), "native case failed; inspect retained observation"
        report["origins"] = origins()
        report["result"] = "PASS_BASIC_TARGETED_FAMILY"
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        report["origins"] = origins()
        report["cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - tick
        write(directory / (PREFIX + "observations.json"), report)
        ledger(
            ledger_path,
            dict(
                kind="targeted_live_terminal",
                family="ordinary/refined guard basic transport",
                route=route,
                tree=tree,
                result=report.get("result", "FAILED"),
                cleanup=report["cleanup"],
                seconds=report["seconds"],
            ),
        )


PREFLIGHT_CASES = (
    "bag_one",
    "source_text_wide",
    "bag_zero",
    "bag_two_equal_null",
    "right_limit_0",
    "forbidden_pending",
    "case_labels",
    "path_hop0",
    "path_whole_positive",
    "path_first_violation_hidden",
    "path_later_violation_hidden",
    "ordinary_tied_subject",
    "refined_tied_subject",
    "refined_violation_outside_page",
    "bound_four",
    "bound_four_refined",
    "visibility_subset",
    "serializable",
    "binding_A",
    "binding_B",
    "binding_A_again",
    "reserved_prefix",
    "seven_39_empty",
    "seven_65_values",
    "imported_reexport",
)


def selected_cases(mode):
    from _pietto_phase68_slice7_cases import manifest

    if mode == "installed_smoke":
        return tuple(c for c in manifest() if c["name"] == "bag_one")
    return tuple(
        c for c in manifest() if mode == "campaign" or c["name"] in PREFLIGHT_CASES
    )


def worker(config_path):
    """One fresh source/installed interpreter; parent owns its existing lab DB."""
    from pietto._project.project_guard_preparation import prepare_guarded_output
    from _pietto_phase68_slice7_cases import case_preparation
    from pietto._project.project_guard_program import prepare_program
    from _pietto_phase68_slice7_check import (
        check_attempt,
        current_origins,
        check_origins,
        actual_record_damages,
        check_tie_contrast,
        check_worker_denominator,
    )

    config = json.loads(config_path.read_text())
    directory = Path(config["directory"])
    connection_root = directory / (PREFIX + "manager")
    connection_root.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    # This Resources object owns only a registered connection, never acquire().
    # Container/network ownership remains with the parent campaign process.
    resource = Resources(
        config["target"], pins["targets"][config["target"]], connection_root
    )
    resource.port = config["port"]
    resource._passwords = tuple(config["passwords"])
    resource.ca_path = Path(config["ca"])
    resource.startup_started = time.monotonic()
    report: dict[str, Any] = dict(
        tree=config["tree"],
        route=config["route"],
        target=config["target"],
        origin=config["origin"],
        expected_cases=[
            c["name"]
            for c in selected_cases(config["mode"])
            if not (config["target"] == "mysql" and c["options"].get("postgres_only"))
        ],
        attempts=[],
        runtime=s01.runtime_identity(),
        worker_pid=os.getpid(),
        parent_database=config["database"],
    )
    output_path = directory / (PREFIX + "worker-report.json")
    try:
        resource.manager = resource.connect(query=False)
        template = None
        first_binding = None
        for case in selected_cases(config["mode"]):
            if resource.target == "mysql" and case["options"].get("postgres_only"):
                continue
            fill(
                resource,
                case["lhs"],
                case["rhs"],
                wide_text=case["options"].get("wide_text", False),
            )
            binding = None
            if "binding_values" in case["options"]:
                from pietto._project.project_guard_preparation import (
                    prepare_guarded_template,
                )
                from pietto._project.project_execution_template import bind_values

                if template is None:
                    seed = case_preparation(
                        directory / (PREFIX + "binding-template"), resource.target, case
                    )
                    template = prepare_guarded_template(seed)
                if case["name"] == "binding_A_again":
                    if first_binding is None:
                        raise ValueError("missing original A binding")
                    binding = first_binding
                else:
                    supplied = list(
                        zip(
                            template.slots,
                            case["options"]["binding_values"],
                            strict=True,
                        )
                    )
                    binding = bind_values(template, supplied)
                    supplied.clear()
                    if case["name"] == "binding_A":
                        first_binding = binding
                preparation = binding.guarded
            else:
                preparation = case_preparation(
                    directory / (PREFIX + case["name"]), resource.target, case
                )
            role = case["options"].get("role", "pietto_query")
            query = (
                refinement(
                    resource,
                    preparation,
                    prepare_guarded_output(preparation, binding=binding),
                    role=role,
                )
                if case["options"].get("refined")
                else None
            )
            arguments: dict[str, Any] = dict(
                refined=query,
                allow=case["options"].get("allow", True),
                page_size=case["options"].get("page_size", 2),
                binding=binding,
                role=role,
                isolation=case["options"].get("isolation", "stable"),
            )
            item = (
                pg_attempt(resource, preparation, **arguments)
                if config["route"] == "postgres_rows"
                else bridge_attempt(resource, preparation, config["route"], **arguments)
            )
            item["case"] = case["name"]
            item = json.loads(json.dumps(item))
            report["attempts"].append(item)
            write(output_path, report)
            program = prepare_program(preparation, refinement=query, binding=binding)
            check_attempt(item, case, program)
            if case["name"] == "ordinary_tied_subject":
                item["same_snapshot_tie_contrast"] = tie_contrast(
                    resource, config["route"]
                )
                check_tie_contrast(item["same_snapshot_tie_contrast"], config["route"])
            item["damage_rejections"] = actual_record_damages(item, case, program)
            write(output_path, report)
        if config["route"] == "postgres_rows" and config["mode"] != "installed_smoke":
            from _pietto_phase68_slice7_check import check_control

            control_names = (
                "pre_cancel",
                "cancel_verify",
                "deadline_verify",
                "cancel_after_guard",
                "incomplete_guard_read",
                "transaction_graft",
                "role_graft",
                "consumer_error",
                "commit_loss",
                "cleanup_error",
                "writer_version",
                "ddl_block",
                "native_guard_error",
                "cancel_guard",
                "deadline_guard",
            )
            report["expected_controls"] = list(control_names)
            report["control_attempts"] = []
            direct = next(
                c for c in selected_cases(config["mode"]) if c["name"] == "bag_one"
            )
            for control in control_names:
                fill(resource, direct["lhs"], direct["rhs"])
                p = case_preparation(
                    directory / (PREFIX + "control-" + control), resource.target, direct
                )
                q = (
                    refinement(resource, p, prepare_guarded_output(p))
                    if control == "writer_version"
                    else None
                )
                previous_view = None
                if control in ("native_guard_error", "cancel_guard", "deadline_guard"):
                    previous_view = set_fault_view(
                        resource,
                        "error" if control == "native_guard_error" else "sleep",
                    )
                try:
                    item = pg_attempt(resource, p, refined=q, control=control)
                finally:
                    if previous_view is not None:
                        manager(
                            resource,
                            'CREATE OR REPLACE VIEW public."phase66 rhs é" WITH (security_invoker=true) AS '
                            + previous_view,
                        )
                item["control"] = control
                item = json.loads(json.dumps(item))
                report["control_attempts"].append(item)
                write(output_path, report)
                check_control(item, control)
                if control == "writer_version":
                    item["case"] = direct["name"]
                    check_attempt(item, direct, prepare_program(p, refinement=q))
                    need_rows = encoded(direct["rows"])
                    if item["rows"] != need_rows:
                        raise ValueError("same-snapshot old version rows changed")
                    q2 = refinement(
                        resource,
                        p,
                        prepare_guarded_output(p),
                        versions={"rhs": ("v2", "r2")},
                    )
                    later = pg_attempt(resource, p, refined=q2)
                    later["case"] = "new_version_observation"
                    item["new_attempt"] = later
                    if (
                        later.get("failure", {}).get("category")
                        != "SINGLE_MATCH_VIOLATED"
                        or later["rows"]
                        or later["session"] == item["session"]
                    ):
                        raise ValueError(
                            "new version did not cause fresh full guard violation"
                        )
                    later = json.loads(json.dumps(later))
                    item["new_attempt"] = later
                    later_case = dict(
                        direct,
                        name="new_version_observation",
                        rows=(),
                        states=("VIOLATED",),
                    )
                    later_program = prepare_program(p, refinement=q2)
                    check_attempt(later, later_case, later_program)
                    later["damage_rejections"] = actual_record_damages(
                        later, later_case, later_program
                    )
                    write(output_path, report)
        if config["route"] != "postgres_rows" and config["mode"] != "installed_smoke":
            from _pietto_phase68_slice7_check import check_bridge_control

            report["expected_controls"] = [
                "cancel_verify",
                "deadline_verify",
                "incomplete_guard_read",
            ]
            report["control_attempts"] = []
            direct = next(
                c for c in selected_cases(config["mode"]) if c["name"] == "bag_one"
            )
            for control in report["expected_controls"]:
                fill(resource, direct["lhs"], direct["rhs"])
                p = case_preparation(
                    directory / (PREFIX + "control-" + control), resource.target, direct
                )
                item = bridge_attempt(resource, p, config["route"], control=control)
                item["control"] = control
                item = json.loads(json.dumps(item))
                report["control_attempts"].append(item)
                write(output_path, report)
                check_bridge_control(item, control)
        check_worker_denominator(
            report, report["expected_cases"], report.get("expected_controls", [])
        )
        from copy import deepcopy

        report["denominator_damage_rejections"] = []
        for group in ("attempts", "control_attempts"):
            if report.get(group):
                damaged = deepcopy(report)
                damaged[group].pop()
                try:
                    check_worker_denominator(
                        damaged,
                        report["expected_cases"],
                        report.get("expected_controls", []),
                    )
                except ValueError:
                    report["denominator_damage_rejections"].append(group)
                else:
                    raise ValueError("worker denominator damage accepted")
        observed = origins()
        expected = current_origins(observed, ROOT / "src")
        import sysconfig

        origin_root = (
            Path(sysconfig.get_path("purelib"))
            if config["origin"] == "installed"
            else ROOT / "src"
        )
        check_origins(
            observed,
            expected,
            installed=config["origin"] == "installed",
            root=origin_root,
        )
        from copy import deepcopy

        origin_damages = []
        for name in ("omitted", "foreign_path", "wrong_bytes"):
            damaged = deepcopy(observed)
            key = sorted(damaged)[0]
            if name == "omitted":
                del damaged[key]
            elif name == "foreign_path":
                damaged[key]["path"] = (
                    "/tmp/foreign-origin/" + Path(damaged[key]["path"]).name
                )
            else:
                damaged[key]["sha256"] = "0" * 64
            try:
                check_origins(
                    damaged,
                    expected,
                    installed=config["origin"] == "installed",
                    root=origin_root,
                )
            except ValueError:
                origin_damages.append(name)
            else:
                raise ValueError("origin damage accepted")
        report["origin_damage_rejections"] = origin_damages
        report["origins"] = observed
        report["origin_inventory"] = sorted(observed)
        write(
            directory / (PREFIX + "origin-witness.json"),
            dict(
                pid=os.getpid(),
                origin=config["origin"],
                loaded=sorted(observed),
                sha256=expected,
            ),
        )
        report["result"] = "PASS_SELECTED_NATIVE_CASES"
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        if resource.manager is not None:
            resource.manager.close()
        report["manager_closed"] = resource.manager is None or bool(
            getattr(resource.manager, "closed", True)
            if resource.target == "postgres"
            else not resource.manager.is_connected()
        )
        report["origins"] = origins()
        write(output_path, report)


def native_group(
    directory,
    ledger_path,
    target,
    route,
    tree,
    *,
    mode,
    python,
    origins_to_run=("source", "installed"),
):
    """One target/lifecycle, with sequential fresh origin workers and raw files."""
    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources(target, pins["targets"][target], directory)
    charges = dict(source_db_lifecycle_starts=1)
    if mode == "preflight":
        charges["targeted_live_family_starts"] = 1
    ledger(
        ledger_path,
        dict(
            kind="native_group_start",
            mode=mode,
            route=route,
            tree=tree,
            database=resource.name,
            directory=str(directory),
        ),
        **charges,
    )
    report: dict[str, Any] = dict(tree=tree, route=route, mode=mode, workers=[])
    tick = time.monotonic()
    try:
        resource.acquire()
        setup(resource)
        for origin in origins_to_run:
            root = directory / (PREFIX + origin)
            root.mkdir(mode=0o700)
            config = dict(
                target=target,
                route=route,
                tree=tree,
                mode="installed_smoke"
                if mode == "preflight" and origin == "installed"
                else mode,
                origin=origin,
                directory=str(root),
                database=resource.name,
                port=resource.port,
                passwords=resource._passwords,
                ca=str(resource.ca_path),
            )
            config_path = root / (PREFIX + "worker-input.json")
            config_path.write_text(json.dumps(config))
            config_path.chmod(0o600)
            argv = [
                str(python),
                "-B",
                str(ROOT / "scripts/phase68_slice7_probe.py"),
                "--mode",
                "worker",
                "--origin",
                origin,
                "--input",
                str(config_path),
            ]
            ledger(
                ledger_path,
                dict(
                    kind="native_worker_registered",
                    argv=argv,
                    directory=str(root),
                    route=route,
                    origin=origin,
                    tree=tree,
                ),
            )
            env = {
                k: v
                for k, v in os.environ.items()
                if k not in ("PYTHONPATH", "UV_PYTHON", "UV_NO_SYNC", "UV_LOCKED")
            }
            with (root / (PREFIX + "worker.log")).open("w") as output:
                child = subprocess.Popen(
                    argv, env=env, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT
                )
                ledger(
                    ledger_path,
                    dict(
                        kind="native_worker_started",
                        pid=child.pid,
                        directory=str(root),
                        origin=origin,
                    ),
                )
                try:
                    code = child.wait(timeout=900)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
                    code = 124
                ledger(
                    ledger_path,
                    dict(
                        kind="native_worker_terminal",
                        pid=child.pid,
                        directory=str(root),
                        returncode=code,
                        reaped=True,
                    ),
                )
            config_path.unlink()
            observation = root / (PREFIX + "worker-report.json")
            report["workers"].append(
                dict(origin=origin, path=str(observation), returncode=code)
            )
            write(directory / (PREFIX + "observations.json"), report)
            if code != 0:
                raise ValueError("S07_NATIVE_WORKER_FAILED:" + origin)
            data = json.loads(observation.read_text())
            from _pietto_phase68_slice7_check import check_worker_denominator

            check_worker_denominator(
                data, data["expected_cases"], data.get("expected_controls", [])
            )
            if (
                data.get("result") != "PASS_SELECTED_NATIVE_CASES"
                or data["expected_cases"] != [a["case"] for a in data["attempts"]]
                or not data["manager_closed"]
            ):
                raise ValueError("S07_NATIVE_WORKER_DENOMINATOR")
        report["result"] = "PASS_NATIVE_GROUP"
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        report["cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - tick
        write(directory / (PREFIX + "observations.json"), report)
        ledger(
            ledger_path,
            dict(
                kind="native_group_terminal",
                mode=mode,
                route=route,
                tree=tree,
                result=report.get("result", "FAILED"),
                cleanup=report["cleanup"],
                seconds=report["seconds"],
            ),
        )


def publish_version(resource):
    namespace = "public" if resource.target == "postgres" else "phase66"
    base = (
        quoted(namespace, resource.target)
        + "."
        + quoted("p68_guard_rhs", resource.target)
    )
    registry = (
        quoted(namespace, resource.target)
        + "."
        + quoted("p68_guard_registry_rhs", resource.target)
    )
    manager(resource, "BEGIN" if resource.target == "postgres" else "START TRANSACTION")
    try:
        manager(
            resource,
            "INSERT INTO " + base + " VALUES (1,NULL,201,'v2'),(1,NULL,202,'v2')",
        )
        manager(resource, "UPDATE " + registry + " SET version_tag='v2',revision='r2'")
        manager(resource, "COMMIT")
    except BaseException:
        manager(resource, "ROLLBACK")
        raise


def set_fault_view(resource, kind):
    """Actual native failure/wait inside a read-only source, not injected IO."""
    if resource.target != "postgres":
        raise ValueError("PG product control fixture")
    manager(resource, "SET search_path=pg_catalog")
    (definition,) = manager(
        resource,
        "SELECT pg_catalog.pg_get_viewdef($1::regclass,true)",
        ('public."phase66 rhs é"',),
    )[0]
    if kind == "sleep":
        manager(
            resource,
            "CREATE OR REPLACE FUNCTION public.p68_guard_delay(value BIGINT) RETURNS BIGINT LANGUAGE plpgsql VOLATILE AS $$ BEGIN PERFORM pg_catalog.pg_sleep(10); RETURN value; END $$",
        )
        expression = 'public.p68_guard_delay(b."key value")'
    else:
        expression = '10 / (b."order.id" - b."order.id")'
    manager(
        resource,
        'CREATE OR REPLACE VIEW public."phase66 rhs é" WITH (security_invoker=true) AS SELECT b."order.id",'
        + expression
        + ' AS "key value",b.token,b.source_version FROM public.p68_guard_rhs AS b WHERE b.source_version=(SELECT version_tag FROM public.p68_guard_registry_rhs)',
    )
    return definition


def tie_contrast(resource, route):
    """Test-only lawful tie refinements demonstrate why repeated SQL is insufficient."""
    target = resource.target
    namespace = "public" if target == "postgres" else "phase66"
    relation = quoted(namespace, target) + "." + quoted("phase66 rhs é", target)
    driver = s01.Driver(
        dict(
            route=route,
            target=target,
            port=resource.port,
            password=resource._passwords[1],
            ca=str(resource.ca_path),
        )
    )
    report: dict[str, Any] = dict(
        kind="test_only_reference_no_production_fallback",
        controls=driver.controls,
        statements=[],
        contexts=[],
        session=None,
    )
    context_sql = (
        "SELECT pg_backend_pid(),current_user,current_setting('transaction_isolation'),current_setting('transaction_read_only'),pg_current_xact_id()::text"
        if target == "postgres"
        else "SELECT VERSION(),@@transaction_isolation,@@character_set_connection,CURRENT_USER(),CONNECTION_ID()"
    )
    try:
        driver.control(
            "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"
            if target == "postgres"
            else "START TRANSACTION READ ONLY"
        )
        raw, rows = driver.query(context_sql, use_copy=False)
        report["contexts"].append(raw)
        report["session"] = rows[0][0 if target == "postgres" else 4]
        key, identity = quoted("key value", target), quoted("order.id", target)
        for order, expected in (
            (key + ",token", ((1, 0), (2, 0))),
            (key + "," + identity + ",token", ((1, 0), (1, 0))),
        ):
            sql = (
                "SELECT "
                + identity
                + ","
                + key
                + " FROM "
                + relation
                + " ORDER BY "
                + order
                + " LIMIT 2"
            )
            raw, rows = driver.query(sql)
            report["statements"].append(raw)
            if (
                raw.get("error")
                or rows != list(expected)
                or raw["statement_cleanup"] != "close_returned"
            ):
                raise ValueError("native tie contrast")
        raw, rows = driver.query(context_sql, use_copy=False)
        report["contexts"].append(raw)
        driver.control("COMMIT")
    except BaseException:
        driver.control("ROLLBACK")
        raise
    finally:
        driver.close()
        report["closed"] = True
        report["session_close_observations"] = (
            []
            if report["session"] is None
            else session_gone(resource, report["session"])
        )
    return report
