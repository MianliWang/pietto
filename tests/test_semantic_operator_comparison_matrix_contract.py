from __future__ import annotations

from pietto.semantic import EffectiveNullability, TypeKind, ValueTypeKind

from _pietto_semantic_expressions import expression_facts


def test_unary_numeric_matrix_preserves_current_behavior() -> None:
    for field, type_name, nullability in (
        ("amount", "Int", EffectiveNullability.NON_NULL),
        ("optional_amount", "Int", EffectiveNullability.NULLABLE),
        ("score", "Float", EffectiveNullability.NON_NULL),
        ("weight", "Float", EffectiveNullability.NULLABLE),
    ):
        for operator in ("+", "-"):
            value, diagnostics = expression_facts(operator + field)
            assert value.kind is ValueTypeKind.KNOWN
            assert value.resolved_type.kind is TypeKind.BUILTIN
            assert value.resolved_type.name == type_name
            assert value.nullability is nullability
            assert diagnostics == ()

    for operator in ("+", "-"):
        for field in ("price", "discount", "status", "active"):
            value, diagnostics = expression_facts(operator + field)
            assert value.kind is ValueTypeKind.UNKNOWN
            assert value.nullability is EffectiveNullability.UNKNOWN
            assert diagnostics == (
                (
                    "PIE-S2105",
                    f"Invalid operands for operator {operator}: expected numeric operand",
                ),
            )
        value, diagnostics = expression_facts(operator + "null")
        assert value.kind is ValueTypeKind.UNKNOWN
        assert diagnostics == ()


def test_binary_numeric_decimal_modulo_and_division_matrix_preserves_behavior() -> None:
    for left, right, type_name, operators in (
        ("amount", "tax", "Int", ("+", "-", "*")),
        ("score", "weight", "Float", ("+", "-", "*")),
        ("amount", "score", "Float", ("+", "-", "*")),
        ("score", "amount", "Float", ("+", "-", "*")),
        ("price", "discount", "Decimal", ("+", "-", "*")),
        ("price", "amount", "Decimal", ("+", "-")),
        ("amount", "price", "Decimal", ("+", "-")),
    ):
        for operator in operators:
            value, diagnostics = expression_facts(f"{left} {operator} {right}")
            assert value.kind is ValueTypeKind.KNOWN
            assert value.resolved_type.kind is TypeKind.BUILTIN
            assert value.resolved_type.name == type_name
            assert value.nullability is EffectiveNullability.UNKNOWN
            assert diagnostics == ()

    value, diagnostics = expression_facts("amount % tax")
    assert value.kind is ValueTypeKind.KNOWN
    assert value.resolved_type.name == "Int"
    assert value.nullability is EffectiveNullability.UNKNOWN
    assert diagnostics == ()

    for expression, operator, expected in (
        ("price * amount", "*", "numeric operands"),
        ("amount * price", "*", "numeric operands"),
        ("score + price", "+", "numeric operands"),
        ("price - score", "-", "numeric operands"),
        ("status + status", "+", "numeric operands"),
        ("active * amount", "*", "numeric operands"),
        ("score % amount", "%", "Int operands"),
        ("amount % score", "%", "Int operands"),
        ("price % price", "%", "Int operands"),
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.UNKNOWN
        assert diagnostics == (
            (
                "PIE-S2105",
                f"Invalid operands for operator {operator}: expected {expected}",
            ),
        )

    for left in ("amount", "score", "price", "status", "active"):
        for right in ("amount", "score", "price", "status", "active"):
            value, diagnostics = expression_facts(f"{left} / {right}")
            assert value.nullability is EffectiveNullability.UNKNOWN
            if {left, right} <= {"amount", "score"}:
                # SQL division: Int / Int truncates to Int; a Float gives Float.
                assert value.kind is ValueTypeKind.KNOWN
                assert value.resolved_type.name == (
                    "Int" if left == right == "amount" else "Float"
                )
                assert diagnostics == ()
            elif {left, right} <= {"amount", "score", "price"}:
                # Decimal division keeps its deferred unknown result.
                assert value.kind is ValueTypeKind.UNKNOWN
                assert diagnostics == ()
            else:
                assert value.kind is ValueTypeKind.UNKNOWN
                assert diagnostics == (
                    (
                        "PIE-S2105",
                        "Invalid operands for operator /: expected numeric operands",
                    ),
                )


def test_bool_operator_matrix_preserves_current_behavior() -> None:
    for operator in ("and", "or"):
        value, diagnostics = expression_facts(f"active {operator} active")
        assert value.kind is ValueTypeKind.KNOWN
        assert value.resolved_type.name == "Bool"
        assert value.nullability is EffectiveNullability.UNKNOWN
        assert diagnostics == ()
        for left, right in (("active", "amount"), ("amount", "active")):
            value, diagnostics = expression_facts(f"{left} {operator} {right}")
            assert value.kind is ValueTypeKind.UNKNOWN
            assert diagnostics == (
                (
                    "PIE-S2105",
                    f"Invalid operands for operator {operator}: expected Bool operands",
                ),
            )
        for left, right in (
            ("active", "null"),
            ("null", "active"),
        ):
            value, diagnostics = expression_facts(f"{left} {operator} {right}")
            assert value.kind is ValueTypeKind.UNKNOWN
            assert diagnostics == ()


def test_comparison_between_and_is_null_boundaries_preserve_behavior() -> None:
    for expression in (
        "amount == tax",
        "amount < score",
        "price >= amount",
        "price > score",
        'status == "x"',
        "active != active",
        "order_date <= created_at",
        'created_at >= "2024-01-01"',
        "amount between tax and score",
    ):
        value, diagnostics = expression_facts(expression)
        assert value.resolved_type.name == "Bool"
        assert value.nullability is EffectiveNullability.UNKNOWN
        assert diagnostics == ()

    for expression, operator in (
        ('amount == "x"', "=="),
        ("active < amount", "<"),
        ("created_at != 1", "!="),
        ('amount between 1 and "z"', "between"),
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.UNKNOWN
        assert diagnostics == (
            (
                "PIE-S2105",
                f"Invalid operands for operator {operator}: expected comparable operands",
            ),
        )

    for expression, operator, remedy in (
        ("null == status", "==", "; write `is null` instead"),
        ("amount between null and null", "between", ""),
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.UNKNOWN
        assert diagnostics == (
            (
                "PIE-S2105",
                f"Invalid operands for operator {operator}: "
                f"comparison with null is never true{remedy}",
            ),
        )

    value, diagnostics = expression_facts("amount between null and 5")
    assert value.kind is ValueTypeKind.UNKNOWN
    assert diagnostics == ()
    value, diagnostics = expression_facts("created_at is null")
    assert value.resolved_type.name == "Bool"
    assert value.nullability is EffectiveNullability.NON_NULL
    assert diagnostics == ()
