"""Semantic IR construction entry point."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    CheckDef,
    ComparisonExpr,
    ConstraintDef,
    DeriveDef,
    DottedNameExpr,
    EnumDef,
    Expression,
    FieldDef,
    IndexDef,
    LiteralExpr,
    NameExpr,
    Node,
    Parameter,
    QueryDef,
    Script,
    SelectItem,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
    TypeExpr,
    UniqueDef,
)
from pietto.errors import Diagnostic
from pietto.ir.diagnostics import missing_semantic_fact_diagnostic
from pietto.ir.lowering import (
    lower_canonical_type_ref,
    lower_expr,
    lower_group_key_ref,
    lower_value_type,
    lower_row_schema,
    lower_span,
    lower_type_ref,
)
from pietto.ir.model import (
    AggregateCallIR,
    BinaryIR,
    ComparisonIR,
    ConnectorIR,
    ConstraintIR,
    DefinitionIR,
    DeriveIR,
    EnumIR,
    ExpressionIR,
    FilterIR,
    FieldRefIR,
    IrResult,
    LimitIR,
    LiteralIR,
    NullabilityIR,
    OrderDirectionIR,
    OrderItemIR,
    ParameterIR,
    ProjectionIR,
    RelationIR,
    RelationKindIR,
    RelationSourceIR,
    ResultPredicateIR,
    RowFieldIR,
    ScriptIR,
    ShapeCheckIR,
    ShapeFieldDeriveIR,
    ShapeFieldIR,
    ShapeIndexIR,
    ShapeIR,
    ShapeItemIR,
    ShapeUniqueIR,
    SourceIR,
    SourceSpan,
    StaticValue,
    SymbolId,
    SymbolNamespace,
    TypeIR,
    TypeRefIR,
)
from pietto.semantic import RowField, RowSchema, SemanticModel
from pietto.semantic.model import SatisfyingResultPredicateInfo

DerivedRelation = TableDef | QueryDef
RelationDefinition = SourceDef | TableDef | QueryDef
CallableDefinition = ConstraintDef | DeriveDef


def build_ir(
    script: Script,
    semantic_model: SemanticModel,
) -> IrResult:
    """Lower supported declarations from an already analyzed script."""

    definitions: list[DefinitionIR] = []
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        try:
            lowered = _lower_definition(definition, semantic_model)
        except _MissingSemanticFact as error:
            diagnostics.append(
                missing_semantic_fact_diagnostic(error.node, error.message)
            )
            continue
        if lowered is not None:
            definitions.append(lowered)

    if diagnostics:
        return IrResult(ir=None, diagnostics=tuple(diagnostics))
    return IrResult(ir=ScriptIR(definitions=tuple(definitions)), diagnostics=())


def _lower_definition(
    definition: Node,
    semantic_model: SemanticModel,
) -> DefinitionIR | None:
    """Lower one supported declaration and skip later-slice definitions."""

    if isinstance(definition, TypeDef):
        return _lower_type(definition, semantic_model)
    if isinstance(definition, EnumDef):
        return EnumIR(
            symbol=_symbol(SymbolNamespace.TYPE, definition.name),
            name=definition.name,
            members=definition.members,
            span=lower_span(definition.span),
        )
    if isinstance(definition, ShapeDef):
        return _lower_shape(definition, semantic_model)
    if isinstance(definition, (ConstraintDef, DeriveDef)):
        return _lower_callable(definition, semantic_model)
    if isinstance(definition, SourceDef):
        return _lower_source(definition, semantic_model)
    if isinstance(definition, (TableDef, QueryDef)):
        return _lower_relation(definition, semantic_model)
    return None


def _lower_type(
    definition: TypeDef,
    semantic_model: SemanticModel,
) -> TypeIR:
    """Lower one type definition after checking required semantic facts."""

    _require_type_facts(definition.base, semantic_model)
    return TypeIR(
        symbol=_symbol(SymbolNamespace.TYPE, definition.name),
        name=definition.name,
        declared_type=lower_type_ref(definition.base, semantic_model),
        canonical_type=lower_canonical_type_ref(definition.base, semantic_model),
        span=lower_span(definition.span),
    )


def _lower_shape(
    definition: ShapeDef,
    semantic_model: SemanticModel,
) -> ShapeIR:
    """Lower fields and existing semantically checked shape metadata."""

    symbol = _symbol(SymbolNamespace.TYPE, definition.name)
    field_environment = _shape_fields(definition, semantic_model)
    items = tuple(
        _lower_shape_item(
            item,
            semantic_model,
            fields=field_environment,
            field_owner=symbol,
        )
        for item in definition.items
    )
    return ShapeIR(
        symbol=symbol,
        name=definition.name,
        fields=tuple(item for item in items if isinstance(item, ShapeFieldIR)),
        items=items,
        span=lower_span(definition.span),
    )


def _lower_shape_item(
    item: FieldDef | CheckDef | UniqueDef | IndexDef,
    semantic_model: SemanticModel,
    *,
    fields: Mapping[str, RowField],
    field_owner: SymbolId,
) -> ShapeItemIR:
    """Lower one shape item while preserving mixed source order."""

    if isinstance(item, FieldDef):
        _require_type_facts(item.type_expr, semantic_model)
        type_ref = lower_type_ref(item.type_expr, semantic_model)
        derive = None
        if item.derive_expression is not None:
            expression = _require_lowered_expression(
                item.derive_expression,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
            )
            derive = ShapeFieldDeriveIR(
                expression=expression,
                span=lower_span(item.derive_expression.span),
            )
        return ShapeFieldIR(
            name=item.name,
            type_ref=type_ref,
            nullability=NullabilityIR(type_ref.nullability),
            derive=derive,
            span=lower_span(item.span),
        )
    if isinstance(item, CheckDef):
        return ShapeCheckIR(
            name=item.name,
            expression=_require_lowered_expression(
                item.expression,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
            ),
            span=lower_span(item.span),
        )
    if isinstance(item, UniqueDef):
        return ShapeUniqueIR(
            name=item.name,
            fields=item.field_names,
            span=lower_span(item.span),
        )

    predicate = None
    if item.predicate is not None:
        predicate = _require_lowered_expression(
            item.predicate,
            semantic_model,
            fields=fields,
            field_owner=field_owner,
        )
    return ShapeIndexIR(
        name=item.name,
        fields=item.field_names,
        predicate=predicate,
        span=lower_span(item.span),
    )


def _shape_fields(
    definition: ShapeDef,
    semantic_model: SemanticModel,
) -> Mapping[str, RowField]:
    """Rebuild the analyzed shape field environment for expression lowering."""

    fields: dict[str, RowField] = {}
    for field in definition.fields:
        if field.name in fields:
            continue
        _require_type_facts(field.type_expr, semantic_model)
        fields[field.name] = RowField(
            name=field.name,
            resolved_type=semantic_model.type_resolutions[field.type_expr],
            nullability=semantic_model.type_nullability[field.type_expr],
            definition=field,
        )
    return fields


def _lower_callable(
    definition: CallableDefinition,
    semantic_model: SemanticModel,
) -> ConstraintIR | DeriveIR:
    """Lower one semantically checked top-level callable declaration."""

    symbol = _symbol(SymbolNamespace.CALLABLE, definition.name)
    parameters = tuple(
        _lower_parameter(parameter, semantic_model)
        for parameter in definition.parameters
    )
    _require_type_facts(definition.return_type, semantic_model)
    body = _require_lowered_expression(
        definition.body,
        semantic_model,
        fields=_callable_fields(definition, semantic_model),
        field_owner=symbol,
    )
    return_type = lower_type_ref(definition.return_type, semantic_model)
    span = lower_span(definition.span)
    if isinstance(definition, ConstraintDef):
        return ConstraintIR(
            symbol=symbol,
            name=definition.name,
            parameters=parameters,
            return_type=return_type,
            body=body,
            span=span,
        )
    return DeriveIR(
        symbol=symbol,
        name=definition.name,
        parameters=parameters,
        return_type=return_type,
        body=body,
        span=span,
    )


def _lower_parameter(
    parameter: Parameter,
    semantic_model: SemanticModel,
) -> ParameterIR:
    """Lower one callable parameter using existing semantic type facts."""

    _require_type_facts(parameter.type, semantic_model)
    return ParameterIR(
        name=parameter.name,
        type_ref=lower_type_ref(parameter.type, semantic_model),
        span=lower_span(parameter.span),
    )


def _callable_fields(
    definition: CallableDefinition,
    semantic_model: SemanticModel,
) -> Mapping[str, RowField]:
    """Rebuild the analyzed parameter environment for expression lowering."""

    fields: dict[str, RowField] = {}
    for parameter in definition.parameters:
        if parameter.name in fields:
            continue
        _require_type_facts(parameter.type, semantic_model)
        fields[parameter.name] = RowField(
            name=parameter.name,
            resolved_type=semantic_model.type_expansions[parameter.type],
            nullability=semantic_model.type_nullability[parameter.type],
        )
    return fields


def _lower_source(
    definition: SourceDef,
    semantic_model: SemanticModel,
) -> SourceIR:
    """Lower one source using its analyzed row schema and static connector."""

    schema = semantic_model.source_row_schemas.get(definition)
    if schema is None:
        raise _MissingSemanticFact(definition, "source row schema")

    shape_symbol = None
    if definition.shape_name is not None:
        shape = semantic_model.type_symbols.get(definition.shape_name)
        if not isinstance(shape, ShapeDef):
            raise _MissingSemanticFact(definition, "resolved source shape")
        shape_symbol = _symbol(SymbolNamespace.TYPE, shape.name)

    return SourceIR(
        symbol=_symbol(SymbolNamespace.RELATION, definition.name),
        name=definition.name,
        shape_symbol=shape_symbol,
        row_schema=lower_row_schema(schema, semantic_model),
        connector=_lower_connector(definition),
        span=lower_span(definition.span),
    )


def _lower_connector(definition: SourceDef) -> ConnectorIR:
    """Copy a semantically validated connector call as static metadata."""

    connector = definition.connector
    if not isinstance(connector, CallExpr):
        raise _MissingSemanticFact(definition, "static source connector call")

    arguments: list[StaticValue] = []
    for argument in connector.arguments:
        if not isinstance(argument, LiteralExpr):
            raise _MissingSemanticFact(definition, "static connector argument")
        arguments.append(argument.value)

    if isinstance(connector.callee, NameExpr):
        name = connector.callee.name
    elif isinstance(connector.callee, DottedNameExpr):
        name = ".".join(connector.callee.parts)
    else:  # pragma: no cover - CallExpr constrains this union.
        raise _MissingSemanticFact(definition, "static connector name")

    return ConnectorIR(
        name=name,
        arguments=tuple(arguments),
        span=lower_span(connector.span),
    )


def _lower_relation(
    definition: DerivedRelation,
    semantic_model: SemanticModel,
) -> RelationIR:
    """Lower one minimal table or query from existing semantic facts."""

    target = semantic_model.from_resolutions.get(definition.from_clause)
    if target is None:
        raise _MissingSemanticFact(definition.from_clause, "resolved relation input")
    schema = semantic_model.relation_row_schemas.get(definition)
    if schema is None:
        raise _MissingSemanticFact(definition, "relation row schema")

    input_schema = _relation_schema(target, semantic_model)
    target_symbol = _symbol(SymbolNamespace.RELATION, target.name)
    row_schema = lower_row_schema(schema, semantic_model)
    output_fields = {field.name: field for field in row_schema.fields}
    let_expansions = _let_expansions(definition, semantic_model)

    filter_ir = None
    if definition.where_clause is not None:
        expression = _require_lowered_expression(
            definition.where_clause.expression,
            semantic_model,
            fields=input_schema.fields,
            field_owner=target_symbol,
            field_qualifier=target.name,
            let_expansions=let_expansions,
        )
        filter_ir = FilterIR(
            expression=expression,
            span=lower_span(definition.where_clause.span),
        )

    projections = tuple(
        _lower_projection(
            item,
            semantic_model,
            input_schema=input_schema,
            target_symbol=target_symbol,
            output_fields=output_fields,
            let_expansions=let_expansions,
        )
        for item in definition.select_items
    )
    group_keys = _lower_group_keys(
        definition,
        semantic_model,
        input_schema=input_schema,
        target_symbol=target_symbol,
        field_qualifier=target.name,
        let_expansions=let_expansions,
    )
    order_by = _lower_order_by(
        definition,
        semantic_model,
        input_schema=input_schema,
        target_symbol=target_symbol,
        projections=projections,
        group_keys=group_keys,
        let_expansions=let_expansions,
    )
    limit = _lower_limit(definition)
    result_predicate = _lower_result_predicate(
        definition,
        semantic_model,
        input_schema=input_schema,
        target_symbol=target_symbol,
    )
    return RelationIR(
        symbol=_symbol(SymbolNamespace.RELATION, definition.name),
        name=definition.name,
        kind=(
            RelationKindIR.TABLE
            if isinstance(definition, TableDef)
            else RelationKindIR.QUERY
        ),
        source=RelationSourceIR(
            target=target_symbol,
            name=target.name,
            span=lower_span(definition.from_clause.span),
        ),
        filter=filter_ir,
        projections=projections,
        row_schema=row_schema,
        span=lower_span(definition.span),
        order_by=order_by,
        limit=limit,
        group_keys=group_keys,
        result_predicate=result_predicate,
    )


def _lower_group_keys(
    definition: DerivedRelation,
    semantic_model: SemanticModel,
    *,
    input_schema: RowSchema,
    target_symbol: SymbolId,
    field_qualifier: str,
    let_expansions: Mapping[str, Expression],
) -> tuple[FieldRefIR, ...]:
    """Lower accepted unique GROUP BY keys from semantic row facts."""

    clause = definition.group_by_clause
    if clause is None or input_schema.is_unknown:
        return ()

    group_keys: list[FieldRefIR] = []
    seen_identities: set[str] = set()
    for item in clause.items:
        effective_key = _effective_group_key_expression(
            item.key,
            let_expansions=let_expansions,
            let_stack=frozenset(),
        )
        field = _group_key_field(
            effective_key,
            input_schema=input_schema,
            field_qualifier=field_qualifier,
        )
        if field is None:
            continue
        identity = field.name
        if identity in seen_identities:
            continue
        seen_identities.add(identity)
        group_keys.append(
            lower_group_key_ref(
                effective_key,
                semantic_model,
                field=field,
                field_owner=target_symbol,
            )
        )
    return tuple(group_keys)


def _effective_group_key_expression(
    expression: NameExpr | DottedNameExpr,
    *,
    let_expansions: Mapping[str, Expression],
    let_stack: frozenset[str],
) -> NameExpr | DottedNameExpr:
    if not isinstance(expression, NameExpr):
        return expression
    if expression.name not in let_expansions:
        return expression
    if expression.name in let_stack:
        return expression

    expanded = let_expansions[expression.name]
    if isinstance(expanded, DottedNameExpr):
        return expanded
    if isinstance(expanded, NameExpr):
        return _effective_group_key_expression(
            expanded,
            let_expansions=let_expansions,
            let_stack=let_stack | frozenset((expression.name,)),
        )
    return expression


def _group_key_field(
    expression: NameExpr | DottedNameExpr,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
) -> RowField | None:
    """Resolve one syntactic GROUP BY key against the sole relation input."""

    if isinstance(expression, NameExpr):
        return input_schema.fields.get(expression.name)
    if len(expression.parts) == 2 and expression.parts[0] == field_qualifier:
        return input_schema.fields.get(expression.parts[1])
    return None


def _lower_order_by(
    definition: DerivedRelation,
    semantic_model: SemanticModel,
    *,
    input_schema: RowSchema,
    target_symbol: SymbolId,
    projections: tuple[ProjectionIR, ...],
    group_keys: tuple[FieldRefIR, ...],
    let_expansions: Mapping[str, Expression],
) -> tuple[OrderItemIR, ...]:
    """Lower input-scope or grouped result-scope sorting expressions."""

    clause = definition.order_by_clause
    if clause is None:
        return ()
    if definition.group_by_clause is not None:
        return _lower_grouped_order_by(
            definition,
            projections=projections,
            group_keys=group_keys,
        )
    return tuple(
        OrderItemIR(
            expression=_require_lowered_expression(
                item.expression,
                semantic_model,
                fields=input_schema.fields,
                field_owner=target_symbol,
                field_qualifier=target_symbol.name,
                let_expansions=let_expansions,
            ),
            direction=_lower_order_direction(item.direction),
            span=lower_span(item.span),
        )
        for item in clause.items
    )


def _lower_grouped_order_by(
    definition: DerivedRelation,
    *,
    projections: tuple[ProjectionIR, ...],
    group_keys: tuple[FieldRefIR, ...],
) -> tuple[OrderItemIR, ...]:
    clause = definition.order_by_clause
    if clause is None:
        return ()
    output_expressions = _grouped_order_output_expressions(
        projections,
        group_keys=group_keys,
    )
    order_by: list[OrderItemIR] = []
    for item in clause.items:
        if not isinstance(item.expression, NameExpr):
            raise _MissingSemanticFact(item.expression, "grouped order output")
        expression = output_expressions.get(item.expression.name)
        if expression is None:
            raise _MissingSemanticFact(item.expression, "grouped order output")
        order_by.append(
            OrderItemIR(
                expression=expression,
                direction=_lower_order_direction(item.direction),
                span=lower_span(item.span),
            )
        )
    return tuple(order_by)


def _grouped_order_output_expressions(
    projections: tuple[ProjectionIR, ...],
    *,
    group_keys: tuple[FieldRefIR, ...],
) -> dict[str, ExpressionIR]:
    group_key_fields = {key.field for key in group_keys if key.field is not None}
    output_expressions: dict[str, ExpressionIR] = {}
    for projection in projections:
        if projection.name is None or projection.name in output_expressions:
            continue
        expression = projection.expression
        if isinstance(expression, AggregateCallIR):
            output_expressions[projection.name] = expression
            continue
        if (
            isinstance(expression, FieldRefIR)
            and expression.field is not None
            and expression.field in group_key_fields
        ):
            output_expressions[projection.name] = expression
    return output_expressions


def _lower_order_direction(direction: str | None) -> OrderDirectionIR:
    return OrderDirectionIR("ASC" if direction is None else direction.upper())


def _lower_limit(definition: DerivedRelation) -> LimitIR | None:
    """Copy one semantically validated static limit into relation IR."""

    clause = definition.limit_clause
    if clause is None:
        return None
    expression = clause.expression
    if (
        not isinstance(expression, LiteralExpr)
        or type(expression.value) is not int
        or not 0 <= expression.value <= 9_223_372_036_854_775_807
    ):
        raise _MissingSemanticFact(expression, "validated static relation limit")
    return LimitIR(
        value=expression.value,
        span=lower_span(expression.span),
    )


def _lower_result_predicate(
    definition: DerivedRelation,
    semantic_model: SemanticModel,
    *,
    input_schema: RowSchema,
    target_symbol: SymbolId,
) -> ResultPredicateIR | None:
    clause = definition.satisfying_clause
    if clause is None:
        return None
    predicate_info = semantic_model.result_predicates.get(definition)
    if predicate_info is None:
        raise _MissingSemanticFact(clause, "validated satisfying result predicate")
    return ResultPredicateIR(
        expression=_lower_satisfying_expression(
            clause.expression,
            predicate_info,
            semantic_model,
            input_schema=input_schema,
            target_symbol=target_symbol,
        ),
        span=lower_span(clause.span),
    )


def _lower_satisfying_expression(
    expression: Expression,
    predicate_info: SatisfyingResultPredicateInfo,
    semantic_model: SemanticModel,
    *,
    input_schema: RowSchema,
    target_symbol: SymbolId,
) -> ExpressionIR:
    if isinstance(expression, NameExpr):
        output_expression = predicate_info.output_expressions.get(expression.name)
        if output_expression is None:
            raise _MissingSemanticFact(expression, "satisfying output expression")
        return _require_lowered_expression(
            output_expression,
            semantic_model,
            fields=input_schema.fields,
            field_owner=target_symbol,
            field_qualifier=target_symbol.name,
        )

    span, value_type = _satisfying_expression_common(
        expression,
        predicate_info,
        semantic_model,
    )
    if isinstance(expression, LiteralExpr):
        return LiteralIR(
            value=expression.value,
            span=span,
            value_type=value_type,
        )
    if isinstance(expression, ComparisonExpr):
        return ComparisonIR(
            left=_lower_satisfying_expression(
                expression.left,
                predicate_info,
                semantic_model,
                input_schema=input_schema,
                target_symbol=target_symbol,
            ),
            operator=expression.operator,
            right=_lower_satisfying_expression(
                expression.right,
                predicate_info,
                semantic_model,
                input_schema=input_schema,
                target_symbol=target_symbol,
            ),
            span=span,
            value_type=value_type,
        )
    if isinstance(expression, BinaryExpr) and expression.operator in {"and", "or"}:
        return BinaryIR(
            left=_lower_satisfying_expression(
                expression.left,
                predicate_info,
                semantic_model,
                input_schema=input_schema,
                target_symbol=target_symbol,
            ),
            operator=expression.operator,
            right=_lower_satisfying_expression(
                expression.right,
                predicate_info,
                semantic_model,
                input_schema=input_schema,
                target_symbol=target_symbol,
            ),
            span=span,
            value_type=value_type,
        )
    raise _MissingSemanticFact(expression, "supported satisfying expression")


def _satisfying_expression_common(
    expression: Expression,
    predicate_info: SatisfyingResultPredicateInfo,
    semantic_model: SemanticModel,
) -> tuple[SourceSpan, TypeRefIR]:
    value_type = predicate_info.expression_value_types.get(expression)
    if value_type is None:
        raise _MissingSemanticFact(expression, "satisfying expression value type")
    return lower_span(expression.span), lower_value_type(value_type, semantic_model)


def _relation_schema(
    definition: RelationDefinition,
    semantic_model: SemanticModel,
) -> RowSchema:
    """Return the existing semantic row schema for a relation input."""

    if isinstance(definition, SourceDef):
        schema = semantic_model.source_row_schemas.get(definition)
    else:
        schema = semantic_model.relation_row_schemas.get(definition)
    if schema is None:
        raise _MissingSemanticFact(definition, "input relation row schema")
    return schema


def _let_expansions(
    definition: DerivedRelation,
    semantic_model: SemanticModel,
) -> Mapping[str, Expression]:
    """Return admitted relation-local let bindings for row-level IR expansion."""

    let_scope = semantic_model.let_scopes.get(definition)
    if let_scope is None:
        return {}
    admitted_names = set(let_scope.value_types)
    return {
        binding.name: binding.expression
        for binding in let_scope.bindings
        if binding.name in admitted_names
    }


def _lower_projection(
    item: SelectItem,
    semantic_model: SemanticModel,
    *,
    input_schema: RowSchema,
    target_symbol: SymbolId,
    output_fields: Mapping[str, RowFieldIR],
    let_expansions: Mapping[str, Expression],
) -> ProjectionIR:
    """Lower one projection using existing semantic output-name behavior."""

    expression = _require_lowered_expression(
        item.expression,
        semantic_model,
        fields=input_schema.fields,
        field_owner=target_symbol,
        field_qualifier=target_symbol.name,
        let_expansions=let_expansions,
    )
    output_name = _projection_output_name(item)
    output_field = output_fields.get(output_name) if output_name is not None else None
    type_ref = output_field.type_ref if output_field is not None else None
    return ProjectionIR(
        name=output_name,
        expression=expression,
        type_ref=type_ref,
        span=lower_span(item.span),
    )


def _projection_output_name(item: SelectItem) -> str | None:
    """Mirror the stable projection names established by semantic analysis."""

    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _require_lowered_expression(
    expression: Expression,
    semantic_model: SemanticModel,
    *,
    fields: Mapping[str, RowField],
    field_owner: SymbolId,
    field_qualifier: str | None = None,
    let_expansions: Mapping[str, Expression] | None = None,
) -> ExpressionIR:
    """Lower a relation expression or convert its diagnostic into IR failure."""

    result = lower_expr(
        expression,
        semantic_model,
        fields=fields,
        field_owner=field_owner,
        field_qualifier=field_qualifier,
        let_expansions=let_expansions,
    )
    if result.expression is None:
        raise _MissingSemanticFact(expression, "expression value type")
    return result.expression


def _require_type_facts(
    type_expr: TypeExpr,
    semantic_model: SemanticModel,
) -> None:
    """Require all Phase 2 facts consumed by type metadata lowering."""

    if type_expr not in semantic_model.type_resolutions:
        raise _MissingSemanticFact(type_expr, "type resolution")
    if type_expr not in semantic_model.type_expansions:
        raise _MissingSemanticFact(type_expr, "canonical type expansion")
    if type_expr not in semantic_model.type_nullability:
        raise _MissingSemanticFact(type_expr, "effective nullability")


def _symbol(namespace: SymbolNamespace, name: str) -> SymbolId:
    """Build a stable IR symbol identity."""

    return SymbolId(namespace=namespace, name=name)


class _MissingSemanticFact(Exception):
    """Internal control flow for expected IR prerequisite failures."""

    def __init__(self, node: Node, message: str) -> None:
        super().__init__(message)
        self.node = node
        self.message = message
