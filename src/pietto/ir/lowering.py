"""Internal lowering helpers for foundational Semantic IR metadata."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING

from pietto._window_identity import WindowFunctionRole
from pietto.ast_nodes import (
    AnyExpr,
    SourceDef,
    AuthoredWindowFrameExclusion,
    AuthoredWindowFrame,
    AuthoredWindowFrameKind,
    BetweenExpr,
    BinaryExpr,
    CastExpr,
    CallExpr,
    ConditionalExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    LiteralExpr,
    MembershipExpr,
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
    AggregateWindowCallIR,
    AggregateCallIR,
    AnyFieldIR,
    ExistsIR,
    ConnectorIR,
    BetweenIR,
    BinaryIR,
    CastIR,
    CallIR,
    ConditionalIR,
    ComparisonIR,
    ExpressionIR,
    ExpressionLoweringResult,
    FieldId,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    MembershipIR,
    NamedWindowBaseIR,
    NamedWindowDeclarationIR,
    NamedWindowLocalSpecIR,
    NamedWindowOccurrenceIR,
    NamedWindowUseIR,
    NullabilityIR,
    OrderItemIR,
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
from pietto.semantic.catalog import is_builtin_function_name
from pietto.semantic.aggregates import (
    aggregate_argument_can_use_let_scope,
    semantic_aggregate_call_name,
    semantic_aggregate_result_value_type,
)
from pietto.semantic.expressions import _canonical_value_type
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
from pietto.semantic.model import AnyFieldReadInfo, AnyValueSemanticInfo
from pietto.semantic.window_semantics import (
    AggregateWindowAnalysis,
    FrameValueWindowSemanticFact,
    NavigationWindowSemanticFact,
    ValidatedFrame,
    ValidatedFrameNotApplicable,
    ResolvedNamedWindowNamespace,
    ResolvedWindowFrame,
    WindowExpressionAnalysis,
)

if TYPE_CHECKING:
    from pietto.ir.joins import JoinReads

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
    join_reads: JoinReads | None = None,
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
                join_reads=join_reads,
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
                join_reads=join_reads,
                window_input_expressions=window_input_expressions,
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
    join_reads: JoinReads | None = None,
) -> WindowCallIR | AggregateWindowCallIR:
    """Lower one semantically admitted window without re-running analysis."""

    aggregate_name = semantic_aggregate_call_name(expression.call)
    if aggregate_name in {"sum", "count", "avg", "min", "max"}:
        analysis = semantic_model.aggregate_window_analyses.get(expression)
        expected_analysis_type = AggregateWindowAnalysis
    else:
        analysis = semantic_model.window_expression_analyses.get(expression)
        expected_analysis_type = WindowExpressionAnalysis
    if type(analysis) is not expected_analysis_type:
        raise _WindowExpressionLoweringError(
            expression,
            "validated window semantic facts",
        )
    assert analysis is not None
    if analysis.authored_expression is not expression:
        raise _WindowExpressionLoweringError(
            expression,
            "exact authored window analysis",
        )
    effective_expression = analysis.semantic_fact.expression
    if type(analysis) is AggregateWindowAnalysis:
        identity = effective_expression.identity
        callee = effective_expression.call.callee
        if (
            identity.namespace != ()
            or identity.role is not WindowFunctionRole.WINDOW_FUNCTION
            or type(callee) is not NameExpr
            or callee.name != identity.name
            or identity.name not in {"sum", "count", "avg", "min", "max"}
        ):
            raise _WindowExpressionLoweringError(
                expression, "supported aggregate window function identity"
            )

        def lower_aggregate_operand(operand: Expression) -> ExpressionIR:
            if type(operand) is NameExpr and operand.name in window_input_expressions:
                return window_input_expressions[operand.name]
            if isinstance(operand, BinaryExpr):
                return BinaryIR(
                    left=lower_aggregate_operand(operand.left),
                    operator=operand.operator,
                    right=lower_aggregate_operand(operand.right),
                    span=lower_span(operand.span),
                    value_type=lower_value_type(
                        semantic_model.expression_value_types[operand], semantic_model
                    ),
                )
            if isinstance(operand, UnaryExpr):
                return UnaryIR(
                    operator=operand.operator,
                    operand=lower_aggregate_operand(operand.operand),
                    span=lower_span(operand.span),
                    value_type=lower_value_type(
                        semantic_model.expression_value_types[operand], semantic_model
                    ),
                )
            if isinstance(operand, CallExpr):
                callee = _callee_name(operand)
                return CallIR(
                    callee=callee,
                    callee_symbol=(
                        SymbolId(SymbolNamespace.CALLABLE, callee)
                        if is_builtin_function_name(callee)
                        else None
                    ),
                    arguments=tuple(
                        lower_aggregate_operand(item) for item in operand.arguments
                    ),
                    span=lower_span(operand.span),
                    value_type=lower_value_type(
                        semantic_model.expression_value_types[operand], semantic_model
                    ),
                )
            return _lower_expr_node(
                operand,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=frozenset(),
                join_reads=join_reads,
                window_input_expressions=window_input_expressions,
            )

        validated_frame = analysis.validated_specification.frame
        if type(validated_frame) is not ValidatedFrame:
            raise _WindowExpressionLoweringError(expression, "aggregate window frame")
        result_value_type = analysis.semantic_fact.result.value_type
        if type(result_value_type) is not ValueType:
            raise _WindowExpressionLoweringError(expression, "aggregate window result")
        frame = (
            None
            if validated_frame.resolved.origin.value == "effective_default"
            else _lower_effective_window_frame(
                validated_frame.resolved, lower_aggregate_operand
            )
        )
        return AggregateWindowCallIR(
            span=lower_span(expression.span),
            value_type=lower_value_type(result_value_type, semantic_model),
            function=effective_expression.identity.name,
            arguments=tuple(
                lower_aggregate_operand(item)
                for item in effective_expression.call.arguments
            ),
            spec=WindowSpecIR(
                partition_by=tuple(
                    lower_aggregate_operand(item)
                    for item in effective_expression.spec.partition_by
                ),
                order_by=tuple(
                    _lower_window_order_item(item, lower_aggregate_operand)
                    for item in effective_expression.spec.order_by
                ),
                span=lower_span(effective_expression.spec.span),
                frame=frame,
            ),
            named_use=_lower_named_window_use(analysis, lower_aggregate_operand),
        )
    assert type(analysis) is WindowExpressionAnalysis
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
            join_reads=join_reads,
            window_input_expressions=window_input_expressions,
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
    analysis: WindowExpressionAnalysis | AggregateWindowAnalysis,
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
    join_reads: JoinReads | None = None,
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
            join_reads=join_reads,
            window_input_expressions=window_input_expressions,
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


class _AnyReads:
    """Checked local and outer reads of one scalar ANY predicate."""

    def __init__(
        self,
        info: AnyValueSemanticInfo,
        model: SemanticModel,
        parent: JoinReads | _AnyReads | None,
        field_qualifier: str | None,
    ) -> None:
        self.info = info
        self.model = model
        self.parent = parent
        if isinstance(parent, _AnyReads):
            self.aliases = parent.aliases
            self.outer = parent.outer
        else:
            self.outer = parent
            occupied = {
                read.binding
                for value in model.any_values.values()
                for read in value.field_reads.values()
            }
            if parent is not None:
                occupied.update(item.binding for item in parent.inputs)
            if field_qualifier is not None:
                occupied.add(field_qualifier)
            occupied.update(
                binding.name
                for value in model.any_values.values()
                if value.use.owner.let_clause is not None
                for binding in value.use.owner.let_clause.bindings
            )
            self.aliases = {}
            counter = 0
            for any_expression in model.any_values:
                while True:
                    counter += 1
                    alias = f"_pietto_value_{counter}"
                    if alias not in occupied:
                        occupied.add(alias)
                        break
                self.aliases[id(any_expression)] = alias

    def field_ref(
        self,
        expression: NameExpr | DottedNameExpr,
        *,
        span: SourceSpan,
        value_type: TypeRefIR,
    ) -> FieldRefIR | AnyFieldIR:
        read = self.info.field_reads.get(expression)
        if read is None:
            raise _LetExpansionLoweringError(
                expression, "resolved ANY field occurrence"
            )
        return self.capture_ref(expression, read, span=span)

    def capture_ref(
        self,
        expression: Expression,
        read: AnyFieldReadInfo,
        *,
        span: SourceSpan,
    ) -> FieldRefIR | AnyFieldIR:
        value_type = lower_value_type(read.value_type, self.model)
        relation = SymbolId(SymbolNamespace.RELATION, read.relation.name)
        if isinstance(read.occurrence, AnyExpr):
            scope: JoinReads | _AnyReads | None = self
            while (
                isinstance(scope, _AnyReads)
                and scope.info.use.expression is not read.occurrence
            ):
                scope = scope.parent
            binding = (
                self.aliases.get(id(read.occurrence))
                if isinstance(scope, _AnyReads)
                else None
            )
            if binding is None:
                raise _LetExpansionLoweringError(expression, "visible ANY binder")
            return AnyFieldIR(
                span=span,
                value_type=value_type,
                binding=binding,
                source_binding=read.binding,
                name=read.field_name,
                relation=relation,
            )
        owner = self.info.use.owner
        if read.occurrence is owner.from_clause:
            ordinal = 0
        else:
            positions = tuple(
                i
                for i, clause in enumerate(owner.join_clauses, 1)
                if clause is read.occurrence
            )
            if len(positions) != 1:
                raise _LetExpansionLoweringError(
                    expression, "visible outer input occurrence"
                )
            ordinal = positions[0]
        if self.outer is None:
            if ordinal != 0:
                raise _LetExpansionLoweringError(expression, "outer JOIN input")
            field = FieldId(owner=relation, name=read.field_name)
        else:
            if ordinal >= len(self.outer.inputs):
                raise _LetExpansionLoweringError(expression, "outer JOIN input ordinal")
            input_value = self.outer.inputs[ordinal]
            if input_value.binding != read.binding or input_value.target != relation:
                raise _LetExpansionLoweringError(expression, "exact outer JOIN input")
            field = FieldId(owner=relation, name=read.field_name, input=ordinal)
        return FieldRefIR(
            span=span,
            value_type=value_type,
            name=read.field_name,
            qualifier=(read.binding,),
            field=field,
        )


def _any_connector(iterator: SourceDef) -> ConnectorIR:
    connector = iterator.connector
    if not isinstance(connector, CallExpr):
        raise _LetExpansionLoweringError(
            iterator.connector, "static ANY source connector"
        )
    arguments: list[str | int | float | bool | None] = []
    for item in connector.arguments:
        if not isinstance(item, LiteralExpr):
            raise _LetExpansionLoweringError(
                item, "static ANY source connector argument"
            )
        arguments.append(item.value)
    return ConnectorIR(
        name=_callee_name(connector),
        arguments=tuple(arguments),
        span=lower_span(connector.span),
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
    join_reads: JoinReads | _AnyReads | None = None,
    window_input_expressions: Mapping[str, ExpressionIR] | None = None,
) -> ExpressionIR:
    """Recursively copy one expression into parser-independent IR."""

    window_inputs = window_input_expressions or {}
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

    if isinstance(expression, AnyExpr):
        info = semantic_model.any_values.get(expression)
        if info is None:
            raise _LetExpansionLoweringError(expression, "resolved ANY value facts")
        if info.use.expression is not expression:
            raise _LetExpansionLoweringError(expression, "exact ANY occurrence")
        reads = _AnyReads(info, semantic_model, join_reads, field_qualifier)
        iterator = info.iterator
        connector = (
            _any_connector(iterator) if isinstance(iterator, SourceDef) else None
        )
        predicate = _lower_expr_node(
            info.predicate,
            semantic_model,
            fields=fields,
            field_owner=field_owner,
            field_qualifier=field_qualifier,
            let_expansions=let_expansions,
            let_stack=let_stack,
            join_reads=reads,
            window_input_expressions=window_inputs,
        )
        captures = []
        for read in info.captures:
            matches = tuple(
                occurrence
                for value in semantic_model.any_values.values()
                for occurrence, candidate in value.field_reads.items()
                if candidate is read
            )
            if len(matches) != 1:
                raise _LetExpansionLoweringError(
                    expression, "exact ANY capture occurrence"
                )
            captures.append(
                reads.capture_ref(matches[0], read, span=lower_span(matches[0].span))
            )
        try:
            return ExistsIR(
                target=SymbolId(SymbolNamespace.RELATION, iterator.name),
                binding=reads.aliases[id(expression)],
                connector=connector,
                authored_span=lower_span(info.use.authored_expression.span),
                authored_occurrence=info.use.authored_expression.span.occurrence,
                current_occurrence=expression.span.occurrence,
                authored_context_span=lower_span(info.use.authored_context.span),
                context_span=lower_span(info.use.context.span),
                owner=SymbolId(SymbolNamespace.RELATION, info.use.owner.name),
                authored_join_count=info.use.authored_join_count,
                join_prefix_count=info.use.join_prefix_count,
                predicate=predicate,
                captures=tuple(captures),
                **common,
            )
        except ValueError as error:
            raise _LetExpansionLoweringError(
                expression, "checked ANY Bool value"
            ) from error
    if type(expression) is WindowExpr:
        return _lower_window_expr(
            expression,
            semantic_model,
            fields=fields,
            field_owner=field_owner,
            field_qualifier=field_qualifier,
            let_expansions=let_expansions,
            window_input_expressions=window_inputs,
            join_reads=None if isinstance(join_reads, _AnyReads) else join_reads,
        )
    if isinstance(expression, LiteralExpr):
        return LiteralIR(value=expression.value, **common)
    if isinstance(expression, (NameExpr, DottedNameExpr)) and isinstance(
        join_reads, _AnyReads
    ):
        if expression in join_reads.info.field_reads:
            return join_reads.field_ref(
                expression, span=lower_span(expression.span), value_type=value_type
            )
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
                join_reads=join_reads,
                window_input_expressions=window_inputs,
            )
        if join_reads is not None:
            return join_reads.field_ref(
                expression, span=lower_span(expression.span), value_type=value_type
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
        if join_reads is not None:
            return join_reads.field_ref(
                expression, span=lower_span(expression.span), value_type=value_type
            )
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
                        join_reads=join_reads,
                        window_input_expressions=window_inputs,
                    )
                    for argument in expression.arguments
                ),
                order_by=tuple(
                    OrderItemIR(
                        expression=_lower_expr_node(
                            item.expression,
                            semantic_model,
                            fields=fields,
                            field_owner=field_owner,
                            field_qualifier=field_qualifier,
                            let_expansions=let_expansions,
                            let_stack=let_stack,
                            join_reads=join_reads,
                            window_input_expressions=window_inputs,
                        ),
                        direction=OrderDirectionIR(
                            "ASC" if item.direction is None else item.direction.upper()
                        ),
                        span=lower_span(item.span),
                    )
                    for item in expression.aggregate_order_by
                ),
                **common,
            )
        callee_symbol = None
        if is_builtin_function_name(callee):
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
                    join_reads=join_reads,
                    window_input_expressions=window_inputs,
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
                join_reads=join_reads,
                window_input_expressions=window_inputs,
            ),
            **common,
        )
    if isinstance(expression, ConditionalExpr):
        return ConditionalIR(
            when_true=_lower_expr_node(
                expression.when_true,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
                join_reads=join_reads,
                window_input_expressions=window_inputs,
            ),
            condition=_lower_expr_node(
                expression.condition,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
                join_reads=join_reads,
                window_input_expressions=window_inputs,
            ),
            when_false=_lower_expr_node(
                expression.when_false,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
                join_reads=join_reads,
                window_input_expressions=window_inputs,
            ),
            **common,
        )
    if isinstance(expression, MembershipExpr):
        return MembershipIR(
            value=_lower_expr_node(
                expression.value,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
                join_reads=join_reads,
                window_input_expressions=window_inputs,
            ),
            options=tuple(
                _lower_expr_node(
                    option,
                    semantic_model,
                    fields=fields,
                    field_owner=field_owner,
                    field_qualifier=field_qualifier,
                    let_expansions=let_expansions,
                    let_stack=let_stack,
                    join_reads=join_reads,
                    window_input_expressions=window_inputs,
                )
                for option in expression.options
            ),
            negated=expression.negated,
            **common,
        )
    if isinstance(expression, CastExpr):
        return CastIR(
            value=_lower_expr_node(
                expression.value,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
                join_reads=join_reads,
                window_input_expressions=window_inputs,
            ),
            target=lower_canonical_type_ref(expression.target, semantic_model),
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
                join_reads=join_reads,
                window_input_expressions=window_inputs,
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
                join_reads=join_reads,
                window_input_expressions=window_inputs,
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
                join_reads=join_reads,
                window_input_expressions=window_inputs,
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
                join_reads=join_reads,
                window_input_expressions=window_inputs,
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
                join_reads=join_reads,
                window_input_expressions=window_inputs,
            ),
            lower=_lower_expr_node(
                expression.lower,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
                join_reads=join_reads,
                window_input_expressions=window_inputs,
            ),
            upper=_lower_expr_node(
                expression.upper,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
                let_expansions=let_expansions,
                let_stack=let_stack,
                join_reads=join_reads,
                window_input_expressions=window_inputs,
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
                join_reads=join_reads,
                window_input_expressions=window_inputs,
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
    if function_name == "string_agg":
        return let_expansions
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
    if function_name == "string_agg" and len(expression.arguments) == 2:
        argument_type = semantic_model.expression_value_types.get(
            expression.arguments[0]
        )
        expected = (
            None
            if argument_type is None
            else semantic_aggregate_result_value_type(
                function_name,
                _canonical_value_type(argument_type, semantic_model.type_expansions),
            )
        )
    elif not expression.arguments:
        expected = semantic_aggregate_result_value_type(function_name)
    elif len(expression.arguments) == 1:
        argument_type = semantic_model.expression_value_types.get(
            expression.arguments[0]
        )
        expected = (
            None
            if argument_type is None
            else semantic_aggregate_result_value_type(
                function_name,
                _canonical_value_type(argument_type, semantic_model.type_expansions),
            )
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
