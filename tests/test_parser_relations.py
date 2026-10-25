from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from pathlib import Path
from typing import Any, cast, get_args

import pytest

from _pietto_parser_layout import layout_free
from pietto.ast_nodes import (
    BinaryExpr,
    BlockRelationDef,
    CallExpr,
    CaptureClause,
    CapturedFieldExpr,
    ComparisonExpr,
    DottedNameExpr,
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    FromClause,
    FunctionDef,
    GroupByClause,
    LetRelationDef,
    LiteralExpr,
    ModuleDeclarationKind,
    NameExpr,
    Node,
    Nullability,
    QueryDef,
    RelationMembershipExpr,
    SelectBody,
    SetOperationBody,
    ShapeDef,
    SourceDef,
    SetRelationDef,
    Span,
    TableDef,
    TableFunctionFromClause,
    TypeDef,
    ValuesBody,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source


def test_definition_union_matches_top_level_grammar() -> None:
    assert get_args(Definition) == (
        TypeDef,
        EnumDef,
        ConstraintDef,
        DeriveDef,
        ShapeDef,
        SourceDef,
        TableDef,
        QueryDef,
        SetRelationDef,
        BlockRelationDef,
        FunctionDef,
    )


@pytest.mark.parametrize(
    "body",
    [
        "    select:\n        id\n",
        "    from input_relation\n",
        "    from input_relation\n    select:\n",
        "    from input_relation\n    select:\n        alias =\n",
    ],
)
def test_table_and_query_malformed_body_diagnostics_are_consistent(
    body: str,
) -> None:
    path = Path("examples/relations/malformed.pietto")
    table_result = parse_source(f"table broken:\n{body}", path=path)
    query_result = parse_source(f"query broken:\n{body}", path=path)

    assert table_result.ast is None
    assert query_result.ast is None
    assert table_result.diagnostics == query_result.diagnostics
    assert table_result.diagnostics
    assert all(
        diagnostic.code == "PIE-P1000"
        and diagnostic.severity is Severity.ERROR
        and diagnostic.location.path == str(path)
        for diagnostic in table_result.diagnostics
    )


@pytest.mark.parametrize("kind", ["table", "query"])
@pytest.mark.parametrize(
    "clause",
    [
        "    join accounts on row.account_id == accounts.id\n",
        "    having count(id) > 1\n",
        "    order by id\n",
        "    window recent\n",
        "    expect:\n        id is not null\n",
        "    union other_relation\n",
    ],
)
def test_relations_reject_not_yet_supported_clauses(
    kind: str,
    clause: str,
) -> None:
    result = parse_source(
        f"{kind} projected:\n    from input_relation\n{clause}    select:\n        id\n"
    )

    assert result.ast is None
    assert any(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


@pytest.mark.parametrize("kind", ["table", "query"])
def test_inline_group_by_requires_no_colon(kind: str) -> None:
    result = parse_source(
        f"{kind} grouped:\n    from input_relation\n"
        "    group by account_id\n    select account_id\n"
    )
    assert result.diagnostics == () and result.ast is not None
    relation = result.ast.definitions[0]
    assert isinstance(relation, (TableDef, QueryDef))
    assert relation.group_by_clause is not None
    assert [
        item.key.name
        for item in relation.group_by_clause.items
        if isinstance(item.key, NameExpr)
    ] == ["account_id"]


def _block(source: str, path: str = "blocks.pietto") -> BlockRelationDef:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[-1]
    assert type(definition) is BlockRelationDef
    return definition


@pytest.mark.parametrize("kind", ["table", "query"])
def test_flat_relation_lets_precede_the_body_and_keep_their_own_spans(
    kind: str,
) -> None:
    definition = _block(
        f"{kind} vip_report:\n"
        "    let vip:\n"
        "        from customers\n"
        '        where tier == "gold"\n'
        "        select:\n"
        "            id\n"
        "\n"
        "    let values:\n"
        "        from vip\n"
        "        select:\n"
        "            id\n"
        "    from values\n"
        "    where customer_id in vip\n"
        "    select:\n"
        "        id\n"
    )

    assert definition.kind is ModuleDeclarationKind(kind)
    assert definition.parameters == ()
    vip, values = definition.let_relations
    assert type(vip) is LetRelationDef and vip.name == "vip"
    assert vip.span == Span(
        path="blocks.pietto", line=2, column=5, end_line=6, end_column=15
    )
    assert vip.captures == ()
    assert type(vip.body) is SelectBody
    assert type(vip.body.from_clause) is FromClause
    assert vip.body.from_clause.source_name == "customers"
    assert values.name == "values"
    assert type(values.body) is SelectBody
    assert type(values.body.from_clause) is FromClause
    assert values.body.from_clause.source_name == "vip"
    body = definition.body
    assert type(body) is SelectBody
    assert type(body.from_clause) is FromClause
    assert body.from_clause.source_name == "values"
    assert body.where_clause is not None
    assert type(body.where_clause.expression) is RelationMembershipExpr


def test_derived_table_is_a_let_read_by_name_beside_row_level_let() -> None:
    definition = _block(
        "query frequent_customers:\n"
        "    let counts:\n"
        "        from orders\n"
        "        group by:\n"
        "            customer_id\n"
        "        select:\n"
        "            customer_id\n"
        "            n = count()\n"
        "    from counts\n"
        "\n"
        "    let doubled = n * 2\n"
        "    where doubled > 10\n"
        "    select:\n"
        "        customer_id\n"
    )

    (counts,) = definition.let_relations
    assert type(counts.body) is SelectBody
    assert type(counts.body.group_by_clause) is GroupByClause
    body = definition.body
    assert type(body) is SelectBody and type(body.from_clause) is FromClause
    assert body.from_clause.source_name == "counts"
    assert body.let_clause is None
    assert [item.name for item in body.naming_declarations] == ["doubled"]


def test_capture_lines_start_only_a_let_body() -> None:
    definition = _block(
        "query latest_order:\n"
        "    let latest:\n"
        "        capture customers\n"
        "\n"
        "        capture capture\n"
        "        from orders\n"
        "        select:\n"
        "            id\n"
        "    from customers\n"
        "    select:\n"
        "        id\n"
    )

    (latest,) = definition.let_relations
    assert [type(item) for item in latest.captures] == [CaptureClause] * 2
    assert [item.name for item in latest.captures] == ["customers", "capture"]
    assert latest.captures[0].span == Span(
        path="blocks.pietto", line=3, column=9, end_line=3, end_column=26
    )


def test_a_capture_qualified_value_name_reads_the_captured_input() -> None:
    """Only a two-part value name qualified by a capture line is rewritten."""
    definition = _block(
        "query q:\n"
        "    let m:\n"
        "        capture lhs\n"
        "        capture lhs\n"
        "        from rhs\n"
        "        where rhs.key == lhs.key and key == lhs.id.x\n"
        "        select:\n"
        "            id\n"
        "            v = lhs.key\n"
        "    from lhs\n"
        "    where lhs.key > 0\n"
        "    select:\n"
        "        id\n"
    )

    (let,) = definition.let_relations
    body = let.body
    assert type(body) is SelectBody and body.where_clause is not None
    both = body.where_clause.expression
    assert type(both) is BinaryExpr and both.operator == "and"
    inner, outer = both.left, both.right
    assert type(inner) is ComparisonExpr and type(outer) is ComparisonExpr
    assert inner.left == DottedNameExpr(span=inner.left.span, parts=("rhs", "key"))
    assert inner.right == CapturedFieldExpr(
        span=Span(path="blocks.pietto", line=6, column=26, end_line=6, end_column=33),
        capture="lhs",
        field="key",
        ordinal=0,
    )
    # A bare name and a three-part name keep their nodes.
    assert type(outer.left) is NameExpr
    assert type(outer.right) is DottedNameExpr
    assert type(body.select_items[1].expression) is CapturedFieldExpr
    # The declaration body has no capture line of its own.
    declared: Any = definition.body
    assert declared.where_clause is not None
    assert type(declared.where_clause.expression.left) is DottedNameExpr


def test_let_bodies_may_be_values_or_set_operations() -> None:
    definition = _block(
        "table codes:\n"
        "    let seed:\n"
        "        values(id: Int,):\n"
        "            1\n"
        "    let empty:\n"
        "        values(id: Int)\n"
        "    let both:\n"
        "        union all:\n"
        "            from seed\n"
        "            from empty\n"
        "    from both\n"
        "    select:\n"
        "        id\n"
    )

    seed, empty, both = definition.let_relations
    assert type(seed.body) is ValuesBody and len(seed.body.rows) == 1
    assert type(empty.body) is ValuesBody and empty.body.rows == ()
    assert type(both.body) is SetOperationBody
    assert [item.relation_name for item in both.body.operands] == ["seed", "empty"]


@pytest.mark.parametrize(
    "source",
    [
        (
            "query q:\n    let a:\n        let b:\n            from r\n"
            "            select:\n                id\n        from b\n"
            "        select:\n            id\n    from a\n    select:\n        id\n"
        ),
        (
            "query q:\n    from d:\n        from r\n        select:\n"
            "            id\n    select:\n        id\n"
        ),
        (
            "query q:\n    query a:\n        from r\n        select:\n"
            "            id\n    from a\n    select:\n        id\n"
        ),
        "query q:\n    capture r\n    from r\n    select:\n        id\n",
        (
            "query q:\n    let a:\n        from r\n        capture r\n"
            "        select:\n            id\n    from a\n    select:\n        id\n"
        ),
        (
            "query q:\n    let a:\n        capture a, b\n        from r\n"
            "        select:\n            id\n    from a\n    select:\n        id\n"
        ),
        (
            "query q:\n    from r\n    let a:\n        from r\n"
            "        select:\n            id\n    select:\n        id\n"
        ),
    ],
    ids=[
        "nested_let",
        "inline_from_block",
        "local_query_declaration",
        "capture_in_top_level_body",
        "capture_after_let_from",
        "capture_list",
        "let_relation_after_from",
    ],
)
def test_unapproved_relation_block_spellings_are_syntax_errors(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert any(item.code == "PIE-P1000" for item in result.diagnostics)


@pytest.mark.parametrize("kind", ["table", "query"])
def test_typed_values_body_has_rows_or_a_zero_row_header(kind: str) -> None:
    definition = _block(
        f"{kind} seed:\n"
        "    values(id: Int, label: Text | None):\n"
        '        1, "new"\n'
        "\n"
        "        2, None\n"
    )
    empty = _block(f"{kind} empty_seed:\n    values(id: Int)\n")

    body = definition.body
    assert type(body) is ValuesBody
    assert body.span == Span(
        path="blocks.pietto", line=2, column=5, end_line=5, end_column=16
    )
    assert [(item.name, item.type.nullability) for item in body.columns] == [
        ("id", Nullability.NOT_NULL),
        ("label", Nullability.NULLABLE),
    ]
    assert [[type(value) for value in row.values] for row in body.rows] == [
        [LiteralExpr, LiteralExpr]
    ] * 2
    assert [row.span.line for row in body.rows] == [3, 5]
    assert type(empty.body) is ValuesBody and empty.body.rows == ()
    assert [item.name for item in empty.body.columns] == ["id"]
    for source in (
        "query q:\n    values():\n        1\n",
        "query q:\n    values:\n        1\n",
        "query q:\n    values(id: Int):\n",
        "query q:\n    values(id: Int):\n        1,\n",
    ):
        result = parse_source(source)
        assert result.ast is None
        assert any(item.code == "PIE-P1000" for item in result.diagnostics)


def test_table_function_from_keeps_its_call_and_binding_apart() -> None:
    definition = _block(
        "query days:\n    from generate_series(1, 31, 1) as n\n    select:\n        n\n"
    )

    body = definition.body
    assert type(body) is SelectBody
    function = body.from_clause
    assert type(function) is TableFunctionFromClause
    assert not hasattr(function, "source_name")
    assert function.binding_name == "n"
    assert type(function.call) is CallExpr
    assert type(function.call.callee) is NameExpr
    assert function.call.callee.name == "generate_series"
    assert [
        argument.value
        for argument in function.call.arguments
        if type(argument) is LiteralExpr
    ] == [1, 31, 1]
    assert function.span == Span(
        path="blocks.pietto", line=2, column=5, end_line=2, end_column=40
    )
    plain = parse_source("query q:\n    from generate_series\n    select:\n        n\n")
    assert plain.ast is not None and type(plain.ast.definitions[0]) is QueryDef
    unbound = parse_source(
        "query q:\n    from generate_series(1)\n    select:\n        n\n"
    )
    assert unbound.ast is None


def test_existing_relation_forms_keep_their_existing_classes() -> None:
    result = parse_source(
        "table t:\n    from rows\n    select:\n        id\n"
        "query q:\n    union all:\n        from a\n        from b\n"
    )

    assert result.ast is not None
    assert [type(item) for item in result.ast.definitions] == [TableDef, SetRelationDef]
    nested = _block(
        "query q:\n    let a:\n        from rows\n        select:\n            id\n"
        "    union all:\n        from a\n        from a\n"
    )
    assert type(nested.body) is SetOperationBody


APPROVED_FORMS = {
    "parameters_and_lets": (
        "query orders_since(cutoff: Int, label: Text | None,):\n"
        "    let recent:\n"
        "        from orders\n"
        "        where order_day >= cutoff\n"
        "        select:\n"
        "            id\n"
        "    from orders\n"
        "    where id in recent\n"
        "    select:\n"
        "        id\n"
        '        note = coalesce(label, "none")\n'
    ),
    "flat_lets": (
        "query vip_report:\n"
        "    let vip:\n"
        "        from customers\n"
        '        where tier == "gold"\n'
        "        select:\n"
        "            id\n"
        "    let big_vip_orders:\n"
        "        from orders\n"
        "        where customer_id in vip and total > 1000\n"
        "        select:\n"
        "            id\n"
        "    from big_vip_orders\n"
        "    select:\n"
        "        id\n"
    ),
    "derived_table_let": (
        "query frequent_customers:\n"
        "    let counts:\n"
        "        from orders\n"
        "        group by:\n"
        "            customer_id\n"
        "        select:\n"
        "            customer_id\n"
        "            n = count()\n"
        "    from counts\n"
        "    where n > 10\n"
        "    select:\n"
        "        customer_id\n"
    ),
    "values_and_union": (
        "query seed:\n"
        "    values(id: Int, label: Text | None,):\n"
        '        1, "new"\n'
        "        2, None\n"
        "\n"
        "query empty_seed:\n"
        "    values(id: Int, label: Text | None)\n"
        "\n"
        "query all_codes:\n"
        "    let local_seed:\n"
        "        values(id: Int):\n"
        "            3\n"
        "    let codes:\n"
        "        union all:\n"
        "            from local_seed\n"
        "            from seed\n"
        "    from codes\n"
        "    select:\n"
        "        id\n"
    ),
    "table_function": (
        "query days:\n    from generate_series(1, 31, 1) as n\n    select:\n        n\n"
    ),
    "capture_exists_lateral": (
        "query customers_with_recent_orders:\n"
        "    let recent:\n"
        "        capture customers\n"
        "        from orders\n"
        "        where orders.customer_id == customers.id\n"
        "        select:\n"
        "            id\n"
        "    from customers\n"
        "    where exists recent\n"
        "    select:\n"
        "        id\n"
        "\n"
        "query latest_order:\n"
        "    let latest:\n"
        "        capture customers\n"
        "        from orders\n"
        "        where orders.customer_id == customers.id\n"
        "        select:\n"
        "            id\n"
        "        order by:\n"
        "            id desc\n"
        "        limit 1\n"
        "    from customers\n"
        "    let l = latest\n"
        "    left join l on True\n"
        "    select:\n"
        "        last_order = l.id\n"
    ),
    "python_style_layout": (
        "query paid_regions:\n"
        "    from orders\n"
        "    let contact = lower(trim(email))\n"
        "    let doubled = amount * 2\n"
        "    where:\n"
        '        status == "paid"\n'
        "        (region == 'EU'\n"
        "            or region == 'NA')\n"
        "    group by region, contact\n"
        "    select:\n"
        "        region, contact\n"
        "        n = count(), total = sum(\n"
        "            doubled)\n"
        "    having n >= 10\n"
        "    order by n desc, region\n"
    ),
    "self_correlation_renamed_by_let": (
        "query largest_orders:\n"
        "    let customer_orders:\n"
        "        from orders\n"
        "        select:\n"
        "            customer_id\n"
        "            total\n"
        "    let customer_top:\n"
        "        capture orders\n"
        "        from customer_orders\n"
        "        where customer_orders.customer_id == orders.customer_id\n"
        "        select:\n"
        "            top = max(total)\n"
        "    from orders\n"
        "    where total == scalar customer_top.top\n"
        "    select:\n"
        "        id\n"
    ),
}


@pytest.mark.parametrize("source", APPROVED_FORMS.values(), ids=APPROVED_FORMS)
def test_approved_forms_build_copyable_nodes_with_nested_trimmed_spans(
    source: str,
) -> None:
    result = parse_source(source, path="approved.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    lines = source.split("\n")

    def offset(line: int, column: int) -> int:
        return sum(len(item) + 1 for item in lines[: line - 1]) + column - 1

    pending: list[tuple[object, Node | None]] = [(result.ast, None)]
    while pending:
        value, parent = pending.pop()
        if type(value) is tuple:
            pending.extend((item, parent) for item in value)
            continue
        assert "antlr" not in type(value).__module__
        if not is_dataclass(value) or isinstance(value, type):
            continue
        if isinstance(value, Node):
            assert type(replace(value)) is type(value) and replace(value) == value
            span = value.span
            assert span.path == "approved.pietto"
            text = source[
                offset(span.line, span.column) : offset(span.end_line, span.end_column)
            ]
            assert text and text == text.strip(), (type(value).__name__, text)
            if parent is not None:
                outer = parent.span
                assert (outer.line, outer.column) <= (span.line, span.column)
                assert (span.end_line, span.end_column) <= (
                    outer.end_line,
                    outer.end_column,
                )
            parent = value
        pending.extend((getattr(value, item.name), parent) for item in fields(value))


# Python-style layout: header-line suites, comma lists, condition blocks and
# implicit line joining build the long form's AST; only spans differ.
def _query(body: str) -> str:
    return "query q:\n    from orders\n" + body


LAYOUT_EQUIVALENT_FORMS = {
    "select_header_line": (
        _query("    select id, customer_id, total = sum(amount)\n"),
        _query(
            "    select:\n"
            "        id\n"
            "        customer_id\n"
            "        total = sum(amount)\n"
        ),
    ),
    "select_comma_block_lines": (
        _query(
            "    select distinct:\n"
            "        id, customer_id\n"
            "        label = lower(trim(name)), n = f(a, b)\n"
        ),
        _query(
            "    select distinct:\n"
            "        id\n"
            "        customer_id\n"
            "        label = lower(trim(name))\n"
            "        n = f(a, b)\n"
        ),
    ),
    "list_clauses_on_header_lines": (
        _query(
            "    let contact = lower(trim(email))\n"
            "    let doubled = amount * 2\n"
            "    group by region, c.name\n"
            "    select region\n"
            "    order by region desc, total\n"
            "    limit 20\n"
        ),
        _query(
            "\n"
            "    let contact = lower(trim(email))\n"
            "    let doubled = amount * 2\n"
            "    group by:\n"
            "        region\n"
            "        c.name\n"
            "    select:\n"
            "        region\n"
            "    order by:\n"
            "        region desc\n"
            "        total\n"
            "    limit 20\n"
        ),
    ),
    "where_condition_block": (
        _query(
            "    where:\n"
            '        status == "paid"\n'
            '        "2026-01-01" <= ordered_at <= "2026-12-31"\n'
            "\n"
            "        # each line is one operand\n"
            '        email like "%@%" and coupon_code is None\n'
            '        region in ("EU", "NA")\n'
            "    select id\n"
        ),
        _query(
            '    where (status == "paid") and ("2026-01-01" <= ordered_at <= "2026-12-31") and (email like "%@%" and coupon_code is None) and (region in ("EU", "NA"))\n'
            "    select id\n"
        ),
    ),
    "single_line_where_block": (
        _query("    where:\n        a or b\n    select id\n"),
        _query("    where a or b\n    select id\n"),
    ),
    "satisfying_header_line_and_block": (
        _query(
            "    group by region\n"
            "    select region, n = count()\n"
            "    having:\n"
            "        n >= 10\n"
            "        not (n > 99 or n < 0)\n"
        ),
        _query(
            "    group by region\n"
            "    select region, n = count()\n"
            "    having (n >= 10) and (not (n > 99 or n < 0))\n"
        ),
    ),
    "joined_lines_inside_parentheses": (
        _query(
            "    where (region == 'EU'\n"
            "  # any indentation, comments and blank lines\n"
            "\n"
            "                and amount > f(1,\n"
            "    2))\n"
            "    select id, x = coalesce(\n"
            "        name,\n"
            "        'none',\n"
            "    )\n"
        ),
        _query(
            "    where (region == 'EU' and amount > f(1, 2))\n"
            "    select id, x = coalesce(name, 'none',)\n"
        ),
    ),
}


@pytest.mark.parametrize(
    "case", sorted(LAYOUT_EQUIVALENT_FORMS), ids=sorted(LAYOUT_EQUIVALENT_FORMS)
)
def test_python_style_layouts_build_the_long_form_ast(case: str) -> None:
    short, long = LAYOUT_EQUIVALENT_FORMS[case]
    short_result = parse_source(short)
    long_result = parse_source(long)
    assert short_result.diagnostics == long_result.diagnostics == ()
    assert short_result.ast is not None and long_result.ast is not None
    assert layout_free(short_result.ast) == layout_free(long_result.ast)


def test_condition_block_lines_fold_left_with_spans_through_each_operand() -> None:
    result = parse_source(
        _query("    where:\n        a\n        b or c\n        d\n    select id\n")
    )
    assert result.diagnostics == () and result.ast is not None
    where = cast(QueryDef, result.ast.definitions[0]).where_clause
    assert where is not None
    outer = cast(BinaryExpr, where.expression)
    inner = cast(BinaryExpr, outer.left)
    assert (outer.operator, inner.operator) == ("and", "and")
    assert type(inner.right) is BinaryExpr
    assert cast(BinaryExpr, inner.right).operator == "or"
    spans = (where.span, outer.span, inner.span, inner.right.span, outer.right.span)
    assert [(s.line, s.column, s.end_line, s.end_column) for s in spans] == [
        (3, 5, 6, 10),
        (4, 9, 6, 10),
        (4, 9, 5, 15),
        (5, 9, 5, 15),
        (6, 9, 6, 10),
    ]


def test_header_line_items_keep_their_own_spans() -> None:
    result = parse_source(_query("    select id, total = sum(amount)\n"))
    assert result.diagnostics == () and result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[0])
    assert [
        (item.alias, item.span.line, item.span.column, item.span.end_column)
        for item in relation.select_items
    ] == [(None, 3, 12, 14), ("total", 3, 16, 35)]


LAYOUT_REJECTIONS = {
    "trailing_comma": (
        _query("    select id\n    order by a, b,\n"),
        "A trailing comma does not continue a list on the next line; remove the comma.",
        4,
        18,
    ),
    "header_line_then_block": (
        _query("    select id\n        name\n"),
        "This clause already has its content on the header line after ':'; "
        "an indented block cannot follow it.",
        4,
        9,
    ),
    "condition_header_line_then_block": (
        _query("    where a\n        b\n    select id\n"),
        "A `where` condition ends with its line; write one condition per line "
        "in a `where:` block, or continue a condition inside parentheses.",
        4,
        9,
    ),
    "where_line_then_block": (
        _query("    where a\n        and b\n    select id\n"),
        "A `where` condition ends with its line; write one condition per line "
        "in a `where:` block, or continue a condition inside parentheses.",
        4,
        9,
    ),
    "window_item_on_header_line": (
        _query(
            "    let w = window(\n        order by id)\n    select n = row_number() window w\n"
        ),
        "A window item must be on its own line in a `select:` block.",
        5,
        12,
    ),
    "window_item_after_other_items": (
        _query(
            "    select:\n"
            "        id, n = row_number() window(\n"
            "            order by id)\n"
        ),
        "Unexpected 'window'; expected ',' or end of line. A window call is a "
        "whole `select:` item on a line of its own.",
        4,
        30,
    ),
    "condition_line_starts_with_and": (
        _query("    where:\n        a\n        and b\n    select id\n"),
        "A condition line cannot start with `and` or `or`; the lines of a "
        "condition block are joined with `and`, and parentheses continue one "
        "condition across lines.",
        5,
        9,
    ),
    "condition_line_starts_with_or": (
        _query("    group by a\n    select a\n    having:\n        or a\n"),
        "A condition line cannot start with `and` or `or`; the lines of a "
        "condition block are joined with `and`, and parentheses continue one "
        "condition across lines.",
        6,
        9,
    ),
    "ordinal_group_by": (
        _query("    group by region, 1\n    select region\n"),
        "Ordinal GROUP BY expressions are not supported.",
        3,
        22,
    ),
}


@pytest.mark.parametrize(
    "case", sorted(LAYOUT_REJECTIONS), ids=sorted(LAYOUT_REJECTIONS)
)
def test_python_style_layout_mistakes_have_targeted_messages(case: str) -> None:
    source, message, line, column = LAYOUT_REJECTIONS[case]
    result = parse_source(source, path="layout.pietto")
    assert result.ast is None
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [("PIE-P1000", message, line, column)]


@pytest.mark.parametrize(
    ("body", "line", "column", "message"),
    (
        ("    where:\n    select id\n", 4, 5, "Expected an indented block after ':'."),
        ("    select a = b = c\n", 3, 18, "Unexpected '='."),
        ("    select:\n", 3, 12, "Expected an indented block after ':'."),
        ("    select id\n    order by a,, b\n", 4, 16, "Unexpected ','."),
        (
            "    select id\n    order by ,\n",
            4,
            14,
            "Unexpected ','. A clause lists its items on its header line, or in "
            "an indented block after ':'.",
        ),
    ),
)
def test_malformed_python_style_layouts_stay_syntax_errors(
    body: str, line: int, column: int, message: str
) -> None:
    result = parse_source(_query(body))
    assert result.ast is None
    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in result.diagnostics
    ] == [("PIE-P1000", line, column, message)]


def test_soft_keywords_name_outputs_lets_and_expression_fields() -> None:
    result = parse_source(
        _query(
            "    let type = lower(kind)\n"
            "    let limit = 3\n"
            "    where from == 'web' and source.mode != check\n"
            "    select type, where = limit, select = orders.table\n"
        )
    )
    assert result.diagnostics == () and result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[0])
    assert relation.let_clause is None
    assert [binding.name for binding in relation.naming_declarations] == [
        "type",
        "limit",
    ]
    assert [(item.alias, item.expression) for item in relation.select_items] == [
        (None, NameExpr(span=relation.select_items[0].span, name="type")),
        (
            "where",
            NameExpr(span=relation.select_items[1].expression.span, name="limit"),
        ),
        (
            "select",
            DottedNameExpr(
                span=relation.select_items[2].expression.span,
                parts=("orders", "table"),
            ),
        ),
    ]
