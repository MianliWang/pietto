"""Complete driver-call observations, preserving protocol differences and failures."""

from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from typing import Any

from _pietto_target_conformance_resources import (
    QUERY_SECONDS,
    READ_SECONDS,
    deadline,
    error_fact,
)

MAX_ROWS = 100_000
MAX_RESULT_BYTES = 16 * 1024 * 1024
MAX_DIAGNOSTICS = 1024
MAX_DIAGNOSTIC_BYTES = 64 * 1024


class ObserverFailure(ValueError):
    pass


def scalar(value: object) -> dict[str, Any]:
    if value is None:
        return {"kind": "null"}
    if type(value) is bool:
        return {"kind": "bool", "value": value}
    if type(value) is int:
        return {"kind": "int", "value": str(value)}
    if type(value) is str:
        return {"kind": "text", "value": value}
    if type(value) is bytes:
        return {"kind": "bytes", "value": value.hex()}
    if type(value) is float and math.isfinite(value):
        return {"kind": "float", "value": value.hex()}
    if type(value) is Decimal and value.is_finite():
        return {"kind": "decimal", "value": str(value)}
    raise ObserverFailure("UNSUPPORTED_VALUE_TYPE")


class Observer:
    def __init__(self, target: str, connection: Any, identity: str):
        self.target, self.connection, self.identity = target, connection, identity
        self.submission_count = 0
        self.notices: list[dict[str, Any]] = []
        self.notices_lost = False
        self.diagnostic_failures: list[dict[str, Any]] = []
        if target == "postgres":
            connection.add_notice_handler(self.notice)

    def notice(self, diagnostic: Any) -> None:
        # Diagnostic storage expires on return from the callback.
        if len(self.notices) >= MAX_DIAGNOSTICS:
            self.notices_lost = True
            return
        self.notices.append(
            {
                "severity": diagnostic.severity_nonlocalized,
                "sqlstate": diagnostic.sqlstate,
                "message": diagnostic.message_primary,
            }
        )

    def cursor(self, prepared: bool) -> Any:
        if self.target == "postgres":
            return self.connection.cursor()
        return self.connection.cursor(
            prepared=prepared, read_timeout=READ_SECONDS, write_timeout=QUERY_SECONDS
        )

    def diagnostics(self) -> dict[str, Any]:
        if self.target == "postgres":
            return {
                "protocol": "postgres_notices",
                "total": None,
                "details": list(self.notices),
                "complete": not self.notices_lost,
            }
        value: dict[str, Any] = {
            "protocol": "mysql_warnings",
            "total": None,
            "details": [],
            "complete": False,
        }
        cursor: Any = None
        try:
            cursor = self.connection.cursor(
                read_timeout=READ_SECONDS, write_timeout=QUERY_SECONDS
            )
            with deadline(QUERY_SECONDS):
                cursor.execute("SHOW COUNT(*) WARNINGS")
                counts = cursor.fetchall()
            if len(counts) != 1 or len(counts[0]) != 1 or type(counts[0][0]) is not int:
                raise ObserverFailure("DIAGNOSTIC_TOTAL_UNAVAILABLE")
            value["total"] = counts[0][0]
            with deadline(QUERY_SECONDS):
                cursor.execute("SHOW WARNINGS")
                rows = cursor.fetchall()
            if len(rows) > MAX_DIAGNOSTICS:
                raise ObserverFailure("DIAGNOSTIC_LIMIT")
            value["details"] = [
                {
                    "severity": row[0],
                    "vendor_code": row[1],
                    "message": row[2],
                    "sqlstate": None,
                }
                for row in rows
            ]
            if (
                len(json.dumps(value["details"], ensure_ascii=False).encode())
                > MAX_DIAGNOSTIC_BYTES
            ):
                raise ObserverFailure("DIAGNOSTIC_LIMIT")
            value["complete"] = value["total"] == len(value["details"])
        except Exception as error:
            self.diagnostic_failures.append(error_fact(error, "diagnostics"))
        finally:
            if cursor is not None:
                try:
                    with deadline(QUERY_SECONDS):
                        cursor.close()
                except Exception as error:
                    self.diagnostic_failures.append(
                        error_fact(error, "diagnostics.close")
                    )
            if self.diagnostic_failures:
                value["complete"] = False
        return value

    def capture(
        self,
        sql: str,
        parameters: tuple[object, ...] = (),
        *,
        rows: bool = True,
        prepared: bool = False,
        secret: bool = False,
        native: bool = False,
        transaction_control: bool = False,
    ) -> dict[str, Any]:
        if transaction_control and (
            sql != "BEGIN" or parameters or rows or prepared or native or secret
        ):
            raise ObserverFailure("UNREVIEWED_TRANSACTION_CONTROL")
        self.notices.clear()
        self.notices_lost = False
        self.diagnostic_failures.clear()
        cursor: Any = None
        observation: dict[str, Any] = {
            "sql": "CREDENTIAL_MANAGEMENT" if secret else sql,
            "sql_sha256": None
            if secret
            else hashlib.sha256(sql.encode("utf-8")).hexdigest(),
            "parameters": [] if secret else [scalar(value) for value in parameters],
            "identity": self.identity,
            "prepared": prepared or self.target == "postgres",
            "buffering": "client_complete"
            if self.target == "postgres"
            else "unbuffered",
            "status": "failed",
            "execute": "not_started",
            "fetch": "not_started",
            "close": "not_started",
            "metadata": None,
            "rows": [],
            "diagnostics": None,
            "failures": [],
            "cursor_type": None,
            "api": None,
            "native": None,
        }
        if (
            self.target == "mysql"
            and not transaction_control
            and (self.identity == "query" or native)
        ):
            if secret:
                raise ObserverFailure("SECRET_NATIVE_QUERY_FORBIDDEN")
            return self.capture_native(observation, parameters, rows=rows)
        stage = "execute"
        try:
            cursor = self.cursor(prepared)
            observation["cursor_type"] = (
                type(cursor).__module__ + "." + type(cursor).__name__
            )
            observation["api"] = observation["cursor_type"]
            with deadline(QUERY_SECONDS):
                # Actual cursor input only; MySQL native queries use the separately
                # observed low-level route below, including zero-parameter queries.
                self.submission_count += 1
                cursor.execute(sql, parameters or None)
            observation["execute"] = "success"
            stage = "fetch"
            if rows:
                if cursor.description is None:
                    raise ObserverFailure("METADATA_UNAVAILABLE")
                observation["metadata"] = [
                    list(column) for column in cursor.description
                ]
                if not observation["metadata"]:
                    raise ObserverFailure("METADATA_UNAVAILABLE")
                size = 0
                with deadline(READ_SECONDS):
                    while True:
                        batch = cursor.fetchmany(1000)
                        if not batch:
                            break
                        for row in batch:
                            encoded = [scalar(value) for value in row]
                            size += len(
                                json.dumps(encoded, ensure_ascii=False).encode("utf-8")
                            )
                            if (
                                len(observation["rows"]) >= MAX_ROWS
                                or size > MAX_RESULT_BYTES
                            ):
                                raise ObserverFailure("RESULT_LIMIT")
                            observation["rows"].append(encoded)
                observation["fetch"] = "success"
            else:
                if cursor.description is not None:
                    raise ObserverFailure("UNEXPECTED_RESULT_SET")
                observation["fetch"] = "not_applicable"
            stage = "diagnostics"
            with deadline(READ_SECONDS):
                observation["diagnostics"] = self.diagnostics()
            observation["failures"].extend(self.diagnostic_failures)
            if observation["diagnostics"]["complete"] is not True:
                raise ObserverFailure("DIAGNOSTICS_INCOMPLETE")
        except Exception as error:
            observation[stage if stage in {"execute", "fetch"} else "status"] = "failed"
            fact = error_fact(error, stage)
            if not secret:
                fact["message"] = str(error)
            if isinstance(error, ObserverFailure):
                fact["kind"] = str(error)
            observation["failures"].append(fact)
            if observation["diagnostics"] is None:
                try:
                    with deadline(READ_SECONDS):
                        observation["diagnostics"] = self.diagnostics()
                    observation["failures"].extend(self.diagnostic_failures)
                except Exception as secondary:
                    observation["failures"].append(error_fact(secondary, "diagnostics"))
                    observation["diagnostics"] = {
                        "protocol": self.target,
                        "total": None,
                        "details": [],
                        "complete": False,
                    }
        finally:
            if cursor is not None:
                try:
                    with deadline(QUERY_SECONDS):
                        cursor.close()
                    observation["close"] = "success"
                except Exception as error:
                    observation["close"] = "failed"
                    observation["failures"].append(error_fact(error, "close"))
        if not observation["failures"]:
            observation["status"] = "success"
        return observation

    def begin(self) -> dict[str, Any]:
        # Fixed transaction management retains its original ordinary command.
        # It is never selected as a fallback from a native query failure.
        return self.capture("BEGIN", rows=False, transaction_control=True)

    def capture_native(self, observation, parameters, *, rows):
        from _pietto_mysql_native_prepared import (
            API,
            NativeStatement,
            characters,
            verify_native,
        )

        observation["api"] = API
        observation["prepared"] = True
        statement = NativeStatement(self.connection)
        observation["native"] = statement.record
        stage = "prepare"
        with statement:
            try:
                with deadline(QUERY_SECONDS):
                    self.submission_count += 1
                    statement.prepare(observation["sql"])
                    stage = "parameter_count"
                    if statement.record["parameter_count"] != len(parameters):
                        raise ObserverFailure("NATIVE_PARAMETER_COUNT")
                    stage = "execute"
                    has_rows = statement.execute(parameters)
                observation["execute"] = "success"
                stage = "fetch"
                if has_rows:
                    observation["metadata"] = statement.record["result_metadata"]
                    size = 0
                    with deadline(READ_SECONDS):
                        for batch in statement.batches():
                            for row in batch:
                                encoded = characters(
                                    [scalar(value) for value in row],
                                    observation["metadata"],
                                )
                                size += len(
                                    json.dumps(encoded, ensure_ascii=False).encode()
                                )
                                if (
                                    len(observation["rows"]) >= MAX_ROWS
                                    or size > MAX_RESULT_BYTES
                                ):
                                    raise ObserverFailure("RESULT_LIMIT")
                                observation["rows"].append(encoded)
                    observation["fetch"] = "success"
                    if not rows:
                        raise ObserverFailure("UNEXPECTED_RESULT_SET")
                elif rows:
                    raise ObserverFailure("METADATA_UNAVAILABLE")
                else:
                    observation["fetch"] = "not_applicable"
                stage = "diagnostics"
                observation["diagnostics"] = self.diagnostics()
                observation["failures"].extend(self.diagnostic_failures)
                if observation["diagnostics"]["complete"] is not True:
                    raise ObserverFailure("DIAGNOSTICS_INCOMPLETE")
            except Exception as error:
                if stage in {"execute", "fetch"}:
                    observation[stage] = "failed"
                fact = error_fact(error, stage) | {"message": str(error)}
                if isinstance(error, ObserverFailure):
                    fact["kind"] = str(error)
                observation["failures"].append(fact)
                # Do not issue another command before a real rowset terminal.
                if observation["diagnostics"] is None:
                    if not self.connection.unread_result:
                        observation["diagnostics"] = self.diagnostics()
                        observation["failures"].extend(self.diagnostic_failures)
                    else:
                        observation["diagnostics"] = {
                            "protocol": "mysql_warnings",
                            "total": None,
                            "details": [],
                            "complete": False,
                        }
            finally:
                try:
                    with deadline(QUERY_SECONDS):
                        statement.close()
                    observation["close"] = "success"
                except Exception as error:
                    statement.record["close_send"] = "failed"
                    observation["close"] = "failed"
                    observation["failures"].append(error_fact(error, "close"))
        if not observation["failures"]:
            observation["status"] = "success"
        try:
            verify_native(observation)
        except ValueError as error:
            observation["status"] = "failed"
            observation["failures"].append(
                error_fact(error, "observation") | {"message": str(error)}
            )
        return observation

    def session_id(self) -> int:
        value = (
            self.connection.info.backend_pid
            if self.target == "postgres"
            else self.connection.connection_id
        )
        if type(value) is not int or value <= 0:
            raise ObserverFailure("SESSION_ID_UNAVAILABLE")
        return value

    def rollback(self) -> None:
        with deadline(QUERY_SECONDS):
            self.connection.rollback()
