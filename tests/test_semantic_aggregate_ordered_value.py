"""`first` and `last`: the value of a direct field at the first or last
member row of a group in an order that ends in a unique key (Phase74 S12).

Its order is proven total statically: each key is a direct field that is
never None (by type or a top-level WHERE conjunct `k is not None`), and the
keys with the field GROUP BY keys that are never None cover one `unique(...)`
of the FROM source. A single file and a schema_version = 2 project report the
same diagnostics; a schema_version = 1 project refuses the call."""

from __future__ import annotations

import json

import pytest

from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

PREFIX = """shape Sale:
    id: Int
    shop_id: Int
    seq: Int
    customer_id: Int | None
    plant: Text
    pot: Text | None
    price_cents: Int
    weight: Float | None
    discount: Decimal(12, 2)
    paid: Bool
    flagged: Bool | None
    sold_at: Timestamp
    day: Date
    token: UUID
    sale_key = unique(id)
    shop_seq = unique(shop_id, seq)
    customer_seq = unique(customer_id, seq)
shape Shop:
    id: Int
    name: Text
    shop_key = unique(id)
source sales: Sale = postgres.table("nursery.sales")
source shops: Shop = postgres.table("nursery.shops")
"""
LINE = PREFIX.count("\n") + 6  # the line of `_grouped`'s call


def _grouped(call: str, *, where: str = "", key: str = "shop_id") -> str:
    return (
        f"query q:\n    from sales\n{where}    group by {key}\n    select:\n"
        f"        {key}\n        v = {call}\n"
    )


def _analyze(body: str) -> SemanticResult:
    parsed = parse_source(PREFIX + body)
    assert parsed.diagnostics == () and parsed.ast is not None, parsed.diagnostics
    return analyze(parsed.ast)


def _rows(result: SemanticResult) -> list[tuple[str, int, int | None, str, str | None]]:
    return [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.message,
            item.suggestion,
        )
        for item in result.diagnostics
    ]


def _output(result: SemanticResult, name: str = "v") -> tuple[str, str]:
    (schema,) = (
        schema
        for definition, schema in result.model.relation_row_schemas.items()
        if definition.name == "q"
    )
    field = schema.fields[name]
    return field.resolved_type.name, field.nullability.value


@pytest.mark.parametrize(
    ("call", "expected"),
    [
        ("first(plant, order by sold_at, id)", ("Text", "non_null")),
        ("last(plant, order by sold_at, id)", ("Text", "non_null")),
        ("first(pot, order by sold_at, id)", ("Text", "nullable")),
        ("first(price_cents, order by id)", ("Int", "non_null")),
        ("last(discount, order by id)", ("Decimal", "non_null")),
        ("first(weight, order by id)", ("Float", "nullable")),
        ("first(paid, order by id)", ("Bool", "non_null")),
        ("last(flagged, order by id)", ("Bool", "nullable")),
        ("first(day, order by id desc)", ("Date", "non_null")),
        ("first(sold_at, order by price_cents desc, id)", ("Timestamp", "non_null")),
        ("last(token, order by sold_at, sales.id)", ("UUID", "non_null")),
    ],
)
def test_a_grouped_first_or_last_has_its_fields_type(
    call: str, expected: tuple[str, str]
) -> None:
    result = _analyze(_grouped(call))

    assert result.diagnostics == ()
    assert _output(result) == expected


def test_without_group_by_the_value_may_be_none() -> None:
    result = _analyze(
        "query q:\n    from sales\n    select:\n"
        "        v = first(plant, order by sold_at, id)\n        n = count()\n"
    )

    assert result.diagnostics == ()
    assert _output(result) == ("Text", "nullable")


@pytest.mark.parametrize(
    ("call", "where", "key"),
    [
        # The field GROUP BY keys seed the walk: (shop_id, seq) is unique.
        ("first(plant, order by seq)", "", "shop_id"),
        ("last(plant, order by sold_at, seq)", "", "shop_id"),
        ("first(plant, order by seq, sold_at)", "", "shop_id"),
        # A key after a complete unique key never changes the order.
        ("first(plant, order by id, sold_at)", "", "shop_id"),
        # A top-level WHERE conjunct proves a key never None.
        (
            "first(plant, order by weight, id)",
            "    where paid and weight is not None\n",
            "shop_id",
        ),
        (
            "first(plant, order by sales.weight desc, sales.id)",
            "    where sales.weight is not None\n",
            "shop_id",
        ),
        # ... and so a nullable field GROUP BY key.
        (
            "first(plant, order by seq)",
            "    where customer_id is not None\n",
            "customer_id",
        ),
    ],
)
def test_an_order_that_ends_in_a_unique_key_is_admitted(
    call: str, where: str, key: str
) -> None:
    assert _rows(_analyze(_grouped(call, where=where, key=key))) == []


def test_a_let_name_of_a_field_reads_as_that_field() -> None:
    result = _analyze(
        "query q:\n    from sales\n    let t = sold_at\n    let w = weight\n"
        "    let p = pot\n    let known = w is not None\n    where known\n"
        "    group by shop_id\n    select:\n        shop_id\n"
        "        v = first(p, order by t, w, id)\n"
    )

    assert result.diagnostics == ()
    assert _output(result) == ("Text", "nullable")


_NOT_UNIQUE = (
    "The order of {name} does not end in a unique key, so rows that tie have no "
    "promised order"
)
_UNIQUE_HINT = (
    "end the `order by` with the fields of a `unique(...)` key of its source, "
    "such as `id`"
)
_NONE_HINT = (
    "add `{key} is not None` to the query's `where` as a top-level `and` test, "
    "or order by a key that is never None"
)


def _refusal(code: str, column: int, message: str, hint: str | None = None):
    return (
        code,
        LINE,
        column,
        message if hint is None else f"{message}; {hint}",
        hint,
    )


@pytest.mark.parametrize(
    ("call", "where", "key", "expected"),
    [
        (
            "first(plant)",
            "",
            "shop_id",
            _refusal(
                "PIE-S2104",
                13,
                "Invalid arguments for aggregate first: expected ORDER BY key",
                "a group's rows have no order: write `first(x, order by k, id)`",
            ),
        ),
        (
            "last(plant, order by sold_at)",
            "",
            "shop_id",
            _refusal("PIE-S2104", 13, _NOT_UNIQUE.format(name="last"), _UNIQUE_HINT),
        ),
        # A nullable GROUP BY key does not count: NULL keys repeat.
        (
            "first(plant, order by seq)",
            "",
            "customer_id",
            _refusal("PIE-S2104", 13, _NOT_UNIQUE.format(name="first"), _UNIQUE_HINT),
        ),
        (
            "first(plant, order by weight, id)",
            "",
            "shop_id",
            _refusal(
                "PIE-S2104",
                35,
                "Order key weight of first may be None, and None has no promised "
                "place in the order",
                _NONE_HINT.format(key="weight"),
            ),
        ),
        # Only a top-level `and` conjunct proves it.
        (
            "first(plant, order by weight, id)",
            "    where weight is not None or paid\n",
            "shop_id",
            _refusal(
                "PIE-S2104",
                35,
                "Order key weight of first may be None, and None has no promised "
                "place in the order",
                _NONE_HINT.format(key="weight"),
            ),
        ),
        (
            "first(plant, order by price_cents + 1, id)",
            "",
            "shop_id",
            _refusal("PIE-S2104", 35, "Order key of first must be a direct field"),
        ),
        (
            "first(lower(plant), order by id)",
            "",
            "shop_id",
            _refusal(
                "PIE-S2315",
                13,
                "Aggregate function first requires a direct field argument; "
                "expression arguments are not supported yet",
            ),
        ),
        (
            "first(o.plant for o in group)",
            "",
            "shop_id",
            _refusal(
                "PIE-S2334",
                13,
                "first takes no generator",
                "write `first(x, order by k, id)`",
            ),
        ),
        (
            "max(price_cents, order by id)",
            "",
            "shop_id",
            _refusal(
                "PIE-S2104",
                13,
                "Internal ORDER BY is only supported by string_agg, first and last",
            ),
        ),
    ],
    ids=[
        "no_order",
        "not_unique",
        "nullable_group_key",
        "nullable_key",
        "nullable_key_or",
        "expression_key",
        "expression_value",
        "generator",
        "other_aggregate_order",
    ],
)
def test_each_refused_order_or_value_is_one_diagnostic(
    call: str, where: str, key: str, expected: tuple
) -> None:
    body = _grouped(call, where=where, key=key)
    line = LINE + where.count("\n")
    assert _rows(_analyze(body)) == [(expected[0], line, *expected[2:])]


def test_an_enum_value_is_refused_by_type() -> None:
    result = _analyze(
        "enum Size:\n    small\n    large\nshape Pot:\n    id: Int\n    size: Size\n"
        '    pot_key = unique(id)\nsource pots: Pot = postgres.table("pots")\n'
        "query q:\n    from pots\n    select:\n"
        "        v = first(size, order by id)\n"
    )

    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-S2314",
            "Aggregate function first expects Bool, Int, Float, Decimal, Text, "
            "Date, Timestamp, or UUID field argument, got Size",
        )
    ]


def test_an_input_whose_fields_are_not_known_is_refused() -> None:
    """No key of a source without a shape, or of a query over one, is proven
    a field, never None or unique."""
    text = (
        'source raw = postgres.table("x.raw")\n'
        "query q:\n    from raw\n    group by shop_id\n    select:\n"
        "        shop_id\n        v = first(plant, order by sold_at)\n"
        "query base:\n    from raw\n    select:\n        id\n        plant\n"
        "query later:\n    from base\n    select:\n"
        "        v = last(plant, order by id)\n"
    )
    parsed = parse_source(text)
    assert parsed.ast is not None
    unknown = (
        "The order of {name} reads an input whose fields are not known, so rows "
        "that tie have no promised order"
    )
    shape_hint = (
        "give its source a shape with a `unique(...)` key and end the `order by` "
        "with its fields"
    )
    source_hint = (
        "last reads the `unique(...)` keys of a source: read the source with "
        "`from`, not a table or query"
    )
    assert [row for row in _rows(analyze(parsed.ast)) if row[0] != "PIE-S2303"] == [
        (
            "PIE-S2104",
            7,
            13,
            f"{unknown.format(name='first')}; {shape_hint}",
            shape_hint,
        ),
        (
            "PIE-S2104",
            16,
            13,
            f"{unknown.format(name='last')}; {source_hint}",
            source_hint,
        ),
    ]


def test_join_rows_and_a_query_input_are_refused() -> None:
    result = _analyze(
        "query q:\n    from sales\n    let s = shops\n"
        "    inner join s on s.id == sales.shop_id\n    group by s.name\n"
        "    select:\n        name = s.name\n"
        "        v = first(sales.plant, order by sales.id)\n"
        "query base:\n    from sales\n    select:\n        id\n        plant\n"
        "query later:\n    from base\n    select:\n"
        "        v = last(plant, order by id)\n"
    )

    join_hint = "join in one query, then group it in another that reads it with `from`"
    source_hint = (
        "last reads the `unique(...)` keys of a source: read the source with "
        "`from`, not a table or query"
    )
    assert _rows(result) == [
        (
            "PIE-S2334",
            LINE + 2,
            13,
            f"first over JOIN rows is not available yet; {join_hint}",
            join_hint,
        ),
        (
            "PIE-S2104",
            LINE + 11,
            13,
            f"{_NOT_UNIQUE.format(name='last')}; {source_hint}",
            source_hint,
        ),
    ]


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        # One diagnostic: the window admits no internal ORDER BY.
        (
            "v = first(plant, order by id) window(partition by shop_id)",
            [
                (
                    "PIE-S2104",
                    "Internal ORDER BY is not supported in a window; for one value "
                    "per group, drop the `window(...)`",
                    "for one value per group, drop the `window(...)`",
                )
            ],
        ),
        (
            "v = last(plant) window(partition by shop_id)",
            [
                (
                    "PIE-S2103",
                    "Aggregate window functions are not implemented: last; window "
                    "aggregates are sum, count, avg, min and max",
                    None,
                )
            ],
        ),
        # Two independent defects, as before.
        (
            "v = max(price_cents, order by id) window(partition by shop_id)",
            [
                ("PIE-S2104", "Internal ORDER BY is not supported in a window", None),
                (
                    "PIE-S2104",
                    "Internal ORDER BY is only supported by string_agg, first and last",
                    None,
                ),
            ],
        ),
        (
            'v = string_agg(plant, ",", order by id) window(partition by shop_id)',
            [("PIE-S2104", "Internal ORDER BY is not supported in a window", None)],
        ),
    ],
)
def test_a_window_form_reports_its_window_refusal(item: str, expected: list) -> None:
    result = _analyze(
        f"query q:\n    from sales\n    select:\n        id\n        {item}\n"
    )

    assert [
        (row.code, row.message, row.suggestion) for row in result.diagnostics
    ] == expected


def test_a_first_outside_a_select_item_is_an_aggregate_out_of_place() -> None:
    result = _analyze(
        'query q:\n    from sales\n    where first(plant, order by id) == "x"\n'
        "    select:\n        id\n"
    )

    assert [(row.code, row.message) for row in result.diagnostics] == [
        (
            "PIE-S2308",
            "Aggregate first() is not allowed in where clause; use it only as a "
            "direct aliased select projection",
        )
    ]


@pytest.mark.parametrize(
    ("name", "hint"),
    [
        *(
            (
                name,
                "Pietto never picks an arbitrary row; write `first(x, order by k, id)`",
            )
            for name in ("any_value", "nth", "head", "ANY_VALUE")
        ),
        *(
            (
                name,
                "write `first(x, order by v desc, id)`; numpy and polars `argmax` "
                "return a position, not a value",
            )
            for name in ("arg_max", "argmax", "max_by", "idxmax")
        ),
        *(
            (name, "write `first(x, order by v, id)`")
            for name in ("arg_min", "argmin", "min_by", "idxmin")
        ),
    ],
)
def test_an_arbitrary_row_or_arg_max_habit_names_first(name: str, hint: str) -> None:
    result = _analyze(_grouped(f"{name}(plant, price_cents)"))

    assert _rows(result)[0] == (
        "PIE-S2103",
        LINE,
        13,
        f"Unknown function: {name}; {hint}",
        hint,
    )


@pytest.mark.parametrize("name", ["first", "last"])
def test_a_def_named_first_or_last_must_be_renamed(name: str) -> None:
    result = _analyze(
        f"def {name}(x: Int) -> Int:\n    return x + 1\n"
        "query q:\n    from sales\n    select:\n        id\n"
    )

    adjective = "first" if name == "first" else "last"
    assert _rows(result) == [
        (
            "PIE-S2398",
            PREFIX.count("\n") + 1,
            1,
            f"Def {name} has the name of a built-in function; a def cannot shadow one",
            f"Rename this def: `{name}` is now the built-in ordered {adjective}-value "
            f"aggregate, and a call to {name} always means it.",
        )
    ]


def _joined(call: str) -> str:
    return (
        "query q:\n    from sales\n    let s = shops\n"
        "    inner join s on s.id == sales.shop_id\n    group by s.name\n"
        f"    select:\n        name = s.name\n        v = {call}\n"
    )


# A call with an error inside it, of its value or of an order key, reports
# that error alone: no order proof or JOIN refusal follows it.
TWO_DEFECT_BODIES = (
    (
        _grouped("first(plant, order by sold_att, id)"),
        [("PIE-S2102", LINE, 35, "Unknown field: sold_att")],
    ),
    (
        _joined("first(lower(sales.plant), order by sales.id)"),
        [
            (
                "PIE-S2315",
                LINE + 2,
                13,
                "Aggregate function first requires a direct field argument",
            )
        ],
    ),
    (
        _joined("first(sales.plant, order by sales.sold_att)"),
        [("PIE-S2102", LINE + 2, 41, "Unknown field: sales.sold_att")],
    ),
    (
        _joined('string_agg(sales.plant, ",", order by sales.sold_att)'),
        [("PIE-S2102", LINE + 2, 51, "Unknown field: sales.sold_att")],
    ),
    # The rule is per call: the next call of the relation is still proven.
    (
        _grouped("first(plant, order by sold_att, id)")
        + "        w = last(plant, order by sold_at)\n",
        [
            ("PIE-S2102", LINE, 35, "Unknown field: sold_att"),
            ("PIE-S2104", LINE + 1, 13, _NOT_UNIQUE.format(name="last")),
        ],
    ),
)


@pytest.mark.parametrize(("body", "expected"), TWO_DEFECT_BODIES)
def test_a_call_with_an_error_inside_it_reports_that_error_alone(
    body: str, expected: list
) -> None:
    # Each message up to its first `; `, which starts a hint.
    assert [row[:3] + (row[3].split("; ")[0],) for row in _rows(_analyze(body))] == (
        expected
    )


PROJECT_BODIES = (
    _grouped("first(plant, order by sold_at, id)")
    + _grouped(
        "last(pot, order by weight, id)", where="    where weight is not None\n"
    ).replace("query q:", "query r:"),
    _grouped("first(plant, order by sold_at)"),
    _grouped("first(plant, order by weight, id)"),
    _grouped("first(plant)"),
    _grouped("first(o.plant for o in group)"),
    _joined("first(sales.plant, order by sales.id)"),
    *(body for body, _ in TWO_DEFECT_BODIES),
    # A `let:` name in the call, which a project reads otherwise: a computed
    # value or key, or a key the proof refuses, is the file's diagnostic alone.
    _grouped("last(k, order by id)", where="    let k = lower(plant)\n"),
    "query q:\n    from sales\n    let k = lower(plant)\n    select:\n"
    "        v = last(k, order by id)\n",
    _grouped("first(plant, order by k, id)", where="    let k = lower(plant)\n"),
    _grouped("last(plant, order by t)", where="    let t = sold_at\n"),
    _grouped("last(plant, order by w, id)", where="    let w = weight\n"),
)


@pytest.mark.parametrize("body", PROJECT_BODIES)
def test_a_schema_version_2_project_reports_what_a_file_does(
    tmp_path, capsys, body: str
) -> None:
    from pietto import cli

    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (tmp_path / "main.pietto").write_text(PREFIX + body)
    found = []
    for argv in (
        ["check", "--project", str(tmp_path), "--format", "json"],
        ["check", str(tmp_path / "main.pietto"), "--format", "json"],
    ):
        code = cli.main(argv)
        found.append(
            (
                code,
                [
                    (
                        row["code"],
                        row["location"]["line"],
                        row["location"]["column"],
                        row["message"],
                        row["suggestion"],
                    )
                    for row in json.loads(capsys.readouterr().out)["diagnostics"]
                ],
            )
        )
    assert found[0] == found[1]
    assert (found[0][0] == 0) is (body == PROJECT_BODIES[0])


def test_a_schema_version_1_project_has_no_first_or_last(tmp_path, capsys) -> None:
    from pietto import cli

    (tmp_path / "pietto.toml").write_text(
        'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (tmp_path / "main.pietto").write_text(
        PREFIX
        + _grouped("first(plant, order by sold_at, id)")
        + _grouped("last(plant)").replace("query q:", "query r:")
    )

    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 1
    assert [
        (row["code"], row["location"]["line"], row["message"])
        for row in json.loads(capsys.readouterr().out)["diagnostics"]
    ] == [
        (
            "PIE-S2334",
            line,
            f"{name}(...): a schema_version = 1 project has no {name}(...) in the "
            "current syntax; set schema_version = 2 to check it.",
        )
        for name, line in (("first", LINE), ("last", LINE + 6))
    ]
