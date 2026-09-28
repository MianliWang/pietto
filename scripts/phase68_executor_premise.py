"""Explicit local S01 experiments. Importing/checking reports never opens a DB."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import selectors
import struct
import subprocess
import sys
import tempfile
import threading
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice01-"
FORMAT = "pietto.phase68-executor-premise.v1"
STATUSES = (
    "OBSERVED_SUPPORTED",
    "OBSERVED_UNSUPPORTED",
    "OBSERVED_MISMATCH",
    "INCONCLUSIVE_ENVIRONMENT",
)
HELPERS = {
    "_pietto_phase68_executor_cases",
    "_pietto_target_conformance_resources",
    "_pietto_target_conformance_observation",
    "_pietto_mysql_native_prepared",
    "_pietto_phase66_sql_emission_probe",
    "_pietto_target_conformance_cases",
    "_pietto_phase67_result_product_probe",
    "_pietto_phase67_real_consumer_probe",
    "_pietto_phase67_whole_result_probe",
}


def helper(name):
    if name not in HELPERS:
        raise ValueError("unregistered helper")
    dependencies = {
        "_pietto_mysql_native_prepared": ("_pietto_target_conformance_resources",),
        "_pietto_target_conformance_observation": (
            "_pietto_target_conformance_resources",
        ),
        "_pietto_target_conformance_cases": (
            "_pietto_phase66_sql_emission_probe",
            "_pietto_mysql_native_prepared",
        ),
    }
    for dependency in dependencies.get(name, ()):
        helper(dependency)
    path = ROOT / "tests" / (name + ".py")
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    module = sys.modules[name]
    if Path(module.__file__).resolve() != path.resolve():
        raise ValueError("foreign helper")
    return module


def scalar(value):
    if value is None:
        return {"kind": "null"}
    if type(value) is bool:
        return {"kind": "bool", "value": value}
    if type(value) is int:
        return {"kind": "int", "value": str(value)}
    if type(value) is float:
        return {"kind": "float", "bits": struct.pack(">d", value).hex()}
    if type(value) is str:
        return {"kind": "text", "value": value}
    if type(value) is bytes:
        return {"kind": "bytes", "value": value.hex()}
    if isinstance(value, Decimal):
        sign, digits, exponent = value.as_tuple()
        coefficient = int("".join(map(str, digits))) * (-1 if sign else 1)
        return {"kind": "decimal", "coefficient": str(coefficient), "scale": -exponent}
    if isinstance(value, datetime):
        return {"kind": "datetime", "value": value.isoformat(timespec="microseconds")}
    if isinstance(value, UUID):
        return {"kind": "uuid", "value": value.hex}
    raise TypeError("unregistered scalar carrier: " + type(value).__name__)


def input_identity():
    paths = [
        "scripts/phase68_executor_premise.py",
        "ci/phase68-executor-premise-requirements.txt",
        "tests/phase66_target_pins.json",
        *["tests/" + x + ".py" for x in sorted(HELPERS)],
        "src/pietto/_project/project_result_binding.py",
        "src/pietto/_project/project_result_reader.py",
        "src/pietto/_project/project_arrow_interop.py",
    ]
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def runtime_identity():
    cases = helper("_pietto_phase68_executor_cases")
    result = {
        "python": sys.version,
        "executable": sys.executable,
        "versions": {},
        "origins": {},
        "libraries": {},
        "modules": {},
    }
    for name in cases.PINS:
        dist = importlib.metadata.distribution(name)
        result["versions"][name] = dist.version
        result["origins"][name] = str(dist.locate_file(""))
        for file in dist.files or ():
            path = Path(str(dist.locate_file(file))).resolve()
            if ".so" in path.name and path.is_file():
                result["libraries"][str(path)] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    for module, distribution in (
        ("psycopg", "psycopg"),
        ("mysql.connector", "mysql-connector-python"),
        ("adbc_driver_manager", "adbc-driver-manager"),
        ("adbc_driver_postgresql", "adbc-driver-postgresql"),
        ("pyarrow", "pyarrow"),
    ):
        result["modules"][module] = str(
            Path(
                str(
                    importlib.metadata.distribution(distribution).locate_file(
                        module.replace(".", "/") + "/__init__.py"
                    )
                )
            ).resolve()
        )
    return result


def scalar_domain(record, route):
    """Carrier/domain legality, separate from original positional value equality."""
    try:
        for row in record["actual"]:
            if len(row) != 7:
                return False
            for index, value in enumerate(row):
                kind = value["kind"]
                if kind == "null":
                    continue
                if index == 0 and not (
                    kind == "int" and -(2**63) <= int(value["value"]) < 2**63
                ):
                    return False
                if index == 1 and not (
                    (
                        route == "mysql_rows"
                        and kind == "int"
                        and value["value"] in ("0", "1")
                    )
                    or (
                        route != "mysql_rows"
                        and kind == "bool"
                        and type(value["value"]) is bool
                    )
                ):
                    return False
                if index == 2 and not (
                    kind == "float"
                    and math.isfinite(
                        struct.unpack(">d", bytes.fromhex(value["bits"]))[0]
                    )
                ):
                    return False
                if index == 3 and not (
                    kind == "text" and len(value["value"].encode("utf-8")) <= 256
                ):
                    return False
                if index == 4:
                    if route == "postgres_adbc":
                        if kind != "text" or not Decimal(value["value"]).is_finite():
                            return False
                    elif (
                        kind != "decimal"
                        or value["scale"] != 2
                        or abs(int(value["coefficient"])) >= 10**9
                    ):
                        return False
                if index == 5 and not (
                    kind == "datetime"
                    and datetime.fromisoformat(value["value"]).tzinfo is None
                ):
                    return False
                if index == 6 and not (
                    kind in ("uuid", "bytes")
                    and len(bytes.fromhex(value["value"])) == 16
                ):
                    return False
        return True
    except (KeyError, TypeError, ValueError, ArithmeticError, struct.error):
        return False


def verify_submission(observed, sql, parameters, route):
    if observed["sql"] != sql or observed["parameters"] != parameters:
        raise ValueError("statement/value correspondence")
    method = "cmd_stmt_execute" if route == "mysql_rows" else "execute"
    submits = [c for c in observed["api_calls"] if c["method"] == method]
    if route == "mysql_rows":
        wrappers = [c for c in observed["api_calls"] if c["method"] == "execute"]
        if (
            len(wrappers) != 1
            or wrappers[0]["values"] != parameters
            or wrappers[0]["sql"] is not None
        ):
            raise ValueError("native helper argument correspondence")
    if len(submits) != 1 or submits[0]["values"] != parameters:
        raise ValueError("native submitted values")
    preparations = [
        c for c in observed["api_calls"] if c["method"] == "cmd_stmt_prepare"
    ]
    if route == "mysql_rows":
        if len(preparations) != 1 or preparations[0]["sql"] != sql:
            raise ValueError("native submitted SQL")
    elif submits[0]["sql"] != sql:
        raise ValueError("submitted SQL")


def _mysql_blocking_session(found, session):
    return (
        len(found) == 1
        and found[0][0] == session
        and found[0][4] == "Execute"
        and found[0][6] == "User sleep"
        and found[0][7] == "SELECT SLEEP(5)"
    )


def _cancellation_matches(record, target):
    control = record["cancellation"]
    request = control["request"]
    if (
        request.get("execution_observed") is not True
        or not record["control_joined"]
        or request.get("session_id") != record["owned_session_id"]
        or control.get("error")
    ):
        return False
    if target == "mysql":
        # The frozen standalone SLEEP query reports interruption as 1, not an error.
        return (
            request.get("signal_sent") is True
            and control.get("signal") == "owned manager KILL QUERY returned"
            and not record.get("error")
            and record["actual"] == [[{"kind": "int", "value": "1"}]]
            and record["source_terminal"] == "native_rowset_eof"
            and record["statement_cleanup"] == "close_returned"
        )
    return control.get("signal") == "returned" and bool(record.get("error"))


def failure(exc, password):
    return {
        "type": type(exc).__name__,
        "sqlstate": getattr(exc, "sqlstate", None),
        "vendor_code": getattr(exc, "errno", None),
        "message": str(exc).replace(password, "<redacted>")[:4096],
    }


def rpc(event, **data):
    print(json.dumps({"event": event, **data}), flush=True)
    response = json.loads(sys.stdin.readline())
    if response.get("ack") != event:
        raise RuntimeError("manager/control acknowledgement mismatch")
    return response


class Driver:
    """One explicit experiment connection, with observations at actual API calls."""

    def __init__(self, config):
        self.config = config
        self.route = config["route"]
        self.target = config["target"]
        self.active = None
        self.controls = []
        self.connect()

    def connect(self):
        c = self.config
        if self.route == "postgres_adbc":
            import adbc_driver_postgresql.dbapi as api

            uri = (
                f"postgresql://pietto_query:{c['password']}@127.0.0.1:{c['port']}/phase66"
                "?sslmode=disable&gssencmode=disable&passfile=/dev/null&connect_timeout=10"
                "&options=-c%20statement_timeout%3D10000%20-c%20client_encoding%3DUTF8"
                "%20-c%20search_path%3Dpublic%20-c%20timezone%3DUTC"
            )
            self.connection = api.connect(uri, autocommit=True)
        elif self.route == "postgres_rows":
            import psycopg

            self.connection = psycopg.connect(
                host="127.0.0.1",
                port=c["port"],
                dbname="phase66",
                user="pietto_query",
                password=c["password"],
                autocommit=True,
                connect_timeout=10,
                sslmode="disable",
                gssencmode="disable",
                passfile="/dev/null",
                cursor_factory=psycopg.RawCursor,
                options="-c statement_timeout=10000 -c client_encoding=UTF8 -c search_path=public -c timezone=UTC",
            )
        else:
            import mysql.connector

            self.connection = mysql.connector.connect(
                host="127.0.0.1",
                port=c["port"],
                database="phase66",
                user="pietto_query",
                password=c["password"],
                connection_timeout=10,
                read_timeout=20,
                write_timeout=10,
                use_pure=True,
                autocommit=True,
                charset="utf8mb4",
                collation="utf8mb4_0900_bin",
                ssl_ca=c["ca"],
                ssl_verify_cert=True,
                ssl_verify_identity=False,
                tls_versions=["TLSv1.2", "TLSv1.3"],
                get_warnings=False,
                raise_on_warnings=False,
                consume_results=False,
            )

    def control(self, sql):
        options = (
            {"adbc_stmt_kwargs": {"adbc.postgresql.use_copy": False}}
            if self.route == "postgres_adbc"
            else {}
        )
        with self.connection.cursor(**options) as cursor:
            cursor.execute(sql)
        self.controls.append({"sql": sql, "returned": True})

    def query(self, sql, parameters=(), *, use_copy=True, early=False):
        record = {
            "sql": sql,
            "parameters": [scalar(x) for x in parameters],
            "api_calls": [],
            "actual": [],
            "raw_actual": [],
            "metadata": [],
            "pulls": [],
            "source_terminal": "not_observed",
            "statement_cleanup": "not_started",
            "stage": "execute",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "options": {"use_copy": use_copy, "batch_size_hint_bytes": 1}
            if self.route == "postgres_adbc"
            else {},
        }
        tick = time.monotonic()
        cursor = None
        previous = sys.getprofile()

        def observe(frame, event, result):
            if previous:
                previous(frame, event, result)
            if event != "call":
                return
            local, name = frame.f_locals, frame.f_code.co_name
            owner = local.get("self")
            if owner is cursor and name in ("execute", "_bind"):
                values = local.get("params", local.get("parameters", ()))
                if hasattr(values, "num_columns"):
                    values = tuple(
                        values.column(i)[0].as_py() for i in range(values.num_columns)
                    )
                record["api_calls"].append(
                    {
                        "method": name,
                        "sql": local.get("query", local.get("operation")),
                        "values": [scalar(v) for v in (values or ())],
                    }
                )
            elif owner is self.connection and name in (
                "cmd_stmt_prepare",
                "cmd_stmt_execute",
            ):
                record["api_calls"].append(
                    {
                        "method": name,
                        "sql": local["statement"].decode()
                        if name == "cmd_stmt_prepare"
                        else None,
                        "values": [scalar(v) for v in local.get("data", ())],
                        "statement_id": local.get("statement_id"),
                    }
                )

        native_rows = []
        try:
            if self.route == "mysql_rows":
                cursor = helper("_pietto_mysql_native_prepared").NativeStatement(
                    self.connection
                )
                self.active = cursor
                sys.setprofile(observe)
                cursor.prepare(sql)
                cursor.execute(tuple(parameters))
                record["metadata"] = cursor.record["result_metadata"]
                record["execute_returned_before_pull"] = True
                record["rowcount_observed"] = getattr(cursor, "rowcount", None)
                record["pgresult_rows_observed"] = getattr(
                    getattr(cursor, "pgresult", None), "ntuples", None
                )
                record["stage"] = "fetch"
                while True:
                    batch, terminal = self.connection.get_rows(
                        count=1, binary=True, columns=cursor.columns, read_timeout=20
                    )
                    record["pulls"].append(len(batch))
                    record["raw_actual"].extend(
                        [[scalar(v) for v in row] for row in batch]
                    )
                    decoded = [
                        tuple(
                            v.decode("utf-8")
                            if type(v) is bytes and column[8] != 63
                            else v
                            for v, column in zip(row, cursor.columns, strict=True)
                        )
                        for row in batch
                    ]
                    native_rows.extend(decoded)
                    if terminal is not None:
                        cursor.record["terminal"] = {
                            "kind": "rowset_eof",
                            "packet": terminal,
                        }
                        record["source_terminal"] = "native_rowset_eof"
                        break
                    if early:
                        break
                record["native"] = cursor.record
            else:
                options = (
                    {
                        "adbc_stmt_kwargs": {
                            "adbc.postgresql.use_copy": use_copy,
                            "adbc.postgresql.batch_size_hint_bytes": 1,
                        }
                    }
                    if self.route == "postgres_adbc"
                    else {}
                )
                cursor = self.connection.cursor(**options)
                self.active = cursor
                sys.setprofile(observe)
                if self.route == "postgres_adbc" and parameters:
                    import pyarrow as pa

                    types = (
                        [pa.int64(), pa.string(), pa.string(), pa.int32()]
                        if sql
                        == helper("_pietto_phase68_executor_cases").PARAMETER_SQL[
                            "postgres"
                        ]
                        else [
                            {
                                bool: pa.bool_(),
                                int: pa.int64(),
                                float: pa.float64(),
                                str: pa.string(),
                            }[type(v)]
                            for v in parameters
                        ]
                    )
                    bound = pa.record_batch(
                        [
                            pa.array([v], type=t)
                            for v, t in zip(parameters, types, strict=True)
                        ],
                        names=["p" + str(i + 1) for i in range(len(parameters))],
                    )
                    cursor.execute(sql, bound)
                elif self.route == "postgres_rows":
                    cursor.execute(sql, tuple(parameters), prepare=True)
                else:
                    cursor.execute(sql)
                record["metadata"] = [list(column) for column in cursor.description]
                if self.route == "postgres_adbc":
                    for column in record["metadata"]:
                        # ADBC reports Arrow DataType objects, not DB-API integer codes.
                        column[1] = str(column[1])
                record["execute_returned_before_pull"] = True
                record["rowcount_observed"] = getattr(cursor, "rowcount", None)
                record["pgresult_rows_observed"] = getattr(
                    getattr(cursor, "pgresult", None), "ntuples", None
                )
                record["stage"] = "fetch"
                if self.route == "postgres_adbc":
                    reader = cursor.fetch_record_batch()
                    record["arrow_schema"] = [
                        {
                            "ordinal": i,
                            "name": f.name,
                            "type": str(f.type),
                            "nullable": f.nullable,
                            "metadata": {
                                k.hex(): v.hex() for k, v in (f.metadata or {}).items()
                            },
                        }
                        for i, f in enumerate(reader.schema)
                    ]
                    try:
                        while True:
                            try:
                                batch = reader.read_next_batch()
                            except StopIteration:
                                record["source_terminal"] = "arrow_StopIteration"
                                break
                            record["pulls"].append(batch.num_rows)
                            native_rows.extend(
                                tuple(
                                    batch.column(i)[j].as_py()
                                    for i in range(batch.num_columns)
                                )
                                for j in range(batch.num_rows)
                            )
                            if early:
                                break
                    finally:
                        reader.close()
                else:
                    while True:
                        batch = cursor.fetchmany(1)
                        record["pulls"].append(len(batch))
                        if not batch:
                            record["source_terminal"] = "empty_fetchmany"
                            break
                        native_rows.extend(batch)
                        if early:
                            break
            record["stage"] = "returned"
        except Exception as exc:
            record["error"] = failure(exc, self.config["password"])
        finally:
            sys.setprofile(previous)
            record["actual"] = [[scalar(v) for v in row] for row in native_rows]
            if cursor is not None:
                try:
                    cursor.close()
                    record["statement_cleanup"] = "close_returned"
                except Exception as exc:
                    record["statement_cleanup"] = "failed"
                    record["cleanup_error"] = failure(exc, self.config["password"])
            record["elapsed_seconds"] = time.monotonic() - tick
        if len(native_rows) > 16 or len(json.dumps(record).encode()) > 1024 * 1024:
            raise ValueError("observation budget exceeded")
        return record, native_rows

    def close(self):
        self.connection.close()


def check_values(record, case, route):
    expected = helper("_pietto_phase68_executor_cases").expected_rows(case, route)

    def bag(rows):
        return Counter(json.dumps(x, sort_keys=True) for x in rows)

    return bag(record["actual"]) == bag(expected)


def worker(config, directory):
    cases = helper("_pietto_phase68_executor_cases")
    for name in (
        "_pietto_target_conformance_resources",
        "_pietto_target_conformance_observation",
        "_pietto_mysql_native_prepared",
    ):
        helper(name)
    driver = Driver(config)
    route, target = config["route"], config["target"]
    records = []

    def add(group, case, record, *, expected_error=False):
        status = "OBSERVED_SUPPORTED"
        if record.get("error") and not expected_error:
            status = (
                "OBSERVED_UNSUPPORTED"
                if record["error"]["type"] == "NotSupportedError"
                else "OBSERVED_MISMATCH"
            )
        elif case in (
            *cases.CASES["P02"],
            *cases.CASES["P03"],
            "multi_pull",
            "empty_eof",
            "compiled_nonempty",
            "compiled_empty",
        ) and not check_values(record, case, route):
            status = "OBSERVED_MISMATCH"
        if case == "stable_view" and (
            record["before"].get("error")
            or record["after"].get("error")
            or record["before"]["actual"] != [[{"kind": "int", "value": "10"}]]
            or record["after"]["actual"] != record["before"]["actual"]
        ):
            status = "OBSERVED_MISMATCH"
        if case == "serializable_readonly" and (
            record["read"].get("error")
            or record["read"]["actual"] != [[{"kind": "int", "value": "11"}]]
        ):
            status = "OBSERVED_MISMATCH"
        if case == "late_error" and not record.get("error"):
            status = "OBSERVED_MISMATCH"
        if case == "cancel_blocking_read":
            if record["cancellation"]["request"].get("execution_observed") is not True:
                status = "INCONCLUSIVE_ENVIRONMENT"
            elif not _cancellation_matches(record, target):
                status = "OBSERVED_MISMATCH"
        if case == "fixed_emission_values" and record["original_typed_rows"] != helper(
            "_pietto_target_conformance_cases"
        ).fixed_rows(target):
            status = "OBSERVED_MISMATCH"
        if group == "P03":
            record["domain_valid"] = scalar_domain(record, route)
            if not record["domain_valid"]:
                status = "OBSERVED_MISMATCH"
        records.append(
            {
                "route": route,
                "target": target,
                "group": group,
                "case": case,
                "status": status,
                "observation": record,
            }
        )

        print(
            json.dumps({"event": "observation", "record": records[-1]}, default=str),
            flush=True,
        )

    try:
        info_sql = (
            "SELECT current_user, current_database(), pg_backend_pid(), current_setting('transaction_isolation'), current_setting('transaction_read_only'), version()"
            if target == "postgres"
            else "SELECT CURRENT_USER(), DATABASE(), CONNECTION_ID(), @@transaction_isolation, @@transaction_read_only, VERSION()"
        )
        info, raw = driver.query(info_sql)
        if info.get("error"):
            raise RuntimeError("query-role identity failed")
        identity = {
            "python": sys.version,
            "executable": sys.executable,
            "distributions": {
                name: importlib.metadata.version(name) for name in cases.PINS
            },
            "origins": {},
            "native_libraries": {},
            "session": info,
            "server": config["server"],
            "image": config["image"],
            "endpoint": config["endpoint"],
        }
        modules = {
            "postgres_rows": ("psycopg",),
            "mysql_rows": ("mysql.connector",),
            "postgres_adbc": (
                "adbc_driver_manager",
                "adbc_driver_postgresql",
                "pyarrow",
            ),
        }[route]
        identity["module_paths"] = {
            name: str(Path(sys.modules[name].__file__).resolve()) for name in modules
        }
        for name in cases.PINS:
            dist = importlib.metadata.distribution(name)
            identity["origins"][name] = str(dist.locate_file(""))
        for line in Path("/proc/self/maps").read_text().splitlines():
            path = line.split()[-1]
            if (
                path.startswith("/")
                and ("site-packages" in path or "libpq" in path)
                and ".so" in path
            ):
                p = Path(path)
                if p.is_file():
                    identity["native_libraries"][path] = hashlib.sha256(
                        p.read_bytes()
                    ).hexdigest()
        add("P01", "identity", identity)
        for index, case in enumerate(cases.CASES["P02"]):
            rec, _ = driver.query(
                cases.PARAMETER_SQL[target], cases.parameters(target, index)
            )
            if route == "postgres_adbc":
                alternate, _ = driver.query(
                    cases.PARAMETER_SQL[target],
                    cases.parameters(target, index),
                    use_copy=False,
                )
                rec["documented_alternative"] = alternate
            add("P02", case, rec)
        for case, predicate in (
            ("carriers_populated", "n < 3"),
            ("carriers_empty", "n < 0"),
            ("carriers_all_null", "n = 3"),
        ):
            rec, _ = driver.query(
                cases.SCALAR_SELECT + " WHERE " + predicate + " ORDER BY n"
            )
            add("P03", case, rec)
        driver.control(
            "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"
            if target == "postgres"
            else "SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ"
        )
        if target == "mysql":
            driver.control("SET SESSION TRANSACTION READ ONLY")
            driver.control("START TRANSACTION READ ONLY")
        before, _ = driver.query("SELECT value FROM p68_view")
        mutation = rpc("mutate_view")
        after, _ = driver.query("SELECT value FROM p68_view")
        view_info, _ = driver.query(info_sql)
        driver.control("COMMIT")
        add(
            "P04",
            "stable_view",
            {
                "before": before,
                "mutation": mutation,
                "after": after,
                "session": view_info,
                "transaction_terminal": "COMMIT_returned",
                "controls": list(driver.controls),
            },
        )
        driver.control(
            "BEGIN ISOLATION LEVEL SERIALIZABLE READ ONLY"
            if target == "postgres"
            else "SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE"
        )
        if target == "mysql":
            driver.control("SET SESSION TRANSACTION READ ONLY")
            driver.control("START TRANSACTION READ ONLY")
        read, _ = driver.query("SELECT value FROM p68_view")
        serial_info, _ = driver.query(info_sql)
        driver.control("COMMIT")
        add(
            "P04",
            "serializable_readonly",
            {
                "read": read,
                "session": serial_info,
                "transaction_terminal": "COMMIT_returned",
                "controls": list(driver.controls),
                "claim": "normal read only; not all concurrent histories",
            },
        )
        for case, sql in (
            ("multi_pull", "SELECT n FROM p68_values ORDER BY n"),
            ("empty_eof", "SELECT n FROM p68_values WHERE n < 0"),
        ):
            rec, _ = driver.query(sql)
            add("P05", case, rec)
        sql = (
            "SELECT 10 / (n - 3) AS value FROM p68_values ORDER BY n"
            if target == "postgres"
            else "SELECT CASE WHEN n = 3 THEN JSON_EXTRACT('invalid', '$') ELSE CAST(n AS JSON) END AS value FROM p68_values ORDER BY n"
        )
        rec, _ = driver.query(sql)
        rec["fault"] = "real server expression; actual delivery/error stage reported"
        add("P05", "late_error", rec, expected_error=True)
        # An injected close error is separate from all natural driver terminals.
        rec, _ = driver.query("SELECT n FROM p68_values WHERE n < 0")
        try:
            raise RuntimeError("test-only cleanup injection")
        except RuntimeError as exc:
            rec["injected_cleanup"] = {"type": type(exc).__name__, "natural": False}
        add("P05", "cleanup_injection", rec)
        sys.path.insert(0, str(ROOT / "src"))
        product = helper("_pietto_phase67_result_product_probe")
        from pietto._project.project_result_contract import build_result_contract
        from pietto._project.project_result_binding import bind_producer

        checked, artifact = product.build_source(directory / "direct", target)
        contract = build_result_contract(checked)
        producer = bind_producer(contract, artifact, product.observations(target))
        for case in ("compiled_nonempty", "compiled_empty"):
            if case == "compiled_empty":
                rpc("empty_rows")
            rec, _ = driver.query(artifact.rendered.sql.decode("utf-8"))
            rec["plan_verified"] = checked.verified
            rec["producer_fields"] = len(producer.fields)
            rec["artifact_retained"] = producer.artifact is artifact
            add("P07", case, rec)
        emission = helper("_pietto_phase66_sql_emission_probe")
        helper("_pietto_target_conformance_cases")
        fixture = emission.fixed_fixture(target, "R_fixed_direct", "bind")
        checked, outcome = emission.build_case(
            directory / "fixed",
            fixture["source"],
            fixture["contract"],
            fixture["policy"],
        )
        from pietto._project.project_sql_emission import serialize_project_sql_emission

        data = serialize_project_sql_emission(outcome)
        document = emission.decode_public(data)
        args = emission.decoded_arguments(document)
        rec, raw = driver.query(document["sql"], args)
        rec["original_typed_rows"] = [
            [helper("_pietto_target_conformance_observation").scalar(v) for v in row]
            for row in raw
        ]
        rec["plan_verified"] = checked.verified
        rec["artifact_bytes"] = data.decode()
        rec["fixed_values_claim"] = (
            "separate current immutable emission artifact; not a reusable template"
        )
        add("P07", "fixed_emission_values", rec)
        add(
            "P07",
            "family_inventory",
            {
                "families": cases.FAMILIES,
                "current_producer": "SQLSelect/SQLColumn direct builtin field realizations",
                "current_obligation_owner": "project_single_match; executor fulfillment remains S07",
                "production_changed": False,
            },
        )
        rec, _ = driver.query("SELECT n FROM p68_values ORDER BY n", early=True)
        rec["delivery_complete"] = False
        driver.close()
        rec["connection_cleanup"] = "close_returned; exclusive connection discarded"
        add("P05", "early_close", rec)
        driver.connect()
        _, raw = driver.query(info_sql)
        session_id = raw[0][2]
        rpc("blocking_ready", session_id=session_id)
        cancellation = {}

        def cancel():
            response = json.loads(sys.stdin.readline())
            cancellation["request"] = response
            try:
                if response.get("ack") != "cancel_now":
                    raise RuntimeError("unregistered cancellation")
                if route == "postgres_rows":
                    driver.connection.cancel_safe(timeout=2)
                elif route == "postgres_adbc":
                    driver.active.adbc_cancel()
                cancellation["signal"] = (
                    "returned"
                    if target == "postgres"
                    else "owned manager KILL QUERY returned"
                    if response.get("signal_sent") is True
                    else "not_sent"
                )
            except Exception as exc:
                cancellation["error"] = failure(exc, config["password"])

        control = threading.Thread(target=cancel, name="p68-owned-cancel")
        control.start()
        rec, _ = driver.query(
            "SELECT pg_sleep(5)" if target == "postgres" else "SELECT SLEEP(5)"
        )
        control.join(6)
        if control.is_alive():
            raise RuntimeError("registered cancellation thread did not join")
        rec["cancellation"] = cancellation
        rec["control_joined"] = True
        rec["owned_session_id"] = session_id
        add("P06", "cancel_blocking_read", rec, expected_error=True)
    finally:
        driver.close()
    print(json.dumps({"event": "result", "records": records}, default=str), flush=True)


def setup(resources):
    cases = helper("_pietto_phase68_executor_cases")
    target = resources.target
    columns = (
        "v_int BIGINT, v_bool BOOLEAN, v_float DOUBLE PRECISION, v_text TEXT, v_decimal NUMERIC(9,2), v_time TIMESTAMP(6), v_uuid UUID"
        if target == "postgres"
        else "v_int BIGINT, v_bool TINYINT, v_float DOUBLE, v_text VARCHAR(64), v_decimal DECIMAL(9,2), v_time DATETIME(6), v_uuid BINARY(16)"
    )
    statements = [
        "CREATE TABLE p68_values (n INTEGER PRIMARY KEY, " + columns + ")",
        "CREATE TABLE p68_view (value INTEGER)",
        "INSERT INTO p68_view VALUES (10)",
        (
            'CREATE TABLE "rows" (id BIGINT NOT NULL, other BIGINT)'
            if target == "postgres"
            else "CREATE TABLE `rows` (id BIGINT NOT NULL, other BIGINT)"
        ),
    ]
    old_cases = helper("_pietto_target_conformance_cases")
    statements.extend(sql for sql, args in old_cases.native_setup(target) if not args)
    with resources.manager.cursor() as cursor:
        for sql in statements:
            cursor.execute(sql)
        for sql, secret in resources.role_statements():
            cursor.execute(sql)
    sql = (
        "INSERT INTO p68_values VALUES ("
        + (
            ", ".join("$" + str(i) for i in range(1, 9))
            if target == "postgres"
            else ", ".join("?" for _ in range(8))
        )
        + ")"
    )
    for row in cases.fixture_rows(target):
        if target == "postgres":
            with resources.manager.cursor() as cursor:
                cursor.execute(sql, row, prepare=True)
        else:
            statement = helper("_pietto_mysql_native_prepared").NativeStatement(
                resources.manager
            )
            try:
                statement.prepare(sql)
                statement.execute(row)
            finally:
                statement.close()


def _send_control(child, message):
    data = json.dumps(message).encode("utf-8") + b"\n"
    if len(data) > 4096:
        raise ValueError("control reply limit exceeded")
    if child.stdin.write(data) != len(data):
        raise RuntimeError("incomplete control reply")


def _pump_child(child, dispatch, *, initial=None, seconds=180):
    """S01 JSON-line control channel: one owner, explicit bytes, bounded reap."""
    if not 0 < seconds <= 180:
        raise ValueError("control deadline outside existing bound")
    assert child.stdout and child.stderr
    selector = selectors.DefaultSelector()
    pending, stderr = bytearray(), bytearray()
    total, terminal = 0, False
    deadline = time.monotonic() + seconds
    primary = None
    try:
        for stream in (child.stdout, child.stderr):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ)
        if initial is not None:
            _send_control(child, initial)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("registered child control timeout")
            for key, _ in selector.select(min(0.2, remaining)):
                try:
                    data = os.read(key.fd, 65536)
                except BlockingIOError:
                    continue
                if not data:
                    selector.unregister(key.fileobj)
                    if key.fileobj is child.stdout:
                        if pending:
                            raise RuntimeError("incomplete control frame at EOF")
                        if not terminal:
                            raise RuntimeError("registered child missing terminal")
                    continue
                if key.fileobj is child.stderr:
                    if len(stderr) + len(data) > 4096:
                        raise RuntimeError("child stderr limit exceeded")
                    stderr.extend(data)
                    continue
                total += len(data)
                if total > 32 * 1024 * 1024:
                    raise RuntimeError("child control stream limit exceeded")
                pending.extend(data)
                # Consume every complete frame from this read before any select.
                while b"\n" in pending:
                    frame, _, pending = pending.partition(b"\n")
                    if len(frame) > 16 * 1024 * 1024:
                        raise RuntimeError("child control frame limit exceeded")
                    if terminal:
                        raise RuntimeError("control message after terminal")
                    message = json.loads(frame.decode("utf-8"))
                    if (
                        type(message) is not dict
                        or type(message.get("event")) is not str
                    ):
                        raise ValueError("invalid child control message")
                    dispatch(message)
                    terminal = message["event"] == "result"
                if len(pending) > 16 * 1024 * 1024:
                    raise RuntimeError("child control frame limit exceeded")
        # Both pipes have been drained; exit is still a separate required fact.
        child.wait(timeout=min(10, max(0.001, deadline - time.monotonic())))
        if child.returncode:
            raise RuntimeError("registered child failed")
        return bytes(stderr)
    except BaseException as error:
        primary = error
        error.add_note("captured child stderr bytes: " + str(len(stderr)))
        raise
    finally:
        selector.close()
        try:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
        except BaseException as cleanup:
            if primary is None:
                raise
            primary.add_note("owned child reap failure: " + type(cleanup).__name__)


def run_child(resources, route, directory, record_observation):
    with resources.manager.cursor() as cursor:
        cursor.execute("UPDATE p68_view SET value = 10")
        cursor.execute(
            'DELETE FROM "rows"'
            if resources.target == "postgres"
            else "DELETE FROM `rows`"
        )
        cursor.execute(
            'INSERT INTO "rows" VALUES (1,NULL),(1,NULL),(2,3)'
            if resources.target == "postgres"
            else "INSERT INTO `rows` VALUES (1,NULL),(1,NULL),(2,3)"
        )
        cursor.execute("SELECT version()")
        server = cursor.fetchone()[0]
    config = {
        "route": route,
        "target": resources.target,
        "port": resources.port,
        "password": resources._passwords[1],
        "ca": str(resources.ca_path),
        "server": server,
        "image": resources.runtime_image_id,
        "endpoint": resources.endpoint_observation,
    }
    env = helper("_pietto_target_conformance_resources").clean_environment()
    with subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "_worker",
            "--directory",
            str(directory),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        env=env,
    ) as child:
        result = None

        def dispatch(message):
            nonlocal result
            event = message["event"]
            if event == "observation":
                record_observation(message["record"])
                return
            if event == "result":
                result = message["records"]
                return
            if event == "worker_error":
                raise RuntimeError(json.dumps(message))
            if event in ("mutate_view", "empty_rows"):
                with resources.manager.cursor() as cursor:
                    cursor.execute(
                        "UPDATE p68_view SET value = 11"
                        if event == "mutate_view"
                        else (
                            'DELETE FROM "rows"'
                            if resources.target == "postgres"
                            else "DELETE FROM `rows`"
                        )
                    )
                response = {"ack": event}
                if event == "mutate_view":
                    with resources.manager.cursor() as cursor:
                        cursor.execute("SELECT value FROM p68_view")
                        response["manager_actual"] = [
                            [scalar(v) for v in row] for row in cursor.fetchall()
                        ]
                _send_control(child, response)
            elif event == "blocking_ready":
                session = message["session_id"]
                if type(session) is not int or session <= 0:
                    raise ValueError("invalid owned session")
                _send_control(child, {"ack": event})
                seen = False
                signal_sent = False
                observed_thread = None
                deadline = time.monotonic() + 4
                while time.monotonic() < deadline:
                    with resources.manager.cursor() as cursor:
                        if resources.target == "postgres":
                            cursor.execute(
                                "SELECT state, wait_event, query FROM pg_stat_activity WHERE pid = $1",
                                (session,),
                            )
                            found = cursor.fetchone()
                            seen = (
                                found is not None
                                and found[0] == "active"
                                and found[1] == "PgSleep"
                                and "pg_sleep(5)" in found[2]
                            )
                        else:
                            cursor.execute("SHOW PROCESSLIST")
                            found = [r for r in cursor.fetchall() if r[0] == session]
                            observed_thread = [
                                {
                                    "session_id": row[0],
                                    "command": row[4],
                                    "state": row[6],
                                    "query": row[7],
                                }
                                for row in found
                            ]
                            seen = _mysql_blocking_session(found, session)
                    if seen:
                        break
                    time.sleep(0.05)
                if resources.target == "mysql" and seen:
                    with resources.manager.cursor() as cursor:
                        cursor.execute("KILL QUERY " + str(session))
                    signal_sent = True
                _send_control(
                    child,
                    {
                        "ack": "cancel_now",
                        "execution_observed": seen,
                        "session_id": session,
                        "signal_sent": signal_sent,
                        "observed_thread": observed_thread,
                    },
                )
            else:
                raise ValueError("unregistered child request")

        stderr = _pump_child(child, dispatch, initial=config)
        if stderr:
            resources.event(
                "premise_child_stderr",
                route=route,
                message=resources.without_secrets(stderr.decode("utf-8")),
            )
        return result


def run(directory, ledger):
    cases = helper("_pietto_phase68_executor_cases")
    for name in (
        "_pietto_target_conformance_resources",
        "_pietto_target_conformance_observation",
        "_pietto_mysql_native_prepared",
    ):
        helper(name)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    runtime = runtime_identity()
    (directory / (PREFIX + "runtime-context.json")).write_text(
        json.dumps(runtime, indent=2) + "\n"
    )
    report = {
        "format": FORMAT,
        "input_identity": input_identity(),
        "records": [],
        "resources": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "location": "local",
        "assessment": "HOLD",
    }
    import sqlite3
    import _sqlite3

    with sqlite3.connect(":memory:") as db:
        report["sqlite_inventory"] = {
            "version": sqlite3.sqlite_version,
            "source_id": db.execute("select sqlite_source_id()").fetchone()[0],
            "module": getattr(_sqlite3, "__file__", "builtin in " + sys.executable),
            "durability_qualified": False,
        }
    try:
        for target in ("postgres", "mysql"):
            state = json.loads(ledger.read_text())
            counter = state["budgets"]["db_lifecycle_starts"]
            if counter["used"] >= counter["limit"]:
                raise RuntimeError("DB lifecycle budget exhausted")
            counter["used"] += 1
            ledger.write_text(json.dumps(state, indent=2) + "\n")
            with tempfile.TemporaryDirectory(prefix=PREFIX + target + "-") as temporary:
                work = Path(temporary)
                resources = helper("_pietto_target_conformance_resources").Resources(
                    target, pins["targets"][target], work
                )
                try:
                    resources.acquire()
                    setup(resources)
                    for route in (
                        (cases.ROUTES[0], cases.ROUTES[2])
                        if target == "postgres"
                        else (cases.ROUTES[1],)
                    ):
                        child_dir = work / route
                        child_dir.mkdir()

                        def record_observation(value):
                            report["records"].append(value)
                            (directory / (PREFIX + "report.json")).write_text(
                                json.dumps(report, indent=2, default=str) + "\n"
                            )

                        completed = run_child(
                            resources, route, child_dir, record_observation
                        )
                        if completed != [
                            r for r in report["records"] if r["route"] == route
                        ]:
                            raise ValueError("child observation collection mismatch")
                        (directory / (PREFIX + "report.json")).write_text(
                            json.dumps(report, indent=2, default=str) + "\n"
                        )
                finally:
                    cleanup = resources.cleanup()
                    report["resources"].append(
                        {
                            "target": target,
                            "cleanup": cleanup,
                            "events": resources.events,
                        }
                    )
                    if cleanup["status"] != "success":
                        raise RuntimeError("owned resource cleanup incomplete")
        report["records"].sort(
            key=lambda r: cases.DENOMINATOR.index((r["route"], r["group"], r["case"]))
        )
        report["assessment"] = (
            "HOLD"
            if any(r["status"] == "INCONCLUSIVE_ENVIRONMENT" for r in report["records"])
            else "PRODUCT_GATE_BLOCKED_REPLAN"
            if any(r["status"] != "OBSERVED_SUPPORTED" for r in report["records"])
            else "READY_FOR_SLICE02_EXPERIMENT"
        )
    finally:
        report["ended_at"] = datetime.now(timezone.utc).isoformat()
        (directory / (PREFIX + "report.json")).write_text(
            json.dumps(report, indent=2, default=str) + "\n"
        )
    verify_report(report, input_identity(), runtime)
    if report["assessment"] == "HOLD":
        raise RuntimeError("mandatory experiment inconclusive")


def verify_report(report, expected_inputs, expected_runtime):
    """Independent data-only acceptance; never trusts a report's summary flag."""
    cases = helper("_pietto_phase68_executor_cases")
    if (
        report.get("format") != FORMAT
        or report.get("input_identity") != expected_inputs
        or report.get("location") != "local"
    ):
        raise ValueError("report source context")
    rows = report["records"]
    if tuple((r["route"], r["group"], r["case"]) for r in rows) != cases.DENOMINATOR:
        raise ValueError("complete route/case denominator")
    for row in rows:
        route, case, observed, status = (
            row["route"],
            row["case"],
            row["observation"],
            row["status"],
        )
        target = "mysql" if route == "mysql_rows" else "postgres"
        if row["target"] != target or status not in STATUSES:
            raise ValueError("target/status")
        if status == "INCONCLUSIVE_ENVIRONMENT":
            continue
        if (
            status == "OBSERVED_UNSUPPORTED"
            and observed.get("error", {}).get("type") != "NotSupportedError"
        ):
            raise ValueError("unsupported observation lacks actual driver error")
        if case == "identity":
            if (
                observed["distributions"] != cases.PINS
                or observed["distributions"] != expected_runtime["versions"]
                or observed["python"] != expected_runtime["python"]
                or observed["executable"] != expected_runtime["executable"]
                or observed["origins"] != expected_runtime["origins"]
            ):
                raise ValueError("dependency identity")
            modules = {
                "postgres_rows": ("psycopg",),
                "mysql_rows": ("mysql.connector",),
                "postgres_adbc": (
                    "adbc_driver_manager",
                    "adbc_driver_postgresql",
                    "pyarrow",
                ),
            }[route]
            if (
                observed["module_paths"]
                != {name: expected_runtime["modules"][name] for name in modules}
                or not observed["native_libraries"]
                or any(
                    expected_runtime["libraries"].get(name) != digest
                    for name, digest in observed["native_libraries"].items()
                )
            ):
                raise ValueError("module/native library identity")
            if not observed["session"]["actual"][0][0]["value"].startswith(
                "pietto_query"
            ):
                raise ValueError("query role")
        if case in cases.CASES["P02"]:
            index = cases.CASES["P02"].index(case)
            verify_submission(
                observed,
                cases.PARAMETER_SQL[target],
                [scalar(x) for x in cases.parameters(target, index)],
                route,
            )
        if status == "OBSERVED_UNSUPPORTED":
            continue
        if case in (
            *cases.CASES["P02"],
            *cases.CASES["P03"],
            "multi_pull",
            "empty_eof",
            "compiled_nonempty",
            "compiled_empty",
        ):
            match = check_values(observed, case, route)
            if row["group"] == "P03":
                domain = scalar_domain(observed, route)
                if observed["domain_valid"] is not domain:
                    raise ValueError("carrier/domain claim")
                match = match and domain
            if (status == "OBSERVED_SUPPORTED") != (
                match and not observed.get("error")
            ):
                raise ValueError("original value/status mismatch")
            if status == "OBSERVED_SUPPORTED" and (
                observed["source_terminal"] == "not_observed"
                or observed["statement_cleanup"] != "close_returned"
            ):
                raise ValueError("incomplete normal terminal")
        if case.startswith("carriers_") and [
            c[0] for c in observed["metadata"]
        ] != list(cases.LABELS):
            raise ValueError("positional metadata")
        if case in ("stable_view", "serializable_readonly"):
            actual = observed["session"]["actual"]
            isolation = "repeatable read" if case == "stable_view" else "serializable"
            expected_isolation = (
                isolation
                if target == "postgres"
                else isolation.upper().replace(" ", "-")
            )
            readonly = (
                {"kind": "text", "value": "on"}
                if target == "postgres"
                else {"kind": "int", "value": "1"}
            )
            if (
                len(actual) != 1
                or len(actual[0]) != 6
                or not actual[0][0]["value"].startswith("pietto_query")
                or actual[0][3] != {"kind": "text", "value": expected_isolation}
                or actual[0][4] != readonly
            ):
                raise ValueError("actual transaction role/isolation/readonly")
            if (
                observed["transaction_terminal"] != "COMMIT_returned"
                or observed["controls"][-1] != {"sql": "COMMIT", "returned": True}
                or not all(c["returned"] is True for c in observed["controls"])
            ):
                raise ValueError("transaction control terminal")
            if case == "stable_view":
                expected = [[{"kind": "int", "value": "10"}]]
                if observed["mutation"]["manager_actual"] != [
                    [{"kind": "int", "value": "11"}]
                ]:
                    raise ValueError("controlled source mutation not observed")
                if status == "OBSERVED_SUPPORTED" and (
                    observed["before"]["actual"] != expected
                    or observed["after"]["actual"] != expected
                ):
                    raise ValueError("stable source view")
            elif status == "OBSERVED_SUPPORTED" and observed["read"]["actual"] != [
                [{"kind": "int", "value": "11"}]
            ]:
                raise ValueError("serializable normal read")
        if (
            case == "late_error"
            and status == "OBSERVED_SUPPORTED"
            and not observed.get("error")
        ):
            raise ValueError("real error not observed")
        if case == "early_close" and observed["delivery_complete"] is not False:
            raise ValueError("early close promoted to completion")
        if case == "cleanup_injection" and observed["injected_cleanup"] != {
            "type": "RuntimeError",
            "natural": False,
        }:
            raise ValueError("cleanup injection misclassified")
        if case == "cancel_blocking_read":
            if (
                observed["cancellation"]["request"].get("execution_observed")
                is not True
            ):
                raise ValueError("cancellation terminal/synchronization")
            if (status == "OBSERVED_SUPPORTED") != _cancellation_matches(
                observed, target
            ):
                raise ValueError("cancellation terminal/synchronization")
        if case.startswith("compiled_") and (
            not observed["plan_verified"]
            or observed["producer_fields"] != 2
            or not observed["artifact_retained"]
        ):
            raise ValueError("compiled/producer correspondence")
        if case == "fixed_emission_values":
            literal = helper("_pietto_target_conformance_cases").fixed_rows(target)
            emission = helper("_pietto_phase66_sql_emission_probe")
            document = emission.decode_public(observed["artifact_bytes"].encode())
            verify_submission(
                observed,
                document["sql"],
                [scalar(v) for v in emission.decoded_arguments(document)],
                route,
            )
            if (
                document["target"]["family"] != target
                or (
                    (status == "OBSERVED_SUPPORTED")
                    != (observed["original_typed_rows"] == literal)
                )
                or not observed["plan_verified"]
            ):
                raise ValueError("fixed emission original values")
        if case == "family_inventory" and (
            observed["families"] != cases.FAMILIES
            or observed["production_changed"] is not False
        ):
            raise ValueError("query family obligations")
        if (
            status == "OBSERVED_SUPPORTED"
            and observed.get("error")
            and case not in ("late_error", "cancel_blocking_read")
        ):
            raise ValueError("error promoted to supported")
    assessment = (
        "HOLD"
        if any(r["status"] == "INCONCLUSIVE_ENVIRONMENT" for r in rows)
        else "PRODUCT_GATE_BLOCKED_REPLAN"
        if any(r["status"] != "OBSERVED_SUPPORTED" for r in rows)
        else "READY_FOR_SLICE02_EXPERIMENT"
    )
    if report["assessment"] != assessment:
        raise ValueError("false next-stage assessment")
    if [r["target"] for r in report["resources"]] != ["postgres", "mysql"] or any(
        r["cleanup"]["status"] != "success" for r in report["resources"]
    ):
        raise ValueError("owned resource closure")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "check", "_worker"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path)
    args = parser.parse_args()
    if args.action == "_worker":
        config = json.loads(sys.stdin.readline())
        try:
            worker(config, args.directory)
        except Exception as exc:
            import traceback

            frames = traceback.extract_tb(exc.__traceback__)
            print(
                json.dumps(
                    {
                        "event": "worker_error",
                        "failure": failure(exc, config["password"]),
                        "frames": [
                            {"file": f.filename, "line": f.lineno, "name": f.name}
                            for f in frames
                        ],
                    }
                ),
                flush=True,
            )
            return 1
    elif args.action == "run":
        if args.ledger is None or args.ledger.name != PREFIX + "ledger.json":
            parser.error("the one S01 ledger is required")
        run(args.directory, args.ledger)
    else:
        verify_report(
            json.loads((args.directory / (PREFIX + "report.json")).read_text()),
            input_identity(),
            json.loads(
                (args.directory / (PREFIX + "runtime-context.json")).read_text()
            ),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
