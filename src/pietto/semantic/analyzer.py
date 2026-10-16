"""Semantic analysis entry point."""

from __future__ import annotations

from pietto.ast_nodes import SetRelationDef
from pietto._flat_relational_admission import syntax_diagnostics
from pietto._syntax_admission import unadmitted_syntax_diagnostics

from collections.abc import Iterator, Mapping
from dataclasses import fields, replace
from typing import TYPE_CHECKING

from pietto.ast_nodes import (
    AuthoredJoinKind,
    BetweenExpr,
    BinaryExpr,
    CastExpr,
    CallExpr,
    CheckDef,
    ConditionalExpr,
    ComparisonExpr,
    ConstraintDef,
    Definition,
    DeriveDef,
    DottedNameExpr,
    EnumDef,
    Expression,
    FieldDef,
    FromClause,
    IsNullExpr,
    IndexDef,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    Node,
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
    WindowSpec,
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
from pietto.semantic.let_bindings import (
    analyze_relation_let_bindings,
    let_expansion_diagnostics,
)
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
from pietto.semantic.relationship_metadata import (
    check_relationship_conditions,
    check_relationship_metadata,
)
from pietto.semantic.relations import check_join_references, resolve_relation_inputs
from pietto.semantic.shapes import check_field_derives, check_shape_structures
from pietto.semantic.source_connectors import (
    check_source_connectors,
    check_table_names,
)
from pietto.semantic.satisfying import check_satisfying_clauses
from pietto.semantic.sources import check_sources
from pietto.semantic.predicate_checks import check_predicates
from pietto.semantic.type_aliases import expand_type_aliases

if TYPE_CHECKING:
    from pietto.semantic.window_semantics import (
        ResolvedNamedWindowNamespace,
        WindowExpressionAnalysis,
    )

_DECIMAL_PRECISION_MAX = 65


def analyze(
    script: Script,
    *,
    mode_override: CheckMode | None = None,
) -> SemanticResult:
    """Build the incremental semantic model and ordered diagnostics."""

    mode = mode_override or CheckMode.CHECKED
    try:
        mode = mode_override or _mode_from_script(script)
        unadmitted = unadmitted_syntax_diagnostics(script)
        if unadmitted:
            return SemanticResult(
                model=SemanticModel(mode=mode), diagnostics=unadmitted
            )
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
        if isinstance(definition, EnumDef):
            diagnostics.extend(_duplicate_enum_member_diagnostics(definition))
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
        _record_type_expression(
            type_expr,
            type_symbols=type_symbols,
            type_resolutions=type_resolutions,
            type_nullability=type_nullability,
            decimal_precision_scales=decimal_precision_scales,
            diagnostics=diagnostics,
            mode=mode,
            report_implicit_nullability=True,
        )
    for type_expr in _iter_cast_target_type_expressions(script):
        _record_type_expression(
            type_expr,
            type_symbols=type_symbols,
            type_resolutions=type_resolutions,
            type_nullability=type_nullability,
            decimal_precision_scales=decimal_precision_scales,
            diagnostics=diagnostics,
            mode=mode,
            report_implicit_nullability=False,
        )

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
    diagnostics.extend(check_join_references(script, relation_symbols))
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
        named_window_namespaces,
    ) = _analyze_relation_schema_expressions(
        script,
        mode=mode,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
        type_expansions=type_expansions,
    )
    diagnostics.extend(schema_diagnostics)
    diagnostics.extend(
        check_relationship_conditions(
            script,
            relationships,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
            type_expansions=type_expansions,
        )
    )
    expression_value_types, expression_diagnostics = type_shape_predicates(
        script,
        type_resolutions=type_resolutions,
        type_expansions=type_expansions,
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
    connector_diagnostics = check_source_connectors(script, expression_value_types)
    diagnostics.extend(connector_diagnostics)
    diagnostics.extend(
        check_table_names(
            script, (*connector_expression_diagnostics, *connector_diagnostics)
        )
    )
    diagnostics.extend(check_predicates(script, expression_value_types))
    result_predicates, satisfying_diagnostics = check_satisfying_clauses(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        relation_let_expressions=_relation_let_expressions_for_satisfying(
            let_scopes,
        ),
        type_expansions=type_expansions,
        record_unknown=True,
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

    diagnostics.extend(
        diagnostic
        for definition in script.definitions
        for diagnostic in syntax_diagnostics(definition)
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
            named_window_namespaces=named_window_namespaces,
            result_predicates=result_predicates,
            let_scopes=let_scopes,
            relationships=relationships,
        ),
        diagnostics=tuple(
            sorted(
                _explain_join_binding_fields(
                    script,
                    diagnostics,
                    {
                        name: (
                            source_row_schemas.get(definition)
                            if isinstance(definition, SourceDef)
                            else relation_row_schemas.get(definition)
                        )
                        for name, definition in relation_symbols.items()
                        if isinstance(definition, (SourceDef, TableDef, QueryDef))
                    },
                ),
                key=_diagnostic_order,
            )
        ),
    )


def _explain_join_binding_fields(
    script: Script,
    diagnostics: list[Diagnostic],
    relation_schemas: Mapping[str, RowSchema | None],
) -> list[Diagnostic]:
    """Say why a single-file JOIN binding field is unknown; keep code and span.

    Only a field the JOIN target has, on a binding a project exposes.
    """

    names: dict[SourceLocation, str] = {}
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        # A project exposes the fields of every JOIN binding but SEMI and ANTI;
        # a binding name written twice has no single target and gets no hint.
        written = [clause.target_binding_name for clause in definition.join_clauses]
        bindings = {
            clause.target_binding_name: relation_schemas.get(
                clause.target_relation_name
            )
            for clause in definition.join_clauses
            if clause.kind not in (AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI)
            and clause.target_binding_name != definition.from_clause.source_name
            and written.count(clause.target_binding_name) == 1
        }
        pending: list[object] = [definition] if bindings else []
        while pending:
            value = pending.pop()
            if type(value) is tuple:
                pending.extend(value)
            elif (
                type(value) is DottedNameExpr
                and len(value.parts) == 2
                and (schema := bindings.get(value.parts[0])) is not None
                and not schema.is_unknown
                and value.parts[1] in schema.fields
            ):
                span = value.span
                location = SourceLocation(
                    path=span.path,
                    line=span.line,
                    column=span.column,
                    end_line=span.end_line,
                    end_column=span.end_column,
                )
                names[location] = ".".join(value.parts)
            elif isinstance(value, Node):
                pending.extend(getattr(value, field.name) for field in fields(value))
    return [
        replace(
            diagnostic,
            message=(
                f"{diagnostic.message}; JOIN binding fields are not available in "
                "single-file mode (use an EXPLICIT_MODULES project)"
            ),
        )
        if diagnostic.code == "PIE-S2102"
        and diagnostic.location in names
        and diagnostic.message == f"Unknown field: {names[diagnostic.location]}"
        else diagnostic
        for diagnostic in diagnostics
    ]


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
    if isinstance(expression, ConditionalExpr):
        return (expression.when_true, expression.condition, expression.when_false)
    if isinstance(expression, MembershipExpr):
        return (expression.value, *expression.options)
    if isinstance(expression, CastExpr):
        return (expression.value,)
    if isinstance(expression, BinaryExpr):
        return (expression.left, expression.right)
    if isinstance(expression, ComparisonExpr):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    if isinstance(expression, (LiteralExpr, NameExpr, DottedNameExpr, WindowExpr)):
        return ()
    raise AssertionError(f"Unsupported expression: {type(expression).__name__}")


def _analyze_relation_schema_expressions(
    script: Script,
    *,
    mode: CheckMode,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    cyclic_relations: set[DerivedRelation],
    type_expansions: Mapping[TypeExpr, ResolvedType],
) -> tuple[
    dict[DerivedRelation, RowSchema],
    list[Diagnostic],
    dict[Expression, ValueType],
    list[Diagnostic],
    dict[DerivedRelation, LetScopeSemanticInfo],
    dict[WindowExpr, WindowExpressionAnalysis],
    dict[DerivedRelation, ResolvedNamedWindowNamespace],
]:
    """Refine relation schemas from computed projection expression types."""

    relation_row_schemas, _ = propagate_relation_schemas(
        script,
        mode=mode,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
        type_expansions=type_expansions,
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
                type_expansions=type_expansions,
            )
        )
        temporary_value_types, _, _, _ = type_relation_expressions(
            script,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
            relation_let_value_types={
                definition: scope.value_types
                for definition, scope in temporary_let_scopes.items()
            },
            type_expansions=type_expansions,
        )
        temporary_value_types.update(temporary_let_value_types)
        refined_schemas, _ = propagate_relation_schemas(
            script,
            mode=mode,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            cyclic_relations=cyclic_relations,
            expression_value_types=temporary_value_types,
            type_expansions=type_expansions,
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
        type_expansions=type_expansions,
    )
    (
        relation_value_types,
        relation_expression_diagnostics,
        window_expression_analyses,
        named_window_namespaces,
    ) = type_relation_expressions(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        relation_let_value_types={
            definition: scope.value_types for definition, scope in let_scopes.items()
        },
        type_expansions=type_expansions,
        let_diagnostics=let_diagnostics,
    )
    relation_value_types.update(let_value_types)
    relation_expression_diagnostics.extend(let_diagnostics)
    expansion_diagnostics = [
        diagnostic
        for definition, scope in let_scopes.items()
        for diagnostic in let_expansion_diagnostics(definition, scope.value_types)
    ]
    # A key over the let inlining limit already has that error: no PIE-S2380.
    over_limit = {diagnostic.location for diagnostic in expansion_diagnostics}
    relation_expression_diagnostics[:] = [
        diagnostic
        for diagnostic in relation_expression_diagnostics
        if not (diagnostic.code == "PIE-S2380" and diagnostic.location in over_limit)
    ]
    relation_expression_diagnostics.extend(expansion_diagnostics)
    final_schemas, schema_diagnostics = propagate_relation_schemas(
        script,
        mode=mode,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
        expression_value_types=relation_value_types,
        type_expansions=type_expansions,
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
        named_window_namespaces,
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
    if isinstance(definition, (SourceDef, TableDef, QueryDef, SetRelationDef)):
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


def _duplicate_enum_member_diagnostics(definition: EnumDef) -> list[Diagnostic]:
    """Report each repeated member name once at the enum declaration.

    Members carry no spans of their own.
    """

    seen: set[str] = set()
    repeated: list[str] = []
    for member in definition.members:
        if member in seen and member not in repeated:
            repeated.append(member)
        seen.add(member)
    span = definition.span
    return [
        Diagnostic(
            code="PIE-S2001",
            severity=Severity.ERROR,
            message=f"Duplicate member name in enum {definition.name}: {member}",
            location=SourceLocation(
                path=span.path,
                line=span.line,
                column=span.column,
                end_line=span.end_line,
                end_column=span.end_column,
            ),
        )
        for member in repeated
    ]


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


def _iter_cast_target_type_expressions(script: Script) -> Iterator[TypeExpr]:
    """Yield cast targets without applying declaration-nullability policy."""

    for definition in script.definitions:
        if isinstance(definition, TypeDef):
            yield from _cast_targets_in_type_arguments(definition.base)
            for ensure in definition.ensures:
                yield from _cast_targets_in_expression(ensure.expression)
        elif isinstance(definition, (ConstraintDef, DeriveDef)):
            for parameter in definition.parameters:
                yield from _cast_targets_in_type_arguments(parameter.type)
            yield from _cast_targets_in_type_arguments(definition.return_type)
            yield from _cast_targets_in_expression(definition.body)
        elif isinstance(definition, ShapeDef):
            for item in definition.items:
                if isinstance(item, FieldDef):
                    yield from _cast_targets_in_type_arguments(item.type_expr)
                    if item.derive_expression is not None:
                        yield from _cast_targets_in_expression(item.derive_expression)
                    for ensure in item.ensure_clauses:
                        yield from _cast_targets_in_expression(ensure.expression)
                elif isinstance(item, CheckDef):
                    yield from _cast_targets_in_expression(item.expression)
                elif isinstance(item, IndexDef) and item.predicate is not None:
                    yield from _cast_targets_in_expression(item.predicate)
        elif isinstance(definition, SourceDef):
            yield from _cast_targets_in_expression(definition.connector)
        elif isinstance(definition, (TableDef, QueryDef)):
            yield from _relation_cast_targets(definition)
    for relationship in script.relationships:
        if relationship.base_match is not None:
            yield from _cast_targets_in_expression(relationship.base_match.expression)


def _cast_targets_in_type_arguments(type_expr: TypeExpr) -> Iterator[TypeExpr]:
    """Yield casts written in one declaration type's value arguments."""

    for argument in type_expr.arguments:
        yield from _cast_targets_in_expression(argument.value)


def _record_type_expression(
    type_expr: TypeExpr,
    *,
    type_symbols: dict[str, Definition],
    type_resolutions: dict[TypeExpr, ResolvedType],
    type_nullability: dict[TypeExpr, EffectiveNullability],
    decimal_precision_scales: dict[TypeExpr, DecimalPrecisionScale],
    diagnostics: list[Diagnostic],
    mode: CheckMode,
    report_implicit_nullability: bool,
) -> None:
    """Resolve one declared or cast-target type without weakening validation."""

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
    if report_implicit_nullability:
        implicit_diagnostic = _implicit_nullability_diagnostic(type_expr, mode)
        if implicit_diagnostic is not None:
            diagnostics.append(implicit_diagnostic)


def _relation_cast_targets(definition: TableDef | QueryDef) -> Iterator[TypeExpr]:
    """Yield casts from one relation body in authored clause order."""

    if definition.let_clause is not None:
        for binding in definition.let_clause.bindings:
            yield from _cast_targets_in_expression(binding.expression)
    if definition.where_clause is not None:
        yield from _cast_targets_in_expression(definition.where_clause.expression)
    if definition.group_by_clause is not None:
        for item in definition.group_by_clause.items:
            yield from _cast_targets_in_expression(item.key)
    for item in definition.select_items:
        yield from _cast_targets_in_expression(item.expression)
    if definition.satisfying_clause is not None:
        yield from _cast_targets_in_expression(definition.satisfying_clause.expression)
    if definition.qualify_clause is not None:
        yield from _cast_targets_in_expression(definition.qualify_clause.expression)
    if definition.order_by_clause is not None:
        for item in definition.order_by_clause.items:
            yield from _cast_targets_in_expression(item.expression)
    if definition.limit_clause is not None:
        yield from _cast_targets_in_expression(definition.limit_clause.expression)
    for join in definition.join_clauses:
        if join.on_clause is not None:
            yield from _cast_targets_in_expression(join.on_clause.expression)
    for named_window in definition.named_windows:
        if named_window.spec is not None:
            yield from _window_spec_cast_targets(named_window.spec)


def _cast_targets_in_expression(expression: Expression) -> Iterator[TypeExpr]:
    """Yield every cast target while preserving expression source order."""

    if isinstance(expression, CastExpr):
        yield from _cast_targets_in_expression(expression.value)
        yield expression.target
        return
    if isinstance(expression, WindowExpr):
        yield from _cast_targets_in_expression(expression.call)
        yield from _window_spec_cast_targets(expression.spec)
        return
    for child in _expression_children(expression):
        yield from _cast_targets_in_expression(child)


def _window_spec_cast_targets(spec: WindowSpec) -> Iterator[TypeExpr]:
    """Yield casts in a parsed window spec without widening its semantics."""

    for expression in spec.partition_by:
        yield from _cast_targets_in_expression(expression)
    for item in spec.order_by:
        yield from _cast_targets_in_expression(item.expression)
    frame = spec.frame
    for bound in (frame.start, frame.end):
        if bound is not None and bound.offset is not None:
            yield from _cast_targets_in_expression(bound.offset)


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
