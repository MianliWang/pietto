from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from pietto import _window_identity
from pietto.ast_nodes import (
    QueryDef,
    WindowExpr,
    WindowNthDirectionKind,
    WindowNullTreatmentKind,
)
from pietto.ir import build_ir
from pietto.ir.model import (
    LiteralIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    WindowCallIR,
    WindowFrameBoundKindIR,
    WindowFrameExclusionIR,
    WindowFrameUnitIR,
    WindowNthDirectionIR,
    WindowNullTreatmentIR,
)
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, analyze
from pietto.semantic.window_semantics import (
    ExcludedFrameMembershipView,
    FrameValueFunctionKind,
    NavigationDirection,
    ValidatedFrame,
    ValidatedWindowSpecification,
    WindowFrameApplicability,
    WindowFunctionFramePolicy,
    WindowFunctionFramePolicyKind,
    WindowNthDirection,
    WindowNullTreatment,
    authored_window_specification_from_ast,
    exclude_frame_membership,
    frame_value_candidate_view,
    navigation_candidate_position,
    resolve_authored_window_specification,
    select_frame_value_candidate,
    validate_resolved_window_specification,
)
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.postgres import emit_postgres_sql


PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    value: Int nullable\n"
    "    category: Text nullable\n"
)
FRAME_IDENTITY = _window_identity.WindowFunctionIdentity(
    namespace=("slice9",),
    name="frame_value_contract",
    role=_window_identity.WindowFunctionRole.WINDOW_FUNCTION,
)
FRAME_POLICY = WindowFunctionFramePolicy(
    identity=FRAME_IDENTITY,
    kind=WindowFunctionFramePolicyKind.FRAME_SENSITIVE,
)


def _source(
    call: str,
    *,
    frame: str | None = None,
    connector: str = "postgres.table",
    declarations: str = "",
) -> str:
    frame_source = "" if frame is None else f"            {frame}\n"
    return (
        PREFIX + f'source rows: Row is {connector}("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    select:\n"
        f"        result = {call} window:\n"
        "            order by:\n"
        "                id\n"
        f"{frame_source}"
        f"{declarations}"
    )


def _parsed(source: str) -> tuple[QueryDef, WindowExpr]:
    result = parse_source(source, path="slice9.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert type(expression) is WindowExpr
    return relation, expression


def _analysis(call: str, *, frame: str | None = None):
    parsed = parse_source(_source(call, frame=frame), path="slice9.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    expression = cast(WindowExpr, relation.select_items[0].expression)
    result = analyze(parsed.ast)
    return result, relation, expression


def _compile(
    call: str,
    *,
    frame: str | None = None,
    connector: str = "postgres.table",
) -> tuple[ScriptIR, WindowCallIR]:
    parsed = parse_source(
        _source(call, frame=frame, connector=connector),
        path="slice9.pietto",
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.diagnostics == () and lowered.ir is not None
    relation = cast(RelationIR, lowered.ir.definitions[-1])
    expression = relation.projections[0].expression
    assert type(expression) is WindowCallIR
    return lowered.ir, expression


def _validated(frame: str) -> ValidatedWindowSpecification:
    _relation, expression = _parsed(_source("first_value(value)", frame=frame))
    resolved = resolve_authored_window_specification(
        authored_window_specification_from_ast(expression.spec),
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    result = validate_resolved_window_specification(
        resolved,
        function_identity=FRAME_IDENTITY,
        function_policy=FRAME_POLICY,
        argument_expressions=expression.call.arguments,
    )
    assert type(result) is ValidatedWindowSpecification
    assert type(result.frame) is ValidatedFrame
    return result


@pytest.mark.parametrize(
    ("call", "nth", "nulls"),
    (
        ("lag(value) respect nulls", None, WindowNullTreatmentKind.RESPECT),
        ("lead(value) ignore nulls", None, WindowNullTreatmentKind.IGNORE),
        ("first_value(value) ignore nulls", None, WindowNullTreatmentKind.IGNORE),
        (
            "nth_value(value, 2) from first respect nulls",
            WindowNthDirectionKind.FIRST,
            WindowNullTreatmentKind.RESPECT,
        ),
        (
            "nth_value(value, 2) from last ignore nulls",
            WindowNthDirectionKind.LAST,
            WindowNullTreatmentKind.IGNORE,
        ),
    ),
)
def test_modifier_grammar_retains_exact_authorship(
    call: str,
    nth: WindowNthDirectionKind | None,
    nulls: WindowNullTreatmentKind,
) -> None:
    _relation, expression = _parsed(_source(call))
    assert (
        None if expression.nth_direction is None else expression.nth_direction.kind
    ) is nth
    assert expression.null_treatment is not None
    assert expression.null_treatment.kind is nulls


def test_reverse_modifier_order_is_parser_negative_and_keywords_are_contextual() -> (
    None
):
    invalid = parse_source(
        _source("nth_value(value, 2) respect nulls from first"),
        path="slice9.pietto",
    )
    assert invalid.ast is None
    assert invalid.diagnostics
    contextual = parse_source(
        "shape Keywords:\n"
        "    first: Int not null\n"
        "    last: Int not null\n"
        "    respect: Int not null\n"
        "    ignore: Int not null\n"
        "    nulls: Int not null\n",
        path="slice9.pietto",
    )
    assert contextual.diagnostics == () and contextual.ast is not None


@pytest.mark.parametrize(
    "call",
    (
        "row_number() respect nulls",
        "lag(value) from first",
        "first_value(value) from last",
    ),
)
def test_modifier_applicability_fails_closed(call: str) -> None:
    parsed = parse_source(_source(call), path="slice9.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    result = analyze(parsed.ast)
    assert [item.code for item in result.diagnostics] == ["PIE-S2104"]


def test_omitted_and_explicit_defaults_are_effectively_equal_but_authored_distinct() -> (
    None
):
    omitted, _, omitted_expression = _analysis("nth_value(value, 2)")
    explicit, _, explicit_expression = _analysis(
        "nth_value(value, 2) from first respect nulls"
    )
    assert omitted.diagnostics == explicit.diagnostics == ()
    omitted_fact = omitted.model.window_expression_analyses[
        omitted_expression
    ].frame_value_fact
    explicit_fact = explicit.model.window_expression_analyses[
        explicit_expression
    ].frame_value_fact
    assert omitted_fact is not None and explicit_fact is not None
    assert (
        omitted_fact.modifiers.null_treatment
        is (explicit_fact.modifiers.null_treatment)
        is WindowNullTreatment.RESPECT_NULLS
    )
    assert (
        omitted_fact.modifiers.nth_direction
        is (explicit_fact.modifiers.nth_direction)
        is WindowNthDirection.FROM_FIRST
    )
    assert not omitted_fact.modifiers.null_treatment_is_explicit
    assert not omitted_fact.modifiers.nth_direction_is_explicit
    assert explicit_fact.modifiers.null_treatment_is_explicit
    assert explicit_fact.modifiers.nth_direction_is_explicit
    with pytest.raises(ValueError, match="exact window use|exact authorship"):
        replace(explicit_fact, modifiers=omitted_fact.modifiers)
    omitted_analysis = omitted.model.window_expression_analyses[omitted_expression]
    explicit_analysis = explicit.model.window_expression_analyses[explicit_expression]
    with pytest.raises(ValueError, match="exact window use|exact authorship"):
        replace(
            explicit_analysis,
            validated_specification=omitted_analysis.validated_specification,
        )
    with pytest.raises(ValueError, match="exact source use|exact key"):
        replace(
            explicit.model,
            window_expression_analyses={explicit_expression: omitted_analysis},
        )
    forged_value_types = dict(explicit.model.expression_value_types)
    forged_value_types[explicit_expression] = replace(
        forged_value_types[explicit_expression]
    )
    with pytest.raises(ValueError, match="exact result type"):
        replace(explicit.model, expression_value_types=forged_value_types)


@pytest.mark.parametrize(
    ("call", "function"),
    (
        ("first_value(value)", FrameValueFunctionKind.FIRST_VALUE),
        ("last_value(value)", FrameValueFunctionKind.LAST_VALUE),
        ("nth_value(value, 2)", FrameValueFunctionKind.NTH_VALUE),
    ),
)
def test_frame_value_identities_signatures_and_nullable_results_are_exact(
    call: str,
    function: FrameValueFunctionKind,
) -> None:
    result, _relation, expression = _analysis(call)
    assert result.diagnostics == ()
    analysis = result.model.window_expression_analyses[expression]
    assert analysis.frame_value_fact is not None
    assert analysis.frame_value_fact.function is function
    value_type = result.model.expression_value_types[expression]
    assert (
        value_type.resolved_type is analysis.frame_value_fact.value_type.resolved_type
    )
    assert value_type.resolved_type.name == "Int"
    assert value_type.nullability is EffectiveNullability.NULLABLE


@pytest.mark.parametrize("position", ("0", "-1", "value"))
def test_nth_value_requires_positive_integer_literal(position: str) -> None:
    parsed = parse_source(
        _source(f"nth_value(value, {position})"),
        path="slice9.pietto",
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    result = analyze(parsed.ast)
    assert [item.code for item in result.diagnostics] == ["PIE-S2104"]


def test_frame_value_candidates_start_after_exclusion_and_ignore_only_null_values() -> (
    None
):
    specification = _validated("rows between unbounded preceding and current row")
    membership = exclude_frame_membership(
        specification,
        partition_size=5,
        base_positions=range(0, 5),
        current_position=2,
    )
    assert type(membership) is ExcludedFrameMembershipView
    values = (10, None, 20, None, 30)
    respect = frame_value_candidate_view(
        membership,
        values,
        WindowNullTreatment.RESPECT_NULLS,
    )
    ignore = frame_value_candidate_view(
        membership,
        values,
        WindowNullTreatment.IGNORE_NULLS,
    )
    assert respect.positions == tuple(membership.positions) == (0, 1, 2, 3, 4)
    assert ignore.positions == (0, 2, 4)
    assert select_frame_value_candidate(ignore, FrameValueFunctionKind.FIRST_VALUE) == 0
    assert select_frame_value_candidate(ignore, FrameValueFunctionKind.LAST_VALUE) == 4
    assert (
        select_frame_value_candidate(
            ignore,
            FrameValueFunctionKind.NTH_VALUE,
            nth_position=2,
            nth_direction=WindowNthDirection.FROM_FIRST,
        )
        == 2
    )
    assert (
        select_frame_value_candidate(
            ignore,
            FrameValueFunctionKind.NTH_VALUE,
            nth_position=2,
            nth_direction=WindowNthDirection.FROM_LAST,
        )
        == 2
    )
    assert tuple(membership.positions) == (0, 1, 2, 3, 4)


def test_empty_all_null_and_short_candidate_sequences_return_no_position() -> None:
    specification = _validated("rows current row exclude current row")
    membership = exclude_frame_membership(
        specification,
        partition_size=3,
        base_positions=range(1, 2),
        current_position=1,
    )
    assert type(membership) is ExcludedFrameMembershipView
    empty = frame_value_candidate_view(
        membership,
        (None, None, None),
        WindowNullTreatment.IGNORE_NULLS,
    )
    assert empty.positions == ()
    assert (
        select_frame_value_candidate(empty, FrameValueFunctionKind.FIRST_VALUE) is None
    )
    assert (
        select_frame_value_candidate(
            empty,
            FrameValueFunctionKind.NTH_VALUE,
            nth_position=1,
            nth_direction=WindowNthDirection.FROM_FIRST,
        )
        is None
    )

    nonempty_specification = _validated(
        "rows between unbounded preceding and current row"
    )
    nonempty_membership = exclude_frame_membership(
        nonempty_specification,
        partition_size=3,
        base_positions=range(0, 3),
        current_position=2,
    )
    assert type(nonempty_membership) is ExcludedFrameMembershipView
    all_null = frame_value_candidate_view(
        nonempty_membership,
        (None, None, None),
        WindowNullTreatment.IGNORE_NULLS,
    )
    assert all_null.positions == ()
    short = frame_value_candidate_view(
        nonempty_membership,
        (10, 20, 30),
        WindowNullTreatment.RESPECT_NULLS,
    )
    assert (
        select_frame_value_candidate(
            short,
            FrameValueFunctionKind.NTH_VALUE,
            nth_position=4,
            nth_direction=WindowNthDirection.FROM_FIRST,
        )
        is None
    )


def test_lag_lead_ignore_counts_non_null_candidates_and_zero_keeps_anchor() -> None:
    values = (10, None, 20, None, 30)
    assert (
        navigation_candidate_position(
            values,
            current_position=4,
            direction=NavigationDirection.LAG,
            offset=2,
            null_treatment=WindowNullTreatment.IGNORE_NULLS,
        )
        == 0
    )
    assert (
        navigation_candidate_position(
            values,
            current_position=0,
            direction=NavigationDirection.LEAD,
            offset=2,
            null_treatment=WindowNullTreatment.IGNORE_NULLS,
        )
        == 4
    )
    assert (
        navigation_candidate_position(
            values,
            current_position=1,
            direction=NavigationDirection.LEAD,
            offset=0,
            null_treatment=WindowNullTreatment.IGNORE_NULLS,
        )
        == 1
    )
    assert (
        navigation_candidate_position(
            values,
            current_position=0,
            direction=NavigationDirection.LAG,
            offset=1,
            null_treatment=WindowNullTreatment.IGNORE_NULLS,
        )
        is None
    )


def test_inline_frame_value_ir_and_postgresql_sql_are_concrete() -> None:
    script_ir, expression = _compile(
        "nth_value(value, 2) from first respect nulls",
        frame="rows between unbounded preceding and current row exclude ties",
    )
    assert expression.null_treatment is WindowNullTreatmentIR.RESPECT_NULLS
    assert expression.nth_direction is WindowNthDirectionIR.FROM_FIRST
    assert expression.null_treatment_is_explicit
    assert expression.nth_direction_is_explicit
    position = expression.arguments[1]
    assert type(position) is LiteralIR
    assert position.value_type.canonical_name == "Int"
    assert position.value_type.nullability is NullabilityIR.NON_NULL
    assert expression.spec.frame is not None
    assert expression.spec.frame.unit is WindowFrameUnitIR.ROWS
    assert expression.spec.frame.exclusion is WindowFrameExclusionIR.TIES
    result = emit_postgres_sql(script_ir)
    assert result.diagnostics == ()
    assert 'NTH_VALUE("value", 2) OVER' in result.artifacts[0].sql
    assert "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW EXCLUDE TIES" in (
        result.artifacts[0].sql
    )
    assert "RESPECT NULLS" not in result.artifacts[0].sql
    assert "FROM FIRST" not in result.artifacts[0].sql


def test_backend_modifier_and_frame_limits_fail_closed() -> None:
    ignore_ir, _ = _compile("first_value(value) ignore nulls")
    assert [item.code for item in emit_postgres_sql(ignore_ir).diagnostics] == [
        "PIE-B1000"
    ]
    from_last_ir, _ = _compile("nth_value(value, 2) from last")
    assert [item.code for item in emit_postgres_sql(from_last_ir).diagnostics] == [
        "PIE-B1000"
    ]
    mysql_groups, _ = _compile(
        "first_value(value)",
        frame="groups current row",
        connector="mysql.table",
    )
    assert [item.code for item in emit_mysql_sql(mysql_groups).diagnostics] == [
        "PIE-B1000"
    ]
    range_offset, _ = _compile(
        "first_value(value)",
        frame="range 1 preceding",
    )
    assert [item.code for item in emit_postgres_sql(range_offset).diagnostics] == [
        "PIE-B1000"
    ]
    mysql_exclude, _ = _compile(
        "first_value(value)",
        frame="rows current row exclude no others",
        connector="mysql.table",
    )
    assert [item.code for item in emit_mysql_sql(mysql_exclude).diagnostics] == [
        "PIE-B1000"
    ]


def test_postgresql_rows_groups_offsets_and_exclusion_are_exact() -> None:
    rows, _ = _compile("first_value(value)", frame="rows 1 preceding")
    rows_sql = emit_postgres_sql(rows)
    assert rows_sql.diagnostics == ()
    assert "ROWS 1 PRECEDING EXCLUDE NO OTHERS" in rows_sql.artifacts[0].sql

    groups, _ = _compile(
        "last_value(value)",
        frame="groups current row exclude group",
    )
    groups_sql = emit_postgres_sql(groups)
    assert groups_sql.diagnostics == ()
    assert "GROUPS CURRENT ROW EXCLUDE GROUP" in groups_sql.artifacts[0].sql


def test_mysql_explicit_supported_modifiers_and_old_lag_omission_are_exact() -> None:
    mysql_ir, _ = _compile(
        "nth_value(value, 2) from first respect nulls",
        frame="rows between unbounded preceding and current row",
        connector="mysql.table",
    )
    mysql = emit_mysql_sql(mysql_ir)
    assert mysql.diagnostics == ()
    assert "NTH_VALUE(`value`, 2) FROM FIRST RESPECT NULLS OVER" in (
        mysql.artifacts[0].sql
    )

    lag_ir, lag = _compile("lag(value)")
    assert lag.null_treatment is WindowNullTreatmentIR.RESPECT_NULLS
    assert not lag.null_treatment_is_explicit
    postgres = emit_postgres_sql(lag_ir)
    assert postgres.diagnostics == ()
    assert 'LAG("value") OVER' in postgres.artifacts[0].sql
    assert "RESPECT NULLS" not in postgres.artifacts[0].sql


def test_named_frame_value_reaches_ir_but_target_restriction_still_fails() -> None:
    source = (
        PREFIX + 'source rows: Row is postgres.table("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    select:\n"
        "        result = first_value(value) ignore nulls window framed\n"
        "    window framed:\n"
        "        order by:\n"
        "            id\n"
        "        rows current row\n"
    )
    parsed = parse_source(source, path="slice9.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.ir is not None
    assert lowered.diagnostics == ()
    emitted = emit_postgres_sql(lowered.ir)
    assert not emitted.artifacts
    assert [item.code for item in emitted.diagnostics] == ["PIE-B1000"]


def test_ordinary_calls_do_not_gain_window_identity() -> None:
    source = (
        PREFIX + 'source rows: Row is postgres.table("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    select:\n"
        "        result = first_value(value)\n"
    )
    parsed = parse_source(source, path="slice9.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    assert type(relation.select_items[0].expression) is not WindowExpr
    semantic = analyze(parsed.ast)
    assert [item.code for item in semantic.diagnostics] == ["PIE-S2103"]


def test_window_ir_rejects_inconsistent_modifier_and_frame_combinations() -> None:
    _script, frame_value = _compile("first_value(value)")
    with pytest.raises(ValueError, match="frame IR must match"):
        replace(frame_value, spec=replace(frame_value.spec, frame=None))
    with pytest.raises(ValueError, match="NULL treatment"):
        replace(frame_value, null_treatment=None)
    with pytest.raises(ValueError, match="IGNORE NULLS"):
        replace(
            frame_value,
            null_treatment=WindowNullTreatmentIR.IGNORE_NULLS,
            null_treatment_is_explicit=False,
        )
    with pytest.raises(ValueError, match="nullable result"):
        replace(
            frame_value,
            value_type=replace(
                frame_value.value_type,
                nullability=NullabilityIR.NON_NULL,
            ),
        )
    value_argument = frame_value.arguments[0]
    with pytest.raises(ValueError, match="share exact T"):
        replace(
            frame_value,
            arguments=(
                replace(
                    value_argument,
                    value_type=replace(
                        value_argument.value_type,
                        canonical_name="Text",
                    ),
                ),
            ),
        )
    _nth_script, nth_value = _compile("nth_value(value, 2)")
    position = nth_value.arguments[1]
    assert type(position) is LiteralIR
    with pytest.raises(ValueError, match="positive integer literal"):
        replace(
            nth_value,
            arguments=(nth_value.arguments[0], replace(position, value=0)),
        )
    with pytest.raises(ValueError, match="exact non-null Int typing"):
        replace(
            nth_value,
            arguments=(
                nth_value.arguments[0],
                replace(
                    position,
                    value_type=replace(position.value_type, canonical_name="Text"),
                ),
            ),
        )
    with pytest.raises(ValueError, match="FROM LAST"):
        replace(
            nth_value,
            nth_direction=WindowNthDirectionIR.FROM_LAST,
            nth_direction_is_explicit=False,
        )

    default_frame = frame_value.spec.frame
    assert default_frame is not None
    with pytest.raises(ValueError, match="default frame IR"):
        replace(default_frame, unit=WindowFrameUnitIR.ROWS)

    _shorthand_script, shorthand = _compile(
        "first_value(value)",
        frame="rows unbounded preceding",
    )
    shorthand_frame = shorthand.spec.frame
    assert shorthand_frame is not None
    with pytest.raises(ValueError, match="shorthand frame IR"):
        replace(
            shorthand_frame,
            end=replace(
                shorthand_frame.end,
                kind=WindowFrameBoundKindIR.UNBOUNDED_FOLLOWING,
            ),
        )

    _exclude_script, excluded = _compile(
        "first_value(value)",
        frame="rows current row exclude ties",
    )
    excluded_frame = excluded.spec.frame
    assert excluded_frame is not None
    with pytest.raises(ValueError, match="omitted frame exclusion"):
        replace(excluded_frame, exclusion_is_explicit=False)
