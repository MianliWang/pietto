"""Scalar ANY retains lexical input identity through single-file lowering."""

from pietto.ir import (
    AnyFieldIR,
    BinaryIR,
    ComparisonIR,
    ExistsIR,
    FieldRefIR,
    RelationIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze


def test_nested_any_retains_local_and_outer_field_identities() -> None:
    parsed = parse_source("""shape Row:
    id: Int
source orders: Row = postgres.table("orders")
source customers: Row = postgres.table("customers")
query result:
    from orders
    select found = any(any(candidate.id == buyer.id for candidate in customers) and buyer.id == orders.id for buyer in customers)
""")
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert semantic.script is not None and not semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    relation = next(
        item for item in lowered.ir.definitions if isinstance(item, RelationIR)
    )
    outer = relation.projections[0].expression
    assert isinstance(outer, ExistsIR)
    assert isinstance(outer.predicate, BinaryIR)
    inner = outer.predicate.left
    comparison = outer.predicate.right
    assert isinstance(inner, ExistsIR) and isinstance(inner.predicate, ComparisonIR)
    assert isinstance(comparison, ComparisonIR)
    assert outer.binding != inner.binding
    assert isinstance(inner.predicate.left, AnyFieldIR)
    assert inner.predicate.left.binding == inner.binding
    assert isinstance(inner.predicate.right, AnyFieldIR)
    assert inner.predicate.right.binding == outer.binding
    assert isinstance(comparison.left, AnyFieldIR)
    assert comparison.left.binding == outer.binding
    assert isinstance(comparison.right, FieldRefIR)
    assert comparison.right.field is not None and comparison.right.field.input is None
    assert comparison.right.qualifier == ("orders",)
    assert [capture.name for capture in outer.captures] == ["id"]
    assert [
        capture.binding for capture in inner.captures if isinstance(capture, AnyFieldIR)
    ] == [outer.binding]


def test_any_null_predicate_keeps_unknown_type_and_non_null_result() -> None:
    parsed = parse_source("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
query result:
    from rows
    select found = any(None for candidate in rows)
""")
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert semantic.script is not None and not semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    relation = next(
        item for item in lowered.ir.definitions if isinstance(item, RelationIR)
    )
    expression = relation.projections[0].expression
    assert isinstance(expression, ExistsIR)
    assert expression.value_type.nullability.value == "non_null"
    assert expression.predicate.value_type.canonical_name != "Bool"
