from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    BetweenExpr,
    CastExpr,
    CallExpr,
    ConditionalExpr,
    ComparisonExpr,
    Expression,
    IsNullExpr,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    Script,
    SourceDef,
    TableDef,
    UnaryExpr,
)
from pietto import cli
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    CheckMode,
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)
from pietto.semantic.expressions import type_relation_expressions
from pietto.semantic.row_lookup import (
    bare_candidates,
    bare_field,
    has_bare_field,
    qualified_field,
)

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text nullable\n"
    'source users: User is postgres.table("users")\n'
)
Q1_SOURCE = (
    "shape User:\n"
    "    count: Int not null\n"
    "    name: Text nullable\n"
    "    active: Bool nullable\n"
    'source users: User is postgres.table("users")\n'
)


@pytest.mark.parametrize(
    ("literal", "python_type", "type_name"),
    [
        ('"hello"', str, "Text"),
        ("42", int, "Int"),
        ("1.5", float, "Float"),
        ("true", bool, "Bool"),
    ],
)
def test_literal_expression_maps_to_builtin_type(
    literal: str,
    python_type: type[object],
    type_name: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            f"    where {literal}\n"
            "    select:\n"
            "        id\n"
        )
    )
    expression = _where_expression(result)
    assert isinstance(expression, LiteralExpr)
    assert isinstance(expression.value, python_type)

    value_type = result.model.expression_value_types[expression]

    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.resolved_type.name == type_name
    assert value_type.nullability is EffectiveNullability.NON_NULL


def test_bare_field_uses_row_field_type_and_nullability() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n    from users\n    select:\n        email\n"
        )
    )
    table = _table(result)
    expression = table.select_items[0].expression
    assert isinstance(expression, NameExpr)
    row_field = result.model.relation_row_schemas[table].fields["email"]

    value_type = result.model.expression_value_types[expression]

    assert value_type.resolved_type is row_field.resolved_type
    assert value_type.nullability is EffectiveNullability.NULLABLE
    assert value_type.kind is ValueTypeKind.KNOWN


def test_unknown_bare_field_reports_pie_s2102_and_records_unknown() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n    from users\n    select:\n        missing\n"
        )
    )
    expression = _table(result).select_items[0].expression

    assert [
        (diagnostic.code, diagnostic.severity) for diagnostic in result.diagnostics
    ] == [("PIE-S2102", Severity.ERROR)]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_unknown_input_schema_suppresses_unknown_field_diagnostic() -> None:
    result = analyze(
        _parse(
            'source raw is postgres.table("raw")\n'
            "table projected:\n"
            "    from raw\n"
            "    select:\n"
            "        missing\n"
        ),
        mode_override=CheckMode.LOOSE,
    )
    expression = _table(result).select_items[0].expression

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


@pytest.mark.parametrize("operator", ["is null", "is not null"])
def test_is_null_expression_maps_to_non_null_bool(operator: str) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            f"    where email {operator}\n"
            "    select:\n"
            "        id\n"
        )
    )
    expression = _where_expression(result)
    assert isinstance(expression, IsNullExpr)

    value_type = result.model.expression_value_types[expression]

    assert value_type.resolved_type.name == "Bool"
    assert value_type.nullability is EffectiveNullability.NON_NULL
    assert value_type.kind is ValueTypeKind.KNOWN


def test_simple_comparison_maps_to_bool_and_types_operands() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            '    where email >= "m"\n'
            "    select:\n"
            "        id\n"
        )
    )
    expression = _where_expression(result)
    assert isinstance(expression, ComparisonExpr)

    value_type = result.model.expression_value_types[expression]

    assert value_type.resolved_type.name == "Bool"
    assert value_type.kind is ValueTypeKind.KNOWN
    assert result.model.expression_value_types[expression.left].resolved_type.name == (
        "Text"
    )
    assert result.model.expression_value_types[expression.right].resolved_type.name == (
        "Text"
    )


def test_q1_conditional_membership_and_explicit_cast_have_closed_types() -> None:
    result = analyze(
        _parse(
            Q1_SOURCE + "table projected:\n"
            "    from users\n"
            "    where count in ()\n"
            "    select:\n"
            '        label = "present" if name is not null else "missing"\n'
            "        converted = cast(count as Float)\n"
        )
    )
    table = _table(result)
    assert table.where_clause is not None
    membership = table.where_clause.expression
    conditional = table.select_items[0].expression
    cast = table.select_items[1].expression

    assert isinstance(membership, MembershipExpr)
    assert membership.options == ()
    assert result.model.expression_value_types[membership].resolved_type.name == "Bool"
    assert (
        result.model.expression_value_types[membership].nullability
        is EffectiveNullability.NON_NULL
    )
    assert isinstance(conditional, ConditionalExpr)
    assert result.model.expression_value_types[conditional].resolved_type.name == "Text"
    assert (
        result.model.expression_value_types[conditional].nullability
        is EffectiveNullability.NON_NULL
    )
    assert isinstance(cast, CastExpr)
    assert result.model.expression_value_types[cast].resolved_type.name == "Float"


def test_q1_not_and_like_preserve_sql_nullability() -> None:
    result = analyze(
        _parse(
            Q1_SOURCE + "table projected:\n"
            "    from users\n"
            "    where not (name is null)\n"
            "    select:\n"
            '        matching = name like "A%"\n'
        )
    )
    table = _table(result)
    assert table.where_clause is not None
    where_type = result.model.expression_value_types[table.where_clause.expression]
    matching_type = result.model.expression_value_types[
        table.select_items[0].expression
    ]

    assert result.diagnostics == ()
    assert where_type.resolved_type.name == "Bool"
    assert where_type.nullability is EffectiveNullability.NON_NULL
    assert matching_type.resolved_type.name == "Bool"
    assert matching_type.nullability is EffectiveNullability.NULLABLE


def test_q1_local_null_contexts_record_typed_children_and_three_valued_membership() -> (
    None
):
    result = analyze(
        _parse(
            Q1_SOURCE + "table projected:\n"
            "    from users\n"
            "    where count not in (1, null)\n"
            "    select:\n"
            "        filled = coalesce(null, count)\n"
            "        absent = nullif(count, null)\n"
            '        label = "present" if null else name\n'
        )
    )
    table = _table(result)
    assert table.where_clause is not None
    membership = table.where_clause.expression
    filled = table.select_items[0].expression
    absent = table.select_items[1].expression
    conditional = table.select_items[2].expression

    assert isinstance(membership, MembershipExpr) and membership.negated
    assert isinstance(filled, CallExpr) and isinstance(absent, CallExpr)
    assert isinstance(conditional, ConditionalExpr)
    typed_nulls = (
        filled.arguments[0],
        absent.arguments[1],
        membership.options[1],
        conditional.condition,
    )
    assert all(
        isinstance(expression, LiteralExpr) and expression.value is None
        for expression in typed_nulls
    )
    assert [
        result.model.expression_value_types[expression].resolved_type.name
        for expression in typed_nulls
    ] == ["Int", "Int", "Int", "Bool"]
    assert all(
        result.model.expression_value_types[expression].nullability
        is EffectiveNullability.NULLABLE
        for expression in typed_nulls
    )
    assert result.model.expression_value_types[membership].resolved_type.name == "Bool"
    assert (
        result.model.expression_value_types[membership].nullability
        is EffectiveNullability.NULLABLE
    )
    assert (
        result.model.expression_value_types[filled].nullability
        is EffectiveNullability.NON_NULL
    )
    assert (
        result.model.expression_value_types[absent].nullability
        is EffectiveNullability.NULLABLE
    )


def test_q1_all_null_and_unknown_names_do_not_gain_contextual_types() -> None:
    result = analyze(
        _parse(
            Q1_SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        all_null = coalesce(null, null)\n"
            "        unknown = coalesce(missing, count)\n"
        )
    )
    table = _table(result)
    all_null = table.select_items[0].expression
    unknown = table.select_items[1].expression
    assert isinstance(all_null, CallExpr) and isinstance(unknown, CallExpr)
    assert result.model.expression_value_types[all_null].kind is ValueTypeKind.UNKNOWN
    assert result.model.expression_value_types[unknown].kind is ValueTypeKind.UNKNOWN
    assert all(
        result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN
        for expression in all_null.arguments
    )
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]


def test_a_case_coalesce_or_nullif_of_only_nulls_takes_the_type_beside_it() -> None:
    # Before: each such value was of unknown type, so `v` and the operands of
    # `+`, `==` and `in` were too, and check accepted all of them; PostgreSQL
    # types the inner CASE, COALESCE or NULLIF as text and rejected
    # `"v" + 1` (operator does not exist: text + integer). The wrong `nullif`
    # arity was reported only by emission (PIE-B1000).
    result = analyze(
        _parse(
            Q1_SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        count\n"
            "        v = name if active else (null if active else null)\n"
            "query reader:\n"
            "    from projected\n"
            "    let:\n"
            "        k = null if count > 1 else null\n"
            "    select:\n"
            "        r = v + 1\n"
            "        s = (v if count > 1 else (null if count > 1 else null)) + 1\n"
            "        x = coalesce(v, coalesce(null, null)) == 1\n"
            "        y = nullif(v, k) + 1\n"
            '        z = count in (1, "x", nullif(null, null))\n'
            "        a = nullif(count, coalesce(null, null), 1)\n"
        )
    )
    numeric = (
        "Invalid operands for operator +: expected numeric operands; "
        "string concatenation is not supported yet"
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        ("PIE-S2105", numeric, 16, 13),
        ("PIE-S2105", numeric, 17, 13),
        (
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
            18,
            13,
        ),
        ("PIE-S2105", numeric, 19, 13),
        (
            "PIE-S2105",
            "Invalid operands for operator in: expected same canonical "
            "membership operands",
            20,
            13,
        ),
        (
            "PIE-S2104",
            "Invalid arguments for function nullif: expected 2, got 3",
            21,
            13,
        ),
    ]
    value = _table(result).select_items[1].expression
    assert isinstance(value, ConditionalExpr)
    for expression in (value, value.when_false):
        value_type = result.model.expression_value_types[expression]
        assert value_type.resolved_type.name == "Text"
        assert value_type.nullability is EffectiveNullability.NULLABLE


def test_null_value_reads_bound_shared_dags_by_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pietto.semantic import expressions
    from pietto.semantic.model import RowSchema

    depth = 18
    script = _parse(
        Q1_SOURCE
        + "table projected:\n    from users\n    let:\n        a0 = null\n"
        + "".join(
            f"        a{i} = coalesce(a{i - 1}, a{i - 1})\n"
            for i in range(1, depth + 1)
        )
        + "    select:\n        count\n"
    )
    table = script.definitions[-1]
    assert isinstance(table, TableDef) and table.let_clause is not None
    bindings = {item.name: item.expression for item in table.let_clause.bindings}
    types = dict.fromkeys(bindings, expressions._UNKNOWN_VALUE_TYPE)
    visited: set[int] = set()
    original = expressions._callee_name

    def counted(call: CallExpr) -> str:
        assert id(call) not in visited, "NULL traversal expanded a shared call twice"
        visited.add(id(call))
        return original(call)

    with monkeypatch.context() as patch:
        patch.setattr(expressions, "_callee_name", counted)
        assert expressions._null_reads(
            (bindings[f"a{depth}"], bindings[f"a{depth - 1}"]),
            RowSchema(),
            types,
            bindings,
            values=True,
        ) == (True, True)
    assert len(visited) == depth
    assert analyze(script).diagnostics == ()


def test_null_value_reads_terminate_composite_self_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pietto.semantic import expressions
    from pietto.semantic.model import RowSchema

    script = _parse(
        "shape Row:\n    id: Int not null\n"
        'source items: Row is postgres.table("items")\n'
        "table projected:\n    from items\n    let:\n"
        "        a = coalesce(a, a)\n"
        "    select:\n        v = coalesce(a, 0)\n"
    )
    table = script.definitions[-1]
    assert isinstance(table, TableDef) and table.let_clause is not None
    binding = table.let_clause.bindings[0].expression
    original = expressions._callee_name
    visits = 0

    def bounded(call: CallExpr) -> str:
        nonlocal visits
        visits += 1
        assert visits <= 2, "NULL traversal did not terminate its composite cycle"
        return original(call)

    with monkeypatch.context() as patch:
        patch.setattr(expressions, "_callee_name", bounded)
        assert expressions._null_reads(
            (binding,),
            RowSchema(),
            {"a": expressions._UNKNOWN_VALUE_TYPE},
            {"a": binding},
            values=True,
        ) == (False,)
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in analyze(script).diagnostics
    ] == [
        ("PIE-S2330", "Let binding cannot reference itself: a", 7, 22),
        ("PIE-S2330", "Let binding cannot reference itself: a", 7, 25),
    ]


def test_null_value_reads_keep_alias_visibility_and_binding_scope() -> None:
    from pietto.semantic import expressions
    from pietto.semantic.model import RowField, RowSchema

    script = _parse(
        Q1_SOURCE + "table projected:\n    from users\n"
        "    let:\n        a = null\n        b = a\n    select:\n        v = b\n"
    )
    table = script.definitions[-1]
    assert isinstance(table, TableDef) and table.let_clause is not None
    bindings = {item.name: item.expression for item in table.let_clause.bindings}
    value = table.select_items[0].expression
    unknown = expressions._UNKNOWN_VALUE_TYPE
    field = RowField(
        name="a", resolved_type=unknown.resolved_type, nullability=unknown.nullability
    )
    for schema, visible, lets, expected in (
        (RowSchema(), {"b": unknown}, bindings, True),
        (RowSchema(), {}, bindings, False),
        (RowSchema(fields={"a": field}), {"b": unknown}, bindings, False),
        (
            RowSchema(),
            {"b": unknown},
            expressions.LetValues(bindings, erroneous={"a"}),
            False,
        ),
        (RowSchema(), {"b": unknown}, bindings, True),
    ):
        assert expressions._null_reads(
            (value,), schema, visible, lets, values=True
        ) == (expected,)


@pytest.mark.parametrize("bound", [False, True], ids=["inline", "let"])
@pytest.mark.parametrize(
    "context",
    [
        "coalesce({value}, 1)",
        "nullif({value}, 1)",
        "{value} if true else 1",
        "1 in ({value}, 1)",
        "coalesce({value}, amount / 2)",
        "coalesce({value}, {value}, 1)",
    ],
    ids=[
        "coalesce",
        "nullif",
        "conditional",
        "membership",
        "numeric-coalesce",
        "repeated",
    ],
)
def test_null_context_preserves_error_suppression(bound: bool, context: str) -> None:
    source = (
        "shape Row:\n    id: Int not null\n    amount: Decimal(10, 2) not null\n"
        'source items: Row is postgres.table("items")\n'
        "table projected:\n    from items\n"
    )
    erroneous = "null if missing else null"
    if bound:
        source += f"    let:\n        k = {erroneous}\n"
    value = "k" if bound else f"({erroneous})"
    source += (
        "    select:\n"
        f"        v = lower({context.format(value=value)})\n"
        "        independent = lower(1)\n"
    )
    lines = source.splitlines()
    unknowns = [
        ("PIE-S2102", "Unknown field: missing", line_number, column + 1)
        for line_number, line in enumerate(lines, 1)
        for column in range(len(line))
        if line.startswith("missing", column)
    ]
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in analyze(_parse(source)).diagnostics
    ] == unknowns + [
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: expected Text, got Int",
            len(lines),
            23,
        ),
    ]


def test_null_context_preserves_known_types_beside_child_errors() -> None:
    result = analyze(
        _parse(
            "shape Row:\n    id: Int not null\n"
            'source items: Row is postgres.table("items")\n'
            "table projected:\n    from items\n    select:\n"
            "        conditional = lower(1 if (missing is null) else 2)\n"
            "        membership = lower((absent is null) in (true, false))\n"
            "        branch_mismatch = true if (nosuch is null) else 1\n"
            "        sibling = lower(coalesce(null, unknown_sibling is null))\n"
            "        nullable_branch = lower(null if (other is null) else 1)\n"
            "        erroneous_null = lower(coalesce(null if (bad is null) else null, 1))\n"
        )
    )
    wrong_type = (
        "Invalid argument type for function lower at position 1: expected Text, got {}"
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        ("PIE-S2104", wrong_type.format("Int"), 7, 23),
        ("PIE-S2102", "Unknown field: missing", 7, 35),
        ("PIE-S2104", wrong_type.format("Bool"), 8, 22),
        ("PIE-S2102", "Unknown field: absent", 8, 29),
        (
            "PIE-S2105",
            "Invalid operands for operator conditional: expected same canonical branch types",
            9,
            27,
        ),
        ("PIE-S2102", "Unknown field: nosuch", 9, 36),
        ("PIE-S2104", wrong_type.format("Bool"), 10, 19),
        ("PIE-S2102", "Unknown field: unknown_sibling", 10, 40),
        ("PIE-S2104", wrong_type.format("Int"), 11, 27),
        ("PIE-S2102", "Unknown field: other", 11, 42),
        ("PIE-S2102", "Unknown field: bad", 12, 50),
    ]
    table = _table(result)
    sibling = table.select_items[3].expression
    branch = table.select_items[4].expression
    assert isinstance(sibling, CallExpr) and isinstance(branch, CallExpr)
    coalesce = sibling.arguments[0]
    conditional = branch.arguments[0]
    assert isinstance(coalesce, CallExpr) and isinstance(conditional, ConditionalExpr)
    assert (
        result.model.expression_value_types[coalesce.arguments[0]].resolved_type.name
        == "Bool"
    )
    assert (
        result.model.expression_value_types[conditional.when_true].resolved_type.name
        == "Int"
    )


@pytest.mark.parametrize(
    "erroneous", [False, True], ids=["valid-null", "binding-error"]
)
def test_null_binding_name_suppression_is_not_error_evidence(erroneous: bool) -> None:
    from pietto.errors import Diagnostic
    from pietto.semantic import expressions
    from pietto.semantic.model import RowSchema

    script = _parse(
        Q1_SOURCE + "table projected:\n    from users\n"
        "    let:\n        k = null\n    select:\n        v = coalesce(k, 1)\n"
    )
    table = script.definitions[-1]
    assert isinstance(table, TableDef) and table.let_clause is not None
    bindings = expressions.LetValues(
        {"k": table.let_clause.bindings[0].expression},
        erroneous={"k"} if erroneous else set(),
    )
    diagnostics: list[Diagnostic] = []
    value_type = expressions.infer_row_expression(
        table.select_items[0].expression,
        RowSchema(),
        {},
        diagnostics,
        report_unknown_name=True,
        bare_value_types={"k": expressions._UNKNOWN_VALUE_TYPE},
        bare_value_expressions=bindings,
        suppressed_unknown_names={"k"},
    )
    assert diagnostics == []
    assert value_type.kind is (
        ValueTypeKind.UNKNOWN if erroneous else ValueTypeKind.KNOWN
    )
    if not erroneous:
        assert value_type.resolved_type.name == "Int"
        assert value_type.nullability is EffectiveNullability.NON_NULL


def test_q1_new_type_checks_expand_source_aliases_without_changing_child_identity() -> (
    None
):
    result = analyze(
        _parse(
            "type Age = Int\n"
            "type Flag = Bool\n"
            "type Moment = Timestamp\n"
            "type Money = Decimal(9, 2)\n"
            "shape Event:\n"
            "    age: Age not null\n"
            "    flag: Flag not null\n"
            "    happened: Moment not null\n"
            "    amount: Money not null\n"
            'source events: Event is postgres.table("events")\n'
            "table projected:\n"
            "    from events\n"
            "    where not flag\n"
            "    select:\n"
            "        converted = cast(age as Float)\n"
            "        choice = 1 if flag else 2\n"
            "        direction = sign(age)\n"
            "        calendar = year(happened)\n"
            "        magnitude = abs(amount)\n"
        )
    )
    table = _table(result)
    assert not [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
    assert table.where_clause is not None
    predicate = table.where_clause.expression
    converted = table.select_items[0].expression
    assert isinstance(predicate, UnaryExpr)
    assert isinstance(converted, CastExpr)
    flag = predicate.operand
    age = converted.value
    assert (
        result.model.expression_value_types[flag].resolved_type.kind
        is TypeKind.TYPE_ALIAS
    )
    assert (
        result.model.expression_value_types[age].resolved_type.kind
        is TypeKind.TYPE_ALIAS
    )
    assert [
        result.model.expression_value_types[item.expression].resolved_type.name
        for item in table.select_items
    ] == ["Float", "Int", "Int", "Int", "Decimal"]


def test_q1_nominal_enum_is_not_a_bool_alias() -> None:
    result = analyze(
        _parse(
            "enum Flag:\n"
            "    yes\n"
            "shape Event:\n"
            "    flag: Flag not null\n"
            'source events: Event is postgres.table("events")\n'
            "table projected:\n"
            "    from events\n"
            "    where not flag\n"
            "    select:\n"
            "        flag\n"
        )
    )
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2105"]


@pytest.mark.parametrize(
    ("expression", "code", "message"),
    [
        ("1 if count else 2", "PIE-S2105", "expected Bool condition"),
        ('coalesce(count, "unknown")', "PIE-S2104", "expected same canonical type"),
        (
            'nullif(count, "unknown")',
            "PIE-S2104",
            "expected same canonical comparable type",
        ),
        ("name like count", "PIE-S2105", "expected Text operands"),
        (
            'name not like "Hello!"',
            "PIE-S2105",
            "does not end in the escape character !",
        ),
        ("cast(count as Text)", "PIE-S2105", "expected cast(Int as Float)"),
        ('substr("abc", 0, 2)', "PIE-S2104", "start must be a positive Int literal"),
    ],
)
def test_q1_closed_expression_rules_fail_with_deterministic_diagnostics(
    expression: str,
    code: str,
    message: str,
) -> None:
    result = analyze(
        _parse(
            Q1_SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            f"        value = {expression}\n"
        )
    )

    matching = [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == code and message in diagnostic.message
    ]
    assert len(matching) == 1


def test_like_patterns_with_paired_or_inner_escapes_are_accepted() -> None:
    result = analyze(
        _parse(
            Q1_SOURCE + "table projected:\n"
            "    from users\n"
            '    where name like "100!!" or name like "wow!%"\n'
            "    select:\n"
            "        name\n"
        )
    )

    # Before: `like "Hello!"` also checked OK although PostgreSQL rejects it.
    assert result.diagnostics == ()


@pytest.mark.parametrize(
    ("body", "line", "column"),
    [
        ("    where name like pattern\n    select:\n        name\n", 11, 11),
        ("    where name not like (alias)\n    select:\n        name\n", 11, 11),
        ("    select:\n        name\n        m = name like pattern\n", 13, 13),
        (
            "        m = name like alias\n    where m\n    select:\n        name\n",
            11,
            13,
        ),
        ("        m = name like pattern\n    select:\n        name\n", 11, 13),
    ],
    ids=("where", "parenthesized-chain", "select", "let-read", "let-unread"),
)
def test_let_bound_like_pattern_ending_in_the_escape_is_refused(
    body: str,
    line: int,
    column: int,
) -> None:
    result = analyze(
        _parse(
            Q1_SOURCE + "table projected:\n"
            "    from users\n"
            "    let:\n"
            '        pattern = "abc!"\n'
            "        alias = pattern\n" + body
        )
    )

    # Before: a let-bound "abc!" passed check and emitted the SQL the direct
    # literal is refused for; inside another binding it still passed, since
    # let bodies were typed without the earlier bindings' expressions.
    assert [
        (diagnostic.code, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in result.diagnostics
    ] == [("PIE-S2105", line, column)]


@pytest.mark.parametrize("target", ["Float", "Int"])
@pytest.mark.parametrize(
    "body",
    [
        "    select:\n        count\n        value = cast(nothing as {target})\n",
        "        value = cast(nothing as {target})\n"
        "    select:\n        count\n        copy = value\n",
    ],
    ids=("select", "let"),
)
def test_let_bound_null_cast_is_refused_like_the_null_literal(
    target: str, body: str
) -> None:
    result = analyze(
        _parse(
            Q1_SOURCE + "table projected:\n"
            "    from users\n"
            "    let:\n"
            "        nothing = null\n" + body.format(target=target)
        )
    )

    # Before: `cast(nothing as Float)` passed check and emission refused it,
    # and inside another binding it still passed.
    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2105",
            f"Invalid cast: cast(null as {target}) is not supported; expected "
            "cast(Int as Float), the only supported cast",
        )
    ]


@pytest.mark.parametrize(
    ("expression", "attempted"),
    [
        ("cast(count as Text)", "cast(Int as Text)"),
        ("cast(count as Int)", "cast(Int as Int)"),
        ("cast(ratio as Int)", "cast(Float as Int)"),
        ("cast(name as Text)", "cast(Text as Text)"),
        ("cast(1.5 as Float)", "cast(Float as Float)"),
        ("cast(count as Float not null)", "cast(Int as Float not null)"),
        ("cast(count as Float nullable)", "cast(Int as Float nullable)"),
        ("cast(count as Decimal(10, 2))", "cast(Int as Decimal(10, 2))"),
        ("cast(age as Text)", "cast(Int as Text)"),
        ("cast(count as Age)", "cast(Int as Age)"),
        ("cast(null as Float)", "cast(null as Float)"),
    ],
)
def test_invalid_cast_echoes_the_attempted_pair(
    expression: str,
    attempted: str,
) -> None:
    result = analyze(
        _parse(
            "type Age = Int not null\n"
            "shape Person:\n"
            "    count: Int not null\n"
            "    ratio: Float not null\n"
            "    name: Text not null\n"
            "    age: Age not null\n"
            'source people: Person is postgres.table("people")\n'
            "table projected:\n"
            "    from people\n"
            "    select:\n"
            f"        value = {expression}\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message, diagnostic.location.column)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == [
        (
            "PIE-S2105",
            f"Invalid cast: {attempted} is not supported; expected "
            "cast(Int as Float), the only supported cast",
            17,
        )
    ]


_WINDOW_HINT = "in a SELECT item, with an indented `order by:`)"
_CAST_HINT = "is not supported; expected cast(Int as Float), the only supported cast"
_SUBSTR_BOUNDS_MESSAGE = (
    "Invalid arguments for function substr: start must be a positive Int literal "
    "and count must be a non-negative Int literal"
)


@pytest.mark.parametrize(
    ("expression", "code", "message"),
    [
        ("frob(null)", "PIE-S2103", "Unknown function: frob"),
        ("frob(price / 2)", "PIE-S2103", "Unknown function: frob"),
        (
            "month(price / 2, price / 2)",
            "PIE-S2104",
            "Invalid arguments for function month: expected 1, got 2",
        ),
        (
            "cast(null as Int)",
            "PIE-S2105",
            f"Invalid cast: cast(null as Int) {_CAST_HINT}",
        ),
        (
            "cast(null as Float)",
            "PIE-S2105",
            f"Invalid cast: cast(null as Float) {_CAST_HINT}",
        ),
        (
            "cast(price / 2 as Text)",
            "PIE-S2105",
            f"Invalid cast: cast(unknown as Text) {_CAST_HINT}",
        ),
        (
            "row_number()",
            "PIE-S2103",
            "Window function needs a `window` specification: row_number (write "
            f"`row_number() window:` {_WINDOW_HINT}",
        ),
        (
            "lag(count)",
            "PIE-S2103",
            "Window function needs a `window` specification: lag (write "
            f"`lag(...) window:` {_WINDOW_HINT}",
        ),
        (
            "first_value(price / 2)",
            "PIE-S2103",
            "Window function needs a `window` specification: first_value (write "
            f"`first_value(...) window:` {_WINDOW_HINT}",
        ),
        ("substr(price / 2, 0, 2)", "PIE-S2104", _SUBSTR_BOUNDS_MESSAGE),
        ("cast(price / 2 as Float)", None, None),
        ("lower(null)", None, None),
        # A quotient fits no `Text` parameter, whatever number it is.
        ("substr(coalesce(null, null), 1, 2)", None, None),
    ],
)
def test_type_independent_call_and_cast_checks_ignore_unknown_operands(
    expression: str, code: str | None, message: str | None
) -> None:
    result = analyze(
        _parse(
            "shape Person:\n"
            "    count: Int not null\n"
            "    price: Decimal not null\n"
            'source people: Person is postgres.table("people")\n'
            "table projected:\n"
            "    from people\n"
            "    select:\n"
            f"        value = {expression}\n"
        )
    )

    # Decimal division has no result type yet, so `price / 2` is an operand
    # of unknown type, which these checks do not read.
    assert [
        (diagnostic.code, diagnostic.message, diagnostic.location.column)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == ([] if code is None else [(code, message, 17)])


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        # The operand reported its own error: no PIE-S2105 beside it.
        (
            "shape Person:\n    count: Int not null\n"
            'source people: Person is postgres.table("people")\n'
            "table projected:\n    from people\n    select:\n"
            "        value = cast(missing as Text)\n",
            [("PIE-S2102", "Unknown field: missing")],
        ),
        # An unknown input row explains no cast but the Float one, which alone
        # reads the operand's type.
        (
            "table projected:\n    from nowhere\n    select:\n"
            "        value = cast(x as Text)\n",
            [
                ("PIE-S2301", "Unknown relation: nowhere"),
                ("PIE-S2105", f"Invalid cast: cast(unknown as Text) {_CAST_HINT}"),
            ],
        ),
        (
            'source people is postgres.table("people")\n'
            "table projected:\n    from people\n    select:\n"
            "        value = cast(x as Text)\n",
            [("PIE-S2105", f"Invalid cast: cast(unknown as Text) {_CAST_HINT}")],
        ),
        (
            'source people is postgres.table("people")\n'
            "table projected:\n    from people\n    select:\n"
            "        value = cast(x as Float)\n",
            [],
        ),
    ),
)
def test_only_an_operand_error_explains_an_unknown_cast_operand(
    source: str, expected: list[tuple[str, str]]
) -> None:
    result = analyze(_parse(source), mode_override=CheckMode.LOOSE)

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == expected


@pytest.mark.parametrize(
    ("relation", "expression", "expected"),
    [
        ("people", "foo(amount)", [("PIE-S2103", "Unknown function: foo", 5, 17)]),
        (
            "people",
            "lag(amount)",
            [
                (
                    "PIE-S2103",
                    "Window function needs a `window` specification: lag (write "
                    f"`lag(...) window:` {_WINDOW_HINT}",
                    5,
                    17,
                )
            ],
        ),
        (
            "people",
            "row_number(amount)",
            [
                (
                    "PIE-S2103",
                    "Window function needs a `window` specification: row_number "
                    f"(write `row_number(...) window:` {_WINDOW_HINT}",
                    5,
                    17,
                )
            ],
        ),
        (
            "people",
            "sign(amount, amount)",
            [
                (
                    "PIE-S2104",
                    "Invalid arguments for function sign: expected 1, got 2",
                    5,
                    17,
                )
            ],
        ),
        (
            "people",
            "year(amount, amount)",
            [
                (
                    "PIE-S2104",
                    "Invalid arguments for function year: expected 1, got 2",
                    5,
                    17,
                )
            ],
        ),
        # An argument's own error still explains its caller.
        ("people", "foo(bar(amount))", [("PIE-S2103", "Unknown function: bar", 5, 21)]),
        (
            "nowhere",
            "foo(amount)",
            [
                ("PIE-S2301", "Unknown relation: nowhere", 3, 5),
                ("PIE-S2103", "Unknown function: foo", 5, 17),
            ],
        ),
        (
            "people",
            "substr(amount, 0, -1)",
            [("PIE-S2104", _SUBSTR_BOUNDS_MESSAGE, 5, 17)],
        ),
        (
            "people",
            "substr(amount, start, 2)",
            [("PIE-S2104", _SUBSTR_BOUNDS_MESSAGE, 5, 17)],
        ),
        (
            "people",
            "cast(amount as Text)",
            [("PIE-S2105", f"Invalid cast: cast(unknown as Text) {_CAST_HINT}", 5, 17)],
        ),
        # Checks that read an argument's type stay gradual.
        ("people", "upper(amount)", []),
        ("people", "sign(amount)", []),
        ("people", "year(amount)", []),
        ("people", "substr(amount, 1, 2)", []),
        ("people", "lower(trim(amount))", []),
        ("people", "cast(amount as Float)", []),
    ],
)
def test_unknown_input_row_hides_no_type_independent_call_check(
    relation: str, expression: str, expected: list[tuple[str, str, int, int]]
) -> None:
    result = analyze(
        _parse(
            'source people is postgres.table("people")\n'
            "table projected:\n"
            f"    from {relation}\n"
            "    select:\n"
            f"        value = {expression}\n"
        ),
        mode_override=CheckMode.LOOSE,
    )

    assert [
        (
            diagnostic.code,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
        )
        for diagnostic in result.diagnostics
    ] == expected


def test_unused_let_over_an_unknown_input_row_keeps_its_call_errors() -> None:
    # As over a shaped source, an unused binding is still checked.
    result = analyze(
        _parse(
            'source people is postgres.table("people")\n'
            "table projected:\n"
            "    from people\n"
            "    let:\n"
            "        x = foo(amount)\n"
            "        y = lag(amount)\n"
            "        z = sign(amount, amount)\n"
            "        s = substr(amount, 0, 2)\n"
            "    select:\n"
            "        id\n"
        ),
        mode_override=CheckMode.LOOSE,
    )

    assert [
        (
            diagnostic.code,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
        )
        for diagnostic in result.diagnostics
    ] == [
        ("PIE-S2103", "Unknown function: foo", 5, 13),
        (
            "PIE-S2103",
            "Window function needs a `window` specification: lag (write "
            f"`lag(...) window:` {_WINDOW_HINT}",
            6,
            13,
        ),
        ("PIE-S2104", "Invalid arguments for function sign: expected 1, got 2", 7, 13),
        ("PIE-S2104", _SUBSTR_BOUNDS_MESSAGE, 8, 13),
    ]


def test_a_conditional_condition_known_not_to_be_bool_is_refused_beside_unknowns() -> (
    None
):
    """A condition of a known type that is not Bool is PIE-S2105 also beside a
    branch of unknown type, and over an unknown input row a built-in call is
    a condition of the result type its signature fixes, also as a `let:`
    value (before: each accepted). A condition of unknown type stays
    accepted, and a branch with an error of its own still explains it."""
    unknown_row = analyze(
        _parse(
            'source people is postgres.table("people")\n'
            "table projected:\n"
            "    from people\n"
            "    let:\n"
            "        c = len(name)\n"
            "    select:\n"
            "        a = 1 if len(name) else 2\n"
            "        b = name if 5 else 2\n"
            "        d = 1 if 'x' else name\n"
            "        e = 1 if c else 2\n"
            "        f = 1 if name else 2\n"
            "        g = 1 if contains(name, 'x') else 2\n"
        ),
        mode_override=CheckMode.LOOSE,
    )
    known_row = analyze(
        _parse(
            "shape Person:\n    count: Int not null\n"
            'source people: Person is postgres.table("people")\n'
            "table projected:\n    from people\n    select:\n"
            "        a = missing if 5 else 2\n"
            "        b = 1 if count else missing\n"
        )
    )

    condition = "Invalid operands for operator conditional: expected Bool condition"
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in (*unknown_row.diagnostics, *known_row.diagnostics)
    ] == [
        *(("PIE-S2105", condition, line, 13) for line in (7, 8, 9, 10)),
        ("PIE-S2102", "Unknown field: missing", 7, 13),
        ("PIE-S2102", "Unknown field: missing", 8, 29),
    ]


COMPARISON_SOURCE = (
    "type Age = Int not null\n"
    "enum Status:\n"
    "    active\n"
    "enum Phase:\n"
    "    active\n"
    "    done\n"
    "type Stage = Status not null\n"
    "shape Point:\n"
    "    x: Int not null\n"
    "shape Item:\n"
    "    count: Int not null\n"
    "    ratio: Float not null\n"
    "    amount: Decimal not null\n"
    "    name: Text not null\n"
    "    email: Text nullable\n"
    "    active: Bool not null\n"
    "    born: Date not null\n"
    "    created_at: Timestamp not null\n"
    "    token: UUID not null\n"
    "    payload: Json nullable\n"
    "    blob: Bytes nullable\n"
    "    anything: Any nullable\n"
    "    home: Point nullable\n"
    "    status: Status not null\n"
    "    phase: Phase not null\n"
    "    stage: Stage not null\n"
    "    age: Age not null\n"
    'source items: Item is postgres.table("items")\n'
    "table projected:\n"
    "    from items\n"
)
COMPARISON_WHERE_LINE = COMPARISON_SOURCE.count("\n") + 1


@pytest.mark.parametrize(
    ("predicate", "operator", "column"),
    [
        ('count == "x"', "==", 11),
        ("active == 1", "==", 11),
        ('active != "true"', "!=", 11),
        ("token == 1", "==", 11),
        ("created_at == 5", "==", 11),
        ("born < 5", "<", 11),
        ("ratio > active", ">", 11),
        ("amount <= created_at", "<=", 11),
        ("token >= born", ">=", 11),
        ('email is null or count == "x"', "==", 28),
        ('count between 1 and "z"', "between", 11),
        # One null bound leaves the other to check (before: not checked).
        ('count between null and "z"', "between", 11),
        ('count between "z" and null', "between", 11),
        # Before: an enum, a shape, `Bytes` or `Json` operand was not
        # checked, and PostgreSQL rejected `"status" = 1` (operator does not
        # exist: status = integer). An enum compares with its own enum and
        # its labels, and a shape with its shape.
        ("status == 1", "==", 11),
        ("count != status", "!=", 11),
        ("stage < 1", "<", 11),
        ("status == phase", "==", 11),
        ('status == "done"', "==", 11),
        ("status == name", "==", 11),
        ('status between "active" and 1', "between", 11),
        ("home == 1", "==", 11),
        ('home == "x"', "==", 11),
        ("blob == 1", "==", 11),
        ("payload > count", ">", 11),
        # Before: any Text operand, not only a literal, was accepted against
        # a type whose only constant form is a Text literal, and PostgreSQL
        # rejected `"born" = "name"` (operator does not exist: date = text).
        ("born == name", "==", 11),
        ("created_at >= lower(name)", ">=", 11),
        ("token == email", "==", 11),
        ("blob == name", "==", 11),
        ("payload == name", "==", 11),
    ],
)
def test_comparison_operands_of_different_families_report_s2105(
    predicate: str,
    operator: str,
    column: int,
) -> None:
    for mode in CheckMode:
        result = analyze(_parse(_comparison_source(predicate)), mode_override=mode)

        assert [
            (
                diagnostic.code,
                diagnostic.severity,
                diagnostic.message,
                diagnostic.location.line,
                diagnostic.location.column,
            )
            for diagnostic in result.diagnostics
        ] == [
            (
                "PIE-S2105",
                Severity.ERROR,
                f"Invalid operands for operator {operator}: "
                "expected comparable operands",
                COMPARISON_WHERE_LINE,
                column,
            )
        ], mode
        assert result.model.expression_value_types[_where_expression(result)].kind is (
            ValueTypeKind.UNKNOWN
        )


NULL_LET_SOURCE = (
    COMPARISON_SOURCE + "    let:\n        nothing = null\n        alias = nothing\n"
)


@pytest.mark.parametrize(
    ("predicate", "operator", "remedy", "column"),
    [
        ("email == null", "==", "is null", 11),
        ("null == email", "==", "is null", 11),
        ("email != null", "!=", "is not null", 11),
        ("count < null", "<", None, 11),
        ("count <= null", "<=", None, 11),
        ("null > count", ">", None, 11),
        ("count >= null", ">=", None, 11),
        ("email == nothing", "==", "is null", 11),
        ("email != alias", "!=", "is not null", 11),
        # Before: null against null also suggested `is null`/`is not null`,
        # although `null is null` is TRUE.
        ("null == null", "==", None, 11),
        ("nothing != alias", "!=", None, 11),
        ("alias == null", "==", None, 11),
        ('name == "x" and not (email == null)', "==", "is null", 32),
        ("null between 1 and count", "between", None, 11),
        ("count between nothing and alias", "between", None, 11),
        ("count in (null, nothing)", "in", "is null", 11),
        ("count not in (null)", "not in", "is not null", 11),
        ("null in (1, count)", "in", None, 11),
        ("nothing not in (1)", "not in", None, 11),
    ],
)
def test_comparison_with_null_is_refused_as_never_true(
    predicate: str,
    operator: str,
    remedy: str | None,
    column: int,
) -> None:
    source = f"{NULL_LET_SOURCE}    where {predicate}\n    select:\n        count\n"
    message = (
        f"Invalid operands for operator {operator}: comparison with null is never true"
    )
    if remedy is not None:
        message += f"; write `{remedy}` instead"
    for mode in CheckMode:
        result = analyze(_parse(source), mode_override=mode)

        # Before: each passed check and emitted a test such as `= NULL`.
        assert [
            (
                diagnostic.code,
                diagnostic.severity,
                diagnostic.message,
                diagnostic.location.line,
                diagnostic.location.column,
            )
            for diagnostic in result.diagnostics
        ] == [("PIE-S2105", Severity.ERROR, message, COMPARISON_WHERE_LINE + 3, column)]
        assert result.model.expression_value_types[_where_expression(result)].kind is (
            ValueTypeKind.UNKNOWN
        )


@pytest.mark.parametrize(
    "predicate",
    [
        "count between null and 10",
        "count between 1 and nothing",
        "count in (1, null)",
        "count not in (1, nothing)",
        "null in ()",
    ],
)
def test_null_operands_that_can_be_false_or_match_are_not_refused(
    predicate: str,
) -> None:
    result = analyze(
        _parse(f"{NULL_LET_SOURCE}    where {predicate}\n    select:\n        count\n"),
        mode_override=CheckMode.STRICT,
    )

    assert result.diagnostics == ()


@pytest.mark.parametrize(
    "predicate",
    [
        "count == 1",
        "ratio > 1",
        "amount > 10.5",
        "amount >= count",
        'name == "x"',
        "name < email",
        "active == false",
        "born <= created_at",
        'created_at >= "2024-01-01"',
        'token == "00000000-0000-0000-0000-000000000000"',
        "token != token",
        "payload == payload",
        'payload == "{}"',
        'blob != "x"',
        "anything == anything",
        "anything == 1",
        'anything == "x"',
        "home == home",
        'status == "active"',
        "status == stage",
        'stage != "active"',
        'status between "active" and "active"',
        "age > 18",
        "email == name",
        'coalesce(email, null) == "x"',
        'email is null or email == "x"',
        "count between 1 and 10",
        "count between null and 10",
        "count between 1 and null",
    ],
)
def test_comparable_or_unchecked_operands_keep_bool(predicate: str) -> None:
    result = analyze(
        _parse(_comparison_source(predicate)), mode_override=CheckMode.STRICT
    )

    value_type = result.model.expression_value_types[_where_expression(result)]

    assert result.diagnostics == ()
    assert value_type.resolved_type.name == "Bool"
    assert value_type.nullability is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize(
    "predicate",
    [
        "count if active else count between null and 1",
        "count if active else count between 0 and null",
    ],
)
def test_a_between_with_one_null_bound_is_a_bool_where_it_is_used(
    predicate: str,
) -> None:
    """A `between` with one null bound is a `Bool`, so a conditional with an
    `Int` branch is refused. Before, it had no type and the WHERE passed, and
    PostgreSQL rejected the emitted `CASE WHEN ... THEN "count" ELSE ...`."""
    result = analyze(_parse(_comparison_source(predicate)))

    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (
            "PIE-S2105",
            "Invalid operands for operator conditional: expected same canonical "
            "branch types",
            COMPARISON_WHERE_LINE,
            11,
        )
    ]


@pytest.mark.parametrize(
    "predicate",
    ["email is null", "token is not null", "created_at is null", "payload is not null"],
)
def test_null_tests_have_no_operand_pair_to_check(predicate: str) -> None:
    result = analyze(
        _parse(_comparison_source(predicate)), mode_override=CheckMode.STRICT
    )

    value_type = result.model.expression_value_types[_where_expression(result)]

    assert result.diagnostics == ()
    assert value_type.resolved_type.name == "Bool"
    assert value_type.nullability is EffectiveNullability.NON_NULL


# Single-file row fields keep alias names; `years` is a two-step alias chain.
ALIAS_COMPARISON_SOURCE = (
    "type Age = Int not null\n"
    "type Years = Age not null\n"
    "type Tag = Text not null\n"
    "shape Person:\n"
    "    id: Int not null\n"
    "    age: Age not null\n"
    "    years: Years not null\n"
    "    tag: Tag not null\n"
    "{check}"
    'source people: Person is postgres.table("people")\n'
    "table projected:\n"
    "    from people\n"
    "{clauses}"
)


@pytest.mark.parametrize(
    ("check", "clauses", "operator", "line", "column"),
    [
        ("", '    where years == "x"\n    select:\n        id\n', "==", 12, 11),
        ("", '    select:\n        id\n        flag = age == "x"\n', "==", 14, 16),
        (
            "",
            "    let:\n        bad = tag > 5\n    where bad\n    select:\n        id\n",
            ">",
            13,
            15,
        ),
        (
            '    check named:\n        age == "x"\n',
            "    select:\n        id\n",
            "==",
            10,
            9,
        ),
        (
            "",
            '    select:\n        id\n    order by:\n        years == "x"\n',
            "==",
            15,
            9,
        ),
        (
            "",
            '    where years between "a" and "b"\n    select:\n        id\n',
            "between",
            12,
            11,
        ),
    ],
)
def test_alias_operands_are_compared_as_their_expansion(
    check: str,
    clauses: str,
    operator: str,
    line: int,
    column: int,
) -> None:
    result = analyze(
        _parse(ALIAS_COMPARISON_SOURCE.format(check=check, clauses=clauses))
    )

    assert [
        (
            diagnostic.code,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
        )
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2105",
            f"Invalid operands for operator {operator}: expected comparable operands",
            line,
            column,
        )
    ]
    assert [
        value_type.kind
        for expression, value_type in result.model.expression_value_types.items()
        if isinstance(expression, (ComparisonExpr, BetweenExpr))
    ] == [ValueTypeKind.UNKNOWN]


@pytest.mark.parametrize(
    ("check", "clauses"),
    [
        ("", '    where years >= age and tag == "x"\n    select:\n        id\n'),
        ("", "    select:\n        id\n        flag = years == 18\n"),
        (
            "",
            '    let:\n        ok = tag < "m"\n    where ok\n    select:\n        id\n',
        ),
        ("    check named:\n        age >= 18\n", "    select:\n        id\n"),
        ("", "    select:\n        id\n    order by:\n        years >= 18\n"),
        ("", "    where years between age and 10\n    select:\n        id\n"),
    ],
)
def test_alias_operands_of_one_family_keep_bool(check: str, clauses: str) -> None:
    result = analyze(
        _parse(ALIAS_COMPARISON_SOURCE.format(check=check, clauses=clauses)),
        mode_override=CheckMode.STRICT,
    )

    assert result.diagnostics == ()
    assert {
        (value_type.resolved_type.name, value_type.nullability)
        for expression, value_type in result.model.expression_value_types.items()
        if isinstance(expression, (ComparisonExpr, BetweenExpr))
    } == {("Bool", EffectiveNullability.UNKNOWN)}


ALIAS_SATISFYING_CLAUSES = (
    "    group by:\n"
    "        age\n"
    "    select:\n"
    "        age\n"
    "        n = count()\n"
    "    satisfying:\n"
    "        {predicate}\n"
)


def test_alias_group_keys_in_satisfying_are_compared_as_their_expansion() -> None:
    rejected, accepted = (
        analyze(
            _parse(
                ALIAS_COMPARISON_SOURCE.format(
                    check="",
                    clauses=ALIAS_SATISFYING_CLAUSES.format(predicate=predicate),
                )
            ),
            mode_override=CheckMode.STRICT,
        )
        for predicate in ('age == "x"', "age > 1")
    )

    assert [
        (
            diagnostic.code,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
        )
        for diagnostic in rejected.diagnostics
    ] == [
        (
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
            18,
            9,
        )
    ]
    assert rejected.model.result_predicates == {}
    assert accepted.diagnostics == ()
    (predicate,) = accepted.model.result_predicates.values()
    assert {
        (value_type.resolved_type.name, value_type.nullability)
        for expression, value_type in predicate.expression_value_types.items()
        if isinstance(expression, ComparisonExpr)
    } == {("Bool", EffectiveNullability.UNKNOWN)}


def test_unknown_call_argument_suppresses_dependent_call_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    where unknown_call(missing) >= 1\n"
            "    select:\n"
            "        id\n"
        )
    )
    expression = _where_expression(result)
    assert isinstance(expression, ComparisonExpr)
    assert isinstance(expression.left, CallExpr)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert (
        result.model.expression_value_types[expression.left].kind
        is ValueTypeKind.UNKNOWN
    )
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"
    assert (
        result.model.expression_value_types[expression.left.arguments[0]].kind
        is ValueTypeKind.UNKNOWN
    )


@pytest.mark.parametrize(
    "line_one,column",
    # An indented first code line is a parse error (PIE-P1000), so line 1
    # starts a semantic file at column 1, after spaces or after a comment.
    [
        ("", 1),
        ("\n", 1),
        ("    \n", 5),
        ("# head\n", 7),
        ("   # head\n", 10),
    ],
    ids=["plain", "empty", "spaces", "comment", "spaced_comment"],
)
def test_deep_binary_expression_returns_semantic_recursion_diagnostic(
    line_one: str, column: int
) -> None:
    # The whole file: line 1 from its first character other than a space, or
    # from just after its last one when it holds only spaces and a comment.
    expression = " + ".join(["1"] * 1200)
    script = _parse(f"{line_one}derive total() -> Int not null:\n    {expression}\n")

    result = analyze(script)

    assert result.model.mode is CheckMode.CHECKED
    assert result.model.expression_value_types == {}
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-S2006"
    assert diagnostic.severity is Severity.ERROR
    assert "recursion limit" in diagnostic.message
    location = diagnostic.location
    assert location is not None
    assert (
        location.line,
        location.column,
        location.end_line,
        location.end_column,
    ) == (1, column, 2 + line_one.count("\n"), 4802)


_NESTING_SOURCES = (
    "shape A:\n"
    "    id: Int not null\n"
    'source xs: A is postgres.table("xs")\n'
    'source ys: A is postgres.table("ys")\n'
)
_S2006_MESSAGE = "Semantic analysis recursion limit exceeded while processing source."


def _nested_source(position: str, levels: int) -> str:
    """Return a file whose deepest expression nests exactly ``levels`` levels."""

    if position == "where":
        conjuncts = " and ".join(["id == 1"] * (levels - 1))
        return (
            f"{_NESTING_SOURCES}table q:\n    from xs\n    where {conjuncts}\n"
            "    select:\n        id\n"
        )
    if position == "select":
        terms = " + ".join(["id"] * levels)
        return f"{_NESTING_SOURCES}table q:\n    from xs\n    select:\n        x = {terms}\n"
    if position == "relationship":
        conjuncts = " and ".join(["a.id == b.id"] * (levels - 1))
        return (
            f"{_NESTING_SOURCES}relationship r:\n    endpoint a: xs\n"
            f"    endpoint b: ys\n    on {conjuncts}\n"
        )
    if position == "frame":
        # The window use is one level and its frame offset the rest.
        offset = " + ".join(["1"] * (levels - 1))
        return (
            f"{_NESTING_SOURCES}query q:\n    from xs\n    select:\n"
            "        r = last_value(id) window:\n"
            "            order by:\n                id\n"
            f"            range between {offset} preceding and current row\n"
        )
    conjuncts = " and ".join(["self > 0"] * (levels - 1))
    return f"type Positive = Int not null:\n    ensure {conjuncts}\n"


@pytest.mark.parametrize(
    "position", ["where", "select", "relationship", "ensure", "frame"]
)
def test_an_expression_nested_past_450_levels_is_s2006_wherever_it_is(
    position: str,
) -> None:
    # Before, the limit was wherever Python's recursion limit happened to fall
    # for the caller: about 990 levels in a relationship or a type rule, and
    # about 490 in a window frame offset, which the first bound did not read.
    accepted = analyze(_parse(_nested_source(position, 450)))
    script = _parse(_nested_source(position, 451))
    refused = analyze(script)

    # A computed RANGE offset is refused (PIE-S2104), but not past the bound.
    assert [diagnostic.code for diagnostic in accepted.diagnostics] == (
        ["PIE-S2104"] if position == "frame" else []
    )
    assert [
        (
            diagnostic.code,
            diagnostic.severity,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
            diagnostic.location.end_line,
            diagnostic.location.end_column,
        )
        for diagnostic in refused.diagnostics
    ] == [
        (
            "PIE-S2006",
            Severity.ERROR,
            _S2006_MESSAGE,
            1,
            1,
            script.span.end_line,
            script.span.end_column,
        )
    ]
    assert refused.model.expression_value_types == {}


def test_refusal_past_the_nesting_bound_does_not_depend_on_the_callers_stack() -> None:
    def analyze_below(frames: int, script: Script) -> SemanticResult:
        return analyze(script) if frames == 0 else analyze_below(frames - 1, script)

    deeper = _parse(_nested_source("where", 451))
    deepest_accepted = _parse(_nested_source("where", 450))

    # Before, 451 levels passed here and failed 200 frames further down.
    assert [d.code for d in analyze_below(0, deeper).diagnostics] == ["PIE-S2006"]
    assert [d.code for d in analyze_below(200, deeper).diagnostics] == ["PIE-S2006"]
    # Accepting 450 levels still needs stack headroom, which a shallow caller has.
    assert analyze_below(0, deepest_accepted).diagnostics == ()
    assert analyze_below(10, deepest_accepted).diagnostics == ()


@pytest.mark.parametrize("position", ["where", "frame"])
def test_every_command_treats_an_expression_past_the_bound_alike(
    position: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Before, `emit-sql` wrote SQL for a WHERE that `check` refused, and every
    # command accepted a frame offset just past the bound.
    text_commands = (
        ["check"],
        ["emit-sql", "--dialect", "postgres"],
        ["emit-sql", "--dialect", "mysql"],
        ["explain"],
    )
    json_commands = (
        ["check", "--format", "json"],
        ["emit-sql", "--dialect", "postgres", "--format", "json"],
        ["explain", "--format", "json"],
    )
    accepted = tmp_path / "accepted.pietto"
    accepted.write_text(_nested_source(position, 450), encoding="utf-8")
    refused = tmp_path / "refused.pietto"
    refused.write_text(_nested_source(position, 451), encoding="utf-8")

    for command in (*text_commands, *json_commands):
        assert cli.main([*command, str(refused)]) == 1, command
        captured = capsys.readouterr()
        if command in text_commands:
            assert (captured.out, captured.err) == (
                "",
                f"{refused}:1:1 PIE-S2006 error: {_S2006_MESSAGE}\n",
            )
        else:
            diagnostics = json.loads(captured.out)["diagnostics"]
            assert [(d["code"], d["message"]) for d in diagnostics] == [
                ("PIE-S2006", _S2006_MESSAGE)
            ]
    for command in (["check"], ["emit-sql", "--dialect", "postgres"], ["explain"]):
        status = cli.main([*command, str(accepted)])
        assert "PIE-S2006" not in capsys.readouterr().err
        # A computed RANGE offset is refused (PIE-S2104).
        assert status == int(position == "frame")


def test_expression_value_types_mapping_is_readonly() -> None:
    result = analyze(
        _parse(SOURCE + "table projected:\n    from users\n    select:\n        id\n")
    )
    expression = _table(result).select_items[0].expression

    mutable_value_types = cast(
        dict[Expression, object],
        result.model.expression_value_types,
    )
    with pytest.raises(TypeError):
        mutable_value_types[expression] = result.model.expression_value_types[
            expression
        ]


def test_expression_typing_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    where email is not null\n"
        "    select:\n"
        "        email\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_expression_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    where email is null\n"
            "    select:\n"
            "        email\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _comparison_source(predicate: str) -> str:
    return f"{COMPARISON_SOURCE}    where {predicate}\n    select:\n        count\n"


def _table(result: SemanticResult) -> TableDef:
    definition = result.model.relation_symbols["projected"]
    assert isinstance(definition, TableDef)
    assert definition.where_clause is not None or definition.select_items
    return definition


def _where_expression(result: SemanticResult) -> Expression:
    table = _table(result)
    assert table.where_clause is not None
    return table.where_clause.expression


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


def test_unknown_expression_is_rejected_before_cached_inference() -> None:
    from typing import Any

    from pietto import ast_nodes as ast
    from pietto.semantic.expressions import _infer

    class UnknownExpression(ast.Expression):
        pass

    expression = UnknownExpression(
        span=ast.Span(path=None, line=1, column=1, end_line=1, end_column=2)
    )
    with pytest.raises(AssertionError, match="Unsupported expression"):
        _infer(
            expression,
            cast(Any, None),
            cast(Any, {expression: None}),
            [],
            report_unknown_name=False,
        )


def _int_field(name: str) -> RowField:
    return RowField(
        name=name,
        resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
        nullability=EffectiveNullability.NON_NULL,
    )


@pytest.mark.parametrize(
    "row",
    [
        RowSchema(fields={"id": _int_field("id"), "amount": _int_field("amount")}),
        RowSchema(is_unknown=True),
    ],
)
def test_row_lookups_are_the_name_lookups_they_replace_on_a_row_that_is_not_joined(
    row: RowSchema,
) -> None:
    for name in ("id", "amount", "missing", "rows.id"):
        assert bare_candidates(row, name) == tuple(
            field for key, field in row.fields.items() if key == name
        )
        assert bare_field(row, name) is row.fields.get(name)
        assert has_bare_field(row, name) is (name in row.fields)
    for parts in (
        ("rows", "id"),
        ("rows", "missing"),
        ("other", "id"),
        ("id",),
        ("rows", "id", "amount"),
    ):
        for qualifier in ("rows", ""):
            assert qualified_field(row, parts, qualifier) is (
                row.fields.get(parts[1])
                if len(parts) == 2 and parts[0] == qualifier
                else None
            )


def test_row_lookups_over_a_joined_row_read_bindings_and_every_bare_candidate() -> None:
    order_id, amount, customer_id, name = (
        _int_field("orders.id"),
        _int_field("orders.amount"),
        _int_field("customer.id"),
        _int_field("customer.name"),
    )
    row = RowSchema(
        fields={
            "orders.id": order_id,
            "orders.amount": amount,
            "customer.id": customer_id,
            "customer.name": name,
        },
        joined=True,
    )

    # A bare name reads the one binding that has it; two make it ambiguous.
    assert bare_candidates(row, "id") == (order_id, customer_id)
    assert bare_field(row, "id") is None
    assert has_bare_field(row, "id") is True
    assert bare_candidates(row, "name") == (name,)
    assert bare_field(row, "name") is name
    assert has_bare_field(row, "name") is True
    for missing in ("missing", "orders", "orders.id", ""):
        assert bare_candidates(row, missing) == ()
        assert bare_field(row, missing) is None
        assert has_bare_field(row, missing) is False
    # A two-part read names a binding, whatever the FROM input is called.
    assert qualified_field(row, ("orders", "id"), "orders") is order_id
    assert qualified_field(row, ("customer", "id"), "orders") is customer_id
    assert qualified_field(row, ("customer", "amount"), "orders") is None
    assert qualified_field(row, ("customers", "id"), "orders") is None
    assert qualified_field(row, ("customer",), "orders") is None
    assert qualified_field(row, ("customer", "id", "x"), "orders") is None
    assert qualified_field(row, ("customer", "id"), "") is None


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_join_tail_expressions_use_unique_fields_and_outer_nullability(
    mode: CheckMode,
) -> None:
    result = analyze(
        _parse(
            Q1_SOURCE + "shape Tag:\n"
            "    rank: Int not null\n"
            "    label: Text not null\n"
            'source tags: Tag is postgres.table("tags")\n'
            "def echo(x: Text nullable) -> Text nullable: return x\n"
            "table projected:\n"
            "    from users\n"
            "    left join tags as tag:\n"
            "        from users\n"
            "        on users.count == tag.rank\n"
            "    let:\n"
            "        copied = tag.label\n"
            "    where label is null\n"
            "    select:\n"
            "        user_count = users.count\n"
            "        tag_rank = tag.rank\n"
            "        caption = label\n"
            "        echoed = echo(copied)\n"
            "    order by:\n"
            "        label\n"
        ),
        mode_override=mode,
    )
    table = _table(result)
    schema = result.model.relation_row_schemas[table]

    assert result.diagnostics == ()
    assert not schema.is_unknown
    assert not schema.joined
    assert [
        (name, field.resolved_type.name, field.nullability)
        for name, field in schema.fields.items()
    ] == [
        ("user_count", "Int", EffectiveNullability.NON_NULL),
        ("tag_rank", "Int", EffectiveNullability.NULLABLE),
        ("caption", "Text", EffectiveNullability.NULLABLE),
        ("echoed", "Text", EffectiveNullability.NULLABLE),
    ]
    assert (
        result.model.expression_value_types[
            _where_expression(result)
        ].resolved_type.name
        == "Bool"
    )


def test_relation_expression_typing_uses_the_supplied_joined_input_row() -> None:
    script = _parse(
        Q1_SOURCE + "table projected:\n"
        "    from users\n"
        "    where extra > 0\n"
        "    select:\n"
        "        extra = users.count\n"
        "        peer_count = peer.extra\n"
        "        computed = extra + 1\n"
        "    order by:\n"
        "        extra\n"
    )
    source = next(item for item in script.definitions if isinstance(item, SourceDef))
    table = script.definitions[-1]
    assert isinstance(table, TableDef)
    joined = RowSchema(
        fields={
            "users.count": _int_field("users.count"),
            "peer.extra": RowField(
                name="peer.extra",
                resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
                nullability=EffectiveNullability.NULLABLE,
            ),
        },
        joined=True,
    )
    value_types, diagnostics, windows, named_windows = type_relation_expressions(
        script,
        from_resolutions={table.from_clause: source},
        source_row_schemas={source: RowSchema(fields={"count": _int_field("count")})},
        relation_row_schemas={},
        joined_inputs={table: joined},
    )

    assert diagnostics == []
    assert windows == named_windows == {}
    assert [
        (
            value_types[item.expression].resolved_type.name,
            value_types[item.expression].nullability,
        )
        for item in table.select_items
    ] == [
        ("Int", EffectiveNullability.NON_NULL),
        ("Int", EffectiveNullability.NULLABLE),
        ("Int", EffectiveNullability.UNKNOWN),
    ]
    assert table.order_by_clause is not None
    order_type = value_types[table.order_by_clause.items[0].expression]
    assert order_type.nullability is EffectiveNullability.NULLABLE
