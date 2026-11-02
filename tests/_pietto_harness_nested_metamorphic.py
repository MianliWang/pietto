"""Oracle-free metamorphic laws over nested Collect and Unnest results.

Laws read actual rows in the neutral ``to_pylist()`` model (rows are lists of
dicts, a nested field is a list of dicts, leaves are typed Python values) plus
program and data-set metadata, never an expected value. Each law states its
premise and answers HOLDS, VIOLATED or NOT_APPLICABLE; malformed rows answer
VIOLATED, never an exception. Rules:
- parents pair by the bag of their key: duplicate parents sum;
- a LEFT placeholder is recognized by count, never by all-None fields;
- Unnest output compares as a bag, a container by tie group, and parents as a
  sequence only under an outer ``order by``;
- leaves compare type-exactly, and comparisons across executions ignore ties.

The corpus is enumerated, seeded and bounded, not fuzzed: the tools program
family plus twins, Top-K and tie variants, ON False and Unnest over a Top-K
producer, on MINIMAL, FULL and data sets drawn from the FULL value palette.
Expected values come from the tools typed-literal oracle only; Unnest over a
collected let is composed from its Collect expectation and fails closed when a
LIMIT boundary splits a tie group.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from functools import cache
import itertools
import json
import math
import random
import struct
from typing import Any, NamedTuple
from uuid import UUID

import _pietto_execution_nested_oracle as oracle
from _pietto_execution_nested_oracle import Collect, Let, Segment, Table, Unnest

HOLDS, VIOLATED, NOT_APPLICABLE = "HOLDS", "VIOLATED", "NOT_APPLICABLE"
DEFAULT_LEAVES = oracle.DEFAULT_LEAVES
# Flat LATERAL Timestamp/UUID projection remains refused; its twin uses the
# existing three-leaf domain, while actual Collect/Unnest covers all eight.
NATIVE_LEAVES = {"nested": oracle.LEAVES, "lateral": oracle.DEFAULT_LEAVES}
NATIVE_PROGRAMS = {
    "nested": (
        "C1_closed",
        "C2_captured",
        "C3_topk",
        "C5_hidden_nullable_key_asc",
        "C6_siblings",
        "C7_parent_order_limit",
        "G_captured_id_1",
        "G_captured_id_2",
        "G_captured_id_desc_all",
        "G_captured_k_all",
        "G_inner_false",
        "G_left_false",
        "G_paid",
        "G_strip",
        "G_strip_id",
        "G_strip_id_3",
        "U1_cross",
        "U2_inner_true",
        "U3_inner_v_gt_10",
        "U4_left_true",
        "U5_left_v_gt_10",
        "U6_left_true_where_v_gt_10",
    ),
    "lateral": ("U1_cross", "M1_lateral_cross"),
}
NATIVE_DATASETS = ("MINIMAL", "FULL")
_BY_ID = (("id", False),)
_ORDERS = {
    "id": _BY_ID,
    "id_desc": (("id", True),),
    "k_desc": (("k", True),),
    "v_id": (("v", False), ("id", False)),
    "flag": (("flag", False),),
}
# Every data set keeps these ids unique, so an order on them never ties.
_UNIQUE = {"orders": "id", "payments": "id"}
# customers, orders and payments rows of each seeded data set.
_SEEDED = ((0, 6, 3), (5, 0, 0), (6, 12, 4), (8, 16, 6), (4, 10, 2), (7, 14, 5))
_PYTHON = {
    "Int": int,
    "Bool": bool,
    "Text": str,
    "Float": float,
    "Decimal": Decimal,
    "Date": date,
    "Timestamp": datetime,
    "UUID": UUID,
}
# Three-valued ON predicates over one child row: only TRUE matches.
_PREDICATES: dict[str, Callable[[dict[str, Any]], bool]] = {
    "True": lambda child: True,
    "False": lambda child: False,
    "o.v > 10": lambda child: child["v"] is not None and child["v"] > 10,
}
_READS = {"True": (), "False": (), "o.v > 10": ("v",)}
_CROSS = ("cross", None, False)
_PAIR = "needs two single-let Collects with the same parent clause"
_HIDDEN_KEY = "an order key is not a child field"
_NO_REFERENCE = "a LIMIT boundary tie cannot be excluded without an unlimited reference"
# Damages only the typed-literal oracle sees. Metamorphic laws compare relation
# meaning, while this owner checks parent and child field layout exactly.
ORACLE_ONLY = {
    "child_fields_reordered": "child field layout is a typed-literal oracle check",
    "parent_fields_reordered": "parent field layout is a typed-literal oracle check",
}

Specs = tuple[Any, ...]
Rows = tuple[list[Any], ...]


class Verdict(NamedTuple):
    value: str
    reason: str


@dataclass(frozen=True)
class Flatten:
    """Unnest of one collected let: two-stage over its Collect, or LATERAL."""

    let: Let
    join: str
    lateral: bool

    def __post_init__(self) -> None:
        if self.join not in ("cross", "left") or "id" in self.let.select:
            raise ValueError("Flatten models CROSS or LEFT ON True over non-id fields")


Spec = Collect | Unnest | Flatten


@dataclass(frozen=True)
class Member:
    name: str
    spec: Spec
    files: tuple[tuple[str, str], ...]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Dataset:
    name: str
    seed: str | None
    tables: dict[str, Table]


@dataclass(frozen=True)
class Instance:
    law: str
    programs: tuple[str, ...]
    field: str = ""


@dataclass(frozen=True)
class Law:
    id: str
    family: str
    premise: str
    arity: range
    fit: Callable[[Specs, str], str | None]
    check: Callable[[Specs, Rows, str], str | None]


# Corpus and data sets -------------------------------------------------------


def _render(spec: Spec) -> str:
    if not isinstance(spec, Flatten):
        return oracle._render(spec)
    name, let = spec.let.name, spec.let
    if spec.lateral and let.limit is None:
        let = replace(let, order=())  # a joined let without LIMIT needs no order
    lines = ["query with_orders:", *oracle._render_let(let), "    from customers"]
    if spec.lateral:
        lines = ["query result:", *lines[1:], f"    let o = {name}"]
    else:
        lines += ["    select:", "        id", f"        {name} = collect {name}"]
        lines += ["query result:", "    from with_orders"]
        lines.append(f"    let o = unnest(with_orders.{name})")
    lines.append(
        f"    {spec.join} join o" + (" on True" if spec.join == "left" else "")
    )
    lines += ["    select:", "        id"]
    lines += [f"        {field} = o.{field}" for field in _fields(spec.let)]
    return "\n".join(lines) + "\n"


@cache
def _corpus(leaves: tuple[str, ...]) -> tuple[Member, ...]:
    fields = oracle.child_fields(leaves)
    child = ("id", *fields)
    chosen: dict[Spec, tuple[str, tuple[str, ...]]] = {
        item.spec: (item.name, ("tools",)) for item in oracle.programs(leaves)
    }

    def add(name: str, spec: Spec, tag: str) -> None:
        chosen.setdefault(spec, (name, ("grid", tag)))

    orders = {
        label: order
        for label, order in _ORDERS.items()
        if all(key in child for key, _ in order)
    }
    for (label, order), limit in itertools.product(orders.items(), (None, 1, 2)):
        size = "all" if limit is None else str(limit)
        recent = Let("recent", "orders", child, order, True, limit)
        add(f"G_captured_{label}_{size}", Collect((recent,)), "captured")
        if limit is not None:
            lateral = Flatten(replace(recent, select=fields), "cross", True)
            add(f"G_lateral_{label}_{size}", lateral, "lateral-twin")
        if label in ("id", "k_desc"):
            closed = Let("all_orders", "orders", child, order, False, limit)
            add(f"G_closed_{label}_{size}", Collect((closed,)), "closed")
    k_asc = Let("recent", "orders", child, (("k", False),))
    add("G_captured_k_all", Collect((k_asc,)), "hidden-twin")
    add("G_paid", Collect((Let("paid", "payments", ("v",), _BY_ID),)), "sibling")
    # Visible-id twins of the lets ordered by a hidden unique id.
    add(
        "G_paid_id",
        Collect((Let("paid", "payments", ("id", "v"), _BY_ID),)),
        "hidden-twin",
    )
    if "note" in fields:
        notes = Let("notes", "orders", ("id", "note"), _BY_ID)
        add("G_notes_id", Collect((notes,)), "hidden-twin")
    for name, order, limit in (
        ("G_strip", (), None),
        ("G_strip_id", _BY_ID, None),
        ("G_strip_id_2", _BY_ID, 2),
        ("G_strip_id_3", _BY_ID, 3),
    ):
        add(name, Collect((), order, limit), "strip")
    recent = Let("recent", "orders", child, _BY_ID)
    for limit in (None, 2):
        name = "G_parent_id_" + ("all" if limit is None else str(limit))
        add(name, Collect((recent,), _BY_ID, limit), "parent-order")
    for join in ("inner", "left"):
        add(f"G_{join}_false", Unnest(join, "False", False, False, fields), "on-false")
    for label, join in (("id_desc", "cross"), ("id_desc", "left"), ("k_desc", "cross")):
        let = Let("recent", "orders", fields, _ORDERS[label], True, 2)
        add(f"G_unnest_{label}_2_{join}", Flatten(let, join, False), "topk-unnest")
    # LATERAL twins of the unlimited closed lets: C-COUNT and C-BAG then judge
    # the contents that C-CLOSED only compares between parents.
    for spec in [spec for spec in chosen if isinstance(spec, Collect)]:
        for let in spec.lets:
            if not let.captured and let.limit is None:
                plain = not let.distinct and let.group is None
                body = replace(let, select=fields, order=_BY_ID) if plain else let
                add(
                    f"G_lateral_{let.name}", Flatten(body, "cross", True), "closed-twin"
                )
    header = oracle._header(oracle.seed("FULL", leaves))
    return tuple(
        Member(
            name,
            spec,
            (("pietto.toml", oracle.CONFIG), ("main.pietto", header + _render(spec))),
            tags,
        )
        for spec, (name, tags) in chosen.items()
    )


def corpus(leaves: tuple[str, ...] = DEFAULT_LEAVES) -> tuple[Member, ...]:
    return _corpus(oracle.leaves_of(leaves))


@cache
def _datasets(leaves: tuple[str, ...]) -> tuple[Dataset, ...]:
    """MINIMAL, FULL and seeded draws from the FULL palette of every leaf."""
    found = [Dataset(name, None, oracle.seed(name, leaves)) for name in oracle.SETS]
    palette = oracle.seed("FULL", oracle.LEAVES)
    shape = oracle.seed("FULL", leaves)
    for index, sizes in enumerate(_SEEDED):
        seed = f"pietto-nested-metamorphic-{index}"
        rng = random.Random(seed)
        tables = {}
        for (name, table), size in zip(palette.items(), sizes, strict=True):
            columns = list(zip(*table.rows, strict=True))
            names = [column.name for column in table.columns]
            keep = [names.index(column.name) for column in shape[name].columns]
            rows = []
            for number in range(size):
                drawn = [rng.choice(column) for column in columns]
                if name in _UNIQUE:
                    drawn[0] = 1000 + number
                rows.append(tuple(drawn[i] for i in keep))
            tables[name] = replace(shape[name], rows=tuple(rows))
        found.append(Dataset(f"SEEDED_{index}", seed, tables))
    return tuple(found)


def datasets(leaves: tuple[str, ...] = DEFAULT_LEAVES) -> tuple[Dataset, ...]:
    return _datasets(oracle.leaves_of(leaves))


def _flatten(
    spec: Flatten, parents: list[tuple[Any, list[Any]]]
) -> list[dict[str, Any]]:
    rows = []
    for parent, children in parents:
        if not children and spec.join == "left":
            children = [dict.fromkeys(_fields(spec.let))]
        rows += [{"id": parent, **child} for child in children]
    return rows


def expected(member: Member, tables: dict[str, Table]) -> tuple[Segment, ...]:
    """Tools oracle expectation; Unnest over a collected let is composed."""
    spec = member.spec
    if not isinstance(spec, Flatten):
        return oracle.evaluate(spec, tables)
    parents = []
    for segment in oracle.evaluate(Collect((spec.let,)), tables):
        for parent in segment.candidates:
            groups = parent[spec.let.name].segments
            if any(group.take != len(group.candidates) for group in groups):
                raise ValueError(
                    "a LIMIT boundary splits a tie group of the collected let"
                )
            parents.append((parent["id"], [c for g in groups for c in g.candidates]))
    rows = _flatten(spec, parents)
    return (Segment(tuple(rows), len(rows)),) if rows else ()


def _one(candidate: Any) -> Any:
    return oracle.example((Segment((candidate,), 1),))[0]


def _repicks(segments: tuple[Segment, ...]) -> Iterator[list[Any]]:
    """The oracle example, then each distinct realization that re-picks one
    tie group.

    A group of at most four candidates yields every ordered pick of the right
    size; a larger group yields its reversed and its rotated pick. Equal nested
    values (closed lets, duplicate parents) are re-picked once.
    """
    base = oracle.example(segments)
    yield base
    # repr separates every pair of values that tools ``leaf`` separates.
    seen, nested = {repr(base)}, set()
    start = 0
    for segment in segments:
        options = segment.candidates
        picks = (
            itertools.permutations(options, segment.take)
            if len(options) <= 4
            else (
                options[::-1][: segment.take],
                (options[1:] + options[:1])[: segment.take],
            )
        )
        end = start + segment.take
        found = [[*base[:start], *map(_one, pick), *base[end:]] for pick in picks]
        for offset, candidate in enumerate(segment.candidates[: segment.take]):
            at = start + offset
            for name, value in candidate.items() if type(candidate) is dict else ():
                if isinstance(value, oracle.Nested) and repr(value) not in nested:
                    nested.add(repr(value))
                    for inner in itertools.islice(_repicks(value.segments), 1, None):
                        found.append(
                            [*base[:at], {**base[at], name: inner}, *base[at + 1 :]]
                        )
        for rows in found:
            if (key := repr(rows)) not in seen:
                seen.add(key)
                yield rows
        start = end


def realizations(
    member: Member, tables: dict[str, Table]
) -> Iterator[list[dict[str, Any]]]:
    """Valid result rows: the oracle example first, then tie-group re-picks."""
    spec = member.spec
    if not isinstance(spec, Flatten):
        return _repicks(expected(member, tables))
    producer = oracle.evaluate(Collect((spec.let,)), tables)
    return (
        _flatten(spec, [(row["id"], row[spec.let.name]) for row in rows])
        for rows in _repicks(producer)
    )


@cache
def _realized(leaves: tuple[str, ...]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    return {
        (member.name, dataset.name): next(realizations(member, dataset.tables))
        for dataset in _datasets(leaves)
        for member in _corpus(leaves)
    }


def realized(
    leaves: tuple[str, ...] = DEFAULT_LEAVES,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Oracle example rows for every corpus member on every data set.

    The rows are shared between callers: copy before changing them.
    """
    return _realized(oracle.leaves_of(leaves))


# Rows and program metadata --------------------------------------------------


def _leaf(kind: type, text: str, value: Any) -> tuple[Any, ...]:
    """Local, type-exact leaf identity for metamorphic comparisons."""
    if type(value) is not kind:
        raise TypeError("leaf type changed")
    if kind is type(None):
        return ("none",)
    if kind is bool:
        return ("bool", value)
    if kind is int:
        return ("int", value)
    if kind is str:
        return ("text", value)
    if kind is float:
        if not math.isfinite(value):
            raise ValueError("non-finite Float")
        return ("float", struct.pack("!d", value).hex())
    if kind is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal")
        decimal = value.as_tuple()
        return ("decimal", decimal.sign, decimal.digits, decimal.exponent)
    if kind is datetime:
        return ("timestamp", value.isoformat(timespec="microseconds"), value.fold)
    if kind is date:
        return ("date", value.isoformat())
    if kind is UUID:
        return ("uuid", value.hex)
    raise TypeError(f"unsupported leaf type {kind.__name__}: {text}")


def _k(values: Any) -> tuple[Any, ...]:
    """Type-exact, sortable identity independent of the typed-literal oracle."""
    return tuple(_leaf(type(value), repr(value), value) for value in values)


def _canonical(value: Any) -> tuple[Any, ...]:
    """Local recursive comparison form used only by metamorphic helpers."""
    if type(value) is list:
        return ("list", tuple(_canonical(item) for item in value))
    if type(value) is tuple:
        return ("tuple", tuple(_canonical(item) for item in value))
    if type(value) is dict:
        return (
            "dict",
            tuple((key, _canonical(item)) for key, item in value.items()),
        )
    return _leaf(type(value), repr(value), value)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _items(container: Any) -> list[Any]:
    _require(type(container) is list, "a container is not a list")
    return container


def _bag(rows: list[Any], fields: tuple[str, ...]) -> Counter[Any]:
    return Counter(_k(row[field] for field in fields) for row in rows)


def _paired(a: list[Any], b: list[Any], field: str) -> list[tuple[Any, Any, Any]]:
    """Every container pair of equal parent keys; occurrence counts must agree."""
    left: dict[Any, list[Any]] = {}
    right: dict[Any, list[Any]] = {}
    for rows, found in ((a, left), (b, right)):
        for row in rows:
            found.setdefault(_k([row["id"]]), []).append(row[field])
    counts = {key: len(value) for key, value in left.items()}
    _require(
        counts == {key: len(value) for key, value in right.items()},
        "parent keys differ",
    )
    return [(key, x, y) for key, xs in left.items() for x in xs for y in right[key]]


def _compare(order: tuple[tuple[str, bool], ...]) -> Callable[[Any, Any], int]:
    """PostgreSQL order: NULL last ascending, first descending."""

    def compare(a: Any, b: Any) -> int:
        for name, descending in order:
            x, y = a[name], b[name]
            if x is None or y is None:
                result = (x is None) - (y is None)
            else:
                result = (x > y) - (x < y)
            if result:
                return -result if descending else result
        return 0

    return compare


def _in_order(rows: list[Any], order: tuple[tuple[str, bool], ...]) -> bool:
    compare = _compare(order)
    return all(compare(a, b) <= 0 for a, b in itertools.pairwise(_items(rows)))


def _groups(
    rows: list[Any], order: tuple[tuple[str, bool], ...], select: tuple[str, ...]
) -> list[list[Any]]:
    """Consecutive tie groups; one group when an order key is not selected."""
    keys = [name for name, _ in order]
    visible = set(keys) <= set(select)
    groups: list[list[Any]] = []
    last = None
    for row in _items(rows):
        key = _k(row[name] for name in keys) if visible else ()
        if not groups or key != last:
            groups.append([])
        groups[-1].append(row)
        last = key
    return groups


def _canon(
    rows: list[Any], order: tuple[tuple[str, bool], ...], select: tuple[str, ...]
) -> tuple[Any, ...]:
    return tuple(
        tuple(sorted(_bag(group, select).items()))
        for group in _groups(rows, order, select)
    )


def _fields(let: Let) -> tuple[str, ...]:
    return (*let.select, "n") if let.group is not None else let.select


def _canon_let(container: Any, let: Let) -> tuple[Any, ...]:
    return _canon(container, let.order, _fields(let))


def _keys(owner: Any) -> set[str]:
    return {name for name, _ in owner.order}


def _clause(spec: Any) -> tuple[Any, ...] | None:
    return (spec.order, spec.limit) if isinstance(spec, Collect) else None


def _let(spec: Any, field: str) -> Let | None:
    if isinstance(spec, Collect):
        return next((let for let in spec.lets if let.name == field), None)
    return None


def _single(spec: Any) -> Let | None:
    return spec.lets[0] if isinstance(spec, Collect) and len(spec.lets) == 1 else None


def _the(spec: Any, field: str = "") -> Let:
    """The let named ``field``, or the only let; a law's fit guarantees it."""
    let = _let(spec, field) if field else _single(spec)
    if let is None:
        raise ValueError("no such let")
    return let


def _producer(spec: Any) -> Let | None:
    """The let an Unnest or Flatten reads."""
    if isinstance(spec, Flatten):
        return spec.let
    if isinstance(spec, Unnest):
        return Let("recent", "orders", spec.fields, () if spec.lateral else _BY_ID)
    return None


def _out(spec: Any) -> tuple[str, ...]:
    return _fields(spec.let) if isinstance(spec, Flatten) else spec.fields


def _join(spec: Any) -> tuple[str, str | None, bool]:
    if isinstance(spec, Flatten):
        return (spec.join, "True" if spec.join == "left" else None, False)
    if isinstance(spec, Unnest):
        return (spec.join, spec.on, spec.where)
    return ("", None, False)


def _form(spec: Any) -> tuple[Any, ...] | None:
    if isinstance(spec, Collect):
        return None
    return (type(spec), _producer(spec), _out(spec), spec.lateral)


def _same_rows(a: Let | None, b: Let | None) -> bool:
    """Both lets yield the same child-row bag up to projection; a DISTINCT or
    grouped let's rows depend on its projection, so only an equal let does."""
    if a is None or b is None:
        return False
    if any(let.group is not None or let.distinct for let in (a, b)):
        return a == b
    same = (a.table, a.captured, a.limit) == (b.table, b.captured, b.limit)
    return same and (a.limit is None or a.order == b.order)


def _reference(let: Let, spec: Any) -> bool:
    """``spec`` collects ``let`` without its LIMIT and with every order key."""
    ref = _single(spec)
    return (
        ref is not None
        and _clause(spec) == ((), None)
        and ref == replace(let, limit=None, select=ref.select)
        and _keys(let) <= set(ref.select)
    )


def _ties(let: Let | None, specs: Specs, rows: Rows, at: int) -> str | None:
    """Why a LIMIT boundary tie is not excluded; None when it is.

    ``specs[at]``, when present, is the unlimited reference whose rows show
    the tie groups at the boundary.
    """
    if let is None:
        return "no collected let"
    if let.limit is None or _UNIQUE.get(let.table) in _keys(let):
        return None
    if len(specs) <= at or not _reference(let, specs[at]):
        return _NO_REFERENCE
    compare, limit = _compare(let.order), let.limit
    for row in rows[at]:
        children = _items(row[let.name])
        if len(children) > limit and compare(children[limit - 1], children[limit]) == 0:
            return "a LIMIT boundary splits a tie group"
    return None


def _kinds(let: Let, tables: dict[str, Table]) -> dict[str, str]:
    kinds = {name: tables[let.table].column(name).kind for name in let.select}
    return {**kinds, "n": "Int"} if let.group is not None else kinds


def _layout(
    spec: Spec, tables: dict[str, Table]
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Scalar and nested child column kinds of one program's rows."""
    scalars = {"id": tables["customers"].column("id").kind}
    if isinstance(spec, Collect):
        return scalars, {let.name: _kinds(let, tables) for let in spec.lets}
    producer = _producer(spec)
    assert producer is not None
    return {**scalars, **_kinds(producer, tables)}, {}


def _typed(value: Any, kind: str) -> bool:
    if value is None:
        return True
    if type(value) is not _PYTHON[kind]:
        return False
    try:
        _leaf(type(value), repr(value), value)
    except (TypeError, ValueError):
        return False
    return True


def _malformed(spec: Spec, rows: Any, tables: dict[str, Table]) -> str | None:
    """Why rows do not fit the program's typed shape. Every container here is
    a direct Collect container, so it is a list."""
    if type(rows) is not list:
        return "rows are not a list"
    scalars, nested = _layout(spec, tables)
    labels = {*scalars, *nested}
    for index, row in enumerate(rows):
        if type(row) is not dict or set(row) != labels:
            return f"row {index} does not have exactly the fields {sorted(labels)}"
        for name, kind in scalars.items():
            if not _typed(row[name], kind):
                return f"row {index}.{name} is not a {kind} leaf"
        for name, kinds in nested.items():
            if type(row[name]) is not list:
                return f"row {index}.{name} is not a list"
            for child in row[name]:
                if type(child) is not dict or set(child) != set(kinds):
                    return f"row {index}.{name} has a child without exactly {sorted(kinds)}"
                for label, kind in kinds.items():
                    if not _typed(child[label], kind):
                        return f"row {index}.{name}.{label} is not a {kind} leaf"
    return None


# Laws -------------------------------------------------------------------------
# A fit says why programs are not an instance of the law. A check returns why
# its premise (its docstring) fails on these rows, None when the relation
# holds, and raises ValueError when it is violated.

LAWS: dict[str, Law] = {}
_FAMILIES = {"C": "collect", "O": "order", "U": "unnest"}


def _law(
    law_id: str,
    fit: Callable[[Specs, str], str | None],
    least: int,
    most: int | None = None,
):
    def register(check: Callable[[Specs, Rows, str], str | None]):
        premise = " ".join((check.__doc__ or "").split())
        arity = range(least, (most or least) + 1)
        LAWS[law_id] = Law(law_id, _FAMILIES[law_id[0]], premise, arity, fit, check)
        return check

    return register


def _fit_parent(specs: Specs, field: str) -> str | None:
    m, s = specs
    if isinstance(m, Collect) and m.lets and isinstance(s, Collect) and not s.lets:
        return None if _clause(m) == _clause(s) else "the parent ORDER or LIMIT differs"
    return "needs a Collect and its parent-only twin"


@_law("C-PARENT", _fit_parent, 2)
def _parent(specs: Specs, rows: Rows, field: str) -> str | None:
    """Same FROM, WHERE, parent ORDER and LIMIT."""
    _require(_bag(rows[0], ("id",)) == _bag(rows[1], ("id",)), "parent bags differ")


def _fit_twin(specs: Specs, field: str) -> str | None:
    let = _let(specs[0], field)
    if let is None:
        return f"no collected let {field}"
    if len(specs) > 1 and _clause(specs[0]) != ((), None):
        return "the Collect has a parent ORDER or LIMIT"
    if len(specs) > 1 and (
        _join(specs[1]) != _CROSS or not _same_rows(let, _producer(specs[1]))
    ):
        return "the second program is not a CROSS Unnest of the same child rows"
    return None


@_law("C-EMPTY", _fit_twin, 1, 2)
def _empty(specs: Specs, rows: Rows, field: str) -> str | None:
    """Direct Collect."""
    first, *twin = rows
    flat = _bag(twin[0], ("id",)) if twin else None
    for row in first:
        bare = flat is not None and not flat[_k([row["id"]])]
        _require(
            _items(row[field]) == [] or not bare,
            "a parent without child rows has children",
        )


@_law("C-COUNT", _fit_twin, 2)
def _count(specs: Specs, rows: Rows, field: str) -> str | None:
    """None."""
    got: Counter[Any] = Counter()
    for row in rows[0]:
        got[_k([row["id"]])] += len(_items(row[field]))
    _require(
        +got == _bag(rows[1], ("id",)),
        "child counts per parent key differ from the flat twin",
    )


@_law("C-BAG", _fit_twin, 2, 3)
def _collected(specs: Specs, rows: Rows, field: str) -> str | None:
    """No LIMIT boundary tie."""
    let = _the(specs[0], field)
    if missing := _ties(let, specs, rows, 2):
        return missing
    names = tuple(name for name in _out(specs[1]) if name in _fields(let))
    got = Counter(
        _k([row["id"], *(child[name] for name in names)])
        for row in rows[0]
        for child in _items(row[field])
    )
    _require(
        got == _bag(rows[1], ("id", *names)), "collected rows differ from the flat twin"
    )


def _fit_dup(specs: Specs, field: str) -> str | None:
    let = _let(specs[0], field)
    if let is None or not let.captured:
        return "needs a captured let"
    if any(_let(s, field) != let and not _reference(let, s) for s in specs[1:]):
        return "a program neither collects the same let nor is its unlimited reference"
    return None


@_law("C-DUP", _fit_dup, 1, 3)
def _dup(specs: Specs, rows: Rows, field: str) -> str | None:
    """Captured let, also across programs collecting it; no LIMIT boundary tie."""
    let = _the(specs[0], field)
    peers = [i for i, spec in enumerate(specs) if _let(spec, field) == let]
    at = next((i for i in range(len(specs)) if i not in peers), len(specs))
    if missing := _ties(let, specs, rows, at):
        return missing
    found: dict[Any, set[Any]] = {}
    for i in peers:
        for row in rows[i]:
            found.setdefault(_k([row["id"]]), set()).add(_canon_let(row[field], let))
    _require(
        all(len(c) == 1 for c in found.values()),
        "one parent key got different containers",
    )


def _fit_closed(specs: Specs, field: str) -> str | None:
    let = _let(specs[0], field)
    return None if let is not None and not let.captured else "needs a closed let"


@_law("C-CLOSED", _fit_closed, 1, 2)
def _closed(specs: Specs, rows: Rows, field: str) -> str | None:
    """Closed let; no LIMIT boundary tie."""
    let = _the(specs[0], field)
    if missing := _ties(let, specs, rows, 1):
        return missing
    canon = {_canon_let(row[field], let) for row in rows[0]}
    _require(len(canon) <= 1, "parents got different closed containers")


def _fit_sibling(specs: Specs, field: str) -> str | None:
    m, *own = specs
    if not isinstance(m, Collect) or len(m.lets) < 2 or len(own) != len(m.lets):
        return "needs a multi-let Collect and one single-let Collect per let"
    if own != [Collect((let,), m.order, m.limit) for let in m.lets]:
        return "a single-let program differs in its let or parent clause"
    return None


@_law("C-SIBLING", _fit_sibling, 3, 8)
def _sibling(specs: Specs, rows: Rows, field: str) -> str | None:
    """Same parent clause; no LIMIT boundary tie."""
    for index, let in enumerate(specs[0].lets, 1):
        if _ties(let, (), (), 0):
            return f"{let.name}: {_NO_REFERENCE}"
        mine, own = (
            Counter((_k([row["id"]]), _canon_let(row[let.name], let)) for row in found)
            for found in (rows[0], rows[index])
        )
        _require(mine == own, f"{let.name} differs from the program collecting only it")


def _fit_sorted(specs: Specs, field: str) -> str | None:
    let = _let(specs[0], field)
    if let is None:
        return f"no collected let {field}"
    return None if _keys(let) <= set(_fields(let)) else _HIDDEN_KEY


@_law("O-SORTED", _fit_sorted, 1)
def _sorted(specs: Specs, rows: Rows, field: str) -> str | None:
    """Every order key is a child field."""
    let = _the(specs[0], field)
    for row in rows[0]:
        _require(
            _in_order(row[field], let.order), f"a {field} container is out of order"
        )


def _pair(specs: Specs) -> tuple[Let, Let] | None:
    a, b = (_single(spec) for spec in specs)
    return (a, b) if a and b and _clause(specs[0]) == _clause(specs[1]) else None


def _fit_hidden(specs: Specs, field: str) -> str | None:
    hidden, visible = _let(specs[0], field), _single(specs[1])
    if not hidden or not visible or _clause(specs[0]) != _clause(specs[1]):
        return "needs a collected let and a single-let twin with the same parent clause"
    keys = _keys(visible)
    if hidden != replace(visible, select=hidden.select) or keys <= set(hidden.select):
        return "the lets do not differ by a hidden order key only"
    return (
        None
        if keys | set(hidden.select) <= set(visible.select)
        else "the twin hides a key"
    )


@_law("O-HIDDEN", _fit_hidden, 2)
def _hidden(specs: Specs, rows: Rows, field: str) -> str | None:
    """The lets differ by projection only; no LIMIT boundary tie."""
    hidden, visible = _the(specs[0], field), _the(specs[1])
    if _ties(hidden, (), (), 0):
        return _NO_REFERENCE
    for key, mine, twin in _paired(rows[0], rows[1], hidden.name):
        mine, start = _items(mine), 0
        for group in _groups(twin, visible.order, visible.select):
            chunk = mine[start : start + len(group)]
            same = _bag(chunk, hidden.select) == _bag(group, hidden.select)
            _require(same, f"parent {key}: a tie group differs from the visible twin")
            start += len(group)
        _require(start == len(mine), f"parent {key}: sizes differ")


def _fit_topk(specs: Specs, field: str) -> str | None:
    if not (pair := _pair(specs)):
        return _PAIR
    top, whole = pair
    if top.limit is None or whole != replace(top, limit=None):
        return "the second let is not the first without its LIMIT"
    return None


@_law("O-TOPK", _fit_topk, 2)
def _topk(specs: Specs, rows: Rows, field: str) -> str | None:
    """Same keys and directions; every order key is a child field."""
    top = _the(specs[0])
    assert top.limit is not None
    if not _keys(top) <= set(top.select):
        return _HIDDEN_KEY
    compare = _compare(top.order)
    for key, got, whole in _paired(rows[0], rows[1], top.name):
        got, whole = _items(got), _items(whole)
        size = len(got) == min(top.limit, len(whole))
        _require(
            size and _in_order(got, top.order), f"parent {key}: not an ordered top-k"
        )
        taken = _bag(got, top.select)
        for child in whole:
            label = _k(child[name] for name in top.select)
            if taken[label]:
                taken[label] -= 1
            else:
                _require(
                    compare(child, got[-1]) >= 0,
                    f"parent {key}: an untaken row precedes",
                )
        _require(
            not +taken, f"parent {key}: a top-k row is not in the unlimited container"
        )


def _fit_mono(specs: Specs, field: str) -> str | None:
    if not (pair := _pair(specs)):
        return _PAIR
    a, b = pair
    if a.limit is None or b != replace(a, limit=a.limit + 1):
        return "the second let is not the first with LIMIT k + 1"
    return None


@_law("O-MONO", _fit_mono, 2)
def _mono(specs: Specs, rows: Rows, field: str) -> str | None:
    """No tie at position k; every order key is a child field."""
    let = _the(specs[0])
    k = let.limit
    assert k is not None
    if not _keys(let) <= set(let.select):
        return _HIDDEN_KEY
    compare = _compare(let.order)
    for row in rows[1]:
        longer = _items(row[let.name])
        if len(longer) > k and compare(longer[k - 1], longer[k]) == 0:
            return f"position {k} ties"
    for key, a, b in _paired(rows[0], rows[1], let.name):
        prefix = _canon_let(a, let) == _canon_let(_items(b)[:k], let)
        _require(prefix, f"parent {key}: LIMIT {k} is not a prefix of LIMIT {k + 1}")


def _fit_reverse(specs: Specs, field: str) -> str | None:
    if not (pair := _pair(specs)):
        return _PAIR
    a, d = pair
    key = _UNIQUE.get(a.table)
    if (
        a.limit is not None
        or a.order != ((key, False),)
        or d != replace(a, order=((key, True),))
    ):
        return "needs an unlimited let ordered by its unique key and its reverse"
    return None


@_law("O-REVERSE", _fit_reverse, 2)
def _reverse(specs: Specs, rows: Rows, field: str) -> str | None:
    """Unique key, no LIMIT."""
    let = _the(specs[0])
    for key, a, d in _paired(rows[0], rows[1], let.name):
        forward = [_k(child[n] for n in let.select) for child in _items(a)]
        backward = [_k(child[n] for n in let.select) for child in _items(d)]
        _require(backward == forward[::-1], f"parent {key}: DESC is not ASC reversed")


def _fit_parent_order(specs: Specs, field: str) -> str | None:
    m, s, r = specs
    if not (isinstance(m, Collect) and m.lets and m.order and _keys(m) <= {"id"}):
        return "needs a Collect with an outer ORDER BY on parent fields"
    if (s, r) != (Collect((), m.order, m.limit), Collect((), m.order, None)):
        return "needs the parent-only twin and its unlimited reference"
    return None


@_law("O-PARENT", _fit_parent_order, 3)
def _parent_order(specs: Specs, rows: Rows, field: str) -> str | None:
    """An outer ORDER BY on parent fields."""
    order, limit, n = specs[0].order, specs[0].limit, len(rows[2])
    _require(_in_order(rows[0], order), "parents are out of the outer order")
    same = _canon(rows[0], order, ("id",)) == _canon(rows[1], order, ("id",))
    _require(same, "the parent sequence differs from the parent-only twin")
    _require(
        len(rows[0]) == (n if limit is None else min(limit, n)),
        "LIMIT does not count parents",
    )


def _same_bags(specs: Specs, rows: Rows) -> str | None:
    if missing := _ties(_producer(specs[0]), specs, rows, 2):
        return missing
    names = ("id", *_out(specs[0]))
    _require(_bag(rows[0], names) == _bag(rows[1], names), "the two Unnest bags differ")


def _fit_inner_true(specs: Specs, field: str) -> str | None:
    i, x = specs
    if (
        _join(i) != ("inner", "True", False)
        or _join(x) != _CROSS
        or _form(i) != _form(x)
    ):
        return "needs INNER ON True and CROSS over one producer"
    return None


@_law("U-INNER-TRUE", _fit_inner_true, 2)
def _inner_true(specs: Specs, rows: Rows, field: str) -> str | None:
    """Same producer; no LIMIT boundary tie."""
    return _same_bags(specs, rows)


def _fit_inner_false(specs: Specs, field: str) -> str | None:
    return (
        None if _join(specs[0]) == ("inner", "False", False) else "needs INNER ON False"
    )


@_law("U-INNER-FALSE", _fit_inner_false, 1)
def _inner_false(specs: Specs, rows: Rows, field: str) -> str | None:
    """None."""
    _require(not rows[0], "INNER ON False returned rows")


def _fit_producer(flat: Any, spec: Any) -> str | None:
    let = _single(spec)
    if (
        let is None
        or _clause(spec) != ((), None)
        or not _same_rows(let, _producer(flat))
    ):
        return "the last program is not the producer Collect"
    return None


def _left(specs: Specs, rows: Rows, keep: Callable[[list[Any]], bool]) -> str | None:
    """LEFT = the other join's rows plus one placeholder per kept parent."""
    let = _the(specs[-1])
    if _ties(let, (), (), 0):
        return _NO_REFERENCE
    names = ("id", *_out(specs[0]))
    blank = [None] * (len(names) - 1)
    extra = Counter(
        _k([row["id"], *blank]) for row in rows[-1] if keep(_items(row[let.name]))
    )
    other = _bag(rows[1], names) if len(rows) == 3 else Counter()
    count = sum(other.values()) + sum(extra.values())
    _require(len(rows[0]) == count, "LEFT rows != other rows + placeholders")
    _require(
        _bag(rows[0], names) == other + extra,
        "LEFT != other join + one placeholder per parent",
    )


def _fit_left_true(specs: Specs, field: str) -> str | None:
    left, cross, producer = specs
    if (
        _join(left) != ("left", "True", False)
        or _join(cross) != _CROSS
        or _form(left) != _form(cross)
    ):
        return "needs LEFT ON True and CROSS over one producer"
    return _fit_producer(left, producer)


@_law("U-LEFT-TRUE", _fit_left_true, 3)
def _left_true(specs: Specs, rows: Rows, field: str) -> str | None:
    """Same producer; no LIMIT boundary tie."""
    return _left(specs, rows, lambda children: not children)


def _fit_left_on(specs: Specs, field: str) -> str | None:
    left, inner, producer = specs
    (join, on, where), other = _join(left), _join(inner)
    if (join, where, on in _PREDICATES) != ("left", False, True) or other != (
        "inner",
        on,
        False,
    ):
        return "needs LEFT ON p and INNER ON p"
    return (
        _fit_producer(left, producer)
        if _form(left) == _form(inner)
        else "the producers differ"
    )


@_law("U-LEFT-ON", _fit_left_on, 3)
def _left_on(specs: Specs, rows: Rows, field: str) -> str | None:
    """p reads child fields only; no LIMIT boundary tie."""
    on = _join(specs[0])[1] or ""
    if not set(_READS[on]) <= set(_the(specs[2]).select) & set(_out(specs[0])):
        return "ON reads a field outside the child projection"
    test = _PREDICATES[on]
    return _left(specs, rows, lambda children: not any(test(c) for c in children))


def _fit_left_false(specs: Specs, field: str) -> str | None:
    if _join(specs[0]) != ("left", "False", False):
        return "needs LEFT ON False"
    return _fit_producer(*specs)


@_law("U-LEFT-FALSE", _fit_left_false, 2)
def _left_false(specs: Specs, rows: Rows, field: str) -> str | None:
    """None."""
    return _left(specs, rows, lambda children: True)


def _fit_where(specs: Specs, field: str) -> str | None:
    # The modeled WHERE is `o.v > 10`, which rejects NULL.
    where, inner = specs
    joins = (_join(where), _join(inner))
    if joins != (("left", "True", True), ("inner", "o.v > 10", False)):
        return "needs LEFT ON True WHERE p and INNER ON the same NULL-rejecting p"
    return None if _form(where) == _form(inner) else "the producers differ"


@_law("U-WHERE", _fit_where, 2)
def _where(specs: Specs, rows: Rows, field: str) -> str | None:
    """p rejects NULL; no LIMIT boundary tie."""
    return _same_bags(specs, rows)


def _fit_lateral(specs: Specs, field: str) -> str | None:
    a, b = specs[:2]
    if _form(a) is None or type(a) is not type(b) or a.lateral or not b.lateral:
        return "needs a two-stage Unnest and its LATERAL twin"
    if (
        _join(a) != _join(b)
        or _out(a) != _out(b)
        or not _same_rows(_producer(a), _producer(b))
    ):
        return "the joins, fields or producers differ"
    return None


@_law("U-LATERAL", _fit_lateral, 2, 3)
def _lateral(specs: Specs, rows: Rows, field: str) -> str | None:
    """The same captured let; no LIMIT boundary tie."""
    return _same_bags(specs, rows)


@cache
def _instances(leaves: tuple[str, ...]) -> tuple[Instance, ...]:
    members = _corpus(leaves)
    spec: dict[str, Any] = {member.name: member.spec for member in members}
    found: list[Instance] = []

    def offer(law: str, names: tuple[str, ...], field: str = "") -> None:
        chosen = LAWS[law]
        specs = tuple(spec[name] for name in names)
        if len(names) in chosen.arity and chosen.fit(specs, field) is None:
            found.append(Instance(law, names, field))

    collects = [m.name for m in members if isinstance(m.spec, Collect) and m.spec.lets]
    strips = [
        m.name for m in members if isinstance(m.spec, Collect) and not m.spec.lets
    ]
    singles = [name for name in collects if len(spec[name].lets) == 1]
    flats = [m.name for m in members if not isinstance(m.spec, Collect)]

    def reference(let: Let | None) -> tuple[str, ...]:
        if let is None or not _ties(let, (), (), 0):
            return ()
        return next(((name,) for name in singles if _reference(let, spec[name])), ())

    for m in collects:
        for s in strips:
            offer("C-PARENT", (m, s))
            for r in strips:
                offer("O-PARENT", (m, s, r))
        for let in spec[m].lets:
            ref, field = reference(let), let.name
            for law in ("C-EMPTY", "O-SORTED"):
                offer(law, (m,), field)
            offer("C-CLOSED", (m, *ref), field)
            peer = Collect((let,))
            moved = _clause(spec[m]) != ((), None)
            same = [s for s in singles if moved and spec[s] == peer]
            offer("C-DUP", (m, *same[:1], *ref), field)
            for s in singles:
                offer("O-HIDDEN", (m, s), field)
            for t in flats:
                for law in ("C-EMPTY", "C-COUNT"):
                    offer(law, (m, t), field)
                offer("C-BAG", (m, t, *ref), field)
        own = [Collect((let,), spec[m].order, spec[m].limit) for let in spec[m].lets]
        siblings = [next((s for s in singles if spec[s] == o), "") for o in own]
        if all(siblings):
            offer("C-SIBLING", (m, *siblings))
    for a, b in itertools.permutations(singles, 2):
        for law in ("O-TOPK", "O-MONO", "O-REVERSE"):
            offer(law, (a, b))
    for a in flats:
        producer = next(
            ((p,) for p in singles if _fit_producer(spec[a], spec[p]) is None), ()
        )
        offer("U-INNER-FALSE", (a,))
        offer("U-LEFT-FALSE", (a, *producer))
        for b in flats:
            for law in ("U-INNER-TRUE", "U-WHERE"):
                offer(law, (a, b))
            offer("U-LATERAL", (a, b, *reference(_producer(spec[a]))))
            for law in ("U-LEFT-TRUE", "U-LEFT-ON"):
                offer(law, (a, b, *producer))
    return tuple(found)


def instances(leaves: tuple[str, ...] = DEFAULT_LEAVES) -> tuple[Instance, ...]:
    return _instances(oracle.leaves_of(leaves))


# Verdicts -----------------------------------------------------------------------


def _judge(
    instance: Instance, specs: Specs, rows: Rows, problems: list[str | None]
) -> Verdict:
    law = LAWS[instance.law]
    if len(specs) not in law.arity:
        return Verdict(NOT_APPLICABLE, f"{law.id} does not take {len(specs)} programs")
    if (reason := law.fit(specs, instance.field)) is not None:
        return Verdict(NOT_APPLICABLE, reason)
    for name, problem in zip(instance.programs, problems, strict=True):
        if problem:
            return Verdict(VIOLATED, f"{name}: {problem}")
    try:
        reason = law.check(specs, rows, instance.field)
    except (ArithmeticError, TypeError, ValueError) as exc:
        return Verdict(VIOLATED, str(exc))
    if reason is not None:
        return Verdict(NOT_APPLICABLE, reason)
    return Verdict(HOLDS, f"{law.id} holds under: {law.premise}")


def law_verdicts(
    found: dict[tuple[str, str], Any],
    leaves: tuple[str, ...] = DEFAULT_LEAVES,
    chosen: tuple[Instance, ...] | None = None,
) -> dict[tuple[str, ...], Verdict]:
    """Law verdicts of every instance whose programs all have rows in a data set.

    ``found`` maps (program, data set) to actual rows; the oracle is not read.
    An unknown program or data set raises ValueError.
    """
    leaves = oracle.leaves_of(leaves)
    spec = {member.name: member.spec for member in _corpus(leaves)}
    tables = {dataset.name: dataset.tables for dataset in _datasets(leaves)}
    for program, dataset in found:
        if program not in spec:
            raise ValueError(f"unknown program {program}")
        if dataset not in tables:
            raise ValueError(f"unknown data set {dataset}")
    problems: dict[tuple[str, str], str | None] = {}
    report = {}
    for dataset in sorted({name for _, name in found}):
        for instance in _instances(leaves) if chosen is None else chosen:
            keys = [(name, dataset) for name in instance.programs]
            if not all(key in found for key in keys):
                continue
            for key in keys:
                if key not in problems:
                    problems[key] = _malformed(
                        spec[key[0]], found[key], tables[dataset]
                    )
            specs = tuple(spec[name] for name in instance.programs)
            rows = tuple(found[key] for key in keys)
            label = ("law", dataset, instance.law, instance.field, *instance.programs)
            report[label] = _judge(
                instance, specs, rows, [problems[key] for key in keys]
            )
    return dict(sorted(report.items()))


def verdicts(
    found: dict[tuple[str, str], Any], leaves: tuple[str, ...] = DEFAULT_LEAVES
) -> dict[tuple[str, ...], Verdict]:
    """The oracle verdict of every found entry plus every law verdict."""
    leaves = oracle.leaves_of(leaves)
    members = {member.name: member for member in _corpus(leaves)}
    tables = {dataset.name: dataset.tables for dataset in _datasets(leaves)}
    report = law_verdicts(found, leaves)
    for (program, dataset), rows in found.items():
        label = ("oracle", dataset, program)
        try:
            want = expected(members[program], tables[dataset])
        except ValueError as exc:
            report[label] = Verdict(NOT_APPLICABLE, str(exc))
            continue
        reasons = oracle.check(rows, want)
        report[label] = (
            Verdict(VIOLATED, "; ".join(reasons))
            if reasons
            else Verdict(HOLDS, "matches the typed-literal oracle")
        )
    return dict(sorted(report.items()))


def native_verdicts(
    found: dict[tuple[str, str], Any],
    profile: str,
) -> dict[tuple[str, ...], Verdict]:
    """Judge the complete bounded actual matrix; NA alone never covers a law."""
    expected_keys = {
        (program, dataset)
        for program in NATIVE_PROGRAMS[profile]
        for dataset in NATIVE_DATASETS
    }
    if type(found) is not dict or set(found) != expected_keys:
        raise ValueError("native matrix denominator")
    report = verdicts(found, NATIVE_LEAVES[profile])
    if any(value.value == VIOLATED for value in report.values()):
        raise ValueError("native verdict violated")
    covered = {
        key[2]
        for key, value in report.items()
        if key[0] == "law" and value.value == HOLDS
    }
    required = set(LAWS) - {"U-LATERAL"} if profile == "nested" else {"U-LATERAL"}
    if not required <= covered:
        raise ValueError("native laws without holding witnesses")
    return report


# Law-targeted damages and the canonical document ----------------------------


def law_damages(
    rows: dict[str, list[dict[str, Any]]], leaves: tuple[str, ...] = DEFAULT_LEAVES
) -> dict[str, tuple[str, list[dict[str, Any]]]]:
    """Single-fault copies of one data set's realized rows, each aimed at a law.

    ``rows`` maps program names to realized rows; each damage names the
    program it replaces. Inapplicable damages are absent.
    """
    fields = ("id", *oracle.child_fields(leaves))
    c1, c2, c6 = rows["C1_closed"], rows["C2_captured"], rows["C6_siblings"]
    u4, u5, u6 = (
        rows["U4_left_true"],
        rows["U5_left_v_gt_10"],
        rows["U6_left_true_where_v_gt_10"],
    )
    damaged: dict[str, tuple[str, list[dict[str, Any]]]] = {}
    empty = [p["id"] for p in c2 if p["recent"] == []]
    if empty:
        drop = next(i for i, row in enumerate(u4) if _k([row["id"]]) == _k(empty[:1]))
        damaged["left_placeholder_dropped"] = (
            "U4_left_true",
            u4[:drop] + u4[drop + 1 :],
        )
    owners = [p["id"] for p in c2 if p["recent"]]
    if owners:
        blank = {"id": owners[0], **dict.fromkeys(fields[1:])}
        damaged["left_placeholder_invented"] = ("U4_left_true", [*u4, blank])
    low = {
        _k([p["id"]]): sorted(p["recent"], key=lambda c: c["id"])[:2][::-1] for p in c2
    }
    wrong = [{**p, "recent": low[_k([p["id"]])]} for p in rows["C3_topk"]]
    if _canonical(wrong) != _canonical(rows["C3_topk"]):
        damaged["topk_wrong_end"] = ("C3_topk", wrong)
    for i, p in enumerate(c2):
        if len(p["recent"]) > 1:
            flipped = {**p, "recent": p["recent"][::-1]}
            damaged["child_order_reversed"] = (
                "C2_captured",
                [*c2[:i], flipped, *c2[i + 1 :]],
            )
            break
    for i, p in enumerate(c6):  # `paid` is ordered by its hidden unique id
        if _canonical(p["paid"][::-1]) != _canonical(p["paid"]):
            flipped = {**p, "paid": p["paid"][::-1]}
            damaged["hidden_order_reversed"] = (
                "C6_siblings",
                [*c6[:i], flipped, *c6[i + 1 :]],
            )
            break
    name = "C5_hidden_nullable_key_asc"
    for i, p in enumerate(rows[name]):
        seen = [_canonical(child) for child in p["recent"]]
        twin = next((j for j in range(len(seen)) if seen[j] in seen[:j]), None)
        if twin is not None:
            kept = {**p, "recent": p["recent"][:twin] + p["recent"][twin + 1 :]}
            damaged["duplicate_child_collapsed"] = (
                name,
                [*rows[name][:i], kept, *rows[name][i + 1 :]],
            )
            break
    if c2:
        damaged["parent_duplicated"] = ("C2_captured", [dict(c2[0]), *c2])
    for i, j in itertools.combinations(range(len(c6)), 2):
        a, b = c6[i], c6[j]
        if _k([a["id"]]) != _k([b["id"]]) and _canonical(a["paid"]) != _canonical(
            b["paid"]
        ):
            crossed = list(c6)
            crossed[i], crossed[j] = {**a, "paid": b["paid"]}, {**b, "paid": a["paid"]}
            damaged["sibling_crossed"] = ("C6_siblings", crossed)
            break
    if len(c1) > 1 and c1[0]["all_orders"]:
        short = {**c1[0], "all_orders": c1[0]["all_orders"][:-1]}
        damaged["closed_divergence"] = ("C1_closed", [short, *c1[1:]])
    if _bag(u5, fields) != _bag(u6, fields):
        damaged["on_where_confused"] = ("U5_left_v_gt_10", list(u6))
    # Faults alike in every parent's closed container: only a twin sees them.
    shared: tuple[tuple[str, str, str, Callable[[list[Any]], list[Any]]], ...] = (
        ("closed_last_dropped", "C1_closed", "all_orders", lambda c: c[:-1]),
        ("distinct_ignored", "C9_distinct_let", "flags", lambda c: c[:1] + c),
        (
            "null_record_dropped",
            "C9_distinct_let",
            "flags",
            lambda c: [x for x in c if x["flag"] is not None],
        ),
        (
            "group_count_off",
            "C10_grouped_let",
            "counts",
            lambda c: [{**x, "n": x["n"] + 1} for x in c],
        ),
        (
            "null_group_dropped",
            "C10_grouped_let",
            "counts",
            lambda c: [x for x in c if x["customer_id"] is not None],
        ),
    )
    for damage, name, field, change in shared:
        if name in rows:
            bad = [{**p, field: change(p[field])} for p in rows[name]]
            if _canonical(bad) != _canonical(rows[name]):
                damaged[damage] = (name, bad)
    return damaged


def document(leaves: tuple[str, ...] = DEFAULT_LEAVES) -> bytes:
    """Canonical bytes of the laws, the corpus, the data sets and the instances."""
    leaves = oracle.leaves_of(leaves)
    tables = {
        dataset.name: {
            name: [
                [[c.name, c.type, c.nullable] for c in table.columns],
                [
                    [list(_leaf(type(value), repr(value), value)) for value in row]
                    for row in table.rows
                ],
            ]
            for name, table in dataset.tables.items()
        }
        for dataset in _datasets(leaves)
    }
    body = {
        "leaves": list(leaves),
        "laws": [[law.id, law.family, law.premise] for law in LAWS.values()],
        "members": [
            [m.name, list(m.tags), [list(f) for f in m.files]] for m in _corpus(leaves)
        ],
        "datasets": [[d.name, d.seed, tables[d.name]] for d in _datasets(leaves)],
        "instances": [[i.law, i.field, *i.programs] for i in _instances(leaves)],
    }
    return json.dumps(
        body, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
