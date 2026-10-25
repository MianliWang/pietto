from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from _pietto_parser_layout import layout_free
from pietto.ast_nodes import (
    BinaryExpr,
    RelationshipParameter,
    RelationshipTemplate,
    Script,
    ShapeDef,
    SourceDef,
    Span,
    TableDef,
)
from pietto.errors import Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


def test_relationship_parameters_preserve_names_order_and_spans() -> None:
    path = Path("metadata/relationships.pietto")
    source = (
        "relationship membership(member: User, group: Group):\n"
        "    member.group_id == group.id\n"
    )
    result = parse_source(source, path=path)

    assert result.diagnostics == ()
    assert isinstance(result.ast, Script)
    assert result.ast.definitions == result.ast.relationships == ()
    (relationship,) = result.ast.relationship_templates
    assert isinstance(relationship, RelationshipTemplate)
    assert relationship.name == "membership"
    assert relationship.span == Span(
        path=str(path), line=1, column=1, end_line=2, end_column=32
    )
    assert relationship.parameters == (
        RelationshipParameter(
            span=Span(path=str(path), line=1, column=25, end_line=1, end_column=37),
            name="member",
            shape_name="User",
        ),
        RelationshipParameter(
            span=Span(path=str(path), line=1, column=39, end_line=1, end_column=51),
            name="group",
            shape_name="Group",
        ),
    )


def test_multiple_relationship_declarations_preserve_source_order() -> None:
    result = parse_source(
        "relationship membership(member: User, group: Group):\n"
        "    member.group_id == group.id\n"
        "\n"
        "relationship ownership(owner: User, resource: Account):\n"
        "    owner.id == resource.owner_id\n"
    )

    assert result.diagnostics == () and result.ast is not None
    assert [item.name for item in result.ast.relationship_templates] == [
        "membership",
        "ownership",
    ]
    assert [
        parameter.name
        for relationship in result.ast.relationship_templates
        for parameter in relationship.parameters
    ] == ["member", "group", "owner", "resource"]


def test_relationship_and_endpoint_are_contextual_identifiers() -> None:
    result = parse_source(
        "type relationship = Int\n"
        "shape endpoint:\n"
        "    relationship: relationship\n"
        'source endpoint: endpoint = postgres.table("endpoint")\n'
        "relationship endpoint(relationship: endpoint, endpoint: endpoint):\n"
        "    relationship.relationship == endpoint.relationship\n"
    )

    assert result.diagnostics == () and result.ast is not None
    assert [definition.name for definition in result.ast.definitions] == [
        "relationship",
        "endpoint",
        "endpoint",
    ]
    relationship = result.ast.relationship_templates[0]
    assert relationship.name == "endpoint"
    assert [(item.name, item.shape_name) for item in relationship.parameters] == [
        ("relationship", "endpoint"),
        ("endpoint", "endpoint"),
    ]


def test_script_without_relationships_keeps_empty_collections() -> None:
    result = parse_source(
        "shape User:\n    id: Int\n"
        'source users: User = postgres.table("public.users")\n'
        "table selected:\n    from users\n    select:\n        id\n"
    )

    assert result.diagnostics == () and result.ast is not None
    assert result.ast.relationships == result.ast.relationship_templates == ()
    assert [type(item) for item in result.ast.definitions] == [
        ShapeDef,
        SourceDef,
        TableDef,
    ]


@pytest.mark.parametrize(
    "source",
    [
        "relationship missing(left: User, right: User):\n",
        "relationship missing_name(: User, right: User):\n    True\n",
        "relationship missing_shape(left:, right: User):\n    True\n",
        "relationship missing_colon(left: User, right: User)\n    True\n",
        "relationship braces(left: User, right: User) {\n    True\n}\n",
    ],
)
def test_malformed_relationship_templates_use_existing_parser_failure(
    source: str,
) -> None:
    result = parse_source(source, path="malformed.pietto")
    assert result.ast is None and result.diagnostics
    assert all(
        item.code in {"PIE-P1000", "PIE-P1005"}
        and item.severity is Severity.ERROR
        and item.location.path == "malformed.pietto"
        for item in result.diagnostics
    )


def test_relationship_template_and_parameters_are_immutable() -> None:
    result = parse_source(
        "relationship membership(member: User, group: Group):\n"
        "    member.group_id == group.id\n"
    )
    assert result.ast is not None
    relationship = result.ast.relationship_templates[0]
    with pytest.raises(FrozenInstanceError):
        relationship.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        relationship.parameters[0].name = "changed"  # type: ignore[misc]


def test_unused_valid_relationship_does_not_change_ir_or_sql() -> None:
    program = (
        "shape User:\n    id: Int\n"
        'source users: User = postgres.table("public.users")\n'
        "table selected:\n    from users\n    select:\n        id\n"
    )
    template = "relationship same(a: User, b: User):\n    a.id == b.id\n"
    baseline_parse = parse_source(program)
    template_parse = parse_source(program + template)
    assert baseline_parse.diagnostics == template_parse.diagnostics == ()
    assert baseline_parse.ast is not None and template_parse.ast is not None
    assert baseline_parse.ast.definitions == template_parse.ast.definitions
    assert template_parse.ast.relationship_templates
    baseline_semantic = analyze(baseline_parse.ast)
    template_semantic = analyze(template_parse.ast)
    assert baseline_semantic.diagnostics == template_semantic.diagnostics == ()
    assert baseline_semantic.model.type_symbols == template_semantic.model.type_symbols
    assert (
        baseline_semantic.model.relation_symbols
        == template_semantic.model.relation_symbols
    )
    baseline_ir = build_ir(baseline_parse.ast, baseline_semantic.model)
    template_ir = build_ir(template_parse.ast, template_semantic.model)
    assert baseline_ir == template_ir
    assert isinstance(baseline_ir.ir, ScriptIR) and isinstance(template_ir.ir, ScriptIR)
    assert emit_postgres_sql(baseline_ir.ir) == emit_postgres_sql(template_ir.ir)
    assert emit_mysql_sql(baseline_ir.ir) == emit_mysql_sql(template_ir.ir)


def test_relationship_body_preserves_grouping_and_repeated_parameters() -> None:
    first = parse_source(
        "relationship match(a: Row, a: Row, b: Row):\n"
        "    a.id == b.id and (a.region == b.region or not b.active)\n"
    )
    second = parse_source(
        "relationship match(\n    a: Row, a: Row, b: Row,\n):\n"
        "    a.id == b.id and (a.region == b.region or not b.active)\n"
    )
    assert first.diagnostics == second.diagnostics == ()
    assert first.ast is not None and second.ast is not None
    assert layout_free(first.ast) == layout_free(second.ast)
    (template,) = first.ast.relationship_templates
    assert [item.name for item in template.parameters] == ["a", "a", "b"]
    assert template.parameters[0].span != template.parameters[1].span
    assert isinstance(template.body, BinaryExpr) and template.body.operator == "and"


@pytest.mark.parametrize(
    "body",
    [
        "a.id == b.id",
        "a.id < b.id",
        "a.id == 1",
        "a.active or not b.active",
        "a.id == b.id and True",
    ],
)
def test_relationship_predicates_preserve_arbitrary_row_boolean_bodies(
    body: str,
) -> None:
    result = parse_source(f"relationship r(a: Row, b: Row):\n    {body}\n")
    assert result.diagnostics == () and result.ast is not None
    (template,) = result.ast.relationship_templates
    assert template.body.span.line == 2 and template.body.span.column == 5
    assert template.body.span.end_column == 5 + len(body)


def test_modern_relationship_template_keeps_shape_roles_and_boolean_body() -> None:
    from pietto.ast_nodes import BinaryExpr, RelationshipTemplate

    result = parse_source(
        "relationship ActiveOrderCustomer(order: Order, customer: Customer):\n"
        '    order.customer_id == customer.id and (customer.status == "active" or not customer.disabled)\n',
        path="relationships.pietto",
    )
    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.relationships == ()
    (template,) = result.ast.relationship_templates
    assert isinstance(template, RelationshipTemplate)
    assert [(item.name, item.shape_name) for item in template.parameters] == [
        ("order", "Order"),
        ("customer", "Customer"),
    ]
    assert isinstance(template.body, BinaryExpr) and template.body.operator == "and"
    assert template.parameters[1].span.path == "relationships.pietto"
    assert template.parameters[0].span.column == 34


def test_relationship_template_body_may_follow_its_header() -> None:
    from pietto.ast_nodes import ComparisonExpr

    one_line = parse_source(
        "relationship oc(o: Order, c: Customer): o.customer_id == c.id\n"
    )
    block = parse_source(
        "relationship oc(o: Order, c: Customer):\n    o.customer_id == c.id\n"
    )

    assert one_line.diagnostics == block.diagnostics == ()
    assert one_line.ast is not None and block.ast is not None
    (template,) = one_line.ast.relationship_templates
    (other,) = block.ast.relationship_templates
    assert [(item.name, item.shape_name) for item in template.parameters] == [
        (item.name, item.shape_name) for item in other.parameters
    ]
    assert isinstance(template.body, ComparisonExpr)
    assert isinstance(other.body, ComparisonExpr)
    span = template.body.span
    assert (span.line, span.column, span.end_column) == (1, 41, 62)
    assert (template.span.end_line, template.span.end_column) == (1, 62)


def test_modern_relationship_metadata_requires_explicit_migration() -> None:
    result = parse_source("relationship r: a.id == b.id\n")
    assert result.ast is None
    assert "source-bound metadata" in (result.diagnostics[0].suggestion or "")
