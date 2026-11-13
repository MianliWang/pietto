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
_TYPES = {"id": "Int", "ratio": "Float", "text": "Text"}
_SHAPES = "".join(
    f"shape {shape}:\n"
    + "".join(
        f"    {label}: {_TYPES[model]}{' | None' if nullable else ''}\n"
        for label, model, nullable, _ in fields
    )
    for shape, fields in _FIELDS.items()
)
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
)


def world(target, body):
    """The probe sources ``body`` names, then ``body``: (source, contract).

    A ``body`` that declares header parameters (``result(``) also gets the
    native parameter protocol they need."""
    contract = json.loads(
        probe.parameterized_fixture(target, "", protocol="result(" in body)["contract"]
    )
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
        header += f'source {name}: {shape} = {target}.table("{name}.locator")\n'
    contract["sources"] = sources
    return header + body, probe.encoded(contract).decode()


def build(directory, target, body):
    source, contract = world(target, body)
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
