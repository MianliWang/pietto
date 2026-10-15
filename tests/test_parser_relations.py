from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from pathlib import Path
from typing import Any, get_args

import pytest

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
    GroupByClause,
    LetClause,
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
        "    group by account_id\n",
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
        "    let:\n"
        "        doubled = n * 2\n"
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
    assert type(body.let_clause) is LetClause
    assert [item.name for item in body.let_clause.bindings] == ["doubled"]


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
        "        values(id: Int not null,):\n"
        "            1\n"
        "    let empty:\n"
        "        values(id: Int not null)\n"
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
        "    values(id: Int not null, label: Text nullable):\n"
        '        1, "new"\n'
        "\n"
        "        2, null\n"
    )
    empty = _block(f"{kind} empty_seed:\n    values(id: Int not null)\n")

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
        "query orders_since(cutoff: Int not null, label: Text nullable,):\n"
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
        "    values(id: Int not null, label: Text nullable,):\n"
        '        1, "new"\n'
        "        2, null\n"
        "\n"
        "query empty_seed:\n"
        "    values(id: Int not null, label: Text nullable)\n"
        "\n"
        "query all_codes:\n"
        "    let local_seed:\n"
        "        values(id: Int not null):\n"
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
        "    left join latest as l:\n"
        "        from customers\n"
        "        on true\n"
        "    select:\n"
        "        last_order = l.id\n"
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
