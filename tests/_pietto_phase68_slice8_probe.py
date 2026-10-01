"""Explicit S08 native product acquisition; ordinary imports do not open a DB."""

from dataclasses import asdict
import json
import importlib
import importlib.metadata
from pathlib import Path
import sys
import time
from typing import Any

from _pietto_phase68_slice7_cases import manifest, case_preparation
from _pietto_phase68_slice7_probe import setup, fill, refinement, encoded
from _pietto_phase68_slice6_probe import manager, session_gone
from _pietto_target_conformance_resources import Resources

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice08-"


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def event(path, record, **charges):
    ledger = json.loads(path.read_text())
    for name, count in charges.items():
        if ledger["used"][name] + count > ledger["limits"][name]:
            raise ValueError("S08_BUDGET:" + name)
        ledger["used"][name] += count
    ledger["events"].append(record)
    write(path, ledger)


class Calls:
    """Passive actual driver/packet observations on both registered connections."""

    def __init__(self, owner):
        import threading

        self.owner = owner
        self.events = []
        self.pages = []
        self.previous = sys.getprofile()
        self.previous_thread = threading.getprofile()
        distribution = importlib.metadata.distribution("mysql-connector-python")
        self.files = {
            str(distribution.locate_file("mysql/connector/connection.py")),
            str(distribution.locate_file("mysql/connector/protocol.py")),
        }

    def observe(self, frame, event, result):
        if self.previous is not None or self.previous_thread is not None:
            import threading

            previous = (
                self.previous
                if threading.current_thread() is threading.main_thread()
                else self.previous_thread
            )
            if previous is not None:
                previous(frame, event, result)
        if (
            event == "return"
            and frame.f_code.co_name == "commit_page"
            and frame.f_locals.get("self") is self.owner.enumeration
        ):
            from _pietto_phase68_slice6_probe import page_data

            enumeration = self.owner.enumeration
            if enumeration is not None and not enumeration.progress[3]:
                page = frame.f_locals["checked"].request
                fact = page_data(page, enumeration.query)
                fact.update(
                    sql=page.native.sql.decode(),
                    arguments=encoded((page.native.arguments,))[0],
                    accepted_progress=enumeration.progress,
                )
                self.pages.append(fact)
        if (
            event not in ("call", "return")
            or frame.f_code.co_filename not in self.files
        ):
            return
        local = frame.f_locals
        connection = local.get("self")
        name = frame.f_code.co_name
        if name == "make_stmt_execute":
            matches = tuple(
                c for c in self.owner._connections if c._protocol is connection
            )
            if len(matches) > 1:
                raise ValueError("S08_OBSERVER_ALIASED_PROTOCOL")
            if not matches:
                return
            connection = matches[0]
        elif not any(connection is c for c in self.owner._connections):
            return
        if connection is None:
            return
        fact = {
            "event": name + "." + event,
            "session": connection.connection_id,
            "connection": "data"
            if connection is self.owner._owned_connection
            else "control",
        }
        if name == "cmd_stmt_prepare":
            fact["value"] = local["statement"].hex() if event == "call" else result
        elif name in ("cmd_stmt_execute", "make_stmt_execute"):
            if event == "call":
                value = {
                    "statement_id": local["statement_id"],
                    "data": encoded((local["data"],))[0],
                    "parameters": local["parameters"],
                    "flags": local["flags"],
                }
                if name == "make_stmt_execute":
                    value.update(
                        charset=local["charset"],
                        long_data_used=local["long_data_used"],
                        query_attrs=local["query_attrs"],
                        converter_str_fallback=local["converter_str_fallback"],
                    )
                fact["value"] = value
            else:
                fact["value"] = (
                    result.hex()
                    if name == "make_stmt_execute" and result is not None
                    else result
                )
        elif name == "get_rows":
            fact["value"] = (
                {
                    "count": local["count"],
                    "binary": local["binary"],
                    "columns": local["columns"],
                }
                if event == "call"
                else None
                if result is None
                else {"rows": encoded(result[0]), "eof": result[1]}
            )
        elif name == "cmd_query":
            query = local["query"]
            fact["value"] = (
                (query.decode() if type(query) in (bytes, bytearray) else query)
                if event == "call"
                else {
                    "rowset": type(result) is tuple,
                    "warnings": result.get("warning_count")
                    if type(result) is dict
                    else None,
                }
            )
        elif name == "cmd_stmt_close":
            fact["value"] = local["statement_id"]
        elif name == "_send_cmd" and local["command"] in (22, 23, 24, 25, 26, 28):
            fact["value"] = {
                "command": local["command"],
                "payload": bytes(local["packet"] or local["argument"]).hex(),
                "expect_response": local["expect_response"],
            }
        else:
            return
        self.events.append(json.loads(json.dumps(fact)))

    def __enter__(self):
        import threading

        sys.setprofile(self.observe)
        threading.setprofile(self.observe)
        return self

    def __exit__(self, *exception):
        import threading

        sys.setprofile(self.previous)
        threading.setprofile(self.previous_thread)


def deployment(access, artifact, schemas=("phase66",)):
    from pietto._project.project_execution import MySQLDeploymentPremise

    return MySQLDeploymentPremise(access, artifact.request.sources, schemas)


def attempt(
    resource,
    preparation,
    *,
    query=None,
    ordinary=False,
    allow=True,
    size=2,
    isolation="stable",
    managed=True,
    binding=None,
    user="pietto_query",
    schemas=("phase66",),
    prefix=False,
):
    pa = importlib.import_module("pyarrow")
    from pietto._project.project_execution import (
        MySQLAccess,
        ExecutionLimits,
        prepare_execution,
    )
    from pietto._project.project_execution_mysql import MySQLExecution
    from pietto._project.project_guard_runtime import prepare_guarded_execution
    from pietto._project.project_refinement_enumeration import prepare_refined_execution

    access = MySQLAccess(
        "127.0.0.1",
        resource.port,
        "phase66",
        user,
        resource._passwords[1],
        str(resource.ca_path),
        user + "@%",
        verify_identity=False,
        loopback_tls_exception=True,
    )
    premise = deployment(access, preparation.artifact, schemas) if managed else None
    limits = ExecutionLimits(batch_rows=size, seconds=120)
    request = (
        (
            prepare_refined_execution(
                query,
                access,
                limits=limits,
                isolation=isolation,
                mysql_deployment=premise,
            )
            if query is not None
            else prepare_execution(
                preparation.artifact,
                access,
                limits=limits,
                isolation=isolation,
                binding=binding,
                mysql_deployment=premise,
            )
        )
        if ordinary
        else prepare_guarded_execution(
            preparation,
            access,
            refinement=query,
            limits=limits,
            isolation=isolation,
            allow_guard_sql=allow,
            binding=binding,
            mysql_deployment=premise,
        )
    )
    owner = MySQLExecution(request)
    record: dict[str, Any] = {"rows": [], "events": [], "pages": [], "schemas": []}
    observer = Calls(owner)
    tick = time.monotonic()
    try:
        with observer, owner:
            for batch in owner:
                with batch:
                    array = pa.record_batch(batch)
                    record["schemas"].append(
                        [[f.name, str(f.type), f.nullable] for f in array.schema]
                    )
                    record["rows"].extend(
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
                if prefix:
                    owner.close()
                    break
    except BaseException as error:
        record["failure"] = {
            "kind": type(error).__name__,
            "category": str(error),
            "errno": getattr(error, "errno", None),
            "sqlstate": getattr(error, "sqlstate", None),
        }
    finally:
        owner.close()
        record.update(
            events=observer.events,
            outcome=asdict(owner.outcome),
            session=owner.session_id,
            context=owner.context,
            epoch=owner._epoch,
            guard_states=None if owner.guards is None else owner.guards.states,
            control_events=owner.control_events,
            control_joined=owner.control_joined,
            seconds=time.monotonic() - tick,
            assurance=owner.assurance,
            deployment_schemas=schemas if managed else None,
            pages=observer.pages,
            progress=None if owner.enumeration is None else owner.enumeration.progress,
            environment=owner.environment,
            role=access.account,
            batch_rows=size,
            route="mysql_rows",
            entry="unguarded_refinement"
            if ordinary and query is not None
            else "ordinary"
            if ordinary
            else "guarded_refinement"
            if query is not None
            else "guarded",
            sources=[asdict(obj) for obj in owner._sources],
            source_edges=None
            if owner._qualification is None
            else owner._qualification.edges,
            security=None
            if owner._qualification is None
            else owner._qualification.security,
            metadata=owner.actual_metadata,
            bound_schema=None
            if owner._payloads is None
            else [
                [f.name, str(f.type), f.nullable]
                for f in owner._payloads.binding.schema
            ],
            statements=[
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
            ],
        )
        from _pietto_phase68_slice6_probe import observation_data
        from _pietto_phase68_slice7_probe import native_record

        if owner.source_admissions is not None:
            record["admission"] = observation_data(owner.source_admissions)
        if owner.guards is not None and owner.guards.native is not None:
            record["guard_native"] = native_record(owner.guards.native)
        sessions = [
            c.connection_id for c in owner._connections if c.connection_id is not None
        ]
        record["sessions_gone"] = {str(s): session_gone(resource, s) for s in sessions}
    return record


def vertical(directory, ledger, *, check_mode_warning=False):
    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources("mysql", pins["targets"]["mysql"], directory)
    event(
        ledger,
        {
            "kind": "targeted_native_start",
            "family": "first_mysql_product_vertical",
            "directory": str(directory),
            "database": resource.name,
        },
        targeted_live_family_starts=1,
        source_db_lifecycle_starts=1,
    )
    report: dict[str, Any] = {"attempts": []}
    try:
        resource.acquire()
        setup(resource)
        if check_mode_warning:
            from _pietto_target_conformance_resources import MYSQL_MODE

            resource.query = resource.connect(query=True)
            try:
                with resource.query.cursor() as cursor:
                    cursor.execute("SET SESSION sql_mode=%s", (MYSQL_MODE,))
                    count = cursor.warning_count
                    cursor.execute("SHOW WARNINGS")
                    report["mode_warning_reproduction"] = {
                        "count": count,
                        "rows": cursor.fetchall(),
                    }
                    print(
                        "mode_warning_reproduction",
                        report["mode_warning_reproduction"],
                        flush=True,
                    )
            finally:
                resource.query.close()
                resource.query = None
        for table in ("threads", "events_transactions_current"):
            manager(
                resource,
                "GRANT SELECT ON performance_schema."
                + table
                + " TO 'pietto_query'@'%'",
            )
        manager(resource, "CREATE DATABASE p68_hidden")
        manager(
            resource, "CREATE TABLE p68_hidden.engine_hidden (id BIGINT) ENGINE=MyISAM"
        )
        manager(resource, "INSERT INTO p68_hidden.engine_hidden VALUES (1)")
        manager(
            resource,
            "CREATE SQL SECURITY DEFINER VIEW phase66.p68_visibility AS SELECT id FROM p68_hidden.engine_hidden",
        )
        resource.query = resource.connect(query=True)
        try:
            with resource.query.cursor() as cursor:
                cursor.execute(
                    "SELECT TABLE_SCHEMA,TABLE_NAME FROM information_schema.VIEW_TABLE_USAGE WHERE VIEW_SCHEMA='phase66' AND VIEW_NAME='p68_visibility'"
                )
                report["hidden_dependencies"] = cursor.fetchall()
                try:
                    cursor.execute(
                        "EXPLAIN SELECT id FROM phase66.p68_visibility LIMIT 0"
                    )
                    report["hidden_explain"] = {
                        "accepted": True,
                        "rows": cursor.fetchall(),
                    }
                except Exception as error:
                    report["hidden_explain"] = {
                        "accepted": False,
                        "errno": getattr(error, "errno", None),
                        "sqlstate": getattr(error, "sqlstate", None),
                    }
        finally:
            resource.query.close()
            resource.query = None
        assert (
            report["hidden_dependencies"] == []
            and not report["hidden_explain"]["accepted"]
        )
        write(directory / (PREFIX + "vertical.json"), report)
        for name in (
            "no_request",
            "bag_one",
            "bag_two_equal_null",
            "source_text_wide",
            "path_whole_positive",
            "refined_pages",
        ):
            case = next(c for c in manifest() if c["name"] == name)
            preparation = case_preparation(directory / (PREFIX + name), "mysql", case)
            fill(
                resource,
                case["lhs"],
                case["rhs"],
                wide_text=case["options"].get("wide_text", False),
            )
            query = (
                refinement(
                    resource,
                    preparation,
                    __import__(
                        "pietto._project.project_guard_preparation",
                        fromlist=["prepare_guarded_output"],
                    ).prepare_guarded_output(preparation),
                )
                if case["options"].get("refined")
                else None
            )
            result = attempt(
                resource, preparation, query=query, ordinary=name == "no_request"
            )
            result["case"] = name
            report["attempts"].append(result)
            write(directory / (PREFIX + "vertical.json"), report)
            print(name, result.get("failure"), result["outcome"], flush=True)
            if name == "bag_two_equal_null":
                assert (
                    result.get("failure", {}).get("category") == "SINGLE_MATCH_VIOLATED"
                )
            else:
                assert "failure" not in result
                assert result["rows"] == encoded(case["rows"])
                assert result["outcome"]["source"] == "EOF"
                assert result["outcome"]["transaction"] == "COMMIT_ACK"
            assert result["control_joined"] and all(
                v[-1] == 0 for v in result["sessions_gone"].values()
            )
        report["result"] = "PASS_SIX_SOURCE_PRODUCT_MECHANISMS"
    finally:
        report["cleanup"] = resource.cleanup()
        write(directory / (PREFIX + "vertical.json"), report)
        event(
            ledger,
            {
                "kind": "targeted_native_terminal",
                "family": "first_mysql_product_vertical",
                "result": report.get("result", "FAILED"),
                "cleanup": report["cleanup"],
            },
        )


def controlled_attempt(resource, preparation, kind, *, deadline_seconds=None):
    """Named real interleavings and explicitly marked I/O reply injections."""
    import threading
    from pietto._project import project_execution_mysql as product
    from pietto._project.project_execution import MySQLAccess, ExecutionLimits
    from pietto._project.project_guard_runtime import prepare_guarded_execution

    pa = importlib.import_module("pyarrow")
    access = MySQLAccess(
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
    blocked = kind in ("blocked_cancel", "blocked_deadline")
    limits = ExecutionLimits(
        batch_rows=3 if kind == "rollback_loss" else 1,
        seconds=deadline_seconds if deadline_seconds is not None else 120,
    )
    request = prepare_guarded_execution(
        preparation,
        access,
        limits=limits,
        isolation="serializable" if blocked else "stable",
        mysql_deployment=deployment(access, preparation.artifact),
    )
    owner = product.MySQLExecution(request)
    observer = Calls(owner)
    record: dict[str, Any] = {"kind": kind, "rows": [], "interventions": []}
    original_control = product.read_control
    injected = set()
    stop = threading.Event()
    thread = None

    def control(owner_, sql, *args, **kwargs):
        result = original_control(owner_, sql, *args, **kwargs)
        if (kind, sql) in (("commit_loss", "COMMIT"), ("rollback_loss", "ROLLBACK")):
            record["interventions"].append(
                {"kind": "injected_reply_loss", "native_command_returned": sql}
            )
            raise OSError("injected transaction reply loss")
        return result

    def interrupt_blocked():
        until = owner._started + limits.seconds + 2
        while not stop.is_set() and time.monotonic() < until:
            rows = manager(
                resource,
                "SELECT COUNT(*) FROM performance_schema.data_lock_waits WHERE REQUESTING_THREAD_ID=?",
                (owner._epoch[0],),
            )
            if len(rows) == 1 and type(rows[0][0]) is int and rows[0][0] > 0:
                record["interventions"].append(
                    {
                        "kind": "actual_native_lock_wait",
                        "thread_id": owner._epoch[0],
                        "wait_edges": rows[0][0],
                        "since_open_seconds": time.monotonic() - owner._started,
                    }
                )
                if kind == "blocked_cancel":
                    record["cancel_return"] = owner.cancel()
                else:
                    owner._cancel.wait(10)
                return
            stop.wait(0.02)
        record["interventions"].append({"kind": "native_wait_not_observed"})

    if blocked:
        manager(resource, "START TRANSACTION")
        manager(resource, "SELECT token FROM phase66.p68_guard_lhs FOR UPDATE")
    product.read_control = control
    try:
        with observer, owner:
            if kind == "snapshot_writer":
                manager(resource, "START TRANSACTION")
                manager(resource, "UPDATE phase66.p68_guard_rhs SET `key value`=42")
                manager(resource, "COMMIT")
                record["interventions"].append(
                    {
                        "kind": "actual_business_data_commit",
                        "rows": manager(
                            resource, "SELECT `key value` FROM phase66.p68_guard_rhs"
                        ),
                    }
                )
            elif kind == "replace_transaction":
                with owner._connection.cursor() as cursor:
                    cursor.execute("COMMIT")
                    cursor.execute(
                        "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY"
                    )
                record["interventions"].append(
                    {"kind": "actual_same_connection_commit_begin"}
                )
            elif kind == "role_change":
                manager(resource, "GRANT 'pietto_subset'@'%' TO 'pietto_query'@'%'")
                with owner._connection.cursor() as cursor:
                    cursor.execute("SET ROLE 'pietto_subset'@'%'")
                record["interventions"].append({"kind": "actual_set_role"})
            elif kind == "prepare_error":
                manager(resource, "REVOKE SELECT ON phase66.* FROM 'pietto_query'@'%'")
                record["interventions"].append(
                    {"kind": "actual_select_privilege_revoked_after_admission"}
                )
            elif kind == "read_error":
                original_read = owner._connection.get_rows

                def fail_read(*args, **kwargs):
                    result = original_read(*args, **kwargs)
                    if kwargs.get("binary") is True and "read" not in injected:
                        injected.add("read")
                        record["interventions"].append(
                            {"kind": "injected_binary_read_reply_loss"}
                        )
                        raise OSError("injected read reply loss")
                    return result

                owner._connection.get_rows = fail_read
            elif kind == "close_send_error":
                original_close = owner._connection.cmd_stmt_close

                def fail_close(*args, **kwargs):
                    original_close(*args, **kwargs)
                    record["interventions"].append(
                        {"kind": "injected_close_send_return_loss"}
                    )
                    raise OSError("injected close-send return loss")

                owner._connection.cmd_stmt_close = fail_close
            if blocked:
                thread = threading.Thread(
                    target=interrupt_blocked, name="pietto-s08-test-lock-rendezvous"
                )
                record["interventions"].append(
                    {"kind": "test_thread_registered", "name": thread.name}
                )
                thread.start()
            for batch in owner:
                with batch:
                    array = pa.record_batch(batch)
                    record["rows"].extend(
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
                if kind == "early_close":
                    owner.close()
                    break
                if kind == "rollback_loss":
                    raise ValueError("injected consumer failure")
                if kind == "slow_consumer":
                    assert owner._cancel.wait(limits.seconds + 2)
            if kind == "late_cancel":
                record["cancel_return"] = owner.cancel()
    except BaseException as error:
        record["failure"] = {
            "kind": type(error).__name__,
            "category": str(error),
            "errno": getattr(error, "errno", None),
            "sqlstate": getattr(error, "sqlstate", None),
        }
    finally:
        stop.set()
        if thread is not None:
            thread.join(12)
            record["test_thread_joined"] = not thread.is_alive()
        owner.close()
        product.read_control = original_control
        if blocked:
            manager(resource, "ROLLBACK")
        if kind == "prepare_error":
            manager(resource, "GRANT SELECT ON phase66.* TO 'pietto_query'@'%'")
        record.update(
            events=observer.events,
            outcome=asdict(owner.outcome),
            session=owner.session_id,
            epoch=owner._epoch,
            control_joined=owner.control_joined,
            control_events=owner.control_events,
            deadline_expired=owner.deadline_expired,
        )
        record["sessions_gone"] = {
            str(c.connection_id): session_gone(resource, c.connection_id)
            for c in owner._connections
            if c.connection_id is not None
        }
    return record


def control_family(directory, ledger, tree):
    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources("mysql", pins["targets"]["mysql"], directory)
    event(
        ledger,
        {
            "kind": "targeted_native_start",
            "family": "mysql_owned_controls",
            "directory": str(directory),
            "database": resource.name,
        },
        targeted_live_family_starts=1,
        source_db_lifecycle_starts=1,
    )
    report: dict[str, Any] = {"tree": tree, "controls": []}
    try:
        resource.acquire()
        setup(resource)
        for table in ("threads", "events_transactions_current"):
            manager(
                resource,
                "GRANT SELECT ON performance_schema."
                + table
                + " TO 'pietto_query'@'%'",
            )
        case = next(c for c in manifest() if c["name"] == "no_request")
        preparation = case_preparation(
            directory / (PREFIX + "control-input"), "mysql", case
        )
        fill(resource, case["lhs"], case["rhs"])
        blocking_entry_seconds = None
        for kind in (
            "replace_transaction",
            "role_change",
            "prepare_error",
            "read_error",
            "commit_loss",
            "rollback_loss",
            "close_send_error",
            "early_close",
            "late_cancel",
            "blocked_cancel",
            "blocked_deadline",
            "slow_consumer",
        ):
            deadline_seconds = None
            if kind in ("blocked_deadline", "slow_consumer"):
                if blocking_entry_seconds is None:
                    raise ValueError("S08_MISSING_MEASURED_BLOCK_ENTRY")
                deadline_seconds = blocking_entry_seconds + 5
            record = controlled_attempt(
                resource, preparation, kind, deadline_seconds=deadline_seconds
            )
            if kind == "blocked_cancel":
                blocking_entry_seconds = next(
                    x["since_open_seconds"]
                    for x in record["interventions"]
                    if x["kind"] == "actual_native_lock_wait"
                )
            report["controls"].append(record)
            write(directory / (PREFIX + "controls.json"), report)
            print(kind, record.get("failure"), record["outcome"], flush=True)
            assert record["control_joined"] and all(
                rows[-1] == 0 for rows in record["sessions_gone"].values()
            )
            assert record.get("test_thread_joined", True)
            if kind == "late_cancel":
                assert (
                    record["outcome"]["transaction"] == "COMMIT_ACK"
                    and record["cancel_return"]["late"]
                )
            elif kind == "early_close":
                assert record["outcome"]["source"] == "EARLY_CLOSE"
            else:
                assert "failure" in record and record["outcome"]["delivery"] == "FAILED"
            if kind in ("replace_transaction", "commit_loss", "rollback_loss"):
                assert record["outcome"]["transaction"] == "UNKNOWN"
            if kind.startswith("blocked_"):
                assert any(
                    x["kind"] == "actual_native_lock_wait"
                    for x in record["interventions"]
                )
                assert record["outcome"]["cancel_requested"]
        report["result"] = "PASS_TWELVE_SOURCE_CONTROLS"
    finally:
        from _pietto_phase68_slice7_probe import origins
        from _pietto_mysql_native_prepared import driver_sources

        report["origins"] = origins()
        report["driver_sources"] = driver_sources()
        report["cleanup"] = resource.cleanup()
        write(directory / (PREFIX + "controls.json"), report)
        event(
            ledger,
            {
                "kind": "targeted_native_terminal",
                "family": "mysql_owned_controls",
                "result": report.get("result", "FAILED"),
                "cleanup": report["cleanup"],
            },
        )


def source_lifetime_family(directory, ledger, tree):
    """Metadata-only pinning premise; never execute or EXPLAIN a source view."""
    from _pietto_phase68_slice3_probe import view_sql
    from pietto._project.project_mysql_view_source import recognize_view
    from pietto._project.project_mysql_view_source_verification import verify_view
    from _pietto_mysql_native_prepared import driver_sources

    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources("mysql", pins["targets"]["mysql"], directory)
    event(
        ledger,
        {
            "kind": "targeted_native_start",
            "family": "source_metadata_lifetime",
            "tree": tree,
            "directory": str(directory),
            "database": resource.name,
        },
        targeted_live_family_starts=1,
        source_db_lifecycle_starts=1,
    )
    report: dict[str, Any] = {
        "tree": tree,
        "cases": [],
        "definitions": [],
        "purpose": "metadata-only qualification/lifetime premise, no source execution acceptance",
    }
    query: Any = None
    control: Any = None
    started = time.monotonic()

    def read(connection, sql, args=()):
        with connection.cursor(read_timeout=10, write_timeout=2) as cursor:
            cursor.execute(sql, args)
            rows = cursor.fetchall() if cursor.description else []
            return {
                "sql": sql,
                "arguments": args,
                "rows": rows,
                "warnings": cursor.warning_count,
                "session": connection.connection_id,
                "normal_terminal": not connection.unread_result,
            }

    def epoch():
        return read(
            control,
            "SELECT t.THREAD_ID,e.EVENT_ID,e.STATE,e.ACCESS_MODE,e.ISOLATION_LEVEL,e.AUTOCOMMIT,@@server_uuid FROM performance_schema.threads t JOIN performance_schema.events_transactions_current e USING(THREAD_ID) WHERE t.PROCESSLIST_ID=%s",
            (query.connection_id,),
        )

    def locks():
        return read(
            control,
            "SELECT m.OBJECT_TYPE,m.OBJECT_SCHEMA,m.OBJECT_NAME,m.LOCK_TYPE,m.LOCK_DURATION,m.LOCK_STATUS,m.OBJECT_INSTANCE_BEGIN FROM performance_schema.metadata_locks m JOIN performance_schema.threads t ON t.THREAD_ID=m.OWNER_THREAD_ID WHERE t.PROCESSLIST_ID=%s ORDER BY m.OBJECT_SCHEMA,m.OBJECT_NAME,m.LOCK_TYPE",
            (query.connection_id,),
        )

    try:
        resource.acquire()
        for name in ("left", "right"):
            manager(
                resource,
                f"CREATE TABLE p68s3_{name}(lid INTEGER PRIMARY KEY,version_id INTEGER,k SMALLINT,v SMALLINT,visible VARCHAR(32),hidden BIGINT,f DOUBLE PRECISION) ENGINE=InnoDB",
            )
            manager(
                resource,
                f"INSERT INTO p68s3_{name} VALUES(1,1,1,10,'same',9007199254740993,0.0)",
            )
        manager(resource, "CREATE VIEW p68s3_input AS " + view_sql("mysql"))
        manager(
            resource,
            "CREATE TABLE p68_mdl_base(id BIGINT, p68_raw_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY) ENGINE=InnoDB",
        )
        manager(resource, "INSERT INTO p68_mdl_base(id) VALUES (1),(1)")
        manager(
            resource,
            "CREATE VIEW p68_mdl_wrapper AS SELECT b.*,CAST((p68_raw_id-1)%2 AS SIGNED) AS p68_part,CAST((p68_raw_id-1) DIV 2 AS SIGNED) AS p68_lid FROM phase66.p68_mdl_base AS b",
        )
        manager(
            resource,
            "CREATE VIEW p68_mdl_nested AS SELECT id,p68_part,p68_lid FROM p68_mdl_wrapper",
        )
        manager(
            resource,
            "CREATE TABLE p68_mdl_registry(version_tag VARCHAR(32)) ENGINE=InnoDB",
        )
        manager(resource, "INSERT INTO p68_mdl_registry VALUES ('v1')")
        manager(
            resource,
            "CREATE TABLE p68_mdl_role_base(id BIGINT,source_version VARCHAR(32)) ENGINE=InnoDB",
        )
        manager(resource, "INSERT INTO p68_mdl_role_base VALUES (1,'v1')")
        manager(
            resource,
            "CREATE SQL SECURITY INVOKER VIEW p68_mdl_role AS SELECT b.* FROM p68_mdl_role_base AS b WHERE b.source_version=(SELECT version_tag FROM p68_mdl_registry) AND (CURRENT_USER()<>'pietto_subset@%' OR b.id<>1)",
        )
        manager(
            resource,
            "CREATE FUNCTION p68_mdl_canary() RETURNS BIGINT NOT DETERMINISTIC NO SQL SQL SECURITY DEFINER BEGIN SET @p68_mdl_invoked=COALESCE(@p68_mdl_invoked,0)+1; RETURN 1; END",
        )
        manager(
            resource,
            "CREATE VIEW p68_mdl_unsafe AS SELECT p68_mdl_canary() AS id FROM p68_mdl_base",
        )
        for sql, _ in resource.role_statements()[:1]:
            manager(resource, sql)
        views = (
            "p68s3_input",
            "p68_mdl_wrapper",
            "p68_mdl_nested",
            "p68_mdl_role",
            "p68_mdl_unsafe",
        )
        bases = (
            "p68s3_left",
            "p68s3_right",
            "p68_mdl_base",
            "p68_mdl_registry",
            "p68_mdl_role_base",
        )
        for name in views:
            manager(
                resource,
                "GRANT SELECT,SHOW VIEW ON phase66.`"
                + name
                + "` TO 'pietto_query'@'%'",
            )
        for name in bases:
            manager(
                resource,
                "GRANT SHOW VIEW ON phase66.`" + name + "` TO 'pietto_query'@'%'",
            )
        # INVOKER access needs these two exact source objects; definer-wrapper
        # backing tables keep metadata-only rights for the query account.
        for name in ("p68_mdl_registry", "p68_mdl_role_base"):
            manager(
                resource, "GRANT SELECT ON phase66.`" + name + "` TO 'pietto_query'@'%'"
            )
        for name in ("threads", "events_transactions_current", "metadata_locks"):
            manager(
                resource,
                "GRANT SELECT ON performance_schema." + name + " TO 'pietto_query'@'%'",
            )
        query = resource.query = resource.connect(query=True)
        resource.event("metadata_query_registered", session=query.connection_id)
        control = resource.connect(query=True)
        resource.event("metadata_control_registered", session=control.connection_id)
        report["identity"] = read(
            query,
            "SELECT VERSION(),CURRENT_USER(),CURRENT_ROLE(),DATABASE(),@@sql_mode,@@sql_quote_show_create,@@character_set_connection,@@collation_connection,@@server_uuid",
        )
        report["driver_sources"] = driver_sources()
        report["grants"] = read(query, "SHOW GRANTS FOR CURRENT_USER")
        read(query, "SET @p68_mdl_invoked=0")
        for name in views:
            record = read(query, "SHOW CREATE VIEW phase66.`" + name + "`")
            try:
                row = record["rows"][0]
                proof = recognize_view(
                    ("phase66", name), row[1], charset=row[2], collation=row[3]
                )
                record["references"] = verify_view(proof)
                record["structure"] = "QUALIFIED_DATA_ONLY"
            except Exception as error:
                record["structure"] = "REJECTED"
                record["category"] = str(error)
            report["definitions"].append(record)
        report["canary_after_definitions"] = read(query, "SELECT @p68_mdl_invoked")
        manager(resource, "SET SESSION lock_wait_timeout=1")
        mechanisms = (
            (
                "show_create_view",
                "SHOW CREATE VIEW phase66.p68_mdl_wrapper",
                (),
                "view",
            ),
            (
                "show_create_table",
                "SHOW CREATE TABLE phase66.p68_mdl_base",
                (),
                "table",
            ),
            (
                "information_schema_view_share",
                "SELECT TABLE_NAME,VIEW_DEFINITION,DEFINER,SECURITY_TYPE,CHARACTER_SET_CLIENT,COLLATION_CONNECTION FROM information_schema.VIEWS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s FOR SHARE",
                ("phase66", "p68_mdl_wrapper"),
                "view",
            ),
            (
                "information_schema_table_share",
                "SELECT TABLE_NAME,TABLE_TYPE,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s FOR SHARE",
                ("phase66", "p68_mdl_base"),
                "table",
            ),
            (
                "information_schema_columns_share",
                "SELECT COLUMN_NAME,EXTRA,GENERATION_EXPRESSION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION FOR SHARE",
                ("phase66", "p68_mdl_base"),
                "table",
            ),
        )
        for isolation in ("REPEATABLE READ", "SERIALIZABLE"):
            for mechanism, sql, args, target in mechanisms:
                record: dict[str, Any] = {
                    "mechanism": mechanism,
                    "isolation": isolation,
                    "target": target,
                }
                report["cases"].append(record)
                read(query, "SET SESSION TRANSACTION ISOLATION LEVEL " + isolation)
                read(
                    query,
                    "START TRANSACTION "
                    + (
                        "WITH CONSISTENT SNAPSHOT, "
                        if isolation == "REPEATABLE READ"
                        else ""
                    )
                    + "READ ONLY",
                )
                record["epoch_before"] = epoch()
                try:
                    record["acquisition"] = read(query, sql, args)
                except Exception as error:
                    record["acquisition_error"] = {
                        "kind": type(error).__name__,
                        "errno": getattr(error, "errno", None),
                        "sqlstate": getattr(error, "sqlstate", None),
                    }
                record["locks_after_acquisition"] = locks()
                record["epoch_after"] = epoch()
                try:
                    if target == "view":
                        manager(
                            resource,
                            "ALTER VIEW p68_mdl_wrapper AS SELECT b.*,CAST((p68_raw_id-1)%2 AS SIGNED) AS p68_part,CAST((p68_raw_id-1) DIV 2 AS SIGNED) AS p68_lid FROM phase66.p68_mdl_base AS b WHERE b.id>=0",
                        )
                    else:
                        manager(
                            resource,
                            "ALTER TABLE p68_mdl_base ENGINE=MyISAM",
                        )
                    record["ddl"] = "COMPLETED_WHILE_READER_OPEN"
                except Exception as error:
                    record["ddl"] = "REFUSED_OR_BLOCKED"
                    record["ddl_error"] = {
                        "kind": type(error).__name__,
                        "errno": getattr(error, "errno", None),
                        "sqlstate": getattr(error, "sqlstate", None),
                    }
                read(query, "ROLLBACK")
                record["locks_after_rollback"] = locks()
                if target == "table":
                    record["engine_after_ddl"] = read(
                        resource.manager,
                        "SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA='phase66' AND TABLE_NAME='p68_mdl_base'",
                    )
                    manager(resource, "ALTER TABLE p68_mdl_base ENGINE=InnoDB")
                print(
                    isolation,
                    mechanism,
                    record.get("acquisition_error"),
                    record["ddl"],
                    record["locks_after_acquisition"]["rows"],
                    flush=True,
                )
                write(directory / (PREFIX + "metadata-lifetime.json"), report)
        report["canary_final"] = read(query, "SELECT @p68_mdl_invoked")
        report["result"] = "OBSERVED_METADATA_LIFETIME_CANDIDATES"
    finally:
        for connection in (query, control):
            if connection is not None:
                session = connection.connection_id
                connection.close()
                report.setdefault("sessions_gone", {})[str(session)] = session_gone(
                    resource, session
                )
        resource.query = None
        report["cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - started
        write(directory / (PREFIX + "metadata-lifetime.json"), report)
        event(
            ledger,
            {
                "kind": "targeted_native_terminal",
                "family": "source_metadata_lifetime",
                "tree": tree,
                "result": report.get("result", "FAILED"),
                "cleanup": report["cleanup"],
                "seconds": report["seconds"],
            },
        )


def managed_family(directory, ledger, tree):
    """Compact source-premise representatives, not the complete product corpus."""
    from _pietto_phase68_slice7_probe import origins
    from _pietto_mysql_native_prepared import driver_sources
    from pietto._project.project_guard_preparation import prepare_guarded_output

    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources("mysql", pins["targets"]["mysql"], directory)
    event(
        ledger,
        dict(
            kind="targeted_native_start",
            family="managed_sources",
            tree=tree,
            database=resource.name,
            directory=str(directory),
        ),
        targeted_live_family_starts=1,
        source_db_lifecycle_starts=1,
    )
    report: dict[str, Any] = dict(tree=tree, attempts=[], controls=[])

    def save(name, result):
        result["case"] = name
        report["attempts"].append(result)
        write(directory / (PREFIX + "managed.json"), report)
        print(name, result.get("failure"), result["outcome"], flush=True)
        assert result["control_joined"] and all(
            v[-1] == 0 for v in result["sessions_gone"].values()
        )

    try:
        resource.acquire()
        setup(resource)
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
        for name in (
            "no_request",
            "bag_one",
            "bag_two_equal_null",
            "source_text_wide",
            "path_whole_positive",
            "refined_pages",
        ):
            case = next(c for c in manifest() if c["name"] == name)
            preparation = case_preparation(directory / (PREFIX + name), "mysql", case)
            fill(
                resource,
                case["lhs"],
                case["rhs"],
                wide_text=case["options"].get("wide_text", False),
            )
            query = (
                refinement(resource, preparation, prepare_guarded_output(preparation))
                if case["options"].get("refined")
                else None
            )
            result = attempt(
                resource, preparation, query=query, ordinary=name == "no_request"
            )
            save(name, result)
            if name == "bag_two_equal_null":
                assert (
                    result.get("failure", {}).get("category") == "SINGLE_MATCH_VIOLATED"
                )
            else:
                assert "failure" not in result and result["rows"] == encoded(
                    case["rows"]
                )
                assert result["outcome"]["transaction"] == "COMMIT_ACK"
        case = next(c for c in manifest() if c["name"] == "no_request")
        preparation = case_preparation(directory / (PREFIX + "controls"), "mysql", case)
        fill(resource, case["lhs"], case["rhs"])
        for name, ordinary, allow, isolation in (
            ("missing_ordinary", True, True, "stable"),
            ("missing_disabled_guard", False, False, "stable"),
            ("missing_serializable", False, True, "serializable"),
        ):
            result = attempt(
                resource,
                preparation,
                managed=False,
                ordinary=ordinary,
                allow=allow,
                isolation=isolation,
            )
            save(name, result)
            assert result["failure"]["category"] == "MYSQL_DEPLOYMENT_PREMISE_REQUIRED"
            assert result["statements"] == [] and result["sources"] == []
        before = manager(resource, "SHOW CREATE VIEW phase66.`phase66 rhs é`")
        old = controlled_attempt(resource, preparation, "snapshot_writer")
        report["snapshot_old"] = old
        assert "failure" not in old and old["rows"] == encoded(case["rows"])
        new = attempt(resource, preparation, ordinary=True)
        save("snapshot_fresh", new)
        assert "failure" not in new and new["rows"] == encoded(((1, 42), (1, 42)))
        report["snapshot_definitions"] = [
            before,
            manager(resource, "SHOW CREATE VIEW phase66.`phase66 rhs é`"),
        ]
        assert report["snapshot_definitions"][0] == report["snapshot_definitions"][1]
        # A fresh attempt sees a changed engine after the old use has ended.
        manager(resource, "ALTER TABLE phase66.p68_guard_rhs ENGINE=MyISAM")
        changed = attempt(resource, preparation, ordinary=True)
        save("between_attempt_engine_change", changed)
        assert (
            changed["failure"]["category"] == "MYSQL_SOURCE_ENGINE"
            and not changed["statements"]
        )
        manager(resource, "ALTER TABLE phase66.p68_guard_rhs ENGINE=InnoDB")
        manager(resource, "CREATE DATABASE p68_hidden")
        manager(
            resource,
            "CREATE TABLE p68_hidden.nontransactional (id BIGINT NOT NULL) ENGINE=MyISAM",
        )
        manager(resource, "INSERT INTO p68_hidden.nontransactional VALUES (1)")
        manager(
            resource,
            "CREATE FUNCTION p68_hidden.read_value() RETURNS BIGINT READS SQL DATA SQL SECURITY DEFINER RETURN (SELECT id FROM p68_hidden.nontransactional LIMIT 1)",
        )
        report["routine_instrumentation"] = manager(
            resource,
            "SELECT NAME,ENABLED FROM performance_schema.setup_instruments WHERE NAME LIKE 'statement/sp/%' ORDER BY NAME",
        )

        def calls():
            return manager(
                resource,
                "SELECT OBJECT_TYPE,OBJECT_SCHEMA,OBJECT_NAME,COUNT_STAR FROM performance_schema.events_statements_summary_by_program WHERE OBJECT_SCHEMA='p68_hidden' AND OBJECT_NAME='read_value'",
            )

        report["routine_calls_before"] = calls()
        for name, body in (
            (
                "hidden_routine",
                "SELECT p68_hidden.read_value() AS `order.id`,CAST(NULL AS SIGNED) AS `key value`",
            ),
            (
                "visible_base_hidden_routine",
                "SELECT p68_hidden.read_value() AS `order.id`,b.`key value` AS `key value` FROM phase66.p68_guard_lhs b",
            ),
        ):
            manager(
                resource,
                "CREATE OR REPLACE SQL SECURITY DEFINER VIEW phase66.`phase66 lhs é` AS "
                + body,
            )
            result = attempt(resource, preparation, ordinary=True)
            save(name, result)
            assert (
                result["failure"]["category"] == "MYSQL_VIEW_UNQUALIFIED_CALL"
                and not result["statements"]
            )
        report["routine_calls_after"] = calls()
        assert all(
            tuple(row[:3]) == ("FUNCTION", "p68_hidden", "read_value") and row[3] == 0
            for row in report["routine_calls_after"]
        )
        report["result"] = "PASS_MANAGED_SOURCE_REPRESENTATIVES"
    finally:
        report["origins"] = origins()
        report["driver_sources"] = driver_sources()
        report["cleanup"] = resource.cleanup()
        write(directory / (PREFIX + "managed.json"), report)
        event(
            ledger,
            dict(
                kind="targeted_native_terminal",
                family="managed_sources",
                result=report.get("result", "FAILED"),
                cleanup=report["cleanup"],
            ),
        )


CONTROL_CASES = (
    "replace_transaction",
    "role_change",
    "prepare_error",
    "read_error",
    "commit_loss",
    "rollback_loss",
    "close_send_error",
    "early_close",
    "late_cancel",
    "blocked_cancel",
    "blocked_deadline",
    "slow_consumer",
)


def component_artifact(directory):
    import _pietto_phase67_result_product_probe as product
    from pietto._project.project_sql_emission import emit_project_sql

    directory.parent.mkdir(parents=True, exist_ok=True)
    checked = product.build_neutral(directory, {"main.pietto": product.source("mysql")})
    contract = json.loads(product.emission_input("mysql"))
    source = contract["sources"][0]
    source["relation"]["name"] = "p68s3_input"
    source["fields"][0]["column"] = "hidden"
    source["fields"][1]["column"] = "v"
    source["fields"][1]["representation"]["storage"] = {"kind": "my_smallint"}
    source["fields"][1]["representation"]["domain"] = {
        "kind": "int_range",
        "min": "-32768",
        "max": "32767",
    }
    outcome = emit_project_sql(checked, json.dumps(contract).encode())
    if outcome.status != "VERIFIED":
        raise ValueError("S08_COMPONENT_INPUT")
    return outcome.artifact


def source_delta(resource, directory):
    """Fresh narrow assumption/security representatives on original definitions."""
    from types import SimpleNamespace

    records = []
    artifact = component_artifact(directory / "component")
    result = attempt(resource, SimpleNamespace(artifact=artifact), ordinary=True)
    result["case"] = "component_union_all"
    records.append(result)
    case = next(c for c in manifest() if c["name"] == "no_request")
    prep = case_preparation(directory / "source-delta", "mysql", case)
    fill(resource, case["lhs"], case["rhs"])
    original = manager(resource, "SHOW CREATE VIEW phase66.`phase66 lhs é`")[0][1]
    try:
        manager(resource, "CREATE DATABASE IF NOT EXISTS p68_scope")
        manager(
            resource,
            "CREATE TABLE IF NOT EXISTS p68_scope.private_base (id BIGINT NOT NULL, v BIGINT) ENGINE=InnoDB",
        )
        manager(resource, "DELETE FROM p68_scope.private_base")
        manager(resource, "INSERT INTO p68_scope.private_base VALUES (1,NULL)")
        manager(
            resource,
            "CREATE OR REPLACE SQL SECURITY INVOKER VIEW p68_scope.nested AS SELECT id,v FROM p68_scope.private_base WHERE CURRENT_USER()='root@%'",
        )
        manager(
            resource, "GRANT REFERENCES ON p68_scope.private_base TO 'pietto_query'@'%'"
        )
        manager(
            resource,
            "GRANT SELECT,SHOW VIEW ON p68_scope.nested TO 'pietto_query'@'%'",
        )
        manager(
            resource,
            "CREATE OR REPLACE SQL SECURITY DEFINER VIEW phase66.`phase66 lhs é` AS SELECT id AS `order.id`,v AS `key value` FROM p68_scope.nested",
        )
        for name, schemas in (
            ("outside_accepted_scope", ("phase66",)),
            ("nested_definer_invoker", ("phase66", "p68_scope")),
        ):
            result = attempt(resource, prep, ordinary=True, schemas=schemas)
            result["case"] = name
            result["query_role_grants"] = manager(
                resource, "SHOW GRANTS FOR 'pietto_query'@'%'"
            )
            records.append(result)
        manager(resource, "CREATE DATABASE IF NOT EXISTS p68_hidden")
        manager(
            resource,
            "CREATE TABLE IF NOT EXISTS p68_hidden.nontransactional (id BIGINT NOT NULL) ENGINE=MyISAM",
        )
        manager(resource, "DELETE FROM p68_hidden.nontransactional")
        manager(resource, "INSERT INTO p68_hidden.nontransactional VALUES (1)")
        manager(resource, "DROP FUNCTION IF EXISTS p68_hidden.read_value")
        manager(
            resource,
            "CREATE FUNCTION p68_hidden.read_value() RETURNS BIGINT READS SQL DATA SQL SECURITY DEFINER RETURN (SELECT id FROM p68_hidden.nontransactional LIMIT 1)",
        )
        for name, body in (
            (
                "hidden_routine",
                "SELECT p68_hidden.read_value() AS `order.id`,CAST(NULL AS SIGNED) AS `key value`",
            ),
            (
                "visible_base_hidden_routine",
                "SELECT p68_hidden.read_value() AS `order.id`,b.`key value` AS `key value` FROM phase66.p68_guard_lhs b",
            ),
        ):
            manager(
                resource,
                "CREATE OR REPLACE SQL SECURITY DEFINER VIEW phase66.`phase66 lhs é` AS "
                + body,
            )
            counter = "SELECT OBJECT_TYPE,OBJECT_SCHEMA,OBJECT_NAME,COUNT_STAR FROM performance_schema.events_statements_summary_by_program WHERE OBJECT_SCHEMA='p68_hidden' AND OBJECT_NAME='read_value'"
            before = manager(resource, counter)
            result = attempt(resource, prep, ordinary=True)
            result.update(
                case=name,
                routine_calls_before=before,
                routine_calls_after=manager(resource, counter),
            )
            records.append(result)
    finally:
        manager(resource, "DROP VIEW phase66.`phase66 lhs é`")
        manager(resource, original)
    return records


def worker(config_path):
    """Fresh extraction process; independent oracles are consumed by the parent."""
    import os
    from types import SimpleNamespace
    from _pietto_phase68_slice6_cases import original, source_requirements
    from _pietto_phase68_slice7_probe import origins
    from _pietto_mysql_native_prepared import driver_sources
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_guard_preparation import (
        prepare_guarded_output,
        prepare_guarded_template,
    )
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_refinement import prepare_refinement, TieRefinement

    config = json.loads(config_path.read_text())
    directory = Path(config["directory"])
    connection_root = directory / (PREFIX + "worker-manager")
    connection_root.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources("mysql", pins["targets"]["mysql"], connection_root)
    resource.port, resource._passwords = config["port"], tuple(config["passwords"])
    resource.ca_path = Path(config["ca"])
    resource.startup_started = time.monotonic()
    report: dict[str, Any] = dict(
        tree=config["tree"],
        origin=config["origin"],
        group=config["group"],
        worker_pid=os.getpid(),
        parent_database=config["database"],
        attempts=[],
    )
    path = directory / (PREFIX + "worker.json")
    template = first_binding = None
    try:
        resource.manager = resource.connect(query=False)
        report["manager_session"] = resource.manager.connection_id
        for index, selected in enumerate(config["cases"]):
            case, variant = selected["family"], selected.get("variant")
            work = directory / (PREFIX + str(index))
            binding = query = None
            options: dict[str, Any] = {}
            if config["group"] == "guarded":
                fixture = next(c for c in manifest() if c["name"] == case)
                options = fixture["options"]
                fill(
                    resource,
                    fixture["lhs"],
                    fixture["rhs"],
                    wide_text=options.get("wide_text", False),
                )
                if "binding_values" in options:
                    if template is None:
                        template = prepare_guarded_template(
                            case_preparation(work, "mysql", fixture)
                        )
                    if case == "binding_A_again":
                        binding = first_binding
                    else:
                        supplied = list(
                            zip(template.slots, options["binding_values"], strict=True)
                        )
                        binding = bind_values(template, supplied)
                        supplied.clear()
                        if case == "binding_A":
                            first_binding = binding
                    if binding is None:
                        raise ValueError("S08_MISSING_ORIGINAL_BINDING")
                    preparation = binding.guarded
                else:
                    preparation = case_preparation(work, "mysql", fixture)
                if options.get("refined"):
                    query = refinement(
                        resource,
                        preparation,
                        prepare_guarded_output(preparation, binding=binding),
                        role=options.get("role", "pietto_query"),
                    )
            else:
                artifact = original(
                    work, "mysql", "R2_seven" if case == "seven" else case, variant
                )
                if artifact is None:
                    raise ValueError("S08_UNEXPECTED_COMPILER_BLOCKER")
                preparation = SimpleNamespace(artifact=artifact)
                if config["group"] == "unguarded_refinement":
                    query = prepare_refinement(
                        artifact,
                        source_requirements(
                            artifact, config["providers"], "pietto_query@%"
                        ),
                        policy=TieRefinement(),
                        output=prepare_output(artifact),
                    )
            result = attempt(
                resource,
                preparation,
                query=query,
                ordinary=config["group"] != "guarded",
                allow=options.get("allow", True),
                size=options.get("page_size", 2),
                isolation=options.get("isolation", "stable"),
                binding=binding,
                user=options.get("role", "pietto_query"),
            )
            result.update(case=case, variant=variant)
            report["attempts"].append(result)
            write(path, report)
            print(
                config["origin"],
                config["group"],
                index,
                case,
                variant,
                result.get("failure"),
                flush=True,
            )
        report["controls"] = []
        if config.get("controls"):
            base = next(c for c in manifest() if c["name"] == "no_request")
            prep = case_preparation(
                directory / (PREFIX + "control-input"), "mysql", base
            )
            blocking_entry_seconds = None
            for kind in config["controls"]:
                fill(resource, base["lhs"], base["rhs"])
                seconds = None
                if kind in ("blocked_deadline", "slow_consumer"):
                    if blocking_entry_seconds is None:
                        raise ValueError("S08_MISSING_MEASURED_BLOCK_ENTRY")
                    seconds = blocking_entry_seconds + 5
                result = controlled_attempt(
                    resource, prep, kind, deadline_seconds=seconds
                )
                report["controls"].append(result)
                write(path, report)
                print(
                    config["origin"], "control", kind, result.get("failure"), flush=True
                )
                if kind == "blocked_cancel":
                    blocking_entry_seconds = next(
                        x["since_open_seconds"]
                        for x in result["interventions"]
                        if x["kind"] == "actual_native_lock_wait"
                    )
        if config.get("source_delta", bool(config.get("controls"))):
            report["source_delta"] = source_delta(
                resource, directory / (PREFIX + "source-delta")
            )
            write(path, report)
        if config.get("fresh_refinement"):
            artifact = original(
                directory / (PREFIX + "fresh-root"),
                "mysql",
                "G_emission_table_bag",
                "bag",
            )
            query = prepare_refinement(
                artifact,
                source_requirements(artifact, config["providers"], "pietto_query@%"),
                policy=TieRefinement(),
                output=prepare_output(artifact),
            )
            prep = SimpleNamespace(artifact=artifact)
            report["fresh_refinement"] = [
                attempt(
                    resource, prep, query=query, ordinary=True, size=1, prefix=True
                ),
                attempt(resource, prep, query=query, ordinary=True, size=1),
            ]
            write(path, report)
        report["acquisition"] = "FINISHED_REQUIRES_INDEPENDENT_CHECK"
    finally:
        from _pietto_phase68_slice6_probe import s01

        report["origins"] = origins()
        report["runtime"] = s01.runtime_identity()
        report["driver_sources"] = driver_sources()
        if resource.manager is not None:
            resource.manager.close()
            resource.manager = None
        report["manager_local_closed"] = True
        write(path, report)


def reset_fixture_database(resource):
    """Only the owned fixture namespace, after all earlier product uses ended."""
    manager(resource, "DROP DATABASE phase66")
    manager(
        resource,
        "CREATE DATABASE phase66 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin",
    )
    manager(resource, "USE phase66")
    manager(resource, "DROP USER IF EXISTS 'pietto_query'@'%' ,'pietto_subset'@'%'")


def campaign(
    directory, ledger, tree, *, mode, readiness, reuse_source=None, reuse_ordinary=None
):
    """One DB, serial fresh workers; managers are closed across worker ownership."""
    import os
    import hashlib
    import _pietto_phase68_slice6_probe as six
    import _pietto_phase68_slice5_probe as five
    import _pietto_target_conformance_cases as fixtures
    from _pietto_phase68_slice8_check import check_worker

    if mode == "campaign":
        if readiness is None:
            raise ValueError("S08_READINESS_REQUIRED")
        ready = json.loads(readiness.read_text())
        if ready["tree"] != tree or ready["status"] != "GREEN_FOR_CURRENT_INPUTS":
            raise ValueError("S08_READINESS_IDENTITY")
        for path, digest in ready["inputs"].items():
            if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
                raise ValueError("S08_READINESS_CHANGED")
    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources("mysql", pins["targets"]["mysql"], directory)
    charge = (
        "complete_s08_live_campaign_starts"
        if mode == "campaign"
        else "targeted_live_family_starts"
    )
    event(
        ledger,
        dict(
            parent_pid=os.getpid(),
            kind=mode + "_start",
            tree=tree,
            directory=str(directory),
            database=resource.name,
        ),
        **{charge: 1, "source_db_lifecycle_starts": 1},
    )
    required = json.loads(
        (ledger.parent / (PREFIX + "acceptance-manifest.json")).read_text()
    )
    report: dict[str, Any] = dict(tree=tree, mode=mode, workers=[])
    providers = []
    if reuse_source is not None:
        if mode != "preflight":
            raise ValueError("S08_REUSE_ONLY_PREFLIGHT")
        prior = json.loads((reuse_source / (PREFIX + "worker.json")).read_text())
        prior_config = json.loads(
            (reuse_source / (PREFIX + "manifest.json")).read_text()
        )
        if (
            prior_config["origin"] != "source"
            or len(prior["attempts"]) != 7
            or len(prior["controls"]) != 12
        ):
            raise ValueError("S08_PREFLIGHT_REUSE_DENOMINATOR")
        prior_config["source_delta"] = False
        report["source_core_replay"] = check_worker(
            prior, prior_config, directory / (PREFIX + "reconsume"), ROOT
        )
        report["source_core_replay"].update(
            raw=str(reuse_source / (PREFIX + "worker.json")),
            raw_sha256=hashlib.sha256(
                (reuse_source / (PREFIX + "worker.json")).read_bytes()
            ).hexdigest(),
            producing_tree=prior["tree"],
            original_disposition="preflight02 FAILED before source-delta; only these independently complete attempts reused",
        )

    def reopen():
        # A fresh connection-only owner avoids resetting a live Resources budget.
        root = directory / (PREFIX + "manager-" + str(len(report["workers"])))
        root.mkdir(mode=0o700)
        owner = Resources("mysql", pins["targets"]["mysql"], root)
        owner.port, owner._passwords, owner.ca_path = (
            resource.port,
            resource._passwords,
            resource.ca_path,
        )
        owner.startup_started = time.monotonic()
        connection = owner.connect(query=False)
        report.setdefault("manager_sessions", []).append(connection.connection_id)
        resource.manager = connection
        return owner

    try:
        resource.acquire()
        report["manager_sessions"] = [resource.manager.connection_id]
        if mode == "reset-smoke":
            reset_fixture_database(resource)
        if reuse_ordinary is not None:
            if mode != "campaign":
                raise ValueError("S08_REUSE_ORDINARY_ONLY_CAMPAIGN")
            for origin in ("source", "installed"):
                previous = reuse_ordinary / (PREFIX + "ordinary-" + origin)
                raw = previous / (PREFIX + "worker.json")
                old = json.loads(raw.read_text())
                old_config = json.loads(
                    (previous / (PREFIX + "manifest.json")).read_text()
                )
                if old_config["origin"] != origin or len(old["attempts"]) != 50:
                    raise ValueError("S08_ORDINARY_REUSE_DENOMINATOR")
                audit = check_worker(
                    old,
                    old_config,
                    directory / (PREFIX + "ordinary-reconsume-" + origin),
                    ROOT,
                )
                report.setdefault("reused_ordinary", []).append(
                    dict(
                        origin=origin,
                        raw=str(raw),
                        raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
                        producing_tree=old["tree"],
                        audit=audit,
                        reason="Only parent fixture transition changed; complete original attempts reconsumed, never joined across sessions",
                    )
                )
        groups = (
            ("guarded",)
            if mode == "preflight"
            else ("unguarded_refinement",)
            if mode in ("refinement-smoke", "reset-smoke")
            else ("unguarded_refinement", "guarded")
            if reuse_ordinary is not None
            else ("ordinary", "unguarded_refinement", "guarded")
        )
        for group_index, group in enumerate(groups):
            if group_index:
                reset_fixture_database(resource)
            if group == "ordinary":
                for sql, args in (
                    fixtures.emission_setup("mysql")
                    + fixtures.native_setup("mysql")
                    + fixtures.row_domain_setup("mysql")
                ):
                    manager(resource, sql, args)
                five.setup_seven(resource)
                for sql, _ in resource.role_statements():
                    manager(resource, sql)
                manager(resource, "GRANT SHOW VIEW ON phase66.* TO 'pietto_query'@'%'")
            elif group == "unguarded_refinement":
                providers = six.setup(resource)
            else:
                setup(resource)
                providers = [
                    dict(
                        namespace="phase66",
                        name="phase66 " + side + " é",
                        provider="p68-guard-" + side,
                        version="v1",
                        revision="r1",
                        registry="p68_guard_registry_" + side,
                        tokens=["token"],
                        definition=manager(
                            resource,
                            "SHOW CREATE VIEW phase66.`phase66 " + side + " é`",
                        )[0][1],
                    )
                    for side in ("lhs", "rhs")
                ]
            if mode == "preflight":
                from _pietto_phase68_slice3_probe import setup as setup_component

                manager(resource, "DROP USER 'pietto_query'@'%'")
                report["component_fixture"] = setup_component(
                    resource, "p68-s08-component"
                )
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
            selected = [
                c
                for c in required["families"]
                if c["entry"] == group
                or group == "guarded"
                and c["entry"] == "guarded_refinement"
            ]
            if mode == "preflight":
                selected = [
                    c
                    for c in selected
                    if c["family"]
                    in (
                        "bound_four",
                        "bound_four_refined",
                        "seven_65_values",
                        "bag_two_equal_null",
                        "binding_A",
                        "binding_B",
                        "binding_A_again",
                    )
                ]
            if mode == "refinement-smoke":
                selected = [
                    c
                    for c in selected
                    if (c["family"], c.get("variant"))
                    in (
                        ("G_emission_table_bag", "bag"),
                        ("R2_mixed", "joint"),
                        ("R2_seven", "39_empty"),
                    )
                ]
                if len(selected) != 3:
                    raise ValueError("S08_REFINEMENT_PREFLIGHT_DENOMINATOR")
            if mode == "reset-smoke":
                selected = [
                    c
                    for c in selected
                    if (c["family"], c.get("variant"))
                    == ("G_emission_table_bag", "bag")
                ]
            for origin in ("source", "installed"):
                work = directory / (PREFIX + group + "-" + origin)
                work.mkdir(mode=0o700)
                config: dict[str, Any] = dict(
                    tree=tree,
                    origin=origin,
                    group=group,
                    directory=str(work),
                    port=resource.port,
                    passwords=resource._passwords,
                    ca=str(resource.ca_path),
                    database=resource.name,
                    providers=providers,
                    cases=selected,
                    controls=list(CONTROL_CASES) if mode == "preflight" else [],
                    source_delta=mode == "preflight",
                    schema_observation=True,
                    damages=mode == "campaign",
                    fresh_refinement=mode in ("campaign", "refinement-smoke")
                    and group == "unguarded_refinement",
                )
                if origin == "source" and reuse_source is not None:
                    config["cases"] = []
                    config["controls"] = []
                config_path = work / (PREFIX + "input.json")
                write(config_path, config)
                config_path.chmod(0o600)
                resource.manager.close()
                resource.manager = None
                argv = [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts/phase68_slice8_probe.py"),
                    "--mode",
                    "worker",
                    "--origin",
                    origin,
                    "--input",
                    str(config_path),
                ]
                env = dict(os.environ)
                env.pop("PYTHONPATH", None)
                count = (
                    len(selected)
                    + len(config["controls"])
                    + (5 if config["controls"] else 0)
                )
                with (work / (PREFIX + "worker.log")).open("w") as log:
                    code = worker_process(
                        argv,
                        env,
                        ledger,
                        log,
                        origin=origin,
                        group=group,
                        directory=work,
                        seconds=max(300, count * 180 + 120),
                    )
                observer_owner = reopen()
                observed = json.loads((work / (PREFIX + "worker.json")).read_text())
                observed["manager_gone"] = session_gone(
                    resource, observed["manager_session"]
                )
                write(work / (PREFIX + "worker.json"), observed)
                # Erase only the owned temporary plaintext input, retain nonsecret manifest.
                config_path.unlink()
                clean_config = {k: v for k, v in config.items() if k != "passwords"}
                write(work / (PREFIX + "manifest.json"), clean_config)
                report["workers"].append(
                    dict(path=str(work), origin=origin, group=group, returncode=code)
                )
                write(directory / (PREFIX + "campaign.json"), report)
                if code:
                    raise ValueError("S08_WORKER_FAILED")
                audit = check_worker(
                    observed, clean_config, work / (PREFIX + "independent"), ROOT
                )
                write(work / (PREFIX + "audit.json"), audit)
                report["workers"][-1]["audit"] = audit
                # Keep its registered connection referenced until closed by next iteration.
                observer_owner.manager = resource.manager
        report["result"] = "PASS_CURRENT_" + mode.upper()
    finally:
        report["cleanup"] = resource.cleanup()
        write(directory / (PREFIX + "campaign.json"), report)
        event(
            ledger,
            dict(
                kind=mode + "_terminal",
                result=report.get("result", "FAILED"),
                tree=tree,
                cleanup=report["cleanup"],
            ),
        )


def worker_process(argv, env, ledger, log, *, origin, group, directory, seconds):
    """Register before release and reap on every failure, including handshake."""
    import subprocess

    started = time.monotonic()
    child = subprocess.Popen(
        argv, env=env, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT
    )
    try:
        event(
            ledger,
            dict(
                kind="registered_worker",
                pid=child.pid,
                origin=origin,
                group=group,
                directory=str(directory),
            ),
        )
        if child.stdin is None:
            raise ValueError("S08_WORKER_REGISTRATION_PIPE")
        child.stdin.write(b"1")
        child.stdin.close()
        return child.wait(timeout=seconds)
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        if child.stdin is not None:
            child.stdin.close()
        event(
            ledger,
            dict(
                kind="worker_reaped",
                pid=child.pid,
                returncode=child.returncode,
                seconds=time.monotonic() - started,
            ),
        )
