from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import ConstraintDef, Script, ShapeDef, TypeDef
from pietto.errors import Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, SemanticResult, TypeKind, analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


def test_direct_alias_expands_to_builtin_target() -> None:
    result = analyze(
        _parse("type EmailText = Text\nshape User:\n    email: EmailText\n")
    )
    field_type = _shape(result, "User").fields[0].type_expr

    assert result.model.type_resolutions[field_type].kind is TypeKind.TYPE_ALIAS
    assert result.model.type_expansions[field_type].kind is TypeKind.BUILTIN
    assert result.model.type_expansions[field_type].name == "Text"
    assert result.diagnostics == ()


def test_alias_chain_expands_to_final_builtin_target() -> None:
    result = analyze(
        _parse(
            "type Email = Text\n"
            "type WorkEmail = Email\n"
            "shape User:\n"
            "    email: WorkEmail\n"
        )
    )
    field_type = _shape(result, "User").fields[0].type_expr
    work_email = _type_def(result, "WorkEmail")

    assert result.model.type_expansions[work_email.base].name == "Text"
    assert result.model.type_expansions[field_type].name == "Text"
    assert result.model.type_expansions[field_type].kind is TypeKind.BUILTIN


def test_alias_identity_remains_preserved_in_direct_resolution() -> None:
    result = analyze(_parse("type Email = Text\nshape User:\n    email: Email\n"))
    field_type = _shape(result, "User").fields[0].type_expr
    alias = _type_def(result, "Email")
    resolved = result.model.type_resolutions[field_type]

    assert resolved.name == "Email"
    assert resolved.kind is TypeKind.TYPE_ALIAS
    assert resolved.definition is alias
    assert result.model.type_expansions[field_type].name == "Text"


@pytest.mark.parametrize(
    ("source", "alias_name", "expected_kind", "target_name"),
    [
        (
            "enum Status:\n    active\ntype StatusAlias = Status\n",
            "StatusAlias",
            TypeKind.ENUM,
            "Status",
        ),
        (
            "shape User:\n    id: UUID\ntype UserAlias = User\n",
            "UserAlias",
            TypeKind.SHAPE,
            "User",
        ),
    ],
)
def test_alias_expands_to_user_type_kind(
    source: str,
    alias_name: str,
    expected_kind: TypeKind,
    target_name: str,
) -> None:
    result = analyze(_parse(source))
    alias = _type_def(result, alias_name)
    expansion = result.model.type_expansions[alias.base]

    assert expansion.kind is expected_kind
    assert expansion.name == target_name
    assert expansion.definition is result.model.type_symbols[target_name]


def test_direct_alias_cycle_reports_pie_s2003() -> None:
    result = analyze(_parse("type A = A\n"))
    alias = _type_def(result, "A")

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2003", "Type alias cycle involving A")]
    assert result.model.type_expansions[alias.base].kind is TypeKind.UNKNOWN


def test_indirect_alias_cycle_reports_one_pie_s2003() -> None:
    result = analyze(_parse("type A = B\ntype B = A\n"))

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2003", "Type alias cycle involving A")]
    assert (
        result.model.type_expansions[_type_def(result, "A").base].kind
        is TypeKind.UNKNOWN
    )
    assert (
        result.model.type_expansions[_type_def(result, "B").base].kind
        is TypeKind.UNKNOWN
    )


def test_multiple_alias_cycles_follow_source_order() -> None:
    result = analyze(_parse("type A = B\ntype B = A\ntype C = C\n"))

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (1, "PIE-S2003", "Type alias cycle involving A"),
        (3, "PIE-S2003", "Type alias cycle involving C"),
    ]


def test_unknown_alias_target_reports_only_pie_s2002() -> None:
    result = analyze(_parse("type A = Missing\ntype B = A\n"))

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2002"]
    assert (
        result.model.type_expansions[_type_def(result, "A").base].kind
        is TypeKind.UNKNOWN
    )
    assert (
        result.model.type_expansions[_type_def(result, "B").base].kind
        is TypeKind.UNKNOWN
    )


def test_constraint_returning_bool_alias_is_accepted() -> None:
    result = analyze(
        _parse(
            "type Predicate = Bool\nconstraint valid() -> Predicate:\n    return True\n"
        )
    )
    constraint = result.model.callable_symbols["valid"]
    assert isinstance(constraint, ConstraintDef)

    assert (
        result.model.type_resolutions[constraint.return_type].kind
        is TypeKind.TYPE_ALIAS
    )
    assert result.model.type_expansions[constraint.return_type].name == "Bool"
    assert result.diagnostics == ()


def test_constraint_returning_text_alias_reports_pie_s2401() -> None:
    result = analyze(
        _parse("type Label = Text\nconstraint label() -> Label:\n    return True\n")
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2401"]


def test_deep_alias_chain_returns_semantic_recursion_diagnostic() -> None:
    aliases = [f"type Alias{index} = Alias{index + 1}\n" for index in range(1399)]
    aliases.append("type Alias1399 = Int\n")
    script = _parse("".join(aliases))

    result = analyze(script)

    assert result.model.mode is CheckMode.CHECKED
    assert result.model.type_symbols == {}
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-S2006"
    assert diagnostic.severity is Severity.ERROR
    assert "recursion limit" in diagnostic.message


def test_type_expansions_mapping_is_readonly() -> None:
    result = analyze(_parse("type Email = Text\n"))
    type_expr = _type_def(result, "Email").base

    with pytest.raises(TypeError):
        result.model.type_expansions[type_expr] = (  # type: ignore[index]
            result.model.type_expansions[type_expr]
        )


def test_type_alias_expansion_does_not_mutate_input_ast() -> None:
    script = _parse("type Email = Text\ntype WorkEmail = Email\n")
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_type_alias_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(_parse("type Email = Text\ntype WorkEmail = Email\n"))

    _assert_no_antlr_nodes(result)


_ALIAS_TYPES = "type Age = Int\ntype Money = Decimal(12, 2)\ntype Cash = Money\n"
_ALIAS_RELATIONS = (
    "query filtered:\n"
    "    from orders\n"
    "    where age + 1 > 18 and amount * fee > 0\n"
    "    select:\n"
    "        id\n"
    "        older = age + 1\n"
    "        doubled = age * 2\n"
    "        gap = age - bonus\n"
    "        rest = age % 7\n"
    "        negated = -age\n"
    "        total = amount + fee\n"
    "        less = fee - 1\n"
    "    order by:\n"
    "        age * 2 desc\n"
    "        id\n"
    "table totals:\n"
    "    from orders\n"
    "    select:\n"
    "        total = sum(amount)\n"
    "        mean = avg(fee)\n"
    "        top = max(amount)\n"
    "        low = min(age)\n"
    "        ages = sum(age + 1)\n"
    "query ranked:\n"
    "    from orders\n"
    "    let older = age + 5\n"
    "    group by:\n"
    "        region\n"
    "    select:\n"
    "        region\n"
    "        r = rank() window(order by ages desc)\n"
    "        total = sum(amount)\n"
    "        ages = sum(age + 1)\n"
    "        older_ages = sum(older)\n"
    "        distinct_ages = count_distinct(age)\n"
    "    having:\n"
    "        total > 0\n"
)


def _alias_program(connector: str, *, aliased: bool) -> str:
    def typed(alias: str, base: str) -> str:
        return alias if aliased else base

    return (
        (_ALIAS_TYPES if aliased else "\n" * _ALIAS_TYPES.count("\n"))
        + "shape Order:\n"
        + "    id: Int\n"
        + "    region: Text\n"
        + f"    age: {typed('Age', 'Int')}\n"
        + f"    bonus: {typed('Age', 'Int')}\n"
        + f"    amount: {typed('Money', 'Decimal(12, 2)')}\n"
        + f"    fee: {typed('Cash', 'Decimal(12, 2)')}\n"
        + f'source orders: Order = {connector}("orders")\n'
        + _ALIAS_RELATIONS
    )


@pytest.mark.parametrize(
    ("connector", "emitter", "quote"),
    [
        ("postgres.table", emit_postgres_sql, '"'),
        ("mysql.table", emit_mysql_sql, "`"),
    ],
    ids=("postgres", "mysql"),
)
def test_alias_operands_and_aggregate_arguments_emit_the_base_typed_sql(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    quote: str,
) -> None:
    # Arithmetic and aggregates read an alias, alias chains included, as the
    # type it expands to: the program emits the bytes of its base-typed twin,
    # and computed outputs take the base type, not the alias.
    def compiled(aliased: bool) -> tuple[SemanticResult, ScriptIR]:
        script = _parse(_alias_program(connector, aliased=aliased))
        result = analyze(script)
        assert result.diagnostics == ()
        # A modern `let name = expression` line is a naming declaration the
        # analyzer resolves into the relation's let clause, so lower the
        # analyzed script, as every later reader does.
        assert result.script is not None
        lowered = build_ir(result.script, result.model)
        assert lowered.diagnostics == ()
        assert lowered.ir is not None
        return result, lowered.ir

    semantic, script_ir = compiled(True)
    sql = emitter(script_ir)
    q = quote
    assert sql.diagnostics == ()
    assert [artifact.sql for artifact in sql.artifacts] == [
        "SELECT\n"
        f"    {q}id{q} AS {q}id{q},\n"
        f"    {q}age{q} + 1 AS {q}older{q},\n"
        f"    {q}age{q} * 2 AS {q}doubled{q},\n"
        f"    {q}age{q} - {q}bonus{q} AS {q}gap{q},\n"
        f"    {q}age{q} % 7 AS {q}rest{q},\n"
        f"    -{q}age{q} AS {q}negated{q},\n"
        f"    {q}amount{q} + {q}fee{q} AS {q}total{q},\n"
        f"    {q}fee{q} - 1 AS {q}less{q}\n"
        f"FROM {q}orders{q}\n"
        f"WHERE (({q}age{q} + 1) > 18) AND (({q}amount{q} * {q}fee{q}) > 0)\n"
        "ORDER BY\n"
        f"    {q}age{q} * 2 DESC,\n"
        f"    {q}id{q} ASC",
        "SELECT\n"
        f"    SUM({q}amount{q}) AS {q}total{q},\n"
        f"    AVG({q}fee{q}) AS {q}mean{q},\n"
        f"    MAX({q}amount{q}) AS {q}top{q},\n"
        f"    MIN({q}age{q}) AS {q}low{q},\n"
        f"    SUM(({q}age{q} + 1)) AS {q}ages{q}\n"
        f"FROM {q}orders{q}",
        "SELECT\n"
        f"    {q}region{q} AS {q}region{q},\n"
        f"    RANK() OVER (ORDER BY SUM(({q}age{q} + 1)) DESC) AS {q}r{q},\n"
        f"    SUM({q}amount{q}) AS {q}total{q},\n"
        f"    SUM(({q}age{q} + 1)) AS {q}ages{q},\n"
        f"    SUM(({q}age{q} + 5)) AS {q}older_ages{q},\n"
        f"    COUNT(DISTINCT {q}age{q}) AS {q}distinct_ages{q}\n"
        f"FROM {q}orders{q}\n"
        "GROUP BY\n"
        f"    {q}region{q}\n"
        "HAVING\n"
        f"    SUM({q}amount{q}) > 0",
    ]
    assert sql == emitter(compiled(False)[1])

    schemas = {
        relation.name: schema.fields
        for relation, schema in semantic.model.relation_row_schemas.items()
    }
    assert {
        (relation, name): (field.resolved_type.kind, field.resolved_type.name)
        for relation, name in (
            ("filtered", "id"),
            ("filtered", "older"),
            ("filtered", "negated"),
            ("filtered", "total"),
            ("totals", "top"),
            ("totals", "low"),
            ("ranked", "total"),
            ("ranked", "ages"),
        )
        for field in (schemas[relation][name],)
    } == {
        ("filtered", "id"): (TypeKind.BUILTIN, "Int"),
        ("filtered", "older"): (TypeKind.BUILTIN, "Int"),
        ("filtered", "negated"): (TypeKind.BUILTIN, "Int"),
        ("filtered", "total"): (TypeKind.BUILTIN, "Decimal"),
        ("totals", "top"): (TypeKind.BUILTIN, "Decimal"),
        ("totals", "low"): (TypeKind.BUILTIN, "Int"),
        ("ranked", "total"): (TypeKind.BUILTIN, "Decimal"),
        ("ranked", "ages"): (TypeKind.BUILTIN, "Int"),
    }


_TEXT_BOOL_ALIAS_TYPES = (
    "type Email = Text\n"
    "type Handle = Email\n"
    "type Flag = Bool\n"
    "type Money = Decimal(12, 2)\n"
)


def _text_bool_alias_program(connector: str, relations: str, *, aliased: bool) -> str:
    # The base-typed twin keeps the alias lines blank, so both programs
    # report at the same line and column.
    def typed(alias: str, base: str) -> str:
        return alias if aliased else base

    return (
        (
            _TEXT_BOOL_ALIAS_TYPES
            if aliased
            else "\n" * _TEXT_BOOL_ALIAS_TYPES.count("\n")
        )
        + "shape Person:\n"
        + "    id: Int\n"
        + "    region: Text\n"
        + f"    email: {typed('Email', 'Text')}\n"
        + f"    handle: {typed('Handle', 'Text')}\n"
        + f"    flag: {typed('Flag', 'Bool')}\n"
        + f"    amount: {typed('Money', 'Decimal(12, 2)')}\n"
        + "    flagged = check(flag)\n"
        + "    flagged_ix = index(id) when flag\n"
        + f'source people: Person = {connector}("people")\n'
        + relations
    )


_TEXT_BOOL_ALIAS_RELATIONS = (
    "query filtered:\n"
    "    from people\n"
    '    where flag and email like "a%" and handle not like "%!_x"\n'
    "    select:\n"
    "        id\n"
    "        lowered = lower(email)\n"
    "        trimmed = trim(handle)\n"
    "        length = len(lower(trim(email)))\n"
    '        hit = "x" not like handle\n'
    "query counted:\n"
    "    from people\n"
    "    group by:\n"
    "        region\n"
    "        flag\n"
    "    select:\n"
    "        region\n"
    "        flag\n"
    "        n = count(lower(email))\n"
    "        d = count_distinct(trim(handle))\n"
    "    having:\n"
    "        flag and n > 0\n"
    "table windowed:\n"
    "    from people\n"
    "    select:\n"
    "        id\n"
    "        previous = lag(email, 1, handle) window(order by id)\n"
    "        first = first_value(amount) window(partition by region order by id)\n"
)


@pytest.mark.parametrize(
    ("connector", "emitter", "quote"),
    [
        ("postgres.table", emit_postgres_sql, '"'),
        ("mysql.table", emit_mysql_sql, "`"),
    ],
    ids=("postgres", "mysql"),
)
def test_alias_like_function_arguments_and_conditions_emit_base_typed_sql(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    quote: str,
) -> None:
    # LIKE operands, scalar and window value function arguments, and where,
    # having, shape check and index conditions read an alias, alias chains
    # included, as the type it expands to: the program emits the bytes of its
    # base-typed twin, and computed outputs take the base type.
    def compiled(aliased: bool) -> tuple[SemanticResult, ScriptIR]:
        script = _parse(
            _text_bool_alias_program(
                connector, _TEXT_BOOL_ALIAS_RELATIONS, aliased=aliased
            )
        )
        result = analyze(script)
        assert result.diagnostics == ()
        assert result.script is not None
        lowered = build_ir(result.script, result.model)
        assert lowered.diagnostics == ()
        assert lowered.ir is not None
        return result, lowered.ir

    semantic, script_ir = compiled(True)
    sql = emitter(script_ir)
    q = quote
    lower, trim, length, exclude = (
        ("lower", "trim", "length", " EXCLUDE NO OTHERS")
        if q == '"'
        else ("LOWER", "TRIM", "CHAR_LENGTH", "")
    )
    assert sql.diagnostics == ()
    assert [artifact.sql for artifact in sql.artifacts] == [
        "SELECT\n"
        f"    {q}id{q} AS {q}id{q},\n"
        f"    {lower}({q}email{q}) AS {q}lowered{q},\n"
        f"    {trim}({q}handle{q}) AS {q}trimmed{q},\n"
        f"    {length}({lower}({trim}({q}email{q}))) AS {q}length{q},\n"
        f"    'x' NOT LIKE {q}handle{q} ESCAPE '!' AS {q}hit{q}\n"
        f"FROM {q}people{q}\n"
        f"WHERE ({q}flag{q} AND ({q}email{q} LIKE 'a%' ESCAPE '!')) AND "
        f"({q}handle{q} NOT LIKE '%!_x' ESCAPE '!')",
        "SELECT\n"
        f"    {q}region{q} AS {q}region{q},\n"
        f"    {q}flag{q} AS {q}flag{q},\n"
        f"    COUNT({lower}({q}email{q})) AS {q}n{q},\n"
        f"    COUNT(DISTINCT {trim}({q}handle{q})) AS {q}d{q}\n"
        f"FROM {q}people{q}\n"
        "GROUP BY\n"
        f"    {q}region{q},\n"
        f"    {q}flag{q}\n"
        "HAVING\n"
        f"    {q}flag{q} AND (COUNT({lower}({q}email{q})) > 0)",
        "SELECT\n"
        f"    {q}id{q} AS {q}id{q},\n"
        f"    LAG({q}email{q}, 1, {q}handle{q}) OVER (ORDER BY {q}id{q} ASC) "
        f"AS {q}previous{q},\n"
        f"    FIRST_VALUE({q}amount{q}) OVER (PARTITION BY {q}region{q} ORDER BY "
        f"{q}id{q} ASC RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW{exclude}) "
        f"AS {q}first{q}\n"
        f"FROM {q}people{q}",
    ]
    assert sql == emitter(compiled(False)[1])

    schemas = {
        relation.name: schema.fields
        for relation, schema in semantic.model.relation_row_schemas.items()
    }
    assert {
        name: (field.resolved_type.kind, field.resolved_type.name)
        for name, field in schemas["filtered"].items()
    } == {
        "id": (TypeKind.BUILTIN, "Int"),
        "lowered": (TypeKind.BUILTIN, "Text"),
        "trimmed": (TypeKind.BUILTIN, "Text"),
        "length": (TypeKind.BUILTIN, "Int"),
        "hit": (TypeKind.BUILTIN, "Bool"),
    }
    assert {
        name: (field.resolved_type.kind, field.resolved_type.name)
        for name, field in schemas["windowed"].items()
    } == {
        "id": (TypeKind.BUILTIN, "Int"),
        "previous": (TypeKind.BUILTIN, "Text"),
        "first": (TypeKind.BUILTIN, "Decimal"),
    }


def test_alias_arguments_and_conditions_are_checked_as_their_base_type() -> None:
    # An alias argument or condition is accepted or refused exactly where its
    # base type is; a refusal that names the argument type names the alias.
    def facts(
        relations: str, *, aliased: bool
    ) -> tuple[tuple[str, str, int, int], ...]:
        result = analyze(
            _parse(
                _text_bool_alias_program("postgres.table", relations, aliased=aliased)
            )
        )
        return tuple(
            (d.code, d.message, d.location.line, d.location.column)
            for d in result.diagnostics
        )

    relations = (
        "query q:\n"
        "    from people\n"
        "    where amount\n"
        "    select:\n"
        "        id\n"
        '        m = matches(email, "^a")\n'
        '        s = len(email) + 1 if contains(handle, "@") else 0\n'
        "        a = lower(amount)\n"
        '        b = amount like "a%"\n'
        "        c = len(email) + email\n"
    )
    refused = (
        ("PIE-S2202", "Expected Bool expression in where clause", 17, 11),
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Money",
            22,
            13,
        ),
        (
            "PIE-S2105",
            "Invalid operands for operator like: expected Text operands",
            23,
            13,
        ),
        (
            "PIE-S2105",
            "Invalid operands for operator +: expected numeric operands; "
            "string concatenation is not supported yet",
            24,
            13,
        ),
    )
    assert facts(relations, aliased=True) == refused
    assert facts(relations, aliased=False) == tuple(
        (code, message.replace("got Money", "got Decimal"), line, column)
        for code, message, line, column in refused
    )


def test_count_of_an_enum_alias_is_refused_as_count_of_the_enum() -> None:
    # count and count_distinct read an alias of an enum, alias chains, let
    # values and derived fields included, as that enum: PIE-S2314 at check,
    # never a program that passes check and then fails to emit.
    def facts(*, aliased: bool) -> tuple[tuple[str, str, int, int], ...]:
        # The enum twin keeps the alias lines blank, so both programs report
        # at the same line and column.
        aliases = "type Phase = Status\ntype Stage = Phase\n" if aliased else "\n\n"
        state, stage = ("Phase", "Stage") if aliased else ("Status", "Status")
        result = analyze(
            _parse(
                f"enum Status:\n    active\n    closed\n{aliases}"
                "shape Order:\n"
                "    id: Int\n"
                "    region: Text\n"
                f"    state: {state}\n"
                f"    stage: {stage} | None\n"
                'source orders: Order = postgres.table("orders")\n'
                "table counted:\n"
                "    from orders\n"
                "    select:\n"
                "        n = count(state)\n"
                "query grouped:\n"
                "    from orders\n"
                "    group by:\n"
                "        region\n"
                "    select:\n"
                "        region\n"
                "        n = count(stage)\n"
                "        d = count_distinct(state)\n"
                "table via_let:\n"
                "    from orders\n"
                "    let v = stage\n"
                "    select:\n"
                "        n = count(v)\n"
                "table copied:\n"
                "    from orders\n"
                "    select:\n"
                "        id\n"
                "        state\n"
                "query recounted:\n"
                "    from copied\n"
                "    select:\n"
                "        n = count(state)\n"
            )
        )
        return tuple(
            (d.code, d.message, d.location.line, d.location.column)
            for d in result.diagnostics
        )

    count = "Aggregate function count expects concrete non-Any field argument, got "
    count_distinct = (
        "Aggregate function count_distinct expects Bool, Int, Float, Decimal, "
        "Text, Date, Timestamp, or UUID field argument, got "
    )
    # `recounted` reads the same-file table `copied` by name (PIE-S2382).
    same_file = (
        "PIE-S2382",
        "`copied` is a table of this file; single-file SQL reads it by name, so "
        "the SQL runs only where the database already has a relation named copied "
        "(an EXPLICIT_MODULES project emits it as a CTE)",
        35,
        5,
    )
    assert facts(aliased=True) == (
        ("PIE-S2314", count + "Phase", 15, 13),
        ("PIE-S2314", count + "Stage", 22, 13),
        ("PIE-S2314", count_distinct + "Phase", 23, 13),
        ("PIE-S2314", count + "Stage", 28, 13),
        same_file,
        ("PIE-S2314", count + "Phase", 37, 13),
    )
    assert facts(aliased=False) == (
        ("PIE-S2314", count + "Status", 15, 13),
        ("PIE-S2314", count + "Status", 22, 13),
        ("PIE-S2314", count_distinct + "Status", 23, 13),
        ("PIE-S2314", count + "Status", 28, 13),
        same_file,
        ("PIE-S2314", count + "Status", 37, 13),
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _type_def(result: SemanticResult, name: str) -> TypeDef:
    definition = result.model.type_symbols[name]
    assert isinstance(definition, TypeDef)
    return definition


def _shape(result: SemanticResult, name: str) -> ShapeDef:
    definition = result.model.type_symbols[name]
    assert isinstance(definition, ShapeDef)
    return definition


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
