"""Finite S01 inputs and independent literal oracles; no driver imports."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

ROUTES = ("postgres_rows", "mysql_rows", "postgres_adbc")
CASES = {
    "P01": ("identity",),
    "P02": ("parameterized_nonempty", "parameterized_empty", "parameterized_null"),
    "P03": ("carriers_populated", "carriers_empty", "carriers_all_null"),
    "P04": ("stable_view", "serializable_readonly"),
    "P05": (
        "multi_pull",
        "empty_eof",
        "early_close",
        "late_error",
        "cleanup_injection",
    ),
    "P06": ("cancel_blocking_read",),
    "P07": (
        "compiled_nonempty",
        "compiled_empty",
        "fixed_emission_values",
        "family_inventory",
    ),
}
DENOMINATOR = tuple(
    (route, group, case)
    for route in ROUTES
    for group, cases in CASES.items()
    for case in cases
)
PINS = {
    "psycopg": "3.3.5",
    "psycopg-binary": "3.3.5",
    "mysql-connector-python": "26.7.0",
    "pyarrow": "25.0.1",
    "adbc-driver-manager": "1.12.0",
    "adbc-driver-postgresql": "1.12.0",
    "importlib-resources": "7.1.0",
    "typing-extensions": "4.16.0",
    "antlr4-python3-runtime": "4.13.2",
}
PARAMETER_SQL = {
    "postgres": "SELECT CAST($1 AS BIGINT) AS value, CAST($2 AS TEXT) AS label, CAST($1 AS BIGINT) AS repeated, CAST($3 AS TEXT) AS nullable WHERE CAST($4 AS INTEGER) = 1",
    "mysql": "SELECT CAST(? AS SIGNED) AS value, CAST(? AS CHAR CHARACTER SET utf8mb4) AS label, CAST(? AS SIGNED) AS repeated, CAST(? AS CHAR CHARACTER SET utf8mb4) AS nullable WHERE CAST(? AS SIGNED) = 1",
}
PARAMETERS = (
    (9007199254740993, "quote ' $1 ? %s 😀", None, 1),
    (9007199254740993, "quote ' $1 ? %s 😀", None, 0),
    (-9007199254740993, None, None, 1),
)


def parameters(target, index):
    values = PARAMETERS[index]
    return (
        values
        if target == "postgres"
        else (values[0], values[1], values[0], values[2], values[3])
    )


def fixture_rows(target):
    uid = UUID("00112233-4455-6677-8899-aabbccddeeff")
    value = (
        9007199254740993,
        True if target == "postgres" else 1,
        -0.0,
        "雪e\u0301😀",
        Decimal("12.30"),
        datetime(2001, 2, 3, 4, 5, 6, 123456),
        uid if target == "postgres" else uid.bytes,
    )
    return [(1, *value), (2, *value), (3, *([None] * 7))]


SCALAR_SELECT = (
    "SELECT v_int, v_bool, v_float, v_text, v_decimal, v_time, v_uuid FROM p68_values"
)
LABELS = ("v_int", "v_bool", "v_float", "v_text", "v_decimal", "v_time", "v_uuid")
FAMILIES = {
    "direct/projection": "S03/S06: preserve current direct-field producer correspondence",
    "imports": "S06: carry imported output occurrence and retained provenance",
    "JOIN": "S06/S07: bridge expressions, null extension and retained obligations",
    "aggregate/window": "S06/S07: bridge computed outputs and exact scalar facts",
    "ORDER/LIMIT": "S04/S06: value invalidation, ordered execution and completion",
    "DISTINCT/SET": "S06/S14: positional output and duplicate-occurrence coverage",
    "retained single-match obligations": "S07: actual same-view guard fulfillment; no downstream semantic re-decision",
}


def expected_rows(case, route):
    """Literal output oracle, deliberately independent of runtime encoding."""

    def integer(x):
        return {"kind": "int", "value": x}

    null = {"kind": "null"}
    if case == "parameterized_nonempty":
        return [
            [
                integer("9007199254740993"),
                {"kind": "text", "value": "quote ' $1 ? %s 😀"},
                integer("9007199254740993"),
                null,
            ]
        ]
    if case == "parameterized_null":
        return [
            [integer("-9007199254740993"), null, integer("-9007199254740993"), null]
        ]
    if case in ("parameterized_empty", "carriers_empty", "empty_eof", "compiled_empty"):
        return []
    if case == "carriers_all_null":
        return [[null] * 7]
    if case == "carriers_populated":
        row = [
            integer("9007199254740993"),
            integer("1") if route == "mysql_rows" else {"kind": "bool", "value": True},
            {"kind": "float", "bits": "8000000000000000"},
            {"kind": "text", "value": "雪e\u0301😀"},
            {"kind": "text", "value": "12.30"}
            if route == "postgres_adbc"
            else {"kind": "decimal", "coefficient": "1230", "scale": 2},
            {"kind": "datetime", "value": "2001-02-03T04:05:06.123456"},
            {
                "kind": "uuid" if route == "postgres_rows" else "bytes",
                "value": "00112233445566778899aabbccddeeff",
            },
        ]
        return [row, row]
    if case == "multi_pull":
        return [[integer("1")], [integer("2")], [integer("3")]]
    if case == "compiled_nonempty":
        return [
            [integer("1"), null],
            [integer("1"), null],
            [integer("2"), integer("3")],
        ]
    raise ValueError("no literal rows oracle for this case")
