from __future__ import annotations

import json
from pathlib import Path

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any, cast

import pytest

import pietto.cli as cli

from pietto.ast_nodes import (
    AuthoredJoinKind,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    QueryDef,
    Script,
    SourceDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    build_ir,
    ComparisonIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    FilterIR,
    JoinEqualityIR,
    JoinHopIR,
    JoinIR,
    JoinKindIR,
    LiteralIR,
    NullabilityIR,
    ProjectionIR,
    RelationInputIR,
    RelationInputRoleIR,
    RelationIR,
    RelationKindIR,
    RelationSourceIR,
    ResultPredicateIR,
    RowSchemaIR,
    ScriptIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
)
from pietto.ir.builder import _lower_group_keys
from pietto.ir.diagnostics import (
    join_explain_diagnostics,
    missing_semantic_fact_diagnostic,
)
from pietto.ir.joins import (
    JoinLoweringError,
    JoinReads,
    join_relation_facts,
    lower_join_inputs,
    lower_joins,
    report_join_invariants,
)
from pietto.ir.lowering import lower_span
from pietto.ir.model import OrderDirectionIR, OrderItemIR
from pietto.parser_api import parse_source
from pietto.sql.postgres import emit_postgres_sql
from pietto.semantic import (
    analyze,
    CheckMode,
    EffectiveNullability,
    ResolvedType,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
)
from pietto.semantic.aggregates import child_expressions
from pietto.semantic.model import (
    JoinEqualityInfo,
    JoinFieldRef,
    JoinInfo,
    JoinInputInfo,
    RelationJoinsInfo,
)

INPUTS_MISMATCH = (
    "relation inputs must be one more than its joins; join-free fields name no input"
)
INPUT_ORDER = (
    "relation inputs must be its source as FROM then JOIN targets "
    "in ordinal order, uniquely bound"
)
JOIN_ORDER = "relation joins must be in ordinal order and read an earlier visible input"
JOIN_MATCH = (
    "CROSS joins must have no hops, condition or null extension; "
    "others need a hop or condition"
)
JOIN_HOP = (
    "relation joins must have at most one hop, from source input "
    "to target input by equalities that all run that way"
)
NULL_EXTENSION = "relation join null extensions must match the join kind"
VISIBILITY = "relation inputs must be visible except SEMI and ANTI join targets"
FIELD_INPUT = (
    "relation field references must name a visible input, be owned "
    "by its relation and qualify with its binding"
)


def _type(name: str) -> TypeRefIR:
    return TypeRefIR(
        symbol=None,
        canonical_symbol=None,
        declared_name=name,
        canonical_name=name,
        kind=TypeKindIR.BUILTIN,
        canonical_kind=TypeKindIR.BUILTIN,
        nullability=NullabilityIR.NON_NULL,
    )


INT = _type("Int")
BOOL = _type("Bool")
ORDERS = SymbolId(SymbolNamespace.RELATION, "orders")
# Input ordinal -> (binding, relation, kind of the JOIN that introduces it).
INPUTS = (
    ("orders", "orders", None),
    ("customer", "customers", JoinKindIR.INNER),
    ("returned", "returns", JoinKindIR.SEMI),
    ("region", "regions", JoinKindIR.RIGHT),
    ("rep", "reps", JoinKindIR.LEFT),
    ("tag", "tags", JoinKindIR.FULL),
    ("slot", "slots", JoinKindIR.CROSS),
    ("refund", "refunds", JoinKindIR.ANTI),
)


def _span(line: int) -> SourceSpan:
    return SourceSpan(
        path="join-lowering.pietto", line=line, column=5, end_line=line, end_column=9
    )


def _read(input: int, name: str, line: int = 90) -> FieldRefIR:
    binding, relation, _ = INPUTS[input]
    return FieldRefIR(
        span=_span(line),
        value_type=INT,
        name=name,
        qualifier=(binding,),
        field=FieldId(
            owner=SymbolId(SymbolNamespace.RELATION, relation), name=name, input=input
        ),
    )


def _compare(left: FieldRefIR, right: FieldRefIR, operator: str = "==") -> ComparisonIR:
    return ComparisonIR(
        span=left.span, value_type=BOOL, left=left, operator=operator, right=right
    )


def _hop(name: str, left: FieldRefIR, right: FieldRefIR) -> JoinHopIR:
    assert left.field is not None and left.field.input is not None
    assert right.field is not None and right.field.input is not None
    return JoinHopIR(
        relationship=name,
        left_input=left.field.input,
        right_input=right.field.input,
        equalities=(JoinEqualityIR(left=left, right=right),),
        span=left.span,
    )


def _join(
    ordinal: int,
    source: int,
    *,
    hop: JoinHopIR | None = None,
    condition: ComparisonIR | None = None,
    null_extends: tuple[int, ...] = (),
) -> JoinIR:
    kind = INPUTS[ordinal][2]
    assert kind is not None
    return JoinIR(
        ordinal=ordinal,
        kind=kind,
        source_input=source,
        source_inferred=False,
        target_input=ordinal,
        hops=() if hop is None else (hop,),
        condition=condition,
        null_extends=null_extends,
        span=_span(10 * ordinal),
    )


CUSTOMER_HOP = _hop("order_customer", _read(0, "customer_id", 11), _read(1, "id", 11))
REP_HOP = _hop("customer_rep", _read(1, "rep_id", 41), _read(4, "id", 41))
# The FROM input, then INNER, SEMI, RIGHT, LEFT (one hop plus `on`), FULL,
# CROSS and ANTI JOINs; SEMI and ANTI targets are neither visible nor rows.
JOINS = (
    _join(1, 0, hop=CUSTOMER_HOP),
    _join(2, 0, condition=_compare(_read(2, "order_id", 21), _read(0, "id", 21))),
    _join(
        3,
        1,
        condition=_compare(_read(3, "id", 31), _read(1, "region_id", 31)),
        null_extends=(0, 1),
    ),
    _join(
        4,
        1,
        hop=REP_HOP,
        condition=_compare(_read(4, "level", 42), _read(3, "level", 42), ">"),
        null_extends=(4,),
    ),
    _join(
        5,
        0,
        condition=_compare(_read(5, "order_id", 51), _read(0, "id", 51)),
        null_extends=(0, 1, 3, 4, 5),
    ),
    _join(6, 0),
    _join(7, 0, condition=_compare(_read(7, "order_id", 71), _read(0, "id", 71))),
)


def _input(ordinal: int) -> RelationInputIR:
    binding, relation, kind = INPUTS[ordinal]
    return RelationInputIR(
        ordinal=ordinal,
        role=RelationInputRoleIR.FROM if kind is None else RelationInputRoleIR.TARGET,
        target=SymbolId(SymbolNamespace.RELATION, relation),
        binding=binding,
        visible=kind not in (JoinKindIR.SEMI, JoinKindIR.ANTI),
        span=_span(10 * ordinal or 2),
    )


def _projection(reference: FieldRefIR) -> ProjectionIR:
    return ProjectionIR(
        name="_".join((*reference.qualifier, reference.name)),
        expression=reference,
        type_ref=INT,
        span=reference.span,
    )


def _relation() -> RelationIR:
    return RelationIR(
        symbol=SymbolId(SymbolNamespace.RELATION, "order_facts"),
        name="order_facts",
        kind=RelationKindIR.QUERY,
        source=RelationSourceIR(target=ORDERS, name="orders", span=_span(2)),
        filter=FilterIR(
            expression=_compare(_read(4, "level", 80), _read(0, "id", 80), ">"),
            span=_span(80),
        ),
        projections=tuple(
            _projection(_read(ordinal, "id", 90 + ordinal))
            for ordinal in (0, 1, 3, 4, 5, 6)
        ),
        row_schema=RowSchemaIR(fields=()),
        span=_span(1),
        order_by=(
            OrderItemIR(
                expression=_read(3, "id", 99),
                direction=OrderDirectionIR.ASC,
                span=_span(99),
            ),
        ),
        inputs=tuple(_input(ordinal) for ordinal in range(len(INPUTS))),
        joins=JOINS,
    )


def _join_free() -> RelationIR:
    return RelationIR(
        symbol=SymbolId(SymbolNamespace.RELATION, "order_ids"),
        name="order_ids",
        kind=RelationKindIR.QUERY,
        source=RelationSourceIR(target=ORDERS, name="orders", span=_span(2)),
        filter=None,
        projections=(
            ProjectionIR(
                name="id",
                expression=FieldRefIR(
                    span=_span(3),
                    value_type=INT,
                    name="id",
                    qualifier=(),
                    field=FieldId(owner=ORDERS, name="id"),
                ),
                type_ref=INT,
                span=_span(3),
            ),
        ),
        row_schema=RowSchemaIR(fields=()),
        span=_span(1),
    )


def _with_join(index: int, **changes: Any) -> RelationIR:
    joins = list(JOINS)
    joins[index] = replace(joins[index], **changes)
    return replace(_relation(), joins=tuple(joins))


def _with_input(index: int, **changes: Any) -> RelationIR:
    relation = _relation()
    inputs = list(relation.inputs)
    inputs[index] = replace(inputs[index], **changes)
    return replace(relation, inputs=tuple(inputs))


def _with_projection(reference: FieldRefIR) -> RelationIR:
    relation = _relation()
    return replace(
        relation, projections=(*relation.projections, _projection(reference))
    )


def _with_customer_equality(left: FieldRefIR, right: FieldRefIR) -> RelationIR:
    equalities = (*CUSTOMER_HOP.equalities, JoinEqualityIR(left=left, right=right))
    return _with_join(0, hops=(replace(CUSTOMER_HOP, equalities=equalities),))


def test_a_join_relation_keeps_its_inputs_and_joins() -> None:
    relation = _relation()

    assert relation.source == RelationSourceIR(
        target=ORDERS, name="orders", span=_span(2)
    )
    assert [
        (item.ordinal, item.role, item.binding, item.visible)
        for item in relation.inputs
    ] == [
        (0, RelationInputRoleIR.FROM, "orders", True),
        (1, RelationInputRoleIR.TARGET, "customer", True),
        (2, RelationInputRoleIR.TARGET, "returned", False),
        (3, RelationInputRoleIR.TARGET, "region", True),
        (4, RelationInputRoleIR.TARGET, "rep", True),
        (5, RelationInputRoleIR.TARGET, "tag", True),
        (6, RelationInputRoleIR.TARGET, "slot", True),
        (7, RelationInputRoleIR.TARGET, "refund", False),
    ]
    assert [
        (join.kind, join.source_input, join.target_input, join.null_extends)
        for join in relation.joins
    ] == [
        (JoinKindIR.INNER, 0, 1, ()),
        (JoinKindIR.SEMI, 0, 2, ()),
        (JoinKindIR.RIGHT, 1, 3, (0, 1)),
        (JoinKindIR.LEFT, 1, 4, (4,)),
        (JoinKindIR.FULL, 0, 5, (0, 1, 3, 4, 5)),
        (JoinKindIR.CROSS, 0, 6, ()),
        (JoinKindIR.ANTI, 0, 7, ()),
    ]
    assert relation.joins[0].hops == (CUSTOMER_HOP,)
    assert relation.joins[3].hops == (REP_HOP,)


def test_a_hop_may_match_on_several_equalities_from_source_to_target() -> None:
    relation = _with_customer_equality(_read(0, "region_id"), _read(1, "region_id"))

    assert relation.joins[0].hops[0].equalities == (
        JoinEqualityIR(left=_read(0, "customer_id", 11), right=_read(1, "id", 11)),
        JoinEqualityIR(left=_read(0, "region_id"), right=_read(1, "region_id")),
    )


def test_join_free_relations_have_no_inputs_joins_or_input_ordinals() -> None:
    relation = _join_free()

    assert relation.inputs == relation.joins == ()
    assert FieldId(owner=ORDERS, name="id") == FieldId(
        owner=ORDERS, name="id", input=None
    )
    assert FieldId(owner=ORDERS, name="id") != FieldId(owner=ORDERS, name="id", input=0)


def _join_free_reading_input_zero() -> RelationIR:
    relation = _join_free()
    reference = replace(
        relation.projections[0].expression,
        field=FieldId(owner=ORDERS, name="id", input=0),
    )
    return replace(
        relation, projections=(replace(relation.projections[0], expression=reference),)
    )


VIOLATIONS: tuple[tuple[str, Callable[[], RelationIR], str], ...] = (
    # 1. Inputs and joins come together; join-free fields name no input.
    ("inputs-without-joins", lambda: replace(_relation(), joins=()), INPUTS_MISMATCH),
    ("joins-without-inputs", lambda: replace(_relation(), inputs=()), INPUTS_MISMATCH),
    (
        "one-input-short",
        lambda: replace(_relation(), inputs=_relation().inputs[:-1]),
        INPUTS_MISMATCH,
    ),
    ("join-free-field-names-an-input", _join_free_reading_input_zero, INPUTS_MISMATCH),
    # 2. The relation's source as FROM, then one target per JOIN, with unique
    #    bindings.
    ("input-ordinal-out-of-order", lambda: _with_input(3, ordinal=4), INPUT_ORDER),
    (
        "first-input-is-a-target",
        lambda: _with_input(0, role=RelationInputRoleIR.TARGET),
        INPUT_ORDER,
    ),
    (
        "first-input-is-not-the-from-relation",
        lambda: _with_input(0, target=SymbolId(SymbolNamespace.RELATION, "customers")),
        INPUT_ORDER,
    ),
    (
        "first-input-binding-is-not-the-from-name",
        lambda: _with_input(0, binding="o"),
        INPUT_ORDER,
    ),
    (
        "first-input-span-is-not-the-from-span",
        lambda: _with_input(0, span=_span(3)),
        INPUT_ORDER,
    ),
    (
        "later-input-is-a-from",
        lambda: _with_input(2, role=RelationInputRoleIR.FROM),
        INPUT_ORDER,
    ),
    ("duplicate-binding", lambda: _with_input(4, binding="customer"), INPUT_ORDER),
    # 3. Each JOIN reads an earlier input that is visible before it.
    ("join-ordinal-out-of-order", lambda: _with_join(1, ordinal=3), JOIN_ORDER),
    (
        "join-target-is-not-its-ordinal",
        lambda: _with_join(1, target_input=3),
        JOIN_ORDER,
    ),
    ("join-reads-its-own-target", lambda: _with_join(0, source_input=1), JOIN_ORDER),
    ("join-reads-a-negative-input", lambda: _with_join(0, source_input=-1), JOIN_ORDER),
    (
        "join-reads-a-hidden-semi-target",
        lambda: _with_join(2, source_input=2),
        JOIN_ORDER,
    ),
    # 4. CROSS has nothing to match on; every other JOIN has something.
    (
        "cross-with-condition",
        lambda: _with_join(5, condition=_compare(_read(6, "id"), _read(0, "id"))),
        JOIN_MATCH,
    ),
    (
        "cross-with-hop",
        lambda: _with_join(
            5, hops=(_hop("order_slot", _read(0, "slot_id"), _read(6, "id")),)
        ),
        JOIN_MATCH,
    ),
    ("cross-extends-nulls", lambda: _with_join(5, null_extends=(6,)), JOIN_MATCH),
    ("inner-without-hop-or-condition", lambda: _with_join(0, hops=()), JOIN_MATCH),
    # 5. At most one hop, from the source to the target, by equalities that all
    #    run that way.
    (
        "two-hops",
        lambda: _with_join(0, hops=(CUSTOMER_HOP, CUSTOMER_HOP)),
        JOIN_HOP,
    ),
    (
        "hop-starts-elsewhere",
        lambda: _with_join(3, hops=(replace(REP_HOP, left_input=0),)),
        JOIN_HOP,
    ),
    (
        "hop-ends-elsewhere",
        lambda: _with_join(0, hops=(replace(CUSTOMER_HOP, right_input=2),)),
        JOIN_HOP,
    ),
    (
        "hop-without-equalities",
        lambda: _with_join(0, hops=(replace(CUSTOMER_HOP, equalities=()),)),
        JOIN_HOP,
    ),
    (
        "hop-equality-runs-backwards",
        lambda: _with_join(
            0,
            hops=(
                replace(
                    CUSTOMER_HOP,
                    equalities=(
                        JoinEqualityIR(
                            left=_read(1, "id"), right=_read(0, "customer_id")
                        ),
                    ),
                ),
            ),
        ),
        JOIN_HOP,
    ),
    (
        "hop-second-equality-runs-backwards",
        lambda: _with_customer_equality(_read(1, "region_id"), _read(0, "region_id")),
        JOIN_HOP,
    ),
    (
        "hop-second-equality-stays-on-the-source-side",
        lambda: _with_customer_equality(_read(0, "id"), _read(0, "customer_id")),
        JOIN_HOP,
    ),
    # 6. Null extension per kind; SEMI and ANTI targets are not row inputs.
    ("left-extends-nothing", lambda: _with_join(3, null_extends=()), NULL_EXTENSION),
    (
        "right-extends-the-semi-target",
        lambda: _with_join(2, null_extends=(0, 1, 2)),
        NULL_EXTENSION,
    ),
    (
        "full-keeps-its-target",
        lambda: _with_join(4, null_extends=(0, 1, 3, 4)),
        NULL_EXTENSION,
    ),
    (
        "inner-extends-its-target",
        lambda: _with_join(0, null_extends=(1,)),
        NULL_EXTENSION,
    ),
    (
        "anti-extends-its-target",
        lambda: _with_join(6, null_extends=(7,)),
        NULL_EXTENSION,
    ),
    # 7. SEMI and ANTI targets are hidden; every other input is visible.
    ("from-input-hidden", lambda: _with_input(0, visible=False), VISIBILITY),
    ("semi-target-visible", lambda: _with_input(2, visible=True), VISIBILITY),
    ("inner-target-hidden", lambda: _with_input(1, visible=False), VISIBILITY),
    # 8. Every field reference names a readable input, that input's relation as
    #    owner and its binding as qualifier.
    (
        "projection-reads-a-hidden-target",
        lambda: _with_projection(_read(2, "order_id")),
        FIELD_INPUT,
    ),
    (
        "projection-has-no-field",
        lambda: _with_projection(replace(_read(0, "id"), field=None)),
        FIELD_INPUT,
    ),
    (
        "projection-field-names-no-input",
        lambda: _with_projection(
            replace(_read(0, "id"), field=FieldId(owner=ORDERS, name="id"))
        ),
        FIELD_INPUT,
    ),
    (
        "projection-names-a-missing-input",
        lambda: _with_projection(
            replace(_read(0, "id"), field=FieldId(owner=ORDERS, name="id", input=8))
        ),
        FIELD_INPUT,
    ),
    (
        "projection-is-unqualified",
        lambda: _with_projection(replace(_read(0, "id"), qualifier=())),
        FIELD_INPUT,
    ),
    (
        "projection-qualifier-names-another-binding",
        lambda: _with_projection(replace(_read(0, "id"), qualifier=("customer",))),
        FIELD_INPUT,
    ),
    (
        "filter-reads-a-hidden-target",
        lambda: replace(
            _relation(),
            filter=FilterIR(
                expression=_compare(_read(7, "id"), _read(0, "id")), span=_span(80)
            ),
        ),
        FIELD_INPUT,
    ),
    (
        "group-key-reads-a-hidden-target",
        lambda: replace(_relation(), group_keys=(_read(2, "id"),)),
        FIELD_INPUT,
    ),
    (
        "order-reads-a-hidden-target",
        lambda: replace(
            _relation(),
            order_by=(
                OrderItemIR(
                    expression=_read(7, "id"),
                    direction=OrderDirectionIR.DESC,
                    span=_span(99),
                ),
            ),
        ),
        FIELD_INPUT,
    ),
    (
        "result-predicate-reads-a-hidden-target",
        lambda: replace(
            _relation(),
            result_predicate=ResultPredicateIR(
                expression=_compare(_read(2, "id"), _read(0, "id")), span=_span(98)
            ),
        ),
        FIELD_INPUT,
    ),
    (
        "condition-reads-a-later-input",
        lambda: _with_join(
            2, condition=_compare(_read(3, "id"), _read(4, "region_id"))
        ),
        FIELD_INPUT,
    ),
    (
        "condition-reads-an-earlier-hidden-target",
        lambda: _with_join(
            2, condition=_compare(_read(3, "id"), _read(2, "region_id"))
        ),
        FIELD_INPUT,
    ),
    (
        "hop-equality-qualifier-names-another-binding",
        lambda: _with_customer_equality(
            replace(_read(0, "region_id"), qualifier=("customer",)),
            _read(1, "region_id"),
        ),
        FIELD_INPUT,
    ),
    (
        "projection-field-owner-is-another-relation",
        lambda: _with_projection(
            replace(_read(1, "id"), field=FieldId(owner=ORDERS, name="id", input=1))
        ),
        FIELD_INPUT,
    ),
    (
        "hop-equality-field-owner-is-another-relation",
        lambda: _with_customer_equality(
            _read(0, "region_id"),
            replace(
                _read(1, "region_id"),
                field=FieldId(owner=ORDERS, name="region_id", input=1),
            ),
        ),
        FIELD_INPUT,
    ),
)


@pytest.mark.parametrize(
    ("build", "message"),
    [pytest.param(build, message, id=case) for case, build, message in VIOLATIONS],
)
def test_each_join_invariant_rejects_a_constructed_violation(
    build: Callable[[], RelationIR], message: str
) -> None:
    with pytest.raises(ValueError) as caught:
        build()

    assert str(caught.value) == message


def test_the_first_violated_join_invariant_is_reported() -> None:
    joins = list(JOINS)
    joins[3] = replace(joins[3], null_extends=())
    inputs = list(_relation().inputs)
    inputs[2] = replace(inputs[2], visible=True)

    with pytest.raises(ValueError) as later:
        replace(_relation(), inputs=tuple(inputs), joins=tuple(joins))
    with pytest.raises(ValueError) as earlier:
        replace(
            _relation(),
            inputs=(replace(inputs[0], binding="o"), *inputs[1:]),
            joins=tuple(joins),
        )

    assert str(later.value) == NULL_EXTENSION
    assert str(earlier.value) == INPUT_ORDER


# Lowering single-file JOIN facts (pietto.ir.joins), from hand-built facts over
# parsed relations; the semantic analysis that will produce them is used only
# to name each JOIN target by its relation (`let` inputs) and to turn each
# `where [not] any(...)` between JOINs into its hidden SEMI (ANTI) JOIN.
PATH = "join-lowering.pietto"
SOURCE = """shape Order:
    id: Int
    customer_id: Int | None
    amount: Int
shape Customer:
    id: Int
    name: Text
    region_id: Int | None
shape Region:
    id: Int
    label: Text
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
source regions: Region = postgres.table("shop.regions")
query customer_orders:
    from customers
    let placed = orders
    where any(placed.customer_id == customers.id for placed in placed)
    let last_order = orders
    left join last_order on last_order.amount > 100
    let region = regions
    inner join region on customers.region_id == region.id
    let slot = regions
    cross join slot
    where customers.name != ""
    select:
        name
        last_amount = last_order.amount
        region_label = region.label
        slot_label = slot.label
    order by customers.id desc
query customer_peers:
    from customers
    let peer = customers
    full join peer on peer.region_id == customers.region_id
    let refund = orders
    where not any(refund.customer_id == peer.id for refund in refund)
    let region = regions
    right join region on customers.region_id == region.id
    select:
        customer_id = customers.id
        peer_id = peer.id
        region_label = region.label
query customer_names:
    from customers
    select:
        name
query windowed:
    from customers
    let region = regions
    inner join region on customers.region_id == region.id
    let w = window(order by customers.id)
    select:
        name
        n = row_number() window w
query named_window:
    from customers
    let region = regions
    inner join region on customers.region_id == region.id
    let w = window(order by customers.id)
    select:
        name
query grouped:
    from customers
    let region = regions
    inner join region on customers.region_id == region.id
    group by region.label, customers.name
    select:
        label = region.label
        n = count()
query aggregated:
    from customers
    let region = regions
    inner join region on customers.region_id == region.id
    select:
        label = region.label
        total = 1 + sum(customers.id)
        n = count()
query grouped_window:
    from customers
    let region = regions
    inner join region on customers.region_id == region.id
    let w = window(order by region.label)
    group by region.label
    select:
        label = region.label
        n = row_number() window w
"""


def _parse_script(source: str) -> Script:
    result = parse_source(source, path=PATH)
    assert result.ast is not None and result.diagnostics == (), result.diagnostics
    return result.ast


def _named_script(source: str) -> Script:
    """The parsed relations with each `let` JOIN input named by its relation."""

    script = analyze(_parse_script(source)).script
    assert script is not None
    return script


SCRIPT = _named_script(SOURCE)
INT_TYPE = ResolvedType("Int", TypeKind.BUILTIN)
NON_NULL = EffectiveNullability.NON_NULL
NULLABLE = EffectiveNullability.NULLABLE
CUSTOMERS = SymbolId(SymbolNamespace.RELATION, "customers")
REGIONS = SymbolId(SymbolNamespace.RELATION, "regions")
FACT_FAILURE = "Missing semantic fact required for IR lowering: "
EXPLAIN_REFUSAL = (
    "Single-file explain does not describe JOIN relations yet: Semantic Metadata "
    "Artifact v1 has one input per relation; use emit-sql to see their SQL"
)


def _query(name: str) -> QueryDef:
    return next(
        item
        for item in SCRIPT.definitions
        if isinstance(item, QueryDef) and item.name == name
    )


def _source(name: str) -> SourceDef:
    return next(
        item
        for item in SCRIPT.definitions
        if isinstance(item, SourceDef) and item.name == name
    )


def _at(line: int, column: int, end_line: int, end_column: int) -> SourceSpan:
    return SourceSpan(PATH, line, column, end_line, end_column)


def _join_info(
    definition: QueryDef,
    ordinal: int,
    source: int,
    *,
    mode: str,
    null_extends: tuple[int, ...] = (),
) -> JoinInfo:
    """A JOIN that states its match in `on` (M3), or a CROSS JOIN (M5)."""

    clause = definition.join_clauses[ordinal - 1]
    return JoinInfo(
        ordinal=ordinal,
        clause=clause,
        kind=clause.kind,
        mode=mode,
        source_input=source,
        source_inferred=False,
        target_input=ordinal,
        relationship=None,
        step=None,
        equalities=(),
        condition=None if clause.on_clause is None else clause.on_clause.expression,
        null_extends=null_extends,
    )


def _join_inputs(definition: QueryDef) -> tuple[JoinInputInfo, ...]:
    """The FROM input, then the target of each JOIN clause."""

    name = definition.from_clause.source_name
    return (
        JoinInputInfo(
            ordinal=0, binding=name, relation=_source(name), clause=None, visible=True
        ),
        *(
            JoinInputInfo(
                ordinal=ordinal,
                binding=clause.target_binding_name,
                relation=_source(clause.target_relation_name),
                clause=clause,
                visible=clause.kind
                not in (AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI),
            )
            for ordinal, clause in enumerate(definition.join_clauses, start=1)
        ),
    )


def _field_reads(
    definition: QueryDef, bare: Mapping[str, JoinFieldRef] | None = None
) -> dict[Expression, JoinFieldRef]:
    """Every field read of the relation: `b.f` by binding, `f` from ``bare``."""

    bindings = {item.binding: item.ordinal for item in _join_inputs(definition)}
    pending: list[Expression] = [item.expression for item in definition.select_items]
    if definition.where_clause is not None:
        pending.append(definition.where_clause.expression)
    if definition.order_by_clause is not None:
        pending.extend(item.expression for item in definition.order_by_clause.items)
    pending.extend(
        clause.on_clause.expression
        for clause in definition.join_clauses
        if clause.on_clause is not None
    )
    reads: dict[Expression, JoinFieldRef] = {}
    while pending:
        expression = pending.pop()
        if isinstance(expression, DottedNameExpr):
            binding, field = expression.parts
            reads[expression] = JoinFieldRef(bindings[binding], field)
        elif isinstance(expression, NameExpr):
            reads[expression] = (bare or {})[expression.name]
        else:
            pending.extend(child_expressions(expression))
    return reads


def _customer_orders_facts() -> RelationJoinsInfo:
    """Each JOIN states its match in `on`, except the CROSS JOIN; the first is
    the hidden SEMI JOIN of `where any(...)`."""

    query = _query("customer_orders")
    return RelationJoinsInfo(
        inputs=_join_inputs(query),
        joins=(
            _join_info(query, 1, 0, mode="M3"),
            _join_info(query, 2, 0, mode="M3", null_extends=(2,)),
            _join_info(query, 3, 0, mode="M3"),
            _join_info(query, 4, 0, mode="M5"),
        ),
        row_schema=RowSchema(joined=True),
        field_reads=_field_reads(query, {"name": JoinFieldRef(0, "name")}),
    )


def _customer_peers_facts() -> RelationJoinsInfo:
    query = _query("customer_peers")
    return RelationJoinsInfo(
        inputs=_join_inputs(query),
        joins=(
            _join_info(query, 1, 0, mode="M3", null_extends=(0, 1)),
            _join_info(query, 2, 0, mode="M3"),
            _join_info(query, 3, 0, mode="M3", null_extends=(0, 1)),
        ),
        row_schema=RowSchema(joined=True),
        field_reads=_field_reads(query),
    )


def _region_join_facts(definition: QueryDef) -> RelationJoinsInfo:
    """Facts of `from customers` plus `inner join region on ...`."""

    return RelationJoinsInfo(
        inputs=_join_inputs(definition),
        joins=(_join_info(definition, 1, 0, mode="M3"),),
        row_schema=RowSchema(joined=True),
        field_reads={},
    )


def _model(*facts: tuple[QueryDef, RelationJoinsInfo]) -> SemanticModel:
    return SemanticModel(mode=CheckMode.CHECKED, relation_joins=dict(facts))


def _operand(reads: JoinReads, expression: Expression) -> ExpressionIR:
    if isinstance(expression, LiteralExpr):
        return LiteralIR(
            span=lower_span(expression.span), value_type=INT, value=expression.value
        )
    assert isinstance(expression, NameExpr | DottedNameExpr)
    return reads.field_ref(expression, span=lower_span(expression.span), value_type=INT)


def _lowered(
    definition: QueryDef, info: RelationJoinsInfo
) -> tuple[JoinReads, tuple[JoinIR, ...], list[Expression]]:
    """The inputs, reads and JOINs of the relation, with each `on` handed to
    the condition lowering (a comparison of reads and literals here)."""

    reads = JoinReads(lower_join_inputs(definition, info), info.field_reads)
    conditions: list[Expression] = []

    def lower_condition(expression: Expression) -> ExpressionIR:
        conditions.append(expression)
        assert isinstance(expression, ComparisonExpr)
        return _compare_ir(
            _operand(reads, expression.left),
            _operand(reads, expression.right),
            expression,
        )

    joins = lower_joins(info, lower_condition=lower_condition)
    return reads, joins, conditions


def _compare_ir(
    left: ExpressionIR, right: ExpressionIR, expression: ComparisonExpr
) -> ComparisonIR:
    return ComparisonIR(
        span=lower_span(expression.span),
        value_type=BOOL,
        left=left,
        operator=expression.operator,
        right=right,
    )


def _join_relation_ir(definition: QueryDef, info: RelationJoinsInfo) -> RelationIR:
    """The relation as the builder assembles it from the lowered JOIN facts."""

    reads, joins, _ = _lowered(definition, info)
    source_name = definition.from_clause.source_name
    return RelationIR(
        symbol=SymbolId(SymbolNamespace.RELATION, definition.name),
        name=definition.name,
        kind=RelationKindIR.QUERY,
        source=RelationSourceIR(
            target=SymbolId(SymbolNamespace.RELATION, source_name),
            name=source_name,
            span=lower_span(definition.from_clause.span),
        ),
        filter=None,
        projections=tuple(
            ProjectionIR(
                name=item.alias,
                expression=_operand(reads, item.expression),
                type_ref=INT,
                span=lower_span(item.span),
            )
            for item in definition.select_items
        ),
        row_schema=RowSchemaIR(fields=()),
        span=lower_span(definition.span),
        inputs=reads.inputs,
        joins=joins,
    )


def _failure(error: JoinLoweringError) -> tuple[str, str, int, int]:
    """What the builder reports for the error: code, message, line, column."""

    diagnostic = missing_semantic_fact_diagnostic(error.node, error.message)
    return (
        diagnostic.code,
        diagnostic.message,
        diagnostic.location.line,
        diagnostic.location.column,
    )


def _field(
    span: SourceSpan, name: str, binding: str, owner: SymbolId, input: int
) -> FieldRefIR:
    return FieldRefIR(
        span=span,
        value_type=INT,
        name=name,
        qualifier=(binding,),
        field=FieldId(owner, name, input),
    )


def test_join_inputs_are_the_from_input_then_each_join_target() -> None:
    query = _query("customer_orders")
    orders = SymbolId(SymbolNamespace.RELATION, "orders")
    target = RelationInputRoleIR.TARGET

    inputs = lower_join_inputs(query, _customer_orders_facts())

    assert inputs == (
        RelationInputIR(
            0,
            RelationInputRoleIR.FROM,
            CUSTOMERS,
            "customers",
            True,
            _at(16, 5, 16, 19),
        ),
        # The hidden SEMI JOIN of `where any(...)`, bound to a generated name.
        RelationInputIR(1, target, orders, "_pietto_any_1", False, _at(18, 11, 18, 71)),
        RelationInputIR(2, target, orders, "last_order", True, _at(20, 5, 20, 52)),
        RelationInputIR(3, target, REGIONS, "region", True, _at(22, 5, 22, 58)),
        RelationInputIR(4, target, REGIONS, "slot", True, _at(24, 5, 24, 20)),
    )
    # The FROM input carries the span RelationIR.source has (invariant 2).
    assert inputs[0].span == lower_span(query.from_clause.span)


def test_join_facts_lower_to_joins_with_their_on_conditions() -> None:
    query = _query("customer_orders")
    orders = SymbolId(SymbolNamespace.RELATION, "orders")

    reads, joins, conditions = _lowered(query, _customer_orders_facts())

    # Each `on` is lowered once, in JOIN order (the hidden SEMI JOIN's `on` is
    # the `any` predicate); a JOIN that states its match in `on` has no
    # relationship hop, and the CROSS JOIN has neither.
    assert conditions == [
        clause.on_clause.expression
        for clause in query.join_clauses
        if clause.on_clause is not None
    ]
    assert joins == (
        JoinIR(
            ordinal=1,
            kind=JoinKindIR.SEMI,
            source_input=0,
            source_inferred=False,
            target_input=1,
            hops=(),
            condition=ComparisonIR(
                span=_at(18, 15, 18, 49),
                value_type=BOOL,
                left=_field(
                    _at(18, 15, 18, 33), "customer_id", "_pietto_any_1", orders, 1
                ),
                operator="==",
                right=_field(_at(18, 37, 18, 49), "id", "customers", CUSTOMERS, 0),
            ),
            null_extends=(),
            span=_at(18, 11, 18, 71),
        ),
        JoinIR(
            ordinal=2,
            kind=JoinKindIR.LEFT,
            source_input=0,
            source_inferred=False,
            target_input=2,
            hops=(),
            condition=ComparisonIR(
                span=_at(20, 29, 20, 52),
                value_type=BOOL,
                left=_field(_at(20, 29, 20, 46), "amount", "last_order", orders, 2),
                operator=">",
                right=LiteralIR(span=_at(20, 49, 20, 52), value_type=INT, value=100),
            ),
            null_extends=(2,),
            span=_at(20, 5, 20, 52),
        ),
        JoinIR(
            ordinal=3,
            kind=JoinKindIR.INNER,
            source_input=0,
            source_inferred=False,
            target_input=3,
            hops=(),
            condition=ComparisonIR(
                span=_at(22, 26, 22, 58),
                value_type=BOOL,
                left=_field(
                    _at(22, 26, 22, 45), "region_id", "customers", CUSTOMERS, 0
                ),
                operator="==",
                right=_field(_at(22, 49, 22, 58), "id", "region", REGIONS, 3),
            ),
            null_extends=(),
            span=_at(22, 5, 22, 58),
        ),
        JoinIR(
            ordinal=4,
            kind=JoinKindIR.CROSS,
            source_input=0,
            source_inferred=False,
            target_input=4,
            hops=(),
            condition=None,
            null_extends=(),
            span=_at(24, 5, 24, 20),
        ),
    )
    assert reads.inputs == lower_join_inputs(query, _customer_orders_facts())


def test_join_kinds_null_extensions_and_self_join_reads_lower_from_the_facts() -> None:
    query = _query("customer_peers")

    reads, joins, conditions = _lowered(query, _customer_peers_facts())

    assert [
        (
            join.kind,
            join.source_input,
            join.target_input,
            [(hop.relationship, hop.left_input, hop.right_input) for hop in join.hops],
            join.condition is not None,
            join.null_extends,
        )
        for join in joins
    ] == [
        (JoinKindIR.FULL, 0, 1, [], True, (0, 1)),
        (JoinKindIR.ANTI, 0, 2, [], True, ()),
        (JoinKindIR.RIGHT, 0, 3, [], True, (0, 1)),
    ]
    assert conditions == [
        clause.on_clause.expression
        for clause in query.join_clauses
        if clause.on_clause is not None
    ]
    # The two sides of the self-join stay two inputs of one relation.
    assert [
        (projection.expression.qualifier, projection.expression.field)
        for projection in _join_relation_ir(query, _customer_peers_facts()).projections
        if isinstance(projection.expression, FieldRefIR)
    ] == [
        (("customers",), FieldId(CUSTOMERS, "id", 0)),
        (("peer",), FieldId(CUSTOMERS, "id", 1)),
        (("region",), FieldId(REGIONS, "label", 3)),
    ]
    assert {JoinKindIR(kind.value) for kind in AuthoredJoinKind} == set(JoinKindIR)


def test_a_bare_or_dotted_read_lowers_to_its_input_field_qualified_by_binding() -> None:
    query = _query("customer_orders")
    reads = JoinReads(
        lower_join_inputs(query, _customer_orders_facts()),
        _customer_orders_facts().field_reads,
    )
    bare, dotted = query.select_items[0].expression, query.select_items[1].expression
    assert isinstance(bare, NameExpr) and isinstance(dotted, DottedNameExpr)

    assert reads.field_ref(bare, span=_at(1, 2, 3, 4), value_type=INT) == FieldRefIR(
        span=_at(1, 2, 3, 4),
        value_type=INT,
        name="name",
        qualifier=("customers",),
        field=FieldId(CUSTOMERS, "name", 0),
    )
    assert reads.field_ref(dotted, span=_at(28, 23, 28, 40), value_type=BOOL) == (
        FieldRefIR(
            span=_at(28, 23, 28, 40),
            value_type=BOOL,
            name="amount",
            qualifier=("last_order",),
            field=FieldId(SymbolId(SymbolNamespace.RELATION, "orders"), "amount", 2),
        )
    )


def test_a_read_without_a_resolution_fails_closed_at_the_read() -> None:
    query = _query("customer_orders")
    facts = _customer_orders_facts()
    dotted = query.select_items[1].expression
    reads = JoinReads(
        lower_join_inputs(query, facts),
        {
            read: reference
            for read, reference in facts.field_reads.items()
            if read != dotted
        },
    )
    other = _query("customer_names").select_items[0].expression
    assert isinstance(dotted, DottedNameExpr) and isinstance(other, NameExpr)

    failures = []
    for expression in (dotted, other):
        with pytest.raises(JoinLoweringError) as caught:
            reads.field_ref(
                expression, span=lower_span(expression.span), value_type=INT
            )
        assert caught.value.node is expression
        failures.append(_failure(caught.value))

    assert failures == [
        ("PIE-I1000", f"{FACT_FAILURE}resolved JOIN field read", 28, 23),
        ("PIE-I1000", f"{FACT_FAILURE}resolved JOIN field read", 47, 9),
    ]


def test_lowered_join_facts_build_relations_that_keep_every_invariant() -> None:
    for name, facts in (
        ("customer_orders", _customer_orders_facts),
        ("customer_peers", _customer_peers_facts),
    ):
        query = _query(name)

        relation = _join_relation_ir(query, facts())

        assert relation.inputs == lower_join_inputs(query, facts())
        assert len(relation.joins) == len(query.join_clauses)
        assert relation == _join_relation_ir(query, facts())


def test_join_relation_facts_are_none_without_joins_and_checked_with_them() -> None:
    query = _query("customer_orders")
    facts = _customer_orders_facts()

    assert join_relation_facts(_query("customer_names"), _model()) is None
    assert join_relation_facts(query, _model((query, facts))) is facts


def _with_fact_join(index: int, **changes: Any) -> RelationJoinsInfo:
    facts = _customer_orders_facts()
    joins = list(facts.joins)
    joins[index] = replace(joins[index], **changes)
    return replace(facts, joins=tuple(joins))


def _with_fact_input(index: int, **changes: Any) -> RelationJoinsInfo:
    facts = _customer_orders_facts()
    inputs = list(facts.inputs)
    inputs[index] = replace(inputs[index], **changes)
    return replace(facts, inputs=tuple(inputs))


def _with_fact_read(reference: JoinFieldRef) -> RelationJoinsInfo:
    facts = _customer_orders_facts()
    read = _query("customer_orders").select_items[1].expression
    return replace(facts, field_reads={**facts.field_reads, read: reference})


def _on_equality() -> JoinEqualityInfo:
    """The INNER JOIN's `on` equality, as a pair from customers to region."""

    on = _query("customer_orders").join_clauses[2].on_clause
    assert on is not None
    comparison = cast(ComparisonExpr, on.expression)
    return JoinEqualityInfo(
        left=JoinFieldRef(0, "region_id"),
        right=JoinFieldRef(3, "id"),
        left_type=ValueType(INT_TYPE, NULLABLE),
        right_type=ValueType(INT_TYPE, NON_NULL),
        comparison=comparison,
        left_operand=cast(DottedNameExpr, comparison.left),
        right_operand=cast(DottedNameExpr, comparison.right),
    )


def _without_last_join() -> RelationJoinsInfo:
    """Consistent facts for all but the last JOIN clause: nothing reads it."""

    facts = _customer_orders_facts()
    return replace(
        facts,
        inputs=facts.inputs[:-1],
        joins=facts.joins[:-1],
        field_reads={
            read: reference
            for read, reference in facts.field_reads.items()
            if reference.input != len(facts.joins)
        },
    )


UNDESCRIBED_FACTS: tuple[tuple[str, Callable[[], RelationJoinsInfo | None]], ...] = (
    ("no-facts", lambda: None),
    ("last-join-left-out", _without_last_join),
    (
        "one-join-short",
        lambda: replace(
            _customer_orders_facts(), joins=_customer_orders_facts().joins[:-1]
        ),
    ),
    (
        "one-input-short",
        lambda: replace(
            _customer_orders_facts(), inputs=_customer_orders_facts().inputs[:-1]
        ),
    ),
    (
        "join-names-another-clause",
        lambda: _with_fact_join(1, clause=_query("customer_orders").join_clauses[2]),
    ),
    (
        "input-names-another-clause",
        lambda: _with_fact_input(2, clause=_query("customer_orders").join_clauses[0]),
    ),
    (
        "target-reads-another-relation",
        lambda: _with_fact_input(3, relation=_source("orders")),
    ),
    ("target-has-another-binding", lambda: _with_fact_input(4, binding="slots")),
    ("join-has-another-kind", lambda: _with_fact_join(1, kind=AuthoredJoinKind.INNER)),
    ("on-left-out", lambda: _with_fact_join(1, condition=None)),
    (
        "foreign-on-added",
        lambda: _with_fact_join(
            3, condition=_customer_orders_facts().joins[1].condition
        ),
    ),
    (
        "hop-on-a-cross-join",
        lambda: _with_fact_join(
            3, relationship="customer_region", equalities=(_on_equality(),)
        ),
    ),
    ("read-names-a-missing-input", lambda: _with_fact_read(JoinFieldRef(5, "amount"))),
    (
        "read-names-a-negative-input",
        lambda: _with_fact_read(JoinFieldRef(-1, "amount")),
    ),
)


@pytest.mark.parametrize(
    "facts",
    [pytest.param(facts, id=case) for case, facts in UNDESCRIBED_FACTS],
)
def test_facts_that_do_not_describe_the_join_clauses_fail_at_the_first_join(
    facts: Callable[[], RelationJoinsInfo | None],
) -> None:
    query = _query("customer_orders")
    info = facts()
    model = _model() if info is None else _model((query, info))

    with pytest.raises(JoinLoweringError) as caught:
        join_relation_facts(query, model)

    assert caught.value.node is query.join_clauses[0]
    assert _failure(caught.value) == (
        "PIE-I1000",
        f"{FACT_FAILURE}resolved JOIN facts",
        18,
        11,
    )


@pytest.mark.parametrize(
    "with_facts",
    (
        pytest.param(False, id="after-a-failed-check"),
        pytest.param(True, id="with-facts"),
    ),
)
@pytest.mark.parametrize("name", ("windowed", "named_window", "grouped_window"))
def test_windows_over_join_rows_require_join_facts_but_do_not_refuse_them(
    name: str, with_facts: bool
) -> None:
    """A joined window lowers from the same complete JOIN facts as its row."""

    query = _query(name)
    model = _model((query, _region_join_facts(query))) if with_facts else _model()

    if with_facts:
        assert join_relation_facts(query, model) is model.relation_joins[query]
        return
    with pytest.raises(JoinLoweringError) as caught:
        join_relation_facts(query, model)
    assert _failure(caught.value)[1] == f"{FACT_FAILURE}resolved JOIN facts"
    assert caught.value.node is query.join_clauses[0]


def test_joined_qualify_selected_alias_and_named_window_keep_input_identity() -> None:
    source = """shape Row:
    id: Int
    row_key = unique(id)
source rows: Row = postgres.table("rows")
query ranked:
    from rows
    let other = rows
    inner join other on rows.id == other.id
    let w = window(order by rows.id)
    select:
        k = rows.id
        rn = row_number() window w
    qualify:
        rn <= 1
    order by:
        rn desc
"""
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert not semantic.diagnostics
    assert semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    emitted = emit_postgres_sql(lowered.ir)
    assert not emitted.diagnostics
    sql = emitted.artifacts[-1].sql
    assert 'ROW_NUMBER() OVER "w" AS "rn"' in sql
    assert 'WINDOW\n    "w" AS (ORDER BY "rows"."id" ASC)' in sql
    assert 'WHERE\n    "rn" <= 1' in sql
    assert 'ORDER BY\n    "rn" DESC' in sql


@pytest.mark.parametrize(
    ("build", "message"),
    [pytest.param(build, message, id=case) for case, build, message in VIOLATIONS],
)
def test_a_broken_relation_invariant_fails_at_the_first_join(
    build: Callable[[], RelationIR], message: str
) -> None:
    query = _query("customer_orders")

    with pytest.raises(JoinLoweringError) as caught:
        with report_join_invariants(query):
            build()

    assert caught.value.node is query.join_clauses[0]
    assert isinstance(caught.value.__cause__, ValueError)
    assert str(caught.value.__cause__) == message
    assert missing_semantic_fact_diagnostic(
        caught.value.node, caught.value.message
    ) == Diagnostic(
        code="PIE-I1000",
        severity=Severity.ERROR,
        message=f"{FACT_FAILURE}JOIN invariant: {message}",
        location=SourceLocation(PATH, 18, 11, 18, 71),
    )


def test_invariant_reporting_keeps_join_free_relations_and_other_errors() -> None:
    join_free = _query("customer_names")
    broken = ValueError("relation named window names must be unique")
    other = TypeError("relation named windows must be an exact tuple")

    with pytest.raises(ValueError) as unchanged:
        with report_join_invariants(join_free):
            raise broken
    with pytest.raises(TypeError) as passed:
        with report_join_invariants(_query("customer_orders")):
            raise other
    with report_join_invariants(_query("customer_orders")):
        relation = _join_relation_ir(
            _query("customer_orders"), _customer_orders_facts()
        )

    assert unchanged.value is broken
    assert passed.value is other
    assert relation.joins


def test_explain_is_refused_at_each_join_relation_in_definition_order() -> None:
    second = replace(_relation(), span=_span(7))

    diagnostics = join_explain_diagnostics(
        ScriptIR(definitions=(_join_free(), _relation(), _join_free(), second))
    )

    assert diagnostics == tuple(
        Diagnostic(
            code="PIE-I1000",
            severity=Severity.ERROR,
            message=EXPLAIN_REFUSAL,
            location=SourceLocation(PATH, line, 5, line, 9),
        )
        for line in (1, 7)
    )
    assert join_explain_diagnostics(ScriptIR(definitions=(_join_free(),))) == ()


@pytest.mark.parametrize("name", ("grouped", "aggregated"))
def test_grouping_reaches_join_facts_in_mvp2(name: str) -> None:
    query = _query(name)
    facts = _region_join_facts(query)
    assert join_relation_facts(query, _model((query, facts))) is facts


# Real analyzer -> builder integration; P0's hand-built facts remain the
# independent witnesses for the JOIN structures and invariant failures above.
INTEGRATION_PREFIX = """shape Node:
    id: Int
    parent_id: Int | None
    score: Float
    node_key = unique(id)
source nodes: Node = postgres.table("nodes")
"""
ROW_JOIN = """query joined:
    from nodes
    let peer = nodes
    left join peer on nodes.parent_id == peer.id
    let peer_score = peer.score
    let renamed_score = peer_score
    where nodes.id > 0
    select:
        own = nodes.id
        other = peer.id
        score = renamed_score
    order by peer.id desc
"""
GROUPED_JOIN = """query grouped:
    from nodes
    let peer = nodes
    cross join peer
    let peer_key = peer.id
    let key_again = peer_key
    let own_key = nodes.id
    let measure = peer.score
    group by:
        nodes.id
        key_again
    select:
        own = nodes.id
        other = peer.id
        total = count()
        score_total = sum(measure)
    having:
        other > 0 and total > 0 and sum(measure) > 0.0
    order by:
        key_again desc
        own_key
        score_total
"""


def _analyze_join(source: str) -> tuple[Script, SemanticModel]:
    parsed = _parse_script(source)
    semantic = analyze(parsed)
    assert not [d for d in semantic.diagnostics if d.severity is Severity.ERROR], (
        semantic.diagnostics
    )
    return semantic.script or parsed, semantic.model


def _build_join(source: str) -> tuple[Script, SemanticModel, ScriptIR, RelationIR]:
    script, model = _analyze_join(source)
    result = build_ir(script, model)
    assert result.diagnostics == ()
    assert result.ir is not None
    relation = result.ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    return script, model, result.ir, relation


def _input_field(input: int, name: str) -> FieldId:
    return FieldId(SymbolId(SymbolNamespace.RELATION, "nodes"), name, input)


def test_builder_lowers_self_join_reads_and_let_expansion_in_all_row_clauses() -> None:
    _, _, _, relation = _build_join(INTEGRATION_PREFIX + ROW_JOIN)

    assert [(item.binding, item.target.name) for item in relation.inputs] == [
        ("nodes", "nodes"),
        ("peer", "nodes"),
    ]
    assert relation.joins[0].kind is JoinKindIR.LEFT
    assert relation.joins[0].null_extends == (1,)
    condition = relation.joins[0].condition
    assert isinstance(condition, ComparisonIR)
    assert isinstance(condition.left, FieldRefIR)
    assert isinstance(condition.right, FieldRefIR)
    assert condition.left.field == _input_field(0, "parent_id")
    assert condition.right.field == _input_field(1, "id")
    assert condition.right.value_type.nullability is NullabilityIR.NON_NULL
    projected = tuple(item.expression for item in relation.projections)
    assert all(isinstance(item, FieldRefIR) for item in projected)
    assert [cast(FieldRefIR, item).field for item in projected] == [
        _input_field(0, "id"),
        _input_field(1, "id"),
        _input_field(1, "score"),
    ]
    assert [item.value_type.nullability for item in projected] == [
        NullabilityIR.NON_NULL,
        NullabilityIR.NULLABLE,
        NullabilityIR.NULLABLE,
    ]
    assert relation.filter is not None
    assert isinstance(relation.filter.expression, ComparisonIR)
    assert isinstance(relation.filter.expression.left, FieldRefIR)
    assert relation.filter.expression.left.field == _input_field(0, "id")
    ordered = relation.order_by[0].expression
    assert isinstance(ordered, FieldRefIR)
    assert (ordered.field, ordered.qualifier) == (_input_field(1, "id"), ("peer",))


@pytest.mark.parametrize(
    "expression",
    (
        "-peer.score",
        "peer.score + nodes.score",
        "peer.score if nodes.id > 0 else nodes.score",
        "peer.id in (nodes.id, 2)",
        "Float(peer.id)",
        "peer.id == nodes.id",
        "nodes.id <= peer.id <= 100",
        "peer.id is None",
        "coalesce(peer.score, nodes.score)",
    ),
)
def test_recursive_expression_lowering_never_falls_back_to_from_fields(
    expression: str,
) -> None:
    source = INTEGRATION_PREFIX + (
        "query joined:\n"
        "    from nodes\n"
        "    let peer = nodes\n"
        "    cross join peer\n"
        "    select:\n"
        f"        value = {expression}\n"
    )
    script, model, _, _ = _build_join(source)
    query = script.definitions[-1]
    assert isinstance(query, QueryDef)
    facts = model.relation_joins[query]
    missing = next(
        expression
        for expression, reference in facts.field_reads.items()
        if reference.input == 1
    )
    damaged = replace(
        facts,
        field_reads={
            key: value for key, value in facts.field_reads.items() if key != missing
        },
    )
    result = build_ir(script, replace(model, relation_joins={query: damaged}))
    assert result.ir is None
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (
            "PIE-I1000",
            FACT_FAILURE + "resolved JOIN field read",
            missing.span.line,
            missing.span.column,
        )
    ]


def test_grouped_join_keeps_same_named_input_keys_and_result_scope_identity() -> None:
    _, _, _, relation = _build_join(INTEGRATION_PREFIX + GROUPED_JOIN)
    assert [key.field for key in relation.group_keys] == [
        _input_field(0, "id"),
        _input_field(1, "id"),
    ]
    assert [key.qualifier for key in relation.group_keys] == [("nodes",), ("peer",)]
    assert relation.order_by[0].expression == relation.projections[1].expression
    assert relation.order_by[1].expression == relation.projections[0].expression
    assert relation.order_by[2].expression == relation.projections[3].expression
    assert relation.order_by[0].direction is OrderDirectionIR.DESC
    score_total = relation.projections[3].expression
    assert isinstance(score_total, AggregateCallIR)
    assert score_total.function == "sum"
    assert isinstance(score_total.arguments[0], FieldRefIR)
    assert score_total.arguments[0].field == _input_field(1, "score")
    predicate = relation.result_predicate
    assert predicate is not None
    assert isinstance(predicate.expression, BinaryIR)
    assert isinstance(predicate.expression.right, ComparisonIR)
    assert predicate.expression.right.left == score_total
    left = predicate.expression.left
    assert isinstance(left, BinaryIR)
    assert isinstance(left.left, ComparisonIR)
    assert left.left.left == relation.projections[1].expression


def test_join_group_key_missing_resolution_is_reported_instead_of_skipped() -> None:
    script, model, _, _ = _build_join(INTEGRATION_PREFIX + GROUPED_JOIN)
    query = script.definitions[-1]
    assert isinstance(query, QueryDef) and query.group_by_clause is not None
    key = query.group_by_clause.items[0].key
    facts = model.relation_joins[query]
    damaged = replace(
        facts,
        field_reads={
            read: ref for read, ref in facts.field_reads.items() if read != key
        },
    )
    result = build_ir(script, replace(model, relation_joins={query: damaged}))
    assert result.ir is None
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (
            "PIE-I1000",
            FACT_FAILURE + "resolved JOIN field read",
            key.span.line,
            key.span.column,
        )
    ]


@pytest.mark.parametrize("damage", ("missing", "invariant"))
def test_builder_reports_join_fact_and_invariant_failures_at_first_join(
    damage: str,
) -> None:
    script, model, _, _ = _build_join(INTEGRATION_PREFIX + ROW_JOIN)
    query = script.definitions[-1]
    assert isinstance(query, QueryDef)
    facts = model.relation_joins[query]
    joins = (
        {}
        if damage == "missing"
        else {query: replace(facts, joins=(replace(facts.joins[0], null_extends=()),))}
    )
    result = build_ir(script, replace(model, relation_joins=joins))
    clause = query.join_clauses[0]
    fact = (
        "resolved JOIN facts"
        if damage == "missing"
        else "JOIN invariant: " + NULL_EXTENSION
    )
    assert result.ir is None
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [("PIE-I1000", FACT_FAILURE + fact, clause.span.line, clause.span.column)]


def test_join_free_ir_is_unchanged_when_a_join_relation_is_appended() -> None:
    source = (
        INTEGRATION_PREFIX
        + """query plain:
    from nodes
    let key = id
    group by key
    select:
        own = id
        total = count()
    order by key
"""
    )
    _, _, standalone, plain = _build_join(source)
    _, _, combined, _ = _build_join(source + ROW_JOIN)
    assert combined.definitions[:-1] == standalone.definitions
    assert plain.inputs == plain.joins == ()
    assert plain.group_keys[0].field == FieldId(
        SymbolId(SymbolNamespace.RELATION, "nodes"), "id"
    )


@pytest.mark.parametrize("output_format", ("text", "json"))
def test_explain_join_refusal_uses_the_ir_failure_envelope(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], output_format: str
) -> None:
    path = tmp_path / "joined.pietto"
    path.write_text(INTEGRATION_PREFIX + ROW_JOIN)
    assert cli.main(["explain", str(path), "--format", output_format]) == 1
    captured = capsys.readouterr()
    if output_format == "text":
        assert captured.out == ""
        assert captured.err == f"{path}:7:1 PIE-I1000 error: {EXPLAIN_REFUSAL}\n"
        return
    assert captured.err == ""
    document = json.loads(captured.out)
    assert document["artifact"] == "Semantic Metadata Artifact v1"
    assert document["schema_version"] == 1
    assert document["command"] == "explain"
    assert document["ok"] is False
    assert "metadata" not in document
    assert document["error"] == {
        "stage": "ir",
        "message": "Semantic Metadata Artifact v1 metadata is unavailable because IR construction failed.",
    }
    assert [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in document["diagnostics"]
    ] == [("PIE-I1000", EXPLAIN_REFUSAL, 7, 1)]


@pytest.mark.parametrize(
    ("kind", "null_extends", "visible"),
    (
        ("inner", (), True),
        ("left", (1,), True),
        ("right", (0,), True),
        ("full", (0, 1), True),
        ("cross", (), True),
        ("semi", (), False),
        ("anti", (), False),
    ),
)
def test_real_builder_preserves_each_join_kind(
    kind: str, null_extends: tuple[int, ...], visible: bool
) -> None:
    clause = f"    let peer = nodes\n    {kind} join peer"
    if kind != "cross":
        clause += " on nodes.parent_id == peer.id"
    if kind in {"semi", "anti"}:
        # The JOIN-prefix `[not] any` is the hidden SEMI/ANTI JOIN before a later JOIN.
        negation = "not " if kind == "anti" else ""
        clause = (
            "    let peer = nodes\n"
            f"    where {negation}any(nodes.parent_id == peer.id for peer in peer)\n"
            "    let later = nodes\n    cross join later"
        )
    _, _, _, relation = _build_join(
        INTEGRATION_PREFIX
        + "query joined:\n    from nodes\n"
        + clause
        + "\n    select:\n        own = nodes.id\n"
    )
    assert relation.joins[0].kind is JoinKindIR(kind)
    assert relation.joins[0].null_extends == null_extends
    assert relation.inputs[1].visible is visible
    projected = relation.projections[0].expression
    assert isinstance(projected, FieldRefIR)
    assert projected.field == _input_field(0, "id")
    assert projected.value_type.nullability is (
        NullabilityIR.NULLABLE if kind in {"right", "full"} else NullabilityIR.NON_NULL
    )


def test_join_group_key_type_comes_from_the_nullable_tail_row() -> None:
    source = (
        INTEGRATION_PREFIX
        + """query grouped:
    from nodes
    let peer = nodes
    left join peer on nodes.parent_id == peer.id
    group by nodes.id, peer.id
    select:
        own = nodes.id
        other = peer.id
        total = count()
"""
    )
    _, _, _, relation = _build_join(source)
    assert [key.value_type.nullability for key in relation.group_keys] == [
        NullabilityIR.NON_NULL,
        NullabilityIR.NULLABLE,
    ]


def test_duplicate_join_group_keys_deduplicate_by_input_identity() -> None:
    script, model, _, relation = _build_join(INTEGRATION_PREFIX + GROUPED_JOIN)
    query = script.definitions[-1]
    assert isinstance(query, QueryDef) and query.group_by_clause is not None
    clause = query.group_by_clause
    duplicated = replace(
        query, group_by_clause=replace(clause, items=(*clause.items, *clause.items))
    )
    facts = model.relation_joins[query]
    scope = model.let_scopes[query]
    keys = _lower_group_keys(
        duplicated,
        model,
        input_schema=facts.row_schema,
        target_symbol=SymbolId(SymbolNamespace.RELATION, "nodes"),
        field_qualifier="nodes",
        let_expansions={binding.name: binding.expression for binding in scope.bindings},
        join_reads=JoinReads(relation.inputs, facts.field_reads),
    )
    assert keys == relation.group_keys
    assert [key.field for key in keys] == [_input_field(0, "id"), _input_field(1, "id")]


def test_build_after_failed_tail_check_reports_the_unresolved_field_read() -> None:
    parsed = _parse_script(
        INTEGRATION_PREFIX
        + "query bad:\n    from nodes\n    let peer = nodes\n    cross join peer\n"
        + "    select:\n        missing\n"
    )
    semantic = analyze(parsed)
    assert any(d.severity is Severity.ERROR for d in semantic.diagnostics)
    script = semantic.script or parsed
    query = script.definitions[-1]
    assert isinstance(query, QueryDef)
    selected = query.select_items[0].expression
    assert selected in semantic.model.expression_value_types
    assert selected not in semantic.model.relation_joins[query].field_reads
    result = build_ir(script, semantic.model)
    assert result.ir is None
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (
            "PIE-I1000",
            FACT_FAILURE + "resolved JOIN field read",
            selected.span.line,
            selected.span.column,
        )
    ]
