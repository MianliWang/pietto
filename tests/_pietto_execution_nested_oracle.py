"""Independent typed-literal oracle for Phase71 Collect and Unnest programs.

Seeds, a closed program family rendered as ``schema_version = 2`` project
sources, pure-Python expected values, a tie-aware type-exact comparator and
damage controls. No pietto, driver or Arrow import: expected values come from
the seed literals alone (D71.03, D71.04; the brief's semantic contract).

Semantics kept here, independently of the compiler:
- a captured let whose correlation key is NULL yields ``[]``; an ON or WHERE
  with a NULL operand never matches; LEFT keeps one NULL-extended row when no
  child matches, even when ON is False; a later WHERE may remove it; any
  Unnest other than CROSS, or INNER/LEFT ON True, False or ``o.v > 10``,
  raises ValueError;
- NULL order follows PostgreSQL (``NULL_POSTURE = "target_defined"``): last
  ascending, first descending; only Int, Bool and Decimal keys are admitted;
- rows that tie on every order key form a group whose internal order is not
  compared; at a LIMIT boundary any subset of the right size is accepted;
- parents compare by position, by tie group, or as a bag (bipartite matching);
  a record's fields compare in their contract (child-ordinal) order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import cmp_to_key
import json
import math
from typing import Any
from uuid import UUID

from _pietto_target_conformance_observation import scalar

CONFIG = 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
SENTINEL = "PIETTO-SENTINEL-71-NESTED"
SETS = ("MINIMAL", "FULL")
LEAVES = ("Int", "Bool", "Text", "Float", "Decimal", "Date", "Timestamp", "UUID")
DEFAULT_LEAVES = ("Int", "Bool", "Text")
ORDERABLE = frozenset({"Int", "Bool", "Decimal"})
# Child columns of `orders` that each admitted leaf opens; Int owns two
# same-typed fields so a same-type column swap is observable.
LEAF_COLUMNS = {
    "Int": (("v", "Int"), ("k", "Int")),
    "Bool": (("flag", "Bool"),),
    "Text": (("note", "Text"),),
    "Float": (("ratio", "Float"),),
    "Decimal": (("price", "Decimal(18, 4)"),),
    "Date": (("ship_day", "Date"),),
    "Timestamp": (("seen_at", "Timestamp"),),
    "UUID": (("token", "UUID"),),
}
_ORDER_COLUMNS = (
    "v",
    "k",
    "flag",
    "note",
    "ratio",
    "price",
    "ship_day",
    "seen_at",
    "token",
)
_D = Decimal
_T = datetime
_EXTRA_NULL = (None, None, None, None, None)
# id, customer_id, then _ORDER_COLUMNS in order.
_ORDERS_MINIMAL = (
    (10, 1, 7, 5, True, "a", 0.0, _D("7.0000"), date(2024, 1, 1))
    + (_T(2024, 1, 1, 0, 0, 0, 1), UUID(int=1)),
    (11, 1, 7, 5, True, "a", 0.0, _D("7.0000"), date(2024, 1, 1))
    + (_T(2024, 1, 1, 0, 0, 0, 1), UUID(int=1)),
)
_ORDERS_FULL = (
    (12, 1, 8, 5, False, "b", -0.0, _D("-0.0001"), date(1970, 1, 1))
    + (_T(1999, 12, 31, 23, 59, 59, 999999), UUID(int=2**128 - 1)),
    (20, 3, None, None, None, None) + _EXTRA_NULL,
    (21, 3, 11, 1, False, ',{}"\\', 1.5, _D("12.3400"), date(2024, 2, 29))
    + (_T(2024, 2, 29, 12, 0, 0, 123456), UUID("12345678-1234-5678-1234-567812345678")),
    (22, 3, 12, None, None, "", 1e-300, _D("0.0000"), date(2000, 1, 1))
    + (_T(2000, 1, 1, 0, 0, 0, 500000), UUID(int=3)),
    (23, 3, 13, 2, True, "NULL", -2.25, _D("99999999999999.9999"))
    + (date(9999, 12, 31), _T(9999, 12, 31, 23, 59, 59, 999999), UUID(int=4)),
    (24, 3, 14, 2, False, "é中😀", 1.7976931348623157e308)
    + (_D("-99999999999999.9999"), date(1900, 3, 1), _T(1900, 3, 1, 0, 0, 0, 1))
    + (UUID(int=5),),
    (25, 3, 15, 3, None, SENTINEL, None, None, None, None, None),
    (30, 4, 10, 0, True, "d", 3.0, _D("10.0000"), date(2024, 6, 30))
    + (_T(2024, 6, 30, 6, 30, 0, 250000), UUID(int=6)),
    (40, None, 99, 9, True, "orphan", 4.0, _D("1.0000"), date(2024, 7, 1))
    + (_T(2024, 7, 1, 7, 0, 0, 750000), UUID(int=7)),
)
_CUSTOMERS_MINIMAL = ((1, "A"), (1, "A"), (2, "B"))
_CUSTOMERS_FULL = ((3, "C"), (4, "D"), (None, "N"))
_PAYMENTS_MINIMAL = ((50, 1, 100), (51, 1, 200), (52, 1, None))
_PAYMENTS_FULL = ((53, 3, 400), (54, None, 500), (55, 3, 400), (56, 4, None))


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    nullable: bool

    @property
    def kind(self) -> str:
        return self.type.split("(")[0]

    def spelling(self) -> str:
        return self.type + (" | None" if self.nullable else "")


@dataclass(frozen=True)
class Table:
    name: str
    shape: str
    columns: tuple[Column, ...]
    rows: tuple[tuple[Any, ...], ...]

    def records(self) -> list[dict[str, Any]]:
        names = [column.name for column in self.columns]
        return [dict(zip(names, row, strict=True)) for row in self.rows]

    def column(self, name: str) -> Column:
        for column in self.columns:
            if column.name == name:
                return column
        raise ValueError(f"unknown column {self.name}.{name}")


@dataclass(frozen=True)
class Let:
    name: str
    table: str
    select: tuple[str, ...]
    order: tuple[tuple[str, bool], ...]
    captured: bool = True
    limit: int | None = None
    distinct: bool = False
    group: str | None = None


@dataclass(frozen=True)
class Collect:
    lets: tuple[Let, ...]
    order: tuple[tuple[str, bool], ...] = ()
    limit: int | None = None


@dataclass(frozen=True)
class Unnest:
    join: str
    on: str | None
    where: bool
    lateral: bool
    fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if (self.join, self.on is None) not in _JOINS or self.on not in (None, *_ON):
            raise ValueError(f"Unnest {self.join} join on {self.on!r} is not modeled")


@dataclass(frozen=True)
class Program:
    name: str
    spec: Collect | Unnest
    files: tuple[tuple[str, str], ...]
    result: str = "result"
    twin: str | None = None


@dataclass(frozen=True)
class Segment:
    """Rows in one tie group; ``take`` of the candidates are expected."""

    candidates: tuple[Any, ...]
    take: int


@dataclass(frozen=True)
class Nested:
    segments: tuple[Segment, ...]


def leaves_of(leaves: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    chosen = set(leaves)
    if not chosen <= set(LEAVES) or "Int" not in chosen or len(chosen) != len(leaves):
        raise ValueError("leaves must be distinct admitted leaf names including Int")
    return tuple(name for name in LEAVES if name in chosen)


def child_fields(leaves: tuple[str, ...] = DEFAULT_LEAVES) -> tuple[str, ...]:
    return tuple(
        column for leaf in leaves_of(leaves) for column, _ in LEAF_COLUMNS[leaf]
    )


def seed(set_name: str, leaves: tuple[str, ...] = DEFAULT_LEAVES) -> dict[str, Table]:
    """Typed tables for one seed set; consumers load them with bound parameters."""
    if set_name not in SETS:
        raise ValueError("unknown seed set")
    full = set_name == "FULL"
    fields = child_fields(leaves)
    types = {
        column: spelling for leaf in LEAVES for column, spelling in LEAF_COLUMNS[leaf]
    }
    keep = [2 + _ORDER_COLUMNS.index(column) for column in fields]
    orders = _ORDERS_MINIMAL + (_ORDERS_FULL if full else ())
    return {
        "customers": Table(
            "customers",
            "Customer",
            (Column("id", "Int", True), Column("name", "Text", False)),
            _CUSTOMERS_MINIMAL + (_CUSTOMERS_FULL if full else ()),
        ),
        "orders": Table(
            "orders",
            "Order",
            (Column("id", "Int", False), Column("customer_id", "Int", True))
            + tuple(Column(column, types[column], True) for column in fields),
            tuple(row[:2] + tuple(row[i] for i in keep) for row in orders),
        ),
        "payments": Table(
            "payments",
            "Payment",
            (
                Column("id", "Int", False),
                Column("customer_id", "Int", True),
                Column("v", "Int", True),
            ),
            _PAYMENTS_MINIMAL + (_PAYMENTS_FULL if full else ()),
        ),
    }


def _program_specs(leaves: tuple[str, ...]) -> list[tuple[str, Collect | Unnest]]:
    # Collected `orders` rows carry their non-null id beside the leaves; the
    # hidden-key let (C5) and Unnest rows carry only the leaves.
    leaves_only = child_fields(leaves)
    child = ("id", *leaves_only)
    by_id = (("id", False),)
    recent = Let("recent", "orders", child, by_id)
    specs: list[tuple[str, Collect | Unnest]] = [
        ("C1_closed", Collect((Let("all_orders", "orders", child, by_id, False),))),
        ("C2_captured", Collect((recent,))),
        (
            "C3_topk",
            Collect((Let("recent", "orders", child, (("id", True),), limit=2),)),
        ),
        (
            "C4_ties",
            Collect((Let("recent", "orders", child, (("k", True),), limit=2),)),
        ),
    ]
    hidden = tuple(field for field in leaves_only if field != "k")
    for suffix, descending in (("asc", False), ("desc", True)):
        let = Let("recent", "orders", hidden, (("k", descending),))
        specs.append((f"C5_hidden_nullable_key_{suffix}", Collect((let,))))
    paid = Let("paid", "payments", ("v",), by_id)
    specs.append(("C6_siblings", Collect((recent, paid))))
    specs.append(("C7_parent_order_limit", Collect((recent,), by_id, 3)))
    if "Text" in leaves:
        specs.append(
            ("C8_text_quoting", Collect((Let("notes", "orders", ("note",), by_id),)))
        )
    if "Bool" in leaves:
        flags = Let("flags", "orders", ("flag",), (("flag", False),), False, None, True)
        specs.append(("C9_distinct_let", Collect((flags,))))
    counts = Let(
        "counts",
        "orders",
        ("customer_id",),
        (("customer_id", False),),
        False,
        group="customer_id",
    )
    specs.append(("C10_grouped_let", Collect((counts,))))
    unnests = (
        ("U1_cross", "cross", None, False),
        ("U2_inner_true", "inner", "True", False),
        ("U3_inner_v_gt_10", "inner", "o.v > 10", False),
        ("U4_left_true", "left", "True", False),
        ("U5_left_v_gt_10", "left", "o.v > 10", False),
        ("U6_left_true_where_v_gt_10", "left", "True", True),
    )
    for name, join, on, where in unnests:
        specs.append((name, Unnest(join, on, where, False, leaves_only)))
    for name, join, on in (
        ("M1_lateral_cross", "cross", None),
        ("M2_lateral_inner_true", "inner", "True"),
        ("M3_lateral_left_true", "left", "True"),
    ):
        specs.append((name, Unnest(join, on, False, True, leaves_only)))
    return specs


TWINS = {
    "U1_cross": "M1_lateral_cross",
    "U2_inner_true": "M2_lateral_inner_true",
    "U4_left_true": "M3_lateral_left_true",
}


def programs(leaves: tuple[str, ...] = DEFAULT_LEAVES) -> tuple[Program, ...]:
    leaves = leaves_of(leaves)
    twins = {**TWINS, **{b: a for a, b in TWINS.items()}}
    header = _header(seed("FULL", leaves))
    return tuple(
        Program(
            name,
            spec,
            (("pietto.toml", CONFIG), ("main.pietto", header + _render(spec))),
            twin=twins.get(name),
        )
        for name, spec in _program_specs(leaves)
    )


def program(name: str, leaves: tuple[str, ...] = DEFAULT_LEAVES) -> Program:
    for item in programs(leaves):
        if item.name == name:
            return item
    raise ValueError(f"unknown program {name}")


def _header(tables: dict[str, Table]) -> str:
    lines = []
    for table in tables.values():
        lines.append(f"shape {table.shape}:")
        lines += [f"    {column.name}: {column.spelling()}" for column in table.columns]
    for table in tables.values():
        lines.append(
            f'source {table.name}: {table.shape} = postgres.table("{table.name}")'
        )
    return "\n".join(lines) + "\n"


def _order_text(order: tuple[tuple[str, bool], ...]) -> str:
    return ", ".join(
        name + (" desc" if descending else "") for name, descending in order
    )


def _render_let(let: Let) -> list[str]:
    lines = [f"    let {let.name}:"]
    if let.captured:
        lines.append("        capture customers")
    lines.append(f"        from {let.table}")
    if let.captured:
        lines.append(f"        where {let.table}.customer_id == customers.id")
    if let.group is not None:
        lines.append(f"        group by {let.group}")
    lines.append("        select distinct:" if let.distinct else "        select:")
    lines += [f"            {name}" for name in let.select]
    if let.group is not None:
        lines.append("            n = count()")
    if let.order:
        lines.append(f"        order by {_order_text(let.order)}")
    if let.limit is not None:
        lines.append(f"        limit {let.limit}")
    return lines


def _render(spec: Collect | Unnest) -> str:
    if isinstance(spec, Collect):
        lines = ["query result:"]
        for let in spec.lets:
            lines += _render_let(let)
        lines += ["    from customers", "    select:", "        id"]
        lines += [f"        {let.name} = collect {let.name}" for let in spec.lets]
        if spec.order:
            lines.append(f"    order by {_order_text(spec.order)}")
        if spec.limit is not None:
            lines.append(f"    limit {spec.limit}")
        return "\n".join(lines) + "\n"
    recent = Let(
        "recent", "orders", spec.fields, (("id", False),) if not spec.lateral else ()
    )
    if spec.lateral:
        lines = ["query result:", *_render_let(recent), "    from customers"]
        lines.append("    let o = recent")
    else:
        lines = ["query with_orders:", *_render_let(recent), "    from customers"]
        lines += ["    select:", "        id", "        recent = collect recent"]
        lines += ["query result:", "    from with_orders"]
        lines.append("    let o = unnest(with_orders.recent)")
    lines.append(
        f"    {spec.join} join o" + ("" if spec.on is None else f" on {spec.on}")
    )
    if spec.where:
        lines.append("    where o.v > 10")
    lines += ["    select:", "        id"]
    lines += [f"        {name} = o.{name}" for name in spec.fields]
    return "\n".join(lines) + "\n"


# Evaluation -----------------------------------------------------------------


def _compare(order: tuple[tuple[str, bool], ...]):
    def compare(left: dict[str, Any], right: dict[str, Any]) -> int:
        for name, descending in order:
            a, b = left[name], right[name]
            if a is None and b is None:
                continue
            if a is None:
                return -1 if descending else 1
            if b is None:
                return 1 if descending else -1
            result = (a > b) - (a < b)
            if result:
                return -result if descending else result
        return 0

    return compare


def _check_keys(order: tuple[tuple[str, bool], ...], kinds: dict[str, str]) -> None:
    for name, _ in order:
        if kinds.get(name) not in ORDERABLE:
            raise ValueError(
                f"order key {name} is not an admitted Int/Bool/Decimal key"
            )


def _segments(
    rows: list[dict[str, Any]],
    order: tuple[tuple[str, bool], ...],
    limit: int | None,
    kinds: dict[str, str],
    project,
) -> tuple[Segment, ...]:
    _check_keys(order, kinds)
    remaining = len(rows) if limit is None else limit
    groups: list[list[dict[str, Any]]] = []
    if not order:
        groups = [rows] if rows else []
    else:
        compare = _compare(order)
        ordered = sorted(rows, key=cmp_to_key(compare))
        for row in ordered:
            if groups and compare(groups[-1][0], row) == 0:
                groups[-1].append(row)
            else:
                groups.append([row])
    result = []
    for group in groups:
        if remaining <= 0:
            break
        take = min(remaining, len(group))
        result.append(Segment(tuple(project(row) for row in group), take))
        remaining -= take
    return tuple(result)


def _key(value: Any) -> str:
    return json.dumps(encode(value), sort_keys=True, ensure_ascii=False)


def _let_value(let: Let, parent: dict[str, Any], tables: dict[str, Table]) -> Nested:
    if not let.order:
        raise ValueError(f"collect-read let {let.name} has no order by")
    table = tables[let.table]
    rows = table.records()
    if let.captured:
        rows = [
            row
            for row in rows
            if row["customer_id"] is not None
            and parent["id"] is not None
            and row["customer_id"] == parent["id"]
        ]
    kinds = {column.name: column.kind for column in table.columns}
    if let.group is not None:
        counts: dict[str, list[Any]] = {}
        for row in rows:
            counts.setdefault(_key(row[let.group]), [row[let.group], 0])[1] += 1
        rows = [{let.group: value, "n": n} for value, n in counts.values()]
        kinds = {let.group: kinds[let.group], "n": "Int"}
        select = (*let.select, "n")
    else:
        select = let.select
    if let.distinct:
        unique = {_key([row[name] for name in select]): row for row in rows}
        rows = list(unique.values())
        kinds = {name: kinds[name] for name in select}
    return Nested(
        _segments(
            rows,
            let.order,
            let.limit,
            kinds,
            lambda row: {name: row[name] for name in select},
        )
    )


def evaluate(spec: Collect | Unnest, tables: dict[str, Table]) -> tuple[Segment, ...]:
    customers = tables["customers"]
    parents = customers.records()
    if isinstance(spec, Collect):

        def project(parent: dict[str, Any]) -> dict[str, Any]:
            row: dict[str, Any] = {"id": parent["id"]}
            for let in spec.lets:
                row[let.name] = _let_value(let, parent, tables)
            return row

        kinds = {column.name: column.kind for column in customers.columns}
        return _segments(parents, spec.order, spec.limit, kinds, project)
    output = []
    for parent in parents:
        children = [
            {name: row[name] for name in spec.fields}
            for row in tables["orders"].records()
            if row["customer_id"] is not None
            and parent["id"] is not None
            and row["customer_id"] == parent["id"]
        ]
        matched = [row for row in children if spec.on is None or _ON[spec.on](row)]
        if spec.join == "left" and not matched:
            matched = [dict.fromkeys(spec.fields)]
        for child in matched:
            row = {"id": parent["id"], **child}
            if not spec.where or _greater_than_ten(row["v"]):
                output.append(row)
    return (Segment(tuple(output), len(output)),) if output else ()


def _greater_than_ten(value: Any) -> bool:
    return value is not None and value > 10


# The only Unnest spellings evaluated: (join, ON absent) pairs and ON texts.
_JOINS = frozenset({("cross", True), ("inner", False), ("left", False)})
_ON = {
    "True": lambda row: True,
    "False": lambda row: False,
    "o.v > 10": lambda row: _greater_than_ten(row["v"]),
}


def expected(
    name: str, set_name: str, leaves: tuple[str, ...] = DEFAULT_LEAVES
) -> tuple[Segment, ...]:
    return evaluate(program(name, leaves).spec, seed(set_name, leaves))


# Typed encoding and comparison --------------------------------------------


def leaf(value: Any) -> dict[str, Any]:
    """Type-exact leaf identity (True/1, 1/1.0, Decimal scale, signed zero)."""
    if type(value) is date:
        return {"kind": "date", "value": value.isoformat()}
    return scalar(value)


def encode(value: Any) -> Any:
    if isinstance(value, Nested):
        return {"kind": "nested", "segments": [encode(item) for item in value.segments]}
    if isinstance(value, Segment):
        return {"take": value.take, "candidates": [encode(c) for c in value.candidates]}
    if type(value) is list or type(value) is tuple:
        return {"kind": "list", "items": [encode(item) for item in value]}
    if type(value) is dict:
        return {"kind": "record", "fields": [[k, encode(v)] for k, v in value.items()]}
    return leaf(value)


def _same_leaf(found: Any, want: Any) -> bool:
    try:
        return leaf(found) == leaf(want)
    except ValueError:
        return False


def _matches(found: Any, want: Any) -> bool:
    if isinstance(want, Nested):
        return type(found) is list and _sequence(found, want.segments) is None
    if type(want) is dict:
        # Field order is the contract's child-ordinal order, not a key set.
        return (
            type(found) is dict
            and list(found) == list(want)
            and all(_matches(found[name], want[name]) for name in want)
        )
    return _same_leaf(found, want)


def _assign(found: list[Any], candidates: tuple[Any, ...]) -> bool:
    """Bipartite matching: every found row gets its own matching candidate."""
    edges = [
        [j for j, want in enumerate(candidates) if _matches(f, want)] for f in found
    ]
    owner: dict[int, int] = {}

    def augment(i: int, seen: set[int]) -> bool:
        for j in edges[i]:
            if j not in seen:
                seen.add(j)
                if j not in owner or augment(owner[j], seen):
                    owner[j] = i
                    return True
        return False

    return all(augment(i, set()) for i in range(len(found)))


def _sequence(found: list[Any], segments: tuple[Segment, ...]) -> str | None:
    position = 0
    for index, segment in enumerate(segments):
        chunk = found[position : position + segment.take]
        if len(chunk) < segment.take:
            return f"group {index}: expected {segment.take} rows, found {len(chunk)}"
        if not _assign(chunk, segment.candidates):
            return f"group {index}: rows {position}..{position + segment.take - 1} have no valid assignment"
        position += segment.take
    if position != len(found):
        return f"expected {position} rows, found {len(found)}"
    return None


def check(found_rows: Any, expected_rows: tuple[Segment, ...]) -> list[str]:
    """Empty when found rows satisfy the expectation; otherwise the reasons."""
    if type(found_rows) is not list:
        return ["rows: not a list"]
    reason = _sequence(found_rows, expected_rows)
    if reason is None:
        return []
    reasons = [f"rows: {reason}"]
    flat = [candidate for segment in expected_rows for candidate in segment.candidates]
    if len(flat) == len(found_rows) and all(type(row) is dict for row in found_rows):
        for index, (row, want) in enumerate(zip(found_rows, flat, strict=True)):
            if type(want) is dict:
                for name in sorted(set(row) | set(want)):
                    if name not in row or name not in want:
                        reasons.append(f"rows[{index}].{name}: label differs")
                    elif not _matches(row[name], want[name]):
                        reasons.append(f"rows[{index}].{name}: value differs")
                if set(row) == set(want) and list(row) != list(want):
                    reasons.append(f"rows[{index}]: field order differs")
    return reasons


def example(segments: tuple[Segment, ...]) -> list[Any]:
    """One concrete realization: the first ``take`` candidates of every group."""
    return [
        _realize(candidate)
        for segment in segments
        for candidate in segment.candidates[: segment.take]
    ]


def _realize(value: Any) -> Any:
    if isinstance(value, Nested):
        return example(value.segments)
    if type(value) is dict:
        return {name: _realize(item) for name, item in value.items()}
    return value


# Damage controls ---------------------------------------------------------


def _leaves_in(rows: list[dict[str, Any]]):
    """Yield (container, key) for every scalar leaf, parents first."""
    for row in rows:
        for name, value in row.items():
            if type(value) is list:
                for child in value:
                    for child_name in child:
                        yield child, child_name
            else:
                yield row, name


def _copy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            name: [dict(child) for child in value] if type(value) is list else value
            for name, value in row.items()
        }
        for row in rows
    ]


def _replace_first(rows, accept, change):
    damaged = _copy(rows)
    for container, name in _leaves_in(damaged):
        if accept(container[name]):
            container[name] = change(container[name])
            return damaged
    return None


def _finer_scale(value: Decimal) -> Decimal:
    exponent = value.as_tuple().exponent
    if type(exponent) is not int:
        raise ValueError("finite Decimal required")
    return value.quantize(Decimal(1).scaleb(exponent - 1))


def damages(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Named single-fault copies of realized rows; inapplicable ones are absent."""
    found: dict[str, Any] = {
        "bool_as_int": _replace_first(rows, lambda v: type(v) is bool, int),
        "int_as_float": _replace_first(rows, lambda v: type(v) is int, float),
        "decimal_scale": _replace_first(
            rows,
            lambda v: type(v) is Decimal,
            _finer_scale,
        ),
        "signed_zero": _replace_first(
            rows,
            lambda v: type(v) is float and v == 0,
            lambda v: -v if math.copysign(1, v) > 0 else 0.0,
        ),
        "empty_text_as_null": _replace_first(rows, lambda v: v == "", lambda v: None),
    }
    damaged = _copy(rows)
    for row in damaged:
        hit = next((n for n, v in row.items() if type(v) is list and not v), None)
        if hit is not None:
            row[hit] = None
            found["empty_collection_as_null"] = damaged
            break
    damaged = _copy(rows)
    for row in damaged:
        for name, value in row.items():
            if type(value) is list:
                nulls = [c for c in value if all(x is None for x in c.values())]
                if nulls:
                    value.remove(nulls[0])
                    found["all_null_record_dropped"] = damaged
                    break
        if "all_null_record_dropped" in found:
            break
    found["same_type_swap"] = _swap(rows)
    found["child_moved"] = _move(rows)
    # Field order is part of the contract (child-ordinal order): the same
    # labelled values in reversed order are a different record.
    if rows and len(rows[0]) > 1:
        damaged = _copy(rows)
        damaged[0] = dict(reversed(list(damaged[0].items())))
        found["parent_fields_reordered"] = damaged
    damaged = _copy(rows)
    for row in damaged:
        hit = next(
            (v for v in row.values() if type(v) is list and v and len(v[0]) > 1),
            None,
        )
        if hit is not None:
            hit[0] = dict(reversed(list(hit[0].items())))
            found["child_fields_reordered"] = damaged
            break
    for i, row in enumerate(rows):
        if any(_key(row) == _key(other) for other in rows[i + 1 :]):
            found["duplicate_parent_dropped"] = _copy(rows[:i] + rows[i + 1 :])
            break
    return {name: value for name, value in found.items() if value is not None}


def _kind(value: Any) -> str | None:
    return None if value is None else leaf(value)["kind"]


def _swap(rows):
    for name in rows[0] if rows else ():
        children = [c for row in rows if type(row[name]) is list for c in row[name]]
        labels = list(children[0]) if children else []
        for i, a in enumerate(labels):
            for b in labels[i + 1 :]:
                kinds = {_kind(c[a]) for c in children} | {
                    _kind(c[b]) for c in children
                }
                if len(kinds - {None}) == 1 and any(c[a] != c[b] for c in children):
                    damaged = _copy(rows)
                    for row in damaged:
                        for child in row[name] or ():
                            child[a], child[b] = child[b], child[a]
                    return damaged
    return None


def _move(rows):
    for i, row in enumerate(rows):
        for name, value in row.items():
            if type(value) is list and value:
                scalars = {n: v for n, v in row.items() if type(v) is not list}
                for j, other in enumerate(rows):
                    other_scalars = {
                        n: v for n, v in other.items() if type(v) is not list
                    }
                    if (
                        _key(scalars) != _key(other_scalars)
                        and type(other[name]) is list
                    ):
                        damaged = _copy(rows)
                        damaged[j][name].append(damaged[i][name].pop(0))
                        return damaged
    return None


def document(set_name: str, leaves: tuple[str, ...] = DEFAULT_LEAVES) -> bytes:
    """Canonical bytes of one seed set, its programs and their expectations."""
    tables = seed(set_name, leaves)
    body = {
        "set": set_name,
        "leaves": list(leaves_of(leaves)),
        "tables": {
            name: {
                "columns": [[c.name, c.type, c.nullable] for c in table.columns],
                "rows": [[leaf(value) for value in row] for row in table.rows],
            }
            for name, table in tables.items()
        },
        "programs": [
            {
                "name": item.name,
                "files": [list(pair) for pair in item.files],
                "result": item.result,
                "twin": item.twin,
                "expected": [encode(s) for s in evaluate(item.spec, tables)],
            }
            for item in programs(leaves)
        ],
    }
    return json.dumps(
        body, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
