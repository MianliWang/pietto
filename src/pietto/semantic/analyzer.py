"""Semantic analysis entry point."""

from __future__ import annotations

from collections.abc import Iterator, Mapping

from pietto.ast_nodes import (
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    Expression,
    FromClause,
    Nullability,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
    TypeExpr,
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
    EffectiveNullability,
    ResolvedType,
    RowSchema,
    SemanticModel,
    SemanticResult,
    TypeKind,
    ValueType,
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

    diagnostics.extend(_unsupported_let_clause_diagnostics(script))

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
        implicit_diagnostic = _implicit_nullability_diagnostic(type_expr, mode)
        if implicit_diagnostic is not None:
            diagnostics.append(implicit_diagnostic)

    type_expansions, alias_diagnostics = expand_type_aliases(
        script,
        type_symbols=type_symbols,
        type_resolutions=type_resolutions,
    )
    diagnostics.extend(alias_diagnostics)
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

    return SemanticResult(
        model=SemanticModel(
            mode=mode,
            type_symbols=type_symbols,
            callable_symbols=callable_symbols,
            relation_symbols=relation_symbols,
            type_resolutions=type_resolutions,
            type_expansions=type_expansions,
            type_nullability=type_nullability,
            source_row_schemas=source_row_schemas,
            from_resolutions=from_resolutions,
            relation_row_schemas=relation_row_schemas,
            expression_value_types=expression_value_types,
            result_predicates=result_predicates,
            relationships=relationships,
        ),
        diagnostics=tuple(sorted(diagnostics, key=_diagnostic_order)),
    )


RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef


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
        temporary_value_types, _ = type_relation_expressions(
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
    relation_value_types, relation_expression_diagnostics = type_relation_expressions(
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


def _unsupported_let_clause_diagnostics(script: Script) -> list[Diagnostic]:
    """Fail closed until let binding IR/SQL lowering is implemented."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        let_clause = definition.let_clause
        if let_clause is None:
            continue
        span = let_clause.span
        diagnostics.append(
            Diagnostic(
                code="PIE-S2328",
                severity=Severity.ERROR,
                message=(
                    "`let:` bindings are semantically validated but IR/SQL "
                    "lowering is not supported yet."
                ),
                location=SourceLocation(
                    path=span.path,
                    line=span.line,
                    column=span.column,
                    end_line=span.end_line,
                    end_column=span.end_column,
                ),
            )
        )
    return diagnostics


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
    """Resolve one type name without alias expansion or argument validation."""

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
