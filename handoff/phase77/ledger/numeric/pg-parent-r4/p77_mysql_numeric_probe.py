"""C77-01/C77-02 raw target probe; no Pietto product qualification."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


MIN_INT = -(2**63)
MAX_INT = 2**63 - 1
OVERFLOW = {"errno": 1690, "sqlstate": "22003"}
TARGET_VERSION = {"postgres": 180006, "mysql": "8.4.12"}
MYSQL_RELAY = {
    "profile": "mysql-none-exec-stdio-v1",
    "relay_sha256": "c5aab62143c0c51cf7e9daad8f3df2e242212dd8327588fb4f8a546a1f5bf012",
    "relay_command": "docker container exec -i /bin/bash -c fixed-3306-forward",
    "target_host": "127.0.0.1",
    "target_port": 3306,
}
POSTGRES_RELAY = {
    "profile": "postgres-none-exec-stdio-v1",
    "relay_sha256": "dd3cb68067887ee80acd5801c4ea3c9f1b701daef89a3a11d2e4dff329b55754",
    "relay_command": "docker container exec -i /bin/bash -c fixed-5432-forward",
    "target_host": "127.0.0.1",
    "target_port": 5432,
}


@dataclass(frozen=True)
class Expected:
    name: str
    values: tuple[int | None, ...] | None
    logical_overflow: bool
    engine_observation: str


ARITHMETIC = (
    Expected("safe_plus", (-4, 9, None), False, "must_success"),
    Expected("safe_minus", (4, -9, None), False, "must_success"),
    Expected("safe_multiply", (-21, 0, 9223372030926249001, None), False, "must_success"),
    Expected("min_times_one", (MIN_INT,), False, "observe"),
    Expected("safe_unary", (-7, -7, None), False, "must_success"),
    Expected("over_plus", None, True, "must_1690_22003"),
    Expected("over_minus", None, True, "must_1690_22003"),
    Expected("over_multiply", None, True, "must_1690_22003"),
    Expected("over_negate", None, True, "must_1690_22003"),
    Expected("over_abs", None, True, "must_1690_22003"),
)
SUMS = (
    Expected("empty", (None,), False, "must_success"),
    Expected("all_null", (None,), False, "must_success"),
    Expected("safe", (0,), False, "must_success"),
    Expected("minimum", (MIN_INT,), False, "must_success"),
    Expected("maximum", (MAX_INT,), False, "must_success"),
    Expected("over_positive", None, True, "must_1690_22003"),
    Expected("over_negative", None, True, "must_1690_22003"),
    Expected("group_safe", (0,), False, "must_success"),
    Expected("group_all_null", (None,), False, "must_success"),
    Expected("group_overflow", None, True, "must_1690_22003"),
)

SUM_GUARD = """CASE
  WHEN SUM(value) > 9223372036854775807
    THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED)
  WHEN SUM(value) < -9223372036854775808
    THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED)
  ELSE CAST(SUM(value) AS SIGNED)
END"""


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    return value


def _canonical_plan_bytes(plan: dict[str, object]) -> bytes:
    return (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _metadata(description: object) -> list[list[object]] | None:
    if description is None:
        return None
    return [list(column) for column in description]


def _warnings(cursor: Any, engine: str) -> list[list[object]]:
    if engine == "postgres":
        # Psycopg's notices are connection-level asynchronous observations;
        # this primitive probe records no fabricated statement-local warning.
        return []
    cursor.execute("SHOW WARNINGS")
    return [[_json_value(value) for value in row] for row in cursor.fetchall()]


def observe(cursor: Any, name: str, sql: str, parameters: tuple[object, ...] = (), *, engine: str = "mysql") -> dict[str, object]:
    record: dict[str, object] = {"name": name, "sql": sql, "parameters": list(parameters)}
    try:
        cursor.execute(sql, parameters)
        description = _metadata(cursor.description)
        rows = [[_json_value(value) for value in row] for row in cursor.fetchall()] if description else []
        record.update(kind="success", metadata=description, rows=rows, warnings=[], warnings_error=False)
    except Exception as error:
        record.update(
            kind="error",
            errno=getattr(error, "errno", None),
            sqlstate=getattr(error, "sqlstate", None),
            message=str(error),
            rows=[],
            metadata=None,
            warnings=[],
            warnings_error=False,
        )
        try:
            record["warnings"] = _warnings(cursor, engine)
        except Exception as warning_error:
            record["warnings_error"] = type(warning_error).__name__
        return record
    try:
        record["warnings"] = _warnings(cursor, engine)
    except Exception as warning_error:
        record["warnings_error"] = type(warning_error).__name__
    return record


def _complete_warnings(record: dict[str, object]) -> bool:
    return isinstance(record.get("warnings"), list) and record.get("warnings_error") is False


def _exact_success_rows(record: dict[str, object], expected: object, name: str) -> None:
    if record.get("kind") != "success" or record.get("warnings") or not _complete_warnings(record) or not isinstance(record.get("metadata"), list):
        raise ValueError(f"{name}: successful receipt is incomplete")
    if record.get("rows") != expected:
        raise ValueError(f"{name}: rows differ from the frozen expectation")


def _expect(record: dict[str, object], expected: Expected) -> None:
    if expected.engine_observation == "observe":
        if record.get("kind") == "success":
            _expect(record, Expected(expected.name, expected.values, False, "must_success"))
            return
        if record.get("kind") == "error":
            _error_receipt(record, expected.name)
            return
        raise ValueError(f"{expected.name}: record must preserve one engine terminal")
    if expected.engine_observation == "must_1690_22003":
        if record.get("kind") != "error" or {key: record.get(key) for key in OVERFLOW} != OVERFLOW:
            raise ValueError(f"{expected.name}: expected native 1690/22003 terminal")
        _error_receipt(record, expected.name)
        return
    if expected.engine_observation == "must_22003":
        if record.get("kind") != "error" or record.get("sqlstate") != "22003":
            raise ValueError(f"{expected.name}: expected SQLSTATE 22003 terminal")
        _error_receipt(record, expected.name)
        return
    if record.get("kind") != "success":
        raise ValueError(f"{expected.name}: expected successful primitive")
    if record.get("warnings") or not _complete_warnings(record):
        raise ValueError(f"{expected.name}: warning-only conversion is not accepted")
    metadata = record.get("metadata")
    rows = record.get("rows")
    if not isinstance(metadata, list) or len(metadata) != 1 or not isinstance(rows, list):
        raise ValueError(f"{expected.name}: success requires one result column and row receipt")
    column = metadata[0]
    if (
        not isinstance(column, list)
        or len(column) < 8
        or column[1] != 8
        or not isinstance(column[7], int)
        or column[7] & 32
    ):
        raise ValueError(f"{expected.name}: success requires signed BIGINT metadata")
    actual = tuple(row[0] for row in rows)
    if actual != expected.values:
        raise ValueError(f"{expected.name}: unexpected values {actual!r}")


def _error_receipt(record: dict[str, object], name: str) -> None:
    if record.get("rows") != [] or record.get("metadata") is not None:
        raise ValueError(f"{name}: error cannot carry rows or result metadata")
    if not _complete_warnings(record):
        raise ValueError(f"{name}: error requires a complete warnings receipt")
    if not {"errno", "sqlstate", "message"} <= record.keys() or not isinstance(record.get("message"), str) or not record["message"]:
        raise ValueError(f"{name}: error requires complete native terminal fields")


def self_check() -> None:
    good = {
        "kind": "success",
        "metadata": [["value", 8, None, None, None, None, True, 0, 63]],
        "rows": [[0]],
        "warnings": [],
        "warnings_error": False,
    }


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _connect(endpoint: dict[str, object]):
    engine = endpoint.get("engine")
    required = ("host", "port", "user", "database", "password_env")
    if engine not in {"postgres", "mysql"} or any(not endpoint.get(key) for key in required):
        raise ValueError("endpoint requires engine, host, port, user, database and password_env")
    if endpoint["host"] not in {"127.0.0.1", "::1"} or type(endpoint["port"]) is not int or not 1 <= endpoint["port"] <= 65535:
        raise ValueError("endpoint must be an owned loopback listener")
    if engine == "mysql":
        if endpoint.get("relay_contract") != MYSQL_RELAY or endpoint.get("host") != "127.0.0.1" or endpoint.get("database") != "pietto_numeric_probe" or endpoint.get("user") != "pietto_numeric_probe" or endpoint.get("verify_identity") is not True or endpoint.get("loopback_tls_exception") is not False:
            raise ValueError("endpoint is not the reviewed MySQL literal-none relay")
    elif endpoint.get("relay_contract") != POSTGRES_RELAY or endpoint.get("host") != "127.0.0.1" or endpoint.get("database") != "pietto_numeric_probe" or endpoint.get("user") != "pietto_numeric_probe" or endpoint.get("verify_identity") is not True or endpoint.get("loopback_tls_exception") is not False:
        raise ValueError("endpoint is not the reviewed PostgreSQL literal-none relay")
    password_env = endpoint["password_env"]
    if not isinstance(password_env, str) or password_env not in os.environ:
        raise ValueError("endpoint password environment variable is unavailable")
    common = {
        "host": endpoint["host"],
        "port": endpoint["port"],
        "user": endpoint["user"],
        "password": os.environ[password_env],
    }
    if engine == "mysql":
        import mysql.connector

        kwargs = common | {"database": endpoint["database"]}
        if endpoint.get("ca_file"):
            kwargs |= {
                "ssl_ca": endpoint["ca_file"],
                "ssl_verify_cert": True,
                "ssl_verify_identity": bool(endpoint.get("verify_identity", True)),
            }
        return mysql.connector.connect(**kwargs)
    import psycopg

    kwargs = common | {"dbname": endpoint["database"]}
    if endpoint.get("ca_file"):
        kwargs |= {"sslrootcert": endpoint["ca_file"], "sslmode": "verify-full"}
    return psycopg.connect(**kwargs)


def _control_record(record: dict[str, object], name: str) -> None:
    if record.get("kind") != "success" or record.get("warnings") or not _complete_warnings(record):
        raise ValueError(f"{name}: setup/seed statement did not finish cleanly")


def _expect_target(engine: str, record: dict[str, object], classification: str, values: object, name: str, result_shape: str = "scalar") -> None:
    if classification == "observe":
        _expect(record, Expected(name, tuple(values) if isinstance(values, list) else None, False, "observe"))
        return
    if classification.startswith("observation"):
        record["frozen_oracle_values"] = values
        if record.get("kind") == "error":
            _error_receipt(record, name)
            record["frozen_oracle_match"] = False if values is not None else None
        elif record.get("kind") != "success" or not _complete_warnings(record) or not isinstance(record.get("metadata"), list) or not isinstance(record.get("rows"), list):
            raise ValueError(f"{name}: incomplete observation receipt")
        elif values is not None and result_shape == "scalar":
            record["frozen_oracle_match"] = record["rows"] == [[value] for value in values]
        elif result_shape == "grouped":
            metadata = record["metadata"]
            rows = record["rows"]
            if len(metadata) != 2 or any(not isinstance(row, list) or len(row) != 2 or row[0] != 1 for row in rows):
                raise ValueError(f"{name}: grouped observation requires key/value rows")
            key = metadata[0]
            if engine == "mysql":
                if not (isinstance(key, list) and len(key) >= 8 and key[1] == 3 and isinstance(key[7], int) and not key[7] & 32):
                    raise ValueError(f"{name}: MySQL grouped observation has no signed INT key metadata")
            elif not (isinstance(key, list) and len(key) >= 2 and key[1] == 23):
                raise ValueError(f"{name}: PostgreSQL grouped observation has no int4 key metadata")
        else:
            record["frozen_oracle_match"] = None
        return
    expected = Expected(name, tuple(values) if isinstance(values, list) else None, classification != "must_success", classification)
    if result_shape == "grouped" and classification == "must_success":
        metadata = record.get("metadata")
        if record.get("kind") != "success" or record.get("warnings") or not _complete_warnings(record) or not isinstance(metadata, list) or len(metadata) != 2:
            raise ValueError(f"{name}: grouped success receipt is incomplete")
        if engine == "mysql":
            key, aggregate = metadata
            if not (isinstance(key, list) and len(key) >= 8 and key[1] == 3 and isinstance(key[7], int) and not key[7] & 32):
                raise ValueError(f"{name}: MySQL group key metadata is not signed INT")
            if not (isinstance(aggregate, list) and len(aggregate) >= 8 and aggregate[1] == 8 and isinstance(aggregate[7], int) and not aggregate[7] & 32):
                raise ValueError(f"{name}: MySQL aggregate metadata is not signed BIGINT")
        else:
            if not all(isinstance(column, list) and len(column) >= 2 for column in metadata) or [metadata[0][1], metadata[1][1]] != [23, 20]:
                raise ValueError(f"{name}: PostgreSQL grouped result requires int4/int8 metadata")
        if record.get("rows") != values:
            raise ValueError(f"{name}: grouped rows differ from the frozen oracle")
        return
    if engine == "mysql":
        _expect(record, expected)
        return
    if classification == "must_22003":
        _expect(record, expected)
        return
    metadata = record.get("metadata")
    if record.get("kind") != "success" or record.get("warnings") or not _complete_warnings(record) or not isinstance(metadata, list):
        raise ValueError(f"{name}: PostgreSQL success receipt is incomplete")
    if len(metadata) != 1 or not isinstance(metadata[0], list) or len(metadata[0]) < 2 or metadata[0][1] != 20:
        raise ValueError(f"{name}: PostgreSQL success requires an int8 result metadata record")
    if tuple(row[0] for row in record.get("rows", ())) != expected.values:
        raise ValueError(f"{name}: unexpected PostgreSQL values")


def _observe_probe(cursor: Any, engine: str, index: int, sql: str, parameters: tuple[object, ...]) -> dict[str, object]:
    if engine != "postgres":
        return observe(cursor, "probe:%d" % index, sql, parameters, engine=engine)
    savepoint = "p77_numeric_probe_%d" % index
    cursor.execute("SAVEPOINT " + savepoint)
    record = observe(cursor, "probe:%d" % index, sql, parameters, engine=engine)
    if record.get("kind") == "error":
        cursor.execute("ROLLBACK TO SAVEPOINT " + savepoint)
    cursor.execute("RELEASE SAVEPOINT " + savepoint)
    return record


def _append_probe_then_judge(
    records: list[dict[str, object]],
    engine: str,
    record: dict[str, object],
    classification: str,
    values: object,
    name: str,
    result_shape: str,
) -> None:
    """Keep a raw probe terminal even when its frozen oracle rejects it."""
    records.append(record)
    _expect_target(engine, record, classification, values, name, result_shape)


def run_plan(plan_path: Path, endpoint_path: Path, receipt_path: Path) -> None:
    plan = _load_json(plan_path)
    endpoint = _load_json(endpoint_path)
    if plan.get("artifact") != "pietto.phase77.numeric_primitive_probe.v2" or plan != manifest():
        raise ValueError("unexpected probe plan artifact")
    plan_sha256 = hashlib.sha256(_canonical_plan_bytes(plan)).hexdigest()
    engine = endpoint.get("engine")
    plans = plan.get("plans")
    if not isinstance(engine, str) or not isinstance(plans, dict) or not isinstance(plans.get(engine), dict):
        raise ValueError("endpoint engine has no frozen plan")
    target = plans[engine]
    records: list[dict[str, object]] = []
    terminal: dict[str, object] = {"kind": "success"}
    try:
        connection = _connect(endpoint)
        try:
            cursor = connection.cursor()
            try:
                version = observe(cursor, target["target_version"]["name"], target["target_version"]["sql"], engine=engine)
                records.append(version)
                _exact_success_rows(version, target["target_version"]["expected"], "target version")
                for index, sql in enumerate(target["setup"]):
                    record = observe(cursor, "setup:%d" % index, sql, engine=engine)
                    records.append(record)
                    _control_record(record, "setup:%d" % index)
                for index, item in enumerate(target["seed"]):
                    name = "seed:%d" % index
                    record = observe(cursor, name, item["sql"], tuple(item["parameters"]), engine=engine)
                    records.append(record)
                    _control_record(record, name)
                connection.commit()
                for item in target["catalog"] + target["readback"]:
                    record = observe(cursor, item["name"], item["sql"], engine=engine)
                    records.append(record)
                    if item["expected"] is None:
                        if record.get("kind") != "success" or record.get("warnings") or not _complete_warnings(record) or not isinstance(record.get("metadata"), list):
                            raise ValueError("%s: raw catalog receipt is incomplete" % item["name"])
                    else:
                        _exact_success_rows(record, item["expected"], item["name"])
                for probe in target["probes"]:
                    for route in probe["routes"]:
                        for index, query in enumerate(route["queries"]):
                            name = "%s:%s:%d" % (probe["cell"], route["input_route"], index)
                            record = _observe_probe(cursor, engine, len(records), query["sql"], tuple(query["parameters"]))
                            record["name"] = name
                            _append_probe_then_judge(
                                records,
                                engine,
                                record,
                                route["classification"],
                                route["expected_by_query"][index],
                                name,
                                route.get("result_shape", "scalar"),
                            )
            finally:
                cursor.close()
        finally:
            connection.close()
    except Exception as error:
        terminal = {"kind": "error", "error": type(error).__name__, "message": str(error)}
    receipt_path.write_text(json.dumps({"plan": str(plan_path), "plan_sha256": plan_sha256, "engine": engine, "records": records, "terminal": terminal}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if terminal["kind"] != "success":
        raise SystemExit("numeric probe failed; inspect the preserved receipt")
    _expect(good, Expected("self", (0,), False, "must_success"))
    for bad in (
        {"kind": "success", "metadata": [["value", 8, None, None, None, None, True, 32, 63]], "rows": [[MAX_INT]], "warnings": []},
        {"kind": "success", "metadata": None, "rows": [], "warnings": []},
        {"kind": "error", "errno": 1690, "sqlstate": "22003", "rows": [[1]]},
        {"kind": "error", "errno": 1690, "sqlstate": "22003", "rows": [], "metadata": None, "warnings": None, "warnings_error": False},
        {"kind": "error", "errno": 1690, "sqlstate": "22003", "rows": [], "metadata": None, "warnings": [], "warnings_error": "lost"},
        {"kind": "error", "rows": [], "metadata": None, "warnings": [], "warnings_error": False},
    ):
        try:
            _expect(bad, Expected("must_reject", None, True, "must_1690_22003"))
        except ValueError:
            continue
        raise AssertionError("numeric probe judge accepted an incomplete or unsafe record")
    warning_failure = {"kind": "success", "metadata": [["value", 8, None, None, None, None, True, 0, 63]], "rows": [[0]], "warnings": [], "warnings_error": "RuntimeError"}
    try:
        _expect(warning_failure, Expected("warning_query", (0,), False, "must_success"))
    except ValueError:
        pass
    else:
        raise AssertionError("warning retrieval failure became a successful statement")
    class WarningFailCursor:
        description = [("value", 8, None, None, None, None, True, 0, 63)]

        def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> None:
            if sql == "SHOW WARNINGS":
                error = RuntimeError("warnings unavailable")
                error.errno = 1690
                error.sqlstate = "22003"
                raise error

        def fetchall(self) -> list[tuple[int]]:
            return [(0,)]

    warning_record = observe(WarningFailCursor(), "warning_failure", "SELECT 0", engine="mysql")
    assert warning_record["kind"] == "success" and warning_record["warnings_error"] == "RuntimeError"
    try:
        _expect(warning_record, Expected("warning_failure", (0,), False, "must_success"))
    except ValueError:
        pass
    else:
        raise AssertionError("SHOW WARNINGS failure became an overflow terminal")
    class ErrorWarningFailCursor:
        description = None

        def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> None:
            if sql == "overflow":
                error = RuntimeError("native overflow")
                error.errno = 1690
                error.sqlstate = "22003"
                raise error
            if sql == "SHOW WARNINGS":
                raise RuntimeError("warnings unavailable")

    error_warning_record = observe(ErrorWarningFailCursor(), "error_warning_failure", "overflow", engine="mysql")
    assert error_warning_record["kind"] == "error" and error_warning_record["warnings_error"] == "RuntimeError"
    try:
        _expect(error_warning_record, Expected("error_warning_failure", None, True, "must_1690_22003"))
    except ValueError:
        pass
    else:
        raise AssertionError("error-path SHOW WARNINGS failure became a native terminal")
    frozen = manifest()
    plans = frozen["plans"]
    if plans["postgres"]["seed"] != plans["mysql"]["seed"]:
        raise AssertionError("two-engine numeric plan changed the physical seed")
    for plan in plans.values():
        for probe in plan["probes"]:
            for route in probe["routes"]:
                if len(route["queries"]) != len(route["expected_by_query"]):
                    raise AssertionError("frozen route has no one-to-one query oracle")
        for expected in ARITHMETIC:
            if expected.logical_overflow:
                continue
            cell = expected.name
            probe = next(item for item in plan["probes"] if item["cell"] == cell)
            seed = [row for row in _seed_rows() if row[0] == cell]
            oracle = _finite_oracle(cell, seed)
            if tuple(oracle) != expected.values:
                raise AssertionError(f"{plan['engine']}:{cell}: independent finite oracle drifted")
            routes = {route["input_route"]: route for route in probe["routes"]}
            if routes["literal"]["expected_by_query"] != [oracle]:
                raise AssertionError(f"{plan['engine']}:{cell}: literal oracle is not frozen")
            if routes["column"]["expected_by_query"] != [oracle]:
                raise AssertionError(f"{plan['engine']}:{cell}: column oracle is not frozen")
            if routes["prepared"]["expected_by_query"] != [[value] for value in oracle]:
                raise AssertionError(f"{plan['engine']}:{cell}: prepared oracle is not frozen")
            if routes["literal"]["classification"] != "observation":
                raise AssertionError(f"{plan['engine']}:{cell}: literal must remain an observation")
            expected_required = "observe" if cell == "min_times_one" and plan["engine"] == "mysql" else "must_success"
            if routes["column"]["classification"] != expected_required or routes["prepared"]["classification"] != expected_required:
                raise AssertionError(f"{plan['engine']}:{cell}: physical/prepared target rule drifted")
        unary = next(item for item in plan["probes"] if item["cell"] == "safe_unary")
        literal_sql = unary["routes"][0]["queries"][0]["sql"]
        column_sql = unary["routes"][1]["queries"][0]["sql"]
        prepared_sql = [query["sql"] for query in unary["routes"][2]["queries"]]
        if "SELECT +CAST(-7" not in literal_sql or "SELECT -CAST(7" not in literal_sql or "WHEN 1 THEN -left_value" not in column_sql or not prepared_sql[1].startswith("SELECT -CAST"):
            raise AssertionError(f"{plan['engine']}: unary seed/opcode route drifted")
    preserved: list[dict[str, object]] = []
    mismatch = dict(good, rows=[[7]])
    try:
        _append_probe_then_judge(preserved, "mysql", mismatch, "must_success", [-7], "preserved_mismatch", "scalar")
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched primitive unexpectedly passed")
    if preserved != [mismatch]:
        raise AssertionError("raw terminal was not retained before the oracle judge")
    literal_difference = dict(good, rows=[[7]])
    _expect_target("mysql", literal_difference, "observation", [-7], "literal_difference")
    if literal_difference.get("frozen_oracle_values") != [-7] or literal_difference.get("frozen_oracle_match") is not False:
        raise AssertionError("literal observation did not preserve its independent comparison")
    mysql_sums = {probe["cell"]: probe for probe in plans["mysql"]["probes"] if probe["cell"].startswith("sum_")}
    assert mysql_sums["sum_over_positive"]["routes"][0]["classification"] == "observation_decimal_or_target_native"
    assert mysql_sums["sum_over_positive"]["routes"][1]["classification"] == "observation_cast_or_clamp"
    assert mysql_sums["sum_over_positive"]["routes"][2]["classification"] == "must_1690_22003"
    assert plans["postgres"]["target_version"]["expected"] == [[180006]]
    assert plans["mysql"]["target_version"]["expected"] == [["8.4.12"]]
    valid_version = {"kind": "success", "metadata": [["version", 253]], "rows": [["8.4.12"]], "warnings": [], "warnings_error": False}
    _exact_success_rows(valid_version, [["8.4.12"]], "version")
    for invalid_version in ({**valid_version, "rows": [["8.4.11"]]}, {**valid_version, "rows": []}):
        try:
            _exact_success_rows(invalid_version, [["8.4.12"]], "version")
        except ValueError:
            continue
        raise AssertionError("target version mismatch passed")
    grouped_observation = {"kind": "success", "metadata": [["group_key", 3, None, None, None, None, False, 0, 63], ["value", 246, None, None, None, None, True, 0, 63]], "rows": [[1, {"decimal": "0"}]], "warnings": [], "warnings_error": False}
    _expect_target("mysql", grouped_observation, "observation_decimal_or_target_native", None, "grouped_observation", "grouped")
    grouped_observation["metadata"] = grouped_observation["metadata"][:1]
    try:
        _expect_target("mysql", grouped_observation, "observation_decimal_or_target_native", None, "missing_group", "grouped")
    except ValueError:
        pass
    else:
        raise AssertionError("grouped observation accepted one column")
    try:
        _connect({"engine": "mysql", "host": "192.0.2.1", "port": 3306, "user": "nobody", "database": "phase66", "password_env": "PIETTO_MISSING_PROBE_PASSWORD", "relay_contract": MYSQL_RELAY})
    except ValueError as error:
        assert str(error) == "endpoint must be an owned loopback listener"
    else:
        raise AssertionError("external endpoint passed pre-connect validation")
    try:
        _connect({"engine": "postgres", "host": "127.0.0.1", "port": 5432, "user": "nobody", "database": "app", "password_env": "PIETTO_MISSING_PROBE_PASSWORD", "relay_contract": POSTGRES_RELAY})
    except ValueError as error:
        assert str(error) == "endpoint is not the reviewed PostgreSQL literal-none relay"
    else:
        raise AssertionError("wrong PostgreSQL relay identity passed pre-connect validation")
    tampered = json.loads(json.dumps(frozen))
    tampered["plans"]["mysql"]["probes"].pop()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        plan_path, endpoint_path, receipt_path = root / "plan.json", root / "endpoint.json", root / "receipt.json"
        plan_path.write_text(json.dumps(tampered), encoding="utf-8")
        endpoint_path.write_text(json.dumps({"engine": "mysql", "host": "127.0.0.1", "port": 1, "user": "nobody", "database": "none", "password_env": "PIETTO_MISSING_PROBE_PASSWORD"}), encoding="utf-8")
        try:
            run_plan(plan_path, endpoint_path, receipt_path)
        except ValueError as error:
            assert str(error) == "unexpected probe plan artifact"
        else:
            raise AssertionError("tampered plan reached the endpoint")
        assert not receipt_path.exists()
    class FakeError(Exception):
        sqlstate = "22003"

    class FakeCursor:
        def __init__(self) -> None:
            self.aborted = False
            self.description: list[tuple[object, ...]] | None = None

        def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> None:
            if sql.startswith("SAVEPOINT") or sql.startswith("RELEASE SAVEPOINT"):
                return
            if sql.startswith("ROLLBACK TO SAVEPOINT"):
                self.aborted = False
                return
            if sql == "overflow":
                self.aborted = True
                raise FakeError("overflow")
            if self.aborted:
                error = FakeError("current transaction is aborted")
                error.sqlstate = "25P02"
                raise error
            self.description = [("value", 20)]

        def fetchall(self) -> list[tuple[int]]:
            return [(0,)]

    fake = FakeCursor()
    first = _observe_probe(fake, "postgres", 0, "overflow", ())
    second = _observe_probe(fake, "postgres", 1, "next", ())
    _expect_target("postgres", first, "must_22003", None, "first")
    _expect_target("postgres", second, "must_success", [0], "second")


def _literal(engine: str, value: int | None) -> str:
    if value is None:
        return "CAST(NULL AS %s)" % ("bigint" if engine == "postgres" else "SIGNED")
    return "CAST(%d AS %s)" % (value, "bigint" if engine == "postgres" else "SIGNED")


def _operator(cell: str) -> str:
    return {
        "safe_plus": "+",
        "over_plus": "+",
        "safe_minus": "-",
        "over_minus": "-",
        "safe_multiply": "*",
        "min_times_one": "*",
        "over_multiply": "*",
    }[cell]


def _seed_rows() -> tuple[tuple[str, int, int | None, int | None], ...]:
    return (
        ("safe_plus", 0, -7, 3), ("safe_plus", 1, 0, 9), ("safe_plus", 2, None, 1),
        ("safe_minus", 0, 7, 3), ("safe_minus", 1, 0, 9), ("safe_minus", 2, None, 1),
        ("safe_multiply", 0, -7, 3), ("safe_multiply", 1, 0, 9),
        ("safe_multiply", 2, 3037000499, 3037000499), ("safe_multiply", 3, None, 1),
        ("min_times_one", 0, MIN_INT, 1),
        ("safe_unary", 0, -7, None), ("safe_unary", 1, 7, None), ("safe_unary", 2, None, None),
        ("over_plus", 0, MAX_INT, 1), ("over_minus", 0, MIN_INT, 1),
        ("over_multiply", 0, 3037000500, 3037000500),
        ("over_negate", 0, MIN_INT, None), ("over_abs", 0, MIN_INT, None),
        ("mixed_decimal", 0, 1, 1),
    )


def _unary_opcode(ordinal: int) -> str:
    """The frozen unary operation for each ordered safe-unary seed member."""
    return {0: "+", 1: "-", 2: "+"}[ordinal]


def _independent_arithmetic_oracle(
    cell: str,
    ordinal: int,
    left: int | None,
    right: int | None,
) -> int | None:
    """Compute the finite primitive oracle without inspecting generated SQL."""
    if left is None:
        return None
    if cell == "safe_unary":
        return left if _unary_opcode(ordinal) == "+" else -left
    operator = _operator(cell)
    if right is None:
        raise ValueError(f"{cell}:{ordinal}: binary oracle needs a right operand")
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    return left * right


def _finite_oracle(
    cell: str,
    rows: list[tuple[str, int, int | None, int | None]],
) -> list[int | None]:
    return [_independent_arithmetic_oracle(cell, ordinal, left, right) for _, ordinal, left, right in rows]


def _sum_rows() -> tuple[tuple[str, int, int, int | None], ...]:
    return (
        ("all_null", 1, 0, None), ("all_null", 1, 1, None),
        ("safe", 1, 0, -7), ("safe", 1, 1, 0), ("safe", 1, 2, 7), ("safe", 1, 3, None),
        ("minimum", 1, 0, MIN_INT), ("minimum", 1, 1, 0),
        ("maximum", 1, 0, MAX_INT), ("maximum", 1, 1, 0),
        ("over_positive", 1, 0, MAX_INT), ("over_positive", 1, 1, 1),
        ("over_negative", 1, 0, MIN_INT), ("over_negative", 1, 1, -1),
        ("group_safe", 1, 0, -7), ("group_safe", 1, 1, 7), ("group_safe", 1, 2, None),
        ("group_all_null", 1, 0, None), ("group_all_null", 1, 1, None),
        ("group_overflow", 1, 0, MAX_INT), ("group_overflow", 1, 1, 1),
    )


def _engine_plan(engine: str) -> dict[str, object]:
    if engine not in {"postgres", "mysql"}:
        raise ValueError(engine)
    temporary = "TEMPORARY " if engine == "mysql" else "TEMP "
    primary = "PRIMARY KEY (cell, ordinal)"
    setup = [
        "DROP TABLE IF EXISTS c77_signed_operands",
        "DROP TABLE IF EXISTS c77_signed_sum",
        "CREATE %sTABLE c77_signed_operands (cell VARCHAR(32) NOT NULL, ordinal INTEGER NOT NULL, left_value BIGINT NULL, right_value BIGINT NULL, %s)" % (temporary, primary),
        "CREATE %sTABLE c77_signed_sum (cell VARCHAR(32) NOT NULL, group_key INTEGER NOT NULL, ordinal INTEGER NOT NULL, value BIGINT NULL, PRIMARY KEY (cell, group_key, ordinal))" % (temporary,),
    ]
    if engine == "mysql":
        setup.insert(0, "SET SESSION sql_mode = 'ONLY_FULL_GROUP_BY,STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION'")
        catalog = [
            {"name": "show_operands", "sql": "SHOW CREATE TABLE c77_signed_operands", "expected": None},
            {"name": "show_sum", "sql": "SHOW CREATE TABLE c77_signed_sum", "expected": None},
            {"name": "columns", "sql": "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('c77_signed_operands', 'c77_signed_sum') ORDER BY TABLE_NAME, ORDINAL_POSITION", "expected": [["c77_signed_operands", "cell", "varchar(32)", "NO", "PRI"], ["c77_signed_operands", "ordinal", "int", "NO", "PRI"], ["c77_signed_operands", "left_value", "bigint", "YES", ""], ["c77_signed_operands", "right_value", "bigint", "YES", ""], ["c77_signed_sum", "cell", "varchar(32)", "NO", "PRI"], ["c77_signed_sum", "group_key", "int", "NO", "PRI"], ["c77_signed_sum", "ordinal", "int", "NO", "PRI"], ["c77_signed_sum", "value", "bigint", "YES", ""]]},
        ]
    else:
        catalog = [{
            "name": "columns",
            "sql": "SELECT a.attrelid::regclass::text, a.attname, t.typname, a.attnotnull FROM pg_attribute a JOIN pg_type t ON t.oid = a.atttypid WHERE a.attrelid IN ('c77_signed_operands'::regclass, 'c77_signed_sum'::regclass) AND a.attnum > 0 ORDER BY 1, a.attnum",
            "expected": [["c77_signed_operands", "cell", "varchar", True], ["c77_signed_operands", "ordinal", "int4", True], ["c77_signed_operands", "left_value", "int8", False], ["c77_signed_operands", "right_value", "int8", False], ["c77_signed_sum", "cell", "varchar", True], ["c77_signed_sum", "group_key", "int4", True], ["c77_signed_sum", "ordinal", "int4", True], ["c77_signed_sum", "value", "int8", False]],
        }]
    seed = [
        {"sql": "INSERT INTO c77_signed_operands (cell, ordinal, left_value, right_value) VALUES (%s, %s, %s, %s)", "parameters": list(row)}
        for row in _seed_rows()
    ] + [
        {"sql": "INSERT INTO c77_signed_sum (cell, group_key, ordinal, value) VALUES (%s, %s, %s, %s)", "parameters": list(row)}
        for row in _sum_rows()
    ]
    probes: list[dict[str, object]] = []
    for expected in ARITHMETIC:
        cell = expected.name
        if cell in {"safe_unary", "over_negate", "over_abs"}:
            operator = "ABS(" if cell == "over_abs" else ("+" if cell == "safe_unary" else "-")
            suffix = ")" if cell == "over_abs" else ""
            literal_rows = [row for row in _seed_rows() if row[0] == cell]
            if cell == "safe_unary":
                literal = " UNION ALL ".join(
                    "SELECT %s%s AS value" % (_unary_opcode(row[1]), _literal(engine, row[2]))
                    for row in literal_rows
                )
                physical = "SELECT CASE ordinal WHEN 0 THEN +left_value WHEN 1 THEN -left_value WHEN 2 THEN +left_value END AS value FROM c77_signed_operands WHERE cell = '%s' ORDER BY ordinal" % cell
            else:
                literal = " UNION ALL ".join("SELECT %s%s%s AS value" % (operator, _literal(engine, row[2]), suffix) for row in literal_rows)
                physical = "SELECT %sleft_value%s AS value FROM c77_signed_operands WHERE cell = '%s' ORDER BY ordinal" % (operator, suffix, cell)
            prepared = [
                {"sql": "SELECT %sCAST(%%s AS %s)%s AS value" % ((_unary_opcode(row[1]) if cell == "safe_unary" else operator), "bigint" if engine == "postgres" else "SIGNED", suffix), "parameters": [row[2]]}
                for row in literal_rows
            ]
        else:
            operator = _operator(cell)
            literal_rows = [row for row in _seed_rows() if row[0] == cell]
            literal = " UNION ALL ".join("SELECT %s %s %s AS value" % (_literal(engine, row[2]), operator, _literal(engine, row[3])) for row in literal_rows)
            physical = "SELECT left_value %s right_value AS value FROM c77_signed_operands WHERE cell = '%s' ORDER BY ordinal" % (operator, cell)
            prepared = [
                {"sql": "SELECT CAST(%%s AS %s) %s CAST(%%s AS %s) AS value" % ("bigint" if engine == "postgres" else "SIGNED", operator, "bigint" if engine == "postgres" else "SIGNED"), "parameters": [row[2], row[3]]}
                for row in literal_rows
            ]
        overflow = expected.logical_overflow
        target_error = "must_22003" if engine == "postgres" else "must_1690_22003"
        finite_oracle = _finite_oracle(cell, literal_rows) if not overflow else None
        if finite_oracle is not None and tuple(finite_oracle) != expected.values:
            raise AssertionError(f"{cell}: declared logical oracle diverges from independent oracle")
        probes.append({
            "cell": cell,
            "logical": {"values": list(expected.values) if expected.values is not None else None, "overflow": overflow},
            "routes": [
                {"input_route": "literal", "classification": "observation", "expected_by_query": [finite_oracle if finite_oracle is not None else None], "queries": [{"sql": literal, "parameters": []}]},
                {"input_route": "column", "classification": expected.engine_observation if cell == "min_times_one" and engine == "mysql" else (target_error if overflow else "must_success"), "expected_by_query": [finite_oracle if finite_oracle is not None else None], "queries": [{"sql": physical, "parameters": []}]},
                {"input_route": "prepared", "classification": expected.engine_observation if cell == "min_times_one" and engine == "mysql" else (target_error if overflow else "must_success"), "expected_by_query": [[value] for value in finite_oracle] if finite_oracle is not None else [None for _ in prepared], "queries": prepared},
            ],
        })
    sum_cast = "CAST(SUM(CAST(value AS bigint)) AS bigint)" if engine == "postgres" else "CAST(SUM(value) AS SIGNED)"
    sum_guard = sum_cast if engine == "postgres" else SUM_GUARD
    for expected in SUMS:
        grouped = expected.name.startswith("group_")
        where = "WHERE cell = %s"
        prefix = "SELECT group_key, " if grouped else "SELECT "
        suffix = " GROUP BY group_key ORDER BY group_key" if grouped else ""
        target_error = "must_22003" if engine == "postgres" else "must_1690_22003"
        probes.append({
            "cell": "sum_" + expected.name,
            "logical": {"values": list(expected.values) if expected.values is not None else None, "overflow": expected.logical_overflow},
            "routes": [
                {"input_route": "raw_sum", "classification": "observation_decimal_or_target_native", "result_shape": "grouped" if grouped else "scalar", "expected_by_query": [None], "queries": [{"sql": prefix + "SUM(value) AS value FROM c77_signed_sum " + where + suffix, "parameters": [expected.name]}]},
                {"input_route": "cast_sum", "classification": "observation_cast_or_clamp", "result_shape": "grouped" if grouped else "scalar", "expected_by_query": [None], "queries": [{"sql": prefix + sum_cast + " AS value FROM c77_signed_sum " + where + suffix, "parameters": [expected.name]}]},
                {"input_route": "guarded_sum", "classification": target_error if expected.logical_overflow else "must_success", "result_shape": "grouped" if grouped else "scalar", "expected_by_query": [None if expected.logical_overflow else ([[1, expected.values[0]]] if grouped else list(expected.values))], "queries": [{"sql": prefix + sum_guard + " AS value FROM c77_signed_sum " + where + suffix, "parameters": [expected.name]}]},
            ],
        })
    probes.append({
        "cell": "mixed_decimal_warning",
        "logical": {"values": None, "overflow": False},
        "routes": [{"input_route": "literal", "classification": "observation_mixed_type", "expected_by_query": [None], "queries": [{"sql": "SELECT %s + CAST(1.0 AS %s) AS value" % (_literal(engine, 1), "numeric" if engine == "postgres" else "DECIMAL"), "parameters": []}]}],
    })
    return {
        "engine": engine,
        "setup": setup,
        "seed": seed,
        "catalog": catalog,
        "readback": [
            {"name": "operands", "sql": "SELECT cell, ordinal, left_value, right_value FROM c77_signed_operands ORDER BY cell, ordinal", "expected": [list(row) for row in sorted(_seed_rows())]},
            {"name": "sum", "sql": "SELECT cell, group_key, ordinal, value FROM c77_signed_sum ORDER BY cell, group_key, ordinal", "expected": [list(row) for row in sorted(_sum_rows())]},
        ],
        "probes": probes,
    }


def manifest() -> dict[str, object]:
    return {
        "artifact": "pietto.phase77.numeric_primitive_probe.v2",
        "status": "PREREGISTERED_NOT_STARTED",
        "overflow": OVERFLOW,
        "sum_guard": SUM_GUARD,
        "session": {
            "sql_mode": "ONLY_FULL_GROUP_BY,STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION",
            "warnings": "SHOW WARNINGS after every statement",
            "metadata": "cursor.description retained for every successful SELECT",
        },
        "plans": {"postgres": _engine_plan("postgres"), "mysql": _engine_plan("mysql")},
        "same_physical_seed": {
            "postgres": {
                "signed_column": "BIGINT",
                "literal_cast": "CAST(<value> AS bigint)",
                "checked_sum": "CAST(SUM(CAST(value AS bigint)) AS bigint)",
                "catalog": "pg_attribute/pg_type rows for each result and seed column",
            },
            "mysql": {
                "signed_column": "BIGINT",
                "literal_cast": "CAST(<value> AS SIGNED)",
                "checked_sum_candidate": SUM_GUARD,
                "catalog": "SHOW CREATE TABLE plus Connector/Python cursor.description",
            },
            "prepared_parameters": "%s placeholders via each pinned DB-API driver",
        },
        "mysql_relay_contract": MYSQL_RELAY,
        "postgres_relay_contract": POSTGRES_RELAY,
        "differential_judgment": {
            "safe": "Both targets must preserve the independent logical value, NULL and signed physical result evidence.",
            "mysql_overflow": "MySQL must retain its raw native errno 1690 and SQLSTATE 22003; do not translate it to PostgreSQL text.",
            "postgres_overflow": "PostgreSQL records its own raw terminal; it is a reference observation, not a string oracle for MySQL.",
            "min_times_one": "The logical Int value is MIN_INT, but raw MySQL remains unqualified OBSERVE because older evidence reported 1690. Either raw terminal is preserved; neither opens S01 alone.",
        },
        "arithmetic_setup": [
            "DROP TABLE IF EXISTS c77_signed_operands",
            "CREATE TABLE c77_signed_operands (cell VARCHAR(32) NOT NULL, ordinal INT NOT NULL, left_value BIGINT NULL, right_value BIGINT NULL, PRIMARY KEY (cell, ordinal))",
            "SHOW CREATE TABLE c77_signed_operands",
        ],
        "run_interface": {
            "preflight": [
                "UV_PYTHON=3.13.13 <candidate-python> -I -B p77_mysql_numeric_probe.py --self-check",
                "record image/driver/session/relay identities before opening either target",
            ],
            "engine_inputs": [
                "one owned loopback endpoint from the reviewed network-none exec-stdio relay",
                "a fresh candidate-only DB-API environment",
                "the same ordered seed rows and statement labels on PostgreSQL and MySQL",
            ],
            "receipt": "p77_mysql_numeric_probe.py --run-plan PLAN --endpoint-json ENDPOINT --write-receipt RECEIPT consumes only the frozen plan; it does not choose a cell, route or operand at runtime",
        },
        "arithmetic_forms": {
            "literal": "SELECT CAST(<left> AS SIGNED) <operator> CAST(<right> AS SIGNED) AS value",
            "physical": "SELECT left_value <operator> right_value AS value FROM c77_signed_operands WHERE cell = <cell> ORDER BY ordinal",
            "prepared": "SELECT left_value <operator> CAST(%s AS SIGNED) AS value FROM c77_signed_operands WHERE cell = %s ORDER BY ordinal",
            "unary_physical": "SELECT <operator>left_value AS value FROM c77_signed_operands WHERE cell = <cell> ORDER BY ordinal",
            "abs_physical": "SELECT ABS(left_value) AS value FROM c77_signed_operands WHERE cell = <cell> ORDER BY ordinal",
        },
        "sum_setup": [
            "DROP TABLE IF EXISTS c77_signed_sum",
            "CREATE TABLE c77_signed_sum (cell VARCHAR(32) NOT NULL, group_key INT NOT NULL, ordinal INT NOT NULL, value BIGINT NULL, PRIMARY KEY (cell, group_key, ordinal))",
            "SHOW CREATE TABLE c77_signed_sum",
        ],
        "sum_forms": {
            "raw": "SELECT SUM(value) AS value FROM c77_signed_sum WHERE cell = %s",
            "narrowed": "SELECT CAST(SUM(value) AS SIGNED) AS value FROM c77_signed_sum WHERE cell = %s",
            "guarded": "SELECT " + SUM_GUARD + " AS value FROM c77_signed_sum WHERE cell = %s",
            "grouped_guarded": "SELECT group_key, " + SUM_GUARD + " AS value FROM c77_signed_sum WHERE cell = %s GROUP BY group_key ORDER BY group_key",
        },
        "arithmetic": [{"name": item.name, "values": list(item.values) if item.values is not None else None, "logical_overflow": item.logical_overflow, "engine_observation": item.engine_observation} for item in ARITHMETIC],
        "sums": [{"name": item.name, "values": list(item.values) if item.values is not None else None, "logical_overflow": item.logical_overflow, "engine_observation": item.engine_observation} for item in SUMS],
        "non_claims": [
            "No emitted Pietto SQL is tested here.",
            "No raw MySQL result opens a Pietto form.",
            "SUM DECIMAL and CAST-to-SIGNED are separately observed.",
            "Raw PostgreSQL output is not the MySQL error oracle.",
        ],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--write-manifest", type=Path)
    parser.add_argument("--run-plan", type=Path)
    parser.add_argument("--endpoint-json", type=Path)
    parser.add_argument("--write-receipt", type=Path)
    args = parser.parse_args(argv)
    if args.self_check:
        self_check()
        print("numeric primitive probe judge self-check passed")
    if args.manifest or args.write_manifest:
        payload = json.dumps(manifest(), indent=2, sort_keys=True) + "\n"
        if args.write_manifest:
            args.write_manifest.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
    if args.run_plan or args.endpoint_json or args.write_receipt:
        if not (args.run_plan and args.endpoint_json and args.write_receipt):
            parser.error("--run-plan, --endpoint-json and --write-receipt are required together")
        run_plan(args.run_plan, args.endpoint_json, args.write_receipt)
    if not (args.self_check or args.manifest or args.write_manifest or args.run_plan):
        parser.error("choose --self-check, --manifest, --write-manifest, or --run-plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
