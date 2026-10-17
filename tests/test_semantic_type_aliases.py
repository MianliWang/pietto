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
        _parse(
            "type EmailText = Text not null\n"
            "shape User:\n"
            "    email: EmailText not null\n"
        )
    )
    field_type = _shape(result, "User").fields[0].type_expr

    assert result.model.type_resolutions[field_type].kind is TypeKind.TYPE_ALIAS
    assert result.model.type_expansions[field_type].kind is TypeKind.BUILTIN
    assert result.model.type_expansions[field_type].name == "Text"
    assert result.diagnostics == ()


def test_alias_chain_expands_to_final_builtin_target() -> None:
    result = analyze(
        _parse(
            "type Email = Text not null\n"
            "type WorkEmail = Email not null\n"
            "shape User:\n"
            "    email: WorkEmail not null\n"
        )
    )
    field_type = _shape(result, "User").fields[0].type_expr
    work_email = _type_def(result, "WorkEmail")

    assert result.model.type_expansions[work_email.base].name == "Text"
    assert result.model.type_expansions[field_type].name == "Text"
    assert result.model.type_expansions[field_type].kind is TypeKind.BUILTIN


def test_alias_identity_remains_preserved_in_direct_resolution() -> None:
    result = analyze(
        _parse("type Email = Text not null\nshape User:\n    email: Email not null\n")
    )
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
            "enum Status:\n    active\ntype StatusAlias = Status not null\n",
            "StatusAlias",
            TypeKind.ENUM,
            "Status",
        ),
        (
            "shape User:\n    id: UUID not null\ntype UserAlias = User not null\n",
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
    result = analyze(_parse("type A = A not null\n"))
    alias = _type_def(result, "A")

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2003", "Type alias cycle involving A")]
    assert result.model.type_expansions[alias.base].kind is TypeKind.UNKNOWN


def test_indirect_alias_cycle_reports_one_pie_s2003() -> None:
    result = analyze(_parse("type A = B not null\ntype B = A not null\n"))

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
    result = analyze(
        _parse("type A = B not null\ntype B = A not null\ntype C = C not null\n")
    )

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (1, "PIE-S2003", "Type alias cycle involving A"),
        (3, "PIE-S2003", "Type alias cycle involving C"),
    ]


def test_unknown_alias_target_reports_only_pie_s2002() -> None:
    result = analyze(_parse("type A = Missing not null\ntype B = A not null\n"))

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
            "type Predicate = Bool not null\n"
            "constraint valid() -> Predicate not null:\n"
            "    true\n"
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
        _parse(
            "type Label = Text not null\n"
            "constraint label() -> Label not null:\n"
            "    true\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2401"]


def test_deep_alias_chain_returns_semantic_recursion_diagnostic() -> None:
    aliases = [
        f"type Alias{index} = Alias{index + 1} not null\n" for index in range(1399)
    ]
    aliases.append("type Alias1399 = Int not null\n")
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
    result = analyze(_parse("type Email = Text not null\n"))
    type_expr = _type_def(result, "Email").base

    with pytest.raises(TypeError):
        result.model.type_expansions[type_expr] = (  # type: ignore[index]
            result.model.type_expansions[type_expr]
        )


def test_type_alias_expansion_does_not_mutate_input_ast() -> None:
    script = _parse("type Email = Text not null\ntype WorkEmail = Email not null\n")
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_type_alias_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse("type Email = Text not null\ntype WorkEmail = Email not null\n")
    )

    _assert_no_antlr_nodes(result)


_ALIAS_TYPES = (
    "type Age = Int not null\n"
    "type Money = Decimal(12, 2) not null\n"
    "type Cash = Money not null\n"
)
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
    "    let:\n"
    "        older = age + 5\n"
    "    group by:\n"
    "        region\n"
    "    select:\n"
    "        region\n"
    "        r = rank() window:\n"
    "            order by:\n"
    "                ages desc\n"
    "        total = sum(amount)\n"
    "        ages = sum(age + 1)\n"
    "        older_ages = sum(older)\n"
    "        distinct_ages = count_distinct(age)\n"
    "    satisfying:\n"
    "        total > 0\n"
)


def _alias_program(connector: str, *, aliased: bool) -> str:
    def typed(alias: str, base: str) -> str:
        return alias if aliased else base

    return (
        (_ALIAS_TYPES if aliased else "\n" * _ALIAS_TYPES.count("\n"))
        + "shape Order:\n"
        + "    id: Int not null\n"
        + "    region: Text not null\n"
        + f"    age: {typed('Age', 'Int')} not null\n"
        + f"    bonus: {typed('Age', 'Int')} not null\n"
        + f"    amount: {typed('Money', 'Decimal(12, 2)')} not null\n"
        + f"    fee: {typed('Cash', 'Decimal(12, 2)')} not null\n"
        + f'source orders: Order is {connector}("orders")\n'
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
        lowered = build_ir(script, result.model)
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
    "type Email = Text not null\n"
    "type Handle = Email not null\n"
    "type Flag = Bool not null\n"
    "type Money = Decimal(12, 2) not null\n"
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
        + "    id: Int not null\n"
        + "    region: Text not null\n"
        + f"    email: {typed('Email', 'Text')} not null\n"
        + f"    handle: {typed('Handle', 'Text')} not null\n"
        + f"    flag: {typed('Flag', 'Bool')} not null\n"
        + f"    amount: {typed('Money', 'Decimal(12, 2)')} not null\n"
        + "    check flagged:\n"
        + "        flag\n"
        + "    index flagged_ix on id when flag\n"
        + f'source people: Person is {connector}("people")\n'
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
    "    satisfying:\n"
    "        flag and n > 0\n"
    "table windowed:\n"
    "    from people\n"
    "    select:\n"
    "        id\n"
    "        previous = lag(email, 1, handle) window:\n"
    "            order by:\n"
    "                id\n"
    "        first = first_value(amount) window:\n"
    "            partition by:\n"
    "                region\n"
    "            order by:\n"
    "                id\n"
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
    # satisfying, shape check and index conditions read an alias, alias chains
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
        lowered = build_ir(script, result.model)
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
        ("PIE-S2202", "Expected Bool expression in where clause", 18, 11),
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Money",
            23,
            13,
        ),
        (
            "PIE-S2105",
            "Invalid operands for operator like: expected Text operands",
            24,
            13,
        ),
        (
            "PIE-S2105",
            "Invalid operands for operator +: expected numeric operands",
            25,
            13,
        ),
    )
    assert facts(relations, aliased=True) == refused
    assert facts(relations, aliased=False) == tuple(
        (code, message.replace("got Money", "got Decimal"), line, column)
        for code, message, line, column in refused
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
