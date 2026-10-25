from __future__ import annotations

from pietto.semantic import EffectiveNullability, TypeKind, ValueTypeKind

from _pietto_semantic_expressions import expression_facts


def test_expression_nullability_rules_preserve_current_behavior() -> None:
    for expression, type_name, nullability in (
        ("True", "Bool", EffectiveNullability.NON_NULL),
        ('"text"', "Text", EffectiveNullability.NON_NULL),
        ("1", "Int", EffectiveNullability.NON_NULL),
        ("1.5", "Float", EffectiveNullability.NON_NULL),
        ("+amount", "Int", EffectiveNullability.NON_NULL),
        ("-weight", "Float", EffectiveNullability.NULLABLE),
        ("amount + tax", "Int", EffectiveNullability.UNKNOWN),
        ("amount - tax", "Int", EffectiveNullability.UNKNOWN),
        ("amount * tax", "Int", EffectiveNullability.UNKNOWN),
        ("amount % tax", "Int", EffectiveNullability.UNKNOWN),
        ("active and active", "Bool", EffectiveNullability.UNKNOWN),
        ("active or active", "Bool", EffectiveNullability.UNKNOWN),
        ("amount > tax", "Bool", EffectiveNullability.UNKNOWN),
        ("1 <= amount <= 10", "Bool", EffectiveNullability.UNKNOWN),
        ("amount is None", "Bool", EffectiveNullability.NON_NULL),
        ("amount is not None", "Bool", EffectiveNullability.NON_NULL),
        ("lower(status)", "Text", EffectiveNullability.NON_NULL),
        ("len(status)", "Int", EffectiveNullability.NON_NULL),
        ('matches(status, "ok")', "Bool", EffectiveNullability.UNKNOWN),
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.KNOWN
        assert value.resolved_type.kind is TypeKind.BUILTIN
        assert value.resolved_type.name == type_name
        assert value.nullability is nullability
        assert diagnostics == ()


def test_declared_types_have_two_states_and_only_shapeless_fields_stay_unknown() -> (
    None
):
    from pietto.parser_api import parse_source
    from pietto.semantic import analyze
    from pietto.semantic.model import CheckMode

    parsed = parse_source(
        "shape Order:\n"
        "    id: Int\n"
        "    customer_id: Int\n"
        "shape Customer:\n"
        "    id: Int\n"
        "    name: Text\n"
        "    note: Text | None\n"
        'source orders: Order = postgres.table("orders")\n'
        'source customers: Customer = postgres.table("customers")\n'
        'source raw = postgres.table("raw")\n'
        "query joined:\n"
        "    from orders\n"
        "    let buyer = customers\n"
        "    left join buyer on buyer.id == orders.customer_id\n"
        "    select:\n"
        "        order_id = orders.id\n"
        "        name = buyer.name\n"
        "        note = buyer.note\n"
        "query unshaped:\n"
        "    from raw\n"
        "    select:\n"
        "        x = raw.x\n"
    )
    assert parsed.diagnostics == () and parsed.ast is not None

    result = analyze(parsed.ast, mode_override=CheckMode.STRICT)

    # Bare types report no implicit-nullability diagnostic in any mode.
    assert [(item.code, item.location.line) for item in result.diagnostics] == [
        ("PIE-S2303", 10)
    ]
    sources = {
        source.name: {name: field.nullability for name, field in schema.fields.items()}
        for source, schema in result.model.source_row_schemas.items()
    }
    assert sources == {
        "orders": {
            "id": EffectiveNullability.NON_NULL,
            "customer_id": EffectiveNullability.NON_NULL,
        },
        "customers": {
            "id": EffectiveNullability.NON_NULL,
            "name": EffectiveNullability.NON_NULL,
            "note": EffectiveNullability.NULLABLE,
        },
        "raw": {},
    }
    relations = {
        relation.name: {
            name: field.nullability for name, field in schema.fields.items()
        }
        for relation, schema in result.model.relation_row_schemas.items()
    }
    # The LEFT JOIN null-extends the bare `name` field of its target.
    assert relations == {
        "joined": {
            "order_id": EffectiveNullability.NON_NULL,
            "name": EffectiveNullability.NULLABLE,
            "note": EffectiveNullability.NULLABLE,
        },
        "unshaped": {"x": EffectiveNullability.UNKNOWN},
    }
