"""The JOIN `on` `same_value` cells of Phase77 S06's null-safe JOIN unit and
their probe world (D77.41, D77.52).

Two sources, `lhs` and `rhs`, over the tables `s06ns_l` and `s06ns_r`, hold
the native qualification's fields in its order: `id` (a non-null BIGINT
Int), `v` and, by structure, `k` (a non-null BIGINT Int) or `w`; `v` and `w`
are nullable with one carrier. The representations restate the
qualification's tables. `program` writes a cell's statement (its `==`
version with ``function=False``), `contract` its emission contract, and
`refused` the programs outside every cell.
"""

import json

import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_rows as rows

TARGETS = ("postgres", "mysql")
KINDS = ("inner", "left", "right")
STRUCTURES = ("S1", "S1r", "S2", "S2r", "S3", "S4", "S5")
CARRIERS = ("int", "text", "decimal", "date", "timestamp", "uuid", "float")
# MySQL has no Float cell (O7): its `==` is refused and its `<=>` evidence only.
OPEN = tuple(
    (target, kind, structure, carrier)
    for target in TARGETS
    for kind in KINDS
    for structure in STRUCTURES
    for carrier in CARRIERS
    if (target, carrier) != ("mysql", "float")
)
NULLSAFE = {"postgres": " IS NOT DISTINCT FROM ", "mysql": " <=> "}
TYPES = {
    "int": "Int",
    "text": "Text",
    "decimal": "Decimal(12, 2)",
    "date": "Date",
    "timestamp": "Timestamp",
    "uuid": "UUID",
    "float": "Float",
}
_SAFE = {"kind": "int_range", "min": "-9007199254740993", "max": "9007199254740993"}
REPRESENTATION = {
    "postgres": {
        "int": ({"kind": "pg_int8"}, _SAFE),
        "text": (
            {"kind": "pg_text"},
            {
                "kind": "text",
                "max_characters": 64,
                "encoding": "UTF8",
                "collation": "C",
                "padding": "NO PAD",
            },
        ),
        "decimal": (
            {"kind": "pg_numeric", "precision": 12, "scale": 2},
            {"kind": "decimal", "precision": 12, "scale": 2},
        ),
        "date": ({"kind": "pg_date"}, {"kind": "date"}),
        "timestamp": (
            {"kind": "pg_timestamp", "fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "uuid": ({"kind": "pg_uuid"}, {"kind": "uuid", "encoding": "standard_bytes"}),
        "float": (
            {"kind": "pg_float8"},
            {"kind": "finite_float", "format": "binary64"},
        ),
        "bool": ({"kind": "pg_bool"}, {"kind": "bool01"}),
        "int4": (
            {"kind": "pg_int4"},
            {"kind": "int_range", "min": "-2147483648", "max": "2147483647"},
        ),
    },
    "mysql": {
        "int": ({"kind": "my_bigint"}, _SAFE),
        "text": (
            {"kind": "my_varchar", "length": 64},
            {
                "kind": "text",
                "max_characters": 64,
                "encoding": "utf8mb4",
                "collation": "utf8mb4_0900_bin",
                "padding": "NO PAD",
            },
        ),
        "decimal": (
            {"kind": "my_decimal", "precision": 12, "scale": 2},
            {"kind": "decimal", "precision": 12, "scale": 2},
        ),
        "date": ({"kind": "my_date"}, {"kind": "date"}),
        "timestamp": (
            {"kind": "my_datetime", "fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "uuid": (
            {"kind": "my_uuid_bytes"},
            {"kind": "uuid", "encoding": "standard_bytes"},
        ),
        "float": (
            {"kind": "my_double"},
            {"kind": "finite_float", "format": "binary64"},
        ),
        "bool": ({"kind": "my_bool01"}, {"kind": "bool01"}),
        "int4": (
            {"kind": "my_int"},
            {"kind": "int_range", "min": "-2147483648", "max": "2147483647"},
        ),
    },
}
EXTRA = {"S2": "k", "S2r": "k", "S3": "w", "S5": "k"}
TABLES = ("s06ns_l", "s06ns_r", "s06ns_t")


def fields(structure):
    return ("id", "v", *((EXTRA[structure],) if structure in EXTRA else ()))


def on(kind, structure, *, function=True, left="lhs", right="rhs"):
    """The ON of a structure over `o`, the preserved side (INNER: the left
    input), and `i`, the other."""
    o, i = (right, left) if kind == "right" else (left, right)

    def same(a, b, column):
        if function:
            return f"same_value({a}.{column}, {b}.{column})"
        return f"{a}.{column} == {b}.{column}"

    return {
        "S1": same(o, i, "v"),
        "S1r": same(i, o, "v"),
        "S2": f"{same(o, i, 'v')} and {o}.k == {i}.k",
        "S2r": f"{o}.k == {i}.k and {same(o, i, 'v')}",
        "S3": f"{same(o, i, 'v')} and {same(o, i, 'w')}",
        "S4": f"not {same(o, i, 'v') if function else '(' + same(o, i, 'v') + ')'}",
        "S5": f"{same(o, i, 'v')} or {o}.k == {i}.k",
    }[structure]


def select(structure, sides=("lhs", "rhs")):
    return [
        f"        {side[0]}_{name} = {side}.{name}"
        for side in sides
        for name in fields(structure)
    ]


def program(target, kind, structure, carrier, *, function=True, third=False):
    """A cell's statement: the direct JOIN, every field selected in order."""
    value = TYPES.get(carrier, "Int") + " | None"
    shape = ["shape Row:", "    id: Int", "    v: " + value]
    if EXTRA.get(structure) == "k":
        shape.append("    k: Int")
    elif EXTRA.get(structure) == "w":
        shape.append("    w: " + value)
    names = ("lhs", "rhs", "third") if third else ("lhs", "rhs")
    return (
        "\n".join(
            [
                *shape,
                *(
                    f'source {name}: Row = {target}.table("{table}")'
                    for name, table in zip(names, TABLES)
                ),
                "query result:",
                "    from lhs",
                f"    {kind} join rhs on {on(kind, structure, function=function)}",
                "    select:",
                *select(structure),
            ]
        )
        + "\n"
    )


def contract_document(target, structure, carrier, *, third=False):
    storage, domain = REPRESENTATION[target][carrier]
    key_storage = REPRESENTATION[target]["int"][0]

    def field(ordinal, name):
        if name in ("id", "k"):
            representation = {
                "storage": key_storage,
                "nullable": False,
                "domain": _SAFE,
            }
        else:
            representation = {"storage": storage, "nullable": True, "domain": domain}
        return {
            "ordinal": ordinal,
            "name": name,
            "column": name,
            "representation": representation,
        }

    names = ("lhs", "rhs", "third") if third else ("lhs", "rhs")
    mysql = target == "mysql"
    return {
        "format": "pietto.emission-contract.v1",
        "target": {"family": target, "release": "8.4.12" if mysql else "18.6"},
        "sources": [
            {
                "selector": {"module": "main.pietto", "kind": "source", "name": name},
                "relation": {
                    "namespace": "pietto_s06ns_probe" if mysql else "public",
                    "name": table,
                },
                "scan": "relation_rows",
                "premises": [
                    {"key": "row_domain_matches", "scope": "source", "value": True},
                    {"key": "read_only_object", "scope": "source", "value": True},
                ],
                "fields": [
                    field(index, item) for index, item in enumerate(fields(structure))
                ],
            }
            for name, table in zip(names, TABLES)
        ],
        "environment": [
            {
                "key": "client_encoding",
                "scope": "statement",
                "value": "utf8mb4" if mysql else "UTF8",
            },
            {
                "key": "operator_environment",
                "scope": "statement",
                "value": "builtin_only",
            },
            {
                "key": "identifier_case",
                "scope": "statement",
                "value": "lower_case_table_names=0" if mysql else "quoted_exact",
            },
        ],
    }


def contract(target, structure, carrier, *, third=False):
    document = contract_document(target, structure, carrier, third=third)
    return json.dumps(document, sort_keys=True)


def build(directory, source, contract_text, *, as_main=False):
    """The emission outcome; ``as_main`` derives it as main does, every
    Phase77 cell shut (rows.AS_MAIN)."""
    token = rows.AS_MAIN.set(True) if as_main else None
    try:
        checked, outcome = probe.build_case(directory, source, contract_text)
    finally:
        if token is not None:
            rows.AS_MAIN.reset(token)
    assert checked.verified
    return outcome


def cell(directory, target, kind, structure, carrier, *, function=True):
    return build(
        directory,
        program(target, kind, structure, carrier, function=function),
        contract(target, structure, carrier),
    )


def _field(target, ordinal, name, carrier, nullable=True):
    storage, domain = REPRESENTATION[target][carrier]
    return {
        "ordinal": ordinal,
        "name": name,
        "column": name,
        "representation": {"storage": storage, "nullable": nullable, "domain": domain},
    }


def _with(document, edit):
    edit(document)
    return json.dumps(document, sort_keys=True)


def _widened(target, carrier, nullable=True):
    """Each source gains a last field `x` of ``carrier``, never selected."""

    def edit(document):
        for item in document["sources"]:
            item["fields"].append(
                _field(target, len(item["fields"]), "x", carrier, nullable)
            )

    return edit


def _retyped(target, side, carrier, **domain):
    """One side's `v` takes ``carrier``'s representation, its domain amended."""

    def edit(document):
        storage, base = REPRESENTATION[target][carrier]
        representation = document["sources"][side]["fields"][1]["representation"]
        representation["storage"] = dict(storage, **domain.pop("storage", {}))
        representation["domain"] = dict(base, **domain)

    return edit


def _column(target, name):
    def edit(document):
        for item in document["sources"]:
            item["fields"][1]["column"] = name

    return edit


def _limits(limits):
    def edit(document):
        document["environment"].append(
            {"key": "resource_limits", "scope": "statement", "value": limits}
        )

    return edit


def membership(target):
    """`same_value` inside `any(...)` and `not any(...)`, which main already
    emits on both targets for an Int field: no JOIN `on` cell governs it."""
    base = program(target, "inner", "S1", "int")
    lines = "\n".join(select("S1", ("lhs",)))
    return {
        name: (
            base.replace(
                "    inner join rhs on same_value(lhs.v, rhs.v)\n",
                f"    where {word}any(same_value(r.v, lhs.v) for r in rhs)\n",
            ).replace("\n".join(select("S1")), lines),
            contract(target, "S1", "int"),
        )
        for name, word in (("semi", ""), ("anti", "not "))
    }


def refused(target):
    """Programs outside every cell, as {name: (source, contract)}: each keeps
    main's refusal, the whole blocker list."""
    base = program(target, "inner", "S1", "int")
    left = program(target, "left", "S1", "int")
    s2 = program(target, "inner", "S2", "int")
    paper = contract_document(target, "S1", "int")
    plain = json.dumps(paper, sort_keys=True)
    s2_contract = contract(target, "S2", "int")
    on_s1 = "inner join rhs on same_value(lhs.v, rhs.v)"
    select_s1 = "\n".join(select("S1"))
    items = {
        "full": (
            base.replace(on_s1, "full join rhs on same_value(lhs.v, rhs.v)"),
            plain,
        ),
        # Both sources over one table (C1: two different tables).
        "same_table": (
            base.replace(f'table("{TABLES[1]}")', f'table("{TABLES[0]}")'),
            _with(
                contract_document(target, "S1", "int"),
                lambda document: document["sources"][1]["relation"].update(
                    name=TABLES[0]
                ),
            ),
        ),
        "literal_operand": (
            base.replace("same_value(lhs.v, rhs.v)", "same_value(lhs.v, 1)"),
            plain,
        ),
        "computed_operand": (
            base.replace("same_value(lhs.v, rhs.v)", "same_value(lhs.v + 1, rhs.v)"),
            plain,
        ),
        "same_side_operands": (
            s2.replace("same_value(lhs.v, rhs.v)", "same_value(lhs.v, lhs.k)"),
            s2_contract,
        ),
        "bool_carrier": (
            program(target, "inner", "S1", "int").replace(
                "v: Int | None", "v: Bool | None"
            ),
            contract(target, "S1", "bool"),
        ),
        "non_null_operand": (
            base.replace("same_value(lhs.v, rhs.v)", "same_value(lhs.id, rhs.id)"),
            plain,
        ),
        "int4_carrier": (base, contract(target, "S1", "int4")),
        "text_width_1000": (
            program(target, "inner", "S1", "text"),
            _with(
                contract_document(target, "S1", "text"),
                lambda document: [
                    _retyped(
                        target,
                        side,
                        "text",
                        max_characters=1000,
                        **({"storage": {"length": 1000}} if target == "mysql" else {}),
                    )(document)
                    for side in (0, 1)
                ],
            ),
        ),
        "text_domains_differ": (
            program(target, "inner", "S1", "text"),
            _with(
                contract_document(target, "S1", "text"),
                _retyped(
                    target,
                    1,
                    "text",
                    max_characters=32,
                    **({"storage": {"length": 32}} if target == "mysql" else {}),
                ),
            ),
        ),
        "decimal_parameters_differ": (
            program(target, "inner", "S1", "decimal").replace(
                "source rhs: Row =",
                "shape Other:\n    id: Int\n    v: Decimal(10, 2) | None\n"
                "source rhs: Other =",
            ),
            _with(
                contract_document(target, "S1", "decimal"),
                _retyped(target, 1, "decimal", precision=10, storage={"precision": 10}),
            ),
        ),
        "unselected_wide_text": (
            base.replace(
                "    v: Int | None\n", "    v: Int | None\n    x: Text | None\n"
            ),
            _with(contract_document(target, "S1", "int"), _widened(target, "text")),
        ),
        "unselected_float": (
            base.replace(
                "    v: Int | None\n", "    v: Int | None\n    x: Float | None\n"
            ),
            _with(contract_document(target, "S1", "int"), _widened(target, "float")),
        ),
        "key_on_id": (
            base.replace(
                "    v: Int | None\n", "    v: Int | None\n    row_key = unique(id)\n"
            ),
            plain,
        ),
        "key_on_v": (
            base.replace(
                "    v: Int | None\n", "    v: Int | None\n    row_key = unique(v)\n"
            ),
            plain,
        ),
        "select_subset": (base.replace("        r_v = rhs.v\n", ""), plain),
        "select_reordered": (
            base.replace(
                "        l_id = lhs.id\n        l_v = lhs.v\n",
                "        l_v = lhs.v\n        l_id = lhs.id\n",
            ),
            plain,
        ),
        "select_repeated": (
            base.replace(
                "        r_v = rhs.v\n", "        r_v = rhs.v\n        again = rhs.v\n"
            ),
            plain,
        ),
        "relation_alias_let": (
            left.replace(
                "    left join rhs on same_value(lhs.v, rhs.v)\n",
                "    let r = rhs\n    left join r on same_value(lhs.v, r.v)\n",
            )
            .replace("rhs.id", "r.id")
            .replace("rhs.v", "r.v"),
            plain,
        ),
        "relation_alias_let_where": (
            left.replace(
                "    left join rhs on same_value(lhs.v, rhs.v)\n",
                "    let r = rhs\n    left join r on same_value(r.v, lhs.v)\n"
                "    where r.id is None\n",
            )
            .replace("rhs.id", "r.id")
            .replace("rhs.v", "r.v"),
            plain,
        ),
        "left_where_is_none": (
            left.replace("    select:\n", "    where rhs.id is None\n    select:\n"),
            plain,
        ),
        "left_where_other": (
            left.replace("    select:\n", "    where lhs.id > 0\n    select:\n"),
            plain,
        ),
        "chain_after_left": (
            program(target, "inner", "S1", "int", third=True).replace(
                on_s1,
                "left join rhs on lhs.id == rhs.id\n"
                "    inner join third on same_value(rhs.v, third.v)",
            ),
            contract(target, "S1", "int", third=True),
        ),
        "chain_before_equality": (
            program(target, "inner", "S1", "int", third=True).replace(
                on_s1, on_s1 + "\n    inner join third on lhs.id == third.id"
            ),
            contract(target, "S1", "int", third=True),
        ),
        **{
            f"{name}_before_join": (
                program(target, "inner", "S1", "int", third=True)
                .replace(
                    on_s1 + "\n",
                    f"where {word}any(same_value(r.v, lhs.v) for r in rhs)\n"
                    "    inner join third on lhs.id == third.id\n",
                )
                .replace(select_s1, "\n".join(select("S1", ("lhs", "third")))),
                contract(target, "S1", "int", third=True),
            )
            for name, word in (("semi", ""), ("anti", "not "))
        },
        "inner_order_by": (base + "    order by:\n        lhs.v\n", plain),
        "joined_where": (
            base.replace(
                on_s1,
                "inner join rhs on lhs.id == rhs.id\n    where same_value(lhs.v, rhs.v)",
            ),
            plain,
        ),
        "joined_let": (
            base.replace(
                on_s1,
                "inner join rhs on lhs.id == rhs.id\n"
                "    let same = same_value(lhs.v, rhs.v)\n    where same",
            ),
            plain,
        ),
        "header_parameter": (
            base.replace("query result:", "query result(x: Int):"),
            plain,
        ),
        "def_call": (
            base.replace(
                "query result:",
                "def same(a: Int | None, b: Int | None) -> Bool:\n"
                "    return same_value(a, b)\n\nquery result:",
            ).replace("same_value(lhs.v, rhs.v)", "same(lhs.v, rhs.v)"),
            plain,
        ),
        # Rule two: a cell's statement refused for another reason.
        "node_limit": (
            base,
            _with(contract_document(target, "S1", "int"), _limits({"nodes": 20})),
        ),
        "long_column": (
            base,
            _with(contract_document(target, "S1", "int"), _column(target, "c" * 65)),
        ),
        "long_label": (
            base.replace(
                "        l_id = lhs.id\n", "        " + "l" * 257 + " = lhs.id\n"
            ),
            plain,
        ),
        # Two refusals in one statement.
        "mixed": (
            base.replace("same_value(lhs.v, rhs.v)", "same_value(lhs.v, 1)").replace(
                "    v: Int | None\n", "    v: Int | None\n    x: Float | None\n"
            ),
            _with(contract_document(target, "S1", "int"), _widened(target, "float")),
        ),
    }
    if target == "mysql":
        items["mysql_float"] = (
            program(target, "inner", "S1", "float"),
            contract(target, "S1", "float"),
        )
        items["mysql_float_beside"] = (
            base.replace(
                "    v: Int | None\n", "    v: Int | None\n    f: Float | None\n"
            ).replace(
                "        r_v = rhs.v\n",
                "        r_v = rhs.v\n        same_f = lhs.f == rhs.f\n",
            ),
            _with(
                contract_document(target, "S1", "int"),
                lambda document: [
                    item["fields"].append(_field(target, 2, "f", "float"))
                    for item in document["sources"]
                ],
            ),
        )
    return items
