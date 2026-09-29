"""Closed native metadata/carrier checks and general product control regressions."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from _pietto_phase68_slice5_cases import seven_artifact, seven_rows, build
from pietto._project.project_result_output import prepare_output
from pietto._project.project_execution_reader import (
    bind_native_output,
    decode_native_rows,
)
from pietto._project.project_result_contract import ResultError
from pietto._project import project_execution as execution
from pietto._project import project_execution_postgres as pg
import test_phase68_slice3_execution as old


def adbc_metadata():
    names = (
        "occurred_at",
        "maybe_time",
        "key_value",
        "maybe_key",
        "number",
        "flag",
        "ratio",
        "label",
        "amount",
    )
    types = (
        "timestamp[us]",
        "timestamp[us]",
        "extension<arrow.opaque[storage_type=binary, type_name=uuid, vendor_name=PostgreSQL]>",
        "extension<arrow.opaque[storage_type=binary, type_name=uuid, vendor_name=PostgreSQL]>",
        "int32",
        "bool",
        "double",
        "string",
        "extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>",
    )
    return [
        dict(
            ordinal=i,
            name=n,
            type=t,
            nullable=True,
            metadata={}
            if i not in (2, 3, 8)
            else {
                b"ADBC:postgresql:typname".hex(): (
                    b"numeric" if i == 8 else b"uuid"
                ).hex()
            },
        )
        for i, (n, t) in enumerate(zip(names, types, strict=True))
    ]


def test_qualified_adbc_carriers_and_coordinated_damage(tmp_path):
    output = prepare_output(seven_artifact(tmp_path / "compiled", "postgres"))
    meta = adbc_metadata()
    original = list(seven_rows("postgres")[0])
    raw = list(original)
    raw[2] = original[2].bytes
    raw[8] = str(original[8])
    _, values = decode_native_rows(output, "postgres_adbc", meta, (raw,))
    assert values == (tuple(original),)
    for index, value in (
        (2, b"short"),
        (2, "00112233445566778899aabbccddeeff"),
        (8, "NaN"),
        (8, "1e100"),
        (8, "1.00001"),
        (6, float("inf")),
        (4, True),
    ):
        damaged = list(raw)
        damaged[index] = value
        with pytest.raises(ResultError):
            decode_native_rows(output, "postgres_adbc", meta, (raw, damaged))
    for index, member, value in (
        (2, "type", "binary"),
        (2, "metadata", {}),
        (8, "type", "string"),
        (4, "type", "int64"),
        (0, "type", "timestamp[us, tz=UTC]"),
        (1, "ordinal", 0),
    ):
        damaged = deepcopy(meta)
        damaged[index][member] = value
        with pytest.raises(ResultError):
            bind_native_output(output, "postgres_adbc", damaged)
    with pytest.raises(ResultError):
        bind_native_output(output, "mysql_rows", meta)
    wrong = replace(
        output.contract.scalar_meaning.entries[2].law, byte_order="little_endian"
    )
    entry = output.contract.scalar_meaning.entries[2]
    object.__setattr__(entry, "law", wrong)
    with pytest.raises(ValueError):
        bind_native_output(output, "postgres_adbc", meta)


@pytest.mark.parametrize("control", ("cancel", "deadline"))
@pytest.mark.parametrize("close_fails", (False, True))
def test_computed_general_request_and_control_after_payload(
    tmp_path, monkeypatch, control, close_fails
):
    artifact = build(tmp_path, "postgres", "T_row_direct", "query_bind").artifact
    output = prepare_output(artifact)
    access = execution.PostgresAccess(
        "127.0.0.1", 5432, "test", "pietto_query", "private", "disable"
    )
    request = execution.prepare_execution(artifact, access, output=output)
    assert execution.execution_arguments(request)
    connection = old.Connection()
    old.install(monkeypatch, connection)
    stream = pg.PostgresExecution(request)

    class Payload:
        rows = batches = bytes = 0

        def __init__(self, *args):
            pass

        def accept(self, rows):
            if control == "cancel":
                stream.cancel()
            else:
                assert stream._started is not None
                stream._started -= request.limits.seconds + 1
            return SimpleNamespace(close=close)

    def close():
        closed.append(True)
        if close_fails:
            raise OSError("injected payload cleanup")

    closed = []
    monkeypatch.setattr(pg, "ExecutionPayloads", Payload)
    expected_error = execution.ExecutionError if control == "cancel" else TimeoutError
    with pytest.raises(expected_error):
        with stream:
            next(stream)
    assert closed == [True]
    assert stream.outcome.delivery == "FAILED"
    assert (
        stream.outcome.primary is not None
        and stream.outcome.primary.kind == expected_error.__name__
    )
    assert bool(stream.outcome.cleanup_failures) is close_fails
    assert connection.closed and stream.control_joined


def test_data_only_checker_rejects_actual_record_damage(tmp_path):
    """Synthetic transport record checks the checker; it is not native proof."""
    import json
    from pietto._project.project_sql_emission import serialize_project_sql_emission
    from _pietto_phase68_slice5_cases import expected
    from _pietto_phase68_slice5_probe import check_general_record, oracle_values

    outcome = build(tmp_path, "postgres", "G_emission_table_bag", "bag")
    document = json.loads(serialize_project_sql_emission(outcome))
    rows, _ = expected("postgres", "G_emission_table_bag", "bag")
    types = {
        "Int": (20, "int64"),
        "Bool": (16, "bool"),
        "Float": (701, "double"),
        "Text": (25, "string"),
        "Decimal": (1700, "decimal128(9, 2)"),
    }
    record = dict(
        public=document,
        submissions=[dict(sql=document["sql"], arguments=[], prepare=True)],
        rows=oracle_values(rows, document["columns"]),
        metadata=[
            [c["label"], types[c["logical_type"]["name"]][0], None]
            for c in document["columns"]
        ],
        bound_schema=[
            [
                c["label"],
                types[c["logical_type"]["name"]][1],
                c["nullable"] is not False,
            ]
            for c in document["columns"]
        ],
        outcome=dict(
            source="EOF",
            transaction="COMMIT_ACK",
            delivery="COMPLETE",
            cleanup="CLOSED",
            primary=None,
            cleanup_failures=[],
            rows=len(rows),
        ),
        control_joined=True,
        caught=None,
        context=["pietto_query", "repeatable read", "on", "UTF8", "pg_catalog"],
    )
    record["schemas"] = [record["bound_schema"]]
    record["outcome"]["batches"] = 1
    check_general_record(
        record, "postgres", "G_emission_table_bag", "bag", "postgres_rows"
    )
    for damage in (
        "sql",
        "argument",
        "metadata",
        "result",
        "schema",
        "terminal",
        "context",
        "original",
    ):
        corrupted = deepcopy(record)
        if damage == "sql":
            corrupted["submissions"][0]["sql"] += " LIMIT 0"
        elif damage == "argument":
            corrupted["submissions"][0]["arguments"] = [1]
        elif damage == "metadata":
            corrupted["metadata"][0][1] = 23
        elif damage == "result":
            corrupted["rows"].pop()
        elif damage == "schema":
            corrupted["bound_schema"][0][1] = "int32"
        elif damage == "terminal":
            corrupted["outcome"]["transaction"] = "UNKNOWN"
        elif damage == "context":
            corrupted["context"][0] = "foreign"
        else:
            corrupted["public"]["columns"][0]["ordinal"] = 1
        with pytest.raises(ValueError):
            check_general_record(
                corrupted, "postgres", "G_emission_table_bag", "bag", "postgres_rows"
            )


def test_mysql_unsigned_computed_domain_is_not_source_signedness(tmp_path):
    output = prepare_output(
        build(tmp_path / "rank", "mysql", "A_window_ranking", "peers").artifact
    )
    metadata = [
        [c.label, 8, None, None, None, None, 0, 4097 if i == 0 else 33, 63]
        for i, c in enumerate(output.columns)
    ]
    binding = bind_native_output(output, "mysql_rows", metadata)
    assert binding.fields[1].observation.lower == 0
    assert binding.fields[1].observation.upper == 2**63 - 1
    metadata[0][7] = 33
    with pytest.raises(ResultError):
        bind_native_output(output, "mysql_rows", metadata)
    from pietto._project.project_arrow_result import _value

    with pytest.raises(ResultError):
        _value(2**63, binding.fields[1])
    with pytest.raises(ResultError):
        _value(-1, binding.fields[1])


def test_metadata_primitives_and_foreign_runtime_prefix(tmp_path):
    from _pietto_phase68_slice5_probe import check_origins
    import sys

    output = prepare_output(seven_artifact(tmp_path / "pg", "postgres"))
    meta = adbc_metadata()
    meta[0]["ordinal"] = False
    with pytest.raises(ResultError):
        bind_native_output(output, "postgres_adbc", meta)
    mysql = prepare_output(seven_artifact(tmp_path / "my", "mysql"))
    codes = (12, 12, 254, 254, 3, 1, 5, 253, 246)
    meta = [
        [c.label, t, None, None, None, None, 1, 0, 309 if i == 7 else 63]
        for i, (c, t) in enumerate(zip(mysql.columns, codes, strict=True))
    ]
    meta[5][1] = True
    with pytest.raises(ResultError):
        bind_native_output(mysql, "mysql_rows", meta)
    with pytest.raises(ValueError, match="interpreter"):
        check_origins(dict(prefix="foreign"), "source", sys.prefix)


@pytest.mark.parametrize("route", ("postgres_adbc", "mysql_rows"))
def test_data_only_transport_checks_calls_and_raw_values(route):
    from _pietto_phase68_slice5_probe import check_transport

    row = [{"kind": "int", "value": "1"}]
    record = dict(
        rows=[row],
        transaction="COMMIT_ACK",
        cleanup="CLOSED",
        raw=dict(
            sql="synthetic",
            parameters=[],
            actual=[row],
            raw_actual=[row],
            metadata=[["n", 8, None, None, None, None, 0, 0, 63]],
            api_calls=[dict(method="execute", sql="synthetic", values=[])],
            native=dict(close_send="complete_no_ack", unread_final=False),
            source_terminal="arrow_StopIteration"
            if route == "postgres_adbc"
            else "native_rowset_eof",
            statement_cleanup="close_returned",
        ),
        native_calls=[
            dict(method="cmd_stmt_prepare", event="call", sql="synthetic"),
            dict(method="cmd_stmt_execute", event="call", arguments=[], statement_id=1),
            dict(method="get_rows", event="return", rows=[row], eof={}),
            dict(method="cmd_stmt_close", event="return", statement_id=1),
        ],
    )
    import json

    record = json.loads(json.dumps(record))  # Native records cross this boundary.
    check_transport(record, route, "synthetic", [])
    for kind in ("call", "raw", "terminal", "fetch"):
        damaged = deepcopy(record)
        if kind == "raw":
            damaged["raw"]["actual"][0][0]["value"] = "2"
        elif kind == "terminal":
            damaged["transaction"] = "UNKNOWN"
        elif route == "mysql_rows":
            if kind == "call":
                damaged["native_calls"][0]["sql"] = "foreign"
            else:
                damaged["native_calls"][2]["rows"] = []
        else:
            damaged["raw"]["api_calls"][0]["sql"] = "foreign"
        with pytest.raises(ValueError):
            check_transport(damaged, route, "synthetic", [])
