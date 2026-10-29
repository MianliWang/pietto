from __future__ import annotations

from pietto.ast_nodes import QueryDef, TableDef
from pietto.errors import Severity
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
        value, diagnostics = expression_facts(operator + "None")
        assert value.kind is ValueTypeKind.UNKNOWN
        # Check passes it; PostgreSQL cannot type `-NULL` (PIE-S2385).
        assert diagnostics == (
            (
                (
                    "PIE-S2385",
                    "Single-file SQL emission is unavailable because PostgreSQL "
                    "cannot type operator - when every operand is None; this "
                    "warning does not change check's exit status, but emit-sql "
                    "will refuse this relation.",
                ),
            )
            if operator == "-"
            else ()
        )


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
        (
            "status + status",
            "+",
            "numeric operands; string concatenation is not supported yet",
        ),
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
                assert diagnostics == (
                    (_INT_DIVISION,) if left == right == "amount" else ()
                )
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


_INT_DIVISION = (
    "PIE-S2106",
    "`/` of two Int values truncates in SQL (`7 / 2` is 3, not 3.5); "
    "write `Float(x) / y` for a fractional result",
)
_NONE_OPTION = (
    "PIE-S2107",
    "A `None` option never matches: SQL tests `x == None`, which is never true; "
    'to match None too, write `x == "a" or x is None`',
)
_NONE_NOT_IN_OPTION = (
    "PIE-S2107",
    "A `None` option makes `not in` never true: SQL tests `x != None`, which is "
    'never true; write `x != "a" and x is not None`',
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
            ("active", "None"),
            ("None", "active"),
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
        "tax <= amount <= score",
    ):
        value, diagnostics = expression_facts(expression)
        assert value.resolved_type.name == "Bool"
        assert value.nullability is EffectiveNullability.UNKNOWN
        assert diagnostics == ()

    for expression, operator in (
        ('amount == "x"', "=="),
        ("active < amount", "<"),
        ("created_at != 1", "!="),
        ('1 <= amount <= "z"', "between"),
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
        ("None == status", "==", "; write `is None` instead"),
        ("None <= amount <= None", "between", ""),
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
    value, diagnostics = expression_facts("None <= amount <= 5")
    assert value.resolved_type.name == "Bool"
    assert value.nullability is EffectiveNullability.UNKNOWN
    assert diagnostics == ()
    value, diagnostics = expression_facts("created_at is None")
    assert value.resolved_type.name == "Bool"
    assert value.nullability is EffectiveNullability.NON_NULL
    assert diagnostics == ()


def test_a_null_arithmetic_operand_takes_the_type_of_the_other_operand() -> None:
    """A null operand of `+`, `-`, `*`, `/` or `%` takes the other operand's
    type, which the operator must take, and the expression, always null, is
    of the type the operator gives two operands of that type (a quotient with
    a `Decimal` operand has none). Before, a null operand switched the operand
    check off, so `status + null` passed and emitted SQL that PostgreSQL
    rejects; and the expression stayed of unknown type, so `trim(null % f)`
    passed too."""
    for expression, type_name in (
        ("amount + None", "Int"),
        ("None - score", "Float"),
        ("price * None", "Decimal"),
        ("amount % None", "Int"),
    ):
        value, diagnostics = expression_facts(expression)
        assert (value.kind, value.resolved_type.name, value.nullability) == (
            ValueTypeKind.KNOWN,
            type_name,
            EffectiveNullability.NULLABLE,
        ), expression
        assert diagnostics == (), expression
    for expression, operator in (
        ("None / price", None),
        ("None + None", "+"),
        ("-None", "-"),
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.UNKNOWN
        # Check passes an operator over None only; PostgreSQL cannot type it.
        assert diagnostics == (
            ()
            if operator is None
            else (
                (
                    "PIE-S2385",
                    "Single-file SQL emission is unavailable because PostgreSQL "
                    f"cannot type operator {operator} when every operand is None; "
                    "this warning does not change check's exit status, but "
                    "emit-sql will refuse this relation.",
                ),
            )
        ), expression

    for expression, operator, expected in (
        (
            "status + None",
            "+",
            "numeric operands; string concatenation is not supported yet",
        ),
        ("None - active", "-", "numeric operands"),
        ("order_date * None", "*", "numeric operands"),
        ("score % None", "%", "Int operands"),
        ("None / status", "/", "numeric operands"),
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
    for expression, nullability, warnings in (
        ("price in (1, 2)", EffectiveNullability.NON_NULL, ()),
        ("price not in (amount, -2)", EffectiveNullability.NON_NULL, ()),
        ("amount in (price, discount)", EffectiveNullability.NULLABLE, ()),
        ("discount in (1)", EffectiveNullability.NULLABLE, ()),
        ("price in (1, None)", EffectiveNullability.NULLABLE, (_NONE_OPTION,)),
        (
            "amount not in (None, price)",
            EffectiveNullability.NULLABLE,
            (_NONE_NOT_IN_OPTION,),
        ),
        ("price in (amount + 1)", EffectiveNullability.UNKNOWN, ()),
    ):
        value, diagnostics = expression_facts(expression)
        assert value.kind is ValueTypeKind.KNOWN, expression
        assert value.resolved_type.name == "Bool"
        assert value.nullability is nullability, expression
        assert diagnostics == warnings, expression

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


def test_a_null_option_hides_no_option_the_value_does_not_compare_with() -> None:
    # Before: a null that operands of two types left untyped made the whole
    # list of unknown type, so these passed `check` and PostgreSQL rejected
    # `"id" IN (1, 'x', NULL)` (invalid input syntax for type bigint: "x").
    # An option the value does not compare with is now refused beside such a
    # null; one of the value's family that only the list rule refuses keeps
    # the list of unknown type, as PostgreSQL runs `"amount" IN (2.5, NULL)`,
    # and a null among options of one type is still typed by them.
    source = (
        "shape Row:\n    id: Int\n    amount: Decimal(12, 2)\n"
        "    ratio: Float | None\n    label: Text | None\n"
        'source rows: Row = postgres.table("rows")\n'
        "query q:\n    from rows\n    let k = None\n"
        '    where id in ("x", None)\n'
        "    select:\n"
        '        a = id in (1, "x", None)\n'
        "        b = amount in (2.5, None)\n"
        "        c = ratio not in (1, None, None)\n"
        '        d = id in ("x", k)\n'
        '        e = label in ("a", None)\n'
        "        f = amount in (1, None)\n"
        "        g = id in (k, 2)\n"
    )
    script = parse_source(source).ast
    assert script is not None
    result = analyze(script)

    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (
            *(
                (
                    "PIE-S2105",
                    "Invalid operands for operator in: "
                    "expected same canonical membership operands",
                )
                if warning is None
                else warning
            ),
            line,
            column,
        )
        # A list refused for its types does not warn of its None as well.
        for warning, line, column in (
            (None, 10, 11),
            (None, 12, 13),
            (_NONE_OPTION, 13, 13),
            (_NONE_NOT_IN_OPTION, 14, 13),
            (None, 15, 13),
            (_NONE_OPTION, 16, 13),
            (_NONE_OPTION, 17, 13),
        )
    ]


def test_a_text_literal_option_is_the_enum_label_or_constant_it_compares_as() -> None:
    # `status in ("paid", "shipped")` tests `status == "paid"` and
    # `status == "shipped"`, which compare an enum with its labels, and a Text
    # literal is the only constant form of a Date. Before, the list rule typed
    # each literal as Text and refused the list, while the same list with a
    # None option passed. A literal that is not a label, a Text field and a
    # Text literal against a number are still refused.
    source = (
        "enum Status: paid, shipped\n"
        "type St = Status\n"
        "shape Row:\n    id: Int\n    status: Status\n    maybe: St | None\n"
        "    born: Date\n    label: Text\n"
        'source rows: Row = postgres.table("rows")\n'
        'query q:\n    from rows\n    let p = "paid"\n'
        "    select:\n"
        '        a = status in ("paid", "shipped")\n'
        "        b = status not in (p)\n"
        '        c = maybe in ("shipped", None)\n'
        '        d = "paid" in (status, maybe)\n'
        '        e = born in ("2020-01-01", "2021-01-01")\n'
        '        f = maybe in ("paid")\n'
        '        g = status in ("paid", "gone")\n'
        '        h = status in ("paid", label)\n'
        '        i = id in ("1")\n'
    )
    script = parse_source(source).ast
    assert script is not None
    result = analyze(script)
    relation = script.definitions[-1]
    assert isinstance(relation, QueryDef)
    types = {
        item.alias: result.model.expression_value_types[item.expression]
        for item in relation.select_items
    }

    assert {
        alias: (value.resolved_type.name, value.nullability)
        for alias, value in types.items()
        if value.kind is ValueTypeKind.KNOWN
    } == {
        "a": ("Bool", EffectiveNullability.NON_NULL),
        "b": ("Bool", EffectiveNullability.NON_NULL),
        "c": ("Bool", EffectiveNullability.NULLABLE),
        "d": ("Bool", EffectiveNullability.NULLABLE),
        "e": ("Bool", EffectiveNullability.NON_NULL),
        "f": ("Bool", EffectiveNullability.NULLABLE),
    }
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (*_NONE_OPTION, 16, 13),
        *(
            (
                "PIE-S2105",
                "Invalid operands for operator in: "
                "expected same canonical membership operands",
                line,
                13,
            )
            for line in (20, 21, 22)
        ),
    ]


def test_a_division_of_two_ints_warns_that_it_truncates() -> None:
    # `/` of two Int values is Int, as in PostgreSQL, so `7 / 2` is 3 where
    # Python gives 3.5. It warns where it is written, also in a def body, and
    # not at a call of that def or a read of a `let` name bound to it.
    source = (
        "type Cents = Int\n"
        "def per(c: Int, q: Int) -> Int | None: return c / q\n"
        "shape Row:\n    id: Int\n    cents: Cents\n    qty: Int | None\n"
        "    price: Decimal(12, 2)\n    ratio: Float\n"
        'source rows: Row = postgres.table("rows")\n'
        "query q:\n    from rows\n    let unit = cents / qty\n"
        "    where id / 2 > 1\n"
        "    select:\n"
        "        id\n"
        "        a = unit\n"
        "        b = Float(cents) / qty\n"
        "        c = price / qty\n"
        "        d = ratio / 2\n"
        "        e = per(id, 3)\n"
        "        f = qty / None\n"
        "    order by:\n        id / 3\n"
    )
    script = parse_source(source).ast
    assert script is not None

    assert [
        (d.code, d.severity, d.message, d.location.line, d.location.column)
        for d in analyze(script).diagnostics
    ] == [
        (
            "PIE-S2106",
            Severity.WARNING,
            "`/` of two Int values truncates in SQL (`7 / 2` is 3, not 3.5); "
            "write `Float(x) / y` for a fractional result",
            line,
            column,
        )
        for line, column in ((2, 47), (12, 16), (13, 11), (23, 9))
    ]


def test_a_none_option_of_an_in_list_warns_that_it_never_matches() -> None:
    # `status in ("open", None)` tests `status == None`, never true in SQL,
    # so a None status is not found, and a None option makes `not in` never
    # true. A list that is refused for its types does not warn as well.
    source = (
        "def open_or_none(s: Text | None) -> Bool | None:\n"
        '    return s in ("open", None)\n'
        "shape Row:\n    id: Int\n    status: Text | None\n"
        'source rows: Row = postgres.table("rows")\n'
        "query q:\n    from rows\n"
        '    where status in ("open", None)\n'
        "    select:\n"
        "        id\n"
        '        a = status not in ("x", None, None)\n'
        '        b = status == "open" or status is None\n'
        '        c = id in (1, "x", None)\n'
        "        d = open_or_none(status)\n"
    )
    script = parse_source(source).ast
    assert script is not None
    never_matches = (
        "A `None` option never matches: SQL tests `x == None`, which is never "
        'true; to match None too, write `x == "a" or x is None`'
    )

    assert [
        (d.code, d.severity, d.message, d.location.line, d.location.column)
        for d in analyze(script).diagnostics
    ] == [
        ("PIE-S2107", Severity.WARNING, never_matches, 2, 12),
        ("PIE-S2107", Severity.WARNING, never_matches, 9, 11),
        (
            "PIE-S2107",
            Severity.WARNING,
            "A `None` option makes `not in` never true: SQL tests `x != None`, "
            'which is never true; write `x != "a" and x is not None`',
            12,
            13,
        ),
        (
            "PIE-S2105",
            Severity.ERROR,
            "Invalid operands for operator in: "
            "expected same canonical membership operands",
            14,
            13,
        ),
    ]


_ALIAS_TYPES = (
    "type Age = Int\n"
    "type Money = Decimal(12, 2)\n"
    "type Cash = Money\n"
    "type Ratio = Float\n"
    "type Flag = Bool\n"
    "type Doc = Json\n"
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
            f"    {name}: {alias if aliased else base}\n"
            for name, alias, base in _ALIAS_FIELDS
        )
        + 'source rows: Row = postgres.table("rows")\n'
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
        ("amount in (age, None)", ("BUILTIN", "Bool", EffectiveNullability.NULLABLE)),
    ):
        facts = _alias_operand_facts(expression, aliased=True)
        warnings = ((*_NONE_OPTION, 20, 17),) if "None" in expression else ()
        assert facts == (expected, warnings), expression
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
