"""Independent checker of the public execution witnesses; data only.

It judges the raw facts `_pietto_execution_api_probe` wrote against literal
oracles: the interpreter, the server's TLS and pg_hba.conf rules, the
fixture's rows, the documented examples' output over TLS and on loopback, the
PIE-R codes and terminal states each case must reach, the 10 second statement
limit, the effects an attempt leaves, query bundles and their records, the
refusals of changed bytes, foreign records, values and a code change, the
steps of one loaded bundle, and the absence of every password.
"""

from __future__ import annotations

import ast
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
import json
from typing import Any, cast
from uuid import UUID

FORMAT = "pietto.execution-api-witness.v1"
# fixture.items rows with id > 1, as a bag: the documented query's oracle.
ROWS = [[2, "two"], [2, "two"], [3, "three"], [5, "five"]]
DEMO_SCHEMA = [["id", "int64", False], ["label", "string", False]]
NESTED_SCHEMA = [
    ["renamed", "int64", False],
    ["c", "list<item: struct<i: int64 not null, b: bool, t: string> not null>", False],
]
NESTED_CHILDREN = [
    {"i": 7, "b": True, "t": "a"},
    {"i": 7, "b": True, "t": "a"},
    {"i": 5, "b": None, "t": None},
    {"i": -9223372036854775808, "b": False, "t": ',{}"\\'},
    {"i": 9223372036854775807, "b": True, "t": ""},
    {"i": 0, "b": False, "t": "NULL"},
    {"i": 4, "b": False, "t": "é"},
    {"i": 1, "b": True, "t": "x"},
]
NATIVE_TYPES = {
    "id": "int64",
    "v": "int64",
    "k": "int64",
    "flag": "bool",
    "note": "string",
    "ratio": "double",
    "price": "decimal128(18, 4)",
    "ship_day": "date32[day]",
    "seen_at": "timestamp[us]",
    "token": "extension<arrow.uuid>",
}
NATIVE_OIDS = {
    "id": 20,
    "v": 20,
    "k": 20,
    "flag": 16,
    "note": 25,
    "ratio": 701,
    "price": 1700,
    "ship_day": 1082,
    "seen_at": 1114,
    "token": 2950,
}
UNNEST_PREFLIGHT = {
    ("Int", "Bool", "Text"): [6, 11, [25], 217, 14322, 14322],
    ("Int", "Float", "Decimal"): [6, 11, [], 245, 16170, 16170],
    # U1 is parent id, v, k (three 20-char values) plus Decimal(60, 4).
    # Its escaped widths are 42, 42, 42, 126: 7+3*(4+42)+(4+126)=275;
    # the S12 expanded-row count is 6*11=66, so batch=total=275*66=18150.
    ("Int", "Decimal"): [6, 11, [], 275, 18150, 18150],
    ("Int", "Date", "Timestamp", "UUID"): [6, 11, [], 319, 21054, 21054],
    ("Int", "Bool", "Text", "Float", "Decimal", "Date", "Timestamp", "UUID"): [
        6,
        11,
        [25],
        491,
        32406,
        32406,
    ],
}
COLLECT_PREFLIGHT = {
    # C2 child fields id/v/k/ratio/price have widths 20/20/20/24/20. With
    # 11 children, each array is 4+2+10+11*escaped(width); the parent packet
    # prefix is 7+4+escaped(20)+4+len("11")=59, hence row=2537 and six
    # parent rows give batch=total=15222.
    ("Int", "Float", "Decimal"): [6, 11, [], 2537, 15222, 15222],
    # C2 id/v/k/ship_day/seen_at/token widths are 20/20/20/12/28/38, giving
    # 59+3*478+302+654+874=3323 and batch=total=19938 for six parent rows.
    ("Int", "Date", "Timestamp", "UUID"): [6, 11, [], 3323, 19938, 19938],
    # C1 includes id/v/k/flag/note/ratio/price/ship_day/seen_at/token;
    # Adds Bool 148, Text 588, Float 566 and Decimal 478 to 3323, yielding
    # row=5103 and batch=total=30618 for the all-leaf C1 witness.
    ("Int", "Bool", "Text", "Float", "Decimal", "Date", "Timestamp", "UUID"): [
        6,
        11,
        [25],
        5103,
        30618,
        30618,
    ],
}
DECIMAL256 = Decimal("12345678901234567890123456789012345678901234567856.7890")
AMBIENT = (
    "PGHOST",
    "PGPASSWORD",
    "PGSERVICE",
    "SSLKEYLOGFILE",
    "OPENSSL_CONF",
    "OPENSSL_MODULES",
)
REFUSALS = {
    "premise_none": ["PIE-R1001", "PUBLIC_PREMISE_REQUIRED", False],
    "route_unknown": ["PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE", False],
    "socket_host": ["PIE-R1002", "EXECUTION_ACCESS_PROFILE", False],
    "sql_text": ["PIE-R1002", "PUBLIC_QUERY_TYPE", False],
}
ROLES = ("pietto_cleartext", "pietto_md5", "pietto_trust")
# The interpreter the docs name for the witness.
INTERPRETER = ["CPython", "3.13.13", "Linux", "x86_64"]
# pg_hba.conf as the server reports it, first match first: the refused
# methods, the documented hostssl line and loopback host line of the reader,
# and the fixture's manager.
HBA = [
    ["local", ["all"], "trust"],
    ["host", ["pietto_trust"], "trust"],
    ["host", ["pietto_cleartext"], "password"],
    ["host", ["pietto_md5"], "md5"],
    ["hostssl", ["pietto_reader"], "scram-sha-256"],
    ["host", ["pietto_reader"], "scram-sha-256"],
    ["host", ["pietto_manager"], "scram-sha-256"],
]
TLS = ("TLSv1.2", "TLSv1.3")
EXAMPLE_REPR = (
    "CompiledQuery(module='main.pietto', kind='table', name='active_items',"
    " dialect='postgres', release='18.6', literal_policy='preserve',"
    " origin='live')"
)
# The documented bundle script: the loaded query's origin and slots, then the
# ids with id > 1 and with id > 3, each attempt complete.
BUNDLE_EXAMPLE = ["bundle ('Int',)", "1 [2, 2, 3, 5] COMPLETE", "3 [5] COMPLETE"]
CONSUME_EXAMPLE = [
    "id: int64 not null",
    "label: string not null",
    "COMPLETE 4 [2, 2, 3, 5]",
    "PIE-R3004 FAILED 2",
]
# The documented table compiled bind-safe and loaded from its bundle.
BUNDLE_LOADED = {
    "origin": "bundle",
    "module": "main.pietto",
    "kind": "table",
    "name": "active_items",
    "dialect": "postgres",
    "release": "18.6",
    "literal_policy": "bind-safe",
    "slots": ["Int"],
    "emission": None,
}
# [code, detail, password shown, chained] of each refused bundle input.
BUNDLE_REFUSALS = {
    "tampered": ["PIE-R1007", "COMPILED_CONTENT_PIN", False, False],
    "truncated": ["PIE-R1007", "COMPILED_CONTENT_PIN", False, False],
    "sql_self_pinned": ["PIE-R1008", "COMPILED_JSON", False, False],
    "mixed_records": ["PIE-R1008", "COMPILED_COMPATIBILITY", False, False],
    "foreign_compatibility": ["PIE-R1005", "PUBLIC_BUNDLE_CODE_IDENTITY", False, False],
    "pin_none": ["PIE-R1001", "PUBLIC_TRUST_INPUT_REQUIRED", False, False],
    "bundle_as_pin": ["PIE-R1002", "PUBLIC_TRUST_INPUT_TYPE", False, False],
    "upper_pin": ["PIE-R1002", "PUBLIC_TRUST_INPUT_TYPE", False, False],
    "payload_text": ["PIE-R1002", "PUBLIC_PAYLOAD_TYPE", False, False],
    "payload_bytearray": ["PIE-R1002", "PUBLIC_PAYLOAD_TYPE", False, False],
    "payload_empty": ["PIE-R1002", "PUBLIC_BUNDLE_SIZE", False, False],
    "export_bytes": ["PIE-R1002", "PUBLIC_QUERY_TYPE", False, False],
    "value_bool": ["PIE-R1006", "BINDING_VALUE:0:Int", False, False],
    "value_count": ["PIE-R1006", "BINDING_SLOTS", False, False],
    "values_list": ["PIE-R1002", "PUBLIC_VALUES_TYPE", False, False],
}
# Worker 2 of the code change, on its copied and then changed package.
CODE_CHANGE = {
    "old_records": ["PIE-R1005", "PUBLIC_BUNDLE_CODE_IDENTITY", False, False],
    "relabeled": ["PIE-R1008", "COMPILED_COMPATIBILITY", False, False],
    "execute_live": ["PIE-R1005", "COMPILED_COMPATIBILITY", False, False],
    "execute_loaded": ["PIE-R1005", "COMPILED_COMPATIBILITY", False, False],
    "records_after_change": ["PIE-R1005", "PUBLIC_BUNDLE_CODE_IDENTITY", False, False],
}
RECORD_NAMES = ["accepted_compatibility", "accepted_producer", "expected_pin"]
STEPS = ("first", "other_role", "revoked", "granted", "refused_value", "again")


class Rejected(ValueError):
    pass


def need(condition: object, reason: str) -> None:
    if not condition:
        raise Rejected(reason)


def result(record: Any, reason: Any) -> Any:
    need(type(record) is dict and record.get("returncode") == 0, reason)
    value = record.get("result")
    need(type(value) is dict, reason)
    return value


def hex64(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def check_records(records: Any, reason: str) -> None:
    need(type(records) is dict and sorted(records) == RECORD_NAMES, reason)
    need(all(hex64(v) for v in records.values()), reason)


def check_install(install: Any, recipes: Any) -> None:
    for recipe in recipes:
        commands = install.get(recipe)
        need(type(commands) is dict, "INSTALL")
        for step in ("venv", "install", "check"):
            need(commands.get(step, {}).get("returncode") == 0, "INSTALL")
        need(commands.get("python") == INTERPRETER, "INTERPRETER")


def unopened(value: Any) -> None:
    need(value.get("after_import") == [], "IMPORT_LOADED_DRIVER")
    need(value.get("unopened") == [[], "NOT_STARTED", False], "UNOPENED_EFFECT")


def refused(record: Any, code: Any, detail: Any, reason: Any) -> Any:
    value = result(record, reason)
    unopened(value)
    need((value.get("code"), value.get("detail")) == (code, detail), reason)
    need(value.get("shown") is False and value.get("chained") is False, "CREDENTIAL")
    outcome = value.get("outcome") or {}
    need(
        (outcome.get("end"), outcome.get("transaction"), outcome.get("cleanup"))
        == ("FAILED", "NOT_STARTED", "CLOSED"),
        reason,
    )
    need(record.get("connected") is False, reason)
    return value


def check_consumer_cases(cases: Any) -> None:
    """The database-free laws, from an installed prefix or the checkout."""
    imports = result(cases.get("imports"), "IMPORTS")
    unopened(imports)
    need(imports.get("refusals") == REFUSALS, "REQUEST_REFUSALS")
    need(cases["imports"].get("connected") is False, "IMPORT_CONNECTED")
    ambient = cases.get("ambient") or {}
    need(sorted(ambient) == sorted(AMBIENT), "AMBIENT_DENOMINATOR")
    for name in AMBIENT:
        value = refused(
            ambient[name],
            "PIE-R2003",
            "EXECUTION_AMBIENT_CONNECTION_PROFILE",
            "AMBIENT_" + name,
        )
        need(value.get("after_open") == [], "AMBIENT_LOADED_DRIVER")
        need(ambient[name].get("keylog_created") is False, "KEYLOG_OPENED")
    shadow = cases.get("shadow") or {}
    value = refused(shadow, "PIE-R2002", "EXECUTION_DRIVER_VERSION", "SHADOW")
    need(value.get("psycopg_file") == shadow.get("shadow"), "SHADOW_NOT_IMPORTED")
    need(shadow.get("shadow_imported") is True, "SHADOW_NOT_IMPORTED")
    need(shadow.get("shadow_connected") is False, "SHADOW_CONNECTED")
    # A psycopg_c copy that calls itself binary is refused before psycopg is
    # imported: psycopg never loads and the copy is never imported, so it
    # never receives a connection string.
    copy = cases.get("psycopg_c") or {}
    value = refused(copy, "PIE-R2002", "POSTGRES_DRIVER_LIBRARY", "PSYCOPG_C")
    need(value.get("after_open") == [], "PSYCOPG_C_LOADED")
    need(
        copy.get("copy_imported") is False and copy.get("copy_received") is False,
        "PSYCOPG_C_IMPORTED",
    )
    identity = cases.get("identity") or {}
    clean = result(identity.get("clean"), "IDENTITY")
    stray = result(identity.get("stray"), "IDENTITY")
    need(len(str(clean.get("identity"))) == 64, "IDENTITY")
    need(clean.get("identity") == stray.get("identity"), "IDENTITY_FOLLOWS_CWD")
    need(stray.get("metadata") == "9.9.9", "IDENTITY_CONTROL")
    need(clean.get("metadata") != "9.9.9", "IDENTITY_CONTROL")
    # The stray dist-info changes neither the records an export returns nor
    # what a load accepts; the compatibility is the installed identity.
    exported = clean.get("records")
    need(type(exported) is list and len(exported) == 3, "IDENTITY_BUNDLE")
    need(all(hex64(r) for r in exported), "IDENTITY_BUNDLE")
    need(stray.get("records") == exported, "IDENTITY_BUNDLE")
    need(exported[2] == clean.get("identity"), "IDENTITY_BUNDLE")
    need(clean.get("origin") == stray.get("origin") == "bundle", "IDENTITY_BUNDLE")
    check_bundles(cases.get("bundles"))
    check_code_change(cases.get("code_change") or {})


def check_bundles(record: Any) -> None:
    """Export, load and re-export of one query; unopened attempts with values;
    the refused bundle inputs; nothing loaded, connected or exposed."""
    value = result(record, "BUNDLES")
    unopened(value)
    records = value.get("records")
    need(type(records) is list and len(records) == 3, "BUNDLE_RECORDS")
    need(
        all(hex64(r) for r in [*records, value.get("payload_sha256")]), "BUNDLE_RECORDS"
    )
    need(value.get("equal") == [True, True, True], "BUNDLE_RECORDS")
    need(value.get("loaded") == BUNDLE_LOADED, "BUNDLE_LOADED")
    need(value.get("refusals") == BUNDLE_REFUSALS, "BUNDLE_REFUSALS")
    attempts = value.get("attempts") or []
    need(len(attempts) == 2 and len(set(attempts)) == 2, "BUNDLE_EFFECTS")
    need(value.get("ends") == ["NOT_STARTED", "NOT_STARTED"], "BUNDLE_EFFECTS")
    need(value.get("password_in_payload") is False, "BUNDLE_EFFECTS")
    need(value.get("after") == [], "BUNDLE_EFFECTS")
    need(record.get("connected") is False, "BUNDLE_EFFECTS")


def check_code_change(change: Any) -> None:
    """Worker 2 imported the changed copy; old records, relabeled bytes and,
    after one more change, every earlier query and record are refused."""
    exported = result(change.get("export"), "CODE_CHANGE")
    changed = result(change.get("run"), "CODE_CHANGE")
    check_records(exported.get("records"), "CODE_CHANGE")
    need(changed.get("imported") == change.get("copy"), "CODE_CHANGE_COPY")
    need(exported.get("imported") != change.get("copy"), "CODE_CHANGE_COPY")
    need(changed.get("compatibility_changed") is True, "CODE_CHANGE")
    need(changed.get("own_load") == "bundle", "CODE_CHANGE")
    need(changed.get("refusals") == CODE_CHANGE, "CODE_CHANGE")
    need(change.get("connected") is False, "CODE_CHANGE")


def check_consumer(report: Any) -> Any:
    check_install(report.get("install", {}), ("core", "execute-postgres"))
    core = refused(
        report.get("core"),
        "PIE-R2001",
        "EXECUTION_DEPENDENCY_MISSING",
        "CORE_FALLBACK",
    )
    need(core.get("after_open") == [], "CORE_LOADED_DRIVER")
    schema = result(report.get("core_schema"), "CORE_SCHEMA")
    unopened(schema)
    refused_schema = schema.get("schema") or {}
    need(
        (refused_schema.get("code"), refused_schema.get("detail"))
        == ("PIE-R4004", "EXECUTION_DEPENDENCY_MISSING"),
        "CORE_SCHEMA",
    )
    need(
        refused_schema.get("shown") is False
        and refused_schema.get("chained") is False
        and report["core_schema"].get("connected") is False,
        "CORE_SCHEMA",
    )
    cancelled = result(report.get("core_cancel"), "CORE_CANCEL")
    unopened(cancelled)
    cancel_outcome = cancelled.get("outcome") or {}
    need(
        cancelled.get("cancel_return") is True
        and (cancelled.get("code"), cancelled.get("detail")) == ("PIE-R3009", None)
        and cancelled.get("shown") is False
        and cancelled.get("chained") is False
        and cancel_outcome.get("end") == "CANCELLED"
        and cancel_outcome.get("transaction") == "NOT_STARTED"
        and cancel_outcome.get("cancel") == [True, False, False]
        and report["core_cancel"].get("connected") is False,
        "CORE_CANCEL",
    )
    bundle = refused(
        report.get("core_bundle"),
        "PIE-R2001",
        "EXECUTION_DEPENDENCY_MISSING",
        "CORE_BUNDLE_FALLBACK",
    )
    need(bundle.get("origin") == "bundle", "CORE_BUNDLE_FALLBACK")
    need(bundle.get("after_open") == [], "CORE_LOADED_DRIVER")
    check_consumer_cases(report.get("cases") or {})
    return {"family": "consumer", "verdict": "ACCEPTED"}


def check_mysql(report: Any) -> Any:
    check_install(report.get("install", {}), ("core", "execute-mysql"))
    core = result(report.get("core"), "MYSQL_CORE")
    need(core.get("before") == [], "MYSQL_CORE_IMPORT")
    need(
        core.get("open") == ["PIE-R2001", "EXECUTION_DEPENDENCY_MISSING", False],
        "MYSQL_CORE",
    )
    need(core.get("after") == [], "MYSQL_CORE_IMPORT")
    ambient = report.get("ambient")
    need(
        type(ambient) is dict
        and sorted(ambient) == ["OPENSSL_CONF", "OPENSSL_MODULES", "SSLKEYLOGFILE"],
        "MYSQL_AMBIENT_DENOMINATOR",
    )
    ambient = cast(dict[str, Any], ambient)
    for name, record in ambient.items():
        value = result(record, "MYSQL_AMBIENT_" + name)
        need(value.get("before") == [], "MYSQL_AMBIENT_IMPORT")
        need(
            value.get("request")
            == ["PIE-R2003", "EXECUTION_AMBIENT_CONNECTION_PROFILE", False],
            "MYSQL_AMBIENT_" + name,
        )
        need(value.get("after") == [], "MYSQL_AMBIENT_IMPORT")
    shadow = result(report.get("shadow"), "MYSQL_SHADOW")
    need(shadow.get("before") == [], "MYSQL_SHADOW_IMPORT")
    need(
        shadow.get("open") == ["PIE-R2002", "EXECUTION_DRIVER_VERSION", False],
        "MYSQL_SHADOW",
    )
    need(shadow.get("after") == ["mysql"], "MYSQL_SHADOW_IMPORT")
    return {"family": "mysql", "verdict": "ACCEPTED"}


def check_postgres_adbc(report: Any) -> Any:
    check_install(report.get("install", {}), ("core", "execute-postgres-adbc"))
    core = result(report.get("core"), "ADBC_CORE")
    need(core.get("before") == [], "ADBC_CORE_IMPORT")
    need(
        core.get("open") == ["PIE-R2001", "EXECUTION_DEPENDENCY_MISSING", False],
        "ADBC_CORE",
    )
    need(core.get("after") == [], "ADBC_CORE_IMPORT")
    ambient = report.get("ambient")
    need(
        type(ambient) is dict
        and sorted(ambient) == ["OPENSSL_CONF", "OPENSSL_MODULES", "SSLKEYLOGFILE"],
        "ADBC_AMBIENT_DENOMINATOR",
    )
    ambient = cast(dict[str, Any], ambient)
    for name, record in ambient.items():
        value = result(record, "ADBC_AMBIENT_" + name)
        need(value.get("before") == [], "ADBC_AMBIENT_IMPORT")
        need(
            value.get("request")
            == ["PIE-R2003", "EXECUTION_AMBIENT_CONNECTION_PROFILE", False],
            "ADBC_AMBIENT_" + name,
        )
        need(value.get("after") == [], "ADBC_AMBIENT_IMPORT")
    shadow = result(report.get("shadow"), "ADBC_SHADOW")
    need(shadow.get("before") == [], "ADBC_SHADOW_IMPORT")
    need(
        shadow.get("open") == ["PIE-R2002", "POSTGRES_ADBC_DRIVER_PROFILE", False],
        "ADBC_SHADOW",
    )
    need(shadow.get("after") == ["adbc_driver_postgresql"], "ADBC_SHADOW_IMPORT")
    return {"family": "postgres_adbc", "verdict": "ACCEPTED"}


def outcome_of(value: Any, reason: Any) -> Any:
    outcome = value.get("outcome")
    need(type(outcome) is dict, reason)
    ack = outcome.get("transaction") in ("COMMIT_ACK", "ROLLBACK_ACK")
    need(
        outcome.get("remote")
        == ("TRANSACTION_ACK" if ack else "REMOTE_QUIESCENCE_UNCONFIRMED"),
        reason,
    )
    cancel = outcome.get("cancel")
    need(
        type(cancel) is list
        and len(cancel) == 3
        and all(type(value) is bool for value in cancel)
        and (not cancel[1] or cancel[0])
        and (not cancel[2] or cancel[0]),
        reason,
    )
    return outcome


def check_server(server: Any) -> None:
    need(server.get("version") == "180006", "SERVER_VERSION")
    need(server.get("ssl") == "on", "SERVER_TLS")
    need(server.get("password_encryption") == "scram-sha-256", "SCRAM_DEFAULT")
    need(
        server.get("reader_settings") == ["statement_timeout=0"],
        "READER_STATEMENT_LIMIT",
    )
    hba = server.get("hba") or []
    need(all(row[3] is None for row in hba), "HBA_ERROR")
    need([row[:3] for row in hba] == HBA, "HBA_METHODS")
    hashes = {row[0]: (row[1], row[2]) for row in server.get("hashes") or []}
    need(hashes.get("pietto_reader") == (True, False), "SCRAM_ROLE")
    need(hashes.get("pietto_cleartext") == (True, False), "SCRAM_ROLE")
    need(hashes.get("pietto_md5") == (False, True), "MD5_ROLE")


def check_effects(value: Any, reason: str) -> None:
    """An attempt that ended leaves no thread, no workspace module and no
    file in the working directory, HOME or TMPDIR."""
    before, after = value.get("before") or {}, value.get("after") or {}
    need(after.get("threads") == ["MainThread"], reason + "_THREADS")
    need(before.get("jobs") == [] and after.get("jobs") == [], reason + "_WORKSPACE")
    files = before.get("files") or {}
    need(sorted(files) == ["cwd", "home", "tmp"], reason + "_FILES")
    need(files["home"] == files["tmp"] == [], reason + "_FILES")
    need(after.get("files") == files, reason + "_FILES")


def check_example(record: Any) -> None:
    need(type(record) is dict and record.get("returncode") == 0, "EXAMPLE")
    need(record.get("shown") is False, "CREDENTIAL")
    lines = record.get("stdout", "").strip().splitlines()
    need(len(lines) >= 3 and lines[0] == EXAMPLE_REPR, "EXAMPLE_COMPILE")
    need(
        lines[-2:] == ["COMPLETE COMMIT_ACK CLOSED", "PIE-R1001 INPUT_MISSING"],
        "EXAMPLE_END",
    )
    found: list[list[Any]] = []
    for line in lines[1:-2]:
        batch: list[dict[str, Any]] = ast.literal_eval(line)
        need(type(batch) is list and batch, "EXAMPLE_BATCH")
        found.extend([row["id"], row["label"]] for row in batch)
    need(Counter(map(tuple, found)) == Counter(map(tuple, ROWS)), "EXAMPLE_ROWS")


def check_bundle_example(record: Any) -> None:
    need(type(record) is dict and record.get("returncode") == 0, "BUNDLE_EXAMPLE")
    need(record.get("shown") is False, "CREDENTIAL")
    lines = record.get("stdout", "").strip().splitlines()
    need(lines == BUNDLE_EXAMPLE, "BUNDLE_EXAMPLE")


def check_consume_example(record: Any) -> None:
    need(type(record) is dict and record.get("returncode") == 0, "CONSUME_EXAMPLE")
    need(record.get("shown") is False, "CREDENTIAL")
    need(
        record.get("stdout", "").strip().splitlines() == CONSUME_EXAMPLE,
        "CONSUME_EXAMPLE",
    )


def completed(record: Any, rows: Any, reason: str) -> None:
    outcome = record.get("outcome") or {}
    need("code" not in record and record.get("rows") == rows, reason)
    need(
        (outcome.get("end"), outcome.get("transaction")) == ("COMPLETE", "COMMIT_ACK"),
        reason,
    )


def check_nested_preflight(value: Any) -> None:
    """Independently match the fixed fixture's native source-bound receipt."""
    need(
        type(value) is dict and value.get("identity") == [True] * 6,
        "NESTED_PREFLIGHT_IDENTITY",
    )
    # Five parents, eight physical children, Text <= 5 UTF-8 bytes: each
    # carrier DataRow <= 625 bytes and the five-row batch/total <= 3125.
    need(
        json.dumps(value.get("bounds"), allow_nan=False)
        == json.dumps([5, 8, [5], 625, 3125, 3125]),
        "NESTED_PREFLIGHT_BOUNDS",
    )
    replies = value.get("replies")
    need(type(replies) is list and len(replies) == 4, "NESTED_PREFLIGHT_REPLIES")
    assert type(replies) is list
    expected = (
        (
            "SELECT current_setting('server_encoding')",
            [],
            "current_setting",
            25,
            "UTF8",
        ),
        (
            'SELECT COUNT(*) FROM (SELECT 1 FROM "public"."rows" LIMIT $1) AS "__pietto_nested_bound"',
            [65],
            "count",
            20,
            5,
        ),
        (
            'SELECT COUNT(*) FROM (SELECT 1 FROM "public"."kids" LIMIT $1) AS "__pietto_nested_bound"',
            [17],
            "count",
            20,
            8,
        ),
        (
            'SELECT COALESCE(MAX(LEAST(COALESCE(octet_length("t"),0),$1)),0) FROM "public"."kids"',
            [257],
            "coalesce",
            23,
            5,
        ),
    )
    for reply, (sql, arguments, label, oid, scalar) in zip(
        replies, expected, strict=True
    ):
        need(type(reply) is list and len(reply) == 5, "NESTED_PREFLIGHT_REPLIES")
        wanted = [sql, arguments, [[0, label, oid]], [[scalar]], 2]
        need(
            json.dumps(reply, allow_nan=False) == json.dumps(wanted),
            "NESTED_PREFLIGHT_REPLY",
        )


def check_nested(record: Any, *, closed: bool, bundle: bool = False) -> None:
    value = result(record, "NESTED")
    need(value.get("schema") == NESTED_SCHEMA, "NESTED_SCHEMA")
    preopen = value.get("schema_preopen") or {}
    need(
        preopen.get("closed") is False
        and preopen.get("end") == "NOT_STARTED"
        and preopen.get("loaded") == ["pyarrow"],
        "NESTED_SCHEMA_PREOPEN",
    )
    rows = value.get("rows")
    need(type(rows) is list and len(rows) == 5, "NESTED_PARENT_ROWS")
    nested_rows = cast(list[dict[str, Any]], rows)
    need(
        all(
            type(row) is dict
            and set(row) == {"renamed", "c"}
            and type(row["c"]) is list
            for row in nested_rows
        ),
        "NESTED_ROWS",
    )
    need(
        all(type(row["renamed"]) is int for row in nested_rows), "NESTED_PARENT_VALUES"
    )
    parents = Counter(row["renamed"] for row in nested_rows)
    need(parents == Counter({0: 1, 2: 1, 5: 2, 7: 1}), "NESTED_PARENT_VALUES")
    import _pietto_execution_nested_oracle as oracle

    def tie(*indexes):
        return oracle.Segment(
            tuple(NESTED_CHILDREN[index] for index in indexes), len(indexes)
        )

    # Native fixture seq groups; ties permit permutations, never another parent.
    closed_groups = (tie(0, 2, 3, 7), tie(1, 4, 5), tie(6))
    captured_groups = {
        0: (tie(0), tie(1)),
        2: (tie(2),),
        5: (tie(3), tie(4, 5), tie(6)),
        7: (),
    }
    for row in nested_rows:
        children = row["c"]
        need(
            all(
                type(child) is dict and set(child) == {"i", "b", "t"}
                for child in children
            ),
            "NESTED_ROWS",
        )
        ordered = [{key: child[key] for key in ("i", "b", "t")} for child in children]
        expected = closed_groups if closed else captured_groups[row["renamed"]]
        need(
            not oracle.check(ordered, expected),
            "NESTED_CLOSED" if closed else "NESTED_CAPTURED",
        )
    if not closed:
        by_parent = [row for row in nested_rows if row["renamed"] == 7]
        need(len(by_parent) == 1 and by_parent[0]["c"] == [], "NESTED_EMPTY")
        need(
            any(
                child["b"] is None and child["t"] is None
                for row in nested_rows
                for child in row["c"]
            ),
            "NESTED_NULLABLE",
        )
    outcome = outcome_of(value, "NESTED")
    need(
        (
            outcome.get("end"),
            outcome.get("transaction"),
            outcome.get("cleanup"),
            outcome.get("rows"),
        )
        == ("COMPLETE", "COMMIT_ACK", "CLOSED", 5),
        "NESTED_END",
    )
    need(value.get("origin") == ("bundle" if bundle else "live"), "NESTED_ORIGIN")
    check_nested_preflight(value.get("preflight"))
    check_effects(value, "NESTED")


def _fields(leaves) -> tuple[str, ...]:
    import _pietto_execution_nested_oracle as oracle

    return oracle.child_fields(leaves)


def _untag(value):
    if type(value) is list:
        return [_untag(item) for item in value]
    if type(value) is not dict:
        return value
    tag_keys = set(value)
    if tag_keys not in (
        {"kind", "value"},
        {"fold", "kind", "value"},
        {"kind", "tuple", "value"},
    ):
        return {key: _untag(item) for key, item in value.items()}
    kind, raw = value["kind"], value["value"]
    try:
        if kind == "float" and type(raw) is str and set(value) == {"kind", "value"}:
            return float.fromhex(raw)
        if (
            kind == "decimal"
            and type(raw) is str
            and tag_keys == {"kind", "tuple", "value"}
        ):
            parts = value["tuple"]
            decimal = Decimal(raw)
            if (
                type(parts) is list
                and len(parts) == 3
                and type(parts[0]) is int
                and type(parts[1]) is list
                and type(parts[2]) is int
                and decimal.as_tuple() == (parts[0], tuple(parts[1]), parts[2])
            ):
                return decimal
            raise ValueError
        if kind == "date" and type(raw) is str and set(value) == {"kind", "value"}:
            return date.fromisoformat(raw)
        if (
            kind == "timestamp"
            and type(raw) is str
            and tag_keys == {"fold", "kind", "value"}
            and value["fold"] == 0
        ):
            return datetime.fromisoformat(raw).replace(fold=0)
        if kind == "uuid" and type(raw) is str and set(value) == {"kind", "value"}:
            return UUID(hex=raw)
    except (TypeError, ValueError):
        pass
    raise Rejected("NATIVE_TAG")


def _unnest_preflight(value: Any, leaves, relation="orders") -> None:
    need(
        type(value) is dict and value.get("identity") == [True] * 6,
        "UNNEST_PREFLIGHT_IDENTITY",
    )
    bounds = value.get("bounds")
    need(bounds == UNNEST_PREFLIGHT[tuple(leaves)], "UNNEST_PREFLIGHT_BOUNDS")
    replies = [
        [
            "SELECT current_setting('server_encoding')",
            [],
            [[0, "current_setting", 25]],
            [["UTF8"]],
            2,
        ],
        [
            'SELECT COUNT(*) FROM (SELECT 1 FROM "public"."customers" LIMIT $1) AS "__pietto_nested_bound"',
            [65],
            [[0, "count", 20]],
            [[6]],
            2,
        ],
        [
            f'SELECT COUNT(*) FROM (SELECT 1 FROM "public"."{relation}" LIMIT $1) AS "__pietto_nested_bound"',
            [17],
            [[0, "count", 20]],
            [[11]],
            2,
        ],
    ]
    if "Text" in leaves:
        replies.append(
            [
                f'SELECT COALESCE(MAX(LEAST(COALESCE(octet_length("note"),0),$1)),0) FROM "public"."{relation}"',
                [257],
                [[0, "coalesce", 23]],
                [[25]],
                2,
            ]
        )
    need(value.get("replies") == replies, "UNNEST_PREFLIGHT_REPLIES")


def _collect_preflight(value: Any, leaves) -> None:
    need(
        type(value) is dict and value.get("identity") == [True] * 6,
        "NESTED_PREFLIGHT_IDENTITY",
    )
    need(
        value.get("bounds") == COLLECT_PREFLIGHT[tuple(leaves)],
        "NESTED_PREFLIGHT_BOUNDS",
    )
    replies = [
        [
            "SELECT current_setting('server_encoding')",
            [],
            [[0, "current_setting", 25]],
            [["UTF8"]],
            2,
        ],
        [
            'SELECT COUNT(*) FROM (SELECT 1 FROM "public"."customers" LIMIT $1) AS "__pietto_nested_bound"',
            [65],
            [[0, "count", 20]],
            [[6]],
            2,
        ],
        [
            'SELECT COUNT(*) FROM (SELECT 1 FROM "public"."orders" LIMIT $1) AS "__pietto_nested_bound"',
            [17],
            [[0, "count", 20]],
            [[11]],
            2,
        ],
    ]
    if "Text" in leaves:
        replies.append(
            [
                'SELECT COALESCE(MAX(LEAST(COALESCE(octet_length("note"),0),$1)),0) FROM "public"."orders"',
                [257],
                [[0, "coalesce", 23]],
                [[25]],
                2,
            ]
        )
    need(value.get("replies") == replies, "NESTED_PREFLIGHT_REPLIES")


def _replace_decimal256(value):
    if type(value) is list:
        return [_replace_decimal256(item) for item in value]
    if type(value) is dict:
        return {key: _replace_decimal256(item) for key, item in value.items()}
    return DECIMAL256 if value == Decimal("99999999999999.9999") else value


def check_unnest(
    record: Any, name: str, leaves=None, *, bundle: bool = False, decimal256=False
) -> None:
    import _pietto_execution_nested_oracle as oracle

    leaves = oracle.DEFAULT_LEAVES if leaves is None else oracle.leaves_of(leaves)
    labels = ("id", *_fields(leaves))
    value = result(record, "UNNEST")
    schema = [[label, NATIVE_TYPES[label], True] for label in labels]
    if decimal256:
        schema[labels.index("price")][1] = "decimal256(60, 4)"
    need(value.get("schema") == schema, "UNNEST_SCHEMA")
    need(
        value.get("schema_preopen")
        == {"closed": False, "end": "NOT_STARTED", "loaded": ["pyarrow"]},
        "UNNEST_SCHEMA_PREOPEN",
    )
    raw_rows = value.get("rows")
    need(type(raw_rows) is list, "UNNEST_ROWS")
    rows = []
    for row in raw_rows:
        need(type(row) is dict and set(row) == set(labels), "UNNEST_ROWS")
        rows.append({label: _untag(row[label]) for label in labels})
    expected = oracle.expected(name, "FULL", leaves)
    if decimal256:
        expected = tuple(
            oracle.Segment(
                tuple(_replace_decimal256(item) for item in segment.candidates),
                segment.take,
            )
            for segment in expected
        )
    need(not oracle.check(rows, expected), "UNNEST_ROWS")
    count = sum(segment.take for segment in expected)
    outcome = outcome_of(value, "UNNEST")
    need(
        (
            outcome.get("end"),
            outcome.get("transaction"),
            outcome.get("cleanup"),
            outcome.get("rows"),
        )
        == ("COMPLETE", "COMMIT_ACK", "CLOSED", count),
        "UNNEST_END",
    )
    need(value.get("origin") == ("bundle" if bundle else "live"), "UNNEST_ORIGIN")
    need(
        value.get("metadata")
        == [[label, NATIVE_OIDS[label], None] for label in labels],
        "UNNEST_METADATA",
    )
    _unnest_preflight(
        value.get("preflight"),
        leaves,
        "orders_decimal256" if decimal256 else "orders",
    )
    check_effects(value, "UNNEST")


def check_oracle_nested(
    record: Any, name: str, leaves, *, bundle: bool = False
) -> None:
    import _pietto_execution_nested_oracle as oracle

    leaves = oracle.leaves_of(leaves)
    program = oracle.program(name, leaves)
    let = cast(Any, program.spec).lets[0]
    child = ", ".join(
        field + ": " + NATIVE_TYPES[field] + (" not null" if field == "id" else "")
        for field in ("id", *_fields(leaves))
    )
    value = result(record, "NESTED_FULL")
    need(
        value.get("schema")
        == [
            ["id", "int64", True],
            [let.name, "list<item: struct<" + child + "> not null>", False],
        ],
        "NESTED_SCHEMA",
    )
    need(
        value.get("schema_preopen")
        == {"closed": False, "end": "NOT_STARTED", "loaded": ["pyarrow"]},
        "NESTED_SCHEMA_PREOPEN",
    )
    raw_rows = value.get("rows")
    need(type(raw_rows) is list, "NESTED_ROWS")
    assert isinstance(raw_rows, list)
    child_labels = ("id", *_fields(leaves))
    rows = []
    for row in raw_rows:
        need(type(row) is dict and set(row) == {"id", let.name}, "NESTED_ROWS")
        children = row[let.name]
        need(type(children) is list, "NESTED_ROWS")
        assert isinstance(children, list)
        ordered = []
        for child_row in children:
            need(
                type(child_row) is dict and set(child_row) == set(child_labels),
                "NESTED_ROWS",
            )
            ordered.append({label: _untag(child_row[label]) for label in child_labels})
        # JSON object order is not the already-verified Arrow field order.
        rows.append({"id": _untag(row["id"]), let.name: ordered})
    expected = oracle.expected(name, "FULL", leaves)
    need(not oracle.check(rows, expected), "NESTED_ROWS")
    count = sum(segment.take for segment in expected)
    outcome = outcome_of(value, "NESTED_FULL")
    need(
        (
            outcome.get("end"),
            outcome.get("transaction"),
            outcome.get("cleanup"),
            outcome.get("rows"),
        )
        == ("COMPLETE", "COMMIT_ACK", "CLOSED", count),
        "NESTED_END",
    )
    need(value.get("origin") == ("bundle" if bundle else "live"), "NESTED_ORIGIN")
    _collect_preflight(value.get("preflight"), leaves)
    check_effects(value, "NESTED_FULL")


def check_steps(steps: Any) -> None:
    """One bundle loaded once without its source, then each step on it: the
    reader with values 1, 3 and 1 again, a refused role, the revoked and
    granted privilege, a refused value; distinct attempts and no effects."""
    need(steps.get("returncode") == 0, "BUNDLE_STEPS")
    records = steps.get("records") or []
    need(len(records) == len(STEPS) + 2, "BUNDLE_STEPS")
    first, *done, after = records
    need(
        first == {"loaded": BUNDLE_LOADED, "source_present": False},
        "BUNDLE_STEPS_LOADED",
    )
    need([r.get("step") for r in done] == list(STEPS), "BUNDLE_STEPS")
    by = {r["step"]: r for r in done}
    completed(by["first"], sorted(ROWS), "BUNDLE_STEPS_FIRST")
    completed(by["granted"], [[5, "five"]], "BUNDLE_STEPS_GRANTED")
    completed(by["again"], sorted(ROWS), "BUNDLE_STEPS_AGAIN")
    role = by["other_role"]
    outcome = role.get("outcome") or {}
    need(
        (role.get("code"), outcome.get("end"), outcome.get("transaction"))
        == ("PIE-R2004", "FAILED", "NOT_STARTED"),
        "BUNDLE_STEPS_OTHER_ROLE",
    )
    revoked = by["revoked"]
    need(
        (
            revoked.get("code"),
            revoked.get("sqlstate"),
            (revoked.get("outcome") or {}).get("end"),
        )
        == ("PIE-R3003", "42501", "FAILED"),
        "BUNDLE_STEPS_REVOKED",
    )
    value = by["refused_value"]
    need(
        (value.get("code"), value.get("detail"), value.get("attempt"))
        == ("PIE-R1006", "BINDING_VALUE:0:Int", None)
        and "outcome" not in value,
        "BUNDLE_STEPS_REFUSED_VALUE",
    )
    for record in done:
        need(
            record.get("shown", False) is False
            and record.get("chained", False) is False,
            "CREDENTIAL",
        )
    attempts = [r.get("attempt") for r in done if r.get("attempt") is not None]
    need(len(attempts) == 5 and len(set(attempts)) == 5, "BUNDLE_STEPS_ATTEMPTS")
    need(after.get("threads") == ["MainThread"], "BUNDLE_STEPS_THREADS")
    need(after.get("jobs") == [], "BUNDLE_STEPS_WORKSPACE")
    need(after.get("files") == {"cwd": [], "home": [], "tmp": []}, "BUNDLE_STEPS_FILES")


def composed_expectation(*, outer, grouped=False):
    schema = (
        [["id", "int64", False]]
        if outer
        else [[name, "int64", False] for name in ("parent_id", "child_id", "tag_id")]
    )
    schema.append(
        ["retained", "list<item: struct<id: int64 not null> not null>", outer]
    )
    rows = (
        [{"id": 7, "retained": None}]
        if outer
        else [
            {
                "parent_id": parent,
                "child_id": child,
                "tag_id": child,
                "retained": [{"id": 1}, {"id": 2}],
            }
            for parent in (1, 2)
            for child in ((2,) if grouped else (1, 2, 3))
        ]
    )
    prefix = "pietto_s16_outer_" if outer else "pietto_s16_"
    sources = (
        [("tags", 1, 65), ("rows", 0, 17), ("orders", 2, 17)]
        if outer
        else [("rows", 2, 17), ("tags", 3, 65), ("orders", 4, 17)]
    )
    replies = [
        [
            "SELECT current_setting('server_encoding')",
            [],
            [[0, "current_setting", 25]],
            [["UTF8"]],
            2,
        ]
    ]
    replies.extend(
        [
            f'SELECT COUNT(*) FROM (SELECT 1 FROM "public"."{prefix}{name}" LIMIT $1) AS "__pietto_nested_bound"',
            [cap],
            [[0, "count", 20]],
            [[count]],
            2,
        ]
        for name, count, cap in sources
    )
    preflight = {
        "identity": [True] * 6,
        "bounds": [1, 2, [], 65, 65, 65] if outer else [2, 4, [], 241, 5784, 5784],
        "source_counts": [
            ["public", prefix + name, count] for name, count, _ in sources
        ],
        "group_counts": [2, 0] if outer else [4, 2],
        "replies": replies,
    }
    return schema, rows, preflight


def check_composed_nested(record, *, outer, grouped=False):
    value = result(record, "COMPOSED_NESTED")
    schema, rows, preflight = composed_expectation(outer=outer, grouped=grouped)
    need(value.get("schema") == schema, "COMPOSED_SCHEMA")
    need(
        type(value.get("rows")) is list
        and Counter(json.dumps(row, sort_keys=True) for row in value["rows"])
        == Counter(json.dumps(row, sort_keys=True) for row in rows),
        "COMPOSED_ROWS",
    )
    need(value.get("origin") == ("live" if outer else "bundle"), "COMPOSED_ORIGIN")
    need(
        value.get("schema_preopen")
        == {"closed": False, "end": "NOT_STARTED", "loaded": ["pyarrow"]},
        "COMPOSED_PREOPEN",
    )
    need(value.get("preflight") == preflight, "COMPOSED_PREFLIGHT")
    need(
        value.get("binding")
        == {"parameters": [1] if grouped else [], "arguments": [1] if grouped else []},
        "COMPOSED_BINDING",
    )
    outcome = outcome_of(value, "COMPOSED")
    need(
        (
            outcome.get("end"),
            outcome.get("transaction"),
            outcome.get("cleanup"),
            outcome.get("rows"),
        )
        == ("COMPLETE", "COMMIT_ACK", "CLOSED", len(rows)),
        "COMPOSED_END",
    )
    check_effects(value, "COMPOSED")


def check_postgres(report: Any) -> Any:
    check_install(report.get("install", {}), ("execute-postgres",))
    check_server(report.get("server") or {})
    check_example(report.get("example"))
    check_example(report.get("example_loopback"))
    bind = result(report.get("bind_safe"), "BIND_SAFE")
    need(bind.get("schema") == DEMO_SCHEMA, "RESULT_SCHEMA")
    preopen = bind.get("schema_preopen") or {}
    need(
        preopen.get("closed") is False
        and preopen.get("end") == "NOT_STARTED"
        and preopen.get("loaded") == ["pyarrow"],
        "RESULT_SCHEMA_PREOPEN",
    )
    need(bind.get("rows") == sorted(ROWS), "BIND_SAFE_ROWS")
    outcome = outcome_of(bind, "BIND_SAFE")
    need(
        (outcome["end"], outcome["transaction"], outcome["cleanup"], outcome["rows"])
        == ("COMPLETE", "COMMIT_ACK", "CLOSED", 4),
        "BIND_SAFE_END",
    )
    check_effects(bind, "BIND_SAFE")
    empty = result(report.get("schema_empty"), "EMPTY_RESULT")
    need(empty.get("schema") == DEMO_SCHEMA and empty.get("rows") == [], "EMPTY_RESULT")
    need(
        empty.get("schema_preopen") == preopen,
        "EMPTY_RESULT_PREOPEN",
    )
    empty_outcome = outcome_of(empty, "EMPTY_RESULT")
    need(
        (empty_outcome["end"], empty_outcome["transaction"], empty_outcome["rows"])
        == ("COMPLETE", "COMMIT_ACK", 0),
        "EMPTY_RESULT",
    )
    for key, name in (
        ("unnest_cross", "U1_cross"),
        ("unnest_inner", "U2_inner_true"),
        ("unnest_left", "U4_left_true"),
        ("unnest_left_on", "U5_left_v_gt_10"),
        ("unnest_bundle", "U4_left_true"),
    ):
        check_unnest(report.get(key), name, bundle=key == "unnest_bundle")
    for key, name, leaves, bundle in (
        ("unnest_float_decimal", "U1_cross", ("Int", "Float", "Decimal"), False),
        (
            "unnest_temporal",
            "U2_inner_true",
            ("Int", "Date", "Timestamp", "UUID"),
            False,
        ),
        (
            "unnest_full_bundle",
            "U4_left_true",
            ("Int", "Bool", "Text", "Float", "Decimal", "Date", "Timestamp", "UUID"),
            True,
        ),
    ):
        check_unnest(report.get(key), name, leaves, bundle=bundle)
    check_unnest(
        report.get("unnest_decimal256"),
        "U1_cross",
        ("Int", "Decimal"),
        decimal256=True,
    )
    for key, name, leaves, bundle in (
        ("nested_float_decimal", "C2_captured", ("Int", "Float", "Decimal"), False),
        ("nested_temporal", "C2_captured", ("Int", "Date", "Timestamp", "UUID"), False),
        (
            "nested_full_bundle",
            "C1_closed",
            ("Int", "Bool", "Text", "Float", "Decimal", "Date", "Timestamp", "UUID"),
            True,
        ),
    ):
        check_oracle_nested(report.get(key), name, leaves, bundle=bundle)
    check_composed_nested(report.get("nested_retained_bundle"), outer=False)
    check_composed_nested(report.get("nested_outer_null"), outer=True)
    check_composed_nested(
        report.get("nested_grouped_parameter_bundle"), outer=False, grouped=True
    )
    unnest_limit = result(report.get("unnest_limit"), "UNNEST_LIMIT")
    unnest_outcome = outcome_of(unnest_limit, "UNNEST_LIMIT")
    need(
        (
            unnest_limit.get("code"),
            unnest_limit.get("detail"),
            unnest_limit.get("submitted"),
        )
        == ("PIE-R3004", "POSTGRES_SOURCE_RESOURCE_LIMIT", False),
        "UNNEST_LIMIT",
    )
    need(
        (
            unnest_outcome.get("end"),
            unnest_outcome.get("transaction"),
            unnest_outcome.get("cleanup"),
            unnest_outcome.get("rows"),
            unnest_outcome.get("batches"),
        )
        == ("FAILED", "ROLLBACK_ACK", "CLOSED", 0, 0),
        "UNNEST_LIMIT_END",
    )
    check_nested(report.get("nested_captured"), closed=False)
    check_nested(report.get("nested_closed"), closed=True)
    check_nested(report.get("nested_bundle"), closed=True, bundle=True)
    nested_stopped = result(report.get("nested_stopped"), "NESTED_STOPPED")
    need(nested_stopped.get("schema") == NESTED_SCHEMA, "NESTED_STOPPED_SCHEMA")
    nested_stop_outcome = outcome_of(nested_stopped, "NESTED_STOPPED")
    need(
        nested_stopped.get("first_rows") > 0
        and (
            nested_stop_outcome.get("end"),
            nested_stop_outcome.get("transaction"),
            nested_stop_outcome.get("primary"),
        )
        == ("STOPPED_EARLY", "ROLLBACK_ACK", None),
        "NESTED_STOPPED",
    )
    check_effects(nested_stopped, "NESTED_STOPPED")
    nested_cancelled = result(report.get("nested_cancelled"), "NESTED_CANCEL")
    nested_cancel_outcome = outcome_of(nested_cancelled, "NESTED_CANCEL")
    need(
        nested_cancelled.get("cancel_return") is True
        and (nested_cancelled.get("code"), nested_cancelled.get("detail"))
        == ("PIE-R3009", None)
        and nested_cancelled.get("shown") is False
        and nested_cancelled.get("chained") is False
        and (
            nested_cancel_outcome.get("end"),
            nested_cancel_outcome.get("transaction"),
            nested_cancel_outcome.get("cancel"),
        )
        == ("CANCELLED", "NOT_STARTED", [True, False, False]),
        "NESTED_CANCEL",
    )
    nested_refused = result(report.get("nested_refused"), "NESTED_BOUND")
    nested_refusal_outcome = outcome_of(nested_refused, "NESTED_BOUND")
    need(
        nested_refused.get("schema") == NESTED_SCHEMA
        and nested_refused.get("opened") is not True
        and (nested_refused.get("code"), nested_refused.get("detail"))
        == ("PIE-R3004", "POSTGRES_SOURCE_RESOURCE_LIMIT")
        and nested_refused.get("shown") is False
        and nested_refused.get("chained") is False
        and (
            nested_refusal_outcome.get("end"),
            nested_refusal_outcome.get("rows"),
            nested_refusal_outcome.get("batches"),
        )
        == ("FAILED", 0, 0),
        "NESTED_BOUND",
    )
    early = result(report.get("early_stop"), "EARLY_STOP")
    outcome = outcome_of(early, "EARLY_STOP")
    need(early.get("first_rows") == 1, "EARLY_STOP")
    need(
        (outcome["end"], outcome["transaction"], outcome["rows"], outcome["primary"])
        == ("STOPPED_EARLY", "ROLLBACK_ACK", 1, None),
        "EARLY_STOP_END",
    )
    check_effects(early, "EARLY_STOP")
    interrupted = result(report.get("interrupt"), "INTERRUPT")
    interrupted_outcome = outcome_of(interrupted, "INTERRUPT")
    need(
        interrupted.get("reraised") is True
        and (interrupted_outcome.get("end"), interrupted_outcome.get("transaction"))
        == ("FAILED", "ROLLBACK_ACK")
        and (interrupted_outcome.get("primary") or [None])[0] == "PIE-R3008"
        and interrupted_outcome.get("cancel") == [False, False, False],
        "INTERRUPT",
    )
    buffered = result(report.get("native_unlimited"), "NATIVE_BUFFERING")
    limited = result(report.get("native_limited"), "QUERY_LIMIT")
    need(
        buffered.get("delivered_rows") == limited.get("delivered_rows") == 1
        and buffered.get("first_row")
        == limited.get("first_row")
        == [{"id": 2, "label": "two"}]
        and buffered.get("native_buffered_rows") == 4
        and limited.get("native_buffered_rows") == 1,
        "NATIVE_BUFFERING",
    )
    need(
        buffered.get("second") == "REFUSED"
        and (buffered.get("failure") or {}).get("code") == "PIE-R3004"
        and (buffered.get("outcome") or {}).get("end") == "FAILED"
        and (buffered.get("outcome") or {}).get("transaction") == "ROLLBACK_ACK"
        and (buffered.get("outcome") or {}).get("rows") == 1
        and (buffered.get("outcome") or {}).get("batches") == 1
        and limited.get("second") == "EOF"
        and (limited.get("outcome") or {}).get("end") == "COMPLETE"
        and (limited.get("outcome") or {}).get("transaction") == "COMMIT_ACK"
        and (limited.get("outcome") or {}).get("rows") == 1
        and (limited.get("outcome") or {}).get("batches") == 1,
        "QUERY_LIMIT",
    )
    check = result(report.get("result_check"), "RESULT_CHECK")
    need(
        (check.get("code"), check.get("detail")) == ("PIE-R3005", "VALUE_DOMAIN"),
        "RESULT_CHECK",
    )
    outcome = outcome_of(check, "RESULT_CHECK")
    need(
        (outcome["end"], outcome["transaction"], outcome["cleanup"])
        == ("FAILED", "ROLLBACK_ACK", "CLOSED"),
        "RESULT_CHECK_END",
    )
    authentication = report.get("authentication") or {}
    need(sorted(authentication) == list(ROLES), "AUTH_DENOMINATOR")
    for role in ROLES:
        value = result(authentication[role], "AUTH_" + role)
        need(
            (value.get("code"), value.get("cause"))
            == ("PIE-R2004", "OperationalError"),
            "AUTH_" + role,
        )
        need(
            value.get("shown") is False and value.get("chained") is False, "CREDENTIAL"
        )
        need(value["outcome"]["transaction"] == "NOT_STARTED", "AUTH_" + role)
    timeout = result(report.get("statement_timeout"), "STATEMENT_TIMEOUT")
    need(
        (timeout.get("code"), timeout.get("sqlstate")) == ("PIE-R3002", "57014"),
        "STATEMENT_TIMEOUT",
    )
    # Only Pietto's limit applies (60 s deadline, no server-side limit for the
    # role). The window, counted from the opened attempt, confirms that this
    # limit of about 10 s ended the statement: without it the deadline would,
    # and a cap of 12 s or more falls outside. The exact 10 000 ms is pinned
    # offline (test_each_statement_is_limited_to_exactly_10_seconds).
    opened = timeout.get("opened")
    need(
        type(opened) is float and 9.5 <= timeout.get("seconds", 0) - opened < 12.0,
        "STATEMENT_TIMEOUT_SECONDS",
    )
    outcome = outcome_of(timeout, "STATEMENT_TIMEOUT")
    need(outcome["end"] == "FAILED", "STATEMENT_TIMEOUT_END")
    need(outcome["primary"][2] == "execute", "STATEMENT_TIMEOUT_PHASE")
    # The aborted transaction is closed with the connection, not rolled back.
    need(
        (outcome["transaction"], outcome["cleanup"], outcome["cleanup_failures"])
        == ("UNKNOWN", "FAILED", [["PIE-R5001", "transaction", "ExecutionError"]]),
        "STATEMENT_TIMEOUT_END",
    )
    manual = report.get("manual_cancel") or {}
    manual_result = manual.get("result") or {}
    manual_outcome = manual_result.get("outcome") or {}
    need(
        manual.get("returncode") == 0
        and manual.get("blocked") == [["active", "Lock"]]
        and manual_result.get("cancel_return") is True
        and (manual_result.get("code"), manual_result.get("detail"))
        == ("PIE-R3009", None)
        and manual_result.get("shown") is False
        and manual_result.get("chained") is False
        and (
            manual_outcome.get("end"),
            manual_outcome.get("transaction"),
            manual_outcome.get("cleanup"),
        )
        == ("CANCELLED", "UNKNOWN", "FAILED")
        and manual_outcome.get("remote") == "REMOTE_QUIESCENCE_UNCONFIRMED"
        and manual_outcome.get("cancel") == [True, True, True]
        and manual_outcome.get("cleanup_failures")
        == [["PIE-R5001", "transaction", "ExecutionError"]],
        "MANUAL_CANCEL",
    )
    drop: Any = report.get("dropped") or {}
    value: Any = drop.get("result")
    need(drop.get("returncode") == 0 and type(value) is dict, "DROPPED")
    need(value.get("warnings") == [["PIE-R5002", "DROPPED", True]], "DROPPED_WARNING")
    need(drop.get("during") == 1, "DROPPED_SESSION")
    tls = drop.get("tls") or []
    need(len(tls) == 1 and tls[0][0] is True and tls[0][1] in TLS, "ACTUAL_TLS")
    need(2.0 <= (drop.get("exit_delay") or 0) < 30.0, "DROPPED_EXIT_DELAY")
    need(drop.get("after") == 0, "DROPPED_SESSION_LEFT")
    exported = result(report.get("bundle_export"), "BUNDLE_EXPORT")
    check_records(exported.get("records"), "BUNDLE_EXPORT")
    check_steps(report.get("bundle_steps") or {})
    check_bundle_example(report.get("bundle_example"))
    check_consume_example(report.get("consume_example"))
    need((report.get("cleanup") or {}).get("status") == "success", "RESOURCE_CLEANUP")
    return {"family": "postgres", "verdict": "ACCEPTED"}


def check_postgres_adbc_native(report: Any) -> Any:
    """The installed ADBC wheel, not the service-free ADBC consumer profile."""
    check_install(report.get("install", {}), ("execute-postgres-adbc",))
    check_server(report.get("server") or {})
    native = result(report.get("native"), "ADBC_NATIVE")
    need(native.get("after_import") == [], "ADBC_NATIVE_IMPORT")
    expected = [[2, "two"], [2, "two"], [3, "three"], [5, "five"]]
    for name, origin in (("live", "live"), ("bundle", "bundle")):
        value = native.get(name) or {}
        outcome = outcome_of(value, "ADBC_NATIVE_" + name.upper())
        need(
            value.get("origin") == origin
            and value.get("route") == "postgres_adbc"
            and value.get("sslmode") == "require"
            and value.get("schema") == DEMO_SCHEMA
            and value.get("rows") == expected
            and (
                outcome.get("end"),
                outcome.get("source"),
                outcome.get("transaction"),
                outcome.get("delivery"),
                outcome.get("cleanup"),
                outcome.get("rows"),
                outcome.get("batches"),
                outcome.get("cancel"),
                outcome.get("primary"),
                outcome.get("cleanup_failures"),
            )
            == (
                "COMPLETE",
                "EOF",
                "COMMIT_ACK",
                "COMPLETE",
                "LOCAL_CLOSED_REMOTE_UNOBSERVED",
                4,
                1,
                [False, False, False],
                None,
                [],
            ),
            "ADBC_NATIVE_" + name.upper(),
        )
    empty = native.get("empty") or {}
    empty_outcome = outcome_of(empty, "ADBC_EMPTY")
    need(
        empty.get("route") == "postgres_adbc"
        and empty.get("sslmode") == "require"
        and empty.get("schema") == DEMO_SCHEMA
        and empty.get("rows") == []
        and (
            empty_outcome.get("end"),
            empty_outcome.get("source"),
            empty_outcome.get("transaction"),
            empty_outcome.get("delivery"),
            empty_outcome.get("cleanup"),
            empty_outcome.get("rows"),
            empty_outcome.get("batches"),
            empty_outcome.get("cancel"),
            empty_outcome.get("primary"),
            empty_outcome.get("cleanup_failures"),
        )
        == (
            "COMPLETE",
            "EOF",
            "COMMIT_ACK",
            "COMPLETE",
            "LOCAL_CLOSED_REMOTE_UNOBSERVED",
            0,
            0,
            [False, False, False],
            None,
            [],
        ),
        "ADBC_EMPTY",
    )
    bounded = native.get("bounded") or {}
    bounded_outcome = outcome_of(bounded, "ADBC_BOUNDED")
    need(
        bounded.get("route") == "postgres_adbc"
        and bounded.get("sslmode") == "require"
        and bounded.get("schema") == DEMO_SCHEMA
        and bounded.get("rows") == [[2, "two"]]
        and (
            bounded_outcome.get("end"),
            bounded_outcome.get("source"),
            bounded_outcome.get("transaction"),
            bounded_outcome.get("delivery"),
            bounded_outcome.get("cleanup"),
            bounded_outcome.get("rows"),
            bounded_outcome.get("batches"),
            bounded_outcome.get("cancel"),
            bounded_outcome.get("primary"),
            bounded_outcome.get("cleanup_failures"),
        )
        == (
            "COMPLETE",
            "EOF",
            "COMMIT_ACK",
            "COMPLETE",
            "LOCAL_CLOSED_REMOTE_UNOBSERVED",
            1,
            1,
            [False, False, False],
            None,
            [],
        ),
        "ADBC_BOUNDED",
    )
    early = native.get("early") or {}
    need(
        native.get("early_rows") == [{"id": 2, "label": "two"}]
        and (
            early.get("end"),
            early.get("source"),
            early.get("transaction"),
            early.get("delivery"),
            early.get("cleanup"),
            early.get("rows"),
            early.get("batches"),
            early.get("cancel"),
            early.get("primary"),
            early.get("cleanup_failures"),
        )
        == (
            "STOPPED_EARLY",
            "EARLY_CLOSE",
            "ROLLBACK_ACK",
            "INCOMPLETE",
            "LOCAL_CLOSED_REMOTE_UNOBSERVED",
            1,
            1,
            [False, False, False],
            None,
            [],
        )
        and early.get("remote") == "TRANSACTION_ACK",
        "ADBC_EARLY_CLOSE",
    )
    cancelled = native.get("cancelled") or {}
    cancelled_outcome = outcome_of(cancelled, "ADBC_CANCEL")
    need(
        cancelled.get("cancel_return") is True
        and cancelled.get("closed") is True
        and (cancelled.get("code"), cancelled.get("detail")) == ("PIE-R3009", None)
        and cancelled.get("shown") is False
        and cancelled.get("chained") is False
        and (
            cancelled_outcome.get("end"),
            cancelled_outcome.get("source"),
            cancelled_outcome.get("transaction"),
            cancelled_outcome.get("delivery"),
            cancelled_outcome.get("cleanup"),
            cancelled_outcome.get("remote"),
            cancelled_outcome.get("rows"),
            cancelled_outcome.get("batches"),
            cancelled_outcome.get("cancel"),
            cancelled_outcome.get("primary"),
            cancelled_outcome.get("cleanup_failures"),
        )
        == (
            "CANCELLED",
            "FAILED",
            "NOT_STARTED",
            "FAILED",
            "LOCAL_CLOSED_REMOTE_UNOBSERVED",
            "REMOTE_QUIESCENCE_UNCONFIRMED",
            0,
            0,
            [True, False, False],
            ["PIE-R3009", None, None, None, None],
            [],
        ),
        "ADBC_CANCEL",
    )
    need(native.get("qualification") == ["postgres_adbc"] * 5, "ADBC_QUALIFICATION")
    check_adbc_active(
        report.get("active_cancel"),
        terminal="CANCELLED",
        code="PIE-R3009",
        reason="ADBC_ACTIVE_CANCEL",
    )
    check_adbc_active(
        report.get("active_server_timeout"),
        terminal="FAILED",
        code="PIE-R3002",
        reason="ADBC_ACTIVE_SERVER_TIMEOUT",
        manual=False,
    )
    driver = native.get("driver") or {}
    need(
        driver.get("postgresql_version") == driver.get("manager_version") == "1.13.0"
        and all(
            driver.get(name) is True
            for name in (
                "library_record",
                "module_record",
                "module_in_prefix",
                "library_in_prefix",
                "library_exists",
            )
        )
        and all(
            type(driver.get(name)) is str
            for name in ("prefix", "module", "manager_module", "library")
        )
        and driver["library"].endswith(
            "adbc_driver_postgresql/libadbc_driver_postgresql.so"
        ),
        "ADBC_DRIVER_RECORD",
    )
    authentication = report.get("authentication") or {}
    methods = ("trust", "password", "md5", "gss", "sspi")
    need(sorted(authentication) == sorted(methods), "ADBC_AUTH_DENOMINATOR")
    for method in methods:
        record = authentication[method]
        value = result(record, "ADBC_AUTH_" + method)
        outcome = outcome_of(value, "ADBC_AUTH_" + method)
        stub = record.get("stub") or {}
        events = stub.get("events") or []
        need(
            value.get("after_import") == []
            and value.get("unopened") == [[], "NOT_STARTED", False]
            and value.get("code") == "PIE-R2004"
            and value.get("shown") is False
            and value.get("chained") is False
            and "adbc_driver_postgresql" in value.get("after_open", [])
            and "adbc_driver_manager" in value.get("after_open", [])
            and "psycopg" not in value.get("after_open", [])
            and (
                outcome.get("end"),
                outcome.get("source"),
                outcome.get("transaction"),
                outcome.get("delivery"),
                outcome.get("cleanup"),
                outcome.get("rows"),
                outcome.get("batches"),
                outcome.get("cancel"),
                outcome.get("primary"),
                outcome.get("cleanup_failures"),
            )
            == (
                "FAILED",
                "FAILED",
                "NOT_STARTED",
                "FAILED",
                "LOCAL_CLOSED_REMOTE_UNOBSERVED",
                0,
                0,
                [False, False, False],
                ["PIE-R2004", None, "admission", None, "OperationalError"],
                [],
            )
            and stub.get("startup") == ["pietto_reader", "phase66"]
            and events
            and events[0] == ["startup", "pietto_reader", "phase66"]
            and stub.get("replied") is False
            and not any(event[0] == "reply" for event in events),
            "ADBC_AUTH_" + method,
        )
    ambient = report.get("ambient") or {}
    names = ("SSLKEYLOGFILE", "OPENSSL_CONF", "OPENSSL_MODULES")
    need(sorted(ambient) == sorted(names), "ADBC_NATIVE_AMBIENT_DENOMINATOR")
    for name in names:
        record = ambient[name]
        value = result(record, "ADBC_NATIVE_AMBIENT_" + name)
        need(
            value.get("after_import") == []
            and (value.get("code"), value.get("detail"))
            == ("PIE-R2003", "EXECUTION_AMBIENT_CONNECTION_PROFILE")
            and value.get("shown") is False
            and value.get("chained") is False
            and value.get("after_open") == []
            and record.get("connected") is False
            and record.get("keylog_created") is False,
            "ADBC_NATIVE_AMBIENT_" + name,
        )
    need((report.get("cleanup") or {}).get("status") == "success", "RESOURCE_CLEANUP")
    return {"family": "postgres_adbc_native", "verdict": "ACCEPTED"}


def check_adbc_active(
    record: Any, *, terminal: str, code: str, reason: str, manual=True
) -> None:
    """An active native query, never merely the worker's declared purpose."""
    need(type(record) is dict and record.get("returncode") == 0, reason)
    need(
        record.get("blocked") == [["active", "Lock"]]
        and type(record.get("attempt")) is str
        and bool(record["attempt"]),
        reason + "_BARRIER",
    )
    value = result(record, reason)
    active = value.get("active") or {}
    need(
        active == {"type": "NativeStatement", "purpose": "query", "native": True},
        reason + "_STATEMENT",
    )
    outcome = outcome_of(value, reason)
    primary = outcome.get("primary") or []
    cleanup = outcome.get("cleanup")
    failures = outcome.get("cleanup_failures")
    need(
        value.get("closed") is True
        and value.get("raised") == "AttemptFailed"
        and (
            value.get("cancel_return") is True
            if manual
            else "cancel_return" not in value
        )
        and (
            outcome.get("end"),
            outcome.get("source"),
            outcome.get("transaction"),
            outcome.get("delivery"),
            outcome.get("remote"),
            outcome.get("rows"),
            outcome.get("batches"),
            outcome.get("cancel"),
        )
        == (
            terminal,
            "FAILED",
            "UNKNOWN",
            "FAILED",
            "REMOTE_QUIESCENCE_UNCONFIRMED",
            0,
            0,
            [True, True, True] if manual else [False, False, False],
        )
        and cleanup
        in (
            "FAILED_REMOTE_UNOBSERVED",
            "LOCAL_CLOSED_REMOTE_UNOBSERVED",
        )
        and type(primary) is list
        and len(primary) == 5
        and primary[0] == code
        and (manual or primary[3] == "57014")
        and type(failures) is list
        and all(type(failure) is list and len(failure) == 3 for failure in failures)
        and value.get("late_cancel_return") is True
        and value.get("outcome_after_late") == outcome,
        reason,
    )


def check(report: Any) -> Any:
    need(type(report) is dict and report.get("format") == FORMAT, "ENVELOPE")
    family = report.get("family")
    need(
        family
        in ("consumer", "mysql", "postgres", "postgres_adbc", "postgres_adbc_native"),
        "ENVELOPE",
    )
    family = cast(str, family)
    if "offline_resources" in report:
        from pathlib import Path
        from _pietto_target_conformance_resources import verify_offline_evidence

        target = "mysql" if family == "mysql" else "postgres"
        pin = json.loads(
            Path(__file__).with_name("phase66_target_pins.json").read_text()
        )["targets"][target]
        need(
            verify_offline_evidence(report["offline_resources"], target, pin),
            "OFFLINE_RESOURCES",
        )
    return {
        "consumer": check_consumer,
        "mysql": check_mysql,
        "postgres": check_postgres,
        "postgres_adbc": check_postgres_adbc,
        "postgres_adbc_native": check_postgres_adbc_native,
    }[family](report)
