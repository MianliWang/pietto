"""Semantic analysis entry point."""

from __future__ import annotations

from collections.abc import Iterator

from pietto.ast_nodes import (
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
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
from pietto.semantic.catalog import BUILTIN_TYPE_NAMES
from pietto.semantic.expressions import type_relation_expressions
from pietto.semantic.model import (
    CheckMode,
    EffectiveNullability,
    ResolvedType,
    SemanticModel,
    SemanticResult,
    TypeKind,
)
from pietto.semantic.relation_cycles import check_relation_cycles
from pietto.semantic.relation_schemas import propagate_relation_schemas
from pietto.semantic.relations import resolve_relation_inputs
from pietto.semantic.shapes import check_shape_structures
from pietto.semantic.sources import check_sources
from pietto.semantic.where_checks import check_where_clauses


def analyze(
    script: Script,
    *,
    mode_override: CheckMode | None = None,
) -> SemanticResult:
    """Build the incremental semantic model and ordered diagnostics."""

    mode = mode_override or _mode_from_script(script)
    type_symbols: dict[str, Definition] = {}
    callable_symbols: dict[str, Definition] = {}
    relation_symbols: dict[str, Definition] = {}
    type_resolutions: dict[TypeExpr, ResolvedType] = {}
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

    for type_expr in _iter_type_expressions(script):
        resolved_type = _resolve_type(type_expr, type_symbols)
        type_resolutions[type_expr] = resolved_type
        type_nullability[type_expr] = _effective_nullability(type_expr)

        if resolved_type.kind is TypeKind.UNKNOWN:
            diagnostics.append(_unknown_type_diagnostic(type_expr))
        implicit_diagnostic = _implicit_nullability_diagnostic(type_expr, mode)
        if implicit_diagnostic is not None:
            diagnostics.append(implicit_diagnostic)

    diagnostics.extend(check_shape_structures(script))
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
    relation_row_schemas, schema_diagnostics = propagate_relation_schemas(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
    )
    diagnostics.extend(schema_diagnostics)
    expression_value_types, expression_diagnostics = type_relation_expressions(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
    )
    diagnostics.extend(expression_diagnostics)
    diagnostics.extend(check_where_clauses(script, expression_value_types))

    return SemanticResult(
        model=SemanticModel(
            mode=mode,
            type_symbols=type_symbols,
            callable_symbols=callable_symbols,
            relation_symbols=relation_symbols,
            type_resolutions=type_resolutions,
            type_nullability=type_nullability,
            source_row_schemas=source_row_schemas,
            from_resolutions=from_resolutions,
            relation_row_schemas=relation_row_schemas,
            expression_value_types=expression_value_types,
        ),
        diagnostics=tuple(sorted(diagnostics, key=_diagnostic_order)),
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
