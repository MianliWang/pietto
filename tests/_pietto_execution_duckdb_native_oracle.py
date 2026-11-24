"""The oracle of the Phase79 DuckDB native qualification (preregistration
v7, sections 3, 4 and 4a-4r): every expected value, derived in pure Python
from the fixtures of `_pietto_execution_duckdb_native_cases` and the values
the preregistration states. B2's and tier 2's statements are evaluated here
by Pietto's own laws (three-valued predicates, grouping under `==`, NULL
placed as the PostgreSQL emitter places it, ties as classes, exact `Int`
and binary64 arithmetic that fails where a `Float` leaves binary64 or a
product of non-zero values underflows, equality JOINs where NULL matches
nothing), not by any product code. Writes expected.json; loads no
DuckDB."""

from __future__ import annotations

import functools
import json
import math
import operator
import struct
import sys
from pathlib import Path

import _pietto_execution_duckdb_native_cases as cases

SPEC_SHA256 = "4c4f06a2be5d3ed0784b1121eaad6139e085ed147a96b4a9f0108a8d80d56fe6"
CHILD_SHA256 = "f8c040460b3abb55d7563cffbe754b98afc7cac3ab6c726cbf5bf81fa5cdf1a7"
LCRU = "LOCAL_CLOSED_REMOTE_UNOBSERVED"
OPENED = [["connect", ":memory:"], ["register", "pietto_arrow_0"]]
ENDED = [["unregister", "pietto_arrow_0"], ["close"]]
SCHEMA_P = [["id", "int64", False], ["note", "string", True]]
SCHEMA_Q = [["id", "int64", False], ["price", "double", False]]
P_COLUMNS = (0, 2)
Q_COLUMNS = (0, 4)
COMPARE = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}
# Section 4e, as written there: the ids Q(op) returns for each value of
# cases.C08_VALUES over T5 plus row 6.
TABLE_4E = {
    "==": ({4}, set(), set(), set(), {5}),
    "!=": (
        {1, 2, 3, 5},
        {1, 2, 3, 4, 5},
        {1, 2, 3, 4, 5},
        {1, 2, 3, 4, 5},
        {1, 2, 3, 4},
    ),
    "<": (set(), {4}, {4}, {1, 4}, {1, 2, 3, 4}),
    "<=": ({4}, {4}, {4}, {1, 4}, {1, 2, 3, 4, 5}),
    ">": ({1, 2, 3, 5}, {1, 2, 3, 5}, {1, 2, 3, 5}, {2, 3, 5}, set()),
    ">=": ({1, 2, 3, 4, 5}, {1, 2, 3, 5}, {1, 2, 3, 5}, {2, 3, 5}, {5}),
}
# Section 4a: the 36 rows read back, as duckdb_settings() returns them.
READ_BACK = (
    ("allow_community_extensions", "false"),
    ("allow_extension_repositories", "forbidden"),
    ("allow_persistent_secrets", "false"),
    ("allow_unsigned_extensions", "false"),
    ("arrow_large_buffer_size", "false"),
    ("arrow_lossless_conversion", "false"),
    ("arrow_output_list_view", "false"),
    ("arrow_output_version", "1.0"),
    ("autoinstall_known_extensions", "false"),
    ("autoload_known_extensions", "false"),
    ("enable_progress_bar", "false"),
    ("enable_progress_bar_print", "false"),
    ("max_temp_directory_size", "0 bytes"),
    ("memory_limit", "1.0 GiB"),
    ("python_enable_replacements", "false"),
    ("python_scan_all_frames", "false"),
    ("temp_directory", ""),
    ("threads", "1"),
    ("enable_external_access", "false"),
    ("lock_configuration", "true"),
    ("allowed_configs", "[]"),
    ("allowed_directories", "[]"),
    ("allowed_paths", "[]"),
    ("extension_directories", "[]"),
    ("custom_extension_repository", ""),
    ("autoinstall_extension_repository", ""),
    ("log_query_path", ""),
    ("profiling_output", ""),
    ("disabled_filesystems", ""),
    ("enable_profiling", None),
    ("enable_logging", "0"),
    ("logging_sink", "memory"),
    ("access_mode", "automatic"),
    ("default_collation", ""),
    ("worker_threads", "1"),
    ("max_memory", "1.0 GiB"),
)
EXTENSIONS = ["core_functions", "icu", "json", "parquet"]
# C02a's 25 pairs (section 4, C02a), in order.
C02A_SEEN = [
    ["PIE-R1001", "PUBLIC_QUERY_REQUIRED"],
    ["PIE-R1002", "PUBLIC_QUERY_TYPE"],
    ["PIE-R1001", "PUBLIC_ROUTE_REQUIRED"],
    ["PIE-R1002", "PUBLIC_ROUTE_TYPE"],
    ["PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE"],
    ["PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE"],
    ["PIE-R1001", "PUBLIC_ACCESS_REQUIRED"],
    ["PIE-R1002", "PUBLIC_ACCESS_TYPE"],
    ["PIE-R1002", "PUBLIC_PREMISE_TYPE"],
    ["PIE-R1001", "PUBLIC_LIMITS_REQUIRED"],
    ["PIE-R1002", "PUBLIC_LIMITS_TYPE"],
    ["PIE-R1001", "PUBLIC_ISOLATION_REQUIRED"],
    ["PIE-R1002", "PUBLIC_VALUES_TYPE"],
    ["PIE-R1002", "PUBLIC_PARAMETERS_TYPE"],
    ["PIE-R1006", "BINDING_SLOTS"],
    ["PIE-R1006", "BINDING_PARAMETERS"],
    ["PIE-R1006", "BINDING_PARAMETERS"],
    ["PIE-R1006", "BINDING_PARAMETER:0:Int"],
    ["PIE-R1006", "BINDING_PARAMETER:0:Int"],
    ["PIE-R1006", "BINDING_PARAMETER:0:Int"],
    ["PIE-R1002", "EXECUTION_ACCESS"],
    ["PIE-R1002", "EXECUTION_ACCESS"],
    ["PIE-R1002", "EXECUTION_ACCESS"],
    ["PIE-R1002", "PUBLIC_VALUES_TYPE"],
    ["PIE-R1006", "BINDING_SLOTS"],
    # v7: a list and a tuple holding another type are not the route's
    # access; an empty tuple names no input (check 9).
    ["PIE-R1002", "PUBLIC_ACCESS_TYPE"],
    ["PIE-R1002", "PUBLIC_ACCESS_TYPE"],
    ["PIE-R1002", "DUCKDB_ARROW_SCHEMA"],
]
C02B_SEEN = [
    ["RequestRejected", "PIE-R1002", detail]
    for detail in (
        "DUCKDB_ARROW_SCHEMA",
        "DUCKDB_ARROW_SCHEMA",
        "EXECUTION_ISOLATION",
        "EXECUTION_ISOLATION",
        "EXECUTION_LIMITS",
        "EXECUTION_LIMITS",
        "DUCKDB_ARROW_SCHEMA",
        "DUCKDB_ARROW_SCHEMA",
        "EXECUTION_ISOLATION",
        "EXECUTION_LIMITS",
    )
]
IDENTITY = {
    "python": {"U0": "3.13.13", "U1": "3.13.13", "U2": "3.13.13", "U3": "3.12.13"},
    "platform": "linux-x86_64",
    "glibc_min": [2, 28],
    "duckdb": {
        "version": "2.0.1",
        "tags": [
            "cp312-abi3-manylinux_2_27_x86_64",
            "cp312-abi3-manylinux_2_28_x86_64",
        ],
        "record_hashed": 68,
        "pragma_version": ["v2.0.1", "8d78114e90"],
        "platform": "linux_amd64",
    },
    "pyarrow": {
        "version": "26.0.1",
        "tags": {
            "U1": ["cp313-cp313-manylinux_2_28_x86_64"],
            "U2": ["cp313-cp313-manylinux_2_28_x86_64"],
            "U3": ["cp312-cp312-manylinux_2_28_x86_64"],
        },
    },
}


def outcome(
    end,
    transaction,
    req=False,
    sent=False,
    seen=False,
    late=False,
    batches=0,
    cleanup=LCRU,
):
    """O of section 3: (end, transaction, cleanup, cancel_requested,
    cancel_sent, cancel_observed, deadline_expired, batches)."""
    return [end, transaction, cleanup, req, sent, seen, late, batches]


def rejected(code, detail):
    return {"class": "RequestRejected", "code": code, "detail": detail}


def failed(code, detail, phase, cause=None):
    fact = {"class": "AttemptFailed", "code": code, "detail": detail, "phase": phase}
    fact["sqlstate"] = None
    if cause is not None:
        fact["cause"] = cause
    return fact


def bag(rows, columns):
    return {"$bag": [cases.encode_row([row[k] for k in columns]) for row in rows]}


def complete(rows, schema, batches):
    """A completed attempt: its rows, schema and O (section 3, laws 3 and 4)."""
    return {
        "raised": None,
        "O": outcome("COMPLETE", "COMMIT_ACK", batches=batches),
        "rows": rows,
        "schema": schema,
        "batch_schemas": [schema] if batches else [],
    }


def _c08():
    rows6 = (*cases.T5, cases.ROW6)
    subs = {}
    for op in cases.OPERATORS:
        for k, value in enumerate(cases.C08_VALUES):
            ids = {r[0] for r in rows6 if r[1] is not None and COMPARE[op](r[1], value)}
            if ids != TABLE_4E[op][k]:
                raise AssertionError(f"section 4e differs at {op} {value}")
            for order in ("forward", "reversed"):
                picked = [r for r in rows6 if r[0] in ids]
                subs[f"{op} {value} {order}"] = complete(
                    bag(picked, Q_COLUMNS), SCHEMA_Q, 1 if ids else 0
                )
    if sum(1 for sub in subs.values() if sub["O"][7] == 0) != 10:
        raise AssertionError("section 4e has ten empty sub-cases")
    return subs


def _c11():
    deadline_query = failed("PIE-R3001", None, "query")
    cancelled = failed("PIE-R3009", None, None)
    session = failed("PIE-R2006", "DUCKDB_SESSION_CONTEXT", "session")
    lived = OPENED + ENDED
    return {
        "L1": {"raised": None, "O": outcome("NOT_STARTED", "NOT_STARTED"), "calls": []},
        "L2": {
            "raised": None,
            "O": outcome("STOPPED_EARLY", "UNKNOWN"),
            "calls": lived,
            "second_enter": {"class": "HandleMisuse", "code": "PIE-R4001"},
        },
        "L3": {
            "raised": {"class": "LookupError", "same": True},
            "O": outcome("FAILED", "UNKNOWN", batches=1),
            "primary": ["PIE-R3007", "consumer"],
            "calls": lived,
        },
        "L4": {
            "raised": cancelled,
            "O": outcome("CANCELLED", "NOT_STARTED", req=True),
            "calls": [],
        },
        "L5": {
            "raised": cancelled,
            "O": outcome("CANCELLED", "UNKNOWN", True, True, True),
            "calls": {"$interrupted": [OPENED, ENDED]},
            "resend_alive": False,
            "tripped": False,
            "hook_errors": [],
        },
        "L6": {
            "setup": {"$void_above": 0.5},
            "raised": deadline_query,
            "O": outcome("DEADLINE", "UNKNOWN", True, True, True, True),
            "elapsed": {"$range": [0.5, 30.0]},
            "timer_interval": {"$interval": [0.0, 0.5]},
            "timer_alive": False,
            "tripped": False,
            "hook_errors": [],
        },
        "L7": {
            "raised": failed(
                "PIE-R3001", "EXECUTION_DEADLINE", "query", "TimeoutError"
            ),
            "O": outcome("DEADLINE", "UNKNOWN", True, True, late=True),
            "calls": {"$interrupted": [OPENED, ENDED]},
            "hook_errors": [],
        },
        "L8": {
            "raised": cancelled,
            "O": outcome("CANCELLED", "COMMIT_ACK", req=True, batches=1),
            "trigger": [False, True],
            "calls": lived,
        },
        "L9a": {
            "raised": session,
            "O": outcome("FAILED", "NOT_STARTED"),
            "calls": [["connect", ":memory:"], ["close"]],
        },
        "L9b": {
            "raised": session,
            "O": outcome("FAILED", "NOT_STARTED"),
            "calls": [["connect", ":memory:"], ["close"]],
        },
        "L9c": {
            "raised": session,
            "O": outcome("FAILED", "NOT_STARTED"),
            "calls": [
                ["connect", ":memory:"],
                ["register", "pietto_arrow_0"],
                ["close"],
            ],
        },
        "L10": {
            "raised": failed("PIE-R3006", None, "finalization"),
            "O": outcome("FAILED", "COMMIT_ACK", batches=1, cleanup="FAILED"),
            "cleanup_failures": [["PIE-R5001", "close", "RuntimeError"]],
        },
        "L11a": {
            "raised": failed("PIE-R3003", None, "query", "OutOfRangeException"),
            "O": outcome("FAILED", "UNKNOWN"),
            "calls": lived,
        },
        "L11b": {
            "raised": failed(
                "PIE-R3005", "DUCKDB_RESULT_CHECK", "result", "ResultError"
            ),
            "O": outcome("FAILED", "UNKNOWN"),
            "calls": lived,
        },
        "L12": {
            "raised": failed("PIE-R3004", "EXECUTION_RESOURCE_LIMIT", "delivery"),
            "O": outcome("FAILED", "UNKNOWN"),
            "calls": lived,
        },
        "L13": {
            "raised": failed("PIE-R3003", None, "query", "OutOfMemoryException"),
            "O": outcome("FAILED", "UNKNOWN"),
            "calls": lived,
        },
    }


# B2 (sections 4f-4k): Pietto's laws over the fixtures, in pure Python.
INT64 = (-(2**63), 2**63 - 1)
ARROW = {"Int": "int64", "Text": "string", "Bool": "bool", "Float": "double"}
KINDS = {"id": "Int", "amount": "Int", "note": "Text", "ok": "Bool", "price": "Float"}
# Tier 2's suggestions (D79.26; rules 5 and 22 as D79.28 lands them).
TEXT_7 = (
    "select source fields directly, or group by keys and aggregates of fields,"
    " such as select: customer, total = sum(amount), or add, subtract or"
    " multiply two Int or two Float values, one at least a field or key, such"
    " as net = price - discount; other computed values are not available on"
    " DuckDB"
)
TEXT_7A = (
    "use count(), count(field), sum of an Int field, or min or max of an Int,"
    " Float, Decimal, Date or Timestamp field; other aggregates, sum or avg of"
    " a Float or a Decimal and aggregates of computed values are not available"
    " on DuckDB"
)
TEXT_7C = (
    "narrow the int_range of each Int field this value reads so that every"
    " result fits a signed 64-bit integer; DuckDB emission proves Int"
    " arithmetic from those ranges and literals, and an Int parameter may hold"
    " any signed 64-bit value"
)
TEXT_8 = (
    "compare fields or selected outputs with literals or query parameters of"
    " the same type, and join the tests with and, or and not, such as where"
    " amount >= min_amount and note is not None"
)
TEXT_5 = (
    "DuckDB emission admits duckdb.arrow source reads joined by inner or left"
    " joins on equalities of fields of one type, such as inner join customers"
    " on orders.customer_id == customers.id, then where, group by, having,"
    " select, order by and limit; right, full and cross joins, other on"
    " conditions, Decimal join keys, windows, qualify, distinct, set"
    " operations, relation lets and derived sources are not available on"
    " DuckDB"
)
TEXT_22 = (
    'use the relation namespace "arrow"; the DuckDB route reads registered Arrow tables'
)
TEXT_8B = (
    "remove NUL from the Text literal; DuckDB emission writes no NUL into SQL text"
)
TEXT_9 = (
    "declare non-null Int, Text, Bool, Float, Date, Timestamp or Decimal(p, s)"
    " parameters, p at most 38, and read each one in a where or having"
    " comparison or in selected arithmetic"
)
TEXT_10 = (
    "DuckDB emission reads Int, Text, Bool, Float, Date and Timestamp fields and"
    " Decimal(p, s) fields with p at most 38"
)
# The existing text of the representation check that joins rule 10 (code).
TEXT_B1002 = "use the DuckDB storage and domain of the field's logical type"


class Overflow(Exception):
    """A sum outside signed 64 bits that the statement reads: it fails
    (PIE-R3003)."""


# The value of a sum outside signed 64 bits, which no row may show.
OUT = object()


def _optional(project, field):
    return (
        field == "note"
        or (field == "amount" and cases.PROJECTS[project][1])
        or (project == "PB" and field in ("ok", "price"))
    )


def _value(expr, row, values):
    kind = expr[0]
    if kind == "f":
        value = row[expr[1]]
        if value is OUT:
            raise Overflow
        return value
    if kind == "p":
        return values[expr[1]]
    return expr[1]


def _truth(expr, row, values):
    """True, False or None (unknown), by three-valued logic."""
    kind = expr[0]
    if kind == "cmp":
        a, b = _value(expr[2], row, values), _value(expr[3], row, values)
        return None if a is None or b is None else COMPARE[expr[1]](a, b)
    if kind == "null":
        empty = _value(expr[1], row, values) is None
        return not empty if expr[2] else empty
    if kind == "not":
        a = _truth(expr[1], row, values)
        return None if a is None else not a
    a, b = _truth(expr[1], row, values), _truth(expr[2], row, values)
    if kind == "and":
        return False if False in (a, b) else None if None in (a, b) else True
    return True if True in (a, b) else None if None in (a, b) else False


def _shown(values):
    """A value of a class equal under `==`: a Float class that holds both
    zeros shows either member."""
    first = values[0]
    if isinstance(first, float) and first == 0.0:
        signs = {struct.pack(">d", v) for v in values}
        if len(signs) == 2:
            return {"$any": [cases.encode(0.0), cases.encode(-0.0)]}
    return cases.encode(first)


def _aggregate(item, rows):
    """(the value to order and compare by, its encoding)."""
    function, field = item[1], item[2]
    if function == "count":
        n = len(rows) if field is None else sum(r[field] is not None for r in rows)
        return n, cases.encode(n)
    seen = [r[field] for r in rows if r[field] is not None]
    if not seen:
        return None, None
    if function == "sum":
        total = sum(seen)
        if not INT64[0] <= total <= INT64[1]:
            return OUT, None
        return total, cases.encode(total)
    extreme = (min if function == "min" else max)(seen)
    return extreme, _shown([v for v in seen if v == extreme])


def _compare(keys, a, b):
    """NULL last ascending and first descending, as the PostgreSQL emitter
    places it; 0 for rows that tie on every key."""
    for name, desc in keys:
        x, y = a[name], b[name]
        if x is OUT or y is OUT:
            raise Overflow
        if x is None or y is None:
            order = (x is None) - (y is None)
        else:
            order = (x > y) - (x < y)
        if order:
            return -order if desc else order
    return 0


def _evaluate(spec, rows):
    """B2's statement over the `orders` rows (see _evaluated)."""
    return _evaluated(
        spec, [dict(zip(cases.COLUMNS, row, strict=True)) for row in rows]
    )


class FloatFailure(Exception):
    """A checked `Float` operation that fails the statement, with its detail."""


ARITH = {"+": operator.add, "-": operator.sub, "*": operator.mul}


def _scalar(item, row, values):
    """A selected value: a read, a literal, a parameter, or exact `Int` and
    binary64 arithmetic, each `Float` `+`, `-` and `*` checked as the SQL
    writes it (NULL when an operand is)."""
    kind = item[0]
    if kind in ("neg", "pos"):
        value = _scalar(item[1], row, values)
        return None if value is None else (-value if kind == "neg" else value)
    if kind != "arith":
        return _value(item, row, values)
    a, b = _scalar(item[2], row, values), _scalar(item[3], row, values)
    if a is None or b is None:
        return None
    result = ARITH[item[1]](a, b)
    if isinstance(result, float):
        if math.isinf(result):
            raise FloatFailure("DUCKDB_FLOAT_OVERFLOW")
        if item[1] == "*" and result == 0.0 and a != 0.0 and b != 0.0:
            raise FloatFailure("DUCKDB_FLOAT_UNDERFLOW")
    elif not INT64[0] <= result <= INT64[1]:
        raise AssertionError("an Int result outside its proved range")
    return result


def _evaluated(spec, source):
    """The statement's rows over its source rows (dicts by field name) as
    (raw values by label and field, encoded row), and whether any group's
    sum left signed 64 bits. A checked `Float` failure raises."""
    values = spec["values"] or {}
    if spec["where"] is not None:
        source = [r for r in source if _truth(spec["where"], r, values) is True]
    aggregates = any(item[0] == "agg" for _label, item in spec["select"])
    if not (spec["group"] or aggregates):
        out = []
        for r in source:
            raw = {
                **r,
                **{label: _scalar(item, r, values) for label, item in spec["select"]},
            }
            encoded = [cases.encode(raw[label]) for label, _item in spec["select"]]
            out.append((raw, encoded))
        return out, False
    groups = {}
    for r in source:
        groups.setdefault(tuple(r[k] for k in spec["group"]), []).append(r)
    if not spec["group"]:
        groups = {(): source}
    out = []
    for members in groups.values():
        raw, encoded = {}, []
        for label, item in spec["select"]:
            if item[0] == "agg":
                value, shown = _aggregate(item, members)
            else:
                # A key's arithmetic, per member: a class of both zeros may
                # show either sign.
                each = [_scalar(item, m, values) for m in members]
                value = each[0]
                shown = None if value is None else _shown(each)
            raw[label] = value
            encoded.append(shown)
        out.append((raw, encoded))
    overflowed = any(v is OUT for raw, _encoded in out for v in raw.values())
    if spec["having"] is not None:
        out = [o for o in out if _truth(spec["having"], o[0], values) is True]
    return out, overflowed


def _schema(spec):
    columns = []
    for label, item in spec["select"]:
        if item[0] == "agg":
            kind = "Int" if item[1] in ("count", "sum") else KINDS[item[2]]
            columns.append([label, ARROW[kind], item[1] != "count"])
        else:
            optional = _optional(spec["project"], item[1])
            columns.append([label, ARROW[KINDS[item[1]]], optional])
    return columns


def _rows_expected(spec, out):
    """Law 4's rows: a bag; the sequence of tie classes under `order by`, up
    to the class at the limit; a limit without `order by` keeps any rows of
    the bag. A row that a sum outside signed 64 bits reaches raises
    Overflow."""
    keys, limit = spec["order"], spec["limit"]
    if keys:
        ranked = sorted(
            out, key=functools.cmp_to_key(lambda a, b: _compare(keys, a[0], b[0]))
        )
        classes = []
        for raw, encoded in ranked:
            if classes and _compare(keys, classes[-1][0], raw) == 0:
                classes[-1][1].append((raw, encoded))
            else:
                classes.append((raw, [(raw, encoded)]))
        kept, count = [], 0
        for _first, members in classes:
            if limit is not None and count >= limit:
                break
            kept.append(members)
            count += len(members)
        if any(
            v is OUT for members in kept for raw, _ in members for v in raw.values()
        ):
            raise Overflow
        rows = [[encoded for _raw, encoded in members] for members in kept]
        return {"$ordered": {"classes": rows, "limit": limit}}
    if any(v is OUT for raw, _encoded in out for v in raw.values()):
        raise Overflow
    rows = [encoded for _raw, encoded in out]
    if limit is not None:
        return {"$ordered": {"classes": [rows], "limit": limit}}
    if any(isinstance(v, dict) for row in rows for v in row):
        return {"$bag_any": rows}
    return {"$bag": rows}


def _completed(spec, out, rows=None):
    schema = _schema(spec)
    count = len(out) if spec["limit"] is None else min(len(out), spec["limit"])
    batches = -(-count // 256)
    return {
        "raised": None,
        "O": outcome("COMPLETE", "COMMIT_ACK", batches=batches),
        "rows": _rows_expected(spec, out) if rows is None else rows,
        "schema": schema,
        "batch_schemas": [schema] if batches else [],
    }


def _overflowed(spec):
    return {
        "raised": failed("PIE-R3003", None, "query", "ConversionException"),
        "O": outcome("FAILED", "UNKNOWN"),
        "rows": [],
        "schema": _schema(spec),
    }


def _statement(sub, spec):
    if sub in cases.REFUSED:
        return _blocked(spec, "duckdb_text_literal_nul_not_admitted", TEXT_8B)
    order = sub.rsplit(" ", 1)[1]
    out, overflowed = _evaluate(spec, cases.rows_of(spec["table"], order))
    if sub not in cases.EITHER:
        return _overflowed(spec) if overflowed else _completed(spec, out)
    # The out-of-range group is removed by the having or lies beyond the
    # limit: the statement fails, or it returns the other rows correctly
    # (section 4f). Reading that group's sum is a fixture error here.
    if not overflowed:
        raise AssertionError(f"{sub}: no group overflows")
    return {"either": [_overflowed(spec), _completed(spec, out)]}


def _site(spec, text, offset):
    """The span of `text`, less its first `offset` characters, in the first
    line of the module (the header, then the statement) that holds it."""
    module = cases.header(spec["project"]) + "\n" + cases.body(spec)
    for number, line in enumerate(module.split("\n")):
        found = line.find(text)
        if found >= 0:
            column = found + 1 + offset
            return {
                "path": "main.pietto",
                "line": 1 + number,
                "column": column,
                "end_line": 1 + number,
                "end_column": column + len(text) - offset,
            }
    raise AssertionError(f"{text!r} is not in the statement")


def _blocked(spec, detail, suggestion, site=None, code="PIE-B1003"):
    """A compile refusal with one blocker: by default rule 7 at the computed
    output, or rule 8b at the literal that holds NUL."""
    if site is not None:
        pass
    elif detail == "duckdb_projection_not_admitted":
        raw = next(item[1] for _label, item in spec["select"] if item[0] == "raw")
        site = _site(spec, raw, 0)
    else:
        site = _site(spec, cases.render(cases.NUL_LITERAL), len("note == "))
    reason = "SOURCE_REALIZATION" if code == "PIE-B1001" else "UNSUPPORTED_RULE"
    blocker = [code, reason, detail, site, [], suggestion]
    return {"compile": "BLOCKED", "blockers": [blocker]}


def _blockers(found):
    """A compile refusal with several blockers, each [code, detail, site,
    suggestion], in order (code)."""
    reasons = {"PIE-B1001": "SOURCE_REALIZATION", "PIE-B1002": "REPRESENTATION"}
    return {
        "compile": "BLOCKED",
        "blockers": [
            [code, reasons.get(code, "UNSUPPORTED_RULE"), detail, site, [], text]
            for code, detail, site, text in found
        ],
    }


def _whole(spec):
    """Rule 9's site when no declaration fails: the statement, from its
    first line to the end of its last (code)."""
    module = (cases.header(spec["project"]) + "\n" + cases.body(spec)).split("\n")
    first = next(n for n, line in enumerate(module) if line.startswith("query "))
    last = max(n for n, line in enumerate(module) if line)
    return {
        "path": "main.pietto",
        "line": 1 + first,
        "column": 1,
        "end_line": 1 + last,
        "end_column": 1 + len(module[last]),
    }


def _ranked(rows):
    return {"$ordered": {"classes": [[row] for row in rows], "limit": None}}


def _capacity(sub, spec):
    """C21 from the capacity rows' formulas (section 4h)."""
    n = cases.MAX_ROWS
    if sub == "count":
        total = sum(k % 1000 - 500 for k in range(n))
        row = [cases.encode(v) for v in (n, total, -3.0, n - 1)]
        return _completed(spec, [None], {"$bag": [row]})
    if sub == "group":
        top = [
            [cases.encode(cases.capacity_row(k)[2]), cases.encode(1)]
            for k in (n - 1, n - 2)
        ]
        return _completed(spec, [None] * 2, _ranked(top))
    if sub == "sort":
        rows = [[cases.encode(k)] for k in range(n - 1, -1, -1)]
        return _completed(spec, [None] * n, cases.digest(rows))
    groups = {}
    for k in range(n):
        _id, amount, _note, ok, price = cases.capacity_row(k)
        count, total, low = groups.get(ok, (0, 0, price))
        groups[ok] = (count + 1, total + amount, min(low, price))
    ranked = [
        [cases.encode(ok), *(cases.encode(v) for v in groups[ok])]
        for ok in (False, True)
    ]
    return _completed(spec, [None] * 2, _ranked(ranked))


# Tier 2 (sections 4l-4r): the same laws over the PT, PA and PJ projects.
T2_ARROW = {**ARROW, "Date": "date32[day]", "Timestamp": "timestamp[us]"}
OSE = "OSError"


def _arrow(kind):
    if kind.startswith("Decimal("):
        return "decimal128({}, {})".format(*cases.decimal_of(kind))
    return T2_ARROW[kind]


def _sources(spec):
    """The source reads in FROM and JOIN order: (name, shape, key, joined
    by a left join); a row-input alias (`let o2 = orders`) is a read of its
    source under its own name (D79.29)."""
    by_name = {s[0]: s[1:] for s in cases.T2_PROJECTS[spec["project"]]}
    for line in spec["lets"]:
        alias, source = line.removeprefix("let ").split(" = ")
        by_name[alias] = by_name[source]
    read = [(spec["from"], None)] + [
        (join[1], join[0]) for join in spec["joins"] if not isinstance(join, str)
    ]
    return [(name, *by_name[name], kind == "left") for name, kind in read]


def _kinds(spec):
    """Each readable field's (Pietto type, result nullability), by its
    qualified name, and by its bare name when one source is read."""
    sources = _sources(spec)
    kinds = {}
    for name, shape, _key, left in sources:
        for field, kind, nullable in cases.T2_SHAPES[shape]:
            kinds[f"{name}.{field}"] = (kind, nullable or left)
            if len(sources) == 1:
                kinds[field] = kinds[f"{name}.{field}"]
    return kinds


def _input(spec, key, order):
    shape, rows = cases.T2_TABLES[spec["inputs"][key]]
    rows = rows[::-1] if order == "reversed" else rows
    return shape, rows


def _dicts(spec, name, shape, key, order):
    fields = cases.T2_SHAPES[shape]
    _shape, rows = _input(spec, key, order)
    out = []
    for row in rows:
        values = {
            f"{name}.{field}": cases.quantized(value, kind)
            for (field, kind, _nullable), value in zip(fields, row, strict=True)
        }
        if not spec["joins"]:
            values.update({k.split(".", 1)[1]: v for k, v in values.items()})
        out.append(values)
    return out


def _same(a, b):
    """Pietto's `==` in a JOIN's `on`: NULL matches nothing; -0.0 == 0.0."""
    return a is not None and b is not None and a == b


def _joined_rows(spec, order):
    sources = _sources(spec)
    name, shape, key, _left = sources[0]
    rows = _dicts(spec, name, shape, key, order)
    joins = [join for join in spec["joins"] if not isinstance(join, str)]
    for (kind, _source, pairs), (name, shape, key, _left) in zip(
        joins, sources[1:], strict=True
    ):
        right = _dicts(spec, name, shape, key, order)
        empty = {f"{name}.{field}": None for field, _k, _n in cases.T2_SHAPES[shape]}
        joined = []
        for left in rows:
            matched = [
                {**left, **r}
                for r in right
                if all(_same({**left, **r}[a], {**left, **r}[b]) for a, b in pairs)
            ]
            joined += matched or ([{**left, **empty}] if kind == "left" else [])
        rows = joined
    return rows


def _key_broken(spec, order):
    """D79.24: with a JOIN and an aggregate, a read source whose input has two
    rows equal in every field of a declared key, NULLs left out."""
    if not spec["joins"] or not any(i[0] == "agg" for _l, i in spec["select"]):
        return False
    for _name, shape, key, _left in _sources(spec):
        fields = [f for f, _k, _n in cases.T2_SHAPES[shape]]
        _shape, rows = _input(spec, key, order)
        for unique in cases.T2_KEYS.get(shape, ()):
            seen = [row[fields.index(unique)] for row in rows]
            seen = [v for v in seen if v is not None]
            if len(set(seen)) != len(seen):
                return True
    return False


def _t2_schema(spec):
    kinds = _kinds(spec)
    # An inner JOIN's on makes a direct read of its keys non-null; an
    # arithmetic value takes no proof from it (section 4n).
    proved = {
        field
        for join in spec["joins"]
        if not isinstance(join, str) and join[0] == "inner"
        for pair in join[2]
        for field in pair
    }

    def operands(item):
        if item[0] == "f":
            return [kinds[item[1]]]
        if item[0] in ("neg", "pos"):
            return operands(item[1])
        if item[0] == "arith":
            return operands(item[2]) + operands(item[3])
        if item[0] == "p":
            return [(dict(spec["params"])[item[1]], False)]
        kind = "Float" if isinstance(item[1], float) else "Int"
        return [(kind, False)]

    columns = []
    for label, item in spec["select"]:
        if item[0] == "agg":
            function = item[1]
            if function == "count":
                columns.append([label, "int64", False])
            elif function == "sum":
                columns.append([label, "int64", True])
            else:
                columns.append([label, _arrow(kinds[item[2]][0]), True])
            continue
        found = operands(item)
        kind = found[0][0]
        direct = item[0] == "f" and item[1] in proved
        columns.append([label, _arrow(kind), any(n for _k, n in found) and not direct])
    return columns


def _t2_completed(spec, out, rows=None):
    limits = spec["limits"] or {}
    size = limits.get("batch_rows", 256)
    schema = _t2_schema(spec)
    count = len(out) if spec["limit"] is None else min(len(out), spec["limit"])
    batches = -(-count // size)
    return {
        "raised": None,
        "O": outcome("COMPLETE", "COMMIT_ACK", batches=batches),
        "rows": _rows_expected(spec, out) if rows is None else rows,
        "schema": schema,
        "batch_schemas": [schema] if batches else [],
    }


def _t2_failed(spec, detail, cause="InvalidInputException"):
    return {
        "raised": failed("PIE-R3003", detail, "query", cause),
        "O": outcome("FAILED", "UNKNOWN"),
        "rows": [],
        "schema": _t2_schema(spec),
    }


def _cut(spec, raised, rows, batches, count):
    """A statement that fails after `batches` whole batches: the delivered
    rows are `count` rows of `rows`."""
    schema = _t2_schema(spec) if spec["project"] in cases.T2_PROJECTS else _schema(spec)
    return {
        "raised": raised,
        "O": outcome("FAILED", "UNKNOWN", batches=batches),
        "rows": {"$sub": {"rows": rows, "count": count}},
        "schema": schema,
        "batch_schemas": [schema] if batches else [],
    }


def _refusal(cell, sub, spec):
    """Tier 2's one-blocker refusals (section 4p), at the sites the rules name."""
    name = sub.rsplit(" ", 1)[0]
    line = next(
        (j for j in spec["joins"] if isinstance(j, str)),
        None,
    )
    select = next((i[1] for _l, i in spec["select"] if i[0] == "raw"), None)
    if name == "parameter unread":
        return _blocked(
            spec, "duckdb_parameter_not_admitted", TEXT_9, _site(spec, "m: Int", 0)
        )
    if name == "field beyond 38 digits":
        site = _site(spec, "big: Decimal(39, 2)", 0)
        return _blockers(
            [
                ["PIE-B1003", "duckdb_field_type_not_admitted", site, TEXT_10],
                [
                    "PIE-B1002",
                    "physical_storage_or_domain_mismatch",
                    site,
                    TEXT_B1002,
                ],
            ]
        )
    if name in ("right join parameter", "right join nul"):
        joined = ["PIE-B1003", "duckdb_relation_shape_not_admitted", None, TEXT_5]
        joined[2] = _site(spec, line, 0)
        if name == "right join parameter":
            other = ["duckdb_parameter_not_admitted", _whole(spec), TEXT_9]
        else:
            other = [
                "duckdb_text_literal_nul_not_admitted",
                _site(spec, '"a\0b"', 0),
                TEXT_8B,
            ]
        return _blockers([joined, ["PIE-B1003", *other]])
    if cell == "C23" and name == "sum decimal":
        return _blocked(
            spec, "duckdb_aggregate_not_admitted", TEXT_7A, _site(spec, "sum(cost)", 0)
        )
    if cell == "C23":
        clause = (
            "having " + cases.render(spec["having"])
            if spec["having"] is not None
            else "where " + cases.render(spec["where"])
        )
        return _blocked(
            spec, "duckdb_filter_not_admitted", TEXT_8, _site(spec, clause, 0)
        )
    if cell == "C24" and name in ("range", "int param"):
        return _blocked(
            spec, "duckdb_arithmetic_range_not_proved", TEXT_7C, _site(spec, select, 0)
        )
    if cell == "C24":
        return _blocked(spec, "duckdb_projection_not_admitted", TEXT_7)
    if name == "namespace":
        source = 'source customers: Customer = duckdb.arrow("customers")'
        return _blocked(
            spec,
            "source_identifier_unrepresentable",
            TEXT_22,
            _site(spec, source, 0),
            "PIE-B1001",
        )
    return _blocked(
        spec, "duckdb_relation_shape_not_admitted", TEXT_5, _site(spec, line, 0)
    )


BINDING = {
    "date as datetime": "BINDING_PARAMETER:1:Date",
    "zoned timestamp": "BINDING_PARAMETER:0:Timestamp",
    "timestamp past the end": "BINDING_PARAMETER:0:Timestamp",
    "decimal scale": "BINDING_PARAMETER:2:Decimal",
    "decimal nan": "BINDING_PARAMETER:2:Decimal",
    "inf parameter": "BINDING_PARAMETER:0:Float",
    "nan parameter": "BINDING_PARAMETER:0:Float",
}


# The later failures of C24: (rows before the failing row, least batches).
LATER = {"overflow later": (2048, 0), "overflow after batches": (cases.MUCH_LATER, 1)}


def _t2_statement(cell, sub, spec):
    if sub in cases.T2_REFUSED.get(cell, ()):
        return _refusal(cell, sub, spec)
    name, order = sub.rsplit(" ", 1)
    if sub in cases.T2_BINDING.get(cell, ()):
        code = BINDING[name.removeprefix("bind ")]
        return {"raised": rejected("PIE-R1006", code), "calls": []}
    if _key_broken(spec, order):
        return {"raised": rejected("PIE-R1002", "DUCKDB_ARROW_SCHEMA"), "calls": []}
    try:
        out, overflowed = _evaluated(spec, _joined_rows(spec, order))
    except FloatFailure as failure:
        if name in LATER:
            # A failure while a batch is read, after whole batches of the
            # rows before it: any number for `overflow later`, at least one
            # for `overflow after batches` (section 4m).
            before, first = LATER[name]
            rows = [[cases.encode(k), cases.encode(2.0)] for k in range(before)]
            return {
                "later": {
                    "raised": failed("PIE-R3003", failure.args[0], "query", OSE),
                    "O": outcome("FAILED", "UNKNOWN"),
                    "rows": rows,
                    "batch_rows": 256,
                    "first": first,
                    "schema": _t2_schema(spec),
                }
            }
        return _t2_failed(spec, failure.args[0])
    if overflowed:
        raise AssertionError(f"{cell} {sub}: no tier 2 sum overflows")
    if name == "fan-out cut":
        # Batches of at most 256 rows until one would cross max_rows 500:
        # 245 to 500 JOIN rows in 1 to 500 batches (section 4n).
        rows = [encoded for _raw, encoded in out]
        raised = failed("PIE-R3004", "EXECUTION_RESOURCE_LIMIT", "delivery")
        cut = _cut(spec, raised, rows, 1, [245, 500])
        cut["O"] = _joined_outcome(spec, cut["O"], 1, 500)
        return cut
    done = _t2_completed(spec, out)
    if spec["joins"]:
        count = len(out) if spec["limit"] is None else min(len(out), spec["limit"])
        done["O"] = _joined_outcome(spec, done["O"], done["O"][7], count)
    return done


def _joined_outcome(spec, o, least, most_batches):
    """A JOIN's O (section 4n): its batches from `least` to `most_batches`,
    each of 1 to `batch_rows` rows, together the delivered rows; a batch may
    end early where DuckDB's result chunk ends."""
    size = (spec["limits"] or {}).get("batch_rows", 256)
    return {
        "$outcome": {"fixed": o[:7], "batches": [least, most_batches], "most": size}
    }


# Section 4o: each batch's charge is its own nbytes, a validity bitmap for
# every column included: per column ceil(n / 8) bytes of bitmap, 8 n of an
# int64 or a double, and 4 n of offsets and the UTF-8 bytes of a string
# (the referenced offsets as pyarrow 26.0.1 counts a batch's string column).
def _charge(rows, columns):
    n = len(rows)
    total = 0
    for k in columns:
        total += -(-n // 8)
        if k == 2:
            total += 4 * n + sum(len((r[k] or "").encode()) for r in rows)
        else:
            total += 8 * n
    return total


def _charged(rows, columns, size=256):
    return sum(
        _charge(rows[at : at + size], columns) for at in range(0, len(rows), size)
    )


def _c25():
    t5 = bag(cases.T5, P_COLUMNS)
    exact = _charged(cases.T5, P_COLUMNS)
    if exact != cases.T5_CHARGE:
        raise AssertionError("section 4o: T5's charge differs")
    many = cases.TN * 500
    lived = OPENED + ENDED
    interrupted = {"$interrupted": [OPENED, ENDED]}
    refused = failed("PIE-R3004", "EXECUTION_RESOURCE_LIMIT", "delivery")
    limit = {
        "raised": refused,
        "O": outcome("FAILED", "UNKNOWN"),
        "rows": [],
        "calls": lived,
    }
    later = cases.later_rows()
    groups = {}
    for row in later:
        groups.setdefault(row[2], []).append(row[1])
    good = [
        [cases.encode(note), cases.encode(len(amounts)), cases.encode(sum(amounts))]
        for note, amounts in groups.items()
        if sum(amounts) <= INT64[1]
    ]
    if len(good) != cases.LATER_GROUPS - 1:
        raise AssertionError("section 4o: one later group leaves signed 64 bits")
    two = [_charge(cases.T5[at : at + 2], P_COLUMNS) for at in (0, 2)]
    if sum(two) != cases.BYTES_CUT:
        raise AssertionError("section 4o: T5's first two batches differ")
    schema = _schema(cases.LATER)
    return {
        "bytes at the limit": {
            **complete(t5, SCHEMA_P, 1),
            "bytes": exact,
            "calls": lived,
        },
        "bytes one below": limit,
        "batch bytes one below": limit,
        "bytes in many batches": {
            **complete(bag(many, P_COLUMNS), SCHEMA_P, 24),
            "bytes": _charged(many, P_COLUMNS),
        },
        "rows cut": {
            **_cut(
                cases.stmt(cases.reads("id", "note"), project="P0"),
                refused,
                t5["$bag"],
                2,
                4,
            ),
            "calls": lived,
        },
        "close after the last batch": {
            "raised": None,
            "O": outcome("STOPPED_EARLY", "UNKNOWN", batches=1),
            "rows": t5,
            "calls": lived,
        },
        "cancel after the last batch": {
            "raised": failed("PIE-R3009", None, None),
            "O": outcome("CANCELLED", "UNKNOWN", True, True, batches=1),
            "rows": t5,
            "calls": interrupted,
        },
        "deadline after the last batch": {
            "raised": failed(
                "PIE-R3001", "EXECUTION_DEADLINE", "query", "TimeoutError"
            ),
            "O": outcome("DEADLINE", "UNKNOWN", True, True, late=True, batches=1),
            "rows": t5,
            "calls": interrupted,
        },
        "sum in a later chunk": {
            "either": [
                {
                    "raised": failed("PIE-R3003", None, "query", "ConversionException"),
                    "O": outcome("FAILED", "UNKNOWN"),
                    "rows": [],
                },
                {
                    "later": {
                        "raised": failed("PIE-R3003", None, "query", OSE),
                        "O": outcome("FAILED", "UNKNOWN"),
                        "rows": good,
                        "batch_rows": 256,
                        "first": 0,
                        "schema": schema,
                    }
                },
            ]
        },
        "bytes cut after two batches": {
            **_cut(
                cases.stmt(cases.reads("id", "note"), project="P0"),
                refused,
                t5["$bag"],
                2,
                4,
            ),
            "bytes": cases.BYTES_CUT,
            "calls": lived,
        },
        # The reader's close fails once it has reported its end: cleanup
        # step `reader`, before `unregister` and `close` (D79.27).
        "reader close fails": {
            "raised": failed("PIE-R3006", None, "finalization"),
            "O": outcome("FAILED", "COMMIT_ACK", batches=1, cleanup="FAILED"),
            "rows": t5,
            "cleanup_failures": [["PIE-R5001", "reader", "RuntimeError"]],
            "calls": OPENED + [["reader close"]] + ENDED,
        },
    }


def _c27():
    nothing = {"calls": [], "modules": []}
    handle = {"raised": None, "end": "NOT_STARTED", **nothing}

    def refused(detail):
        return {"raised": rejected("PIE-R1002", detail), **nothing}

    schema = refused("DUCKDB_ARROW_SCHEMA")
    limit = refused("DUCKDB_ARROW_CAPTURE_LIMIT")
    cells = {f"typed:{name}": schema for name in cases.TYPED_FORGED}
    cells.update(
        {
            "typed:edges": handle,
            "names:list": refused("PUBLIC_ACCESS_TYPE"),
            "names:repeated": schema,
            "names:missing": schema,
            "names:extra": schema,
            "names:case": schema,
            "names:one in a tuple": handle,
            "rows:each input at the limit": handle,
            "rows:one input beyond": limit,
            "bytes:over all inputs": limit,
            "bytes:shared input once": handle,
            "bytes:self join once": handle,
        }
    )
    return {sub: cells[sub] for sub in cases.C27_SUBS}


MIB = 1024 * 1024


def _c28():
    """Section 4r: each JOIN with an aggregate over 1,048,576 rows, its peak
    while execute() captures and checks the declared key at most the
    selected bytes, twice the key's bytes, 8 bytes a row of sort indices and
    128 MiB, in KiB."""
    n = cases.MAX_ROWS
    names = {5: 2, 10: 1, 15: 1, 99: 1}
    account = [
        [cases.encode(cases.account_name(k)), cases.encode(count)]
        for k, count in names.items()
    ]
    handles = cases.handle_rows()
    h_bytes = 4 * (n + 1) + sum(len(h.encode()) for h, _n in handles)
    a_bytes = 4 * (n + 1) + sum(len(cases.account_name(k).encode()) for k in range(n))
    # JO's six rows measure far less than this.
    orders = 1024
    sizes = {
        "int key": (orders + 8 * n + a_bytes, 8 * n),
        "text key": (orders + h_bytes + 8 * n, h_bytes),
        "no key check": (orders + h_bytes + 8 * n, 0),
    }
    rows = {
        "int key": {"$bag": account},
        "text key": {
            "$bag": [
                [cases.encode(h), cases.encode(c)]
                for h, c in (("a", 2), ("c", 1), ("z", 1))
            ]
        },
        "no key check": {
            "$bag": [
                [cases.encode(h), cases.encode(k)]
                for h, k in (("a", 1), ("c", 3), ("a", 4), ("z", 6))
            ]
        },
    }
    cells = {}
    for sub in cases.C28_SUBS[:3]:
        spec = cases.PEAK[sub]
        selected, key = sizes[sub]
        bound = (selected + 2 * key + (8 * n if key else 0) + 128 * MIB) // 1024
        done = _t2_completed(spec, [None] * len(rows[sub]["$bag"]), rows[sub])
        cells[sub] = {
            **done,
            "O": _joined_outcome(spec, done["O"], 1, len(rows[sub]["$bag"])),
            "capture_peak_kib": {"$range": [0, bound]},
        }
    # Batch reading's worst shape here (section 4r): above the capture, at
    # most 1 GiB in DuckDB and one batch of at most batch_bytes (1 MiB).
    schema = [["id", "int64", False]]
    o = outcome("COMPLETE", "COMMIT_ACK")
    cells["sorted read"] = {
        "raised": None,
        "O": {"$outcome": {"fixed": o[:7], "batches": [n // 256, n]}},
        "rows_seen": [n, True],
        "schema": schema,
        "batch_schemas": [schema],
        "capture_peak_kib": {"$range": [0, (8 * n + a_bytes + 128 * MIB) // 1024]},
        "run_peak_kib": {"$range": [0, (1024 * MIB + MIB + 128 * MIB) // 1024]},
    }
    # L13's statement at 1 GiB, as L13 expects; the other limits recorded.
    cells["memory margin"] = {
        "raised": failed("PIE-R3003", None, "query", "OutOfMemoryException")
    }
    return cells


def _t2():
    cells = {}
    for cell, subs in cases.T2.items():
        cells[cell] = {sub: _t2_statement(cell, sub, s) for sub, s in subs.items()}
    cells["C25"] = _c25()
    cells["C27"] = _c27()
    cells["C28"] = _c28()
    return cells


def _b2():
    cells = _t2()
    for cell, subs in cases.B2.items():
        if cell == "C22":
            detail = "duckdb_projection_not_admitted"
            cells[cell] = {sub: _blocked(s, detail, TEXT_7) for sub, s in subs.items()}
        elif cell == "C21":
            cells[cell] = {sub: _capacity(sub, s) for sub, s in subs.items()}
        else:
            cells[cell] = {sub: _statement(sub, s) for sub, s in subs.items()}
    return cells


def expected():
    """Every expected value, keyed by cell then sub-case, in section 4's order."""
    loaded = [n for n in sys.modules if n.partition(".")[0] in ("duckdb", "_duckdb")]
    if loaded:
        raise AssertionError(f"the oracle loaded {loaded}")
    t5_p = bag(cases.T5, P_COLUMNS)
    driver = outcome("FAILED", "NOT_STARTED")
    nothing = {"calls": [], "modules": []}
    handle = {"raised": None, "end": "NOT_STARTED", **nothing}
    limit = {"raised": rejected("PIE-R1002", "DUCKDB_ARROW_CAPTURE_LIMIT"), **nothing}
    version = rejected("PIE-R2002", "ARROW_DEPENDENCY_VERSION")
    tn_c2 = [cases.encode(note) for note in cases.NOTES]
    tn_b = [r for r in cases.TN if r[1] != 1]
    unavailable = {
        "raised": rejected("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE"),
        "exists_after": [False, False],
    }
    cells = {
        "C01": {
            "": {"raised": rejected("PIE-R1002", "EXECUTION_ACCESS"), "modules": []}
        },
        "C02a": {
            "": {"rc": 0, "seen": C02A_SEEN, "loaded": [], "paths": {"$c02a": True}}
        },
        "C02b": {"": {"seen": C02B_SEEN, "end": "NOT_STARTED", "modules": []}},
        "C02c": {
            "a": {
                "raised": rejected("PIE-R2001", "ARROW_DEPENDENCY_MISSING"),
                "captured": 0,
            },
            "b": {"raised": version, "captured": 0},
            "c": {"raised": version, "captured": 0},
            "d": {"raised": version, "captured": 0},
        },
        "C03": {
            "a": {
                "raised": failed("PIE-R2001", "EXECUTION_DEPENDENCY_MISSING", "driver"),
                "O": driver,
                "calls": [],
            },
            "b": {
                "raised": failed("PIE-R2002", "EXECUTION_DRIVER_VERSION", "driver"),
                "O": driver,
                "calls": [],
            },
            "c": {
                "raised": failed("PIE-R2002", "EXECUTION_DRIVER_VERSION", "driver"),
                "O": driver,
                "calls": [],
                "modules": [],
                "marker": False,
            },
            "d": {
                "raised": failed("PIE-R2002", "EXECUTION_DRIVER_VERSION", "driver"),
                "O": driver,
                "calls": [],
            },
        },
        "C04": {
            "": {
                "raised": failed("PIE-R2002", "DUCKDB_DRIVER_PROFILE", "session"),
                "O": driver,
                "calls": [["connect", ":memory:"], ["close"]],
            }
        },
        "C05": {
            "a": handle,
            "b": limit,
            "c": handle,
            "d": limit,
            "e": handle,
            "f": {"raised": rejected("PIE-R1002", "DUCKDB_ARROW_SCHEMA"), **nothing},
            "g": limit,
        },
        "C06": {
            sub: {"raised": rejected("PIE-R1002", "DUCKDB_ARROW_SCHEMA"), **nothing}
            for sub in cases.C06_SUBS
        },
        "C07": {
            "P": complete(t5_p, SCHEMA_P, 1),
            "Q==": complete(
                bag([r for r in cases.T5 if r[1] == 10], Q_COLUMNS), SCHEMA_Q, 1
            ),
        },
        "C08": _c08(),
        "C09": {
            "": {
                "raised": None,
                "rows": bag([(7, 5, "a", True, 1.0)] * 2, Q_COLUMNS),
                "schema": SCHEMA_Q,
                "capture_names": ["c0", "c1", "c2", "c3", "c4"],
                "capture_rows": 2,
                "c0_data_size": 16,
                "ranges": {"$disjoint": True},
                "caller_ids_after": [9, 7],
            }
        },
        "C10": {
            "i": {
                **complete(t5_p, SCHEMA_P, 1),
                "E": EXTENSIONS,
                "settings": {"$settings": [list(row) for row in READ_BACK]},
                "K": {"$same": True},
                "hook_errors": [],
                "calls": OPENED + ENDED,
            },
            "ii": {
                "raised": failed("PIE-R3003", None, "query", "CatalogException"),
                "O": outcome("FAILED", "UNKNOWN"),
            },
        },
        "C11": _c11(),
        "C13": {"": complete(bag(cases.T5 * 2, P_COLUMNS), SCHEMA_P, 1)},
        "C14": {
            "a": {
                **complete(bag(cases.TN, P_COLUMNS), SCHEMA_P, 1),
                "capture_c2": tn_c2,
            },
            "b": {**complete(bag(tn_b, P_COLUMNS), SCHEMA_P, 1), "capture_c2": tn_c2},
            "c": {
                **complete(bag(cases.TN * 500, P_COLUMNS), SCHEMA_P, 24),
                "capture_c2": tn_c2 * 500,
            },
        },
        "C15": {
            sub: {"raised": rejected("PIE-R1004", "DUCKDB_BUNDLE_ENTRY")}
            if sub.endswith("bundle")
            else {"routes": {"$excludes": "duckdb_arrow"}}
            if sub == "job_store"
            else unavailable
            for sub in cases.C15_SUBS
        },
        "C16": {
            "": {
                "rows1": t5_p,
                "rows2": t5_p,
                "connects": [["connect", ":memory:"], ["connect", ":memory:"]],
                "connections": 2,
                "attempts": 2,
                "second_enter": {"class": "HandleMisuse", "code": "PIE-R4001"},
            }
        },
        **_b2(),
    }
    cells["C12"] = {
        "ns": {
            "interfaces": ["lo"],
            "netns": {"$differs": True},
            "before": {"home": [], "tmp": [], "cwd": []},
            "after": {"home": [], "tmp": [], "cwd": []},
        },
        **{
            f"{cell}/{sub}": cells[cell][sub]
            for cell in cases.REPEATED
            for sub in cases.CELLS[cell]
        },
    }
    ordered = {cell: cells[cell] for cell in cases.CELLS}
    for cell, subs in cases.CELLS.items():
        if tuple(ordered[cell]) != subs:
            raise AssertionError(f"{cell} sub-cases differ from the fixtures")
    return {
        "format": "pietto.duckdb-native.expected.v7",
        "spec_sha256": SPEC_SHA256,
        "child_sha256": CHILD_SHA256,
        "units": list(cases.UNITS),
        "u0_cells": list(cases.U0_CELLS),
        "skip": cases.SKIP,
        "identity": IDENTITY,
        "cells": ordered,
    }


def text() -> str:
    return json.dumps(expected(), indent=1, ensure_ascii=True) + "\n"


def main(argv: list[str]) -> int:
    """Write expected.json to argv[0]."""
    Path(argv[0]).write_text(text(), encoding="utf-8")
    return 0
