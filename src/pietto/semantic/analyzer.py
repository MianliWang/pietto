"""Semantic analysis entry point."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    ConstraintDef,
    Definition,
    DeriveDef,
    DottedNameExpr,
    EnumDef,
    Expression,
    FromClause,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    Nullability,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
    TypeExpr,
    UnaryExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.callables import (
    check_callable_bodies,
    check_callable_signatures,
)
from pietto.semantic.catalog import BUILTIN_TYPE_NAMES
from pietto.semantic.expressions import (
    type_callable_bodies,
    type_relation_expressions,
    type_shape_field_derives,
    type_shape_predicates,
    type_source_connector_arguments,
)
from pietto.semantic.field_derive_cycles import check_field_derive_cycles
from pietto.semantic.let_bindings import analyze_relation_let_bindings
from pietto.semantic.model import (
    CheckMode,
    DecimalPrecisionScale,
    EffectiveNullability,
    LetScopeSemanticInfo,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    SemanticResult,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.relation_cycles import check_relation_cycles
from pietto.semantic.relation_limits import check_relation_limits
from pietto.semantic.relation_schemas import propagate_relation_schemas
from pietto.semantic.relationship_metadata import check_relationship_metadata
from pietto.semantic.relations import resolve_relation_inputs
from pietto.semantic.shapes import check_field_derives, check_shape_structures
from pietto.semantic.source_connectors import check_source_connectors
from pietto.semantic.satisfying import check_satisfying_clauses
from pietto.semantic.sources import check_sources
from pietto.semantic.predicate_checks import check_predicates
from pietto.semantic.type_aliases import expand_type_aliases

if TYPE_CHECKING:
    from pietto.semantic.window_semantics import WindowExpressionAnalysis

_DECIMAL_PRECISION_MAX = 38


def analyze(
    script: Script,
    *,
    mode_override: CheckMode | None = None,
) -> SemanticResult:
    """Build the incremental semantic model and ordered diagnostics."""

    mode = mode_override or CheckMode.CHECKED
    try:
        mode = mode_override or _mode_from_script(script)
        return _analyze(script, mode=mode)
    except RecursionError:
        span = script.span
        return SemanticResult(
            model=SemanticModel(mode=mode),
            diagnostics=(
                Diagnostic(
                    code="PIE-S2006",
                    severity=Severity.ERROR,
                    message=(
                        "Semantic analysis recursion limit exceeded while "
                        "processing source."
                    ),
                    location=SourceLocation(
                        path=span.path,
                        line=span.line,
                        column=span.column,
                        end_line=span.end_line,
                        end_column=span.end_column,
                    ),
                ),
            ),
        )


def _analyze(script: Script, *, mode: CheckMode) -> SemanticResult:
    """Implement semantic analysis inside the public recursion boundary."""

    type_symbols: dict[str, Definition] = {}
    callable_symbols: dict[str, Definition] = {}
    relation_symbols: dict[str, Definition] = {}
    type_resolutions: dict[TypeExpr, ResolvedType] = {}
    type_expansions: dict[TypeExpr, ResolvedType] = {}
    type_nullability: dict[TypeExpr, EffectiveNullability] = {}
    decimal_precision_scales: dict[TypeExpr, DecimalPrecisionScale] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        namespace_name, namespace = _namespace_for(
            definition,
            type_symbols=type_symbols,
            callable_symbols=callable_symbols,
            relation_symbols=relation_symbols,
        )
        if definition.name in namespace:
            diagnostics.append(_duplicate_diagnostic(definition, namespace_name))
            continue
        namespace[definition.name] = definition

    relationships, relationship_diagnostics = check_relationship_metadata(
        script,
        relation_symbols,
    )
    diagnostics.extend(relationship_diagnostics)

    for type_expr in _iter_type_expressions(script):
        resolved_type = _resolve_type(type_expr, type_symbols)
        type_resolutions[type_expr] = resolved_type
        type_nullability[type_expr] = _effective_nullability(type_expr)

        if resolved_type.kind is TypeKind.UNKNOWN:
            diagnostics.append(_unknown_type_diagnostic(type_expr))
        decimal_precision_scale, decimal_diagnostic = _decimal_precision_scale_fact(
            type_expr
        )
        if decimal_precision_scale is not None:
            decimal_precision_scales[type_expr] = decimal_precision_scale
        if decimal_diagnostic is not None:
            diagnostics.append(decimal_diagnostic)
        implicit_diagnostic = _implicit_nullability_diagnostic(type_expr, mode)
        if implicit_diagnostic is not None:
            diagnostics.append(implicit_diagnostic)

    type_expansions, alias_diagnostics = expand_type_aliases(
        script,
        type_symbols=type_symbols,
        type_resolutions=type_resolutions,
    )
    diagnostics.extend(alias_diagnostics)
    decimal_precision_scales.update(
        _propagate_decimal_precision_scale_aliases(
            type_resolutions=type_resolutions,
            decimal_precision_scales=decimal_precision_scales,
        )
    )
    diagnostics.extend(check_callable_signatures(script, type_expansions))
    diagnostics.extend(check_shape_structures(script))
    diagnostics.extend(check_field_derive_cycles(script))
    source_row_schemas, source_diagnostics = check_sources(
        script,
        mode=mode,
        type_symbols=type_symbols,
        type_resolutions=type_resolutions,
        type_nullability=type_nullability,
    )
    diagnostics.extend(source_diagnostics)
    from_resolutions, relation_diagnostics = resolve_relation_inputs(
        script,
        relation_symbols,
    )
    diagnostics.extend(relation_diagnostics)
    cyclic_relations, cycle_diagnostics = check_relation_cycles(
        script,
        from_resolutions,
    )
    diagnostics.extend(cycle_diagnostics)
    (
        relation_row_schemas,
        schema_diagnostics,
        relation_value_types,
        relation_expression_diagnostics,
        let_scopes,
        window_expression_analyses,
    ) = _analyze_relation_schema_expressions(
        script,
        mode=mode,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
    )
    diagnostics.extend(schema_diagnostics)
    expression_value_types, expression_diagnostics = type_shape_predicates(
        script,
        type_resolutions=type_resolutions,
        type_nullability=type_nullability,
    )
    connector_value_types, connector_expression_diagnostics = (
        type_source_connector_arguments(script)
    )
    expression_value_types.update(connector_value_types)
    expression_diagnostics.extend(connector_expression_diagnostics)
    field_derive_value_types, field_derive_diagnostics = type_shape_field_derives(
        script,
        type_expansions=type_expansions,
        type_nullability=type_nullability,
    )
    expression_value_types.update(field_derive_value_types)
    expression_diagnostics.extend(field_derive_diagnostics)
    callable_value_types, callable_expression_diagnostics = type_callable_bodies(
        script,
        type_expansions=type_expansions,
        type_nullability=type_nullability,
    )
    expression_value_types.update(callable_value_types)
    expression_diagnostics.extend(callable_expression_diagnostics)
    expression_value_types.update(relation_value_types)
    expression_diagnostics.extend(relation_expression_diagnostics)
    diagnostics.extend(expression_diagnostics)
    diagnostics.extend(check_relation_limits(script))
    diagnostics.extend(check_source_connectors(script, expression_value_types))
    diagnostics.extend(check_predicates(script, expression_value_types))
    result_predicates, satisfying_diagnostics = check_satisfying_clauses(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        relation_let_expressions=_relation_let_expressions_for_satisfying(
            let_scopes,
        ),
    )
    diagnostics.extend(satisfying_diagnostics)
    diagnostics.extend(
        check_callable_bodies(
            script,
            type_expansions=type_expansions,
            expression_value_types=expression_value_types,
        )
    )
    diagnostics.extend(
        check_field_derives(
            script,
            type_expansions=type_expansions,
            expression_value_types=expression_value_types,
        )
    )
    decimal_expression_precision_scales = _decimal_expression_precision_scales(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        expression_value_types=expression_value_types,
        decimal_precision_scales=decimal_precision_scales,
    )

    return SemanticResult(
        model=SemanticModel(
            mode=mode,
            type_symbols=type_symbols,
            callable_symbols=callable_symbols,
            relation_symbols=relation_symbols,
            type_resolutions=type_resolutions,
            type_expansions=type_expansions,
            type_nullability=type_nullability,
            decimal_precision_scales=decimal_precision_scales,
            decimal_expression_precision_scales=decimal_expression_precision_scales,
            source_row_schemas=source_row_schemas,
            from_resolutions=from_resolutions,
            relation_row_schemas=relation_row_schemas,
            expression_value_types=expression_value_types,
            window_expression_analyses=window_expression_analyses,
            result_predicates=result_predicates,
            let_scopes=let_scopes,
            relationships=relationships,
        ),
        diagnostics=tuple(sorted(diagnostics, key=_diagnostic_order)),
    )


RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef


def _decimal_expression_precision_scales(
    script: Script,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
    expression_value_types: Mapping[Expression, ValueType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
) -> dict[Expression, DecimalPrecisionScale]:
    """Collect private Decimal precision facts for safe direct field leaves."""

    facts: dict[Expression, DecimalPrecisionScale] = {}
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        input_schema = _relation_input_schema(
            definition,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
        )
        if definition.let_clause is not None:
            for binding in definition.let_clause.bindings:
                _collect_decimal_expression_precision_scales(
                    binding.expression,
                    input_schema=input_schema,
                    field_qualifier=definition.from_clause.source_name,
                    expression_value_types=expression_value_types,
                    decimal_precision_scales=decimal_precision_scales,
                    facts=facts,
                )
        if definition.where_clause is not None:
            _collect_decimal_expression_precision_scales(
                definition.where_clause.expression,
                input_schema=input_schema,
                field_qualifier=definition.from_clause.source_name,
                expression_value_types=expression_value_types,
                decimal_precision_scales=decimal_precision_scales,
                facts=facts,
            )
        for item in definition.select_items:
            _collect_decimal_expression_precision_scales(
                item.expression,
                input_schema=input_schema,
                field_qualifier=definition.from_clause.source_name,
                expression_value_types=expression_value_types,
                decimal_precision_scales=decimal_precision_scales,
                facts=facts,
            )
        if definition.order_by_clause is not None:
            for item in definition.order_by_clause.items:
                _collect_decimal_expression_precision_scales(
                    item.expression,
                    input_schema=input_schema,
                    field_qualifier=definition.from_clause.source_name,
                    expression_value_types=expression_value_types,
                    decimal_precision_scales=decimal_precision_scales,
                    facts=facts,
                )
    return facts


def _relation_input_schema(
    definition: DerivedRelation,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> RowSchema:
    """Return a relation input schema for private post-analysis fact collection."""

    target = from_resolutions.get(definition.from_clause)
    if isinstance(target, SourceDef):
        return source_row_schemas[target]
    if isinstance(target, (TableDef, QueryDef)):
        return relation_row_schemas[target]
    return RowSchema(is_unknown=True)


def _collect_decimal_expression_precision_scales(
    expression: Expression,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
    expression_value_types: Mapping[Expression, ValueType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
    facts: dict[Expression, DecimalPrecisionScale],
) -> None:
    """Walk expression children while assigning facts only to direct fields."""

    direct_fact = _direct_decimal_expression_precision_scale(
        expression,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        expression_value_types=expression_value_types,
        decimal_precision_scales=decimal_precision_scales,
    )
    if direct_fact is not None:
        facts[expression] = direct_fact
        return

    for child in _expression_children(expression):
        _collect_decimal_expression_precision_scales(
            child,
            input_schema=input_schema,
            field_qualifier=field_qualifier,
            expression_value_types=expression_value_types,
            decimal_precision_scales=decimal_precision_scales,
            facts=facts,
        )


def _direct_decimal_expression_precision_scale(
    expression: Expression,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
    expression_value_types: Mapping[Expression, ValueType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
) -> DecimalPrecisionScale | None:
    """Return a Decimal precision fact only for direct Decimal field references."""

    row_field = _direct_expression_row_field(
        expression,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
    )
    if row_field is None or row_field.definition is None:
        return None

    expression_type = expression_value_types.get(expression)
    if expression_type is None or expression_type.kind is not ValueTypeKind.KNOWN:
        return None
    if (
        expression_type.resolved_type.kind is not TypeKind.BUILTIN
        or expression_type.resolved_type.name != "Decimal"
    ):
        return None

    type_expr = row_field.definition.type_expr
    if type_expr.name != "Decimal":
        return None
    return decimal_precision_scales.get(type_expr)


def _direct_expression_row_field(
    expression: Expression,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
) -> RowField | None:
    if input_schema.is_unknown:
        return None
    if isinstance(expression, NameExpr):
        return input_schema.fields.get(expression.name)
    if (
        isinstance(expression, DottedNameExpr)
        and len(expression.parts) == 2
        and expression.parts[0] == field_qualifier
    ):
        return input_schema.fields.get(expression.parts[1])
    return None


def _expression_children(expression: Expression) -> tuple[Expression, ...]:
    if isinstance(expression, CallExpr):
        return expression.arguments
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, BinaryExpr):
        return (expression.left, expression.right)
    if isinstance(expression, ComparisonExpr):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    return ()


def _analyze_relation_schema_expressions(
    script: Script,
    *,
    mode: CheckMode,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    cyclic_relations: set[DerivedRelation],
) -> tuple[
    dict[DerivedRelation, RowSchema],
    list[Diagnostic],
    dict[Expression, ValueType],
    list[Diagnostic],
    dict[DerivedRelation, LetScopeSemanticInfo],
    dict[WindowExpr, WindowExpressionAnalysis],
]:
    """Refine relation schemas from computed projection expression types."""

    relation_row_schemas, _ = propagate_relation_schemas(
        script,
        mode=mode,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
    )
    derived_relation_count = sum(
        isinstance(definition, (TableDef, QueryDef))
        for definition in script.definitions
    )
    iteration_limit = derived_relation_count + 1
    stabilized = False

    for _ in range(iteration_limit):
        temporary_let_scopes, temporary_let_value_types, _ = (
            analyze_relation_let_bindings(
                script.definitions,
                from_resolutions=from_resolutions,
                source_row_schemas=source_row_schemas,
                relation_row_schemas=relation_row_schemas,
            )
        )
        temporary_value_types, _, _ = type_relation_expressions(
            script,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
            relation_let_value_types={
                definition: scope.value_types
                for definition, scope in temporary_let_scopes.items()
            },
        )
        temporary_value_types.update(temporary_let_value_types)
        refined_schemas, _ = propagate_relation_schemas(
            script,
            mode=mode,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            cyclic_relations=cyclic_relations,
            expression_value_types=temporary_value_types,
        )
        if _relation_schema_fingerprint(refined_schemas) == (
            _relation_schema_fingerprint(relation_row_schemas)
        ):
            relation_row_schemas = refined_schemas
            stabilized = True
            break
        relation_row_schemas = refined_schemas

    let_scopes, let_value_types, let_diagnostics = analyze_relation_let_bindings(
        script.definitions,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
    )
    (
        relation_value_types,
        relation_expression_diagnostics,
        window_expression_analyses,
    ) = type_relation_expressions(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        relation_let_value_types={
            definition: scope.value_types for definition, scope in let_scopes.items()
        },
    )
    relation_value_types.update(let_value_types)
    relation_expression_diagnostics.extend(let_diagnostics)
    final_schemas, schema_diagnostics = propagate_relation_schemas(
        script,
        mode=mode,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
        expression_value_types=relation_value_types,
    )
    if stabilized:
        relation_row_schemas = final_schemas

    return (
        relation_row_schemas,
        schema_diagnostics,
        relation_value_types,
        relation_expression_diagnostics,
        let_scopes,
        window_expression_analyses,
    )


def _relation_schema_fingerprint(
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> tuple[
    tuple[
        str,
        bool,
        tuple[tuple[str, str, TypeKind, EffectiveNullability], ...],
    ],
    ...,
]:
    """Compare relation schemas by stable semantic facts instead of identity."""

    return tuple(
        (
            definition.name,
            schema.is_unknown,
            tuple(
                (
                    name,
                    field.resolved_type.name,
                    field.resolved_type.kind,
                    field.nullability,
                )
                for name, field in schema.fields.items()
            ),
        )
        for definition, schema in relation_row_schemas.items()
    )


def _relation_let_expressions_for_satisfying(
    let_scopes: Mapping[DerivedRelation, LetScopeSemanticInfo],
) -> dict[DerivedRelation, dict[str, Expression]]:
    """Return admitted relation-local let expressions for satisfying checks."""

    return {
        definition: {
            binding.name: binding.expression
            for binding in scope.bindings
            if binding.name in scope.value_types
        }
        for definition, scope in let_scopes.items()
    }


def _mode_from_script(script: Script) -> CheckMode:
    """Select the declared mode or the checked default."""

    if script.header is None or script.header.mode is None:
        return CheckMode.CHECKED
    return CheckMode(script.header.mode)


def _namespace_for(
    definition: Definition,
    *,
    type_symbols: dict[str, Definition],
    callable_symbols: dict[str, Definition],
    relation_symbols: dict[str, Definition],
) -> tuple[str, dict[str, Definition]]:
    """Return the namespace assigned to a top-level definition."""

    if isinstance(definition, (TypeDef, EnumDef, ShapeDef)):
        return "type", type_symbols
    if isinstance(definition, (ConstraintDef, DeriveDef)):
        return "callable", callable_symbols
    if isinstance(definition, (SourceDef, TableDef, QueryDef)):
        return "relation", relation_symbols
    raise AssertionError(f"Unsupported definition: {type(definition).__name__}")


def _duplicate_diagnostic(
    definition: Definition,
    namespace_name: str,
) -> Diagnostic:
    """Report a duplicate at the later definition's complete source span."""

    span = definition.span
    return Diagnostic(
        code="PIE-S2001",
        severity=Severity.ERROR,
        message=(
            f"Duplicate symbol name in {namespace_name} namespace: {definition.name}"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _iter_type_expressions(script: Script) -> Iterator[TypeExpr]:
    """Yield supported type expressions in source order."""

    for definition in script.definitions:
        if isinstance(definition, TypeDef):
            yield definition.base
        elif isinstance(definition, (ConstraintDef, DeriveDef)):
            for parameter in definition.parameters:
                yield parameter.type
            yield definition.return_type
        elif isinstance(definition, ShapeDef):
            for field in definition.fields:
                yield field.type_expr


def _resolve_type(
    type_expr: TypeExpr,
    type_symbols: dict[str, Definition],
) -> ResolvedType:
    """Resolve one type name without alias expansion."""

    if type_expr.name in BUILTIN_TYPE_NAMES:
        return ResolvedType(name=type_expr.name, kind=TypeKind.BUILTIN)

    definition = type_symbols.get(type_expr.name)
    if isinstance(definition, TypeDef):
        kind = TypeKind.TYPE_ALIAS
    elif isinstance(definition, EnumDef):
        kind = TypeKind.ENUM
    elif isinstance(definition, ShapeDef):
        kind = TypeKind.SHAPE
    else:
        return ResolvedType(name=type_expr.name, kind=TypeKind.UNKNOWN)
    return ResolvedType(
        name=type_expr.name,
        kind=kind,
        definition=definition,
    )


def _decimal_precision_scale_fact(
    type_expr: TypeExpr,
) -> tuple[DecimalPrecisionScale | None, Diagnostic | None]:
    """Validate and return internal Decimal precision-scale facts."""

    if type_expr.name != "Decimal":
        return None, None

    arguments = type_expr.arguments
    if not arguments:
        return None, None

    if len(arguments) != 2 or any(argument.name is not None for argument in arguments):
        return (
            None,
            _invalid_decimal_type_arguments_diagnostic(
                type_expr,
                "Decimal precision-scale requires exactly two positional integer literal arguments",
            ),
        )

    precision = _integer_literal_value(arguments[0].value)
    scale = _integer_literal_value(arguments[1].value)
    if precision is None or scale is None:
        return (
            None,
            _invalid_decimal_type_arguments_diagnostic(
                type_expr,
                "Decimal precision and scale must be integer literals",
            ),
        )

    if precision < 1 or precision > _DECIMAL_PRECISION_MAX:
        return (
            None,
            _invalid_decimal_type_arguments_diagnostic(
                type_expr,
                f"Decimal precision must be an integer from 1 to {_DECIMAL_PRECISION_MAX}",
            ),
        )

    if scale < 0 or scale > precision:
        return (
            None,
            _invalid_decimal_type_arguments_diagnostic(
                type_expr,
                "Decimal scale must be an integer from 0 to precision",
            ),
        )

    return DecimalPrecisionScale(precision=precision, scale=scale), None


def _propagate_decimal_precision_scale_aliases(
    *,
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
) -> dict[TypeExpr, DecimalPrecisionScale]:
    """Copy Decimal precision-scale facts to safe alias-use type expressions."""

    propagated: dict[TypeExpr, DecimalPrecisionScale] = {}
    for type_expr, resolved_type in type_resolutions.items():
        if type_expr in decimal_precision_scales:
            continue
        if resolved_type.kind is not TypeKind.TYPE_ALIAS:
            continue
        fact = _decimal_precision_scale_for_alias_target(
            resolved_type,
            type_resolutions=type_resolutions,
            decimal_precision_scales=decimal_precision_scales,
        )
        if fact is not None:
            propagated[type_expr] = fact
    return propagated


def _decimal_precision_scale_for_alias_target(
    resolved_type: ResolvedType,
    *,
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
) -> DecimalPrecisionScale | None:
    """Resolve an alias target to existing Decimal precision-scale facts."""

    visited: set[TypeDef] = set()
    current = resolved_type.definition
    while isinstance(current, TypeDef) and current not in visited:
        visited.add(current)
        fact = decimal_precision_scales.get(current.base)
        if fact is not None:
            return fact
        direct = type_resolutions.get(current.base)
        if direct is None or direct.kind is not TypeKind.TYPE_ALIAS:
            return None
        current = direct.definition
    return None


def _integer_literal_value(expression: Expression) -> int | None:
    if isinstance(expression, LiteralExpr) and type(expression.value) is int:
        return expression.value
    return None


def _effective_nullability(type_expr: TypeExpr) -> EffectiveNullability:
    """Map parsed nullability syntax to the initial semantic state."""

    if type_expr.nullability is Nullability.NULLABLE:
        return EffectiveNullability.NULLABLE
    if type_expr.nullability is Nullability.NOT_NULL:
        return EffectiveNullability.NON_NULL
    return EffectiveNullability.UNKNOWN


def _unknown_type_diagnostic(type_expr: TypeExpr) -> Diagnostic:
    """Report an unresolved type name at its complete type-expression span."""

    return _type_diagnostic(
        type_expr,
        code="PIE-S2002",
        severity=Severity.ERROR,
        message=f"Unknown type: {type_expr.name}",
    )


def _invalid_decimal_type_arguments_diagnostic(
    type_expr: TypeExpr,
    message: str,
) -> Diagnostic:
    """Report invalid Decimal precision-scale arguments."""

    return _type_diagnostic(
        type_expr,
        code="PIE-S2004",
        severity=Severity.ERROR,
        message=message,
    )


def _implicit_nullability_diagnostic(
    type_expr: TypeExpr,
    mode: CheckMode,
) -> Diagnostic | None:
    """Apply the mode-sensitive policy for omitted nullability."""

    if type_expr.nullability is not Nullability.IMPLICIT or mode is CheckMode.LOOSE:
        return None
    severity = Severity.WARNING if mode is CheckMode.CHECKED else Severity.ERROR
    return _type_diagnostic(
        type_expr,
        code="PIE-S2005",
        severity=severity,
        message=(
            f"Implicit nullability for type {type_expr.name}; "
            "use `nullable` or `not null`"
        ),
    )


def _type_diagnostic(
    type_expr: TypeExpr,
    *,
    code: str,
    severity: Severity,
    message: str,
) -> Diagnostic:
    """Create a semantic diagnostic from a type-expression span."""

    span = type_expr.span
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _diagnostic_order(diagnostic: Diagnostic) -> tuple[str, int, int, str]:
    """Order diagnostics deterministically by source position and code."""

    location = diagnostic.location
    return (
        location.path or "",
        location.line,
        location.column,
        diagnostic.code,
    )
