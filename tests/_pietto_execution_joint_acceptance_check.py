"""Independent checker of the Phase70 joint acceptance facts.

It imports neither Pietto nor the runner and opens nothing: every expected
outcome below is a literal, stated from its authority (the cell's slice and
docs/execution.md, docs/language.md and D70.02/D70.05), and every row bag is
stated by hand from the four published emission rows (id, flag, text:
9007199254740993, true, "trail 😀  " twice, then 0, false, "A" and 1, NULL,
"a "), which `p0` repeats. Only the native facts of both targets, in one
report or in two single-target reports `combined`, are ACCEPTED; offline facts
or one target alone are at most MATCHED.
"""

from __future__ import annotations

from collections import Counter
import json
import re
from typing import Any

FORMAT = "pietto.execution-joint-acceptance.v1"
ROUTES = {
    "postgres_rows": "postgres",
    "postgres_adbc": "postgres",
    "mysql_rows": "mysql",
}
OPERATIONS = ("execute", "save", "save_recoverable", "recover", "relay_live")
INTERPRETER = ["CPython", "3.13.13", "Linux", "x86_64"]
HEX64 = re.compile("[0-9a-f]{64}")
BIG = 9007199254740993
TRAIL = "trail 😀  "
TEXT = "雪?%s $1"
V1, V2 = "pietto.sql-emission.v1", "pietto.sql-emission.v2"

OK = "ok"
# Where a probe that passed every request check stops: the unopened workspace
# or the sink that does not exist.
WORKSPACE = ("PIE-R1009", "WORKSPACE_OBJECT")
SINK = ("PIE-R1002", "SINK_IDENTITY")
COMPUTED_KEY = ("PIE-R1004", "PUBLIC_R2_COMPUTED_GROUP_KEY")
VALUES_BASIS = ("PIE-R1004", "PUBLIC_R2_VALUES_COORDINATE_BASIS")
SERIES_BASIS = ("PIE-R1004", "PUBLIC_R2_TABLE_FUNCTION_COORDINATE_BASIS")
BLOCK_READ = ("PIE-R1004", "REFINEMENT_EXPRESSION_BLOCK_READ")
LATERAL = ("PIE-R1004", "REFINEMENT_LATERAL_JOIN")
# R2 accepts the shape before any workspace, but it has fewer than nine rows,
# so no prefix fails to recover: only the probes run.
PROBED = "probed"
BINDING_PARAMETERS = ("PIE-R1006", "BINDING_PARAMETERS")
BINDING_INVALID = ("PIE-R1004", "BINDING_INVALID")
BINDING_VECTOR = ("PIE-R1009", "BINDING_VECTOR")
CONSUMER_RELEASED = ("PIE-R1009", "CONSUMER_RELEASED")
PARAMETERS_TYPE = ("PIE-R1002", "PUBLIC_PARAMETERS_TYPE")

# The authorities of the cells.
LETS = "S03 docs/language.md relation lets; D70.05"
KEYS = "S05g docs/execution.md R2 computed group key; D70.05"
PARAMETERS = "S04b/S11 docs/execution.md#parameters; D70.01/D70.02"
POSITIONS = "S04r/S11 docs/language.md query header parameters"
WINDOWS = "S04w/S11 docs/language.md window arguments"
REUSE = "S05 docs/language.md relation lets (reuse, forward reads); D70.05"
KEYS_JOIN = "S05j docs/language.md computed keys with JOIN; docs/execution.md R2"
VALUES = "S06 docs/language.md typed VALUES; docs/execution.md R2 and MySQL"
EXISTS = "S08 docs/language.md relation reads; docs/execution.md R2"
SCALAR = "S07 docs/language.md relation reads; docs/execution.md Errors and R2"
MEMBERSHIP = "S09 docs/language.md relation reads; docs/execution.md R2"
CORRELATED = "S10 docs/language.md capture lines; docs/execution.md R2"
LATERAL_JOINS = "S12 docs/language.md LATERAL joins; docs/execution.md R2"
LEFT_LATERAL = "S13 docs/language.md LEFT LATERAL joins; docs/execution.md R2"
CORRELATED_READS = "S14 docs/language.md correlated scalar/IN; docs/execution.md R2"
ORDERED_READS = "S14 docs/language.md ORDER BY/LIMIT reads (PostgreSQL only)"
SERIES = "S15 docs/language.md generate_series; docs/execution.md R2 and MySQL"
SAVED_PARAMETERS = "S11 docs/execution.md#parameters (saved bindings, R2)"
CAPTURED_PARAMETERS = "S11 docs/language.md header reads in lets with capture lines"
# A scalar read of more than one row (docs/execution.md Errors) on every
# route, and the attempt the server's error ends (docs/execution.md Terminal
# states): PostgreSQL aborts the transaction and sends no ROLLBACK, so
# `postgres_rows` reports one PIE-R5001 cleanup failure and `postgres_adbc`
# closes locally without one; MySQL keeps the transaction and rolls it back
# (S16), with no cleanup failure and its local close state not pinned.
SCALAR_ROWS = ("PIE-R3003", "21000")
SERVER_ERROR_ATTEMPTS = {
    "postgres_rows": ["FAILED", "UNKNOWN", "FAILED", [["PIE-R5001", "transaction"]]],
    "postgres_adbc": ["FAILED", "UNKNOWN", "LOCAL_CLOSED_REMOTE_UNOBSERVED", []],
    "mysql_rows": ["FAILED", "ROLLBACK_ACK", None, []],
}


def _cell(expected: Any, authority: str) -> tuple:
    return expected, authority


def _plain_routes(authority: str, r2: Any = OK) -> dict[str, dict[str, tuple]]:
    """Every operation on every route, R2 as given."""
    return {
        route: {
            "execute": _cell(OK, authority),
            "save": _cell(OK, authority),
            "r2": _cell(r2, authority),
            "relay_live": _cell(OK, authority),
        }
        for route in ROUTES
    }


def _row(*values: Any) -> list[Any]:
    return list(values)


def _times(count: int, *values: Any) -> list[list[Any]]:
    return [list(values) for _ in range(count)]


# Literal oracles per shape: compile (format, parameters, slots, distinct
# PostgreSQL `$n`, MySQL `?` count), bundle, route cells, one row bag per
# binding, and the refused negatives and restated vectors.
ORACLES: dict[str, dict[str, Any]] = {
    # kept = all four rows (id >= 0); paired = rows CROSS JOIN kept.
    "let_chain": {
        "compile": (V1, [], ["Int"], 1, 1),
        "bundle": _cell(OK, LETS),
        "routes": _plain_routes(LETS),
        "rows": [
            _times(4, BIG, True)
            + _times(2, BIG, False)
            + _times(2, BIG, None)
            + _times(2, 0, True)
            + _times(1, 0, False)
            + _times(1, 0, None)
            + _times(2, 1, True)
            + _times(1, 1, False)
            + _times(1, 1, None)
        ],
        "negatives": {},
        "vectors": {"other_value": BINDING_VECTOR, "bool_for_int": BINDING_VECTOR},
    },
    # `other` is read only inside the let; rows CROSS JOIN picked.
    "let_hidden_source": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, LETS),
        "routes": _plain_routes(LETS),
        "rows": [
            _times(4, BIG, TRAIL)
            + _times(2, BIG, "A")
            + _times(2, BIG, "a ")
            + _times(2, 0, TRAIL)
            + _times(1, 0, "A")
            + _times(1, 0, "a ")
            + _times(2, 1, TRAIL)
            + _times(1, 1, "A")
            + _times(1, 1, "a ")
        ],
        "negatives": {},
        "vectors": {},
    },
    # positive = id > 0 groups {BIG, BIG, 1} and {0}; R2 refuses the
    # computed key before any workspace or connection.
    "computed_key": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, KEYS),
        "routes": _plain_routes(KEYS, r2=COMPUTED_KEY),
        "rows": [[_row(True, 3, BIG, 1), _row(False, 1, 0, 0)]],
        "negatives": {},
        "vectors": {},
    },
    # low 0: id > 0 keeps BIG, BIG, 1 and echoes NULL; low 1 keeps BIG, BIG.
    # PostgreSQL reuses $1/$2 for low/label and $3 for the slot; MySQL sends
    # low twice, label once and the slot. A saved NULL label is not "".
    "param_where": {
        "compile": (
            V2,
            [["low", "Int", False], ["label", "Text", True]],
            ["Int"],
            3,
            4,
        ),
        "bundle": _cell(OK, PARAMETERS),
        "routes": _plain_routes(PARAMETERS, r2=PROBED),
        "rows": [
            _times(2, BIG, None, 1) + [_row(1, None, 1)],
            _times(2, BIG, TEXT, 2),
        ],
        "negatives": {
            "missing": BINDING_PARAMETERS,
            "extra": BINDING_PARAMETERS,
            "not_a_dict": PARAMETERS_TYPE,
            "bool_for_int": ("PIE-R1006", "BINDING_PARAMETER:0:Int"),
            "null_for_not_null": ("PIE-R1006", "BINDING_PARAMETER:0:Int"),
            "int_for_text": ("PIE-R1006", "BINDING_PARAMETER:1:Text"),
            "obligation": BINDING_INVALID,
        },
        "vectors": {},
        "restated": {"empty_for_null": BINDING_VECTOR},
    },
    # k = id * low; a NULL high makes every s NULL. low 1: groups {BIG x2, 0,
    # 1}, only c > 1 survives; low 0 collapses all four rows into k = 0.
    "param_grouped": {
        "compile": (V2, [["low", "Int", False], ["high", "Int", True]], [], 2, 3),
        "bundle": _cell(OK, POSITIONS),
        "routes": _plain_routes(POSITIONS, r2=COMPUTED_KEY),
        "rows": [[_row(BIG, 2, 0, None, None)], [_row(0, 4, 0, None, None)]],
        "negatives": {
            "obligation": BINDING_INVALID,
            "null_for_not_null": ("PIE-R1006", "BINDING_PARAMETER:0:Int"),
        },
        "vectors": {},
    },
    # "a" is in "trail 😀  " (twice) and "a ", not in "A"; row_number over id
    # numbers 1, BIG, BIG as 1, 2, 3 and QUALIFY keeps r <= 2. A NULL label
    # keeps nothing. The ORDER key restates `s` and renders no placeholder.
    "param_result": {
        "compile": (V2, [["low", "Int", False], ["label", "Text", True]], [], 2, 4),
        "bundle": _cell(OK, POSITIONS),
        "routes": _plain_routes(POSITIONS, r2=PROBED),
        "rows": [[_row(1, 1, "a", 1), _row(BIG, BIG, "a", 2)], []],
        "negatives": {"obligation": BINDING_INVALID},
        "vectors": {},
    },
    # Over id ordered 0, 1, BIG, BIG: lag(id, 1, -1), ntile(2), the second
    # value of the whole frame; then lag(id, 0, 0), ntile(1), the first value.
    "param_window": {
        "compile": (
            V2,
            [
                ["k", "Int", False],
                ["b", "Int", False],
                ["p", "Int", False],
                ["f", "Int", False],
            ],
            [],
            4,
            4,
        ),
        "bundle": _cell(OK, WINDOWS),
        "routes": _plain_routes(WINDOWS, r2=PROBED),
        "rows": [
            [
                _row(0, -1, 1, 1),
                _row(1, 0, 1, 1),
                _row(BIG, 1, 2, 1),
                _row(BIG, BIG, 2, 1),
            ],
            [_row(0, 0, 1, 0), _row(1, 1, 1, 0)] + _times(2, BIG, BIG, 1, 0),
        ],
        "negatives": {
            "negative_offset": BINDING_INVALID,
            "zero_bucket": BINDING_INVALID,
            "zero_position": BINDING_INVALID,
            "null_count": ("PIE-R1006", "BINDING_PARAMETER:0:Int"),
        },
        "vectors": {},
    },
    # low = every id (BIG, BIG, 0, 1), high = id > 0 (BIG, BIG, 1); both read
    # the forward let `base`, and R2 refines the diamond like module
    # relations.
    "let_reuse": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, REUSE),
        "routes": _plain_routes(REUSE),
        "rows": [
            _times(4, BIG, BIG)
            + _times(2, BIG, 1)
            + _times(2, 0, BIG)
            + [_row(0, 1)]
            + _times(2, 1, BIG)
            + [_row(1, 1)]
        ],
        "negatives": {},
        "vectors": {},
    },
    # rows JOIN p0 on id: four BIG pairs, (0, 0) and (1, 1). Both ids > 0
    # holds for the BIG pairs and (1, 1); `level` is the right id.
    "computed_key_join": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, KEYS_JOIN),
        "routes": _plain_routes(KEYS_JOIN, r2=COMPUTED_KEY),
        "rows": [[_row(True, 5, 1, BIG), _row(False, 1, 0, 0)]],
        "negatives": {},
        "vectors": {},
    },
    # Seed rows (0, "z"), (1, NULL), (1, "y") match ids 0 and 1; BIG none.
    "values_join": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, VALUES),
        "routes": _plain_routes(VALUES, r2=VALUES_BASIS),
        "rows": [[_row(0, "z"), _row(1, None), _row(1, "y")]],
        "negatives": {},
        "vectors": {},
    },
    # Rows keep their duplicates; MySQL compiles no statement without a
    # physical relation.
    "values_only": {
        "compile": (V1, [], [], 0, 0),
        "blocked": {"mysql": ["zero_physical_source_not_admitted_on_target"]},
        "bundle": _cell(OK, VALUES),
        "routes": _plain_routes(VALUES, r2=VALUES_BASIS),
        "rows": [_times(2, 1, "a", 0.5, True) + [_row(2, None, None, None)]],
        "negatives": {},
        "vectors": {},
    },
    # p0 has rows with id > 0 and `none` has no row: every row is kept.
    "exists_closed": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, EXISTS),
        "routes": _plain_routes(EXISTS, r2=BLOCK_READ),
        "rows": [
            _times(2, BIG, True, False) + [_row(0, True, False), _row(1, True, False)]
        ],
        "negatives": {},
        "vectors": {},
    },
    # min(id) = 0 keeps BIG, BIG and 1; the read of no row is NULL.
    "scalar_closed": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, SCALAR),
        "routes": _plain_routes(SCALAR, r2=BLOCK_READ),
        "rows": [_times(2, BIG, 0, None) + [_row(1, 0, None)]],
        "negatives": {},
        "vectors": {},
    },
    # Every attempt fails on the server: execute, save and relay_live run and
    # fail, and no generation completes.
    "scalar_many": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, SCALAR),
        "routes": _plain_routes(SCALAR, r2=BLOCK_READ),
        "failure": SCALAR_ROWS,
        "rows": [[]],
        "negatives": {},
        "vectors": {},
    },
    # smallest = {0}; flags (TRUE, TRUE, FALSE, NULL) against no flag, two
    # TRUE, one NULL and all four, as (in, not in) pairs: an empty relation
    # is (FALSE, TRUE) even for NULL, a NULL value against rows and a
    # non-member against a relation holding NULL are NULL.
    "in_closed": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, MEMBERSHIP),
        "routes": _plain_routes(MEMBERSHIP, r2=BLOCK_READ),
        "rows": [
            # id, flag, capped, then (in, not in) per relation: none, true,
            # null, all.
            _times(
                2, BIG, True, False, False, True, True, False, None, None, True, False
            )
            + [
                _row(0, False, True, False, True, False, True, None, None, True, False),
                _row(1, None, False, False, True, None, None, None, None, None, None),
            ]
        ],
        "negatives": {},
        "vectors": {},
    },
    # Only p0's (1, NULL) has a NULL flag: it is at most BIG, BIG and 1, not
    # 0. Nothing in p0 exceeds BIG; BIG exceeds 1.
    "exists_correlated": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, CORRELATED),
        "routes": _plain_routes(CORRELATED, r2=BLOCK_READ),
        "rows": [_times(2, BIG, False) + [_row(1, True)]],
        "negatives": {},
        "vectors": {},
    },
    # The least p0 id above 0 is 1 and above 1 is BIG (two tied rows, equal
    # values); BIG has none, so CROSS drops it. `twin` of 1 is p0's (1, NULL),
    # which ON i > 1 drops; `twin` of BIG is p0's two (BIG, true) rows.
    "lateral_inner": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, LATERAL_JOINS),
        "routes": _plain_routes(LATERAL_JOINS, r2=LATERAL),
        "rows": [_times(2, 1, BIG, True)],
        "negatives": {},
        "vectors": {},
    },
    # BIG has no larger p0 id (one NULL row each); 0 pairs only with 1; the
    # ON rejects both BIG pairs of 1, which keeps one NULL row.
    "lateral_left": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, LEFT_LATERAL),
        "routes": _plain_routes(LEFT_LATERAL, r2=LATERAL),
        "rows": [_times(2, BIG, None) + [_row(0, 1), _row(1, None)]],
        "negatives": {},
        "vectors": {},
    },
    # Per row: the text of the p0 twin below 2 (none for BIG), its flag IN
    # the flags of smaller p0 ids (BIG: {false, NULL}, 0: none, 1: {false})
    # and NOT IN the flags of larger ones (BIG: none, 0: {true, true, NULL},
    # 1: {true, true}).
    "scalar_in_correlated": {
        "compile": (V1, [], [], 0, 0),
        "bundle": _cell(OK, CORRELATED_READS),
        "routes": _plain_routes(CORRELATED_READS, r2=BLOCK_READ),
        "rows": [
            _times(2, BIG, None, None, True)
            + [_row(0, "A", False, None), _row(1, "a ", None, None)]
        ],
        "negatives": {},
        "vectors": {},
    },
    # p0 ids at least the row's own: the DESC pick is BIG, the ASC pick the
    # row's own id. MySQL BLOCKS each such read, in source order.
    "in_limit": {
        "compile": (V1, [], [], 0, 0),
        "blocked": {"mysql": ["mysql_correlated_order_or_limit_read_not_admitted"] * 2},
        "bundle": _cell(OK, ORDERED_READS),
        "routes": _plain_routes(ORDERED_READS, r2=BLOCK_READ),
        "rows": [
            _times(2, BIG, True, True) + [_row(0, False, True), _row(1, False, True)]
        ],
        "negatives": {},
        "vectors": {},
    },
    # 5 down to -1 by 3; MySQL BLOCKS the table function itself.
    "series_only": {
        "compile": (V1, [], [], 0, 0),
        "blocked": {"mysql": ["table_function_not_admitted_on_target"]},
        "bundle": _cell(OK, SERIES),
        "routes": _plain_routes(SERIES, r2=SERIES_BASIS),
        "rows": [[_row(5), _row(2), _row(-1)]],
        "negatives": {},
        "vectors": {},
    },
    # 2, 1, 0 joined on id: 1 and 0 match once each, 2 not at all.
    "series_join": {
        "compile": (V1, [], [], 0, 0),
        "blocked": {"mysql": ["table_function_not_admitted_on_target"]},
        "bundle": _cell(OK, SERIES),
        "routes": _plain_routes(SERIES, r2=SERIES_BASIS),
        "rows": [[_row(1, "a "), _row(0, "A")]],
        "negatives": {},
        "vectors": {},
    },
    # `tagged` keeps a row whose p0 twin's text differs from label: with "a "
    # all but 1, with the other text every row. `bigger` holds the p0 ids
    # above the row's and above cut (cut 1: BIG, BIG for 0; cut 0: also 1 for
    # 0, BIG, BIG for 1) and none for BIG. The ON rows.id != cut keeps no pair
    # of 0 under cut 0, so 0 keeps one NULL row, as BIG does. PostgreSQL
    # reuses $1 for cut; MySQL sends cut twice and label once.
    "param_capture": {
        "compile": (
            V2,
            [["cut", "Int", False], ["label", "Text", True]],
            [],
            2,
            3,
        ),
        "bundle": _cell(OK, CAPTURED_PARAMETERS),
        "routes": _plain_routes(CAPTURED_PARAMETERS, r2=BLOCK_READ),
        "rows": [
            _times(2, BIG, None) + _times(2, 0, BIG),
            _times(2, BIG, None) + [_row(0, None)] + _times(2, 1, BIG),
        ],
        "negatives": {},
        "vectors": {},
    },
    # low 1: rows BIG, BIG, 1 CROSS JOIN p0 BIG, BIG, 1 (nine rows, so the
    # prefix of eight fails and recover completes); low 2: BIG, BIG twice.
    # Every restatement of the saved {"low": 1} is BINDING_VECTOR, True
    # included.
    "param_r2": {
        "compile": (V2, [["low", "Int", False]], [], 1, 2),
        "bundle": _cell(OK, SAVED_PARAMETERS),
        "routes": _plain_routes(SAVED_PARAMETERS),
        "rows": [
            _times(4, BIG, BIG) + _times(2, BIG, 1) + _times(2, 1, BIG) + [_row(1, 1)],
            _times(4, BIG, BIG),
        ],
        "negatives": {},
        "vectors": {},
        "restated": {
            "other_value": BINDING_VECTOR,
            "bool_for_int": BINDING_VECTOR,
            "missing": BINDING_VECTOR,
        },
    },
}
POLICIES = {"let_chain": "bind-safe", "param_where": "bind-safe"}


class Rejected(ValueError):
    """The facts do not satisfy the literal oracle named by the reason."""


def need(condition: object, reason: str) -> None:
    if not condition:
        raise Rejected(reason)


def _record(value: Any, reason: str) -> Any:
    """`value` when it is a JSON object; raw facts stay untyped."""
    need(type(value) is dict, reason)
    return value


def _items(value: Any, reason: str) -> Any:
    """`value` when it is a JSON array; raw facts stay untyped."""
    need(type(value) is list, reason)
    return value


def _bag(rows: Any) -> Counter:
    need(all(type(row) is list for row in _items(rows, "BAG")), "BAG")
    return Counter(json.dumps(row, sort_keys=True) for row in rows)


def _refused(fact: Any, expected: tuple[str, str], reason: str) -> None:
    fact = _record(fact, reason)
    need(fact.get("outcome") == "refused", reason)
    need((fact.get("code"), fact.get("detail")) == expected, reason)


def _blocked(name: str) -> dict[str, list[str]]:
    """The dialects whose compile_query BLOCKS the shape, with the word of
    each blocked input in source order."""
    return ORACLES[name].get("blocked", {})


def _check_compile(name: str, dialect: str, fact: Any) -> None:
    reason = "COMPILE_" + name + "_" + dialect
    form, parameters, slots, dollars, marks = ORACLES[name]["compile"]
    fact = _record(fact, reason)
    if dialect in _blocked(name):
        words = _blocked(name)[dialect]
        need(
            fact
            == {
                "outcome": "rejected",
                "status": "BLOCKED",
                "codes": ["PIE-B1003"] * len(words),
                "details": words,
            },
            reason,
        )
        return
    need(fact.get("outcome") == "compiled", reason)
    need(
        (
            fact.get("origin"),
            fact.get("format"),
            fact.get("parameters"),
            fact.get("slots"),
        )
        == ("live", form, parameters, slots),
        reason,
    )
    reason = "SQL_" + name + "_" + dialect
    sql = fact.get("sql")
    need(type(sql) is str, reason)
    numbers = {int(item) for item in re.findall(r"\$([0-9]+)", str(sql))}
    if dialect == "postgres":
        need(numbers == set(range(1, dollars + 1)) and "?" not in sql, reason)
    else:
        need(not numbers and str(sql).count("?") == marks, reason)


def _check_bundle(name: str, dialect: str, fact: Any) -> None:
    reason = "BUNDLE_" + name + "_" + dialect
    if dialect in _blocked(name):
        need(fact is None, reason)
        return
    expected, _authority = ORACLES[name]["bundle"]
    if expected != OK:
        _refused(fact, expected, reason)
        return
    fact = _record(fact, reason)
    need(fact.get("outcome") == "loaded", reason)
    records = _items(fact.get("records"), reason)
    need(
        len(records) == 3
        and all(type(r) is str and HEX64.fullmatch(r) for r in records),
        reason,
    )
    _form, parameters, slots, _dollars, _marks = ORACLES[name]["compile"]
    loaded = [
        "bundle",
        "main.pietto",
        "query",
        "result",
        dialect,
        POLICIES.get(name, "preserve"),
        slots,
        parameters,
        None,
    ]
    need(fact.get("query") == loaded, reason)
    need(fact.get("reexported") == [True, True, True, True], reason)


def _check_probe(reason: str, fact: Any, expected: Any, reached: Any) -> None:
    fact = _record(fact, reason)
    need(fact.get("connected") is False and fact.get("workspace") is False, reason)
    if expected not in (OK, PROBED):
        _refused(fact, expected, reason)
    elif reached == "prepared":
        need(fact.get("outcome") == "prepared", reason)
    else:
        _refused(fact, reached, reason)


def _check_rows(reason: str, rows: Any, expected: list[list[Any]]) -> None:
    need(_bag(rows) == _bag(expected), reason)


def _check_execute(reason: str, fact: Any, expected: list[list[Any]]) -> None:
    fact = _record(fact, reason)
    need(fact.get("outcome") == "rows", reason)
    need((fact.get("end"), fact.get("primary")) == ("COMPLETE", None), reason)
    _check_rows(reason, fact.get("rows"), expected)


def _check_failed(reason: str, fact: Any, failure: Any, route: str) -> None:
    """An attempt the server failed, with the route's transaction and
    cleanup facts (None: not pinned)."""
    fact = _record(fact, reason)
    need(
        (fact.get("outcome"), fact.get("error"), fact.get("code"), fact.get("sqlstate"))
        == ("failed", "AttemptFailed", *failure),
        reason,
    )
    attempt = _items(fact.get("attempt"), reason)
    expected = SERVER_ERROR_ATTEMPTS[route]
    need(len(attempt) == len(expected), reason)
    for value, oracle in zip(attempt, expected):
        need(oracle is None or value == oracle, reason)


def _check_restated(reason: str, facts: Any, oracle: Any) -> None:
    """Each refused restatement of the saved parameters, and no other."""
    expected = oracle.get("restated", {})
    facts = _record(facts, reason)
    need(set(facts) == set(expected), reason)
    for name, refusal in expected.items():
        _refused(facts[name], refusal, reason)


def _check_unfinished(reason: str, fact: Any) -> None:
    """A save or relay whose attempt failed: no generation to read."""
    fact = _record(fact, reason)
    need(set(fact) == {"terminal", "settlement", "cleanup"}, reason)
    need((fact.get("terminal"), fact.get("cleanup")) == ("FAILED", False), reason)


def _check_native(name: str, facts: Any, cells: Any, route: str) -> None:
    """The real operations of one route: exactly those whose cell is OK."""
    reasons = name + "_" + route
    oracle = ORACLES[name]
    rows = oracle["rows"]
    failure = oracle.get("failure")
    extent = len(rows[0])
    native = _record(facts.get("native"), "NATIVE_" + reasons)
    ran = {
        column
        for column in ("execute", "save", "r2", "relay_live")
        if cells[column][0] == OK
    }
    need(set(native) == ran, "NATIVE_" + reasons)
    if "execute" in ran:
        reason = "EXECUTE_" + reasons
        runs = _items(native["execute"], reason)
        need(len(runs) == len(rows), reason)
        for run, bag in zip(runs, rows):
            run = _record(run, reason)
            if failure is not None:
                _check_failed(reason, run.get("live"), failure, route)
            else:
                _check_execute(reason, run.get("live"), bag)
            if oracle["bundle"][0] != OK:
                need(run.get("loaded") is None, "LOADED_" + reasons)
            elif failure is not None:
                _check_failed("LOADED_" + reasons, run.get("loaded"), failure, route)
            else:
                _check_execute("LOADED_" + reasons, run.get("loaded"), bag)
    if failure is not None:
        for column, law in (("save", "SAVE_"), ("relay_live", "RELAY_")):
            if column in ran:
                _check_unfinished(law + reasons, native[column])
        need("r2" not in ran, "R2_" + reasons)
        return
    if "save" in ran:
        save = _record(native["save"], "SAVE_" + reasons)
        need(
            (
                save.get("terminal"),
                save.get("settlement"),
                save.get("cleanup"),
                save.get("extent"),
                save.get("closings"),
            )
            == ("COMPLETED", "RELEASED", False, extent, 1),
            "SAVE_" + reasons,
        )
        r1 = _record(save.get("r1"), "R1_" + reasons)
        need(
            r1.get("end") == ["SAVED_SCOPE_EXHAUSTED", True, extent, extent],
            "R1_" + reasons,
        )
        _check_rows("R1_" + reasons, r1.get("rows"), rows[0])
        _check_rows("R1_EXPORT_" + reasons, r1.get("export"), rows[0])
        need(
            r1.get("publication") == ["PUBLISHED", extent],
            "R1_PUBLICATION_" + reasons,
        )
        vectors = _record(r1.get("vectors"), "R1_VECTOR_" + reasons)
        need(set(vectors) == set(oracle["vectors"]), "R1_VECTOR_" + reasons)
        for vector, refusal in oracle["vectors"].items():
            _refused(vectors[vector], refusal, "R1_VECTOR_" + reasons)
        _check_restated("R1_RESTATED_" + reasons, r1.get("restated"), oracle)
        need(r1.get("release") == "release_retention", "R1_RELEASE_" + reasons)
        _refused(r1.get("released_reopen"), CONSUMER_RELEASED, "R1_RELEASE_" + reasons)
    if "r2" in ran:
        r2 = _record(native["r2"], "R2_" + reasons)
        need(
            r2.get("prefix") == ["FAILED", False]
            and r2.get("prefix_closings") == 1
            and r2.get("recover") == ["COMPLETED", "RELEASED", False]
            and (r2.get("closings"), r2.get("extent")) == (2, extent),
            "R2_" + reasons,
        )
        _check_rows("R2_" + reasons, r2.get("rows"), rows[0])
        _check_restated("R2_RESTATED_" + reasons, r2.get("restated"), oracle)
    if "relay_live" in ran:
        relay = _record(native["relay_live"], "RELAY_" + reasons)
        need(
            (
                relay.get("terminal"),
                relay.get("settlement"),
                relay.get("cleanup"),
                relay.get("extent"),
            )
            == ("COMPLETED", "RELEASED", False, extent),
            "RELAY_" + reasons,
        )


def check_shape(name: str, record: Any, mode: str, routes: Any) -> None:
    """Judge one shape's facts on `routes`."""
    need(name in ORACLES, "SHAPE_" + name)
    oracle = ORACLES[name]
    record = _record(record, "SHAPE_" + name)
    dialects = _record(record.get("dialects"), "DIALECTS_" + name)
    need(set(dialects) == {ROUTES[route] for route in routes}, "DIALECTS_" + name)
    for dialect, fact in dialects.items():
        fact = _record(fact, "DIALECTS_" + name)
        _check_compile(name, dialect, fact.get("compile"))
        _check_bundle(name, dialect, fact.get("bundle"))
    # A dialect that BLOCKS the shape has no compiled query for its routes.
    routes = [route for route in routes if ROUTES[route] not in _blocked(name)]
    facts = _record(record.get("routes"), "ROUTES_" + name)
    need(set(facts) == set(routes), "ROUTES_" + name)
    for route in routes:
        cells = oracle["routes"][route]
        reasons = name + "_" + route
        route_facts = _record(facts[route], "ROUTE_" + reasons)
        probes = _record(route_facts.get("probe"), "PROBE_" + reasons)
        need(set(probes) == set(OPERATIONS), "PROBE_" + reasons)
        for operation in OPERATIONS:
            column = "r2" if operation in ("save_recoverable", "recover") else operation
            expected, _authority = cells[column]
            reached = {"execute": "prepared", "relay_live": SINK}.get(
                operation, WORKSPACE
            )
            _check_probe(
                "PROBE_" + reasons + "_" + operation,
                probes[operation],
                expected,
                reached,
            )
        negatives = _record(route_facts.get("negatives"), "NEGATIVE_" + reasons)
        need(set(negatives) == set(oracle["negatives"]), "NEGATIVE_" + reasons)
        for negative, refusal in oracle["negatives"].items():
            _check_probe(
                "NEGATIVE_" + reasons + "_" + negative,
                negatives[negative],
                refusal,
                None,
            )
        if mode == "offline":
            need("native" not in route_facts, "NATIVE_" + reasons)
        else:
            _check_native(name, route_facts, cells, route)


def _check_native_envelope(report: Any) -> tuple[list[str], list[str]]:
    """The campaign's identity, prefix, workers and cleanup; returns the
    targets and the routes left pending by a missing target."""
    context = _record(report.get("context"), "CONTEXT")
    for key in ("probe", "check", "docs", "wheel_sha256"):
        need(type(context.get(key)) is str and HEX64.fullmatch(context[key]), "CONTEXT")
    wheel = context.get("wheel")
    need(type(wheel) is str and wheel.endswith("-py3-none-any.whl"), "CONTEXT")
    install = _record(report.get("install"), "INSTALL")
    prefix = _record(install.get("routes"), "INSTALL")
    for step in ("venv", "install", "check"):
        need(_record(prefix.get(step), "INSTALL").get("returncode") == 0, "INSTALL")
    need(prefix.get("python") == INTERPRETER, "INSTALL")
    targets = _items(report.get("targets"), "TARGETS")
    need(
        targets
        and len(set(targets)) == len(targets)
        and set(targets) <= {"postgres", "mysql"},
        "TARGETS",
    )
    workers = _record(report.get("workers"), "WORKER")
    need(set(workers) == set(targets), "WORKER")
    for target in targets:
        worker = _record(workers[target], "WORKER")
        need(worker.get("returncode") == 0, "WORKER")
        need(worker.get("origin") == "installed", "WORKER")
    cleanup = _record(report.get("cleanup"), "CLEANUP")
    need(set(cleanup) == set(targets), "CLEANUP")
    need(all(value == "success" for value in cleanup.values()), "CLEANUP")
    missing = [f"route:{r}" for r, target in ROUTES.items() if target not in targets]
    return targets, missing


def combined(reports: Any) -> dict[str, Any]:
    """One native report of the campaigns of disjoint targets that ran the
    same probe, checker, docs and wheel; each campaign's envelope is checked
    first."""
    reports = [_record(report, "ENVELOPE") for report in _items(reports, "ENVELOPE")]
    need(reports, "ENVELOPE")
    for report in reports:
        need((report.get("format"), report.get("mode")) == (FORMAT, "native"), "MODE")
        _check_native_envelope(report)
    first = reports[0]
    need(all(r["context"] == first["context"] for r in reports), "CONTEXT")
    targets = [target for report in reports for target in report["targets"]]
    need(len(set(targets)) == len(targets), "TARGETS")
    shapes: dict[str, Any] = {}
    for report in reports:
        for name, record in _record(report.get("shapes"), "SHAPES").items():
            record = _record(record, "SHAPE_" + name)
            entry = shapes.setdefault(name, {"dialects": {}, "routes": {}})
            entry["dialects"].update(
                _record(record.get("dialects"), "DIALECTS_" + name)
            )
            entry["routes"].update(_record(record.get("routes"), "ROUTES_" + name))
    return {
        "format": FORMAT,
        "mode": "native",
        "context": first["context"],
        "install": first["install"],
        "targets": targets,
        "workers": {k: v for r in reports for k, v in r["workers"].items()},
        "cleanup": {k: v for r in reports for k, v in r["cleanup"].items()},
        "shapes": shapes,
    }


def check(report: Any) -> dict[str, Any]:
    """Judge one offline or native report; raises Rejected(<LAW>_<cell>)."""
    report = _record(report, "ENVELOPE")
    need(report.get("format") == FORMAT, "FORMAT")
    mode = report.get("mode")
    need(mode in ("offline", "native"), "MODE")
    if mode == "native":
        targets, pending = _check_native_envelope(report)
    else:
        targets, pending = ["postgres", "mysql"], ["offline"]
    routes = [route for route, target in ROUTES.items() if target in targets]
    shapes = _record(report.get("shapes"), "SHAPES")
    need(set(shapes) == set(ORACLES), "SHAPES")
    for name in ORACLES:
        check_shape(name, shapes[name], str(mode), routes)
    return {
        "family": "joint-acceptance",
        "mode": mode,
        "verdict": "MATCHED" if pending else "ACCEPTED",
        "pending": sorted(set(pending)),
    }
