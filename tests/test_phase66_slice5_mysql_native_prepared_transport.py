"""Pinned-method regression and data-only v2 controls; normal pytest is offline."""

from copy import deepcopy
import hashlib
import sys
from typing import Any

import pytest
import _pietto_phase66_sql_emission_probe as probe

from _pietto_mysql_native_prepared import (
    API,
    BINARY_CHARSET,
    NativeStatement,
    characters,
    driver_sources,
    verify_native,
)


def test_actual_driver_trace_separates_ordinary_diagnostic_fetch():
    from mysql.connector.connection import MySQLConnection
    from mysql.connector.errors import InternalError

    connection = MySQLConnection()
    with NativeStatement(connection) as statement:
        with pytest.raises(InternalError, match="No result set available"):
            connection.get_rows(binary=False)
        assert statement.record["events"] == []
        with pytest.raises(InternalError, match="No result set available"):
            connection.get_rows(binary=True)
        assert [event["event"] for event in statement.record["events"]] == [
            "get_rows.call",
            "get_rows.return",
        ]
        assert statement.record["events"][-1]["value"] is None
    assert connection._socket is None


def test_fixed_transaction_purpose_cannot_bypass_native_queries():
    from mysql.connector.connection import MySQLConnection
    from _pietto_target_conformance_observation import Observer, ObserverFailure

    connection = MySQLConnection()
    observer = Observer("mysql", connection, "query")
    for sql, parameters in (("SELECT 1", ()), ("BEGIN", (1,))):
        with pytest.raises(ObserverFailure, match="UNREVIEWED_TRANSACTION_CONTROL"):
            observer.capture(sql, parameters, rows=False, transaction_control=True)
    with pytest.raises(ObserverFailure, match="UNREVIEWED_TRANSACTION_CONTROL"):
        observer.capture("BEGIN", rows=False, native=True, transaction_control=True)
    assert connection._socket is None and observer.submission_count == 0


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("variant", probe.VARIANTS["P_native_identifiers"])
def test_real_field_origin_identifier_documents(tmp_path, target, variant):
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    item = probe.fixture(target, "P_native_identifiers", variant)
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified and outcome.status == "VERIFIED"
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert document["fixed_values"] == document["parameter_uses"] == []
    assert len(document["request"]["contract"]["sources"][0]["fields"]) == 4
    assert document["columns"][0]["correspondence"]["field"] == (
        2 if variant.startswith("plain") else 0
    )


def native_data(observation, *, session=17, statement=3):
    """Synthetic receipt data only, never a live/installed transport witness."""
    metadata = observation["metadata"]
    count = (
        1
        if any(f.get("stage") == "parameter_count" for f in observation["failures"])
        else len(observation["parameters"])
    )
    parameters = [
        ["?", 253, None, None, None, None, True, 0, 255] for _ in range(count)
    ]
    eof = {"warning_count": 0, "status_flag": 2}
    ok = {
        "field_count": 0,
        "affected_rows": 1,
        "insert_id": 0,
        "status_flag": 2,
        "warning_count": 0,
    }
    prepare_failed = any(f["stage"] == "prepare" for f in observation["failures"])
    executed = observation["execute"] in {"success", "failed"}
    prepared = {
        "statement_id": statement,
        "num_params": len(parameters),
        "parameters": parameters,
        "num_columns": len(metadata or []),
        "columns": metadata or [],
        "warning_count": 0,
    }
    events = []

    def event(name, value):
        events.append({"event": name, "session_id": session, "value": deepcopy(value)})

    def send(command, payload, response=True):
        fact = {"command": command, "payload": payload, "expect_response": response}
        event("_send_cmd.call", fact)
        event("_send_cmd.return", dict(fact))

    sql = observation["sql"].encode().hex()
    event("cmd_stmt_prepare.call", sql)
    send(22, sql)
    event("cmd_stmt_prepare.return", None if prepare_failed else prepared)
    native = {
        "adapter": API,
        "driver_version": "26.7.0",
        "driver_sources": driver_sources(),
        "session_id": session,
        "statement_id": None if prepare_failed else statement,
        "prepare": "started" if prepare_failed else "success",
        "parameter_count": None if prepare_failed else len(parameters),
        "parameter_metadata": None if prepare_failed else parameters,
        "result_metadata": metadata,
        "metadata_eof": eof if metadata else None,
        "terminal": None,
        "unread_final": False,
        "close_send": "no_returned_statement" if prepare_failed else "complete_no_ack",
        "events": events,
    }
    if not prepare_failed:
        identity = statement.to_bytes(4, "little").hex()
        if executed:
            event(
                "cmd_stmt_execute.call",
                {
                    "statement_id": statement,
                    "data": observation["parameters"],
                    "parameters": parameters,
                    "flags": 0,
                },
            )
            event(
                "make_stmt_execute.call",
                {
                    "statement_id": statement,
                    "data": observation["parameters"],
                    "parameters": parameters,
                    "flags": 0,
                    "charset": "utf8mb4",
                    "long_data_used": {},
                    "query_attrs": [],
                    "converter_str_fallback": False,
                },
            )
            event("make_stmt_execute.return", identity + "0001000000")
            send(23, identity + "0001000000")
            event(
                "cmd_stmt_execute.return",
                (
                    None
                    if observation["execute"] == "failed"
                    else [len(metadata), metadata, eof]
                    if metadata
                    else ok
                ),
            )
            if observation["fetch"] == "success":
                event(
                    "get_rows.call",
                    {"binary": True, "columns": metadata, "count": 1000},
                )
                event("get_rows.return", {"rows": observation["rows"], "eof": eof})
                native["terminal"] = {"kind": "rowset_eof", "packet": eof}
            elif observation["fetch"] == "not_applicable":
                native["terminal"] = {"kind": "ok", "packet": ok}
            elif observation["fetch"] == "failed":
                event(
                    "get_rows.call",
                    {
                        "binary": True,
                        "columns": metadata,
                        "count": 1000,
                    },
                )
                event("get_rows.return", None)
        event("cmd_stmt_close.call", statement)
        send(25, identity, False)
        event("cmd_stmt_close.return", statement)
    observation.update(api=API, native=native, prepared=True, cursor_type=None)
    return observation


def test_unmodified_pinned_cursor_rewrites_a_legal_identifier():
    from mysql.connector.connection import MySQLConnection
    from mysql.connector.cursor import MySQLCursorPrepared
    from mysql.connector.errors import OperationalError
    import mysql.connector.connection as module

    quote = chr(96)
    sql = "SELECT " + quote + '%s"' + quote + " FROM t"
    connection = MySQLConnection()
    observed = []
    previous = sys.getprofile()

    def trace(frame, event, arg):
        if previous is not None:
            previous(frame, event, arg)
        if (
            event == "call"
            and frame.f_code.co_filename == module.__file__
            and frame.f_code.co_name == "cmd_stmt_prepare"
            and frame.f_locals.get("self") is connection
        ):
            observed.append(frame.f_locals["statement"])

    try:
        sys.setprofile(trace)
        with pytest.raises(OperationalError, match="MySQL Connection not available"):
            MySQLCursorPrepared(connection).execute(sql)
    finally:
        sys.setprofile(previous)
    assert observed == [sql.replace('%s"', '?"').encode()]
    assert connection._socket is None


@pytest.fixture
def synthetic_native():
    return native_data(
        {
            "sql": "SELECT ? AS v",
            "sql_sha256": hashlib.sha256(b"SELECT ? AS v").hexdigest(),
            "parameters": [{"kind": "int", "value": "11"}],
            "status": "success",
            "execute": "success",
            "fetch": "success",
            "close": "success",
            "metadata": [["v", 8, None, None, None, None, False]],
            "rows": [[{"kind": "int", "value": "11"}]],
            "failures": [],
        }
    )


def test_synthetic_data_only_native_correspondence(synthetic_native):
    verify_native(synthetic_native)


@pytest.mark.parametrize(
    "change",
    (
        "delete",
        "extra",
        "session",
        "statement",
        "payload",
        "values",
        "parameter_metadata",
        "terminal",
        "closure",
        "legacy_cursor",
    ),
)
def test_native_receipt_corruption(synthetic_native, change):
    value = deepcopy(synthetic_native)
    native = value["native"]
    if change == "delete":
        native["events"].pop(1)
    elif change == "extra":
        native["events"].append(deepcopy(native["events"][0]))
    elif change == "session":
        native["events"][0]["session_id"] += 1
    elif change == "statement":
        native["statement_id"] += 1
    elif change == "payload":
        native["events"][1]["value"]["payload"] += "20"
    elif change == "values":
        value["parameters"][0]["value"] = "99"
    elif change == "parameter_metadata":
        native["parameter_metadata"] = []
    elif change == "terminal":
        native["terminal"] = None
    elif change == "closure":
        native["close_send"] = "acknowledged"
    else:
        value["cursor_type"] = "mysql.connector.cursor.MySQLCursorPrepared"
    with pytest.raises(ValueError):
        verify_native(value)


# MySQL flags a _bin-collated character column BINARY, and the pinned driver's
# binary protocol returns its raw bytes: protocol.py _parse_binary_values takes
# the "field[7] == FieldFlag.BINARY or field[8] == 63" branch before decoding.
UTF8MB4_0900_BIN = 309
TEXT_COLUMN = ["note", 253, None, None, None, None, 1, 128, UTF8MB4_0900_BIN]
BLOB_COLUMN = ["raw", 253, None, None, None, None, 1, 128, BINARY_CHARSET]


def test_pinned_driver_returns_bytes_for_a_bin_collated_character_column():
    from mysql.connector.constants import FieldFlag
    from mysql.connector.protocol import MySQLProtocol

    # The exact upstream rule this decoding answers, on the unmodified driver.
    assert FieldFlag.BINARY == 128 and TEXT_COLUMN[7] == FieldFlag.BINARY
    payload = "雪?%s é 😀".encode()
    # One field: a single null-bitmap byte, then one length-coded string.
    packet = bytes([0, len(payload)]) + payload
    binary: Any = tuple(TEXT_COLUMN)
    (value,) = MySQLProtocol()._parse_binary_values([binary], packet, "utf8")
    assert value == payload and type(value) is bytes
    plain: Any = (*TEXT_COLUMN[:7], 0, UTF8MB4_0900_BIN)
    (decoded,) = MySQLProtocol()._parse_binary_values([plain], packet, "utf8")
    assert decoded == payload.decode() and type(decoded) is str


@pytest.mark.parametrize(
    "column,expected",
    (
        (TEXT_COLUMN, {"kind": "text", "value": "雪?%s é 😀"}),
        (BLOB_COLUMN, {"kind": "bytes", "value": "雪?%s é 😀".encode().hex()}),
    ),
)
def test_declared_character_columns_decode_and_binary_columns_do_not(column, expected):
    raw = {"kind": "bytes", "value": "雪?%s é 😀".encode().hex()}
    assert characters([raw], [column]) == [expected]
    # Values the driver already decoded, and other kinds, pass through unchanged.
    assert characters([{"kind": "text", "value": "a  "}], [column]) == [
        {"kind": "text", "value": "a  "}
    ]
    assert characters([{"kind": "null"}], [column]) == [{"kind": "null"}]


@pytest.mark.parametrize("change", ("invalid_utf8", "short_metadata", "no_charset"))
def test_undecodable_character_columns_fail_closed(change):
    row = [{"kind": "bytes", "value": "ff" if change == "invalid_utf8" else "61"}]
    column = {
        "invalid_utf8": TEXT_COLUMN,
        "short_metadata": TEXT_COLUMN[:7],
        "no_charset": [*TEXT_COLUMN[:8], "utf8mb4"],
    }[change]
    with pytest.raises(ValueError):
        characters(row, [column])


def test_decoded_rows_must_correspond_to_the_traced_driver_bytes(synthetic_native):
    payload = "雪?%s é 😀".encode()
    observation = deepcopy(synthetic_native)
    observation["metadata"] = [TEXT_COLUMN]
    observation["rows"] = [[{"kind": "text", "value": payload.decode()}]]
    native = observation["native"]
    native["result_metadata"] = [TEXT_COLUMN]
    for event in native["events"]:
        if event["event"] == "get_rows.call":
            event["value"] = {"binary": True, "columns": [TEXT_COLUMN], "count": 1000}
        elif event["event"] == "get_rows.return" and event["value"] is not None:
            event["value"]["rows"] = [[{"kind": "bytes", "value": payload.hex()}]]
        elif event["event"] == "cmd_stmt_execute.return":
            event["value"] = [1, [TEXT_COLUMN], native["metadata_eof"]]
        elif event["event"] == "cmd_stmt_prepare.return":
            event["value"]["num_columns"] = 1
            event["value"]["columns"] = [TEXT_COLUMN]
    verify_native(observation)
    substituted = deepcopy(observation)
    substituted["rows"] = [[{"kind": "text", "value": "substituted"}]]
    with pytest.raises(ValueError, match="native binary result/terminal mismatch"):
        verify_native(substituted)
    undecoded = deepcopy(observation)
    undecoded["rows"] = [[{"kind": "bytes", "value": payload.hex()}]]
    with pytest.raises(ValueError, match="native binary result/terminal mismatch"):
        verify_native(undecoded)
