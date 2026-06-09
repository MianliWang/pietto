"""Semantic checks and row schemas for source definitions."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import Definition, Script, ShapeDef, SourceDef, TypeExpr
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.catalog import BUILTIN_TYPE_NAMES
from pietto.semantic.model import (
    CheckMode,
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
)


def check_sources(
    script: Script,
    *,
    mode: CheckMode,
    type_symbols: Mapping[str, Definition],
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> tuple[dict[SourceDef, RowSchema], list[Diagnostic]]:
    """Resolve source shape bindings and build source row schemas."""

    schemas: dict[SourceDef, RowSchema] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if not isinstance(definition, SourceDef):
            continue

        schema, diagnostic = _check_source(
            definition,
            mode=mode,
            type_symbols=type_symbols,
            type_resolutions=type_resolutions,
            type_nullability=type_nullability,
        )
        schemas[definition] = schema
        if diagnostic is not None:
            diagnostics.append(diagnostic)

    return schemas, diagnostics


def _check_source(
    source: SourceDef,
    *,
    mode: CheckMode,
    type_symbols: Mapping[str, Definition],
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> tuple[RowSchema, Diagnostic | None]:
    """Check one source without inspecting its connector expression."""

    if source.shape_name is None:
        return _unknown_schema(), _untyped_source_diagnostic(source, mode)

    definition = type_symbols.get(source.shape_name)
    if isinstance(definition, ShapeDef):
        fields: dict[str, RowField] = {}
        for field in definition.fields:
            if field.name in fields:
                continue
            fields[field.name] = RowField(
                name=field.name,
                resolved_type=type_resolutions[field.type_expr],
                nullability=type_nullability[field.type_expr],
                definition=field,
            )
        return RowSchema(fields=fields), None

    if definition is None and source.shape_name not in BUILTIN_TYPE_NAMES:
        message = f"Unknown source shape: {source.shape_name}"
    else:
        message = f"Source shape must refer to a shape: {source.shape_name}"
    return _unknown_schema(), _source_diagnostic(
        source,
        severity=Severity.ERROR,
        message=message,
    )


def _unknown_schema() -> RowSchema:
    """Create an immutable unknown row schema."""

    return RowSchema(is_unknown=True)


def _untyped_source_diagnostic(
    source: SourceDef,
    mode: CheckMode,
) -> Diagnostic | None:
    """Apply the mode-sensitive policy for sources without a shape."""

    if mode is CheckMode.LOOSE:
        return None
    severity = Severity.WARNING if mode is CheckMode.CHECKED else Severity.ERROR
    return _source_diagnostic(
        source,
        severity=severity,
        message=f"Source {source.name} has no bound shape; row schema is unknown",
    )


def _source_diagnostic(
    source: SourceDef,
    *,
    severity: Severity,
    message: str,
) -> Diagnostic:
    """Create a source diagnostic at the complete definition span."""

    span = source.span
    return Diagnostic(
        code="PIE-S2303",
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
