from __future__ import annotations

from pietto.ast_nodes import TableDef
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, TypeKind, ValueTypeKind, analyze

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

    # One null bound may be FALSE: the test is a Bool the other bound decides.
    value, diagnostics = expression_facts("amount between null and 5")
    assert value.resolved_type.name == "Bool"
    assert value.nullability is EffectiveNullability.UNKNOWN
    assert diagnostics == ()
    value, diagnostics = expression_facts("created_at is null")
    assert value.resolved_type.name == "Bool"
    assert value.nullability is EffectiveNullability.NON_NULL
    assert diagnostics == ()


def test_a_null_arithmetic_operand_takes_the_type_of_the_other_operand() -> None:
    """A null operand of `+`, `-`, `*`, `/` or `%` takes the other operand's
    type, which the operator must take, and the expression stays of unknown
    type. Before, a null operand switched the operand check off, so
    `status + null` passed and emitted SQL that PostgreSQL rejects."""
    for expression in (
        "amount + null",
        "null - score",
        "price * null",
        "amount % null",
        "null / price",
        "null + null",
        "-null",
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.UNKNOWN
        assert diagnostics == (), expression

    for expression, operator, expected in (
        ("status + null", "+", "numeric operands"),
        ("null - active", "-", "numeric operands"),
        ("order_date * null", "*", "numeric operands"),
        ("score % null", "%", "Int operands"),
        ("null / status", "/", "numeric operands"),
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.UNKNOWN
        assert diagnostics == (
            (
                "PIE-S2105",
                f"Invalid operands for operator {operator}: expected {expected}",
            ),
        ), expression


def test_membership_mixes_decimal_with_int_as_its_comparisons_do() -> None:
    # `v in (a, b)` tests `v == a` and `v == b`: one canonical type, or Decimal
    # with Int (a null option then reads as Decimal); every other mix is refused.
    for expression, nullability in (
        ("price in (1, 2)", EffectiveNullability.NON_NULL),
        ("price not in (amount, -2)", EffectiveNullability.NON_NULL),
        ("amount in (price, discount)", EffectiveNullability.NULLABLE),
        ("discount in (1)", EffectiveNullability.NULLABLE),
        ("price in (1, null)", EffectiveNullability.NULLABLE),
        ("amount not in (null, price)", EffectiveNullability.NULLABLE),
        ("price in (amount + 1)", EffectiveNullability.UNKNOWN),
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.KNOWN, expression
        assert value.resolved_type.name == "Bool"
        assert value.nullability is nullability, expression
        assert diagnostics == (), expression

    for expression, operator in (
        ("price in (2.5)", "in"),
        ("score in (price)", "in"),
        ("amount in (2.5, 1)", "in"),
        ('price in (1, "x")', "in"),
        ("score not in (1)", "not in"),
        ("price in (amount, score)", "in"),
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.UNKNOWN
        assert diagnostics == (
            (
                "PIE-S2105",
                f"Invalid operands for operator {operator}: "
                "expected same canonical membership operands",
            ),
        ), expression


_ALIAS_TYPES = (
    "type Age = Int not null\n"
    "type Money = Decimal(12, 2) not null\n"
    "type Cash = Money not null\n"
    "type Ratio = Float not null\n"
    "type Flag = Bool not null\n"
    "type Doc = Json not null\n"
)
_ALIAS_FIELDS = (
    ("age", "Age", "Int"),
    ("bonus", "Age", "Int"),
    ("amount", "Money", "Decimal(12, 2)"),
    ("fee", "Money", "Decimal(12, 2)"),
    ("cash", "Cash", "Decimal(12, 2)"),
    ("ratio", "Ratio", "Float"),
    ("flag", "Flag", "Bool"),
    ("doc", "Doc", "Json"),
)


def _alias_operand_facts(
    expression: str, *, aliased: bool
) -> tuple[
    tuple[str, str, EffectiveNullability], tuple[tuple[str, str, int, int], ...]
]:
    # The base-typed program keeps the alias lines blank, so both programs
    # report at the same line and column.
    source = (
        (_ALIAS_TYPES if aliased else "\n" * _ALIAS_TYPES.count("\n"))
        + "shape Row:\n"
        + "".join(
            f"    {name}: {alias if aliased else base} not null\n"
            for name, alias, base in _ALIAS_FIELDS
        )
        + 'source rows: Row is postgres.table("rows")\n'
        + "table projected:\n    from rows\n    select:\n"
        + f"        value = {expression}\n"
    )
    script = parse_source(source).ast
    assert script is not None
    relation = script.definitions[-1]
    assert isinstance(relation, TableDef)
    result = analyze(script)
    value = result.model.expression_value_types[relation.select_items[0].expression]
    return (
        (value.resolved_type.kind.name, value.resolved_type.name, value.nullability),
        tuple(
            (d.code, d.message, d.location.line, d.location.column)
            for d in result.diagnostics
        ),
    )


def test_type_alias_operands_read_as_their_base_type() -> None:
    # Arithmetic, unary +/-, and/or and in read an alias (alias chains included)
    # as the builtin type it expands to; the result is that base type (Bool for
    # in), and every pair the base types refuse stays refused alike.
    unknown = EffectiveNullability.UNKNOWN
    non_null = EffectiveNullability.NON_NULL
    for expression, expected in (
        ("age + 1", ("BUILTIN", "Int", unknown)),
        ("1 + age", ("BUILTIN", "Int", unknown)),
        ("age - bonus", ("BUILTIN", "Int", unknown)),
        ("age * 2", ("BUILTIN", "Int", unknown)),
        ("age % 7", ("BUILTIN", "Int", unknown)),
        ("-age", ("BUILTIN", "Int", non_null)),
        ("+age", ("BUILTIN", "Int", non_null)),
        ("amount + fee", ("BUILTIN", "Decimal", unknown)),
        ("amount - 1", ("BUILTIN", "Decimal", unknown)),
        ("1 + amount", ("BUILTIN", "Decimal", unknown)),
        ("amount * fee", ("BUILTIN", "Decimal", unknown)),
        ("cash + amount", ("BUILTIN", "Decimal", unknown)),
        ("ratio * 2.5", ("BUILTIN", "Float", unknown)),
        ("age + ratio", ("BUILTIN", "Float", unknown)),
        ("flag and flag", ("BUILTIN", "Bool", unknown)),
        ("flag or flag", ("BUILTIN", "Bool", unknown)),
        ("amount in (age, 1)", ("BUILTIN", "Bool", non_null)),
        ("cash not in (bonus)", ("BUILTIN", "Bool", non_null)),
        ("age in (fee, cash)", ("BUILTIN", "Bool", non_null)),
        ("amount in (age, null)", ("BUILTIN", "Bool", EffectiveNullability.NULLABLE)),
    ):
        facts = _alias_operand_facts(expression, aliased=True)
        assert facts == (expected, ()), expression
        assert facts == _alias_operand_facts(expression, aliased=False), expression

    refused = ("UNKNOWN", "<unknown>", unknown)
    for expression, operator, operands in (
        ("amount * 2", "*", "numeric operands"),
        ("amount % 2", "%", "Int operands"),
        ("1.0 + amount", "+", "numeric operands"),
        ("-amount", "-", "numeric operand"),
        ("doc + 1", "+", "numeric operands"),
        ("flag + 1", "+", "numeric operands"),
        ("age and flag", "and", "Bool operands"),
        ("age % ratio", "%", "Int operands"),
        ("ratio in (age)", "in", "same canonical membership operands"),
        ("amount not in (ratio)", "not in", "same canonical membership operands"),
    ):
        facts = _alias_operand_facts(expression, aliased=True)
        assert facts == (
            refused,
            (
                (
                    "PIE-S2105",
                    f"Invalid operands for operator {operator}: expected {operands}",
                    20,
                    17,
                ),
            ),
        ), expression
        assert facts == _alias_operand_facts(expression, aliased=False), expression
