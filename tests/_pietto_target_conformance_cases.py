"""Six finite, independently specified target controls; no resource acquisition."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
import json
import hashlib
from typing import Any
import _pietto_phase66_sql_emission_probe as emission
from _pietto_mysql_native_prepared import API, verify_native

TARGETS = ("postgres", "mysql")
SLICE2_CASE_IDS = (
    "A_legacy",
    "B_result",
    "C_parameters",
    "D_diagnostics",
    "E_recovery",
    "F_privilege_cleanup",
)
CASE_IDS = (
    *SLICE2_CASE_IDS,
    *sorted((*emission.VARIANTS, "Q_native_lifecycle")),
    emission.CONSOLE_CASE,
)
BIG = 9007199254740993
TEXT = "雪?%s e\u0301 😀"


def legacy_source(target: str) -> str:
    if target not in TARGETS:
        raise ValueError("unknown target")
    return (
        "shape LegacyRow:\n    id: Int not null\n"
        f'source source_rows: LegacyRow is {target}.table("phase66_rows")\n'
        "table legacy_rows:\n    from source_rows\n    select:\n        id\n"
    )


def legacy_sql(target: str) -> str:
    quote = '"' if target == "postgres" else "`"
    return f"SELECT\n    {quote}id{quote} AS {quote}id{quote}\nFROM {quote}phase66_rows{quote}"


def control(target: str, case: str) -> tuple[str, tuple[object, ...]]:
    if case == "B_result":
        return "SELECT id, note FROM phase66_control_rows ORDER BY seq", ()
    if case == "C_parameters":
        if target == "postgres":
            return "SELECT $1::bigint AS a, $2::text AS txt, $1::bigint AS again", (
                BIG,
                TEXT,
            )
        return (
            "SELECT CAST(? AS SIGNED) AS a, CAST(? AS CHAR CHARACTER SET utf8mb4) AS txt, CAST(? AS SIGNED) AS again",
            (BIG, TEXT, BIG),
        )
    raise ValueError("unknown control")


def setup(target: str) -> tuple[tuple[str, tuple[object, ...]], ...]:
    markers = ("$1", "$2", "$3") if target == "postgres" else ("?", "?", "?")
    return (
        (
            ("CREATE TABLE phase66_rows (id BIGINT NOT NULL)", ()),
            ("INSERT INTO phase66_rows VALUES (1), (1)", ()),
            (
                "CREATE TABLE phase66_control_rows (seq INTEGER NOT NULL, id BIGINT NOT NULL, note VARCHAR(64))",
                (),
            ),
            (
                f"INSERT INTO phase66_control_rows VALUES ({', '.join(markers)})",
                (1, 7, None),
            ),
            (
                f"INSERT INTO phase66_control_rows VALUES ({', '.join(markers)})",
                (2, 7, None),
            ),
            (
                f"INSERT INTO phase66_control_rows VALUES ({', '.join(markers)})",
                (3, BIG, TEXT),
            ),
            ("CREATE TABLE phase66_diagnostic_rows (value VARCHAR(5))", ()),
        )
        + emission_setup(target)
        + native_setup(target)
        + row_domain_setup(target)
    )


def native_setup(target):
    quote = '"' if target == "postgres" else chr(96)

    def identifier(value):
        return quote + value.replace(quote, quote * 2) + quote

    columns = ", ".join(
        identifier(name) + " BIGINT" + (" NOT NULL" if i < 3 else "")
        for i, name in enumerate(('%s"', '?"', "%s", "neighbor"))
    )
    return (
        (f"CREATE TABLE {identifier('phase66 native')} ({columns})", ()),
        (f"CREATE TABLE {identifier('phase66 native empty')} ({columns})", ()),
        (
            f"INSERT INTO {identifier('phase66 native')} VALUES (11,99,7,NULL),(11,99,7,NULL)",
            (),
        ),
    )


def row_domain_setup(target):
    """C06 physical row domains, appended after every inherited relation.

    PostgreSQL: a keyed parent whose INHERITS child repeats key 1, a view over
    the parent alone, and a SMALLINT LIST-partitioned root. MySQL has no
    inheritance: its declared family is a view over two separately keyed tables,
    beside the same parent-only view and partitioned root. Every row below is the
    oracle; the query role's grants are issued after this setup.
    """
    if target == "postgres":
        return (
            ('CREATE TABLE "phase66 parent" ("id" BIGINT NOT NULL PRIMARY KEY)', ()),
            ('CREATE TABLE "phase66 child" () INHERITS ("phase66 parent")', ()),
            ('INSERT INTO "phase66 parent" VALUES (1), (2)', ()),
            ('INSERT INTO "phase66 child" VALUES (1)', ()),
            (
                'CREATE VIEW "phase66 parent only" AS SELECT "id" FROM ONLY "phase66 parent"',
                (),
            ),
            (
                'CREATE TABLE "phase66 part" ("id" SMALLINT NOT NULL) PARTITION BY LIST ("id")',
                (),
            ),
            (
                'CREATE TABLE "phase66 part one" PARTITION OF "phase66 part" FOR VALUES IN (1)',
                (),
            ),
            (
                'CREATE TABLE "phase66 part two" PARTITION OF "phase66 part" FOR VALUES IN (2)',
                (),
            ),
            ('INSERT INTO "phase66 part" VALUES (1), (1), (2)', ()),
        )
    return (
        ("CREATE TABLE `phase66 parent` (`id` BIGINT NOT NULL PRIMARY KEY)", ()),
        ("CREATE TABLE `phase66 child` (`id` BIGINT NOT NULL PRIMARY KEY)", ()),
        ("INSERT INTO `phase66 parent` VALUES (1), (2)", ()),
        ("INSERT INTO `phase66 child` VALUES (1)", ()),
        (
            "CREATE VIEW `phase66 family` AS SELECT `id` FROM `phase66 parent`"
            " UNION ALL SELECT `id` FROM `phase66 child`",
            (),
        ),
        (
            "CREATE VIEW `phase66 parent only` AS SELECT `id` FROM `phase66 parent`",
            (),
        ),
        (
            "CREATE TABLE `phase66 part` (`id` SMALLINT NOT NULL) PARTITION BY LIST"
            " (`id`) (PARTITION `one` VALUES IN (1), PARTITION `two` VALUES IN (2))",
            (),
        ),
        ("INSERT INTO `phase66 part` VALUES (1), (1), (2)", ()),
    )


def row_domain_expectation(target, variant):
    """(rows, labels, physical types, ordered) of one C06 row-domain witness.

    The declared parent/family domain keeps key 1 from both parent and child, so
    neither ONLY nor a parent-only uniqueness constraint narrows it; the view is
    the parent alone; the partition root is every partition's rows, and its
    offset RANGE of 40000 over a SMALLINT key reaches every preceding row. The
    first row in key order has no predecessor, so it alone returns the default.

    The window types are each target's own rule, never the observed server's:
    PostgreSQL's first_value keeps int2 and its anycompatible lag takes the int4
    literal 999999999; MySQL materializes the 6-character SMALLINT first_value
    as INT and the 10-character default (nine digits and a sign place) as BIGINT.
    """
    bigint = 20 if target == "postgres" else 8
    smallint = 21 if target == "postgres" else 2
    if variant == "inherited_parent":
        return [[_int("1")], [_int("1")], [_int("2")]], ("id",), [bigint], True
    if variant == "view_rows":
        return [[_int("1")], [_int("2")]], ("id",), [bigint], False
    if variant == "partitioned_root":
        return (
            [
                [_int("1"), _int("1"), _int("999999999")],
                [_int("1"), _int("1"), _int("1")],
                [_int("2"), _int("1"), _int("1")],
            ],
            ("id", "low", "high"),
            [smallint, smallint, 23] if target == "postgres" else [smallint, 3, 8],
            False,
        )
    raise ValueError("unknown row-domain variant")


def emission_setup(target):
    if target == "postgres":
        columns = '"order.id" BIGINT NOT NULL, "flag value" BOOLEAN, "text `""é" TEXT COLLATE "C" NOT NULL, "amount value" NUMERIC(9,2) NOT NULL, "ratio value" DOUBLE PRECISION NOT NULL'
        names = ('"phase66 source é"', '"phase66 empty é"')
        parameters = "$1, $2, $3, $4, $5"
    else:
        columns = '`order.id` BIGINT NOT NULL, `flag value` TINYINT, `text ``"é` VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL, `amount value` DECIMAL(9,2) NOT NULL, `ratio value` DOUBLE NOT NULL'
        names = ("`phase66 source é`", "`phase66 empty é`")
        parameters = "?, ?, ?, ?, ?"
    rows = (
        (
            BIG,
            True if target == "postgres" else 1,
            "trail 😀  ",
            Decimal("12.30"),
            -0.0,
        ),
        (
            BIG,
            True if target == "postgres" else 1,
            "trail 😀  ",
            Decimal("12.30"),
            -0.0,
        ),
        (0, False if target == "postgres" else 0, "A", Decimal("0.00"), 1.5),
        (1, None, "a ", Decimal("-0.01"), 0.0),
    )
    collision = '"p0"' if target == "postgres" else "`p0`"
    return (
        tuple((f"CREATE TABLE {name} ({columns})", ()) for name in names)
        + tuple((f"INSERT INTO {names[0]} VALUES ({parameters})", row) for row in rows)
        + ((f"CREATE TABLE {collision} ({columns})", ()),)
        + tuple((f"INSERT INTO {collision} VALUES ({parameters})", row) for row in rows)
        + aggregate_setup(target)
    )


# Five modest fixed aggregation inputs. Every row below is the oracle for the
# aggregate cases; nothing here is read back out of an observation.
AGGREGATE_TABLE_ROWS = {
    "phase66 agg é": (
        (1, 10, True, "a", Decimal("1.00"), 1.5, 10),
        (1, None, True, "a", Decimal("1.00"), 1.5, 11),
        (2, 20, False, "A", Decimal("2.00"), 1.5, 12),
        (None, None, None, "a ", Decimal("1.00"), 1.5, 13),
        (3, 30, None, "😀", Decimal("-0.01"), 1.5, 14),
    ),
    "phase66 agg empty é": (),
    "phase66 agg trio é": (
        (1, 1, True, "a", Decimal("1.00"), 1.5, 20),
        (1, None, True, "a", Decimal("1.00"), 1.5, 21),
        (1, 1, True, "a", Decimal("1.00"), 1.5, 22),
    ),
    "phase66 agg nulls é": (
        (None, None, None, "n", Decimal("0.00"), 0.0, 30),
        (None, None, None, "n", Decimal("0.00"), 0.0, 31),
    ),
    "phase66 agg keys é": (
        (0, None, None, "k", Decimal("0.00"), 0.0, 10),
        (1, None, None, "k", Decimal("0.00"), 0.0, 11),
        (1, None, None, "k", Decimal("0.00"), 0.0, 98),
        (None, None, None, "k", Decimal("0.00"), 0.0, 99),
    ),
    # Slice10 R18: the exact published DISTINCT witness [1, 1, NULL, NULL].
    "phase66 agg dupes é": (
        (1, 1, None, "d", Decimal("0.00"), 0.0, 40),
        (1, 1, None, "d", Decimal("0.00"), 0.0, 41),
        (None, None, None, "d", Decimal("0.00"), 0.0, 42),
        (None, None, None, "d", Decimal("0.00"), 0.0, 43),
    ),
    # Slice11 R22/C17: SA.key = [1, 1, NULL] against SB.key = [1, NULL, NULL];
    # SA.value = [1, 2, NULL] is the membership right A, (value, label) pairs
    # differ only as full tuples, SC carries the common-class multiplicity
    # partner [1, 1, 1, NULL, NULL, NULL] and SL the membership left [1, 1, 2, NULL].
    "phase66 set left é": (
        (1, 1, True, "a", Decimal("1.25"), 1.5, 60),
        (1, 2, True, "b", Decimal("2.50"), -0.0, 61),
        (None, None, None, "c", Decimal("1.25"), 0.0, 62),
    ),
    "phase66 set right é": (
        (1, 1, False, "b", Decimal("1.25"), 1.5, 70),
        (None, 2, False, "a", Decimal("2.50"), 0.0, 71),
        (None, None, None, "c", Decimal("9.99"), 0.0, 72),
    ),
    "phase66 set sextet é": tuple(
        (key, key, None, "s", Decimal("0.00"), 0.0, 80 + i)
        for i, key in enumerate((1, 1, 1, None, None, None))
    ),
    "phase66 set outer é": tuple(
        (key, key, None, "l", Decimal("0.00"), 0.0, 90 + i)
        for i, key in enumerate((1, 1, 2, None))
    ),
}


def aggregate_setup_parameters(target):
    """Independent expected insertion order for the five aggregation relations."""
    result: list[list[Any]] = []
    for rows in AGGREGATE_TABLE_ROWS.values():
        result.append([])
        for row in rows:
            result.append(
                [
                    _maybe(row[0]),
                    _maybe(row[1]),
                    _bool(target, row[2]),
                    _text(str(row[3])),
                    _decimal(str(row[4])),
                    {"kind": "float", "value": float(row[5]).hex()},
                    _integer(str(row[6])),
                ]
            )
    return result


def aggregate_setup(target):
    """One shared column shape over the five fixed aggregation relations."""
    if target == "postgres":
        columns = (
            '"group key" BIGINT, "value é" BIGINT, "flag value" BOOLEAN, '
            '"text `""é" TEXT COLLATE "C" NOT NULL, '
            '"amount value" NUMERIC(9,2) NOT NULL, '
            '"ratio value" DOUBLE PRECISION NOT NULL, "row id" BIGINT NOT NULL'
        )
        quote, markers = '"', ", ".join(f"${i + 1}" for i in range(7))
    else:
        columns = (
            "`group key` BIGINT, `value é` BIGINT, `flag value` TINYINT, "
            '`text ``"é` VARCHAR(64) CHARACTER SET utf8mb4 '
            "COLLATE utf8mb4_0900_bin NOT NULL, "
            "`amount value` DECIMAL(9,2) NOT NULL, "
            "`ratio value` DOUBLE NOT NULL, `row id` BIGINT NOT NULL"
        )
        quote, markers = "`", ", ".join(["?"] * 7)
    statements: list[tuple[str, tuple[object, ...]]] = []
    for name, rows in AGGREGATE_TABLE_ROWS.items():
        relation = quote + name + quote
        statements.append((f"CREATE TABLE {relation} ({columns})", ()))
        for row in rows:
            flag = row[2]
            if target == "mysql" and flag is not None:
                flag = 1 if flag else 0
            statements.append(
                (
                    f"INSERT INTO {relation} VALUES ({markers})",
                    (row[0], row[1], flag, row[3], row[4], row[5], row[6]),
                )
            )
    return tuple(statements)


def emission_rows(target, *, empty=False):
    if empty:
        return []
    true = (
        {"kind": "bool", "value": True}
        if target == "postgres"
        else {"kind": "int", "value": "1"}
    )
    false = (
        {"kind": "bool", "value": False}
        if target == "postgres"
        else {"kind": "int", "value": "0"}
    )
    duplicate = [
        {"kind": "text", "value": "trail 😀  "},
        {"kind": "int", "value": "9007199254740993"},
        true,
        {"kind": "decimal", "value": "12.30"},
        {"kind": "float", "value": "-0x0.0p+0"},
    ]
    return [
        duplicate,
        duplicate,
        [
            {"kind": "text", "value": "A"},
            {"kind": "int", "value": "0"},
            false,
            {"kind": "decimal", "value": "0.00"},
            {"kind": "float", "value": "0x1.8000000000000p+0"},
        ],
        [
            {"kind": "text", "value": "a "},
            {"kind": "int", "value": "1"},
            {"kind": "null"},
            {"kind": "decimal", "value": "-0.01"},
            {"kind": "float", "value": "0x0.0p+0"},
        ],
    ]


def emission_setup_parameters(target):
    # Independent expected insertion order; never use the observer as an oracle.
    rows = [[row[1], row[2], row[0], row[3], row[4]] for row in emission_rows(target)]
    return [[], [], *rows, [], *rows]


def chain_rows(target, *, empty=False):
    return [[*row, dict(row[1])] for row in emission_rows(target, empty=empty)]


# Slice6 implements the retained producer filter of these two inputs. Their source
# purpose is unchanged; the surviving rows are stated here independently, as the
# authored table rows whose `id` is strictly positive, never read back from SQL.
FILTERED_VARIANTS = {
    ("L_emission_blocked", "where_later"),
    ("O_named_later", "producer_filter"),
}


def positive_id_rows(rows):
    return [row for row in rows if int(row[1]["value"]) > 0]


def row_result_rows(target, *, empty=False):
    """Independent three-valued oracle for one Slice6 stage pipeline.

    Columns are record_id, next_id, twice, positive, both, missing, same_text over
    the authored rows that survive `where id > 0`. `both` is `(id > 0) and flag`,
    so the row whose flag is NULL keeps an unknown result rather than false, and
    `missing` is a non-null `flag is null`. Stated here, never read back from SQL.
    """
    if empty:
        return []
    true = (
        {"kind": "bool", "value": True}
        if target == "postgres"
        else {"kind": "int", "value": "1"}
    )
    false = (
        {"kind": "bool", "value": False}
        if target == "postgres"
        else {"kind": "int", "value": "0"}
    )
    duplicate = [
        {"kind": "int", "value": "9007199254740993"},
        {"kind": "int", "value": "9007199254740994"},
        {"kind": "int", "value": "18014398509481988"},
        true,
        true,
        false,
        true,
    ]
    return [
        duplicate,
        duplicate,
        [
            {"kind": "int", "value": "1"},
            {"kind": "int", "value": "2"},
            {"kind": "int", "value": "4"},
            true,
            {"kind": "null"},
            true,
            true,
        ],
    ]


AND_TABLE = {
    ("true", "true"): "true",
    ("true", "false"): "false",
    ("true", "null"): "null",
    ("false", "true"): "false",
    ("false", "false"): "false",
    ("false", "null"): "false",
    ("null", "true"): "null",
    ("null", "false"): "false",
    ("null", "null"): "null",
}
OR_TABLE = {
    ("true", "true"): "true",
    ("true", "false"): "true",
    ("true", "null"): "true",
    ("false", "true"): "true",
    ("false", "false"): "false",
    ("false", "null"): "null",
    ("null", "true"): "true",
    ("null", "false"): "null",
    ("null", "null"): "null",
}
# Each output is one (left, right) operand pair; `self` reuses the row's own flag.
TRUTH_PAIRS = (
    (AND_TABLE, "self", "true"),
    (AND_TABLE, "self", "false"),
    (AND_TABLE, "self", "self"),
    (AND_TABLE, "true", "self"),
    (AND_TABLE, "false", "self"),
    (OR_TABLE, "self", "true"),
    (OR_TABLE, "self", "false"),
    (OR_TABLE, "self", "self"),
    (OR_TABLE, "true", "self"),
    (OR_TABLE, "false", "self"),
)


def truth_rows(target):
    """Explicit finite three-valued oracle; never Python `and`/`or` or truthiness."""

    def value(name):
        if name == "null":
            return {"kind": "null"}
        if target == "postgres":
            return {"kind": "bool", "value": name == "true"}
        return {"kind": "int", "value": "1" if name == "true" else "0"}

    rows = []
    for flag in ("true", "true", "false", "null"):
        rows.append(
            [
                value(
                    table[
                        (
                            flag if left == "self" else left,
                            flag if right == "self" else right,
                        )
                    ]
                )
                for table, left, right in TRUTH_PAIRS
            ]
        )
    return rows


def row_result_metadata(target):
    """Physical result metadata observed from the fixed targets, not desired tags."""
    return (
        [20, 20, 20, 16, 16, 16, 16] if target == "postgres" else [8, 8, 8, 8, 8, 8, 8]
    )


def fixed_rows(target, *, named=False, empty=False):
    """Independent typed oracles, never produced from compiler/public values."""
    if empty:
        return []
    if named:
        row = [
            {"kind": "int", "value": "11"},
            {"kind": "null"},
            {"kind": "int", "value": "17"},
            {"kind": "int", "value": "17"},
            {"kind": "float", "value": "0x1.8000000000000p+0"},
            {"kind": "float", "value": "-0x0.0p+0"},
            {"kind": "text", "value": "雪?%s $1"},
        ]
    else:
        row = [
            {"kind": "int", "value": "11"},
            {"kind": "null"},
            {"kind": "bool", "value": True}
            if target == "postgres"
            else {"kind": "int", "value": "1"},
            {"kind": "bool", "value": False}
            if target == "postgres"
            else {"kind": "int", "value": "0"},
            {"kind": "int", "value": "1"},
            {"kind": "float", "value": "0x1.0000000000000p+0"},
            {"kind": "int", "value": "0"},
            {"kind": "int", "value": "2"},
            {"kind": "int", "value": "-2"},
            {"kind": "float", "value": "0x0.0p+0"},
            {"kind": "float", "value": "-0x0.0p+0"},
            {"kind": "float", "value": "-0x1.8000000000000p+0"},
            {"kind": "int", "value": "9007199254740993"},
            {"kind": "int", "value": "17"},
            {"kind": "int", "value": "17"},
            {"kind": "text", "value": ""},
            {"kind": "text", "value": "a  "},
            {"kind": "text", "value": "雪e\u0301😀"},
            {"kind": "text", "value": "? %s $1"},
            {"kind": "text", "value": "\"'\\\n"},
        ]
    return [row, row]


# Independent JOIN oracles. Every multiset below is stated from the authored table
# rows alone -- never read back from emitted SQL, a public document or a server.
# The published source holds, in this order, id = BIG, BIG, 0 and 1.
def _int(value):
    return {"kind": "int", "value": value}


NULL = {"kind": "null"}
BIG_TEXT = "9007199254740993"


def join_rows(variant):
    """The exact typed BAG each authored JOIN publishes, by hand."""
    if variant == "cross":
        # 4 x 4 ordered pairs; each left id appears once per right row.
        return (
            [[_int(BIG_TEXT)] for _ in range(8)] + [[_int("0")]] * 4 + [[_int("1")]] * 4
        )
    if variant == "inner":
        # id = BIG matches its two partners twice; 0 and 1 match once each.
        return [[_int(BIG_TEXT)] for _ in range(4)] + [[_int("0")], [_int("1")]]
    if variant == "semi":
        # Every left row has at least one partner; multiplicity is the left side's.
        return [[_int(BIG_TEXT)], [_int(BIG_TEXT)], [_int("0")], [_int("1")]]
    if variant == "anti":
        # Every left row has a partner, so the complement is empty.
        return []
    if variant == "left_marker":
        # `enriched` keeps id > 0, so the authored id = 0 row has no partner and
        # null-extends the retained source value, the literal, the computed value
        # and the LET result together.
        matched = [
            _int(BIG_TEXT),
            _int(BIG_TEXT),
            _int("1"),
            _int("18014398509481986"),
            _int("9007199254740994"),
        ]
        return (
            [matched] * 4
            + [[_int("0"), NULL, NULL, NULL, NULL]]
            + [[_int("1"), _int("1"), _int("1"), _int("2"), _int("2")]]
        )
    if variant == "right_accumulated":
        # `leftish` keeps id > 1, so the right rows 0 and 1 null-extend the
        # accumulated left side while BIG matches both retained left rows.
        return [[_int(BIG_TEXT), _int(BIG_TEXT)] for _ in range(4)] + [
            [NULL, _int("0")],
            [NULL, _int("1")],
        ]
    if variant == "via_refined":
        # The relationship equality on id, refined by an equal amount, keeps the
        # same matched pairs as the plain INNER self join.
        return [[_int(BIG_TEXT), _int(BIG_TEXT)] for _ in range(4)] + [
            [_int("0"), _int("0")],
            [_int("1"), _int("1")],
        ]
    if variant == "null_keys":
        # R09 minimum positive: left [1, 2, NULL] against right [2, NULL, 3]. 2
        # matches; 1 and 3 each null-extend the other side; the two NULL keys
        # never match each other, so they stay two distinct unmatched rows.
        return [
            [_int("2"), _int("2")],
            [_int("1"), NULL],
            [NULL, _int("3")],
            [NULL, NULL],
            [NULL, NULL],
        ]
    if variant == "restricted":
        # FULL over the same retained left side: the matched BIG pairs plus the
        # two right-only rows. This corpus has no left-only partner, so the
        # left-preserving half stays witnessed by `left_marker`.
        return [[_int(BIG_TEXT), _int(BIG_TEXT)] for _ in range(4)] + [
            [NULL, _int("0")],
            [NULL, _int("1")],
        ]
    raise ValueError("unknown JOIN variant")


def join_metadata(target, variant):
    """Physical result metadata: every published JOIN column here is a BIGINT."""
    width = len(emission.JOIN_LABELS[variant])
    return [20 if target == "postgres" else 8] * width


# The two inputs whose only remaining restriction was the JOIN family. Each one
# self joins its own source on a non-null identity, so every authored row matches
# its own duplicates. Stated independently from the authored rows.
MIGRATED_JOIN_ROWS = {
    ("O_named_later", "self_join"): [[_int(BIG_TEXT)] for _ in range(4)]
    + [[_int("0")], [_int("1")]],
    ("V_row_blocked", "match_join"): [[_int(BIG_TEXT)] for _ in range(4)]
    + [[_int("0")], [_int("1")]],
}
MIGRATED_JOIN_LABELS = {
    ("O_named_later", "self_join"): ("id",),
    ("V_row_blocked", "match_join"): ("record_id",),
}


def _bool(target, value):
    if value is None:
        return dict(NULL)
    if target == "postgres":
        return {"kind": "bool", "value": value}
    return {"kind": "int", "value": "1" if value else "0"}


def _decimal(value: str) -> dict[str, str]:
    return {"kind": "decimal", "value": value}


def _maybe(value):
    return dict(NULL) if value is None else _integer(str(value))


# Every aggregate oracle below is stated from the authored fixture rows and the
# published function rules, never from an observation. A count is a non-null
# occurrence count; an extreme value over an empty or all-null input is NULL.
AGGREGATE_EXPECTED = {
    ("X_aggregate_global", "bag"): ((3, 2, 1, 1, 1),),
    ("X_aggregate_global", "empty"): ((0, 0, 0, None, None),),
    ("X_aggregate_global", "all_null"): ((2, 0, 0, None, None),),
    # A pre-input filter that keeps no row still leaves the one GLOBAL row.
    ("X_aggregate_global", "where_false"): ((0, 0, 0, None, None),),
    # Hidden determinants: four distinct groups, two identical visible rows.
    ("X_aggregate_grouped", "hidden"): ((2, 1), (1, 1), (1, 0), (1, 1)),
    ("X_aggregate_grouped", "empty"): (),
    ("Y_aggregate_constant", "grouped"): ((1, 5),),
    ("Y_aggregate_constant", "empty"): (),
    ("Y_aggregate_satisfying", "retained"): ((2, 1, 20), (3, 1, 30)),
    ("Y_aggregate_satisfying", "bind"): ((2, 1, 20), (3, 1, 30)),
    ("Y_aggregate_satisfying", "before_input"): ((1, 1, 10), (2, 1, 20), (3, 1, 30)),
    ("Y_aggregate_satisfying", "let_reference"): ((1, 1), (2, 1), (3, 1)),
    ("Z_aggregate_composition", "named"): ((1, 2), (2, 1), (None, 1), (3, 1)),
    ("Z_aggregate_composition", "imported"): ((1, 2), (2, 1), (None, 1), (3, 1)),
    ("Z_aggregate_composition", "let_where"): ((1, 2, 1), (2, 1, 1), (3, 1, 1)),
    ("Z_aggregate_composition", "downstream_filter"): ((1, 2),),
    ("Z_aggregate_joined", "inner_fanout"): ((1, 4), (2, 1), (3, 1)),
    ("Z_aggregate_joined", "left_nullable"): (
        (10, 1, 1),
        (11, 1, 0),
        (98, 1, 0),
        (99, 1, 0),
    ),
    ("Z_aggregate_joined", "right_accumulated"): ((1, 2), (2, 1), (None, 1), (3, 1)),
    ("Z_aggregate_joined", "full_restricted"): ((1, 2), (2, 1), (3, 1), (None, 3)),
    ("Z_aggregate_membership", "semi_global"): ((0,),),
    ("Z_aggregate_membership", "anti_global"): ((1,), (1,), (None,)),
    ("Z_aggregate_membership", "semi_grouped"): (),
    ("Z_aggregate_membership", "anti_grouped"): ((0,), (1,), (1,), (None,)),
    ("Z_aggregate_membership", "filtered_global"): (),
    # The retained groups are {2, NULL, 3}; a base-source scan would instead
    # match the two left `1` occurrences, so this membership is not that.
    ("Z_aggregate_membership", "satisfying_right"): (),
    ("Z_aggregate_transport", "outer_null"): (
        (0, None),
        (1, 2),
        (1, 2),
        (None, None),
    ),
}
AGGREGATE_TYPE_CODES = {
    "postgres": {"Int": 20, "Bool": 16, "Text": 25, "Decimal": 1700},
    "mysql": {"Int": 8, "Bool": 1, "Text": 253, "Decimal": 246},
}


def aggregate_rows(target, case, variant):
    """The exact typed BAG one aggregate case must observe on this target."""
    if (case, variant) == ("X_aggregate_grouped", "visible"):
        return [
            [_bool(target, flag), _maybe(key), _maybe(key), _integer(str(total))]
            for flag, key, total in (
                (True, 1, 2),
                (False, 2, 1),
                (None, None, 1),
                (None, 3, 1),
            )
        ]
    if case == "Y_aggregate_domains":
        if variant == "bool_key":
            return [
                [_bool(target, flag), _integer(str(total))]
                for flag, total in ((True, 2), (False, 1), (None, 2))
            ]
        if variant == "text_key":
            return [
                [_text(label), _integer(str(total))]
                for label, total in (("a", 2), ("A", 1), ("a ", 1), ("😀", 1))
            ]
        return [
            [_decimal(amount), _integer(str(total))]
            for amount, total in (("1.00", 3), ("2.00", 1), ("-0.01", 1))
        ]
    if (case, variant) == ("Z_aggregate_composition", "source_keys"):
        return [
            [_integer(key), _text(label), _integer(str(total))]
            for key, label, total in (
                ("9007199254740993", "trail 😀  ", 2),
                ("0", "A", 1),
                ("1", "a ", 1),
            )
        ]
    return [
        [_maybe(value) for value in row] for row in AGGREGATE_EXPECTED[case, variant]
    ]


def aggregate_types(target, case, variant):
    codes = AGGREGATE_TYPE_CODES[target]
    logical = emission.aggregate_labels(emission.AGGREGATE_LOGICAL, case, variant)
    return [codes[tag] for tag in logical]


def parameter_records(document):
    records = []
    for use in document["parameter_uses"]:
        if use["server_index"] <= len(records):
            continue
        value = document["fixed_values"][use["slot"]]
        tag, payload = value["tag"], value["value"]
        if tag == "Bool" and document["target"]["family"] == "mysql":
            record = {"kind": "int", "value": "1" if payload else "0"}
        else:
            record = {
                "kind": {
                    "Bool": "bool",
                    "Int": "int",
                    "Float": "float",
                    "Text": "text",
                }[tag],
                "value": payload,
            }
        records.append(record)
    return records


def fixed_metadata(target, *, named):
    tags = emission.FIXED_NAMED_TAGS if named else emission.FIXED_TAGS
    # Every Text anchor result, empty or not and whichever literal policy
    # produced it, is VAR_STRING on the pinned MySQL 8.4.12; the CAST target
    # spelling is not the protocol result type.
    mapping = (
        {"Bool": 16, "Int": 20, "Float": 701, "Text": 25}
        if target == "postgres"
        else {"Bool": 8, "Int": 8, "Float": 5, "Text": 253}
    )
    return [mapping[tag] for tag in tags]


# Slice10 result-boundary oracles, stated by hand from the four published
# emission rows (id = BIG, BIG, 0, 1; flag = true, true, false, NULL; text =
# "trail 😀  " x2, "A", "a "), the dupes relation and the published rules. An
# ordered oracle is a list in the exact required order; an unordered one is a
# BAG. Nothing here is read back from an observation.
RESULT_MIGRATED = {
    ("O_named_later", "order_ordinary"),
    ("O_named_later", "order_rebound"),
    ("O_named_later", "order_completed"),
}


def _int_type(target):
    return 20 if target == "postgres" else 8


def metamorphic_expectation(target, variant):
    """(rows, labels, physical types) of one Slice15 premise, derived by hand.

    phase66_rows holds ids 1, 1: `rows.id > r.id` never holds, so every LEFT row
    null-extends `r` and the RIGHT match on that NULL keeps each `last` row alone.
    The native table holds (id 11, neighbor NULL) twice: both UNION forms keep
    only the two id rows.
    """
    if variant == "join_chain_accumulated":
        return [[NULL, _integer("1")]] * 2, ("a", "b"), [_int_type(target)] * 2
    return [[_integer("11")]] * 2, ("k",), [_int_type(target)]


def result_expectation(target, case, variant):
    """(rows, labels, physical types, logical tags, ordered) for one result case."""
    big, zero, one = _integer(BIG_TEXT), _integer("0"), _integer("1")
    i = _int_type(target)
    if (case, variant) == ("O_named_later", "order_ordinary"):
        return [[zero], [one], [big], [big]], ["Key"], [i], ["Int"], True
    if (case, variant) == ("O_named_later", "order_rebound"):
        # The upstream keeps row_number <= 3 and w <= 2: ids 0 and 1; LIMIT 1
        # after ORDER BY id keeps 0.
        return [[zero]], ["id"], [i], ["Int"], True
    if (case, variant) == ("O_named_later", "order_completed"):
        # 4 x 4 CROSS JOIN rows, ordered by the left id.
        return (
            [[zero]] * 4 + [[one]] * 4 + [[big]] * 8,
            ["id"],
            [i],
            ["Int"],
            True,
        )
    if case == "O_result_distinct":
        if variant == "visible_int":
            return [[big], [zero], [one]], ["record_id"], [i], ["Int"], False
        if variant == "null_duplicates":
            return [[one], [dict(NULL)]], ["v"], [i], ["Int"], False
        # Groups BIG -> 2, 0 -> 1, 1 -> 1; the hidden key never enters the tuple.
        return [[_integer("2")], [one]], ["total"], [i], ["Int"], False
    if case == "O_result_order":
        if variant == "ordinary_desc":
            return [[big], [big], [one], [zero]], ["record_id"], [i], ["Int"], True
        if variant == "nullable_key":
            # Each target's own native NULL posture for an ascending key:
            # PostgreSQL sorts NULL last, MySQL sorts NULL first.
            true, false = _bool(target, True), _bool(target, False)
            body = [[zero, false], [big, true], [big, true]]
            null_row = [one, dict(NULL)]
            rows = body + [null_row] if target == "postgres" else [null_row] + body
            bool_type = 16 if target == "postgres" else 1
            return rows, ["record_id", "active"], [i, bool_type], ["Int", "Bool"], True
        if variant == "constant_key":
            return [[big], [big], [one], [zero]], ["record_id"], [i], ["Int"], True
        # helper_hidden: binary collation orders "A" < "a " < "trail 😀  ".
        return [[zero], [one], [big], [big]], ["record_id"], [i], ["Int"], True
    if case == "O_result_limit":
        if variant == "positive":
            return [[zero], [one]], ["record_id"], [i], ["Int"], True
        if variant == "zero":
            return [], ["record_id"], [i], ["Int"], True
        if variant == "inner_then_filter":
            # LIMIT 1 after ORDER BY id keeps 0; the outer filter id > 0 drops it.
            return [], ["rid"], [i], ["Int"], True
        # filter_then_limit: id > 0 first, then ORDER BY id LIMIT 1 keeps 1.
        return [[one]], ["rid"], [i], ["Int"], True
    if case == "O_result_sharing":
        # One producer ORDER BY id LIMIT 2 = {0, 1}; the self join pairs them.
        return [[zero, zero], [one, one]], ["a", "b"], [i, i], ["Int", "Int"], False
    if case == "O_result_membership":
        kind, right = variant.split("_", 1)
        if right == "limit0":
            rows = [] if kind == "semi" else [[big], [big], [zero], [one]]
        else:
            rows = [[zero]] if kind == "semi" else [[big], [big], [one]]
        return rows, ["a"], [i], ["Int"], False
    assert case == "O_result_window"
    if variant == "qualify_distinct":
        return [[big], [zero], [one]], ["record_id"], [i], ["Int"], False
    if variant == "selected_order":
        # row_number over id: 0 -> 1, 1 -> 2, BIG -> 3 and 4; DESC LIMIT 2.
        return (
            [[big, _integer("4")], [big, _integer("3")]],
            ["record_id", "n"],
            [i, i],
            ["Int", "Int"],
            True,
        )
    # qualify_order_limit: rows 0, 1, BIG survive; DISTINCT; ORDER BY id DESC LIMIT 2.
    return [[big], [one]], ["record_id"], [i], ["Int"], True


# Slice11 SET oracles, stated by hand from the fixture rows and the published
# multiplicity laws (UNION ALL m+n, UNION DISTINCT 1, INTERSECT ALL min, INTERSECT
# DISTINCT 1 iff both, EXCEPT ALL max(m-n,0), EXCEPT DISTINCT 1 iff right absent).
# Nothing here is read back from an observation.
SET_MIGRATED = {("O_named_later", "union_dag"), ("O_named_later", "two_facades")}


def _set_chain_rows(target, copies):
    """The `first` producer's seven columns, `copies` times, as a BAG."""
    rows = []
    for row in emission_rows(target):
        text, ident, flag, money, ratio = row
        rows.append([text, ident, money, flag, money, ratio, text])
    return rows * copies


def set_expectation(target, case, variant):
    """(rows, labels, physical types, logical tags, ordered) for one SET case."""
    i = _int_type(target)
    big, zero, one, two = (
        _integer(BIG_TEXT),
        _integer("0"),
        _integer("1"),
        _integer("2"),
    )
    null = dict(NULL)
    text_type = 25 if target == "postgres" else 253
    if (case, variant) in SET_MIGRATED:
        chain_types = (
            [25, 20, 1700, 16, 1700, 701, 25]
            if target == "postgres"
            else [253, 8, 246, 1, 246, 5, 253]
        )
        labels = [
            "TextValue",
            "Key",
            "key",
            "FlagValue",
            "AmountValue",
            "RatioValue",
            "omitted",
        ]
        logical = ["Text", "Int", "Decimal", "Bool", "Decimal", "Float", "Text"]
        if variant == "two_facades":
            return _set_chain_rows(target, 2), labels, chain_types, logical, False
        # union_dag: three self UNION ALL levels over `first`, then Key alone.
        return (
            [[row[1]] for row in _set_chain_rows(target, 8)],
            ["Key"],
            [i],
            ["Int"],
            False,
        )
    if case == "S_set_forms":
        rows = {
            "union_all": [[one]] * 3 + [[null]] * 3,
            "union_distinct": [[one], [null]],
            "intersect_all": [[one], [null]],
            "intersect_distinct": [[one], [null]],
            "except_all": [[one]],
            "except_distinct": [],
        }[variant]
        return rows, ["k"], [i], ["Int"], False
    if case == "S_set_multiplicity":
        rows = {
            "intersect_all": [[one], [one], [null], [null]],
            "intersect_distinct": [[one], [null]],
            "empty_left": [],
            "empty_right": [[one], [one], [null]],
        }[variant]
        label = "v" if variant.startswith("intersect") else "k"
        return rows, [label], [i], ["Int"], False
    if case == "S_set_positions":
        a, b, c = _text("a"), _text("b"), _text("c")
        if variant == "two_column_intersect_distinct":
            rows = [[null, c]]
        elif variant == "two_column_except_all":
            rows = [[one, a], [two, b]]
        else:
            rows = [[one, a], [one, b], [null, c], [one, b], [null, a], [null, c]]
        labels = ["k", "t"] if variant == "renamed_labels_union_all" else ["v", "t"]
        return rows, labels, [i, text_type], ["Int", "Text"], False
    if case == "S_set_domains":
        if variant == "text_union_distinct":
            rows = [[_text("trail 😀  ")], [_text("A")], [_text("a ")]]
            return rows, ["t"], [text_type], ["Text"], False
        if variant == "decimal_intersect_all":
            rows = [[_decimal("12.30")], [_decimal("12.30")], [_decimal("-0.01")]]
            return (
                rows,
                ["m"],
                [1700 if target == "postgres" else 246],
                ["Decimal"],
                False,
            )
        if variant == "big_int_except_all":
            return [[zero], [one]], ["k"], [i], ["Int"], False
        if variant == "bool_union_distinct":
            rows = [[_bool(target, True)], [_bool(target, False)], [null]]
            return rows, ["f"], [16 if target == "postgres" else 1], ["Bool"], False
        rows = [[_float(-0.0)]] * 4 + [[_float(1.5)]] * 2 + [[_float(0.0)]] * 2
        return rows, ["r"], [701 if target == "postgres" else 5], ["Float"], False
    if case == "S_set_nesting":
        rows = {
            "left_fold_except": [],
            "right_nested_except": [[one]],
            "mixed_union_except": [[one]],
        }[variant]
        return rows, ["k"], [i], ["Int"], False
    if case == "S_set_boundaries":
        if variant == "ordered_operands":
            return [[zero], [zero], [one], [one]], ["k"], [i], ["Int"], False
        if variant == "limit_zero_operand":
            return [[big], [big], [zero], [one]], ["k"], [i], ["Int"], False
        if variant == "distinct_operand":
            return (
                [[big], [big], [zero], [zero], [one], [one]],
                ["k"],
                [i],
                ["Int"],
                False,
            )
        # outer_consumer: u = [BIG, BIG, 0, 1, BIG, BIG, 1]; k > 0; ORDER BY k LIMIT 1.
        return [[one]], ["k"], [i], ["Int"], True
    if case == "S_set_producers":
        if variant == "grouped_union":
            rows = [[big, two], [zero, one], [one, one]] * 2
            return rows, ["k", "total"], [i, i], ["Int", "Int"], False
        if variant == "global_empty_union":
            return [[zero], [zero]], ["c"], [i], ["Int"], False
        if variant == "satisfying_union":
            return (
                [[big, two], [big, two]],
                ["k", "total"],
                [i, i],
                ["Int", "Int"],
                False,
            )
        if variant == "window_union_distinct":
            return [[zero], [one]], ["k"], [i], ["Int"], False
        # set_to_window: row_number over k of [BIG, BIG, 0, 1, BIG, BIG, 1].
        rows = [[zero, one], [one, two], [one, _integer("3")]] + [
            [big, _integer(str(n))] for n in (4, 5, 6, 7)
        ]
        return rows, ["k", "n"], [i, i], ["Int", "Int"], False
    if case == "S_set_membership":
        rows = {
            "semi_except": [[two]],
            "anti_except": [[one], [one], [null]],
            "semi_intersect": [[one], [one]],
            "anti_intersect": [[two], [null]],
        }[variant]
        return rows, ["a"], [i], ["Int"], False
    assert case == "S_set_literals"
    rows = [[big, one]] * 4 + [[zero, one]] * 2 + [[one, one]] * 2
    return rows, ["k", "m"], [i, i], ["Int", "Int"], False


def check_set_case(observation, document, target, case_id, variant):
    rows, labels, physical, logical, ordered = set_expectation(target, case_id, variant)
    actual = observation["rows"]
    if ordered:
        if actual != rows:
            raise ValueError("SET ordered row mismatch")
    elif Counter(json.dumps(row, sort_keys=True) for row in actual) != Counter(
        json.dumps(row, sort_keys=True) for row in rows
    ):
        raise ValueError("SET typed BAG mismatch")
    metadata = observation["metadata"]
    if [m[0] for m in metadata] != labels or [m[1] for m in metadata] != physical:
        raise ValueError("SET positional physical metadata mismatch")
    if [c["label"] for c in document["columns"]] != labels or [
        c["logical_type"]["name"] for c in document["columns"]
    ] != logical:
        raise ValueError("SET positional logical metadata mismatch")


def check_result_case(observation, document, target, case_id, variant):
    rows, labels, physical, logical, ordered = result_expectation(
        target, case_id, variant
    )
    actual = observation["rows"]
    if ordered:
        if actual != rows:
            raise ValueError("result boundary ordered row mismatch")
    elif Counter(json.dumps(row, sort_keys=True) for row in actual) != Counter(
        json.dumps(row, sort_keys=True) for row in rows
    ):
        raise ValueError("result boundary typed BAG mismatch")
    metadata = observation["metadata"]
    if [m[0] for m in metadata] != labels or [m[1] for m in metadata] != physical:
        raise ValueError("result boundary positional physical metadata mismatch")
    if [c["label"] for c in document["columns"]] != labels or [
        c["logical_type"]["name"] for c in document["columns"]
    ] != logical:
        raise ValueError("result boundary positional logical metadata mismatch")


def check_emission_case(case, target):
    if set(case) != {"id", "observations", "variants"} or [
        v["variant"] for v in case["variants"]
    ] != list(emission.VARIANTS[case["id"]]):
        raise ValueError("emission case denominator mismatch")
    observed = iter(case["observations"])
    for variant in case["variants"]:
        if set(variant) != {
            "variant",
            "public",
            "public_sha256",
            "submission_before",
            "submission_after",
        }:
            raise ValueError("emission transfer fields")
        data = variant["public"].encode("utf-8")
        if hashlib.sha256(data).hexdigest() != variant["public_sha256"]:
            raise ValueError("public artifact transfer substitution")
        document = emission.decode_public(data)
        before, after = variant["submission_before"], variant["submission_after"]
        if type(before) is not int or type(after) is not int or before < 0:
            raise ValueError("submission observation missing")
        expected_status = emission.expected_status(
            case["id"], variant["variant"], target
        )
        if document["status"] != expected_status or after - before != (
            1 if expected_status == "VERIFIED" else 0
        ):
            raise ValueError("compiler failure submitted or wrong outcome")
        if expected_status != "VERIFIED":
            continue
        check_emission_variant(
            next(observed, None), document, target, case["id"], variant["variant"]
        )
    if next(observed, None) is not None:
        raise ValueError("extra submitted query observations")


def check_emission_variant(observation, document, target, case_id, variant_name):
    """The independent row/metadata oracle for one VERIFIED emission submission."""
    if (
        observation is None
        or observation["sql"].encode() != document["sql"].encode()
        or observation["parameters"] != parameter_records(document)
    ):
        raise ValueError("emitted artifact/submission mismatch")
    check_complete(observation)
    check_identity(observation, target, "query", prepared=True)
    if case_id in {"R_fixed_direct", "S_fixed_named"}:
        named = case_id == "S_fixed_named"
        expected_rows = fixed_rows(
            target, named=named, empty=variant_name.startswith("empty")
        )
        if Counter(
            json.dumps(row, sort_keys=True) for row in observation["rows"]
        ) != Counter(json.dumps(row, sort_keys=True) for row in expected_rows):
            raise ValueError("fixed-value typed BAG mismatch")
        labels = emission.FIXED_NAMED_LABELS if named else emission.FIXED_LABELS
        tags = emission.FIXED_NAMED_TAGS if named else emission.FIXED_TAGS
        types = fixed_metadata(target, named=named)
        if (
            [m[0] for m in observation["metadata"]] != list(labels)
            or [m[1] for m in observation["metadata"]] != types
            or [c["logical_type"]["name"] for c in document["columns"]] != list(tags)
        ):
            raise ValueError("fixed-value positional physical/logical metadata")
        if target == "mysql" and any(
            len(m) != 9 or m[8] != 309
            for m, tag in zip(observation["metadata"], tags, strict=True)
            if tag == "Text"
        ):
            raise ValueError("fixed text result encoding metadata")
        return
    if case_id == "P_native_identifiers":
        number = "7" if variant_name.startswith("plain") else "11"
        expected_rows = (
            []
            if variant_name.startswith("empty")
            else [[_integer(number)], [_integer(number)]]
        )
        if observation["rows"] != expected_rows:
            raise ValueError("native wrong-column regression")
        if [m[:2] for m in observation["metadata"]] != [
            ["id", 20 if target == "postgres" else 8]
        ]:
            raise ValueError("native identifier metadata")
        return
    if variant_name == "truth_table":
        expected_rows = truth_rows(target)
        # BAG multiplicity, not order: this query authors no ordering.
        if Counter(
            json.dumps(row, sort_keys=True) for row in observation["rows"]
        ) != Counter(json.dumps(row, sort_keys=True) for row in expected_rows):
            raise ValueError("three-valued AND/OR table mismatch")
        metadata = observation["metadata"]
        if [m[0] for m in metadata] != list(emission.TRUTH_LABELS) or [
            m[1] for m in metadata
        ] != [16 if target == "postgres" else 8] * len(emission.TRUTH_LABELS):
            raise ValueError("three-valued positional physical metadata mismatch")
        if [c["logical_type"]["name"] for c in document["columns"]] != ["Bool"] * len(
            emission.TRUTH_LABELS
        ):
            raise ValueError("three-valued positional logical metadata mismatch")
        return
    if case_id in {"W_join_shapes", "W_join_values", "V_join_full"}:
        expected_rows = join_rows(variant_name)
        if Counter(
            json.dumps(row, sort_keys=True) for row in observation["rows"]
        ) != Counter(json.dumps(row, sort_keys=True) for row in expected_rows):
            raise ValueError("JOIN typed BAG mismatch")
        labels = emission.JOIN_LABELS[variant_name]
        metadata = observation["metadata"]
        if [m[0] for m in metadata] != list(labels) or [
            m[1] for m in metadata
        ] != join_metadata(target, variant_name):
            raise ValueError("JOIN positional physical metadata mismatch")
        if [c["label"] for c in document["columns"]] != list(labels) or any(
            c["logical_type"]["name"] != "Int" for c in document["columns"]
        ):
            raise ValueError("JOIN positional logical metadata mismatch")
        return
    if (case_id, variant_name) in MIGRATED_JOIN_ROWS:
        expected_rows = MIGRATED_JOIN_ROWS[case_id, variant_name]
        if Counter(
            json.dumps(row, sort_keys=True) for row in observation["rows"]
        ) != Counter(json.dumps(row, sort_keys=True) for row in expected_rows):
            raise ValueError("migrated JOIN typed BAG mismatch")
        labels = MIGRATED_JOIN_LABELS[case_id, variant_name]
        metadata = observation["metadata"]
        if [m[0] for m in metadata] != list(labels) or [m[1] for m in metadata] != [
            20 if target == "postgres" else 8
        ] * len(labels):
            raise ValueError("migrated JOIN physical metadata mismatch")
        if [c["label"] for c in document["columns"]] != list(labels) or any(
            c["logical_type"]["name"] != "Int" for c in document["columns"]
        ):
            raise ValueError("migrated JOIN logical metadata mismatch")
        return
    if case_id in emission.AGGREGATE_CASES:
        expected_rows = aggregate_rows(target, case_id, variant_name)
        if Counter(
            json.dumps(row, sort_keys=True) for row in observation["rows"]
        ) != Counter(json.dumps(row, sort_keys=True) for row in expected_rows):
            raise ValueError("aggregate typed BAG mismatch")
        labels = emission.aggregate_labels(
            emission.AGGREGATE_LABELS, case_id, variant_name
        )
        logical = emission.aggregate_labels(
            emission.AGGREGATE_LOGICAL, case_id, variant_name
        )
        metadata = observation["metadata"]
        if [m[0] for m in metadata] != list(labels) or [
            m[1] for m in metadata
        ] != aggregate_types(target, case_id, variant_name):
            raise ValueError("aggregate positional physical metadata mismatch")
        if [c["label"] for c in document["columns"]] != list(labels) or [
            c["logical_type"]["name"] for c in document["columns"]
        ] != list(logical):
            raise ValueError("aggregate positional logical metadata mismatch")
        return
    if case_id == "G_scan_row_domains":
        expected_rows, labels, physical, ordered = row_domain_expectation(
            target, variant_name
        )
        rows_match = (
            observation["rows"] == expected_rows
            if ordered
            else _bag(observation["rows"]) == _bag(expected_rows)
        )
        if (
            not rows_match
            or [m[:2] for m in observation["metadata"]]
            != [list(pair) for pair in zip(labels, physical, strict=True)]
            or [(c["label"], c["logical_type"]["name"]) for c in document["columns"]]
            != [(label, "Int") for label in labels]
        ):
            raise ValueError("row-domain typed rows or metadata mismatch")
        return
    if case_id == "M_metamorphic_composition":
        expected_rows, labels, physical = metamorphic_expectation(target, variant_name)
        if (
            _bag(observation["rows"]) != _bag(expected_rows)
            or [m[:2] for m in observation["metadata"]]
            != [list(pair) for pair in zip(labels, physical, strict=True)]
            or [(c["label"], c["logical_type"]["name"]) for c in document["columns"]]
            != [(label, "Int") for label in labels]
        ):
            raise ValueError("metamorphic premise typed BAG or metadata mismatch")
        return
    if case_id in {"T_row_direct", "U_row_named"}:
        expected_rows = row_result_rows(target, empty=variant_name.startswith("empty"))
        if Counter(
            json.dumps(row, sort_keys=True) for row in observation["rows"]
        ) != Counter(json.dumps(row, sort_keys=True) for row in expected_rows):
            raise ValueError("row stage typed BAG mismatch")
        metadata = observation["metadata"]
        if [m[0] for m in metadata] != list(emission.ROW_LABELS) or [
            m[1] for m in metadata
        ] != row_result_metadata(target):
            raise ValueError("row stage positional physical metadata mismatch")
        if [c["logical_type"]["name"] for c in document["columns"]] != list(
            emission.ROW_LOGICAL
        ) or [c["label"] for c in document["columns"]] != list(emission.ROW_LABELS):
            raise ValueError("row stage positional logical metadata mismatch")
        return
    if case_id in emission.SET_CASES or ((case_id, variant_name) in SET_MIGRATED):
        check_set_case(observation, document, target, case_id, variant_name)
        return
    if case_id in emission.RESULT_CASES or ((case_id, variant_name) in RESULT_MIGRATED):
        check_result_case(observation, document, target, case_id, variant_name)
        return
    if case_id in emission.WINDOW_CASES:
        key = window_key(case_id, variant_name)
        expected = WINDOW_EXPECTATIONS[key]
        if Counter(
            json.dumps(row, sort_keys=True) for row in observation["rows"]
        ) != Counter(json.dumps(row, sort_keys=True) for row in expected):
            raise ValueError("window typed row multiset mismatch")
        metadata = observation["metadata"]
        labels = WINDOW_LABELS[key]
        logical = WINDOW_COLUMNS[key]
        physical = window_metadata(target, key)
        if [m[0] for m in metadata] != list(labels) or [
            m[1] for m in metadata
        ] != physical:
            raise ValueError("window positional physical metadata mismatch")
        if [c["logical_type"]["name"] for c in document["columns"]] != list(
            logical
        ) or [c["label"] for c in document["columns"]] != list(labels):
            raise ValueError("window positional logical metadata mismatch")
        return
    named = case_id in {"M_named_chain", "N_imported_chain", "O_named_later"}
    expected_rows = (chain_rows if named else emission_rows)(
        target, empty=variant_name == "empty"
    )
    if (case_id, variant_name) in FILTERED_VARIANTS:
        expected_rows = positive_id_rows(expected_rows)
    if Counter(
        json.dumps(row, sort_keys=True) for row in observation["rows"]
    ) != Counter(json.dumps(row, sort_keys=True) for row in expected_rows):
        raise ValueError("emission typed row multiset mismatch")
    metadata = observation["metadata"]
    types = [25, 20, 16, 1700, 701] if target == "postgres" else [253, 8, 1, 246, 5]
    labels = emission.CHAIN_LABELS if named else emission.LABELS
    logical = emission.CHAIN_LOGICAL if named else emission.LOGICAL
    if named:
        types.append(20 if target == "postgres" else 8)
    if [m[0] for m in metadata] != list(labels) or [m[1] for m in metadata] != types:
        raise ValueError("emission positional physical metadata mismatch")
    if [c["logical_type"]["name"] for c in document["columns"]] != list(logical) or [
        c["label"] for c in document["columns"]
    ] != list(labels):
        raise ValueError("emission positional logical metadata mismatch")
    if target == "postgres" and any(m[6] is not None for m in metadata):
        raise ValueError("unavailable nullability was invented")


def _bag(rows):
    return Counter(json.dumps(row, sort_keys=True) for row in rows)


def _support(bag):
    return Counter(set(bag))


def check_relations(receipt_cases):
    """Slice15 metamorphic laws over one full run's own VERIFIED submissions.

    Every law relates executions of distinct generated artifacts and reads no case
    oracle, so an oracle that agrees with a wrong result still has to satisfy it.
    Each premise is stated beside its law; it holds by the authored sources alone.
    """
    rows = {}
    for case in receipt_cases:
        observed = iter(case["observations"])
        if case["id"] == "A_legacy":
            rows["A_legacy", ""] = next(observed)["rows"]
        elif case["id"] in emission.VARIANTS:
            for variant in case["variants"]:
                if variant["submission_after"] != variant["submission_before"]:
                    rows[case["id"], variant["variant"]] = next(observed)["rows"]

    def bag(case, variant=""):
        return _bag(rows[case, variant])

    def columns(case, variant, *positions):
        return _bag([[row[i] for i in positions] for row in rows[case, variant]])

    # L: every rows.id; an ANTI join against an empty right input keeps them all.
    left = bag("O_result_membership", "anti_limit0")
    # A = sa.key (`b except all a` with an empty a); S_set_forms unions A with B.
    union_all = bag("S_set_forms", "union_all")
    a = bag("S_set_multiplicity", "empty_right")
    b = union_all - a
    forms = {v: bag("S_set_forms", v) for v in emission.VARIANTS["S_set_forms"]}
    nesting = {v: bag("S_set_nesting", v) for v in emission.VARIANTS["S_set_nesting"]}
    limits = {v: bag("O_result_limit", v) for v in emission.VARIANTS["O_result_limit"]}
    ranking = [
        [int(value["value"]) for value in row]
        for row in rows["A_window_ranking", "peers"]
    ]
    ids = [row[0] for row in ranking]
    laws = {
        # F1: binding an eligible literal as a parameter never changes the rows.
        **{
            f"F1 {case} {variant}": bag(case, variant)
            == bag(case, variant.replace("preserve", "bind"))
            for case in (
                "P_native_identifiers",
                "R_fixed_direct",
                "S_fixed_named",
                "S_set_literals",
            )
            for variant in emission.VARIANTS[case]
            if "preserve" in variant
        },
        # F2: renaming through a producer or moving it to another module is invisible;
        # naming a different column is not.
        "F2 named producer": bag("P_native_identifiers", "named_preserve")
        == bag("P_native_identifiers", "preserve"),
        "F2 imported module": bag("S_fixed_named", "named_preserve")
        == bag("S_fixed_named", "imported_preserve"),
        "F2 row producer": bag("U_row_named", "named_preserve")
        == bag("T_row_direct", "table_preserve")
        and bag("U_row_named", "imported_bind") == bag("T_row_direct", "query_bind")
        and bag("U_row_named", "empty_preserve")
        == bag("T_row_direct", "empty_preserve"),
        "F2 column identity": bag("P_native_identifiers", "plain_preserve")
        != bag("P_native_identifiers", "preserve"),
        # F3: the six SET forms follow from the two operand BAGs; X op X laws.
        "F3 operands": a <= union_all,
        "F3 intersect": forms["intersect_all"] == a & b
        and forms["intersect_distinct"] == _support(a & b),
        "F3 except": forms["except_all"] == a - b
        and forms["except_distinct"] == _support(a) - _support(b),
        "F3 union distinct": forms["union_distinct"] == _support(union_all),
        "F3 distinct quotient": bag("S_set_multiplicity", "intersect_distinct")
        == _support(bag("S_set_multiplicity", "intersect_all")),
        "F3 empty operand": bag("S_set_multiplicity", "empty_left") == Counter(),
        "F3 self union all": all(
            count % 2 == 0
            for case, variant in (
                ("S_set_domains", "float_union_all"),
                ("S_set_boundaries", "ordered_operands"),
                ("S_set_producers", "grouped_union"),
                ("S_set_producers", "satisfying_union"),
                ("S_set_literals", "preserve"),
            )
            for count in bag(case, variant).values()
        )
        and set(bag("S_set_boundaries", "distinct_operand").values()) == {2},
        "F3 self union distinct": all(
            set(bag("S_set_domains", v).values()) == {1}
            for v in ("text_union_distinct", "bool_union_distinct")
        ),
        "F3 distinct support": bag("O_result_distinct", "visible_int")
        == _support(left),
        # F4: a filter commutes with UNION ALL, NULL-dropping included.
        "F4 filter over union": bag("M_metamorphic_composition", "union_filter_outer")
        == bag("M_metamorphic_composition", "union_filter_operands"),
        # F5: SEMI and ANTI against one right input partition the left BAG.
        "F5 empty right": bag("O_result_membership", "semi_limit0") == Counter(),
        "F5 limited right": bag("O_result_membership", "semi_limit1")
        + bag("O_result_membership", "anti_limit1")
        == left,
        "F5 join partition": bag("W_join_shapes", "semi") + bag("W_join_shapes", "anti")
        == left
        and _support(bag("W_join_shapes", "semi"))
        == _support(bag("W_join_shapes", "inner")),
        "F5 cross": bag("W_join_shapes", "cross")
        == Counter({row: count * left.total() for row, count in left.items()}),
        "F5 set membership": bag("S_set_membership", "semi_except")
        + bag("S_set_membership", "anti_except")
        == bag("S_set_membership", "semi_intersect")
        + bag("S_set_membership", "anti_intersect"),
        # F6: LIMIT over the same order does not commute with a filter.
        "F6 limit": limits["zero"] == Counter()
        and limits["positive"] <= left
        and limits["positive"].total() <= 2,
        "F6 noncommutation": limits["inner_then_filter"] <= limits["filter_then_limit"]
        and limits["inner_then_filter"] != limits["filter_then_limit"],
        # F7: GLOBAL over no row is one row; GROUPED over no row is none.
        "F7 global": bag("X_aggregate_global", "where_false")
        == bag("X_aggregate_global", "empty")
        and bag("X_aggregate_global", "empty").total() == 1,
        "F7 grouped": bag("X_aggregate_grouped", "empty") == Counter()
        and bag("Y_aggregate_constant", "empty") == Counter(),
        "F7 global operand": bag("S_set_producers", "global_empty_union")
        == Counter({row: 2 for row in columns("X_aggregate_global", "empty", 0)}),
        # F8: a, b and c are one authored body, so A-A-A is empty while A-(A-A)
        # and (A+A)-A are A; SET columns are positional.
        "F8 nesting": nesting["left_fold_except"] == Counter()
        and nesting["right_nested_except"] == _support(nesting["mixed_union_except"])
        and nesting["right_nested_except"] != nesting["left_fold_except"],
        "F8 position": columns("S_set_positions", "renamed_labels_union_all", 0)
        == union_all,
        # F9: selected/hidden QUALIFY define the same right membership set.
        # SEMI and ANTI partition the left BAG; an independently executed ranking
        # selects its first two rows, so a coordinated base-scan shortcut fails.
        # Named windows still equal their inline twins and ranks follow peers.
        "F9 named window": bag("A_window_named", "shared")
        == columns("A_window_ranking", "peers", 0, 2, 3),
        "F9 qualify partition": bag("A_window_qualify", "selected")
        + bag("A_window_qualify", "hidden")
        == left
        and not (
            bag("A_window_qualify", "selected") & bag("A_window_qualify", "hidden")
        ),
        "F9 qualify selection": bag("A_window_qualify", "selected")
        == _bag(
            [
                [row[0]]
                for row in rows["A_window_ranking", "peers"]
                if int(row[1]["value"]) <= 2
            ]
        ),
        "F9 peers": sorted(row[1] for row in ranking) == list(range(1, len(ids) + 1))
        and all(
            row[2] == 1 + sum(i < row[0] for i in ids)
            and row[3] == 1 + len({i for i in ids if i < row[0]})
            for row in ranking
        ),
        # F10: outer JOINs keep their preserved side and null-extend jointly.
        "F10 left": all(
            len({row[i] == NULL for i in (1, 2, 3, 4)}) == 1
            for row in rows["W_join_values", "left_marker"]
        )
        and _support(columns("W_join_values", "left_marker", 0)) == _support(left),
        "F10 right": _support(columns("W_join_values", "right_accumulated", 1))
        == _support(left),
        "F10 chain": _support(
            columns("M_metamorphic_composition", "join_chain_accumulated", 1)
        )
        == _support(bag("A_legacy"))
        and bag("M_metamorphic_composition", "join_chain_accumulated").total()
        >= bag("A_legacy").total(),
    }
    broken = [name for name, holds in laws.items() if not holds]
    if broken:
        raise ValueError("metamorphic relation violated: " + ", ".join(broken))


def check_console_case(case, target, generation):
    """Slice13: installed-console documents consumed exactly like API documents.

    The console bytes are identified by SHA-256 against the API record of the
    same input, whose full bytes the receipt carries."""
    expected = emission.console_inputs(target)
    if (
        generation is None
        or set(case) != {"id", "observations", "witnesses"}
        or [(w["witness"], w["id"], w["variant"]) for w in case["witnesses"]]
        != [(i["witness"], i["id"], i["variant"]) for i in expected]
    ):
        raise ValueError("console case denominator mismatch")
    api = {(r["id"], r["variant"]): r for r in generation["emission"]["records"]}
    console = {r["witness"]: r for r in generation["console"]["records"]}
    observed = iter(case["observations"])
    for witness, item in zip(case["witnesses"], expected, strict=True):
        if set(witness) != {
            "witness",
            "id",
            "variant",
            "public_sha256",
            "submission_before",
            "submission_after",
        }:
            raise ValueError("console transfer fields")
        api_record = api[item["id"], item["variant"]]
        data = api_record["public"].encode("utf-8")
        if (
            witness["public_sha256"] != hashlib.sha256(data).hexdigest()
            or witness["public_sha256"] != console[item["witness"]]["public_sha256"]
        ):
            raise ValueError("console artifact transfer substitution")
        document = emission.decode_public(data)
        before, after = witness["submission_before"], witness["submission_after"]
        if type(before) is not int or type(after) is not int or before < 0:
            raise ValueError("console submission observation missing")
        expected_status = emission.expected_status(item["id"], item["variant"], target)
        if document["status"] != expected_status or after - before != (
            1 if expected_status == "VERIFIED" else 0
        ):
            raise ValueError("console compiler failure submitted or wrong outcome")
        if expected_status != "VERIFIED":
            continue
        check_emission_variant(
            next(observed, None), document, target, item["id"], item["variant"]
        )
    if next(observed, None) is not None:
        raise ValueError("extra submitted console observations")


def _integer(value: str) -> dict[str, str]:
    return {"kind": "int", "value": value}


def _text(value: str) -> dict[str, str]:
    return {"kind": "text", "value": value}


# Slice9 window oracles. The emission source holds four rows whose `order.id`
# values are 0, 1 and a duplicated 9007199254740993, so ordering by that
# non-null key gives one peer group and no target's NULL posture can move a
# result. Every value below is derived from those rows by hand.
WINDOW_BIG = "9007199254740993"


def _float(value: float) -> dict[str, str]:
    return {"kind": "float", "value": float.hex(value)}


WINDOW_EXPECTATIONS = {
    # row_number numbers the peers 3 and 4 while rank and dense_rank both give
    # them 3, which is exactly what separates the three identities.
    "A_window_ranking": [
        [_integer("0"), _integer("1"), _integer("1"), _integer("1")],
        [_integer("1"), _integer("2"), _integer("2"), _integer("2")],
        [_integer(WINDOW_BIG), _integer("3"), _integer("3"), _integer("3")],
        [_integer(WINDOW_BIG), _integer("4"), _integer("3"), _integer("3")],
    ],
    # Each partition is its own key, so every row is the only peer rank in its
    # partition: percent_rank is 0 and cume_dist is 1, both exact in binary64.
    # ntile(2) splits the four ordered rows into two buckets of two.
    "A_window_distribution": [
        [_integer("0"), _float(0.0), _float(1.0), _integer("1")],
        [_integer("1"), _float(0.0), _float(1.0), _integer("1")],
        [_integer(WINDOW_BIG), _float(0.0), _float(1.0), _integer("2")],
        [_integer(WINDOW_BIG), _float(0.0), _float(1.0), _integer("2")],
    ],
    # lag carries its explicit 0 default at the first row; lead has no default
    # and is NULL past the last row.
    "A_window_navigation": [
        [_integer("0"), _integer("0"), _integer("1")],
        [_integer("1"), _integer("0"), _integer(WINDOW_BIG)],
        [_integer(WINDOW_BIG), _integer("1"), _integer(WINDOW_BIG)],
        [_integer(WINDOW_BIG), _integer(WINDOW_BIG), {"kind": "null"}],
    ],
}
# ROWS BETWEEN 1 PRECEDING AND CURRENT ROW is a physical two-row frame, so the
# duplicated key does not merge the last two frames.
WINDOW_EXPECTATIONS["A_window_frame_rows"] = [
    [_integer("0"), _integer("0"), _integer("0")],
    [_integer("1"), _integer("0"), _integer("1")],
    [_integer(WINDOW_BIG), _integer("1"), _integer(WINDOW_BIG)],
    [_integer(WINDOW_BIG), _integer(WINDOW_BIG), _integer(WINDOW_BIG)],
]
# RANGE BETWEEN 1 PRECEDING AND CURRENT ROW is a value frame over the key, so
# both peers see only the peer group itself.
WINDOW_EXPECTATIONS["A_window_frame_range"] = [
    [_integer("0"), _integer("0"), _integer("1")],
    [_integer("1"), _integer("0"), _integer("1")],
    [_integer(WINDOW_BIG), _integer(WINDOW_BIG), _integer("1")],
    [_integer(WINDOW_BIG), _integer(WINDOW_BIG), _integer("1")],
]
# GROUPS counts peer groups and EXCLUDE CURRENT ROW removes only this row, so a
# peer of the same group stays in the frame and the first row's frame is empty.
WINDOW_EXPECTATIONS["A_window_groups"] = [
    [_integer("0"), {"kind": "null"}],
    [_integer("1"), _integer("0")],
    [_integer(WINDOW_BIG), _integer("1")],
    [_integer(WINDOW_BIG), _integer("1")],
]
# Two uses of one named declaration observe the same specification.
WINDOW_EXPECTATIONS["A_window_named"] = [
    [_integer("0"), _integer("1"), _integer("1")],
    [_integer("1"), _integer("2"), _integer("2")],
    [_integer(WINDOW_BIG), _integer("3"), _integer("3")],
    [_integer(WINDOW_BIG), _integer("3"), _integer("3")],
]
# G1/G4 over "phase66 agg é" by rid 10..14 (value 10,NULL,20,NULL,30): each use
# keeps its own complete window. `earliest` keeps its one-preceding-row frame (a
# collapse onto the plain use's default frame would read 10 on every row), and
# lag and first_value respect NULL values (ignoring them would give rid 12 ->
# 10/20 and rid 14 -> 20/30).
WINDOW_EXPECTATIONS["A_window_named_use_local"] = [
    [_integer("10"), {"kind": "null"}, _integer("10")],
    [_integer("11"), _integer("10"), _integer("10")],
    [_integer("12"), {"kind": "null"}, {"kind": "null"}],
    [_integer("13"), _integer("20"), _integer("20")],
    [_integer("14"), {"kind": "null"}, {"kind": "null"}],
]
# G8: right QUALIFY retains keys 0 and 1. SEMI keeps those left rows;
# ANTI keeps both BIG occurrences. A base-table shortcut yields all / none.
WINDOW_EXPECTATIONS["A_window_qualify_selected"] = [
    [_integer("0")],
    [_integer("1")],
]
WINDOW_EXPECTATIONS["A_window_qualify_hidden"] = [
    [_integer(WINDOW_BIG)],
    [_integer(WINDOW_BIG)],
]
# PostgreSQL int8 is OID 20 and float8 is OID 701; MySQL LONGLONG is 8 and
# DOUBLE is 5. A ranking or bucket result is the target's own signed64.
WINDOW_PHYSICAL = {
    "postgres": {"Int": 20, "Float": 701, "Bucket": 23},
    "mysql": {"Int": 8, "Float": 5, "Bucket": 8},
}
# A bucket result is not an ordinary Int on every target: PostgreSQL's ntile
# sends int4 where its ranking functions send int8.
WINDOW_WIDTHS = {"A_window_distribution": ("Int", "Float", "Float", "Bucket")}
WINDOW_COLUMNS = {
    "A_window_ranking": ("Int", "Int", "Int", "Int"),
    "A_window_distribution": ("Int", "Float", "Float", "Int"),
    "A_window_navigation": ("Int", "Int", "Int"),
    "A_window_frame_rows": ("Int", "Int", "Int"),
    "A_window_frame_range": ("Int", "Int", "Int"),
    "A_window_groups": ("Int", "Int"),
    "A_window_named": ("Int", "Int", "Int"),
    "A_window_named_use_local": ("Int", "Int", "Int"),
    "A_window_qualify_selected": ("Int",),
    "A_window_qualify_hidden": ("Int",),
}
WINDOW_LABELS = {
    "A_window_ranking": ("record_id", "numbered", "ranked", "densely"),
    "A_window_distribution": ("record_id", "fraction", "cumulative", "bucket"),
    "A_window_navigation": ("record_id", "previous", "upcoming"),
    "A_window_frame_rows": ("record_id", "earliest", "latest"),
    "A_window_frame_range": ("record_id", "earliest", "w"),
    "A_window_groups": ("record_id", "peers"),
    "A_window_named": ("record_id", "ranked", "densely"),
    "A_window_named_use_local": ("record_id", "previous", "earliest"),
    "A_window_qualify_selected": ("record_id",),
    "A_window_qualify_hidden": ("record_id",),
}


def window_metadata(target: str, key: str) -> list[int]:
    """The physical type each window output column actually arrives as."""

    widths = WINDOW_WIDTHS.get(key) or WINDOW_COLUMNS[key]
    return [WINDOW_PHYSICAL[target][name] for name in widths]


def window_key(case_id: str, variant: str) -> str:
    """The oracle key for one window case, splitting the two-variant families."""

    if case_id in {"A_window_frame", "A_window_qualify"}:
        return f"{case_id}_{variant}"
    if (case_id, variant) == ("A_window_named", "use_local"):
        return "A_window_named_use_local"
    return case_id


def expected_rows(case: str) -> list[list[dict[str, str]]]:
    # These literals are the oracle, not the observer's encoding of its results.
    if case == "A_legacy":
        return [[_integer("1")], [_integer("1")]]
    if case == "B_result":
        return [
            [_integer("7"), {"kind": "null"}],
            [_integer("7"), {"kind": "null"}],
            [_integer("9007199254740993"), _text(TEXT)],
        ]
    if case == "C_parameters":
        return [
            [_integer("9007199254740993"), _text(TEXT), _integer("9007199254740993")]
        ]
    raise ValueError("no row oracle for case")


def check_complete(observation: dict[str, Any]) -> None:
    keys = {
        "sql",
        "sql_sha256",
        "parameters",
        "identity",
        "prepared",
        "buffering",
        "status",
        "execute",
        "fetch",
        "close",
        "metadata",
        "rows",
        "diagnostics",
        "failures",
        "cursor_type",
        "api",
        "native",
    }
    if (
        set(observation) != keys
        or type(observation["sql"]) is not str
        or type(observation["parameters"]) is not list
        or type(observation["rows"]) is not list
    ):
        raise ValueError("malformed observation")
    if observation["native"] is not None:
        verify_native(observation)
    elif observation["api"] != observation["cursor_type"]:
        raise ValueError("cursor API identity")
    if (
        observation["sql"] != "CREDENTIAL_MANAGEMENT"
        and observation["sql_sha256"]
        != hashlib.sha256(observation["sql"].encode()).hexdigest()
    ):
        raise ValueError("SQL byte identity mismatch")
    if observation["fetch"] == "success":
        metadata = observation["metadata"]
        if (
            not isinstance(metadata, list)
            or not metadata
            or any(
                not isinstance(column, list) or len(column) < 7 for column in metadata
            )
            or any(len(row) != len(metadata) for row in observation["rows"])
        ):
            raise ValueError("incomplete positional metadata")
    elif observation["fetch"] == "not_applicable" and (
        observation["metadata"] is not None or observation["rows"] != []
    ):
        raise ValueError("unexpected unobserved result")
    if (
        observation.get("status") != "success"
        or observation.get("execute") != "success"
        or observation.get("fetch") not in {"success", "not_applicable"}
        or observation.get("close") != "success"
        or observation.get("failures") != []
        or observation.get("diagnostics", {}).get("complete") is not True
    ):
        raise ValueError("incomplete observation")
    diagnostic = observation["diagnostics"]
    if (
        set(diagnostic) != {"protocol", "total", "details", "complete"}
        or (
            diagnostic["protocol"] == "postgres_notices"
            and diagnostic["total"] is not None
        )
        or (
            diagnostic["protocol"] == "mysql_warnings"
            and (
                type(diagnostic["total"]) is not int
                or diagnostic["total"] != len(diagnostic["details"])
            )
        )
    ):
        raise ValueError("diagnostic completeness mismatch")


def check_identity(
    observation: dict[str, Any],
    target: str,
    identity: str,
    *,
    prepared: bool = False,
    transaction_control: bool = False,
) -> None:
    if transaction_control and (
        identity != "query"
        or observation["sql"] != "BEGIN"
        or observation["parameters"] != []
        or prepared
    ):
        raise ValueError("transaction purpose substitution")
    native = (
        target == "mysql"
        and not transaction_control
        and (identity == "query" or observation.get("api") == API)
    )
    if (
        observation.get("identity") != identity
        or observation.get("prepared")
        is not (prepared or target == "postgres" or native)
        or observation.get("buffering")
        != ("client_complete" if target == "postgres" else "unbuffered")
        or observation.get("diagnostics", {}).get("protocol")
        != ("postgres_notices" if target == "postgres" else "mysql_warnings")
    ):
        raise ValueError("observation identity or protocol substitution")
    if native:
        verify_native(observation)
    elif observation.get("native") is not None:
        raise ValueError("unexpected native route")
    elif observation.get("api") != (
        "psycopg.RawCursor"
        if target == "postgres"
        else "mysql.connector.cursor.MySQLCursorPrepared"
        if prepared
        else "mysql.connector.cursor.MySQLCursor"
    ):
        raise ValueError("cursor route identity")


def check_rows(observation: dict[str, Any], case: str, target: str) -> None:
    check_complete(observation)
    expected = expected_rows(case)
    actual = observation["rows"]
    if case == "A_legacy":
        actual_bag = Counter(json.dumps(row, sort_keys=True) for row in actual)
        expected_bag = Counter(json.dumps(row, sort_keys=True) for row in expected)
        if actual_bag != expected_bag:
            raise ValueError("BAG result mismatch")
    elif actual != expected:
        raise ValueError("ordered result or value type mismatch")
    names = {
        "A_legacy": ["id"],
        "B_result": ["id", "note"],
        "C_parameters": ["a", "txt", "again"],
    }[case]
    types = {
        "postgres": {
            "A_legacy": [20],
            "B_result": [20, 1043],
            "C_parameters": [20, 25, 20],
        },
        "mysql": {"A_legacy": [8], "B_result": [8, 253], "C_parameters": [8, 253, 8]},
    }[target][case]
    metadata = observation.get("metadata")
    if (
        not isinstance(metadata, list)
        or [m[0] for m in metadata] != names
        or [m[1] for m in metadata] != types
    ):
        raise ValueError("positional metadata mismatch")
    if any(len(m) < 7 for m in metadata):
        raise ValueError("incomplete protocol metadata")
    if target == "postgres" and any(m[6] is not None for m in metadata):
        raise ValueError("unavailable nullability metadata was invented")


def check_server_error(
    observation: dict[str, Any], target: str, *, privilege: bool = False
) -> None:
    expected = (
        ("42501" if privilege else "22012")
        if target == "postgres"
        else ("42000" if privilege else "42S22")
    )
    failures = observation.get("failures", [])
    native = target == "mysql" and observation.get("api") == API
    # The native layer is not uniform: MySQL resolves a missing column while it
    # prepares the statement, but checks the CREATE DATABASE privilege only when
    # the prepared statement executes.
    at_prepare = native and not privilege
    stage = "prepare" if at_prepare else "execute"
    if (
        observation.get("status") != "failed"
        or observation.get("execute") != ("not_started" if at_prepare else "failed")
        or observation.get("close") != "success"
        or len(failures) != 1
        or failures[0].get("stage") != stage
        or failures[0].get("sqlstate") != expected
        or (
            target == "mysql"
            and failures[0].get("vendor_code") != (1044 if privilege else 1054)
        )
        or observation.get("diagnostics", {}).get("complete") is not True
    ):
        raise ValueError("wrong failure layer or exact server error")
    if target == "mysql":
        diagnostic = observation["diagnostics"]
        if (
            diagnostic["total"] != 1
            or len(diagnostic["details"]) != 1
            or diagnostic["details"][0]["vendor_code"] != (1044 if privilege else 1054)
            or diagnostic["details"][0]["severity"] != "Error"
        ):
            raise ValueError("server error diagnostic loss")


def check_case(case: dict[str, Any], target: str, generation: Any = None) -> None:
    case_id = case.get("id")
    observations = case.get("observations", [])
    if case_id in emission.VARIANTS:
        check_emission_case(case, target)
    elif case_id == emission.CONSOLE_CASE:
        check_console_case(case, target, generation)
    elif case_id in SLICE2_CASE_IDS[:3]:
        if len(observations) != 1:
            raise ValueError("wrong observation denominator")
        statement, params = (
            (legacy_sql(target), ())
            if case_id == "A_legacy"
            else control(target, case_id)
        )
        observation = observations[0]
        check_identity(observation, target, "query", prepared=case_id == "C_parameters")
        if observation.get("sql") != statement:
            raise ValueError("submitted SQL substitution")
        expected_params = (
            []
            if not params
            else [_integer("9007199254740993"), _text(TEXT)]
            + ([_integer("9007199254740993")] if target == "mysql" else [])
        )
        if observation.get("parameters") != expected_params:
            raise ValueError("submitted parameter substitution")
        if case_id == "C_parameters" and observation.get("api") != (
            "psycopg.RawCursor" if target == "postgres" else API
        ):
            raise ValueError("wrong native parameter cursor")
        check_rows(observation, case_id, target)
    elif case_id == "Q_native_lifecycle":
        if (
            set(case)
            != {"id", "observations", "recovery", "session_before", "session_after"}
            or len(observations) != (5 if target == "postgres" else 8)
            or case.get("recovery") != "success"
            or type(case.get("session_before")) is not int
            or case["session_before"] <= 0
            or case["session_before"] != case.get("session_after")
        ):
            raise ValueError("native lifecycle denominator/session")
        sql = [
            "SELECT 1 AS v",
            "SELECT CAST($1 AS integer)"
            if target == "postgres"
            else "DO JSON_EXTRACT(?, '$')",
            "SELECT 2 AS v",
            "CREATE TABLE IF NOT EXISTS phase66_rows (id BIGINT NOT NULL)"
            if target == "postgres"
            else "INSERT IGNORE INTO phase66_diagnostic_rows VALUES ('abcdef')",
            "SELECT id FROM phase66_rows WHERE 1=0",
        ] + (
            ["SELECT ? AS v", "SELECT JSON_EXTRACT(?, '$')", "SELECT 3 AS v"]
            if target == "mysql"
            else []
        )
        if [o["sql"] for o in observations] != sql or [
            o["parameters"] for o in observations
        ] != [[], [_text("{")], [], [], []] + (
            [[], [_text("{")], []] if target == "mysql" else []
        ):
            raise ValueError("native lifecycle SQL/value substitution")
        for i in (0, 2, 4):
            check_complete(observations[i])
            check_identity(observations[i], target, "query")
        if (
            observations[0]["rows"] != [[_integer("1")]]
            or observations[2]["rows"] != [[_integer("2")]]
            or observations[4]["rows"] != []
            or observations[4]["metadata"][0][:2]
            != ["id", 20 if target == "postgres" else 8]
        ):
            raise ValueError("native recovery/empty result")
        failed = observations[1]
        check_identity(failed, target, "query", prepared=True)
        errors = failed["failures"]
        if (
            failed["status"] != "failed"
            or failed["execute"] != "failed"
            or failed["close"] != "success"
            or failed["diagnostics"]["complete"] is not True
            or len(errors) != 1
            or errors[0]["stage"] != "execute"
            or errors[0]["sqlstate"] != ("22P02" if target == "postgres" else "22032")
            or target == "mysql"
            and errors[0]["vendor_code"] != 3141
        ):
            raise ValueError("native allocated execution error")
        if target == "mysql" and (
            failed["diagnostics"]["total"] != 1
            or failed["diagnostics"]["details"][0]["vendor_code"] != 3141
        ):
            raise ValueError("native execution error diagnostics")
        warning = observations[3]
        check_complete(warning)
        check_identity(warning, target, "fixture_manager", prepared=target == "mysql")
        if (
            warning["fetch"] != "not_applicable"
            or len(warning["diagnostics"]["details"]) != 1
            or (
                warning["diagnostics"]["details"][0]["sqlstate"] != "42P07"
                if target == "postgres"
                else warning["diagnostics"]["details"][0]["vendor_code"] != 1265
            )
        ):
            raise ValueError("native warning/no-result loss")
        if target == "mysql":
            mismatch = observations[5]
            check_identity(mismatch, target, "query")
            if (
                mismatch["status"] != "failed"
                or mismatch["execute"] != "not_started"
                or len(mismatch["failures"]) != 1
                or mismatch["failures"][0]["stage"] != "parameter_count"
                or mismatch["failures"][0]["kind"] != "NATIVE_PARAMETER_COUNT"
            ):
                raise ValueError("empty-vector native arity guard")
            late = observations[6]
            check_identity(late, target, "query", prepared=True)
            if (
                late["status"] != "failed"
                or late["execute"] != "success"
                or late["fetch"] != "failed"
                or late["close"] != "success"
                or len(late["failures"]) != 1
                or late["failures"][0]["stage"] != "fetch"
                or late["failures"][0]["sqlstate"] != "22032"
                or late["failures"][0]["vendor_code"] != 3141
                or late["diagnostics"]["complete"] is not True
                or late["diagnostics"]["total"] != 1
                or late["diagnostics"]["details"][0]["vendor_code"] != 3141
            ):
                raise ValueError("native fetch error/diagnostic loss")
            check_complete(observations[7])
            check_identity(observations[7], target, "query")
            if observations[7]["rows"] != [[_integer("3")]]:
                raise ValueError("native recovery after fetch failure")
    elif case_id == "D_diagnostics":
        if len(observations) != (2 if target == "postgres" else 3):
            raise ValueError("wrong diagnostic control denominator")
        first, empty = observations[:2]
        check_identity(first, target, "fixture_manager")
        check_identity(empty, target, "query")
        statement = (
            "CREATE TABLE IF NOT EXISTS phase66_rows (id BIGINT NOT NULL)"
            if target == "postgres"
            else "INSERT IGNORE INTO phase66_diagnostic_rows VALUES ('abcdef')"
        )
        if (
            first.get("sql") != statement
            or empty.get("sql") != "SELECT 1 AS v"
            or any(observation.get("parameters") != [] for observation in observations)
        ):
            raise ValueError("diagnostic statement or parameter substitution")
        check_complete(first)
        check_complete(empty)
        if empty["rows"] != [[_integer("1")]]:
            raise ValueError("diagnostic success control lost its row")
        details = first["diagnostics"]["details"]
        if len(details) != 1 or empty["diagnostics"]["details"] != []:
            raise ValueError("lost or unexpected diagnostic")
        if target == "postgres":
            if (
                first["diagnostics"]["total"] is not None
                or details[0]["sqlstate"] != "42P07"
                or details[0]["severity"] != "NOTICE"
            ):
                raise ValueError("wrong PostgreSQL notice")
        else:
            settings = case.get("settings", [])
            if [item.get("sql") for item in settings] != [
                "SET SESSION max_error_count=0",
                "SET SESSION max_error_count=64",
            ]:
                raise ValueError("diagnostic control setting evidence missing")
            for item in settings:
                check_complete(item)
                check_identity(item, target, "fixture_manager")
                if item["parameters"] != []:
                    raise ValueError("diagnostic setting parameter substitution")
            if first["diagnostics"]["total"] != 1 or details[0]["vendor_code"] != 1265:
                raise ValueError("wrong MySQL fixture warning")
            truncated = observations[2]
            check_identity(truncated, target, "fixture_manager")
            if truncated.get("sql") != statement:
                raise ValueError("truncation statement substitution")
            if (
                truncated.get("status") != "failed"
                or truncated["diagnostics"]
                != {
                    "protocol": "mysql_warnings",
                    "total": 1,
                    "details": [],
                    "complete": False,
                }
                or truncated.get("close") != "success"
                or [f.get("kind") for f in truncated.get("failures", [])]
                != ["DIAGNOSTICS_INCOMPLETE"]
            ):
                raise ValueError("truncation cannot be complete success")
    elif case_id in {"E_recovery", "F_privilege_cleanup"}:
        if len(observations) != 3:
            raise ValueError("wrong success-failure-success denominator")
        for observation in observations:
            check_identity(observation, target, "query")
        error_sql = (
            (
                "CREATE TABLE public.phase66_denied (id BIGINT)"
                if target == "postgres"
                else "CREATE DATABASE phase66_denied"
            )
            if case_id == "F_privilege_cleanup"
            else (
                "SELECT 1/0"
                if target == "postgres"
                else "SELECT missing_column FROM phase66_rows"
            )
        )
        if [observation.get("sql") for observation in observations] != [
            "SELECT 1 AS v",
            error_sql,
            "SELECT 2 AS v",
        ] or any(observation.get("parameters") != [] for observation in observations):
            raise ValueError("recovery statement or parameter substitution")
        check_complete(observations[0])
        check_server_error(
            observations[1], target, privilege=case_id == "F_privilege_cleanup"
        )
        check_complete(observations[2])
        if observations[0]["rows"] != [[_integer("1")]] or observations[2]["rows"] != [
            [_integer("2")]
        ]:
            raise ValueError("recovery control result mismatch")
        if (
            case.get("recovery") != "success"
            or case.get("session_before") != case.get("session_after")
            or type(case.get("session_before")) is not int
            or case.get("session_before", 0) <= 0
        ):
            raise ValueError("reconnection or failed recovery")
        if case_id == "E_recovery":
            begin = case.get("begin", {})
            check_complete(begin)
            check_identity(begin, target, "query", transaction_control=True)
            if begin["sql"] != "BEGIN" or begin["parameters"] != []:
                raise ValueError("transaction start evidence missing")
            expected_states = (3, 0) if target == "postgres" else (True, False)
            actual_states = (
                case.get("state_after_failure"),
                case.get("state_after_recovery"),
            )
            if actual_states != expected_states or any(
                type(actual) is not type(expected)
                for actual, expected in zip(actual_states, expected_states, strict=True)
            ):
                raise ValueError("transaction recovery was not observed")
        if (
            case_id == "F_privilege_cleanup"
            and case.get("privileges_verified") is not True
        ):
            raise ValueError("query privilege evidence missing")
    else:
        raise ValueError("unknown case")
