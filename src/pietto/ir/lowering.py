"""Internal lowering helpers for foundational Semantic IR metadata."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from pietto._window_identity import WindowFunctionRole
from pietto.ast_nodes import (
    AuthoredWindowFrameExclusion,
    AuthoredWindowFrame,
    AuthoredWindowFrameKind,
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    OrderItem,
    Span,
    TypeDef,
    TypeExpr,
    UnaryExpr,
    WindowExpr,
    WindowFrameBoundKind,
    WindowSpec,
)
from pietto.ir.diagnostics import missing_semantic_fact_diagnostic
from pietto.ir.model import (
    AggregateCallIR,
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    ExpressionLoweringResult,
    FieldId,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    NamedWindowBaseIR,
    NamedWindowDeclarationIR,
    NamedWindowLocalSpecIR,
    NamedWindowOccurrenceIR,
    NamedWindowUseIR,
    NullabilityIR,
    OrderDirectionIR,
    RowFieldIR,
    RowSchemaIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    UnaryIR,
    WindowCallIR,
    WindowFrameBoundIR,
    WindowFrameBoundKindIR,
    WindowFrameExclusionIR,
    WindowFrameIR,
    WindowFrameUnitIR,
    WindowFunctionIdentityIR,
    WindowFunctionRoleIR,
    WindowOrderItemIR,
    WindowNthDirectionIR,
    WindowNullTreatmentIR,
    WindowRelationOccurrenceIR,
    WindowSpecIR,
    WindowUseKindIR,
    WindowUseOccurrenceIR,
)
from pietto.semantic.catalog import BUILTIN_FUNCTIONS
from pietto.semantic.aggregates import (
    aggregate_argument_can_use_let_scope,
    semantic_aggregate_call_name,
    semantic_aggregate_result_value_type,
)
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.window_semantics import (
    FrameValueWindowSemanticFact,
    NavigationWindowSemanticFact,
    ValidatedFrame,
    ValidatedFrameNotApplicable,
    ResolvedNamedWindowNamespace,
    ResolvedWindowFrame,
    WindowExpressionAnalysis,
)

_UNKNOWN_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)
_WINDOW_ARGUMENT_ARITIES = {
    "row_number": frozenset({0}),
    "rank": frozenset({0}),
    "dense_rank": frozenset({0}),
    "percent_rank": frozenset({0}),
    "cume_dist": frozenset({0}),
    "ntile": frozenset({1}),
    "lag": frozenset({1, 2, 3}),
    "lead": frozenset({1, 2, 3}),
    "first_value": frozenset({1}),
    "last_value": frozenset({1}),
    "nth_value": frozenset({2}),
}


def lower_type_ref(
    type_expr: TypeExpr,
    semantic_model: SemanticModel,
) -> TypeRefIR:
    """Lower one parsed type reference from readonly semantic facts."""

    resolved = semantic_model.type_resolutions.get(type_expr)
    canonical = semantic_model.type_expansions.get(type_expr)
    nullability = semantic_model.type_nullability.get(
        type_expr,
        EffectiveNullability.UNKNOWN,
    )
    return _type_ref_from_semantics(
        declared_name=type_expr.name,
        resolved=resolved,
        canonical=canonical,
        nullability=nullability,
    )


def lower_canonical_type_ref(
    type_expr: TypeExpr,
    semantic_model: SemanticModel,
) -> TypeRefIR:
    """Lower the canonical target of one parsed type reference."""

    type_ref = lower_type_ref(type_expr, semantic_model)
    return TypeRefIR(
        symbol=type_ref.canonical_symbol,
        canonical_symbol=type_ref.canonical_symbol,
        declared_name=type_ref.canonical_name,
        canonical_name=type_ref.canonical_name,
        kind=type_ref.canonical_kind,
        canonical_kind=type_ref.canonical_kind,
        nullability=type_ref.nullability,
    )


def lower_value_type(
    value_type: ValueType,
    semantic_model: SemanticModel,
) -> TypeRefIR:
    """Lower an expression value type with canonical alias information."""

    resolved = value_type.resolved_type
    canonical = resolved
    if isinstance(resolved.definition, TypeDef):
        canonical = semantic_model.type_expansions.get(
            resolved.definition.base,
            resolved,
        )
    return _type_ref_from_semantics(
        declared_name=resolved.name,
        resolved=resolved,
        canonical=canonical,
        nullability=value_type.nullability,
    )


def lower_expr(
    expression: Expression,
    semantic_model: SemanticModel,
    *,
    fields: Mapping[str, RowField] | None = None,
    field_owner: SymbolId | None = None,
    field_qualifier: str | None = None,
    let_expansions: Mapping[str, Expression] | None = None,
    window_input_expressions: Mapping[str, ExpressionIR] | None = None,
) -> ExpressionLoweringResult:
    """Lower one typed expression without re-running semantic analysis."""

    if (
        expression not in semantic_model.expression_value_types
        and not _is_static_connector_call(expression)
    ):
        return ExpressionLoweringResult(
            expression=None,
            diagnostics=(
                missing_semantic_fact_diagnostic(
                    expression,
                    "expression value type",
                ),
            ),
        )

    try:
        if type(expression) is WindowExpr:
            lowered = _lower_window_expr(
                expression,
                semantic_model,
                fields=fields or {},
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions or {},
                window_input_expressions=window_input_expressions or {},
            )
        else:
            lowered = _lower_expr_node(
                expression,
                semantic_model,
                fields=fields or {},
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions or {},
                let_stack=frozenset(),
            )
    except (_LetExpansionLoweringError, _WindowExpressionLoweringError) as error:
        return ExpressionLoweringResult(
            expression=None,
            diagnostics=(
                missing_semantic_fact_diagnostic(error.expression, error.fact),
            ),
        )

    return ExpressionLoweringResult(expression=lowered, diagnostics=())


def lower_group_key_ref(
    expression: NameExpr | DottedNameExpr,
    semantic_model: SemanticModel,
    *,
    field: RowField,
    field_owner: SymbolId,
) -> FieldRefIR:
    """Lower one resolved GROUP BY field without requiring expression facts."""

    value_type = lower_value_type(
        ValueType(
            resolved_type=field.resolved_type,
            nullability=field.nullability,
        ),
        semantic_model,
    )
    if isinstance(expression, NameExpr):
        name = expression.name
        qualifier: tuple[str, ...] = ()
    else:
        name = expression.parts[-1]
        qualifier = expression.parts[:-1]
    return FieldRefIR(
        name=name,
        qualifier=qualifier,
        field=FieldId(owner=field_owner, name=field.name),
        span=lower_span(expression.span),
        value_type=value_type,
    )


def _lower_window_expr(
    expression: WindowExpr,
    semantic_model: SemanticModel,
    *,
    fields: Mapping[str, RowField],
    field_owner: SymbolId | None,
    field_qualifier: str | None,
    let_expansions: Mapping[str, Expression],
    window_input_expressions: Mapping[str, ExpressionIR],
) -> WindowCallIR:
    """Lower one semantically admitted window without re-running analysis."""

    analysis = semantic_model.window_expression_analyses.get(expression)
    if type(analysis) is not WindowExpressionAnalysis:
        raise _WindowExpressionLoweringError(
            expression,
            "validated window semantic facts",
        )
    if analysis.authored_expression is not expression:
        raise _WindowExpressionLoweringError(
            expression,
            "exact authored window analysis",
        )
    effective_expression = analysis.semantic_fact.expression
    identity = effective_expression.identity
    callee = effective_expression.call.callee
    arities = _WINDOW_ARGUMENT_ARITIES.get(identity.name)
    if (
        identity.namespace != ()
        or identity.role is not WindowFunctionRole.WINDOW_FUNCTION
        or arities is None
        or type(callee) is not NameExpr
        or callee.name != identity.name
    ):
        raise _WindowExpressionLoweringError(
            expression,
            "supported window function identity",
        )
    if len(effective_expression.call.arguments) not in arities:
        raise _WindowExpressionLoweringError(
            expression,
            "supported window function arity",
        )
    if not effective_expression.spec.order_by:
        raise _WindowExpressionLoweringError(
            expression,
            "nonempty window order specification",
        )
    if any(
        item.direction is not None
        and (type(item.direction) is not str or item.direction not in ("asc", "desc"))
        for item in effective_expression.spec.order_by
    ):
        raise _WindowExpressionLoweringError(
            expression,
            "supported window order direction",
        )

    def lower_operand(operand: Expression) -> ExpressionIR:
        if type(operand) is NameExpr and operand.name in window_input_expressions:
            return window_input_expressions[operand.name]
        return _lower_expr_node(
            operand,
            semantic_model,
            fields=fields,
            field_owner=field_owner,
            field_qualifier=field_qualifier,
            let_expansions=let_expansions,
            let_stack=frozenset(),
        )

    frame_ir: WindowFrameIR | None = None
    validated_frame = analysis.validated_specification.frame
    if type(validated_frame) is ValidatedFrame:
        resolved = validated_frame.resolved
        assert resolved.unit is not None
        assert resolved.start is not None
        assert resolved.end is not None
        assert resolved.exclusion is not None
        frame_ir = _lower_effective_window_frame(resolved, lower_operand)
    elif type(validated_frame) is not ValidatedFrameNotApplicable:
        raise AssertionError("window lowering requires exact validated frame evidence")

    modifiers = None
    if type(analysis.navigation_fact) is NavigationWindowSemanticFact:
        modifiers = analysis.navigation_fact.modifiers
    elif type(analysis.frame_value_fact) is FrameValueWindowSemanticFact:
        modifiers = analysis.frame_value_fact.modifiers
    null_treatment = (
        None
        if modifiers is None or modifiers.null_treatment is None
        else WindowNullTreatmentIR(modifiers.null_treatment.value)
    )
    nth_direction = (
        None
        if modifiers is None or modifiers.nth_direction is None
        else WindowNthDirectionIR(modifiers.nth_direction.value)
    )
    named_use = _lower_named_window_use(analysis, lower_operand)

    return WindowCallIR(
        span=lower_span(expression.span),
        value_type=lower_value_type(
            semantic_model.expression_value_types[expression],
            semantic_model,
        ),
        identity=WindowFunctionIdentityIR(
            namespace=identity.namespace,
            name=identity.name,
            role=WindowFunctionRoleIR(identity.role.value),
        ),
        arguments=tuple(
            lower_operand(argument) for argument in effective_expression.call.arguments
        ),
        spec=WindowSpecIR(
            partition_by=tuple(
                lower_operand(partition)
                for partition in effective_expression.spec.partition_by
            ),
            order_by=tuple(
                _lower_window_order_item(item, lower_operand)
                for item in effective_expression.spec.order_by
            ),
            span=lower_span(effective_expression.spec.span),
            frame=frame_ir,
        ),
        null_treatment=null_treatment,
        null_treatment_is_explicit=(
            False if modifiers is None else modifiers.null_treatment_is_explicit
        ),
        nth_direction=nth_direction,
        nth_direction_is_explicit=(
            False if modifiers is None else modifiers.nth_direction_is_explicit
        ),
        named_use=named_use,
    )


def _lower_window_bound(
    kind: WindowFrameBoundKind,
    offset: Expression | None,
    lower_operand: Callable[[Expression], ExpressionIR],
) -> WindowFrameBoundIR:
    return WindowFrameBoundIR(
        kind=WindowFrameBoundKindIR(kind.value.replace("_", " ").upper()),
        offset=None if offset is None else lower_operand(offset),
    )


def _lower_window_order_item(
    item: OrderItem,
    lower_operand: Callable[[Expression], ExpressionIR],
) -> WindowOrderItemIR:
    if type(item) is not OrderItem:
        raise TypeError("window order item must be exact")
    return WindowOrderItemIR(
        expression=lower_operand(item.expression),
        direction=OrderDirectionIR(
            "ASC" if item.direction is None else item.direction.upper()
        ),
        direction_is_explicit=item.direction is not None,
        span=lower_span(item.span),
    )


def _lower_effective_window_frame(
    resolved: ResolvedWindowFrame,
    lower_operand: Callable[[Expression], ExpressionIR],
) -> WindowFrameIR:
    if type(resolved) is not ResolvedWindowFrame:
        raise TypeError("effective window frame must be exact")
    assert resolved.unit is not None
    assert resolved.start is not None
    assert resolved.end is not None
    assert resolved.exclusion is not None
    return WindowFrameIR(
        unit=WindowFrameUnitIR(resolved.unit.value.upper()),
        start=_lower_window_bound(
            resolved.start.kind,
            resolved.start.offset,
            lower_operand,
        ),
        end=_lower_window_bound(
            resolved.end.kind,
            resolved.end.offset,
            lower_operand,
        ),
        exclusion=WindowFrameExclusionIR(
            resolved.exclusion.value.replace("_", " ").upper()
        ),
        frame_is_explicit=(
            resolved.authored.kind is not AuthoredWindowFrameKind.OMITTED
        ),
        end_is_explicit=resolved.authored.kind is AuthoredWindowFrameKind.BETWEEN,
        exclusion_is_explicit=(
            resolved.authored.exclusion is not AuthoredWindowFrameExclusion.OMITTED
        ),
    )


def _lower_authored_window_frame(
    frame: AuthoredWindowFrame,
    lower_operand: Callable[[Expression], ExpressionIR],
) -> WindowFrameIR | None:
    if type(frame) is not AuthoredWindowFrame:
        raise TypeError("authored window frame must be exact")
    if frame.kind is AuthoredWindowFrameKind.OMITTED:
        return None
    assert frame.unit is not None
    assert frame.start is not None
    end = frame.end
    if frame.kind is AuthoredWindowFrameKind.SHORTHAND:
        end_ir = WindowFrameBoundIR(WindowFrameBoundKindIR.CURRENT_ROW)
    else:
        assert end is not None
        end_ir = _lower_window_bound(end.kind, end.offset, lower_operand)
    exclusion = (
        WindowFrameExclusionIR.NO_OTHERS
        if frame.exclusion is AuthoredWindowFrameExclusion.OMITTED
        else WindowFrameExclusionIR(frame.exclusion.value.replace("_", " ").upper())
    )
    return WindowFrameIR(
        unit=WindowFrameUnitIR(frame.unit.value.upper()),
        start=_lower_window_bound(frame.start.kind, frame.start.offset, lower_operand),
        end=end_ir,
        exclusion=exclusion,
        frame_is_explicit=True,
        end_is_explicit=frame.kind is AuthoredWindowFrameKind.BETWEEN,
        exclusion_is_explicit=(
            frame.exclusion is not AuthoredWindowFrameExclusion.OMITTED
        ),
    )


def _lower_named_local_spec(
    specification: WindowSpec | None,
    fallback_span: Span,
    lower_operand: Callable[[Expression], ExpressionIR],
) -> NamedWindowLocalSpecIR:
    if specification is None:
        return NamedWindowLocalSpecIR((), (), None, lower_span(fallback_span))
    return NamedWindowLocalSpecIR(
        partition_by=tuple(
            lower_operand(expression) for expression in specification.partition_by
        ),
        order_by=tuple(
            _lower_window_order_item(item, lower_operand)
            for item in specification.order_by
        ),
        frame=_lower_authored_window_frame(specification.frame, lower_operand),
        span=lower_span(specification.span),
    )


def _lower_named_window_use(
    analysis: WindowExpressionAnalysis,
    lower_operand: Callable[[Expression], ExpressionIR],
) -> NamedWindowUseIR | None:
    named = analysis.resolved_named_use
    if named is None:
        return None
    authored = named.composed.expression
    occurrence = named.composed.occurrence
    query_block = occurrence.query_block
    owner = WindowRelationOccurrenceIR(
        SymbolId(SymbolNamespace.RELATION, query_block.relation_name),
        lower_span(query_block.span),
    )
    target = named.composed.target_template.occurrence
    target_ir = NamedWindowOccurrenceIR(
        owner,
        target.declaration_position,
        lower_span(target.span),
    )
    assert authored.base is not None
    return NamedWindowUseIR(
        occurrence=WindowUseOccurrenceIR(
            owner,
            occurrence.selected_output_ordinal,
            WindowUseKindIR(occurrence.kind.value),
            lower_span(occurrence.span),
        ),
        target=target_ir,
        reference_spelling=authored.base.name,
        local_spec=_lower_named_local_spec(
            authored.spec,
            authored.spec.span,
            lower_operand,
        ),
    )


def lower_named_window_declarations(
    namespace: ResolvedNamedWindowNamespace,
    semantic_model: SemanticModel,
    *,
    fields: Mapping[str, RowField],
    field_owner: SymbolId,
    field_qualifier: str,
    let_expansions: Mapping[str, Expression],
    window_input_expressions: Mapping[str, ExpressionIR],
) -> tuple[NamedWindowDeclarationIR, ...]:
    """Lower every declaration occurrence without choosing a target strategy."""

    if type(namespace) is not ResolvedNamedWindowNamespace:
        raise TypeError("named window namespace must be exact")
    owner = WindowRelationOccurrenceIR(
        SymbolId(SymbolNamespace.RELATION, namespace.query_block.relation_name),
        lower_span(namespace.query_block.span),
    )

    def lower_operand(expression: Expression) -> ExpressionIR:
        if type(expression) is NameExpr and expression.name in (
            window_input_expressions
        ):
            return window_input_expressions[expression.name]
        return _lower_expr_node(
            expression,
            semantic_model,
            fields=fields,
            field_owner=field_owner,
            field_qualifier=field_qualifier,
            let_expansions=let_expansions,
            let_stack=frozenset(),
        )

    occurrences = {
        template.occurrence: NamedWindowOccurrenceIR(
            owner,
            template.occurrence.declaration_position,
            lower_span(template.occurrence.span),
        )
        for template in namespace.templates
    }
    return tuple(
        NamedWindowDeclarationIR(
            occurrence=occurrences[template.occurrence],
            name=template.declaration.name,
            base=(
                None
                if template.base is None
                else NamedWindowBaseIR(
                    template.base.reference.name,
                    occurrences[template.base.target],
                )
            ),
            local_spec=_lower_named_local_spec(
                template.declaration.spec,
                template.declaration.span,
                lower_operand,
            ),
            span=lower_span(template.declaration.span),
        )
        for template in namespace.templates
    )


def _lower_expr_node(
    expression: Expression,
    semantic_model: SemanticModel,
    *,
    fields: Mapping[str, RowField],
    field_owner: SymbolId | None,
    field_qualifier: str | None,
    let_expansions: Mapping[str, Expression],
    let_stack: frozenset[str],
) -> ExpressionIR:
    """Recursively copy one expression into parser-independent IR."""

    value_type = lower_value_type(
        semantic_model.expression_value_types.get(
            expression,
            _UNKNOWN_VALUE_TYPE,
        ),
        semantic_model,
    )
    common = {
        "span": lower_span(expression.span),
        "value_type": value_type,
    }

    if isinstance(expression, LiteralExpr):
        return LiteralIR(value=expression.value, **common)
    if isinstance(expression, NameExpr):
        if expression.name in let_expansions:
            if expression.name in let_stack:
                raise _LetExpansionLoweringError(
                    expression,
                    "acyclic let binding expansion",
                )
            expanded = let_expansions[expression.name]
            if expanded not in semantic_model.expression_value_types:
                raise _LetExpansionLoweringError(
                    expanded,
                    "let binding expression value type",
                )
            return _lower_expr_node(
                expanded,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack | frozenset((expression.name,)),
            )
        field = None
        if expression.name in fields:
            field = FieldId(owner=field_owner, name=expression.name)
        return FieldRefIR(
            name=expression.name,
            qualifier=(),
            field=field,
            **common,
        )
    if isinstance(expression, DottedNameExpr):
        field = None
        if (
            len(expression.parts) == 2
            and expression.parts[0] == field_qualifier
            and expression.parts[1] in fields
        ):
            field = FieldId(owner=field_owner, name=expression.parts[1])
        return FieldRefIR(
            name=expression.parts[-1],
            qualifier=expression.parts[:-1],
            field=field,
            **common,
        )
    if isinstance(expression, CallExpr):
        callee = _callee_name(expression)
        if _is_valid_aggregate_projection(expression, semantic_model, value_type):
            return AggregateCallIR(
                function=callee,
                arguments=tuple(
                    _lower_expr_node(
                        argument,
                        semantic_model,
                        fields=fields,
                        field_owner=field_owner,
                        field_qualifier=field_qualifier,
                        let_expansions=_aggregate_argument_let_expansions(
                            callee,
                            argument,
                            let_expansions,
                        ),
                        let_stack=frozenset(),
                    )
                    for argument in expression.arguments
                ),
                **common,
            )
        callee_symbol = None
        if callee in BUILTIN_FUNCTIONS:
            callee_symbol = SymbolId(SymbolNamespace.CALLABLE, callee)
        return CallIR(
            callee=callee,
            callee_symbol=callee_symbol,
            arguments=tuple(
                _lower_expr_node(
                    argument,
                    semantic_model,
                    fields=fields,
                    field_owner=field_owner,
                    field_qualifier=field_qualifier,
                    let_expansions=let_expansions,
                    let_stack=let_stack,
                )
                for argument in expression.arguments
            ),
            **common,
        )
    if isinstance(expression, UnaryExpr):
        return UnaryIR(
            operator=expression.operator,
            operand=_lower_expr_node(
                expression.operand,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            **common,
        )
    if isinstance(expression, BinaryExpr):
        return BinaryIR(
            left=_lower_expr_node(
                expression.left,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            operator=expression.operator,
            right=_lower_expr_node(
                expression.right,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            **common,
        )
    if isinstance(expression, ComparisonExpr):
        return ComparisonIR(
            left=_lower_expr_node(
                expression.left,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            operator=expression.operator,
            right=_lower_expr_node(
                expression.right,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            **common,
        )
    if isinstance(expression, BetweenExpr):
        return BetweenIR(
            value=_lower_expr_node(
                expression.value,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            lower=_lower_expr_node(
                expression.lower,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            upper=_lower_expr_node(
                expression.upper,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            **common,
        )
    if isinstance(expression, IsNullExpr):
        return IsNullIR(
            value=_lower_expr_node(
                expression.value,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            negated=expression.negated,
            **common,
        )
    raise TypeError(f"Unsupported expression AST node: {type(expression).__name__}")


def _aggregate_argument_let_expansions(
    function_name: str,
    argument: Expression,
    let_expansions: Mapping[str, Expression],
) -> Mapping[str, Expression]:
    if aggregate_argument_can_use_let_scope(
        function_name,
        argument,
        let_expansions,
    ):
        return let_expansions
    return {}


def _callee_name(expression: CallExpr) -> str:
    """Return the static source-level name of a call target."""

    if isinstance(expression.callee, NameExpr):
        return expression.callee.name
    return ".".join(expression.callee.parts)


class _LetExpansionLoweringError(Exception):
    """Internal fail-closed guard for inconsistent let lowering facts."""

    def __init__(self, expression: Expression, fact: str) -> None:
        super().__init__(fact)
        self.expression = expression
        self.fact = fact


class _WindowExpressionLoweringError(Exception):
    """Internal fail-closed guard for inconsistent window lowering facts."""

    def __init__(self, expression: Expression, fact: str) -> None:
        super().__init__(fact)
        self.expression = expression
        self.fact = fact


def _is_valid_aggregate_projection(
    expression: CallExpr,
    semantic_model: SemanticModel,
    value_type: TypeRefIR,
) -> bool:
    """Return whether this call is a precise output projection aggregate."""

    function_name = semantic_aggregate_call_name(expression)
    if function_name is None:
        return False
    semantic_value_type = semantic_model.expression_value_types.get(expression)
    if semantic_value_type is None:
        return False
    if not _aggregate_type_matches_ir(
        function_name,
        expression,
        semantic_model,
        semantic_value_type,
        value_type,
    ):
        return False

    for relation, schema in semantic_model.relation_row_schemas.items():
        for item in relation.select_items:
            if item.expression is not expression or item.alias is None:
                continue
            field = schema.fields.get(item.alias)
            return (
                field is not None
                and field.resolved_type.kind is semantic_value_type.resolved_type.kind
                and field.resolved_type.name == semantic_value_type.resolved_type.name
                and field.nullability is semantic_value_type.nullability
            )
    return False


def _aggregate_type_matches_ir(
    function_name: str,
    expression: CallExpr,
    semantic_model: SemanticModel,
    semantic_value_type: ValueType,
    value_type: TypeRefIR,
) -> bool:
    if not expression.arguments:
        expected = semantic_aggregate_result_value_type(function_name)
    elif len(expression.arguments) == 1:
        argument_type = semantic_model.expression_value_types.get(
            expression.arguments[0]
        )
        expected = (
            None
            if argument_type is None
            else semantic_aggregate_result_value_type(function_name, argument_type)
        )
    else:
        expected = None
    return (
        expected is not None
        and semantic_value_type == expected
        and value_type.canonical_kind is TypeKindIR.BUILTIN
        and value_type.canonical_name == expected.resolved_type.name
        and value_type.nullability.value == expected.nullability.value
    )


def _is_static_connector_call(expression: Expression) -> bool:
    """Allow the validated connector call omitted from expression typing."""

    return isinstance(expression, CallExpr) and _callee_name(expression) in (
        "postgres.table",
        "mysql.table",
    )


def lower_row_schema(
    schema: RowSchema,
    semantic_model: SemanticModel,
) -> RowSchemaIR:
    """Lower an ordered semantic row schema without retaining AST nodes."""

    return RowSchemaIR(
        fields=tuple(
            _lower_row_field(field, semantic_model) for field in schema.fields.values()
        ),
        is_unknown=schema.is_unknown,
    )


def _lower_row_field(
    field: RowField,
    semantic_model: SemanticModel,
) -> RowFieldIR:
    """Lower a row field, using its declaration when semantic facts have one."""

    if field.definition is not None:
        type_ref = lower_type_ref(field.definition.type_expr, semantic_model)
        span = lower_span(field.definition.span)
    else:
        type_ref = _type_ref_from_semantics(
            declared_name=field.resolved_type.name,
            resolved=field.resolved_type,
            canonical=field.resolved_type,
            nullability=field.nullability,
        )
        span = None

    nullability = _lower_nullability(field.nullability)
    return RowFieldIR(
        name=field.name,
        type_ref=type_ref,
        nullability=nullability,
        span=span,
    )


def _type_ref_from_semantics(
    *,
    declared_name: str,
    resolved: ResolvedType | None,
    canonical: ResolvedType | None,
    nullability: EffectiveNullability,
) -> TypeRefIR:
    """Copy resolved type facts into parser-independent IR metadata."""

    resolved = resolved or _unknown_type(declared_name)
    canonical = canonical or _unknown_type()

    return TypeRefIR(
        symbol=_type_symbol(resolved),
        canonical_symbol=_type_symbol(canonical),
        declared_name=declared_name,
        canonical_name=canonical.name,
        kind=TypeKindIR(resolved.kind.value),
        canonical_kind=TypeKindIR(canonical.kind.value),
        nullability=_lower_nullability(nullability),
    )


def _type_symbol(resolved: ResolvedType) -> SymbolId | None:
    """Build a stable type symbol unless semantic resolution is Unknown."""

    if resolved.kind is TypeKind.UNKNOWN:
        return None
    return SymbolId(
        namespace=SymbolNamespace.TYPE,
        name=resolved.name,
    )


def _unknown_type(name: str = "<unknown>") -> ResolvedType:
    """Create an internal Unknown type for incomplete semantic metadata."""

    return ResolvedType(name=name, kind=TypeKind.UNKNOWN)


def _lower_nullability(value: EffectiveNullability) -> NullabilityIR:
    """Copy effective semantic nullability into the IR enum."""

    return NullabilityIR(value.value)


def lower_span(span: Span) -> SourceSpan:
    """Copy a parser AST span without retaining the AST object."""

    return SourceSpan(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
