"""One statement on the pinned pure driver, with independent call observations."""

from __future__ import annotations

from functools import cache
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from typing import Any

from _pietto_target_conformance_resources import QUERY_SECONDS, READ_SECONDS

API = "mysql.native-prepared.v1"
BINARY_CHARSET = 63


@cache
def driver_sources() -> dict[str, str]:
    distribution = importlib.metadata.distribution("mysql-connector-python")
    if distribution.version != "26.7.0":
        raise ValueError("native adapter requires Connector/Python26.7.0")
    return {
        name: hashlib.sha256(
            Path(str(distribution.locate_file(name))).read_bytes()
        ).hexdigest()
        for name in (
            "mysql/connector/connection.py",
            "mysql/connector/protocol.py",
            "mysql/connector/abstracts.py",
        )
    }


def characters(row, columns):
    """Data-only: the pinned binary protocol returns raw bytes for a character
    column MySQL flags BINARY, so decode by the column's declared character set.
    The call trace keeps the driver's own bytes; only the result is decoded."""
    result = []
    for value, column in zip(row, columns, strict=True):
        if value.get("kind") == "bytes":
            if (
                type(column) is not list
                or len(column) < 9
                or type(column[8]) is not int
            ):
                raise ValueError("native column character set missing")
            if column[8] != BINARY_CHARSET:
                try:
                    decoded = bytes.fromhex(value["value"]).decode("utf-8")
                except (ValueError, UnicodeDecodeError) as error:
                    raise ValueError("native character column decoding") from error
                value = {"kind": "text", "value": decoded}
        result.append(value)
    return result


def values(items):
    # Reuse the facility's finite scalar encoding, including signed-zero floats.
    from _pietto_target_conformance_observation import scalar

    return [scalar(item) for item in items]


class NativeStatement:
    """Single prepare/execute/drain/close; never reusable or a DB-API cursor."""

    def __init__(self, connection: Any):
        if (
            type(connection).__module__ != "mysql.connector.connection"
            or type(connection).__name__ != "MySQLConnection"
        ):
            raise ValueError("native adapter requires the pinned pure connection")
        self.connection = connection
        self.prepared: Any = None
        self.columns: Any = None
        self.previous: Any = None
        self.record: dict[str, Any] = {
            "adapter": API,
            "driver_version": "26.7.0",
            "driver_sources": driver_sources(),
            "session_id": connection.connection_id,
            "statement_id": None,
            "prepare": "not_started",
            "parameter_count": None,
            "parameter_metadata": None,
            "result_metadata": None,
            "metadata_eof": None,
            "terminal": None,
            "unread_final": None,
            "close_send": "not_started",
            "events": [],
        }
        self.filename = str(
            importlib.metadata.distribution("mysql-connector-python").locate_file(
                "mysql/connector/connection.py"
            )
        )
        self.protocol_filename = self.filename.replace("/connection.py", "/protocol.py")

    def observe(self, frame, event, result):
        if self.previous is not None:
            self.previous(frame, event, result)
        local = frame.f_locals
        protocol = (
            frame.f_code.co_filename == self.protocol_filename
            and frame.f_code.co_name == "make_stmt_execute"
            and local.get("self") is self.connection._protocol
        )
        if (
            not protocol
            and (
                frame.f_code.co_filename != self.filename
                or local.get("self") is not self.connection
            )
            or event not in {"call", "return"}
        ):
            return
        name = frame.f_code.co_name
        fact: dict[str, Any] = {
            "event": name + "." + event,
            "session_id": self.connection.connection_id,
        }
        if protocol:
            fact["value"] = (
                {
                    "statement_id": local["statement_id"],
                    "data": values(local["data"]),
                    "parameters": list(local["parameters"]),
                    "flags": local["flags"],
                    "charset": local["charset"],
                    "long_data_used": local["long_data_used"],
                    "query_attrs": local["query_attrs"],
                    "converter_str_fallback": local["converter_str_fallback"],
                }
                if event == "call"
                else result.hex()
                if result is not None
                else None
            )
        elif name == "cmd_stmt_prepare":
            fact["value"] = local["statement"].hex() if event == "call" else result
        elif name == "cmd_stmt_execute":
            fact["value"] = (
                {
                    "statement_id": local["statement_id"],
                    "data": values(local["data"]),
                    "parameters": list(local["parameters"]),
                    "flags": local["flags"],
                }
                if event == "call"
                else result
            )
        elif name == "get_rows":
            # Ordinary SHOW diagnostics on this same connection are a separate
            # observer path, not rows or terminals of this binary statement.
            if local["binary"] is not True:
                return
            fact["value"] = (
                {
                    "binary": local["binary"],
                    "columns": local["columns"],
                    "count": local["count"],
                }
                if event == "call"
                else None
                if result is None
                else {
                    "rows": [values(row) for row in result[0]],
                    "eof": result[1],
                }
            )
        elif name == "cmd_stmt_close":
            fact["value"] = local["statement_id"]
        elif name == "_send_cmd" and local["command"] in {22, 23, 24, 25, 26, 28}:
            fact["value"] = {
                "command": local["command"],
                "payload": bytes(local["packet"] or local["argument"]).hex(),
                "expect_response": local["expect_response"],
            }
        else:
            return
        self.record["events"].append(json.loads(json.dumps(fact)))

    def __enter__(self):
        self.previous = sys.getprofile()
        sys.setprofile(self.observe)
        return self

    def __exit__(self, *exception):
        sys.setprofile(self.previous)

    def prepare(self, sql: str) -> None:
        if self.record["prepare"] != "not_started":
            raise ValueError("statement already prepared")
        self.record["prepare"] = "started"
        prepared = self.connection.cmd_stmt_prepare(
            sql.encode("utf-8"),
            read_timeout=READ_SECONDS,
            write_timeout=QUERY_SECONDS,
        )
        # Register ownership before any metadata validation can fail.
        self.prepared = prepared
        self.record["statement_id"] = prepared["statement_id"]
        self.record["parameter_count"] = prepared["num_params"]
        self.record["parameter_metadata"] = [
            list(column) for column in prepared["parameters"]
        ]
        self.record["prepare"] = "success"
        if prepared.get("warning_count") != 0:
            raise ValueError("prepare warnings require diagnosis before execute")

    def execute(self, parameters: tuple[object, ...]) -> bool:
        if self.prepared is None:
            raise ValueError("statement not prepared")
        if (
            type(self.prepared["num_params"]) is not int
            or self.prepared["num_params"] != len(parameters)
            or len(self.prepared["parameters"]) != len(parameters)
        ):
            raise ValueError("NATIVE_PARAMETER_COUNT")
        result = self.connection.cmd_stmt_execute(
            self.prepared["statement_id"],
            data=parameters,
            parameters=self.prepared["parameters"],
            read_timeout=READ_SECONDS,
            write_timeout=QUERY_SECONDS,
        )
        if isinstance(result, tuple) and len(result) == 3:
            self.columns = result[1]
            self.record["result_metadata"] = [list(column) for column in self.columns]
            self.record["metadata_eof"] = result[2]
            # Required public-property bookkeeping used by the pinned cursor.
            # Only get_rows observing the real rowset terminal may clear it.
            self.connection.unread_result = True
            return True
        if type(result) is not dict:
            raise ValueError("unknown native execution result")
        self.record["terminal"] = {"kind": "ok", "packet": result}
        return False

    def batches(self):
        if self.columns is None:
            raise ValueError("native rowset missing")
        while self.record["terminal"] is None:
            rows, terminal = self.connection.get_rows(
                count=1000,
                binary=True,
                columns=self.columns,
                read_timeout=READ_SECONDS,
            )
            if terminal is not None:
                self.record["terminal"] = {"kind": "rowset_eof", "packet": terminal}
            yield rows

    def close(self) -> None:
        self.record["unread_final"] = self.connection.unread_result
        if self.prepared is None:
            self.record["close_send"] = "no_returned_statement"
            return
        self.record["close_send"] = "started"
        self.connection.cmd_stmt_close(
            self.prepared["statement_id"],
            read_timeout=READ_SECONDS,
            write_timeout=QUERY_SECONDS,
        )
        # COM_STMT_CLOSE has no response: this is send completion only.
        self.record["close_send"] = "complete_no_ack"


def verify_native(observation):
    """Data-only correspondence check; no connection or driver methods."""
    native = observation["native"]
    if type(native) is not dict or set(native) != {
        "adapter",
        "driver_version",
        "driver_sources",
        "session_id",
        "statement_id",
        "prepare",
        "parameter_count",
        "parameter_metadata",
        "result_metadata",
        "metadata_eof",
        "terminal",
        "unread_final",
        "close_send",
        "events",
    }:
        raise ValueError("native observation fields")
    if (
        native["adapter"] != API
        or native["driver_version"] != "26.7.0"
        or native["driver_sources"] != driver_sources()
        or type(native["session_id"]) is not int
        or native["session_id"] <= 0
        or observation["api"] != API
        or observation["cursor_type"] is not None
    ):
        raise ValueError("native adapter/session identity")
    events = native["events"]
    if type(events) is not list or any(
        type(event) is not dict
        or set(event) != {"event", "session_id", "value"}
        or event["session_id"] != native["session_id"]
        for event in events
    ):
        raise ValueError("native call/session identity")

    def calls(name):
        return [e["value"] for e in events if e["event"] == name]

    sql = observation["sql"].encode().hex()
    if calls("cmd_stmt_prepare.call") != [sql]:
        raise ValueError("native prepare SQL substitution")
    sends = calls("_send_cmd.call")
    if any(
        type(send) is not dict
        or set(send) != {"command", "payload", "expect_response"}
        or type(send["command"]) is not int
        or type(send["payload"]) is not str
        or send["expect_response"] is not (send["command"] != 25)
        for send in sends
    ):
        raise ValueError("native command fields")
    if not sends or sends[0] != {
        "command": 22,
        "payload": sql,
        "expect_response": True,
    }:
        raise ValueError("native command payload substitution")
    if calls("_send_cmd.return") != sends:
        raise ValueError("native command observation incomplete")
    if native["prepare"] != "success":
        if (
            observation["status"] == "success"
            or [e["event"] for e in events]
            != [
                "cmd_stmt_prepare.call",
                "_send_cmd.call",
                "_send_cmd.return",
                "cmd_stmt_prepare.return",
            ]
            or calls("cmd_stmt_prepare.return") != [None]
            or native["statement_id"] is not None
            or native["close_send"] != "no_returned_statement"
        ):
            raise ValueError("native prepare incomplete")
        return
    prepared = calls("cmd_stmt_prepare.return")
    if (
        len(prepared) != 1
        or type(prepared[0]) is not dict
        or set(prepared[0])
        != {
            "statement_id",
            "num_params",
            "parameters",
            "num_columns",
            "columns",
            "warning_count",
        }
        or type(native["statement_id"]) is not int
        or native["statement_id"] <= 0
        or prepared[0]["statement_id"] != native["statement_id"]
        or prepared[0]["num_params"] != native["parameter_count"]
        or prepared[0]["parameters"] != native["parameter_metadata"]
        or type(prepared[0]["num_params"]) is not int
        or prepared[0]["num_params"] < 0
        or type(prepared[0]["num_columns"]) is not int
        or prepared[0]["num_columns"] != len(prepared[0]["columns"])
    ):
        raise ValueError("native prepared identity/metadata")
    expected = {
        "statement_id": native["statement_id"],
        "data": observation["parameters"],
        "parameters": native["parameter_metadata"],
        "flags": 0,
    }
    executed = calls("cmd_stmt_execute.call")
    fetched = calls("get_rows.return")
    expected_events = [
        "cmd_stmt_prepare.call",
        "_send_cmd.call",
        "_send_cmd.return",
        "cmd_stmt_prepare.return",
        *(
            [
                "cmd_stmt_execute.call",
                "make_stmt_execute.call",
                "make_stmt_execute.return",
                "_send_cmd.call",
                "_send_cmd.return",
                "cmd_stmt_execute.return",
            ]
            if executed
            else []
        ),
        *[event for _ in fetched for event in ("get_rows.call", "get_rows.return")],
        "cmd_stmt_close.call",
        "_send_cmd.call",
        "_send_cmd.return",
        "cmd_stmt_close.return",
    ]
    if [event["event"] for event in events] != expected_events:
        raise ValueError("native call denominator/order")
    if observation["execute"] == "success" and (
        executed != [expected]
        or native["parameter_count"] != len(observation["parameters"])
        or len(native["parameter_metadata"]) != native["parameter_count"]
    ):
        raise ValueError("native argument correspondence")
    if executed and executed != [expected]:
        raise ValueError("native execute statement substitution")
    if executed:
        encoded = calls("make_stmt_execute.call")
        packets = calls("make_stmt_execute.return")
        if (
            len(encoded) != 1
            or set(encoded[0])
            != set(expected)
            | {"charset", "long_data_used", "query_attrs", "converter_str_fallback"}
            or any(encoded[0][key] != value for key, value in expected.items())
            or encoded[0]["charset"] != "utf8mb4"
            or encoded[0]["long_data_used"] != {}
            or encoded[0]["query_attrs"] not in (None, [])
            or encoded[0]["converter_str_fallback"] is not False
            or len(packets) != 1
            or len(sends) < 2
            or sends[1]["payload"] != packets[0]
        ):
            raise ValueError("native driver encoding/command payload mismatch")
    identity = native["statement_id"].to_bytes(4, "little").hex()
    expected_commands = [22, *([23] if executed else []), 25]
    if (
        [s["command"] for s in sends] != expected_commands
        or any(not s["payload"].startswith(identity) for s in sends[1:])
        or sends[-1] != {"command": 25, "payload": identity, "expect_response": False}
        or calls("cmd_stmt_close.call") != [native["statement_id"]]
        or calls("cmd_stmt_close.return") != [native["statement_id"]]
        or native["close_send"] != "complete_no_ack"
    ):
        raise ValueError("native statement closure")
    if observation["status"] == "success":
        terminal = native["terminal"]
        if (
            native["unread_final"] is not False
            or type(terminal) is not dict
            or set(terminal) != {"kind", "packet"}
            or type(terminal["packet"]) is not dict
            or type(terminal["packet"].get("status_flag")) is not int
            or terminal["packet"]["status_flag"] & 8
        ):
            raise ValueError("native terminal missing")
        if observation["fetch"] == "success":
            if (
                not fetched
                or any(
                    type(f) is not dict or set(f) != {"rows", "eof"} for f in fetched
                )
                or any(f["eof"] is not None for f in fetched[:-1])
                or fetched[-1]["eof"] is None
                or terminal != {"kind": "rowset_eof", "packet": fetched[-1]["eof"]}
                or [
                    characters(row, observation["metadata"])
                    for f in fetched
                    for row in f["rows"]
                ]
                != observation["rows"]
                or native["result_metadata"] != observation["metadata"]
                or len(calls("get_rows.call")) != len(fetched)
                or any(
                    call
                    != {
                        "binary": True,
                        "columns": observation["metadata"],
                        "count": 1000,
                    }
                    for call in calls("get_rows.call")
                )
            ):
                raise ValueError("native binary result/terminal mismatch")
            if calls("cmd_stmt_execute.return") != [
                [
                    len(observation["metadata"]),
                    observation["metadata"],
                    native["metadata_eof"],
                ]
            ]:
                raise ValueError("native execution/metadata terminal correspondence")
        elif terminal["kind"] != "ok" or calls("get_rows.call"):
            raise ValueError("native no-rowset terminal mismatch")
        elif calls("cmd_stmt_execute.return") != [terminal["packet"]]:
            raise ValueError("native OK correspondence")
