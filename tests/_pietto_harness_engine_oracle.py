"""In-process DuckDB and SQLite oracles of the generated forms.

For a case of tests/_pietto_harness_generated_forms.py this module draws
seeded rows for its sources ``t`` and ``u``, loads them into an in-memory
SQLite database or DuckDB connection as tables ``t`` and ``u``, and writes the
case's own SQL from the case alone: every expression fully parenthesized,
each ``let`` inlined, ``==`` and ``!=`` as ``=`` and ``<>``, SQL's
three-valued ``AND`` and ``OR``, ``count()`` as ``COUNT(*)`` and each ORDER BY
key with Pietto's null order, ``NULLS LAST`` ascending and ``NULLS FIRST``
descending (docs/language.md). The same text runs on both engines. Rows come
back normalized by the generator's oracle types, so that SQLite's 0 and 1
compare with ``Bool`` values and DuckDB's dates and decimals with SQLite's
text and reals; a zero keeps its sign.

It never imports pietto: the test owner compares the product's public
outputs with what these engines return.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
import random
from typing import Any

import _pietto_harness_generated_forms as forms

ROWS = 6  # rows of each source, ids 1 to ROWS
# Small pools with the generator's literals, ties and both signs; every Int
# stays far inside the contract's range under three nested operators, and
# every Float is a short binary fraction, so sums and products are exact.
VALUES: dict[str, tuple[Any, ...]] = {
    "Int": (-7, -1, 0, 1, 7, 12),
    "Float": (-1.5, 0.0, 0.5, 2.0, 3.25),
    "Text": ("a", "A", "Zz", "b", ""),
    "Bool": (True, False),
    "Date": ("2025-12-31", "2026-01-31", "2026-02-01"),
}
_SQL_TYPES = {
    "sqlite": {"Int": "INTEGER", "Float": "REAL", "Text": "TEXT", "Bool": "INTEGER"},
    "duckdb": {
        "Int": "BIGINT",
        "Float": "DOUBLE",
        "Text": "VARCHAR",
        "Bool": "BOOLEAN",
    },
}
_DATE = {"sqlite": "TEXT", "duckdb": "DATE"}  # SQLite keeps ISO text, in date order
_OPERATORS = {"==": "=", "!=": "<>"}


def rows(case: forms.Case, source: str) -> list[tuple[Any, ...]]:
    """The rows of ``source`` (``t`` or ``u``): deterministic per case."""
    rng = random.Random(f"rows:{case.profile}:{case.seed}:{source}")
    return [
        (
            ident,
            *(
                None if nullable and rng.random() < 0.3 else rng.choice(VALUES[kind])
                for _, kind, nullable in case.fields[1:]
            ),
        )
        for ident in range(1, ROWS + 1)
    ]


def load(connection: Any, case: forms.Case, engine: str) -> None:
    """Create and fill ``t`` and ``u`` on a sqlite3 or duckdb connection."""
    types = _SQL_TYPES[engine] | {"Date": _DATE[engine]}
    columns = ", ".join(
        f'"{name}" {types[kind]}{"" if nullable else " NOT NULL"}'
        for name, kind, nullable in case.fields
    )
    marks = ", ".join("?" for _ in case.fields)
    for source in ("t", "u"):
        connection.execute(f'CREATE TABLE "{source}" ({columns})')
        connection.executemany(
            f'INSERT INTO "{source}" VALUES ({marks})', rows(case, source)
        )


def _name(field: str) -> str:
    return ".".join(f'"{part}"' for part in field.split("."))


def _sql(case: forms.Case, expression: tuple) -> str:
    tag = expression[0]
    if tag == "field":
        return _name(expression[1])
    if tag == "let":
        return _sql(case, dict(case.lets)[expression[1]])
    if tag == "lit":
        kind, text = expression[1:]
        if kind == "Text":
            return "'" + text[1:-1] + "'"
        return text.upper() if kind == "Bool" else text
    if tag == "neg":
        return f"(-{_sql(case, expression[1])})"
    if tag in ("arith", "cmp", "bool"):
        operator = _OPERATORS.get(expression[1], expression[1].upper())
        return f"({_sql(case, expression[2])} {operator} {_sql(case, expression[3])})"
    if tag == "call":
        arguments = ", ".join(_sql(case, a) for a in expression[2:])
        return f"{expression[1].upper()}({arguments})"
    if tag == "isnone":
        return f"({_sql(case, expression[1])} IS {'NOT ' if expression[2] else ''}NULL)"
    if tag == "agg":
        argument = _sql(case, expression[2]) if expression[2] else "*"
        return f"{expression[1].upper()}({argument})"
    raise ValueError(tag)


def oracle_sql(case: forms.Case) -> str:
    """The case's query, without its LIMIT, as SQL that SQLite and DuckDB
    both run; ``disagreement`` applies the LIMIT."""
    items = ", ".join(f'{_sql(case, e)} AS "{name}"' for name, e in case.items)
    text = f'SELECT {items} FROM "t" AS "t"'
    if case.join is not None:
        kind, on = case.join
        text += f' {kind.upper()} JOIN "u" AS "r"'
        text += f" ON {_sql(case, on)}" if on else ""
    if case.where is not None:
        text += f" WHERE {_sql(case, case.where)}"
    if case.keys:
        text += " GROUP BY " + ", ".join(_name(key) for key in case.keys)
    if case.order:
        text += " ORDER BY " + ", ".join(
            f"{_name(key)} {'DESC NULLS FIRST' if desc else 'ASC NULLS LAST'}"
            for key, desc in case.order
        )
    return text


def _value(kind: str, value: Any) -> Any:
    if value is None or kind in ("Int", "Text"):
        return value
    if kind == "Bool":
        return bool(value) if value in (0, 1) else value
    if kind == "Float":
        return float(value)
    return str(value)  # Date: DuckDB's date and SQLite's text, both ISO


def normalized(case: forms.Case, records: Sequence[Sequence[Any]]) -> list[tuple]:
    """``records`` as tuples of comparable values, in the oracle's types."""
    kinds = [kind for _, kind, _ in forms.expected_columns(case)]
    return [
        tuple(_value(kind, value) for kind, value in zip(kinds, record, strict=True))
        for record in records
    ]


def _key(row: tuple) -> tuple:
    # `True == 1`, `1.0 == 1` and `-0.0 == 0.0` in Python; a type and a repr
    # tell each pair apart.
    return tuple((type(value).__name__, repr(value)) for value in row)


def ordered(case: forms.Case) -> bool:
    """Whether the case's ORDER BY fixes the order of every output row: a
    row form ends with the unique ``id``, and an aggregate form's keys name
    its groups; a JOIN repeats ``t.id``."""
    if case.form == "row":
        return True
    return case.form == "aggregate" and {k for k, _ in case.order} >= set(case.keys)


def disagreement(case: forms.Case, seen: list[tuple], wanted: list[tuple]) -> str:
    """Why ``seen`` is not a result of the case whose unlimited oracle rows
    are ``wanted``, or an empty string. Under an order with ties a LIMIT may
    keep any of the tied rows, so there the count and bag inclusion bind."""
    keys, want = [_key(row) for row in seen], [_key(row) for row in wanted]
    if case.limit is not None:
        if len(keys) != min(case.limit, len(want)):
            return "row count differs"
        if not ordered(case):
            return "" if not Counter(keys) - Counter(want) else "rows outside the bag"
        want = want[: case.limit]
    if ordered(case):
        return "" if keys == want else "rows differ"
    return "" if Counter(keys) == Counter(want) else "bags differ"


def null_in_non_null(case: forms.Case, records: list[tuple]) -> list[str]:
    """The columns that the oracle types ``non_null`` but hold a NULL."""
    columns = forms.expected_columns(case)
    return [
        name
        for index, (name, _, state) in enumerate(columns)
        if state == forms.NON_NULL and any(row[index] is None for row in records)
    ]
