from dataclasses import replace

import pytest

from pietto.ir import (
    AggregateCallIR,
    AggregateWindowCallIR,
    BinaryIR,
    LiteralIR,
    RelationIR,
    build_ir,
)
from pietto.ir.model import (
    WindowFrameBoundIR,
    WindowFrameBoundKindIR,
    WindowFrameExclusionIR,
    WindowFrameIR,
    WindowFrameUnitIR,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze


def test_aggregate_window_has_its_own_ir_carrier_and_omits_the_default_frame():
    parsed = parse_source("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        running = sum(id) window(order by id)
""")
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    lowered = build_ir(parsed.ast, semantic.model)
    assert not lowered.diagnostics
    assert lowered.ir is not None
    relation = lowered.ir.definitions[-1]
    assert type(relation) is RelationIR
    expression = relation.projections[0].expression
    assert type(expression) is AggregateWindowCallIR
    assert expression.function == "sum"
    assert expression.spec.frame is None


def test_aggregate_window_carrier_rejects_forged_argument_and_result_contracts():
    parsed = parse_source("""shape Row:
    id: Int
    amount: Decimal
    occurred_at: Date
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        total = sum(id) window()
        decimal_total = sum(amount) window()
        earliest = min(occurred_at) window()
        counted = count(id) window()
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None
    relation = lowered.ir.definitions[-1]
    assert type(relation) is RelationIR
    total, decimal_total, earliest, counted = (
        item.expression for item in relation.projections
    )
    assert type(total) is AggregateWindowCallIR
    assert type(decimal_total) is AggregateWindowCallIR
    assert type(earliest) is AggregateWindowCallIR
    assert type(counted) is AggregateWindowCallIR
    with pytest.raises(ValueError, match="contract"):
        replace(total, arguments=earliest.arguments)
    with pytest.raises(ValueError, match="contract"):
        replace(total, value_type=earliest.value_type)
    literal = LiteralIR(
        span=total.span, value_type=total.arguments[0].value_type, value=1
    )
    with pytest.raises(ValueError, match="contract"):
        replace(total, arguments=(literal,))
    invalid_operator = BinaryIR(
        left=total.arguments[0],
        operator="/",
        right=literal,
        span=total.span,
        value_type=total.value_type,
    )
    with pytest.raises(ValueError, match="contract"):
        replace(total, arguments=(invalid_operator,))
    wrong_leaf = BinaryIR(
        left=replace(total.arguments[0], value_type=earliest.value_type),
        operator="+",
        right=literal,
        span=total.span,
        value_type=total.value_type,
    )
    with pytest.raises(ValueError, match="contract"):
        replace(total, arguments=(wrong_leaf,))
    decimal_with_literal = BinaryIR(
        left=decimal_total.arguments[0],
        operator="+",
        right=literal,
        span=decimal_total.span,
        value_type=decimal_total.value_type,
    )
    with pytest.raises(ValueError, match="contract"):
        replace(decimal_total, arguments=(decimal_with_literal,))
    forged_grouped_value = AggregateCallIR(
        span=total.span,
        value_type=total.arguments[0].value_type,
        function="bogus",
        arguments=total.arguments,
    )
    with pytest.raises(ValueError, match="contract"):
        replace(total, arguments=(forged_grouped_value,))
    with pytest.raises(ValueError, match="contract"):
        replace(
            counted,
            arguments=(
                replace(
                    counted.arguments[0],
                    value_type=replace(
                        counted.arguments[0].value_type, canonical_name="Any"
                    ),
                ),
            ),
        )
    nested = BinaryIR(
        left=total,
        operator="+",
        right=literal,
        span=total.span,
        value_type=total.value_type,
    )
    with pytest.raises(ValueError, match="nested window"):
        replace(total, arguments=(nested,))
    groups_frame = WindowFrameIR(
        unit=WindowFrameUnitIR.GROUPS,
        start=WindowFrameBoundIR(WindowFrameBoundKindIR.UNBOUNDED_PRECEDING),
        end=WindowFrameBoundIR(WindowFrameBoundKindIR.CURRENT_ROW),
        exclusion=WindowFrameExclusionIR.NO_OTHERS,
        frame_is_explicit=True,
        end_is_explicit=True,
        exclusion_is_explicit=False,
    )
    with pytest.raises(
        ValueError, match="GROUPS aggregate windows require an ORDER BY"
    ):
        replace(total, spec=replace(total.spec, order_by=(), frame=groups_frame))
