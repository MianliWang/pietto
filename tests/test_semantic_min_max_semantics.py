from __future__ import annotations

import pytest

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze
from pietto.semantic.catalog import BUILTIN_FUNCTIONS

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Int not null\n"
    "    score: Float not null\n"
    "    price: Decimal not null\n"
    "    order_date: Date nullable\n"
    "    created_at: Timestamp not null\n"
    "    raw: Bytes not null\n"
    "    payload: Json not null\n"
    "    id: UUID not null\n"
    "    anything: Any nullable\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_no_group_direct_aliased_min_max_int_projections_are_accepted(
    relation_kind: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + f"{relation_kind} order_extremes:\n"
        "    from orders\n"
        "    select:\n"
        "        smallest_amount = min(amount)\n"
        "        largest_amount = max(amount)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["smallest_amount", "largest_amount"]
    _assert_field(
        schema.fields["smallest_amount"], "Int", EffectiveNullability.NULLABLE
    )
    _assert_field(schema.fields["largest_amount"], "Int", EffectiveNullability.NULLABLE)
    for item in relation.select_items:
        value_type = result.model.expression_value_types[item.expression]
        _assert_field_like_value(schema.fields[item.alias or ""], value_type)


def test_no_group_min_max_accept_date_and_timestamp_arguments() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_time_extremes:\n"
        "    from orders\n"
        "    select:\n"
        "        first_order_date = min(order_date)\n"
        "        latest_created_at = max(created_at)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(
        schema.fields["first_order_date"],
        "Date",
        EffectiveNullability.NULLABLE,
    )
    _assert_field(
        schema.fields["latest_created_at"],
        "Timestamp",
        EffectiveNullability.NULLABLE,
    )


def test_qualified_min_max_field_arguments_are_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_extremes:\n"
        "    from orders\n"
        "    select:\n"
        "        first_order_date = min(orders.order_date)\n"
        "        highest_score = max(orders.score)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(
        schema.fields["first_order_date"],
        "Date",
        EffectiveNullability.NULLABLE,
    )
    _assert_field(
        schema.fields["highest_score"], "Float", EffectiveNullability.NULLABLE
    )


def test_grouped_min_max_projections_are_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table grouped_order_extremes:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        smallest_amount = min(amount)\n"
        "        latest_created_at = max(created_at)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == [
        "status",
        "smallest_amount",
        "latest_created_at",
    ]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(
        schema.fields["smallest_amount"], "Int", EffectiveNullability.NULLABLE
    )
    _assert_field(
        schema.fields["latest_created_at"],
        "Timestamp",
        EffectiveNullability.NULLABLE,
    )


@pytest.mark.parametrize(
    ("function_name", "field_name", "actual_type"),
    [
        ("min", "status", "Text"),
        ("max", "active", "Bool"),
        ("max", "raw", "Bytes"),
        ("min", "payload", "Json"),
        ("max", "id", "UUID"),
        ("min", "anything", "Any"),
    ],
)
def test_min_max_reject_unsupported_direct_field_argument_types(
    function_name: str,
    field_name: str,
    actual_type: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_extremes:\n"
            "    from orders\n"
            "    select:\n"
            f"        value = {function_name}({field_name})\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2314",
            f"Aggregate function {function_name} expects Int, Float, Decimal, "
            f"Date, or Timestamp field argument, got {actual_type}",
        )
    ]


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = min()",
            ("PIE-S2309", "Aggregate function min expects 1 arguments, got 0"),
        ),
        (
            "value = max(amount, score)",
            ("PIE-S2309", "Aggregate function max expects 1 arguments, got 2"),
        ),
        (
            "value = min(amount + amount)",
            (
                "PIE-S2315",
                "Aggregate function min requires a direct field argument; "
                "expression arguments are not supported yet",
            ),
        ),
        (
            "value = min(max(amount))",
            ("PIE-S2311", "Nested aggregate max() is not supported"),
        ),
        (
            "min(amount)",
            ("PIE-S2313", "Aggregate min() projection requires an explicit alias"),
        ),
        (
            "value = min(amount) + 1",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around min() is not supported yet",
            ),
        ),
        (
            "value = lower(min(amount))",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around min() is not supported yet",
            ),
        ),
    ],
)
def test_min_max_invalid_projection_shapes_use_existing_aggregate_diagnostics(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_extremes:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


def test_projection_alias_is_not_a_min_max_argument() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_extremes:\n"
        "    from orders\n"
        "    select:\n"
        "        subtotal = amount + amount\n"
        "        smallest_subtotal = min(subtotal)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    field = result.model.relation_row_schemas[relation].fields["smallest_subtotal"]

    assert _errors(result) == [("PIE-S2102", "Unknown field: subtotal")]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


_DIRECT_FIELD_ONLY = (
    "requires a direct field argument; expression arguments are not supported yet"
)
_TEXT_EXTREMUM = (
    "expects Int, Float, Decimal, Date, or Timestamp field argument, got Text"
)


@pytest.mark.parametrize(
    ("binding", "projection", "grouped", "expected"),
    (
        pytest.param(
            "w = amount",
            "o = max(w)",
            False,
            [("PIE-S2315", 19, 13, f"Aggregate function max {_DIRECT_FIELD_ONLY}")],
            id="field_value",
        ),
        pytest.param(
            "w = amount",
            "o = max(not w)",
            False,
            [("PIE-S2315", 19, 13, f"Aggregate function max {_DIRECT_FIELD_ONLY}")],
            id="inside_an_expression",
        ),
        pytest.param(
            "w = amount",
            "o = min(w + 1)",
            False,
            [("PIE-S2315", 19, 13, f"Aggregate function min {_DIRECT_FIELD_ONLY}")],
            id="arithmetic",
        ),
        pytest.param(
            "w = status",
            "o = max(w)",
            False,
            [("PIE-S2314", 19, 13, f"Aggregate function max {_TEXT_EXTREMUM}")],
            id="unsupported_type",
        ),
        pytest.param(
            "w = lower(status)",
            "o = min(w)",
            False,
            [("PIE-S2314", 19, 13, f"Aggregate function min {_TEXT_EXTREMUM}")],
            id="computed_unsupported_type",
        ),
        pytest.param(
            "w = null",
            "o = max(w)",
            False,
            [("PIE-S2315", 19, 13, f"Aggregate function max {_DIRECT_FIELD_ONLY}")],
            id="null",
        ),
        pytest.param(
            "w = nosuch",
            "o = max(w)",
            False,
            [("PIE-S2102", 17, 13, "Unknown field: nosuch")],
            id="binding_error_alone",
        ),
        pytest.param(
            "w = w",
            "o = max(w)",
            False,
            [("PIE-S2330", 17, 13, "Let binding cannot reference itself: w")],
            id="cyclic_binding_error_alone",
        ),
        pytest.param(
            "w = amount",
            "o = max(w)",
            True,
            [("PIE-S2315", 22, 13, f"Aggregate function max {_DIRECT_FIELD_ONLY}")],
            id="grouped",
        ),
    ),
)
def test_single_file_min_max_argument_reading_a_let_name_reports_its_value_written_in(
    binding: str,
    projection: str,
    grouped: bool,
    expected: list[tuple[str, int, int, str]],
) -> None:
    """A single file keeps the direct-field surface of `min` and `max`, so a
    `let:` name in their argument is no direct field (PIE-S2315); otherwise
    the argument is checked as the binding's value written in its place:
    `max(w)` with `w = status` is PIE-S2314 as `max(status)` is, and a binding
    with an error of its own reports only that error. Before: PIE-S2102
    `Unknown field: w` at the name."""

    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_extremes:\n"
            "    from orders\n"
            f"    let:\n        {binding}\n"
            + (
                "    group by:\n        status\n    select:\n        status\n"
                if grouped
                else "    select:\n"
            )
            + f"        {projection}\n"
        )
    )

    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in result.diagnostics
    ] == expected


def test_single_file_min_max_reads_a_let_name_by_the_shape_of_its_input_row() -> None:
    """Over a known input row, a min/max LET read is PIE-S2315 even when its
    value is a field of unknown type. Over an unknown input row, each local
    LET name is PIE-S2102. The direct field read `max(z)` stays accepted even
    when the field's type is unknown."""

    result = analyze(
        _parse(
            SOURCE_PREFIX + 'source raw is postgres.table("raw")\n'
            "table shapeless:\n"
            "    from raw\n"
            "    let:\n        w = 3\n        v = x\n"
            "    select:\n        o = max(w)\n        p = min(v)\n"
            "table untyped:\n"
            "    from orders\n"
            "    select:\n        status\n        z = null\n"
            "table untyped_through_let:\n"
            "    from untyped\n"
            "    let:\n        w = z\n"
            "    select:\n        o = max(w)\n        p = max(z)\n"
        )
    )

    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in result.diagnostics
    ] == [
        ("PIE-S2303", 14, 1, "Source raw has no bound shape; row schema is unknown"),
        ("PIE-S2102", 21, 17, "Unknown field: w"),
        ("PIE-S2102", 22, 17, "Unknown field: v"),
        ("PIE-S2315", 33, 13, f"Aggregate function max {_DIRECT_FIELD_ONLY}"),
    ]


def test_single_file_grouped_window_input_refuses_min_max_of_a_let_name_as_in_place() -> (
    None
):
    """A grouped single-file window reads the `min` of a `let:` name as the
    output schema does, refused, so a relation reading it reports what it
    reports over `min(amount + 1)` written in place. Before: PIE-S2102 for the
    name and for `w0`; then PIE-S2103 in place of the `w0` PIE-S2102."""

    def diagnostics(let_clause: str, argument: str) -> list[tuple[str, int, int, str]]:
        result = analyze(
            _parse(
                SOURCE_PREFIX + "table t1:\n"
                "    from orders\n"
                f"{let_clause}"
                "    group by:\n        status\n"
                "    select:\n"
                "        status\n"
                f"        a1 = min({argument})\n"
                "        w0 = rank() window:\n"
                "            order by:\n"
                "                status\n"
                "table t2:\n"
                "    from t1\n"
                "    select:\n"
                "        a1\n"
                "        r1 = percent_rank() window:\n"
                "            partition by:\n"
                "                w0\n"
                "            order by:\n"
                "                a1 desc\n"
            )
        )
        return [
            (d.code, d.location.line, d.location.column, d.message)
            for d in result.diagnostics
        ]

    refused = f"Aggregate function min {_DIRECT_FIELD_ONLY}"
    assert diagnostics("    let:\n        k2 = amount + 1\n", "k2") == [
        ("PIE-S2315", 22, 14, refused),
        ("PIE-S2102", 32, 17, "Unknown field: w0"),
    ]
    assert diagnostics("", "amount + 1") == [
        ("PIE-S2315", 20, 14, refused),
        ("PIE-S2102", 30, 17, "Unknown field: w0"),
    ]


def test_min_max_in_invalid_context_is_rejected() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_extremes:\n"
            "    from orders\n"
            "    where min(amount) > 0\n"
            "    select:\n"
            "        amount\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate min() is not allowed in where clause; "
            "use it only as a direct aliased select projection",
        )
    ]


def test_invalid_min_max_projection_aliases_keep_unknown_schema() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_extremes:\n"
        "    from orders\n"
        "    select:\n"
        "        value = max(status)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == [
        (
            "PIE-S2314",
            "Aggregate function max expects Int, Float, Decimal, Date, or "
            "Timestamp field argument, got Text",
        )
    ]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_count_sum_and_avg_semantics_remain_unchanged() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count()\n"
        "        amount_total = sum(amount)\n"
        "        average_score = avg(score)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["amount_total"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(
        schema.fields["average_score"], "Float", EffectiveNullability.NULLABLE
    )


def test_min_and_max_are_not_scalar_builtin_functions() -> None:
    assert "count" not in BUILTIN_FUNCTIONS
    assert "sum" not in BUILTIN_FUNCTIONS
    assert "avg" not in BUILTIN_FUNCTIONS
    assert "min" not in BUILTIN_FUNCTIONS
    assert "max" not in BUILTIN_FUNCTIONS


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
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


def _assert_field_like_value(field: object, value_type: object) -> None:
    assert (
        getattr(field, "resolved_type").name
        == getattr(
            value_type,
            "resolved_type",
        ).name
    )
    assert getattr(field, "nullability") is getattr(value_type, "nullability")
