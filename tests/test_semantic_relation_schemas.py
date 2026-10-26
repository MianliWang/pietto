from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import Node, QueryDef, Script, SourceDef, TableDef
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, RowSchema, SemanticResult, analyze
from pietto.semantic import analyzer

SOURCE = (
    "shape User:\n"
    "    id: UUID\n"
    "    email: Text | None\n"
    'source users: User = postgres.table("users")\n'
)


def test_table_from_typed_source_builds_known_schema() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        email\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    schema = result.model.relation_row_schemas[table]

    assert schema.is_unknown is False
    assert list(schema.fields) == ["id", "email"]
    assert result.diagnostics == ()


def test_query_from_typed_source_builds_known_schema() -> None:
    result = analyze(
        _parse(SOURCE + "query output:\n    from users\n    select:\n        email\n")
    )
    query = _relation(result, "output", QueryDef)

    assert list(result.model.relation_row_schemas[query].fields) == ["email"]


def test_query_from_table_uses_table_schema() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "query output:\n"
            "    from projected\n"
            "    select:\n"
            "        email\n"
        )
    )
    table = _relation(result, "projected", TableDef)
    query = _relation(result, "output", QueryDef)

    assert (
        result.model.relation_row_schemas[query].fields["email"]
        is result.model.relation_row_schemas[table].fields["email"]
    )


def test_output_field_order_and_type_information_are_preserved() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "        id\n"
        )
    )
    table = _relation(result, "projected", TableDef)
    source = _relation(result, "users", SourceDef)

    schema = result.model.relation_row_schemas[table]
    source_schema = result.model.source_row_schemas[source]

    assert list(schema.fields) == ["email", "id"]
    assert (
        schema.fields["email"].resolved_type
        is source_schema.fields["email"].resolved_type
    )
    assert schema.fields["email"].nullability is EffectiveNullability.NULLABLE
    assert schema.fields["id"].nullability is EffectiveNullability.NON_NULL


def test_unknown_selected_field_reports_p2102_and_unknown_schema() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n    from users\n    select:\n        missing\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    assert _diagnostics(result) == [
        ("PIE-S2102", Severity.ERROR, "Unknown field: missing")
    ]
    assert result.model.relation_row_schemas[table].is_unknown is True


@pytest.mark.parametrize(
    ("selected", "name", "column"),
    (
        ("total = emial", "emial", 17),
        ("first = email\n        second = first", "first", 18),
    ),
)
def test_aliased_bare_name_that_is_no_field_reports_s2102_and_unknown_schema(
    selected: str, name: str, column: int
) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    let normalized = lower(email)\n"
            "    select:\n"
            f"        {selected}\n"
            "        kept = normalized\n"
            "query downstream:\n"
            "    from projected\n"
            "    where total > 3\n"
            "    select:\n"
            "        t2 = second\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    assert [
        (code, message, diagnostic.location.column)
        for (code, _, message), diagnostic in zip(
            _diagnostics(result), result.diagnostics, strict=True
        )
    ] == [("PIE-S2102", f"Unknown field: {name}", column)]
    assert result.model.relation_row_schemas[table].is_unknown is True


_UNKNOWN_TYPED_INPUT = (
    "shape Row:\n"
    "    id: Int\n"
    "    amount: Int\n"
    "    price: Float\n"
    "    qty: Float\n"
    'source rows: Row = postgres.table("rows")\n'
    "table rates:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "        per = amount / id\n"
    "        unit_price = price / qty\n"
)


@pytest.mark.parametrize(
    ("body", "output"),
    (
        # R1: rename an input field whose type is unknown.
        ("    from rates\n    select:\n        id\n        ratio = per\n", "ratio"),
        # R4: the same through a WHERE on the renamed field.
        (
            "    from rates\n    where unit_price > 1.0\n    select:\n"
            "        id\n        p = unit_price\n",
            "p",
        ),
        # R5: an alias equal to the field name.
        ("    from rates\n    select:\n        id\n        per = per\n", "per"),
        # R9: with ORDER BY on the input field.
        (
            "    from rates\n    select:\n        id\n        ratio = per\n"
            "    order by:\n        per desc\n",
            "ratio",
        ),
        # R10: beside a window item.
        (
            "    from rates\n    select:\n        id\n        ratio = per\n"
            "        rn = row_number() window(order by id asc)\n",
            "ratio",
        ),
        # R11: through a pass-through table.
        (
            "    from passed\n    select:\n        r = per\n",
            "r",
        ),
    ),
)
def test_aliased_read_of_an_input_field_of_unknown_type_is_a_computed_output(
    body: str, output: str
) -> None:
    result = analyze(
        _parse(
            _UNKNOWN_TYPED_INPUT
            + "table passed:\n    from rates\n    select:\n        id\n        per\n"
            + "query q:\n"
            + body
        )
    )
    query = _relation(result, "q", QueryDef)
    schema = result.model.relation_row_schemas[query]

    # `amount / id` in rates divides two Int values (PIE-S2106).
    assert [
        (item.code, item.severity, item.message, item.location.line)
        for item in result.diagnostics
    ] == [
        (
            "PIE-S2106",
            Severity.WARNING,
            "`/` of two Int values truncates in SQL (`7 / 2` is 3, not 3.5); "
            "write `Float(x) / y` for a fractional result",
            11,
        ),
    ]
    assert schema.is_unknown is False
    assert output in schema.fields


def test_semantic_diagnostic_uses_canonical_code_format() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n    from users\n    select:\n        missing\n"
        )
    )

    assert result.diagnostics[0].code == "PIE-S2102"


def test_unknown_field_diagnostic_uses_expression_span() -> None:
    path = Path("examples/semantic/unknown-field.pietto")
    script = _parse(
        SOURCE + "query output:\n    from users\n    select:\n        missing\n",
        path=path,
    )
    query = script.definitions[-1]
    assert isinstance(query, QueryDef)

    diagnostic = analyze(script).diagnostics[0]

    _assert_location_matches(diagnostic, query.select_items[0].expression)


def test_duplicate_projection_reports_p2305_and_keeps_first_field() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "        email\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    assert _diagnostics(result) == [
        ("PIE-S2305", Severity.ERROR, "Duplicate projection field: email")
    ]
    assert list(result.model.relation_row_schemas[table].fields) == ["email"]


def test_duplicate_projection_diagnostic_uses_later_item_span() -> None:
    path = Path("examples/semantic/duplicate-projection.pietto")
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "        id\n",
        path=path,
    )
    table = script.definitions[-1]
    assert isinstance(table, TableDef)

    diagnostic = analyze(script).diagnostics[0]

    _assert_location_matches(diagnostic, table.select_items[1])


def test_unknown_input_schema_suppresses_field_diagnostics() -> None:
    result = analyze(
        _parse(
            'source raw = postgres.table("raw")\n'
            "table projected:\n"
            "    from raw\n"
            "    select:\n"
            "        missing\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2303"]
    assert result.model.relation_row_schemas[table].is_unknown is True


def test_unknown_from_target_produces_unknown_schema_without_field_cascade() -> None:
    result = analyze(
        _parse(
            "query output:\n"
            "    from missing_relation\n"
            "    select:\n"
            "        missing_field\n"
        )
    )
    query = _relation(result, "output", QueryDef)

    assert [
        (
            diagnostic.code,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
        )
        for diagnostic in result.diagnostics
    ] == [("PIE-S2301", "Unknown relation: missing_relation", 2, 5)]
    assert result.model.relation_row_schemas[query].is_unknown is True


def test_mixed_projections_validate_names_without_checking_calls() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    where unknown_predicate(missing_field)\n"
            "    select:\n"
            "        lower(email)\n"
            "        normalized = unknown_call(missing_field)\n"
            "        missing\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    assert _diagnostics(result) == [
        ("PIE-S2102", Severity.ERROR, "Unknown field: missing_field"),
        (
            "PIE-S2304",
            Severity.WARNING,
            "Computed projection requires an explicit alias",
        ),
        ("PIE-S2102", Severity.ERROR, "Unknown field: missing_field"),
        ("PIE-S2102", Severity.ERROR, "Unknown field: missing"),
    ]
    assert result.model.relation_row_schemas[table].is_unknown is True
    assert list(result.model.relation_row_schemas[table].fields) == [
        "normalized",
        "missing",
    ]


def test_unknown_upstream_schema_suppresses_downstream_field_diagnostics() -> None:
    result = analyze(
        _parse(
            SOURCE + "table first:\n"
            "    from users\n"
            "    select:\n"
            "        missing\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        another_missing\n"
        )
    )
    second = _relation(result, "second", QueryDef)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert result.model.relation_row_schemas[second].is_unknown is True


def test_relation_cycles_produce_unknown_schemas_with_cycle_diagnostic() -> None:
    result = analyze(
        _parse(
            "table first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "table second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n"
        )
    )
    first = _relation(result, "first", TableDef)
    second = _relation(result, "second", TableDef)

    assert result.model.relation_row_schemas[first].is_unknown is True
    assert result.model.relation_row_schemas[second].is_unknown is True
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2302"]


@pytest.mark.parametrize("reverse", [False, True])
def test_a_long_chain_of_computed_tables_is_refined_in_linear_work(
    reverse: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Each table computes its output from the one before, so refinement types
    # one more table per pass. Before, every pass typed every table again.
    count = 150
    tables = [
        f"table t{index}:\n    from t{index - 1}\n    select:\n        a = a + 1\n"
        for index in range(1, count + 1)
    ]
    source = (
        "shape T:\n    a: Int\n"
        'source t0: T = postgres.table("t0")\n'
        + "".join(reversed(tables) if reverse else tables)
        + f"table last:\n    from t{count}\n    select:\n        b = missing\n"
    )
    typed_tables: list[int] = []
    type_relation_expressions = analyzer.type_relation_expressions

    def counted(script: Script, **arguments: Any) -> Any:
        typed_tables.append(
            sum(isinstance(item, TableDef) for item in script.definitions)
        )
        return type_relation_expressions(script, **arguments)

    monkeypatch.setattr(analyzer, "type_relation_expressions", counted)
    result = analyze(_parse(source))

    for index in range(1, count + 1):
        table = _relation(result, f"t{index}", TableDef)
        field = result.model.relation_row_schemas[table].fields["a"]
        assert (field.resolved_type.name, field.nullability) == (
            "Int",
            EffectiveNullability.UNKNOWN,
        )
    assert [
        (diagnostic.code, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in result.diagnostics
    ] == [("PIE-S2102", 4 * count + 7, 13)]
    assert sum(typed_tables) < 4 * (count + 1)


def test_relation_row_schema_mapping_is_readonly() -> None:
    result = analyze(
        _parse(SOURCE + "table projected:\n    from users\n    select:\n        id\n")
    )
    table = _relation(result, "projected", TableDef)

    with pytest.raises(TypeError):
        result.model.relation_row_schemas[table] = RowSchema()  # type: ignore[index]


def test_relation_schema_propagation_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table projected:\n    from users\n    select:\n        id\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_relation_schema_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query output:\n"
            "    from projected\n"
            "    select:\n"
            "        id\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation[RelationT: (SourceDef, TableDef, QueryDef)](
    result: SemanticResult,
    name: str,
    expected_type: type[RelationT],
) -> RelationT:
    definition = result.model.relation_symbols[name]
    assert isinstance(definition, expected_type)
    return definition


def _diagnostics(
    result: SemanticResult,
) -> list[tuple[str, Severity, str]]:
    return [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ]


def _assert_location_matches(diagnostic: Diagnostic, node: Node) -> None:
    span = node.span
    assert diagnostic.location.path == span.path
    assert diagnostic.location.line == span.line
    assert diagnostic.location.column == span.column
    assert diagnostic.location.end_line == span.end_line
    assert diagnostic.location.end_column == span.end_column


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)


@pytest.mark.parametrize("target_first", [False, True])
def test_join_target_projection_types_propagate_through_forward_dependencies(
    target_first: bool,
) -> None:
    target = (
        "table named_users:\n"
        "    from users\n"
        "    select:\n"
        "        uid = id\n"
        "        address = upper(email)\n"
    )
    consumer = (
        "table matched_users:\n"
        "    from users\n"
        "    let peer = named_users\n"
        "    inner join peer on users.id == peer.uid\n"
        "    select:\n"
        "        address = peer.address\n"
    )
    result = analyze(
        _parse(
            SOURCE
            + (target + consumer if target_first else consumer + target)
            + "query output:\n"
            "    from matched_users\n"
            "    select:\n"
            "        address\n"
        )
    )

    assert result.diagnostics == ()
    for name in ("named_users", "matched_users", "output"):
        relation = result.model.relation_symbols[name]
        assert isinstance(relation, (TableDef, QueryDef))
        schema = result.model.relation_row_schemas[relation]
        assert not schema.is_unknown
        assert not schema.joined
        assert schema.fields["address"].name == "address"
        assert schema.fields["address"].resolved_type.name == "Text"
        assert schema.fields["address"].nullability is EffectiveNullability.NULLABLE


def test_refused_join_has_no_projected_fields_for_downstream_let_shadowing() -> None:
    result = analyze(
        _parse(
            SOURCE + "table refused:\n"
            "    from users\n"
            "    inner join missing on users.id == missing.id\n"
            "    select:\n"
            "        out = users.id\n"
            "query output:\n"
            "    from refused\n"
            "    let out = 1\n"
            "    select:\n"
            "        value = out\n"
        )
    )
    relation = _relation(result, "refused", TableDef)
    assert result.model.relation_row_schemas[relation] == RowSchema(is_unknown=True)
    assert [
        (
            diagnostic.code,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
        )
        for diagnostic in result.diagnostics
    ] == [("PIE-S2301", "Unknown relation: missing", 7, 5)]
