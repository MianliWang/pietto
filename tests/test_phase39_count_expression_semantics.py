from __future__ import annotations

import pytest

from pietto.ast_nodes import CallExpr, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze

SOURCE_PREFIX = (
    "enum Status:\n"
    "    active\n"
    "    paused\n"
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    enum_status: Status not null\n"
    "    active: Bool not null\n"
    "    optional_active: Bool nullable\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float nullable\n"
    "    payload: Json not null\n"
    "    raw: Bytes not null\n"
    "    id: UUID not null\n"
    "    anything: Any nullable\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize(
    ("projection", "expected_argument_type", "expected_nullability"),
    [
        ("known_values = count(amount + tax)", "Int", EffectiveNullability.UNKNOWN),
        ("known_values = count(amount + 1)", "Int", EffectiveNullability.UNKNOWN),
        ("known_values = count(+amount)", "Int", EffectiveNullability.NON_NULL),
        ("known_values = count(amount % tax)", "Int", EffectiveNullability.UNKNOWN),
        ("known_values = count(score * weight)", "Float", EffectiveNullability.UNKNOWN),
        ("known_values = count(lower(status))", "Text", EffectiveNullability.UNKNOWN),
        ("known_values = count(trim(status))", "Text", EffectiveNullability.UNKNOWN),
        ("known_values = count(len(status))", "Int", EffectiveNullability.UNKNOWN),
        (
            "known_values = count(active and true)",
            "Bool",
            EffectiveNullability.UNKNOWN,
        ),
        (
            "known_values = count(active or optional_active)",
            "Bool",
            EffectiveNullability.UNKNOWN,
        ),
    ],
)
def test_no_group_count_expression_arguments_are_semantically_accepted(
    projection: str,
    expected_argument_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_counts:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )
    relation = _relation(result)
    expression = relation.select_items[0].expression
    assert isinstance(expression, CallExpr)
    argument = expression.arguments[0]
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(schema.fields["known_values"], "Int", EffectiveNullability.NON_NULL)
    _assert_value_type(
        result.model.expression_value_types[expression],
        "Int",
        EffectiveNullability.NON_NULL,
    )
    _assert_value_type(
        result.model.expression_value_types[argument],
        expected_argument_type,
        expected_nullability,
    )


def test_grouped_count_expression_arguments_are_semantically_accepted() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table grouped_order_counts:\n"
            "    from orders\n"
            "    group by:\n"
            "        region\n"
            "    select:\n"
            "        region\n"
            "        known_amounts = count(amount + tax)\n"
            "        known_statuses = count(lower(status))\n"
            "        known_active = count(active and optional_active)\n"
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == [
        "region",
        "known_amounts",
        "known_statuses",
        "known_active",
    ]
    _assert_field(schema.fields["region"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["known_amounts"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(
        schema.fields["known_statuses"],
        "Int",
        EffectiveNullability.NON_NULL,
    )
    _assert_field(schema.fields["known_active"], "Int", EffectiveNullability.NON_NULL)


def test_qualified_field_leaves_count_as_resolved_direct_input_leaves() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_counts:\n"
            "    from orders\n"
            "    select:\n"
            "        known_values = count(orders.amount + 1)\n"
            "        known_statuses = count(lower(orders.status))\n"
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(schema.fields["known_values"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(
        schema.fields["known_statuses"],
        "Int",
        EffectiveNullability.NON_NULL,
    )


@pytest.mark.parametrize(
    "projection",
    [
        "known_values = count(1)",
        'known_values = count("x")',
        "known_values = count(true)",
        "known_values = count(1 + 2)",
        "known_values = count(amount > 1)",
        "known_values = count(amount between 1 and 10)",
        "known_values = count(amount is null)",
        "known_values = count(anything is null)",
        "known_values = count(enum_status is null)",
        'known_values = count(matches(status, "active"))',
    ],
)
def test_literal_only_and_leaf_policy_risks_remain_deferred(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_counts:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2315",
            "Aggregate function count requires a direct field argument; "
            "expression arguments are deferred",
        )
    ]


def test_projection_alias_leaf_still_uses_unresolved_field_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_counts:\n"
            "    from orders\n"
            "    select:\n"
            "        subtotal = amount + tax\n"
            "        known_values = count(subtotal + tax)\n"
        )
    )
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields["known_values"]

    assert _errors(result) == [("PIE-S2102", "Unknown field: subtotal")]
    assert field.resolved_type.kind is TypeKind.UNKNOWN


def test_direct_any_and_enum_count_field_rejections_remain_unchanged() -> None:
    for projection in (
        "known_values = count(anything)",
        "known_values = count(enum_status)",
    ):
        result = analyze(
            _parse(
                SOURCE_PREFIX + "table order_counts:\n"
                "    from orders\n"
                "    select:\n"
                f"        {projection}\n"
            )
        )

        assert _errors(result) == [
            (
                "PIE-S2314",
                "Aggregate function count expects concrete non-Any field argument, "
                f"got {'Any' if 'anything' in projection else 'Status'}",
            )
        ]


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "known_values = count(count())",
            ("PIE-S2311", "Nested aggregate count() is not supported"),
        ),
        (
            "known_values = count(amount) + 1",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around count() is deferred",
            ),
        ),
    ],
)
def test_nested_aggregate_and_composition_diagnostics_are_preserved(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_counts:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


def test_count_expression_inside_satisfying_remains_invalid_context() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table grouped_order_counts:\n"
            "    from orders\n"
            "    group by:\n"
            "        region\n"
            "    select:\n"
            "        region\n"
            "        known_values = count(amount + tax)\n"
            "    satisfying:\n"
            "        count(amount + tax) > 0\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate count() is not allowed in satisfying clause; "
            "use it only as a direct aliased select projection",
        )
    ]


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(result: SemanticResult) -> TableDef | QueryDef:
    relation = next(iter(result.model.relation_row_schemas))
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_field(
    field: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(field, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(field, "resolved_type").name == expected_type
    assert getattr(field, "nullability") is expected_nullability


def _assert_value_type(
    value_type: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(value_type, "resolved_type").name == expected_type
    assert getattr(value_type, "nullability") is expected_nullability
