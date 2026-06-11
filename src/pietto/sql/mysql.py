"""Private MySQL SQL generation skeleton."""

from __future__ import annotations

from typing import Protocol, cast

from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import (
    ConstraintIR,
    DefinitionIR,
    DeriveIR,
    EnumIR,
    RelationIR,
    ScriptIR,
    ShapeIR,
    SourceIR,
    SourceSpan,
    TypeIR,
)
from pietto.sql.model import SqlResult

_EMITTING_DEFINITION_TYPES = (RelationIR,)
_NON_EMITTING_DEFINITION_TYPES = (
    TypeIR,
    EnumIR,
    ShapeIR,
    SourceIR,
    ConstraintIR,
    DeriveIR,
)


class _DiagnosticDefinition(Protocol):
    """Minimum definition data needed for one backend diagnostic."""

    @property
    def name(self) -> str: ...

    @property
    def span(self) -> SourceSpan: ...


def emit_mysql_sql(script_ir: ScriptIR) -> SqlResult:
    """Skip metadata and fail closed until MySQL relation rendering exists."""

    diagnostics: list[Diagnostic] = []
    for definition in script_ir.definitions:
        if isinstance(definition, _NON_EMITTING_DEFINITION_TYPES):
            continue
        if isinstance(definition, _EMITTING_DEFINITION_TYPES):
            diagnostics.append(
                _unsupported_definition_diagnostic(
                    definition,
                    reason="MySQL relation rendering is not implemented",
                )
            )
            continue
        diagnostics.append(_unsupported_definition_diagnostic(definition))

    return SqlResult(artifacts=(), diagnostics=tuple(diagnostics))


def _unsupported_definition_diagnostic(
    definition: DefinitionIR,
    *,
    reason: str | None = None,
) -> Diagnostic:
    """Report one unsupported MySQL emission target at its IR span."""

    diagnostic_definition = cast(_DiagnosticDefinition, definition)
    span = diagnostic_definition.span
    message = (
        "MySQL SQL emission is not implemented for "
        f"{type(definition).__name__}: {diagnostic_definition.name}"
    )
    if reason is not None:
        message = f"{message}. {reason}"
    return Diagnostic(
        code="PIE-B1000",
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
