from __future__ import annotations

from pietto.semantic import EffectiveNullability, TypeKind, ValueTypeKind

from _pietto_semantic_expressions import expression_facts


def test_expression_nullability_rules_preserve_current_behavior() -> None:
    for expression, type_name, nullability in (
        ("true", "Bool", EffectiveNullability.NON_NULL),
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
        ("amount between 1 and 10", "Bool", EffectiveNullability.UNKNOWN),
        ("amount is null", "Bool", EffectiveNullability.NON_NULL),
        ("amount is not null", "Bool", EffectiveNullability.NON_NULL),
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
