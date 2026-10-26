"""PIE-S2385 warns only for completed single-file emission blockers."""

from __future__ import annotations

import pytest

from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze


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


@pytest.mark.parametrize(
    "condition",
    (
        "True",
        "rows.text == other.text or True",
        "rows.id == rows.id",
    ),
)
def test_full_join_warning_needs_a_direct_cross_input_equality(condition: str) -> None:
    result = _analyze(
        _PREFIX
        + f"""query q:
    from rows
    let other = rows
    full join other on {condition}
    select id = rows.id
"""
    )

    assert not [item for item in result if item.code == "PIE-S2385"]


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
