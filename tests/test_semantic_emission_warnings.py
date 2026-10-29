"""PIE-S2385 warns only for completed single-file emission blockers."""

from __future__ import annotations

import pytest

from pietto.errors import Severity
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.postgres import emit_postgres_sql


_PREFIX = """shape Row:
    id: Int
    value: Int | None
    text: Text | None
    label: Text | None
source rows: Row = postgres.table("rows")
"""


@pytest.mark.parametrize(
    "body",
    [
        "first = first_value(value) window(order by id range 2 preceding)",
        "previous = lag(value) ignore nulls window(order by id)",
        "last = nth_value(value, 1) from last window(order by id)",
    ],
)
def test_window_emission_blockers_warn_without_failing_check(body: str) -> None:
    result = _analyze(_PREFIX + "query q:\n    from rows\n    select " + body + "\n")

    assert [(item.code, item.severity) for item in result] == [
        ("PIE-S2385", Severity.WARNING)
    ]


def test_selected_aggregate_range_offset_warns() -> None:
    result = _analyze(
        _PREFIX
        + """query q:
    from rows
    select value = sum(id) window(order by id range 1 preceding)
"""
    )

    assert [(item.code, item.severity) for item in result] == [
        ("PIE-S2385", Severity.WARNING)
    ]


def test_hidden_qualify_aggregate_range_offset_warns() -> None:
    result = _analyze(
        _PREFIX
        + """query q:
    from rows
    select id
    qualify sum(id) window(order by id range 1 preceding) > 0
"""
    )

    assert [(item.code, item.severity) for item in result] == [
        ("PIE-S2385", Severity.WARNING)
    ]


def test_mixed_window_families_keep_every_range_warning_in_source_order() -> None:
    result = _analyze(
        _PREFIX
        + """query q:
    from rows
    select:
        old = first_value(value) window(order by id range 1 preceding)
        first = sum(id) window(order by id range 2 preceding)
        second = avg(id) window(order by id range 3 preceding)
"""
    )

    warnings = [item for item in result if item.code == "PIE-S2385"]
    assert len(warnings) == 3
    assert [(item.location.line, item.location.column) for item in warnings] == sorted(
        (item.location.line, item.location.column) for item in warnings
    )


def test_invalid_hidden_aggregate_range_preserves_its_error_without_a_warning() -> None:
    result = _analyze(
        _PREFIX
        + """query q:
    from rows
    select id
    qualify sum(id) window(order by id range 9223372036854775808 preceding) > 0
"""
    )

    assert [item.code for item in result] == ["PIE-S2104"]


def test_full_join_text_equality_warns_but_other_join_errors_remain_errors() -> None:
    source = (
        _PREFIX
        + """query q:
    from rows
    let other = rows
    full join other on rows.text == other.text
    select id = rows.id
"""
    )

    result = _analyze(source)

    assert [(item.code, item.severity) for item in result] == [
        ("PIE-S2385", Severity.WARNING)
    ]


def test_full_join_warns_for_each_noncanonical_equality_in_a_positive_and() -> None:
    result = _analyze(
        _PREFIX
        + """query q:
    from rows
    let other = rows
    full join other on rows.id == other.id and rows.text == other.text and rows.label == other.label
    select id = rows.id
"""
    )

    assert [item.code for item in result] == ["PIE-S2385", "PIE-S2385"]


@pytest.mark.parametrize(
    ("alias", "field_type"),
    (
        ("Key = Int", "Key"),
        ("Key = Int", "Key | None"),
        ("Middle = Key", "Middle"),
    ),
)
def test_full_join_canonical_int_alias_does_not_warn(
    alias: str, field_type: str
) -> None:
    aliases = "type Key = Int\n" if alias == "Middle = Key" else ""
    result = _analyze(
        aliases
        + f"type {alias}\n"
        + f"""shape AliasRow:
    id: {field_type}
source left: AliasRow = postgres.table("left")
source right: AliasRow = postgres.table("right")
query q:
    from left
    let other = right
    full join other on left.id == other.id
    select id = left.id
"""
    )

    assert not [item for item in result if item.code == "PIE-S2385"]


_FULL_FORM = (
    "this FULL JOIN condition is not an equality between Int fields of its two sides"
)
_FULL_TYPES = "this FULL JOIN equality is not between canonical Int fields"


# PostgreSQL emits a FULL JOIN only when each `and` conjunct of its `on`
# equates an Int field of the target with an Int field of an earlier input.
@pytest.mark.parametrize(
    ("condition", "expected"),
    (
        ("True", [(24, _FULL_FORM)]),
        ("rows.text == other.text or True", [(24, _FULL_FORM)]),
        ("rows.id == rows.id", [(24, _FULL_FORM)]),
        ("other.id == other.id", [(24, _FULL_FORM)]),
        ("rows.id < other.id", [(24, _FULL_FORM)]),
        ("rows.id + 1 == other.id", [(24, _FULL_FORM)]),
        ("not (rows.id != other.id)", [(24, _FULL_FORM)]),
        ("rows.id == other.id and rows.value > 3", [(48, _FULL_FORM)]),
        ('rows.id == other.id and other.text == "x"', [(48, _FULL_FORM)]),
        ("rows.text == other.text and rows.id == other.id", [(24, _FULL_TYPES)]),
        ("rows.id == other.id", []),
        ("other.value == rows.id and rows.id == other.id", []),
    ),
)
def test_full_join_warns_for_each_conjunct_postgresql_cannot_join_on(
    condition: str, expected: list[tuple[int, str]]
) -> None:
    result = _analyze(
        _PREFIX
        + f"""query q:
    from rows
    let other = rows
    full join other on {condition}
    select id = rows.id
"""
    )

    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in result
    ] == [("PIE-S2385", 10, column, _message(detail)) for column, detail in expected]


@pytest.mark.parametrize(
    ("before", "expected"),
    (
        ("    where any(s.id == rows.id for s in rows)\n", True),
        ("    where not any(s.id == rows.id for s in rows)\n", True),
        # A RIGHT JOIN takes the pending filter into its ON.
        (
            "    where any(s.id == rows.id for s in rows)\n"
            "    let r = rows\n    right join r on r.id == rows.id\n",
            False,
        ),
    ),
)
def test_full_join_after_a_pending_any_filter_warns(
    before: str, expected: bool
) -> None:
    source = (
        _PREFIX
        + "query q:\n    from rows\n"
        + before
        + "    let other = rows\n    full join other on rows.id == other.id\n"
        + "    select id = rows.id\n"
    )
    line = source.splitlines().index("    full join other on rows.id == other.id") + 1

    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in _analyze(source)
    ] == (
        [
            (
                "PIE-S2385",
                line,
                5,
                _message(
                    "a `where any(...)` or `where not any(...)` filter comes before "
                    "this FULL JOIN"
                ),
            )
        ]
        if expected
        else []
    )


def test_full_join_reads_a_relationship_call_as_its_body() -> None:
    source = (
        "shape Row:\n    id: Int\n    text: Text\n"
        'source rows: Row = postgres.table("rows")\n'
        "relationship Same(a: Row, b: Row):\n    a.id == b.id\n"
        'relationship Tagged(a: Row, b: Row):\n    a.id == b.id and b.text == "x"\n'
        "query native:\n    from rows\n    let other = rows\n"
        "    full join other on Same(rows, other)\n    select id = rows.id\n"
        "query filtered:\n    from rows\n    let other = rows\n"
        "    full join other on Tagged(rows, other)\n    select id = rows.id\n"
    )

    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in _analyze(source)
    ] == [("PIE-S2385", 17, 24, _message(_FULL_FORM))]


_NULLS = """shape Row:
    id: Int
    text: Text
source rows: Row = postgres.table("rows")
query q:
    from rows
    let z = None
    let y = z
    let unread = None + None
    select:
"""
_TEXT_NULL = "PostgreSQL types a CASE, coalesce or nullif of only None values as text"


# Each expression the SQL renders, a `let:` name read as its value; line 11.
@pytest.mark.parametrize(
    ("item", "column", "detail"),
    (
        (
            "x = None + None",
            13,
            "PostgreSQL cannot type operator + when every operand is None",
        ),
        ("x = -y", 13, "PostgreSQL cannot type operator - when every operand is None"),
        (
            "x = z * y",
            13,
            "PostgreSQL cannot type operator * when every operand is None",
        ),
        (
            "x = id + (None - None)",
            19,
            "PostgreSQL cannot type operator - when every operand is None",
        ),
        (
            "x = coalesce(None, None) + 1",
            13,
            f"{_TEXT_NULL}, which operator + does not take",
        ),
        (
            "x = not coalesce(None, None)",
            13,
            f"{_TEXT_NULL}, which operator not does not take",
        ),
        (
            "x = abs(nullif(None, None))",
            13,
            f"{_TEXT_NULL}, which function abs does not take",
        ),
        (
            "x = 1 if coalesce(None, None) else 2",
            13,
            f"{_TEXT_NULL}, which a condition does not take",
        ),
        (
            "x = 1 if id > 0 else coalesce(None, None)",
            13,
            f"{_TEXT_NULL}, and a conditional has no common type for text and Int",
        ),
        (
            "x = id == coalesce(None, None)",
            13,
            f"{_TEXT_NULL}, and operator == has no common type for text and Int",
        ),
        (
            "x = id in (coalesce(None, None), 2)",
            13,
            f"{_TEXT_NULL}, and operator in has no common type for text and Int",
        ),
        (
            "x = coalesce(coalesce(None, None), 1)",
            13,
            f"{_TEXT_NULL}, and coalesce has no common type for text and Int",
        ),
        (
            "x = any(o.id == None + None for o in rows)",
            25,
            "PostgreSQL cannot type operator + when every operand is None",
        ),
        (
            "x = substr(text, 3000000000, 2)",
            13,
            "this substr index is outside PostgreSQL's 32-bit integer range",
        ),
        (
            "x = lag(id, 3000000000) window(order by id)",
            13,
            "this lag integer argument is outside PostgreSQL's 32-bit integer range",
        ),
        (
            "x = ntile(3000000000) window(order by id)",
            13,
            "this ntile integer argument is outside PostgreSQL's 32-bit integer range",
        ),
        (
            "x = Float(id if (None or id > 0) else id)",
            13,
            "PostgreSQL emission converts only a value known to be Int to Float or Text",
        ),
        ("x = Float(id if id > 0 else None)", None, None),
        ("x = text == coalesce(None, None)", None, None),
        ("x = None and None", None, None),
        ("x = id + None", None, None),
        ("x = substr(text, 2147483647, 2)", None, None),
    ),
)
def test_expressions_postgresql_cannot_type_warn(
    item: str, column: int | None, detail: str | None
) -> None:
    for dialect in ("postgres", "mysql"):
        source = _NULLS.replace("postgres.", f"{dialect}.") + f"        {item}\n"

        assert [
            (found.code, found.location.line, found.location.column, found.message)
            for found in _analyze(source)
        ] == (
            [("PIE-S2385", 11, column, _message(detail))]
            if dialect == "postgres" and detail is not None
            else []
        )


def test_null_conditions_warn_where_they_filter() -> None:
    result = _analyze(
        _NULLS.replace("    select:\n", "")
        + "    where coalesce(None, None)\n    select id\n"
    )

    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in result
    ] == [
        (
            "PIE-S2385",
            10,
            11,
            _message(f"{_TEXT_NULL}, which a condition does not take"),
        )
    ]


_QUALIFY_READ = "`n` is an untyped all-None output that its QUALIFY stage reads"
_QUALIFY_REFUSED = (
    "PostgreSQL types a NULL output that its QUALIFY stage reads as text, "
    "which Pietto leaves untyped"
)
_CONDITION_REFUSED = (
    "PostgreSQL types a CASE, COALESCE or NULLIF of only NULL values as text, "
    "which a condition does not take"
)


# QUALIFY reads the SELECT outputs through a derived table, whose NULL outputs
# PostgreSQL types as text, as it does a CTE's, and its predicate is a
# condition. Before: check was silent and PostgreSQL emission returned SQL
# that PostgreSQL rejects (`WHERE "n" = 1`, `WHERE COALESCE(NULL, NULL)`).
@pytest.mark.parametrize(
    ("item", "predicate", "location", "detail", "refusal"),
    (
        ("n = None", "n == 1", (11, 13), _QUALIFY_READ, _QUALIFY_REFUSED),
        (
            "n = None if id > 0 else None",
            "n + 1 > 2 and id > 0",
            (11, 13),
            _QUALIFY_READ,
            _QUALIFY_REFUSED,
        ),
        ("n = coalesce(None, None)", "n", (11, 13), _QUALIFY_READ, _QUALIFY_REFUSED),
        (
            "n = id",
            "coalesce(None, None)",
            (13, 9),
            f"{_TEXT_NULL}, which a condition does not take",
            _CONDITION_REFUSED,
        ),
        (
            "n = id",
            "nullif(z, y)",
            (13, 9),
            f"{_TEXT_NULL}, which a condition does not take",
            _CONDITION_REFUSED,
        ),
    ),
)
def test_qualify_reads_of_null_values_warn_where_postgresql_refuses(
    item: str,
    predicate: str,
    location: tuple[int, int],
    detail: str,
    refusal: str,
) -> None:
    for dialect in ("postgres", "mysql"):
        source = _NULLS.replace("postgres.", f"{dialect}.") + (
            f"        {item}\n    qualify:\n        {predicate}\n"
        )
        parsed = parse_source(source, path="input.pietto")
        assert parsed.ast is not None
        result = analyze(parsed.ast)

        assert [
            (found.code, found.location.line, found.location.column, found.message)
            for found in result.diagnostics
        ] == (
            [("PIE-S2385", *location, _message(detail))]
            if dialect == "postgres"
            else []
        )
        assert result.script is not None
        lowered = build_ir(result.script, result.model)
        assert lowered.ir is not None
        if dialect == "postgres":
            assert [
                (found.code, found.message)
                for found in emit_postgres_sql(lowered.ir).diagnostics
            ] == [
                (
                    "PIE-B1000",
                    "PostgreSQL SQL emission is not implemented for RelationIR: q. "
                    + refusal,
                )
            ]
        else:
            emitted = emit_mysql_sql(lowered.ir)
            assert emitted.diagnostics == ()
            assert len(emitted.artifacts) == 1


# A statement defines each relation it reads as a CTE, which takes the place
# of a table named without a schema in the CTEs after it and the main SELECT.
@pytest.mark.parametrize(
    ("table", "warned"),
    (("items", True), ("public.items", False), ("Items", False)),
)
def test_a_cte_that_would_hide_a_table_read_warns(table: str, warned: bool) -> None:
    source = (
        "shape Row:\n    id: Int\n"
        'source raw: Row = postgres.table("raw")\n'
        f'source listed: Row = postgres.table("{table}")\n'
        "table items:\n    from raw\n    select:\n        id\n"
        "query reader:\n    from listed\n"
        "    where any(i.id == listed.id for i in items)\n    select:\n        id\n"
        "query own:\n    from items\n    select:\n        id\n"
    )

    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in _analyze(source)
    ] == (
        [
            (
                "PIE-S2385",
                9,
                1,
                _message(
                    "its SQL defines relation items as a CTE, which would hide table "
                    "items read in the same SQL"
                ),
            )
        ]
        if warned
        else []
    )


def test_a_relation_with_an_error_gets_no_cte_warning() -> None:
    source = (
        "shape Row:\n    id: Int\n"
        'source raw: Row = postgres.table("raw")\n'
        'source listed: Row = postgres.table("items")\n'
        "table items:\n    from raw\n    select:\n        id\n"
        "query reader:\n    from listed\n"
        "    where any(i.id == listed.id for i in items)\n    select:\n"
        "        x = nosuch\n"
    )

    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in _analyze(source)
    ] == [("PIE-S2102", 13, 13, "Unknown field: nosuch")]


# PostgreSQL emission counts a field of a built-in type only; a field typed by
# a shape, also through an alias or a `let` name, passes check and warns.
@pytest.mark.parametrize(
    ("call", "warned"),
    (
        ("count(home)", True),
        ("count(h)", True),
        ("count(place)", True),
        ("count(id)", False),
        ("count()", False),
    ),
)
def test_a_count_of_a_shape_typed_field_warns(call: str, warned: bool) -> None:
    for dialect in ("postgres", "mysql"):
        source = (
            "shape Address:\n    city: Text\ntype Place = Address\n"
            "shape Row:\n    id: Int\n    home: Address | None\n    place: Place\n"
            f'source rows: Row = {dialect}.table("rows")\n'
            "query q:\n    from rows\n    let h = home\n    select:\n"
            f"        n = {call}\n"
        )
        parsed = parse_source(source, path="input.pietto")
        assert parsed.ast is not None
        result = analyze(parsed.ast)
        assert [
            (item.code, item.location.line, item.location.column, item.message)
            for item in result.diagnostics
        ] == (
            [
                (
                    "PIE-S2385",
                    13,
                    13,
                    _message(
                        "PostgreSQL emission counts only a field of a built-in "
                        "type, not one of a shape"
                    ),
                )
            ]
            if warned and dialect == "postgres"
            else []
        )
        if dialect == "postgres":
            assert result.script is not None
            lowered = build_ir(result.script, result.model)
            assert lowered.ir is not None
            assert [
                item.code for item in emit_postgres_sql(lowered.ir).diagnostics
            ] == (["PIE-B1000"] if warned else [])


def _message(detail: str) -> str:
    return (
        f"Single-file SQL emission is unavailable because {detail}; this warning "
        "does not change check's exit status, but emit-sql will refuse this relation."
    )


@pytest.mark.parametrize(
    "value",
    ("None", "None if id > 0 else None", "coalesce(None, None)", "nullif(None, None)"),
)
def test_downstream_relation_read_of_all_null_output_warns(value: str) -> None:
    source = (
        _PREFIX
        + f"""table produced:
    from rows
    select value = {value}
query read:
    from produced
    select value
"""
    )

    result = _analyze(source)

    assert [(item.code, item.severity) for item in result] == [
        ("PIE-S2385", Severity.WARNING)
    ]


@pytest.mark.parametrize(
    ("connector", "warned"), [("postgres.table", True), ("mysql.table", False)]
)
def test_only_a_postgresql_file_warns_for_a_read_of_an_all_null_output(
    connector: str, warned: bool
) -> None:
    """MySQL emission keeps an untyped NULL output; PostgreSQL types it as text."""

    source = _PREFIX.replace("postgres.table", connector) + (
        "table produced:\n    from rows\n    select value = None\n"
        "query read:\n    from produced\n    select value\n"
    )

    result = _analyze(source)

    assert [(item.code, item.severity) for item in result] == (
        [("PIE-S2385", Severity.WARNING)] if warned else []
    )


def test_all_null_output_warns_for_join_target_and_multi_hop_reader() -> None:
    source = (
        _PREFIX
        + """table produced:
    from rows
    select value = None
table bridge:
    from produced
    select value
query joined:
    from rows
    let p = produced
    cross join p
    select id = rows.id
query final:
    from bridge
    select value
"""
    )

    result = _analyze(source)

    assert [(item.code, item.severity) for item in result] == [
        ("PIE-S2385", Severity.WARNING)
    ]


def test_all_null_outputs_follow_admitted_lets_and_implicit_names() -> None:
    source = (
        _PREFIX
        + """table produced:
    from rows
    let absent = None
    let nested = nullif(None, None)
    select:
        out = absent
        nested_out = nested if id > 0 else coalesce(None, None)
table implicit:
    from rows
    let empty = None
    select empty
query reader:
    from produced
    select out, nested_out
query implicit_reader:
    from implicit
    select empty
"""
    )

    result = _analyze(source)

    assert [(item.code, item.severity) for item in result] == [
        ("PIE-S2385", Severity.WARNING),
        ("PIE-S2385", Severity.WARNING),
        ("PIE-S2385", Severity.WARNING),
    ]


@pytest.mark.parametrize(
    "bindings, output",
    (
        ("    let empty = None\n", "coalesce(empty, empty)"),
        ("    let empty = None\n", "empty if id > 0 else empty"),
        (
            "    let empty = None\n    let left = empty\n    let right = empty\n",
            "coalesce(left, right)",
        ),
    ),
)
def test_all_null_output_keeps_repeated_and_diamond_let_reads(
    bindings: str, output: str
) -> None:
    result = _analyze(
        _PREFIX
        + "table produced:\n    from rows\n"
        + bindings
        + f"    select out = {output}\n"
        + "query reader:\n    from produced\n    select out\n"
    )

    assert [(item.code, item.severity) for item in result] == [
        ("PIE-S2385", Severity.WARNING)
    ]


def test_all_null_warning_keeps_an_independent_error_and_ignores_typed_or_unread() -> (
    None
):
    source = (
        _PREFIX
        + """table produced:
    from rows
    select:
        value = None
        bad = missing
table typed:
    from rows
    select value = None if id > 0 else id
table unread:
    from rows
    select value = None
query reader:
    from produced
    select value
query typed_reader:
    from typed
    select value
"""
    )

    result = _analyze(source)

    assert [item.code for item in result] == ["PIE-S2385", "PIE-S2102"]


def test_all_null_warning_does_not_follow_an_erroneous_let_dependency() -> None:
    source = (
        _PREFIX
        + """table produced:
    from rows
    let broken = missing
    select out = None if broken else None
query reader:
    from produced
    select out
"""
    )

    result = _analyze(source)

    assert [item.code for item in result] == ["PIE-S2102"]


def test_reserved_user_nullif_name_never_becomes_an_emission_warning() -> None:
    result = _analyze(
        _PREFIX
        + """def nullif(value: Int) -> Int: return value
query q:
    from rows
    select value = nullif(id)
"""
    )

    assert [item.code for item in result] == ["PIE-S2398"]


def _analyze(source: str):
    parsed = parse_source(source, path="input.pietto")
    assert parsed.ast is not None, parsed.diagnostics
    return analyze(parsed.ast).diagnostics
