"""Bounded S05 native acquisition and independent data-only acceptance."""

import argparse
import importlib
from typing import Any
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

import _pietto_phase68_slice4_probe as prior

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice05-"


def charge(path, category, reason):
    data = json.loads(path.read_text())
    if data["used"][category] >= data["ceilings"][category]:
        raise ValueError("S05 budget exhausted: " + category)
    data["used"][category] += 1
    data["events"].append(dict(kind="charge", category=category, reason=reason))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def collect_pg(artifact, access, *, binding=None, control=None):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_execution as execution
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_sql_emission import (
        EmissionOutcome,
        serialize_project_sql_emission,
    )

    output = prepare_output(artifact, binding=binding)
    request = execution.prepare_execution(
        artifact,
        access,
        binding=binding,
        output=output,
        limits=execution.ExecutionLimits(batch_rows=4, seconds=45),
    )
    stream = PostgresExecution(request)
    submitted, rows, schemas = [], [], []
    old = sys.getprofile()

    def observe(frame, event, value):
        if old:
            old(frame, event, value)
        if (
            event == "call"
            and frame.f_code.co_name == "execute"
            and frame.f_locals.get("self") is stream._cursor
        ):
            submitted.append(
                dict(
                    sql=frame.f_locals.get("query"),
                    arguments=[
                        prior.s01.scalar(v)
                        for v in (frame.f_locals.get("params") or ())
                    ],
                    prepare=frame.f_locals.get("prepare"),
                )
            )

    caught = None
    try:
        sys.setprofile(observe)
        with stream:
            for batch in stream:
                with batch:
                    actual = pa.record_batch(batch)
                    schemas.append(
                        [[f.name, str(f.type), f.nullable] for f in actual.schema]
                    )
                    rows.extend(
                        [
                            [
                                prior.s01.scalar(actual.column(i)[j].as_py())
                                for i in range(actual.num_columns)
                            ]
                            for j in range(actual.num_rows)
                        ]
                    )
                if control == "cancel":
                    stream.cancel()
                elif control == "consumer_error":
                    raise ValueError("owned consumer failure")
    except BaseException as error:
        caught = dict(kind=type(error).__name__, category=str(error))
    finally:
        sys.setprofile(old)
        stream.close()
    return dict(
        public=json.loads(
            serialize_project_sql_emission(EmissionOutcome("VERIFIED", (), artifact))
        ),
        submissions=submitted,
        rows=rows,
        schemas=schemas,
        bound_schema=None
        if stream._payloads is None
        else [
            [f.name, str(f.type), f.nullable] for f in stream._payloads.binding.schema
        ],
        metadata=stream.actual_metadata,
        raw_metadata=stream.actual_metadata_details,
        outcome=asdict(stream.outcome),
        session=stream.session_id,
        context=stream.context,
        control_joined=stream.control_joined,
        caught=caught,
    )


def check_pg(record, expected_rows, *, expected_sql=None):
    if expected_sql is None:
        probe = prior.load(
            "s05_emission", ROOT / "tests/_pietto_phase66_sql_emission_probe.py"
        )
        document = probe.decode_public(json.dumps(record["public"]).encode())
        expected_submit = dict(
            sql=document["sql"],
            arguments=[prior.s01.scalar(v) for v in probe.decoded_arguments(document)],
            prepare=True,
        )
    else:
        if (
            record["public"]["sql"] != expected_sql
            or record["public"]["parameter_uses"]
        ):
            raise ValueError("seven-scalar original direct query")
        expected_submit = dict(sql=expected_sql, arguments=[], prepare=True)
    if record["submissions"] != [expected_submit]:
        raise ValueError("actual submitted SQL/arguments")
    if Counter(json.dumps(r, sort_keys=True) for r in record["rows"]) != Counter(
        json.dumps(r, sort_keys=True) for r in expected_rows
    ):
        raise ValueError("independent complete result")
    outcome = record["outcome"]
    if (
        (
            outcome["source"],
            outcome["transaction"],
            outcome["delivery"],
            outcome["cleanup"],
        )
        != ("EOF", "COMMIT_ACK", "COMPLETE", "CLOSED")
        or outcome["primary"] is not None
        or outcome["cleanup_failures"]
        or not record["control_joined"]
        or record["caught"] is not None
    ):
        raise ValueError("separate terminals")
    if len(record["schemas"]) != outcome["batches"] or any(
        schema != record["bound_schema"] for schema in record["schemas"]
    ):
        raise ValueError("actual consumer batches")
    if outcome["rows"] != len(expected_rows) or record["bound_schema"] is None:
        raise ValueError("consumer denominator or empty schema")
    if tuple(record["context"]) != (
        "pietto_query",
        "repeatable read",
        "on",
        "UTF8",
        "pg_catalog",
    ):
        raise ValueError("execution context")


def setup_seven(resources):
    import _pietto_phase68_slice5_cases as cases
    import _pietto_phase67_result_product_probe as product

    target = resources.target
    quote = '"' if target == "postgres" else "`"
    for precision, scale in ((39, 4), (65, 30)):
        types = (
            [
                "TIMESTAMP(6)",
                "TIMESTAMP(6)",
                "UUID",
                "UUID",
                "INTEGER",
                "BOOLEAN",
                "DOUBLE PRECISION",
                'TEXT COLLATE "C"',
                f"NUMERIC({precision},{scale})",
            ]
            if target == "postgres"
            else [
                "DATETIME(6)",
                "DATETIME(6)",
                "BINARY(16)",
                "BINARY(16)",
                "INTEGER",
                "TINYINT",
                "DOUBLE",
                "VARCHAR(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin",
                f"DECIMAL({precision},{scale})",
            ]
        )
        definition = ",".join(
            quote + name + quote + " " + kind
            for name, kind in zip(product.TEMPORAL_NAMES, types, strict=True)
        )
        for state in ("values", "empty", "null"):
            name = "p68seven" + str(precision) + "_" + state
            prior.s03.manager(
                resources, "CREATE TABLE " + name + " (" + definition + ")"
            )
            markers = ",".join(
                "$" + str(i + 1) if target == "postgres" else "?" for i in range(9)
            )
            sql = "INSERT INTO " + name + " VALUES (" + markers + ")"
            rows = (
                cases.seven_rows(target, precision)
                if state == "values"
                else ((None,) * 9,)
                if state == "null"
                else ()
            )
            for row in rows:
                if target == "postgres":
                    with resources.manager.cursor() as cursor:
                        cursor.execute(sql, row, prepare=True)
                else:
                    native = prior.s01.helper(
                        "_pietto_mysql_native_prepared"
                    ).NativeStatement(resources.manager)
                    try:
                        native.prepare(sql)
                        native.execute(row)
                    finally:
                        native.close()


def collect_bridge(artifact, config):
    pa = importlib.import_module("pyarrow")
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_execution_reader import decode_native_rows
    from pietto._project.project_arrow_result import bind_arrow
    from pietto._project.project_arrow_interop import build_managed_batch
    from pietto._project.project_execution_binding_verification import native_arguments
    from pietto._project.project_sql_emission import (
        EmissionOutcome,
        serialize_project_sql_emission,
    )

    output = prepare_output(artifact)
    if any(
        item.downstream_enforcement_required
        for item in artifact.request.plan.single_matches
    ):
        raise ValueError("UNFULFILLED_RUNTIME_OBLIGATION")
    parameters = native_arguments(
        artifact,
        tuple(
            s.site.position.literal.value for s in artifact.request.plan.literal_slots
        ),
    )
    driver = prior.s01.Driver(config)
    report: dict[str, Any] = dict(
        route=config["route"],
        public=json.loads(
            serialize_project_sql_emission(EmissionOutcome("VERIFIED", (), artifact))
        ),
        transaction="NOT_STARTED",
        cleanup="NOT_STARTED",
    )
    try:
        if config["target"] == "postgres":
            driver.control("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        else:
            driver.control("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            driver.control("START TRANSACTION READ ONLY")
        report["transaction"] = "OPEN"
        trace = []
        previous = sys.getprofile()

        def observe(frame, event, returned):
            if previous:
                previous(frame, event, returned)
            if frame.f_locals.get("self") is driver.connection and event in (
                "call",
                "return",
            ):
                name = frame.f_code.co_name
                if name in (
                    "cmd_stmt_prepare",
                    "cmd_stmt_execute",
                    "get_rows",
                    "cmd_stmt_close",
                ):
                    if name == "get_rows" and frame.f_locals.get("binary") is not True:
                        return
                    item: dict[str, Any] = dict(
                        method=name,
                        event=event,
                        statement_id=frame.f_locals.get("statement_id"),
                    )
                    if event == "call" and name == "cmd_stmt_prepare":
                        item["sql"] = frame.f_locals["statement"].decode()
                    elif event == "call" and name == "cmd_stmt_execute":
                        item["arguments"] = [
                            prior.s01.scalar(v) for v in frame.f_locals.get("data", ())
                        ]
                    elif (
                        event == "return"
                        and name == "get_rows"
                        and returned is not None
                    ):
                        item["rows"] = [
                            [prior.s01.scalar(v) for v in row] for row in returned[0]
                        ]
                        item["eof"] = returned[1]
                    trace.append(item)

        try:
            sys.setprofile(observe)
            raw, rows = driver.query(artifact.rendered.sql.decode(), parameters)
        finally:
            sys.setprofile(previous)
        report["native_calls"] = trace
        report["raw"] = raw
        if "error" in raw:
            raise ValueError("native driver failure: " + str(raw["error"]))
        metadata = (
            raw["arrow_schema"]
            if config["route"] == "postgres_adbc"
            else raw["metadata"]
        )
        producer, decoded = decode_native_rows(output, config["route"], metadata, rows)
        binding = bind_arrow(producer)
        report["bound_schema"] = [
            [f.name, str(f.type), f.nullable] for f in binding.schema
        ]
        with build_managed_batch(binding, decoded) as batch:
            actual = pa.record_batch(batch)
            report["rows"] = [
                [
                    prior.s01.scalar(actual.column(i)[j].as_py())
                    for i in range(actual.num_columns)
                ]
                for j in range(actual.num_rows)
            ]
        driver.control("COMMIT")
        report["transaction"] = "COMMIT_ACK"
    finally:
        try:
            if report["transaction"] == "OPEN":
                driver.control("ROLLBACK")
                report["transaction"] = "ROLLBACK_ACK"
        finally:
            driver.close()
            report["cleanup"] = "CLOSED"
            # Preserve actual raw even when metadata/carrier acceptance fails.
            if config.get("record_path"):
                Path(config["record_path"]).write_text(
                    json.dumps(report, indent=2) + "\n"
                )
    return report


def main():
    if sys.argv[1:] == ["worker"]:
        print(
            json.dumps(
                dict(
                    event="result",
                    data=campaign_worker(json.loads(sys.stdin.readline())),
                )
            ),
            flush=True,
        )
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("campaign",))
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--tree", required=True)
    args = parser.parse_args()
    start = time.monotonic()
    campaign(args)
    print(json.dumps(dict(complete=True, seconds=time.monotonic() - start)))


def oracle_values(rows, columns):
    """Normalize the old independent finite oracle into lossless result notation."""
    from decimal import Decimal
    from uuid import UUID

    converted = []
    for row in rows:
        values = []
        for value, column in zip(row, columns, strict=True):
            kind = column["logical_type"]["name"]
            if value["kind"] == "null":
                decoded = None
            elif kind == "Bool":
                raw = value["value"]
                assert raw in (True, False, "0", "1")
                decoded = raw is True or raw == "1"
            elif value["kind"] == "int":
                decoded = int(value["value"])
            elif value["kind"] == "float":
                decoded = float.fromhex(value["value"])
            elif value["kind"] == "decimal":
                decoded = Decimal(value["value"])
            elif kind == "UUID":
                decoded = UUID(hex=value["value"])
            else:
                decoded = value["value"]
            values.append(prior.s01.scalar(decoded))
        converted.append(values)
    return converted


def check_transport(record, route, sql, args):
    pulls = []
    raw = record["raw"]
    if raw["sql"] != sql or raw["parameters"] != args or "error" in raw:
        raise ValueError("native SQL or arguments")
    if route == "mysql_rows":
        calls = record["native_calls"]
        if [
            c["sql"]
            for c in calls
            if c["method"] == "cmd_stmt_prepare" and c["event"] == "call"
        ] != [sql]:
            raise ValueError("actual native prepare")
        execute = [
            c
            for c in calls
            if c["method"] == "cmd_stmt_execute" and c["event"] == "call"
        ]
        close = [
            c
            for c in calls
            if c["method"] == "cmd_stmt_close" and c["event"] == "return"
        ]
        pulls = [
            c for c in calls if c["method"] == "get_rows" and c["event"] == "return"
        ]
        if (
            len(execute) != 1
            or execute[0]["arguments"] != args
            or len(close) != 1
            or close[0]["statement_id"] != execute[0]["statement_id"]
            or not pulls
            or pulls[-1]["eof"] is None
        ):
            raise ValueError("actual native execute/fetch/close")
        if (
            raw["native"]["close_send"] != "complete_no_ack"
            or raw["native"]["unread_final"] is not False
        ):
            raise ValueError("native statement terminal")
    else:
        calls = raw["api_calls"]
        if not any(
            c["method"] == "execute" and c["sql"] == sql and c["values"] == args
            for c in calls
        ):
            raise ValueError("actual ADBC execute")
        if args and not any(
            c["method"] == "_bind" and c["values"] == args for c in calls
        ):
            raise ValueError("actual ADBC Arrow bind")
    if (
        raw["source_terminal"]
        != ("arrow_StopIteration" if route == "postgres_adbc" else "native_rowset_eof")
        or raw["statement_cleanup"] != "close_returned"
        or record["transaction"] != "COMMIT_ACK"
        or record["cleanup"] != "CLOSED"
    ):
        raise ValueError("bridge terminals")
    from decimal import Decimal

    native_expected = []
    for row in record["rows"]:
        values = []
        for value in row:
            if route == "mysql_rows" and value["kind"] == "bool":
                value = dict(kind="int", value="1" if value["value"] else "0")
            elif value["kind"] == "uuid":
                value = dict(kind="bytes", value=value["value"])
            elif route == "postgres_adbc" and value["kind"] == "decimal":
                coefficient = value["coefficient"]
                number = Decimal(
                    (
                        int(coefficient.startswith("-")),
                        tuple(map(int, coefficient.lstrip("-"))),
                        -value["scale"],
                    )
                )
                value = dict(kind="text", value=format(number, "f"))
            values.append(value)
        native_expected.append(values)
    if raw["actual"] != native_expected:
        raise ValueError("raw native values versus checked consumer")
    if route == "mysql_rows":
        fetched = [row for call in pulls for row in call["rows"]]
        if fetched != raw["raw_actual"]:
            raise ValueError("actual native fetch records")
        decoded = []
        for row in fetched:
            values = []
            for value, meta in zip(row, raw["metadata"], strict=True):
                if value["kind"] == "bytes" and meta[8] != 63:
                    value = dict(
                        kind="text", value=bytes.fromhex(value["value"]).decode("utf-8")
                    )
                values.append(value)
            decoded.append(values)
        if decoded != raw["actual"]:
            raise ValueError("native character transport")


def check_general_record(record, target, case, variant, route):
    from _pietto_phase68_slice5_cases import emission, expected

    document = emission.decode_public(json.dumps(record["public"]).encode())
    expected_rows, ordered = expected(target, case, variant)
    values = oracle_values(expected_rows, document["columns"])
    if route == "postgres_rows":
        check_pg(record, values)
    else:
        args = [prior.s01.scalar(v) for v in emission.decoded_arguments(document)]
        check_transport(record, route, document["sql"], args)
        if Counter(
            map(lambda r: json.dumps(r, sort_keys=True), record["rows"])
        ) != Counter(map(lambda r: json.dumps(r, sort_keys=True), values)):
            raise ValueError("bridge independent complete values")
    if ordered and record["rows"] != values:
        raise ValueError("declared result order")
    widths = {
        "pg_int2": "int16",
        "pg_int4": "int32",
        "pg_int8": "int64",
        "my_smallint": "int16",
        "my_int": "int32",
        "my_bigint": "int64",
        "my_signed_int": "int64",
    }
    expected_schema = []
    for column in document["columns"]:
        kind, rep = column["logical_type"]["name"], column["representation"]
        if kind == "Int":
            typ = widths[rep["storage"]["kind"]]
        elif kind == "Decimal":
            domain = rep["domain"]
            typ = f"decimal{128 if domain['precision'] <= 38 else 256}({domain['precision']}, {domain['scale']})"
        else:
            typ = {"Float": "double", "Text": "string", "Bool": "bool"}[kind]
        expected_schema.append([column["label"], typ, column["nullable"] is not False])
    codes = {
        "pg_int2": 21,
        "pg_int4": 23,
        "pg_int8": 20,
        "pg_bool": 16,
        "pg_float8": 701,
        "pg_text": 25,
        "pg_numeric": 1700,
        "my_smallint": 2,
        "my_int": 3,
        "my_bigint": 8,
        "my_signed_int": 8,
        "my_bool01": 1,
        "my_signed_bool": 8,
        "my_double": 5,
        "my_varchar": 253,
        "my_utf8mb4_text": 253,
        "my_decimal": 246,
    }
    if route != "postgres_adbc":
        actual = (
            record["metadata"]
            if route == "postgres_rows"
            else record["raw"]["metadata"]
        )
        expected_types = [
            [c["label"], codes[c["representation"]["storage"]["kind"]]]
            for c in document["columns"]
        ]
        if [list(m[:2]) for m in actual] != expected_types:
            raise ValueError("independent raw physical metadata")
    else:
        actual = record["raw"]["arrow_schema"]
        for c, meta, expected_field in zip(
            document["columns"], actual, expected_schema, strict=True
        ):
            expected_type = expected_field[1]
            if c["logical_type"]["name"] == "Decimal":
                expected_type = "extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>"
            if (
                meta["name"] != c["label"]
                or meta["ordinal"] != c["ordinal"]
                or meta["type"] != expected_type
            ):
                raise ValueError("independent raw Arrow metadata")
    if record["bound_schema"] != expected_schema:
        raise ValueError("independent checked schema")


def seven_sql(precision, state, target="postgres"):
    import _pietto_phase67_result_product_probe as product

    quote = '"' if target == "postgres" else "`"

    def field(name):
        return quote + name + quote

    return (
        "SELECT "
        + ", ".join(
            field("s0") + "." + field(name) + " AS " + field(label)
            for name, label in zip(
                product.TEMPORAL_NAMES, product.TEMPORAL_LABELS, strict=True
            )
        )
        + " FROM "
        + field("public" if target == "postgres" else "phase66")
        + "."
        + field("p68seven" + str(precision) + "_" + state)
        + " AS "
        + field("s0")
    )


def check_seven_record(record, precision, state, route):
    from _pietto_phase68_slice5_cases import seven_rows
    import _pietto_phase67_result_product_probe as product

    rows = (
        seven_rows("postgres", precision)
        if state == "values"
        else ((None,) * 9,)
        if state == "null"
        else ()
    )
    expected = [[prior.s01.scalar(v) for v in row] for row in rows]
    target = "mysql" if route == "mysql_rows" else "postgres"
    sql = seven_sql(precision, state, target)
    if route == "postgres_rows":
        check_pg(record, expected, expected_sql=sql)
        if [m[:2] for m in record["metadata"]] != [
            [label, oid]
            for label, oid in zip(
                product.TEMPORAL_LABELS,
                (1114, 1114, 2950, 2950, 23, 16, 701, 25, 1700),
                strict=True,
            )
        ]:
            raise ValueError("seven raw metadata")
    else:
        if record["public"]["sql"] != sql:
            raise ValueError("seven original SQL")
        check_transport(record, route, sql, [])
        if route == "mysql_rows":
            metadata = record["raw"]["metadata"]
            codes = (12, 12, 254, 254, 3, 1, 5, 253, 246)
            if (
                [m[:2] for m in metadata]
                != [
                    [name, code]
                    for name, code in zip(product.TEMPORAL_LABELS, codes, strict=True)
                ]
                or metadata[7][8] != 309
                or any(metadata[i][8] != 63 for i in (2, 3))
            ):
                raise ValueError("seven native metadata")
        else:
            metadata = record["raw"]["arrow_schema"]
            expected_types = (
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
            if len(metadata) != 9:
                raise ValueError("seven native metadata")
            for i, (meta, name, typ) in enumerate(
                zip(metadata, product.TEMPORAL_LABELS, expected_types, strict=True)
            ):
                if (
                    type(meta["ordinal"]) is not int
                    or meta["ordinal"] != i
                    or meta["name"] != name
                    or meta["type"] != typ
                ):
                    raise ValueError("seven native metadata")
                if (
                    i in (2, 3, 8)
                    and meta["metadata"].get(b"ADBC:postgresql:typname".hex())
                    != (b"numeric" if i == 8 else b"uuid").hex()
                ):
                    raise ValueError("seven opaque metadata")
        if Counter(json.dumps(r, sort_keys=True) for r in record["rows"]) != Counter(
            json.dumps(r, sort_keys=True) for r in expected
        ):
            raise ValueError("seven bridge values")
    types = [
        "timestamp[us]",
        "timestamp[us]",
        "extension<arrow.uuid>",
        "extension<arrow.uuid>",
        "int32",
        "bool",
        "double",
        "string",
        f"decimal256({precision}, {4 if precision == 39 else 30})",
    ]
    if record["bound_schema"] != [
        [n, t, True] for n, t in zip(product.TEMPORAL_LABELS, types, strict=True)
    ]:
        raise ValueError("seven checked schema")


def campaign_worker(config):
    import hashlib
    import traceback
    from _pietto_phase68_slice5_cases import CASES, build, seven_artifact

    if config["origin"] == "source":
        sys.path.insert(0, str(ROOT / "src"))
    from pietto._project.project_execution import PostgresAccess

    directory = Path(config["directory"])
    directory.mkdir()
    access = PostgresAccess(
        "127.0.0.1",
        config["port"],
        "phase66",
        "pietto_query",
        config["password"],
        "disable",
    )
    report: dict[str, Any] = dict(
        origin=config["origin"],
        route=config["route"],
        prefix=sys.prefix,
        results=[],
        complete=False,
    )
    try:
        for case, variant in CASES:
            key = case + "-" + variant
            outcome = build(directory / (PREFIX + key), config["target"], case, variant)
            if outcome.status == "BLOCKED":
                report["results"].append(
                    dict(
                        key=key,
                        status="BLOCKED",
                        blockers=[[b.code, b.detail] for b in outcome.blockers],
                    )
                )
                continue
            path = directory / (PREFIX + key + ".json")
            config["record_path"] = str(path)
            record = (
                collect_pg(outcome.artifact, access)
                if config["route"] == "postgres_rows"
                else collect_bridge(outcome.artifact, config)
            )
            path.write_text(json.dumps(record, indent=2) + "\n")
            check_general_record(
                json.loads(path.read_text()),
                config["target"],
                case,
                variant,
                config["route"],
            )
            report["results"].append(dict(key=key, status="VERIFIED", file=path.name))
        for precision in (39, 65):
            for state in ("values", "empty", "null"):
                key = "seven-" + str(precision) + "-" + state
                artifact = seven_artifact(
                    directory / (PREFIX + key),
                    config["target"],
                    precision=precision,
                    state=state,
                )
                path = directory / (PREFIX + key + ".json")
                config["record_path"] = str(path)
                record = (
                    collect_pg(artifact, access)
                    if config["route"] == "postgres_rows"
                    else collect_bridge(artifact, config)
                )
                path.write_text(json.dumps(record, indent=2) + "\n")
                check_seven_record(
                    json.loads(path.read_text()), precision, state, config["route"]
                )
                report["results"].append(
                    dict(key=key, status="VERIFIED", file=path.name)
                )
        if config["route"] == "postgres_rows":
            report["bound"] = bound_cases(directory, access)
        report["origins"] = {}
        for name, module in tuple(sys.modules.items()):
            if name == "pietto" or name.startswith("pietto."):
                filename = getattr(module, "__file__", None)
                if filename:
                    path = Path(filename).resolve()
                    if not path.is_relative_to(
                        ROOT / "src/pietto"
                        if config["origin"] == "source"
                        else Path(sys.prefix)
                    ):
                        raise ValueError("foreign production origin")
                    report["origins"][name] = dict(
                        path=str(path),
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
        report["complete"] = True
        return report
    except BaseException:
        (directory / (PREFIX + "failure.txt")).write_text(traceback.format_exc())
        raise
    finally:
        (directory / (PREFIX + "worker.json")).write_text(
            json.dumps(report, indent=2) + "\n"
        )


def bound_cases(directory, access):
    import _pietto_phase67_result_product_probe as product
    from pietto._project.project_execution_template import bind_values

    source = product.source("postgres").replace("renamed = id", "renamed = id + 1")
    template = prior.template(
        directory / (PREFIX + "bound-template"), source, lower=-10, upper=10
    )
    a = bind_values(template, ((template.slots[0], 1),))
    b = bind_values(template, ((template.slots[0], 5),))
    results = []
    for name, binding, offset, control in (
        ("A", a, 1, None),
        ("B", b, 5, None),
        ("A_again", a, 1, None),
        ("cancel", a, 1, "cancel"),
        ("consumer_error", a, 1, "consumer_error"),
    ):
        result = collect_pg(binding.artifact, access, binding=binding, control=control)
        path = directory / (PREFIX + "bound-" + name + ".json")
        path.write_text(json.dumps(result, indent=2) + "\n")
        if control is None:
            check_pg(
                result,
                [
                    [prior.s01.scalar(v) for v in (x + offset, y)]
                    for x, y in ((0, 0), (2, None), (5, 3), (5, 3), (-1, -1))
                ],
            )
            domain = result["public"]["columns"][0]["representation"]["domain"]
            if domain != dict(
                kind="int_range", min=str(-10 + offset), max=str(10 + offset)
            ):
                raise ValueError("value-sensitive original range")
        elif (
            result["outcome"]["transaction"] != "ROLLBACK_ACK"
            or result["outcome"]["delivery"] != "FAILED"
            or result["outcome"]["rows"] != 4
            or not result["control_joined"]
        ):
            raise ValueError("bound control terminal")
        results.append(dict(key=name, file=path.name))
    return results


def campaign(args):
    import subprocess
    import _pietto_target_conformance_cases as fixtures

    args.directory.mkdir(mode=0o700)
    runtime = prior.s01.runtime_identity()
    if runtime["versions"] != prior.s01.helper("_pietto_phase68_executor_cases").PINS:
        raise ValueError("changed pinned runtime")
    report: dict[str, Any] = dict(
        tree=args.tree, runtime=runtime, workers=[], resources=[], complete=False
    )
    try:
        for target in ("postgres", "mysql"):
            root = args.directory / (PREFIX + target)
            root.mkdir()
            pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
            resources = prior.s01.helper(
                "_pietto_target_conformance_resources"
            ).Resources(target, pins["targets"][target], root)
            charge(args.ledger, "source_db_lifecycle_starts", "complete S05 " + target)
            state = dict(target=target)
            report["resources"].append(state)
            try:
                resources.acquire()
                statements = (
                    fixtures.emission_setup(target)
                    + fixtures.native_setup(target)
                    + fixtures.row_domain_setup(target)
                )
                for sql, parameters in statements:
                    if target == "postgres":
                        with resources.manager.cursor() as cursor:
                            cursor.execute(sql, parameters or None)
                    elif not parameters:
                        prior.s03.manager(resources, sql)
                    else:
                        statement = prior.s01.helper(
                            "_pietto_mysql_native_prepared"
                        ).NativeStatement(resources.manager)
                        try:
                            statement.prepare(sql)
                            statement.execute(parameters)
                        finally:
                            statement.close()
                setup_seven(resources)
                if target == "postgres":
                    prior.s03.manager(
                        resources,
                        'CREATE TABLE "rows"(id BIGINT NOT NULL,other BIGINT)',
                    )
                    with resources.manager.cursor() as cursor:
                        cursor.executemany(
                            'INSERT INTO "rows" VALUES($1,$2)',
                            ((0, 0), (2, None), (5, 3), (5, 3), (-1, -1)),
                        )
                for sql, secret in resources.role_statements():
                    prior.s03.manager(resources, sql)
                routes = (
                    (
                        ("postgres_rows", "source"),
                        ("postgres_rows", "installed"),
                        ("postgres_adbc", "source"),
                    )
                    if target == "postgres"
                    else (("mysql_rows", "source"),)
                )
                for route, origin in routes:
                    directory = root / (PREFIX + route + "-" + origin)
                    config = dict(
                        target=target,
                        route=route,
                        origin=origin,
                        port=resources.port,
                        password=resources._passwords[1],
                        ca=str(resources.ca_path),
                        directory=str(directory),
                    )
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-B",
                            str(ROOT / "scripts/phase68_slice5_probe.py"),
                            "worker",
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        bufsize=0,
                    )
                    child = dict(
                        route=route,
                        origin=origin,
                        pid=process.pid,
                        directory=str(directory),
                        exit=None,
                    )
                    report["workers"].append(child)
                    (args.directory / (PREFIX + "report.json")).write_text(
                        json.dumps(report, indent=2) + "\n"
                    )
                    messages = []
                    try:
                        prior.s01._pump_child(
                            process, messages.append, initial=config, seconds=180
                        )
                        if (
                            len(messages) != 1
                            or messages[0]["event"] != "result"
                            or messages[0]["data"]["complete"] is not True
                        ):
                            raise ValueError("worker completion")
                        check_worker(directory, origin, route, prefix=sys.prefix)
                    finally:
                        if process.poll() is None:
                            process.terminate()
                            process.wait(timeout=5)
                        child.update(
                            exit=process.poll(), reaped=process.poll() is not None
                        )
                        for stream in (process.stdin, process.stdout, process.stderr):
                            if stream:
                                stream.close()
            finally:
                state["cleanup"] = resources.cleanup()
                state["events"] = resources.events
            if state["cleanup"]["status"] != "success":
                raise ValueError("owned resources remain")
        report["complete"] = True
    finally:
        (args.directory / (PREFIX + "report.json")).write_text(
            json.dumps(report, indent=2) + "\n"
        )


def check_worker(directory, origin, route, *, prefix):
    from _pietto_phase68_slice5_cases import CASES, emission

    report = json.loads((directory / (PREFIX + "worker.json")).read_text())
    keys = [case + "-" + variant for case, variant in CASES] + [
        "seven-" + str(p) + "-" + s
        for p in (39, 65)
        for s in ("values", "empty", "null")
    ]
    if (
        report["prefix"] != str(prefix)
        or report["origin"] != origin
        or report["route"] != route
        or [r["key"] for r in report["results"]] != keys
        or report["complete"] is not True
    ):
        raise ValueError("worker exact denominator")
    target = "mysql" if route == "mysql_rows" else "postgres"
    for index, result in enumerate(report["results"]):
        if index < len(CASES):
            case, variant = CASES[index]
            expected_status = emission.expected_status(case, variant, target)
            if result["status"] != expected_status:
                raise ValueError("original target boundary")
            if expected_status == "BLOCKED":
                if not result["blockers"]:
                    raise ValueError("absent original blocker")
                continue
        if result["file"] != PREFIX + result["key"] + ".json":
            raise ValueError("foreign case record")
        path = directory / result["file"]
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("case observation budget")
        record = json.loads(path.read_text())
        if index < len(CASES):
            case, variant = CASES[index]
            check_general_record(record, target, case, variant, route)
        else:
            _, precision, state = result["key"].split("-")
            check_seven_record(record, int(precision), state, route)
    if route == "postgres_rows":
        if [b["key"] for b in report["bound"]] != [
            "A",
            "B",
            "A_again",
            "cancel",
            "consumer_error",
        ]:
            raise ValueError("bound denominator")
        for entry in report["bound"]:
            result = json.loads((directory / entry["file"]).read_text())
            name = entry["key"]
            if name in ("A", "B", "A_again"):
                offset = 5 if name == "B" else 1
                expected = [
                    [prior.s01.scalar(v) for v in (x + offset, y)]
                    for x, y in ((0, 0), (2, None), (5, 3), (5, 3), (-1, -1))
                ]
                check_pg(result, expected)
                if result["submissions"][0]["arguments"] != [prior.s01.scalar(offset)]:
                    raise ValueError("bound actual arguments")
                if result["public"]["columns"][0]["representation"]["domain"] != dict(
                    kind="int_range", min=str(-10 + offset), max=str(10 + offset)
                ):
                    raise ValueError("bound range")
            elif (
                result["outcome"]["transaction"] != "ROLLBACK_ACK"
                or result["outcome"]["delivery"] != "FAILED"
                or not result["control_joined"]
            ):
                raise ValueError("bound termination")
    check_origins(report, origin, prefix)
    return report


def check_origins(report, origin, prefix):
    import hashlib

    if report["prefix"] != str(prefix):
        raise ValueError("selected interpreter origin")
    required = (
        "project_result_output",
        "project_result_binding",
        "project_execution_reader",
        "project_arrow_result",
        "project_arrow_interop",
    )
    if any("pietto._project." + name not in report["origins"] for name in required):
        raise ValueError("production consumers absent")
    for name, item in report["origins"].items():
        path = Path(item["path"])
        base = ROOT / "src/pietto" if origin == "source" else Path(report["prefix"])
        if (
            not path.is_relative_to(base)
            or (origin == "installed" and "site-packages" not in path.parts)
            or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
        ):
            raise ValueError("actual production origin")
