"""The oracle of the Phase79 S06 native qualification (preregistration v4,
sections 3, 4 and 4a-4e): every expected value, derived in pure Python from
the fixtures of `_pietto_execution_duckdb_native_cases` and the values the
preregistration states. Writes expected.json; loads no DuckDB."""

from __future__ import annotations

import json
import operator
import sys
from pathlib import Path

import _pietto_execution_duckdb_native_cases as cases

SPEC_SHA256 = "b555959784f18d51bcc11f08c2cc4d6d60fe9e23a2aaf8bf9f94fb5c37ec441a"
CHILD_SHA256 = "e88dafbbc7e4a06a442bc61f5c1ca4c5ea2909398d019f404861143bd600db77"
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
# Section 4a: the 35 rows read back, as duckdb_settings() returns them.
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
    ("memory_limit", "256.0 MiB"),
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
    ("logging_storage", "memory"),
    ("access_mode", "automatic"),
    ("worker_threads", "1"),
    ("max_memory", "256.0 MiB"),
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
        "version": "2.0.0",
        "tags": [
            "cp312-abi3-manylinux_2_27_x86_64",
            "cp312-abi3-manylinux_2_28_x86_64",
        ],
        "record_hashed": 68,
        "pragma_version": ["v2.0.0", "d54cbbe3df"],
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
            "O": outcome("STOPPED_EARLY", "COMMIT_ACK"),
            "calls": lived,
            "second_enter": {"class": "HandleMisuse", "code": "PIE-R4001"},
        },
        "L3": {
            "raised": {"class": "LookupError", "same": True},
            "O": outcome("FAILED", "COMMIT_ACK", batches=1),
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
            "O": outcome("DEADLINE", "COMMIT_ACK", req=True, late=True),
            "calls": lived,
            "hook_errors": [],
        },
        "L8": {
            "raised": cancelled,
            "O": outcome("CANCELLED", "COMMIT_ACK", req=True),
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
            "O": outcome("FAILED", "COMMIT_ACK"),
            "calls": lived,
        },
        "L12": {
            "raised": failed("PIE-R3004", "EXECUTION_RESOURCE_LIMIT", "delivery"),
            "O": outcome("FAILED", "COMMIT_ACK"),
            "calls": lived,
        },
    }


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
        "C05": {"a": handle, "b": limit, "c": handle, "d": limit, "e": limit},
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
            "bundle": {"raised": rejected("PIE-R1004", "DUCKDB_BUNDLE_ENTRY")},
            "save": unavailable,
            "save_recoverable": unavailable,
            "recover": unavailable,
            "relay_live": unavailable,
            "job_store": {"routes": {"$excludes": "duckdb_arrow"}},
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
        "format": "pietto.s06-duckdb-native.expected.v1",
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
