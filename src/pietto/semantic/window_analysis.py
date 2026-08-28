"""Private semantic analysis for the bounded ranking and distribution subset."""

from __future__ import annotations

from collections.abc import Mapping

from pietto._window_identity import WindowFunctionIdentity, WindowFunctionRole
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    OrderItem,
    QueryDef,
    SelectItem,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import child_expressions, contains_semantic_aggregate
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
    NavigationWindowSemanticFact,
    RankingAdvancePolicy,
    RankingWindowSemanticFact,
    WindowExpressionAnalysis,
    WindowExpressionSemanticFact,
    WindowExpressionUnsupported,
    WindowFunctionFramePolicy,
    WindowFunctionFramePolicyKind,
    WindowOccurrenceIdentity,
    WindowOrderBindingFact,
    WindowPartitionBindingFact,
    WindowResultAvailability,
    WindowResultAvailabilityKind,
)
from pietto.semantic.window_navigation_analysis import (
    analyze_navigation_arguments,
    navigation_window_function_frame_policy,
    navigation_direction,
)
from pietto.semantic.window_order_analysis import bind_window_order_fields
from pietto.semantic.window_partition_analysis import bind_window_partition_fields
from pietto.semantic.window_input_analysis import (
    WindowInputScopeKind,
    build_window_input_scope,
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


def builtin_window_function_frame_policy(
    identity: WindowFunctionIdentity,
) -> WindowFunctionFramePolicy | None:
    """Return exact current builtin metadata policy or fail closed when absent."""

    if type(identity) is not WindowFunctionIdentity:
        raise TypeError("builtin frame policy lookup requires an exact identity")
    matches = tuple(
        WindowFunctionFramePolicy(
            identity=definition[0],
            kind=WindowFunctionFramePolicyKind.FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN,
        )
        for definition in (*_RANKING_POLICIES, *_DISTRIBUTION_FUNCTIONS)
        if definition[0] == identity
    )
    navigation_policy = navigation_window_function_frame_policy(identity)
    if navigation_policy is not None:
        matches = (*matches, navigation_policy)
    if len(matches) > 1:
        raise ValueError("builtin frame policy identity must be unique")
    return matches[0] if matches else None


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
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
) -> WindowExpressionAnalysis | WindowExpressionUnsupported:
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
        let_value_types=let_value_types,
        let_expressions=let_expressions,
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
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
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
        let_value_types=let_value_types,
        let_expressions=let_expressions,
        family="distribution",
    )
    if isinstance(result, WindowExpressionUnsupported):
        return result
    if result.distribution_fact is None:
        raise AssertionError("distribution analyzer returned no distribution fact")
    return result.distribution_fact


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
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
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
        let_value_types=let_value_types,
        let_expressions=let_expressions,
        family="ranking",
    )
    if isinstance(result, WindowExpressionUnsupported):
        return result
    if result.ranking_fact is None:
        raise AssertionError("ranking analyzer returned no ranking fact")
    return result.ranking_fact


def analyze_navigation_window_expression(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
) -> NavigationWindowSemanticFact | WindowExpressionUnsupported:
    """Analyze one direct selected navigation expression transiently."""

    result = _analyze_recognized_window_expression(
        definition=definition,
        item=item,
        selected_output_ordinal=selected_output_ordinal,
        source_id=source_id,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        value_types=value_types,
        diagnostics=diagnostics,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
        family="navigation",
    )
    if isinstance(result, WindowExpressionUnsupported):
        return result
    if result.navigation_fact is None:
        raise AssertionError("navigation analyzer returned no navigation fact")
    return result.navigation_fact


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
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
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
        let_value_types=let_value_types,
        let_expressions=let_expressions,
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
    let_value_types: Mapping[str, ValueType] | None,
    let_expressions: Mapping[str, Expression] | None,
    family: str | None,
) -> WindowExpressionAnalysis | WindowExpressionUnsupported:
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
    navigation = (
        navigation_direction(expression) if family in {None, "navigation"} else None
    )
    if (
        advance_policy is None
        and distribution_definition is None
        and navigation is None
    ):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="unsupported window function identity",
            diagnostics=diagnostics,
        )

    function_name = expression.identity.name
    if navigation is not None:
        signature = None
        result_formula = None
        distribution_policy = None
    elif advance_policy is not None:
        signature = _RANKING_SIGNATURE
        result_formula = _RANKING_RESULT_FORMULA
        distribution_policy = None
    else:
        assert distribution_definition is not None
        _, distribution_policy, signature, result_formula = distribution_definition

    actual_arity = len(expression.call.arguments)
    if navigation is not None and actual_arity not in {1, 2, 3}:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason=f"{function_name} requires one through three arguments",
            diagnostics=diagnostics,
            code="PIE-S2104",
            message=(
                f"Invalid arguments for function {function_name}: expected 1 through "
                f"3, got {actual_arity}"
            ),
        )
    if navigation is None:
        assert signature is not None
        expected_arity = len(signature.parameters)
    else:
        expected_arity = actual_arity
    if navigation is None and actual_arity != expected_arity:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason=f"{function_name} requires {expected_arity} arguments",
            diagnostics=diagnostics,
            code="PIE-S2104",
            message=(
                f"Invalid arguments for function {function_name}: expected "
                f"{expected_arity}, got "
                f"{actual_arity}"
            ),
        )

    if item.alias is None:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason=f"{function_name} requires a direct selected output alias",
            diagnostics=diagnostics,
        )

    if _relation_has_forbidden_window_placement(definition, item):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="window expression appears outside one direct selected output",
            diagnostics=diagnostics,
        )

    has_canonical_scope_facts = (
        let_value_types is not None or let_expressions is not None
    )
    if not has_canonical_scope_facts and (
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
            reason="relation context requires canonical window input scope facts",
            diagnostics=diagnostics,
        )

    has_selected_aggregate = any(
        contains_semantic_aggregate(selected.expression)
        for selected in definition.select_items
    )
    if definition.group_by_clause is None and has_selected_aggregate:
        # The established aggregate schema pass owns PIE-S2312 for this route.
        return WindowExpressionUnsupported(
            occurrence=occurrence,
            expression=expression,
            identity=expression.identity,
            reason=f"no-group aggregate context does not admit {function_name}",
        )

    input_scope = build_window_input_scope(
        definition=definition,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        value_types=value_types,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    if (
        input_scope.kind is WindowInputScopeKind.GROUPED_RESULT
        and not input_scope.has_valid_group_aggregate
    ):
        # GROUP schema validation owns invalid and pure-group diagnostics.
        return WindowExpressionUnsupported(
            occurrence=occurrence,
            expression=expression,
            identity=expression.identity,
            reason=f"grouped context does not admit {function_name}",
        )

    direct_partition_expressions: list[NameExpr | DottedNameExpr] = []
    for partition_expression in expression.spec.partition_by:
        if type(partition_expression) is NameExpr:
            direct_partition_expressions.append(partition_expression)
        elif type(partition_expression) is DottedNameExpr:
            direct_partition_expressions.append(partition_expression)
        else:
            return _unsupported(
                occurrence=occurrence,
                expression=expression,
                reason="window partition expression must be a direct field",
                diagnostics=diagnostics,
            )

    if direct_partition_expressions and input_scope.row_schema.is_unknown:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="window input schema must be concrete",
            diagnostics=diagnostics,
        )

    diagnostics_before = len(diagnostics)
    partition_bindings = bind_window_partition_fields(
        partition_expressions=tuple(direct_partition_expressions),
        input_schema=input_scope.row_schema,
        field_qualifier=field_qualifier,
        value_types=value_types,
        diagnostics=diagnostics,
        bare_value_types=input_scope.bare_value_types,
        allow_qualified_fields=input_scope.allows_qualified_fields,
    )
    if partition_bindings is None:
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
            reason="window partition field type must be concrete",
        )

    if not expression.spec.order_by:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason=f"{function_name} requires at least one window order field",
            diagnostics=diagnostics,
        )

    direct_order_items: list[OrderItem] = []
    for order_item in expression.spec.order_by:
        if type(order_item) is not OrderItem or type(order_item.expression) not in {
            NameExpr,
            DottedNameExpr,
        }:
            return _unsupported(
                occurrence=occurrence,
                expression=expression,
                reason="window order expression must be a direct field",
                diagnostics=diagnostics,
            )
        direct_order_items.append(order_item)

    if input_scope.row_schema.is_unknown:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="window input schema must be concrete",
            diagnostics=diagnostics,
        )

    diagnostics_before = len(diagnostics)
    order_bindings = bind_window_order_fields(
        order_items=tuple(direct_order_items),
        input_schema=input_scope.row_schema,
        field_qualifier=field_qualifier,
        value_types=value_types,
        diagnostics=diagnostics,
        bare_value_types=input_scope.bare_value_types,
        allow_qualified_fields=input_scope.allows_qualified_fields,
    )
    if order_bindings is None:
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
            reason=(
                "window order direction must be omitted, asc, or desc"
                if any(
                    item.direction is not None
                    and (
                        type(item.direction) is not str
                        or item.direction not in ("asc", "desc")
                    )
                    for item in direct_order_items
                )
                else "window order field type must be concrete"
            ),
        )

    if navigation is not None:
        navigation_result = analyze_navigation_arguments(
            occurrence=occurrence,
            expression=expression,
            input_schema=input_scope.row_schema,
            field_qualifier=field_qualifier,
            value_types=value_types,
            diagnostics=diagnostics,
            bare_value_types=input_scope.bare_value_types,
            allow_qualified_fields=input_scope.allows_qualified_fields,
        )
        if isinstance(navigation_result, WindowExpressionUnsupported):
            return navigation_result
        semantic_fact = navigation_result.semantic_fact
        return WindowExpressionAnalysis(
            semantic_fact=semantic_fact,
            ranking_fact=None,
            distribution_fact=None,
            partition_binding_fact=WindowPartitionBindingFact(
                semantic_fact=semantic_fact,
                bindings=partition_bindings,
            ),
            order_binding_fact=WindowOrderBindingFact(
                semantic_fact=semantic_fact,
                bindings=order_bindings,
            ),
            navigation_fact=navigation_result,
        )

    assert signature is not None
    assert result_formula is not None
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
    ranking_fact: RankingWindowSemanticFact | None = None
    distribution_fact: DistributionWindowSemanticFact | None = None
    if advance_policy is not None:
        ranking_fact = RankingWindowSemanticFact(
            semantic_fact=semantic_fact,
            advance_policy=advance_policy,
        )
    else:
        assert distribution_policy is not None
        if distribution_policy is DistributionWindowPolicy.PERCENT_RANK:
            ranking_fact = RankingWindowSemanticFact(
                semantic_fact=semantic_fact,
                advance_policy=RankingAdvancePolicy.GAPPED_PEER_RANK,
            )
        distribution_fact = DistributionWindowSemanticFact(
            semantic_fact=semantic_fact,
            distribution_policy=distribution_policy,
            ranking_fact=ranking_fact,
            bucket_count=bucket_count,
        )
    return WindowExpressionAnalysis(
        semantic_fact=semantic_fact,
        ranking_fact=ranking_fact,
        distribution_fact=distribution_fact,
        partition_binding_fact=WindowPartitionBindingFact(
            semantic_fact=semantic_fact,
            bindings=partition_bindings,
        ),
        order_binding_fact=WindowOrderBindingFact(
            semantic_fact=semantic_fact,
            bindings=order_bindings,
        ),
    )


def _ranking_policy(expression: WindowExpr) -> RankingAdvancePolicy | None:
    callee = expression.call.callee
    if type(callee) is not NameExpr:
        return None
    for identity, advance_policy in _RANKING_POLICIES:
        if expression.identity == identity and callee.name == identity.name:
            return advance_policy
    return None


def _relation_has_forbidden_window_placement(
    definition: TableDef | QueryDef,
    selected_window_item: SelectItem,
) -> bool:
    """Reject forbidden placements without reopening the relation context."""

    expressions: list[Expression] = []
    if definition.where_clause is not None:
        expressions.append(definition.where_clause.expression)
    if definition.group_by_clause is not None:
        expressions.extend(item.key for item in definition.group_by_clause.items)
    if definition.satisfying_clause is not None:
        expressions.append(definition.satisfying_clause.expression)
    if definition.let_clause is not None:
        expressions.extend(
            binding.expression for binding in definition.let_clause.bindings
        )
    if definition.order_by_clause is not None:
        expressions.extend(item.expression for item in definition.order_by_clause.items)
    expressions.extend(
        item.expression
        for item in definition.select_items
        if item is not selected_window_item and type(item.expression) is not WindowExpr
    )
    return any(_contains_window_expression(expression) for expression in expressions)


def _contains_window_expression(expression: Expression) -> bool:
    if type(expression) is WindowExpr:
        return True
    return any(
        _contains_window_expression(child) for child in child_expressions(expression)
    )


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
