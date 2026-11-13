"""The MySQL Float row-comparison cells of Phase77 S06 and their probe world.

The world has the tables of the native qualification (s06-float-b10), with
their fields in their order: `f6o` and `f6i` with an `id`, a nullable Float
`v` and NOT NULL binary Text keys `kn` (64) and `kw` (1000); `f6j`, another
source over `f6o`'s table; and `f6s` with an `id` and nullable Floats `f1`
and `f2`. The other sources, for refusals only, differ from those tables:
`f6p` and `f6q` add to `f6o`'s fields a NOT NULL Text `kx` (255) and a
non-null Float `nv`; `f6z` is `f6o`'s with a nullable `kn`; `f6t` is an
`id`, a nullable Float `f1` and a non-null Float `f3`; `f6u` adds to
`f6s`'s fields a nullable Float `f4` and `f6k` the Text `kw`; `f6r` holds
`f6s`'s fields as `f1`, `id`, `f2`; and `f6w` is an `id`, `v` and a NOT NULL
Text `kv` (4000).
"""

from copy import deepcopy
import json

import _pietto_sql_emission as probe

# Each shape's fields as (name, fixture field, nullable, Text width).
_FIELDS = {
    "Probe": (
        ("id", "id", None, None),
        ("v", "ratio", True, None),
        ("kn", "text", False, 64),
        ("kw", "text", False, 1000),
    ),
    "Same": (
        ("id", "id", None, None),
        ("f1", "ratio", True, None),
        ("f2", "ratio", True, None),
    ),
}
_FIELDS["Extra"] = (
    *_FIELDS["Probe"],
    ("kx", "text", False, 255),
    ("nv", "ratio", False, None),
)
_FIELDS["NullKey"] = tuple(
    ("kn", "text", True, 64) if item[0] == "kn" else item for item in _FIELDS["Probe"]
)
_FIELDS["Same3"] = (*_FIELDS["Same"][:2], ("f3", "ratio", False, None))
_FIELDS["Same4"] = (*_FIELDS["Same"], ("f4", "ratio", True, None))
_FIELDS["Turned"] = tuple(_FIELDS["Same"][i] for i in (1, 0, 2))
_FIELDS["Keyed"] = (*_FIELDS["Same"], ("kw", "text", False, 1000))
_FIELDS["Wide"] = (*_FIELDS["Probe"][:2], ("kv", "text", False, 4000))
# Phase77 S07: `s7` holds the fields of the native qualification's `s7`
# tables in their order; `t7` adds, for refusals and unread-field programs,
# NOT NULL Text keys of 255 and 32 characters and a nullable 64-character one.
_FIELDS["S7"] = (
    ("id", "id", None, None),
    ("g", "id", None, None),
    ("f1", "ratio", True, None),
    ("f2", "ratio", True, None),
    ("h1", "ratio", False, None),
    ("h2", "ratio", False, None),
    ("kn", "text", False, 64),
    ("kw", "text", False, 1000),
)
_FIELDS["T7"] = (
    *_FIELDS["S7"],
    ("kx", "text", False, 255),
    ("k3", "text", False, 32),
    ("kz", "text", True, 64),
)
_TYPES = {"id": "Int", "ratio": "Float", "text": "Text", "money": "Decimal(9, 2)"}


def _shape(shape, extra=""):
    return (
        f"shape {shape}:\n"
        + "".join(
            f"    {label}: {_TYPES[model]}{' | None' if nullable else ''}\n"
            for label, model, nullable, _ in _FIELDS[shape]
        )
        + extra
    )


_SHAPES = "".join(_shape(shape) for shape in _FIELDS)
# Phase77 S07 same-class sources, whose shapes only the programs that read
# them declare, so no other program's text changes: `u7` is `s7` with a
# unique key and `d7` `s7` with an unread Decimal(9, 2) field.
_FIELDS["U7"] = _FIELDS["S7"]
_FIELDS["D7"] = (*_FIELDS["S7"], ("dz", "money", False, None))
_READ_SHAPES = {"U7": _shape("U7", "    u7_key = unique(id)\n"), "D7": _shape("D7")}
# Each source as (name, shape, table).
_SOURCES = (
    ("f6o", "Probe", "f6o"),
    ("f6i", "Probe", "f6i"),
    ("f6j", "Probe", "f6o"),
    ("f6s", "Same", "f6s"),
    ("f6p", "Extra", "f6p"),
    ("f6q", "Extra", "f6q"),
    ("f6z", "NullKey", "f6z"),
    ("f6t", "Same3", "f6t"),
    ("f6u", "Same4", "f6u"),
    ("f6r", "Turned", "f6r"),
    ("f6k", "Keyed", "f6k"),
    ("f6w", "Wide", "f6w"),
    ("s7", "S7", "s7"),
    ("t7", "T7", "t7"),
    ("u7", "U7", "u7"),
    ("d7", "D7", "d7"),
)


def world(target, body, release=None):
    """The probe sources ``body`` names, then ``body``: (source, contract).

    A ``body`` that declares header parameters (``result(``) also gets the
    native parameter protocol they need; ``release`` replaces the contract's
    target release."""
    contract = json.loads(
        probe.parameterized_fixture(target, "", protocol="result(" in body)["contract"]
    )
    if release is not None:
        contract["target"]["release"] = release
    base = contract["sources"][0]
    fields = {item["name"]: item for item in base["fields"]}
    header, sources = _SHAPES, []
    for name, shape, table in _SOURCES:
        if name not in body:
            continue
        source = deepcopy(base)
        source["selector"]["name"] = name
        source["relation"]["name"] = "phase77 " + table
        source["fields"] = []
        for ordinal, (label, model, nullable, width) in enumerate(_FIELDS[shape]):
            field = deepcopy(fields[model])
            field["name"] = field["column"] = label
            field["ordinal"] = ordinal
            if nullable is not None:
                field["representation"]["nullable"] = nullable
            if width is not None:
                field["representation"]["domain"]["max_characters"] = width
                if "length" in field["representation"]["storage"]:
                    field["representation"]["storage"]["length"] = width
            source["fields"].append(field)
        sources.append(source)
        header += _READ_SHAPES.get(shape, "")
        header += f'source {name}: {shape} = {target}.table("{name}.locator")\n'
    contract["sources"] = sources
    return header + body, probe.encoded(contract).decode()


def build(directory, target, body, release=None):
    source, contract = world(target, body, release)
    checked, outcome = probe.build_case(directory, source, contract)
    assert checked.verified
    return outcome


def query(*lines, declaration="table", parameters=None):
    header = "" if parameters is None else f"({parameters})"
    return f"{declaration} result{header}:\n" + "".join(
        f"    {line}\n" for line in lines
    )


_SAME_ROW = {
    "==": "f1 == f2",
    "!=": "f1 != f2",
    "not !=": "not (f1 != f2)",
    "same_value": "same_value(f1, f2)",
    "not same_value": "not same_value(f1, f2)",
}
_JOINS = {
    ("inner", "=="): "f6i.v == f6o.v",
    ("inner", "not !="): "not (f6i.v != f6o.v)",
    ("left", "=="): "f6i.v == f6o.v",
}
JOINED = ("oid = f6o.id", "ov = f6o.v", "iid = f6i.id", "iv = f6i.v")
# The qualified forms of s06-float-b10, as (cell, key, body): every same-row
# form as a SELECT item and as the WHERE, and every JOIN form over the Float
# alone and beside the narrow and the wide key.
QUALIFIED = (
    *(
        (
            ("same_row", "select", form),
            None,
            query("from f6s", "select:", "    id", f"    r = {tree}"),
        )
        for form, tree in _SAME_ROW.items()
    ),
    *(
        (
            ("same_row", "where", form),
            None,
            query("from f6s", f"where {tree}", "select:", "    id", "    f1", "    f2"),
        )
        for form, tree in _SAME_ROW.items()
    ),
    *(
        (
            (kind, "none" if key is None else "text", form),
            key,
            query(
                "from f6o",
                f"{kind} join f6i on {on}"
                + ("" if key is None else f" and f6i.{key} == f6o.{key}"),
                "select:",
                *(f"    {item}" for item in JOINED),
            ),
        )
        for (kind, form), on in _JOINS.items()
        for key in (None, "kn", "kw")
    ),
)
# Programs of the same class: renamed or reordered operands and keys, a
# subset of the SELECT items and a query declaration.
SAME_CLASS = {
    "swapped": query(
        "from f6o",
        "inner join f6i on f6o.v == f6i.v and f6o.kn == f6i.kn",
        "select:",
        "    ov = f6o.v",
    ),
    "tree_only": query("from f6s", "select:", "    r = not same_value(f2, f1)"),
    "query_where": query(
        "from f6s", "where f2 != f1", "select:", "    id", declaration="query"
    ),
    "left_subset": query(
        "from f6o",
        "left join f6i on f6i.v == f6o.v and f6i.kw == f6o.kw",
        "select:",
        "    iid = f6i.id",
    ),
}
_PAIR = ("PIE-B1003", "comparison_type_pair_not_admitted")
_JOIN = ("inner join f6i on f6i.v == f6o.v", "select:", "    oid = f6o.id")
_EQ = "def eq(a: Float | None, b: Float | None) -> Bool | None:\n    return a == b\n\n"
# Every other program keeps main's refusal on MySQL, and emits on PostgreSQL.
REFUSED = {
    # A relation alias `let`, read (also through a chain) or not, and a named
    # window: the plan resolves an alias to its source, so emission reads the
    # query as written.
    "relation_alias": (
        query(
            "from f6o",
            "let i = f6i",
            "inner join i on i.v == f6o.v",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "alias_chain": (
        query(
            "let i = f6i",
            "let j = i",
            "from f6o",
            "inner join j on j.v == f6o.v",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "from_alias": (
        query("let s = f6s", "from s", "select:", "    id", "    r = f1 == f2"),
        [_PAIR],
    ),
    "unread_alias": (query("let i = f6i", "from f6o", *_JOIN), [_PAIR]),
    "named_window": (
        query(
            "from f6s",
            "let w = window(order by id)",
            "select:",
            "    id",
            "    r = f1 == f2",
        ),
        [_PAIR],
    ),
    # A `def` inlined into the comparison, its `not` or `and`, or an item.
    "def_item": (
        _EQ + query("from f6s", "select:", "    id", "    r = eq(f1, f2)"),
        [_PAIR],
    ),
    "def_where": (
        _EQ + query("from f6s", "where eq(f1, f2)", "select:", "    id"),
        [_PAIR],
    ),
    "def_on": (
        _EQ
        + query(
            "from f6o",
            "inner join f6i on eq(f6i.v, f6o.v)",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "def_not": (
        "def neg(x: Bool | None) -> Bool | None:\n    return not x\n\n"
        + query("from f6s", "select:", "    id", "    r = neg(f1 != f2)"),
        [_PAIR],
    ),
    "def_and": (
        "def both(x: Bool | None, y: Bool | None) -> Bool | None:\n"
        "    return x and y\n\n"
        + query(
            "from f6o",
            "inner join f6i on both(f6i.v == f6o.v, f6i.kn == f6o.kn)",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "def_other_item": (
        "def ident(x: Int) -> Int:\n    return x\n\n"
        + query("from f6s", "select:", "    x = ident(id)", "    r = f1 == f2"),
        [_PAIR],
    ),
    # A header parameter the query does not read.
    "parameter_select": (
        query(
            "from f6s",
            "select:",
            "    id",
            "    r = f1 == f2",
            declaration="query",
            parameters="p: Int",
        ),
        [_PAIR],
    ),
    "parameter_where": (
        query(
            "from f6s",
            "where f1 == f2",
            "select:",
            "    id",
            declaration="query",
            parameters="p: Float | None",
        ),
        [_PAIR],
    ),
    "parameter_join": (
        query("from f6o", *_JOIN, declaration="query", parameters="p: Int"),
        [_PAIR],
    ),
    "same_field": (query("from f6s", "select:", "    id", "    r = f1 == f1"), [_PAIR]),
    "non_null_operand": (
        query("from f6t", "select:", "    id", "    r = f1 == f3"),
        [_PAIR],
    ),
    # `same_value` outside its same-row cells.
    "same_value_same_field": (
        query("from f6s", "select:", "    id", "    r = same_value(f1, f1)"),
        [_PAIR],
    ),
    "same_value_non_null": (
        query("from f6t", "select:", "    id", "    r = same_value(f1, f3)"),
        [_PAIR],
    ),
    "same_value_float_item": (
        query("from f6s", "select:", "    f1", "    r = same_value(f1, f2)"),
        [_PAIR],
    ),
    "not_equal": (query("from f6s", "select:", "    r = not (f1 == f2)"), [_PAIR]),
    "where_not_equal": (
        query("from f6s", "where not (f1 == f2)", "select:", "    id"),
        [_PAIR],
    ),
    "nested_or": (
        query("from f6s", "select:", "    r = f1 == f2 or f1 is None"),
        [_PAIR],
    ),
    "two_comparisons": (
        query("from f6s", "select:", "    r = f1 == f2", "    s = f1 != f2"),
        [_PAIR, _PAIR],
    ),
    "where_and_item": (
        query("from f6s", "where f1 == f2", "select:", "    r = f1 != f2"),
        [_PAIR],
    ),
    "other_where": (
        query("from f6s", "where id > 1", "select:", "    r = f1 == f2"),
        [_PAIR],
    ),
    "float_item": (
        query("from f6s", "select:", "    f1", "    r = f1 == f2"),
        [_PAIR],
    ),
    "non_null_item": (
        query("from f6t", "where f1 == f3", "select:", "    id", "    f3"),
        [_PAIR],
    ),
    "literal_item": (
        query("from f6s", "select:", "    n = 1", "    r = f1 == f2"),
        [_PAIR],
    ),
    "order_by": (
        query("from f6s", "select:", "    id", "    r = f1 == f2", "order by id"),
        [_PAIR],
    ),
    "limit": (query("from f6s", "select:", "    r = f1 == f2", "limit 2"), [_PAIR]),
    "distinct": (query("from f6s", "select distinct:", "    r = f1 == f2"), [_PAIR]),
    "window_beside": (
        query(
            "from f6s",
            "select:",
            "    r = f1 == f2",
            "    n = row_number() window(order by id)",
        ),
        [_PAIR],
    ),
    # Beside another refusal: main's whole blocker list.
    "beside_refused_item": (
        query("from f6s", "select:", "    r = f1 == f2", "    q = f1 / f2"),
        [_PAIR, ("PIE-B1003", "float_division_not_realized")],
    ),
    "let_comparison": (
        query("from f6s", "let e = f1 == f2", "select:", "    r = e"),
        [_PAIR],
    ),
    "let_operand": (
        query("from f6s", "let g = f1", "select:", "    r = g == f2"),
        [_PAIR],
    ),
    "upstream_query": (
        "table a:\n    from f6s\n    select:\n        id\n        f1\n        f2\n\n"
        + query("from a", "select:", "    r = f1 == f2"),
        [_PAIR],
    ),
    "union_operand": (
        "table a:\n    from f6s\n    select:\n        r = f1 == f2\n\n"
        "table b:\n    from f6s\n    select:\n        r = f1 != f2\n\n"
        "table result:\n    union all a, b\n",
        [_PAIR],
    ),
    "relation_let": (
        query(
            "let r:",
            "    from f6s",
            "    select:",
            "        f1",
            "        f2",
            "from r",
            "select:",
            "    q = f1 == f2",
        ),
        [_PAIR],
    ),
    "right_join": (
        query(
            "from f6o",
            "right join f6i on f6i.v == f6o.v",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "inner_not_equal": (
        query(
            "from f6o",
            "inner join f6i on f6i.v != f6o.v",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "left_not_not_equal": (
        query(
            "from f6o",
            "left join f6i on not (f6i.v != f6o.v)",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "int_key": (
        query(
            "from f6o",
            "inner join f6i on f6i.v == f6o.v and f6i.id == f6o.id",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "key_first": (
        query(
            "from f6o",
            "inner join f6i on f6i.kn == f6o.kn and f6i.v == f6o.v",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "key_width_255": (
        query(
            "from f6p",
            "inner join f6q on f6q.v == f6p.v and f6q.kx == f6p.kx",
            "select:",
            "    oid = f6p.id",
        ),
        [_PAIR],
    ),
    "nullable_key": (
        query(
            "from f6o",
            "inner join f6z on f6z.v == f6o.v and f6z.kn == f6o.kn",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "mixed_key_widths": (
        query(
            "from f6o",
            "inner join f6i on f6i.v == f6o.v and f6i.kn == f6o.kw",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    # A source whose fields, which the statement's CTE writes whether the
    # query selects them or not, are not those of its cell's tables: another
    # field, of a kind those tables held or not, the fields in another order,
    # or the same-row table as a JOIN input.
    "unselected_key_same_row": (
        query("from f6k", "where f1 != f2", "select:", "    id"),
        [_PAIR],
    ),
    "unselected_nullable_float": (
        query("from f6u", "where f1 != f2", "select:", "    id"),
        [_PAIR],
    ),
    "reordered_fields": (
        query("from f6r", "where f1 != f2", "select:", "    id"),
        [_PAIR],
    ),
    "same_row_table_joined": (
        query(
            "from f6s",
            "inner join f6o on f6o.v == f6s.f1",
            "select:",
            "    sid = f6s.id",
        ),
        [_PAIR],
    ),
    "unselected_wide_text": (
        query(
            "from f6o",
            "inner join f6w on f6w.v == f6o.v",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    # Both Float operands, or both keys, read one JOIN input.
    "join_same_side": (
        query(
            "from f6o",
            "inner join f6s on f6s.f1 == f6s.f2",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "key_same_side": (
        query(
            "from f6o",
            "inner join f6i on f6i.v == f6o.v and f6i.kn == f6i.kn",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "non_null_join_float": (
        query(
            "from f6p",
            "inner join f6q on f6q.nv == f6p.nv",
            "select:",
            "    oid = f6p.id",
        ),
        [_PAIR],
    ),
    "two_float_conditions": (
        query(
            "from f6o",
            "inner join f6i on f6i.v == f6o.v and not (f6i.v != f6o.v)",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "text_item": (
        query(
            "from f6o",
            "inner join f6i on f6i.v == f6o.v",
            "select:",
            "    oid = f6o.id",
            "    k = f6o.kn",
        ),
        [_PAIR],
    ),
    "where_after_join": (
        query(
            "from f6o",
            "inner join f6i on f6i.v == f6o.v",
            "where f6o.id > 1",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "same_table": (
        query(
            "from f6o",
            "inner join f6j on f6j.v == f6o.v",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "self_join": (
        query(
            "let o2 = f6o",
            "from f6o",
            "inner join o2 on o2.v == f6o.v",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    "two_joins": (
        query(
            "from f6o",
            "inner join f6i on f6i.v == f6o.v",
            "inner join f6s on f6s.id == f6o.id",
            "select:",
            "    oid = f6o.id",
        ),
        [_PAIR],
    ),
    # The qualification's SEMI and ANTI shapes: semi_exists, semi_exists_not_ne
    # (and semi_in) returned outer rows twice; anti_not_exists and
    # semi_exists_ne matched but stay refused for the D77.07 packet.
    "semi_exists": (
        query(
            "let z = f6i",
            "from f6o",
            "where any(z.v == f6o.v for z in z)",
            "select:",
            "    id",
        ),
        [_PAIR],
    ),
    "anti_not_exists": (
        query(
            "let z = f6i",
            "from f6o",
            "where not any(z.v == f6o.v for z in z)",
            "select:",
            "    id",
        ),
        [_PAIR],
    ),
    "semi_exists_ne": (
        query(
            "let z = f6i",
            "from f6o",
            "where any(z.v != f6o.v for z in z)",
            "select:",
            "    id",
        ),
        [_PAIR],
    ),
    "semi_exists_not_ne": (
        query(
            "let z = f6i",
            "from f6o",
            "where any(not (z.v != f6o.v) for z in z)",
            "select:",
            "    id",
        ),
        [_PAIR],
    ),
}


# Phase77 S07 (D77.39): the paired forms of the S07 native qualification
# (reauthor/s07 manifest `pietto_forms`) that the MySQL Float key cells
# (rows.MYSQL_FLOAT_KEY_CELLS) hold, as {name: (cell, body)}, restated here
# because tests never read `.cache`; a lane check compared them byte for byte.
# Only the GROUP BY forms were judged CANDIDATE_EMISSION_EXPERIMENT_READY.
_KEY_FIELDS = {"h": "h1", "f": "f1", "n": "kn", "w": "kw"}
_KEY_CARRIERS = {"h": "H", "f": "F", "n": "N"}


def key_body(template, keys, source="s7"):
    """The paired Pietto form of ``template`` over ``keys`` (field names)."""
    names = "".join(f"        {key}\n" for key in keys)
    if template == "group":
        return (
            f"query result:\n    from {source}\n    group by:\n{names}"
            f"    select:\n{names}        n = count()\n"
        )
    if template == "distinct":
        return f"query result:\n    from {source}\n    select distinct:\n{names}"
    return (
        f"table a:\n    from {source}\n    select:\n{names}"
        "query result:\n    union distinct:\n        from a\n        from a\n"
    )


def _keys(keyset):
    second = {"h": "h2", "f": "f2"}
    return tuple(
        second[letter] if letter in keyset[:position] else _KEY_FIELDS[letter]
        for position, letter in enumerate(keyset)
    )


KEY_FORMS = {
    f"group.{keyset}": (
        ("group", tuple(_KEY_CARRIERS[letter] for letter in keyset)),
        key_body("group", _keys(keyset)),
    )
    for keyset in ("h", "f", "hh", "ff", "hnh", "fnf")
}
# The paired forms that keep main's refusal: the DISTINCT and UNION DISTINCT
# forms, which the raw campaign judged PRIMITIVE_OBSERVATION_ONLY (no on-disk
# deduplication witnessed), and the wide-key controls (D77.08), whose text
# with identifiers erased equals their narrow forms'.
REFUSED_KEY_FORMS = {
    f"{template}.{keyset}": key_body(template, _keys(keyset))
    for template in ("group", "distinct", "union_distinct")
    for keyset in ("h", "f", "hh", "ff", "hnh", "fnf", "hwh", "fwf")
    if f"{template}.{keyset}" not in KEY_FORMS
}


def erased(sql):
    """A MySQL statement with every quoted identifier replaced by ?."""
    import re

    return re.sub(r"`[^`]*`", "?", sql)


def _probe(template, count):
    """The S07 probe of ``template`` (group) over ``count`` keys (MySQL
    `many` variant, identifiers erased), restated from the manifest."""
    assert template == "group"
    items = ", ".join(["?.? AS ?"] * count)
    return (
        f"WITH ? ({', '.join(['?'] * (count + 1))}) AS (SELECT {items}, COUNT(*)"
        f" AS ? FROM ?.? AS ? GROUP BY {', '.join(['?.?'] * count)}) SELECT"
        f" {items}, ?.? AS ? FROM ? AS ?"
    )


KEY_PROBES = {
    name: _probe(cell[0], len(cell[1])) for name, (cell, _) in KEY_FORMS.items()
}
# Programs of the same class: a table or query declaration, other output
# names, other fields of the same carriers in another order, a source with
# unread fields the statement never writes, one with a unique key and one
# with an unread Decimal field.
KEY_SAME_CLASS = {
    "group_table": (
        ("group", ("H",)),
        "table result:\n    from s7\n    group by:\n        h1\n"
        "    select:\n        h1\n        n = count()\n",
    ),
    "group_renamed": (
        ("group", ("H", "H")),
        "query result:\n    from s7\n    group by:\n        h2\n        h1\n"
        "    select:\n        a = h2\n        b = h1\n        c = count()\n",
    ),
    "group_unread_fields": (("group", ("F",)), key_body("group", ("f2",), "t7")),
    "group_unique_key": (("group", ("H",)), key_body("group", ("h1",), "u7")),
    "group_unread_decimal": (
        ("group", ("F", "N", "F")),
        key_body("group", ("f1", "kn", "f2"), "d7"),
    ),
}
_GROUP = ("PIE-B1003", "group_key_type_outside_reviewed_comparison_domain")
_DISTINCT = ("PIE-B1003", "distinct_field_comparison_domain_unsupported")
_SET = ("PIE-B1003", "set_row_equivalence_domain_unsupported")
_COUNT_DISTINCT = ("PIE-B1003", "count_distinct_argument_outside_reviewed_int_domain")
_IDENT = "def ident(x: Float) -> Float:\n    return x\n\n"
_IDI = "def idi(x: Int) -> Int:\n    return x\n\n"
_W = "table w:\n    from s7\n    select:\n        id\n        p = cume_dist() window(order by g)\n\n"


def _grouped(*lines, parameters=None):
    return query(*lines, declaration="query", parameters=parameters)


def _union(
    *lines, tail="query result:\n    union distinct:\n        from a\n        from a\n"
):
    return "table a:\n" + "".join(f"    {line}\n" for line in lines) + tail


_GROUP_H1 = ("group by:", "    h1", "select:", "    h1", "    n = count()")
# Every other MySQL Float key, DISTINCT field or set column keeps main's
# whole blocker list (code, detail, suggestion and location; a lane check
# compared each with 0.1.11), and the program emits on PostgreSQL.
KEY_REFUSED = {
    **{
        name: (
            body,
            [
                _GROUP
                if name.startswith("group")
                else _DISTINCT
                if name.startswith("distinct")
                else _SET
            ],
        )
        for name, body in REFUSED_KEY_FORMS.items()
    },
    # The DISTINCT and UNION DISTINCT programs of the same class.
    "distinct_table": (
        key_body("distinct", ("f2", "kn", "f1")).replace(
            "query result", "table result"
        ),
        [_DISTINCT],
    ),
    "distinct_unread_fields": (key_body("distinct", ("h2",), "t7"), [_DISTINCT]),
    "union_query_operand": (
        key_body("union_distinct", ("h1", "h2")).replace("table a", "query a"),
        [_SET],
    ),
    "union_unread_fields": (key_body("union_distinct", ("f2", "f1"), "t7"), [_SET]),
    # Keys outside every cell: carriers, order, count, Text width, nullability.
    "group_mixed_nullability": (key_body("group", ("h1", "f1")), [_GROUP]),
    "group_text_first": (key_body("group", ("kn", "h1", "h2")), [_GROUP]),
    "group_float_text": (key_body("group", ("h1", "kn")), [_GROUP]),
    "group_four_keys": (key_body("group", ("h1", "h2", "f1", "f2")), [_GROUP]),
    "group_width_255": (key_body("group", ("h1", "kx", "h2"), "t7"), [_GROUP]),
    "group_width_32": (key_body("group", ("h1", "k3", "h2"), "t7"), [_GROUP]),
    "group_nullable_text": (key_body("group", ("h1", "kz", "h2"), "t7"), [_GROUP]),
    "group_int_key": (key_body("group", ("h1", "id")), [_GROUP]),
    # Another aggregate, clause, input, declaration or select list.
    "group_other_aggregate": (
        _grouped("from s7", *_GROUP_H1, "    m = max(id)"),
        [_GROUP],
    ),
    "group_count_argument": (
        _grouped(
            "from s7", "group by:", "    h1", "select:", "    h1", "    n = count(h2)"
        ),
        [_GROUP],
    ),
    "group_where": (_grouped("from s7", "where id > 1", *_GROUP_H1), [_GROUP]),
    "group_relation_alias": (_grouped("let s = s7", "from s", *_GROUP_H1), [_GROUP]),
    "group_named_window": (
        _grouped("from s7", "let w = window(order by id)", *_GROUP_H1),
        [_GROUP],
    ),
    "group_def": (
        _IDENT
        + _grouped(
            "from s7",
            "group by:",
            "    h1",
            "select:",
            "    x = ident(h1)",
            "    n = count()",
        ),
        [_GROUP],
    ),
    "group_def_count": (
        _IDI + _grouped("from s7", *_GROUP_H1[:4], "    n = idi(count())"),
        [_GROUP],
    ),
    "group_parameter": (_grouped("from s7", *_GROUP_H1, parameters="p: Int"), [_GROUP]),
    "group_order_by": (_grouped("from s7", *_GROUP_H1, "order by h1"), [_GROUP]),
    "group_limit": (_grouped("from s7", *_GROUP_H1, "limit 2"), [_GROUP]),
    "group_upstream": (
        "table a:\n    from s7\n    select:\n        h1\n\n"
        + _grouped("from a", *_GROUP_H1),
        [_GROUP],
    ),
    "group_join": (
        _grouped(
            "from s7",
            "inner join t7 on t7.id == s7.id",
            "group by:",
            "    s7.h1",
            "select:",
            "    h = s7.h1",
            "    n = count()",
        ),
        [_GROUP],
    ),
    "group_select_reordered": (
        _grouped(
            "from s7",
            "group by:",
            "    h1",
            "    h2",
            "select:",
            "    h2",
            "    h1",
            "    n = count()",
        ),
        [_GROUP],
    ),
    "group_count_first": (
        _grouped(
            "from s7",
            "group by:",
            "    h1",
            "    h2",
            "select:",
            "    n = count()",
            "    h1",
            "    h2",
        ),
        [_GROUP],
    ),
    "group_key_unselected": (
        _grouped(
            "from s7",
            "group by:",
            "    h1",
            "    h2",
            "select:",
            "    h1",
            "    n = count()",
        ),
        [_GROUP],
    ),
    # D77.39: count_distinct and distribution keys stay refused (window
    # keys keep their own tests in test_sql_windows.py).
    "group_count_distinct": (
        _grouped(
            "from s7",
            "group by:",
            "    kn",
            "select:",
            "    kn",
            "    n = count_distinct(f1)",
        ),
        [_COUNT_DISTINCT],
    ),
    "count_distinct_global": (
        _grouped("from s7", "select:", "    n = count_distinct(h1)"),
        [_COUNT_DISTINCT],
    ),
    "distribution_group": (
        _W
        + _grouped(
            "from w", "group by:", "    p", "select:", "    p", "    n = count()"
        ),
        [_GROUP],
    ),
    "distribution_distinct": (
        _W + _grouped("from w", "select distinct:", "    p"),
        [_DISTINCT],
    ),
    "distinct_mixed_nullability": (key_body("distinct", ("f1", "h1")), [_DISTINCT]),
    "distinct_width_255": (key_body("distinct", ("f1", "kx", "f2"), "t7"), [_DISTINCT]),
    "distinct_nullable_text": (
        key_body("distinct", ("f1", "kz", "f2"), "t7"),
        [_DISTINCT],
    ),
    "distinct_int_item": (key_body("distinct", ("f1", "id")), [_DISTINCT]),
    "distinct_where": (
        _grouped("from s7", "where id > 1", "select distinct:", "    f1"),
        [_DISTINCT],
    ),
    "distinct_order_by": (
        _grouped("from s7", "select distinct:", "    f1", "order by f1"),
        [_DISTINCT],
    ),
    "distinct_limit": (
        _grouped("from s7", "select distinct:", "    f1", "limit 2"),
        [_DISTINCT],
    ),
    "distinct_let": (
        _grouped("from s7", "let k = f1", "select distinct:", "    k"),
        [_DISTINCT],
    ),
    "distinct_relation_alias": (
        _grouped("let s = s7", "from s", "select distinct:", "    f1"),
        [_DISTINCT],
    ),
    "distinct_named_window": (
        _grouped(
            "from s7", "let w = window(order by id)", "select distinct:", "    f1"
        ),
        [_DISTINCT],
    ),
    "distinct_def": (
        _IDENT + _grouped("from s7", "select distinct:", "    x = ident(h1)"),
        [_DISTINCT],
    ),
    "distinct_parameter": (
        _grouped("from s7", "select distinct:", "    f1", parameters="p: Int"),
        [_DISTINCT],
    ),
    "distinct_same_field": (
        _grouped("from s7", "select distinct:", "    a = f1", "    b = f1"),
        [_DISTINCT],
    ),
    "distinct_literal": (
        _grouped("from s7", "select distinct:", "    f1", "    n = 1"),
        [_DISTINCT],
    ),
    "distinct_upstream": (
        "table a:\n    from s7\n    select:\n        f1\n\n"
        + _grouped("from a", "select distinct:", "    f1"),
        [_DISTINCT],
    ),
    "distinct_beside_refused": (
        _grouped("from s7", "select distinct:", "    f1", "    q = h1 / h2"),
        [("PIE-B1003", "float_division_not_realized")],
    ),
    "union_mixed_nullability": (key_body("union_distinct", ("h1", "f1")), [_SET]),
    "union_width_255": (key_body("union_distinct", ("h1", "kx", "h2"), "t7"), [_SET]),
    "union_two_tables": (
        "table b:\n    from s7\n    select:\n        h1\n"
        + _union(
            "from s7",
            "select:",
            "    h1",
            tail="query result:\n    union distinct:\n        from a\n        from b\n",
        ),
        [_SET],
    ),
    "union_three_operands": (
        key_body("union_distinct", ("h1",)) + "        from a\n",
        [_SET],
    ),
    "union_where": (_union("from s7", "where id > 1", "select:", "    h1"), [_SET]),
    "union_let": (_union("from s7", "let k = h1", "select:", "    k"), [_SET]),
    "union_relation_alias": (
        _union("let s = s7", "from s", "select:", "    h1"),
        [_SET],
    ),
    "union_def": (_IDENT + _union("from s7", "select:", "    x = ident(h1)"), [_SET]),
    "union_distinct_operand": (
        _union("from s7", "select distinct:", "    h1"),
        [_DISTINCT],
    ),
    "union_window_operand": (
        _union(
            "from s7", "select:", "    h1", "    n = row_number() window(order by id)"
        ),
        [_SET],
    ),
    # D77.08: Float INTERSECT and EXCEPT stay refused, either quantifier.
    **{
        f"{kind}_{quantifier}": (
            key_body("union_distinct", ("h1",)).replace(
                "union distinct", f"{kind} {quantifier}"
            ),
            [_SET],
        )
        for kind in ("intersect", "except")
        for quantifier in ("distinct", "all")
    },
}
# main's suggestion of each refusal above, and the line (in the body) and
# column of each one not at line 4, column 9: the first Float key or
# DISTINCT field, the count_distinct, or the set body.
_SUGGESTIONS = {
    "count_distinct_argument_outside_reviewed_int_domain": (
        "Use the aggregate's reviewed direct argument carrier, or keep it in"
        " check/plan; do not coerce its input to force emission."
    ),
    "float_division_not_realized": (
        "Use an already supported scalar form with its reviewed operand"
        " carriers, or keep this expression in check/plan. Do not use a cast"
        " or a different contract to force emission."
    ),
    "set_row_equivalence_domain_unsupported": (
        "Use Int, Bool, Text, Decimal or Float with exact matching carriers."
        " On MySQL a Float set, a window distribution result included, is"
        " limited to UNION ALL, and Timestamp to UNION ALL/DISTINCT; keep"
        " other unreviewed set carriers in check --project."
    ),
    **dict.fromkeys(
        (
            "distinct_field_comparison_domain_unsupported",
            "group_key_type_outside_reviewed_comparison_domain",
        ),
        "Use a reviewed direct projection or grouping/order/set form with"
        " matching carriers, or keep this declaration in check/plan; do not"
        " widen equality or coerce operands to force emission.",
    ),
}
_KEY_REFUSED_AT = {
    "distinct_beside_refused": (5, 9),
    "distinct_def": (7, 9),
    "distinct_let": (5, 9),
    "distinct_named_window": (5, 9),
    "distinct_relation_alias": (5, 9),
    "distinct_upstream": (9, 9),
    "distinct_where": (5, 9),
    "distribution_distinct": (10, 9),
    "distribution_group": (10, 9),
    "except_all": (6, 5),
    "except_distinct": (6, 5),
    "group_count_distinct": (7, 9),
    "group_def": (7, 9),
    "group_def_count": (7, 9),
    "group_join": (5, 9),
    "group_named_window": (5, 9),
    "group_relation_alias": (5, 9),
    "group_text_first": (5, 9),
    "group_upstream": (9, 9),
    "group_where": (5, 9),
    "intersect_all": (6, 5),
    "intersect_distinct": (6, 5),
    "union_def": (9, 5),
    "union_distinct.f": (6, 5),
    "union_distinct.ff": (7, 5),
    "union_distinct.fnf": (8, 5),
    "union_distinct.fwf": (8, 5),
    "union_distinct.h": (6, 5),
    "union_distinct.hh": (7, 5),
    "union_distinct.hnh": (8, 5),
    "union_distinct.hwh": (8, 5),
    "union_let": (7, 5),
    "union_mixed_nullability": (7, 5),
    "union_query_operand": (7, 5),
    "union_relation_alias": (7, 5),
    "union_three_operands": (6, 5),
    "union_two_tables": (10, 5),
    "union_unread_fields": (7, 5),
    "union_where": (7, 5),
    "union_width_255": (8, 5),
    "union_window_operand": (7, 5),
}
_RELEASE = (
    "PIE-B1003",
    "target_release_not_reviewed",
    'the reviewed mysql release is "8.4.12"',
    None,
    None,
)
# D77.37 rule two: main's refusal of a cell form's Float key, which the form
# reports again whenever another check refuses it.
KEY_FORM_REFUSAL = {"group.h": (*_GROUP, _SUGGESTIONS[_GROUP[1]], 4, 9)}


def refusals(outcome, body):
    """The public blockers of ``outcome``, emitted from ``body`` in its MySQL
    world, as (code, detail, suggestion, line in ``body``, column)."""
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    offset = world("mysql", body)[0].count("\n") - body.count("\n")
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    return [
        (
            item["code"],
            item["subject"]["detail"],
            item["suggestion"],
            *(
                (None, None)
                if item["location"] is None
                else (item["location"]["line"] - offset, item["location"]["column"])
            ),
        )
        for item in public["blockers"]
    ]


def key_cells(artifact):
    """The S07 cell each reader derives from its own input: emission from its
    plan, compiled replay from the bundle's records, the pure boundary from
    the emission document."""
    from pietto._project import project_completed_semantics as semantics
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled

    built = build_compiled(artifact)
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    document = pure._decode(json.loads(observed.canonical_bytes))[0]
    return (
        rows.mysql_float_key_cell(artifact.request),
        semantics._compiled_float_key_cell(root.records),
        pure._mysql_float_key_cell(pure._Doc(document)),
    )


def assert_key_cell_emits(directory, cell, body):
    """``body`` emits on MySQL the PostgreSQL statement in MySQL spelling,
    whose text with identifiers erased is the cell's probe; the live verifier
    and the pure boundary accept both; every reader derives ``cell``."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project.project_sql_emission import serialize_project_sql_emission
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    emitted = {}
    for target in ("postgres", "mysql"):
        outcome = build(directory / target, target, body)
        assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
        artifact = outcome.artifact
        assert artifact is not None
        assert verify_project_sql_emission(artifact, artifact.request).verified
        observed = portable.export_emission_observation(artifact, artifact.request)
        assert observed.canonical_bytes is not None
        assert (
            pure.parse_emission_observation(observed.canonical_bytes).status
            is pure.Status.OK
        )
        emitted[target] = artifact.rendered.sql.decode("utf-8")
    assert emitted["mysql"] == (
        emitted["postgres"].replace('"', "`").replace("`public`", "`phase66`")
    )
    assert erased(emitted["mysql"]) == _probe(cell[0], len(cell[1]))
    assert key_cells(artifact) == (cell, cell, cell)


def assert_key_refused(directory, name):
    """KEY_REFUSED ``name`` keeps main's blocker on MySQL (code, detail,
    suggestion, line and column) and emits on PostgreSQL."""
    body, ((code, detail),) = KEY_REFUSED[name]
    assert build(directory / "postgres", "postgres", body).status == "VERIFIED"
    outcome = build(directory / "mysql", "mysql", body)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert refusals(outcome, body) == [
        (code, detail, _SUGGESTIONS[detail], *_KEY_REFUSED_AT.get(name, (4, 9)))
    ]


def assert_refused_key_cell_reports_main(directory, name, monkeypatch):
    """D77.37 rule two: the cell form ``name`` refused for another reason
    reports main's whole blocker list. Under a contract naming the
    unreviewed MySQL release 8.4.11 emission_blockers (also read by the live
    verifier and guarded preparation) and the outcome give the release
    blocker and main's refusal of the Float key; refused by a check later
    than emission_blockers (row query correspondence), main's refusal."""
    from pietto._project import project_sql_emission as emission

    body, main = KEY_FORMS[name][1], KEY_FORM_REFUSAL[name]
    seen = []
    blockers = emission.emission_blockers
    monkeypatch.setattr(
        emission,
        "emission_blockers",
        lambda request: seen.append(blockers(request)) or seen[-1],
    )
    outcome = build(directory / "release", "mysql", body, "8.4.11")
    assert [(b.code, b.detail) for b in seen[0]] == [_RELEASE[:2], main[:2]]
    assert refusals(outcome, body) == [_RELEASE, main]
    monkeypatch.setattr(emission, "verify_row_query", lambda request, query: False)
    assert refusals(build(directory / "late", "mysql", body), body) == [main]


def forged_key_artifact(directory, body, monkeypatch):
    """A MySQL artifact of ``body`` with its compiled bundle and emission
    document, each made while emission (and the live verifier these run)
    took every statement for an S07 cell."""
    import _pietto_sql_emission_portable as portable
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project.project_compiled_build import build_compiled

    with monkeypatch.context() as patch:
        patch.setattr(rows, "mysql_float_key_cell", lambda request: ("group", ("H",)))
        outcome = build(directory, "mysql", body)
        artifact = outcome.artifact
        assert outcome.status == "VERIFIED" and artifact is not None
        observed = portable.export_emission_observation(artifact, artifact.request)
        assert observed.canonical_bytes is not None
        return artifact, build_compiled(artifact), observed.canonical_bytes


def assert_forged_key_refused(directory, body, monkeypatch):
    """Emission forced past the S07 cell law: the live verifier refuses the
    artifact from its plan and the pure boundary the document, each by its
    own derivation, whose tables restate emission's."""
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    artifact, _, document = forged_key_artifact(directory, body, monkeypatch)
    assert verify_project_sql_emission(artifact, artifact.request).issues == (
        "plan_ast_correspondence",
    )
    refused = pure.parse_emission_observation(document)
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "MySQL Float key cell",
    )
    assert pure._MYSQL_FLOAT_KEY_CELLS == rows.MYSQL_FLOAT_KEY_CELLS
    assert pure._MYSQL_FLOAT_KEY_CARRIERS == rows.MYSQL_FLOAT_KEY_CARRIERS


def assert_tampered_key_refused(directory, name, tamper):
    """The document of the cell form ``name``, rewritten by ``tamper`` into a
    statement no cell holds, is refused by the pure boundary."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    artifact = build(directory, "mysql", KEY_FORMS[name][1]).artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    document = json.loads(observed.canonical_bytes)
    tamper(document["records"])
    refused = pure.parse_emission_observation(json.dumps(document))
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "MySQL Float key cell",
    )
