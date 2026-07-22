"""Private semantic analysis for the bounded ranking and distribution subset."""

from __future__ import annotations

from pietto._window_identity import WindowFunctionIdentity, WindowFunctionRole
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import contains_semantic_aggregate
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.generic_compatibility import (
    ConcreteTypeExpression,
    GenericSignature,
    LogicalTypeIdentity,
    SignatureParameter,
    SignatureMatch,
    bind_signature,
)
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.nullability_formulas import (
    NonNullFormula,
    NullabilityEvaluationContext,
    NullabilityEvaluationMatch,
    SignatureResultFormula,
    evaluate_signature_result_nullability,
)
from pietto.semantic.window_semantics import (
    DistributionWindowPolicy,
    DistributionWindowSemanticFact,
    RankingAdvancePolicy,
    RankingWindowSemanticFact,
    WindowExpressionSemanticFact,
    WindowExpressionUnsupported,
    WindowOccurrenceIdentity,
    WindowResultAvailability,
    WindowResultAvailabilityKind,
)

__all__: tuple[str, ...] = ()

_RANKING_RESULT_IDENTITY = LogicalTypeIdentity(
    name="Int",
    kind=TypeKind.BUILTIN,
)
_RANKING_SIGNATURE = GenericSignature(
    type_variables=(),
    parameters=(),
    result=ConcreteTypeExpression(logical_type=_RANKING_RESULT_IDENTITY),
)
_RANKING_RESULT_FORMULA = SignatureResultFormula(
    signature=_RANKING_SIGNATURE,
    nullability=NonNullFormula(),
)
_ROW_NUMBER_RESULT_IDENTITY = _RANKING_RESULT_IDENTITY
_ROW_NUMBER_SIGNATURE = _RANKING_SIGNATURE
_ROW_NUMBER_RESULT_FORMULA = _RANKING_RESULT_FORMULA

_DISTRIBUTION_FLOAT_RESULT_IDENTITY = LogicalTypeIdentity(
    name="Float",
    kind=TypeKind.BUILTIN,
)
_DISTRIBUTION_INT_RESULT_IDENTITY = _RANKING_RESULT_IDENTITY
_PERCENT_RANK_SIGNATURE = GenericSignature(
    type_variables=(),
    parameters=(),
    result=ConcreteTypeExpression(
        logical_type=_DISTRIBUTION_FLOAT_RESULT_IDENTITY,
    ),
)
_PERCENT_RANK_RESULT_FORMULA = SignatureResultFormula(
    signature=_PERCENT_RANK_SIGNATURE,
    nullability=NonNullFormula(),
)
_CUME_DIST_SIGNATURE = GenericSignature(
    type_variables=(),
    parameters=(),
    result=ConcreteTypeExpression(
        logical_type=_DISTRIBUTION_FLOAT_RESULT_IDENTITY,
    ),
)
_CUME_DIST_RESULT_FORMULA = SignatureResultFormula(
    signature=_CUME_DIST_SIGNATURE,
    nullability=NonNullFormula(),
)
_NTILE_SIGNATURE = GenericSignature(
    type_variables=(),
    parameters=(
        SignatureParameter(
            position=0,
            type_expression=ConcreteTypeExpression(
                logical_type=_DISTRIBUTION_INT_RESULT_IDENTITY,
            ),
        ),
    ),
    result=ConcreteTypeExpression(
        logical_type=_DISTRIBUTION_INT_RESULT_IDENTITY,
    ),
)
_NTILE_RESULT_FORMULA = SignatureResultFormula(
    signature=_NTILE_SIGNATURE,
    nullability=NonNullFormula(),
)

_RANKING_POLICIES = (
    (
        WindowFunctionIdentity(
            namespace=(),
            name="row_number",
            role=WindowFunctionRole.WINDOW_FUNCTION,
        ),
        RankingAdvancePolicy.PER_ROW,
    ),
    (
        WindowFunctionIdentity(
            namespace=(),
            name="rank",
            role=WindowFunctionRole.WINDOW_FUNCTION,
        ),
        RankingAdvancePolicy.GAPPED_PEER_RANK,
    ),
    (
        WindowFunctionIdentity(
            namespace=(),
            name="dense_rank",
            role=WindowFunctionRole.WINDOW_FUNCTION,
        ),
        RankingAdvancePolicy.DENSE_PEER_RANK,
    ),
)

_DISTRIBUTION_FUNCTIONS = (
    (
        WindowFunctionIdentity(
            namespace=(),
            name="percent_rank",
            role=WindowFunctionRole.WINDOW_FUNCTION,
        ),
        DistributionWindowPolicy.PERCENT_RANK,
        _PERCENT_RANK_SIGNATURE,
        _PERCENT_RANK_RESULT_FORMULA,
    ),
    (
        WindowFunctionIdentity(
            namespace=(),
            name="cume_dist",
            role=WindowFunctionRole.WINDOW_FUNCTION,
        ),
        DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION,
        _CUME_DIST_SIGNATURE,
        _CUME_DIST_RESULT_FORMULA,
    ),
    (
        WindowFunctionIdentity(
            namespace=(),
            name="ntile",
            role=WindowFunctionRole.WINDOW_FUNCTION,
        ),
        DistributionWindowPolicy.BALANCED_BUCKETS,
        _NTILE_SIGNATURE,
        _NTILE_RESULT_FORMULA,
    ),
)


def analyze_window_expression(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
) -> (
    RankingWindowSemanticFact
    | DistributionWindowSemanticFact
    | WindowExpressionUnsupported
):
    """Analyze one direct selected recognized window expression transiently."""

    return _analyze_recognized_window_expression(
        definition=definition,
        item=item,
        selected_output_ordinal=selected_output_ordinal,
        source_id=source_id,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        value_types=value_types,
        diagnostics=diagnostics,
        family=None,
    )


def analyze_distribution_window_expression(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
) -> DistributionWindowSemanticFact | WindowExpressionUnsupported:
    """Analyze one direct selected distribution expression transiently."""

    result = _analyze_recognized_window_expression(
        definition=definition,
        item=item,
        selected_output_ordinal=selected_output_ordinal,
        source_id=source_id,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        value_types=value_types,
        diagnostics=diagnostics,
        family="distribution",
    )
    if isinstance(result, RankingWindowSemanticFact):
        raise AssertionError("distribution analyzer returned a ranking fact")
    return result


def analyze_ranking_window_expression(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
) -> RankingWindowSemanticFact | WindowExpressionUnsupported:
    """Analyze one direct selected ranking expression without publishing it."""

    result = _analyze_recognized_window_expression(
        definition=definition,
        item=item,
        selected_output_ordinal=selected_output_ordinal,
        source_id=source_id,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        value_types=value_types,
        diagnostics=diagnostics,
        family="ranking",
    )
    if isinstance(result, DistributionWindowSemanticFact):
        raise AssertionError("ranking analyzer returned a distribution fact")
    return result


def analyze_row_number_window_expression(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
) -> WindowExpressionSemanticFact | WindowExpressionUnsupported:
    """Retain the Slice 7 core-fact result shape through the ranking analyzer."""

    result = analyze_ranking_window_expression(
        definition=definition,
        item=item,
        selected_output_ordinal=selected_output_ordinal,
        source_id=source_id,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        value_types=value_types,
        diagnostics=diagnostics,
    )
    if isinstance(result, WindowExpressionUnsupported):
        return result
    return result.semantic_fact


def _analyze_recognized_window_expression(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    family: str | None,
) -> (
    RankingWindowSemanticFact
    | DistributionWindowSemanticFact
    | WindowExpressionUnsupported
):
    """Own the single common validation and construction path."""

    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("definition must be an exact TableDef or QueryDef")
    if type(item) is not SelectItem:
        raise TypeError("item must be an exact SelectItem")
    if type(item.expression) is not WindowExpr:
        raise TypeError("item expression must be an exact WindowExpr")
    if type(input_schema) is not RowSchema:
        raise TypeError("input_schema must be an exact RowSchema")
    if type(field_qualifier) is not str:
        raise TypeError("field_qualifier must be an exact string")
    if type(value_types) is not dict:
        raise TypeError("value_types must be an exact dict")
    if type(diagnostics) is not list:
        raise TypeError("diagnostics must be an exact list")

    expression = item.expression
    occurrence = WindowOccurrenceIdentity(
        source_id=source_id,
        relation_name=definition.name,
        selected_output_ordinal=selected_output_ordinal,
        span=expression.span,
    )

    advance_policy = (
        _ranking_policy(expression) if family in {None, "ranking"} else None
    )
    distribution_definition = (
        _distribution_definition(expression)
        if family in {None, "distribution"}
        else None
    )
    if advance_policy is None and distribution_definition is None:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="unsupported window function identity",
            diagnostics=diagnostics,
        )

    function_name = expression.identity.name
    if advance_policy is not None:
        signature = _RANKING_SIGNATURE
        result_formula = _RANKING_RESULT_FORMULA
        distribution_policy = None
    else:
        assert distribution_definition is not None
        _, distribution_policy, signature, result_formula = distribution_definition

    expected_arity = len(signature.parameters)
    if len(expression.call.arguments) != expected_arity:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason=f"{function_name} requires {expected_arity} arguments",
            diagnostics=diagnostics,
            code="PIE-S2104",
            message=(
                f"Invalid arguments for function {function_name}: expected "
                f"{expected_arity}, got "
                f"{len(expression.call.arguments)}"
            ),
        )

    if item.alias is None:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason=f"{function_name} requires a direct selected output alias",
            diagnostics=diagnostics,
        )

    if (
        definition.group_by_clause is not None
        or definition.satisfying_clause is not None
        or definition.let_clause is not None
        or any(
            contains_semantic_aggregate(selected.expression)
            for selected in definition.select_items
        )
    ):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason=f"relation context does not admit {function_name}",
            diagnostics=diagnostics,
        )

    if (
        sum(
            type(selected.expression) is WindowExpr
            for selected in definition.select_items
        )
        != 1
    ):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="relation requires exactly one window output",
            diagnostics=diagnostics,
        )

    if expression.spec.partition_by:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason=f"{function_name} partitioning is deferred",
            diagnostics=diagnostics,
        )

    if len(expression.spec.order_by) != 1:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason=f"{function_name} requires exactly one window order field",
            diagnostics=diagnostics,
        )

    order_item = expression.spec.order_by[0]
    if order_item.direction is not None:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="explicit window order direction is deferred",
            diagnostics=diagnostics,
        )

    order_expression = order_item.expression
    if not isinstance(order_expression, (NameExpr, DottedNameExpr)):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="window order expression must be a direct field",
            diagnostics=diagnostics,
        )

    if input_schema.is_unknown:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="window input schema must be concrete",
            diagnostics=diagnostics,
        )

    diagnostics_before = len(diagnostics)
    order_value_type = infer_row_expression(
        order_expression,
        input_schema,
        value_types,
        diagnostics,
        report_unknown_name=True,
        field_qualifier=field_qualifier,
    )
    if (
        order_value_type.kind is ValueTypeKind.UNKNOWN
        or order_value_type.resolved_type.kind is TypeKind.UNKNOWN
    ):
        if len(diagnostics) == diagnostics_before:
            _append_call_diagnostic(
                diagnostics,
                expression.call,
                code="PIE-S2103",
                message=f"Unknown function: {_source_function_name(expression.call)}",
            )
        return WindowExpressionUnsupported(
            occurrence=occurrence,
            expression=expression,
            identity=expression.identity,
            reason="window order field type must be concrete",
        )

    bucket_count: int | None = None
    signature_arguments: tuple[LogicalTypeIdentity, ...] = ()
    if distribution_policy is DistributionWindowPolicy.BALANCED_BUCKETS:
        argument = expression.call.arguments[0]
        if (
            type(argument) is not LiteralExpr
            or type(argument.value) is not int
            or argument.value <= 0
        ):
            return _unsupported(
                occurrence=occurrence,
                expression=expression,
                reason="ntile requires one positive integer literal",
                diagnostics=diagnostics,
                code="PIE-S2104",
                message=(
                    "Invalid arguments for function ntile: expected one positive "
                    "integer literal"
                ),
            )
        bucket_count = argument.value
        signature_arguments = (_DISTRIBUTION_INT_RESULT_IDENTITY,)

    signature_match = bind_signature(signature, signature_arguments)
    if type(signature_match) is not SignatureMatch:
        raise AssertionError("recognized window signature must bind")
    nullability_match = evaluate_signature_result_nullability(
        result_formula,
        NullabilityEvaluationContext(
            argument_nullabilities=tuple(
                EffectiveNullability.NON_NULL for _ in signature_arguments
            ),
            omitted_positions=(),
        ),
    )
    if type(nullability_match) is not NullabilityEvaluationMatch:
        raise AssertionError("recognized window nullability formula must evaluate")

    result_type = ValueType(
        resolved_type=ResolvedType(
            name=signature_match.result_type.name,
            kind=signature_match.result_type.kind,
        ),
        nullability=nullability_match.value,
    )
    if result_type.nullability is not EffectiveNullability.NON_NULL:
        raise AssertionError("recognized window result must be non-null")
    semantic_fact = WindowExpressionSemanticFact(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        result=WindowResultAvailability(
            kind=WindowResultAvailabilityKind.CONCRETE,
            value_type=result_type,
        ),
    )
    if advance_policy is not None:
        return RankingWindowSemanticFact(
            semantic_fact=semantic_fact,
            advance_policy=advance_policy,
        )

    assert distribution_policy is not None
    ranking_fact = None
    if distribution_policy is DistributionWindowPolicy.PERCENT_RANK:
        ranking_fact = RankingWindowSemanticFact(
            semantic_fact=semantic_fact,
            advance_policy=RankingAdvancePolicy.GAPPED_PEER_RANK,
        )
    return DistributionWindowSemanticFact(
        semantic_fact=semantic_fact,
        distribution_policy=distribution_policy,
        ranking_fact=ranking_fact,
        bucket_count=bucket_count,
    )


def _ranking_policy(expression: WindowExpr) -> RankingAdvancePolicy | None:
    callee = expression.call.callee
    if type(callee) is not NameExpr:
        return None
    for identity, advance_policy in _RANKING_POLICIES:
        if expression.identity == identity and callee.name == identity.name:
            return advance_policy
    return None


def _distribution_definition(
    expression: WindowExpr,
) -> (
    tuple[
        WindowFunctionIdentity,
        DistributionWindowPolicy,
        GenericSignature,
        SignatureResultFormula,
    ]
    | None
):
    callee = expression.call.callee
    if type(callee) is not NameExpr:
        return None
    for definition in _DISTRIBUTION_FUNCTIONS:
        identity = definition[0]
        if expression.identity == identity and callee.name == identity.name:
            return definition
    return None


def _unsupported(
    *,
    occurrence: WindowOccurrenceIdentity,
    expression: WindowExpr,
    reason: str,
    diagnostics: list[Diagnostic],
    code: str = "PIE-S2103",
    message: str | None = None,
) -> WindowExpressionUnsupported:
    _append_call_diagnostic(
        diagnostics,
        expression.call,
        code=code,
        message=message
        or f"Unknown function: {_source_function_name(expression.call)}",
    )
    return WindowExpressionUnsupported(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        reason=reason,
    )


def _source_function_name(call: CallExpr) -> str:
    if type(call.callee) is NameExpr:
        return call.callee.name
    assert isinstance(call.callee, DottedNameExpr)
    return ".".join(call.callee.parts)


def _append_call_diagnostic(
    diagnostics: list[Diagnostic],
    call: CallExpr,
    *,
    code: str,
    message: str,
) -> None:
    span = call.span
    diagnostics.append(
        Diagnostic(
            code=code,
            severity=Severity.ERROR,
            message=message,
            location=SourceLocation(
                path=span.path,
                line=span.line,
                column=span.column,
                end_line=span.end_line,
                end_column=span.end_column,
            ),
        )
    )
