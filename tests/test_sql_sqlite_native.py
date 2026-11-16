"""In-process qualification of SQLite SQL (Phase78 B1 and B2, D78.03, PL.47).

Each cell emits one program, as a single file with the SQLite backend or as
a project module with the SQLite project adapter, runs the SQL with the
standard-library `sqlite3` on a test-owned `:memory:` database of `STRICT`
tables, a project cell with its query parameters bound, and judges the raw
result against an oracle written before the run: a literal expected result,
the pure BAG/NULL equality oracle, or Python's own comparison operators with
NULL as unknown. Cells run only on the measured build, which its release,
source id and compile options identify together. On any other build the
SQLite class decides (`--pietto-sqlite-class` or `PIETTO_SQLITE_CLASS`):
`hosted-refusal` keeps the asserted refusal after each cell has emitted its
program, while `qualified` fails and `report` skips with a counted
`PIETTO_NOT_RUN sqlite-native` line in the module fixture, before a cell
emits anything. There only the coverage laws (SQLite) and the PostgreSQL
replay binding (PostgreSQL, the golden's statements too) emit programs, those
of every cell except the premise controls, and the self-tests still run.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import operator
import os
import re
import sqlite3
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import _pietto_ir_bag_null_oracle as oracle
import _pietto_sql_sqlite as project_files
from pietto._project import project_sql_emission_cli as emission_cli
from pietto._project import project_sqlite_emission as adapter
from pietto._project import project_sqlite_sql as adapter_sql
from pietto.errors import Severity
from pietto.ir import LiteralIR, RelationIR, ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import emit_postgres_sql, sqlite_relations
from pietto.sql.sqlite import QUALIFIED_SQLITE_BUILD, emit_sqlite_sql
from pietto.sql.sqlite import SQLiteBuild as _Build

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "tests/fixtures/sqlite/single_file.pietto"
SQL_GOLDEN = REPO_ROOT / "tests/fixtures/golden/emit_sqlite_single_file.sql"
# One PASS run of PostgreSQL 18.6 over the PostgreSQL bytes of every law cell
# and golden statement (D78.08); the file states its source and regeneration.
POSTGRES_REPLAY = REPO_ROOT / "tests/fixtures/sqlite/postgres_replay_v1.json"
SQLITE_CLASS_VARIABLE = "PIETTO_SQLITE_CLASS"
SQLITE_CLASSES = ("hosted-refusal", "qualified", "report")
INT_MIN = -9_223_372_036_854_775_808
INT_MAX = 9_223_372_036_854_775_807
_RecordProperty = Callable[[str, object], None]


def _observe(connection: sqlite3.Connection) -> _Build:
    release, source_id = connection.execute(
        "SELECT sqlite_version(), sqlite_source_id()"
    ).fetchone()
    options = connection.execute("PRAGMA compile_options").fetchall()
    return _Build(release, source_id, tuple(row[0] for row in options))


def _refusal(observed: _Build) -> str | None:
    """The first part of the identity that differs, or None when it is the
    measured build."""

    if observed.release != QUALIFIED_SQLITE_BUILD.release:
        return "SQLITE_BUILD_RELEASE"
    if observed.source_id != QUALIFIED_SQLITE_BUILD.source_id:
        return "SQLITE_BUILD_SOURCE"
    if observed.compile_options != QUALIFIED_SQLITE_BUILD.compile_options:
        return "SQLITE_BUILD_OPTIONS"
    return None


def _sqlite_class(environ: Mapping[str, str], option: str | None) -> str:
    """The declared class; with none, hosted CI keeps the refusal and any
    other run reports. A class never qualifies a build."""

    declared = environ.get(SQLITE_CLASS_VARIABLE)
    if option is not None and declared is not None and declared != option:
        raise ValueError("PIETTO_SQLITE_CLASS_CONFLICT")
    value = option if option is not None else declared
    if value is None:
        return "hosted-refusal" if environ.get("GITHUB_ACTIONS") == "true" else "report"
    if value not in SQLITE_CLASSES:
        raise ValueError("PIETTO_SQLITE_CLASS_UNKNOWN")
    return value


def _qualified(observed: _Build, declared: str) -> bool:
    refusal = _refusal(observed)
    if refusal is None:
        return True
    if declared == "hosted-refusal":
        return False
    if declared == "qualified":
        pytest.fail(f"PIETTO_SQLITE_REQUIRED {refusal}", pytrace=False)
    pytest.skip(f"PIETTO_NOT_RUN sqlite-native {refusal}")


@pytest.fixture(scope="module")
def native_build(request: pytest.FixtureRequest) -> bool:
    """True on the measured build; False is the asserted refusal."""

    declared = _sqlite_class(
        os.environ, request.config.getoption("--pietto-sqlite-class")
    )
    with closing(sqlite3.connect(":memory:")) as connection:
        observed = _observe(connection)
    return _qualified(observed, declared)


@dataclass(slots=True)
class _Native:
    """The native observations of one test, each kept as a user property."""

    qualified: bool
    record_property: _RecordProperty
    observed: int = 0

    def observe(self, name: str, payload: Sequence[object]) -> None:
        self.record_property(name, json.dumps(payload))
        self.observed += 1


@pytest.fixture
def native(
    native_build: bool,
    record_property: _RecordProperty,
    request: pytest.FixtureRequest,
) -> Iterator[_Native]:
    """The runtime witness of a native test: exactly one native observation
    on the measured build, whatever class is declared, and none on a refused
    build, where only `hosted-refusal` lets a native test start."""

    witness = _Native(native_build, record_property)
    yield witness
    expected = 1 if native_build else 0
    if witness.observed != expected:
        pytest.fail(
            f"PIETTO_SQLITE_UNOBSERVED {request.node.name}: "
            f"{witness.observed} native observations, expected {expected}",
            pytrace=False,
        )


# Fixture tables. Every column follows the premises of the SQLite rules:
# STRICT, BINARY collation, UTF-8, Bool as INTEGER 0/1, finite REAL. The
# premise controls below break one premise each on purpose.
_SCHEMA = (
    "CREATE TABLE `t` (`id` INTEGER NOT NULL, `n` INTEGER, `s` TEXT, "
    "`b` INTEGER, `x` REAL) STRICT"
)
_ROWS: tuple[tuple[object, ...], ...] = (
    (1, INT_MIN, "a", 1, -0.5),
    (2, INT_MAX, "A", 0, 1e300),
    (3, 0, "\u00e9", None, 0.0),
    (4, None, "e\u0301", 1, -0.0),
    (5, 7, None, 0, None),
    (6, 7, "\u4e2d", 1, 2.5),
    (7, 7, "\u4e2d", 1, 2.5),
    (8, None, "\U0001f600", None, None),
    (9, 1, "", 0, 1.0),
)
# What a STRICT REAL column gives back: it keeps no zero sign (row 4).
_READBACK: tuple[tuple[object, ...], ...] = (
    (1, INT_MIN, "a", 1, -0.5),
    (2, INT_MAX, "A", 0, 1e300),
    (3, 0, "\u00e9", None, 0.0),
    (4, None, "e\u0301", 1, 0.0),
    (5, 7, None, 0, None),
    (6, 7, "\u4e2d", 1, 2.5),
    (7, 7, "\u4e2d", 1, 2.5),
    (8, None, "\U0001f600", None, None),
    (9, 1, "", 0, 1.0),
)
_ACCOUNTS = (
    "CREATE TABLE `accounts` (`id` INTEGER NOT NULL, `name` TEXT NOT NULL, "
    "`active` INTEGER NOT NULL, `score` REAL, `region` TEXT) STRICT"
)
# Two Bool fields over every pair of FALSE, TRUE and NULL.
_PAIR_SCHEMA = (
    "CREATE TABLE `t` (`id` INTEGER NOT NULL, `b` INTEGER, `c` INTEGER) STRICT"
)
_PAIRS: tuple[tuple[object, ...], ...] = (
    (1, 0, 0),
    (2, 0, 1),
    (3, 0, None),
    (4, 1, 0),
    (5, 1, 1),
    (6, 1, None),
    (7, None, 0),
    (8, None, 1),
    (9, None, None),
)
# The `rows` table under a name with a backtick and with columns that are not
# the field names; a project contract maps `id`, `n`, `s`, `b` and `x` to them.
_ALIASED_TABLE = "t`x y"
_ALIASED_COLUMNS = ("i`d", "N space", '\u00e9"q', "select", "n")
_ALIASED_SCHEMA = (
    "CREATE TABLE `t``x y` (`i``d` INTEGER NOT NULL, `N space` INTEGER, "
    '`\u00e9"q` TEXT, `select` INTEGER, `n` REAL) STRICT'
)


def _n_rows(*pairs: tuple[int | None, int | None]) -> tuple[tuple[object, ...], ...]:
    """Rows of `t` that set only `id`, from 1, and each `(n, b)` pair."""

    return tuple((i, n, None, b, None) for i, (n, b) in enumerate(pairs, 1))


# The T2 fixtures (S10): `avg` over values that cancel, and one-sided `sum`
# values at and past the signed 64-bit bounds; the two `sum-mixed` tables
# break the non-negative `int_range` their contract declares on purpose.
_T2_FIXTURES: dict[str, tuple[str, str, tuple[tuple[object, ...], ...]]] = {
    "cancel": (
        "t",
        _SCHEMA,
        _n_rows((1, 0), (2**53, 0), (-(2**53), 0), (2**53, 1), (1, 1), (1, 1)),
    ),
    "sum-up": (
        "t",
        _SCHEMA,
        _n_rows(
            (INT_MAX - 7, 1), (3, 1), (4, 1), (None, 1), (0, 0), (5, 0), (None, None)
        ),
    ),
    "sum-down": (
        "t",
        _SCHEMA,
        _n_rows((INT_MIN + 7, 1), (-3, 1), (-4, 1), (None, 1), (0, 0)),
    ),
    "sum-over": ("t", _SCHEMA, _n_rows((INT_MAX, 1), (1, 1))),
    "sum-under": ("t", _SCHEMA, _n_rows((INT_MIN, 1), (-1, 1))),
    "sum-mixed": ("t", _SCHEMA, _n_rows((INT_MAX, 1), (1, 1), (-1, 1))),
    "sum-mixed-reversed": ("t", _SCHEMA, _n_rows((-1, 1), (1, 1), (INT_MAX, 1))),
}
# The `int_range` of `n` that a project contract declares for a fixture.
_N_RANGES = {
    "sum-up": (0, INT_MAX),
    "sum-over": (0, INT_MAX),
    "sum-mixed": (0, INT_MAX),
    "sum-mixed-reversed": (0, INT_MAX),
    "sum-down": (INT_MIN, 0),
    "sum-under": (INT_MIN, 0),
}
_FIXTURES: dict[str, tuple[str, str, tuple[tuple[object, ...], ...]]] = {
    **_T2_FIXTURES,
    "rows": ("t", _SCHEMA, _ROWS),
    "bool-pairs": ("t", _PAIR_SCHEMA, _PAIRS),
    "nocase": ("t", _SCHEMA.replace("`s` TEXT", "`s` TEXT COLLATE NOCASE"), _ROWS),
    "aliased": (_ALIASED_TABLE, _ALIASED_SCHEMA, _ROWS),
    "aliased-nocase": (
        _ALIASED_TABLE,
        _ALIASED_SCHEMA.replace("q` TEXT", "q` TEXT COLLATE NOCASE"),
        _ROWS,
    ),
    "bool-two": (
        "t",
        _SCHEMA,
        ((1, None, None, 2, None), (2, None, None, 1, None), (3, None, None, 0, None)),
    ),
    # Columns named `true` and `false`, in mixed case, that no field declares
    # and that hold the other Bool value.
    "bool-named-columns": (
        "t",
        _SCHEMA.replace("`x` REAL", "`x` REAL, `True` INTEGER, `fAlSe` INTEGER"),
        tuple((*row, 0, 1) for row in _ROWS),
    ),
    "real-edges": (
        "t",
        _SCHEMA,
        (
            (1, None, None, None, math.inf),
            (2, None, None, None, -math.inf),
            (3, None, None, None, math.nan),
        ),
    ),
    "accounts": (
        "accounts",
        _ACCOUNTS,
        (
            (1, "Ann", 1, 0.9, "east"),
            (2, "Mia", 0, None, "west"),
            (3, "O'Neil `\u00e9`", 1, 0.5, None),
            (4, "Zed", 1, 0.4, "east"),
            (5, "mo", 0, 2.0, "east"),
            (6, "Bo", 1, None, "west"),
        ),
    ),
}
_HEADER = """shape Row:
    id: Int
    n: Int | None
    s: Text | None
    b: Bool | None
    x: Float | None

source t: Row = sqlite.table("t")

"""
_ALIASED_HEADER = _HEADER.replace('sqlite.table("t")', 'sqlite.table("t`x y")')
_PAIR_HEADER = """shape Pair:
    id: Int
    b: Bool | None
    c: Bool | None

source t: Pair = sqlite.table("t")

"""
_TYPES = {"id": "Int", "n": "Int", "s": "Text", "b": "Bool", "x": "Float"}
_COLUMN_TYPES = {**_TYPES, "c": "Bool"}
_FIXTURE_COLUMNS = {"rows": tuple(_TYPES), "bool-pairs": ("id", "b", "c")}


@dataclass(frozen=True, slots=True)
class _Cell:
    name: str
    program: str
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    ordered: bool
    fixture: str = "rows"
    # The `where` condition of a cell that selects only `id`.
    condition: str | None = None
    # A project cell's query arguments in declaration order; None for a file.
    arguments: tuple[object, ...] | None = None


@dataclass(frozen=True, slots=True)
class _Record:
    """What one native run returned for the SQL bytes and parameters it ran."""

    sql: str
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    parameters: tuple[object, ...] = ()


def _q(*clauses: str, header: str = _HEADER, parameters: str = "") -> str:
    head = f"query q{parameters}:\n    from t\n"
    return header + head + "".join(f"    {c}\n" for c in clauses)


def _b(head: str, *items: str) -> str:
    return head + ":" + "".join(f"\n        {item}" for item in items)


def _ids(*values: object) -> tuple[tuple[object, ...], ...]:
    return tuple((value,) for value in values)


def _where(name: str, condition: str, *ids: object, fixture: str = "rows") -> _Cell:
    header = _PAIR_HEADER if fixture == "bool-pairs" else _HEADER
    program = _q(f"where {condition}", _b("select", "id"), header=header)
    return _Cell(name, program, ("id",), _ids(*ids), False, fixture, condition)


def _order(name: str, keys: tuple[str, ...], *ids: int) -> _Cell:
    return _Cell(
        name, _q(_b("select", "id"), _b("order by", *keys)), ("id",), _ids(*ids), True
    )


_LITERALS = (
    "id",
    "big = 9223372036854775807",
    "zero = 0",
    "half = 1.5",
    "nought = 0.0",
    'quote = "O\'Neil"',
    'wide = "\u00e9\u4e2d\U0001f600"',
    "truth = True",
    "falsity = False",
)
_MATRIX: tuple[_Cell, ...] = (
    _Cell(
        "select-every-type", _q(_b("select", *_TYPES)), tuple(_TYPES), _READBACK, False
    ),
    _Cell(
        "select-literals",
        _q("where id == 1", _b("select", *_LITERALS)),
        tuple(item.split(" = ")[0] for item in _LITERALS),
        ((1, INT_MAX, 0, 1.5, 0.0, "O'Neil", "\u00e9\u4e2d\U0001f600", 1, 0),),
        False,
    ),
    _Cell(
        "select-multiplicity",
        _q(_b("select", "n", "s")),
        ("n", "s"),
        (
            (INT_MIN, "a"),
            (INT_MAX, "A"),
            (0, "\u00e9"),
            (None, "e\u0301"),
            (7, None),
            (7, "\u4e2d"),
            (7, "\u4e2d"),
            (None, "\U0001f600"),
            (1, ""),
        ),
        False,
    ),
    _Cell(
        "select-bool-results",
        _q(
            _b("select", "id", "yes = b == True", "flip = not b", "missing = x is None")
        ),
        ("id", "yes", "flip", "missing"),
        (
            (1, 1, 0, 0),
            (2, 0, 1, 0),
            (3, None, None, 0),
            (4, 1, 0, 0),
            (5, 0, 1, 1),
            (6, 1, 0, 0),
            (7, 1, 0, 0),
            (8, None, None, 1),
            (9, 0, 1, 0),
        ),
        False,
    ),
    _Cell(
        "select-connectives",
        _q(
            _b(
                "select",
                "id",
                "both = b and (x is not None)",
                "either = b or (x is None)",
            )
        ),
        ("id", "both", "either"),
        (
            (1, 1, 1),
            (2, 0, 0),
            (3, None, None),
            (4, 1, 1),
            (5, 0, 1),
            (6, 1, 1),
            (7, 1, 1),
            (8, 0, 1),
            (9, 0, 0),
        ),
        False,
    ),
    _where("where-int-ne", "n != 7", 1, 2, 3, 9),
    _where("where-int-lt", "n < 0", 1),
    _where("where-int-le", "n <= 0", 1, 3),
    _where("where-int-gt", "n > 7", 2),
    _where("where-int-ge-max", "n >= 9223372036854775807", 2),
    _where("where-text-lt-case", 'n is not None and s < "a"', 2, 9),
    _where("where-text-gt-non-ascii", 's > "z"', 3, 6, 7, 8),
    _where("where-text-ge-combining", 's >= "e"', 3, 4, 6, 7, 8),
    _where("where-text-le-empty", 's <= ""', 9),
    _where("where-text-ne", 's != "a"', 2, 3, 4, 6, 7, 8, 9),
    _where("where-bool-bare", "b", 1, 4, 6, 7),
    _where("where-bool-not", "not b", 2, 5, 9),
    _where("where-bool-ne", "b != False", 1, 4, 6, 7),
    _where("where-bool-none", "b is None", 3, 8),
    _where("where-bool-not-none", "b is not None", 1, 2, 4, 5, 6, 7, 9),
    # Bool order: FALSE before TRUE, and NULL is unknown, so never kept.
    _where("where-bool-lt-true", "b < True", 2, 5, 9),
    _where("where-bool-lt-false", "b < False"),
    _where("where-bool-le-true", "b <= True", 1, 2, 4, 5, 6, 7, 9),
    _where("where-bool-le-false", "b <= False", 2, 5, 9),
    _where("where-bool-gt-false", "b > False", 1, 4, 6, 7),
    _where("where-bool-gt-true", "b > True"),
    _where("where-bool-ge-false", "b >= False", 1, 2, 4, 5, 6, 7, 9),
    _where("where-bool-ge-true", "b >= True", 1, 4, 6, 7),
    _where("where-bool-pair-lt", "b < c", 2, fixture="bool-pairs"),
    _where("where-bool-pair-le", "b <= c", 1, 2, 5, fixture="bool-pairs"),
    _where("where-bool-pair-gt", "b > c", 4, fixture="bool-pairs"),
    _where("where-bool-pair-ge", "b >= c", 1, 4, 5, fixture="bool-pairs"),
    _where("where-int-not-none", "n is not None", 1, 2, 3, 5, 6, 7, 9),
    _where("where-text-none", "s is None", 5),
    _where("where-text-not-none", "s is not None", 1, 2, 3, 4, 6, 7, 8, 9),
    _where("where-float-none", "x is None", 5, 8),
    _where("where-float-not-none", "x is not None", 1, 2, 3, 4, 6, 7, 9),
    _where("where-float-eq-zero", "x == 0.0", 3, 4),
    _where("where-float-lt", "x < 0.5", 1, 3, 4),
    _where("where-float-le-zero", "x <= 0.0", 1, 3, 4),
    _where("where-float-gt-zero", "x > 0.0", 2, 6, 7, 9),
    _where("where-float-ge", "x >= 2.5", 2, 6, 7),
    _where("where-float-ne", "x != 1.0", 1, 2, 3, 4, 6, 7),
    _where("where-three-valued", '(n > 0 or s == "a") and not (b == False)', 1, 6, 7),
    _where("where-or-none", "b or x is None", 1, 4, 5, 6, 7, 8),
    _where("where-not-or", 'not (s == "a" or n is None)', 2, 3, 6, 7, 9),
    _order("order-int-asc", ("n", "id"), 1, 3, 9, 5, 6, 7, 2, 4, 8),
    _order("order-int-desc", ("n desc", "id"), 4, 8, 2, 5, 6, 7, 9, 3, 1),
    _order("order-text-asc", ("s", "id"), 9, 2, 1, 4, 3, 6, 7, 8, 5),
    _order("order-text-desc", ("s desc", "id"), 5, 8, 6, 7, 3, 4, 1, 2, 9),
    _order("order-bool-asc", ("b", "id"), 2, 5, 9, 1, 4, 6, 7, 3, 8),
    _order("order-bool-desc", ("b desc", "id"), 3, 8, 1, 4, 6, 7, 2, 5, 9),
    _order("order-float-asc", ("x", "id"), 1, 3, 4, 9, 6, 7, 2, 5, 8),
    _order("order-float-desc", ("x desc", "id"), 5, 8, 2, 6, 7, 9, 3, 4, 1),
    _order("order-two-keys", ("b", "x desc", "id"), 5, 2, 9, 6, 7, 4, 1, 8, 3),
    _order("order-id-desc", ("id desc",), 9, 8, 7, 6, 5, 4, 3, 2, 1),
    _Cell(
        "order-field-not-output",
        _q(_b("select", "id", "N = s"), _b("order by", "n", "id")),
        ("id", "N"),
        (
            (1, "a"),
            (3, "\u00e9"),
            (9, ""),
            (5, None),
            (6, "\u4e2d"),
            (7, "\u4e2d"),
            (2, "A"),
            (4, "e\u0301"),
            (8, "\U0001f600"),
        ),
        True,
    ),
    _Cell(
        "limit-three",
        _q(_b("select", "id"), _b("order by", "id"), "limit 3"),
        ("id",),
        _ids(1, 2, 3),
        True,
    ),
    _Cell(
        "limit-zero",
        _q(_b("select", "id"), _b("order by", "id"), "limit 0"),
        ("id",),
        (),
        True,
    ),
    _Cell(
        "limit-keeps-duplicates",
        _q("where n == 7", _b("select", "n", "s"), _b("order by", "s"), "limit 2"),
        ("n", "s"),
        ((7, "\u4e2d"), (7, "\u4e2d")),
        True,
    ),
    _Cell(
        "limit-nulls-first",
        _q(_b("select", "id"), _b("order by", "x desc", "id"), "limit 1"),
        ("id",),
        _ids(5),
        True,
    ),
    _Cell(
        "limit-max",
        _q(_b("select", "id"), "limit 9223372036854775807"),
        ("id",),
        _ids(1, 2, 3, 4, 5, 6, 7, 8, 9),
        False,
    ),
    _Cell(
        "count-each-type",
        _q(
            _b(
                "select",
                "rows = count()",
                "ns = count(n)",
                "ss = count(s)",
                "bs = count(b)",
                "xs = count(x)",
            )
        ),
        ("rows", "ns", "ss", "bs", "xs"),
        ((9, 7, 8, 7, 7),),
        False,
    ),
    _Cell(
        "min-max-extremes",
        _q(_b("select", "lo = min(n)", "hi = max(n)", "flo = min(x)", "fhi = max(x)")),
        ("lo", "hi", "flo", "fhi"),
        ((INT_MIN, INT_MAX, -0.5, 1e300),),
        False,
    ),
    _Cell(
        "aggregate-no-rows",
        _q(
            "where id > 100",
            _b(
                "select",
                "rows = count()",
                "seen = count(n)",
                "lo = min(n)",
                "hi = max(x)",
            ),
        ),
        ("rows", "seen", "lo", "hi"),
        ((0, 0, None, None),),
        False,
    ),
    _Cell(
        "group-no-rows",
        _q("where id > 100", _b("group by", "s"), _b("select", "s", "rows = count()")),
        ("s", "rows"),
        (),
        False,
    ),
    _Cell(
        "aggregate-only-nulls",
        _q(
            "where x is None",
            _b(
                "select", "rows = count()", "lo = min(x)", "hi = max(x)", "top = max(n)"
            ),
        ),
        ("rows", "lo", "hi", "top"),
        ((2, None, None, 7),),
        False,
    ),
    _Cell(
        "group-text",
        _q(_b("group by", "s"), _b("select", "s", "rows = count()", "hi = max(n)")),
        ("s", "rows", "hi"),
        (
            ("a", 1, INT_MIN),
            ("A", 1, INT_MAX),
            ("\u00e9", 1, 0),
            ("e\u0301", 1, None),
            (None, 1, 7),
            ("\u4e2d", 2, 7),
            ("\U0001f600", 1, None),
            ("", 1, 1),
        ),
        False,
    ),
    _Cell(
        "group-bool",
        _q(_b("group by", "b"), _b("select", "b", "rows = count()", "lo = min(x)")),
        ("b", "rows", "lo"),
        ((0, 3, 1.0), (1, 4, -0.5), (None, 2, 0.0)),
        False,
    ),
    _Cell(
        "group-float-zero",
        _q(_b("group by", "x"), _b("select", "x", "rows = count()")),
        ("x", "rows"),
        ((-0.5, 1), (1e300, 1), (0.0, 2), (None, 2), (2.5, 2), (1.0, 1)),
        False,
    ),
    _Cell(
        "group-int-null-key",
        _q(_b("group by", "n"), _b("select", "n", "rows = count()", "xs = count(x)")),
        ("n", "rows", "xs"),
        (
            (INT_MIN, 1, 1),
            (INT_MAX, 1, 1),
            (0, 1, 1),
            (None, 2, 1),
            (7, 3, 2),
            (1, 1, 1),
        ),
        False,
    ),
    _Cell(
        "group-two-keys",
        _q(_b("group by", "b", "n"), _b("select", "b", "n", "rows = count()")),
        ("b", "n", "rows"),
        (
            (1, INT_MIN, 1),
            (0, INT_MAX, 1),
            (None, 0, 1),
            (1, None, 1),
            (0, 7, 1),
            (1, 7, 2),
            (None, None, 1),
            (0, 1, 1),
        ),
        False,
    ),
    _Cell(
        "group-order-by-count",
        _q(
            "where n is not None",
            _b("group by", "b"),
            _b("select", "b", 'tag = "k"', "rows = count()", "lo = min(n)"),
            _b("order by", "rows desc", "b"),
        ),
        ("b", "tag", "rows", "lo"),
        ((0, "k", 3, 1), (1, "k", 3, INT_MIN), (None, "k", 1, 0)),
        True,
    ),
    _Cell(
        "group-order-by-max",
        _q(
            _b("group by", "s"),
            _b("select", "s", "hi = max(x)"),
            _b("order by", "hi desc", "s"),
        ),
        ("s", "hi"),
        (
            ("\U0001f600", None),
            (None, None),
            ("A", 1e300),
            ("\u4e2d", 2.5),
            ("", 1.0),
            ("e\u0301", 0.0),
            ("\u00e9", 0.0),
            ("a", -0.5),
        ),
        True,
    ),
    _Cell(
        "group-order-by-key-desc",
        _q(
            _b("group by", "b"),
            _b("select", "b", "rows = count()"),
            _b("order by", "b desc"),
        ),
        ("b", "rows"),
        ((None, 2), (1, 4), (0, 3)),
        True,
    ),
    _Cell(
        "group-limit",
        _q(
            _b("group by", "n"),
            _b("select", "n", "rows = count()"),
            _b("order by", "rows desc", "n"),
            "limit 2",
        ),
        ("n", "rows"),
        ((7, 3), (None, 2)),
        True,
    ),
)
# Each premise control breaks one premise of the SQLite rules on purpose: the
# premise is the caller's, and this is what the SQL then means.
_PREMISES: tuple[_Cell, ...] = (
    _Cell(
        "premise-nocase-merges-case",
        _q('where s == "a"', _b("select", "id")),
        ("id",),
        _ids(1, 2),
        False,
        "nocase",
    ),
    _Cell(
        "premise-bool-two-bare",
        _q("where b", _b("select", "id")),
        ("id",),
        _ids(1, 2),
        False,
        "bool-two",
    ),
    _Cell(
        "premise-bool-two-eq-true",
        _q("where b == True", _b("select", "id")),
        ("id",),
        _ids(2),
        False,
        "bool-two",
    ),
    _Cell(
        "premise-real-infinity-kept-nan-null",
        _q(_b("select", "id", "x")),
        ("id", "x"),
        ((1, math.inf), (2, -math.inf), (3, None)),
        False,
        "real-edges",
    ),
)
# Equality cells whose expected bag the pure BAG/NULL oracle derives from the
# fixture rows: `==` keeps TRUE rows, `not (==)` keeps FALSE rows.
_EQUALITIES = (
    ("n", "7", 7),
    ("n", "0", 0),
    ("n", "9223372036854775807", INT_MAX),
    ("s", '"a"', "a"),
    ("s", '"A"', "A"),
    ("s", '"\u00e9"', "\u00e9"),
    ("s", '"e\u0301"', "e\u0301"),
    ("s", '""', ""),
    ("b", "True", True),
    ("b", "False", False),
)


def _scalar(field: str, value: object) -> oracle.ProjectBagNullScalar:
    if value is None:
        return oracle.project_bag_null()
    if field == "b":
        assert value in (0, 1, True, False)
        return oracle.project_bag_bool(bool(value))
    if type(value) is int:
        return oracle.project_bag_int(value)
    assert type(value) is str
    return oracle.project_bag_text(value)


def _oracle_cells() -> tuple[_Cell, ...]:
    position = tuple(_TYPES).index
    cells: list[_Cell] = []
    for field, spelling, value in _EQUALITIES:
        truths = [
            (
                row[0],
                oracle.evaluate_project_bag_null_equality(
                    _scalar(field, row[position(field)]), _scalar(field, value)
                ),
            )
            for row in _ROWS
        ]
        for prefix, condition, keep in (
            ("oracle-eq", f"{field} == {spelling}", oracle.ProjectBagNullTruth.TRUE),
            (
                "oracle-not-eq",
                f"not ({field} == {spelling})",
                oracle.ProjectBagNullTruth.FALSE,
            ),
        ):
            ids = (identifier for identifier, truth in truths if truth is keep)
            cells.append(_where(f"{prefix}-{field}-{len(cells) // 2}", condition, *ids))
    return tuple(cells)


# Python's own comparison of two values of one type is the order oracle: Int
# and Float by value (`-0.0 == 0.0`), Text by code point, which BINARY UTF-8
# order keeps, and Bool with FALSE before TRUE. NULL makes a comparison unknown.
_PYTHON_OPERATORS: dict[str, Callable[[Any, Any], object]] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}
_NULL_TESTS = ("is None", "is not None")
_OUTPUTS = {
    "==": "eq",
    "!=": "ne",
    "<": "lt",
    "<=": "le",
    ">": "gt",
    ">=": "ge",
    "is None": "missing",
    "is not None": "present",
}


def _python_value(field: str, raw: object) -> object:
    if raw is None or _COLUMN_TYPES[field] != "Bool":
        return raw
    assert raw in (0, 1)
    return bool(raw)


def _python_truth(left: object, spelling: str, right: object) -> bool | None:
    if spelling in _NULL_TESTS:
        return (left is None) is (spelling == "is None")
    if left is None or right is None:
        return None
    return bool(_PYTHON_OPERATORS[spelling](left, right))


def _sql_truth(truth: bool | None) -> int | None:
    return None if truth is None else int(truth)


def _python_cells() -> tuple[_Cell, ...]:
    """SELECT cells whose expected values Python's operators derive from the
    fixture rows: each emitted comparison and NULL test of each value type
    against one literal, and the two Bool fields against each other."""

    position = tuple(_TYPES).index
    cells: list[_Cell] = []
    for field, literal in (("n", "7"), ("s", '"a"'), ("b", "True"), ("x", "0.0")):
        spellings = (*sqlite_relations._COMPARISONS, *_NULL_TESTS)
        items = tuple(
            f"{_OUTPUTS[spelling]} = {field} {spelling}"
            + ("" if spelling in _NULL_TESTS else f" {literal}")
            for spelling in spellings
        )
        value = ast.literal_eval(literal)
        rows = tuple(
            (
                row[0],
                *(
                    _sql_truth(
                        _python_truth(
                            _python_value(field, row[position(field)]), spelling, value
                        )
                    )
                    for spelling in spellings
                ),
            )
            for row in _ROWS
        )
        columns = ("id", *(_OUTPUTS[spelling] for spelling in spellings))
        name = f"python-select-{_TYPES[field].lower()}"
        cells.append(_Cell(name, _q(_b("select", "id", *items)), columns, rows, False))
    spellings = tuple(sqlite_relations._COMPARISONS)
    rows = tuple(
        (
            identifier,
            *(
                _sql_truth(
                    _python_truth(
                        _python_value("b", b), spelling, _python_value("c", c)
                    )
                )
                for spelling in spellings
            ),
        )
        for identifier, b, c in _PAIRS
    )
    items = tuple(f"{_OUTPUTS[spelling]} = b {spelling} c" for spelling in spellings)
    cells.append(
        _Cell(
            "python-select-bool-pair",
            _q(_b("select", "id", *items), header=_PAIR_HEADER),
            ("id", *(_OUTPUTS[spelling] for spelling in spellings)),
            rows,
            False,
            "bool-pairs",
        )
    )
    return tuple(cells)


_LAW_CELLS = _MATRIX + _oracle_cells() + _python_cells()


def _values(fixture: str, field: str, b: object) -> list[object]:
    """`field` of each row of `fixture` in the `group by b` group `b`."""

    _table, _schema, rows = _FIXTURES[fixture]
    at, key = tuple(_TYPES).index(field), tuple(_TYPES).index("b")
    return [row[at] for row in rows if row[key] == b]


def _avg(values: Sequence[object]) -> float | None:
    """`avg` of an Int field: compensated summation divided by the count,
    which SQLite's `AVG(CAST(x AS REAL))` equalled in every S05 case. Plain
    left-to-right summation is no oracle: it differs in the last bits, or more
    when values cancel (the lead's `avg` ruling under PL.47)."""

    present = [float(value) for value in values if isinstance(value, int)]
    return math.fsum(present) / len(present) if present else None


# The T2 forms (PL.47, S10), each cell run as a single file and as a project
# module. They stay out of `_LAW_CELLS`, whose PostgreSQL replay
# `postgres_replay_v1.json` binds, until R1 replays them. Each comparisons
# cell writes HAVING's six comparisons of one type with `and` and `or`; an
# output named like a column (`n`, `x`) or `TRUE` would change the result if
# HAVING read an output alias or a Bool literal as a name.
_T2_CELLS: tuple[_Cell, ...] = (
    _Cell(
        "t2-count-distinct-every-type",
        _q(
            _b(
                "select",
                *(f"d{f} = count_distinct({f})" for f in ("id", "n", "s", "b")),
            )
        ),
        ("did", "dn", "ds", "db"),
        ((9, 5, 7, 2),),
        False,
    ),
    _Cell(
        "t2-count-distinct-grouped-ordered",
        _q(
            _b("group by", "b"),
            _b("select", "b", "ds = count_distinct(s)"),
            _b("order by", "ds desc", "b"),
        ),
        ("b", "ds"),
        ((1, 3), (0, 2), (None, 2)),
        True,
    ),
    _Cell(
        "t2-avg-int-grouped",
        _q(_b("group by", "b"), _b("select", "b", "a = avg(n)", "e = avg(id)")),
        ("b", "a", "e"),
        tuple(
            (b, _avg(_values("rows", "n", b)), _avg(_values("rows", "id", b)))
            for b in (1, 0, None)
        ),
        False,
    ),
    _Cell(
        "t2-avg-int-cancelling",
        _q(_b("group by", "b"), _b("select", "b", "a = avg(n)")),
        ("b", "a"),
        tuple((b, _avg(_values("cancel", "n", b))) for b in (0, 1)),
        False,
        "cancel",
    ),
    _Cell(
        "t2-empty-input",
        _q(
            "where id > 100",
            _b("select", "a = avg(n)", "d = count_distinct(s)", "c = count()"),
        ),
        ("a", "d", "c"),
        ((None, 0, 0),),
        False,
    ),
    _Cell(
        "t2-all-null-input",
        _q("where n is None", _b("select", "a = avg(n)", "d = count_distinct(n)")),
        ("a", "d"),
        ((None, 0),),
        False,
    ),
    _Cell(
        "t2-having-outputs-named-like-columns",
        _q(
            _b("group by", "s"),
            _b("select", "s", "n = count()", "x = max(id)"),
            "having n > 1 or x == 9",
        ),
        ("s", "n", "x"),
        (("\u4e2d", 2, 7), ("", 1, 9)),
        False,
    ),
    _Cell(
        "t2-having-int-comparisons",
        _q(
            _b("group by", "b"),
            _b("select", "b", "c = count()"),
            "having c == 4 or c != 3 and c < 4 or c <= 2 and c > 1 and c >= 2",
        ),
        ("b", "c"),
        ((1, 4), (None, 2)),
        False,
    ),
    _Cell(
        "t2-having-float-comparisons",
        _q(
            _b("group by", "b"),
            _b("select", "b", "hi = max(x)"),
            "having hi == 2.5 or hi != 2.5 and hi > 1.0 and hi < 100.0"
            " or hi <= 0.0 and hi >= 0.0",
        ),
        ("b", "hi"),
        ((1, 2.5), (None, 0.0)),
        False,
    ),
    _Cell(
        "t2-having-text-comparisons",
        _q(
            _b("group by", "s"),
            _b("select", "s", "c = count()"),
            'having s == "a" or s != "A" and s < "b"'
            ' or s <= "" and s > "x" and s >= ""',
        ),
        ("s", "c"),
        (("a", 1), ("", 1)),
        False,
    ),
    _Cell(
        "t2-having-bool-comparisons",
        _q(
            _b("group by", "b"),
            _b("select", "b", "c = count()"),
            "having b == True or b != True and b < True"
            " or b <= False and b > False and b >= False",
        ),
        ("b", "c"),
        ((1, 4), (0, 3)),
        False,
    ),
    _Cell(
        "t2-having-bool-literal-beside-an-output-named-true",
        _q(
            _b("group by", "b"), _b("select", "b", "TRUE = count()"), "having b == True"
        ),
        ("b", "TRUE"),
        ((1, 4),),
        False,
    ),
    _Cell(
        "t2-having-avg-and-count-distinct",
        _q(
            _b("group by", "b"),
            _b("select", "b", "a = avg(id)", "d = count_distinct(s)"),
            "having a > 5.4 or d == 3",
        ),
        ("b", "a", "d"),
        ((1, 4.5, 3), (None, 5.5, 2)),
        False,
    ),
    _Cell(
        "t2-having-where-order-limit",
        _q(
            "where x is not None",
            _b("group by", "b"),
            _b("select", "b", "c = count()"),
            "having c > 1",
            _b("order by", "c desc"),
            "limit 1",
        ),
        ("b", "c"),
        ((1, 4),),
        True,
    ),
)
# A Bool literal is written 1 or 0, so no output or column named `true` or
# `false`, in any letter case, stands in for it in `where` or `select`, as
# one stood in for B1's TRUE and FALSE. Each cell also runs as a project
# module; they stay out of `_LAW_CELLS`, whose PostgreSQL replay binds, and
# out of `_T2_CELLS`, which R1 replays.
_BOOL_NAME_CELLS: tuple[_Cell, ...] = (
    _Cell(
        "bool-literals-beside-outputs-named-true-and-false",
        _q(
            "where b == True or b == False",
            _b("select", "id", "TRUE = n", "FALSE = s", "yes = True", "no = False"),
        ),
        ("id", "TRUE", "FALSE", "yes", "no"),
        tuple((*row[:3], 1, 0) for row in _ROWS if row[3] is not None),
        False,
    ),
    _Cell(
        "bool-literals-beside-columns-named-true-and-false",
        _q(
            "where b == True or b == False and n == 7",
            _b("select", "id", "yes = True", "no = False"),
        ),
        ("id", "yes", "no"),
        tuple((i, 1, 0) for i in (1, 4, 5, 6, 7)),
        False,
        "bool-named-columns",
    ),
)
_CELLS = _LAW_CELLS + _PREMISES + _T2_CELLS + _BOOL_NAME_CELLS

# Query parameters of each type with their arguments; -0.0 keeps its sign.
_PARAMETERS = (("n", 7), ("s", "a"), ("b", True), ("x", -0.0))


def _carried(value: object) -> object:
    """A bound argument as SQLite returns it: a `Bool` as 0 or 1."""

    return int(value) if type(value) is bool else value


def _parameter_cells() -> tuple[_Cell, ...]:
    """Project cells that read query parameters, with expected values from
    Python's operators: a parameter of each type in `select` (its value, each
    comparison with its field and one with the parameter on the left) and in
    `where`; an optional one bound to NULL and to a value; numbers given by
    first read, not declaration; the signed 64-bit extremes; a decomposed
    accent; and one in the `where` of an aggregated relation, since `check`
    refuses a parameter as a grouped result (PIE-S2355)."""

    position = tuple(_TYPES).index
    spellings = tuple(adapter_sql.OPERATORS)
    cells: list[_Cell] = []
    for field, value in _PARAMETERS:
        kind = _TYPES[field]
        raws = [(row[0], _python_value(field, row[position(field)])) for row in _ROWS]
        items = (
            "got = v",
            *(f"{_OUTPUTS[spelling]} = {field} {spelling} v" for spelling in spellings),
            f"rev = v < {field}",
        )
        rows = tuple(
            (
                identifier,
                _carried(value),
                *(_sql_truth(_python_truth(raw, s, value)) for s in spellings),
                _sql_truth(_python_truth(value, "<", raw)),
            )
            for identifier, raw in raws
        )
        columns = ("id", "got", *(_OUTPUTS[spelling] for spelling in spellings), "rev")
        signature = f"(v: {kind})"
        program = _q(_b("select", "id", *items), parameters=signature)
        name = f"project-parameter-select-{kind.lower()}"
        cells.append(_Cell(name, program, columns, rows, False, arguments=(value,)))
        kept = (i for i, raw in raws if _python_truth(value, "<=", raw) is True)
        program = _q(f"where v <= {field}", _b("select", "id"), parameters=signature)
        name = f"project-parameter-where-{kind.lower()}"
        cells.append(
            _Cell(name, program, ("id",), _ids(*kept), False, arguments=(value,))
        )
    program = _q(
        _b("select", "id", "missing = w is None", "eq = s == w"),
        parameters="(w: Text | None)",
    )
    for name, value in (("null", None), ("bound", "a")):
        rows = tuple(
            (row[0], int(value is None), _sql_truth(_python_truth(row[2], "==", value)))
            for row in _ROWS
        )
        cells.append(
            _Cell(
                f"project-parameter-optional-{name}",
                program,
                ("id", "missing", "eq"),
                rows,
                False,
                arguments=(value,),
            )
        )
    return (
        *cells,
        _Cell(
            "project-parameter-numbered-by-first-read",
            _q(
                "where n >= lo and n <= hi",
                _b("select", "id", "top = hi"),
                parameters="(lo: Int, hi: Int)",
            ),
            ("id", "top"),
            tuple((identifier, 7) for identifier in (3, 5, 6, 7, 9)),
            False,
            arguments=(0, 7),
        ),
        _Cell(
            "project-parameter-int-extremes",
            _q(
                "where n == lo or n == hi",
                _b("select", "id", "low = lo", "high = hi"),
                parameters="(lo: Int, hi: Int)",
            ),
            ("id", "low", "high"),
            ((1, INT_MIN, INT_MAX), (2, INT_MIN, INT_MAX)),
            False,
            arguments=(INT_MIN, INT_MAX),
        ),
        _Cell(
            "project-parameter-text-decomposed",
            _q("where s == v", _b("select", "id"), parameters="(v: Text)"),
            ("id",),
            _ids(4),
            False,
            arguments=("e\u0301",),
        ),
        _Cell(
            "project-parameter-where-grouped",
            _q(
                "where s != v",
                _b("group by", "b"),
                _b("select", "b", "rows = count()"),
                parameters="(v: Text)",
            ),
            ("b", "rows"),
            ((0, 2), (1, 3), (None, 2)),
            False,
            arguments=("a",),
        ),
    )


# Aliased cells (PL.47) read the `aliased` table, whose contract maps each
# field to another column, so the SQL must name the contract's table and
# columns; the read runs again on a `COLLATE NOCASE` column.
_ALIASED_READ = _Cell(
    "project-aliased-read",
    _q(
        'where s != "a" and n is not None',
        _b("select", *_TYPES, 'low = s < "a"'),
        _b("order by", "s desc", "id"),
        header=_ALIASED_HEADER,
    ),
    (*_TYPES, "low"),
    (
        (6, 7, "\u4e2d", 1, 2.5, 0),
        (7, 7, "\u4e2d", 1, 2.5, 0),
        (3, 0, "\u00e9", None, 0.0, 0),
        (2, INT_MAX, "A", 0, 1e300, 1),
        (9, 1, "", 0, 1.0, 1),
    ),
    True,
    "aliased",
    arguments=(),
)
_ALIASED_CELLS = (
    _ALIASED_READ,
    replace(
        _ALIASED_READ, name=f"{_ALIASED_READ.name}-nocase", fixture="aliased-nocase"
    ),
    _Cell(
        "project-aliased-group-order-by-min",
        _q(
            "where x is not None",
            _b("group by", "b"),
            _b("select", "b", "rows = count()", "lo = min(n)", "hi = max(x)"),
            _b("order by", "lo", "b"),
            header=_ALIASED_HEADER,
        ),
        ("b", "rows", "lo", "hi"),
        ((1, 4, INT_MIN, 2.5), (None, 1, 0, 0.0), (0, 2, 1, 1e300)),
        True,
        "aliased",
        arguments=(),
    ),
)

# Project-only T2 cells (PL.47): `sum` of an Int over a one-sided
# `int_range`, at the bounds, in HAVING and ORDER BY and over no rows, and
# HAVING with a query parameter of each type.
_PROJECT_T2_CELLS = (
    _Cell(
        "project-t2-sum-up-to-the-bound",
        _q(_b("group by", "b"), _b("select", "b", "s = sum(n)", "c = count(n)")),
        ("b", "s", "c"),
        ((1, INT_MAX, 3), (0, 5, 2), (None, None, 0)),
        False,
        "sum-up",
        arguments=(),
    ),
    _Cell(
        "project-t2-sum-down-to-the-bound",
        _q(_b("group by", "b"), _b("select", "b", "s = sum(n)")),
        ("b", "s"),
        ((1, INT_MIN), (0, 0)),
        False,
        "sum-down",
        arguments=(),
    ),
    _Cell(
        "project-t2-sum-having-order",
        _q(
            _b("group by", "b"),
            _b("select", "b", "s = sum(n)"),
            "having s > 0",
            _b("order by", "s desc"),
        ),
        ("b", "s"),
        ((1, INT_MAX), (0, 5)),
        True,
        "sum-up",
        arguments=(),
    ),
    _Cell(
        "project-t2-sum-empty-input",
        _q("where id > 100", _b("select", "s = sum(n)")),
        ("s",),
        ((None,),),
        False,
        "sum-up",
        arguments=(),
    ),
    _Cell(
        "project-t2-having-parameters",
        _q(
            _b("group by", "s", "b"),
            _b("select", "s", "b", "c = count()", "hi = max(x)"),
            "having c >= i and s != w and hi > f or b == k",
            parameters="(i: Int, w: Text, f: Float, k: Bool)",
        ),
        ("s", "b", "c", "hi"),
        (
            ("A", 0, 1, 1e300),
            (None, 0, 1, None),
            ("\u4e2d", 1, 2, 2.5),
            ("", 0, 1, 1.0),
        ),
        False,
        arguments=(2, "a", 0.0, False),
    ),
)

# Project cells (PL.47): each single-file law and T2 cell's program as a
# project module, with the same oracle, and the parameter cells. Project SQL writes
# `COLLATE BINARY` where single files assume it, so each of these that reads
# `s` runs again on the `nocase` fixture with the same oracle; the `Bool` and
# `REAL` premise controls keep their meaning, as the contract assumes them.
_PROJECT_LAW_CELLS = (
    *(
        replace(cell, name=f"project-{cell.name}", arguments=())
        for cell in (*_LAW_CELLS, *_T2_CELLS)
    ),
    *_parameter_cells(),
    *_PROJECT_T2_CELLS,
)
_PROJECT_CELLS = (
    *_PROJECT_LAW_CELLS,
    *(
        replace(cell, name=f"{cell.name}-nocase", fixture="nocase")
        for cell in _PROJECT_LAW_CELLS
        if cell.fixture == "rows"
        and re.search(r"\bs\b", cell.program.split("\nquery q", 1)[1])
    ),
    *(
        replace(cell, name=f"project-{cell.name}", arguments=())
        for cell in (*_PREMISES, *_BOOL_NAME_CELLS)
        if cell.fixture != "nocase"
    ),
    *_ALIASED_CELLS,
)


def _ir(program: str) -> ScriptIR:
    parsed = parse_source(program, path="native.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert all(item.severity is not Severity.ERROR for item in semantic.diagnostics), (
        semantic.diagnostics
    )
    assert semantic.script is not None
    built = build_ir(semantic.script, semantic.model)
    assert built.diagnostics == ()
    assert built.ir is not None
    return built.ir


def _emit_all(program: str) -> tuple[tuple[str, str], ...]:
    result = emit_sqlite_sql(_ir(program))
    assert result.diagnostics == ()
    return tuple((artifact.name, artifact.sql) for artifact in result.artifacts)


def _emit(program: str) -> str:
    ((_name, sql),) = _emit_all(program)
    return sql


def _project_source(fixture: str) -> dict[str, Any]:
    """The contract entry of a fixture's table: `id` is the one non-null
    field, and an aliased fixture's fields read its own table and columns."""

    columns = _FIXTURE_COLUMNS["bool-pairs" if fixture == "bool-pairs" else "rows"]
    fields = tuple(
        (column, _COLUMN_TYPES[column], column != "id") for column in columns
    )
    entry = project_files.source_entry("t", fields)
    if fixture in _N_RANGES:
        low, high = _N_RANGES[fixture]
        domain = entry["fields"][1]["representation"]["domain"]
        domain.update(min=str(low), max=str(high))
    if fixture.startswith("aliased"):
        entry["relation"]["name"] = _ALIASED_TABLE
        for field, column in zip(entry["fields"], _ALIASED_COLUMNS, strict=True):
            field["column"] = column
    return entry


@pytest.fixture(scope="module")
def project_emit(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[_Cell], adapter.SQLiteArtifact]:
    """Emits a project cell's program as the module `main.pietto` of an
    explicit-module project whose contract describes the fixture table, once
    per program and contract, and returns the verified artifact."""

    emitted: dict[tuple[object, ...], adapter.SQLiteArtifact] = {}

    def emit(cell: _Cell) -> adapter.SQLiteArtifact:
        source = _project_source(cell.fixture)
        key = (cell.program, json.dumps(source))
        if key not in emitted:
            document = project_files.contract(source)
            path = tmp_path_factory.mktemp("sqlite-project") / "project"
            project_files.write(path, cell.program, document, "")
            outcome, _ = emission_cli.emit_project(
                path,
                "main.pietto",
                "query",
                "q",
                "sqlite",
                "contract.json",
                emission_cli.POLICIES["preserve"],
            )
            assert type(outcome) is adapter.SQLiteEmission, (
                cell.name,
                outcome.diagnostics,
                outcome.blockers,
            )
            assert outcome.artifact is not None, (cell.name, outcome.blockers)
            emitted[key] = outcome.artifact
        return emitted[key]

    return emit


_CARRIERS: dict[str, Callable[[Any], object]] = {
    "sqlite_integer": int,
    "sqlite_bool01": int,
    "sqlite_text": str,
    "sqlite_real": float,
}


def _binding(cell: _Cell, artifact: adapter.SQLiteArtifact) -> tuple[object, ...]:
    """The values for `?1`, `?2`, ...: each read's argument, carried by its
    `physical_type`, at the `server_index` the document gives it."""

    assert cell.arguments is not None
    bound: dict[int, object] = {}
    for use in json.loads(artifact.document)["parameter_uses"]:
        value = cell.arguments[use["owner"]["parameter"]]
        carried = None if value is None else _CARRIERS[use["physical_type"]](value)
        assert repr(bound.setdefault(use["server_index"], carried)) == repr(carried)
    assert sorted(bound) == list(range(1, len(bound) + 1)), cell.name
    return tuple(bound[number] for number in sorted(bound))


def _run(fixture: str, sql: str, parameters: tuple[object, ...] = ()) -> _Record:
    table, schema, rows = _FIXTURES[fixture]
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute(schema)
        marks = ", ".join("?" * len(rows[0]))
        quoted = table.replace("`", "``")
        connection.executemany(f"INSERT INTO `{quoted}` VALUES ({marks})", rows)
        cursor = connection.execute(sql, parameters)
        columns = tuple(item[0] for item in cursor.description)
        return _Record(sql, columns, tuple(cursor.fetchall()), parameters)


def _typed(row: object, width: int) -> tuple[tuple[str, str], ...]:
    """A row as type names and reprs: 1, 1.0 and True differ, and so do
    0.0 and -0.0 or a precomposed and a decomposed accent."""

    if type(row) is not tuple or len(row) != width:
        raise AssertionError(f"row {row!r} is not a tuple of width {width}")
    return tuple((type(value).__name__, repr(value)) for value in row)


def _judge(
    cell: _Cell, sql: str, record: object, parameters: tuple[object, ...] = ()
) -> None:
    """Judge only a record of a native run of exactly these SQL bytes with
    exactly these bound values."""

    if type(record) is not _Record:
        raise AssertionError(f"{cell.name}: no native record: {record!r}")
    if record.sql != sql:
        raise AssertionError(f"{cell.name}: the record ran other SQL bytes")
    width = len(parameters)
    if _typed(record.parameters, width) != _typed(parameters, width):
        raise AssertionError(f"{cell.name}: the record bound other values")
    if record.columns != cell.columns:
        raise AssertionError(f"{cell.name}: columns {record.columns!r}")
    if type(record.rows) is not tuple:
        raise AssertionError(f"{cell.name}: rows are not a tuple")
    width = len(cell.columns)
    observed = [_typed(row, width) for row in record.rows]
    expected = [_typed(row, width) for row in cell.rows]
    if cell.ordered and observed != expected:
        raise AssertionError(f"{cell.name}: rows {record.rows!r}")
    if not cell.ordered and Counter(observed) != Counter(expected):
        raise AssertionError(f"{cell.name}: bag {record.rows!r}")


@pytest.mark.parametrize("cell", _CELLS, ids=lambda cell: cell.name)
def test_each_cell_matches_its_prewritten_oracle(cell: _Cell, native: _Native) -> None:
    sql = _emit(cell.program)
    if not native.qualified:
        return
    record = _run(cell.fixture, sql)
    native.observe("cell", [cell.program, cell.fixture, sql, repr(record.rows)])
    _judge(cell, sql, record)


@pytest.mark.parametrize("cell", _PROJECT_CELLS, ids=lambda cell: cell.name)
def test_each_project_cell_matches_its_prewritten_oracle(
    cell: _Cell,
    native: _Native,
    project_emit: Callable[[_Cell], adapter.SQLiteArtifact],
) -> None:
    artifact = project_emit(cell)
    sql = artifact.sql.decode("utf-8")
    parameters = _binding(cell, artifact)
    if not native.qualified:
        return
    record = _run(cell.fixture, sql, parameters)
    native.observe(
        "project_cell",
        [cell.program, cell.fixture, sql, repr(parameters), repr(record.rows)],
    )
    _judge(cell, sql, record, parameters)


_OVERFLOW = ("OperationalError", 1, "SQLITE_ERROR", "integer overflow")


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("sum-over", _OVERFLOW),
        ("sum-under", _OVERFLOW),
        ("sum-mixed", _OVERFLOW),
        ("sum-mixed-reversed", ("rows", repr(((INT_MAX,),)))),
    ],
)
def test_a_one_sided_sum_fails_exactly_outside_signed_64_bits(
    fixture: str,
    expected: tuple[object, ...],
    native: _Native,
    project_emit: Callable[[_Cell], adapter.SQLiteArtifact],
) -> None:
    """Rule 35's `sum` cells (PL.47): over one sign SQLite fails exactly
    when the result leaves signed 64 bits, where PostgreSQL's exact sum
    raises SQLSTATE 22003. The `sum-mixed` premise controls break the declared
    non-negative range: the exact sum fits in both scan orders, yet SQLite
    fails in one and not in the other, so a mixed range stays refused."""

    program = _q(_b("select", "s = sum(n)"))
    cell = _Cell(
        f"project-t2-{fixture}", program, ("s",), (), False, fixture, arguments=()
    )
    sql = project_emit(cell).sql.decode("utf-8")
    if not native.qualified:
        return
    try:
        observed: tuple[object, ...] = ("rows", repr(_run(fixture, sql).rows))
    except sqlite3.Error as error:
        observed = (
            type(error).__name__,
            error.sqlite_errorcode,
            error.sqlite_errorname,
            str(error),
        )
    native.observe("sum_order", [program, fixture, sql, list(observed)])
    assert observed == expected


_GOLDEN = {
    "active_accounts": _Cell(
        "active_accounts",
        "",
        ("id", "label", "score"),
        ((1, "Ann", 0.9), (3, "O'Neil `\u00e9`", 0.5), (4, "Zed", 0.4)),
        False,
    ),
    "ranked_names": _Cell(
        "ranked_names",
        "",
        ("id", "name", "flagged", "kind", "weight", "rank"),
        (
            (5, "mo", 1, "account", 1.5, INT_MAX),
            (3, "O'Neil `\u00e9`", 0, "account", 1.5, INT_MAX),
        ),
        True,
    ),
    "region_counts": _Cell(
        "region_counts",
        "",
        ("region", "accounts", "scored", "low", "high"),
        (("east", 3, 3, 1, 2.0), ("west", 2, 0, 2, None)),
        True,
    ),
    "totals": _Cell("totals", "", ("rows", "top"), ((6, 6),), False),
}


@pytest.mark.parametrize("name", tuple(_GOLDEN))
def test_the_reviewed_golden_runs_natively(name: str, native: _Native) -> None:
    golden = SQL_GOLDEN.read_text(encoding="utf-8")
    statements = tuple(
        re.findall(r"^-- (\w+)\n(.*?);$", golden, re.MULTILINE | re.DOTALL)
    )
    # The golden bytes are the emitter's bytes for the fixture source.
    assert _emit_all(SOURCE.read_text(encoding="utf-8")) == statements
    assert tuple(statement for statement, _sql in statements) == tuple(_GOLDEN)
    if not native.qualified:
        return
    sql = dict(statements)[name]
    record = _run("accounts", sql)
    native.observe("golden", [name, "accounts", sql, repr(record.rows)])
    _judge(_GOLDEN[name], sql, record)


# PostgreSQL type OIDs by Pietto type: int8 or int4, float8, text, bool. A
# column that projects a bare Float literal may also arrive as numeric (1700),
# because the PostgreSQL emitter writes that literal as a decimal.
_PG_OIDS = {"Int": (20, 23), "Float": (701,), "Text": (25,), "Bool": (16,)}
_PG_VALUES: dict[str, Callable[[str], object]] = {
    "int": int,
    "float": float,
    "decimal": Decimal,
    "str": ast.literal_eval,
    "bool": {"True": True, "False": False}.__getitem__,
}
_PG_BOOLS: dict[object, bool] = {0: False, 1: True}


def _postgres(program: str) -> dict[str, tuple[str, dict[str, tuple[str, bool]]]]:
    """The PostgreSQL statements of a program with its `sqlite.table`
    connector swapped for `postgres.table`, each with its output columns'
    Pietto types and whether the column projects a bare Float literal."""

    assert 'sqlite.table("' in program
    script = _ir(program.replace('sqlite.table("', 'postgres.table("'))
    result = emit_postgres_sql(script)
    assert result.diagnostics == ()
    found: dict[str, dict[str, tuple[str, bool]]] = {}
    for relation in script.definitions:
        if not isinstance(relation, RelationIR):
            continue
        columns = found.setdefault(relation.name, {})
        fields = relation.row_schema.fields
        for field, projection in zip(fields, relation.projections, strict=True):
            assert projection.name in (None, field.name)
            value = projection.expression
            literal = isinstance(value, LiteralIR) and type(value.value) is float
            columns[field.name] = (field.type_ref.canonical_name, literal)
    return {item.name: (item.sql, found[item.name]) for item in result.artifacts}


def _pg_key(kind: str, value: object, oid: int, signed: bool) -> object:
    """A PostgreSQL value with its Pietto type kept, as the replay judge
    compares it: a Float as the finite decimal of its shortest repr, with
    its zero sign only when `signed`."""

    if value is None:
        return None
    if kind != "Float":
        if type(value) is not {"Int": int, "Text": str, "Bool": bool}[kind]:
            raise AssertionError(f"{kind} carried as {value!r}")
        return value
    if type(value) is float and oid == 701:
        number = Decimal(repr(value))
    elif type(value) is Decimal and oid == 1700:
        number = value
    else:
        raise AssertionError(f"Float carried as {value!r} under OID {oid}")
    if not number.is_finite():
        raise AssertionError(f"non-finite Float {value!r}")
    return number, signed and number == 0 and number.is_signed()


def _pg_rows(
    kinds: Sequence[str],
    rows: Sequence[Sequence[object]],
    oids: Sequence[int],
    signed: bool,
) -> list[tuple[object, ...]]:
    return [
        tuple(
            _pg_key(kind, value, oid, signed)
            for kind, value, oid in zip(kinds, row, oids, strict=True)
        )
        for row in rows
    ]


def _loaded(value: object, saved: object) -> bool:
    """Whether the replay loaded this fixture value: a Bool column's 0 or 1
    as a boolean, every other value with its own type."""

    if isinstance(saved, list) and saved[0] == "bool":
        return type(value) is int and value in (0, 1) and saved[1] == repr(bool(value))
    return saved == (None if value is None else [type(value).__name__, repr(value)])


def test_each_postgres_replay_binds_the_bytes_it_ran() -> None:
    """A saved PostgreSQL result counts for a cell only while the tree emits
    the PostgreSQL bytes that ran, on the fixture rows the run loaded, and
    while it meets the cell's prewritten oracle under the replay judge:
    types kept, carriers by type OID, rows as a sequence or a bag, and a zero
    sign as the one declared divergence (`ZERO_SIGN`). No database opens."""

    replay = json.loads(POSTGRES_REPLAY.read_text(encoding="utf-8"))
    assert replay["format"] == "pietto.phase78.s03.postgres-replay.v1"
    assert set(replay["fixtures"]) == {entry["fixture"] for entry in replay["entries"]}
    for name, saved in replay["fixtures"].items():
        table, _schema, rows = _FIXTURES[name]
        assert saved["table"] == table, name
        assert len(saved["rows"]) == len(rows), name
        for row, saved_row in zip(rows, saved["rows"]):
            pairs = zip(row, saved_row, strict=True)
            assert all(_loaded(value, item) for value, item in pairs), (name, row)
    subjects = []
    for cell in _LAW_CELLS:
        ((sql, columns),) = _postgres(cell.program).values()
        subjects.append((cell.name, cell, cell.fixture, sql, columns))
    golden = _postgres(SOURCE.read_text(encoding="utf-8"))
    for name, cell in _GOLDEN.items():
        subjects.append(("golden-" + name, cell, "accounts", *golden[name]))
    # One saved run per cell and golden statement, in that order, and no other.
    assert [entry["id"] for entry in replay["entries"]] == [s[0] for s in subjects]
    for entry, (name, cell, fixture, sql, columns) in zip(replay["entries"], subjects):
        assert entry["fixture"] == fixture, name
        digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        assert entry["postgres_sql_sha256"] == digest, name
        assert tuple(entry["columns"]) == cell.columns == tuple(columns), name
        kinds = [columns[column][0] for column in cell.columns]
        oids = entry["type_oids"]
        for column, oid in zip(cell.columns, oids, strict=True):
            kind, literal = columns[column]
            assert oid in _PG_OIDS[kind] + ((1700,) if literal else ()), (name, oid)
        observed = [
            [None if item is None else _PG_VALUES[item[0]](item[1]) for item in row]
            for row in entry["rows"]
        ]
        # The prewritten oracle, with a Bool column's 0 and 1 as booleans.
        wanted = [
            [
                _PG_BOOLS[value] if kind == "Bool" and value is not None else value
                for kind, value in zip(kinds, row, strict=True)
            ]
            for row in cell.rows
        ]
        canonical = [_PG_OIDS[kind][0] for kind in kinds]
        agree = []
        for signed in (False, True):
            seen = _pg_rows(kinds, observed, oids, signed)
            want = _pg_rows(kinds, wanted, canonical, signed)
            agree.append(
                seen == want if cell.ordered else Counter(seen) == Counter(want)
            )
        assert agree[0], (name, entry["rows"])
        assert entry["divergences"] == ([] if agree[1] else ["ZERO_SIGN"]), name


_WIDE = """shape Wide:
    id: Int
    ghost: Int | None

source t: Wide = sqlite.table("t")
source absent: Wide = sqlite.table("absent")

"""
_NO_GHOST = ("OperationalError", 1, "SQLITE_ERROR", "no such column: t.ghost")


@pytest.mark.parametrize(
    ("program", "expected"),
    [
        (_WIDE + "query q:\n    from t\n    select:\n        ghost\n", _NO_GHOST),
        (
            _WIDE
            + "query q:\n    from t\n    where ghost is None\n    select:\n        id\n",
            _NO_GHOST,
        ),
        (
            _WIDE
            + "query q:\n    from t\n    select:\n        id\n    order by:\n        ghost\n",
            _NO_GHOST,
        ),
        (
            _WIDE + "query q:\n    from absent\n    select:\n        id\n",
            ("OperationalError", 1, "SQLITE_ERROR", "no such table: absent"),
        ),
    ],
    ids=("select", "where", "order-by", "table"),
)
def test_a_name_the_database_lacks_fails_the_statement(
    program: str, expected: tuple[str, int, str, str], native: _Native
) -> None:
    sql = _emit(program)
    if not native.qualified:
        return
    with pytest.raises(sqlite3.Error) as caught:
        _run("rows", sql)
    error = caught.value
    observed = (
        type(error).__name__,
        error.sqlite_errorcode,
        error.sqlite_errorname,
        str(error),
    )
    native.observe("native_error", [program, "rows", sql, observed])
    assert observed == expected


@pytest.mark.parametrize(
    ("schema", "insert", "parameters", "expected"),
    [
        # Python's name table has no entry for SQLITE_CONSTRAINT_DATATYPE, so
        # this case judges the code and the text only.
        (
            _SCHEMA,
            "INSERT INTO `t` (`id`, `n`) VALUES (?, ?)",
            (1, "x"),
            (
                "IntegrityError",
                3091,
                None,
                "cannot store TEXT value in INTEGER column t.n",
            ),
        ),
        (
            "CREATE TABLE `r` (`x` REAL NOT NULL) STRICT",
            "INSERT INTO `r` VALUES (?)",
            (math.nan,),
            (
                "IntegrityError",
                1299,
                "SQLITE_CONSTRAINT_NOTNULL",
                "NOT NULL constraint failed: r.x",
            ),
        ),
    ],
    ids=("strict-text-into-integer", "nan-into-not-null-real"),
)
def test_the_fixture_premises_are_enforced_natively(
    schema: str,
    insert: str,
    parameters: tuple[object, ...],
    expected: tuple[str, int, str | None, str],
    native: _Native,
) -> None:
    if not native.qualified:
        return
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute(schema)
        with pytest.raises(sqlite3.Error) as caught:
            connection.execute(insert, parameters)
    error = caught.value
    raw = (type(error).__name__, error.sqlite_errorcode, error.sqlite_errorname)
    native.observe(
        "premise_error", [schema, insert, repr(parameters), [*raw, str(error)]]
    )
    name = raw[2] if expected[2] is not None else None
    assert (*raw[:2], name, str(error)) == expected


def test_the_running_build_is_observed(
    native_build: bool, record_property: _RecordProperty
) -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        observed = _observe(connection)
    record_property(
        "sqlite_build",
        json.dumps(
            {
                "sqlite3.sqlite_version": sqlite3.sqlite_version,
                "sqlite_version()": observed.release,
                "sqlite_source_id()": observed.source_id,
                "compile_options": observed.compile_options,
                "refusal": _refusal(observed),
            }
        ),
    )
    assert observed.release == sqlite3.sqlite_version
    assert (_refusal(observed) is None) is native_build


_FORGED = (
    (replace(QUALIFIED_SQLITE_BUILD, release="3.53.2"), "SQLITE_BUILD_RELEASE"),
    (
        replace(
            QUALIFIED_SQLITE_BUILD,
            source_id=QUALIFIED_SQLITE_BUILD.source_id[:-1] + "8",
        ),
        "SQLITE_BUILD_SOURCE",
    ),
    (
        replace(
            QUALIFIED_SQLITE_BUILD,
            compile_options=(
                *QUALIFIED_SQLITE_BUILD.compile_options,
                "ENABLE_LOAD_EXTENSION",
            ),
        ),
        "SQLITE_BUILD_OPTIONS",
    ),
    (
        replace(
            QUALIFIED_SQLITE_BUILD,
            compile_options=QUALIFIED_SQLITE_BUILD.compile_options[:-1],
        ),
        "SQLITE_BUILD_OPTIONS",
    ),
    (
        replace(
            QUALIFIED_SQLITE_BUILD,
            compile_options=tuple(reversed(QUALIFIED_SQLITE_BUILD.compile_options)),
        ),
        "SQLITE_BUILD_OPTIONS",
    ),
    (
        _Build(
            "3.46.1",
            "2024-08-13 09:16:08 "
            "c9c2ab54ba1f5f46360f1b4f35d849cd3f080e6fc2b6c60e91b16c63f69aalt1",
            ("COMPILER=gcc-15.2.0", "ENABLE_LOAD_EXTENSION"),
        ),
        "SQLITE_BUILD_RELEASE",
    ),
)


@pytest.mark.parametrize(("forged", "category"), _FORGED)
def test_a_forged_build_is_refused_in_every_class(
    forged: _Build, category: str
) -> None:
    assert _refusal(forged) == category
    assert _qualified(forged, "hosted-refusal") is False
    with pytest.raises(
        pytest.skip.Exception, match=f"^PIETTO_NOT_RUN sqlite-native {category}$"
    ):
        _qualified(forged, "report")
    with pytest.raises(
        pytest.fail.Exception, match=f"^PIETTO_SQLITE_REQUIRED {category}$"
    ):
        _qualified(forged, "qualified")
    for declared in SQLITE_CLASSES:
        assert _qualified(QUALIFIED_SQLITE_BUILD, declared) is True


@pytest.mark.parametrize(
    ("environ", "option", "expected"),
    [
        ({}, None, "report"),
        ({"GITHUB_ACTIONS": "true"}, None, "hosted-refusal"),
        ({"GITHUB_ACTIONS": "true"}, "qualified", "qualified"),
        ({SQLITE_CLASS_VARIABLE: "qualified"}, None, "qualified"),
        ({SQLITE_CLASS_VARIABLE: "report"}, "report", "report"),
        # The job store's storage class is not this class.
        ({"PIETTO_STORAGE_CLASS": "qualified"}, None, "report"),
        ({"PIETTO_STORAGE_CLASS": "hosted-refusal"}, None, "report"),
    ],
)
def test_the_sqlite_class_is_declared_or_defaulted(
    environ: dict[str, str], option: str | None, expected: str
) -> None:
    assert _sqlite_class(environ, option) == expected


@pytest.mark.parametrize(
    ("environ", "option", "code"),
    [
        (
            {SQLITE_CLASS_VARIABLE: "report"},
            "qualified",
            "PIETTO_SQLITE_CLASS_CONFLICT",
        ),
        ({SQLITE_CLASS_VARIABLE: "QUALIFIED"}, None, "PIETTO_SQLITE_CLASS_UNKNOWN"),
        ({SQLITE_CLASS_VARIABLE: ""}, None, "PIETTO_SQLITE_CLASS_UNKNOWN"),
    ],
)
def test_a_conflicting_or_unknown_sqlite_class_fails_closed(
    environ: dict[str, str], option: str | None, code: str
) -> None:
    with pytest.raises(ValueError, match=f"^{code}$"):
        _sqlite_class(environ, option)


def _cell(name: str) -> _Cell:
    (cell,) = (cell for cell in _CELLS if cell.name == name)
    return cell


def test_the_judge_fails_every_fabricated_fail_open_shape() -> None:
    bag = _cell("select-multiplicity")
    order = _cell("order-text-asc")
    typed = _cell("select-literals")
    sql = "SELECT fabricated"

    def record(
        cell: _Cell, rows: tuple[tuple[object, ...], ...] | None = None
    ) -> _Record:
        return _Record(sql, cell.columns, cell.rows if rows is None else rows)

    for cell in (bag, order, typed):
        _judge(cell, sql, record(cell))
    _judge(bag, sql, record(bag, tuple(reversed(bag.rows))))

    literal = typed.rows[0]
    fabricated = [
        (bag, None),
        (bag, (sql, bag.columns, bag.rows)),
        (bag, replace(record(bag), sql=sql + " ")),
        (bag, replace(record(bag), columns=("n", "other"))),
        (bag, replace(record(bag), columns=("n",))),
        (bag, record(bag, ())),
        (bag, record(bag, bag.rows[1:])),
        (bag, record(bag, bag.rows + bag.rows[:1])),
        (bag, record(bag, tuple(dict.fromkeys(bag.rows)))),
        (bag, record(bag, tuple(row + (None,) for row in bag.rows))),
        (bag, replace(record(bag), rows=list(bag.rows))),
        (bag, record(bag, ((None, "a"), *bag.rows[1:]))),
        (
            bag,
            record(
                bag, ((INT_MIN, "a"), (INT_MAX, "A"), (0, "e\u0301"), *bag.rows[3:])
            ),
        ),
        (order, record(order, (order.rows[1], order.rows[0], *order.rows[2:]))),
        (order, record(order, order.rows[:-1])),
        (typed, record(typed, ((True, *literal[1:]),))),
        (typed, record(typed, ((1.0, *literal[1:]),))),
        (typed, record(typed, ((*literal[:4], -0.0, *literal[5:]),))),
        (typed, record(typed, ((*literal[:7], True, literal[8]),))),
        (typed, record(typed, ((*literal[:2], False, *literal[3:]),))),
    ]
    for cell, output in fabricated:
        with pytest.raises(AssertionError):
            _judge(cell, sql, output)

    bound = (7, -0.0)
    _judge(bag, sql, replace(record(bag), parameters=bound), bound)
    for parameters in ((), (7,), (7, 0.0), (7.0, -0.0), (7, -0.0, None), [7, -0.0]):
        with pytest.raises(AssertionError):
            _judge(bag, sql, replace(record(bag), parameters=parameters), bound)


def _python_ids(cell: _Cell) -> tuple[tuple[object, ...], ...] | None:
    """The ids a bare Bool field, one comparison or one NULL test keeps by
    Python's operators; None for a compound condition."""

    assert cell.condition is not None
    columns = _FIXTURE_COLUMNS[cell.fixture]
    match = re.fullmatch(
        r'(\w+)(?: (==|!=|<=|>=|<|>) ("[^"]*"|\S+)| (is None|is not None))?',
        cell.condition,
    )
    if match is None:
        return None
    field, spelling, right, test = match.groups()
    kept = []
    for row in _FIXTURES[cell.fixture][2]:
        value = _python_value(field, row[columns.index(field)])
        if test is not None:
            truth = _python_truth(value, test, None)
        elif spelling is None:
            truth = value
        elif right in columns:
            truth = _python_truth(
                value, spelling, _python_value(right, row[columns.index(right)])
            )
        else:
            truth = _python_truth(value, spelling, ast.literal_eval(right))
        if truth is True:
            kept.append(row[0])
    return _ids(*kept)


def test_each_single_where_oracle_agrees_with_python() -> None:
    """No SQLite: a prewritten `where` oracle of one comparison, NULL test or
    bare Bool field keeps exactly the rows Python's operators keep."""

    for cell in _LAW_CELLS:
        if cell.condition is None:
            continue
        expected = _python_ids(cell)
        if expected is None:
            assert re.search(r"\b(and|or|not)\b", cell.condition), cell.name
            continue
        assert Counter(cell.rows) == Counter(expected), cell.name


_SECTION = re.compile(r"\n(FROM|WHERE|GROUP BY|HAVING|ORDER BY|LIMIT)\b")
_TEXT_LITERAL = re.compile(r"'(?:[^']|'')*'")
_AGGREGATE = re.compile(
    r"\b(COUNT|MIN|MAX|AVG)\((DISTINCT |CAST\()?(\*|`t`\.`(\w+)`)(?: AS REAL\))?\)"
)
_COLUMN = re.compile(r"`t`\.`(\w+)`")
_FLOAT = re.compile(r"(?<![\w.`])\d+(?:\.\d+(?:e[+-]\d+)?|e[+-]\d+)(?![\w.`])")
_INT = re.compile(r"(?<![\w.`])\d+(?![\w.`])")
# `@<type>` stands for an aggregate of that result type.
_OPERAND = r"`t`\.`\w+`|@\w+|'\?'|\d+(?:\.\d+)?(?:e[+-]\d+)?"
_COMPARISON = re.compile(rf"({_OPERAND}) (<>|<=|>=|=|<|>) ({_OPERAND})")
_NULL_TEST = re.compile(r"(`t`\.`\w+`) (IS NOT NULL|IS NULL)")


def _aggregate_form(match: re.Match[str]) -> tuple[str, str]:
    """An aggregate's form, its name and argument type, and its result type."""

    function, prefix, _argument, column = match.groups()
    name = "count_distinct" if prefix == "DISTINCT " else function.lower()
    assert (name == "avg") is (prefix == "CAST("), match[0]
    argument = _COLUMN_TYPES[column] if column else "*"
    result = {"count": "Int", "count_distinct": "Int", "avg": "Float"}.get(name)
    return f"{name} {argument}", result or argument


def _operand_type(operand: str) -> str:
    if operand.startswith("@"):
        return operand[1:]
    column = _COLUMN.fullmatch(operand)
    if column is not None:
        return _COLUMN_TYPES[column[1]]
    if operand == "'?'":
        return "Text"
    return "Float" if _FLOAT.fullmatch(operand) else "Int"


def _forms(sql: str) -> set[str]:
    """The forms one statement uses, read from its bytes: each comparison,
    NULL test, connective and order direction with its clause and type."""

    parts = _SECTION.split(_TEXT_LITERAL.sub("'?'", sql))
    clauses = {"SELECT": parts[0], **dict(zip(parts[1::2], parts[2::2]))}
    forms = {"limit"} if "LIMIT" in clauses else set()
    for clause, text in clauses.items():
        name = clause.lower()
        for match in _AGGREGATE.finditer(text):
            forms.add(_aggregate_form(match)[0])
            if clause in ("ORDER BY", "HAVING"):
                forms.add(f"{name} aggregate")
        for column in _COLUMN.findall(_AGGREGATE.sub("", text)):
            forms.add(f"{name} {_COLUMN_TYPES[column]}")
        if clause == "ORDER BY":
            for column, direction in _ORDER_KEY.findall(text):
                forms.add(f"order by {_COLUMN_TYPES[column]} {direction}")
        if clause not in ("SELECT", "WHERE", "HAVING"):
            continue
        # shortcut: a Bool literal is 1 or 0 in the bytes, so each counts as
        # literal Int too outside HAVING, and only one compared with a Bool
        # operand counts as literal Bool; read the IR if the guards must
        # tell them apart.
        for literal, pattern in (("Float", _FLOAT), ("Int", _INT)):
            if clause != "HAVING" and pattern.search(
                _FLOAT.sub("", text) if literal == "Int" else text
            ):
                forms.add(f"literal {literal}")
        if "'?'" in text:
            forms.add("literal Text")
        typed = _AGGREGATE.sub(lambda match: "@" + _aggregate_form(match)[1], text)
        for left, comparison, right in _COMPARISON.findall(typed):
            kinds = {_operand_type(left), _operand_type(right)}
            if kinds == {"Bool", "Int"} and {left, right} & {"0", "1"}:
                kinds = {"Bool"}  # a Bool literal is written 1 or 0
                forms.add("literal Bool")
            assert len(kinds) == 1, sql
            forms.add(f"{name} {kinds.pop()} {comparison}")
        for operand, test in _NULL_TEST.findall(text):
            forms.add(f"{name} {_operand_type(operand)} {test}")
        for connective in re.findall(r"\b(AND|OR)\b", text):
            forms.add(f"{name} Bool {connective}")
        if re.search(r"\bNOT (?!NULL)", text):
            forms.add(f"{name} Bool NOT")
    return forms


# The emitter's own vocabulary, so a new value type, operator, connective,
# aggregate or direction needs a native cell before it can ship. Each
# comparison and NULL test is required per clause and value type, not once.
_KINDS = tuple(sorted(sqlite_relations._VALUE_TYPES))
_ORDER_KEY = re.compile(
    r"`t`\.`(\w+)` ("
    + "|".join(map(re.escape, sqlite_relations._DIRECTIONS.values()))
    + ")"
)
_REQUIRED_FORMS = {
    *(
        f"{clause} {kind}"
        for clause in ("select", "where", "group by", "order by")
        for kind in _KINDS
    ),
    *(f"count {kind}" for kind in ("*", *_KINDS)),
    *(
        f"{function.lower()} {kind}"
        for function in sqlite_relations._EXTREMA.values()
        for kind in sorted(sqlite_relations._EXTREMA_TYPES)
    ),
    *(f"count_distinct {kind}" for kind in sorted(sqlite_relations._DISTINCT_TYPES)),
    "avg Int",
    "order by aggregate",
    "having aggregate",
    *(
        f"having {kind} {test}"
        for kind in _KINDS
        for test in sqlite_relations._COMPARISONS.values()
    ),
    *(
        f"having Bool {connective}"
        for connective in sqlite_relations._CONNECTIVES.values()
    ),
    "limit",
    *(f"literal {kind}" for kind in _KINDS),
    *(
        f"{clause} {kind} {test}"
        for clause in ("select", "where")
        for kind in _KINDS
        for test in (
            *sqlite_relations._COMPARISONS.values(),
            "IS NULL",
            "IS NOT NULL",
        )
    ),
    *(
        f"{clause} Bool {connective}"
        for clause in ("select", "where")
        for connective in (*sqlite_relations._CONNECTIVES.values(), "NOT")
    ),
    *(
        f"order by {kind} {direction}"
        for kind in _KINDS
        for direction in sqlite_relations._DIRECTIONS.values()
    ),
}


def _missing_forms(cells: Sequence[_Cell]) -> set[str]:
    forms = set().union(*(_forms(_emit(cell.program)) for cell in cells))
    return _REQUIRED_FORMS - forms


_VALUE_KINDS = {bool: "Bool", int: "Int", float: "Float", str: "Text"}
_STORAGE_KINDS = {storage: kind for kind, storage in adapter.STORAGES.items()}
_PREDICATES = (
    adapter_sql.SQLiteComparison,
    adapter_sql.SQLiteLogical,
    adapter_sql.SQLiteNot,
    adapter_sql.SQLiteIsNull,
)


def _project_forms(artifact: adapter.SQLiteArtifact) -> set[str]:
    """The forms one verified project statement uses, read from the adapter's
    SQL AST that renders its bytes: each column, parameter, literal,
    comparison, NULL test, connective, aggregate and key with its clause and
    type. It asserts that `COLLATE BINARY` is written exactly at each `Text`
    comparison and key."""

    ast = artifact.ast
    uses = json.loads(artifact.document)["parameter_uses"]
    parameters = {u["server_index"]: _STORAGE_KINDS[u["physical_type"]] for u in uses}
    forms = {"limit"} if ast.limit is not None else set()

    def kind(node: object) -> str:
        if isinstance(node, _PREDICATES):
            return "Bool"
        if type(node) is adapter_sql.SQLiteAggregate:
            results = {"count": "Int", "count_distinct": "Int", "avg": "Float"}
            return results.get(node.function) or kind(node.argument)
        if type(node) is adapter_sql.SQLiteColumn:
            return _COLUMN_TYPES[ast.columns[node.field]]
        if type(node) is adapter_sql.SQLiteParameter:
            return parameters[node.number]
        assert type(node) is adapter_sql.SQLiteLiteral, node
        return _VALUE_KINDS[type(node.value)]

    def walk(node: object, clause: str) -> None:
        if type(node) is adapter_sql.SQLiteAggregate:
            argument = "*" if node.argument is None else kind(node.argument)
            text = node.function == "count_distinct" and argument == "Text"
            assert node.collate is text, node
            forms.add(f"{node.function} {argument}")
            if clause == "having":
                forms.add("having aggregate")
            return
        if type(node) is adapter_sql.SQLiteLiteral:
            forms.add(f"literal {kind(node)}")
        elif type(node) is adapter_sql.SQLiteParameter:
            forms.add(f"{clause} parameter {kind(node)}")
        elif type(node) is adapter_sql.SQLiteColumn:
            forms.add(f"{clause} {kind(node)}")
        elif type(node) is adapter_sql.SQLiteComparison:
            left = kind(node.left)
            assert kind(node.right) == left, node
            assert node.collate is (left == "Text"), node
            forms.add(f"{clause} {left} {node.operator}")
        elif type(node) is adapter_sql.SQLiteIsNull:
            test = "IS NOT NULL" if node.negated else "IS NULL"
            forms.add(f"{clause} {kind(node.operand)} {test}")
        elif type(node) is adapter_sql.SQLiteLogical:
            forms.add(f"{clause} Bool {node.operator}")
        else:
            assert type(node) is adapter_sql.SQLiteNot, node
            forms.add(f"{clause} Bool NOT")
        for name in ("left", "right", "operand"):
            child = getattr(node, name, None)
            if child is not None:
                walk(child, clause)

    for result in ast.results:
        walk(result.value, "select")
    if ast.where is not None:
        walk(ast.where, "where")
    if ast.having is not None:
        walk(ast.having, "having")
    for clause, keys in (("group by", ast.group_by), ("order by", ast.order_by)):
        for key in keys:
            walk(key.value, clause)
            if type(key.value) is adapter_sql.SQLiteAggregate:
                assert not key.collate, key
                forms.add(f"{clause} aggregate")
                continue
            assert key.collate is (kind(key.value) == "Text"), key
            if key.descending is not None:
                direction = "desc" if key.descending else "asc"
                forms.add(f"{clause} {kind(key.value)} {direction}")
    return forms


# The adapter's own vocabulary (PL.47): its value types, operators,
# connectives, aggregate functions and key directions, and a query parameter
# of each type in `select`, `where` and `having`, each per clause and type;
# HAVING has no `not` or null test, which `check` refuses there (PIE-S2327).
_PROJECT_FORMS = {
    *(
        f"{clause} {kind}"
        for clause in ("select", "where", "group by", "order by")
        for kind in adapter.TYPES
    ),
    *(
        f"{clause} parameter {kind}"
        for clause in ("select", "where", "having")
        for kind in adapter.TYPES
    ),
    *(f"count {kind}" for kind in ("*", *adapter.TYPES)),
    # Rule 10 admits each other aggregate over the field types it reads.
    *(
        f"{function} {kind}"
        for function, kinds in adapter._ARGUMENTS.items()
        for kind in sorted(kinds)
    ),
    "order by aggregate",
    "having aggregate",
    *(
        f"having {kind} {test}"
        for kind in adapter.TYPES
        for test in adapter_sql.OPERATORS.values()
    ),
    *(f"having Bool {connective}" for connective in adapter_sql.LOGICAL.values()),
    "limit",
    *(f"literal {kind}" for kind in adapter.TYPES),
    *(
        f"{clause} {kind} {test}"
        for clause in ("select", "where")
        for kind in adapter.TYPES
        for test in (*adapter_sql.OPERATORS.values(), "IS NULL", "IS NOT NULL")
    ),
    *(
        f"{clause} Bool {connective}"
        for clause in ("select", "where")
        for connective in (*adapter_sql.LOGICAL.values(), "NOT")
    ),
    *(
        f"order by {kind} {direction}"
        for kind in adapter.TYPES
        for direction in ("asc", "desc")
    ),
}


def test_every_emitted_form_has_a_native_cell(
    project_emit: Callable[[_Cell], adapter.SQLiteArtifact],
) -> None:
    assert _missing_forms((*_LAW_CELLS, *_T2_CELLS)) == set()
    artifacts = (project_emit(cell) for cell in _PROJECT_LAW_CELLS)
    assert _PROJECT_FORMS - set().union(*map(_project_forms, artifacts)) == set()
    for cell in _ALIASED_CELLS:
        ast = project_emit(cell).ast
        assert (ast.table, ast.columns) == (_ALIASED_TABLE, _ALIASED_COLUMNS)
    names = [cell.name for cell in (*_CELLS, *_PROJECT_CELLS)]
    assert len(names) == len(set(names))
